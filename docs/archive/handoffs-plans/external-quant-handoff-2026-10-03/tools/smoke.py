"""Minimum compute + archived input reading only; no fitting or sealed research."""
from pathlib import Path
import argparse
import hashlib
import json
import sys


def fingerprint(paths):
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--with-archives", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    sys.path.insert(0, str(root / "src"))
    sys.path.insert(0, str(root / ".agents/skills/lei-quant-tools/scripts"))
    from quant_tools import mean_hac, xshg_date
    from tsfresh_calculators import mean_abs_change
    days = ["2026-03-02", "2026-03-03", "2026-03-04"]
    result = mean_hac({"metric": "synthetic paired error", "unit": "synthetic",
                       "frequency": "qualified_session", "calendar": days, "nlags": 1,
                       "observations": [{"date": d, "difference": v}
                                        for d, v in zip(days, [1, -1, 0])]})
    assert result["mean_difference"] == 0 and result["n"] == 3
    assert mean_abs_change([1, 4, 2]) == 2.5
    calendar = xshg_date("2026-03-02")
    output = {"synthetic_compute": "passed", "calendar_snapshot": calendar,
              "real_fits": 0, "resamplings_of_saved_financial_data": 0}
    if args.with_archives:
        from workflow_bridge import read_archived_run, prepare_workflow_input
        import lei_signal.research.workflow as workflow
        # Guard against accidental use of the real fit path during recovery.
        def prohibited(*a, **kw):
            raise AssertionError("recovery must not fit or execute a research contract")
        workflow.run_workflow = prohibited
        raw = root / "docs/experiments/raw/tsfresh-factor-validation-2026-10-02"
        files = [raw / ("run-" + name) / f for name in ("joint", "amplitude", "serial")
                 for f in ("contract.json", "preflight.json", "result.json", "receipt.json", "report.md")]
        journal = root / "docs/experiments/raw/research-workflow-ledgers-2026-09-29/b6ab4b610f391a532442a2ae/attempts.jsonl"
        files.append(journal)
        before = fingerprint(files)
        summaries = []
        for name in ("joint", "amplitude", "serial"):
            contract, predictions, proof, source = read_archived_run(raw / ("run-" + name))
            ready, packet = prepare_workflow_input(contract, predictions, proof,
                baseline="B1", start="2025-01-02", end="2025-12-02")
            assert ready["status"] == "ready" and ready["planned_dates"] == 222
            assert ready["prediction_rows"] == 888 and packet is not None
            rejected, _ = prepare_workflow_input(contract, predictions, proof,
                baseline="B1", start="2025-01-02", end="2026-06-30")
            assert rejected["status"] == "not_applicable"
            summaries.append({"variant": name, "archive_receipt_matches": source["receipt_matches_archived_journal"],
                              "complete_period": ready, "full_period": rejected})
        assert fingerprint(files) == before
        output.update(archive_reading="passed", original_files_unchanged=True,
                      input_sha256=before, summaries=summaries)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
