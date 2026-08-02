"""Round 2 语义收尾门禁：针对复核中指出的业务语义级缺陷逐条固化。

这批测试刻意写成「精确断言」而非「存在性断言」。复核意见指出，旧测试只要求
「出现了任意一条转换」「结果非空就跳过」，导致错误实现照样能通过。下面每个用例
都锁定**确切的日期、确切的状态链、确切的排除集合**，错误实现必须失败。

覆盖：
  1. SQLite 结构生命周期：candidate -> confirmed -> invalidated 三段齐全且日期正确
  2. 事件生命周期字段（valid_until / lifecycle_id / ended_event_id）真正落库
  3. 生命周期「结束事件」不得进入前向收益统计
  4. 持久化失败必须可见（sqlite_persisted 标志），不得静默吞掉
"""
from __future__ import annotations

import sqlite3
from datetime import date

import numpy as np
import pandas as pd
import pytest

from lei_signal.compose.pipeline import analyze, analyze_bars
from lei_signal.domain.types import (
    Provenance,
    StructureInstance,
    StructureStatus,
)
from lei_signal.events.lifecycle import END_SUB_RULES
from lei_signal.research.outcomes import build_forward_outcomes
from lei_signal.storage.sqlite_store import connect, write_events, write_structures


def _bars(rows: int = 600, seed: int = 303) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0.05, 1.6, rows))
    return pd.DataFrame(
        {
            "open": close + rng.normal(0, 0.3, rows),
            "high": close + rng.uniform(0.2, 1.8, rows),
            "low": close - rng.uniform(0.2, 1.8, rows),
            "close": close,
            "volume": rng.integers(500_000, 5_000_000, rows).astype(float),
        },
        index=pd.bdate_range("2022-01-03", periods=rows),
    )


def _structure(
    *,
    detected: date,
    confirmed: date | None,
    invalidated: date | None,
    status: StructureStatus,
) -> StructureInstance:
    return StructureInstance(
        structure_id="S-ROUND2",
        symbol="600000",
        structure_type="bottom_C",
        side="long",
        detected_date=detected,
        c_price=10.0,
        neckline=11.0,
        reference_high=12.0,
        confirmed_date=confirmed,
        status=status,
        invalidated_date=invalidated,
        invalidated_reason="break_c" if invalidated else None,
        source_event_ids=("E1",),
        source_rule_id="bottom_structure",
        provenance=Provenance.LEI_EXPLICIT,
    )


# ---------------- 1. 结构生命周期：完整状态链、日期精确 ----------------


def test_structure_lifecycle_records_full_chain_with_exact_dates(tmp_path) -> None:  # noqa: ANN001
    """复核复现用例：候选 2/26、确认 2/28、失效 3/14，三段转换缺一不可。

    旧实现的错误表现（必须被本用例挡住）：
      * 只记录 ``2024-02-26 None->candidate`` 与 ``2024-02-28 candidate->invalidated``
      * 漏掉 ``candidate->confirmed``、``confirmed->invalidated``
      * 因 ``confirmed_date or invalidated_date`` 的 or 链把**确认日**当成**失效日**
    """
    structure = _structure(
        detected=date(2024, 2, 26),
        confirmed=date(2024, 2, 28),
        invalidated=date(2024, 3, 14),
        status=StructureStatus.INVALIDATED,
    )
    connection = connect(tmp_path / "lifecycle.db")
    write_structures(connection, [structure])

    rows = [
        (row["changed_on"], row["from_status"], row["to_status"])
        for row in connection.execute(
            "SELECT changed_on, from_status, to_status FROM structure_lifecycle "
            "WHERE structure_id = 'S-ROUND2' ORDER BY changed_on"
        )
    ]
    assert rows == [
        ("2024-02-26", None, "candidate"),
        ("2024-02-28", "candidate", "confirmed"),
        ("2024-03-14", "confirmed", "invalidated"),
    ], f"结构生命周期链不完整或日期错误：{rows}"

    # 关键反例：确认日绝不能被记成失效日
    assert ("2024-02-28", "candidate", "invalidated") not in rows

    # 幂等：重复运行不得产生重复行
    write_structures(connection, [structure])
    count = connection.execute(
        "SELECT COUNT(*) AS c FROM structure_lifecycle WHERE structure_id = 'S-ROUND2'"
    ).fetchone()["c"]
    assert count == 3
    connection.close()


