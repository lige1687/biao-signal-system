"""组合层模拟器：把无资金约束的 R 信号流重放到有资金约束的账户曲线上。

依据 docs/handoff-portfolio-layer-prompt.md 与手册 6.3（简版仓位算法 +
海龟降级规则）。本模块不生成信号、不触碰 engine/service——输入是
execute_run 产出的逐笔 trades dict（JSON 兼容），输出事件日权益曲线与
容量统计。规则（手册 6.3 为准）：

1. 单笔风险 = 当前权益 × risk_pct（含回撤降级系数）；股数 = 风险预算 ÷
   (入场价 − 止损价)；平仓损益 = 预算 × r_net（交易成本已含在 r_net 内，
   见 engine FeeModel）。
2. 全局并发上限 max_concurrent：超限时新信号按到达序（signal_date,
   symbol）丢弃并计数（衡量容量约束的代价）。
3. 同池并发上限 pool_concurrent_cap（交易 dict 的 ``pool`` 字段分池；
   None = 不限）——「同一基准日/聚类合计敞口」规则的简化档。
4. 回撤降级（手册 6.3 原文「账户亏损超过 10% 后，新头寸按当前资金 ×
   80% 计算，依此类推」）：权益从峰值回撤每超过一档 dd_threshold，
   新头寸风险再乘一次 dd_factor；权益创新高即恢复 1.0。

无约束对照（现状 = R 累计）= max_concurrent/pool_concurrent_cap 置 None
且关降级，走同一代码路径，保证对照与实验组口径逐项一致。

口径说明（防误读）：
- 权益为「已实现」口径：仅在平仓日变动（信号本身无逐日盯市数据），
  两口径（约束/无约束）共享同一近似，回撤对比仍成立；
- 同一标的已有持仓时新信号丢弃（单一品种一个仓位）；
- 退出日 = 入场日的单笔（当日止损）在入场定价后立即结算；
- 未平仓（exit_date=None）与 r_net=None 的交易不进入模拟（计数留痕）。
"""
from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

#: 交易 dict 必备字段（execute_run 的 _trade_dict 输出子集）。
_REQUIRED_FIELDS = ("symbol", "entry_date", "exit_date", "r_net")


@dataclass(frozen=True, slots=True)
class PortfolioConfig:
    """组合模拟参数（手册 6.3 的可执行化）。"""

    risk_pct: float = 0.01                 # 单笔风险占当前权益比例（基准 1%）
    max_concurrent: int | None = 10        # 全局并发持仓上限（None=不限）
    pool_concurrent_cap: int | None = 6    # 同池并发上限（None=不限）
    dd_deescalate: bool = True             # 回撤降级开关（对照实验可关）
    dd_threshold: float = 0.10             # 降级档距：峰值回撤每超一档再乘
    dd_factor: float = 0.8                 # 降级乘数（手册 6.3 原文 80%）
    initial_equity: float = 1_000_000.0
    #: 市场层总敞口上限（宽度定闸，full_sim 接口）：date_iso -> (0,1]，
    #: 按事件日缩放单笔预算与并发/池上限（ceil，下限 1）。None = 不启用
    #: （行为与历史版本逐位一致）。缺数据日由调用方兜底为 1.0（不挡交易）。
    cap_fn: Callable[[str], float] | None = field(default=None, repr=False,
                                                  compare=False)

    def __post_init__(self) -> None:
        if not 0 < self.risk_pct <= 0.5:
            raise ValueError(f"risk_pct 不合理: {self.risk_pct}")
        if self.max_concurrent is not None and self.max_concurrent < 1:
            raise ValueError(f"max_concurrent 必须 >= 1: {self.max_concurrent}")
        if self.pool_concurrent_cap is not None and self.pool_concurrent_cap < 1:
            raise ValueError(
                f"pool_concurrent_cap 必须 >= 1: {self.pool_concurrent_cap}"
            )
        if not 0 < self.dd_threshold <= 1 or not 0 < self.dd_factor < 1:
            raise ValueError("dd_threshold/dd_factor 取值非法")

    def _cap_on(self, day: str) -> float:
        if self.cap_fn is None:
            return 1.0
        cap = float(self.cap_fn(day))
        return min(max(cap, 0.0), 1.0)

    @property
    def label(self) -> str:
        cap = "不限" if self.max_concurrent is None else self.max_concurrent
        pool = "不限" if self.pool_concurrent_cap is None else self.pool_concurrent_cap
        deesc = "降级开" if self.dd_deescalate else "降级关"
        return f"risk{self.risk_pct:.1%}|N{cap}|池{pool}|{deesc}"


