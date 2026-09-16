"""二轮复验遗漏二·固定验收（端到端）：中断→刷新→历史→真实点击重试。

隔离服务 8023 + 桩模型（第1次请求断流、第2次正常），零真实模型请求。
验收链：中断（部分正文+未完成标记）→ 刷新页面 → 打开历史载入 →
未完成标注与「重试生成」按钮可见（身份来自服务端投影，非猜）→
真实点击重试 → 桩累计 2 次调用 → 原问题数仍 1 → 再次刷新恢复显示
最终回答，旧部分原文保留；已完成问题不再出现重试入口。
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

RAW = Path(__file__).parent
SCREENS = RAW / "screens"
BASE = "http://127.0.0.1:8023"
QUESTION = "510300 最近怎么看？先说判断，再讲机会和风险，现有依据够不够？"


def main() -> dict:
    out: dict = {"scenario": "recheck2-history-retry-e2e"}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{BASE}/agent", wait_until="domcontentloaded")
        page.wait_for_timeout(1200)
        box = page.locator("#agent-question")
        box.fill(QUESTION)
        box.press("Enter")
        # 中断：部分正文 + 未完成标记
        page.wait_for_selector("text=AI 讲解未完成", timeout=60_000)
        out["interrupt_notice"] = True
        page.screenshot(path=str(SCREENS / "R2-interrupted.png"))

        # 刷新 → 打开历史 → 载入会话
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(1200)
        if page.get_by_role("button", name="收起历史对话").count() == 0:
            page.get_by_role("button", name="展开历史对话").click()
        page.locator(".ar-history-item").first.click()
        page.wait_for_selector("text=以下是按当时内容恢复的历史记录", timeout=15_000)
        page.wait_for_timeout(800)
        out["history_incomplete_label"] = page.get_by_text(
            "此回答当时未完成").count() > 0
        retry_btn = page.get_by_role(
            "button", name="重试生成这个回答（复用原问题与依据，不新增记录）")
        out["history_retry_button_visible"] = retry_btn.count() > 0
        page.screenshot(path=str(SCREENS / "R2-history-retry-visible.png"))

        # 真实点击重试 → 等完成
        retry_btn.first.click()
        page.wait_for_selector("text=停止接收", state="detached", timeout=120_000)
        page.wait_for_timeout(800)
        out["after_retry_answer_count"] = page.locator("article.ar-answer").count()
        out["after_retry_has_full_text"] = page.get_by_text("按这份数据，510300").count() > 0
        page.screenshot(path=str(SCREENS / "R2-after-retry.png"))

        # 再次刷新恢复：最终回答显示；已完成问题不再出现重试入口
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(1200)
        if page.get_by_role("button", name="收起历史对话").count() == 0:
            page.get_by_role("button", name="展开历史对话").click()
        page.locator(".ar-history-item").first.click()
        page.wait_for_selector("text=以下是按当时内容恢复的历史记录", timeout=15_000)
        page.wait_for_timeout(800)
        out["final_restore_answer_count"] = page.locator("article.ar-answer").count()
        out["final_restore_retry_buttons"] = page.get_by_role(
            "button", name="重试生成这个回答（复用原问题与依据，不新增记录）").count()
        out["final_restore_incomplete_labels"] = page.get_by_text("此回答当时未完成").count()
        page.screenshot(path=str(SCREENS / "R2-final-restore.png"))
        browser.close()

    env = json.loads((RAW / "environment-iso-stub.json").read_text())
    conn = sqlite3.connect(env["temporary_db"])
    out["db"] = {
        "questions": conn.execute(
            "SELECT COUNT(*) FROM agent_messages WHERE role='user'").fetchone()[0],
        "answers": conn.execute(
            "SELECT COUNT(*) FROM agent_messages WHERE role='assistant'").fetchone()[0],
        "request_state": conn.execute(
            "SELECT answer_state FROM agent_chat_requests").fetchone()[0],
        "trade_plans": conn.execute("SELECT COUNT(*) FROM trade_plans").fetchone()[0],
        "fund_trades": conn.execute("SELECT COUNT(*) FROM fund_trades").fetchone()[0],
    }
    conn.close()
    (RAW / "acceptance-R2-history-retry.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2))
    return out


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False, indent=2))
