"""验收D（v2）：两入口分阶段展示 + 迟到响应不串入 + 刷新恢复 + 不重复记录。

在独立端口（8022，桩模型）运行。产品事实：工作台流式期间禁用「新对话/
历史」，逃逸路径是「停止接收」（中断=本次回答不落历史）；控制台可通过
切标的在流式期间重置会话。

Part1 迟到守卫（工作台）：发问 → 资料先显 → 停止接收 → 新对话 → 等服务端
  完成 → 新视图无迟到内容；历史里只有问题（停止不落假回答）。
Part2 分阶段+恢复+刷新（工作台）：完整走完一轮 → 新对话 → 历史载入回答 →
  刷新后再载入 → 回答与资料卡恢复；sqlite 计数核对不重复。
Part3 控制台：/symbol/510300 抽屉发问 → 资料卡先显 → 流式期间切到
  /symbol/510880 → 等完成后回来 → 新视图无旧回答串入。
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

RAW = Path(__file__).parent
SCREENS = RAW / "screens"
BASE = os.environ.get("ISO_BASE", "http://127.0.0.1:8022")
QUESTION = "510300 最近怎么看？先说判断，再讲机会和风险，现有依据够不够？"


def ms(t0: float) -> int:
    return int((time.monotonic() - t0) * 1000)


def load_history_first(page) -> None:
    if page.get_by_role("button", name="收起历史对话").count() == 0:
        page.get_by_role("button", name="展开历史对话").click()
    page.locator(".ar-history-item").first.click()
    page.wait_for_selector("text=以下是按当时内容恢复的历史记录", timeout=15_000)
    page.wait_for_timeout(800)


def main() -> dict:
    out: dict = {"scenario": "d-two-entries-v2", "base": BASE}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)

        # ---------- Part1：迟到守卫（停止接收 → 新对话） ----------
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{BASE}/agent", wait_until="domcontentloaded")
        page.wait_for_timeout(1200)
        box = page.locator("#agent-question")
        box.fill(QUESTION)
        t0 = time.monotonic()
        box.press("Enter")
        page.wait_for_selector("text=系统资料已就绪", timeout=60_000)
        out["p1_ws_t_facts_ms"] = ms(t0)
        page.screenshot(path=str(SCREENS / "D-ws-facts.png"))
        page.get_by_role("button", name="停止接收").click()
        page.wait_for_timeout(800)
        page.get_by_role("button", name="新对话", exact=True).click()
        page.wait_for_timeout(1500)
        # 等服务端把旧流走完（桩 8s 首字延迟 + 生成）
        page.wait_for_timeout(12_000)
        out["p1_new_session_no_late_answer"] = (
            page.locator("article.ar-answer").count() == 0)
        page.screenshot(path=str(SCREENS / "D-ws-new-session-no-late.png"))
        # 停止的会话在历史里只有问题、没有回答（不落假记录）
        load_history_first(page)
        out["p1_stopped_session_history_answers"] = page.locator("article.ar-answer").count()
        out["p1_stopped_session_history_questions"] = page.locator(".ar-user-message").count()
        # 开新会话给 Part2 用
        page.get_by_role("button", name="新对话", exact=True).click()
        page.wait_for_timeout(600)

        # ---------- Part2：分阶段 + 完成 + 恢复 + 刷新 ----------
        box.fill(QUESTION)
        t1 = time.monotonic()
        box.press("Enter")
        page.wait_for_selector("text=系统资料已就绪", timeout=60_000)
        out["p2_t_facts_ms"] = ms(t1)
        page.screenshot(path=str(SCREENS / "D-ws-p2-facts.png"))
        page.wait_for_selector("text=停止接收", state="detached", timeout=120_000)
        out["p2_t_done_ms"] = ms(t1)
        out["p2_answer_len"] = len(
            page.locator("article.ar-answer").last.inner_text(timeout=10_000))
        page.get_by_role("button", name="新对话", exact=True).click()
        page.wait_for_timeout(800)
        load_history_first(page)
        out["p2_restored_answer_count"] = page.locator("article.ar-answer").count()
        out["p2_restored_text_len"] = len(
            page.locator("article.ar-answer").last.inner_text(timeout=10_000))
        page.screenshot(path=str(SCREENS / "D-ws-restored.png"))
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(1200)
        load_history_first(page)
        out["p2_after_reload_restored_count"] = page.locator("article.ar-answer").count()
        page.screenshot(path=str(SCREENS / "D-ws-after-reload.png"))
        page.close()

        # ---------- Part3：控制台抽屉（切标的中断迟到路径） ----------
        page2 = browser.new_page(viewport={"width": 1440, "height": 900})
        page2.goto(f"{BASE}/symbol/510300", wait_until="domcontentloaded")
        page2.wait_for_timeout(2500)
        page2.get_by_role("button", name="AI 助手").click()
        page2.wait_for_timeout(600)
        cbox = page2.get_by_placeholder("就这个标的讨论（多轮记忆）")
        cbox.fill(QUESTION)
        t2 = time.monotonic()
        cbox.press("Enter")
        page2.wait_for_selector("text=系统资料已就绪", timeout=60_000)
        out["p3_console_t_facts_ms"] = ms(t2)
        page2.screenshot(path=str(SCREENS / "D-console-facts.png"))
        # 流式期间直接切标的（抽屉随路由重置，旧流迟到内容不得串入新会话）
        page2.goto(f"{BASE}/symbol/510880", wait_until="domcontentloaded")
        page2.wait_for_timeout(2000)
        page2.get_by_role("button", name="AI 助手").click()
        page2.wait_for_timeout(800)
        page2.wait_for_timeout(12_000)  # 等旧流服务端完成
        out["p3_console_after_switch_turns"] = page2.locator(
            "aside.agent-console .turn").count()
        page2.screenshot(path=str(SCREENS / "D-console-after-switch.png"))
        browser.close()

    # ---------- 记录计数（D 服务器的临时库） ----------
    env = json.loads((RAW / "environment-iso-stub.json").read_text())
    db = env["temporary_db"]
    conn = sqlite3.connect(db)
    out["db_counts"] = {
        "messages": conn.execute("SELECT COUNT(*) FROM agent_messages").fetchone()[0],
        "sessions": conn.execute("SELECT COUNT(*) FROM agent_sessions").fetchone()[0],
        "trade_plans": conn.execute("SELECT COUNT(*) FROM trade_plans").fetchone()[0],
        "fund_trades": conn.execute("SELECT COUNT(*) FROM fund_trades").fetchone()[0],
        "answers": conn.execute(
            "SELECT COUNT(*) FROM agent_messages WHERE role='assistant'").fetchone()[0],
        "questions": conn.execute(
            "SELECT COUNT(*) FROM agent_messages WHERE role='user' AND question_id IS NOT NULL"
        ).fetchone()[0],
    }
    conn.close()
    (RAW / "acceptance-D-result.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2))
    return out


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False, indent=2))
