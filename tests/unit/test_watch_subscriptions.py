"""watch_subscription: 迁移 013 幂等 + CRUD + 命中判定 + 状态机.

覆盖:
  - migration 013 应用幂等, 不会重复执行
  - create/list/get/dismiss roundtrip
  - 重复订阅 (同 symbol/level/source_rule_id/watch_kind 在 live 状态) 返回已有行
  - mark_triggered active -> pending_confirmation 一次性写 triggered_*
  - mark_triggered 二次跑到不覆盖 triggered_at
  - dismiss active / pending 都能转 dismissed
  - evaluate_hit 命中容差 (±0.5%)
"""
from __future__ import annotations

from lei_signal.api import watch_subscriptions as ws
from lei_signal.storage.sqlite_store import connect


def test_migration_013_applies_idempotently(tmp_path) -> None:
    db = tmp_path / "lab.db"
    conn = connect(db)
    conn.close()
    # 第二次 connect 重复应用迁移不得报错
    conn = connect(db)
    try:
        row = conn.execute(
            "SELECT name FROM schema_migrations WHERE ordinal = 13"
        ).fetchone()
        assert row is not None
        # 表与索引确实存在
        assert conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='watch_subscriptions'"
        ).fetchone() is not None
    finally:
        conn.close()


def test_create_list_get_dismiss_roundtrip(tmp_path) -> None:
    conn = connect(tmp_path / "lab.db")
    try:
        w = ws.create_watch(
            conn, symbol="600519.SS", direction="long", module="A",
            watch_kind="price", watch_text_cn="回踩 1500 算买点",
            level=1500.0, source_rule_id="dual_ma_bull_confirmed",
            as_signal_rule_ids=("dual_ma_bull_confirmed",),
        )
        assert w.state == ws.WATCH_ACTIVE
        assert w.symbol == "600519.SS"
        assert w.level == 1500.0
        assert w.as_signal_rule_ids == ("dual_ma_bull_confirmed",)

        # list 默认只列 live
        items = ws.list_watches(conn)
        assert len(items) == 1
        assert items[0].watch_id == w.watch_id

        # 按 symbol 过滤
        items = ws.list_watches(conn, symbol="600519.SS")
        assert len(items) == 1

        # 拉空
        assert ws.list_watches(conn, symbol="OTHER") == []

        # get
        got = ws.get_watch(conn, w.watch_id)
        assert got is not None
        assert got.watch_text_cn == "回踩 1500 算买点"

        # dismiss
        dismissed = ws.mark_dismissed(conn, w.watch_id, reason="测试取消")
        assert dismissed is not None
        assert dismissed.state == ws.WATCH_DISMISSED
        assert dismissed.dismissed_reason == "测试取消"
        assert dismissed.dismissed_at is not None

        # dismiss 后 live 默认过滤掉
        assert ws.list_watches(conn) == []
        # 但显式查 dismissed 能查到
        items = ws.list_watches(conn, filter_states=(ws.WATCH_DISMISSED,))
        assert len(items) == 1
    finally:
        conn.close()


def test_duplicate_subscribe_returns_existing(tmp_path) -> None:
    """同 (symbol, level, source_rule_id, watch_kind) 在 live 状态视为同一订阅."""
    conn = connect(tmp_path / "lab.db")
    try:
        w1 = ws.create_watch(
            conn, symbol="600519.SS", direction="long", module="A",
            watch_kind="price", watch_text_cn="回踩 1500 算买点", level=1500.0,
        )
        # 重复订阅 (同 symbol/level/rule_id/kind, 但 text_cn 略不同) -> 返回已有
        w2 = ws.create_watch(
            conn, symbol="600519.SS", direction="long", module="A",
            watch_kind="price", watch_text_cn="不一样的话", level=1500.0,
        )
        assert w2.watch_id == w1.watch_id
        assert ws.list_watches(conn) == [w1]

        # 不同 level 应开新行
        w3 = ws.create_watch(
            conn, symbol="600519.SS", direction="long", module="A",
            watch_kind="price", watch_text_cn="另一个", level=1480.0,
        )
        assert w3.watch_id != w1.watch_id
        assert len(ws.list_watches(conn)) == 2

        # dismissed 后可以重新订阅同 level -> 开新行
        ws.mark_dismissed(conn, w1.watch_id, reason="x")
        w4 = ws.create_watch(
            conn, symbol="600519.SS", direction="long", module="A",
            watch_kind="price", watch_text_cn="重新订阅", level=1500.0,
        )
        assert w4.watch_id != w1.watch_id
    finally:
        conn.close()


