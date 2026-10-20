"""飞书自定义机器人 Webhook 的签名动作回执。

自定义机器人只支持打开链接。本模块提供轻量回执页和 POST 接口，验签后复用既有
计划状态机。动作链接可证明由 LEI 签发，但不能证明点击者的飞书身份。
"""
from __future__ import annotations

import html
import json
import os
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from string import Template
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from lei_signal.api.config import sqlite_path as default_db
from lei_signal.notify.base import NotificationPayload
from lei_signal.notify.feishu_webhook import FeishuWebhookNotifier
from lei_signal.notify.signing import SignedAction, sign_action, verify_action
from lei_signal.plans.actions import handle_supersede, validate_resume_on
from lei_signal.plans.context import context_from_result
from lei_signal.plans.store import (
    add_annotation,
    get_action_item,
    get_plan,
    set_entered,
    set_exited,
    update_action_item,
)
from lei_signal.storage.sqlite_store import connect

router = APIRouter(prefix="/api/feishu-webhook", tags=["feishu-webhook"])

_PAGE = Template("""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="referrer" content="no-referrer">
<meta http-equiv="Content-Security-Policy"
      content="default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'">
<title>LEI 待办确认</title>
<style>
:root {
  color-scheme: light;
  --ink: #20231f;
  --muted: #666c63;
  --line: #d7dbd3;
  --paper: #fbfcf9;
  --accent: #244f3b;
  --accent-soft: #e5eee8;
  --danger: #9a3b36;
}
* { box-sizing: border-box; }
body {
  min-height: 100vh;
  margin: 0;
  padding: max(20px, env(safe-area-inset-top)) 18px max(28px, env(safe-area-inset-bottom));
  color: var(--ink);
  background: #eef0eb;
  font: 16px/1.55 -apple-system, BlinkMacSystemFont, "PingFang SC", "Noto Sans CJK SC", sans-serif;
}
main {
  width: min(100%, 560px);
  margin: 0 auto;
  padding: clamp(22px, 6vw, 34px);
  background: var(--paper);
  border: 1px solid var(--line);
  border-top: 5px solid var(--accent);
}
.eyebrow {
  margin: 0 0 6px;
  color: var(--accent);
  font-size: 12px;
  font-weight: 750;
  letter-spacing: .13em;
}
h1 { margin: 0; font-size: clamp(24px, 7vw, 34px); line-height: 1.15; }
.meta {
  margin: 24px 0;
  padding: 14px 0;
  border-block: 1px solid var(--line);
  color: var(--muted);
  overflow-wrap: anywhere;
}
.status {
  margin: 18px 0;
  padding: 12px 14px;
  color: var(--accent);
  background: var(--accent-soft);
  border-inline-start: 3px solid var(--accent);
}
fieldset { margin: 0; padding: 0; border: 0; }
label { display: block; margin-top: 18px; font-weight: 700; }
textarea, select {
  width: 100%;
  min-height: 48px;
  margin-top: 7px;
  padding: 11px 12px;
  color: var(--ink);
  background: #fdfefc;
  border: 1px solid #aeb4ab;
  border-radius: 4px;
  font: inherit;
}
textarea { resize: vertical; }
.help { margin: 7px 0 0; color: var(--muted); font-size: 13px; }
.actions { display: grid; grid-template-columns: 1fr auto; gap: 10px; margin-top: 24px; }
button {
  min-height: 48px;
  padding: 11px 18px;
  border: 1px solid var(--accent);
  border-radius: 4px;
  font: inherit;
  font-weight: 750;
  cursor: pointer;
}
.primary { color: #f8faf7; background: var(--accent); }
.secondary { color: var(--accent); background: transparent; }
.notice { margin-top: 24px; color: var(--muted); font-size: 13px; }
@media (max-width: 380px) {
  .actions { grid-template-columns: 1fr; }
  .secondary { order: 2; }
}
</style>
</head>
<body>
<main>
<p class="eyebrow">LEI · PLAN SUPERVISOR</p>
<h1>待办确认</h1>
<p class="meta"><strong>计划</strong> $plan<br><strong>待办</strong> $action</p>
$status
$form
<p class="notice">此页面只记录计划执行状态，不连接券商，也不会自动提交交易。</p>
</main>
</body>
</html>""")

_FORM = Template("""<form method="post" action="/api/feishu-webhook/action/submit">
<input type="hidden" name="plan_id" value="$plan">
<input type="hidden" name="action_id" value="$action">
<input type="hidden" name="expires_at" value="$expires">
<input type="hidden" name="nonce" value="$nonce">
<input type="hidden" name="signature" value="$signature">
<fieldset>
<label for="operation">处理方式</label>
<select id="operation" name="operation" required>
<option value="done">已执行</option>
<option value="defer">推迟</option>
</select>
<label for="reason_cn">推迟原因</label>
<textarea id="reason_cn" name="reason_cn" rows="3" maxlength="500"
          placeholder="选择推迟时必填，例如：条件尚未满足"></textarea>
<label for="resume_on_json">恢复条件 JSON</label>
<textarea id="resume_on_json" name="resume_on_json" rows="4" maxlength="1000"
          placeholder='{"field":"close","op":">=","ref":"ema20"}'></textarea>
<p class="help">选择推迟时，原因和系统可计算的恢复条件都必须填写。</p>
</fieldset>
<div class="actions">
<button class="primary" type="submit">提交回执</button>
</div>
</form>""")


