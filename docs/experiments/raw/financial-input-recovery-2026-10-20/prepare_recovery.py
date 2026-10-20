"""Save current bounded recovery anchors, without changing any archived input."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent
ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
sys.path.insert(0, str(ROOT / "src"))
from lei_signal.research.output_storage import plan_output


def save(name, data):
    with (HERE / name).open("x") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


stamp = datetime.now().astimezone().isoformat()
expected = {
    "/Users/yongbiaoli/Desktop/lei signal doc/LEI 技术交易体系.md":
        "df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20",
    "/Users/yongbiaoli/Desktop/lei signal doc/LEI 技术实现.md":
        "85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903",
}
assert all(sha(path) == digest for path, digest in expected.items())
save("strategy-anchors.json", {"checked_at": stamp, "sources": expected,
                              "layer": "research source qualification only"})
plan = plan_output(ROOT, "financial-input-recovery-20261020", 128 * 1024**2,
                   internal_bytes=800 * 1024)
save("storage-plan.json", plan)
command = [sys.executable, "-m", "lei_signal.research.preparation",
           "--reference-ref", "reference.osap.catalog@1.1.0"]
import os
run = subprocess.run(command, cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "src"),
                                          "PYTHONDONTWRITEBYTECODE": "1"},
                     text=True, capture_output=True, check=False)
save("osap-preparation-recheck.json", {
    "checked_at": stamp, "exit_code": run.returncode,
    "result": json.loads(run.stdout) if run.returncode == 0 else None,
    "stderr": run.stderr,
    "supersedes": "2026-10-20 11:14 retrieval format blocker; original owner repaired at 11:30",
})
assert run.returncode == 0
parsed = json.loads(run.stdout)
assert not parsed["issues"] and parsed["research_references"][0]["ref"] == "reference.osap.catalog@1.1.0"
with urlopen("http://localhost:5188/api/upgrades", timeout=10) as response:
    items = json.load(response)["items"]
goal = next(item for item in items if item["id"] == "okr-8830a1f1ec4f")
save("goal-before.json", {key: goal.get(key) for key in
                         ("id", "version", "title", "status", "milestones", "next_action")})
save("method-sources.json", {
    "read_at": stamp,
    "unique_pages": 3, "web_operations": 5, "max_operations": 6,
    "sources": [
        {"product": "Microsoft Qlib", "source_date": "current documentation retrieved 2026-10-20",
         "url": "https://qlib.readthedocs.io/en/latest/advanced/PIT.html",
         "observation": "Financial period and publication date are separate; revisions retained as occurrences.",
         "application": "Preserve original and corrected values with publication time; never replace historic observations with latest.",
         "limit": "A storage format does not establish source completeness or accounting field correctness."},
        {"product": "Microsoft RD-Agent", "source_date": "repository README retrieved 2026-10-20",
         "url": "https://github.com/microsoft/RD-Agent",
         "observation": "Research hypotheses and development execution form a feedback loop.",
         "application": "Controller chooses the unresolved question; Luna prepares evidence; controller independently accepts or rejects; quantify resulting qualification changes.",
         "limit": "Repository performance claims were not independently verified; no framework migration or installation."},
        {"product": "Pandera", "source_date": "current documentation retrieved 2026-10-20",
         "url": "https://pandera.readthedocs.io/en/stable/lazy_validation.html",
         "observation": "lazy=True collects multiple schema/data failures with individual failure_cases.",
         "application": "Keep simultaneous blockers per company-month; clearing one notice must not silently clear other field or source failures.",
         "limit": "This stage uses the existing selector's explicit blocker lists; it does not claim Pandera was installed or that automatic repairs are safe."},
    ],
    "new_original_data_downloads": 0, "new_market_effects": 0,
})
contract = json.loads((HERE / "sol-contract-v2.json").read_text())
contract["mission"] = "Inspect exact saved stock-level fields for a defensive diagnostic and select original value-source pages; no market effect or network"
contract["write_paths"] = [str(HERE / "local-feasibility.json").lstrip("/")]
contract["expected_outputs"] = ["local-feasibility.json with exact columns, hashes, original evidence paths and missing fields"]
save("sol-feasibility-contract.json", contract)
print(json.dumps({"output": plan["output"], "osap_lookup": "passed",
                  "goal_version": goal["version"]}, ensure_ascii=False))
