"""Frozen four-cell MA correction for twelve accounts. No work on import.

The caller owns the correction contract, one-use marker, and external route plan.
This module refuses to run until all three are explicitly supplied and checked.
"""
from __future__ import annotations

import argparse
import ast
import csv
from decimal import Decimal
import hashlib
from importlib.metadata import version as package_version
import importlib.util
import json
import os
from pathlib import Path
import sys

START, END = "2022-01-01", "2026-06-30"
CORE_REL = "docs/experiments/raw/factor-ma-state-accounts-2026-09-24/implementation-r2-2026-09-27/account_runner.py"
OLD_REL = "docs/experiments/raw/factor-ma-state-accounts-2026-09-27"
INPUT_REL = "docs/experiments/raw/factor-ma-state-accounts-2026-09-24/inputs"
POST_REL = "docs/experiments/raw/factor-ma-account-postprocess-r2-2026-09-27"
BASE_REL = "docs/archive/handoffs-plans/factor-baseline-reset-2026-09-24/formal-accounts-release-2026-09-27.json"
CHANGES = {
    ("510300.SS", "2025-05-29", "S20"): (True, False),
    ("159915.SZ", "2023-01-09", "S60"): (True, False),
    ("159915.SZ", "2023-04-14", "S120"): (True, False),
    ("588000.SS", "2024-04-30", "S60"): (True, False),
}
POLICIES = {"510300.SS": ("S20", "D20"), "159915.SZ": ("S60", "D60", "S120"), "588000.SS": ("S60",)}
FEES = {"base": "0.001", "stress": "0.002"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text())


def assert_bool(value, expected, label):
    if type(value) is not bool or value is not expected:
        raise ValueError(f"strict state mismatch: {label}: {value!r} expected {expected!r}")


def parse_state(value: str):
    if value == "True":
        return True
    if value == "False":
        return False
    if value == "" or value is None:
        return None
    raise ValueError(f"unrecognized saved state: {value!r}")


def corrected_states(symbol, rows):
    """Require four known transitions; derive D only where its S actually changed."""
    out = [dict(row) for row in rows]
    seen = set()
    for row in out:
        for (s, day, scol), (before, after) in CHANGES.items():
            if s != symbol or row["date"] != day:
                continue
            if (s, day, scol) in seen:
                raise ValueError("duplicate correction date")
            n = scol[1:]
            prior_s = parse_state(row[scol]) if isinstance(row[scol], str) else row[scol]
            prior_e = parse_state(row[f"E{n}"]) if isinstance(row[f"E{n}"], str) else row[f"E{n}"]
            prior_d = parse_state(row[f"D{n}"]) if isinstance(row[f"D{n}"], str) else row[f"D{n}"]
            assert_bool(prior_s, before, scol)
            if type(prior_e) is not bool or type(prior_d) is not bool:
                raise ValueError("unknown E/D at correction date")
            assert_bool(prior_d, prior_s and prior_e, f"D{n}")
            row[scol] = after
            row[f"D{n}"] = after and prior_e
            seen.add((s, day, scol))
    expected = {key for key in CHANGES if key[0] == symbol}
    if seen != expected:
        raise ValueError(f"missing correction cells: {sorted(expected - seen)}")
    return out


def key(account):
    return account["symbol"], account["policy_id"], account["fee_scenario_id"]


def allowed_keys():
    return {(s, p, f) for s, policies in POLICIES.items() for p in policies for f in FEES}


def replace_accounts(old, replacements):
    keys = [key(a) for a in old]
    if len(old) != len(set(keys)) or len(old) != 132:
        raise ValueError("original account key set invalid")
    if set(replacements) != allowed_keys():
        raise ValueError("replacement key set must be exact twelve")
    result = [replacements.get(key(a), a) for a in old]
    for before, after in zip(old, result):
        if key(before) not in allowed_keys() and before != after:
            raise ValueError("untouched account changed")
    return result


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def local_import_closure(root):
    """Statically enumerate local Python source loaded by the frozen helpers."""
    src = root / "src"
    seeds = {Path(__file__).resolve(), root / CORE_REL, root / POST_REL / "postprocess.py",
             src / "lei_signal/research/output_storage.py"}
    pending = list(seeds)
    found = set()
    while pending:
        path = pending.pop().resolve()
        if path in found:
            continue
        if not path.is_file():
            raise ValueError(f"local source missing: {path}")
        found.add(path)
        for node in ast.walk(ast.parse(path.read_text())):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module] + [node.module + "." + alias.name for alias in node.names]
            for name in names:
                if not (name == "lei_signal" or name.startswith("lei_signal.")):
                    continue
                parts = name.split(".")
                for i in range(1, len(parts) + 1):
                    package = src.joinpath(*parts[:i]) / "__init__.py"
                    if package.is_file():
                        pending.append(package)
                module = src.joinpath(*parts).with_suffix(".py")
                if module.is_file():
                    pending.append(module)
    return {str(p): sha(p) for p in sorted(found)}


