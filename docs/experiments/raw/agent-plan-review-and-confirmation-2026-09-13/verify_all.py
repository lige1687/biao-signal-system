"""计划补齐、确认与历史恢复——六组验收（2026-09-13）。

真实浏览器（Playwright+本机 Chrome）+ 真后端 + 合成夹具（TH881272/516220）
+ 本地假模型 + 临时库 preview.db。结构化逐项结果写入 RESULTS.json；
任一 FAIL → 进程退出码 1。合成/真实界限：行情与分析为测试夹具，模型为
本地假模型桩；确认/拒绝/保存/恢复全部走真实后端路由与 SQLite。
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
BASE = "http://127.0.0.1:8014"
WEB = "http://127.0.0.1:5174"
RESULTS: list[dict] = []
PLAN_LOG: list[dict] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append({"check": name, "verdict": "PASS" if ok else "FAIL", "detail": detail})
    print(f"{'PASS' if ok else 'FAIL'} | {name}" + (f" | {detail}" if detail else ""))


def api_get(path: str):
    return json.loads(urllib.request.urlopen(BASE + path).read())


def db_snapshot() -> tuple[dict[str, str], int]:
    tmp = Path(tempfile.mkdtemp()) / "ro.db"
    shutil.copy(PREVIEW_DB, tmp)
    conn = sqlite3.connect(tmp)
    plans = dict(conn.execute("SELECT plan_id, state FROM trade_plans").fetchall())
    trades = conn.execute("SELECT count(*) FROM fund_trades").fetchone()[0]
    conn.close()
    return plans, trades


def db_bindings() -> list[tuple]:
    tmp = Path(tempfile.mkdtemp()) / "ro.db"
    shutil.copy(PREVIEW_DB, tmp)
    conn = sqlite3.connect(tmp)
    rows = conn.execute(
        "SELECT plan_id, question_id, session_id FROM agent_plan_draft_bindings "
        "ORDER BY created_at").fetchall()
    conn.close()
    return rows


def js_click_send(page) -> None:
    """React 受控输入：以原生 setter 写值 + 触发 input 事件，再点发送。"""
    page.evaluate("""(() => {
      const ta = document.querySelector('.ar-composer textarea');
      const setter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype, 'value').set;
      setter.call(ta, window.__msg);
      ta.dispatchEvent(new Event('input', { bubbles: true }));
      const b = [...document.querySelectorAll('.ar-composer button')]
        .find(x => x.innerText.includes('发送'));
      b.click();
    })()""")


def ask_and_wait_plan(page, message: str) -> None:
    page.evaluate(f"window.__msg = {json.dumps(message)}")
    js_click_send(page)
    page.locator(".plan-draft-card").first.wait_for(state="visible", timeout=90000)
    page.wait_for_timeout(800)


def save_and_get_plan_id(page) -> str:
    card = page.locator(".plan-draft-card").first
    page.wait_for_function(
        "() => { const c = document.querySelector('.plan-draft-card');"
        " if (!c) return false; const b = [...c.querySelectorAll('button')]"
        ".find(x => x.innerText.trim() === '保存草稿'); return b && !b.disabled; }",
        timeout=60000)
    card.get_by_role("button", name="保存草稿").click()
    # 保存成功的新形态：出现「补齐并核对」+ plan_id 文本（保存按钮隐藏）
    card.get_by_role("button", name="补齐并核对").wait_for(state="visible", timeout=30000)
    m = re.search(r"plan_id:\s*(plan_[0-9A-Za-z_]+)", card.inner_text())
    if not m:
        raise RuntimeError("保存后未见 plan_id，卡片原文："
                           + card.inner_text()[:400].replace("\n", " | "))
    return m.group(1)


def main() -> int:
    plans_before, trades_before = db_snapshot()
    check("G0 baseline: preview db ready", True,
          f"plans={len(plans_before)} fund_trades={trades_before}")

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("request", lambda r: PLAN_LOG.append(
            {"method": r.method, "url": r.url}) if "/api/plans" in r.url else None)
        page.on("response", lambda r: PLAN_LOG.append(
            {"status": r.status, "url": r.url}) if "/api/plans" in r.url else None)

        # ---------- G1 版本：服务端权威 + 失败不空版本 ----------
        v = api_get("/api/plans/ruleset-version")["ruleset_version"]
        check("G1.1 ruleset-version endpoint is authoritative", v == "2.1.0", f"v={v}")

        page.goto(f"{WEB}/symbol/516220", wait_until="domcontentloaded")
        page.get_by_role("button", name="建立执行计划").first.wait_for(
            state="visible", timeout=120000)
        page.context.route("**/plans/ruleset-version", lambda route: route.abort())
        page.get_by_role("button", name="建立执行计划").click()
        page.wait_for_timeout(1500)
        create_btn = page.get_by_role("button", name="建立草案（待核对）")
        blocked = create_btn.is_disabled()
        hint = "规则集版本" in page.locator("body").inner_text()
        check("G1.2 load-failure blocks submit (no empty version)",
              blocked and hint, f"disabled={blocked} hint={hint}")
        page.context.unroute("**/plans/ruleset-version")
        page.goto(f"{WEB}/agent", wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        # ---------- G2 真实正例：TH881272 讨论→保存→补齐→确认 armed ----------
        page.goto(f"{WEB}/agent", wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        ask_and_wait_plan(page, "TH881272 帮我把当前的买点整理成计划")
        card = page.locator(".plan-draft-card").first
        card_text = card.inner_text()
        check("G2.1 P3 legal prefill (C/two_b_reversal)",
              "C · long" in card_text and "two_b_reversal" in card_text,
              card_text[:90].replace("\n", " | "))

        plan_id_a = save_and_get_plan_id(page)
        check("G2.2 save returns real plan_id",
              plan_id_a.startswith("plan_") and "TH881272" in plan_id_a,
              plan_id_a)

        # G3b（先证拒绝边界）：未补失效价直接确认 → 422 MISSING_INVALIDATION
        card.get_by_role("button", name="确认生效").click()
        page.wait_for_timeout(3500)
        body = card.inner_text()
        rejected = "草稿已保存但未激活" in body and "补齐并核对" in body
        state_after_reject = db_snapshot()[0].get(plan_id_a)
        check("G3.1 incomplete draft confirm rejected, still editable",
              rejected and state_after_reject == "draft",
              f"state={state_after_reject}")

        # 补齐并核对 → 编辑计划 → 填齐 → 保存修改 → 确认生效
        card.get_by_role("button", name="补齐并核对").click()
        page.locator(".rv-panel").wait_for(state="visible", timeout=30000)
        page.get_by_role("button", name="编辑计划").click()
        page.wait_for_timeout(1200)
        page.get_by_placeholder("如 2026-12-31").first.fill("2099-12-31")
        page.get_by_placeholder("如结构 C 点").fill("0.55")
        for label in ["交易假设", "失效标准", "回撤预案", "止盈预案", "止损预案"]:
            page.locator("label", has_text=label).last.locator("textarea, input").first.fill(
                f"{label}（计划流程验收：用户明确补齐）")
        page.get_by_role("button", name="保存修改").click()
        page.wait_for_timeout(2500)
        drawer_confirm = page.locator(".rv-panel").get_by_role(
            "button", name="确认生效", exact=True)
        drawer_confirm.wait_for(state="visible", timeout=30000)
        # 等符合性报告回填（按钮从禁用变可用）再点，消除间歇 no-op
        page.wait_for_function(
            "() => { const p = document.querySelector('.rv-panel'); if (!p) return false;"
            " const b = [...p.querySelectorAll('button')]"
            ".find(x => x.innerText.trim() === '确认生效'); return b && !b.disabled; }",
            timeout=60000)
        drawer_confirm.click()
        page.wait_for_timeout(4000)
        states_now = db_snapshot()[0]
        armed_ok = states_now.get(plan_id_a) == "armed"
        diag = ""
        if not armed_ok:
            rv = page.locator(".rv-panel")
            diag = rv.inner_text()[-220:].replace("\n", " | ") if rv.count() else "drawer closed"
        check("G2.3 complete→confirm 200, state=armed", armed_ok,
              f"state={states_now.get(plan_id_a)} {diag}")
        page.screenshot(path=str(OUT / "g2-armed.png"))

        # ---------- G4 身份与历史：armed 恢复不重存；第二问题独立绑定 ----------
        page.goto(f"{WEB}/agent", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        # 会话列表由 react-query 加载（宽屏历史面板默认展开）；后端标题截断
        # 为 16 字，用「TH881272」+非「再帮」定位首个正例会话
        hist = page.locator(".ar-history-item", has_text="TH881272").filter(
            has_not_text="再帮").first
        hist.wait_for(state="visible", timeout=90000)
        hist.click()
        page.wait_for_timeout(4000)
        card2 = page.locator(".plan-draft-card").first
        restored = card2.inner_text()
        check("G4.1 history restore shows armed status without re-save",
              "已确认生效" in restored and "草稿已保存" not in restored
              and plan_id_a in restored,
              restored[:110].replace("\n", " | "))
        plans_after_restore, trades_after = db_snapshot()
        check("G4.2 restore adds no plans/trades",
              len(plans_after_restore) == len(plans_before) + 1 and trades_after == trades_before,
              f"plans={len(plans_after_restore)} trades={trades_after}")

        # 同一标的不同问题 → 不同 plan_id、各自绑定
        page.get_by_role("button", name="新对话").first.click()
        page.wait_for_timeout(800)
        ask_and_wait_plan(page, "TH881272 再帮我把当前的买点整理成计划")
        plan_id_b = save_and_get_plan_id(page)
        binds = db_bindings()
        bind_a = next((b for b in binds if b[0] == plan_id_a), None)
        bind_b = next((b for b in binds if b[0] == plan_id_b), None)
        check("G4.3 two questions → two distinct plans, own bindings",
              plan_id_a != plan_id_b and bind_a and bind_b
              and bind_a[1] != bind_b[1] and bind_a[1] is not None and bind_b[1] is not None,
              f"A={plan_id_a[:24]}(q{bind_a[1] if bind_a else '-'}) "
              f"B={plan_id_b[:24]}(q{bind_b[1] if bind_b else '-'})")

        # ---------- G5 两入口 + 迟到响应 ----------
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
        page.locator(".agent-console .plan-draft-card").first.wait_for(
            state="visible", timeout=90000)
        console_card = page.locator(".agent-console .plan-draft-card").first
        console_card.get_by_role("button", name="保存草稿").click()
        console_card.get_by_role("button", name="补齐并核对").wait_for(
            state="visible", timeout=30000)
        check("G5.1 console entry: save + review entry reachable",
              console_card.get_by_role("button", name="补齐并核对").count() == 1)

        # 迟到响应：工作台保存瞬间暂停后端 → 切新会话 → 放行 → 无串扰
        page.goto(f"{WEB}/agent", wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        import subprocess
        backend_pid = int(subprocess.check_output(
            ["lsof", "-ti", ":8014"]).split()[0]).__int__()
        ask_and_wait_plan(page, "TH881272 帮我把当前的买点整理成计划")
        card3 = page.locator(".plan-draft-card").first
        subprocess.run(["kill", "-STOP", str(backend_pid)])
        card3.get_by_role("button", name="保存草稿").click()
        page.evaluate("""(() => {
          const btns = [...document.querySelectorAll('button')];
          btns.find(b => b.innerText === '新对话').click();
        })()""")
        subprocess.run(["kill", "-CONT", str(backend_pid)])
        page.wait_for_timeout(4000)
        welcome = page.locator(".ar-welcome").count() > 0
        stray = "草稿已保存" in page.locator("body").inner_text()
        check("G5.2 late save response does not leak into new conversation",
              welcome and not stray, f"welcome={welcome} stray={stray}")

        # ---------- G3 其余：P3 无合法候选 → 待补，不保存 ----------
        page.goto(f"{WEB}/agent", wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        ask_and_wait_plan(page, "516220 帮我把当前的买点整理成计划")
        card4 = page.locator(".plan-draft-card").first
        t4 = card4.inner_text()
        save_disabled = card4.get_by_role("button", name="保存草稿").is_disabled()
        check("G3.2 early signal gives no legal prefill → stays pending",
              "暂不能保存" in t4 and save_disabled,
              t4[:100].replace("\n", " | "))
        browser.close()

    # ---------- G6 回归（外部命令，由 run_all 外层执行） ----------
    ok = all(r["verdict"] == "PASS" for r in RESULTS)
    Path(OUT / "RESULTS.json").write_text(json.dumps(
        {"results": RESULTS, "plan_requests": PLAN_LOG}, ensure_ascii=False, indent=2))
    print(f"\nTOTAL: {sum(r['verdict']=='PASS' for r in RESULTS)}/"
          f"{len(RESULTS)} PASS")
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    try:
        code = main()
    except Exception as exc:  # 崩溃必须反映在退出码，不得静默
        check("script-crashed", False, f"{type(exc).__name__}: {exc}")
        Path(OUT / "RESULTS.json").write_text(json.dumps(
            {"results": RESULTS, "plan_requests": PLAN_LOG}, ensure_ascii=False, indent=2))
        code = 1
    sys.exit(code)