def test_structure_lifecycle_candidate_only_has_single_transition(tmp_path) -> None:  # noqa: ANN001
    """仅候选、未确认的结构只能有一条 None->candidate，不得凭空补确认。"""
    structure = _structure(
        detected=date(2024, 2, 26),
        confirmed=None,
        invalidated=None,
        status=StructureStatus.CANDIDATE,
    )
    connection = connect(tmp_path / "candidate.db")
    write_structures(connection, [structure])
    rows = [
        (row["changed_on"], row["from_status"], row["to_status"])
        for row in connection.execute(
            "SELECT changed_on, from_status, to_status FROM structure_lifecycle "
            "ORDER BY changed_on"
        )
    ]
    assert rows == [("2024-02-26", None, "candidate")]
    connection.close()


def test_structure_lifecycle_candidate_invalidated_skips_confirmed(tmp_path) -> None:  # noqa: ANN001
    """候选期直接失效：必须是 candidate->invalidated，不得插入 confirmed。"""
    structure = _structure(
        detected=date(2024, 2, 26),
        confirmed=None,
        invalidated=date(2024, 3, 4),
        status=StructureStatus.INVALIDATED,
    )
    connection = connect(tmp_path / "candidate_invalid.db")
    write_structures(connection, [structure])
    rows = [
        (row["changed_on"], row["from_status"], row["to_status"])
        for row in connection.execute(
            "SELECT changed_on, from_status, to_status FROM structure_lifecycle "
            "ORDER BY changed_on"
        )
    ]
    assert rows == [
        ("2024-02-26", None, "candidate"),
        ("2024-03-04", "candidate", "invalidated"),
    ]
    connection.close()


# ---------------- 2. 事件生命周期字段真正落库 ----------------


def test_event_lifecycle_columns_are_persisted(tmp_path) -> None:  # noqa: ANN001
    """valid_until / lifecycle_id / ended_event_id 必须写进 signal_events。

    旧实现只在内存事件上加了这三个字段，数据库表没有列、写入也不带它们，
    导致「某状态何时生效、何时结束」无法从库里还原。
    """
    result = analyze_bars("600000", _bars())
    connection = connect(tmp_path / "events.db")

    columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(signal_events)")
    }
    assert {"valid_until", "lifecycle_id", "ended_event_id"} <= columns, (
        f"signal_events 缺少生命周期列：{sorted(columns)}"
    )

    write_events(connection, result.events, run_id="round2")

    # 内存里有多少条带生命周期字段，库里就必须有多少条——不允许静默丢失
    expected_lifecycle = sum(1 for e in result.events if e.lifecycle_id is not None)
    expected_valid_until = sum(1 for e in result.events if e.valid_until is not None)
    expected_ended = sum(1 for e in result.events if e.ended_event_id is not None)
    assert expected_lifecycle > 0, "样本内应当存在带 lifecycle_id 的事件"

    stored_lifecycle = connection.execute(
        "SELECT COUNT(*) AS c FROM signal_events WHERE lifecycle_id IS NOT NULL"
    ).fetchone()["c"]
    stored_valid_until = connection.execute(
        "SELECT COUNT(*) AS c FROM signal_events WHERE valid_until IS NOT NULL"
    ).fetchone()["c"]
    stored_ended = connection.execute(
        "SELECT COUNT(*) AS c FROM signal_events WHERE ended_event_id IS NOT NULL"
    ).fetchone()["c"]
    assert stored_lifecycle == expected_lifecycle
    assert stored_valid_until == expected_valid_until
    assert stored_ended == expected_ended

    # 逐条核对一个具体事件的取值，防止「写了但写错列」
    sample = next(e for e in result.events if e.valid_until is not None)
    row = connection.execute(
        "SELECT valid_until, lifecycle_id, ended_event_id FROM signal_events "
        "WHERE event_id = ?",
        (sample.event_id,),
    ).fetchone()
    assert row["valid_until"] == sample.valid_until.isoformat()
    assert row["lifecycle_id"] == sample.lifecycle_id
    assert row["ended_event_id"] == sample.ended_event_id
    connection.close()


