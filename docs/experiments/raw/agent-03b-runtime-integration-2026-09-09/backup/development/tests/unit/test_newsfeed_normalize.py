"""newsfeed 归一化（dedupe/粗筛/标的匹配）单元测试。"""
from __future__ import annotations

from lei_signal.newsfeed.normalize import (
    compute_dedupe_key,
    match_symbols,
    preclassify,
    title_norm,
)

_KEYWORDS = {
    "macro": ["央行", "美联储", "LPR"],
    "risk": ["危机", "关税"],
    "policy": ["国务院", "证监会"],
    "industry": ["财报", "营收"],
}


def test_title_norm_strips_punct_and_brackets() -> None:
    assert title_norm("【央行】 降准 —— 0.5个百分点") == "央行降准05个百分点"


def test_dedupe_key_url_wins_and_title_norm_stable() -> None:
    assert compute_dedupe_key("eastmoney", "http://x/1", "任意") == compute_dedupe_key(
        "eastmoney", "http://x/1", "完全不同"
    )
    # 标题仅差标点/空格 → 同 key
    assert compute_dedupe_key("sina", None, "【美联储】加息") == compute_dedupe_key(
        "sina", None, "美联储加息"
    )
    assert compute_dedupe_key("sina", None, "a") != compute_dedupe_key("eastmoney", None, "a")


def test_preclassify_categories() -> None:
    assert preclassify("央行开展逆回购操作", _KEYWORDS, []) == "macro"
    assert preclassify("美国对华关税升级", _KEYWORDS, []) == "risk"
    assert preclassify("国务院常务会议召开", _KEYWORDS, []) == "policy"
    # 纯噪音 → None（不入库）
    assert preclassify("某公司发布公告更换审计机构", _KEYWORDS, []) is None
    # 无关键词但命中标的 → industry
    assert preclassify("英伟达发布新品", _KEYWORDS, ["英伟达"]) == "industry"
    # 并列取 FLASH_CATEGORIES 顺序先者（macro 在 industry 前）
    assert preclassify("美联储财报", _KEYWORDS, []) == "macro"


def test_match_symbols_case_insensitive_and_cap() -> None:
    assert match_symbols("NVDA and amd rally", ["nvda", "AMD"]) == ["nvda", "AMD"]
    assert match_symbols("中际旭创获大单", ["中际旭创", "新易盛", "天孚", "太辰光"]) == ["中际旭创"]
    assert match_symbols("无关文本", ["NVDA"]) == []
