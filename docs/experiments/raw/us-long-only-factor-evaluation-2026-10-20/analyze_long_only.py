"""Frozen French 2x3 value-weighted monthly long-only reference comparison.

CLI --design ABS --contract ABS. Contract us-long-only-run/1 needs approved true,
exact SHA bindings for design, runner, definitions_snapshot, source_qualification,
method_review, storage_plan, storage_module, and sources BM/OP/MOM. No source
download. Output is create-only on the saved external route.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import random
import re
import statistics
import struct
from pathlib import Path

MAIN = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
STORAGE_MODULE = MAIN / "src/lei_signal/research/output_storage.py"
SCHEMA = "us-long-only-run/1"
SOURCES = ("BM", "OP", "MOM")
SIZES = ("small", "big")
SERIES = ("L", "N", "H", "B")
CONTRASTS = (("H-B", "H", "B"), ("H-N", "H", "N"), ("B-L", "B", "L"), ("H-L", "H", "L"))
METRICS = ("mean_H_minus_B", "mean_H_minus_N", "mean_B_minus_L",
           "sd_H_minus_B", "B_negative_mean_H_minus_B",
           "B_positive_mean_H_minus_B", "B_negative_mean_H_minus_N")


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def bound(binding):
    if not isinstance(binding, dict) or set(binding) != {"path", "sha256"}:
        raise ValueError("binding needs exact path and sha256")
    path = Path(binding["path"])
    digest = binding["sha256"]
    if not path.is_absolute() or not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("invalid bound path or sha256")
    if not path.is_file() or sha256(path) != digest:
        raise ValueError(f"bound source absent or changed: {path}")
    return path.resolve()


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load {name}")
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def calendar(start, end):
    def index(value):
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value):
            raise ValueError("bad period month")
        return int(value[:4]) * 12 + int(value[5:7]) - 1
    lo, hi = index(start), index(end)
    if hi < lo:
        raise ValueError("reversed period")
    return [f"{m // 12:04d}-{m % 12 + 1:02d}" for m in range(lo, hi + 1)]


def parse_section(path, *, returns_section, count_section, headers):
    """Isolate exactly the two named monthly sections; ignore annual/other tables."""
    wanted = {returns_section: {}, count_section: {}}
    found = set()
    section = None
    waiting_header = False
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        for raw in f:
            line = raw.strip()
            if line in wanted:
                if line in found:
                    raise ValueError(f"duplicate section: {line}")
                found.add(line)
                section = line
                waiting_header = True
                continue
            if section is None:
                continue
            if waiting_header:
                if not line:
                    continue
                cells = next(csv.reader([raw], strict=True))
                if cells[0].strip() != "" or [v.strip() for v in cells[1:]] != headers:
                    raise ValueError(f"wrong monthly header in {section}")
                waiting_header = False
                continue
            if not line:
                section = None
                continue
            cells = next(csv.reader([raw], strict=True))
            key = cells[0].strip()
            if not re.fullmatch(r"\d{6}", key):
                section = None
                continue
            month = f"{key[:4]}-{key[4:6]}"
            if month[5:7] not in [f"{m:02d}" for m in range(1, 13)] or len(cells) != 7:
                raise ValueError(f"invalid monthly row: {key}")
            if month in wanted[section]:
                raise ValueError(f"duplicate monthly row: {month} {section}")
            values = []
            for cell in cells[1:]:
                try:
                    value = float(cell.strip())
                except ValueError:
                    raise ValueError(f"non-numeric value {month} {section}") from None
                if not math.isfinite(value):
                    raise ValueError(f"nonfinite value {month} {section}")
                values.append(value)
            wanted[section][month] = values
    if found != set(wanted) or waiting_header:
        raise ValueError("required monthly section absent/incomplete")
    return wanted[returns_section], wanted[count_section]


def prepare_source(source, periods, *, returns_section, count_section, missing_codes):
    returns, counts = parse_section(source["path"], returns_section=returns_section,
                                    count_section=count_section, headers=source["headers"])
    if source["small_indices"] != [0, 1, 2] or source["big_indices"] != [3, 4, 5]:
        raise ValueError("unexpected size order")
    result = {}
    for period in periods:
        required = calendar(period["start"], period["end"])
        if len(required) != period["expected_months"]:
            raise ValueError("period month count differs")
        if any(month not in returns or month not in counts for month in required):
            raise ValueError(f"missing return/count month in {period['id']}")
        result[period["id"]] = {}
        for size in SIZES:
            indices = source[f"{size}_indices"]
            rows = []
            for month in required:
                r, n = returns[month], counts[month]
                if len(r) != 6 or len(n) != 6:
                    raise ValueError("return/count width mismatch")
                prices = [r[i] for i in indices]
                numbers = [n[i] for i in indices]
                if any(v in missing_codes or v < -100 for v in prices):
                    raise ValueError(f"missing/invalid monthly return: {month}")
                if any(v in missing_codes or v <= 0 or v != int(v) for v in numbers):
                    raise ValueError(f"missing/invalid firm count: {month}")
                L, N, H = [v / 100 for v in prices]
                B = (L + N + H) / 3
                rows.append({"month": month, "source": source["id"], "size": size,
                             "L": L, "N": N, "H": H, "B": B,
                             "Nfirm_L": int(numbers[0]), "Nfirm_N": int(numbers[1]),
                             "Nfirm_H": int(numbers[2])})
            result[period["id"]][size] = rows
    return result


def mean(values):
    return math.fsum(values) / len(values) if values else None


def sample_sd(values):
    return statistics.stdev(values) if len(values) > 1 else None


def wealth_stats(values):
    """Gross monthly path includes initial wealth 1 in its peak."""
    wealth = peak = 1.0
    worst = 0.0
    for value in values:
        if value < -1:
            raise ValueError("return below -100%")
        wealth *= 1 + value
        if not math.isfinite(wealth):
            raise ValueError("nonfinite wealth path")
        peak = max(peak, wealth)
        worst = min(worst, wealth / peak - 1)
    return wealth - 1, worst


def describe(rows):
    if not rows:
        raise ValueError("empty selected period")
    n = len(rows)
    negative = [r for r in rows if r["B"] < 0]
    positive = [r for r in rows if r["B"] > 0]
    top = sorted(rows, key=lambda r: (-r["B"], r["month"]))[:math.ceil(.1 * n)]
    performance = {}
    for name in SERIES:
        values = [r[name] for r in rows]
        growth, drawdown = wealth_stats(values)
        performance[name] = {"mean": mean(values), "sample_sd": sample_sd(values),
                             "worst_month": min(values),
                             "negative_month_fraction": sum(v < 0 for v in values) / n,
                             "B_negative_month_mean": mean([r[name] for r in negative]),
                             "B_positive_month_mean": mean([r[name] for r in positive]),
                             "top_B_decile_month_mean": mean([r[name] for r in top]),
                             "monthly_compounded_path_growth": growth,
                             "monthly_compounded_path_drawdown": drawdown}
    contrasts = {}
    for label, left, right in CONTRASTS:
        diffs = [r[left] - r[right] for r in rows]
        contrasts[label] = {
            "mean_paired_difference": mean(diffs),
            "sample_sd_of_paired_difference": sample_sd(diffs),
            "sample_sd_level_difference": performance[left]["sample_sd"] - performance[right]["sample_sd"],
            "B_negative_mean_difference": mean([r[left] - r[right] for r in negative]),
            "B_positive_mean_difference": mean([r[left] - r[right] for r in positive]),
            "top_B_decile_mean_difference": mean([r[left] - r[right] for r in top])}
    counts = {}
    for name in ("L", "N", "H"):
        v = [r[f"Nfirm_{name}"] for r in rows]
        counts[name] = {"min": min(v), "median": statistics.median(v), "max": max(v)}
    totals = [r["Nfirm_L"] + r["Nfirm_N"] + r["Nfirm_H"] for r in rows]
    counts["three_groups_total"] = {"min": min(totals), "median": statistics.median(totals), "max": max(totals)}
    return {"months": n, "first_month": rows[0]["month"], "last_month": rows[-1]["month"],
            "B_negative_months": len(negative), "B_positive_months": len(positive),
            "B_zero_months": n - len(negative) - len(positive),
            "top_B_month_count": len(top), "top_B_months": [r["month"] for r in top],
            "top_B_positive_months": sum(r["B"] > 0 for r in top),
            "performance": performance, "contrasts": contrasts, "firm_counts": counts}


def stability(rows, *, halves=None):
    years = sorted({r["month"][:4] for r in rows})
    annual = {year: describe([r for r in rows if r["month"].startswith(year)])["contrasts"]
              for year in years}
    n = len(rows)
    by_contrast = {}
    for label, left, right in CONTRASTS:
        leave = {year: mean([r[left] - r[right] for r in rows if not r["month"].startswith(year)])
                 for year in years}
        contributions = {year: math.fsum(r[left] - r[right] for r in rows if r["month"].startswith(year)) / n
                         for year in years}
        dominant = sorted(contributions, key=lambda y: (-abs(contributions[y]), y))[0]
        by_contrast[label] = {"leave_one_year_out_mean_min": min(leave.values()),
                              "leave_one_year_out_mean_max": max(leave.values()),
                              "largest_absolute_annual_mean_contribution": {
                                  "year": dominant, "value": contributions[dominant]}}
    half_values = None
    if halves:
        half_values = []
        for start, end in halves:
            subset = [r for r in rows if start <= r["month"] <= end]
            if len(subset) != len(calendar(start, end)):
                raise ValueError("half calendar support incomplete")
            half_values.append({"start": start, "end": end, "statistics": describe(subset)})
    return {"annual_contrasts": annual, "contrasts": by_contrast, "primary_halves": half_values}


def circular_indices(n, block, rng):
    out = []
    while len(out) < n:
        start = rng.randrange(n)
        out.extend((start + offset) % n for offset in range(block))
    return out[:n]


def quantile(values, fraction):
    values = sorted(values)
    point = (len(values) - 1) * fraction
    low, high = math.floor(point), math.ceil(point)
    return values[low] + (values[high] - values[low]) * (point - low)


def draw_stats(rows):
    d = describe(rows)
    c, p = d["contrasts"], d["performance"]
    return {
        "mean_H_minus_B": c["H-B"]["mean_paired_difference"],
        "mean_H_minus_N": c["H-N"]["mean_paired_difference"],
        "mean_B_minus_L": c["B-L"]["mean_paired_difference"],
        "sd_H_minus_B": c["H-B"]["sample_sd_level_difference"],
        "B_negative_mean_H_minus_B": c["H-B"]["B_negative_mean_difference"],
        "B_positive_mean_H_minus_B": c["H-B"]["B_positive_mean_difference"],
        "B_negative_mean_H_minus_N": c["H-N"]["B_negative_mean_difference"]}


def intervals(joint_rows, *, draws=5000, block=12, seed=20261020):
    """One index matrix shared by BM/OP/MOM; conditions recomputed each draw."""
    n = len(joint_rows["BM"])
    if any(len(joint_rows[s]) != n for s in SOURCES):
        raise ValueError("joint period sizes differ")
    rng = random.Random(seed)
    collections = {(source, metric): [] for source in SOURCES for metric in METRICS}
    digest = hashlib.sha256()
    for _ in range(draws):
        indices = circular_indices(n, block, rng)
        for index in indices:
            digest.update(struct.pack(">H", index))
        for source in SOURCES:
            stats = draw_stats([joint_rows[source][i] for i in indices])
            for metric in METRICS:
                value = stats[metric]
                if value is not None:
                    collections[source, metric].append(value)
    out = {}
    for source in SOURCES:
        out[source] = {}
        for metric in METRICS:
            values = collections[source, metric]
            out[source][metric] = {
                "bounds_95": [quantile(values, .025), quantile(values, .975)] if values else None,
                "valid_draws": len(values), "missing_draws": draws - len(values)}
    return {"draws": draws, "block_months": block, "seed": seed,
            "index_sha256_u16be": digest.hexdigest(),
            "empty_conditions_are_missing": True, "pointwise": out}


def calculate(prepared, design, *, draws=None):
    periods = design["periods"]
    if [(p["id"], p["expected_months"]) for p in periods] != [
        ("primary", 120), ("early", 618), ("recent_public", 20)]:
        raise ValueError("periods differ from frozen definition")
    output = {}
    monthly = []
    for source in SOURCES:
        output[source] = {}
        for period in periods:
            ident = period["id"]
            output[source][ident] = {}
            for size in SIZES:
                rows = prepared[source][ident][size]
                if [r["month"] for r in rows] != calendar(period["start"], period["end"]):
                    raise ValueError("source date support differs")
                stat = describe(rows)
                stat["stability"] = stability(rows, halves=design["stability"]["primary_halves"] if ident == "primary" else None)
                output[source][ident][size] = stat
                monthly.extend({"period": ident, **row,
                                **{label: row[left] - row[right] for label, left, right in CONTRASTS}}
                               for row in rows)
    u = design["uncertainty"]
    if (u["period"], u["size"], u["block_months"], u["draws"], u["seed"], u["statistics"]) != (
        "primary", "big", 12, 5000, 20261020, list(METRICS)):
        raise ValueError("uncertainty differs from frozen design")
    joint = {s: prepared[s]["primary"]["big"] for s in SOURCES}
    ci = intervals(joint, draws=u["draws"] if draws is None else draws,
                   block=u["block_months"], seed=u["seed"])
    for source in SOURCES:
        output[source]["primary"]["big"]["uncertainty"] = {
            **{key: ci[key] for key in ("draws", "block_months", "seed", "index_sha256_u16be", "empty_conditions_are_missing")},
            "pointwise": ci["pointwise"][source]}
    return output, monthly


def execute(design_path, contract_path):
    design_path = Path(design_path).resolve()
    contract_path = Path(contract_path).resolve()
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("schema") != SCHEMA or contract.get("approved") is not True:
        raise ValueError("run contract not approved")
    names = {"design", "runner", "definitions_snapshot", "source_qualification",
             "method_review", "storage_plan", "storage_module"}
    bindings = contract.get("bindings", {})
    if set(bindings) != names or set(contract.get("sources", {})) != set(SOURCES):
        raise ValueError("incomplete contract bindings")
    files = {name: bound(binding) for name, binding in bindings.items()}
    source_files = {source: bound(binding) for source, binding in contract["sources"].items()}
    if files["design"] != design_path or files["runner"] != Path(__file__).resolve():
        raise ValueError("wrong bound design/runner")
    if files["storage_module"] != STORAGE_MODULE.resolve():
        raise ValueError("wrong storage module")
    design = json.loads(design_path.read_text(encoding="utf-8"))
    if design.get("schema") != "us-long-only-reference-design/1" or design.get("status") != "design_before_effects":
        raise ValueError("design state differs")
    if contract.get("output") != design["output"] or files["storage_plan"] != Path(design["storage_plan"]).resolve():
        raise ValueError("output or storage plan differs")
    sources = {item["id"]: item for item in design["sources"]}
    if set(sources) != set(SOURCES) or any(source_files[s] != Path(sources[s]["path"]).resolve() or
                                           contract["sources"][s]["sha256"] != sources[s]["sha256"] for s in SOURCES):
        raise ValueError("source identity differs from design")
    definitions = json.loads(files["definitions_snapshot"].read_text(encoding="utf-8"))
    objects = definitions.get("objects")
    if not isinstance(objects, list):
        raise ValueError("definition objects missing")
    registered = {(item.get("id"), item.get("version")) for item in objects if isinstance(item, dict)}
    if any(tuple(sources[s]["reference"].split("@", 1)) not in registered for s in SOURCES):
        raise ValueError("source reference definition not registered")
    qualification = json.loads(files["source_qualification"].read_text(encoding="utf-8"))
    if qualification.get("performance_not_computed") is not True:
        raise ValueError("source qualification state changed")
    metadata = qualification.get("metadata", {})
    for s in SOURCES:
        entry = metadata.get(Path(source_files[s]).name)
        if not entry or entry.get("sha256") != sources[s]["sha256"]:
            raise ValueError("source qualification does not bind source")
    storage = json.loads(files["storage_plan"].read_text(encoding="utf-8"))
    if storage.get("output") != design["output"]:
        raise ValueError("saved route differs")
    out = Path(design["output"])
    if out.exists():
        raise FileExistsError("refusing existing output")
    storage_mod = module(files["storage_module"], "french_output_storage")
    storage_mod.recheck_saved_plan(MAIN, storage, storage["task_id"], storage["estimated_bytes"],
                                   storage["internal_metadata_bytes"])
    if not storage_mod._still_mounted(storage):
        raise ValueError("external disk not mounted")
    prepared = {s: prepare_source({**sources[s], "path": source_files[s]}, design["periods"],
                                   returns_section=design["returns_section"], count_section=design["count_section"],
                                   missing_codes=design["missing_codes"]) for s in SOURCES}
    output, monthly = calculate(prepared, design)
    if out.exists() or not storage_mod._still_mounted(storage):
        raise FileExistsError("output exists or external disk changed")
    run = out.parent
    if run.parent.exists() and run.parent.stat().st_dev != storage["external_device"]:
        raise ValueError("external parent device differs")
    run.mkdir(parents=True, exist_ok=False)
    out.mkdir(exist_ok=False)
    with (out / "monthly.csv").open("x", encoding="utf-8", newline="") as f:
        fields = ["period", "source", "size", "month", "L", "N", "H", "B",
                  "H-B", "H-N", "B-L", "H-L", "Nfirm_L", "Nfirm_N", "Nfirm_H"]
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(monthly)
    result = {
        "schema": "us-long-only-reference-result/1", "unit": "decimal published portfolio monthly return",
        "statistics": output,
        "source_sha256": {s: sources[s]["sha256"] for s in SOURCES},
        "source_family": design["source_family"],
        "source_version": qualification["source_version"],
        "definition_notes": design["definition_notes"],
        "definition_references": {s: sources[s]["reference"] for s in SOURCES},
        "design_sha256": sha256(design_path), "runner_sha256": sha256(__file__),
        "definitions_snapshot_sha256": sha256(files["definitions_snapshot"]),
        "qualification_sha256": sha256(files["source_qualification"]),
        "method_review_sha256": sha256(files["method_review"]),
        "storage_plan_sha256": sha256(files["storage_plan"]),
        "contract_sha256": sha256(contract_path),
        "monthly_sha256": sha256(out / "monthly.csv"),
        "not_evaluated": design["not_evaluated"],
        "limits": ["Published US value-weighted long-only groups, not OSAP or local stock strategy.",
                   "B is equal capital to three published groups; no cash or fee model.",
                   "Differences are paired arithmetic monthly contrasts, never compounded short spreads.",
                   "Initial wealth 1 included in month-end quote-path drawdown.",
                   "All public history was previously available; intervals are exploratory and pointwise."]}
    with (out / "result.json").open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, allow_nan=False, indent=2)
        f.write("\n")
    return {"result": str(out / "result.json"), "sha256": sha256(out / "result.json")}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--design", required=True)
    parser.add_argument("--contract", required=True)
    args = parser.parse_args()
    print(json.dumps(execute(args.design, args.contract), ensure_ascii=False))


if __name__ == "__main__":
    main()
