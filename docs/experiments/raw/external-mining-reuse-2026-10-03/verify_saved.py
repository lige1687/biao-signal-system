"""Verify saved artificial evidence; stdlib only, no new optimization."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def near(a, b):
    assert math.isclose(a, b, abs_tol=1e-9, rel_tol=1e-9), (a, b)


def corr(a, b):
    ca = [v - sum(a)/len(a) for v in a]
    cb = [v - sum(b)/len(b) for v in b]
    d = math.sqrt(sum(v*v for v in ca) * sum(v*v for v in cb))
    return None if d == 0 else sum(x*y for x,y in zip(ca,cb))/d


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    root = ap.parse_args().root
    manifest = json.loads((root/"manifest.json").read_text())
    for item in manifest["files"]:
        p = root/item["path"]
        assert p.stat().st_size == item["bytes"], item["path"]
        assert hashlib.sha256(p.read_bytes()).hexdigest() == item["sha256"], item["path"]
    data = json.loads((root/"core-result.json").read_text())
    assert data["upstream_source_unchanged"]
    for key, filename in [("protocol_sha256","protocol.json"),("runner_sha256","run.py")]:
        assert data[key] == hashlib.sha256((root/filename).read_bytes()).hexdigest()
    rows = data["pool_transitions"]
    assert [r["size"] for r in rows] == [1,2,2,3]
    assert [r["eval_cnt"] for r in rows] == [1,2,2,3]
    assert rows[1]["json"] == rows[2]["json"]
    assert rows[3]["json"]["exprs"] == ["$close","$open","$low"]
    x,z,target = (data["inputs"][n] for n in ["x","z","target"])
    features = {"$close":x,"$open":z,"$high":x,"$low":[[-v for v in r] for r in x]}
    for row in rows:
        daily = []
        for day, truth in enumerate(target):
            predicted = [sum(w*features[e][day][j] for e,w in zip(row["json"]["exprs"],row["json"]["weights"])) for j in range(4)]
            daily.append(corr(predicted,truth))
        near(sum(daily)/len(daily),row["current_ic"])
    near(rows[0]["current_ic"],1/math.sqrt(2))
    for row in rows[1:]:
        near(row["current_ic"],1)
    near(corr(x[0],z[0]),0)
    near(corr(x[0],features["$low"][0]),-1)
    for case in data["semantic_cases"]:
        assert all(corr(a,b) is None for a,b in zip(case["input"],case["target"]))
        near(corr([r[0] for r in case["input"]],[r[0] for r in case["target"]]),1)
        near(case["native_ic"],0)
    assert data["stock_data_precondition"]["missing_module"] == "qlib"
    assert data["budget"]["market_fits"] == 0
    print(json.dumps({"status":"passed","files_verified":len(manifest["files"]),"independent_numeric_cases":6,"new_fits":0,"requires_upstream_torch_numpy":False}))


if __name__ == "__main__":
    main()
