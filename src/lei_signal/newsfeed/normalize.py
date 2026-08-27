"""归一化：去重键、快讯关键词粗筛、标的实体匹配。纯函数无 IO。"""
from __future__ import annotations

import hashlib
import re

#: 快讯粗筛支持的类别（blogger 由来源直接指定，不参与粗筛）。
FLASH_CATEGORIES = ("macro", "risk", "policy", "industry")

_PUNCT = re.compile(r"[\s【】\[\]（）()：:，,。.!！?？'\"`~·\-—_/\\|]+")


def title_norm(title: str) -> str:
    """标题归一化：去空白与常见标点，用于无 URL 条目的 dedupe。"""
    return _PUNCT.sub("", title)


def compute_dedupe_key(source: str, url: str | None, title: str) -> str:
    """有 URL 用 URL，无 URL 用 source+归一化标题。"""
    raw = url if url else f"{source}|{title_norm(title)}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def match_symbols(text: str, symbols: list[str]) -> list[str]:
    """配置的重点标的大小写不敏感命中，最多 3 个。"""
    hit = [s for s in symbols if s and s.lower() in text.lower()]
    return hit[:3]


def preclassify(
    text: str, keywords: dict[str, list[str]], symbols: list[str]
) -> str | None:
    """快讯粗筛：各类关键词命中计 1 分，标的命中给 industry 加 2 分。

    返回得分最高的类别（并列取 FLASH_CATEGORIES 顺序先者）；0 分返回
    None——调用方据此丢弃该条（控制入库量与 LLM 成本）。
    """
    scores = {k: 0 for k in FLASH_CATEGORIES}
    for cat, kws in keywords.items():
        if cat not in scores:
            continue
        scores[cat] += sum(1 for kw in kws if kw and kw in text)
    if match_symbols(text, symbols):
        scores["industry"] += 2
    best: str | None = None
    best_score = 0
    for cat in FLASH_CATEGORIES:
        if scores[cat] > best_score:
            best = cat
            best_score = scores[cat]
    return best


__all__ = [
    "FLASH_CATEGORIES",
    "compute_dedupe_key",
    "match_symbols",
    "preclassify",
    "title_norm",
]
