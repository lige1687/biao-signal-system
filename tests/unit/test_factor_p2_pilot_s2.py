"""S2 试点A合成验收测试（合同 §4 最低测试集四类）。

覆盖：
(a) 资格与输出边界：conditional 未承担拒绝、BLOCK 不可承担、
    ranking=conditional+research_signal=blocked 时请求 target 依赖统计
    （Rank IC/分组/差额）必须 BLOCK、删合同必需字段明确失败；
(b) 数值与时间正确性：同向/反向/并列/常量、月份边界、尾部缺失、
    样本不足返回缺失不返回 0、行序不变性；
(c) 样本去向完整性：预期→特征可算→目标可算→共同样本逐步对齐、
    每步互斥主因；
(d) 独立校验可否定错误：改坏诊断数值/样本归属/时间配对必须被发现，
    重算哈希不能蒙混（校验器从原始输入复算，不看任何自报哈希）。

合成输入全部手造（虚构产品/月份/价格），不读取任何冻结真实输入。
"""

from __future__ import annotations

import copy
import json
import math
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from lei_signal.research import data_quality as dq
from lei_signal.research import momentum_prototype as mp
from lei_signal.research.trading_calendar import TradingCalendar

PILOT_DIR = Path(__file__).resolve().parents[2] / "docs/experiments/raw/factor-p2-pilot-s2-2026-09-19"
sys.path.insert(0, str(PILOT_DIR))

import pilot  # noqa: E402
import reference_check  # noqa: E402


# ---------------------------------------------------------------- 合成输入

def month_range(start_ym: str, end_ym: str) -> list[str]:
    y, m = (int(x) for x in start_ym.split("-"))
    ey, em = (int(x) for x in end_ym.split("-"))
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def make_calendar_payload(months: list[str]) -> dict:
    import calendar as cal
    days: dict[str, dict] = {}
    for ym in months:
        y, m = (int(x) for x in ym.split("-"))
        for d in range(1, cal.monthrange(y, m)[1] + 1):
            dd = date(y, m, d)
            days[dd.isoformat()] = {
                "is_trading_day": dd.weekday() < 5,
                "source_flag": 1 if dd.weekday() < 5 else 0,
                "source_month": ym,
            }
    return {"days": days, "months_requested": list(months), "authority": "synthetic"}


CAL_MONTHS = month_range("2023-09", "2026-02")
CAL_PAYLOAD = make_calendar_payload(CAL_MONTHS)
CALENDAR = TradingCalendar(CAL_PAYLOAD)

EVAL_START, EVAL_END, TARGET_END = "2025-01-01", "2025-12-31", "2026-02-28"


def trading_days_between(payload: dict, start: str, end: str) -> list[str]:
    return sorted(d for d, r in payload["days"].items()
                  if r["is_trading_day"] and start <= d <= end)


ALL_TDAYS = trading_days_between(CAL_PAYLOAD, "2023-09-01", TARGET_END)

# 虚构产品：二次价格路径，保证逐月动量截面既非恒定也非全同。
COEFFS = {
    "SYN-A": (0.030, 0.00010), "SYN-B": (0.055, 0.00013),
    "SYN-C": (0.020, 0.00022), "SYN-D": (0.070, 0.00007),
    "SYN-E": (0.040, 0.00018), "SYN-F": (0.060, 0.00002),
    "SYN-GAPX": (0.050, 0.00011), "SYN-SHORT": (0.045, 0.00015),
}


def make_series(sym: str, days: list[str]) -> pd.Series:
    a, b = COEFFS[sym]
    idx = pd.DatetimeIndex(pd.to_datetime(days))
    return pd.Series([100.0 + a * i + b * i * i for i in range(len(days))], index=idx)


def make_indexes() -> dict[str, pd.Series]:
    indexes = {s: make_series(s, ALL_TDAYS) for s in COEFFS}
    # GAPX：2025-04 整月无报价 → 落在该月的 exit 端点缺失（目标不可算）。
    indexes["SYN-GAPX"] = indexes["SYN-GAPX"].drop(
        index=pd.DatetimeIndex(pd.to_datetime(
            [d for d in ALL_TDAYS if d.startswith("2025-04")])))
    # SHORT：2024-12 才开始，不足 253 条历史 → 动量不可算。
    short_days = [d for d in ALL_TDAYS if d >= "2024-12-01"]
    indexes["SYN-SHORT"] = make_series("SYN-SHORT", short_days)
    return indexes


