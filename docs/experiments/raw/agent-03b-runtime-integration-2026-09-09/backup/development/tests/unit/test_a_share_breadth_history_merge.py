"""get_ma_breadth_history 读侧合并（33 年全史 + live 尾部）的口径测试。

背景：A股宽度趋势图 2021 年之前空缺——live 历史被 [-max_points:] 截断在
~1260 交易日，而 1993 起的研究全史落在单独文件无人读。修法是读侧拼接：
全史铺底（只取 live 起点之前的日期），live 接管其后（重叠日期 live 为准）。
"""

from pathlib import Path

from lei_signal.market_context import a_share_breadth as asb


def _write(path: Path, rows: list[dict]) -> None:
    import json

    path.write_text(json.dumps(rows), encoding="utf-8")


def test_merge_full_history_before_live_start(tmp_path, monkeypatch):
    monkeypatch.setenv("LEI_CACHE_ROOT", str(tmp_path))
    _write(
        tmp_path / "a_share_ma_breadth_full_history.json",
        [
            {"date": "1993-04-22", "ma20_pct": 92.4},
            # 与 live 重叠的日期：应被丢弃，live 值生效
            {"date": "2024-01-03", "ma20_pct": 1.0},
            # 晚于 live 起点的全史尾巴：应被丢弃
            {"date": "2024-01-10", "ma20_pct": 2.0},
        ],
    )
    _write(
        tmp_path / "a_share_ma_breadth_history.json",
        [
            {"date": "2024-01-02", "ma20_pct": 50.0},
            {"date": "2024-01-03", "ma20_pct": 51.0},
            {"date": "2024-01-04", "ma20_pct": 52.0},
        ],
    )

    hist = asb.get_ma_breadth_history(lookback_days=100)

    assert [h["date"] for h in hist] == [
        "1993-04-22", "2024-01-02", "2024-01-03", "2024-01-04",
    ]
    # 重叠日期 2024-01-03 用 live 的 51.0，而非全史的 1.0
    assert hist[2]["ma20_pct"] == 51.0


def test_degrades_to_live_only_when_full_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("LEI_CACHE_ROOT", str(tmp_path))
    _write(
        tmp_path / "a_share_ma_breadth_history.json",
        [{"date": "2024-01-02", "ma20_pct": 50.0}],
    )

    hist = asb.get_ma_breadth_history(lookback_days=100)

    assert [h["date"] for h in hist] == ["2024-01-02"]


def test_full_only_when_live_missing(tmp_path, monkeypatch):
    """live 文件被清空/损坏时，全史仍可读（尾部止于回填日，前端自然短一截）。"""
    monkeypatch.setenv("LEI_CACHE_ROOT", str(tmp_path))
    _write(
        tmp_path / "a_share_ma_breadth_full_history.json",
        [{"date": "1993-04-22", "ma20_pct": 92.4}],
    )

    hist = asb.get_ma_breadth_history(lookback_days=100)

    assert [h["date"] for h in hist] == ["1993-04-22"]


def test_lookback_slicing_takes_most_recent(tmp_path, monkeypatch):
    monkeypatch.setenv("LEI_CACHE_ROOT", str(tmp_path))
    _write(
        tmp_path / "a_share_ma_breadth_full_history.json",
        [
            {"date": "1993-04-22", "ma20_pct": 1.0},
            {"date": "1993-04-23", "ma20_pct": 2.0},
        ],
    )
    _write(
        tmp_path / "a_share_ma_breadth_history.json",
        [{"date": "2024-01-02", "ma20_pct": 50.0}],
    )

    hist = asb.get_ma_breadth_history(lookback_days=2)

    assert [h["date"] for h in hist] == ["1993-04-23", "2024-01-02"]
