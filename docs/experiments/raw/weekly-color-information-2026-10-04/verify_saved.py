"""Standard-library readback of saved evidence, never a market re-run."""
import argparse
from pathlib import Path
import hashlib
import json
import math
from statistics import mean

REL = Path("docs/experiments/raw/weekly-color-information-2026-10-04")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument("--results-only", action="store_true")
    args = parser.parse_args()
    raw = args.root / REL
    manifest = json.loads((raw/"manifest.json").read_text())
    required = {str(REL/"analysis.json"), str(REL/"verify_saved.py")}
    required |= {str(REL/target/"core-01"/name)
                 for target in ("return","risk") for name in ("result.json","contract.json","receipt.json")}
    for item in manifest["files"]:
        if args.results_only and item["path"] not in required:
            continue
        path = args.root / item["path"]
        assert path.stat().st_size == item["bytes"], item["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"], item["path"]
    assert required <= {item["path"] for item in manifest["files"]}
    analysis = json.loads((raw/"analysis.json").read_text())
    rows, fits, summary = 0, 0, {}
    for target in ("return","risk"):
        folder = raw/target/"core-01"
        result = json.loads((folder/"result.json").read_text())
        contract = json.loads((folder/"contract.json").read_text())
        receipt = json.loads((folder/"receipt.json").read_text())
        assert hashlib.sha256((folder/"result.json").read_bytes()).hexdigest() == receipt["outputs"]["result.json"]
        predictions = result["predictions"]
        assert len({r["id"] for r in predictions}) == len(predictions)
        for row in predictions:
            fold = contract["split"]["folds"][int(row["fold"])]
            assert fold["eval_start"] <= row["date"] <= row["label_end"] <= fold["eval_end"]
            row["ETF_mean"] = analysis["core"][target]["training_means"][row["fold"]][row["asset"]]
        assets = sorted({r["asset"] for r in predictions})
        scores = {m: math.sqrt(mean(mean((r[m]-r["y"])**2 for r in predictions if r["asset"] == asset)
                                    for asset in assets)) for m in ("B0","B1","B2","ETF_mean")}
        for m,v in scores.items():
            assert abs(v-analysis["core"][target]["subsets"]["all"]["rmse"][m]) < 1e-10
        rows += len(predictions)
        fits += result["execution"]["fits"]
        summary[target] = {"rows":len(predictions),"rmse":scores,"B1_minus_B2":scores["B1"]-scores["B2"]}
    assert fits == 8 and rows == sum(analysis["core"][target]["subsets"]["all"]["rows"] for target in ("return", "risk"))
    print(json.dumps({"saved_evidence_verified":True,"new_fits":0,"mode":"results_only" if args.results_only else "manifest",
                      "input_qualification_rechecked":False,"summary":summary},ensure_ascii=False,allow_nan=False))


if __name__ == "__main__":
    main()
