"""T4 合成时点测试（人工合成时间戳，不是行情）。每例写明人工标准答案，运行后核对并写 cases-output.json。

另做两项生产对照（只调用生产函数，不改源码）：
  P1 aggregate_weekly 在节假日短周：默认日历 vs 注入日历；
  P2 aggregate_weekly 周五盘中：最后一根日线尚未收盘时，周线是否被当成已完成。
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path[:0] = [str(HERE), str(REPO / "src")]

from lei_signal.data.bar_completeness import classify_a_share_bar  # noqa: E402
from lei_signal.data.calendar import weekday_calendar  # noqa: E402
from lei_signal.data.point_in_time import aggregate_weekly  # noqa: E402
from timing import Calendar, Exchange, Fact, decidable_at, execution, localize  # noqa: E402

SH = ZoneInfo("Asia/Shanghai")
EX = Exchange()
D = dt.date
# 合成日历：覆盖 2026-09-28（一）..2026-10-18（日）；10-01..10-09 休市（人工设定，不代表真实安排）
#   → 9/28—9/30 为三天短周；10/5—10/9 整周休市；10/12—10/16 为普通周
HOL = {D(2026, 10, i) for i in range(1, 10)}
DAYS = [D(2026, 9, 28) + dt.timedelta(days=i) for i in range(21)]
CAL = Calendar(frozenset(x for x in DAYS if x.weekday() < 5 and x not in HOL), D(2026, 9, 28), D(2026, 10, 18))


def t(d, hh, mm=0):
    return dt.datetime(d.year, d.month, d.day, hh, mm, tzinfo=SH)


def day_bar(d, available=None, **kw):
    return Fact(f"1d:{d}", "1d", t(d, 15), available, **kw)


def week_bar(d_last, available=None, **kw):
    return Fact(f"1w:{d_last}", "1w", t(d_last, 15) if d_last else None, available, **kw)


CASES = []


def case(name, got, want, note):
    CASES.append({"case": name, "got": got, "expected": want, "ok": got == want, "note": note})


# 1 普通周：周五收盘后周线可知；周五 14:59 不可知
fri = D(2026, 10, 16)
wk = week_bar(CAL.last_trading_of_week(fri), available=t(fri, 15, 20))
case("1_normal_week_after_close", decidable_at(EX, CAL, [wk], t(fri, 15, 30))["status"], "decidable",
     "周线完成＝本周最后交易日收盘；来源 15:20 到达，15:30 可决定")
case("1b_normal_week_before_close", decidable_at(EX, CAL, [wk], t(fri, 14, 59))["status"], "not_yet",
     "周五盘中周线未完成")
# 2 节假日短周：9/28—9/30 三天，周三收盘即完成
short_last = CAL.last_trading_of_week(D(2026, 9, 28))
wk2 = week_bar(short_last, available=t(short_last, 15, 10))
case("2_holiday_short_week", [short_last.isoformat() if short_last else None, decidable_at(EX, CAL, [wk2], t(D(2026, 9, 30), 15, 30))["status"]],
     ["2026-09-30", "decidable"], "按注入日历，周三是本周最后交易日")
# 2b 整周休市：没有周线，不得用下一周补
case("2b_all_closed_week", CAL.last_trading_of_week(D(2026, 10, 5)), None, "10/5—10/9 整周休市：该周没有周线，不能用下一周补")
# 3 周内未完成：周三观察，本周周线不能参与
case("3_incomplete_week_midweek", decidable_at(EX, CAL, [wk], t(D(2026, 10, 14), 16))["status"], "not_yet",
     "周三收盘后本周仍未结束")
# 4 收盘后修订：日线 15:05 首发、18:00 修订；按观察时刻取版本
rev = day_bar(D(2026, 10, 12), available=t(D(2026, 10, 12), 15, 5), revisions=[(t(D(2026, 10, 12), 18), "v1")])
case("4_post_close_revision", [decidable_at(EX, CAL, [rev], t(D(2026, 10, 12), 16))["versions"]["1d:2026-10-12"],
                               decidable_at(EX, CAL, [rev], t(D(2026, 10, 12), 19))["versions"]["1d:2026-10-12"]],
     ["v0", "v1"], "16:00 的决定只能用首发版本；19:00 的决定用修订版本；两者都保留")
# 5 午间休市：11:30 的小时线在 11:30 完成，下一允许成交在 13:00
h1130 = Fact("60m:10-12 11:30", "60m", t(D(2026, 10, 12), 11, 30), t(D(2026, 10, 12), 11, 31))
dec = decidable_at(EX, CAL, [h1130], t(D(2026, 10, 12), 11, 45))
from timing import next_open  # noqa: E402
case("5_lunch_break", [dec["status"], next_open(EX, CAL, t(D(2026, 10, 12), 11, 31), intraday=True).isoformat()],
     ["decidable", "2026-10-12T13:00:00+08:00"], "午休期间可决定但不能成交")
# 6 末根小时未结束：14:30 观察，15:00 那根不可用
h1500 = Fact("60m:10-12 15:00", "60m", t(D(2026, 10, 12), 15), t(D(2026, 10, 12), 15, 1))
case("6_last_hour_unfinished", decidable_at(EX, CAL, [h1500], t(D(2026, 10, 12), 14, 30))["status"], "not_yet",
     "最后一根小时线 15:00 才完成")
# 7 日线已触发、小时确认晚到：日线 10-12 收盘触发；小时确认 10-13 10:30 完成 → 决定在 10-13 10:30，
#   日线参考执行（下一交易日开盘 10-13 09:30）已早于确认，不能用来执行“需要小时确认”的版本
day_sig = day_bar(D(2026, 10, 12), available=t(D(2026, 10, 12), 15, 5))
h_conf = Fact("60m:10-13 10:30", "60m", t(D(2026, 10, 13), 10, 30), t(D(2026, 10, 13), 10, 31))
dd = decidable_at(EX, CAL, [day_sig, h_conf], t(D(2026, 10, 13), 11))
case("7_hourly_confirmation_late", [dd["status"], dd["at"],
                                    next_open(EX, CAL, dt.datetime.fromisoformat(dd["at"]), intraday=True).isoformat()],
     ["decidable", "2026-10-13T10:31:00+08:00", "2026-10-13T10:31:00+08:00"],
     "决定时刻取较晚的输入；执行从确认之后才可能，不是日线参考的 09:30")
# 8 资料缺失：小时数据未接入 → unknown，不是“没有确认”
missing = Fact("60m:unconnected", "60m", None, missing=True)
case("8_missing_hourly", decidable_at(EX, CAL, [day_sig, missing], t(D(2026, 10, 13), 16))["status"], "unknown",
     "小时资料未接入：结论 unknown，不能写成“小时没转强”")
# 8b 日历未覆盖：覆盖范围外的周不能判断完成
case("8b_calendar_uncovered", CAL.last_trading_of_week(D(2026, 10, 19)), None, "日历只到 10-18：下一周完成时刻 unknown")
# 9 周末 / 月末执行节奏：周二的日线信号在周末节奏下要等周五收盘复核，下周一开盘执行
ex_w = execution(EX, CAL, t(D(2026, 10, 13), 15, 5), "weekly_action")
ex_d = execution(EX, CAL, t(D(2026, 10, 13), 15, 5), "daily_reference")
case("9_weekly_cadence", [ex_d["execute_at"], ex_w["evaluate_at"], ex_w["execute_at"]],
     ["2026-10-14T09:30:00+08:00", "2026-10-16T15:00:00+08:00", None],
     "日线参考 10-14 开盘执行；周末节奏 10-16 收盘复核；下一开盘在日历覆盖外 → unknown，不猜 10-19")

# ---- 生产对照 ----
idx = pd.DatetimeIndex([pd.Timestamp(x) for x in DAYS if x in CAL.trading])
bars = pd.DataFrame({"open": 1.0, "high": 1.1, "low": 0.9, "close": 1.0, "volume": 1.0}, index=idx)
upto_wed = bars.loc[:"2026-09-30"]
w_default = aggregate_weekly(upto_wed)
w_injected = aggregate_weekly(upto_wed, calendar=weekday_calendar(HOL))
prod = {
    "P1_short_week_default_calendar_weeks": len(w_default),
    "P1_short_week_injected_calendar_weeks": len(w_injected),
    "P1_injected_available_date": [x.date().isoformat() for x in w_injected.index],
}
upto_fri = bars.loc[:"2026-10-16"]
w_fri = aggregate_weekly(upto_fri, calendar=weekday_calendar(HOL))
prod["P2_friday_bar_present_weeks"] = [x.date().isoformat() for x in w_fri.index]
prod["P2_bar_completeness_at_14_00"] = classify_a_share_bar(D(2026, 10, 16), t(D(2026, 10, 16), 14),
                                                            calendar=weekday_calendar(HOL))
prod["P3_bar_completeness_naive_observed_at"] = classify_a_share_bar(
    D(2026, 10, 16), dt.datetime(2026, 10, 16, 7, 30), calendar=weekday_calendar(HOL))
prod["_reading"] = {
    "P1": "默认日历（只认周一至周五）在短周周三收盘后不承认周线完成，要等下一根日线；注入日历则当天完成。",
    "P2": "aggregate_weekly 只看日期：只要周五那一行存在，就把本周当成已完成，不管该行是否已收盘（T5 K1 已复现，此处只作时点合同依据）。",
    "P3": "classify_a_share_bar 把不带时区的观测时刻当作上海时间；若调用方传入的是 UTC 07:30（=上海 15:30），会被误判为盘中。",
}

expected_prod = {"P1_short_week_default_calendar_weeks": 0, "P1_short_week_injected_calendar_weeks": 1,
                 "P2_bar_completeness_at_14_00": "partial", "P3_bar_completeness_naive_observed_at": "partial"}
prod_ok = all(prod[k] == v for k, v in expected_prod.items()) and "2026-10-16" in prod["P2_friday_bar_present_weeks"]

out = {"cases": CASES, "production_checks": prod, "production_expected": expected_prod, "production_ok": prod_ok,
       "_note": "合成日历与合成时间戳；休市日为人工设定，不代表真实交易所安排。"}
(HERE / "cases-output.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
fails = [c["case"] for c in CASES if not c["ok"]] + ([] if prod_ok else ["production_checks"])
for c in CASES:
    print(c["case"], c["ok"], c["got"])
print("production:", {k: v for k, v in prod.items() if not k.startswith("_")})
print("FAILURES:", fails or "none")
sys.exit(1 if fails else 0)
