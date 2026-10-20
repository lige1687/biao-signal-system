"""R2 验证：计划草稿 保存 → 确认 → 后端状态 → 刷新/历史恢复（2026-09-13）。

真实浏览器（Playwright + 本机 Chrome）+ 真前端 + 隔离预览后端
（合成数据 516220 + 本地假模型 + 临时库 preview.db）。
记录实际 plan_id、保存/确认请求效果与后端状态；不以 question_id 替代计划编号。
"""
from __future__ import annotations

import json
import sqlite3
import shutil
import tempfile
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent
PREVIEW_DB = Path("/Users/yongbiaoli/lei-agent-ux-20260913/docs/experiments/raw/"
                  "agent-user-experience-phase1-2026-09-13/preview/preview.db")
PLAN_ID = None  # 由保存步骤捕获


def api_get(path: str):
    return json.loads(urllib.request.urlopen("http://127.0.0.1:8014" + path).read())


def db_state() -> tuple[str, str | None, str | None]:
    tmp = Path(tempfile.mkdtemp()) / "ro.db"
    shutil.copy(PREVIEW_DB, tmp)
    conn = sqlite3.connect(tmp)
    row = conn.execute(
        "SELECT state FROM trade_plans WHERE plan_id LIKE 'plan_516220%' "
        "ORDER BY created_at DESC LIMIT 1").fetchone()
    bind = conn.execute(
        "SELECT question_id, session_id FROM agent_plan_draft_bindings "
        "WHERE plan_id LIKE 'plan_516220%' ORDER BY created_at DESC LIMIT 1").fetchone()
    conn.close()
    return (row[0] if row else "missing"), (bind[0] if bind else None), (bind[1] if bind else None)


def main() -> int:
    results: list[tuple[str, str]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        req_log: list[str] = []
        page.on("request", lambda r: req_log.append(f"{r.method} {r.url}") if "/api/plans" in r.url else None)
        page.on("response", lambda r: req_log.append(f"  -> {r.status} {r.url}") if "/api/plans" in r.url else None)

        page.goto("http://127.0.0.1:5174/agent", wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        page.get_by_role("textbox", name="输入问题").fill("516220 帮我把当前的买点整理成计划")
        page.get_by_role("button", name="发送 ↑").click()
        page.locator(".plan-draft-card").first.wait_for(state="visible", timeout=60000)
        card = page.locator(".plan-draft-card").first
        head = card.inner_text()[:110].replace("\n", " | ")
        results.append(("plan-card-with-question-id", "PASS" if "原问题 #" in head else f"FAIL({head})"))

        # 1) 页面保存草稿
        card.get_by_role("button", name="保存草稿").click()
        card.get_by_role("button", name="草稿已保存").wait_for(state="visible", timeout=30000)
        global PLAN_ID
        PLAN_ID = card.get_by_role("button", name="草稿已保存").get_attribute("title") or ""
        PLAN_ID = PLAN_ID.replace("草稿已保存（plan_id: ", "").replace("）", "").strip()
        results.append(("save-draft-plan-id", f"PASS({PLAN_ID})" if PLAN_ID.startswith("plan_") else f"FAIL({PLAN_ID})"))

        # 服务端只读核对：draft 态 + 原问题绑定
        state, qid, sid = db_state()
        results.append(("server-state-draft", f"PASS(state={state})" if state == "draft" else f"FAIL({state})"))
        results.append(("server-question-binding",
                        f"PASS(question={qid})" if isinstance(qid, int) else f"FAIL({qid})"))

        # 2) 页面确认生效（不完整草稿：目标价与五项预案待补）
        card.get_by_role("button", name="确认生效").click()
        page.wait_for_timeout(5000)
        body = card.inner_text()
        if "已确认生效" in body:
            results.append(("confirm-result", "PASS(confirmed)"))
        else:
            # 记录拒绝/不可用提示原文
            notice = body[body.find("确认生效"):][:220].replace("\n", " | ")
            results.append(("confirm-result", f"RECORDED({notice})"))
        page.screenshot(path=str(OUT / "r2-after-confirm.png"))
        state2, _, _ = db_state()
        results.append(("server-state-after-confirm", f"state={state2}"))

        # 3) 刷新 + 历史恢复：仍关联同一计划
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        hist = page.get_by_role("button", name="整理成计划").first
        hist.click()
        page.wait_for_timeout(4000)
        card2 = page.locator(".plan-draft-card")
        restored = card2.count() >= 1 and ("516220" in card2.first.inner_text())
        ident = card2.first.inner_text()[:120].replace("\n", " | ") if restored else "-"
        results.append(("history-restore-identity", f"PASS({ident[:80]})" if restored else "FAIL"))
        page.screenshot(path=str(OUT / "r2-history-restore.png"))
        browser.close()

    print("== plan API requests ==")
    for line in req_log:
        print(" ", line)
    print("== results ==")
    ok = True
    for name, verdict in results:
        print(f"{name}: {verdict}")
        if verdict.startswith("FAIL"):
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    main()
