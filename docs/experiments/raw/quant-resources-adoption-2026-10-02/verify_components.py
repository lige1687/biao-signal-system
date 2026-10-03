"""Independent arithmetic, official schedule, exact borrowed source, and real CLI checks."""
import ast
import copy
from datetime import date, timedelta
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[4]
RAW = Path(__file__).resolve().parent
SKILL = ROOT / ".agents/skills/lei-quant-tools"
sys.path.insert(0, str(SKILL / "scripts"))
spec = importlib.util.spec_from_file_location("quant_tools", SKILL / "scripts/quant_tools.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
checks = []


def check(name, actual, expected):
    passed = abs(actual - expected) < 1e-12 if isinstance(expected, float) else actual == expected
    checks.append({"name": name, "actual": actual, "expected": expected, "passed": passed})
    if not passed:
        raise AssertionError(name)


def reject(name, payload):
    try:
        module.mean_hac(payload)
    except (ValueError, KeyError, TypeError):
        refused = True
    else:
        refused = False
    check(name, refused, True)


calendar = ["2026-03-02", "2026-03-03", "2026-03-04", "2026-03-05", "2026-03-06", "2026-03-09"]
packet = {"metric": "synthetic paired difference", "unit": "test unit", "frequency": "qualified_session",
          "calendar": calendar, "observations": [{"date": d, "difference": v} for d, v in
                                                   zip(calendar, [1, 1, 1, -1, -1, -1])], "nlags": 2}
positive = module.mean_hac(packet)
# Independent arithmetic: sum squares=6, lag1 products=3, lag2 products=0.
# Bartlett weights 2/3 and 1/3 -> (6 + 2*(2/3*3))/36 = 10/36.
check("positive_dependency_mean", positive["mean_difference"], 0.0)
check("positive_dependency_variance", positive["mean_variance"], 10 / 36)
negative_packet = copy.deepcopy(packet)
for row, value in zip(negative_packet["observations"], [1, -1, 1, -1, 1, -1]):
    row["difference"] = value
negative = module.mean_hac(negative_packet)
# Independent arithmetic: lag1=-5, lag2=4 -> (6 + 2*(-10/3+4/3))/36 = 2/36.
check("negative_dependency_variance", negative["mean_variance"], 2 / 36)
lag_zero = {**packet, "nlags": 0}
check("zero_lag_variance", module.mean_hac(lag_zero)["mean_variance"], 6 / 36)
constant = copy.deepcopy(packet)
for row in constant["observations"]:
    row["difference"] = 7
constant_result = module.mean_hac(constant)
check("constant_series_zero_variance", constant_result["mean_variance"], 0.0)
check("constant_series_warning", "does not establish certainty" in constant_result["warning"], True)
bad = copy.deepcopy(packet);bad["observations"].pop(2);reject("missing_planned_date_rejected", bad)
bad = copy.deepcopy(packet);bad["observations"][1]["date"] = calendar[0];reject("duplicate_date_rejected", bad)
bad = copy.deepcopy(packet);bad["observations"][0]["difference"] = None;reject("missing_value_rejected", bad)
bad = copy.deepcopy(packet);bad["observations"][0]["difference"] = float("inf");reject("infinite_value_rejected", bad)
reject("automatic_lag_rejected", {**packet, "nlags": None})
reject("boolean_lag_rejected", {**packet, "nlags": True})
reject("lag_beyond_series_rejected", {**packet, "nlags": 6})

# Source-level exactness: both selected functions are unchanged from the downloaded wheel.
upstream = ast.parse((RAW / "sandwich_covariance.py").read_text())
borrowed = ast.parse((SKILL / "scripts/statsmodels_hac.py").read_text())
for name in ("weights_bartlett", "S_hac_simple"):
    left = next(n for n in upstream.body if isinstance(n, ast.FunctionDef) and n.name == name)
    right = next(n for n in borrowed.body if isinstance(n, ast.FunctionDef) and n.name == name)
    check("unchanged_upstream_function:" + name, ast.dump(left), ast.dump(right))

# Independently transcribed seven closure ranges from SSE announcement 2025 no.45.
closure_ranges = [("2026-01-01", "2026-01-03"), ("2026-02-15", "2026-02-23"),
                  ("2026-04-04", "2026-04-06"), ("2026-05-01", "2026-05-05"),
                  ("2026-06-19", "2026-06-21"), ("2026-09-25", "2026-09-27"),
                  ("2026-10-01", "2026-10-07")]
official_weekday_closures = set()
for start, end in closure_ranges:
    d = date.fromisoformat(start)
    while d <= date.fromisoformat(end):
        if d.weekday() < 5:
            official_weekday_closures.add(d.isoformat())
        d += timedelta(days=1)
snapshot = json.loads((SKILL / "references/xshg-2026.json").read_text())
check("borrowed_2026_holidays_match_official_notice", sorted(snapshot["holidays"]), sorted(official_weekday_closures))
check("weekday_holiday_count", len(official_weekday_closures), 19)
all_days = [date(2026, 1, 1) + timedelta(days=i) for i in range(365)]
expected_open = [d.isoformat() for d in all_days if d.weekday() < 5 and d.isoformat() not in official_weekday_closures]
actual_open = [d.isoformat() for d in all_days if module.xshg_date(d.isoformat())["status"] == "scheduled_open"]
check("all_365_dates_match_annual_schedule", actual_open, expected_open)
check("annual_scheduled_open_days", len(actual_open), 242)
check("outside_year_unknown", module.xshg_date("2027-01-04")["status"], "unknown")
check("current_holiday_schedule", module.xshg_date("2026-10-02")["status"], "scheduled_closed")
check("no_arrival_claim", module.xshg_date("2026-10-02")["historical_arrival"], "unknown")

(RAW / "synthetic-input.json").write_text(json.dumps(packet, indent=2) + "\n")
cli = subprocess.run([sys.executable, str(SKILL / "scripts/quant_tools.py"), "mean-hac",
                      str(RAW / "synthetic-input.json")], capture_output=True, text=True)
check("real_cli_exit", cli.returncode, 0)
check("real_cli_result", json.loads(cli.stdout)["mean_variance"], 10 / 36)
(RAW / "synthetic-output.json").write_text(cli.stdout)
cli_calendar = subprocess.run([sys.executable, str(SKILL / "scripts/quant_tools.py"), "xshg-date",
                               "2026-10-02"], capture_output=True, text=True)
check("calendar_cli_exit", cli_calendar.returncode, 0)
check("calendar_cli_result", json.loads(cli_calendar.stdout)["status"], "scheduled_closed")
(RAW / "calendar-output.json").write_text(cli_calendar.stdout)
front = yaml.safe_load((SKILL / "SKILL.md").read_text().split("---", 2)[1])
check("skill_name", front["name"], "lei-quant-tools")

results = {"passed": sum(c["passed"] for c in checks), "total": len(checks), "checks": checks,
           "numerical_results": {"positive_dependency": positive, "negative_dependency": negative},
           "coverage": "one synthetic batch; 365 annual schedule dates; no market-performance experiment"}
(RAW / "checks.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
manifest = json.loads((RAW / "manifest.json").read_text())
manifest["tests"][0].update(status="passed", result="checks.json", checks=len(checks))
manifest["runtime"] = {"python": sys.version, "numpy": module.np.__version__, "added_dependencies": [],
                       "full_libraries_installed": False}
(RAW / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"passed": results["passed"], "total": results["total"], "scheduled_open_days": len(actual_open)}, ensure_ascii=False))