def verify_inputs(root):
    """Frozen old bindings and saved outputs, without relying on live definitions."""
    base = read_json(root / BASE_REL)
    old = root / OLD_REL
    evidence = read_json(root / POST_REL / "evidence-hashes-before-after.json")
    if evidence["before"] != evidence["after"] or not evidence["unchanged"]:
        raise ValueError("old postprocess evidence is not immutable")
    required = {CORE_REL: base["bindings"]["core_sha256"],
                f"{OLD_REL}/accounts.json": "a7603b8d4342ba55afc513832506d0d00a73301b997b14d1807afe42392eb2d4"}
    original_release = read_json(old / "release-manifest.json")
    if sys.version != original_release["python"] or package_version("pandas") != original_release["pandas"]:
        raise ValueError("frozen Python/pandas environment changed")
    direct = [INPUT_REL + "/manifest.json", INPUT_REL + "/calendar.json",
              f"{OLD_REL}/release-manifest.json", f"{OLD_REL}/resolved-cards.json",
              f"{OLD_REL}/accounts.json"]
    for s in POLICIES:
        direct += [f"{OLD_REL}/{s}-states-protected.csv", f"{OLD_REL}/{s}-mapped-actions.json",
                   f"{OLD_REL}/{s}-execution-reference.json"]
    for rel in direct:
        if rel in evidence["before"]:
            required[rel] = evidence["before"][rel]
        elif rel in original_release["bindings"]:
            required[rel] = original_release["bindings"][rel]
        elif rel != f"{OLD_REL}/release-manifest.json":
            raise ValueError(f"missing frozen hash {rel}")
    for rel, expected in original_release["bindings"].items():
        # The frozen run bound 659 files. Two live code/registry paths drifted
        # after freezing; their saved resolved cards stay the authority here.
        if not any(rel.endswith("/" + suffix) or rel == suffix for suffix in
                   ("docs/research/definitions.v1.json", "src/lei_signal/research/definitions.py")):
            required[rel] = expected
    manifest = read_json(root / INPUT_REL / "manifest.json")
    for sm in manifest["symbols"]:
        if sm["symbol"] in POLICIES:
            for field in ("warmup", "signal_economic_close", "nominal_execution_ohlc"):
                source = sm[field]
                required[source["path"]] = source["sha256"]
    for rel, expected in required.items():
        actual = sha(root / rel)
        if actual != expected:
            raise ValueError(f"frozen dependency drift: {rel}")
    # A changed current registry is deliberately excluded: the old resolved cards
    # and original release are pinned; the old driver.prepare must never be called.
    return required, manifest