@dataclass(slots=True)
class _Signal:
    """归一化后的一笔信号（全部字段平仓前可知，无泄漏）。"""

    symbol: str
    pool: str
    signal_date: str        # ISO；缺省回落 entry_date
    entry_date: str
    exit_date: str
    r_net: float
    entry_price: float | None
    stop_price: float | None
    seq: int                # 输入序（稳定排序兜底）


@dataclass(slots=True)
class _Position:
    sig: _Signal
    budget: float           # 入场时锁定的风险预算（元）
    shares: float | None    # 预算 ÷ (入场价−止损价)；价格缺失时 None
    factor: float           # 入场时的降级系数（1.0 = 无降级）
    cap: float              # 入场时的市场层敞口上限（1.0 = 无缩放）
    pnl: float | None = None


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]


def _normalize(trades: list[dict], default_pool: str) -> tuple[list[_Signal], dict]:
    """校验、去重、排序。返回 (信号列表, 输入统计)。"""
    stats = {"input": len(trades), "excluded_open": 0, "excluded_no_rnet": 0,
             "excluded_dedup": 0, "excluded_bad_price": 0}
    seen: set[tuple[str, str, str]] = set()
    recs: list[_Signal] = []
    for i, t in enumerate(trades):
        missing = [k for k in _REQUIRED_FIELDS if t.get(k) is None]
        if "exit_date" in missing:
            stats["excluded_open"] += 1
            continue
        if any(missing):
            stats["excluded_no_rnet"] += 1
            continue
        sig_date = _iso(t.get("signal_date")) or _iso(t["entry_date"]) or ""
        key = (str(t["symbol"]), sig_date, _iso(t["entry_date"]) or "")
        if key in seen:
            stats["excluded_dedup"] += 1
            continue
        seen.add(key)
        recs.append(_Signal(
            symbol=str(t["symbol"]),
            pool=str(t.get("pool", default_pool)),
            signal_date=sig_date,
            entry_date=_iso(t["entry_date"]) or "",
            exit_date=_iso(t["exit_date"]) or "",
            r_net=float(t["r_net"]),
            entry_price=float(t["entry_price"]) if t.get("entry_price") else None,
            stop_price=float(t["stop_price"]) if t.get("stop_price") else None,
            seq=i,
        ))
    recs.sort(key=lambda r: (r.entry_date, r.signal_date, r.symbol, r.seq))
    stats["usable"] = len(recs)
    return recs, stats


def _deescalation_factor(equity: float, peak: float, cfg: PortfolioConfig) -> float:
    """手册 6.3 降级：峰值回撤每超过一档 dd_threshold，风险再乘 dd_factor。"""
    if not cfg.dd_deescalate or peak <= 0 or equity >= peak:
        return 1.0
    dd = 1.0 - equity / peak
    level = 0 if dd <= cfg.dd_threshold else int(dd / cfg.dd_threshold)
    return cfg.dd_factor ** level


def _max_drawdown(curve: list[dict], *, seed: float | None = None) -> float:
    """曲线内最大回撤（比例）。seed 显式给定时不以首点为峰值起点。"""
    peak = -math.inf
    mdd = 0.0
    for pt in curve:
        eq = pt["equity"]
        if seed is not None:
            peak = seed
            seed = None
        peak = max(peak, eq)
        if peak > 0:
            mdd = max(mdd, (peak - eq) / peak)
    return mdd


def _cagr(curve: list[dict], initial: float) -> float | None:
    if len(curve) < 2 or initial <= 0 or curve[-1]["equity"] <= 0:
        return None
    d0 = datetime.fromisoformat(curve[0]["date"])
    d1 = datetime.fromisoformat(curve[-1]["date"])
    years = max((d1 - d0).days / 365.25, 1e-9)
    return (curve[-1]["equity"] / initial) ** (1 / years) - 1


