"""R2c：既有详情页表单（字段完整）→ 核对抽屉确认生效（2026-09-13）。

证明既有 UI 支持"字段完整的计划经页面确认生效"；同时核对会话草稿
保持 draft 未被确认。合成数据 + 临时库；不写真实台账。
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import urllib.request
from pathlib import Path

import re

from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent
PREVIEW_DB = Path("/Users/yongbiaoli/lei-agent-ux-20260913/docs/experiments/raw/"
                  "agent-user-experience-phase1-2026-09-13/preview/preview.db")
CONV_PLAN_PREFIX = "plan_516220_SS_20260913114346"  # 会话保存的草稿（前一轮 R2）


def db_states() -> dict[str, str]:
    tmp = Path(tempfile.mkdtemp()) / "ro.db"
    shutil.copy(PREVIEW_DB, tmp)
    conn = sqlite3.connect(tmp)
    rows = conn.execute("SELECT plan_id, state FROM trade_plans ORDER BY created_at").fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}


def main() -> int:
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        req_log = []
        page.on("request", lambda r: req_log.append(f">> {r.method} {r.url}") if "/api/plans" in r.url and "confirm" in r.url else None)
        page.on("response", lambda r: req_log.append(f"   <- {r.status} {r.url}") if "/api/plans" in r.url and "confirm" in r.url else None)
        page.goto("http://127.0.0.1:5174/symbol/516220", wait_until="domcontentloaded")
        page.get_by_role("button", name="建立执行计划").first.wait_for(state="visible", timeout=120000)
        page.get_by_role("button", name="建立执行计划").click()
        page.wait_for_timeout(1200)

        dlg = page.locator(".cp-card, [class*=dialog], [class*=create-plan]").last
        # 方向/模块默认（A/long）；逐项填写必填与硬阻断相关字段
        page.get_by_placeholder("如 2026-12-31").first.fill("2026-12-31")
        page.get_by_placeholder("如 first_ma_pullback").fill("first_ma_pullback")
        page.get_by_placeholder("一句话说明触发").fill("上升趋势首次回撤到均线附近（合成验证）")
        page.get_by_placeholder("如结构 C 点").fill("0.521")
        for label in ["交易假设", "失效标准", "回撤预案", "止盈预案", "止损预案"]:
            field = page.locator("label", has_text=label).last.locator("textarea, input").first
            field.fill(f"{label}（R2 合成验证：完整字段经页面确认）")
        page.get_by_role("button", name="建立草案（待核对）").click()
        # 核对抽屉出现
        page.wait_for_timeout(2500)
        drawer_text = page.locator("body").inner_text()
        results.append(("review-drawer-open", "PASS" if "符合性" in drawer_text or "确认" in drawer_text else "FAIL"))

        # 确认生效（抽屉内）
        confirm = page.get_by_role("button", name="确认生效", exact=True)
        confirm.wait_for(state="visible", timeout=30000)
        # 等符合性报告到达（按钮从禁用变可用），再确认
        page.wait_for_function(
            "() => { const b = [...document.querySelectorAll('button')].find(x => x.innerText.trim() === '确认生效');"
            " return b && !b.disabled; }", timeout=60000)
        confirm.click()
        page.wait_for_timeout(5000)
        states = db_states()
        new_armed = [pid for pid, s in states.items()
                     if s in ("armed", "entered") and not pid.startswith(CONV_PLAN_PREFIX)]
        results.append(("complete-plan-confirmed",
                        f"PASS(new={new_armed[:1]})" if new_armed else "FAIL"))
        conv_state = next((s for pid, s in states.items() if pid.startswith(CONV_PLAN_PREFIX)), "missing")
        results.append(("conversation-draft-still-draft",
                        f"PASS(state={conv_state})" if conv_state == "draft" else f"FAIL({conv_state})"))
        page.screenshot(path=str(OUT / "r2c-complete-plan-armed.png"))
        print("== confirm requests ==")
        for line in req_log:
            print(" ", line)
        # 抽屉内提示原文（如"暂时无法核实"或阻断文案）
        drawer = page.locator(".rv-conformance, [class*=rv-]").all_inner_texts()
        print("== drawer texts ==")
        for d in drawer[:4]:
            print(" ", d[:150].replace("\n", " | "))
        browser.close()

    print("== conversation draft untouched ==")
    ok = True
    for name, verdict in results:
        print(f"{name}: {verdict}")
        if verdict.startswith("FAIL"):
            ok = False
    return 0 if ok else 1




if __name__ == "__main__":
    main()
