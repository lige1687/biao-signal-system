"""消息内标的提取：全局会话里用户报代码自动带材料（中文语境抽取 + 排序 + 继承）。"""
from __future__ import annotations

import json
from dataclasses import dataclass

from lei_signal.api.routes.agent import (
    _SYMBOL_TOKEN_RE,
    _last_resolved_symbol,
    _resolve_symbol_from_message,
)


@dataclass
class _Msg:
    role: str
    meta_json: str


class _OkService:
    """任何代码都分析成功（用于验证 resolve 路径）。"""

    def get(self, symbol: str):  # noqa: ANN202
        @dataclass
        class _E:
            result: object = object()
        return _E()


class _FailService:
    def get(self, symbol: str):  # noqa: ANN202
        @dataclass
        class _E:
            result: object = None
            error: str = "no data"
        return _E()


def test_extract_from_chinese_context():
    assert _SYMBOL_TOKEN_RE.findall("那515880那个怎么样") == ["515880"]
    assert _SYMBOL_TOKEN_RE.findall("看看512890.SS呗") == ["512890.SS"]
    assert _SYMBOL_TOKEN_RE.findall("TH881157.SECTOR 呢") == ["TH881157"]  # 后缀留给 resolve 补


def test_extract_letter_etf():
    assert "IGV" in _SYMBOL_TOKEN_RE.findall("看看IGV呗")
    assert "SOXX" in _SYMBOL_TOKEN_RE.findall("SOXX如何")


def test_indicator_words_not_extracted():
    # MA20/EMA20/KDJ：字母后紧跟数字，lookahead 拒绝；普通词不构成代码形态
    assert _SYMBOL_TOKEN_RE.findall("MA20和EMA20是什么") == []
    assert _SYMBOL_TOKEN_RE.findall("今天天气不错") == []


def test_resolve_prefers_numeric_over_letters():
    got = _resolve_symbol_from_message("IGV 和 515880 比一下", _OkService())
    assert got == "515880.SS"  # 含数字候选优先于纯字母


def test_resolve_normalizes_bare_code():
    assert _resolve_symbol_from_message("515880那个", _OkService()) == "515880.SS"


def test_resolve_returns_none_when_analysis_fails():
    assert _resolve_symbol_from_message("515880那个", _FailService()) is None


def test_inherit_from_last_assistant_meta():
    rows = [
        _Msg("user", "{}"),
        _Msg("assistant", json.dumps({"resolved_symbol": "515880.SS"})),
    ]
    assert _last_resolved_symbol(rows) == "515880.SS"
    assert _last_resolved_symbol([_Msg("user", "{}")]) is None
    assert _last_resolved_symbol([_Msg("assistant", "not-json")]) is None
