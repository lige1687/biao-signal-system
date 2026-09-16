"""意图路由与报单文本解析（规则层，零 LLM）。"""
from __future__ import annotations

import pytest

from lei_signal.copilot.intent import parse_intent, parse_trade_report


def test_intent_recommend():
    for msg in ("今天看什么", "有什么推荐", "今天有什么机会标的"):
        assert parse_intent(msg).kind == "recommend"


def test_intent_holdings():
    assert parse_intent("看下我的持仓").kind == "holdings"
    assert parse_intent("持仓速览").kind == "holdings"


def test_intent_trade_report():
    assert parse_intent("我昨天买了1万515880").kind == "trade_report"
    assert parse_intent("卖了5000块纳斯达克基金").kind == "trade_report"


def test_intent_review():
    assert parse_intent("本周复盘").kind == "review"
    assert parse_intent("看看上周复盘").kind == "review"


def test_intent_chat_fallback():
    assert parse_intent("515880 这个买点为什么是买点").kind == "chat"
    assert parse_intent("市场环境怎么样").kind == "chat"


def test_trade_report_buy_with_code_and_amount():
    p = parse_trade_report("我昨天买了1万515880", today="2026-09-05")
    assert p.side == "buy"
    assert p.fund_code == "515880"
    assert p.amount == pytest.approx(10000.0)
    assert p.trade_date == "2026-09-04"


def test_trade_report_sell_with_wan_and_k():
    assert parse_trade_report(
        "卖了1.5万白酒基金", today="2026-09-05"
    ).amount == pytest.approx(15000.0)
    assert parse_trade_report(
        "买了2k货币基金", today="2026-09-05"
    ).amount == pytest.approx(2000.0)


def test_trade_report_name_extraction_and_missing():
    p = parse_trade_report("我买了5000块的纳斯达克100基金", today="2026-09-05")
    assert p.side == "buy"
    assert p.amount == pytest.approx(5000.0)
    assert "纳斯达克100" in (p.fund_name or "")
    assert "fund_code" in p.missing  # 没给代码，确认卡里补


def test_trade_report_today_default():
    p = parse_trade_report("买了1万515880", today="2026-09-05")
    assert p.trade_date == "2026-09-05"


def test_trade_report_amount_missing():
    p = parse_trade_report("我买了点515880", today="2026-09-05")
    assert "amount" in p.missing
