"""newsfeed 统一条目模型。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class NewsItem:
    """各源归一化后的最小公共条目。dedupe_key 由 normalize.compute_dedupe_key 生成。"""

    source: str  # eastmoney|sina|gnews|wechat|bilibili
    title: str
    published_at: str  # ISO8601 带时区
    url: str | None = None
    source_name: str | None = None
    summary: str | None = None
    content: str | None = None
    category: str | None = None
    dedupe_key: str = ""

    def to_row(self) -> dict:
        return {
            "source": self.source,
            "source_name": self.source_name,
            "url": self.url,
            "title": self.title,
            "summary": self.summary,
            "content": self.content,
            "category": self.category,
            "published_at": self.published_at,
            "dedupe_key": self.dedupe_key,
        }


__all__ = ["NewsItem"]
