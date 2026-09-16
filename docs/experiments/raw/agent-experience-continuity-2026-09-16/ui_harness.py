"""真实浏览器验收（agent-experience-continuity-2026-09-16，Playwright + 系统 Chrome）。

只驱动真实构建前端与真实 SSE 流，不替换任何前端逻辑。
对照 inputs-and-acceptance.md：案例 1/3/4 走工作台，案例 1/3 走控制台，外加一个窄屏。

用法：python3 ui_harness.py <label>     # label = before | after
截图落 screens/<label>-*.png；同时落 screens/<label>-dom-notes.json
（每屏的关键文字摘录：对象、资料日期、首句、回答字数），供改前/改后逐字对照。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

RAW = Path(__file__).parent
SCREENS = RAW / "screens"
BASE = "http://127.0.0.1:8022"

CASE1 = "通信板块最近怎么看？"
CASE3 = "就看515880，现在怎么看？"
CASE4 = "先别买，什么情况值得再看？"


def _launch(p):
    return p.chromium.launch(channel="chrome", headless=True)


def wait_answer_done(page, timeout_s: int = 60) -> None:
    """等当前回答到达终态：出现动作条（工作台）或动作区（控制台）。"""
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout_s:
        if page.locator("text=复制文字").count() > 0:
            return
        if page.locator("text=判定层数据直出").count() > 0 or \
           page.locator("text=依据系统数据").count() > 0:
            time.sleep(0.5)
            return
        time.sleep(0.5)


def workspace_cases(page, label: str, notes: dict) -> None:
    page.goto(f"{BASE}/agent", wait_until="domcontentloaded")
    page.wait_for_selector("#agent-question", timeout=15000)
    for case_id, question in (("case1", CASE1), ("case3", CASE3), ("case4", CASE4)):
        box = page.locator("#agent-question")
        box.fill(question)
        box.press("Enter")
        wait_answer_done(page)
        time.sleep(0.8)
        answers = page.locator("article.ar-answer")
        last = answers.last
        text = last.inner_text()
        notes[f"workspace-{case_id}"] = {
            "question": question,
            "answer_excerpt": text[:600],
            "answer_chars": len(text),
        }
        page.screenshot(path=str(SCREENS / f"{label}-ws-{case_id}.png"), full_page=False)


def console_cases(page, label: str, notes: dict) -> None:
    page.goto(f"{BASE}/agent", wait_until="domcontentloaded")
    page.wait_for_selector("#agent-question", timeout=15000)
    page.locator("text=AI 助手").first.click()
    page.wait_for_selector(".agent-console input", timeout=10000)
    for case_id, question in (("case1", CASE1), ("case3", CASE3)):
        box = page.locator(".agent-console input")
        box.fill(question)
        box.press("Enter")
        wait_answer_done(page)
        time.sleep(0.8)
        turns = page.locator(".agent-console .turn")
        texts = [turns.nth(i).inner_text() for i in range(turns.count())]
        notes[f"console-{case_id}"] = {
            "question": question,
            "answer_excerpt": (texts[-1] if texts else "")[:600],
        }
        page.screenshot(path=str(SCREENS / f"{label}-console-{case_id}.png"), full_page=False)


def narrow_case(page, label: str, notes: dict) -> None:
    page.set_viewport_size({"width": 480, "height": 900})
    page.goto(f"{BASE}/agent", wait_until="domcontentloaded")
    page.wait_for_selector("#agent-question", timeout=15000)
    box = page.locator("#agent-question")
    box.fill(CASE3)
    box.press("Enter")
    wait_answer_done(page)
    time.sleep(0.8)
    page.screenshot(path=str(SCREENS / f"{label}-ws-narrow-case3.png"), full_page=False)
    notes["narrow-case3"] = {"question": CASE3, "viewport": "480x900"}
    page.set_viewport_size({"width": 1440, "height": 900})


def main() -> None:
    label = sys.argv[1] if len(sys.argv) > 1 else "before"
    SCREENS.mkdir(exist_ok=True)
    notes: dict = {"label": label, "base": BASE, "synthetic": True,
                   "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    with sync_playwright() as p:
        browser = _launch(p)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        workspace_cases(page, label, notes)
        console_cases(page, label, notes)
        narrow_case(page, label, notes)
        browser.close()
    (SCREENS / f"{label}-dom-notes.json").write_text(
        json.dumps(notes, ensure_ascii=False, indent=1))
    print(f"DONE {label}: {len(notes) - 3} captures")


if __name__ == "__main__":
    main()