def _db_path(request: Request) -> str:
    return getattr(request.app.state, "plans_db_path", None) or default_db()


def _secret() -> str:
    return os.environ.get("FEISHU_ACTION_SECRET", "")


def _verify_values(
    *, plan_id: str, action_id: str, expires_at: str, nonce: str, signature: str
) -> SignedAction:
    if not _secret():
        raise HTTPException(status_code=503, detail="飞书回执未启用")
    try:
        return verify_action(
            _secret(),
            plan_id=plan_id,
            action_id=action_id,
            expires_at=int(expires_at),
            nonce=nonce,
            signature=signature,
        )
    except (TypeError, ValueError) as exc:
        detail = str(exc)
        status = 410 if "过期" in detail else 401
        raise HTTPException(status_code=status, detail=detail) from exc


def _verify_query(request: Request) -> SignedAction:
    try:
        return _verify_values(
            plan_id=request.query_params["plan_id"],
            action_id=request.query_params["action_id"],
            expires_at=request.query_params["expires_at"],
            nonce=request.query_params["nonce"],
            signature=request.query_params["signature"],
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail="动作链接参数不完整") from exc


def _register_nonce(conn: sqlite3.Connection, signed: SignedAction) -> None:
    now = datetime.now(UTC).isoformat()
    row = conn.execute(
        """
        SELECT plan_id, action_id, expires_at
        FROM feishu_webhook_nonces
        WHERE nonce = ?
        """,
        (signed.nonce,),
    ).fetchone()
    if row is None:
        conn.execute(
            """
            INSERT INTO feishu_webhook_nonces
                (nonce, plan_id, action_id, expires_at, consumed_at, created_at)
            VALUES (?, ?, ?, ?, NULL, ?)
            """,
            (signed.nonce, signed.plan_id, signed.action_id, signed.expires_at, now),
        )
        conn.commit()
        return
    same_context = (
        row["plan_id"] == signed.plan_id
        and row["action_id"] == signed.action_id
        and row["expires_at"] == signed.expires_at
    )
    if not same_context:
        raise HTTPException(status_code=400, detail="动作链接上下文不一致")


def _is_consumed(conn: sqlite3.Connection, nonce: str) -> bool:
    row = conn.execute(
        "SELECT consumed_at FROM feishu_webhook_nonces WHERE nonce = ?", (nonce,)
    ).fetchone()
    return bool(row and row["consumed_at"])


def _claim_nonce(conn: sqlite3.Connection, nonce: str) -> bool:
    cursor = conn.execute(
        """
        UPDATE feishu_webhook_nonces
        SET consumed_at = ?
        WHERE nonce = ? AND consumed_at IS NULL
        """,
        (datetime.now(UTC).isoformat(), nonce),
    )
    conn.commit()
    return cursor.rowcount == 1


def _signature(signed: SignedAction) -> str:
    return sign_action(
        _secret(),
        signed.plan_id,
        signed.action_id,
        expires_at=signed.expires_at,
        nonce=signed.nonce,
    )


def _page(signed: SignedAction, *, message: str = "", show_form: bool = True) -> str:
    values = {
        "plan": html.escape(signed.plan_id, quote=True),
        "action": html.escape(signed.action_id, quote=True),
        "expires": str(signed.expires_at),
        "nonce": html.escape(signed.nonce, quote=True),
        "signature": html.escape(_signature(signed), quote=True),
    }
    status = f'<p class="status" role="status">{html.escape(message)}</p>' if message else ""
    form = _FORM.substitute(values) if show_form else ""
    return _PAGE.substitute(plan=values["plan"], action=values["action"], status=status, form=form)


async def _read_form(request: Request) -> dict[str, str]:
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/x-www-form-urlencoded":
        raise HTTPException(status_code=415, detail="仅支持网页表单提交")
    try:
        raw = (await request.body()).decode("utf-8")
        values = parse_qs(raw, keep_blank_values=True, max_num_fields=12)
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="回执表单无法解析") from exc
    return {key: entries[-1] for key, entries in values.items() if entries}


