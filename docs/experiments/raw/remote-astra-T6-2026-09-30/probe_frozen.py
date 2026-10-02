"""冻结引擎实际行为：把同一批人工输入交给被测程序的 /tmp 副本运行。

被测程序：
- docs/experiments/raw/research-broad-etf-technical-2026-09-08/execution/engine.py（48账户）
- docs/experiments/raw/research-broad-etf-cash-2026-09-08/first12/run_accounts.py（首12账户；只调用其 simulate）
做法：原样复制到临时目录并核对 sha256 与封存锁一致，再从副本加载；运行结束删除临时目录。
不改、不在旧 raw 目录里运行任何会写输出的入口；只写本目录 frozen-behavior.json。

用法：/tmp/bq-venv/bin/python probe_frozen.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
import traceback
from decimal import Decimal
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
TECH = REPO / "docs/experiments/raw/research-broad-etf-technical-2026-09-08/execution"
F12 = REPO / "docs/experiments/raw/research-broad-etf-cash-2026-09-08/first12"
LOCKS = {
    # execution/source-lock.json 与 first12/account-results/run-lock.json 中记录的指纹
    "engine.py": (TECH / "engine.py", "b13f9491bfe69a6f71e4ae1f393bb81c953a8a91a18131974adce782db0856a7"),
    "first12/run_accounts.py": (F12 / "run_accounts.py", "4c51b79d064171446404b391434d685932a078bb8fd4d601b487ee8f09910547"),
    "first12/inputs/dated-restrictions.json": (F12 / "inputs/dated-restrictions.json",
                                               "06d01e93347bbf7341111d29118e20aeb22d37c5d872c5cb2257dd78404225c7"),
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def structure_only(position, observations, close):
    """与 48账户运行入口相同：A/C/D 只守结构失效。"""
    return None


def tech_inputs(case: dict):
    sym = case["symbol"]
    prices = {sym: {}}
    for d, (o, c) in case["bars"].items():
        o, c = float(o), float(c)
        prices[sym][d] = dict(open=o, high=max(o, c), low=min(o, c), close=c, volume=1.0)
    actions = []
    for a in case.get("engine_actions", case.get("actions", [])):
        if a["type"] == "split":
            actions.append(dict(event_id=a["id"], symbol=sym, type="split", announcement_date=a["announcement"],
                                ex_date=a["ex"], ratio=float(a["ratio"])))
        else:
            actions.append(dict(event_id=a["id"], symbol=sym, type="cash_dividend", announcement_date=a["announcement"],
                                record_date=a["record"], ex_date=a["ex"], pay_date=a["pay"],
                                cash_per_share=float(a["cash"])))
    config = "A20E" if case["kind"] == "acd" else "R0"
    cands = [dict(candidate_id=c["id"], config_id=config, symbol=sym, signal_date=c["signal_date"],
                  signal_accepted=True, signal_reject_reason=None, signal_ref=float(c["signal_ref"]),
                  target=None if c.get("target") is None else float(c["target"]), stop=float(c["stop"]),
                  upper=None, variant="early") for c in case.get("candidates", [])]
    obs = {sym: {d: dict(ema20=float(case["obs"]["ema20"]), cost20=float(case["obs"]["cost20"]))
                 for d in case["bars"]}}
    kwargs = dict(start=case["start"], end=case["end"], weekly_per_symbol=float(case["weekly"]),
                  initial_per_symbol=float(case["initial"]), fee=float(case["fee"]), config_id=config,
                  limits={sym: float(case["limit"])}, limit_changes={sym: []},
                  blocked_dates={sym: list(case.get("blocked", []))},
                  exit_rule=structure_only if case["kind"] == "acd" else None, explicit_config_set={"A20E"})
    return prices, actions, cands, obs, kwargs


def run_technical(engine, case: dict) -> dict:
    sym = case["symbol"]
    prices, actions, cands, obs, kwargs = tech_inputs(case)
    r = engine.simulate(prices, actions, cands, obs, **kwargs)
    daily = {row["date"]: dict(cash=row["cash"], units=row[f"units_{sym}"], mark=row[f"mark_{sym}"],
                               mark_date=row[f"mark_date_{sym}"], receivable=row["receivable"], equity=row["equity"],
                               funding=row["total_funding"], nav=row["nav"], deposit=row["deposit"],
                               stale=row["stale_symbols"]) for row in r["daily"]}
    orders = {}
    sells = []
    for o in r["orders"]:
        rec = dict(status=o["status"], reason=o.get("reason"), planned_date=o.get("planned_date"),
                   attempts=[[a["date"], a["reason"]] for a in o["attempts"]], fill_date=o.get("resolved_date")
                   if o["status"] == "filled" else None, stop=o.get("stop"), target=o.get("target"))
        if o["side"] == "buy":
            orders[o["candidate_id"]] = rec
        else:
            sells.append(rec)
    trades = [dict(date=t["date"], side=t["side"], shares=t["shares"], price=t["price"], notional=t["notional"],
                   fee=t["fee"], risk_budget=t.get("risk_budget")) for t in r["trades"]]
    positions = [dict(stop=p["stop"], target=p["target"], shares=p["shares"], div_accrued=p["dividend_accrued"],
                      div_paid=p["dividend_paid"], net_pnl=p["net_pnl"], closed=p["closed"], exit_date=p["exit_date"],
                      market_value=p["market_value"], level_actions=p.get("level_actions"))
                 for p in r["roundtrips"]]
    events = [e for e in r["events"] if e["kind"] not in ("deposit",)]
    return dict(status="ok", trades=trades, orders=orders, sells=sells, positions=positions, daily=daily, events=events)


def run_f12_hold(f12, case: dict) -> dict:
    sym = case["symbol"]
    bars = []
    for d, (o, c) in sorted(case["bars"].items()):
        o, c = Decimal(o), Decimal(c)
        bars.append(dict(date=d, open=o, high=max(o, c), low=min(o, c), close=c, volume=Decimal(1)))
    actions = []
    for a in case.get("engine_actions", case.get("actions", [])):
        x = dict(event_id=a["id"], symbol=sym, type=a["type"], announcement_date=a["announcement"], effective_date=a["ex"])
        if a["type"] == "split":
            x["ratio"] = a["ratio"]
        else:
            x.update(record_date=a["record"], pay_date=a["pay"], cash=a["cash"])
        actions.append(x)
    settings = dict(blocked_dates={sym: list(case.get("blocked", []))}, limits={sym: float(case["limit"])}, limit_changes={})
    r = f12.simulate("t6-" + case["id"], sym, "hold", Decimal(case["fee"]), bars, actions, settings, [],
                     case["start"], case["end"])
    daily = {row["date"]: dict(cash=row["cash"], units=row["units"], mark=row["mark"], receivable=row["receivable"],
                               equity=row["equity"], mark_age_days=row["mark_age_days"]) for row in r["daily"]}
    trades = [dict(date=t["date"], side=t["side"], shares=t["shares"], price=t["price"], notional=t["notional"],
                   fee=t["fee"]) for t in r["trades"]]
    return dict(status="ok", trades=trades, orders={}, sells=[], positions=[], daily=daily,
                rejected=r["rejected"], summary=r["summary"])


def plain(x):
    if isinstance(x, Decimal):
        return format(x.normalize(), "f")
    if isinstance(x, dict):
        return {k: plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [plain(v) for v in x]
    if isinstance(x, set):
        return sorted(x)
    return x


def main():
    spec = json.loads((HERE / "cases.json").read_text())
    defaults = spec["defaults"]
    tmp = Path(tempfile.mkdtemp(prefix="t6-frozen-"))
    try:
        hashes = {}
        for rel, (src, locked) in LOCKS.items():
            dst = tmp / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            got = sha(dst)
            hashes[rel] = dict(locked=locked, copy=got, original=sha(src), match=got == locked == sha(src))
            if not hashes[rel]["match"]:
                raise SystemExit(f"fingerprint mismatch: {rel}")
        engine = load("t6_frozen_technical_engine", tmp / "engine.py")
        f12 = load("t6_frozen_first12_runner", tmp / "first12/run_accounts.py")
        assert Path(f12.__file__).resolve().is_relative_to(tmp.resolve())
        out = []
        for raw in spec["cases"]:
            case = dict(defaults)
            case.update(raw)
            try:
                if case["engine"] == "technical":
                    res = run_technical(engine, case)
                else:
                    res = run_f12_hold(f12, case)
            except Exception as exc:  # 引擎主动拒绝也是“实际行为”
                res = dict(status="raised", error=f"{type(exc).__name__}: {exc}",
                           trace=traceback.format_exc().splitlines()[-3:])
            out.append(dict(id=case["id"], boundary=case["boundary"], engine=case["engine"],
                            used_engine_actions_override="engine_actions" in raw, result=plain(res)))
        payload = dict(_note="冻结引擎在 /tmp 副本中对 cases.json 人工输入的实际输出；未改动任何旧文件。",
                       fingerprints=hashes, cases=out)
        (HERE / "frozen-behavior.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
        print("cases", len(out), "statuses", {c["id"]: c["result"]["status"] for c in out})
    finally:
        for name in ("t6_frozen_technical_engine", "t6_frozen_first12_runner"):
            sys.modules.pop(name, None)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