def test_mark_triggered_advances_to_pending(tmp_path) -> None:
    conn = connect(tmp_path / "lab.db")
    try:
        w = ws.create_watch(
            conn, symbol="600519.SS", direction="long", module="A",
            watch_kind="price", watch_text_cn="x", level=1500.0,
        )
        # active -> pending
        out = ws.mark_triggered(
            conn, w.watch_id,
            triggered_price=1495.0,
            triggered_reason_cn="跌破 level",
            now_iso="2026-08-09T14:46:00+00:00",
        )
        assert out is not None
        assert out.state == ws.WATCH_PENDING
        assert out.triggered_at == "2026-08-09T14:46:00+00:00"
        assert out.triggered_price == 1495.0
        assert out.triggered_reason_cn == "跌破 level"
        assert out.last_checked_at == "2026-08-09T14:46:00+00:00"

        # 二次跑到: mark_triggered 是 one-shot, 已是 pending 时直接返回原值,
        # 不会改 state/triggered_at/price/reason/last_checked_at
        # (决策: 命中是有信号意义的一次性事件, 不应被覆盖)
        out2 = ws.mark_triggered(
            conn, w.watch_id,
            triggered_price=1490.0,
            triggered_reason_cn="继续跌",
            now_iso="2026-08-09T15:00:00+00:00",
        )
        assert out2 is not None
        assert out2.state == ws.WATCH_PENDING
        assert out2.triggered_at == "2026-08-09T14:46:00+00:00"  # 首次时间保留
        assert out2.triggered_price == 1495.0  # 首次价保留
        assert out2.triggered_reason_cn == "跌破 level"  # 首次 reason 保留
        # last_checked_at 也不被二次 mark_triggered 触碰 (no-op on pending state)
    finally:
        conn.close()


def test_dismiss_pending_or_promoted_terminal(tmp_path) -> None:
    """pending 也能 dismiss; promoted 不能 dismiss (终态)."""
    conn = connect(tmp_path / "lab.db")
    try:
        w = ws.create_watch(
            conn, symbol="X", direction="long", module="A",
            watch_kind="price", watch_text_cn="x", level=100.0,
        )
        ws.mark_triggered(
            conn, w.watch_id, triggered_price=99.0, triggered_reason_cn="hit",
        )
        # pending -> dismissed OK
        out = ws.mark_dismissed(conn, w.watch_id, reason="放弃")
        assert out is not None and out.state == ws.WATCH_DISMISSED

        # promoted -> dismissed 不行 (终态)
        w2 = ws.create_watch(
            conn, symbol="Y", direction="long", module="A",
            watch_kind="price", watch_text_cn="y", level=200.0,
        )
        ws.mark_triggered(
            conn, w2.watch_id, triggered_price=199.0, triggered_reason_cn="hit",
        )
        ws.mark_promoted(conn, w2.watch_id, plan_id="plan_test")
        out2 = ws.mark_dismissed(conn, w2.watch_id, reason="尝试")
        assert out2 is not None
        assert out2.state == ws.WATCH_PROMOTED  # 不变
        assert out2.promoted_plan_id == "plan_test"
    finally:
        conn.close()


def test_evaluate_hit_long_threshold() -> None:
    """long: last_close <= level*(1+tol) 命中."""
    from lei_signal.api.watch_subscriptions import WatchSubscription
    w = WatchSubscription(
        watch_id="ws_x", symbol="X", direction="long", module="A",
        source_candidate_id=None, source_rule_id=None, level=100.0,
        watch_kind="price", watch_text_cn="x", as_signal_rule_ids=(),
        state=ws.WATCH_ACTIVE, created_at="", last_checked_at=None,
        triggered_at=None, triggered_price=None, triggered_reason_cn=None,
        promoted_plan_id=None, dismissed_at=None, dismissed_reason=None,
    )
    # 价格刚好 == 阈值 -> 命中
    hit, reason = ws.evaluate_hit(w, 100.0 * 1.005)
    assert hit is True
    # 略高于阈值 -> 不命中
    hit, _ = ws.evaluate_hit(w, 100.0 * 1.01)
    assert hit is False
    # 远低于 level -> 命中
    hit, _ = ws.evaluate_hit(w, 95.0)
    assert hit is True


