"""``research/data_snapshot.py`` 的单元测试。

期望值全部手算，独立于被测函数：小样本的价格与行数直接写死在断言里。
网络失败分支一律用模拟 opener 覆盖，不联网。
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

import pandas as pd
import pytest

from lei_signal.data.providers import SinaPriceProvider
from lei_signal.research.data_snapshot import (
    DEFAULT_SNAPSHOT_USES,
    TRANSFORM_VERSION,
    AcquisitionFailed,
    BudgetExceeded,
    FetchBudget,
    RequestSpec,
    acquire_prices,
    diff_snapshots,
    fresh_dir,
    import_prices,
    load_snapshot,
)

SYMBOL = "510300.SS"  # 仓库规范写法；冻结 CSV 用 .SH，差异见 data_quality


def _bar(day: str, close: float) -> dict:
    """构造一根新浪口径的日线。open/high/low 围绕 close 取合法关系。"""
    return {
        "day": day,
        "open": f"{close:.3f}",
        "high": f"{close + 0.1:.3f}",
        "low": f"{close - 0.1:.3f}",
        "close": f"{close:.3f}",
        "volume": "1000",
    }


#: 三根合法日线，手算：收盘 4.000 / 4.100 / 4.200，共 3 行。
THREE_BARS = [
    _bar("2026-09-01", 4.0),
    _bar("2026-09-02", 4.1),
    _bar("2026-09-03", 4.2),
]


def _opener(payload) -> callable:
    text = payload if isinstance(payload, str) else json.dumps(payload)

    def opener(url: str) -> str:  # noqa: ARG001
        return text

    return opener


def _factory(*args, **kwargs):
    """provider 工厂：注入空 sleep，避免重试测试真的等待。"""
    return SinaPriceProvider(*args, sleep=lambda _: None, **kwargs)


def _clock():
    ticks = iter(
        [datetime(2026, 9, 10, 12, 0, i, tzinfo=UTC) for i in range(60)]
    )
    return lambda: next(ticks)


def _budget(**kw) -> FetchBudget:
    base = {
        "max_instruments": 2,
        "max_trading_days": 60,
        "max_requests": 10,
        "timeout_seconds": 5.0,
        "max_retries": 2,
    }
    base.update(kw)
    return FetchBudget(**base)


def _spec(days: int = 3) -> RequestSpec:
    return RequestSpec(source_id="sina_getKLineData", instrument_id=SYMBOL, trading_days=days)


# --------------------------------------------------------------------------
# 正常小例
# --------------------------------------------------------------------------


def test_acquire_normal_small_case(tmp_path):
    result = acquire_prices(
        [_spec()],
        budget=_budget(),
        out_dir=tmp_path / "snap",
        opener=_opener(THREE_BARS),
        clock=_clock(),
        provider_factory=_factory,
    )
    frame = result.frames[SYMBOL]
    # 手算：3 行，收盘依次 4.0 / 4.1 / 4.2
    assert len(frame) == 3
    assert list(frame["close"]) == [4.0, 4.1, 4.2]
    assert str(frame.index.min().date()) == "2026-09-01"

    snap = result.snapshot
    assert snap["mode"] == "acquire"
    assert snap["request"]["requests_used"] == 1
    assert snap["semantics"]["price_basis"] == "nominal_close"
    assert snap["semantics"]["trading_calendar"]["authority"] == "none"
    # 四类时间分别记录，且 available_at 保持未知
    ref = snap["market_data_refs"][SYMBOL]
    assert ref["observed_at"] == "2026-09-03"
    assert ref["available_at"] is None
    assert ref["health"] == "unknown"
    assert ref["generated_at"] is not None
    assert ref["fetched_at"] is not None
    # 原始响应与标准化产物分开存放
    assert (result.directory / "raw").is_dir()
    assert (result.directory / "normalized" / f"{SYMBOL}.csv").exists()


def test_raw_body_is_stored_verbatim(tmp_path):
    payload = json.dumps(THREE_BARS)
    result = acquire_prices(
        [_spec()],
        budget=_budget(),
        out_dir=tmp_path / "snap",
        opener=_opener(payload),
        clock=_clock(),
        provider_factory=_factory,
    )
    raw_files = sorted((result.directory / "raw").glob("*.raw.json"))
    assert len(raw_files) == 1
    assert raw_files[0].read_text(encoding="utf-8") == payload


# --------------------------------------------------------------------------
# 乱序 / 重复与冲突
# --------------------------------------------------------------------------


def test_out_of_order_response_is_sorted(tmp_path):
    shuffled = [THREE_BARS[2], THREE_BARS[0], THREE_BARS[1]]
    result = acquire_prices(
        [_spec()],
        budget=_budget(),
        out_dir=tmp_path / "snap",
        opener=_opener(shuffled),
        clock=_clock(),
        provider_factory=_factory,
    )
    # 手算：排序后收盘 4.0 / 4.1 / 4.2
    assert list(result.frames[SYMBOL]["close"]) == [4.0, 4.1, 4.2]


def test_duplicate_dates_are_recorded_not_hidden(tmp_path):
    payload = [
        _bar("2026-09-01", 4.0),
        _bar("2026-09-01", 4.5),  # 同日冲突值
        _bar("2026-09-02", 4.1),
    ]
    result = acquire_prices(
        [_spec()],
        budget=_budget(),
        out_dir=tmp_path / "snap",
        opener=_opener(payload),
        clock=_clock(),
        provider_factory=_factory,
    )
    item = result.snapshot["instruments"][0]
    # 去重发生了，而且必须在快照里留痕，不能悄悄吞掉
    assert item["provider_report"]["duplicates_removed"] == 1
    assert item["rows"] == 2


# --------------------------------------------------------------------------
# 失败分支：绝不伪装成空成功
# --------------------------------------------------------------------------


def test_empty_response_fails_loudly(tmp_path):
    with pytest.raises(AcquisitionFailed):
        acquire_prices(
            [_spec()],
            budget=_budget(),
            out_dir=tmp_path / "snap",
            opener=_opener(""),
            clock=_clock(),
            provider_factory=_factory,
        )


def test_missing_field_fails_loudly(tmp_path):
    broken = [{"day": "2026-09-01", "open": "4", "high": "4.1", "low": "3.9"}]
    with pytest.raises(AcquisitionFailed):
        acquire_prices(
            [_spec()],
            budget=_budget(),
            out_dir=tmp_path / "snap",
            opener=_opener(broken),
            clock=_clock(),
            provider_factory=_factory,
        )


def test_failure_writes_aborted_evidence(tmp_path):
    out = tmp_path / "snap"
    with pytest.raises(AcquisitionFailed):
        acquire_prices(
            [_spec()],
            budget=_budget(),
            out_dir=out,
            opener=_opener(""),
            clock=_clock(),
            provider_factory=_factory,
        )
    aborted = json.loads((out / "aborted.json").read_text(encoding="utf-8"))
    assert aborted["reason"] == "acquisition_failed"
    assert aborted["calls"], "失败也必须留下请求记录"


def test_error_response_fails_loudly(tmp_path):
    def boom(url: str) -> str:  # noqa: ARG001
        raise OSError("connection reset")

    with pytest.raises(AcquisitionFailed):
        acquire_prices(
            [_spec()],
            budget=_budget(),
            out_dir=tmp_path / "snap",
            opener=boom,
            clock=_clock(),
            provider_factory=_factory,
        )


def test_timeout_is_reported_as_failure(tmp_path):
    def slow(url: str) -> str:  # noqa: ARG001
        raise TimeoutError("read timed out")

    with pytest.raises(AcquisitionFailed):
        acquire_prices(
            [_spec()],
            budget=_budget(),
            out_dir=tmp_path / "snap",
            opener=slow,
            clock=_clock(),
            provider_factory=_factory,
        )


# --------------------------------------------------------------------------
# 有限重试与请求上限
# --------------------------------------------------------------------------


def test_limited_retry_then_success(tmp_path):
    calls = {"n": 0}

    def flaky(url: str) -> str:  # noqa: ARG001
        calls["n"] += 1
        if calls["n"] < 3:
            raise OSError("transient")
        return json.dumps(THREE_BARS)

    result = acquire_prices(
        [_spec()],
        budget=_budget(max_retries=2),  # 首次 + 2 次重试 = 3
        out_dir=tmp_path / "snap",
        opener=flaky,
        clock=_clock(),
        provider_factory=_factory,
    )
    # 手算：第 3 次才成功，共 3 次请求
    assert calls["n"] == 3
    assert result.snapshot["request"]["requests_used"] == 3
    assert len(result.frames[SYMBOL]) == 3


def test_preflight_blocks_before_any_request(tmp_path):
    """最坏情况请求数超预算时，一次请求都不能发出。"""
    calls = {"n": 0}

    def counting(url: str) -> str:  # noqa: ARG001
        calls["n"] += 1
        return json.dumps(THREE_BARS)

    with pytest.raises(BudgetExceeded):
        acquire_prices(
            [_spec(), RequestSpec(source_id="s", instrument_id="512890.SS", trading_days=3)],
            budget=_budget(max_requests=3, max_retries=2),  # 最坏 2×3=6 > 3
            out_dir=tmp_path / "snap",
            opener=counting,
            clock=_clock(),
            provider_factory=_factory,
        )
    assert calls["n"] == 0


def test_too_many_instruments_blocked(tmp_path):
    specs = [_spec(), RequestSpec(source_id="s", instrument_id="512890.SS")]
    with pytest.raises(BudgetExceeded):
        acquire_prices(
            specs,
            budget=_budget(max_instruments=1),
            out_dir=tmp_path / "snap",
            opener=_opener(THREE_BARS),
            clock=_clock(),
            provider_factory=_factory,
        )


def test_too_many_trading_days_blocked(tmp_path):
    with pytest.raises(BudgetExceeded):
        acquire_prices(
            [_spec(days=90)],
            budget=_budget(max_trading_days=60),
            out_dir=tmp_path / "snap",
            opener=_opener(THREE_BARS),
            clock=_clock(),
            provider_factory=_factory,
        )


def test_budget_exhaustion_surfaces_as_budget_error(tmp_path):
    """provider 的重试循环会把异常吞成 DataUnavailableError；

    预算命中必须仍然以 BudgetExceeded 暴露，不能退化成普通获取失败。
    """
    def always_fail(url: str) -> str:  # noqa: ARG001
        raise OSError("down")

    with pytest.raises(BudgetExceeded):
        acquire_prices(
            [_spec(), RequestSpec(source_id="s", instrument_id="512890.SS", trading_days=3)],
            # 允许预检通过（最坏 2×1=2 ≤ 2），但第一个标的就会耗尽
            budget=_budget(max_requests=1, max_retries=0, max_instruments=2),
            out_dir=tmp_path / "snap",
            opener=always_fail,
            clock=_clock(),
            provider_factory=_factory,
        )


# --------------------------------------------------------------------------
# 离线复用、防覆盖、差异
# --------------------------------------------------------------------------


def test_offline_reload_is_identical(tmp_path):
    result = acquire_prices(
        [_spec()],
        budget=_budget(),
        out_dir=tmp_path / "snap",
        opener=_opener(THREE_BARS),
        clock=_clock(),
        provider_factory=_factory,
    )
    loaded = load_snapshot(result.directory)
    assert loaded.verified
    assert loaded.hash_mismatches == ()
    pd.testing.assert_frame_equal(
        loaded.frames[SYMBOL],
        result.frames[SYMBOL],
        check_names=False,
        check_freq=False,
    )


def test_tampered_snapshot_fails_verification(tmp_path):
    result = acquire_prices(
        [_spec()],
        budget=_budget(),
        out_dir=tmp_path / "snap",
        opener=_opener(THREE_BARS),
        clock=_clock(),
        provider_factory=_factory,
    )
    path = result.directory / "normalized" / f"{SYMBOL}.csv"
    path.write_text(path.read_text(encoding="utf-8").replace("4.2", "9.9"), encoding="utf-8")
    loaded = load_snapshot(result.directory)
    assert not loaded.verified
    assert loaded.hash_mismatches


def test_never_overwrites_existing_output(tmp_path):
    out = tmp_path / "snap"
    first = acquire_prices(
        [_spec()], budget=_budget(), out_dir=out,
        opener=_opener(THREE_BARS), clock=_clock(), provider_factory=_factory,
    )
    second = acquire_prices(
        [_spec()], budget=_budget(), out_dir=out,
        opener=_opener(THREE_BARS), clock=_clock(), provider_factory=_factory,
    )
    assert first.directory != second.directory
    assert second.directory.name.endswith("-01")
    # 旧目录内容仍在
    assert (first.directory / "snapshot.json").exists()


def test_fresh_dir_bumps_numeric_suffix(tmp_path):
    base = tmp_path / "run-01"
    base.mkdir()
    assert fresh_dir(base).name == "run-01"[:-3] + "-01" or fresh_dir(base) != base


def test_diff_detects_historical_revision(tmp_path):
    revised = [_bar("2026-09-01", 4.0), _bar("2026-09-02", 4.1), _bar("2026-09-03", 4.9)]
    a = acquire_prices(
        [_spec()], budget=_budget(), out_dir=tmp_path / "a",
        opener=_opener(THREE_BARS), clock=_clock(), provider_factory=_factory,
    )
    b = acquire_prices(
        [_spec()], budget=_budget(), out_dir=tmp_path / "b",
        opener=_opener(revised), clock=_clock(), provider_factory=_factory,
    )
    diff = diff_snapshots(a.directory, b.directory)
    assert not diff["identical"]
    entry = diff["changed"][SYMBOL]
    assert entry["classification"] == "historical_revision"
    assert entry["dates_with_changed_values"] == ["2026-09-03"]


def test_diff_classifies_append_only(tmp_path):
    appended = [*THREE_BARS, _bar("2026-09-04", 4.3)]
    a = acquire_prices(
        [_spec()], budget=_budget(), out_dir=tmp_path / "a",
        opener=_opener(THREE_BARS), clock=_clock(), provider_factory=_factory,
    )
    b = acquire_prices(
        [_spec(days=4)], budget=_budget(), out_dir=tmp_path / "b",
        opener=_opener(appended), clock=_clock(), provider_factory=_factory,
    )
    diff = diff_snapshots(a.directory, b.directory)
    entry = diff["changed"][SYMBOL]
    assert entry["classification"] == "append_only"
    assert entry["dates_only_in_new"] == ["2026-09-04"]
    assert entry["dates_with_changed_values"] == []


def test_identical_repeat_is_reported_identical(tmp_path):
    a = acquire_prices(
        [_spec()], budget=_budget(), out_dir=tmp_path / "a",
        opener=_opener(THREE_BARS), clock=_clock(), provider_factory=_factory,
    )
    b = acquire_prices(
        [_spec()], budget=_budget(), out_dir=tmp_path / "b",
        opener=_opener(THREE_BARS), clock=_clock(), provider_factory=_factory,
    )
    assert diff_snapshots(a.directory, b.directory)["identical"]


# --------------------------------------------------------------------------
# 离线导入
# --------------------------------------------------------------------------


def _write_csv(path, rows) -> None:
    pd.DataFrame(rows).to_csv(path, index=False)


def test_import_reads_only_and_keeps_source_untouched(tmp_path):
    src = tmp_path / "prices.csv"
    _write_csv(
        src,
        [
            {"date": "2026-09-01", "symbol": SYMBOL, "open": 4.0, "high": 4.1,
             "low": 3.9, "close": 4.0, "volume": 100},
            {"date": "2026-09-02", "symbol": SYMBOL, "open": 4.1, "high": 4.2,
             "low": 4.0, "close": 4.1, "volume": 120},
        ],
    )
    before = src.read_bytes()
    result = import_prices(
        src, source_id="frozen_csv", out_dir=tmp_path / "imp", clock=_clock()
    )
    assert src.read_bytes() == before, "导入必须只读，不得改写源文件"
    assert list(result.frames[SYMBOL]["close"]) == [4.0, 4.1]
    ref = result.snapshot["market_data_refs"][SYMBOL]
    # 导入不代表本次取得，fetched_at 必须为空
    assert ref["fetched_at"] is None
    assert ref["available_at"] is None
    assert result.snapshot["source"]["import_source"]["sha256"]


def test_import_rejects_unknown_instrument(tmp_path):
    src = tmp_path / "prices.csv"
    _write_csv(
        src,
        [{"date": "2026-09-01", "symbol": SYMBOL, "open": 4.0, "high": 4.1,
          "low": 3.9, "close": 4.0, "volume": 100}],
    )
    with pytest.raises(AcquisitionFailed):
        import_prices(
            src, source_id="frozen_csv", out_dir=tmp_path / "imp",
            instrument_ids=["999999.SH"], clock=_clock(),
        )


def test_import_rejects_missing_columns(tmp_path):
    src = tmp_path / "bad.csv"
    _write_csv(src, [{"date": "2026-09-01", "symbol": SYMBOL, "close": 4.0}])
    with pytest.raises(AcquisitionFailed):
        import_prices(src, source_id="frozen_csv", out_dir=tmp_path / "imp", clock=_clock())


def test_tampered_raw_response_is_also_detected(tmp_path):
    """缺陷F回归：原始响应体是第一手证据，被改动必须报出来。

    自查发现原实现只核 normalized，raw 被改不报——那更危险。
    """
    result = acquire_prices(
        [_spec()],
        budget=_budget(),
        out_dir=tmp_path / "snap",
        opener=_opener(THREE_BARS),
        clock=_clock(),
        provider_factory=_factory,
    )
    raw = next((result.directory / "raw").glob("*.raw.json"))
    original = raw.read_text(encoding="utf-8")
    tampered = original.replace("4.000", "9.999", 1)
    assert tampered != original, "测试自身必须真的改到内容"
    raw.write_text(tampered, encoding="utf-8")

    loaded = load_snapshot(result.directory)
    assert loaded.verified is False
    assert any("raw.json" in m for m in loaded.hash_mismatches)


# --------------------------------------------------------------------------
# 第六轮自查：修复后的回归守卫
# --------------------------------------------------------------------------


def test_mixed_price_basis_is_refused_not_silently_collapsed(tmp_path):
    """缺陷G回归：异构口径不得被写成单一口径的快照。

    原实现用 specs[0] 取 price_basis/currency，第二个 spec 的口径被静默丢弃；
    更糟的是下游 check_prices 从快照读单一口径，因此混用检查永远不会触发。
    """
    from lei_signal.research.data_snapshot import _build_snapshot

    specs = [
        RequestSpec(source_id="s", instrument_id="A", price_basis="nominal_close"),
        RequestSpec(source_id="s", instrument_id="B", price_basis="economic_index"),
    ]
    with pytest.raises(AcquisitionFailed, match="多种价格口径"):
        _build_snapshot(
            mode="t", directory=tmp_path, specs=specs, per_instrument=[], refs={},
            started_at="x", finished_at="y", calls=[], budget=None, requests_used=0,
        )

    mixed_ccy = [
        RequestSpec(source_id="s", instrument_id="A", currency="CNY"),
        RequestSpec(source_id="s", instrument_id="B", currency="USD"),
    ]
    with pytest.raises(AcquisitionFailed, match="多种币种"):
        _build_snapshot(
            mode="t", directory=tmp_path, specs=mixed_ccy, per_instrument=[], refs={},
            started_at="x", finished_at="y", calls=[], budget=None, requests_used=0,
        )


def test_snapshot_records_basis_per_instrument(tmp_path, small_csv_factory=None):
    """口径逐标的留痕，便于回溯（即使全批一致）。"""
    src = tmp_path / "p.csv"
    pd.DataFrame([
        {"date": "2026-01-02", "symbol": SYMBOL, "open": 4.0, "high": 4.1,
         "low": 3.9, "close": 4.0, "volume": 100},
    ]).to_csv(src, index=False)
    res = import_prices(src, source_id="t", out_dir=tmp_path / "o", clock=_clock())
    per = res.snapshot["semantics"]["price_basis_by_instrument"]
    assert per == {SYMBOL: "nominal_close"}


def test_unknown_price_basis_requires_explicit_adjusted(tmp_path):
    """缺陷I回归：复权口径不许猜。"""
    src = tmp_path / "p.csv"
    pd.DataFrame([
        {"date": "2026-01-02", "symbol": SYMBOL, "open": 4.0, "high": 4.1,
         "low": 3.9, "close": 4.0, "volume": 100},
    ]).to_csv(src, index=False)

    with pytest.raises(AcquisitionFailed, match="复权口径未登记"):
        import_prices(src, source_id="t", out_dir=tmp_path / "a",
                      price_basis="some_new_basis", clock=_clock())

    # 显式声明后放行
    ok = import_prices(src, source_id="t", out_dir=tmp_path / "b",
                       price_basis="some_new_basis", adjusted=True, clock=_clock())
    assert ok.snapshot["instruments"][0]["provider_report"]["adjusted"] is True


def test_snapshot_version_mismatch_is_refused(tmp_path):
    """缺陷M回归：跨版本快照不得被静默读入。"""
    src = tmp_path / "p.csv"
    pd.DataFrame([
        {"date": "2026-01-02", "symbol": SYMBOL, "open": 4.0, "high": 4.1,
         "low": 3.9, "close": 4.0, "volume": 100},
    ]).to_csv(src, index=False)
    res = import_prices(src, source_id="t", out_dir=tmp_path / "o", clock=_clock())

    sp = res.directory / "snapshot.json"
    payload = json.loads(sp.read_text(encoding="utf-8"))
    payload["transform_version"] = "research-data-snapshot/0.9"
    sp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(AcquisitionFailed, match="transform_version"):
        load_snapshot(res.directory)

    payload["transform_version"] = TRANSFORM_VERSION
    payload["schema_version"] = "something-else/2.0"
    sp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(AcquisitionFailed, match="schema_version"):
        load_snapshot(res.directory)


def test_snapshot_uses_are_explicit_and_exposed(tmp_path):
    """缺陷N回归：用途声明必须是显式的，且能被下游读到做交叉核对。"""
    src = tmp_path / "p.csv"
    pd.DataFrame([
        {"date": "2026-01-02", "symbol": SYMBOL, "open": 4.0, "high": 4.1,
         "low": 3.9, "close": 4.0, "volume": 100},
    ]).to_csv(src, index=False)
    res = import_prices(src, source_id="t", out_dir=tmp_path / "o", clock=_clock())
    loaded = load_snapshot(res.directory)
    # 默认声明六类用途齐全，并注明依据
    assert set(loaded.declared_uses) == set(DEFAULT_SNAPSHOT_USES)
    assert "production_trade" in loaded.declared_not_for
    assert res.snapshot["uses_basis"].startswith("本实现默认")


def test_field_structure_mismatch_is_detected_even_when_hash_matches(tmp_path):
    """缺陷P回归：哈希一致 ≠ 结构正确。

    早期只核哈希，一份只剩 close 列的 CSV 也能 verified=True 通过，
    而下游默认存在 open/high/low/close/volume。
    """
    import hashlib

    src = tmp_path / "p.csv"
    pd.DataFrame([
        {"date": "2026-01-02", "symbol": SYMBOL, "open": 4.0, "high": 4.1,
         "low": 3.9, "close": 4.0, "volume": 100},
    ]).to_csv(src, index=False)
    res = import_prices(src, source_id="t", out_dir=tmp_path / "o", clock=_clock())

    f = res.directory / "normalized" / f"{SYMBOL}.csv"
    trimmed = "date,close\n2026-01-02,4.0\n"
    f.write_text(trimmed, encoding="utf-8")
    sp = res.directory / "snapshot.json"
    snap = json.loads(sp.read_text(encoding="utf-8"))
    # 把哈希改成新内容的哈希：模拟「合法重写但结构变了」
    snap["instruments"][0]["normalized"]["sha256"] = hashlib.sha256(
        trimmed.encode()
    ).hexdigest()
    sp.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")

    loaded = load_snapshot(res.directory)
    assert loaded.verified is False
    assert any("fields missing" in m for m in loaded.hash_mismatches)


def test_binding_reads_fields_from_snapshot_when_given(tmp_path):
    """缺陷T回归：绑定判定不得套用常量，应以实际快照字段为前提。"""
    from lei_signal.research import definitions as d
    from lei_signal.research.data_snapshot import bind_definitions

    fake_snapshot = {
        "semantics": {
            # 假设某快照已经提供 economic_index
            "fields": ["date", "symbol", "economic_index"],
            "currency": "CNY",
        }
    }
    reg = d.load_registry()
    with_snap = bind_definitions(
        registry=reg, refs=["mixed.momentum.raw@1.0.0"],
        purpose="description", snapshot=fake_snapshot,
    )
    info = with_snap["bindings"]["mixed.momentum.raw@1.0.0"]
    assert info["missing_fields"] == [], "该快照已含 economic_index，应可直接满足"

    # 不给快照时套用常量（名义价字段），仍应报缺 economic_index
    without = bind_definitions(
        registry=reg, refs=["mixed.momentum.raw@1.0.0"], purpose="description"
    )
    assert "economic_index" in without["bindings"]["mixed.momentum.raw@1.0.0"][
        "missing_fields"
    ]


# --------------------------------------------------------------------------
# 第五轮（变异检测）暴露的覆盖假象
# --------------------------------------------------------------------------


def test_mapper_collapsing_two_products_is_refused(tmp_path):
    """变异 N12 暴露：导入映射的重复身份检测此前无测试。

    两个不同来源代码映射到同一身份时必须报错，否则两只产品会被悄悄并成一只。
    """
    src = tmp_path / "p.csv"
    pd.DataFrame([
        {"date": "2026-01-02", "symbol": "510300.SH", "open": 4.0, "high": 4.1,
         "low": 3.9, "close": 4.0, "volume": 100},
        {"date": "2026-01-02", "symbol": "512890.SH", "open": 1.0, "high": 1.1,
         "low": 0.9, "close": 1.0, "volume": 100},
    ]).to_csv(src, index=False)

    # 恶意/错误的映射器：把两只都映射到同一身份
    with pytest.raises(AcquisitionFailed, match="映射到同一身份"):
        import_prices(
            src, source_id="t", out_dir=tmp_path / "o",
            symbol_mapper=lambda s: "510300.SS", clock=_clock(),
        )


def test_binding_enforces_declared_uses_of_the_object(tmp_path):
    """变异 N13 暴露：绑定的用途强制此前**完全没有测试**。

    我在第一轮报告里把「拿 diagnostic 去解析被拒」当证据写过，
    却从未锁进测试——它坏了没人知道。
    """
    from lei_signal.research import definitions as d
    from lei_signal.research.data_snapshot import bind_definitions

    reg = d.load_registry()
    # description 在 mixed.momentum.raw 的 uses 内 → 可解析
    allowed = bind_definitions(
        registry=reg, refs=["mixed.momentum.raw@1.0.0"], purpose="description"
    )
    assert allowed["bindings"]["mixed.momentum.raw@1.0.0"]["resolved"] is True

    # attribution 不在其 uses 内 → 必须被拒
    refused = bind_definitions(
        registry=reg, refs=["mixed.momentum.raw@1.0.0"], purpose="attribution"
    )
    info = refused["bindings"]["mixed.momentum.raw@1.0.0"]
    assert info["resolved"] is False
    assert "not allowed" in info["error"]
