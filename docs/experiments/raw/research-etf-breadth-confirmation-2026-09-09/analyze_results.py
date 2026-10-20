"""Independent arithmetic checks and fixed diagnostics for the frozen run."""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PREP = HERE / "prepared"
RESULTS = HERE / "results"
DIAG = HERE / "diagnostics"
OLD = ROOT / "docs/experiments/raw/research-broad-etf-cash-2026-09-08/first12"
START, END, INITIAL = pd.Timestamp("2018-07-05"), pd.Timestamp("2026-06-30"), 1_000_000.0


def save_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def weekly_targets(width, dates):
    x = width.reindex(dates)
    iso = x.index.isocalendar()
    out = []
    for _, g in x.groupby([iso.year, iso.week]):
        next_monday = g.index.max() + pd.Timedelta(days=7 - g.index.max().weekday())
        if next_monday > END:
            continue
        valid = g[g.valid.fillna(False)]
        if valid.empty:
            out.append({"signal_date": g.index.max(), "target": np.nan, "valid": False})
        else:
            row = valid.iloc[-1]
            target = 1.0 if row.b200 < 43.3 else (0.5 if row.b200 < 56.7 else 0.0)
            out.append({"signal_date": g.index.max(), "width_date": valid.index[-1], "target": target, "valid": True, "b200": row.b200})
    return pd.DataFrame(out).set_index("signal_date")


def independent_verify():
    stored = pd.read_csv(RESULTS / "summary.csv").set_index("account_id")
    checks = []
    for account_id, row in stored.iterrows():
        fee_dir = RESULTS / ("fee-10bp" if row.fee_rate == 0.001 else "fee-20bp")
        d = pd.read_parquet(fee_dir / f"{account_id}-daily.parquet")
        try:
            t = pd.read_csv(fee_dir / f"{account_id}-trades.csv")
        except pd.errors.EmptyDataError:
            t = pd.DataFrame(columns=["notional", "fee"])
        eq = float(d.equity.iloc[-1])
        high = np.maximum.accumulate(np.r_[INITIAL, d.equity.to_numpy(float)])
        series = np.r_[INITIAL, d.equity.to_numpy(float)]
        max_dd = float(np.min(series / high - 1))
        years = (END - START).days / 365.25
        calc = {
            "end_equity": eq,
            "cagr": (eq / INITIAL) ** (1 / years) - 1,
            "max_drawdown": max_dd,
            "average_weight": float(d.loc[d.is_quote_day, "weight"].mean()),
            "turnover_initial_multiple": float(t.notional.sum() / INITIAL),
            "fees": float(t.fee.sum()),
            "trades": len(t),
        }
        diffs = {k: abs(calc[k] - float(row[k])) for k in calc}
        checks.append({"account_id": account_id, "calculated": calc, "absolute_differences": diffs, "passed": all(v < (1e-6 if k != "end_equity" else 0.005) for k, v in diffs.items())})
    save_json(DIAG / "independent_arithmetic_check.json", {"accounts": len(checks), "passed": all(x["passed"] for x in checks), "checks": checks})


def source_disagreements():
    a = pd.read_parquet(PREP / "breadth_all_a.parquet")
    c = pd.read_parquet(PREP / "breadth_csi300.parquet")
    common = pd.concat({"all_a": a, "csi300": c}, axis=1).loc[START:END]
    mask = common[("all_a", "valid")].fillna(False) & common[("csi300", "valid")].fillna(False)
    x = common[mask].copy()
    for n in ["b50", "b200"]:
        x[("all_a", f"d20_{n}")] = x[("all_a", n)] - x[("all_a", n)].shift(20)
        x[("csi300", f"d20_{n}")] = x[("csi300", n)] - x[("csi300", n)].shift(20)
    rows = []
    for n in ["b50", "b200"]:
        da, dc = x[("all_a", f"d20_{n}")], x[("csi300", f"d20_{n}")]
        valid = da.notna() & dc.notna()
        disagree = valid & ((da > 0) != (dc > 0))
        rows.append({"measure": n, "common_days": int(valid.sum()), "direction_disagreement_days": int(disagree.sum()), "direction_disagreement_rate": float(disagree.sum()/valid.sum())})
    dates = pd.read_csv(OLD / "inputs/bars/sh510300-nominal.csv", parse_dates=["date"]).query("date >= @START and date <= @END").date
    wa, wc = weekly_targets(a, pd.DatetimeIndex(dates)), weekly_targets(c, pd.DatetimeIndex(dates))
    joined = wa[["target", "valid"]].join(wc[["target", "valid"]], lsuffix="_all_a", rsuffix="_csi300")
    both = joined.valid_all_a & joined.valid_csi300
    diff = joined[both & (joined.target_all_a != joined.target_csi300)].copy()
    diff.reset_index().to_csv(DIAG / "weekly_source_target_disagreements.csv", index=False)
    thresholds = []
    for name, w in [("all_a", wa), ("csi300", wc)]:
        v = w[w.valid]
        thresholds.append({"source": name, "valid_weeks": len(v), "target_100_weeks": int((v.target==1).sum()), "target_50_weeks": int((v.target==.5).sum()), "target_0_weeks": int((v.target==0).sum()), "target_changes": int(v.target.ne(v.target.shift()).sum())})
    pd.DataFrame(rows).to_csv(DIAG / "daily_direction_disagreement_summary.csv", index=False)
    pd.DataFrame(thresholds).to_csv(DIAG / "weekly_threshold_frequency.csv", index=False)


