"""Small synthetic contract checks; never opens saved market panel."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pandas as pd

HERE = Path(__file__).resolve().parent
WORKTREE = HERE.parents[3]
MAIN = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
sys.path.insert(0, str(MAIN / "src"))
spec = importlib.util.spec_from_file_location("daily_weekly_opportunity", WORKTREE / "src/lei_signal/research/daily_weekly_opportunity.py")
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)
checks = {}


def check(name, condition):
    checks[name] = bool(condition)
    if not condition:
        raise AssertionError(name)


days = pd.date_range("2020-12-21", periods=130 * 7, freq="D")
raw_flags = {str(d.date()): {"is_trading_day": d.weekday() < 5} for d in days}
calendar = m.covered_calendar(raw_flags)
sessions = [d for d in days if calendar.is_trading_day(d)]
bars = [{"asset": a, "date": str(d.date()), "status": "quoted",
         "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0 + i / 10,
         "volume": 1.0} for a in m.ASSETS for i, d in enumerate(sessions)]
q = m.qualify_dates(bars, calendar, str(days[0].date()), str(days[-1].date()))
check("121 complete week qualification", q["status"] == "passed" and all(
    x["first_121_week_sunday"] == str(days[121 * 7 - 1].date()) for x in q["assets"].values()))

missing = [r for r in bars if not (r["asset"] == m.ASSETS[0] and r["date"] == str(sessions[100].date()))]
check("one missing open day rejected", m.qualify_dates(missing, calendar, str(days[0].date()), str(days[-1].date()))["status"] == "failed")
week = sessions[5 * 80:5 * 81]
missing_week = [r for r in bars if not (r["asset"] == m.ASSETS[0] and r["date"] in {str(d.date()) for d in week})]
check("whole open week rejected", m.qualify_dates(missing_week, calendar, str(days[0].date()), str(days[-1].date()))["status"] == "failed")
check("duplicate rejected", m.qualify_dates(bars + [bars[0]], calendar, str(days[0].date()), str(days[-1].date()))["status"] == "failed")
broken = [dict(r) for r in bars]
broken[0]["high"] = float("nan")
check("nonfinite rejected", m.qualify_dates(broken, calendar, str(days[0].date()), str(days[-1].date()))["status"] == "failed")
try:
    m.covered_calendar({k: v for k, v in raw_flags.items() if k != str(days[30].date())})
except ValueError:
    check("unknown natural date rejected", True)
else:
    check("unknown natural date rejected", False)

closed_flags = dict(raw_flags)
for d in pd.date_range(days[70], periods=7):
    closed_flags[str(d.date())] = {"is_trading_day": False}
closed_calendar = m.covered_calendar(closed_flags)
closed_sessions = {str(d.date()) for d in pd.date_range(days[70], periods=7)}
closed_bars = [r for r in bars if r["date"] not in closed_sessions]
closed_q = m.qualify_dates(closed_bars, closed_calendar, str(days[0].date()), str(days[-1].date()))
check("all-closed week has no bar", closed_q["status"] == "passed" and len(closed_q["all_closed_weeks"]) == 1)

daily = pd.DataFrame([r for r in bars if r["asset"] == m.ASSETS[0]]).set_index("date")
daily.index = pd.DatetimeIndex(daily.index)
f = m._features(daily)
check("seeded 120 EMA", pd.isna(f.ema120.iloc[118]) and f.ema120.iloc[119] == daily.close.iloc[:120].mean())
check("strict equality", m._features(daily.assign(close=100.0)).stage.iloc[-1] == 0)
weekly_120 = m.feature_rows(daily.loc[:days[120 * 7 - 1]], calendar)
check("120 weeks not ready", weekly_120[-1]["qualified"] is False)
weekly_121 = m.feature_rows(daily.loc[:days[121 * 7 - 1]], calendar)
check("121 weeks ready", weekly_121[-1]["qualified"] is True)
full = m.feature_rows(daily, calendar)
check("future append leaves prefix unchanged", full[:len(weekly_121)] == weekly_121)
check("partial tail excluded", all(r["observation_at"][:10] <= str(days[-1].date()) for r in full))
check("no target values in feature rows", all("R20_pct" not in r for r in full))
future_days = pd.date_range("2025-12-01", "2026-03-31")
future_calendar = m.covered_calendar({str(d.date()): {"is_trading_day": d.weekday() < 5} for d in future_days})
check("cross-phase target excluded", m.label_dates("2025-12-28T23:59:59+08:00", future_calendar) is None)
check("21 closes 20 intervals", m.label_dates("2026-01-04T23:59:59+08:00", future_calendar) == ("2026-01-05", "2026-02-02"))
down = m.label_values([100.0, 90.0] + [100.0] * 19)
check("hand-calculated down excursion", down["R20_pct"] == 0 and
      abs(down["MAE20_pct"] - 10) < 1e-12 and down["positive20"] is False)
gain = m.label_values([100.0] * 20 + [110.0])
check("hand-calculated 20 interval gain", abs(gain["R20_pct"] - 10) < 1e-12 and
      gain["MAE20_pct"] == 0 and gain["positive20"] is True)

same = [{"asset": "A", "phase": "P", "observation_at": str(i), "B1": 0,
         "X": x, "R20_pct": y} for x, y in ((0, 1), (0, 3), (1, 5), (1, 7)) for i in [x * 10 + y]]
same += [{"asset": "A", "phase": "P", "observation_at": "20", "B1": 1,
          "X": 1, "R20_pct": 9}]
cell = m.effect_cells(same)["A|P"]
check("unsupported category blocks full denominator", cell["full_delta_pct_points"] is None and
      cell["cells"][0]["weight"] == 4 / 5 and cell["cells"][0]["delta_pct_points"] == 4)
support_rows = [{**r, "qualified": True, "label_dates": ("2026-01-05", "2026-02-02")} for r in same]
check("feature-only support rejects thin category", m.support_cells(support_rows)["A|P"]["unsupported_stages"] == [1])
effect_rows = [{**r, "MAE20_pct": 0.0, "positive20": r["R20_pct"] > 0,
                "weekly_sma120_direction": 1, "weekly_ema120_direction": 1} for r in same]
check("effect preserves counterexamples", m.describe_effect(effect_rows)["asset_phase"]["A|P"]["B0"]["all"]["N"] == 5)

(HERE / "synthetic-checks.json").write_text(json.dumps({"status": "passed", "checks": checks}, indent=2))
print(json.dumps({"status": "passed", "count": len(checks)}))
