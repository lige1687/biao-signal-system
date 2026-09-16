"""三轮收口（r3 复核）浏览器链：分句级混合问法（两入口）。

固定验收：两入口
1. 「先解释ATR止损，不用比较，直接帮我回测」（先否定比较再肯定回测）→
   诚实「暂未支持」拦截，无任何非 GET backtest 流量、无补测任务卡，
   工作台上下文保持通信ETF；
2. 纯概念「ATR止损是什么意思？我不要求回测」→ 正常讨论回复
   （工作台等新答案卡出现再断言；控制台要求轮数净增+新请求）。
隔离服务（临时库、MODEL_MODE=degraded 无模型）。
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

RAW = Path(__file__).parent
SCREENS = RAW / "screens"
BASE = "http://127.0.0.1:8022"
MIXED = "先解释ATR止损，不用比较，直接帮我回测"
CONCEPT = "ATR止损是什么意思？我不要求回测"
INTERCEPT = "这项比较暂未支持"

requests_log: list[dict] = []


def _attach_network(page) -> None:
    def on_response(resp):
        req = resp.request
        if "/api/" not in req.url:
            return
        entry = {"method": req.method, "url": req.url.replace(BASE, ""),
                 "status": resp.status}
        if "/api/agent/chat" in req.url:
            try:
                entry["message"] = json.loads(req.post_data or "{}").get("message")
            except ValueError:
                pass
        requests_log.append(entry)

    page.on("response", on_response)


def _no_backtest_task_traffic() -> bool:
    return not any("/api/backtest" in r["url"] and r["method"] != "GET"
                   for r in requests_log)


def _wait_intercept(page, timeout_s: int = 30) -> bool:
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout_s:
        if page.locator(f"text={INTERCEPT}").count() > 0:
            return True
        time.sleep(0.4)
    return False


def run_workspace(page, notes: dict) -> None:
    page.goto(f"{BASE}/agent", wait_until="domcontentloaded")
    page.wait_for_selector("#agent-question", timeout=15000)
    box = page.locator("#agent-question")
    box.fill("就看515880，现在怎么看？")
    box.press("Enter")
    t0 = time.monotonic()
    while time.monotonic() - t0 < 90:
        if page.locator("text=复制文字").count() > 0:
            break
        time.sleep(0.5)
    ws = {}
    box.fill(MIXED)
    box.press("Enter")
    ws["mixed_intercepted"] = _wait_intercept(page)
    time.sleep(1.0)
    ws["mixed_no_backtest_task"] = page.locator("text=补测任务").count() == 0 \
        and _no_backtest_task_traffic()
    ws["mixed_context_kept"] = "通信ETF" in \
        page.locator(".ar-composer-context").inner_text()
    page.screenshot(path=str(SCREENS / "r3-ws-mixed-intercept.png"))
    # 纯概念：先等新答案卡数量净增，再等该卡离开工作态
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
    page.screenshot(path=str(SCREENS / "r3-ws-concept-answered.png"))
    notes["workspace"] = ws


def run_console(page, notes: dict) -> None:
    page.goto(f"{BASE}/symbol/515880.SS", wait_until="domcontentloaded")
    page.wait_for_selector("text=AI 助手", timeout=15000)
    page.locator("text=AI 助手").first.click()
    box = page.locator(".agent-console input")
    box.wait_for(timeout=10000)
    cs = {}
    before = page.locator(".agent-console .turn").count()
    box.fill(MIXED)
    box.press("Enter")
    cs["mixed_intercepted"] = _wait_intercept(page)
    cs["mixed_turn_grew"] = page.locator(".agent-console .turn").count() > before
    cs["mixed_no_backtest_task"] = page.locator("text=补测任务").count() == 0 \
        and _no_backtest_task_traffic()
    page.screenshot(path=str(SCREENS / "r3-console-mixed-intercept.png"))
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
    cs["concept_new_request"] = any(r.get("message") == CONCEPT for r in requests_log)
    cs["concept_answered_strict"] = (cnt > before2 and INTERCEPT not in last
                                     and len(last.strip()) > 40)
    page.screenshot(path=str(SCREENS / "r3-console-concept-answered.png"))
    notes["console"] = cs


def main() -> None:
    notes: dict = {"synthetic": True, "model_mode": "degraded",
                   "flow": "atr-clause-mixed-chain-r3"}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        _attach_network(page)
        run_workspace(page, notes)
        run_console(page, notes)
        browser.close()
    notes["no_backtest_task_traffic"] = _no_backtest_task_traffic()
    (RAW / "atr-clause-mixed-notes.json").write_text(
        json.dumps(notes, ensure_ascii=False, indent=1))
    (RAW / "atr-clause-mixed-requests.json").write_text(
        json.dumps(requests_log, ensure_ascii=False, indent=1))
    print(json.dumps(notes, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