def confirmation_opportunities():
    actions = json.loads((OLD / "inputs/actions.json").read_text())
    from run_backtest import continuous_close, load_bars
    rows = []
    for symbol, source in [("510300", "all_a"), ("510300", "csi300"), ("159915", "all_a")]:
        bars = load_bars(symbol)
        run_dates = bars.loc[START:END].index
        width = pd.read_parquet(PREP / f"breadth_{source}.parquet")
        weekly = weekly_targets(width, run_dates)
        internal = ("sh" if symbol.startswith("5") else "sz") + symbol
        cont = continuous_close(bars, actions, internal)
        confirms = {
            "W1": (width.b50 - width.b50.shift(20)) > 0,
            "W2": (width.b200 - width.b200.shift(20)) > 0,
            "W3": cont > cont.rolling(50, min_periods=50).mean(),
        }
        valid_weekly = weekly[weekly.valid]
        prev_target = 0.0
        for i, (start, event) in enumerate(valid_weekly.iterrows()):
            if event.target <= prev_target:
                prev_target = event.target
                continue
            later = valid_weekly.iloc[i+1:]
            stop_candidates = later.index[later.target < event.target]
            stop = stop_candidates.min() if len(stop_candidates) else END
            first_opens = run_dates[run_dates > start]
            if not len(first_opens):
                continue
            first_open = first_opens.min()
            for version, conf in confirms.items():
                possible = conf.loc[(conf.index >= start) & (conf.index < stop)]
                passed = possible[possible.fillna(False)]
                if len(passed):
                    pass_day = passed.index.min()
                    opens = run_dates[run_dates > pass_day]
                    resolution = opens.min() if len(opens) else END
                    status = "immediate" if pass_day == start else "delayed"
                else:
                    pass_day = pd.NaT
                    resolution = stop
                    status = "not_bought_before_reason_changed"
                price0 = float(bars.loc[first_open, "open"])
                span = bars.loc[(bars.index >= first_open) & (bars.index <= resolution), "close"]
                rows.append({
                    "symbol": symbol, "source": source, "raw_signal_date": start,
                    "raw_target": event.target, "version": version, "status": status,
                    "confirmation_date": pass_day, "resolution_date": resolution,
                    "wait_trading_days": max(0, int((run_dates[(run_dates >= first_open) & (run_dates <= resolution)]).size - 1)),
                    "worst_price_change_during_wait": float(span.min()/price0-1),
                    "best_price_change_during_wait": float(span.max()/price0-1),
                    "end_price_change_during_wait": float(span.iloc[-1]/price0-1),
                })
            prev_target = event.target
    df = pd.DataFrame(rows)
    df.to_csv(DIAG / "common_raw_buy_opportunities.csv", index=False)
    summary = df.groupby(["symbol","source","version","status"]).size().rename("opportunities").reset_index()
    summary.to_csv(DIAG / "common_raw_buy_opportunity_summary.csv", index=False)


def membership_jump_decomposition():
    membership = pd.read_parquet(PREP / "csi300_membership_daily.parquet")
    panel = pd.read_parquet(Path.home()/".lei_signal_lab/cache/a_share_klines_full.parquet")
    panel.columns = [str(c).zfill(6) for c in panel.columns]
    panel = panel.sort_index()
    audit = json.loads((PREP / "csi300_membership_probe_audit.json").read_text())
    breadth = pd.read_parquet(PREP / "breadth_csi300.parquet")
    rows = []
    for raw in audit["detected_effective_dates"]:
        day = pd.Timestamp(raw)
        prev_days = membership.loc[membership.date < day, "date"]
        if prev_days.empty or day not in panel.index:
            continue
        prev_day = prev_days.max()
        old = set(membership.loc[membership.date == prev_day, "symbol"])
        new = set(membership.loc[membership.date == day, "symbol"])
        def calc(members, n):
            flags=[]
            for code in members:
                if code not in panel.columns or pd.isna(panel.at[day,code]): continue
                hist=panel.loc[:day,code].dropna().tail(n)
                if len(hist) < 200 if n == 200 else len(panel.loc[:day,code].dropna().tail(200)) < 200: continue
                flags.append(float(panel.at[day,code]) > float(hist.mean()))
            return (100*sum(flags)/len(flags),len(flags)) if flags else (np.nan,0)
        old50,nold=calc(old,50); old200,_=calc(old,200)
        actual=breadth.loc[day] if day in breadth.index else None
        if actual is None: continue
        rows.append({"effective_date":day,"previous_date":prev_day,"added":len(new-old),"removed":len(old-new),"eligible_old_pool":nold,"b50_actual_new_members":actual.b50,"b50_old_members_same_prices":old50,"b50_membership_effect":actual.b50-old50,"b200_actual_new_members":actual.b200,"b200_old_members_same_prices":old200,"b200_membership_effect":actual.b200-old200})
    pd.DataFrame(rows).to_csv(DIAG / "csi300_membership_jump_decomposition.csv", index=False)


def final_manifest():
    files=[]
    for p in sorted(HERE.rglob("*")):
        if p.is_file() and p.name != "artifact_manifest.json" and "__pycache__" not in p.parts:
            files.append({"path":str(p.relative_to(HERE)),"sha256":sha256(p),"bytes":p.stat().st_size})
    report = ROOT / "docs/experiments/etf-breadth-source-and-confirmation-backtest-2026-09-09.md"
    files.append({"path":str(report.relative_to(ROOT)),"sha256":sha256(report),"bytes":report.stat().st_size})
    save_json(HERE/"artifact_manifest.json",{"files":files,"count":len(files)})


def main():
    DIAG.mkdir(exist_ok=True)
    independent_verify()
    source_disagreements()
    confirmation_opportunities()
    membership_jump_decomposition()
    final_manifest()
    print(json.dumps({"independent":json.loads((DIAG/"independent_arithmetic_check.json").read_text())["passed"],"files":len(list(DIAG.iterdir()))},ensure_ascii=False))


if __name__ == "__main__":
    main()
