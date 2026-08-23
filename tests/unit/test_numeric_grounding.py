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


# ---------- Fix round 1: 入口归一化（中文数字/千分位/科学计数法/零宽/全角） ----------


def test_cn_numeral_price_hallucination_rejected():
    """I-1: 中文数字编价位不得静默通过（一千九=1900、八千五=8500 均需校验）。"""
    ok, reason = verify_numeric_grounding(
        "关键位一千九，跌破八千五离场", frozenset({1938.56, 8700.0})
    )
    assert not ok and "1900" in reason


def test_cn_numeral_matches_whitelist():
    ok, _ = verify_numeric_grounding("反弹至八千七百点附近", frozenset({8700.0}))
    assert ok  # 八千七百 -> 8700


def test_cn_numeral_unparseable_skipped_not_misparsed():
    """吃不准就跳过（跳过=不校验），绝不解析错：年份式「二零二六」不产出数字。"""
    assert extract_market_numbers("二零二六年复盘") == []


def test_thousands_separator_kept_as_one_number():
    """I-2: 1,938.56 是一个数，不是 1 和 938.56。"""
    assert extract_market_numbers("EMA20 为 1,938.56") == [1938.56]
    ok, _ = verify_numeric_grounding("EMA20 为 1,938.56", frozenset({1938.56}))
    assert ok


def test_scientific_notation_matches_whitelist():
    """I-2: 1.93856e3 = 1938.56，应与白名单对上。"""
    assert 1938.56 in extract_market_numbers("EMA20 约 1.93856e3")
    ok, _ = verify_numeric_grounding("EMA20 约 1.93856e3", frozenset({1938.56}))
    assert ok


def test_scientific_notation_hallucination_rejected():
    ok, _ = verify_numeric_grounding("目标 4.321e3", frozenset({1938.56}))
    assert not ok  # 4321 幻觉价位


def test_fullwidth_hallucination_rejected():
    ok, reason = verify_numeric_grounding("关键位４３２１", frozenset({1938.56}))
    assert not ok and "4321" in reason


def test_zero_width_digit_split_hallucination_rejected():
    """零宽字符切数字（43\u200b21）不得绕过。"""
    ok, reason = verify_numeric_grounding(
        "关键位 43\u200b21", frozenset({8700.0})
    )
    assert not ok and "4321" in reason


def test_zero_width_inside_whitelisted_number_still_passes():
    ok, _ = verify_numeric_grounding("关键位 87\u200b00", frozenset({8700.0}))
    assert ok  # 剔零宽后 8700 与白名单对上
