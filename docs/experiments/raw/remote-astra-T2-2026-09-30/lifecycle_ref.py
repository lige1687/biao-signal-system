"""T2 完整 A 回调参考生命周期（研究适配草案 v0：draft / not approved / not evaluated）。

只用当日及此前已完成日线字段；小时确认未接入，一律输出 unknown，不用日线代替。
每个开关的“推荐值”与“生产值”见 RECOMMENDED / PRODUCTION；逐条依据见 T2/lifecycle.md：
  episode_reset_on_black  D1 LEI 转黑是否结束趋势段（从而重置首次计数）
  pre_entry_low_cancel    D2 入场前收盘跌破触碰以来低点是否作废候选（把 A5 前移）
  zone_exit               D3 未入场时何时结束候选：'band'=收盘回到触碰带上方；
                          'prior_high'=收盘超过回撤前高点（回撤已走完、未给进入）
  arm_rule                D4 'departure'=先有一整天最低价离开触碰带；'close_above_ma'=收盘在 SMA_N 上
  direction_check         D5 'daily'=候选期间每天要求 close > close_lagN；'touch_only'=只查触碰日
  structure_recheck       D6 A3 底部构造每天重核有效性（False=首次命中后缓存）
  gap_first               D7 缺价打断趋势段后首次状态：'unknown' 或 'restart'（重新记首次）
  a3_mode                 D8 'any'=实现 A3“至少一种”；'structure_required'=体系 §4.4 日线部分
  hold_until_both_variants  生产把早期版、确认版放在同一个回撤候选里，两版都发出才结束；
                          研究读法按所选版本入场即结束（两版分别运行）
"""
from __future__ import annotations

from dataclasses import dataclass

GROUPS = (20, 60, 120)
NEED = ["open", "high", "low", "close"] + [f"{p}{n}" for p in ("sma", "ema", "close_lag")
                                           for n in (20, 60, 120)]
RECOMMENDED = dict(episode_reset_on_black=False, pre_entry_low_cancel=False,
                   zone_exit="prior_high", arm_rule="departure", direction_check="daily",
                   structure_recheck=True, gap_first="unknown", a3_mode="any",
                   hold_until_both_variants=False)
PRODUCTION = dict(episode_reset_on_black=True, pre_entry_low_cancel=True, zone_exit="band",
                  arm_rule="close_above_ma", direction_check="touch_only",
                  structure_recheck=False, gap_first="restart", a3_mode="any",
                  hold_until_both_variants=True)


@dataclass
class Cycle:
    touch_date: str
    first: bool | None
    low_run: float
    peak: float
    a3_struct: str | None = None
    a3_reclaim: bool = False
    early_done: bool = False
    conf_done: bool = False


def active_structure(structures, start: str, as_of: str):
    """[start, as_of] 内确认、as_of 当日仍有效的最新底部构造。"""
    best = None
    for s in structures:
        if start <= s["confirmed_date"] <= as_of and not (
                s.get("invalidated_date") and s["invalidated_date"] <= as_of):
            if best is None or s["confirmed_date"] > best["confirmed_date"]:
                best = s
    return best


