"""S3 试点A合成验收测试（受限输出边界 / 排序规则 / 样本账 / 独立校验）。

覆盖（承接 S2 四类测试思路，适配 S3 受限模式）：
(a) 资格与输出边界：target 承接判定固定阻塞（含裁决 usable 也拒绝）；
    禁止统计清单与合同 §8 禁项一致；
(b) 截面排序规则：mixed.momentum.rank@1.0.0 的 sort(key=(-score, symbol))，
    同分精确相等才按符号升序，高分在前；
(c) 独立校验器 observation_days_independent 与生产 complete_month_last_trading_days
    在边界月份（不完整月/缺整月/缺逐日）上语义一致；
(d) 独立校验可否定错误：干净合成产物通过；篡改动量值/位次/阶段标注/样本行/
    注入 target 键/翻掉重建标注都能被发现。

合成输入全部手造（虚构产品/日期/价格），不读取任何冻结真实输入。
"""

from __future__ import annotations

import copy
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

from lei_signal.research import data_quality as dq
from lei_signal.research import momentum_prototype as mp
from lei_signal.research.trading_calendar import TradingCalendar

PILOT_DIR = (
    Path(__file__).resolve().parents[2]
    / "docs/experiments/raw/factor-p2-pilot-s3-2026-09-19"
)
sys.path.insert(0, str(PILOT_DIR))

import pilot_s3 as pilot  # noqa: E402 （2026-09-19 返修改名：避免与 S2 目录同名 pilot 模块冲突）
import reference_check_s3 as rc  # noqa: E402


# ---------------------------------------------------------------- 合成输入

def weekday_dates_back(end: date, count: int) -> list[str]:
    """从 end（含）往前取 count 个工作日，返回升序字符串列表。"""
    out: list[str] = []
    cur = end
    while len(out) < count:
        if cur.weekday() < 5:
            out.append(cur.isoformat())
        cur -= timedelta(days=1)
    return sorted(out)


OBS1, OBS2 = "2024-01-31", "2024-02-29"
# 300 个工作日止于 OBS2：OBS1 位于第 279 位（0 基 278），
# CCC（少 20 个报价）在 OBS1 因子可算（vc=259）但资格不足（<273），
# 在 OBS2 达标（vc=280）——覆盖 ranking 阻塞与跨月晋级两条路径。
DATES = weekday_dates_back(date(2024, 2, 29), 300)
assert OBS1 in DATES and OBS2 in DATES
assert DATES.index(OBS2) - DATES.index(OBS1) == 21


def make_calendar_payload(days: list[str]) -> dict:
    day_set = set(days)
    months = sorted({d[:7] for d in days})
    import calendar as _cal

    payload_days: dict[str, dict] = {}
    for ym in months:
        y, m = int(ym[:4]), int(ym[5:7])
        for d in range(1, _cal.monthrange(y, m)[1] + 1):
            iso = f"{ym}-{d:02d}"
            payload_days[iso] = {"is_trading_day": iso in day_set,
                                 "source_flag": 1 if iso in day_set else 0,
                                 "source_month": ym}
    return {"days": payload_days, "months_requested": months,
            "authority": "synthetic"}


CLOSES = {
    # A 快速上涨、B 缓慢下跌：动量 A > B；C 晚 20 个报价日入场。
    "AAA.SS": [1.0 * (1.0 + 0.002 * i) for i in range(len(DATES))],
    "BBB.SS": [2.0 * (1.0 - 0.0004 * i) for i in range(len(DATES))],
    "CCC.SS": [3.0 * (1.0 + 0.001 * i) for i in range(len(DATES) - 20)],
}
SYMBOLS = sorted(CLOSES)
TARGET_REASON = "target_use_not_approved: 测试用固定原因"


# ---------------------------------------------------------------- (a) 闸门

def _report_with_verdict(verdict: str) -> dq.QualityReport:
    """真实 QualityReport（零 findings，仅给定用途裁决）。"""
    return dq.QualityReport(
        findings=(),
        verdicts=(dq.UseVerdict(use="research_signal", verdict=verdict,
                                reasons=("测试原因",)),),
        counts={},
    )


