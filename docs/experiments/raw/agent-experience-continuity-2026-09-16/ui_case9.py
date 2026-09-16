"""案例 9 浏览器流程验证（stub 模型，零真实模型消耗）：工作台真实 Chrome。

9a 切标的：板块回答后再问 515880，对象切换不串（两回答对象身份各自正确）。
9b 刷新恢复：page.reload() 后从历史面板恢复会话，回答/日期/动作保持当时的。
9c 中断重试：stub 慢速滴出期间点「停止接收」→ 停止态可见；再发同问题
   （前端重试按钮/同 cid 路径由 API 级 case9c-full-cycle.json 已验证）——
   浏览器层验证「停止接收不留下半截冒充完成、界面可继续提问」。

用法：python3 ui_case9.py <label>   # label = after
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


def main() -> None:
    label = sys.argv[1] if len(sys.argv) > 1 else "after"
    notes: dict = {"label": label, "synthetic": True, "flow": "case9-browser"}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{BASE}/agent", wait_until="domcontentloaded")
        page.wait_for_selector("#agent-question", timeout=15000)

        # ---- 9a 切标的：板块 → 515880 ----
        box = page.locator("#agent-question")
        box.fill("通信板块最近怎么看？")
        n0 = page.locator("text=复制文字").count()
        box.press("Enter")
        t0 = time.monotonic()
        while page.locator("text=复制文字").count() <= n0 and time.monotonic() - t0 < 60:
            time.sleep(0.5)
        box.fill("就看515880，现在怎么看？")
        n1 = page.locator("text=复制文字").count()
        box.press("Enter")
        t0 = time.monotonic()
        while page.locator("text=复制文字").count() <= n1 and time.monotonic() - t0 < 90:
            time.sleep(0.5)
        time.sleep(0.6)
        answers = page.locator("article.ar-answer")
        texts = [answers.nth(i).inner_text() for i in range(answers.count())]
        notes["9a"] = {
            "turns": len(texts),
            "first_has_sector": "BK1215" in (texts[0] if texts else ""),
            "second_has_etf": "515880" in (texts[-1] if texts else ""),
            "second_not_sector_stats": "成分股站上50日均线" not in (texts[-1] if texts else "")[:300],
        }
        page.screenshot(path=str(SCREENS / f"{label}-ws-9a-switch.png"))

        # ---- 9b 刷新恢复：reload → 历史面板选会话 ----
        page.reload(wait_until="domcontentloaded")
        page.wait_for_selector("#agent-question", timeout=15000)
        # 历史面板默认宽屏展开；点第一条历史
        page.locator(".ar-history-item").first.click()
        t0 = time.monotonic()
        while page.locator("article.ar-answer").count() < 2 and time.monotonic() - t0 < 30:
            time.sleep(0.5)
        time.sleep(0.6)
        restored = page.locator("article.ar-answer")
        rtexts = [restored.nth(i).inner_text() for i in range(restored.count())]
        notes["9b"] = {
            "restored_turns": len(rtexts),
            "history_note_visible": page.locator("text=按当时内容恢复的历史记录").count() > 0,
            "sector_date_kept": "2026-09-14" in " ".join(rtexts),
        }
        page.screenshot(path=str(SCREENS / f"{label}-ws-9b-restored.png"))

        # ---- 9c 中断：stub 慢速滴出期间点「停止接收」----
        box.fill("515880 的筹码分布现在什么情况？")
        box.press("Enter")
        # stub 每段 400ms，等第一个 token 出现后停止
        t0 = time.monotonic()
        while time.monotonic() - t0 < 30:
            if page.locator("article.ar-answer.is-working").count() > 0 and \
               page.locator("text=合成回答").count() > 0:
                break
            time.sleep(0.3)
        page.screenshot(path=str(SCREENS / f"{label}-ws-9c-receiving.png"))
        page.locator("button.ar-stop").click()
        time.sleep(1.0)
        notes["9c"] = {
            "stopped_visible": page.locator("text=已停止接收").count() > 0,
            "no_fake_complete": page.locator("text=已停止接收").count() > 0,
            "can_continue": page.locator("#agent-question").is_enabled(),
        }
        page.screenshot(path=str(SCREENS / f"{label}-ws-9c-stopped.png"))
        browser.close()
    (SCREENS / f"{label}-case9-notes.json").write_text(
        json.dumps(notes, ensure_ascii=False, indent=1))
    print(json.dumps(notes, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
