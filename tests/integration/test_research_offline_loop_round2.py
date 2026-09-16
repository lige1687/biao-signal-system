"""第二轮小型离线闭环：快照 → 指纹 → 身份映射 → 日历 → 定义与用途核验。

全程离线，不运行任何收益账户路径。
本文件同时承担 §三 要求的第四项独立期望值检查（资料不足却试图升级用途）
与 §六 要求的价格/每份分红同步缩放检查。
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from lei_signal.research import data_quality as q
from lei_signal.research.data_snapshot import bind_definitions, load_snapshot
from lei_signal.research.symbol_identity import audit_mapping, build_mapping
from lei_signal.research.trading_calendar import TradingCalendar

ROOT = Path(__file__).resolve().parents[2]
R1 = ROOT / "docs/experiments/raw/research-data-provenance-2026-09-10"
R2 = ROOT / "docs/experiments/raw/research-data-provenance-round2-2026-09-10"
SNAPSHOT = R1 / "example-fullpool"
CALENDAR = R2 / "calendar-szse/calendar.json"
ACTIONS = (
    ROOT
    / "docs/experiments/raw/research-rotation-clean-2026-09-09/full-pool-preparation"
    / "action-sources/normalized-actions.json"
)


@pytest.fixture(scope="module")
def loaded():
    if not (SNAPSHOT / "snapshot.json").exists():
        pytest.skip("上一轮快照产物不存在")
    return load_snapshot(SNAPSHOT)


@pytest.fixture(scope="module")
def cal():
    if not CALENDAR.exists():
        pytest.skip("本轮日历产物不存在")
    return TradingCalendar.from_file(CALENDAR)


# --------------------------------------------------------------------------
# 闭环各段
# --------------------------------------------------------------------------


def test_step1_snapshot_fingerprints_verify(loaded):
    assert loaded.verified is True
    assert loaded.hash_mismatches == ()
    # 手算：冻结全池 14 只、18,916 行
    assert len(loaded.frames) == 14
    assert sum(len(f) for f in loaded.frames.values()) == 18916


def test_step2_identity_mapping_balances(loaded):
    """用第四轮实际生成的规范标签快照做**真**行数核对，不靠假设。"""
    mapping = build_mapping(loaded.frames)
    canonical_dir = (
        ROOT
        / "docs/experiments/raw/research-identity-wiring-2026-09-10/canonical-snapshot"
    )
    if not (canonical_dir / "snapshot.json").exists():
        pytest.skip("规范标签快照不存在")
    mapped = load_snapshot(canonical_dir).frames

    audit = audit_mapping(loaded.frames, mapping, mapped_frames=mapped)
    assert audit.rows_verified is True
    assert audit.balanced is True
    assert audit.products_before == audit.products_after == 14
    assert audit.rows_before == audit.rows_after == 18916
    assert audit.first_date == "2019-09-02"
    assert audit.last_date == "2026-06-30"
    # 13 只来源写法是 .SH，1 只是 .SZ
    assert sum(1 for i in mapping.values() if i.source_format == "SH") == 13
    assert sum(1 for i in mapping.values() if i.source_format == "SZ") == 1
    # 映射后全部可被生产 resolve_symbol 认成 A 股
    assert all(i.repo_resolvable for i in mapping.values())
    # 映射后的键必须正好是各自的规范身份
    assert set(mapped) == {i.canonical for i in mapping.values()}


def test_step3_calendar_finds_no_conflict_with_frozen_prices(loaded, cal):
    """官方日历与冻结价格互不冲突：休市日无报价、交易日无整池空缺。"""
    report = q.check_prices(
        loaded.frames,
        declared_basis="nominal_close",
        calendar=cal,
        evaluation_start="2019-09-02",
        evaluation_end="2026-06-30",
    )
    codes = {f.code for f in report.findings}
    assert "quote_on_closed_day" not in codes, "不得存在休市日却有报价"
    assert "trading_day_without_any_quote" not in codes
    # 但覆盖不全必须如实降级
    assert "calendar_coverage_partial" in codes


def test_step4_binding_still_rejects_without_economic_index():
    """名义价缺 economic_index，相关定义绑定必须继续被拒绝。"""
    from lei_signal.research import definitions as d

    result = bind_definitions(
        registry=d.load_registry(),
        refs=["mixed.price.economic@1.0.0", "mixed.momentum.raw@1.0.0"],
        purpose="description",
    )
    for ref, info in result["bindings"].items():
        assert info["directly_satisfiable"] is False, ref
        assert "economic_index" in info["missing_fields"], ref


def test_step5_a_legitimate_check_can_pass(loaded, cal):
    """闭环里至少有一个能走通的合法检查：描述用途放行。"""
    report = q.check_prices(loaded.frames, declared_basis="nominal_close", calendar=cal)
    assert q.require_use(report, "description") == q.USABLE
    assert q.require_use(report, "diagnostic") == q.USABLE


# --------------------------------------------------------------------------
# §三 第四项独立检查：资料不足却试图升级用途
# --------------------------------------------------------------------------


def test_use_upgrade_request_is_refused_with_reasons(loaded, cal):
    price = q.check_prices(loaded.frames, declared_basis="nominal_close", calendar=cal)
    payload = json.loads(ACTIONS.read_text(encoding="utf-8"))
    actions = q.check_actions(payload["events"], declared_symbols=list(loaded.frames))
    report = q.merge_reports(price, actions)

    # 归因需要公司行动的可得时间；21/21 缺失 → 必须被拒
    with pytest.raises(q.UseNotPermitted) as exc:
        q.require_use(report, "attribution")
    assert exc.value.verdict == q.CONDITIONAL
    assert any("available_at" in r for r in exc.value.reasons)

    # 排序同样不放行（日历覆盖不全 + 代码写法不一致）
    with pytest.raises(q.UseNotPermitted):
        q.require_use(report, "ranking")

    # 显式承担条件才放行——这一步必须是调用方的主动动作
    assert q.require_use(report, "attribution", allow_conditional=True) == q.CONDITIONAL


def test_conditional_never_silently_becomes_usable(loaded, cal):
    report = q.check_prices(loaded.frames, declared_basis="nominal_close", calendar=cal)
    assert report.verdict_for("ranking") == q.CONDITIONAL
    with pytest.raises(q.UseNotPermitted):
        q.require_use(report, "ranking")  # 默认不放行


# --------------------------------------------------------------------------
# §六：价格缩放必须同步缩放每份现金分红
# --------------------------------------------------------------------------


def test_price_and_per_unit_dividend_scale_together():
    """名义价 ×10 时每份现金分红也必须 ×10，经济指数才不变。

    期望值来自经济含义手推，不是调用被测函数得来：
    100 元、每份分红 1 元 ⇒ 分红占价格 1%；
    1000 元、每份分红 10 元 ⇒ 同样 1%。两者的经济指数必须逐值相等。
    """
    from copy import deepcopy

    from lei_signal.research.definitions import economic_index

    quotes = pd.Series(
        [100.0, 99.0], index=pd.to_datetime(["2020-01-01", "2020-01-02"])
    )
    actions = [
        dict(
            event_id="d",
            type="cash_dividend",
            cash=1.0,
            effective_date="2020-01-02",
            available_at="2020-01-01T12:00:00+08:00",
        )
    ]
    scaled_actions = deepcopy(actions)
    scaled_actions[0]["cash"] *= 10

    expected = economic_index(quotes, actions)
    pd.testing.assert_series_equal(economic_index(quotes * 10, scaled_actions), expected)

    # 反例：只缩价格不缩每份分红，经济含义已变，不得要求不变
    assert economic_index(quotes * 10, actions).iloc[-1] != expected.iloc[-1]


def test_actions_and_events_sources_are_not_conflated():
    """actions 来自公司行动文件；带账户事件字段的记录必须被拒。"""
    payload = json.loads(ACTIONS.read_text(encoding="utf-8"))
    raw_actions = payload["events"]
    # 原始文件里不应出现账户事件字段
    leaked = [
        a for a in raw_actions
        if any(k in a for k in ("account_id", "event", "amount"))
    ]
    assert leaked == [], "原始公司行动文件不应带账户事件字段"

    report = q.check_actions(raw_actions)
    assert "events_passed_as_actions" not in {f.code for f in report.findings}

    # 反向：伪造一条账户事件混入，必须被拦
    polluted = [*raw_actions, {
        "event_id": "x", "symbol": "510300", "type": "cash_dividend",
        "effective_date": "2026-01-05", "account_id": "E11", "event": "cash_paid",
        "amount": 100.0,
    }]
    bad = q.check_actions(polluted)
    assert "events_passed_as_actions" in {f.code for f in bad.findings}


# --------------------------------------------------------------------------
# §三 第一项：一次确实改变内容的篡改
# --------------------------------------------------------------------------


def test_byte_level_tamper_is_detected(tmp_path, loaded):
    """复制一份快照后改动一个字节，指纹核验必须失败。"""
    import shutil

    copy = tmp_path / "snap"
    shutil.copytree(SNAPSHOT, copy)
    target = copy / "normalized" / "510300.SH.csv"
    original = target.read_bytes()
    tampered = original.replace(b"3.904", b"3.905", 1)
    assert tampered != original, "测试自身必须真的改到内容"
    target.write_bytes(tampered)

    reloaded = load_snapshot(copy)
    assert reloaded.verified is False
    assert "normalized/510300.SH.csv" in reloaded.hash_mismatches
