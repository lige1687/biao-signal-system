"""Small, read-only legacy comparisons; writes only a NEW requested output directory.

No old main(), accounts or network calls. The standalone fixtures and generated
cards make the examples reviewable without changing existing consumers.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.dont_write_bytecode = True
from lei_signal.research import definitions as d  # noqa: E402 -- local standalone entry point


def legacy(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def save(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def compare(a, b, name, checks, atol=1e-10):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if a.shape != b.shape:
        raise AssertionError(f"{name}: different shapes {a.shape} {b.shape}")
    np.testing.assert_allclose(a, b, rtol=1e-10, atol=atol, equal_nan=True, err_msg=name)
    mask = np.isfinite(a) & np.isfinite(b)
    checks.append(
        dict(
            name=name,
            cells=int(a.size),
            finite_cells=int(mask.sum()),
            max_absolute_error=float(np.max(np.abs(a[mask] - b[mask]))) if mask.any() else 0.0,
        )
    )


def common_manifest(reg, refs, inputs, protocol, pool, cutoff, quality):
    # This is a replay TODAY; historical data arrival times are NOT invented.
    now = pd.Timestamp.now(tz="Asia/Shanghai").isoformat()
    result = d.make_manifest(
        registry=reg,
        references=refs,
        code_files=[Path(__file__), Path(d.__file__)],
        input_files=inputs,
        protocol=protocol,
        pool_version=pool,
        data_cutoff=cutoff,
        available_at=now,
        decision_at=now,
        quality=quality,
    )
    result["historical_available_at"] = "unknown: sources do not certify vendor arrival timestamps"
    result["execution_protocol"] = "definition replay only; no trades executed"
    return result


def mixed_example(reg, out, checks):
    def source(key):
        return ROOT / reg["sources"][key]["path"]

    old = legacy(source("mixed_code"), "_definitions_old_mixed")
    p = pd.read_csv(source("mixed_prices"), dtype={"symbol": str, "date": str})
    p.symbol = p.symbol.str[:6]
    # Bound by a fixed date chosen for formula checks, not returns.
    p = p[p.date <= "2023-12-29"].sort_values(["symbol", "date"])
    actions = [
        old.action_fields(a) for a in json.loads(source("mixed_actions").read_text())["events"]
    ]
    actions = [a for a in actions if a["effective_date"] and a["effective_date"] <= "2023-12-29"]
    p.to_csv(out / "mixed-nominal-input.csv", index=False)
    save(out / "mixed-actions-input.json", actions)
    # Legacy builds the signal input. Independent adapters verify every indicator
    # below, not the market truth of the legacy corporate action database.
    idx = old.economic_indices(p, actions)
    idx.to_csv(out / "mixed-signal-input.csv", index=False)
    rows, independent = [], []
    for symbol, g in idx.groupby("symbol"):
        g = g.sort_values("date").set_index("date")
        q = g.economic_index
        f = d.quote_features(q)
        bound = d.calculate("mixed.momentum.raw@1.0.0", q, registry=reg)
        compare(bound["values"], f.momentum, f"mixed-binding:{symbol}", checks)
        for key in ("momentum", "sma200", "rv_rank", "valid_count"):
            compare(f[key], g[key], f"mixed:{symbol}:{key}", checks)
        for stop in sorted(set([200, 252, 253, 272, 273, min(780, len(q)), len(q)])):
            if stop <= len(q):
                prefix = d.quote_features(q.iloc[:stop])
                compare(prefix, f.iloc[:stop], f"mixed-prefix:{symbol}:{stop}", checks)
        scaled = d.quote_features(q * 10)
        compare(scaled.momentum, f.momentum, f"mixed-scale:{symbol}", checks)
        independent.append(
            pd.DataFrame(
                dict(
                    date=f.index,
                    symbol=symbol,
                    momentum=f.momentum.values,
                    rv_rank=f.rv_rank.values,
                    valid_count=f.valid_count.values,
                )
            )
        )
        for day in g.index[-3:]:
            row = {"date": day, "symbol": symbol, **f.loc[day].to_dict()}
            rows.append(row)
    data = pd.concat(independent)
    decisions = old.decisions(idx)
    matched = 0
    for dec in decisions:
        if dec["config"] != "momentum_top3":
            continue
        g = data[data.date == dec["decision_date"]].set_index("symbol")
        selected = d.select_mixed(
            g.momentum.to_dict(),
            g.rv_rank.to_dict(),
            g.valid_count.to_dict(),
            current_quotes=set(g.index),
        )
        expected = dec["selected"].split("|") if dec["selected"] else []
        if selected != expected:
            raise AssertionError(f"monthly selection differs at {dec['decision_date']}")
        matched += 1
    checks.append({"name": "mixed-monthly-selected-list", "dates": matched, "exact": True})
    pd.DataFrame(rows).to_csv(out / "mixed-output.csv", index=False)
    manifest = common_manifest(
        reg,
        ["mixed.momentum.raw@1.0.0", "mixed.top3@1.0.0", "trend.sma200@1.0.0"],
        [source("mixed_prices"), source("mixed_actions"), out / "mixed-signal-input.csv"],
        source("mixed_protocol"),
        "rotation-reconstructed-full-v1/full14",
        "2023-12-29T15:00:00+08:00",
        "real_frozen_input_formula_comparison; corporate_action_availability_unverified",
    )
    manifest["output_schema"] = {
        "date": "observation date",
        "momentum": "fraction",
        "sma200": "economic_index",
        "rv_rank": "fraction",
        "missing_reason": "empty numeric cells = insufficient valid observations",
    }
    manifest["legacy_code"] = d.fingerprint(source("mixed_code"))
    save(out / "mixed-manifest.json", manifest)


def breadth_example(reg, out, checks):
    def source(key):
        return ROOT / reg["sources"][key]["path"]

    old = legacy(source("breadth_code"), "_definitions_old_breadth")
    prepared = source("breadth_quality").parent
    fingerprints = json.loads(source("breadth_inputs").read_text())
    # Locate only the explicit source referenced by the frozen local manifest.
    cache_name = next(k for k in fingerprints if k.endswith("/a_share_klines_full.parquet"))
    cache = Path(cache_name)
    real = cache.is_file() and d.fingerprint(cache)["sha256"] == fingerprints[cache_name]["sha256"]
    frozen = pd.read_parquet(prepared / "breadth_csi300.parquet")
    if (
        d.fingerprint(prepared / "breadth_csi300.parquet")["sha256"]
        != fingerprints["prepared/breadth_csi300.parquet"]["sha256"]
    ):
        raise ValueError("changed frozen breadth comparison output")
    members = pd.read_parquet(source("csi_members"))
    if real:
        # Include a regular day and a member-change boundary; endpoints fixed.
        target_dates = frozen.loc["2025-06-13":"2025-06-18"].index
        panel = pd.read_parquet(cache)
        member_rows = members[pd.to_datetime(members.date).isin(target_dates)].copy()
        membership = {pd.Timestamp(day): list(g.symbol) for day, g in member_rows.groupby("date")}
        names = sorted(set(member_rows.symbol))
        columns = {}
        for s in names:
            if s not in panel:
                continue
            q = panel[s]
            before = q[q.index < target_dates[0]].dropna().tail(200)
            columns[s] = pd.concat([before, q.reindex(target_dates)])
        sample = pd.DataFrame(columns).sort_index()
        quality = (
            "real_frozen_csi300_B; 20-session membership probes, historical availability unknown"
        )
    else:
        target_dates = pd.bdate_range("2020-01-01", periods=205)
        sample = pd.DataFrame(
            {"a": np.arange(1.0, 206), "b": np.arange(206.0, 1.0, -1)}, index=target_dates
        )
        membership = {day: ["a", "b"] for day in target_dates}
        member_rows = pd.DataFrame(
            [dict(date=day, symbol=s) for day, ss in membership.items() for s in ss]
        )
        quality = "synthetic_only: frozen cache missing or hash mismatch"
    sample.to_csv(out / "breadth-input.csv", index_label="date")
    member_rows.to_csv(out / "breadth-members.csv", index=False)
    bound = d.calculate(
        "breadth.csi300.b50.common@1.0.0", sample, registry=reg, membership=membership
    )
    actual = bound["values"]
    expected = old.breadth_from_close_panel(sample, membership)
    for col in ("b50", "b200"):
        compare(actual[col] * 100, expected[col], f"breadth-legacy:{col}", checks)
    for col in ("eligible", "pool_total", "quoted", "coverage"):
        compare(actual[col], expected[col], f"breadth-legacy:{col}", checks)
    if real:
        for col in ("b50", "b200"):
            compare(
                actual.loc[target_dates, col] * 100,
                frozen.loc[target_dates, col],
                f"breadth-frozen:{col}",
                checks,
            )
    # Keep exact day positions; adding future rows cannot change the earlier result.
    cut = len(sample) - 1
    prefix = d.breadth(sample.iloc[:cut], membership)
    compare(prefix[["b50", "b200"]], actual.iloc[:cut][["b50", "b200"]], "breadth-prefix", checks)
    scaled = d.breadth(sample * 10, membership)
    compare(scaled[["b50", "b200"]], actual[["b50", "b200"]], "breadth-scale", checks)
    actual.loc[target_dates].to_csv(out / "breadth-output.csv", index_label="date")
    actual_delta = d.breadth_delta(frozen.b50 / 100)
    compare(actual_delta * 100, frozen.b50 - frozen.b50.shift(20), "breadth-delta20", checks)
    manifest = common_manifest(
        reg,
        ["breadth.csi300.b50.common@1.0.0", "breadth.csi300.b200.common@1.0.0"],
        [
            out / "breadth-input.csv",
            out / "breadth-members.csv",
            source("csi_members"),
            prepared / "breadth_csi300.parquet",
        ],
        source("breadth_protocol"),
        "csi300/frozen20-session-probe-v1",
        str(target_dates[-1].date()) + "T15:00:00+08:00",
        quality,
    )
    manifest["output_schema"] = {
        "b50": "fraction",
        "b200": "fraction",
        "coverage": "fraction",
        "eligible": "stock_count",
        "missing_reason": "membership_missing/no_eligible_quotes/coverage_below_minimum/null",
    }
    manifest["legacy_code"] = d.fingerprint(source("breadth_code"))
    manifest["source_cache"] = (
        d.fingerprint(cache) if real else {"status": "unavailable_or_revised"}
    )
    if real and d.fingerprint(cache)["sha256"] != fingerprints[cache_name]["sha256"]:
        raise ValueError("cache changed during verification")
    if (
        d.fingerprint(prepared / "breadth_csi300.parquet")["sha256"]
        != fingerprints["prepared/breadth_csi300.parquet"]["sha256"]
    ):
        raise ValueError("frozen breadth changed during verification")
    save(out / "breadth-manifest.json", manifest)
    return real


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="must not already exist")
    args = parser.parse_args()
    if args.output.exists():
        parser.error(
            "output already exists: choose a new run directory; never overwrite old evidence"
        )
    reg = d.load_registry()
    cards = d.validate_registry(reg)
    # Input identities are checked before imports or calculations.
    d.verify_sources(reg)
    args.output.mkdir(parents=True)
    save(args.output / "resolved-definition-cards.json", list(cards.values()))
    checks = []
    mixed_example(reg, args.output, checks)
    real = breadth_example(reg, args.output, checks)
    d.verify_sources(reg)
    report = dict(
        status="passed",
        definitions=len(cards),
        sources_checked=len(reg["sources"]),
        comparisons=checks,
        breadth_real_input=real,
        old_sources_unchanged=True,
        scope="formula/selection consistency only; no account simulation or alpha regression",
    )
    save(args.output / "verification.json", report)
    save(
        args.output / "artifact-manifest.json",
        {
            "files": [d.fingerprint(p) for p in sorted(args.output.iterdir()) if p.is_file()],
            "registry": d.fingerprint(d.REGISTRY),
            "codes": [d.fingerprint(Path(__file__)), d.fingerprint(Path(d.__file__))],
        },
    )
    print(json.dumps({k: v for k, v in report.items() if k != "comparisons"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