def simulate_portfolio(
    trades: list[dict],
    config: PortfolioConfig,
    *,
    default_pool: str = "main",
) -> dict:
    """逐日（事件日）重放信号流，返回权益曲线与容量统计（JSON 兼容 dict）。

    同一事件日内顺序：先平旧仓（释放容量）→ 再按到达序处理入场 →
    当日开当日平的仓位入场后立即结算。权益/峰值/降级系数只在平仓结算后
    更新，入场定价用的是彼时的已实现权益——无未来函数。
    """
    recs, in_stats = _normalize(trades, default_pool)
    by_entry: dict[str, list[_Signal]] = {}
    for r in recs:
        by_entry.setdefault(r.entry_date, []).append(r)

    equity = config.initial_equity
    peak = config.initial_equity
    cum_r = 0.0
    open_pos: dict[str, _Position] = {}
    taken: list[dict] = []
    dropped: list[dict] = []
    curve: list[dict] = []
    busted = False

    def _settle(pos: _Position, when: str) -> None:
        nonlocal equity, peak, cum_r
        pnl = pos.budget * pos.sig.r_net
        equity += pnl
        cum_r += pos.sig.r_net
        peak = max(peak, equity)
        taken.append({
            "symbol": pos.sig.symbol, "pool": pos.sig.pool,
            "signal_date": pos.sig.signal_date, "entry_date": pos.sig.entry_date,
            "exit_date": pos.sig.exit_date, "r_net": pos.sig.r_net,
            "budget": round(pos.budget, 2), "shares": pos.shares,
            "factor": round(pos.factor, 6), "cap": round(pos.cap, 4),
            "pnl": round(pnl, 2),
            "settle": when,
        })

    event_dates = sorted(set(by_entry) | {r.exit_date for r in recs})
    for day in event_dates:
        # -- 1) 旧仓到期结算（先平后开：同日容量可用）--
        for sym in sorted(open_pos):
            pos = open_pos[sym]
            if pos.sig.exit_date == day:
                _settle(pos, "open")
                del open_pos[sym]
        if busted or equity <= 0:
            busted = True
        # -- 2) 当日入场（按 signal_date, symbol 到达序）--
        day_cap = config._cap_on(day)
        for sig in by_entry.get(day, []):
            if busted or equity <= 0:
                dropped.append({**_sig_view(sig), "drop_date": day,
                                "reason": "bust"})
                continue
            pool_open = sum(
                1 for p in open_pos.values() if p.sig.pool == sig.pool)
            if sig.symbol in open_pos:
                dropped.append({**_sig_view(sig), "drop_date": day,
                                "reason": "same_symbol_open"})
                continue
            if config.max_concurrent is not None and len(open_pos) >= max(
                    1, math.ceil(config.max_concurrent * day_cap)):
                dropped.append({**_sig_view(sig), "drop_date": day,
                                "reason": "capacity_full"})
                continue
            if config.pool_concurrent_cap is not None and pool_open >= max(
                    1, math.ceil(config.pool_concurrent_cap * day_cap)):
                dropped.append({**_sig_view(sig), "drop_date": day,
                                "reason": "pool_cap"})
                continue
            factor = _deescalation_factor(equity, peak, config)
            budget = equity * config.risk_pct * factor * day_cap
            shares = None
            if sig.entry_price and sig.stop_price and \
                    sig.entry_price > sig.stop_price:
                shares = budget / (sig.entry_price - sig.stop_price)
            pos = _Position(sig, budget, shares, factor, day_cap)
            if sig.exit_date == day:  # 当日开当日平：立即结算，不占过夜容量
                _settle(pos, "same_day")
            else:
                open_pos[sig.symbol] = pos
        # -- 3) 曲线点 --
        pool_counts: dict[str, int] = {}
        for p in open_pos.values():
            pool_counts[p.sig.pool] = pool_counts.get(p.sig.pool, 0) + 1
        curve.append({
            "date": day, "equity": round(equity, 2),
            "cum_R": round(cum_r, 4), "n_open": len(open_pos),
            "open_by_pool": pool_counts, "cap": round(day_cap, 4),
        })

    return _build_result(config, in_stats, curve, taken, dropped, busted)


def _sig_view(sig: _Signal) -> dict:
    return {"symbol": sig.symbol, "pool": sig.pool,
            "signal_date": sig.signal_date, "entry_date": sig.entry_date,
            "exit_date": sig.exit_date, "r_net": sig.r_net}


