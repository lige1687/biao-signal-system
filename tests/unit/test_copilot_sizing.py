"""仓位档位建议：档位规则 + 参数走 rules.v1.yaml + 降档 + 话术边界。"""
from __future__ import annotations

from lei_signal.copilot.sizing import build_sizing_advice


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
