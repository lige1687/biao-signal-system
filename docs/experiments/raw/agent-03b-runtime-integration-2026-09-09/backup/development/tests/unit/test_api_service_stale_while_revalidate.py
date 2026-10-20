"""AnalysisService.get 的 stale-while-revalidate 行为测试（无网络）。

读请求在 per-symbol 锁被后台刷新（预热/他人 refresh）持有时：
- 已有条目（哪怕过期）先返回，不排队等待；
- 冷缓存（无条目）照常阻塞等首份数据；
- refresh=True 始终强刷，不受该优化影响。
"""
from __future__ import annotations

import threading
import time
from typing import Any

from lei_signal.api.services import AnalysisService

_SYMBOL = "^IXIC"  # 海外指数：走扁平 TTL 路径，ttl=0 时永远视为过期，不受时段感知影响


def _make_service(ttl_seconds: int) -> tuple[AnalysisService, dict[str, Any]]:
    """analyze_fn 可切换「立即返回 / 阻塞到放行」两种模式。"""
    control: dict[str, Any] = {"blocking": False, "started": threading.Event(),
                               "release": threading.Event()}
    lock = threading.Lock()
    calls: list[str] = []

    def analyze(symbol: str, **kwargs: Any) -> object:
        with lock:
            calls.append(symbol)
        if control["blocking"]:
            control["started"].set()
            control["release"].wait(timeout=10)
        return object()

    service = AnalysisService(analyze_fn=analyze, ttl_seconds=ttl_seconds)
    return service, control


def test_read_returns_stale_entry_while_refresh_in_flight() -> None:
    """锁被 refresh 持有 + 已有条目：读请求拿旧数据立即返回，不排队。"""
    service, control = _make_service(ttl_seconds=0)
    first = service.get(_SYMBOL)  # 首份（ttl=0，之后永远算过期）

    control["blocking"] = True
    refresher = threading.Thread(target=lambda: service.get(_SYMBOL, refresh=True))
    refresher.start()
    assert control["started"].wait(timeout=5)  # refresher 已进入 analyze（持锁中）

    t0 = time.monotonic()
    got = service.get(_SYMBOL)  # 读请求：应立即返回旧条目
    elapsed = time.monotonic() - t0

    assert got is first
    assert elapsed < 2.0
    assert refresher.is_alive()  # 刷新仍在后台进行

    control["release"].set()
    refresher.join(timeout=5)
    assert not refresher.is_alive()


def test_read_blocks_for_first_data_on_cold_cache() -> None:
    """锁被持 + 无条目：读请求必须等首份数据出来（不能返回空）。"""
    service, control = _make_service(ttl_seconds=0)
    control["blocking"] = True

    first_getter = threading.Thread(target=lambda: service.get(_SYMBOL))
    first_getter.start()
    assert control["started"].wait(timeout=5)  # 首个请求持锁抓取中

    result: dict[str, Any] = {}

    def reader() -> None:
        result["entry"] = service.get(_SYMBOL)

    second = threading.Thread(target=reader)
    second.start()
    time.sleep(0.5)
    assert "entry" not in result  # 冷缓存：不允许提前返回

    control["release"].set()
    first_getter.join(timeout=5)
    second.join(timeout=5)
    assert result["entry"] is not None


def test_refresh_true_bypasses_fresh_cache() -> None:
    """缓存新鲜时 refresh=True 仍强刷（手动刷新按钮依赖此语义）。"""
    service, _ = _make_service(ttl_seconds=900)
    v1 = service.get(_SYMBOL)
    v2 = service.get(_SYMBOL)  # 新鲜，直接命中
    assert v2 is v1
    v3 = service.get(_SYMBOL, refresh=True)
    assert v3 is not v1
