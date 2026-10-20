"""诊断「肉眼看到横盘密集区，但 B 模块没信号」卡在哪条（handoff-b-adaptation 任务二）。

用法：
  python scripts/diagnose_dense_zone.py <symbol>
  python scripts/diagnose_dense_zone.py <symbol> --start 2024-03-01 --end 2024-06-01
  python scripts/diagnose_dense_zone.py <symbol> --cb 40 --cl 0.05
  python scripts/diagnose_dense_zone.py <symbol> --scan   # 同时输出全谱可捕捉档

逐日输出 B1 三条件状态：
  1. 时钟三类（|s60|<10% 横盘）—— 给出 s60 年化斜率值；
  2. 六线带宽 max/min-1 —— 给出带宽值与阈值差距；
  3. 横盘寿命 zone_age（时钟三类状态寿命，允许 ≤20 根间歇）—— 给出寿命与 min_bars 差距。
然后标出「时钟三类持续 ≥40 根但 B1 从未激活」的区间各卡在哪条，以及全谱参数空间
（cb∈{20,30,40,63,90,126,180}, cl∈{2%,3%,4%,5%,6%,8%,10%}）中哪些档会捕捉到。

诊断只读行情，不改任何东西；与回测同一份 dense_breakout 内部函数，口径一致。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402

from lei_signal.backtest.runner import load_pool_frames  # noqa: E402
from lei_signal.domain.rules_config import get_rule  # noqa: E402
from lei_signal.rules.clock_classifier import (  # noqa: E402
    TYPE3_SIDEWAYS,
    slope_series,
)
from lei_signal.rules.dense_breakout import (  # noqa: E402
    _LINE_COLUMNS,
    _bandwidth_condition,
    _state_age_series,
)

CB_SPECTRUM = (20, 30, 40, 63, 90, 126, 180)
CL_SPECTRUM = (0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10)

_CLOCK_SHORT = {0: "数据不足", 1: "一类", 2: "二类", 3: "三类", 4: "四类", 5: "五类"}


def _bandwidth_value(frame: pd.DataFrame) -> pd.Series:
    lines = frame[list(_LINE_COLUMNS)].astype(float)
    valid = (lines > 0).all(axis=1)
    ratio = lines.max(axis=1) / lines.min(axis=1) - 1.0
    return ratio.where(valid)


def _zone_exit_bars() -> int:
    spec = get_rule("dense_breakout")
    return int(spec.param("zone_exit_bars", 20))


def diagnose(
    symbol: str,
    *,
    cb: int = 126,
    cl: float = 0.02,
    start: str | None = None,
    end: str | None = None,
    scan: bool = False,
) -> None:
    frames = load_pool_frames()
    if symbol not in frames:
        print(f"[err] {symbol} 不在回测池（需 ≥300 根已缓存行情）")
        sys.exit(1)
    full = frames[symbol]
    # 指标在全帧上计算（s60 需要 60 根预热，先切片会导致前段全 NaN），再按位置切显示区间。
    s60_full, _ = slope_series(full)
    from lei_signal.rules.dense_breakout import clock_series

    clock_full = clock_series(full)
    clock3_full = clock_full == TYPE3_SIDEWAYS
    bandwidth_full = _bandwidth_value(full)
    bandwidth_ok_full = _bandwidth_condition(full, cl)
    zone_age_full = _state_age_series(clock3_full, exit_bars=_zone_exit_bars())
    b1_full = clock3_full & bandwidth_ok_full & (zone_age_full >= cb)

    pos = range(len(full))
    if start:
        pos = [i for i in pos if full.index[i] >= pd.Timestamp(start)]
    if end:
        pos = [i for i in pos if full.index[i] <= pd.Timestamp(end)]
    if not pos:
        print("[err] 指定区间无行情")
        sys.exit(1)
    a, b = pos[0], pos[-1] + 1
    frame = full.iloc[a:b]
    s60 = s60_full.iloc[a:b].reset_index(drop=True)
    clock = clock_full.iloc[a:b].reset_index(drop=True)
    clock3 = clock3_full.iloc[a:b].reset_index(drop=True)
    bandwidth = bandwidth_full.iloc[a:b].reset_index(drop=True)
    zone_age = zone_age_full.iloc[a:b].reset_index(drop=True)
    b1_active = b1_full.iloc[a:b].reset_index(drop=True)

    print(f"=== {symbol} B1 诊断（cb={cb} 根, cl≤{cl:.0%}）===")
    print(
        f"区间 {frame.index[0].date()} ~ {frame.index[-1].date()}，共 {len(frame)} 根；"
        f"B1 激活日 {int(b1_active.sum())} 个\n"
    )

    # ---- 逐日状态表（只打状态变化或临近边界的日子，避免全量刷屏） ----
    header = f"{'日期':<12}{'时钟':<6}{'s60':>8}{'带宽':>8}{'寿命':>6}  状态"
    print(header)
    print("-" * len(header))
    prev_state = None
    for i, ts in enumerate(frame.index):
        c3 = bool(clock3.iloc[i])
        ctype = int(clock.iloc[i])
        b1 = bool(b1_active.iloc[i])
        bw = bandwidth.iloc[i]
        age = int(zone_age.iloc[i])
        s = s60.iloc[i]
        state = (c3, b1)
        # 打印：B1 激活日、状态切换日、或时钟三类但带宽/寿命卡边界（带宽差 ≤50%
        # 或寿命差 ≤10 根），避免全量刷屏。
        bw_block = pd.notna(bw) and bw >= cl
        age_block = age < cb
        near = c3 and not b1 and (
            (pd.notna(bw) and abs(bw - cl) / cl < 0.5) or (cb - age) in range(1, 11)
        )
        if b1 or state != prev_state or near:
            if b1:
                status = "★B1激活"
            elif not c3:
                status = "非横盘"
            else:
                blockers = []
                if bw_block:
                    blockers.append(f"带宽{bw * 100:.2f}%≥{cl:.0%}")
                if age_block:
                    blockers.append(f"寿命{age}<{cb}")
                status = "卡 " + " / ".join(blockers) if blockers else "数据不足"
            print(
                f"{str(ts.date()):<12}{_CLOCK_SHORT.get(ctype, str(ctype)):<6}"
                f"{s * 100 if pd.notna(s) else float('nan'):>7.1f}%"
                f"{bw * 100 if pd.notna(bw) else float('nan'):>7.2f}%"
                f"{age:>6}  {status}"
            )
        prev_state = state

    # ---- 找「肉眼横盘但系统不认」区间 ----
    print("\n=== 时钟三类持续 ≥40 根但 B1 未激活的区间 ===")
    misses = _find_missed_windows(clock3, b1_active, min_len=40)
    if not misses:
        print("（无；所有持续横盘段均在该参数下激活过 B1）")
    for w_start, w_end in misses:
        seg_bw = bandwidth.iloc[w_start:w_end + 1]
        seg_age = zone_age.iloc[w_start:w_end + 1]
        min_bw = float(seg_bw.min())
        max_age = int(seg_age.max())
        d1 = frame.index[w_start].date()
        d2 = frame.index[w_end].date()
        print(f"\n区间 {d1} ~ {d2}（{w_end - w_start + 1} 根）")
        if max_age >= cb:
            gap = min_bw - cl
            print(
                f"  寿命达标（峰值 {max_age}≥{cb}）；卡在带宽：最窄 {min_bw:.2%}，"
                f"比阈值 {cl:.0%} 宽 {gap:.2%} → 需 cl≥{min_bw:.4f}"
            )
        elif min_bw < cl:
            gap = cb - max_age
            print(
                f"  带宽达标（最窄 {min_bw:.2%}<{cl:.0%}）；卡在寿命：峰值 {max_age}，"
                f"差 {gap} 根 → 需 cb≤{max_age}"
            )
        else:
            print(
                f"  两条都不达标：带宽最窄 {min_bw:.2%}（需 cl≥{min_bw:.4f}）、"
                f"寿命峰值 {max_age}（需 cb≤{max_age}）"
            )
        if scan:
            catches = [
                (c, x)
                for c in CB_SPECTRUM
                for x in CL_SPECTRUM
                if c <= max_age and x > min_bw
            ]
            if catches:
                lo_c, hi_c = min(c for c, _ in catches), max(c for c, _ in catches)
                lo_x, hi_x = min(x for _, x in catches), max(x for _, x in catches)
                print(
                    f"  全谱可捕捉：cb∈[{lo_c}..{hi_c}] 且 cl∈[{lo_x:.0%}..{hi_x:.0%}]"
                    f"（共 {len(catches)} 档；cb 越短/cl 越宽越宽松）"
                )
            else:
                print("  全谱无档可捕捉（横盘太短或带宽始终 >10%）")


def _find_missed_windows(
    clock3: pd.Series, b1_active: pd.Series, *, min_len: int
) -> list[tuple[int, int]]:
    """连续 clock3 段（允许 ≤20 根间歇，与 zone_age 同口径），长度 ≥min_len
    且段内 B1 从未激活，返回 [(start_idx, end_idx)]。"""
    runs: list[tuple[int, int]] = []
    n = len(clock3)
    i = 0
    tol = _zone_exit_bars()
    while i < n:
        if not bool(clock3.iloc[i]):
            i += 1
            continue
        j = i
        gap = 0
        last = i
        while j < n:
            if bool(clock3.iloc[j]):
                last = j
                gap = 0
            else:
                gap += 1
                if gap > tol:
                    break
            j += 1
        if last - i + 1 >= min_len and not bool(b1_active.iloc[i:last + 1].any()):
            runs.append((i, last))
        i = last + 1
    return runs


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("symbol")
    ap.add_argument("--cb", type=int, default=126, help="minimum_consolidation_bars（默认 126）")
    ap.add_argument("--cl", type=float, default=0.02, help="cluster_threshold（默认 0.02）")
    ap.add_argument("--start", default=None, help="起始日 YYYY-MM-DD")
    ap.add_argument("--end", default=None, help="结束日 YYYY-MM-DD")
    ap.add_argument("--scan", action="store_true", help="对每个漏检区间扫全谱可捕捉档")
    args = ap.parse_args()
    diagnose(args.symbol, cb=args.cb, cl=args.cl, start=args.start, end=args.end, scan=args.scan)


if __name__ == "__main__":
    main()