class TestQualificationBoundaries:
    def test_target_gate_blocks_conditional(self):
        rec = pilot.require_target_use_blocked(
            _report_with_verdict(dq.CONDITIONAL))
        assert rec["blocked"] is True and rec["target_use_approved"] is False
        assert rec["verdict"] == dq.CONDITIONAL
        assert rec["reasons"] == ["测试原因"]

    def test_target_gate_blocks_even_if_verdict_usable(self):
        # 裁决可用但授权未给：仍拒绝，不得把"裁决可用"当放行。
        rec = pilot.require_target_use_blocked(_report_with_verdict(dq.USABLE))
        assert rec["blocked"] is True and rec["verdict"] == "unapproved"

    def test_forbidden_statistics_list_matches_contract(self):
        assert set(pilot.TARGET_DEPENDENT_STATISTICS) == {
            "rank_ic", "quantile_groups_q2", "reference_difference"}
        # 目标只许以 unavailable 原因出现，不许 value。
        assert pilot.TARGET_UNAVAILABLE_REASON.startswith(
            "target_use_not_approved")

    def test_frozen_binding_rejects_wrong_hash(self, tmp_path):
        f = tmp_path / "input.txt"
        f.write_text("hello", encoding="utf-8")
        man = tmp_path / "manifest.json"
        man.write_text(json.dumps({"inputs": {
            "registry": {"path": str(f), "sha256": "0" * 64}}}),
            encoding="utf-8")
        with pytest.raises(pilot.FrozenInputError):
            pilot.verify_frozen_inputs(man)
        good = tmp_path / "manifest_ok.json"
        import hashlib
        digest = hashlib.sha256(b"hello").hexdigest()
        good.write_text(json.dumps({"inputs": {
            "registry": {"path": str(f), "sha256": digest}}}),
            encoding="utf-8")
        assert pilot.verify_frozen_inputs(good)["all_match"] is True


# ---------------------------------------------------------------- (b) 排序

class TestOrderingRule:
    def test_desc_then_symbol_tie(self):
        rows = [{"symbol": "C", "momentum": 1.0},
                {"symbol": "A", "momentum": 1.0},
                {"symbol": "B", "momentum": 0.5}]
        ordered = pilot.order_cross_section(rows)
        assert [r["symbol"] for r in ordered] == ["A", "C", "B"]

    def test_near_equal_floats_not_tied(self):
        # 无近似容差：1.0 与 1.0 + 1e-15 不是同分，数值大者在前。
        rows = [{"symbol": "A", "momentum": 1.0},
                {"symbol": "A2", "momentum": 1.0 + 1e-15}]
        ordered = pilot.order_cross_section(rows)
        assert [r["symbol"] for r in ordered] == ["A2", "A"]


# ---------------------------------------------- (c) 观察日独立实现一致性

class TestObservationDaysIndependent:
    def test_matches_production_on_edge_months(self):
        payload = make_calendar_payload(DATES)
        cal = TradingCalendar(payload)
        start, end = OBS1[:8] + "01", OBS2
        # 生产：完整月份最后交易日（不完整不推断月末）。
        exp = mp.complete_month_last_trading_days(cal, start, end)
        got = rc.observation_days_independent(payload, start, end)
        assert got == exp

    def test_window_clipped_mid_month_returns_in_window_last_day(self):
        # 窗口裁剪月中而日历记录完整：取窗内最后交易日（不是推断自然月末）。
        payload = make_calendar_payload(DATES)
        got = rc.observation_days_independent(payload, "2024-02-01", "2024-02-15")
        cal = TradingCalendar(payload)
        assert got == ["2024-02-15"]  # 周四，窗内最后一个交易日
        assert got == mp.complete_month_last_trading_days(
            cal, "2024-02-01", "2024-02-15")

    def test_incomplete_calendar_records_no_month_end_inference(self):
        # 日历缺 02-14 之后的逐日记录：该月不完整，不推断月末。
        payload = make_calendar_payload(DATES)
        payload["days"] = {d: rec for d, rec in payload["days"].items()
                           if d <= "2024-02-13"}
        got = rc.observation_days_independent(payload, "2024-02-01", "2024-02-28")
        assert got == []
        cal = TradingCalendar(payload)
        assert mp.complete_month_last_trading_days(
            cal, "2024-02-01", "2024-02-28") == []

    def test_missing_whole_month_skipped(self):
        payload = make_calendar_payload(DATES)
        payload["months_requested"] = [
            m for m in payload["months_requested"] if m != "2023-12"]
        got = rc.observation_days_independent(
            payload, "2023-11-01", "2024-01-31")
        assert "2023-12-29" not in got
        assert got == ["2023-11-30", "2024-01-31"]