def validate_gate(root, contract_path, release_path, plan_path):
    contract, release, plan = map(read_json, (contract_path, release_path, plan_path))
    if release.get("authorized") is not True or release.get("contract_sha256") != sha(contract_path) or release.get("route_plan_sha256") != sha(plan_path):
        raise ValueError("new correction release is absent or not bound to contract and route plan")
    if contract.get("affected_keys") != [list(k) for k in sorted(allowed_keys())]:
        raise ValueError("new contract key list differs from fixed twelve")
    if contract.get("old_accounts_sha256") != "a7603b8d4342ba55afc513832506d0d00a73301b997b14d1807afe42392eb2d4":
        raise ValueError("old accounts binding mismatch")
    if contract.get("window") != [START, END] or str(contract.get("initial_cash_cny")) != "100000" or contract.get("fees") != FEES:
        raise ValueError("window or cash changed")
    if plan.get("task_id") != contract.get("task_id") + "-account" or release.get("task_id") != contract.get("task_id"):
        raise ValueError("task identity mismatch")
    expected_corrections = [
        {"symbol": "510300.SS", "date": "2025-05-29", "fields": {"S20": False, "D20": False}},
        {"symbol": "159915.SZ", "date": "2023-01-09", "fields": {"S60": False, "D60": False}},
        {"symbol": "159915.SZ", "date": "2023-04-14", "fields": {"S120": False}},
        {"symbol": "588000.SS", "date": "2024-04-30", "fields": {"S60": False}},
    ]
    if contract.get("state_corrections") != expected_corrections:
        raise ValueError("frozen correction cells changed")
    required_release_bindings = local_import_closure(root)
    for rel in ("configs/research-output-policy.v1.json", "configs/storage-policy.v1.json",
                POST_REL + "/release-manifest.json", POST_REL + "/evidence-hashes-before-after.json",
                POST_REL + "/paired-comparisons.json", POST_REL + "/policy-retention.json",
                POST_REL + "/six-product-support.json",
                "docs/experiments/raw/factor-ma-year-dependence-2026-09-27/annual-account-summary.json",
                OLD_REL + "/release-manifest.json", OLD_REL + "/resolved-cards.json",
                OLD_REL + "/accounts.json", INPUT_REL + "/manifest.json", INPUT_REL + "/calendar.json"):
        required_release_bindings[str(root / rel)] = sha(root / rel)
    bindings = release.get("bindings")
    bound = {str((root / p).resolve()): h for p, h in bindings.items()} if isinstance(bindings, dict) else {}
    if not all(bound.get(p) == h for p, h in required_release_bindings.items()):
        raise ValueError("release lacks complete local source and storage-policy closure")
    for name, expected in bindings.items():
        p = Path(name) if Path(name).is_absolute() else root / name
        if sha(p) != expected:
            raise ValueError(f"release dependency drift: {name}")
    attempt_path = release_path.parent / "account-attempt.json"
    if release.get("attempt_sha256") != sha(attempt_path):
        raise ValueError("one-use attempt marker changed")
    attempt = read_json(attempt_path)
    if attempt.get("state") != "reserved" or attempt.get("completed_keys") != []:
        raise ValueError("one-use correction attempt is not fresh")
    # Only now may the storage module be imported; its bytes were just checked.
    from lei_signal.research.output_storage import recheck_saved_plan
    recheck_saved_plan(root, plan, plan["task_id"], plan["estimated_bytes"], plan["internal_metadata_bytes"])
    return plan


def secure_output_dir(plan):
    """Create only this fresh external result using anchored, no-follow opens."""
    mount = Path(plan["external_mount"])
    base = Path(plan["run_directory"]).parent.parent
    task = Path(plan["run_directory"]).parent.name
    run_id = plan["run_id"]
    if base != mount / "LeiSignal-新实验结果" or Path(plan["output"]) != base / task / run_id / "result":
        raise ValueError("external route position changed")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    mount_fd = os.open(mount, flags)
    try:
        base_fd = os.open(base.name, flags, dir_fd=mount_fd)
        try:
            if os.fstat(base_fd).st_dev != plan["external_device"]:
                raise ValueError("external device changed before mkdir")
            try:
                os.mkdir(task, dir_fd=base_fd)
            except FileExistsError:
                pass
            task_fd = os.open(task, flags, dir_fd=base_fd)
            try:
                if os.fstat(task_fd).st_dev != plan["external_device"]:
                    raise ValueError("task directory device changed")
                os.mkdir(run_id, dir_fd=task_fd)
                run_fd = os.open(run_id, flags, dir_fd=task_fd)
                try:
                    os.mkdir("result", dir_fd=run_fd)
                    result_fd = os.open("result", flags, dir_fd=run_fd)
                    try:
                        if os.fstat(result_fd).st_dev != plan["external_device"]:
                            raise ValueError("result device changed")
                        retained_fd = os.dup(result_fd)
                    finally:
                        os.close(result_fd)
                finally:
                    os.close(run_fd)
            finally:
                os.close(task_fd)
        finally:
            os.close(base_fd)
    finally:
        os.close(mount_fd)
    return retained_fd


