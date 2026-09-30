"""B3-a 候选因子单测：抵扣价距离＋入场均线组最近距离。

期望值来自独立闭式/直算（见 raw/factor-b3a-2026-09-20/hand-expectations.md，
固定于实现运行之前），不调用被测函数推导期望。
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
import pytest

from lei_signal.research.factor_lab.b3a_factors import (
    CANDIDATE_COST_BASIS20,
    CANDIDATE_PULLBACK_MA,
    calculate_b3a_batch,
)
from lei_signal.research.factor_lab.contracts import IdentityFormatError

RAW_DIR = (Path(__file__).resolve().parents[2]
           / "docs/experiments/raw/factor-b3a-2026-09-20")
TOL = 1e-6


def make_protocol(**overrides):
    protocol = {
        "protocol_id": "b3a-test-protocol",
        "version": "0.0.1",
        "kind": "calculation_only",
        "data_mode": "synthetic",
        "synthetic": True,
        "timezone": "Asia/Shanghai",
        "evaluation_cutoff": "2030-01-01T15:00:00+08:00",
    }
    protocol.update(overrides)
    return protocol


def load_bars(fixture_id: str) -> dict[str, pd.DataFrame]:
    payload = json.loads((RAW_DIR / "fixtures" / f"{fixture_id}.json").read_text())
    frame = pd.DataFrame(
        payload["bars"],
        columns=["date", "open", "high", "low", "close", "volume"],
    ).set_index("date")
    return {payload["symbol"]: frame}


def run(reference: str, fixture_id: str):
    batch = calculate_b3a_batch(
        reference, {"bars": load_bars(fixture_id)}, protocol=make_protocol()
    )
    return batch, list(batch.values.itertuples(index=False))


class TestCostBasisDistance20:
    def test_normal_zero_and_step(self):
        _, rows = run(CANDIDATE_COST_BASIS20, "fx1-normal")
        assert math.isclose(rows[159].value, 0.0, abs_tol=TOL)
        assert math.isclose(rows[160].value, 0.2, abs_tol=TOL)  # 120/100-1
        assert math.isclose(rows[180].value, 0.0, abs_tol=TOL)  # 120/120-1

    def test_first_computable_at_t20_with_step_return(self):
        _, rows = run(CANDIDATE_COST_BASIS20, "fx3-step")
        assert pd.isna(rows[19].value) and rows[19].missing_reason == "warmup_history_insufficient"
        assert math.isclose(rows[119].value, 0.1, abs_tol=TOL)  # 110/100-1

    def test_short_series_all_warmup(self):
        _, rows = run(CANDIDATE_COST_BASIS20, "fx2-short")
        assert len(rows) == 19
        assert all(pd.isna(r.value)
                   and r.missing_reason == "warmup_history_insufficient" for r in rows)

    def test_observation_day_missing_close(self):
        _, rows = run(CANDIDATE_COST_BASIS20, "fx4-missing-close")
        assert pd.isna(rows[50].value) and rows[50].missing_reason == "price_missing"
        assert pd.isna(rows[70].value) and rows[70].missing_reason == "warmup_history_insufficient"

    def test_zero_denominator_returns_reason_not_value(self):
        _, rows = run(CANDIDATE_COST_BASIS20, "fx5-zero-denominator")
        assert pd.isna(rows[20].value)
        assert rows[20].missing_reason == "zero_denominator"

    def test_constant_series_zero_distance(self):
        _, rows = run(CANDIDATE_COST_BASIS20, "fx1-normal")
        assert math.isclose(rows[100].value, 0.0, abs_tol=TOL)


class TestPullbackMaDistance:
    def test_constant_segment_zero_distance(self):
        _, rows = run(CANDIDATE_PULLBACK_MA, "fx1-normal")
        assert math.isclose(rows[150].value, 0.0, abs_tol=TOL)

    def test_sma20_reaches_close_after_step(self):
        # t=199：SMA20 已全部为 120，与收盘重合，最近距离 0
        _, rows = run(CANDIDATE_PULLBACK_MA, "fx1-normal")
        assert math.isclose(rows[199].value, 0.0, abs_tol=TOL)

    def test_warmup_until_all_six_mas_available(self):
        _, rows = run(CANDIDATE_PULLBACK_MA, "fx3-step")
        assert pd.isna(rows[118].value)
        assert rows[118].missing_reason == "warmup_history_insufficient"
        # t=119：EMA20=100+10·2/21=100.952381（seeded EMA，含当日收盘），
        # 最近距离 = 9.047619/100.952381 = 0.089623（独立闭式算出）
        assert math.isclose(rows[119].value, 0.0896226415, abs_tol=TOL)

    def test_short_series_all_warmup(self):
        _, rows = run(CANDIDATE_PULLBACK_MA, "fx2-short")
        assert len(rows) == 19
        assert all(pd.isna(r.value)
                   and r.missing_reason == "warmup_history_insufficient" for r in rows)

    def test_missing_close_propagates_and_window_missing_blocks(self):
        _, rows = run(CANDIDATE_PULLBACK_MA, "fx4-missing-close")
        assert pd.isna(rows[50].value) and rows[50].missing_reason == "price_missing"
        # t=100：SMA120 窗口含缺失收盘 → 整组不可算，不部分计算
        assert pd.isna(rows[100].value)
        assert rows[100].missing_reason == "warmup_history_insufficient"

    def test_too_short_for_sma120(self):
        _, rows = run(CANDIDATE_PULLBACK_MA, "fx5-zero-denominator")
        assert pd.isna(rows[30].value)
        assert rows[30].missing_reason == "warmup_history_insufficient"


class TestContractAndRejections:
    def test_unknown_reference_rejected(self):
        with pytest.raises(IdentityFormatError, match="unknown B3-a candidate"):
            calculate_b3a_batch("candidate:unknown@draft-1", {"bars": {}},
                                protocol=make_protocol())

    def test_non_synthetic_protocol_rejected(self):
        with pytest.raises(IdentityFormatError, match="synthetic"):
            calculate_b3a_batch(CANDIDATE_COST_BASIS20,
                                {"bars": load_bars("fx2-short")},
                                protocol=make_protocol(synthetic=False))

    def test_missing_bars_rejected(self):
        with pytest.raises(IdentityFormatError, match="bars"):
            calculate_b3a_batch(CANDIDATE_COST_BASIS20, {},
                                protocol=make_protocol())

    def test_metadata_complete_and_candidate_kind(self):
        batch, _ = run(CANDIDATE_PULLBACK_MA, "fx3-step")
        meta = batch.metadata
        assert meta["card_kind"] == "candidate"
        assert meta["synthetic"] is True
        assert meta["production_authorization"] == "not_authorized"
        assert meta["protocol"]["kind"] == "calculation_only"
        assert meta["card"]["spec_layer"] == "entry_trigger"
        assert meta["card"]["definition"]["parameters"] == {
            "windows": [20, 60, 120], "ma_types": ["ema", "sma"]}

    def test_no_trading_judgment_in_findings(self):
        batch, _ = run(CANDIDATE_PULLBACK_MA, "fx1-normal")
        joined = json.dumps(batch.findings, ensure_ascii=False)
        for banned in ("买入", "卖出", "可入场", "信号触发"):
            assert banned not in joined