def run_reference(rows, *, structures=(), atr=1.0, k_atr=1.0, entry_variant="early",
                  target=None, groups=GROUPS, **opts):
    o = {**RECOMMENDED, **opts}
    ev, episode, gap_broke, prev = [], None, False, None
    armed, used, peak, cyc = {}, {}, {}, {g: None for g in groups}

    def close_cycle(g, day, kind, reason, **extra):
        c = cyc[g]
        ev.append(dict(date=day, group=g, type=kind, reason=reason, touch=c.touch_date,
                       first=c.first, **extra))
        cyc[g], used[g], armed[g] = None, True, False

    exit_reason = ("left_zone_no_entry" if o["zone_exit"] == "band" else "resumed_without_entry")

    def zone_exit(r, c, band):
        return (o["zone_exit"] == "band" and r["close"] > band) or (
            o["zone_exit"] == "prior_high" and r["close"] > c.peak)

    def signal(g, day, r, c, variant):
        b = target(day, r["close"]) if target else None
        risk = r["close"] - c.low_run
        return dict(date=day, group=g, type="signal", reason="A4_" + variant, variant=variant,
                    touch=c.touch_date, first=c.first, A_ref=r["close"], C=round(c.low_run, 9),
                    execute="next_allowed_open",
                    a3_source="structure" if c.a3_struct else "ema20_reclaim",
                    a3_structure=c.a3_struct, lower_timeframe="unknown_not_connected",
                    B=b, B_status="available" if b else "unknown_pending_T1",
                    rr=round((b - r["close"]) / risk, 6) if b and risk > 0 else None)

    def end_episode(day, reason):
        for g in groups:
            if cyc[g]:
                close_cycle(g, day, "cancel", reason)
        ev.append(dict(date=day, type="episode_end", reason=reason))

    for r in rows:
        day = r["date"]
        if not all(r.get(c) is not None for c in NEED):
            if episode:
                end_episode(day, "data_gap")
                gap_broke = True
            episode, prev = None, None
            continue
        sma_stack = r["sma20"] > r["sma60"] > r["sma120"]
        gate = (sma_stack and r["ema20"] > r["ema60"] > r["ema120"] and r["clock"] == 2
                and r["weekly"] is True)
        black = r["close"] < r["ema20"] and r["close"] < r["close_lag20"]
        if not sma_stack:
            gap_broke = False
        if episode and (not sma_stack or r["close"] < r["sma120"]
                        or (o["episode_reset_on_black"] and black)):
            end_episode(day, "black" if sma_stack and r["close"] >= r["sma120"] else "stack_or_sma120")
            episode, prev = None, r
            continue
        if episode is None:
            if not gate:
                prev = r
                continue
            known = not (gap_broke and o["gap_first"] == "unknown")
            episode, gap_broke = {"id": day, "first_known": known}, False
            armed, used, peak = ({g: False for g in groups}, {g: False for g in groups},
                                 {g: r["high"] for g in groups})
            ev.append(dict(date=day, type="episode_open", first_known=known))
        a = r.get("atr20", atr)
        if a is None or not a > 0:  # 与生产一致：ATR 不可用的日子不推进回撤候选
            prev = r
            continue
        reclaim = prev is not None and prev["close"] <= prev["ema20"] and r["close"] > r["ema20"]
        for g in groups:
            band = r[f"sma{g}"] + k_atr * a
            c = cyc[g]
            if c is not None:
                if o["pre_entry_low_cancel"] and r["close"] < c.low_run:
                    close_cycle(g, day, "cancel", "A5_low_broken_before_entry")
                    continue
                if o["direction_check"] == "daily" and not r["close"] > r[f"close_lag{g}"]:
                    close_cycle(g, day, "cancel", "direction_changed")
                    continue
                c.a3_reclaim = c.a3_reclaim or reclaim
                if o["structure_recheck"] or c.a3_struct is None:
                    s = active_structure(structures, c.touch_date, day)
                    c.a3_struct = s["id"] if s else (None if o["structure_recheck"] else c.a3_struct)
                c.low_run = min(c.low_run, r["low"])
                a3 = c.a3_struct is not None or (o["a3_mode"] == "any" and c.a3_reclaim)
                trig = (r["clock"] == 2 and r["weekly"] is True and prev is not None
                        and r["close"] > r["ema20"] and r["ema20"] > prev["ema20"] and a3)
                conf = trig and r["close"] > r["close_lag20"]
                if o["hold_until_both_variants"]:
                    for variant, hit in (("early", trig and not c.early_done),
                                         ("confirmed", conf and not c.conf_done)):
                        if hit:
                            ev.append(signal(g, day, r, c, variant))
                            setattr(c, "early_done" if variant == "early" else "conf_done", True)
                    if c.early_done and c.conf_done:
                        cyc[g], used[g], armed[g] = None, True, False
                        continue
                    if not c.early_done and not c.conf_done and zone_exit(r, c, band):
                        close_cycle(g, day, "cancel", exit_reason)
                    continue
                if conf if entry_variant == "confirmed" else trig:
                    ev.append(signal(g, day, r, c, entry_variant))
                    cyc[g], used[g], armed[g] = None, True, False
                    continue
                if zone_exit(r, c, band):
                    close_cycle(g, day, "cancel", exit_reason)
                continue
            if o["arm_rule"] == "departure":
                if r["low"] > band:
                    armed[g], peak[g] = True, max(peak[g], r["high"]) if armed[g] else r["high"]
                    continue
                peak[g] = max(peak[g], r["high"])
            elif r["close"] > r[f"sma{g}"]:
                armed[g], peak[g] = True, max(peak[g], r["high"])
            if armed[g] and r["clock"] == 2 and r["low"] <= band and r["close"] > r[f"close_lag{g}"]:
                first = (not used[g]) if episode["first_known"] else None
                cyc[g] = Cycle(day, first, r["low"], peak[g], a3_reclaim=reclaim)
                if not o["structure_recheck"]:
                    s = active_structure(structures, day, day)
                    cyc[g].a3_struct = s["id"] if s else None
                ev.append(dict(date=day, group=g, type="touch", first=first))
        prev = r
    return ev