def read_csv(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def read_nominal_quotes(path, pd):
    """Exact old driver quote parser, copied as a pure read-only adapter."""
    if path.suffix == ".parquet":
        frame = pd.read_parquet(path).reset_index()
        frame = frame.rename(columns={frame.columns[0]: "date"})
    else:
        frame = pd.read_csv(path, dtype={"open": str, "close": str})
    frame["date"] = pd.to_datetime(frame["date"]).dt.strftime("%Y-%m-%d")
    return [{"date": r["date"], "open": str(r["open"]), "close": str(r["close"])}
            for r in frame.to_dict("records")]


def clean(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    return value


def write_json(out_fd, name, value, device):
    if os.fstat(out_fd).st_dev != device:
        raise ValueError("external result device changed")
    payload = (json.dumps(clean(value), ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=out_fd)
    with os.fdopen(fd, "wb") as f:
        f.write(payload)
        f.flush()
        os.fsync(f.fileno())


def write_csv(out_fd, name, rows, device):
    rows = clean(rows)
    if os.fstat(out_fd).st_dev != device:
        raise ValueError("external result device changed")
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=out_fd)
    with os.fdopen(fd, "w", newline="") as f:
        writer = csv.DictWriter(f, list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in row.items()})
        f.flush()
        os.fsync(f.fileno())


def summarize(root, accounts, new_daily):
    """Use accepted R2 pure postprocess helpers; never call its writing run()."""
    post = load_module(root / POST_REL / "postprocess.py", "accepted_postprocess")
    core = post.core
    old = root / OLD_REL
    keyed = {key(a): a for a in accounts}
    daily = {}
    for a in accounts:
        k = key(a)
        rows = new_daily[k] if k in new_daily else read_csv(old / a["daily_path"])
        daily[k] = {r["date"]: r for r in rows if r["is_trading_day"] in (True, "True")}
    paired, nested = [], []
    for symbol in post.SYMBOLS:
        group = [a for a in accounts if a["symbol"] == symbol]
        product_retention = []
        for policy in post.POLICIES:
            opponents = ["B0", "B50"] + ([f"S{policy[1:]}", f"E{policy[1:]}"] if policy[0] == "D" else [])
            enriched = {}
            for other in opponents:
                pairs = core.evaluate_pair(group, policy, other, symbol=symbol)
                for row in pairs:
                    row["symbol"] = symbol
                    for fee in FEES:
                        a, b = keyed[(symbol, policy, fee)], keyed[(symbol, other, fee)]
                        annual = post.annual_details(a, b)
                        row[fee]["annual_details"] = annual
                        row[fee]["recovery"] = post.recovery_details(a, b)
                        row[fee]["failure_reasons"] = post.per_fee_reasons(row[fee], annual, fee)
                        da, db = daily[key(a)], daily[key(b)]
                        less = [d for d in sorted(set(da) & set(db)) if Decimal(str(da[d]["invested_pct"])) < Decimal(str(db[d]["invested_pct"])) - Decimal("1e-8")]
                        row[fee].update(less_exposure_dates=less, less_exposure_count=len(less), candidate_average_invested_pct=a["average_invested_pct"], comparator_average_invested_pct=b["average_invested_pct"], missed_upside=None, missed_upside_null_reason="economic_open_source_not_available")
                    paired.append(row)
                enriched[other] = pairs
            retained = core.evaluate_policy(group, policy, symbol=symbol)
            required = ["B0"] if policy[0] in "SE" else ["B0", f"S{policy[1:]}", f"E{policy[1:]}"]
            for row in retained:
                failed = []
                for other in required:
                    for fee in FEES:
                        failed += [dict(comparator=other, fee_scenario_id=fee, **reason) for reason in enriched[other][row["return_cost_tier_pp"]][fee]["failure_reasons"]]
                for dom in row["dominated_by"]:
                    a, b = keyed[(symbol, policy, dom["fee_scenario_id"])], keyed[(symbol, dom["opponent"], dom["fee_scenario_id"])]
                    failed.append(dict(code="simpler_opponent_approximately_dominates", **dom,
                                       opponent_minus_candidate_return_pp=b["net_annualized_return_pct"]-a["net_annualized_return_pct"],
                                       opponent_minus_candidate_mdd_pp=b["max_account_drawdown_pct"]-a["max_account_drawdown_pct"],
                                       opponent_minus_candidate_trades_per_year=b["trades_per_year"]-a["trades_per_year"]))
                row["failure_reasons"] = failed
                product_retention.append(row)
        nested.append(product_retention)
    retention = [r for group in nested for r in group]
    support = [post.aggregate(nested, p, t) for p in post.POLICIES for t in (0, 1, 2)]
    if (len(paired), len(retention), len(support)) != (432, 162, 27):
        raise ValueError("postprocess row counts changed")
    return paired, retention, support


def comparison_cohort(accounts, original, old_accounts_sha, release_sha):
    """Keep per-row source identity, then expose one explicit comparison view."""
    old_by_key = {key(a): a for a in original}
    source_index = []
    for a in accounts:
        k = key(a)
        source_index.append({"key": list(k), "version": "corrected" if k in allowed_keys() else "original",
                             "source_identity": a["source_identity"],
                             "old_source_identity": old_by_key[k]["source_identity"]})
    cohort = hashlib.sha256(json.dumps({"old_accounts_sha256": old_accounts_sha,
                                        "correction_release_sha256": release_sha,
                                        "source_index": source_index}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    view = [dict(a, source_identity=cohort) for a in accounts]
    if any(key(a) != key(b) for a, b in zip(accounts, view)):
        raise ValueError("comparison cohort changed key order")
    return cohort, source_index, view


def annual_summary(accounts, retention):
    """Pure annual readout matching the accepted saved-year consumer."""
    years = (2022, 2023, 2024, 2025, 2026)
    labels = {}
    for row in retention:
        labels.setdefault((row["symbol"], row["policy_id"]), []).append(row)
    output = []
    for a in accounts:
        annual = {int(x["year"]): x for x in a["annual"]}
        if set(annual) != set(years):
            raise ValueError(f"annual periods missing: {key(a)}")
        profits = {year: Decimal(annual[year]["profit_cny"]) for year in years}
        net = Decimal(a["ending_assets_100k_cny"]) - Decimal(a["initial_cash_cny"])
        if abs(sum(profits.values(), Decimal(0)) - net) > Decimal("0.01"):
            raise ValueError(f"annual profit does not reconcile: {key(a)}")
        for y in years[:-1]:
            if abs(Decimal(annual[y]["end_wealth"]) - Decimal(annual[y + 1]["start_wealth"])) > Decimal("0.01"):
                raise ValueError(f"annual boundary does not reconcile: {key(a)} {y}")
        if abs(Decimal(annual[2026]["end_wealth"]) - Decimal(a["ending_assets_100k_cny"])) > Decimal("0.01"):
            raise ValueError(f"annual terminal does not reconcile: {key(a)}")
        tiers = sorted(x["return_cost_tier_pp"] for x in labels.get((a["symbol"], a["policy_id"]), []) if x["retained"])
        greatest = max(years, key=lambda y: profits[y])
        least = min(years, key=lambda y: profits[y])
        yname = lambda y: str(y) if y < 2026 else "2026H1"
        output.append({"symbol": a["symbol"], "policy_id": a["policy_id"], "fee_scenario_id": a["fee_scenario_id"],
                       "retained_tiers_pp": tiers,
                       "year_profit_cny": {yname(y): str(profits[y]) for y in years},
                       "year_return_pct": {yname(y): annual[y]["return_pct"] for y in years},
                       "year_mdd_pct": {yname(y): annual[y]["max_account_drawdown_pct"] for y in years},
                       "profit_2022_2025_cny": str(sum((profits[y] for y in years[:-1]), Decimal(0))),
                       "profit_2026H1_cny": str(profits[2026]), "total_net_profit_cny": str(net),
                       "h1_profit_contribution_pct": float(profits[2026] / net * 100) if net > 0 else None,
                       "total_net_profit_nonpositive": net <= 0,
                       "largest_profit_year": yname(greatest), "largest_profit_year_cny": str(profits[greatest]),
                       "largest_loss_year": yname(least), "largest_loss_year_cny": str(profits[least])})
    return output


def assert_unaffected_downstream(root, paired, retention, support, annual):
    """Every summary row outside the declared dependency graph must be exact."""
    post = root / POST_REL
    changed = {s: set(policies) for s, policies in POLICIES.items()}
    impacted_policy = {s: set(policies) for s, policies in POLICIES.items()}
    impacted_policy["159915.SZ"].add("D120")
    impacted_policy["588000.SS"].add("D60")
    def same_subset(new, saved, selector, label, count):
        left = [x for x in new if selector(x)]
        right = [x for x in saved if selector(x)]
        def canonical(x, parent=""):
            if isinstance(x, dict):
                return {k: canonical(v, k) for k, v in x.items()}
            if isinstance(x, list):
                values = [canonical(v, parent) for v in x]
                if parent in ("dominated_by", "failure_reasons"):
                    values.sort(key=lambda v: json.dumps(v, sort_keys=True, ensure_ascii=False))
                return values
            return x
        if len(left) != count or canonical(left) != canonical(right):
            raise ValueError(f"unaffected {label} rows changed or count drifted")
    same_subset(paired, read_json(post / "paired-comparisons.json"),
                lambda x: x["policy_id"] not in changed.get(x["symbol"], set()) and
                          x["benchmark_id"] not in changed.get(x["symbol"], set()), "pair", 378)
    same_subset(retention, read_json(post / "policy-retention.json"),
                lambda x: x["policy_id"] not in impacted_policy.get(x["symbol"], set()), "retention", 138)
    affected_support = set().union(*impacted_policy.values())
    same_subset(support, read_json(post / "six-product-support.json"),
                lambda x: x["policy_id"] not in affected_support, "support", 9)
    saved_annual = read_json(root / "docs/experiments/raw/factor-ma-year-dependence-2026-09-27/annual-account-summary.json")["rows"]
    same_subset(annual, saved_annual,
                lambda x: (x["symbol"], x["policy_id"], x["fee_scenario_id"]) not in allowed_keys() and
                          x["policy_id"] not in impacted_policy.get(x["symbol"], set()), "annual", 116)


def claim_once(parent, name, value):
    """Fixed local contract marker; it persists after any failure or route change."""
    fd = os.open(parent / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write((json.dumps(value, sort_keys=True) + "\n").encode())
        f.flush()
        os.fsync(f.fileno())


def run(root, contract_path, release_path, plan_path):
    plan = validate_gate(root, contract_path, release_path, plan_path)
    bindings, manifest = verify_inputs(root)
    old = root / OLD_REL
    core = load_module(root / CORE_REL, "accepted_account_core")
    import pandas as pd  # Exact old read_csv float parsing is part of the frozen signal path.
    original = read_json(old / "accounts.json")
    if len(original) != 132 or {key(a) for a in original if a["status"] == "completed"} != {key(a) for a in original}:
        raise ValueError("old accounts incomplete")
    # A local claim is consumed before external creation. A failed run cannot be
    # silently replayed with a newly generated route directory.
    claim_prefix = "account-" + sha(contract_path)
    claim_once(release_path.parent, claim_prefix + ".started.json",
               {"contract_sha256": sha(contract_path), "release_sha256": sha(release_path), "route_plan_sha256": sha(plan_path), "fixed_keys": [list(k) for k in sorted(allowed_keys())]})
    # The route was checked before mkdir; all later writes use the held result fd.
    output_fd = secure_output_dir(plan)
    device = plan["external_device"]
    write_json(output_fd, "source-manifest.json", {"frozen_inputs": bindings, "adapter_sha256": sha(Path(__file__)), "contract_sha256": sha(contract_path), "release_sha256": sha(release_path), "route_plan_sha256": sha(plan_path), "old_accounts_sha256": sha(old / "accounts.json")}, device)
    calendar_spec = read_json(root / INPUT_REL / "calendar.json")
    trading = sorted(d for d, v in read_json(root / calendar_spec["trading_days"]["source_path"])["days"].items() if v["is_trading_day"])
    replacements, new_daily = {}, {}
    for sm in manifest["symbols"]:
        symbol = sm["symbol"]
        if symbol not in POLICIES:
            continue
        saved = read_csv(old / f"{symbol}-states-protected.csv")
        changed = corrected_states(symbol, saved)
        by_day = {r["date"]: r for r in changed}
        if len(by_day) != len(changed):
            raise ValueError("duplicate state day")
        warm = pd.read_csv(root / sm["warmup"]["path"])
        signal = pd.read_csv(root / sm["signal_economic_close"]["path"])
        if len(warm) != 252:
            raise ValueError("wrong original warmup length")
        joined = pd.concat([warm, signal], ignore_index=True)
        rows = [{"date": str(r["date"])[:10], "close": r["economic_index"]} for r in joined.to_dict("records")]
        rebuilt = core.build_states(rows, calendar=[d for d in trading if rows[0]["date"] <= d <= END])
        rebuilt_by_day = {r["date"]: r for r in rebuilt}
        for prior in saved:
            reconstructed = rebuilt_by_day[prior["date"]]
            for policy in (f"{kind}{n}" for n in (20, 60, 120) for kind in "SED"):
                if parse_state(prior[policy]) is not reconstructed[policy]:
                    raise ValueError(f"saved state differs from same-core warmup: {symbol} {prior['date']} {policy}")
        preopen = rebuilt_by_day[str(warm.iloc[-1]["date"])[:10]]
        quotes = read_nominal_quotes(root / sm["nominal_execution_ohlc"]["path"], pd)
        bars = [{"date": q["date"], "open": q["open"], "close": q["close"]} for q in quotes if START <= q["date"] <= END]
        if {b["date"] for b in bars} != set(by_day):
            raise ValueError("nominal quote/state dates differ")
        actions = read_json(old / f"{symbol}-mapped-actions.json")
        reference = read_json(old / f"{symbol}-execution-reference.json")
        restrictions = {r["date"]: "blocked" for r in reference if r["restriction"] == "blocked"}
        if any(r["restriction"] not in (None, "blocked") for r in reference):
            raise ValueError("unknown saved execution restriction")
        for policy in POLICIES[symbol]:
            chosen = [dict(b, state=parse_state(by_day[b["date"]][policy])) for b in bars]
            pre_state = preopen[policy]
            if type(pre_state) not in (bool, type(None)):
                raise ValueError("invalid preopen state")
            for fee_id, fee in FEES.items():
                k = (symbol, policy, fee_id)
                claim_once(release_path.parent, claim_prefix + "." + ".".join(k) + ".json",
                           {"contract_sha256": sha(contract_path), "key": list(k), "account_attempt": 1})
                result = core.simulate_one(policy, chosen, actions=actions, fee=fee,
                                           trading_calendar=[d for d in trading if START <= d <= END],
                                           restrictions=restrictions, period_start=START, period_end=END,
                                           pre_open_state=pre_state)
                file_prefix = f"{symbol}-{policy}-{fee_id}"
                write_csv(output_fd, f"{file_prefix}-daily.csv", result["daily"], device)
                write_json(output_fd, f"{file_prefix}-ledger.json", {field: value for field, value in result.items() if field != "daily"}, device)
                a = dict(next(a for a in original if key(a) == k))
                a.update(clean(result["full"]), annual=clean(result["annual"]),
                         source_identity=sha(release_path), daily_path=f"{file_prefix}-daily.csv", ledger_path=f"{file_prefix}-ledger.json")
                replacements[k] = a
                new_daily[k] = result["daily"]
                write_json(output_fd, f"attempt-progress-{len(replacements):02d}.json", {"completed_keys": [list(x) for x in sorted(replacements)], "account_paths_attempted": len(replacements), "status": "partial_until_summary"}, device)
    accounts = replace_accounts(original, replacements)
    cohort, source_index, comparison_view = comparison_cohort(accounts, original, sha(old / "accounts.json"), sha(release_path))
    paired, retention, support = summarize(root, comparison_view, new_daily)
    annual = annual_summary(accounts, retention)
    assert_unaffected_downstream(root, paired, retention, support, annual)
    write_json(output_fd, "accounts.json", accounts, device)
    write_json(output_fd, "comparison-cohort.json", {"cohort_source_identity": cohort, "source_index": source_index,
                                                     "view_rule": "Only source_identity is set to cohort hash in memory for frozen same-period comparisons; accounts.json retains original per-row provenance."}, device)
    write_json(output_fd, "paired-comparisons.json", paired, device)
    write_json(output_fd, "policy-retention.json", retention, device)
    write_json(output_fd, "six-product-support.json", support, device)
    write_json(output_fd, "annual-account-summary.json", {"source_sha256": sha(old / "accounts.json"),
                                                         "corrected_cohort_source_identity": cohort, "rows": annual}, device)
    write_json(output_fd, "run-summary.json", {"status": "completed_pending_controller_review", "account_paths_attempted": 12, "preserved_accounts": 120, "paired_rows": 432, "retention_rows": 162, "support_rows": 27}, device)
    os.close(output_fd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--route-plan", type=Path, required=True)
    args = parser.parse_args()
    run(*(p.resolve() for p in (args.root, args.contract, args.release, args.route_plan)))


if __name__ == "__main__":
    main()