# -------------------------------------------- (d) 独立校验（合成全链）

def build_result_artifacts(out: Path) -> None:
    """手工构造一套受限产物（期望值在测试内独立计算），供校验器复算比对。

    夹具约定：无行动记录（经济指数=归一化收盘，动量=直接比值）；
    CCC 晚 20 个报价日入场 → 在 OBS1 因子可算但 ranking 资格不足。
    """
    months = [OBS1, OBS2]
    all_rows: list[dict] = []
    ledger_months: list[dict] = []
    totals = {"expected": 0, "factor_computable": 0, "ranking_usable": 0,
              "target_unavailable": 0}
    for obs in months:
        obs_pos = DATES.index(obs)
        elig, month_rows, n_factor = [], [], 0
        for sym in SYMBOLS:
            closes = CLOSES[sym]
            offset = len(DATES) - len(closes)  # 晚入场产品的位置偏移
            j = obs_pos - offset  # 该产品在自身报价序列中的位置
            row = {"symbol": sym, "observation_date": obs, "eligible": False,
                   "blocked_stage": None, "main_reason": None,
                   "momentum": None, "rank": None}
            if j < 0:
                row["blocked_stage"], row["main_reason"] = \
                    "factor", "factor:no_quote_at_observation"
            elif j < 252:
                row["blocked_stage"], row["main_reason"] = \
                    "factor", "factor:insufficient_warmup"
            else:
                mom = closes[j - 21] / closes[j - 252] - 1
                row["momentum"] = mom
                n_factor += 1
                vc = j + 1
                if vc < 273:
                    row["blocked_stage"] = "ranking"
                    row["main_reason"] = (
                        f"ranking:mixed.eligible_not_met(valid_count={vc}<273)")
                else:
                    row["eligible"] = True
                    row["blocked_stage"] = "target"
                    row["main_reason"] = f"target:{TARGET_REASON}"
                    elig.append(row)
            month_rows.append(row)
        ordered = sorted(elig, key=lambda r: (-r["momentum"], r["symbol"]))
        for k, r in enumerate(ordered):
            r["rank"] = k + 1
        all_rows += copy.deepcopy(month_rows)
        ledger_months.append({
            "observation_date": obs, "status": "ranking_recorded",
            "meets_min_diagnostic_sample": len(elig) >= 6,
            "expected": len(SYMBOLS), "factor_computable": n_factor,
            "ranking_usable": len(elig), "target_unavailable": len(elig),
            "blocked_counts": {}, "conservation_ok": True,
            "ordering": [{"rank": r["rank"], "symbol": r["symbol"],
                          "momentum": r["momentum"]} for r in ordered],
        })
        totals["expected"] += len(SYMBOLS)
        totals["factor_computable"] += n_factor
        totals["ranking_usable"] += len(elig)
        totals["target_unavailable"] += len(elig)
    manifest = {
        "historical_reconstruction_only": True,
        "inputs": {"symbols": SYMBOLS,
                   "unknown_available_at_events": [],
                   "evaluation_start": OBS1[:8] + "01",
                   "evaluation_end": OBS2},
        "observation_days": {"count": len(months), "first": OBS1, "last": OBS2},
        "gates": {"target_use_block": {
            "blocked": True, "verdict": "conditional",
            "target_unavailable_reason": TARGET_REASON}},
    }
    ledger = {"historical_reconstruction_only": True, "months": ledger_months}
    sample = {"historical_reconstruction_only": True,
              "sample_flow_totals": totals,
              "rows": all_rows}
    (out / "run-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    (out / "ranking-ledger.json").write_text(
        json.dumps(ledger, ensure_ascii=False), encoding="utf-8")
    (out / "sample-ledger.json").write_text(
        json.dumps(sample, ensure_ascii=False), encoding="utf-8")


