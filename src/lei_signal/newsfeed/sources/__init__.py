"""newsfeed 数据源包。约定：

每个 collect_* 返回 ``(items, new_watermark)``；水位为 None 表示本轮无新内容
（调用方不更新水位）。失败统一抛 :class:`NewsSourceError`，由管线降级记录。
"""
from __future__ import annotations


class NewsSourceError(RuntimeError):
    """单个源抓取失败（网络/风控/解析）。管线捕获后继续其他源。"""


__all__ = ["NewsSourceError"]
