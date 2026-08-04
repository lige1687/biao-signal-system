"""LEI 监督员 skill 的 HTTP 客户端（调 /api/plans*）。

用 stdlib urllib，无额外依赖。失败时回退直连 store 模块（不写两套逻辑）。
用法见各子命令。后端默认 127.0.0.1:8000，可用 LEI_API_BASE 覆盖。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))

API_BASE = os.environ.get("LEI_API_BASE", "http://127.0.0.1:8000")


def _req(method: str, path: str, body: dict | None = None) -> object:
    url = f"{API_BASE}/api{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode())
        except Exception:  # noqa: BLE001
            detail = {"error": str(exc)}
        print(json.dumps(detail, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(1) from exc
    except urllib.error.URLError as exc:
        # 回退：直连 store 模块（不写两套逻辑）
        return _fallback_direct(method, path, body, exc)


def _fallback_direct(method: str, path: str, body: dict | None, exc: Exception) -> object:
    """API 不可用时直连 store（只支持只读与简单写，保证 skill 不断链）。"""
    from lei_signal.api.config import sqlite_path  # noqa: PLC0415
    from lei_signal.storage.sqlite_store import connect  # noqa: PLC0415
    from lei_signal.plans import store  # noqa: PLC0415
    print(f"[fallback] API 不可用（{exc}），直连 store", file=sys.stderr)
    conn = connect(sqlite_path())
    try:
        if path == "/plans" and method == "GET":
            return [
                {"plan_id": p.plan_id, "symbol": p.symbol, "module": p.module,
                 "direction": p.direction, "state": p.state, "valid_until": p.valid_until}
                for p in store.list_plans(conn)
            ]
        if path.startswith("/plans/") and path.endswith("/alerts") and method == "GET":
            plan_id = path[len("/plans/"):-len("/alerts")]
            plan = store.get_plan(conn, plan_id)
            if plan is None:
                raise SystemExit("计划不存在")
            print(f"[fallback] 计划 {plan_id}（{plan.symbol}），alerts 需后端取数，API 不可用时无法计算",
                  file=sys.stderr)
            return []
        raise SystemExit(f"[fallback] 不支持该操作: {method} {path}")
    finally:
        conn.close()


def cmd_create(args: argparse.Namespace) -> None:
    body = {
        "symbol": args.symbol, "module": args.module, "direction": args.direction,
        "ruleset_version": args.ruleset, "reason": args.reason, "valid_until": args.valid_until,
        "entry_rule_id": args.entry_rule, "entry_lifecycle_id": args.lifecycle,
        "invalidation_price": args.invalidation, "thesis_cn": args.thesis,
        "invalidation_criteria_cn": args.invalidation_criteria,
        "drawdown_playbook_cn": args.drawdown, "take_profit_plan_cn": args.take_profit,
        "stop_plan_cn": args.stop_plan,
    }
    print(json.dumps(_req("POST", "/plans", body), ensure_ascii=False, indent=2))


def cmd_confirm(args: argparse.Namespace) -> None:
    print(json.dumps(_req("POST", f"/plans/{args.plan_id}/confirm"), ensure_ascii=False, indent=2))


def cmd_list(args: argparse.Namespace) -> None:
    qs = []
    if args.symbol:
        qs.append(f"symbol={args.symbol}")
    if args.state:
        qs.append(f"state={args.state}")
    path = "/plans" + (f"?{'&'.join(qs)}" if qs else "")
    print(json.dumps(_req("GET", path), ensure_ascii=False, indent=2))


def cmd_alerts(args: argparse.Namespace) -> None:
    print(json.dumps(_req("GET", f"/plans/{args.plan_id}/alerts"), ensure_ascii=False, indent=2))


def cmd_actions(args: argparse.Namespace) -> None:
    print(json.dumps(_req("GET", f"/plans/{args.plan_id}/actions"), ensure_ascii=False, indent=2))


def cmd_revise(args: argparse.Namespace) -> None:
    body = {"changed_field": args.field, "new_value": args.value, "changed_by": "user"}
    print(json.dumps(_req("POST", f"/plans/{args.plan_id}/revise", body), ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="LEI 监督员 plan CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create"); c.add_argument("--symbol", required=True); c.add_argument("--module", required=True)
    c.add_argument("--direction", required=True); c.add_argument("--ruleset", required=True)
    c.add_argument("--reason", default=""); c.add_argument("--valid-until", default="")
    c.add_argument("--entry-rule", default=None); c.add_argument("--lifecycle", default=None)
    c.add_argument("--invalidation", type=float, default=None); c.add_argument("--thesis", default="")
    c.add_argument("--invalidation-criteria", default=""); c.add_argument("--drawdown", default="")
    c.add_argument("--take-profit", default=""); c.add_argument("--stop-plan", default="")
    c.set_defaults(func=cmd_create)
    f = sub.add_parser("confirm"); f.add_argument("plan_id"); f.set_defaults(func=cmd_confirm)
    l = sub.add_parser("list"); l.add_argument("--symbol"); l.add_argument("--state"); l.set_defaults(func=cmd_list)
    a = sub.add_parser("alerts"); a.add_argument("plan_id"); a.set_defaults(func=cmd_alerts)
    ac = sub.add_parser("actions"); ac.add_argument("plan_id"); ac.set_defaults(func=cmd_actions)
    r = sub.add_parser("revise"); r.add_argument("plan_id"); r.add_argument("field"); r.add_argument("value")
    r.set_defaults(func=cmd_revise)
    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