def test_evaluate_hit_short_threshold() -> None:
    from lei_signal.api.watch_subscriptions import WatchSubscription
    w = WatchSubscription(
        watch_id="ws_x", symbol="X", direction="short", module="A",
        source_candidate_id=None, source_rule_id=None, level=100.0,
        watch_kind="price", watch_text_cn="x", as_signal_rule_ids=(),
        state=ws.WATCH_ACTIVE, created_at="", last_checked_at=None,
        triggered_at=None, triggered_price=None, triggered_reason_cn=None,
        promoted_plan_id=None, dismissed_at=None, dismissed_reason=None,
    )
    # 短: 价 >= level*(1-tol) 命中
    hit, _ = ws.evaluate_hit(w, 100.0 * 0.995)
    assert hit is True
    # 远低于 level -> 不命中
    hit, _ = ws.evaluate_hit(w, 95.0)
    assert hit is False
    # 远高于 level -> 命中 (做空信号)
    hit, _ = ws.evaluate_hit(w, 110.0)
    assert hit is True


def test_evaluate_hit_state_kind_not_implemented() -> None:
    """v1 不接 kind=state, 永远不命中."""
    from lei_signal.api.watch_subscriptions import WatchSubscription
    w = WatchSubscription(
        watch_id="ws_x", symbol="X", direction="long", module="A",
        source_candidate_id=None, source_rule_id=None, level=None,
        watch_kind="state", watch_text_cn="x", as_signal_rule_ids=(),
        state=ws.WATCH_ACTIVE, created_at="", last_checked_at=None,
        triggered_at=None, triggered_price=None, triggered_reason_cn=None,
        promoted_plan_id=None, dismissed_at=None, dismissed_reason=None,
    )
    hit, reason = ws.evaluate_hit(w, 50.0)
    assert hit is False
    assert "TODO" in reason


def test_run_intraday_check_with_mock_quote(tmp_path, monkeypatch) -> None:
    """run_intraday_check 用注入的 quote_provider, 走完整一轮命中."""
    conn_path = str(tmp_path / "lab.db")
    conn = connect(conn_path)
    try:
        w = ws.create_watch(
            conn, symbol="600519.SS", direction="long", module="A",
            watch_kind="price", watch_text_cn="回踩 1500 算买点", level=1500.0,
        )
    finally:
        conn.close()

    class _FakeQuote:
        def __init__(self, price): self.price = price

    class _FakeProvider:
        def __init__(self, price): self._price = price
        def fetch(self, symbol):
            return _FakeQuote(self._price)

    # 价格 1490 < level 1500 -> 命中
    report = ws.run_intraday_check(
        conn_path, quote_provider=_FakeProvider(1490.0), dry_run=False,
    )
    assert report.total_active == 1
    assert len(report.triggered) == 1
    assert report.checked_at  # 写入了

    conn = connect(conn_path)
    try:
        got = ws.get_watch(conn, w.watch_id)
        assert got is not None
        assert got.state == ws.WATCH_PENDING
        assert got.triggered_price == 1490.0
    finally:
        conn.close()


def test_run_intraday_check_no_hit_updates_only_last_checked(tmp_path) -> None:
    """未命中只更新 last_checked_at, state 不变."""
    conn_path = str(tmp_path / "lab.db")
    conn = connect(conn_path)
    try:
        w = ws.create_watch(
            conn, symbol="600519.SS", direction="long", module="A",
            watch_kind="price", watch_text_cn="x", level=1500.0,
        )
    finally:
        conn.close()

    class _FakeQuote:
        def __init__(self, price): self.price = price

    class _FakeProvider:
        def fetch(self, symbol): return _FakeQuote(2000.0)  # 远高于 level

    report = ws.run_intraday_check(
        conn_path, quote_provider=_FakeProvider(), dry_run=False,
    )
    assert report.total_active == 1
    assert report.triggered == []

    conn = connect(conn_path)
    try:
        got = ws.get_watch(conn, w.watch_id)
        assert got is not None
        assert got.state == ws.WATCH_ACTIVE
        assert got.last_checked_at is not None
        assert got.triggered_at is None
    finally:
        conn.close()
