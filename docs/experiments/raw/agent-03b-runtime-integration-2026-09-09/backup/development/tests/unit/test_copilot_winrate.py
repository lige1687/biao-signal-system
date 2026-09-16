"""分标的×模块胜率查询测试。"""
from __future__ import annotations

from lei_signal.copilot import winrate


def test_known_symbol_modules():
    w = winrate.winrate_for("513180.SS")  # 恒生科技：C 有 15 笔样本
    assert w is not None
    assert "C" in w["modules"]
    assert "胜率" in w["winrate_cn"]
    assert "叙事参考" in w["note_cn"]


def test_specified_module():
    w = winrate.winrate_for("515880.SS", "A")
    assert w is not None and set(w["modules"]) == {"A"}


def test_unknown_symbol_none():
    assert winrate.winrate_for("999999.SS") is None


def test_small_sample_flagged():
    w = winrate.winrate_for("515880.SS", "A")  # 仅 2 笔
    assert w is not None
    assert "样本过小" in w["modules"]["A"]["winrate_cn"]
