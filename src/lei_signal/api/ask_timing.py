"""提问分段计时（2026-09-15 agent-ask-stability）。

一轮问答从「收到问题」到「回答保存」曾约 162 秒，日志只有起止、没有
分段——无法回答「慢在哪一段」。本模块提供零依赖的分段计时：

- ``mark(name)``：阶段到达点（相对请求开始的偏移毫秒）；
- ``span(name)``：准备段内部的耗时块（同名多次累计，如多次读库）；
- ``summary()``：一次性结构化汇总，供服务端日志与流式 done 下发。

六段口径（任务书 §一）：收到问题 → 请求身份登记 → 行情与系统分析准备
→ 第一份有用资料展示 → 模型开始输出正文 → 回答完成并保存。
日志只含会话号、标的与耗时——不含问题原文、密钥或 SQL 参数。
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any

__all__ = ["AskTiming", "NULL_TIMING"]


class AskTiming:
    """单请求分段计时（单线程内使用；准备线程与生成器间按引用传递）。"""

    def __init__(self) -> None:
        self._t0 = time.perf_counter()
        self.marks: dict[str, int] = {}   # name -> 相对开始的偏移 ms
        self.spans: dict[str, int] = {}   # name -> 累计耗时 ms

    def mark(self, name: str) -> None:
        self.marks[name] = int((time.perf_counter() - self._t0) * 1000)

    @contextmanager
    def span(self, name: str):  # noqa: ANN201
        started = time.perf_counter()
        try:
            yield
        finally:
            self.spans[name] = self.spans.get(name, 0) + int(
                (time.perf_counter() - started) * 1000)

    def summary(self) -> dict[str, Any]:
        return {
            "total_ms": int((time.perf_counter() - self._t0) * 1000),
            "marks_ms": dict(self.marks),
            "spans_ms": dict(self.spans),
        }


class _NullTiming:
    """不计时的空实现（非流式路径/缺省），与 AskTiming 同接口。"""

    def mark(self, name: str) -> None:  # noqa: ARG002
        return None

    @contextmanager
    def span(self, name: str):  # noqa: ANN002, ANN201
        yield

    def summary(self) -> dict[str, Any]:
        return {}


NULL_TIMING = _NullTiming()
