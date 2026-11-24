import json
from types import SimpleNamespace

import pytest

from lei_signal.api.routes.agent import _user_background


def rows(texts):
    out = []
    for i, text in enumerate(texts, 1):
        out += [
            SimpleNamespace(role="user", content=text, message_id=i, meta_json=None),
            SimpleNamespace(
                role="assistant",
                content="",
                question_id=i,
                meta_json=json.dumps({"resolved_symbol": "515880.SS"}),
            ),
        ]
    return out


def background(*texts):
    return _user_background(rows(texts), "515880.SS")


@pytest.mark.parametrize(
    "text",
    [
        "朋友昨天操作了，已经清仓",
        "朋友昨天操作了。已经清仓",
        "如果以后有钱，每月定投",
        "假设我已经持有，现在清仓",
        "朋友有一万元闲钱，每月定投",
        "朋友手里有，重仓持有着",
    ],
)
def test_foreign_hypothesis_never_updates(text):
    before = background("我已经持有了", "我有一万闲钱")
    assert background("我已经持有了", "我有一万闲钱", text) == before


@pytest.mark.parametrize("text", ["十万闲钱", "三千元", "已经清仓", "每月定投"])
def test_unowned_standalone_not_memorized(text):
    assert background(text) == {}


def test_explicit_self_switch_and_update_order():
    assert not background("我已经持有了", "朋友还持有，但我已清仓").get("holding")
    assert background("我清仓了，但我又已经持有了")["holding"] is True
    assert background("我有一万闲钱", "我没有闲钱，这是每月工资定投")["purpose"] == "income_dca"


def test_purpose_clear_without_new_purpose():
    assert background("我每月工资定投", "我不定投了").get("purpose") is None


def test_correction_needs_previous_value():
    assert background("不是一万，是五千") == {}
    assert background("我有一万闲钱", "不是一万，是五千")["budget"]["amount"] == 5000


def test_ambiguous_bindings_not_last_answer_wins():
    h = rows(["我已经持有了"])
    h += [
        SimpleNamespace(
            role="assistant",
            content="",
            question_id=1,
            meta_json=json.dumps({"resolved_symbol": "510300.SS"}),
        )
    ]
    assert _user_background(h, "510300.SS") == {}


def test_backtest_intent_shared_with_frontend():
    from pathlib import Path

    from lei_signal.copilot.resolve import parse_request

    cases = json.loads(Path("tests/fixtures/agent_semantics/atr_intents.json").read_text())
    for case in cases:
        assert (parse_request(case["text"])["intent"] == "backtest_request") == case["backtest"], (
            case["text"]
        )


@pytest.mark.parametrize(
    "text",
    [
        "我有五千元预算？",
        "我是不是有五千元预算",
        "我下个月会有五千元预算",
        "我打算以后投入，每月五千",
    ],
)
def test_questions_and_future_preserve_current(text):
    assert background("我有一万闲钱", text) == background("我有一万闲钱")


def test_conjunction_keeps_update_order():
    assert background("我清仓了但我又已经持有了")["holding"] is True

@pytest.mark.parametrize('text', ['我有五千元预算吗', '我已经持有了吗'])
def test_question_without_punctuation_is_not_a_fact(text):
    before = background('我有一万闲钱')
    assert background('我有一万闲钱', text) == before
