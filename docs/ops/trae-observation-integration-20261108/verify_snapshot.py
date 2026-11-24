"""Independent acceptance against original input rows, without the exporter."""
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import fmean

HERE = Path(__file__).resolve().parent
manifest = json.loads((HERE / "manifest.json").read_text())
snapshot = json.loads(Path(manifest["output"]).read_text())
inputs = {}
for symbol, source in manifest["inputs"].items():
    path = Path(source["path"])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]
    rows = json.loads(path.read_text()) if path.suffix == ".json" else list(csv.DictReader(path.open()))
    inputs[symbol] = {row.get("day", row.get("date")): float(row.get("close", row.get("value"))) for row in rows}

checked = []
for card in snapshot["cards"]:
    num, den = (inputs[card[key]["symbol"]] for key in ("numerator", "denominator"))
    days = sorted(d for d in set(num) & set(den) if "2024-01-01" <= d <= "2026-11-06")
    assert days == [point["date"] for point in card["points"]]
    ratios = [num[d] / den[d] for d in days]
    for i, row in enumerate(card["points"]):
        assert row["numerator"] == num[row["date"]] and row["denominator"] == den[row["date"]]
        assert math.isclose(row["ratio"], ratios[i], rel_tol=1e-13)
        if i < 59:
            assert row["ma60"] is None
        else:
            assert math.isclose(row["ma60"], fmean(ratios[i-59:i+1]), rel_tol=1e-13)
    checked.append(dict(id=card["id"], checked_points=len(days), same_date_pairs=True,
                        matched_raw_prices=True, trailing_mean_only=True))
assert len(checked) == 4
result = dict(status="passed", checked=checked, total_points=sum(x["checked_points"] for x in checked),
              output_sha256=hashlib.sha256(Path(manifest["output"]).read_bytes()).hexdigest())
(HERE / "data-acceptance.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
