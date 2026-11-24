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


# ---- 意图路由扩展（2026-09-19，agent-intent-routing）用例矩阵 ----

def test_intent_dca():
    for msg in ("现在能定投吗", "这个ETF适合定投吗", "开始分批投沪深300"):
        assert parse_intent(msg).kind == "dca"


def test_intent_sentiment():
    for msg in ("市场情绪怎么样", "市场恐慌了吗", "现在散户热不热"):
        assert parse_intent(msg).kind == "sentiment"


def test_intent_mindset_recognized_no_fallback_when_seeds_present():
    # 识别成功、种子库在场（configs/mindset_seed.json 已入仓）：不带回落标注
    for msg in ("最近拿不住怎么办", "心态崩了", "跌得睡不着"):
        i = parse_intent(msg)
        assert i.kind == "mindset"
        assert i.fallback_reason is None


def test_intent_mindset_fallback_when_seeds_missing(monkeypatch):
    # 种子库缺位：识别成功但带显式回落原因（回落发生在 dispatch 层），
    # 行为与接入前缺位场景一致
    monkeypatch.setattr("lei_signal.copilot.intent._mindset_seeds_ok", lambda: False)
    i = parse_intent("心态崩了")
    assert i.kind == "mindset"
    assert i.fallback_reason == "mindset_seed_missing"


def test_intent_new_kinds_negative():
    # 否定用例：不含任何新词表词，不得命中新三类
    assert parse_intent("设置提醒").kind == "chat"
    assert parse_intent("今天大盘为什么跌").kind == "chat"
    assert parse_intent("换一种止损方式").kind == "chat"
    assert parse_intent("这只基金规模多大").kind == "chat"
    assert parse_intent("工资到账了怎么安排").kind == "chat"  # 「工资」不在 dca 窄词表


def test_intent_cross_priority():
    # 旧五类前位优先（追加式扩展的构造性质）
    assert parse_intent("推荐个适合定投的ETF").kind == "recommend"
    assert parse_intent("我昨天申购了定投500元515880").kind == "trade_report"
    assert parse_intent("市场情绪恐慌，看下我的持仓").kind == "holdings"
    # sentiment 先于 mindset（与 resolve.py 话题词表同序的既定取舍）
    assert parse_intent("情绪不好，睡不着").kind == "sentiment"
    # 无否定处理既有局限：「别定投了」与「别买了」同层定位，命中 dca
    assert parse_intent("别定投了，风险太大").kind == "dca"
    # 「每月」不在 dca 窄词表，review 前位优先
    assert parse_intent("每月复盘一次").kind == "review"


def test_intent_old_chat_has_no_fallback_reason():
    i = parse_intent("市场环境怎么样")
    assert i.kind == "chat"
    assert i.fallback_reason is None  # 真未命中：不带新回落原因


def test_intent_no_hidden_session_state():
    # dispatch 逐条独立判定，无跨消息上下文（上下文承接归 agent 入口）
    seq = ["现在能定投吗", "515880 呢", "买了1万515880"]
    assert [parse_intent(m).kind for m in seq] == ["dca", "chat", "trade_report"]
