"""Bounded source counterexample and exact installed reference examples; no network."""
import ast
import hashlib
import json
import re
from pathlib import Path
from statistics import mean

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[4]
RAW = Path(__file__).resolve().parent
checks = []


def check(name, actual, expected):
    passed = actual == expected
    checks.append({"name": name, "actual": actual, "expected": expected, "passed": passed})
    if not passed:
        raise AssertionError(name)


def example(path):
    code = re.findall(r"```python\n(.*?)```", path.read_text(), flags=re.S)
    namespace = {}
    for block in code:
        exec(compile(block, str(path), "exec"), namespace)
    return namespace


source = RAW / "reviewed/validation/purging-embargo/SKILL.md"
block = next(b for b in re.findall(r"```python\n(.*?)```", source.read_text(), re.S)
             if "def purged_split" in b)
tree = ast.parse(block)
function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "purged_split")
namespace = {"np": np}
exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), "exec"), namespace)
train, test = namespace["purged_split"](500, 100, 100, 111, 5, 2)
future = train[train >= 111]
check("upstream_example_total_training_rows", len(train), 482)
check("upstream_future_training_rows", len(future), 387)
check("upstream_training_after_test_includes_last_row", int(train.max()), 499)
check("upstream_past_only_part", train[train < 100].tolist(), list(range(95)))

skill_root = ROOT / ".agents/skills"
availability = example(skill_root / "lei-data-availability/references/cases.md")
known = availability["known_version"]
events = availability["events"]
check("before_initial_publication", known(events, "2026-04-20T15:00:00+08:00"), None)
check("initial_version_available", known(events, "2026-04-21T15:00:00+08:00")["value"], 10)
check("revised_version_available_later", known(events, "2026-05-11T15:00:00+08:00")["value"], 12)
check("future_revision_does_not_change_past", known(events[:1], "2026-04-21T15:00:00+08:00"),
      known(events, "2026-04-21T15:00:00+08:00"))
try:
    known(events, "2026-04-21T15:00:00")
except ValueError:
    no_timezone_rejected = True
else:
    no_timezone_rejected = False
check("unknown_timezone_rejected", no_timezone_rejected, True)

validation = example(skill_root / "lei-causal-validation/references/cases.md")
date_pairs = [("2026-04-01", "2026-04-03"), ("2026-04-02", "2026-04-06"),
              ("2026-04-06", "2026-04-08"), ("2026-04-07", "2026-04-09"),
              ("2026-04-08", "2026-04-10")]
rows = [{"asset": asset, "date": d, "label_end": end} for d, end in date_pairs
        for asset in ("ETF-A", "ETF-B")]
training = validation["training_rows"](rows, "2026-04-03", "2026-04-06")
evaluation = validation["evaluation_rows"](rows, "2026-04-06", "2026-04-07")
check("mature_training_observations", [(r["asset"], r["date"]) for r in training],
      [("ETF-A", "2026-04-01"), ("ETF-B", "2026-04-01")])
check("whole_date_evaluation", [(r["asset"], r["date"]) for r in evaluation],
      [("ETF-A", "2026-04-06"), ("ETF-B", "2026-04-06"),
       ("ETF-A", "2026-04-07"), ("ETF-B", "2026-04-07")])
check("training_and_evaluation_dates_disjoint", bool({r["date"] for r in training} &
      {r["date"] for r in evaluation}), False)
check("train_statistics_are_unchanged_when_future_values_append", mean([1, 3]), 2)
check("contamination_counterexample", round(mean([1, 3, 1000]), 4), 334.6667)

for name in ("lei-data-availability", "lei-causal-validation"):
    skill = skill_root / name / "SKILL.md"
    frontmatter = yaml.safe_load(skill.read_text().split("---", 2)[1])
    check(name + ":matching_name", frontmatter["name"], name)
    check(name + ":description_exists", isinstance(frontmatter["description"], str)
          and bool(frontmatter["description"]), True)
    for target in re.findall(r"\]\(([^)]+)\)", skill.read_text()):
        check(name + ":link:" + target, (skill.parent / target).is_file(), True)

results = {"checks": checks, "passed": sum(c["passed"] for c in checks),
           "total": len(checks), "upstream_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
           "scope": "模拟例和安装结构核验；未运行真实因子研究，未测自动选择或端到端Codex行为"}
(RAW / "case-checks.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
manifest = json.loads((RAW / "manifest.json").read_text())
manifest["tests"][0].update(status="passed", result="case-checks.json", checks=len(checks))
(RAW / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"passed": results["passed"], "total": results["total"],
                  "future_training_rows_in_upstream_example": len(future)}, ensure_ascii=False))
