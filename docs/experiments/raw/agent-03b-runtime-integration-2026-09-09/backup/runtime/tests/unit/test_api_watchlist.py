"""自选股存储：迁移 7 幂等 + CRUD 回环。"""
from __future__ import annotations

from lei_signal.api.watchlist import delete_watchlist, list_watchlist, upsert_watchlist
from lei_signal.storage.sqlite_store import connect


def test_migration_007_applies_idempotently(tmp_path) -> None:
    db = tmp_path / "lab.db"
    conn = connect(db)
    conn.close()
    # 第二次 connect 重复应用迁移不得报错
    conn = connect(db)
    try:
        row = conn.execute(
            "SELECT name FROM schema_migrations WHERE ordinal = 7"
        ).fetchone()
        assert row is not None
    finally:
        conn.close()


def test_upsert_list_delete_roundtrip(tmp_path) -> None:
    conn = connect(tmp_path / "lab.db")
    try:
        item = upsert_watchlist(
            conn, symbol="159915.SZ", display_name=None, market="cn_sz", note="创业板"
        )
        assert item.sort_order == 1
        again = upsert_watchlist(
            conn, symbol="159915.SZ", display_name="创业板ETF", market="cn_sz", note=None
        )
        # 重复添加保留原 sort_order 与 added_at，更新名称
        assert again.sort_order == 1
        assert again.added_at == item.added_at
        assert again.display_name == "创业板ETF"

        upsert_watchlist(conn, symbol="QQQ", display_name=None, market="us", note=None)
        items = list_watchlist(conn)
        assert [i.symbol for i in items] == ["159915.SZ", "QQQ"]
        assert items[1].sort_order == 2

        assert delete_watchlist(conn, "159915.SZ") is True
        assert delete_watchlist(conn, "159915.SZ") is False  # 幂等
        assert [i.symbol for i in list_watchlist(conn)] == ["QQQ"]
    finally:
        conn.close()


def test_group_crud_and_delete_preserves_symbols(tmp_path) -> None:
    """分组增删改 + 删组时成员转为未分组（不能连带删掉自选标的）。"""
    from lei_signal.api.watchlist import (
        create_group,
        delete_group,
        list_groups,
        move_to_group,
        rename_group,
    )

    conn = connect(tmp_path / "lab.db")
    try:
        tech = create_group(conn, "科技")
        defense = create_group(conn, "防御")
        assert [g.name for g in list_groups(conn)] == ["科技", "防御"]
        # 同名幂等，不新建
        assert create_group(conn, "科技").group_id == tech.group_id

        upsert_watchlist(
            conn, symbol="QQQ", display_name=None, market="us", group_id=tech.group_id
        )
        upsert_watchlist(
            conn, symbol="510300.SS", display_name=None, market="cn_sh",
            group_id=defense.group_id,
        )
        assert {i.symbol: i.group_id for i in list_watchlist(conn)} == {
            "QQQ": tech.group_id,
            "510300.SS": defense.group_id,
        }

        assert rename_group(conn, tech.group_id, "科技成长") is True
        assert "科技成长" in [g.name for g in list_groups(conn)]

        assert move_to_group(conn, "510300.SS", tech.group_id) is True
        assert move_to_group(conn, "NOT_THERE", tech.group_id) is False

        # 删组：标的必须保留，只是变成未分组
        assert delete_group(conn, tech.group_id) is True
        items = {i.symbol: i.group_id for i in list_watchlist(conn)}
        assert items == {"QQQ": None, "510300.SS": None}, "删组不得删除标的"
        assert delete_group(conn, tech.group_id) is False  # 幂等

        # 空组名拒绝
        import pytest

        with pytest.raises(ValueError):
            create_group(conn, "   ")
    finally:
        conn.close()
