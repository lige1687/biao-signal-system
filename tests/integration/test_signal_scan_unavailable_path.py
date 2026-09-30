"""unavailable 语义验收：数据不足 -> 显式 unavailable 行，不伪装为无信号（J1/S2）。

契约：docs/archive/handoffs-plans/2026-09-19-arch-j1-contract.json G3。
承载路径：src/lei_signal/api/signal_scan.py::run_signal_scan —— 买点走
routes/opportunities.run_opportunity_scan，同轮用 refresh=False 读同一份
服务缓存做卖点提取与 unavailable 落库（signal_alerts 表）。

与既有 tests/unit/test_signal_scan.py 的差别：那里用 _FakeService 桩服务层；
这里用**真实 AnalysisService**（analyze_fn 注入冻结样本）——数据不足的
DataUnavailableError 由生产管线 analyze_bars 的 MIN_BARS=21 门槛抛出，
经服务层错误隔离与 _classify_error 透传，再由 signal_scan 显式落
SIDE_UNAVAILABLE 行，全链路无桩。

「不伪装为 no_signal」的对照设计：
- 数据健康且无卖点信号的标的 -> signal_alerts **零行**（缺席 = 无信号）；
- 数据不可用的标的 -> signal_alerts **显式一行** side=unavailable /
  kind=data_unavailable / tier=hard + error 原文（在场且可分辨）。
"""
from __future__ import annotations

from contextlib import closing

from lei_signal.api.opportunity_scan import list_scan, today_date
from lei_signal.api.services import AnalysisService
from lei_signal.api.signal_alerts_store import (
    SIDE_SELL,
    SIDE_UNAVAILABLE,
    get_scan_as_of,
    list_signal_alerts,
)
from lei_signal.api.signal_scan import run_signal_scan
from lei_signal.storage.sqlite_store import connect
from tests.golden.scan_entry_samples import (
    SYMBOL_CANDIDATE,
    SYMBOL_UNAVAILABLE,
    stub_analyze,
)

#: 与双入口护栏共享的冻结锚点：生产门槛错误原文关键词
_UNAVAILABLE_ERROR_KEYWORDS = ("只有 10 根日K线", "21 根")


def test_unavailable_row_explicit_not_disguised_as_no_signal(tmp_path) -> None:  # noqa: ANN001
    db = str(tmp_path / "lab.db")
    service = AnalysisService(
        analyze_fn=stub_analyze, sqlite_path=db, ttl_seconds=900
    )
    summary = run_signal_scan(
        service, db, symbols=[SYMBOL_CANDIDATE, SYMBOL_UNAVAILABLE], as_of="close",
    )

    assert summary["scanned"] == 2
    assert summary["unavailable"] == 1
    assert summary["sell_rows"] == 0  # 候选样本健康上行，无卖点事件

    with closing(connect(db)) as conn:
        # --- signal_alerts：unavailable 显式在场，no_signal 以缺席表达 ---
        unavailable = list_signal_alerts(conn, today_date(), side=SIDE_UNAVAILABLE)
        assert [r.symbol for r in unavailable] == [SYMBOL_UNAVAILABLE]
        row = unavailable[0]
        assert row.kind == "data_unavailable"
        assert row.tier == "hard"
        assert row.title == "数据不可用"
        for keyword in _UNAVAILABLE_ERROR_KEYWORDS:
            assert keyword in (row.error or ""), f"error 文案漂移: {row.error!r}"

        sell = list_signal_alerts(conn, today_date(), side=SIDE_SELL)
        assert sell == []
        # 对照：健康标的没有任何一行（它的「无信号」= 行缺席，而非 unavailable 行）；
        # 直接查全表（排除 as_of 元数据行 side=meta，symbol 为空串），不经 side 过滤。
        all_rows = conn.execute(
            "SELECT symbol, side FROM signal_alerts "
            "WHERE scan_date = ? AND side != 'meta'",
            (today_date(),),
        ).fetchall()
        assert {(r["symbol"], r["side"]) for r in all_rows} == {
            (SYMBOL_UNAVAILABLE, SIDE_UNAVAILABLE),
        }

        # as_of meta 行照写（signal_scan 落库完整性）
        assert get_scan_as_of(conn, today_date()) == "close"

        # --- 买点表：unavailable 以 none+error 表达（既有编排语义，记录）---
        buy_rows = {r.symbol: r for r in list_scan(conn, today_date())}
        assert buy_rows[SYMBOL_UNAVAILABLE].verdict == "none"
        assert buy_rows[SYMBOL_UNAVAILABLE].error is not None
        for keyword in _UNAVAILABLE_ERROR_KEYWORDS:
            assert keyword in (buy_rows[SYMBOL_UNAVAILABLE].error or "")
        # 健康候选不受不可用标的拖累，判定照常
        assert buy_rows[SYMBOL_CANDIDATE].verdict == "waiting"
        assert buy_rows[SYMBOL_CANDIDATE].error is None