def _build_result(
    config: PortfolioConfig,
    in_stats: dict,
    curve: list[dict],
    taken: list[dict],
    dropped: list[dict],
    busted: bool,
) -> dict:
    initial = config.initial_equity
    final = curve[-1]["equity"] if curve else initial
    seg_days_total = 0.0
    open_weighted = 0.0
    max_open = 0
    pool_max: dict[str, int] = {}
    for i, pt in enumerate(curve):
        max_open = max(max_open, pt["n_open"])
        for pool, n in pt["open_by_pool"].items():
            pool_max[pool] = max(pool_max.get(pool, 0), n)
        if i + 1 < len(curve):
            days = (
                datetime.fromisoformat(curve[i + 1]["date"])
                - datetime.fromisoformat(pt["date"])
            ).days
            seg_days_total += days
            open_weighted += pt["n_open"] * days
    avg_open = open_weighted / seg_days_total if seg_days_total else 0.0

    by_reason: dict[str, dict] = {}
    for d in dropped:
        agg = by_reason.setdefault(
            d["reason"], {"n": 0, "forfeited_R": 0.0})
        agg["n"] += 1
        agg["forfeited_R"] += d["r_net"]

    result = {
        "config": {
            "risk_pct": config.risk_pct,
            "max_concurrent": config.max_concurrent,
            "pool_concurrent_cap": config.pool_concurrent_cap,
            "dd_deescalate": config.dd_deescalate,
            "dd_threshold": config.dd_threshold,
            "dd_factor": config.dd_factor,
            "initial_equity": initial,
            "label": config.label,
            "cap_fn_enabled": config.cap_fn is not None,
        },
        "input_stats": in_stats,
        "busted": busted,
        "final_equity": round(final, 2),
        "total_return_pct": round((final / initial - 1) * 100, 3),
        "max_drawdown_pct": round(_max_drawdown(curve, seed=initial) * 100, 3),
        "cagr_pct": round(_cagr(curve, initial) * 100, 3)
        if _cagr(curve, initial) is not None else None,
        "cum_R_taken": round(sum(t["r_net"] for t in taken), 3),
        "n_taken": len(taken),
        "n_dropped": len(dropped),
        "dropped_by_reason": {
            k: {"n": v["n"], "forfeited_R": round(v["forfeited_R"], 3)}
            for k, v in sorted(by_reason.items())
        },
        "concurrency": {
            "max_open": max_open,
            "avg_open": round(avg_open, 3),
            "avg_utilization": round(avg_open / config.max_concurrent, 3)
            if config.max_concurrent else None,
            "pool_max": pool_max,
        },
        "by_year": _year_metrics(curve, taken, dropped, initial),
        "curve": curve,
        "taken": taken,
        "dropped": dropped,
    }
    return result


def _year_metrics(
    curve: list[dict], taken: list[dict], dropped: list[dict], initial: float
) -> dict:
    """分年份：收益率 / 最大回撤 / 已实现 R / 容量丢弃。峰值以年初权益起算。"""
    years = sorted({pt["date"][:4] for pt in curve})
    out: dict[str, dict] = {}
    prev_eq = initial
    for year in years:
        window = [pt for pt in curve if pt["date"][:4] == year]
        year_exits = [t for t in taken if t["exit_date"][:4] == year]
        year_dropped = [d for d in dropped if d["drop_date"][:4] == year]
        eq_end = window[-1]["equity"] if window else prev_eq
        out[year] = {
            "return_pct": round((eq_end / prev_eq - 1) * 100, 3) if prev_eq > 0 else None,
            "max_drawdown_pct": round(_max_drawdown(window, seed=prev_eq) * 100, 3),
            "cum_R": round(sum(t["r_net"] for t in year_exits), 3),
            "n_taken": len(year_exits),
            "n_dropped": len(year_dropped),
            "forfeited_R": round(sum(d["r_net"] for d in year_dropped), 3),
        }
        prev_eq = eq_end
    return out


def unconstrained_config(risk_pct: float, initial_equity: float = 1_000_000.0,
                         ) -> PortfolioConfig:
    """无约束对照：并发/池上限不限、降级关——与现状 R 累计唯一差异是
    按 risk_pct 复利资金化（同一代码路径，口径可比）。"""
    return PortfolioConfig(
        risk_pct=risk_pct, max_concurrent=None, pool_concurrent_cap=None,
        dd_deescalate=False, initial_equity=initial_equity,
    )


__all__ = [
    "PortfolioConfig",
    "simulate_portfolio",
    "unconstrained_config",
]
