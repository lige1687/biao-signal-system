"""Independent NumPy reconstruction from official CSVs; imports no runner code."""
import csv
import hashlib
import io
import json
import math
import random
import struct
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

RAW = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def section(path, title):
    text = Path(path).read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.strip() == title]
    assert len(starts) == 1
    i = starts[0] + 1
    while not lines[i].strip():
        i += 1
    header = [x.strip() for x in next(csv.reader([lines[i]]))]
    rows = {}
    for cells in csv.reader(io.StringIO("\n".join(lines[i + 1:]))):
        if not cells or not cells[0].strip().isdigit() or len(cells[0].strip()) != 6:
            break
        date = cells[0].strip()
        month = date[:4] + "-" + date[4:]
        assert month not in rows and len(cells) == 7
        rows[month] = [float(x) for x in cells[1:]]
    return header[1:], rows


def main():
    design = json.loads((RAW / "design.json").read_text())
    contract = json.loads((RAW / "run-contract.json").read_text())
    result_path = Path(design["output"]) / "result.json"
    result = json.loads(result_path.read_text())
    for binding in [*contract["bindings"].values(), *contract["sources"].values()]:
        assert sha(binding["path"]) == binding["sha256"], binding["path"]
    assert result["contract_sha256"] == sha(RAW / "run-contract.json")
    assert result["monthly_sha256"] == sha(Path(design["output"]) / "monthly.csv")
    checks = 0
    max_error = 0.0
    raw_primary = {}
    expected_rows = {}

    def check(actual, wanted):
        nonlocal checks, max_error
        checks += 1
        if actual is None or wanted is None:
            assert actual is None and wanted is None
            return
        error = abs(float(actual) - float(wanted))
        max_error = max(max_error, error)
        assert error <= 1e-10 * max(1, abs(float(wanted))), (actual, wanted, error)

    labels = ["L", "N", "H", "B"]
    pairs = {"H-B": (2, 3), "H-N": (2, 1), "B-L": (3, 0), "H-L": (2, 0)}
    for source in design["sources"]:
        h, returns = section(source["path"], design["returns_section"])
        ch, counts = section(source["path"], design["count_section"])
        assert h == ch == source["headers"]
        for period in design["periods"]:
            dates = sorted(m for m in returns if period["start"] <= m <= period["end"])
            assert len(dates) == period["expected_months"]
            for size, indices in [("big", [3, 4, 5]), ("small", [0, 1, 2])]:
                original = np.array([returns[m] for m in dates])[:, indices] / 100
                x = np.column_stack([original, original.mean(axis=1)])
                n = np.array([counts[m] for m in dates])[:, indices]
                saved = result["statistics"][source["id"]][period["id"]][size]
                if size == "big" and period["id"] == "primary":
                    raw_primary[source["id"]] = x
                check(saved["months"], len(dates))
                neg, pos = x[:, 3] < 0, x[:, 3] > 0
                top = sorted(range(len(dates)), key=lambda i: (-x[i, 3], dates[i]))[:math.ceil(.1 * len(dates))]
                assert saved["top_B_months"] == [dates[i] for i in top]
                for key, value in [("B_negative_months", neg.sum()), ("B_positive_months", pos.sum()),
                                   ("B_zero_months", (~(neg | pos)).sum())]:
                    check(saved[key], value)
                for j, label in enumerate(labels):
                    p = saved["performance"][label]
                    wealth = np.r_[1.0, np.cumprod(1 + x[:, j])]
                    values = {
                        "mean": x[:, j].mean(), "sample_sd": x[:, j].std(ddof=1),
                        "worst_month": x[:, j].min(), "negative_month_fraction": (x[:, j] < 0).mean(),
                        "B_negative_month_mean": x[neg, j].mean() if neg.any() else None,
                        "B_positive_month_mean": x[pos, j].mean() if pos.any() else None,
                        "top_B_decile_month_mean": x[top, j].mean(),
                        "monthly_compounded_path_growth": wealth[-1] - 1,
                        "monthly_compounded_path_drawdown": (wealth / np.maximum.accumulate(wealth) - 1).min(),
                    }
                    for key, value in values.items():
                        check(p[key], value)
                for label, (a, b) in pairs.items():
                    diff = x[:, a] - x[:, b]
                    for key, value in {
                        "mean_paired_difference": diff.mean(),
                        "sample_sd_of_paired_difference": diff.std(ddof=1),
                        "sample_sd_level_difference": x[:, a].std(ddof=1) - x[:, b].std(ddof=1),
                        "B_negative_mean_difference": diff[neg].mean() if neg.any() else None,
                        "B_positive_mean_difference": diff[pos].mean() if pos.any() else None,
                        "top_B_decile_mean_difference": diff[top].mean(),
                    }.items():
                        check(saved["contrasts"][label][key], value)
                    yearly = saved["stability"]["annual_contrasts"]
                    for year in yearly:
                        selection = np.array([d.startswith(year) for d in dates])
                        check(yearly[year][label]["mean_paired_difference"], diff[selection].mean())
                    left = [diff[np.array([not d.startswith(y) for d in dates])].mean() for y in yearly]
                    check(saved["stability"]["contrasts"][label]["leave_one_year_out_mean_min"], min(left))
                    check(saved["stability"]["contrasts"][label]["leave_one_year_out_mean_max"], max(left))
                check(saved["contrasts"]["H-B"]["mean_paired_difference"] +
                      saved["contrasts"]["B-L"]["mean_paired_difference"],
                      saved["contrasts"]["H-L"]["mean_paired_difference"])
                for label, col in [("L", n[:, 0]), ("N", n[:, 1]), ("H", n[:, 2]),
                                   ("three_groups_total", n.sum(axis=1))]:
                    for key, value in [("min", col.min()), ("median", np.median(col)), ("max", col.max())]:
                        check(saved["firm_counts"][label][key], value)
                for i, month in enumerate(dates):
                    expected_rows[(period["id"], source["id"], size, month)] = (x[i], n[i])

    # Check complete exported rows against originals, including signed differences.
    seen = set()
    with (Path(design["output"]) / "monthly.csv").open() as f:
        for row in csv.DictReader(f):
            key = tuple(row[k] for k in ("period", "source", "size", "month"))
            assert key not in seen
            seen.add(key)
            x, n = expected_rows[key]
            for j, label in enumerate(labels):
                check(row[label], x[j])
            for label, (a, b) in pairs.items():
                check(row[label], x[a] - x[b])
            for j, label in enumerate(labels[:3]):
                check(row["Nfirm_" + label], n[j])
    assert seen == set(expected_rows)

    # Independent vectorized interval estimates using the frozen random stream.
    rng = random.Random(20261020)
    indices = np.array([[(start + offset) % 120
                         for start in [rng.randrange(120) for _ in range(10)]
                         for offset in range(12)] for _ in range(5000)])
    digest = hashlib.sha256(b"".join(struct.pack(">H", int(i)) for i in indices.ravel())).hexdigest()
    for sid, x in raw_primary.items():
        a = x[indices]
        hb, hn, bl = a[:, :, 2] - a[:, :, 3], a[:, :, 2] - a[:, :, 1], a[:, :, 3] - a[:, :, 0]
        neg, pos = a[:, :, 3] < 0, a[:, :, 3] > 0
        def conditional(v, mask):
            den = mask.sum(axis=1)
            return np.divide((v * mask).sum(axis=1), den,
                             out=np.full(5000, np.nan), where=den > 0)
        values = {
            "mean_H_minus_B": hb.mean(axis=1), "mean_H_minus_N": hn.mean(axis=1),
            "mean_B_minus_L": bl.mean(axis=1),
            "sd_H_minus_B": a[:, :, 2].std(axis=1, ddof=1) - a[:, :, 3].std(axis=1, ddof=1),
            "B_negative_mean_H_minus_B": conditional(hb, neg),
            "B_positive_mean_H_minus_B": conditional(hb, pos),
            "B_negative_mean_H_minus_N": conditional(hn, neg),
        }
        u = result["statistics"][sid]["primary"]["big"]["uncertainty"]
        assert digest == u["index_sha256_u16be"]
        for metric, v in values.items():
            good = v[np.isfinite(v)]
            saved = u["pointwise"][metric]
            check(saved["valid_draws"], len(good))
            check(saved["missing_draws"], 5000 - len(good))
            for actual, wanted in zip(saved["bounds_95"], np.quantile(good, [.025, .975])):
                check(actual, wanted)

    receipt = {
        "schema": "us-long-only-independent-check/1",
        "checked_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "result": {"path": str(result_path), "sha256": sha(result_path)},
        "checker_sha256": sha(__file__), "runner_imported": False,
        "method": "Independent CSV section reading and NumPy arithmetic; 5000 identical-design block draws independently reconstructed",
        "numeric_comparisons": checks, "exported_rows": len(seen), "maximum_absolute_difference": max_error,
        "tolerance": "1e-10 * max(1, abs(reference)), floating roundoff only",
        "status": "passed", "source_hashes_match": True, "new_hypothesis_variants": 0,
        "limits": "Checks calculation, not historical source revisions, stock membership or future usefulness.",
    }
    out = RAW / "independent-check.json"
    with out.open("x") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
