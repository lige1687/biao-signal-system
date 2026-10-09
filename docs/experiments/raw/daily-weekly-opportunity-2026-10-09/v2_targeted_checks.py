"""Review-failure regressions only; synthetic inputs and no real stage run."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile

import pandas as pd

HERE = Path(__file__).resolve().parent
WORKTREE = HERE.parents[3]
MAIN = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
sys.path.insert(0, str(MAIN / "src"))


def module_at(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


m = module_at("daily_weekly_opportunity", WORKTREE / "src/lei_signal/research/daily_weekly_opportunity.py")
runner = module_at("daily_weekly_guarded_runner", HERE / "guarded_runner.py")
checks = {}


def check(name, okay):
    checks[name] = bool(okay)
    if not okay:
        raise AssertionError(name)


days = pd.date_range("2026-06-22", "2026-06-30")
cal = m.covered_calendar({str(d.date()): {"is_trading_day": d.weekday() < 5} for d in days})
sessions = [d for d in days if cal.is_trading_day(d)]
bars = [{"asset": asset, "date": str(d.date()), "status": "quoted", "action_known": True,
         "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1.0}
        for asset in m.ASSETS for d in sessions]
tail_missing = [r for r in bars if not (r["asset"] == m.ASSETS[0] and r["date"] == "2026-06-30")]
q = m.qualify_dates(tail_missing, cal, "2026-06-22", "2026-06-30")
check("missing open day in incomplete tail named", "missing declared session: 2026-06-30" in
      q["assets"][m.ASSETS[0]]["issues"])
unknown = [dict(r) for r in bars]
unknown[0]["action_known"] = False
q = m.qualify_dates(unknown, cal, "2026-06-22", "2026-06-30")
check("action unknown named", "action unknown: 2026-06-22" in
      q["assets"][m.ASSETS[0]]["issues"])

long_days = pd.date_range("2020-12-21", periods=123 * 7, freq="D")
long_cal = m.covered_calendar({str(d.date()): {"is_trading_day": d.weekday() < 5} for d in long_days})
traded = [d for d in long_days if long_cal.is_trading_day(d)]
cutoff = long_days[122 * 7 + 2]
daily = pd.DataFrame({"open": 100.0, "high": 101.0, "low": 99.0,
                      "close": [100 + i / 100 for i in range(sum(d <= cutoff for d in traded))],
                      "volume": 1.0}, index=pd.DatetimeIndex([d for d in traded if d <= cutoff]))
features = m.feature_rows(daily, long_cal)
check("122 complete weeks plus three days preserves 122", len(features) == 122 and
      features[-1]["observation_at"][:10] == str(long_days[122 * 7 - 1].date()))

rows = []
for asset in m.ASSETS:
    for i, sunday in enumerate(("2025-01-05", "2025-01-12", "2025-01-19")):
        rows.append({"asset": asset, "phase": "eval_2025", "observation_at": sunday,
                     "qualified": True, "B1": 0, "X": (0, 1, 0)[i],
                     "label_dates": (("2025-01-06", "2025-02-03"),
                                     ("2025-01-13", "2025-02-10"),
                                     ("2025-01-20", "2025-02-17"))[i]})
rows.extend([{"asset": m.ASSETS[0], "phase": "eval_2025", "observation_at": "2025-01-26",
              "qualified": False, "B1": None, "X": None, "label_dates": None},
             {"asset": m.ASSETS[0], "phase": "eval_2025", "observation_at": "2025-12-28",
              "qualified": True, "B1": 0, "X": 1, "label_dates": None}])
support = m.support_cells(rows)
check("all eight fixed groups retained", len(support) == 8 and
      support[f"{m.ASSETS[0]}|eval_2026H1"]["N"] == 0)
g = support[f"{m.ASSETS[0]}|eval_2025"]
check("original denominator and exclusions", g["scheduled_N"] == 5 and g["N"] == 3 and
      g["excluded_pre_warmup_N"] == 1 and g["excluded_unmatured_date_N"] == 1)
check("state runs and common dates", g["state_runs_X0"] == 2 and
      g["state_runs_X1"] == 1 and g["shared_four_etf_review_dates"] == 3)
check("date-only overlap count", g["pairwise_date_windows"] == 3 and
      g["overlapping_date_window_pairs"] == 3)

check("one fixed budget marker across release routes",
      runner.budget_marker_path("features").name == runner.digest(runner.CONTRACT) + "-features.json")
fake = {"external_mount": str(HERE), "external_device": HERE.stat().st_dev,
        "run_directory": str(HERE / "never-create/task/run"),
        "output": str(HERE / "never-create/task/run/result")}
try:
    runner.open_external_output(fake)
except RuntimeError:
    check("nonmount cannot create output directories", not (HERE / "never-create").exists())
else:
    check("nonmount cannot create output directories", False)

if runner.DATE_RECEIPT.is_file():
    release = {"status": "released", "stage": "features", "attempt_id": "synthetic-only",
               "runner_sha256": runner.digest(runner.__file__), "module_sha256": runner.digest(runner.MODULE),
               "closure_sha256": runner.digest(runner.CLOSURE), "contract_sha256": runner.digest(runner.CONTRACT),
               "source_bindings_sha256": runner.digest(runner.SOURCE_BINDINGS),
               "amendment_sha256": runner.digest(runner.AMENDMENT),
               "date_receipt_sha256": "incorrect"}
    with tempfile.TemporaryDirectory(dir=HERE) as temp:
        release_path = Path(temp) / "release.json"
        release_path.write_text(json.dumps(release))
        try:
            runner.guard_release(release_path, "features")
        except ValueError as exc:
            check("date receipt release hash blocks before budget", "date qualification" in str(exc)
                  and not runner.budget_marker_path("features").exists())
        else:
            check("date receipt release hash blocks before budget", False)

(HERE / "v2-targeted-checks.json").write_text(json.dumps({"status": "passed", "checks": checks}, indent=2) + "\n")
print(json.dumps({"status": "passed", "count": len(checks)}))
