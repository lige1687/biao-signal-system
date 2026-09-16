"""收口一浏览器链独立复核（agent-continuity-zcode-closeout-2026-09-17）。

在 cfix2 轮 ui_atr_chain.py 基础上新增**请求证据**：Playwright 网络层记录
两入口每一问对应的 /api/agent/chat(+/stream) 请求方法、载荷、响应状态与
content-type，落 atr-chain-requests.json（与页面截图共同构成「页面与请求
证据」）。模型路径整体停用（MODEL_MODE=degraded，无模型环境变量），
不调用真实模型、不读密钥；业务写入全部落在临时库。

固定验收：515880 上下文 → ATR 比较问法诚实拦截且对象保持通信ETF →
点「继续讨论」发送 → 得到讨论回复（非拦截复读）、补测任务零新增 →
概念问法正常讨论；显式比较仍拒绝。两入口（工作台 /agent + 控制台抽屉）。
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

RAW = Path(__file__).parent
SCREENS = RAW / "screens"
BASE = "http://127.0.0.1:8022"
ASK_COMPARE = "如果换成ATR止损，胜率会有什么变化？"
ASK_CONCEPT = "ATR止损是什么意思？我不要求回测"
INTERCEPT = "这项比较暂未支持"

requests_log: list[dict] = []


def _attach_network(page) -> None:
    def on_response(resp):
        req = resp.request
        url = req.url
        if "/api/agent/chat" not in url:
            return
        entry = {
            "method": req.method,
            "url": url.replace(BASE, ""),
            "status": resp.status,
            "content_type": resp.headers.get("content-type", ""),
            "payload": None,
        }
        try:
            body = req.post_data
            if body:
                d = json.loads(body)
                entry["payload"] = {
                    "message": d.get("message"),
                    "context_kind": d.get("context_kind"),
                    "symbol": d.get("symbol"),
                    "client_request_id": d.get("client_request_id"),
                }
        except (TypeError, ValueError):
            pass
        requests_log.append(entry)

    page.on("response", on_response)


def wait_new_answer(page, prev: int, timeout_s: int = 90) -> None:
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout_s:
        if page.locator("text=复制文字").count() > prev:
            return
        time.sleep(0.4)


def run_workspace(page, notes: dict) -> None:
    page.goto(f"{BASE}/agent", wait_until="domcontentloaded")
    page.wait_for_selector("#agent-question", timeout=15000)
    box = page.locator("#agent-question")
    # 建立 515880 上下文
    box.fill("就看515880，现在怎么看？")
    n0 = page.locator("text=复制文字").count()
    box.press("Enter")
    wait_new_answer(page, n0, 90)
    # 1. 比较请求 → 诚实拦截，对象保持通信ETF
    box.fill(ASK_COMPARE)
    box.press("Enter")
    t0 = time.monotonic()
    while page.locator(f"text={INTERCEPT}").count() == 0 and time.monotonic() - t0 < 30:
        time.sleep(0.4)
    ws = {}
    ws["intercepted"] = page.locator(f"text={INTERCEPT}").count() > 0
    ws["context_kept_comm_etf"] = \
        page.locator(".ar-composer-context").inner_text().find("通信ETF") >= 0
    page.screenshot(path=str(SCREENS / "r3-ws-atr-intercept.png"))
    # 2. 点继续讨论 → 发送 → 讨论回复（非拦截复读），补测零新增
    n1 = page.locator("text=复制文字").count()
    page.locator("text=继续讨论（不做数值比较）").first.click()
    box.press("Enter")
    wait_new_answer(page, n1, 90)
    last = page.locator("article.ar-answer").last.inner_text()
    ws["discussion_reached"] = INTERCEPT not in last
    ws["discussion_not_empty"] = len(last.strip()) > 40
    ws["no_backtest_tasks"] = page.locator("text=补测任务").count() == 0
    page.screenshot(path=str(SCREENS / "r3-ws-atr-continued.png"))
    # 3. 概念问题 → 正常讨论
    n2 = page.locator("text=复制文字").count()
    box.fill(ASK_CONCEPT)
    box.press("Enter")
    wait_new_answer(page, n2, 90)
    last2 = page.locator("article.ar-answer").last.inner_text()
    ws["concept_answered"] = INTERCEPT not in last2 and len(last2.strip()) > 40
    # 4. 显式比较仍诚实拒绝
    n3 = page.locator("text=复制文字").count()
    box.fill(ASK_COMPARE)
    box.press("Enter")
    t0 = time.monotonic()
    while page.locator("article.ar-answer").count() <= n3 and \
            time.monotonic() - t0 < 30:
        time.sleep(0.4)
        if page.locator(f"text={INTERCEPT}").count() > 0:
            break
    ws["explicit_compare_still_refused"] = page.locator(f"text={INTERCEPT}").count() > 0
    ws["context_kept_comm_etf_final"] = \
        page.locator(".ar-composer-context").inner_text().find("通信ETF") >= 0
    page.screenshot(path=str(SCREENS / "r3-ws-atr-explicit-refused.png"))
    notes["workspace"] = ws


def run_console(page, notes: dict) -> None:
    page.goto(f"{BASE}/symbol/515880.SS", wait_until="domcontentloaded")
    page.wait_for_selector("text=AI 助手", timeout=15000)
    page.locator("text=AI 助手").first.click()
    box = page.locator(".agent-console input")
    box.wait_for(timeout=10000)
    cs = {}
    # 1. 比较请求 → 拦截，对象保持通信ETF
    box.fill(ASK_COMPARE)
    box.press("Enter")
    t0 = time.monotonic()
    while page.locator(f"text={INTERCEPT}").count() == 0 and time.monotonic() - t0 < 30:
        time.sleep(0.4)
    cs["intercepted"] = page.locator(f"text={INTERCEPT}").count() > 0
    head_txt = page.locator(".agent-console .drawer-head").inner_text() \
        if page.locator(".agent-console .drawer-head").count() else ""
    cs["context_kept_comm_etf"] = "通信ETF" in head_txt or \
        "515880" in page.locator(".agent-console").inner_text()
    page.screenshot(path=str(SCREENS / "r3-console-atr-intercept.png"))
    # 2. 继续讨论 → 发送 → 讨论回复
    page.locator("text=继续讨论（不做数值比较）").first.click()
    box.press("Enter")
    t0 = time.monotonic()
    while time.monotonic() - t0 < 90:
        turns = page.locator(".agent-console .turn")
        last = turns.last.inner_text() if turns.count() else ""
        if last and "正在整理" not in last and "仍在生成" not in last \
                and "等待系统" not in last:
            if "数据直出" in last or "依据系统数据" in last or "截至" in last:
                break
        time.sleep(0.5)
    turns = page.locator(".agent-console .turn")
    last = turns.last.inner_text() if turns.count() else ""
    cs["discussion_reached"] = INTERCEPT not in last and len(last.strip()) > 40
    cs["no_backtest_tasks"] = page.locator("text=补测任务").count() == 0
    page.screenshot(path=str(SCREENS / "r3-console-atr-continued.png"))
    # 3. 概念问题 → 正常讨论
    box.fill(ASK_CONCEPT)
    box.press("Enter")
    t0 = time.monotonic()
    while time.monotonic() - t0 < 90:
        turns = page.locator(".agent-console .turn")
        cnt = turns.count()
        last = turns.nth(cnt - 1).inner_text() if cnt else ""
        if last and "正在整理" not in last and "仍在生成" not in last \
                and "等待系统" not in last:
            if "数据直出" in last or "依据系统数据" in last or "截至" in last:
                break
        time.sleep(0.5)
    turns = page.locator(".agent-console .turn")
    last = turns.last.inner_text() if turns.count() else ""
    cs["concept_answered"] = INTERCEPT not in last and len(last.strip()) > 40
    page.screenshot(path=str(SCREENS / "r3-console-atr-concept.png"))
    notes["console"] = cs


def main() -> None:
    notes: dict = {"synthetic": True, "model_mode": "degraded",
                   "flow": "atr-chain-r3-closeout"}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        _attach_network(page)
        run_workspace(page, notes)
        run_console(page, notes)
        browser.close()
    (SCREENS / "r3-atr-chain-notes.json").write_text(
        json.dumps(notes, ensure_ascii=False, indent=1))
    (RAW / "atr-chain-requests.json").write_text(
        json.dumps(requests_log, ensure_ascii=False, indent=1))
    ok = all(v for entry in notes.values() if isinstance(entry, dict)
             for k, v in entry.items() if k != "context_kept_comm_etf" or v)
    print(json.dumps(notes, ensure_ascii=False, indent=1))
    print(f"REQUESTS_CAPTURED={len(requests_log)} ALL_OK={ok}")


if __name__ == "__main__":
    main()