class TestIndependentVerifier:
    @pytest.fixture(autouse=True)
    def _fixture(self, tmp_path):
        # 报价 CSV（reference_check 只需 date,close 两列）
        snap_dir = tmp_path / "snapshot"
        snap_dir.mkdir()
        instruments = [{"instrument_id": s,
                        "normalized": {"path": f"{s}.csv"}}
                       for s in SYMBOLS]
        snap_dir.joinpath("snapshot.json").write_text(
            json.dumps({"instruments": instruments}), encoding="utf-8")
        for sym, closes in CLOSES.items():
            offset = len(DATES) - len(closes)
            lines = ["date,close"] + [
                f"{DATES[offset + i]},{c}" for i, c in enumerate(closes)]
            snap_dir.joinpath(f"{sym}.csv").write_text("\n".join(lines),
                                                       encoding="utf-8")
        cal = tmp_path / "calendar.json"
        cal.write_text(json.dumps(make_calendar_payload(DATES)),
                       encoding="utf-8")
        actions = tmp_path / "actions.json"
        actions.write_text(json.dumps({"events": []}), encoding="utf-8")
        run04 = tmp_path / "run04-values.csv"
        lines = ["object_id,symbol,date,momentum,unit"]
        for sym, closes in CLOSES.items():
            offset = len(DATES) - len(closes)
            for obs in (OBS1, OBS2):
                j = DATES.index(obs) - offset
                mom = closes[j - 21] / closes[j - 252] - 1
                lines.append(f"x,{sym},{obs},{mom!r},fraction")
        run04.write_text("\n".join(lines), encoding="utf-8")
        self.paths = {"snapshot_dir": snap_dir, "calendar": cal,
                      "actions": actions, "run04": run04}
        self.out = tmp_path / "out"
        self.out.mkdir()

    def _build_and_verify(self):
        build_result_artifacts(self.out)
        return rc.verify(
            out_dir=self.out, snapshot_dir=self.paths["snapshot_dir"],
            actions_path=self.paths["actions"],
            calendar_path=self.paths["calendar"],
            run04_values_path=self.paths["run04"],
            evaluation_start=OBS1[:8] + "01", evaluation_end=OBS2)

    def test_clean_result_passes_with_expected_flow(self):
        res = self._build_and_verify()
        assert res["ok"], res["mismatches"]
        sample = json.loads((self.out / "sample-ledger.json").read_text())
        assert sample["sample_flow_totals"]["ranking_usable"] > 0
        assert sample["sample_flow_totals"]["ranking_usable"] == \
            sample["sample_flow_totals"]["target_unavailable"]

    def test_tampered_momentum_detected(self):
        self._build_and_verify()
        sample = json.loads((self.out / "sample-ledger.json").read_text())
        for r in sample["rows"]:
            if r["momentum"] is not None:
                r["momentum"] *= 1.0000001
                break
        (self.out / "sample-ledger.json").write_text(json.dumps(sample))
        assert not rc.verify(
            out_dir=self.out, snapshot_dir=self.paths["snapshot_dir"],
            actions_path=self.paths["actions"],
            calendar_path=self.paths["calendar"],
            run04_values_path=self.paths["run04"],
            evaluation_start=OBS1[:8] + "01", evaluation_end=OBS2)["ok"]

    def test_tampered_rank_order_detected(self):
        self._build_and_verify()
        ledger = json.loads((self.out / "ranking-ledger.json").read_text())
        order = ledger["months"][0]["ordering"]
        if len(order) >= 2:
            order[0], order[1] = order[1], order[0]
            order[0]["rank"], order[1]["rank"] = 1, 2
        (self.out / "ranking-ledger.json").write_text(json.dumps(ledger))
        assert not rc.verify(
            out_dir=self.out, snapshot_dir=self.paths["snapshot_dir"],
            actions_path=self.paths["actions"],
            calendar_path=self.paths["calendar"],
            run04_values_path=self.paths["run04"],
            evaluation_start=OBS1[:8] + "01", evaluation_end=OBS2)["ok"]

    def test_tampered_stage_classification_detected(self):
        self._build_and_verify()
        sample = json.loads((self.out / "sample-ledger.json").read_text())
        for r in sample["rows"]:
            if r["blocked_stage"] == "target":
                r["blocked_stage"] = "factor"
                r["main_reason"] = "factor:no_quote_at_observation"
                r["eligible"] = False
                break
        (self.out / "sample-ledger.json").write_text(json.dumps(sample))
        assert not rc.verify(
            out_dir=self.out, snapshot_dir=self.paths["snapshot_dir"],
            actions_path=self.paths["actions"],
            calendar_path=self.paths["calendar"],
            run04_values_path=self.paths["run04"],
            evaluation_start=OBS1[:8] + "01", evaluation_end=OBS2)["ok"]

    def test_dropped_sample_row_detected(self):
        self._build_and_verify()
        sample = json.loads((self.out / "sample-ledger.json").read_text())
        sample["rows"] = sample["rows"][:-1]
        (self.out / "sample-ledger.json").write_text(json.dumps(sample))
        assert not rc.verify(
            out_dir=self.out, snapshot_dir=self.paths["snapshot_dir"],
            actions_path=self.paths["actions"],
            calendar_path=self.paths["calendar"],
            run04_values_path=self.paths["run04"],
            evaluation_start=OBS1[:8] + "01", evaluation_end=OBS2)["ok"]

    def test_injected_target_value_detected(self):
        self._build_and_verify()
        sample = json.loads((self.out / "sample-ledger.json").read_text())
        sample["rows"][0]["target"] = 0.05  # 禁止的 target 数值
        (self.out / "sample-ledger.json").write_text(json.dumps(sample))
        assert not rc.verify(
            out_dir=self.out, snapshot_dir=self.paths["snapshot_dir"],
            actions_path=self.paths["actions"],
            calendar_path=self.paths["calendar"],
            run04_values_path=self.paths["run04"],
            evaluation_start=OBS1[:8] + "01", evaluation_end=OBS2)["ok"]

    def test_marker_flip_detected(self):
        self._build_and_verify()
        manifest = json.loads((self.out / "run-manifest.json").read_text())
        manifest["historical_reconstruction_only"] = False
        (self.out / "run-manifest.json").write_text(json.dumps(manifest))
        assert not rc.verify(
            out_dir=self.out, snapshot_dir=self.paths["snapshot_dir"],
            actions_path=self.paths["actions"],
            calendar_path=self.paths["calendar"],
            run04_values_path=self.paths["run04"],
            evaluation_start=OBS1[:8] + "01", evaluation_end=OBS2)["ok"]


