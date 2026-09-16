"""三轮收口 G1 浏览器链（agent-continuity-zcode-closeout-r2-2026-09-17）。

固定验收（主控复核轮）：两入口
1. 混合问法「请解释一下用ATR止损回测，比较收益」→ 诚实「暂未支持」拦截，
   **不提交默认规则补测任务**（网络层无 /api/backtest 任务创建请求、页面无
   补测任务卡片、上下文保持通信ETF）；
2. 混合问法「先聊聊，再帮我用ATR止损补测」→ 同样拦截；
3. 纯概念「ATR止损是什么意思？我不要求回测」→ 正常讨论回复（工作台按
   本轮终态等待；控制台要求轮数净增+新请求，防上一轮提前满足）。
隔离服务（临时库、MODEL_MODE=degraded 无模型）；请求证据落
atr-mixed-requests.json；截图落 screens/。
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

RAW = Path(__file__).parent
SCREENS = RAW / "screens"
BASE = "http://127.0.0.1:8022"
MIXED_1 = "请解释一下用ATR止损回测，比较收益"
MIXED_2 = "先聊聊，再帮我用ATR止损补测"
CONCEPT = "ATR止损是什么意思？我不要求回测"
INTERCEPT = "这项比较暂未支持"

requests_log: list[dict] = []


def _attach_network(page) -> None:
    def on_response(resp):
        req = resp.request
        url = req.url
        if "/api/" not in url:
            return
        entry = {"method": req.method, "url": url.replace(BASE, ""),
                 "status": resp.status}
        if "/api/agent/chat" in url:
            try:
                d = json.loads(req.post_data or "{}")
                entry["message"] = d.get("message")
            except ValueError:
                pass
        requests_log.append(entry)

    page.on("response", on_response)


def _wait_done_marker(page, timeout_s: int = 90) -> None:
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout_s:
        if page.locator("text=复制文字").count() > 0:
            return
        time.sleep(0.4)


def _wait_intercept(page, timeout_s: int = 30) -> bool:
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout_s:
        if page.locator(f"text={INTERCEPT}").count() > 0:
            return True
        time.sleep(0.4)
    return False


def _no_backtest_traffic() -> bool:
    # 只有**任务创建类**（非 GET）backtest 流量才算提交任务；
    # GET /api/backtest/options 是面板配置读取，不是任务。
    return not any("/api/backtest" in r["url"] and r["method"] != "GET"
                   for r in requests_log)


def run_workspace(page, notes: dict) -> None:
    page.goto(f"{BASE}/agent", wait_until="domcontentloaded")
    page.wait_for_selector("#agent-question", timeout=15000)
    box = page.locator("#agent-question")
    box.fill("就看515880，现在怎么看？")
    box.press("Enter")
    _wait_done_marker(page, 90)
    ws = {}
    # 混合问法1 → 拦截、无默认规则任务、对象保持
    box.fill(MIXED_1)
    box.press("Enter")
    ws["mixed1_intercepted"] = _wait_intercept(page)
    time.sleep(1.0)
    ws["mixed1_no_backtest_task"] = page.locator("text=补测任务").count() == 0 \
        and _no_backtest_traffic()
    ws["mixed1_context_kept"] = "通信ETF" in \
        page.locator(".ar-composer-context").inner_text()
    page.screenshot(path=str(SCREENS / "r2-ws-mixed1-intercept.png"))
    # 混合问法2 → 拦截
    box.fill(MIXED_2)
    box.press("Enter")
    ws["mixed2_intercepted"] = _wait_intercept(page)
    time.sleep(1.0)
    ws["mixed2_no_backtest_task"] = page.locator("text=补测任务").count() == 0 \
        and _no_backtest_traffic()
    page.screenshot(path=str(SCREENS / "r2-ws-mixed2-intercept.png"))
    # 纯概念 → 讨论回复（非拦截复读）。先等**新**答案卡出现（拦截卡也算
    # ar-answer，必须等数量净增），再等该卡离开工作态，防止提前读旧卡。
    box.fill(CONCEPT)
    box.press("Enter")
    n_ans = page.locator("article.ar-answer").count()
    t0 = time.monotonic()
    while page.locator("article.ar-answer").count() <= n_ans and \
            time.monotonic() - t0 < 60:
        time.sleep(0.4)
    t0 = time.monotonic()
    while time.monotonic() - t0 < 90:
        last = page.locator("article.ar-answer").last.inner_text()
        if last.strip() and "正在整理" not in last and "仍在生成" not in last \
                and len(last.strip()) > 40:
            break
        time.sleep(0.5)
    last = page.locator("article.ar-answer").last.inner_text()
    ws["concept_new_card"] = page.locator("article.ar-answer").count() > n_ans
    ws["concept_answered"] = INTERCEPT not in last and len(last.strip()) > 40
    ws["concept_reached_backend"] = any(
        r.get("message") == CONCEPT for r in requests_log)
    ws["concept_no_backtest_task"] = page.locator("text=补测任务").count() == 0
    page.screenshot(path=str(SCREENS / "r2-ws-concept-answered.png"))
    notes["workspace"] = ws


def run_console(page, notes: dict) -> None:
    page.goto(f"{BASE}/symbol/515880.SS", wait_until="domcontentloaded")
    page.wait_for_selector("text=AI 助手", timeout=15000)
    page.locator("text=AI 助手").first.click()
    box = page.locator(".agent-console input")
    box.wait_for(timeout=10000)
    cs = {}
    # 混合问法1 → 拦截、无任务
    before = page.locator(".agent-console .turn").count()
    box.fill(MIXED_1)
    box.press("Enter")
    cs["mixed1_intercepted"] = _wait_intercept(page)
    cs["mixed1_turn_grew"] = page.locator(".agent-console .turn").count() > before
    cs["mixed1_no_backtest_task"] = page.locator("text=补测任务").count() == 0 \
        and _no_backtest_traffic()
    page.screenshot(path=str(SCREENS / "r2-console-mixed1-intercept.png"))
    # 混合问法2 → 拦截
    box.fill(MIXED_2)
    box.press("Enter")
    cs["mixed2_intercepted"] = _wait_intercept(page)
    cs["mixed2_no_backtest_task"] = page.locator("text=补测任务").count() == 0 \
        and _no_backtest_traffic()
    # 纯概念 → 严格：轮数净增 + 新请求 + 回复无拦截语
    box.fill(CONCEPT)
    before2 = page.locator(".agent-console .turn").count()
    box.press("Enter")
    t0 = time.monotonic()
    while time.monotonic() - t0 < 90:
        turns = page.locator(".agent-console .turn")
        cnt = turns.count()
        if cnt > before2:
            last = turns.nth(cnt - 1).inner_text()
            if ("正在整理" not in last and "仍在生成" not in last
                    and "等待系统" not in last
                    and ("数据直出" in last or "依据系统数据" in last or "截至" in last)):
                break
        time.sleep(0.5)
    turns = page.locator(".agent-console .turn")
    cnt = turns.count()
    last = turns.nth(cnt - 1).inner_text() if cnt else ""
    cs["concept_turn_grew"] = cnt > before2
    cs["concept_new_request"] = any(
        r.get("message") == CONCEPT for r in requests_log)
    cs["concept_answered_strict"] = (cnt > before2 and INTERCEPT not in last
                                     and len(last.strip()) > 40)
    page.screenshot(path=str(SCREENS / "r2-console-concept-answered.png"))
    notes["console"] = cs


def main() -> None:
    notes: dict = {"synthetic": True, "model_mode": "degraded",
                   "flow": "atr-mixed-chain-r2"}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        _attach_network(page)
        run_workspace(page, notes)
        run_console(page, notes)
        browser.close()
    notes["no_backtest_api_traffic"] = _no_backtest_traffic()
    (RAW / "atr-mixed-notes.json").write_text(
        json.dumps(notes, ensure_ascii=False, indent=1))
    (RAW / "atr-mixed-requests.json").write_text(
        json.dumps(requests_log, ensure_ascii=False, indent=1))
    print(json.dumps(notes, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
