"""Synthetic I/O probe only; never modifies implementation or frozen inputs."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location(
    "preflight_manifest_probe", ROOT / "scripts/check_research_input.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
base = Path(__file__).parent / "run-02"
out = base / "manifest-failure"
assert not out.exists(), "Probe output must be fresh"
original = module._write_json

def fail_manifest(path, value):
    if path.name == "manifest.json":
        raise OSError("SYNTHETIC manifest disk failure")
    return original(path, value)

result = {"synthetic": True, "scope": "manifest write failure only"}
with patch.object(module, "_write_json", fail_manifest):
    try:
        result["returned_exit"] = module.main([
            "--snapshot", str(base / "synthetic-snapshot"),
            "--start", "2026-06-01", "--end", "2026-06-02",
            "--use", "description", "--out", str(out),
        ])
    except OSError as exc:
        result["uncaught"] = str(exc)
result["manifest_exists"] = (out / "manifest.json").exists()
result["failed_marker_exists"] = (out / "FAILED.txt").exists()
partial = json.loads((out / "preflight.json").read_text())
result["partial_request_satisfied"] = partial["request_satisfied"]
original(base / "manifest-failure-summary.json", result)
print(json.dumps(result, indent=2))