class TestEconomicIndexIndependent:
    def test_split_and_cash_adjustment_hand_computed(self):
        quotes = [("2024-01-01", 10.0), ("2024-01-02", 10.0),
                  ("2024-01-03", 12.0), ("2024-01-04", 12.0)]
        events = [
            {"event_id": "s1", "type": "split", "effective_date": "2024-01-03",
             "ratio": 2.0, "available_at": None},
            {"event_id": "c1", "type": "cash_dividend",
             "effective_date": "2024-01-03", "cash": 0.5, "available_at": None},
        ]
        levels, unknown = rc.economic_index_independent(quotes, events)
        # t2→t3：先拆分(×2)再分红(+0.5)逆序叠乘：(12×2 + 0.5)/10 = 2.45
        assert levels == [1.0, 1.0, 2.45, 2.45]
        assert unknown == ["c1", "s1"]  # 未知可得时点逐条上报

    def test_events_for_independent_bare_code_attach(self):
        raw = [{"event_id": "e1", "symbol": "600000", "type": "cash_dividend",
                "ex_date": "2024-01-05", "cash_per_unit": 0.1}]
        got = rc.events_for_independent(raw, "600000.SS", {"600000": "600000.SS"})
        assert got[0]["effective_date"] == "2024-01-05"
        assert got[0]["cash"] == 0.1
