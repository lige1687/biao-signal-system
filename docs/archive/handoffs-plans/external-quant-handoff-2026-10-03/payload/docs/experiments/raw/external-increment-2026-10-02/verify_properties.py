"""Record a finite engineering attempt; run with bytecode/plugin autoload disabled."""
import hashlib
import json
import os
import sys
import time
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RAW = Path(__file__).resolve().parent
os.environ["HYPOTHESIS_STORAGE_DIRECTORY"] = str(
    ROOT / "logs/external-increment-2026-10-02/hypothesis")
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
sys.path.insert(0, str(ROOT / "src"))
import pytest  # noqa: E402 -- configure storage and plugin discovery before importing pytest


class Capture:
    def __init__(self):
        self.outcomes = []
        self.modules = []

    def pytest_collection_modifyitems(self, items):
        self.modules = list({item.module for item in items})

    def pytest_runtest_logreport(self, report):
        if report.when == "call" or report.failed or report.skipped:
            self.outcomes.append({"nodeid": report.nodeid, "phase": report.when,
                                  "outcome": report.outcome,
                                  "detail": str(report.longrepr) if report.failed else None})


manifest = json.loads((RAW / "manifest.json").read_text())
entry = manifest["tests"][-1]
attempt = entry["batch"]
out = RAW / f"attempt-{attempt}.json"
if out.exists():
    raise SystemExit("preserve previous result; register a new allowed attempt first")
entry["status"] = "running"
manifest["budget"]["test_batches_used"] += 1
(RAW / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n")
target = ROOT / "tests/unit/test_research_property_checks.py"
started = time.monotonic()
capture = Capture()
code = pytest.main(["-q", str(target), "-p", "no:cacheprovider", "--tb=short"], plugins=[capture])
result = {"exit_code": int(code), "elapsed_seconds": time.monotonic()-started,
          "hypothesis_version": version("hypothesis"), "outcomes": capture.outcomes,
          "generated_calls": {}, "intentional_control": {},
          "test_code_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
          "scope": "synthetic demonstration adapter only; "
                   "no factor or financial effectiveness result"}
for module in capture.modules:
    result["generated_calls"].update(dict(getattr(module, "RUN_COUNTS", {})))
    result["intentional_control"].update(getattr(module, "CONTROL", {}))
passed = sum(r["outcome"] == "passed" for r in capture.outcomes)
result["accepted"] = code == 0 and passed == 3
out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n")
entry.update(status="passed" if result["accepted"] else "failed", result=out.name)
(RAW / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n")
print(json.dumps(result, ensure_ascii=False))
raise SystemExit(0 if result["accepted"] else 1)