def make_report(verdicts: dict, findings=()) -> dq.QualityReport:
    return dq.QualityReport(
        findings=tuple(findings),
        verdicts=tuple(dq.UseVerdict(u, v, ()) for u, v in verdicts.items()),
        counts={},
    )


PILOT_REPORT = make_report({
    "ranking": dq.CONDITIONAL, "research_signal": dq.CONDITIONAL,
})
BLOCKED_REPORT = make_report(
    {"ranking": dq.UNUSABLE, "research_signal": dq.UNUSABLE},
    findings=(dq.Finding(level=dq.BLOCK, code="syn_block",
                         message="BLOCK 级问题", affects_uses=("ranking",)),),
)


def run_ok(indexes=None):
    return pilot.run_pilot(
        indexes=indexes or make_indexes(), calendar=CALENDAR,
        quality_report=PILOT_REPORT,
        evaluation_start=EVAL_START, evaluation_end=EVAL_END,
        target_window_end=TARGET_END,
        ranking_acknowledge_conditional=True, target_use_approved=True)


N_MONTHS = 12


# ---------------------------------------------------- (a) 资格与输出边界

class TestQualificationBoundaries:
    def test_conditional_not_acknowledged_rejected(self):
        with pytest.raises(dq.UseNotPermitted):
            pilot.run_pilot(indexes=make_indexes(), calendar=CALENDAR,
                            quality_report=PILOT_REPORT,
                            evaluation_start=EVAL_START, evaluation_end=EVAL_END,
                            target_window_end=TARGET_END,
                            ranking_acknowledge_conditional=False,
                            target_use_approved=True)

    def test_block_level_cannot_be_assumed(self):
        # BLOCK 级：即使调用方 accept_structural 也一律拒绝（闸门无后门）。
        with pytest.raises(dq.UseNotPermitted):
            dq.require_use(BLOCKED_REPORT, "ranking", accept_structural=True)
        with pytest.raises(dq.UseNotPermitted):
            pilot.run_pilot(indexes=make_indexes(), calendar=CALENDAR,
                            quality_report=BLOCKED_REPORT,
                            evaluation_start=EVAL_START, evaluation_end=EVAL_END,
                            target_window_end=TARGET_END,
                            ranking_acknowledge_conditional=True,
                            target_use_approved=True)

    def test_protocol_misuse_target_stats_blocked(self):
        # ranking=conditional（已承担）+ research_signal=blocked：请求 target
        # 依赖统计（Rank IC/分组差额）必须整体 BLOCK，不得改称诊断统计绕过。
        blocked = make_report({"ranking": dq.CONDITIONAL,
                               "research_signal": dq.BLOCKED_VERDICT
                               if hasattr(dq, "BLOCKED_VERDICT") else "blocked"})
        with pytest.raises(dq.UseNotPermitted) as ei:
            pilot.run_pilot(indexes=make_indexes(), calendar=CALENDAR,
                            quality_report=blocked,
                            evaluation_start=EVAL_START, evaluation_end=EVAL_END,
                            target_window_end=TARGET_END,
                            ranking_acknowledge_conditional=True,
                            target_use_approved=False)
        assert "research_signal" in str(ei.value)
        assert "不得改称诊断统计" in str(ei.value)

    def test_missing_required_field_fails_without_default(self):
        base = dict(indexes=make_indexes(), calendar=CALENDAR,
                    quality_report=PILOT_REPORT, evaluation_start=EVAL_START,
                    evaluation_end=EVAL_END, target_window_end=TARGET_END,
                    ranking_acknowledge_conditional=True,
                    target_use_approved=True)
        with pytest.raises(TypeError):
            pilot.run_pilot(**{k: v for k, v in base.items() if k != "evaluation_end"})
        with pytest.raises(ValueError):
            pilot.run_pilot(**{**base, "indexes": {}})
        with pytest.raises(ValueError):
            pilot.run_pilot(**{**base, "quality_report": None})


# ------------------------------------------------ (b) 数值与时间正确性

