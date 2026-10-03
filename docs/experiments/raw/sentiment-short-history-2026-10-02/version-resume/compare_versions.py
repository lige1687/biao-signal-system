"""Compare immutable saved provider snapshots; no prices, outcomes or fitting."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
old_path = ROOT / "earliest-ma-snapshot.json"
new_path = ROOT.parent / "inputs" / "ma_percentage_historical.json"
expected = {
    old_path: "d864e90bb71817bbb55caeba7985807d3806d290934102072d4fcd1aea8096b2",
    new_path: "613fa152ee6cf2820df59f5566eb4601bda2f1c71747b7bda96d8128282011c7",
}
for path, fingerprint in expected.items():
    assert hashlib.sha256(path.read_bytes()).hexdigest() == fingerprint
old, new = (json.loads(p.read_text()) for p in (old_path, new_path))
before = {r["date"]: r for r in old["data"]}
after = {r["date"]: r for r in new["data"]}
dates = sorted(set(before) & set(after))
result = {
    "old_generated_at": old["metadata"]["generated_at"],
    "new_generated_at": new["metadata"]["generated_at"],
    "old_rows": len(before),
    "old_range": [min(before), max(before)],
    "common_dates": len(dates),
    "range": [min(dates), max(dates)],
    "windows": {},
}
for window in (20, 50, 200):
    key = f"ma_{window}"
    differences = [after[d][key]["percentage_above"] - before[d][key]["percentage_above"] for d in dates]
    counts = [after[d][key]["count_above"] - before[d][key]["count_above"] for d in dates]
    result["windows"][str(window)] = {
        "changed_percentage_dates": sum(abs(v) > 1e-8 for v in differences),
        "max_absolute_percentage_point_change": max(abs(v) for v in differences),
        "changed_numerator_dates": sum(v != 0 for v in counts),
        "max_absolute_numerator_change": max(abs(v) for v in counts),
    }
for name, source in (("old", before), ("new", after)):
    result[f"low15_in_shared_{name}"] = [d for d in dates if all(source[d][f"ma_{w}"]["percentage_above"] <= 15 for w in (20, 50))]
(ROOT / "reproduced-version-comparison.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(result, ensure_ascii=False))