def _validate_defer(request: Request, plan_id: str, resume_raw: str) -> dict:
    try:
        predicate = json.loads(resume_raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="恢复条件必须是合法 JSON") from exc
    if not isinstance(predicate, dict):
        raise HTTPException(status_code=422, detail="恢复条件必须是 JSON 对象")
    service = getattr(request.app.state, "analysis_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="分析服务不可用，暂不能校验恢复条件")
    with closing(connect(_db_path(request))) as conn:
        plan = get_plan(conn, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="计划不存在")
    entry = service.get(plan.symbol)
    if entry.result is None:
        raise HTTPException(status_code=503, detail=entry.error or "分析结果不可用")
    try:
        validate_resume_on(predicate, context_from_result(entry.result))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return predicate


def _notify_result(*, plan_id: str, action_id: str, operation: str, detail: str = "") -> None:
    webhook_url = os.environ.get("FEISHU_WEBHOOK_URL")
    if not webhook_url:
        return
    operation_cn = "已执行" if operation == "done" else "已推迟"
    body = f"计划 `{plan_id}`\n\n待办 `{action_id}` 已记录为**{operation_cn}**。"
    if detail:
        body += f"\n\n{detail}"
    FeishuWebhookNotifier(webhook_url).send(
        NotificationPayload(
            title=f"LEI 回执 · {operation_cn}",
            body_md=body,
            tier=2,
            plan_id=plan_id,
            action_id=action_id,
        )
    )


@router.get("/action", response_class=HTMLResponse)
def action_page(request: Request) -> HTMLResponse:
    signed = _verify_query(request)
    with closing(connect(_db_path(request))) as conn:
        item = get_action_item(conn, signed.action_id)
        if item is None or item.plan_id != signed.plan_id:
            raise HTTPException(status_code=404, detail="待办不存在")
        _register_nonce(conn, signed)
        consumed = _is_consumed(conn, signed.nonce)
    message = "该链接已处理，无需重复提交。" if consumed else ""
    return HTMLResponse(_page(signed, message=message, show_form=not consumed))


@router.post("/action/submit", response_class=HTMLResponse)
async def submit_action(request: Request) -> HTMLResponse:
    form = await _read_form(request)
    try:
        signed = _verify_values(
            plan_id=form["plan_id"],
            action_id=form["action_id"],
            expires_at=form["expires_at"],
            nonce=form["nonce"],
            signature=form["signature"],
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail="回执参数不完整") from exc

    operation = form.get("operation", "")
    reason = form.get("reason_cn", "").strip()
    resume_raw = form.get("resume_on_json", "").strip()
    predicate: dict | None = None
    if operation == "defer":
        if not reason or not resume_raw:
            raise HTTPException(status_code=422, detail="推迟必须填写原因和恢复条件")
        predicate = _validate_defer(request, signed.plan_id, resume_raw)
    elif operation != "done":
        raise HTTPException(status_code=422, detail="未知操作")

    with closing(connect(_db_path(request))) as conn:
        _register_nonce(conn, signed)
        item = get_action_item(conn, signed.action_id)
        if item is None or item.plan_id != signed.plan_id:
            raise HTTPException(status_code=404, detail="待办不存在")
        if _is_consumed(conn, signed.nonce) or item.state in ("done", "expired"):
            return HTMLResponse(
                _page(signed, message="该待办已经处理，无需重复提交。", show_form=False)
            )
        if item.state != "open":
            raise HTTPException(status_code=409, detail=f"待办当前状态不可处理: {item.state}")
        if not _claim_nonce(conn, signed.nonce):
            return HTMLResponse(
                _page(signed, message="该待办已经处理，无需重复提交。", show_form=False)
            )

        if operation == "done":
            update_action_item(conn, item.action_id, state="done", close_kind="done")
            plan = get_plan(conn, signed.plan_id)
            if plan is not None and item.kind == "ENTER" and plan.state == "armed":
                entered = set_entered(
                    conn,
                    signed.plan_id,
                    entered_on=item.due_from or datetime.now(UTC).date().isoformat(),
                )
                handle_supersede(conn, entered)
            elif plan is not None and item.kind == "EXIT" and plan.state == "entered":
                set_exited(
                    conn,
                    signed.plan_id,
                    exited_on=item.due_from or datetime.now(UTC).date().isoformat(),
                )
            add_annotation(
                conn,
                signed.plan_id,
                ref_kind="action",
                ref_id=item.action_id,
                kind="webhook_done",
                reason_cn="通过飞书 Webhook 回执标记已执行",
                author="user",
            )
            result_detail = "后续监督周期将按已执行状态继续。"
        else:
            assert predicate is not None
            update_action_item(
                conn,
                item.action_id,
                state="deferred",
                resume_on=json.dumps(predicate, ensure_ascii=False),
            )
            add_annotation(
                conn,
                signed.plan_id,
                ref_kind="action",
                ref_id=item.action_id,
                kind="defer_reason",
                reason_cn=reason,
                author="user",
            )
            predicate_json = json.dumps(predicate, ensure_ascii=False)
            result_detail = f"原因：{reason}\n\n恢复条件：`{predicate_json}`"

    _notify_result(
        plan_id=signed.plan_id,
        action_id=signed.action_id,
        operation=operation,
        detail=result_detail,
    )
    return HTMLResponse(
        _page(
            signed,
            message="回执已记录，后续监督周期会按最新状态继续处理。",
            show_form=False,
        )
    )


__all__ = ["router"]