class TestNumericAndTime:
    def test_rank_perfect_same_direction(self):
        frame = pd.DataFrame({"momentum": [1, 2, 3, 4, 5, 6],
                              "target": [10, 20, 30, 40, 50, 60]})
        assert mp.rank_diagnostic(frame)["value"] == pytest.approx(1.0)

    def test_rank_perfect_reverse(self):
        frame = pd.DataFrame({"momentum": [1, 2, 3, 4, 5, 6],
                              "target": [60, 50, 40, 30, 20, 10]})
        assert mp.rank_diagnostic(frame)["value"] == pytest.approx(-1.0)

    def test_rank_ties_average_ranks(self):
        # 手算：名次 m=[1,2.5,2.5,4]、t=[1,2,3,4]，Pearson=4.5/sqrt(22.5)。
        frame = pd.DataFrame({"momentum": [1, 2, 2, 3], "target": [1, 2, 3, 4]})
        assert mp.rank_diagnostic(frame)["value"] == pytest.approx(
            4.5 / math.sqrt(22.5))

    def test_rank_constant_returns_missing_not_zero(self):
        frame = pd.DataFrame({"momentum": [2, 2, 2, 2], "target": [1, 2, 3, 4]})
        out = mp.rank_diagnostic(frame)
        assert out["value"] is None and out["reason"] == "constant_rank"

    def test_rank_insufficient_pairs_returns_missing_not_zero(self):
        frame = pd.DataFrame({"momentum": [1, 2], "target": [1, 2]})
        out = mp.rank_diagnostic(frame)
        assert out["value"] is None and out["reason"] == "fewer_than_three_pairs"

    def test_rank_row_order_invariance(self):
        frame = pd.DataFrame({"momentum": [1, 5, 3, 2, 6, 4],
                              "target": [3, 6, 4, 2, 5, 1]})
        shuffled = frame.sample(frac=1.0, random_state=7).reset_index(drop=True)
        assert (mp.rank_diagnostic(frame)["value"]
                == pytest.approx(mp.rank_diagnostic(shuffled)["value"]))

    def test_build_targets_tail_incomplete_and_endpoint_missing(self):
        idx = pd.DatetimeIndex(pd.to_datetime(ALL_TDAYS))
        series = pd.Series([100.0 + i for i in range(len(idx))], index=idx)
        sessions = mp.validate_sessions(CALENDAR.trading_days(EVAL_START, TARGET_END))
        last_obs = CALENDAR.trading_days("2025-12-01", "2025-12-31")[-1]
        tail = mp.build_targets(series, sessions, [last_obs])
        # 12 月末观察日的 exit 落在 2026-01，仍在窗口内 → 应可算。
        assert pd.notna(tail["target"].iloc[0])
        beyond = mp.build_targets(series, sessions, ["2026-02-27"])
        assert pd.isna(beyond["target"].iloc[0]) \
            and beyond["reason"].iloc[0] == "future_incomplete"
        # 缺端点：删掉 exit 当日报价，不得顺延到下一报价。
        obs0 = CALENDAR.trading_days("2025-06-01", "2025-06-30")[-1]
        pos = list(sessions).index(pd.Timestamp(obs0))
        exit_day = sessions[pos + 22]
        holed = series.drop(index=pd.DatetimeIndex([exit_day]))
        holed_res = mp.build_targets(holed, sessions, [obs0])
        assert pd.isna(holed_res["target"].iloc[0]) \
            and holed_res["reason"].iloc[0] == "endpoint_missing_or_invalid"
        # 观察日不是交易日：显式 reason，不静默换日。
        off = mp.build_targets(series, sessions, ["2025-06-15"])  # 周日
        assert off["reason"].iloc[0] == "observation_not_session"

    def test_complete_month_last_trading_days_excludes_incomplete(self):
        payload = make_calendar_payload(month_range("2024-01", "2024-03"))
        # 3 月被抠掉若干天记录 → 月份不完整，不得推断月末。
        for d in [f"2024-03-{x:02d}" for x in (11, 12, 13, 14, 15)]:
            payload["days"].pop(d)
        cal = TradingCalendar(payload)
        out = mp.complete_month_last_trading_days(cal, "2024-01-01", "2024-03-31")
        assert out == ["2024-01-31", "2024-02-29"]

    def test_pilot_input_order_invariance(self):
        r1 = run_ok()
        idx2 = {s: make_indexes()[s] for s in sorted(COEFFS, reverse=True)}
        r2 = run_ok(idx2)
        assert json.dumps(r1["months"], sort_keys=True) \
            == json.dumps(r2["months"], sort_keys=True)


# ---------------------------------------------------- (c) 样本去向完整性

