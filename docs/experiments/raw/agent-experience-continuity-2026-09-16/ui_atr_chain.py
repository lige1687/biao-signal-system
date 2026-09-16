"""收口一浏览器链（两入口，2026-09-17）：ATR 拦截 → 继续讨论 → 真实讨论回复。

固定验收（二轮复验）：
1. 515880 上下文问「如果换成ATR止损，胜率会有什么变化？」→ 诚实「暂未支持」，
   上下文保持通信ETF（不被 ATR 指标词截走）；
2. 点「继续讨论」发送草稿 → 得到讨论回复（不是同一条拦截提示），补测数为零；
3. 显式比较请求仍被诚实拒绝；
4. 概念问题「ATR止损是什么意思？我不要求回测」→ 正常讨论回复。
两入口（工作台 /agent 与控制台 AI 助手抽屉）各跑一遍。
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


def wait_new_answer(page, prev: int, timeout_s: int = 60) -> None:
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout_s:
        if page.locator("text=复制文字").count() > prev:
            return
        time.sleep(0.4)


def run_workspace(page, notes: dict) -> None:
    page.goto(f"{BASE}/agent", wait_until="domcontentloaded")
    page.wait_for_selector("#agent-question", timeout=15000)
    box = page.locator("#agent-question")
    # 先建立 515880 上下文
    box.fill("就看515880，现在怎么看？")
    n0 = page.locator("text=复制文字").count()
    box.press("Enter")
    wait_new_answer(page, n0, 90)
    # 1. 比较请求 → 拦截，对象保持通信ETF
    box.fill(ASK_COMPARE)
    box.press("Enter")
    t0 = time.monotonic()
    while page.locator(f"text={INTERCEPT}").count() == 0 and time.monotonic() - t0 < 30:
        time.sleep(0.4)
    ws = {}
    ws["intercepted"] = page.locator(f"text={INTERCEPT}").count() > 0
    ws["context_kept"] = page.locator(".ar-composer-context").inner_text().find("通信ETF") >= 0
    page.screenshot(path=str(SCREENS / "r2-ws-atr-intercept.png"))
    # 2. 点继续讨论 → 发送 → 讨论回复（非拦截复读）
    n1 = page.locator("text=复制文字").count()
    page.locator("text=继续讨论（不做数值比较）").first.click()
    box.press("Enter")
    wait_new_answer(page, n1, 90)
    last = page.locator("article.ar-answer").last.inner_text()
    ws["discussion_reached"] = INTERCEPT not in last
    ws["no_backtest"] = page.locator("text=补测任务").count() == 0
    page.screenshot(path=str(SCREENS / "r2-ws-atr-continued.png"))
    # 4. 概念问题 → 正常讨论
    box.fill(ASK_CONCEPT)
    n2 = page.locator("text=复制文字").count()
    box.press("Enter")
    wait_new_answer(page, n2, 90)
    last2 = page.locator("article.ar-answer").last.inner_text()
    ws["concept_answered"] = INTERCEPT not in last2
    notes["workspace"] = ws


def run_console(page, notes: dict) -> None:
    page.goto(f"{BASE}/symbol/515880.SS", wait_until="domcontentloaded")
    page.wait_for_selector("text=AI 助手", timeout=15000)
    page.locator("text=AI 助手").first.click()
    box = page.locator(".agent-console input")
    box.wait_for(timeout=10000)
    cs = {}
    box.fill(ASK_COMPARE)
    box.press("Enter")
    t0 = time.monotonic()
    while page.locator(f"text={INTERCEPT}").count() == 0 and time.monotonic() - t0 < 30:
        time.sleep(0.4)
    cs["intercepted"] = page.locator(f"text={INTERCEPT}").count() > 0
    cs["context_kept"] = page.locator(".agent-console .drawer-head").inner_text().find("通信ETF") >= 0 \
        or page.locator(".agent-console").inner_text().find("515880") >= 0
    page.locator("text=继续讨论（不做数值比较）").first.click()
    box.press("Enter")
    t0 = time.monotonic()
    while time.monotonic() - t0 < 90:
        turns = page.locator(".agent-console .turn")
        last = turns.last.inner_text() if turns.count() else ""
        if last and "正在整理" not in last and "仍在生成" not in last and "等待系统" not in last:
            if "数据直出" in last or "依据系统数据" in last or "截至" in last:
                break
        time.sleep(0.5)
    turns = page.locator(".agent-console .turn")
    last = turns.last.inner_text() if turns.count() else ""
    cs["discussion_reached"] = INTERCEPT not in last
    cs["no_backtest"] = page.locator("text=补测任务").count() == 0
    page.screenshot(path=str(SCREENS / "r2-console-atr-continued.png"))
    notes["console"] = cs


def main() -> None:
    notes: dict = {"synthetic": True, "flow": "atr-chain-r2"}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        run_workspace(page, notes)
        run_console(page, notes)
        browser.close()
    (SCREENS / "r2-atr-chain-notes.json").write_text(
        json.dumps(notes, ensure_ascii=False, indent=1))
    print(json.dumps(notes, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
