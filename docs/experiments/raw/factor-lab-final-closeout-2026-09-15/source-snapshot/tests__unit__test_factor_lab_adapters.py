"""factor_lab 适配层单测：合法/非法输入、端点、缩放不变、追加不变、候选就绪。"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lei_signal.research.factor_lab.adapters import (
    CANDIDATE_DUAL_MA,
    calculate_batch,
)
from lei_signal.research.factor_lab.contracts import IdentityFormatError


def make_protocol(**overrides):
    protocol = {
        "protocol_id": "test-protocol",
        "version": "0.0.1",
        "kind": "calculation_only",
        "data_mode": "synthetic",
        "synthetic": True,
        "timezone": "Asia/Shanghai",
        "evaluation_cutoff": "2030-01-01T15:00:00+08:00",
    }
    protocol.update(overrides)
    return protocol


def geometric_panel(entities: dict[str, float], rows: int = 300, base=100.0):
    dates = pd.bdate_range("2017-01-02", periods=rows)
    t = np.arange(rows, dtype=float)
    return pd.DataFrame(
        {name: base * (1.0 + g) ** t for name, g in entities.items()}, index=dates
    )


MOMENTUM_REF = "mixed.momentum.raw@1.0.0"
RV20_REF = "mixed.rv20@1.0.0"
D50_REF = "trend.distance50@1.0.0"
D200_REF = "trend.distance200@1.0.0"
B50_REF = "breadth.csi300.b50.common@1.0.0"
B200_REF = "breadth.csi300.b200.common@1.0.0"


class TestRejections:
    def test_unknown_reference_rejected(self):
        with pytest.raises(IdentityFormatError, match="not resolvable"):
            calculate_batch("not.a.ref@1.0.0", {"prices": geometric_panel({"a": 0.01})},
                            protocol=make_protocol())

    def test_wrong_version_rejected(self):
        with pytest.raises(IdentityFormatError, match="not resolvable"):
            calculate_batch("mixed.momentum.raw@1.0.1",
                            {"prices": geometric_panel({"a": 0.01})},
                            protocol=make_protocol())

    def test_registered_but_unimplemented_rejected(self):
        # trend.sma50 已登记且 calculate 支持，但 factor_lab 只开放声明过的对象；
        # 造一个已登记、factor_lab 未接的引用（如 mixed.price.economic）。
        with pytest.raises(IdentityFormatError, match="no factor_lab implementation"):
            calculate_batch("mixed.price.economic@1.0.0",
                            {"prices": geometric_panel({"a": 0.01})},
                            protocol=make_protocol())

    def test_missing_prices_input_rejected(self):
        with pytest.raises(IdentityFormatError, match="prices"):
            calculate_batch(MOMENTUM_REF, {}, protocol=make_protocol())

    def test_duplicate_dates_rejected(self):
        panel = geometric_panel({"a": 0.01}, rows=10)
        duplicated = pd.concat([panel, panel.iloc[[-1]]])
        with pytest.raises(IdentityFormatError, match="unique increasing"):
            calculate_batch(MOMENTUM_REF, {"prices": duplicated},
                            protocol=make_protocol())

    def test_duplicate_entity_columns_rejected(self):
        panel = geometric_panel({"a": 0.01})
        panel["a2"] = panel["a"]
        panel.columns = ["a", "a"]
        with pytest.raises(IdentityFormatError, match="entity columns"):
            calculate_batch(MOMENTUM_REF, {"prices": panel}, protocol=make_protocol())

    def test_kind_purpose_mismatch_rejected(self):
        with pytest.raises(IdentityFormatError, match="not allowed here"):
            calculate_batch(MOMENTUM_REF, {"prices": geometric_panel({"a": 0.01})},
                            protocol=make_protocol(kind="strategy_explanation"))

    def test_breadth_without_membership_rejected(self):
        with pytest.raises(IdentityFormatError, match="membership"):
            calculate_batch(B50_REF, {"prices": geometric_panel({"a": 0.01, "b": 0.02})},
                            protocol=make_protocol())

    def test_membership_symbol_not_in_panel_rejected(self):
        panel = geometric_panel({"a": 0.01, "b": 0.02}, rows=220)
        membership = {day: ["a", "b", "ghost"] for day in panel.index}
        with pytest.raises(IdentityFormatError, match="ghost"):
            calculate_batch(B50_REF,
                            {"prices": panel, "membership_by_date": membership},
                            protocol=make_protocol())

    def test_dual_ma_missing_volume_rejected(self):
        dates = pd.bdate_range("2024-01-01", periods=30)
        bars = {"x": pd.DataFrame({"close": np.linspace(100, 110, 30)}, index=dates)}
        with pytest.raises(IdentityFormatError, match="volume"):
            calculate_batch(CANDIDATE_DUAL_MA, {"bars": bars}, protocol=make_protocol())


class TestLegalBatches:
    def test_three_entity_interface(self):
        panel = geometric_panel({"alpha": 0.01, "beta": 0.005, "gamma": 0.0})
        batch = calculate_batch(MOMENTUM_REF, {"prices": panel}, protocol=make_protocol())
        assert batch.metadata["reference"] == MOMENTUM_REF
        assert batch.metadata["synthetic"] is True
        assert batch.metadata["entity_axis"] == "instrument"
        assert batch.metadata["card_kind"] == "registered"
        assert not batch.values.duplicated(["observation_date", "entity_id"]).any()
        assert set(batch.values.columns) == {
            "observation_date", "entity_id", "value", "missing_reason"}
        # 缺值行保留：3实体×300行 = 900行
        assert len(batch.values) == 900
        assert batch.metadata["definition_status"]
        assert batch.metadata["production_authorization"] == "not_authorized"

    def test_five_entity_same_interface(self):
        panel = geometric_panel({"alpha": 0.01, "beta": 0.005, "gamma": 0.0,
                                 "delta": 0.002, "epsilon": 0.0})
        batch3 = calculate_batch(MOMENTUM_REF, {"prices": panel[["alpha", "beta", "gamma"]]},
                                 protocol=make_protocol())
        batch5 = calculate_batch(MOMENTUM_REF, {"prices": panel}, protocol=make_protocol())
        assert list(batch3.values.columns) == list(batch5.values.columns)
        assert batch5.metadata["reference"] == batch3.metadata["reference"]
        assert len(batch5.values) == 1500
        # 改名称不影响无量纲计算
        renamed = panel.rename(columns={"alpha": "zzz"})
        batch_renamed = calculate_batch(MOMENTUM_REF, {"prices": renamed},
                                        protocol=make_protocol())
        v_orig = batch5.values[batch5.values.entity_id == "alpha"]["value"].to_numpy()
        v_renamed = (batch_renamed.values[batch_renamed.values.entity_id == "zzz"]
                     ["value"].to_numpy())
        np.testing.assert_allclose(v_orig, v_renamed, atol=1e-12)

    def test_momentum_first_legal_position_253(self):
        panel = geometric_panel({"alpha": 0.01})
        batch = calculate_batch(MOMENTUM_REF, {"prices": panel}, protocol=make_protocol())
        rows = batch.values.sort_values("observation_date").reset_index(drop=True)
        assert rows.iloc[250]["missing_reason"] == "warmup_history_insufficient"
        assert pd.isna(rows.iloc[250]["value"])
        assert rows.iloc[251]["missing_reason"] == "warmup_history_insufficient"
        # 第253条（0基252）首次可算：I(t-21)/I(t-252)-1 = 1.01^231-1
        expected = 1.01 ** 231 - 1
        assert rows.iloc[252]["value"] == pytest.approx(expected, rel=1e-9)
        assert rows.iloc[252]["missing_reason"] is None

    def test_rv20_ddof1_annualized_and_zero_for_constant_growth(self):
        panel = geometric_panel({"alpha": 0.01})
        batch = calculate_batch(RV20_REF, {"prices": panel}, protocol=make_protocol())
        rows = batch.values.sort_values("observation_date").reset_index(drop=True)
        # 等比价格序列的20期收益全相等 → 样本标准差(ddof=1)=0
        assert rows.iloc[252]["value"] == pytest.approx(0.0, abs=1e-6)
        # 独立手算：构造两条交替收益序列核对ddof=1
        prices = pd.Series([100.0, 101.0, 100.0, 102.0, 101.0, 103.0, 102.0, 104.0,
                            103.0, 105.0, 104.0, 106.0, 105.0, 107.0, 106.0, 108.0,
                            107.0, 109.0, 108.0, 110.0, 109.0, 111.0])
        batch2 = calculate_batch(RV20_REF, {"prices": pd.DataFrame({"s": prices})},
                                 protocol=make_protocol())
        first_valid = batch2.values.dropna(subset=["value"]).sort_values(
            "observation_date").iloc[0]
        rets = prices.pct_change().dropna().to_numpy()
        expected = np.std(rets[:20], ddof=1) * np.sqrt(252)  # 首个有效值=前20个收益
        assert first_valid["value"] == pytest.approx(expected, rel=1e-12)

    def test_sma_includes_current_day_strict_boundary(self):
        # 平价序列：价格==均线 → distance=0（严格大于不成立，above=0，distance=0）
        flat = pd.DataFrame({"f": [100.0] * 60},
                            index=pd.bdate_range("2024-01-01", periods=60))
        batch = calculate_batch(D50_REF, {"prices": flat}, protocol=make_protocol())
        rows = batch.values.sort_values("observation_date").reset_index(drop=True)
        assert rows.iloc[48]["missing_reason"] == "warmup_history_insufficient"
        # 第50条（0基49）：SMA50含当日 = 100 → distance=0
        assert rows.iloc[49]["value"] == pytest.approx(0.0, abs=1e-12)
        assert rows.iloc[49]["missing_reason"] is None

    def test_distance200_first_position(self):
        panel = geometric_panel({"alpha": 0.01})
        batch = calculate_batch(D200_REF, {"prices": panel}, protocol=make_protocol())
        rows = batch.values.sort_values("observation_date").reset_index(drop=True)
        assert pd.isna(rows.iloc[198]["value"])
        expected = panel["alpha"].iloc[199] / panel["alpha"].iloc[:200].mean() - 1
        assert rows.iloc[199]["value"] == pytest.approx(expected, rel=1e-12)


class TestBreadth:
    def _membership(self, panel, segments):
        membership = {}
        for start, end, members in segments:
            for day in panel.loc[pd.Timestamp(start):pd.Timestamp(end)].index:
                membership[day] = list(members)
        return membership

    def test_common_denominator_and_change(self):
        panel = geometric_panel({"m1": 0.01, "m2": 0.008, "m3": -0.005}, rows=220)
        # 前200天 m3 缺席（名单只有 m1,m2）；之后 m3 加入
        membership = self._membership(panel, [
            (panel.index[0], panel.index[199], ["m1", "m2"]),
            (panel.index[200], panel.index[-1], ["m1", "m2", "m3"]),
        ])
        protocol = make_protocol()
        for ref in (B50_REF, B200_REF):
            batch = calculate_batch(ref, {"prices": panel, "membership_by_date": membership,
                                          "universe_id": "synthetic_idx"}, protocol=protocol)
            assert batch.metadata["entity_axis"] == "universe"
            rows = batch.values.sort_values("observation_date").reset_index(drop=True)
            # 前199天无一成员有200有效收盘 → 缺失及原因
            first_valid = rows[rows["value"].notna()].iloc[0]
            assert first_valid["observation_date"] == panel.index[199]
            # m1,m2 在上、m3 在下 → b=2/3（共同合格分母=全部3个成员）
            later = rows[rows["observation_date"] == panel.index[210]].iloc[0]
            assert later["value"] == pytest.approx(2 / 3, abs=1e-9)

    def test_zero_eligible_and_missing_reasons(self):
        panel = geometric_panel({"m1": 0.01, "m2": 0.008}, rows=210)
        membership = {day: [] for day in panel.index}  # 名单缺失
        batch = calculate_batch(B50_REF, {"prices": panel, "membership_by_date": membership},
                                protocol=make_protocol())
        assert (batch.values["missing_reason"] == "membership_missing").all()
        assert batch.values["value"].isna().all()


class TestInvariance:
    def test_price_scale_does_not_change_dimensionless_values(self):
        panel = geometric_panel({"alpha": 0.01, "beta": -0.003}, rows=280)
        for ref in (MOMENTUM_REF, RV20_REF, D50_REF, D200_REF):
            base = calculate_batch(ref, {"prices": panel}, protocol=make_protocol())
            scaled = calculate_batch(ref, {"prices": panel * 2.0},
                                     protocol=make_protocol())
            merged = base.values.merge(scaled.values, on=["observation_date", "entity_id"],
                                       suffixes=("_b", "_s"))
            both = merged[merged["value_b"].notna() & merged["value_s"].notna()]
            assert len(both) > 0
            np.testing.assert_allclose(both["value_b"], both["value_s"], atol=1e-10)

    def test_append_future_does_not_change_history(self):
        panel = geometric_panel({"alpha": 0.01}, rows=300)
        truncated = panel.iloc[:280]
        for ref in (MOMENTUM_REF, RV20_REF):
            full = calculate_batch(ref, {"prices": panel}, protocol=make_protocol())
            part = calculate_batch(ref, {"prices": truncated}, protocol=make_protocol())
            merged = part.values.merge(full.values, on=["observation_date", "entity_id"],
                                       suffixes=("_p", "_f"))
            both = merged[merged["value_p"].notna() & merged["value_f"].notna()]
            np.testing.assert_allclose(both["value_p"], both["value_f"], atol=1e-12)


class TestDualMaCandidate:
    def _bars(self, rows: int, start: float, step: float):
        dates = pd.bdate_range("2024-01-01", periods=rows)
        close = pd.Series([start + step * i for i in range(rows)], index=dates)
        return pd.DataFrame({
            "open": close.shift(1).fillna(close.iloc[0] - step),
            "high": close + 0.5, "low": close - 0.5, "close": close,
            "volume": 1_000_000.0,
        })

    def test_candidate_rising_series_state_true_after_ready(self):
        bars = {"x": self._bars(45, 100.0, 1.0)}
        batch = calculate_batch(CANDIDATE_DUAL_MA, {"bars": bars}, protocol=make_protocol())
        assert batch.metadata["card_kind"] == "candidate"
        assert batch.metadata["entity_axis"] == "instrument"
        assert batch.metadata["value_type"] == "boolean"
        rows = batch.values.sort_values("observation_date").reset_index(drop=True)
        # 前20行未就绪：value=NaN + warmup_not_ready（不混成有效看空样本）
        assert (rows.iloc[:20]["value"].isna()).all()
        assert (rows.iloc[:20]["missing_reason"] == "warmup_not_ready").all()
        # 稳定上升序列：就绪后状态全真（Close>两均线、均线上升、绿色）
        assert (rows.iloc[20:]["value"] == 1).all()
        assert (rows.iloc[20:]["missing_reason"].isna()).all()

    def test_candidate_flat_series_suppressed_by_gray_color(self):
        bars = {"x": self._bars(45, 100.0, 0.0)}
        batch = calculate_batch(CANDIDATE_DUAL_MA, {"bars": bars}, protocol=make_protocol())
        rows = batch.values.sort_values("observation_date").reset_index(drop=True)
        # 平价：颜色为灰（分歧），状态为0但就绪（不是未就绪）
        ready = rows.iloc[20:]
        assert (ready["value"] == 0).all()
        assert (ready["missing_reason"].isna()).all()

    def test_two_entities_and_findings(self):
        bars = {"x": self._bars(45, 100.0, 1.0), "y": self._bars(45, 50.0, -0.5)}
        batch = calculate_batch(CANDIDATE_DUAL_MA, {"bars": bars}, protocol=make_protocol())
        assert len(batch.values) == 90
        findings = {f["entity_id"]: f for f in batch.findings
                    if f["code"] == "entity_readiness"}
        assert findings["x"]["state_true_rows"] == 25
        assert findings["y"]["state_true_rows"] == 0
        assert findings["y"]["not_ready_rows"] == 20
        # 源代码身份进入元数据
        module_paths = [m["path"] for m in batch.metadata["code_identity"]["modules"]]
        assert "src/lei_signal/rules/dual_ma.py" in module_paths
        assert "src/lei_signal/rules/lei_color.py" in module_paths
