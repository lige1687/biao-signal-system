"""C1—C3 补修验证（2026-09-13 主控三轮复核固定项）。

真实浏览器（Playwright+本机 Chrome）+ 真后端 + 合成夹具 + 本地假模型 +
临时库。C3 的 503/409 分支用**明确标注的合成响应注入**（Playwright route
fulfill）驱动前端提示逻辑，分别覆盖三条渲染分支；422/正例走真实后端。
结构化结果写 RESULTS-C.json；任一 FAIL → 退出码 1。
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent
PREVIEW_DB = Path("/Users/yongbiaoli/lei-agent-ux-20260913/docs/experiments/raw/"
                  "agent-user-experience-phase1-2026-09-13/preview/preview.db")
BASE = "http://127.0.0.1:8014"
WEB = "http://127.0.0.1:5174"
RESULTS: list[dict] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append({"check": name, "verdict": "PASS" if ok else "FAIL", "detail": detail})
    print(f"{'PASS' if ok else 'FAIL'} | {name}" + (f" | {detail}" if detail else ""))


def db_plans() -> dict[str, str]:
    tmp = Path(tempfile.mkdtemp()) / "ro.db"
    shutil.copy(PREVIEW_DB, tmp)
    conn = sqlite3.connect(tmp)
    plans = dict(conn.execute("SELECT plan_id, state FROM trade_plans").fetchall())
    conn.close()
    return plans


def db_plan_full(plan_id: str) -> dict | None:
    tmp = Path(tempfile.mkdtemp()) / "ro.db"
    shutil.copy(PREVIEW_DB, tmp)
    conn = sqlite3.connect(tmp)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT plan_id, state, ruleset_version "
        "FROM trade_plans WHERE plan_id = ?", (plan_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def main() -> int:
    plans_before = db_plans()

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        # ============ C1：三路径版本失败/恢复 ============
        # C1.a 讨论路径（工作台卡片）：abort → 保存禁用+提示 → 恢复 → 可保存
        page.goto(f"{WEB}/agent", wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        page.evaluate("""(() => {
          const ta = document.querySelector('.ar-composer textarea');
          const setter = Object.getOwnPropertyDescriptor(
            window.HTMLTextAreaElement.prototype, 'value').set;
          setter.call(ta, 'TH881272 帮我把当前的买点整理成计划');
          ta.dispatchEvent(new Event('input', { bubbles: true }));
          const b = [...document.querySelectorAll('.ar-composer button')]
            .find(x => x.innerText.includes('发送'));
          b.click();
        })()""")
        page.locator(".plan-draft-card").first.wait_for(state="visible", timeout=90000)
        card = page.locator(".plan-draft-card").first
        page.context.route("**/plans/ruleset-version", lambda route: route.abort())
        # 刷新后从历史面板重新打开该会话（工作台不自动恢复上一会话）；
        # 该会话尚未保存过计划（无 plan_draft 绑定）→ 卡片 planId 为空
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        hist = page.locator(".ar-history-item", has_text="TH881272").filter(
            has_not_text="再帮").first
        hist.wait_for(state="visible", timeout=60000)
        hist.click()
        page.wait_for_timeout(4000)
        card = page.locator(".plan-draft-card").first
        card.wait_for(state="visible", timeout=60000)
        save_btn = card.get_by_role("button", name="保存草稿")
        save_btn.wait_for(state="visible", timeout=30000)
        c1a_blocked = save_btn.is_disabled()
        c1a_hint = "规则集版本读取失败" in card.inner_text() and "重新读取" in card.inner_text()
        check("C1.a discussion path: load-failure blocks save with retry hint",
              c1a_blocked and c1a_hint, f"disabled={c1a_blocked} hint={c1a_hint}")
        page.context.unroute("**/plans/ruleset-version")
        card.get_by_role("button", name="重新读取").click()
        page.wait_for_timeout(1500)
        check("C1.a recovery enables save",
              not save_btn.is_disabled(), f"disabled={save_btn.is_disabled()}")

        # C1.b/C1.c 技术入场与持仓监督（详情页表单；其余字段填齐避免掩盖）
        page.goto(f"{WEB}/symbol/516220", wait_until="domcontentloaded")
        page.get_by_role("button", name="建立执行计划").first.wait_for(
            state="visible", timeout=120000)

        def dialog_form_paths(ruleset_ok: bool) -> dict:
            captured = {}
            def handler(route):
                captured["called"] = True
                if ruleset_ok:
                    route.fulfill(status=200, content_type="application/json",
                                  body=json.dumps({"ruleset_version": "2.1.0"}))
                else:
                    route.abort()
            return handler, captured

        # 技术入场
        h_ok, _ = dialog_form_paths(True)
        page.context.route("**/plans/ruleset-version", h_ok)
        page.get_by_role("button", name="建立执行计划").click()
        page.wait_for_timeout(1200)
        entry_btn = page.get_by_role("button", name="建立草案（待核对）")
        page.context.unroute("**/plans/ruleset-version")
        h_bad, _ = dialog_form_paths(False)
        page.context.route("**/plans/ruleset-version", h_bad)
        page.reload(wait_until="domcontentloaded")
        page.get_by_role("button", name="建立执行计划").first.wait_for(
            state="visible", timeout=120000)
        page.get_by_role("button", name="建立执行计划").click()
        page.wait_for_timeout(1500)
        entry_btn = page.get_by_role("button", name="建立草案（待核对）")
        # 其余必填先填齐（避免“被其他空字段禁用”的误判）
        page.get_by_placeholder("如 2026-12-31").first.fill("2099-12-31")
        page.get_by_placeholder("一句话说明触发").fill("C1 验收触发说明")
        for label in ["交易假设", "失效标准", "回撤预案", "止盈预案", "止损预案"]:
            page.locator("label", has_text=label).last.locator("textarea, input").first.fill(
                f"{label}（C1 验收）")
        page.wait_for_timeout(300)
        entry_blocked = entry_btn.is_disabled()
        body_text = page.locator("body").inner_text()
        check("C1.b entry form: load-failure blocks submit with hint",
              entry_blocked and "规则集版本读取失败" in body_text,
              f"disabled={entry_blocked}")
        # 恢复：重新读取成功后按钮即可用（其余字段已齐，唯一变量是版本）
        h_rec, _ = dialog_form_paths(True)
        page.context.route("**/plans/ruleset-version", h_rec)
        page.get_by_role("button", name="重新读取").first.click()
        page.wait_for_timeout(1500)
        check("C1.b entry form: recovery enables submit",
              not entry_btn.is_disabled(), f"disabled={entry_btn.is_disabled()}")

        # 持仓监督：填齐退出预案/有效期/触发，再单独关掉版本
        page.get_by_role("button", name="持仓盯盘（已有仓位）").click()
        page.wait_for_timeout(600)
        page.get_by_placeholder("如 2026-12-31").last.fill("2099-12-31")
        page.get_by_placeholder("涨到此价提醒", exact=False).fill("10")
        page.get_by_placeholder("跌破此价提醒", exact=False).fill("5")
        for label in ["止盈预案", "止损预案"]:
            page.locator("label", has_text=label).last.locator("textarea, input").first.fill(
                f"{label}（C1 验收）")
        holding_btn = page.get_by_role("button", name="建立草案（待核对）")
        page.context.unroute("**/plans/ruleset-version")
        h_bad2, _ = dialog_form_paths(False)
        page.context.route("**/plans/ruleset-version", h_bad2)
        page.reload(wait_until="domcontentloaded")
        page.get_by_role("button", name="建立执行计划").first.wait_for(
            state="visible", timeout=120000)
        page.get_by_role("button", name="建立执行计划").click()
        page.wait_for_timeout(1200)
        page.get_by_role("button", name="持仓盯盘（已有仓位）").click()
        page.wait_for_timeout(400)
        page.get_by_placeholder("如 2026-12-31").last.fill("2099-12-31")
        page.get_by_placeholder("涨到此价提醒", exact=False).fill("10")
        page.get_by_placeholder("跌破此价提醒", exact=False).fill("5")
        for label in ["止盈预案", "止损预案"]:
            page.locator("label", has_text=label).last.locator("textarea, input").first.fill(
                f"{label}（C1 验收）")
        holding_btn = page.get_by_role("button", name="建立草案（待核对）")
        holding_blocked = holding_btn.is_disabled()
        body_text = page.locator("body").inner_text()
        page.context.unroute("**/plans/ruleset-version")
        check("C1.c holding form: load-failure blocks submit with hint",
              holding_blocked and "规则集版本读取失败" in body_text,
              f"disabled={holding_blocked}")
        h_rec2, _ = dialog_form_paths(True)
        page.context.route("**/plans/ruleset-version", h_rec2)
        page.get_by_role("button", name="重新读取").first.click()
        page.wait_for_timeout(1500)
        check("C1.c holding form: recovery enables submit",
              not holding_btn.is_disabled(), f"disabled={holding_btn.is_disabled()}")
        page.context.unroute("**/plans/ruleset-version")
        # 不真正创建持仓计划：关闭对话框（验证目的已达）
        # 清理：关闭对话框（不创建）
        page.evaluate("document.querySelector('.drawer-overlay')?.click()")
        page.wait_for_timeout(400)

        # ============ C2：响应丢失后重试复用原快照 ============
        page.goto(f"{WEB}/agent", wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        page.evaluate("""(() => {
          const ta = document.querySelector('.ar-composer textarea');
          const setter = Object.getOwnPropertyDescriptor(
            window.HTMLTextAreaElement.prototype, 'value').set;
          setter.call(ta, 'TH881272 帮我把当前的买点整理成计划');
          ta.dispatchEvent(new Event('input', { bubbles: true }));
          const b = [...document.querySelectorAll('.ar-composer button')]
            .find(x => x.innerText.includes('发送'));
          b.click();
        })()""")
        card = page.locator(".plan-draft-card").first
        card.wait_for(state="visible", timeout=90000)
        page.wait_for_function(
            "() => { const c = document.querySelector('.plan-draft-card');"
            " if (!c) return false; const b = [...c.querySelectorAll('button')]"
            ".find(x => x.innerText.trim() === '保存草稿'); return b && !b.disabled; }",
            timeout=60000)
        plans_before_c2 = db_plans()

        # 首次保存：服务端真实落库，但响应以网络错误丢弃（模拟响应丢失）
        first_payload: dict = {}
        def lose_response(route):
            import json as _json
            req = route.request
            first_payload.update(_json.loads(req.post_data or "{}"))
            # 真实落库（服务端处理成功），客户端只收到网络错误
            import urllib.request as _u
            rq = _u.Request(BASE + "/api/plans", data=(req.post_data or "").encode("utf-8"),
                            headers={"Content-Type": "application/json"}, method="POST")
            resp = _u.urlopen(rq)
            first_payload["_server_plan_id"] = _json.loads(resp.read())["plan_id"]
            route.abort()
        page.context.route("**/api/plans", lose_response)
        card.get_by_role("button", name="保存草稿").click()
        page.wait_for_timeout(2500)
        page.context.unroute("**/api/plans")
        server_plan_id = first_payload.get("_server_plan_id", "")
        # 客户端进入“结果未知”态：核对保存结果按钮出现
        check("C2.1 lost-response enters unknown-result state",
              page.get_by_role("button", name="核对保存结果").count() == 1
              and bool(server_plan_id),
              f"server_plan_id={server_plan_id[:36]}")
        # 版本缓存“变化”（合成注入 3.0.0）：重试仍复用快照版本
        page.context.route("**/plans/ruleset-version", lambda route: route.fulfill(
            status=200, content_type="application/json",
            body=json.dumps({"ruleset_version": "3.0.0"})))
        page.get_by_role("button", name="核对保存结果").click()
        page.wait_for_timeout(3500)
        page.context.unroute("**/plans/ruleset-version")
        card_text = card.inner_text()
        plan_now = db_plan_full(server_plan_id) if server_plan_id else None
        same_id = server_plan_id in card_text
        idempotent = len([x for x in db_plans()]) == len(plans_before_c2) + 1
        original_version = (plan_now or {}).get("ruleset_version") == first_payload.get("ruleset_version")
        check("C2.2 retry reuses snapshot: same plan_id, original version, no duplicate",
              same_id and idempotent and original_version and plan_now["state"] == "draft",
              f"id_in_card={same_id} idempotent={idempotent} "
              f"version={plan_now and plan_now.get('ruleset_version')}")

        # ============ C3：三种错误的页面提示不冲突 ============
        # C3.a 422（真实）：保存后未补失效价直接确认 → 引导「补齐并核对」
        page.get_by_role("button", name="确认生效").click()
        page.wait_for_timeout(3000)
        t = card.inner_text()
        c422 = ("补齐并核对" in t or "编辑本草稿" in t) and "另建新草稿" not in t.split("确认生效")[0]
        check("C3.a 422 guides editing the same draft", c422, t[-160:].replace("\n", " | "))

        # C3.b 503（合成响应注入，明确标注）：提示“稍后重试”
        def fulfill_503(route):
            route.fulfill(status=503, content_type="application/json", body=json.dumps(
                {"detail": {"code": "ANALYSIS_UNAVAILABLE",
                            "message": "分析服务暂时缺席（合成注入测试）"}}))
        page.context.route("**/confirm", fulfill_503)
        card.get_by_role("button", name="确认生效").click()
        page.wait_for_timeout(2500)
        page.context.unroute("**/confirm")
        t = card.inner_text()
        c503 = "稍后重试" in t and "另建新草稿" not in t
        check("C3.b 503 guides retry-later (injected response)", c503, t[-160:].replace("\n", " | "))

        # C3.c 409 版本变更（合成响应注入，明确标注）：提示“另建新草稿”，不指向原地编辑
        def fulfill_409(route):
            route.fulfill(status=409, content_type="application/json", body=json.dumps(
                {"detail": {"code": "RULESET_VERSION_CHANGED",
                            "message": "计划基于规则集 1.3.0，当前为 2.1.0；请复核后重建草稿"}}))
        page.context.route("**/confirm", fulfill_409)
        card.get_by_role("button", name="确认生效").click()
        page.wait_for_timeout(2500)
        page.context.unroute("**/confirm")
        t = card.inner_text()
        c409 = "另建新草稿" in t and "补齐并核对\" 修改本草稿" not in t
        check("C3.c 409 guides rebuild (not in-place edit)", c409, t[-180:].replace("\n", " | "))

        # ============ G4 补充：已保存未确认 draft 的历史恢复 ============
        page.goto(f"{WEB}/agent", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        hist = page.locator(".ar-history-item", has_text="TH881272").filter(
            has_not_text="再帮").first
        hist.wait_for(state="visible", timeout=90000)
        hist.click()
        page.wait_for_timeout(4000)
        rc = page.locator(".plan-draft-card").first
        rt = rc.inner_text()
        has_binding = server_plan_id and server_plan_id in rt
        draft_state_shown = "草稿（可补齐/核对后确认）" in rt
        no_resave = rc.get_by_role("button", name="保存草稿").count() == 0
        check("G4.x draft history restore shows saved state, no re-save",
              has_binding and draft_state_shown and no_resave,
              f"binding={has_binding} draftShown={draft_state_shown} noResave={no_resave}")
        page.screenshot(path=str(OUT / "c-fixes-draft-restore.png"))

        # ============ G5.1 补充：控制台实际点开核对抽屉 ============
        page.goto(f"{WEB}/symbol/th881272", wait_until="domcontentloaded")
        page.get_by_role("button", name="AI 助手").first.wait_for(
            state="visible", timeout=120000)
        page.get_by_role("button", name="AI 助手").first.click()
        page.wait_for_timeout(1500)
        page.evaluate("""(() => {
          const inp = document.querySelector('.drawer-input input');
          const setter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value').set;
          setter.call(inp, '帮我把当前的买点整理成计划');
          inp.dispatchEvent(new Event('input', { bubbles: true }));
          const b = [...document.querySelectorAll('.drawer-input button')]
            .find(x => x.innerText === '发送');
          b.click();
        })()""")
        cc = page.locator(".agent-console .plan-draft-card").first
        cc.wait_for(state="visible", timeout=90000)
        cc.get_by_role("button", name="保存草稿").click()
        cc.get_by_role("button", name="补齐并核对").wait_for(state="visible", timeout=30000)
        cc.get_by_role("button", name="补齐并核对").click()
        page.locator(".agent-console .rv-panel").wait_for(state="visible", timeout=30000)
        drawer_has_plan = "监督员 · 计划核对" in page.locator(".agent-console .rv-panel").inner_text()
        check("G5.1 console actually opens review drawer for the saved plan",
              drawer_has_plan, f"drawer={drawer_has_plan}")
        browser.close()

    ok = all(r["verdict"] == "PASS" for r in RESULTS)
    Path(OUT / "RESULTS-C.json").write_text(json.dumps(
        {"results": RESULTS}, ensure_ascii=False, indent=2))
    print(f"\nTOTAL: {sum(r['verdict']=='PASS' for r in RESULTS)}/{len(RESULTS)} PASS")
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    try:
        code = main()
    except Exception as exc:
        check("script-crashed", False, f"{type(exc).__name__}: {exc}")
        Path(OUT / "RESULTS-C.json").write_text(json.dumps(
            {"results": RESULTS}, ensure_ascii=False, indent=2))
        code = 1
    sys.exit(code)
