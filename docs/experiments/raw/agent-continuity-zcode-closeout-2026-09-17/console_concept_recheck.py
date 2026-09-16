"""控制台概念问法复测（r3 修正）：上轮 ui_atr_chain_r3.py 的控制台概念一步
等待条件可能被上一轮已完成回答提前满足（无新请求也判通过）。本脚本只跑
控制台抽屉的概念问法，硬性要求：① .turn 轮数净增；② 网络层出现该消息的
新 /api/agent/chat 请求；③ 新末轮不含拦截语且非空。"""
from __future__ import annotations

import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

RAW = Path(__file__).parent
SCREENS = RAW / "screens"
BASE = "http://127.0.0.1:8022"
ASK_CONCEPT = "ATR止损是什么意思？我不要求回测"
INTERCEPT = "这项比较暂未支持"

captured: list[dict] = []


def main() -> None:
    notes: dict = {"synthetic": True, "model_mode": "degraded",
                   "flow": "console-concept-recheck-r3"}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        def on_response(resp):
            if "/api/agent/chat" in resp.request.url:
                try:
                    d = json.loads(resp.request.post_data or "{}")
                except ValueError:
                    d = {}
                captured.append({"message": d.get("message"),
                                 "status": resp.status,
                                 "url": resp.request.url.replace(BASE, "")})

        page.on("response", on_response)
        page.goto(f"{BASE}/symbol/515880.SS", wait_until="domcontentloaded")
        page.wait_for_selector("text=AI 助手", timeout=15000)
        page.locator("text=AI 助手").first.click()
        box = page.locator(".agent-console input")
        box.wait_for(timeout=10000)
        cs = {}
        box.fill(ASK_CONCEPT)
        before = page.locator(".agent-console .turn").count()
        box.press("Enter")
        t0 = time.monotonic()
        while time.monotonic() - t0 < 90:
            turns = page.locator(".agent-console .turn")
            cnt = turns.count()
            if cnt > before:
                last = turns.nth(cnt - 1).inner_text()
                if ("正在整理" not in last and "仍在生成" not in last
                        and "等待系统" not in last
                        and ("数据直出" in last or "依据系统数据" in last
                             or "截至" in last)):
                    break
            time.sleep(0.5)
        turns = page.locator(".agent-console .turn")
        cnt = turns.count()
        last = turns.nth(cnt - 1).inner_text() if cnt else ""
        cs["turn_count_increased"] = cnt > before
        cs["new_request_seen"] = any(
            c.get("message") == ASK_CONCEPT for c in captured)
        cs["concept_answered_strict"] = (cnt > before and INTERCEPT not in last
                                         and len(last.strip()) > 40)
        page.screenshot(path=str(SCREENS / "r3-console-atr-concept-recheck.png"))
        notes["console_concept"] = cs
        browser.close()
    notes["captured"] = captured
    (RAW / "console-concept-recheck.json").write_text(
        json.dumps(notes, ensure_ascii=False, indent=1))
    print(json.dumps(notes, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