# ---------------- 3. 结束事件不得参与收益统计 ----------------


def test_lifecycle_end_events_are_excluded_from_forward_outcomes() -> None:
    """``*_ended`` 等生命周期结束事件不得作为收益样本进入统计。

    这些事件方向是 neutral，旧实现按「非看空即看多」计入，会污染样本量、
    均值与胜率。本用例要求样本内确实存在结束事件，且一条都不得出现在结果里。
    """
    result = analyze_bars("600000", _bars())
    ended_events = [
        event
        for event in result.events
        if event.evidence.get("sub_rule") in END_SUB_RULES
    ]
    assert ended_events, "样本内应当存在生命周期结束事件，否则本用例失去意义"
    ended_keys = {
        f"{event.rule_id}:{event.evidence['sub_rule']}" for event in ended_events
    }

    outcomes = build_forward_outcomes(result)
    assert not outcomes.empty
    atomic = outcomes.loc[outcomes["signal_kind"] == "atomic"]
    leaked = ended_keys & set(atomic["signal_key"])
    assert not leaked, f"生命周期结束事件不得参与收益统计，泄漏：{sorted(leaked)}"

    # 反向确认：非结束事件仍然被统计，排除逻辑没有误伤
    assert len(atomic) == len(result.events) - len(ended_events)

    # 同时确认方向调整口径的列确实存在（看空详情页依赖它们）
    for horizon in (1, 5, 10, 20):
        assert f"direction_adjusted_return_{horizon}" in outcomes.columns
        assert f"mfe_adjusted_{horizon}" in outcomes.columns
        assert f"mae_adjusted_{horizon}" in outcomes.columns


# ---------------- 4. 持久化失败必须可见 ----------------


def _fixed_provider(bars: pd.DataFrame, name: str = "fixed"):  # noqa: ANN202
    from lei_signal.data.providers import PriceData
    from lei_signal.data.symbols import resolve_symbol
    from lei_signal.data.validation import ValidationReport

    class Fixed:
        def fetch(self, symbol, *, min_rows=21):  # noqa: ANN001, ANN202, ARG002
            info = resolve_symbol(symbol)
            return PriceData(
                symbol=info.symbol,
                display_name=info.symbol,
                bars=bars,
                report=ValidationReport(
                    rows=len(bars),
                    first_date=bars.index[0],
                    last_date=bars.index[-1],
                    adjusted=True,
                    provider=name,
                    duplicates_removed=0,
                    warnings=(),
                ),
                info=info,
            )

    return Fixed()


