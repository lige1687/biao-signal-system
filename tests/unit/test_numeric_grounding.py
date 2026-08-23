# tests/unit/test_numeric_grounding.py
"""数值接地：编数字必拒、照抄必过、量词序号豁免。"""
from lei_signal.plans.grounding import (
    collect_payload_numbers,
    extract_market_numbers,
    verify_numeric_grounding,
)


def test_collect_recursive():
    payload = {"a": 1938.56, "b": [{"c": 8700}, {"d": "rule_x12"}], "e": 3.0}
    nums = collect_payload_numbers(payload)
    assert 1938.56 in nums and 8700.0 in nums and 3.0 in nums
    assert 12.0 not in nums  # 字符串里的数字不抽


def test_extract_exempts_quantifiers_and_dates():
    text = "三根K线 · 第 3 次催办 · 买点② · 2026-08-21 · 十日均线粘合（2 个结构）"
    assert extract_market_numbers(text) == []


def test_extract_catches_prices_and_percents():
    text = "收盘 8700，偏差 ~1.2%，EMA20 为 1938.56"
    got = extract_market_numbers(text)
    assert 8700.0 in got and 1.2 in got and 1938.56 in got


def test_verify_rejects_invented_number():
    ok, reason = verify_numeric_grounding(
        "关键位 4321.00", frozenset({1938.56, 8700.0})
    )
    assert not ok and "4321" in reason


def test_verify_accepts_rounding_within_tolerance():
    ok, _ = verify_numeric_grounding(
        "EMA20 约 1939", frozenset({1938.56})
    )
    assert ok  # |1939-1938.56|/1938.56 < 0.5%


def test_verify_accepts_percentage_derivation():
    ok, _ = verify_numeric_grounding(
        "偏差约 1.2%", frozenset({1938.56, 1962.0})
    )
    assert ok  # |1962-1938.56|/1938.56 ≈ 1.2%


def test_verify_empty_text_passes():
    assert verify_numeric_grounding("无数字", frozenset())[0]
