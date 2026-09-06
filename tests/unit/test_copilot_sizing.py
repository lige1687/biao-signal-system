"""仓位档位建议：档位规则 + 参数走 rules.v1.yaml + 降档 + 话术边界。"""
from __future__ import annotations

from lei_signal.copilot.sizing import build_sizing_advice, siphon_regime


def test_params_from_rules_yaml_not_hardcoded():
    adv = build_sizing_advice("515880", rr=3.4)
    assert adv.cap_pct == 30.0                       # single_symbol_cap_pct
    assert "10" in adv.tier_pct_cn and "15" in adv.tier_pct_cn  # 标准档区间来自账本
    assert any("30%" in r for r in adv.reasons)      # 硬顶写进依据


def test_rr_high_gives_standard_tier():
    adv = build_sizing_advice("515880", rr=3.4)
    assert adv.tier == "标准"
    assert any("3.4" in r for r in adv.reasons)


def test_rr_low_gives_trial_tier():
    adv = build_sizing_advice("515880", rr=1.8)
    assert adv.tier == "试仓"


def test_rr_not_computable_gives_trial_and_says_so():
    adv = build_sizing_advice("515880", rr=None, rr_computable=False)
    assert adv.tier == "试仓"
    assert any("不可计算" in r for r in adv.reasons)


def test_same_group_exposure_downgrades():
    adv = build_sizing_advice("515880", rr=3.4, same_group_exposure_pct=25.0)
    assert adv.tier == "试仓"  # 标准 -> 试仓
    assert any("同板块" in r for r in adv.reasons)


def test_disclaimer_tells_user_decides():
    adv = build_sizing_advice("515880", rr=3.4)
    assert "由你决定" in adv.disclaimer_cn
    assert adv.strength == "observation"


def test_tier_pct_cn_ranges():
    adv = build_sizing_advice("515880", rr=3.4)
    assert "10" in adv.tier_pct_cn and "15" in adv.tier_pct_cn


def test_breadth_weak_market_downgrades():
    """宽度弱市（<43.3）降一档；文案含依据与档位线。"""
    out = build_sizing_advice(
        "515880.SS", 4.0, rr_computable=True, breadth_ma200_pct=25.4
    )
    assert out.tier == "试仓"  # 标准 → 试仓
    assert any("宽度环境弱市" in r for r in out.reasons)


def test_breadth_weak_but_siphon_exempt():
    """虹吸独立行情豁免：同样弱市宽度不降档，文案说明价格原则。"""
    out = build_sizing_advice(
        "515880.SS", 4.0, rr_computable=True, breadth_ma200_pct=25.4, siphon=True
    )
    assert out.tier == "标准"  # 不降
    assert any("独立行情" in r and "虹吸" in r for r in out.reasons)


def test_breadth_normal_no_adjustment():
    out = build_sizing_advice(
        "510300.SS", 4.0, rr_computable=True, breadth_ma200_pct=55.0
    )
    assert out.tier == "标准"
    assert not any("宽度" in r for r in out.reasons)


def test_breadth_missing_no_adjustment():
    out = build_sizing_advice("510300.SS", 4.0, rr_computable=True, breadth_ma200_pct=None)
    assert out.tier == "标准"


def test_siphon_regime_detection():
    """虹吸判定：标的120日+60% vs 基准+10% → 独立行情；相近 → 非独立。"""
    import pandas as pd
    idx = pd.date_range("2025-01-01", periods=200, freq="B")
    strong = pd.DataFrame({"close": [1.0 * (1.006 ** i) for i in range(200)]}, index=idx)
    flat = pd.DataFrame({"close": [1.0 * (1.0005 ** i) for i in range(200)]}, index=idx)
    s, diff = siphon_regime(strong, flat)
    assert s is True and diff > 20
    s2, _ = siphon_regime(flat, flat)
    assert s2 is False
