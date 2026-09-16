"""Round 3 最小复现 3：SQLite 300 根 → 600 根增量生命周期一致。

复现什么
--------
D3 的原始缺陷：``signal_events`` 以 ``event_id`` 为主键、写入用
``INSERT OR IGNORE``。同一事件在 300 根窗口下算出的 ``valid_until``
被第一次写入锁死；换到 600 根窗口重跑，真实有效窗口延长了，但库里
仍是旧值 —— 增量回放后的生命周期与内存结果不一致。

修复方案（Plan A：事件不可变 + 生命周期快照表）
  * ``signal_events`` 继续 INSERT OR IGNORE —— 事件身份本来就不可变，
    并且写入前会用 ``_assert_event_identity`` 校验身份字段没被改写。
  * 生命周期（valid_until / lifecycle_id / ended_event_id）迁到
    ``event_lifecycle_snapshots``，主键 (event_id, run_id, as_of)。
    同一事件在不同 as_of 下有不同快照，两者都对 —— 各自是那个时点
    系统能得出的正确结论。查询按 as_of 降序取最新。

本脚本打印：共同事件数、抽样对比、以及**如果按旧语义（首次写入即锁死）
会有多少条漂移** —— 用来证明这条复现有区分力，而不是恒真。

运行：/opt/homebrew/bin/python3.11 scripts/round3_repro/repro3_sqlite_incremental_lifecycle.py
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from lei_signal.compose.pipeline import analyze_bars
from lei_signal.storage.sqlite_store import (
    connect,
    read_latest_lifecycle,
    write_event_lifecycles,
    write_events,
    write_structures,
)


def _bars(rows: int, seed: int = 11) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0.05, 1.5, rows))
    return pd.DataFrame(
        {
            "open": close,
            "high": close + rng.uniform(0.3, 1.5, rows),
            "low": close - rng.uniform(0.3, 1.5, rows),
            "close": close,
            "volume": rng.integers(1_000_000, 5_000_000, rows).astype(float),
        },
        index=pd.bdate_range("2022-01-03", periods=rows),
    )


def main() -> int:
    full = _bars(600)
    prefix = full.iloc[:300]

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "incr.db"
        conn = connect(db_path)

        r1 = analyze_bars("SYN", prefix)
        as_of_1 = prefix.index[-1].date()
        write_events(conn, r1.events, run_id="run-300")
        write_structures(conn, r1.structures)
        write_event_lifecycles(conn, r1.events, run_id="run-300", as_of=as_of_1)

        r2 = analyze_bars("SYN", full)
        as_of_2 = full.index[-1].date()
        write_events(conn, r2.events, run_id="run-600")
        write_structures(conn, r2.structures)
        write_event_lifecycles(conn, r2.events, run_id="run-600", as_of=as_of_2)

        r1_by_id = {e.event_id: e for e in r1.events}
        r2_by_id = {e.event_id: e for e in r2.events}
        common = sorted(set(r1_by_id) & set(r2_by_id))

        print("== 两次运行 ==")
        print(f"run-300  bars={len(prefix)}  as_of={as_of_1}  events={len(r1.events)}")
        print(f"run-600  bars={len(full)}  as_of={as_of_2}  events={len(r2.events)}")
        print(f"共同 event_id = {len(common)}")
        print()

        # 区分力证明：旧语义下会有多少条 valid_until 漂移
        would_drift = [
            eid for eid in common
            if r1_by_id[eid].valid_until != r2_by_id[eid].valid_until
        ]
        print("== 区分力证明（这条复现不是恒真的）==")
        print(f"300 根 与 600 根 下 valid_until 不同的共同事件：{len(would_drift)} 条")
        if would_drift:
            sample = would_drift[0]
            print(f"  例：{sample}")
            print(f"      300 根算出 valid_until = {r1_by_id[sample].valid_until}")
            print(f"      600 根算出 valid_until = {r2_by_id[sample].valid_until}")
            print("  → 旧的 INSERT OR IGNORE 会把 300 根那个值锁死，库里永远读到过期窗口。")
        print()

        print("== 修复后：每个共同 event_id 的最新快照 vs 内存最新结果 ==")
        drift: list[str] = []
        for eid in common:
            snap = read_latest_lifecycle(conn, eid)
            mem = r2_by_id[eid]
            if snap is None:
                drift.append(f"{eid}: 缺快照")
                continue
            expected_valid = mem.valid_until.isoformat() if mem.valid_until else None
            if snap.run_id != "run-600":
                drift.append(f"{eid}: run_id db={snap.run_id} 期望=run-600")
            if snap.valid_until != expected_valid:
                drift.append(
                    f"{eid}: valid_until db={snap.valid_until} mem={expected_valid}"
                )
            if snap.lifecycle_id != mem.lifecycle_id:
                drift.append(
                    f"{eid}: lifecycle_id db={snap.lifecycle_id} mem={mem.lifecycle_id}"
                )
            if snap.ended_event_id != mem.ended_event_id:
                drift.append(
                    f"{eid}: ended_event_id db={snap.ended_event_id} mem={mem.ended_event_id}"
                )

        for eid in common[:3]:
            snap = read_latest_lifecycle(conn, eid)
            assert snap is not None
            print(f"  {eid}")
            print(f"      最新快照 as_of={snap.as_of} run_id={snap.run_id} "
                  f"valid_until={snap.valid_until} lifecycle={snap.lifecycle_id}")
        print(f"  ...（共 {len(common)} 条全部逐字段比对）")
        print()

        # 审计留痕：旧快照没有被覆盖
        rows = conn.execute(
            "SELECT COUNT(*) AS n FROM event_lifecycle_snapshots WHERE run_id = 'run-300'"
        ).fetchone()["n"]
        print("== 审计留痕（Plan A 的代价与收益）==")
        print(f"run-300 的历史快照仍在库中：{rows} 行 —— 可回答"
              "「300 根那天系统认为的有效窗口是什么」。")
        print()

        if drift:
            print(f"FAIL: {len(drift)} 条生命周期漂移")
            for line in drift[:5]:
                print(f"  {line}")
            return 1
        print(f"PASS: {len(common)} 个共同事件的最新生命周期快照与 600 根内存结果"
              "逐字段一致（valid_until / lifecycle_id / ended_event_id / run_id）。")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