def test_sqlite_persist_failure_is_visible_not_swallowed(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    """写库失败时 ``sqlite_persisted`` 必须为 False，不得静默当成成功。"""
    bars = _bars(rows=300)

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr("lei_signal.storage.sqlite_store.write_events", _boom)
    result = analyze(
        "600000",
        provider=_fixed_provider(bars),
        cache_root=str(tmp_path / "cache"),
        sqlite_path=str(tmp_path / "research.db"),
    )
    # 分析结果本身必须照常返回（落库失败不阻断），但状态必须为 False
    assert result.assessment is not None
    assert result.sqlite_persisted is False, "写库失败必须显式暴露为 False"


def test_sqlite_persist_success_sets_flag_true(tmp_path) -> None:  # noqa: ANN001
    """正常写库时 ``sqlite_persisted`` 为 True，且事件确实落库。"""
    result = analyze(
        "600000",
        provider=_fixed_provider(_bars(rows=300)),
        cache_root=str(tmp_path / "cache"),
        sqlite_path=str(tmp_path / "research.db"),
    )
    assert result.sqlite_persisted is True
    connection = connect(tmp_path / "research.db")
    stored = connection.execute(
        "SELECT COUNT(*) AS c FROM signal_events"
    ).fetchone()["c"]
    assert stored == len(result.events)
    connection.close()


def test_sqlite_flag_is_none_when_persistence_not_requested() -> None:
    """未要求持久化时标志为 None，界面据此显示「未接入」而不是「已接入」。"""
    result = analyze_bars("600000", _bars(rows=300))
    assert result.sqlite_persisted is None


# ---------------- 5. 界面：机会/风险分离、方向调整口径、上传路径 ----------------


def _source_of(function: object) -> str:
    import inspect

    return inspect.getsource(function)  # type: ignore[arg-type]


def test_research_detail_uses_direction_adjusted_columns_only() -> None:
    """看空信号详情页必须用方向调整口径，不得再读原始涨跌。

    复核指出：底层已生成 direction_adjusted_*，但详情页仍读 fwd_return / mfe / mae，
    导致同一信号出现「命中率正确、均值为负」的两套互相矛盾的口径。
    """
    from lei_signal.ui import app

    source = _source_of(app._render_research)
    assert 'return_column = f"direction_adjusted_return_{horizon}"' in source, (
        "详情页收益列必须是 direction_adjusted_return_*"
    )
    assert 'f"mfe_adjusted_{horizon}"' in source
    assert 'f"mae_adjusted_{horizon}"' in source
    for forbidden in (
        'f"fwd_return_{horizon}"',
        'f"mfe_{horizon}"',
        'f"mae_{horizon}"',
    ):
        assert forbidden not in source, f"详情页不得使用原始口径列 {forbidden}"


def test_research_page_wires_risk_transitions() -> None:
    """风险状态转换必须真正接到界面上，而不是只存在于底层函数。"""
    from lei_signal.ui import app

    assert "build_risk_transitions(result)" in _source_of(app._render_research)


def test_diagnostics_conclusion_separates_opportunity_and_risk() -> None:
    """诊断结论必须分别展示机会阶段与风险状态，风险不得顶掉机会。"""
    from lei_signal.ui import app

    source = _source_of(app._render_diagnostics)
    assert "a.opportunity_stage.value" in source
    assert "a.risk_state.value" in source
    # 不得再退回兼容字段 stage 作为结论主语
    assert "STAGE_CN[a.stage.value]" not in source


def test_stage_history_chart_carries_both_opportunity_and_risk() -> None:
    """阶段历史图必须同时承载机会阶段与风险状态两条独立线。"""
    from lei_signal.domain.types import STAGE_CN, STAGE_RANK
    from lei_signal.ui.charts import build_stage_history_figure

    result = analyze_bars("600000", _bars(rows=300), build_history=True)
    history = pd.DataFrame(
        [
            {
                "date": pd.Timestamp(state.day),
                "stage_rank": STAGE_RANK.get(state.opportunity_stage.value, 0),
                "stage_cn": STAGE_CN[state.opportunity_stage.value],
                "risk_rank": {"none": 0, "warning": 1, "confirmed": 2}.get(
                    state.risk_state.value, 0
                ),
                "risk_cn": state.risk_state.value,
            }
            for state in result.history
        ]
    ).set_index("date")
    figure = build_stage_history_figure(history)
    names = [trace.name or "" for trace in figure.data]
    assert any("机会" in name for name in names), f"缺少机会阶段线：{names}"
    assert any("风险" in name for name in names), f"缺少风险状态线：{names}"


def test_upload_path_persists_cache_and_sqlite() -> None:
    """CSV/Parquet 上传路径必须与正常路径一样写缓存与研究库。

    复核指出：上传路径直接调 analyze_bars，绕过了缓存与 SQLite 持久化。
    """
    from lei_signal.ui import app

    source = _source_of(app._analyze_upload)
    assert "analyze(" in source, "上传路径必须走 analyze()，而非直接 analyze_bars()"
    assert "cache_root" in source
    assert "sqlite_path" in source


def test_sqlite_status_is_surfaced_in_ui() -> None:
    """界面必须根据 sqlite_persisted 显示真实状态，不得恒显示「已接入」。"""
    import inspect

    from lei_signal.ui import app

    assert "sqlite_persisted" in inspect.getsource(app)


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
