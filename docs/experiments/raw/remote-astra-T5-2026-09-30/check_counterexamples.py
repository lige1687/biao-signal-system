"""T5 跨模块交易时点反例核验脚本（只读业务代码，不修改 src/）。

运行：
  cd 仓库根 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
      /tmp/bq-venv/bin/python docs/experiments/raw/remote-astra-T5-2026-09-30/check_counterexamples.py

输入全部是人工合成报价（见 synth.py），不联网、不读本机数据库/接口。
SQLite 只写 /tmp/t5-work/ 下临时库，结束时删除。
隔离手段（写明）：
  * MemoryProvider：内存行情源替身，经真实 validate_bars 包装；
  * H07 在内存中把 features.weekly_context / compose.pipeline 模块里的
    aggregate_weekly 名字临时换成“记录参数后调用原函数”的包装，运行后恢复。
产物：results.json（逐假设实际输出与判定）、inputs/*.json（合成输入）。
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import platform
import shutil
import sqlite3
import subprocess
import sys
import time
import traceback
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]  # 机械修复1：原 parents[2] 指向 docs/，少一级
sys.path.insert(0, str(HERE))

from synth import (  # noqa: E402
    SYNTH_LABEL,
    MemoryProvider,
    base_rows,
    day_of,
    dump,
    ev,
    random_series,
    st,
    to_bars,
)

from lei_signal.compose.pipeline import AnalysisResult, analyze, analyze_bars  # noqa: E402
from lei_signal.data.calendar import weekday_calendar  # noqa: E402
from lei_signal.data.point_in_time import aggregate_weekly  # noqa: E402
from lei_signal.data.validation import validate_bars  # noqa: E402
from lei_signal.rules.strict_structure import (  # noqa: E402
    detect_strict_structures,
    merge_contained_bars,
)
from lei_signal.rules.tradability_gate import evaluate_tradability  # noqa: E402

TMP = Path("/tmp/t5-work")
INPUTS = HERE / "inputs"
RESULTS: dict[str, dict] = {}


def save_input(name: str, bars: pd.DataFrame, note: str) -> str:
    INPUTS.mkdir(exist_ok=True)
    path = INPUTS / f"{name}.json"
    rows = [
        {"date": str(ts.date()), **{k: (None if pd.isna(v) else float(v)) for k, v in row.items()}}
        for ts, row in bars.iterrows()
    ]
    dump({"label": SYNTH_LABEL, "note": note, "rows": rows}, path)
    return str(path.relative_to(REPO))


def fresh_db(name: str) -> str:
    TMP.mkdir(exist_ok=True)
    path = TMP / f"{name}.db"
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(path) + suffix)
        if p.exists():
            p.unlink()
    return str(path)


def db_rows(path: str, sql: str) -> list[dict]:
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute(sql)]
    finally:
        con.close()


def by_sub(result: AnalysisResult, sub_rule: str, day: date | None = None) -> list:
    return [
        e for e in result.events
        if e.evidence.get("sub_rule") == sub_rule and (day is None or e.available_date == day)
    ]


def tradability_checks(frame: pd.DataFrame) -> dict:
    tr = evaluate_tradability(frame, len(frame) - 1)
    return {
        "tradable": tr.tradable,
        "blocking_reasons": list(tr.blocking_reasons),
        "checks": [
            {"code": c.code, "label": c.label_cn, "blocked": c.blocked, "detail": c.detail_cn}
            for c in tr.condition_checks
        ],
    }


def record(hid: str, payload: dict) -> None:
    RESULTS[hid] = payload
    print(f"[{hid}] {payload.get('verdict')} :: {payload.get('summary', '')}")


# ---------------------------------------------------------------- H01
def h01() -> None:
    bars = to_bars(base_rows())
    inp = save_input("H01_base", bars, "两次探底+放量突破颈线(下标62)+下标80最低价回到C以下")
    D = day_of(bars, 62)
    inval_day = day_of(bars, 80)
    full = analyze_bars("T5", bars)
    cuts = {}
    for n in (80, 81):
        res = analyze_bars("T5", bars.iloc[:n])
        cuts[str(day_of(bars, n - 1))] = [ev(e) for e in by_sub(res, "breakout_volume", D)]
    pre = analyze_bars("T5", bars.iloc[:80])
    pre_on_d = {e.event_id for e in pre.events if e.available_date == D}
    full_on_d = {e.event_id for e in full.events if e.available_date == D}
    removed = [ev(e) for e in pre.events if e.event_id in pre_on_d - full_on_d]
    confirmed_on_d = [st(s) for s in pre.bottoms if s.confirmed_date == D]
    from lei_signal.compose.pipeline import _build_structure_necklines

    necks = _build_structure_necklines(pre.bottoms)

    # H01c：反转K线底部上的“放量突破”
    rows: list[dict] = []
    for i in range(60):
        c = 100 - i * 0.8
        rows.append(dict(open=c + 0.3, high=c + 0.5, low=c - 0.4, close=c, volume=1e6))
    last = rows[-1]["close"]
    rows.append(dict(open=last - 0.2, high=last, low=last - 1.6, close=last - 1.4, volume=1e6))
    p = rows[-1]
    rows.append(dict(open=p["close"] - 0.2, high=p["open"] + 1.2, low=p["close"] - 0.5,
                     close=p["open"] + 1.0, volume=3e6))
    for _ in range(15):
        c = rows[-1]["close"] + 0.3
        rows.append(dict(open=c - 0.2, high=c + 0.4, low=c - 0.5, close=c, volume=1e6))
    rbars = to_bars(rows)
    inp_c = save_input("H01c_reversal", rbars, "长跌后阴线+放量阳线反包(下标61)")
    rres = analyze_bars("T5", rbars)
    c_events = []
    for e in by_sub(rres, "breakout_volume"):
        close = float(rres.frame.loc[pd.Timestamp(e.available_date), "close"])
        sid = e.structure_id
        stype = next((s.structure_type for s in rres.structures if s.structure_id == sid), None)
        c_events.append({**ev(e), "structure_type": stype, "neckline": e.evidence.get("neckline"),
                         "close": close, "close_above_neckline": close > float(e.evidence["neckline"]),
                         "reason_cn": e.reason_cn})
    reproduced = bool(cuts[str(day_of(bars, 79))]) and not cuts[str(day_of(bars, 80))]
    record("H01", {
        "inputs": [inp, inp_c],
        "D_breakout_day": str(D), "invalidation_day": str(inval_day),
        "breakout_volume_on_D_by_cut": cuts,
        "breakout_volume_on_D_full": [ev(e) for e in by_sub(full, "breakout_volume", D)],
        "events_on_D_removed_by_full_history": removed,
        "full_structure_states": [st(s) for s in full.bottoms],
        "H01b_structures_confirmed_on_D": confirmed_on_d,
        "H01b_neckline_map_entries_for_D": {str(k.date()): v for k, v in necks.items()
                                            if k.date() == D},
        "H01c_breakout_events_on_reversal_bottom": c_events,
        "expected_by_source": "门禁1/§3.2：截至 D 已发布的事件在追加未来行情后不变；pipeline._build_structure_necklines 文档：确认后、失效之前可用。",
        "verdict": "复现" if reproduced else "未复现",
        "summary": (
            f"D={D} 的 breakout_volume 在截到 {day_of(bars, 79)} 时存在，"
            f"一旦看到 {inval_day} 的C失效就从过去消失" if reproduced else "未见差异"
        ),
    })


# ---------------------------------------------------------------- H01d（事后追加的确认检查）
def h01d(series: list[tuple[str, pd.DataFrame]]) -> None:
    """H11 中 S3 在 2022-07-06 出现“同一事件编号换绑结构”，验证它对研究库写入的后果。

    隔离：在内存中把 lei_signal.api.services.default_provider 换成返回 MemoryProvider
    的函数（只影响本进程本函数运行期间，结束后恢复）；cache_root/sqlite_path 都指向 /tmp。
    """
    import lei_signal.api.services as services
    from lei_signal.storage.sqlite_store import EventIdentityConflictError

    bars = dict(series)["S3_uptrend_seed101"]
    p = bars.index.get_loc(pd.Timestamp("2022-07-06"))
    prefix = bars.iloc[: p + 1]
    pre = analyze_bars("510300.SS", prefix)
    full = analyze_bars("510300.SS", bars)
    pre_bv = {e.event_id: e for e in by_sub(pre, "breakout_volume", date(2022, 7, 6))}
    full_bv = {e.event_id: e for e in by_sub(full, "breakout_volume", date(2022, 7, 6))}
    same_day_confirmed = [st(s) for s in pre.bottoms if s.confirmed_date == date(2022, 7, 6)]
    same_day_full = [st(s) for s in full.bottoms if s.confirmed_date == date(2022, 7, 6)]
    rebinding = [{"event_id": k[:16], "prefix_structure": pre_bv[k].structure_id[:30],
                  "full_structure": full_bv[k].structure_id[:30],
                  "prefix_neckline": pre_bv[k].evidence.get("neckline"),
                  "full_neckline": full_bv[k].evidence.get("neckline")}
                 for k in pre_bv if k in full_bv and pre_bv[k].structure_id != full_bv[k].structure_id]

    db = fresh_db("h01d")
    direct = {}
    analyze("510300", provider=MemoryProvider(prefix), sqlite_path=db, run_id="api-2022-07-06")
    try:
        analyze("510300", provider=MemoryProvider(bars), sqlite_path=db, run_id="api-2022-11-30")
        direct["second_run"] = "no error"
    except EventIdentityConflictError as exc:
        direct["second_run"] = f"EventIdentityConflictError: {exc}"
    direct["analysis_runs"] = db_rows(db, "select run_id, last_data_date from analysis_runs")
    direct["lifecycle_snapshot_runs"] = db_rows(db, "select run_id, count(*) n from event_lifecycle_snapshots group by run_id")
    direct["signal_events_by_run"] = db_rows(db, "select run_id, count(*) n from signal_events group by run_id")

    db2 = fresh_db("h01d_service")
    original = services.default_provider
    svc_out = {}
    try:
        holder = {"bars": prefix}
        services.default_provider = lambda: MemoryProvider(holder["bars"])
        svc = services.AnalysisService(cache_root=str(TMP / "cache"), sqlite_path=db2, ttl_seconds=0)
        e1 = svc.get("510300", refresh=True)
        holder["bars"] = bars
        e2 = svc.get("510300", refresh=True)
        e3 = svc.get("510300", refresh=True)
        svc_out = {
            "first": {"error": e1.error, "persist_conflict": e1.persist_conflict,
                      "sqlite_persisted": e1.result.sqlite_persisted if e1.result else None},
            "second": {"error": e2.error, "persist_conflict": (e2.persist_conflict or "")[:220],
                       "sqlite_persisted": e2.result.sqlite_persisted if e2.result else None},
            "third_same_data": {"persist_conflict_again": e3.persist_conflict is not None,
                                "sqlite_persisted": e3.result.sqlite_persisted if e3.result else None},
            "analysis_runs": db_rows(db2, "select run_id, last_data_date from analysis_runs"),
            "lifecycle_snapshot_as_of": db_rows(db2, "select as_of, count(*) n from event_lifecycle_snapshots group by as_of"),
            "signal_events_total": db_rows(db2, "select count(*) n from signal_events")[0]["n"],
        }
    finally:
        services.default_provider = original
    record("H01d", {
        "input": "random_series(seed=101) 人工合成 S3，前缀截到 2022-07-06 vs 全历史 2022-11-30",
        "same_day_confirmed_structures_prefix": same_day_confirmed,
        "same_day_confirmed_structures_full": same_day_full,
        "breakout_volume_rebinding": rebinding,
        "direct_analyze": direct,
        "analysis_service": svc_out,
        "verdict": "复现" if rebinding and "Conflict" in direct.get("second_run", "") else "未复现",
        "summary": "同一事件编号后来换绑到另一结构 → 写研究库时身份冲突 → 之后每次运行都冲突、该标的研究库生命周期与运行记录停写",
    })


# ---------------------------------------------------------------- H02
def two_structure_rows() -> list[dict]:
    def up(rows, n, step):
        for _ in range(n):
            c = rows[-1]["close"] + step
            rows.append(dict(open=c - step * 0.5, high=c + 0.4, low=c - 0.5, close=c, volume=1e6))

    def engulf(rows, drop=1.4):
        last = rows[-1]["close"]
        rows.append(dict(open=last - 0.2, high=last, low=last - drop - 0.2, close=last - drop,
                         volume=1e6))
        p = rows[-1]
        rows.append(dict(open=p["close"] - 0.2, high=p["open"] + 1.2, low=p["close"] - 0.5,
                         close=p["open"] + 1.0, volume=1e6))

    rows: list[dict] = []
    for i in range(60):
        c = 100 - i * 0.8
        rows.append(dict(open=c + 0.3, high=c + 0.5, low=c - 0.4, close=c, volume=1e6))
    engulf(rows)
    up(rows, 25, 0.35)
    engulf(rows, drop=1.0)
    up(rows, 4, 0.2)
    return rows


def h02() -> None:
    rows = two_structure_rows()
    probe = analyze_bars("T5", to_bars(rows))
    rev = sorted([s for s in probe.bottoms if s.structure_type == "bullish_reversal_bottom"],
                 key=lambda s: s.detected_date)
    x_c = rev[-1].c_price
    c = rows[-1]["close"]
    rows.append(dict(open=c, high=c + 0.2, low=x_c - 0.3, close=c - 0.3, volume=1e6))
    for _ in range(6):
        c = rows[-1]["close"] + 0.3
        rows.append(dict(open=c - 0.15, high=c + 0.4, low=c - 0.5, close=c, volume=1e6))
    bars = to_bars(rows)
    inp = save_input("H02_two_structures", bars, "两段阳线反包底部；末段只击穿后一个底部的C")
    res = analyze_bars("T5", bars, build_history=True)
    sid_type = {s.structure_id: s.structure_type for s in res.structures}
    x = next(s for s in res.bottoms if s.invalidated_date is not None
             and s.invalidated_date == day_of(bars, len(rows) - 7))
    D = x.invalidated_date
    window = []
    for state in res.history:
        if abs((state.day - D).days) <= 4:
            window.append({
                "day": str(state.day), "opportunity_stage": state.opportunity_stage.value,
                "risk_state": state.risk_state.value, "display_stage": state.stage.value,
                "color": state.color.value,
                "observations": {f"{sid_type[k]}:{k[-8:]}": v.tier for k, v in state.observations.items()},
                "live_bottoms": [f"{s.structure_type}:{s.structure_id[-8:]}" for s in state.live_bottoms],
            })
    touched_events = [ev(e) for e in res.events if e.rule_id == "bottom_c_lifecycle"
                      and e.available_date == D]

    # H02b/H02c：只有候选、从未确认的底部触及C
    cbars = to_bars(base_rows(confirm_close=72.6, climb=0.0))
    inp_b = save_input("H02b_candidate_only", cbars, "两次探底但从未收盘突破颈线；下标78最低价回到C以下")
    cres = analyze_bars("T5", cbars, build_history=True)
    cand = [s for s in cres.bottoms if s.confirmed_date is None and s.invalidated_date is not None]
    Dc = cand[0].invalidated_date
    pos = cbars.index.get_loc(pd.Timestamp(Dc))
    cpre = analyze_bars("T5", cbars.iloc[: pos + 1], build_history=True)
    state_c = next(s for s in cpre.history if s.day == Dc)
    from lei_signal.api.sell_signals import extract_sell_signals

    sells = [dataclasses.asdict(s) for s in extract_sell_signals(cpre)]
    record("H02", {
        "inputs": [inp, inp_b],
        "structures": [st(s) for s in res.bottoms],
        "X_invalidated_day": str(D),
        "state_window_around_D": window,
        "c_touch_events_on_D": touched_events,
        "H02b_candidate_structures": [st(s) for s in cand],
        "H02b_state_on_Dc": {"day": str(Dc), "risk_state": state_c.risk_state.value,
                              "display_stage": state_c.stage.value,
                              "opportunity_stage": state_c.opportunity_stage.value},
        "H02b_risk_alerts_on_Dc": [r.code for r in cpre.assessment.risks],
        "H02b_c_lifecycle_events_on_Dc": [ev(e) for e in cpre.events
                                           if e.rule_id == "bottom_c_lifecycle" and e.available_date == Dc],
        "H02c_sell_signals_on_Dc": sells,
        "verdict": "核心无问题；显示合并与候选失效处理见 summary",
        "summary": "另一结构的观察档与机会阶段不受影响；失效当天组合显示阶段=失效；候选失效有风险提示与硬卖点但无事件",
    })


# ---------------------------------------------------------------- H03
def h03(scan_series: list[tuple[str, pd.DataFrame]]) -> None:
    abars = to_bars(base_rows(confirm_low=68.5))
    inp = save_input("H03a_same_bar_touch_and_break", abars, "下标62同一根：最低68.5<=C 且收盘74.4>颈线")
    ares = analyze_bars("T5", abars)
    a_targets = [st(s) for s in ares.bottoms if str(s.detected_date) == str(day_of(abars, 61))]

    def ohlc(rows):
        frame = pd.DataFrame(rows, columns=["open", "high", "low", "close"],
                             index=pd.bdate_range("2024-01-01", periods=len(rows)))
        frame["volume"] = 1e6
        return frame

    top = ohlc([(9, 10, 9.0, 9.8), (9.4, 9.5, 8.7, 9.0), (9.2, 10.4, 8.2, 8.4)])
    bottom = ohlc([(9.2, 9.8, 9.0, 9.4), (9.9, 10.3, 9.3, 10.2), (10.0, 10.9, 8.8, 9.0)])
    save_input("H03b_strict_outside_bar", top, "严格顶部等待确认时，一根K线同时新高且跌破触发低点")
    b_out = {
        "top_merged": [dataclasses.asdict(m) for m in merge_contained_bars(top)],
        "top_structures": [dataclasses.asdict(s) for s in detect_strict_structures(top)],
        "bottom_merged": [dataclasses.asdict(m) for m in merge_contained_bars(bottom)],
        "bottom_structures": [dataclasses.asdict(s) for s in detect_strict_structures(bottom)],
    }
    # H03c：转黑日/C失效日与档位升级同日的性质检查（扫描序列上）
    props = []
    for name, bars in scan_series:
        res = analyze_bars("T5", bars, build_history=True)
        black_days = {s.day for s in res.history if s.color.value == "black"}
        ema = [e for e in res.events if e.rule_id == "ema20_reclaim_rising"]
        sbyid = {s.structure_id: s for s in res.structures}
        on_black = [ev(e) for e in ema if e.available_date in black_days]
        obs_on_black = [str(s.day) for s in res.history
                        if s.color.value == "black" and s.observations]
        after_c = [ev(e) for e in ema if sbyid[e.structure_id].invalidated_date is not None
                   and e.available_date >= sbyid[e.structure_id].invalidated_date]
        obs_dead = [str(s.day) for s in res.history for sid in s.observations
                    if sbyid[sid].invalidated_date is not None and sbyid[sid].invalidated_date <= s.day]
        props.append({"series": name, "black_days": len(black_days), "ema_events": len(ema),
                      "ema_events_on_black_days": on_black[:5], "observations_on_black_days": obs_on_black[:5],
                      "ema_events_on_or_after_c": after_c[:5], "observations_of_dead_structures": obs_dead[:5]})
    a_ok = all(s["confirmed"] == "None" and s["invalidated"] == str(day_of(abars, 62)) for s in a_targets)
    c_ok = all(not (p["ema_events_on_black_days"] or p["observations_on_black_days"]
                    or p["ema_events_on_or_after_c"] or p["observations_of_dead_structures"]) for p in props)
    record("H03", {
        "inputs": [inp],
        "a_structures_detected_on_L2_confirm_day": a_targets,
        "a_ok_touch_wins": a_ok,
        "b_strict_outside_bar": b_out,
        "c_property_checks": props,
        "c_ok": c_ok,
        "verdict": "未发现问题（(b)原文先后待确认）" if a_ok and c_ok else "发现不一致",
        "summary": "(a)先触C即失效；(b)外包K线被包含合并吸收后按新高作废；(c)转黑/失效当天无升级",
    })


# ---------------------------------------------------------------- H04
def h04() -> None:
    bars = to_bars(base_rows(right_side=(73.8, 74.5, 75.0)))
    inp = save_input("H04_pivot_confirm_day", bars, "第二低点(下标58)右侧三根收盘已高于颈线73.5；三左三右在下标61确认")
    full = analyze_bars("T5", bars, build_history=True)
    out = {}
    for n in (61, 62, 63):
        res = analyze_bars("T5", bars.iloc[:n], build_history=True)
        out[str(day_of(bars, n - 1))] = {
            "bottoms": [st(s) for s in res.bottoms],
            "swing_low_events": [ev(e) for e in res.events if e.evidence.get("sub_rule") == "swing_low_confirmed"],
            "b1_price": res.assessment.b1_price,
        }
    full_b1 = {str(d): a.b1_price for d, a in full.assessments_by_date.items()
               if d in (day_of(bars, 57), day_of(bars, 58))}
    full_bottoms = [st(s) for s in full.bottoms if s.detected_date <= day_of(bars, 62)]
    ok = (not out[str(day_of(bars, 60))]["bottoms"]
          and all(b["confirmed"] == str(day_of(bars, 62)) for b in full_bottoms
                  if b["type"] in ("higher_low_bottom", "double_bottom")))
    record("H04", {
        "inputs": [inp], "by_cut": out, "full_b1_on_pivot_high_confirm": full_b1,
        "full_bottoms": full_bottoms,
        "verdict": "未发现问题" if ok else "发现不一致",
        "summary": "拐点后第3根才出现低点与结构；确认最早在其次日；截断与全历史一致",
    })


# ---------------------------------------------------------------- H05
def h05() -> None:
    base = to_bars(base_rows()).iloc[:63].copy()
    intraday = base.copy()
    intraday.iloc[-1] = [72.4, 74.6, 72.1, 74.4, 2.4e6]
    final = base.copy()
    final.iloc[-1] = [72.4, 74.6, 72.1, 73.0, 3.5e6]
    inp_i = save_input("H05_intraday_1430", intraday, "D日14:30盘中版：暂时站上颈线73.5（成交量未走完）")
    inp_f = save_input("H05_final_close", final, "D日收盘版：收回颈线下方")
    D = day_of(base, 62)
    db = fresh_db("h05")
    r1 = analyze("510300", provider=MemoryProvider(intraday), sqlite_path=db, run_id=f"api-{D}")
    trad = tradability_checks(r1.frame)
    r2 = analyze("510300", provider=MemoryProvider(final), sqlite_path=db, run_id=f"api-{D}")
    fields = [f.name for f in dataclasses.fields(AnalysisResult)]
    from lei_signal.api.schemas import BuyPointReviewDTO

    review_fields = list(BuyPointReviewDTO.model_fields)
    db_struct = db_rows(db, "select structure_type, status, confirmed_date from structure_instances")
    db_life = db_rows(db, "select structure_id, changed_on, from_status, to_status from structure_lifecycle")
    db_conf = db_rows(db, "select rule_id, available_date, evidence_json from signal_events "
                          "where available_date = '%s'" % D)
    db_conf = [{"rule_id": r["rule_id"], "sub_rule": json.loads(r["evidence_json"]).get("sub_rule")}
               for r in db_conf]
    mem_final = sorted(f"{e.rule_id}:{e.evidence.get('sub_rule')}" for e in r2.events if e.available_date == D)
    stale_in_db = sorted({f"{r['rule_id']}:{r['sub_rule']}" for r in db_conf} - set(mem_final))

    # 决定翻转搜索：同一天盘中版 vs 收盘版的买点复核结论
    from lei_signal.api.routes.opportunities import build_review

    drift = np.concatenate([np.full(200, 0.05), np.full(500, 0.12)])
    vol = np.full(700, 0.011)
    series = random_series(101, drift, vol)
    flips, tried = [], 0
    for p in range(699, 380, -3):
        o, h, l, c, v = series.iloc[p][["open", "high", "low", "close", "volume"]]
        if h - c < 0.004 * c:
            continue
        tried += 1
        a = series.iloc[: p + 1].copy()
        a.iloc[-1] = [o, h, min(o, c), h, v * 0.8]
        b = series.iloc[: p + 1]
        ra = build_review(analyze("510300", provider=MemoryProvider(a)), symbol="510300.SS")
        rb = build_review(analyze("510300", provider=MemoryProvider(b)), symbol="510300.SS")
        if ra.verdict != rb.verdict:
            check9 = next(c9 for c9 in ra.tradability.condition_checks if c9.code == "depends_on_future")
            flips.append({
                "day": str(series.index[p].date()),
                "intraday_bar": {"open": o, "high": h, "low": min(o, c), "close": h},
                "final_bar": {"open": o, "high": h, "low": l, "close": c},
                "intraday_verdict": ra.verdict_cn, "final_verdict": rb.verdict_cn,
                "intraday_candidates": [x.scenario_cn for x in ra.candidates],
                "intraday_summary": ra.summary_cn,
                "intraday_check9": {"blocked": check9.blocked, "detail": check9.detail_cn},
            })
            if len(flips) >= 3:
                break
        if tried >= 60:
            break
    record("H05", {
        "inputs": [inp_i, inp_f, "random_series(seed=101, 200根漂移0.05%+500根漂移0.12%, 波动1.1%) 人工合成"],
        "D": str(D),
        "intraday_events_on_D": [ev(e) for e in r1.events if e.available_date == D],
        "intraday_opportunity_stage": r1.assessment.opportunity_stage.value,
        "final_events_on_D": mem_final,
        "final_opportunity_stage": r2.assessment.opportunity_stage.value,
        "intraday_tradability_check9": next(c for c in trad["checks"] if c["code"] == "depends_on_future"),
        "analysis_result_fields_about_completeness": [f for f in fields if any(k in f for k in ("complet", "partial", "final", "intraday"))],
        "buy_point_review_fields_about_completeness": [f for f in review_fields if any(k in f for k in ("complet", "partial", "final", "intraday"))],
        "db_after_final_run": {"structure_instances": db_struct, "structure_lifecycle": db_life,
                                "events_on_D_in_db_not_in_final_memory": stale_in_db},
        "verdict_flip_search": {"tried_days": tried, "flips": flips},
        "verdict": "复现",
        "summary": "盘中版确认结构并永久写入研究库；收盘版已不成立但库中仍在；第9条恒写“不依赖未完成K线”",
    })


# ---------------------------------------------------------------- H06
def h06() -> None:
    idx = pd.bdate_range("2024-01-01", periods=30)
    close = np.linspace(10, 13, 30)
    bars = pd.DataFrame(dict(open=close, high=close + 0.3, low=close - 0.3, close=close,
                             volume=np.full(30, 1e6)), index=idx)
    bars.index.name = "date"
    intraday = bars.copy()
    intraday.iloc[-1] = [12.9, 13.6, 12.9, 13.5, 4e5]
    final = bars.copy()
    final.iloc[-1] = [12.9, 13.6, 12.4, 12.5, 1.2e6]
    inp = save_input("H06_friday_intraday", intraday, "第6周周五 14:30 盘中版（收盘版见 summary）")
    wi = aggregate_weekly(intraday)
    wf = aggregate_weekly(final)
    ri = analyze_bars("T5", intraday)
    record("H06", {
        "inputs": [inp],
        "intraday_last_week": {"available_date": str(wi.index[-1].date()), **{k: (bool(v) if k == "is_complete" else float(v) if isinstance(v, (int, float, np.floating, np.integer)) else str(v)) for k, v in wi.iloc[-1].items()}},
        "final_last_week": {"available_date": str(wf.index[-1].date()), "close": float(wf.iloc[-1]["close"]), "low": float(wf.iloc[-1]["low"])},
        "pipeline_weekly_trend_last_index": str(ri.weekly_trend.index[-1].date()),
        "pipeline_weekly_trend_last_close": float(ri.weekly_trend.iloc[-1]["close"]),
        "verdict": "复现",
        "summary": "周五盘中数据让当周周线被标“已完成”，收盘价取盘中价，无任何标注",
    })


# ---------------------------------------------------------------- H07
def h07() -> None:
    import lei_signal.compose.pipeline as pl
    import lei_signal.features.weekly_context as wc

    holidays = [date(2024, 2, 8), date(2024, 2, 9)]
    cal = weekday_calendar(holidays)
    idx = [d for d in pd.bdate_range("2024-01-01", "2024-02-07") if d.date() not in holidays]
    n = len(idx)
    close = np.linspace(10, 12, n)
    bars = pd.DataFrame(dict(open=close, high=close + 0.2, low=close - 0.2, close=close,
                             volume=np.full(n, 1e6)), index=pd.DatetimeIndex(idx, name="date"))
    inp = save_input("H07_short_week", bars, "人工设定 2024-02-08/09（周四、周五）休市的短周，截至周三")
    calls = []
    orig_pl, orig_wc = pl.aggregate_weekly, wc.aggregate_weekly

    def spy(caller):
        def wrapper(daily, *, as_of=None, calendar=None):
            out = aggregate_weekly(daily, as_of=as_of, calendar=calendar)
            calls.append({"caller": caller, "calendar_injected": calendar is not None,
                          "last_week_available_date": str(out.index[-1].date()) if len(out) else None})
            return out
        return wrapper

    try:
        pl.aggregate_weekly = spy("compose.pipeline.analyze_bars")
        wc.aggregate_weekly = spy("features.weekly_context.weekly_env_series")
        res = analyze_bars("T5", bars, calendar=cal)
        from lei_signal.features.weekly_context import weekly_env_series

        weekly_env_series(res.frame)  # symbols._build_pullback_opportunities 的同一调用
    finally:
        pl.aggregate_weekly, wc.aggregate_weekly = orig_pl, orig_wc
    record("H07", {
        "inputs": [inp], "calls": calls,
        "pipeline_weekly_trend_last_index": str(res.weekly_trend.index[-1].date()),
        "verdict": "复现（已知）",
        "summary": "同一次分析里主流程周线含短周（周三），模块A/回撤卡周线环境不含（只到上周五）",
    })


# ---------------------------------------------------------------- H08
def h08() -> None:
    rows = base_rows()
    full_bars = to_bars(rows)
    miss = full_bars.copy()
    miss.iloc[80, miss.columns.get_loc("low")] = np.nan
    inp = save_input("H08a_missing_low", miss, "下标80最低价缺失（真实最低68.6会触及C=68.8）")
    clean, report = validate_bars(miss, symbol="510300.SS", provider="synthetic_t5", adjusted=True)
    r_miss = analyze_bars("T5", clean, build_history=True)
    r_full = analyze_bars("T5", full_bars, build_history=True)
    D = day_of(full_bars, 80)

    def summary(res):
        s = next(x for x in res.history if x.day == D)
        return {"risk_state": s.risk_state.value, "display_stage": s.stage.value,
                "live_bottoms": [f"{b.structure_type}" for b in s.live_bottoms],
                "structures_detected_0327": [st(b) for b in res.bottoms
                                             if b.detected_date == day_of(full_bars, 61)],
                "last_day_live_bottoms": [b.structure_type for b in res.history[-1].live_bottoms]}

    vmiss = full_bars.copy()
    vmiss.iloc[70, vmiss.columns.get_loc("volume")] = np.nan
    inp_v = save_input("H08b_missing_volume", vmiss, "下标70成交量缺失")
    vclean, vreport = validate_bars(vmiss, symbol="510300.SS", provider="synthetic_t5", adjusted=True)
    vres = analyze_bars("T5", vclean)
    d70 = pd.Timestamp(day_of(full_bars, 70))
    vrow = vres.frame.loc[d70]
    vfull = analyze_bars("T5", full_bars).frame
    later = vres.frame["volume_ratio20"].iloc[71:90] / vfull["volume_ratio20"].iloc[71:90]
    record("H08", {
        "inputs": [inp, inp_v],
        "a_validate_warnings": list(report.warnings),
        "a_missing_low_row_after_validate": {k: (None if pd.isna(v) else float(v)) for k, v in clean.loc[pd.Timestamp(D)].items()},
        "a_with_missing_low": summary(r_miss),
        "a_with_true_low": summary(r_full),
        "b_validate_warnings": list(vreport.warnings),
        "b_volume_after_validate": float(vclean.loc[d70, "volume"]),
        "b_volume_ratio20_on_day": float(vrow["volume_ratio20"]),
        "b_pullback_shrink_on_day": bool(vrow["pullback_shrink"]),
        "b_next19_ratio_inflation_min_max": [float(later.min()), float(later.max())],
        "verdict": "复现",
        "summary": "最低价缺失被当成“没触及C”，结构继续有效；成交量缺失被静默当0；均无警告",
    })


# ---------------------------------------------------------------- H09
def h09() -> None:
    out: dict = {}
    # (a) 修订旧K线
    orig = to_bars(base_rows())
    revised = orig.copy()
    revised.iloc[80, revised.columns.get_loc("low")] = 69.0
    save_input("H09a_revised_low", revised, "行情源更正：下标80最低价由68.6改为69.0（不再触及C）")
    db = fresh_db("h09a")
    errs = []
    for tag, bars in (("run1_original", orig), ("run2_revised", revised)):
        try:
            analyze("510300", provider=MemoryProvider(bars), sqlite_path=db, run_id=f"t5-{tag}")
        except Exception as exc:  # noqa: BLE001
            errs.append(f"{tag}: {type(exc).__name__}: {exc}")
    sid_prefix = "structure_higher_low_bottom"
    out["a_errors"] = errs
    out["a_structure_instances"] = db_rows(db, f"select structure_id, status, confirmed_date, invalidated_date from structure_instances where structure_id like '{sid_prefix}%'")
    out["a_structure_lifecycle"] = db_rows(db, f"select structure_id, changed_on, from_status, to_status, reason from structure_lifecycle where structure_id like '{sid_prefix}%'")
    out["a_c_touch_events_in_db"] = db_rows(db, "select available_date, structure_id from signal_events where rule_id='bottom_c_lifecycle'")
    # (b) 回补缺失的一天
    gap = orig.iloc[:71].drop(orig.index[59])
    save_input("H09b_gap_first_run", gap, "首次运行缺 2024-03-25（下标59）这一天，截至下标70")
    db_b = fresh_db("h09b")
    errs_b = []
    for tag, bars in (("run1_gap", gap), ("run2_backfilled", orig)):
        try:
            analyze("510300", provider=MemoryProvider(bars), sqlite_path=db_b, run_id=f"t5-{tag}")
        except Exception as exc:  # noqa: BLE001
            errs_b.append(f"{tag}: {type(exc).__name__}: {exc}")
    cur = analyze_bars("510300.SS", orig)  # 机械修复2：原写 "T5"，与入库符号不同导致编号对照失效
    cur_ids = {s.structure_id for s in cur.structures}
    rows_b = db_rows(db_b, "select structure_id, structure_type, detected_date, status, confirmed_date, invalidated_date from structure_instances where side='bottom'")
    out["b_errors"] = errs_b
    out["b_structure_instances"] = [{**r, "in_current_analysis": r["structure_id"] in cur_ids} for r in rows_b]
    out["b_swing_low_events_for_L2"] = db_rows(db_b, "select event_date, available_date from signal_events where rule_id='swing_pivots' and event_date='%s'" % day_of(orig, 58))
    # (c) 回放旧日写库
    db_c = fresh_db("h09c")
    analyze("510300", provider=MemoryProvider(orig), sqlite_path=db_c, run_id="t5-full")
    before = db_rows(db_c, f"select status, invalidated_date from structure_instances where structure_id like '{sid_prefix}%'")
    analyze("510300", provider=MemoryProvider(orig), as_of=day_of(orig, 75), sqlite_path=db_c, run_id=None)
    after = db_rows(db_c, f"select status, invalidated_date from structure_instances where structure_id like '{sid_prefix}%'")
    life_c = db_rows(db_c, f"select changed_on, from_status, to_status from structure_lifecycle where structure_id like '{sid_prefix}%'")
    out["c_before_replay"] = before
    out["c_after_replay_as_of"] = {"as_of": str(day_of(orig, 75)), "rows": after}
    out["c_structure_lifecycle"] = life_c
    record("H09", {**out, "verdict": "复现（修订语义待确认）",
                   "summary": "修订/回补/回放都直接改写结构表“当前状态”，无修订记录，三张表互相矛盾"})


# ---------------------------------------------------------------- H10
def h10() -> None:
    def ohlc(rows):
        frame = pd.DataFrame(rows, columns=["open", "high", "low", "close"],
                             index=pd.bdate_range("2024-01-01", periods=len(rows)))
        frame["volume"] = 1e6
        return frame

    base = [(9, 10, 9.0, 9.8), (9.4, 9.5, 8.7, 9.0), (8.9, 9.2, 8.3, 8.5)]
    inner = ohlc(base + [(8.6, 9.0, 8.4, 8.7)])
    outer = ohlc(base + [(9.0, 10.5, 8.0, 10.2)])
    save_input("H10_inner_bar", inner, "严格顶部D日确认后追加一根内包K线")
    save_input("H10_outer_bar", outer, "严格顶部D日确认后追加一根创新高的外包K线")

    def tops(frame):
        return [(str(s.confirmed_date), s.final_price) for s in detect_strict_structures(frame) if s.side == "top"]

    prefix = tops(inner.iloc[:3])
    record("H10", {
        "prefix_top_confirmations": prefix,
        "after_inner_bar": tops(inner),
        "after_outer_bar": tops(outer),
        "existing_test_note": "tests/unit/test_strict_structure.py::test_prefix_invariance 的第4根(9.5,10.5,9.4)不与第3根构成包含，未覆盖本情形",
        "verdict": "复现（已知/已记录）",
        "summary": "内包K线把确认日后移一天；外包新高K线让已确认顶部从历史中消失",
    })


# ---------------------------------------------------------------- H11
def scan_series_list() -> list[tuple[str, pd.DataFrame]]:
    s1 = random_series(5, np.concatenate([np.full(160, 0.15), np.full(260, 0.0), np.full(120, 0.35), np.full(100, -0.1)]),
                       np.concatenate([np.full(160, 0.012), np.full(260, 0.0025), np.full(120, 0.012), np.full(100, 0.012)]))
    s2 = random_series(3, np.concatenate([np.full(150, 0.25), np.full(150, 0.0), np.full(150, -0.2), np.full(250, 0.3)]),
                       np.full(700, 0.012))
    s3 = random_series(101, np.concatenate([np.full(200, 0.05), np.full(500, 0.12)]), np.full(700, 0.011))
    return [("S1_sideways_mix_seed5", s1), ("S2_trend_mix_seed3", s2), ("S3_uptrend_seed101", s3)]


def _ev_key(e):
    return e.event_id


def h11(series: list[tuple[str, pd.DataFrame]]) -> None:
    from lei_signal.rules.module_d_false_breakout import _params as d_params
    from lei_signal.rules.module_d_false_breakout import _zone_intervals
    from lei_signal.domain.rules_config import get_rule

    report = []
    for name, bars in series:
        digest = hashlib.sha256(pd.util.hash_pandas_object(bars).values.tobytes()).hexdigest()[:16]
        full = analyze_bars("T5", bars, build_history=True)
        full_by_id = {e.event_id: e for e in full.events}
        full_hist = {s.day: s for s in full.history}
        full_strict = {(s.side, s.confirmed_date, s.reference_price) for s in detect_strict_structures(bars)}
        _, thr, mb, xb = d_params(get_rule("module_d_false_breakout"))
        full_zones = _zone_intervals(full.frame, thr, mb, xb)
        cuts = sorted(set(np.linspace(150, len(bars) - 2, 25).astype(int)))
        diffs: dict[str, list] = {}
        n_compared = 0

        def add(cat, item):
            diffs.setdefault(cat, [])
            if len(diffs[cat]) < 4:
                diffs[cat].append(item)
            diffs.setdefault(cat + "#count", [0])[0] += 1

        for p in cuts:
            cut_day = bars.index[p].date()
            pre = analyze_bars("T5", bars.iloc[: p + 1])
            n_compared += 1
            pre_by_id = {e.event_id: e for e in pre.events}
            full_vis = {k: e for k, e in full_by_id.items() if e.available_date <= cut_day}
            pre_strict = {(s.side, s.confirmed_date, s.reference_price) for s in detect_strict_structures(bars.iloc[: p + 1])}
            strict_changed = pre_strict != {x for x in full_strict if x[1] <= cut_day}
            pre_zones = _zone_intervals(pre.frame, thr, mb, xb)
            zones_changed = [z for z in pre_zones] != [(a, min(b, p + 1)) for a, b in full_zones if a <= p]

            def cat_of(e):
                rule = e.rule_id
                sub = e.evidence.get("sub_rule")
                if rule == "first_ma_pullback" and strict_changed:
                    return f"{rule}[已知:严格构造包含合并]"
                if rule == "module_d_false_breakout" and zones_changed:
                    return f"{rule}[已知:D密集区结束日追溯]"
                if sub == "breakout_volume":
                    return f"{rule}:{sub}[H01]"
                return f"{rule}:{sub}[未归类]"

            for k in set(pre_by_id) - set(full_vis):
                add("only_in_prefix:" + cat_of(pre_by_id[k]), {"cut": str(cut_day), **ev(pre_by_id[k])})
            for k in set(full_vis) - set(pre_by_id):
                add("only_in_full:" + cat_of(full_vis[k]), {"cut": str(cut_day), **ev(full_vis[k])})
            horizon = cut_day + timedelta(days=1)
            for k in set(pre_by_id) & set(full_vis):
                a, b = pre_by_id[k], full_vis[k]
                fields = {
                    "event_date": (a.event_date, b.event_date),
                    "structure_id": (a.structure_id, b.structure_id),
                    "lifecycle_id": (a.lifecycle_id, b.lifecycle_id),
                    "evidence": (json.dumps(a.evidence, sort_keys=True, default=str), json.dumps(b.evidence, sort_keys=True, default=str)),
                    "valid_until": (a.valid_until, min(b.valid_until, horizon)),
                }
                if a.ended_event_id is not None:
                    fields["ended_event_id"] = (a.ended_event_id, b.ended_event_id)
                for f, (x, y) in fields.items():
                    if x != y:
                        add(f"field:{f}:" + cat_of(a), {"cut": str(cut_day), **ev(a), "prefix": str(x)[:120], "full": str(y)[:120]})
            for s in pre.history:
                g = full_hist[s.day]
                for f in ("opportunity_stage", "risk_state", "color", "daily_long", "weekly_long"):
                    if getattr(s, f) != getattr(g, f):
                        add(f"state:{f}", {"cut": str(cut_day), "day": str(s.day), "prefix": str(getattr(s, f)), "full": str(getattr(g, f))})
                pa = (s.primary_bottom.structure_id if s.primary_bottom else None)
                pb = (g.primary_bottom.structure_id if g.primary_bottom else None)
                if pa != pb:
                    add("state:primary_bottom", {"cut": str(cut_day), "day": str(s.day)})
                if {x.structure_id for x in s.live_bottoms} != {x.structure_id for x in g.live_bottoms}:
                    add("state:live_bottoms", {"cut": str(cut_day), "day": str(s.day)})
                oa = {k: (v.lifecycle_id, v.tier, v.opened_on, v.last_upgraded_on) for k, v in s.observations.items()}
                ob = {k: (v.lifecycle_id, v.tier, v.opened_on, v.last_upgraded_on) for k, v in g.observations.items()}
                if oa != ob:
                    add("state:observations", {"cut": str(cut_day), "day": str(s.day)})
            fs = {x.structure_id: x for x in full.structures}
            for s in pre.structures:
                g = fs.get(s.structure_id)
                if g is None:
                    add("structure:missing_in_full", {"cut": str(cut_day), **st(s)})
                    continue
                if s.confirmed_date is not None and s.confirmed_date != g.confirmed_date:
                    add("structure:confirmed_date", {"cut": str(cut_day), **st(s)})
                if s.invalidated_date is not None and s.invalidated_date != g.invalidated_date:
                    add("structure:invalidated_date", {"cut": str(cut_day), **st(s)})
                if s.confirmed_date is None and g.confirmed_date is not None and g.confirmed_date <= cut_day:
                    add("structure:confirmation_visible_only_in_full", {"cut": str(cut_day), **st(g)})
                if s.invalidated_date is None and g.invalidated_date is not None and g.invalidated_date <= cut_day:
                    add("structure:invalidation_visible_only_in_full", {"cut": str(cut_day), **st(g)})
            pa = pre.assessment
            fa = full.assessments_by_date[cut_day]
            for f in ("stage", "opportunity_stage", "risk_state", "b1_price"):
                if getattr(pa, f) != getattr(fa, f):
                    add(f"assessment:{f}", {"cut": str(cut_day), "prefix": str(getattr(pa, f)), "full": str(getattr(fa, f))})
            if {e.event_id for e in pa.active_events} != {e.event_id for e in fa.active_events}:
                extra = {e.event_id for e in pa.active_events} ^ {e.event_id for e in fa.active_events}
                rules = sorted({cat_of(pre_by_id.get(k) or full_by_id[k]) for k in extra})
                add("assessment:active_events", {"cut": str(cut_day), "rules": rules})
            da = {k: v for k, v in pa.dimensions.items() if k != "量价"}
            dfull = {k: v for k, v in fa.dimensions.items() if k != "量价"}
            if da != dfull:
                add("assessment:dimensions(除量价)", {"cut": str(cut_day), "prefix": da, "full": dfull})
            if pa.dimensions.get("量价") != fa.dimensions.get("量价"):
                add("design_note:量价维度(历史评估不带筹码代理)", {"cut": str(cut_day), "prefix": pa.dimensions.get("量价"), "full": fa.dimensions.get("量价")})
        counts = {k[:-6]: v[0] for k, v in diffs.items() if k.endswith("#count")}
        examples = {k: v for k, v in diffs.items() if not k.endswith("#count")}
        report.append({"series": name, "label": SYNTH_LABEL, "bars": len(bars), "data_hash16": digest,
                       "events_full": len(full.events), "structures_full": len(full.structures),
                       "cuts": n_compared, "diff_counts": counts, "diff_examples": examples})
        print(f"  H11 {name}: {counts}")
    unclassified = {k: v for r in report for k, v in r["diff_counts"].items() if "未归类" in k or k.startswith(("state:", "structure:", "assessment:"))}
    record("H11", {"series": report, "non_attributed_or_state_diffs": unclassified,
                   "verdict": "见 non_attributed_or_state_diffs",
                   "summary": "全链路截断/全历史一致性扫描"})


# ---------------------------------------------------------------- H12
def h12() -> None:
    n = 100
    close = np.linspace(10, 14, n) + np.sin(np.arange(n) / 3) * 0.15
    bars = pd.DataFrame(dict(open=close, high=close + 0.2, low=close - 0.2, close=close,
                             volume=np.full(n, 1e6)), index=pd.bdate_range("2024-01-01", periods=n))
    bars.index.name = "date"
    inp = save_input("H12_short_history", bars, "仅100根日线（EMA120 不可算，周线约20周）")
    res = analyze_bars("T5", bars)
    a = res.assessment
    last = res.history[-1]
    long_factors = [{"kind": kind, "label": f.label_cn, "detail": f.detail_cn}
                    for kind, lst in (("support", a.supports), ("conflict", a.conflicts))
                    for f in lst if f.dimension == "长周期"]
    trad = tradability_checks(res.frame)
    record("H12", {
        "inputs": [inp],
        "daily_long": last.daily_long.value, "weekly_long": last.weekly_long.value,
        "dimension_long_cycle": a.dimensions.get("长周期"),
        "long_cycle_factors": long_factors,
        "tradability_blocked_checks": [c for c in trad["checks"] if c["blocked"]],
        "verdict": "复现（显示层，待确认）",
        "summary": "两条长周期都 unknown 时，长周期维度写“冲突”；可交易性另行按“数据不足”阻断",
    })


def main() -> None:
    t0 = time.time()
    if INPUTS.exists():
        shutil.rmtree(INPUTS)
    meta = {
        "label": SYNTH_LABEL,
        "git_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip(),
        "git_status_src_configs_tests": subprocess.run(["git", "status", "--porcelain", "src", "configs", "tests"], cwd=REPO, capture_output=True, text=True).stdout.strip() or "clean",
        "python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
        "source_sha256": {
            p: hashlib.sha256((REPO / p).read_bytes()).hexdigest()
            for p in (
                "src/lei_signal/compose/pipeline.py", "src/lei_signal/state/machine.py",
                "src/lei_signal/events/log.py", "src/lei_signal/events/lifecycle.py",
                "src/lei_signal/features/pivots.py", "src/lei_signal/data/point_in_time.py",
                "src/lei_signal/data/bar_completeness.py", "src/lei_signal/data/validation.py",
                "src/lei_signal/rules/strict_structure.py", "src/lei_signal/rules/bottom_structure.py",
                "src/lei_signal/rules/volume.py", "src/lei_signal/rules/tradability_gate.py",
                "src/lei_signal/features/weekly_context.py", "src/lei_signal/storage/sqlite_store.py",
                "src/lei_signal/api/routes/symbols.py", "src/lei_signal/api/sell_signals.py",
                "configs/rules.v2.yaml",
            )
        },
    }
    series = scan_series_list()
    for fn in (h01, h02, lambda: h03(series), h04, h05, h06, h07, h08, h09, h10, lambda: h11(series), h12,
               lambda: h01d(series)):
        name = getattr(fn, "__name__", "lambda")
        try:
            fn()
        except Exception:  # noqa: BLE001 - 单项失败须可见，不吞掉
            hid = name.upper() if name != "<lambda>" else f"ERR{len(RESULTS)}"
            RESULTS[hid] = {"verdict": "脚本异常", "traceback": traceback.format_exc()}
            print(f"[{hid}] 脚本异常\n{traceback.format_exc()}")
    meta["elapsed_seconds"] = round(time.time() - t0, 1)
    dump({"meta": meta, "results": RESULTS}, HERE / "results.json")
    shutil.rmtree(TMP, ignore_errors=True)
    print(f"done in {meta['elapsed_seconds']}s")


if __name__ == "__main__":
    main()
