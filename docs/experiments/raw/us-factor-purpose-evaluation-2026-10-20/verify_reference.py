"""Independent NumPy check from original CSV, without importing the runner."""
from pathlib import Path
import csv
import hashlib
import json
import random
import numpy as np

RAW = Path(__file__).resolve().parent
design = json.loads((RAW / "design.json").read_text())
manifest = json.loads(Path(design["source_manifest"]["path"]).read_text())
source = Path(manifest["returns"]["path"])
assert hashlib.sha256(source.read_bytes()).hexdigest() == manifest["returns"]["sha256"]
result_path = Path(design["output"]) / "result.json"
result = json.loads(result_path.read_text())
assert hashlib.sha256((result_path.parent / "monthly.csv").read_bytes()).hexdigest() == result["output_csv_sha256"]
with source.open() as handle:
    raw_rows = list(csv.DictReader(handle))
checks = []
for p in design["periods"]:
    rows = [r for r in raw_rows if p["start"] <= r["date"][:7] <= p["end"]]
    rows.sort(key=lambda r: r["date"])
    assert len(rows) == p["expected_months"]
    assert len({r["date"][:7] for r in rows}) == len(rows)
    x = np.array([[float(r[k]) / 100 for k in ["Mom12m", "GP", "BM"]] for r in rows])
    assert np.isfinite(x).all()
    m, gp, bm = x.T
    vals = dict(M=m, halfM=m / 2, GP=gp, BM=bm, mixGP=(m + gp) / 2, mixBM=(m + bm) / 2)
    neg, pos = m < 0, m > 0
    order = sorted(range(len(m)), key=lambda i: (-m[i], rows[i]["date"]))
    top = order[:int(np.ceil(len(m) / 10))]
    saved = result["periods"][p["id"]]
    assert saved["top_M_dates"] == [rows[i]["date"] for i in top]
    assert (saved["M_negative_months"], saved["M_positive_months"], saved["M_zero_months"]) == (
        int(neg.sum()), int(pos.sum()), int((m == 0).sum()))
    for name, y in vals.items():
        expected = dict(mean=y.mean(), sample_sd=y.std(ddof=1), worst=y.min(),
                        negative_fraction=(y < 0).mean(), when_M_negative=y[neg].mean(),
                        when_M_positive=y[pos].mean(), top_M_month_mean=y[top].mean(),
                        correlation_with_M=np.corrcoef(y, m)[0, 1])
        checks.extend(abs(expected[k] - saved["series"][name][k]) for k in expected)
    for c in ["GP", "BM"]:
        y = vals["mix" + c]
        for label, b in [("M", m), ("halfM", m / 2), ("candidate_alone", vals[c])]:
            d = y - b
            expected = dict(mean_difference=d.mean(), sample_sd_difference=y.std(ddof=1) - b.std(ddof=1),
                            when_M_negative_difference=d[neg].mean(),
                            when_M_positive_difference=d[pos].mean(),
                            top_M_month_difference=d[top].mean())
            checks.extend(abs(expected[k] - saved["comparisons"][c][label][k]) for k in expected)
    if p["id"] != "recent":
        continue
    # Same frozen random indices; independent array reductions and percentile calculation.
    rng = random.Random(20261020)
    ids = []
    for draw in range(5000):
        starts = [rng.randrange(len(m)) for _ in range(10)]
        ids.append([(start + j) % len(m) for start in starts for j in range(12)])
    ids = np.array(ids)
    paired_m = m[ids]
    negatives = paired_m < 0
    counts = negatives.sum(axis=1)
    assert (counts > 0).all()
    for c in ["GP", "BM"]:
        y = vals["mix" + c][ids]
        for label, b in [("M", m[ids]), ("halfM", (m / 2)[ids]), ("candidate_alone", vals[c][ids])]:
            diffs = y - b
            values = dict(mean_difference=diffs.mean(axis=1),
                          sample_sd_difference=y.std(axis=1, ddof=1) - b.std(axis=1, ddof=1),
                          when_M_negative_difference=(diffs * negatives).sum(axis=1) / counts)
            for metric, arr in values.items():
                expected = np.quantile(arr, [.025, .975])
                actual = saved["uncertainty"]["pointwise"][c][label][metric]["bounds_95"]
                checks.extend(abs(expected - actual))
assert max(checks) < 1e-12, max(checks)
receipt = dict(status="passed", independent_implementation="numpy direct original CSV",
               numeric_checks=len(checks), max_abs_error=float(max(checks)),
               source_sha256=manifest["returns"]["sha256"],
               result_sha256=hashlib.sha256(result_path.read_bytes()).hexdigest(),
               note="Arithmetic and source check only; not another scientific variant or validity proof.")
(RAW / "independent-numeric-review.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