class TestSampleFlow:
    def test_stepwise_exclusive_accounting(self):
        result = run_ok()
        t = result["sample_flow_totals"]
        months = result["months"]
        assert t["expected"] == 8 * N_MONTHS
        # 逐步对账：特征可算 = 预期 − 特征缺；共同样本 = 双侧都不缺。
        feat_miss = sum(f["expected"] - f["feature_computable"]
                        for f in (m["sample_flow"] for m in months))
        # SHORT 2024-12 起步，到 2025-11 才攒够 253 条历史（10 个月特征缺）；
        # GAPX 缺 2025-04 报价，4 月末观察日特征缺 → 合计 11。
        assert feat_miss == 11
        assert t["feature_computable"] == t["expected"] - feat_miss
        # GAPX 的 exit 落在 2025-04 的两个月份（2、3 月末）目标端点缺失。
        gapx_target_missing = sum(
            m["sample_flow"]["excluded_counts"].get(
                "target_endpoint_missing_or_invalid", 0) for m in months)
        assert gapx_target_missing == 2
        assert t["target_computable"] == t["expected"] - gapx_target_missing
        assert t["common_sample"] == t["expected"] - feat_miss - gapx_target_missing
        assert t["expected"] >= t["feature_computable"] >= t["common_sample"]
        assert t["expected"] >= t["target_computable"] >= t["common_sample"]
        # 每月互斥主因：排除原因各归一类，总排除数 = 预期 − 共同。
        for m in months:
            f = m["sample_flow"]
            assert f["expected"] - f["common_sample"] == sum(f["excluded_counts"].values())
            assert set(f["excluded_counts"]) <= {
                "feature_not_computable", "target_future_incomplete",
                "target_endpoint_missing_or_invalid", "target_observation_not_session",
                "target_missing"}

    def test_insufficient_common_sample_marks_not_computable(self):
        # 只留 5 个有完整历史的产品 → 全部月份 not_computable，不硬算。
        small = {s: make_indexes()[s] for s in list(COEFFS)[:5]}
        result = run_ok(small)
        assert all(m["status"] == "not_computable"
                   and m["reason"] == "insufficient_common_sample"
                   for m in result["months"])

    def test_output_carries_historical_marker(self):
        result = run_ok()
        assert result["historical_reconstruction_only"] == "historical_reconstruction_only"


# ------------------------------------------------ (d) 独立校验可否定错误

class TestIndependentVerifier:
    def _verify(self, result):
        return reference_check.verify(result, indexes=make_indexes(),
                                      calendar_payload=CAL_PAYLOAD)

    def test_verifier_passes_on_clean_result(self):
        assert self._verify(run_ok())["ok"] is True

    def test_tampered_diagnostic_value_detected(self):
        result = run_ok()
        # 篡改 + “重算哈希”：结果里根本没有自报哈希，校验器只信原始输入
        # 复算出的数值，因此改完再怎么声称哈希一致都会被抓。
        for m in result["months"]:
            if m["status"] == "ok" and m["rank_ic"]["value"] is not None:
                m["rank_ic"]["value"] += 0.05
                break
        out = self._verify(result)
        assert out["ok"] is False and any("rank_ic" in s for s in out["mismatches"])

    def test_tampered_group_membership_detected(self):
        result = run_ok()
        m = next(m for m in result["months"] if m["status"] == "ok"
                 and m["quantile_groups_q2"]["status"] == "ok"
                 and m["quantile_groups_q2"]["groups"]["low"]["n"] >= 1
                 and m["quantile_groups_q2"]["groups"]["high"]["n"] >= 1)
        g = m["quantile_groups_q2"]["groups"]
        stolen = g["low"]["entities"].pop()
        g["high"]["entities"].append(stolen)
        out = self._verify(result)
        assert out["ok"] is False and any("组成员" in s or "mean_target" in s
                                          for s in out["mismatches"])

    def test_tampered_time_pairing_detected(self):
        result = run_ok()
        m = next(m for m in result["months"] if m["status"] == "ok")
        m["target_window"]["exit_date"] = "2030-01-01"
        out = self._verify(result)
        assert out["ok"] is False and any("target_window" in s
                                          for s in out["mismatches"])

    def test_tampered_sample_accounting_detected(self):
        result = run_ok()
        result["sample_flow_totals"]["common_sample"] += 1
        deep = copy.deepcopy(result)
        deep["months"][0]["sample_flow"]["common_sample"] += 1
        for mutated in (result, deep):
            out = self._verify(mutated)
            assert out["ok"] is False

    def test_chain_values_consistent_month_by_month(self):
        # 主链与独立实现逐月数值一致（含 IC、分组、参考差额、观察日）。
        result = run_ok()
        out = self._verify(result)
        assert out == {"ok": True, "mismatches": []}
