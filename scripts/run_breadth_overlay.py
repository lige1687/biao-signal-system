"""宽度极值叠加交易系统实验（用户口径·2026-08-27 第二轮）。

用户方向（复述自用户原话，非手册 E 配置型）：
- 形态一（极值买卖叠加）：极值低时结合买入信号买入/上浮投入；极值高时
  **卖出**（直接强平持仓，只做多、无对冲）。
- 形态二（仓位管理·软）：极值低+有信号 → 增大投入；极值高+有信号 →
  减少/不买；卖出同理（高档强卖、低档不强卖且预算上浮）。
- 两档阈值都测：85/15 一档、80/20 一档；宽度线测 B200 单线与
  B50+B200 双线（用户图例口径）。
- 全 A 宽度已回填 1993→2026（本轮信号流受回测深池限制仍为 2016+，
  纯宽度层覆盖 24 年）。

判定标准（事前写死，跑之前落 docstring，跑完不许改）：
- J-M1（形态二主判）：该臂 终值 >= 1.05 × 现行闸 full_v2 终值
  且 阴跌段(2021-06-18→2024-02-29)DD <= full_v2 + 3pp
  且 2026 年内 DD <= full_v2 + 3pp。
- J-S1（形态一强平判）：对同参数无强平版：阴跌段 DD 改善 >= 3pp
  且 2026DD <= 10% 且 终值 >= 0.95 × 无强平版。
- 三考题（对 unc 无约束）照 full_stack 口径全部报告：
  阴跌段 DD <= 0.6×unc、2026DD <= 10%、终值 >= 0.7×unc。
- 「放大版」乘数 1.5 撞「risk_pct 钉死 <=1%」铁律：合规版（上浮关，
  <=1.0）同测隔离贡献；放大版仅观察、待拍板。

口径：
- 信号流 = A 门禁(cm0.5+shrink+基准非横+stage>=4) + B' 去重后流
  （与 full_stack 完全同源，复用缓存 run JSON，无新 execute_run）。
- 宽度周频信号、t+1 生效（与 position_cap_map 同防前视口径）；
  顶部强平 = 区 episode 首日收盘确认、t+1 开盘强平所有持仓（一次
  连续在场只触发一次）；强平价 = t+1 开盘（池内 bars），强平笔的
  费用近似沿用原笔 fee 拖累（fee_R = 原 gross R − 原 r_net，声明）。
- 乘数表（B200 单线）：
    m_8515: <=15→1.5, >=85→0.25, 其间 1.0
    m_8020: <=20→1.5, >=80→0.25, 其间 1.0
    m_8020_comp(合规): <=20→1.0, >=80→0.25
    m_8020_zero: <=20→1.5, >=80→0.0
  双线（B50 与 B200 同时入档才算）：
    d_8515 / d_8025 同乘数。注：双线低档极稀有（A 股 B50<=20 且
    B200<=20 几乎不发生），低档乘数基本不触发——如实报告。
- 强平臂：s85(在 m_8515 上)、s80(在 m_8020 上)、s80d(在 d_8020 上)。
- 追加（跑完 m/s 臂后按发现追加预登记，2026-08-27 当日落死）：
  混合臂 = 现行五档闸仅改过热档（中段压缩不动）：
    h_025: (20,1.0)(40,0.8)(60,0.6)(85,0.4)(999,0.25)
    h_040: 同上末档 0.40
    h_80:  (20,1.0)(40,0.8)(60,0.6)(80,0.5)(999,0.25)
  J-H2（混合臂判）：终值 >= 1.25 × full_v2 且 阴跌段 DD <= 15%
  且 2026DD <= 10%（回撤保护不弃、过热档收益拿回）。
- 第三轮追加（2026-08-27，跑前落死）：
  (a) 混合臂微调（过热档修法 v2），J-H3 同 J-H2 三条件：
    ha_045: (20,1.0)(40,0.8)(60,0.6)(80,0.45)(999,0.25)
    ha_050_030: (20,1.0)(40,0.8)(60,0.6)(80,0.50)(999,0.30)
    ha_050_040: (20,1.0)(40,0.8)(60,0.6)(80,0.50)(999,0.40)
    ha_070_050: (20,1.0)(40,0.8)(60,0.7)(80,0.50)(999,0.40)
  (b) 跨引擎/跨标的稳健性：宽度闸（full_v2 与 h_80 固定臂）叠加到
    五条信号流：A门禁+B'（主）、A 全量（ETF）、B'（个股）、
    C+D（个股反转/假突破）、全模块 A+B'+C+D。
    J-X1（全模块流上）：ha 臂 终值 >= 1.15 × full_v2(同流) 且
    阴跌 DD <= full_v2(同流) + 3pp 且 2026DD <= full_v2(同流) + 2pp。
    其余流只报告不判定（样本结构不同，判定量省着花）。
- 第四轮追加（2026-08-27，跑前落死）：
  (a) 背离路牌 + h_80（dv_h80）：背离 = 基准 000300.SS 收盘 ≥ 过去
    120 日最高收盘 × 0.999 且 B200 较 20 交易日前下降 >= 5pp（周频
    收盘判定、t+1 生效、条件式非持续）；生效日压仓乘数 0.3，与 h_80
    档位 cap 取 min。
  (b) 停新买软方案：fz_v2_0 = TIERS_V2 末档 0.1→0.0（>=85 停新买）；
    fz_80_0 = (20,1.0)(40,0.8)(60,0.6)(80,0.0)(999,0.0)（>=80 停新买）。
  (c) 分账制（ETF 腿上闸、个股腿不上闸）：split_5050 = A_only@h_80
    （50 万）+ Bp_only@无闸（50 万）子账户各自模拟、日权益曲线合并
    （子账户间不再平衡，声明）；split_6040 同理 60/40；split_full =
    A@h_80（50 万）+ B'+C+D@无闸（50 万）。
  J-H4（新臂统一判，同 J-H 三条件）：终值 >= 1.25 × full_v2(主流)
  且 阴跌 DD <= 15% 且 2026DD <= 10%；分账臂按合并日权益曲线算
  阴跌/2026DD（年度回撤种子 = 上年末权益，与 _year_metrics 同口径）。

纪律：纯实验脚本；不改 src/configs/web；N 累计叠加（本轮 9 臂 ×
3 判定 ≈ 10 组判定量）。
输出：docs/experiments/raw/breadth_overlay/
复现：python3 scripts/run_breadth_overlay.py（约 2 分钟）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from run_full_stack_sim import (  # noqa: E402
    SEG_HI,
    SEG_LO,
    gate_a,
    load_runs,
    seg_max_dd,
)

from lei_signal.backtest.full_sim import (  # noqa: E402
    TIERS_V2,
    cap_fn_from_map,
    dedup_signals,
    position_cap_map,
)
from lei_signal.backtest.portfolio import (  # noqa: E402
    PortfolioConfig,
    simulate_portfolio,
    unconstrained_config,
)
from lei_signal.backtest.runner import load_pool_frames  # noqa: E402

RAW = REPO / "docs/experiments/raw/breadth_overlay"
RAW.mkdir(parents=True, exist_ok=True)
CN_BREADTH = Path.home() / ".lei_signal_lab/cache/a_share_ma_breadth_history.json"

LO, HI = 15.0, 85.0
LO2, HI2 = 20.0, 80.0
BOOST, CUT, CUT_ZERO = 1.5, 0.25, 0.0


class BoostConfig(PortfolioConfig):
    """研究档：乘数允许 >1（极值低上浮）；其余与 PortfolioConfig 同。"""

    def _cap_on(self, day: str) -> float:
        return float(self.cap_fn(day)) if self.cap_fn else 1.0


def load_breadth() -> pd.DataFrame:
    """A 股宽度研究史：优先 33 年 full_history（回填管道独立文件，
    2026-08-27 双写者事故后分离），缺则回落 live 短史文件。"""
    full = CN_BREADTH.parent / "a_share_ma_breadth_full_history.json"
    path = full if full.exists() else CN_BREADTH
    df = pd.DataFrame(json.loads(path.read_text()))
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date").sort_index()[["ma50_pct", "ma200_pct"]]


def weekly_multiplier_map(br: pd.DataFrame, *, low: float, high: float,
                          boost: float, cut: float, dual: bool
                          ) -> dict[str, float]:
    """周频（每周最后宽度日）收盘取宽度 → t+1 生效的乘数表。
    dual=True 时两线同时入档才算；单线版只看 B200。"""
    days = br.index
    week_key = [(d.isocalendar().week, d.year) for d in days]
    is_sig = [i + 1 == len(days) or week_key[i + 1] != week_key[i]
              for i in range(len(days))]
    b50, b200 = br["ma50_pct"], br["ma200_pct"]
    out: dict[str, float] = {}
    for i, d in enumerate(days):
        if not is_sig[i]:
            continue
        if dual:
            lo_hit = b50[d] <= low and b200[d] <= low
            hi_hit = b50[d] >= high and b200[d] >= high
        else:
            lo_hit, hi_hit = b200[d] <= low, b200[d] >= high
        m = boost if lo_hit else (cut if hi_hit else 1.0)
        if i + 1 < len(days):  # t+1 生效（下一宽度交易日，日频索引）
            out[str(days[i + 1].date())] = round(m, 4)
    return out


def sell_exec_days(br: pd.DataFrame, high: float, dual: bool) -> list[str]:
    """顶部区 episode 首日收盘确认 → t+1（下一宽度交易日）强平执行日。
    一次连续在场只触发一次（离场后再次进场才再触发）。"""
    b50, b200 = br["ma50_pct"], br["ma200_pct"]
    zone = pd.Series(
        ((b50 >= high) & (b200 >= high)) if dual else (b200 >= high),
        index=br.index)
    out, in_prev = [], False
    for d, z in zone.items():
        if z and not in_prev:
            pos = br.index.get_loc(d)
            if pos + 1 < len(br.index):
                out.append(str(br.index[pos + 1].date()))
        in_prev = bool(z)
    return out


def divergence_map(br: pd.DataFrame, bench: pd.DataFrame | None,
                   lookback: int = 120, drop_pp: float = 5.0,
                   press: float = 0.3) -> dict[str, float]:
    """背离路牌（预登记定义见 docstring）：基准收盘 ≥ 过去 lookback 日
    最高收盘 × 0.999 且 B200 较 20 交易日前下降 ≥ drop_pp → 该周信号日
    t+1 生效压仓乘数 press；其余日 1.0（条件式，非持续状态）。"""
    if bench is None or bench.empty:
        return {}
    close = bench["close"].reindex(br.index).ffill()
    roll_max = close.rolling(lookback, min_periods=60).max()
    b200 = br["ma200_pct"]
    d20 = b200 - b200.shift(20)
    div = (close >= roll_max * 0.999) & (d20 <= -drop_pp)
    days = br.index
    week_key = [(d.isocalendar().week, d.year) for d in days]
    is_sig = [i + 1 == len(days) or week_key[i + 1] != week_key[i]
              for i in range(len(days))]
    out: dict[str, float] = {}
    for i in range(len(days)):
        if is_sig[i] and bool(div.iloc[i]) and i + 1 < len(days):
            out[str(days[i + 1].date())] = press
    return out


def force_sell_stream(stream: list[dict], sell_days: list[str],
                      frames: dict) -> tuple[list[dict], int]:
    """强平叠加：持仓期内遇强平日 → 截断为该日开盘退出。
    r_net = (强平价−entry)/(entry−stop) − fee_R，fee_R 取原笔
    （gross_R − r_net）作费用拖累近似（声明）。返回 (新流, 强平笔数)。"""
    sell_set = sorted(sell_days)
    out, n_forced = [], 0
    for t in stream:
        forced = next((d for d in sell_set
                       if t["entry_date"] < d < t["exit_date"]), None)
        if forced is None:
            out.append(t)
            continue
        f = frames.get(t["symbol"])
        if f is None or forced not in f.index:
            out.append(t)  # 无行情可用：不强平（保守）
            continue
        px = float(f.at[forced, "open"])
        e, s = float(t["entry_price"]), float(t["stop_price"])
        gross0 = (float(t["exit_price"]) - e) / (e - s)
        fee_r = max(gross0 - float(t["r_net"]), 0.0)
        r_forced = (px - e) / (e - s) - fee_r
        out.append({**t, "exit_date": forced, "exit_price": px,
                    "r_net": round(r_forced, 4),
                    "forced_by_breadth": True})
        n_forced += 1
    return out, n_forced


def main() -> None:
    runs = load_runs(rerun=False)
    a_gated = [{**t, "pool": "A_ETF"} for t in gate_a(runs["A"])]
    b_all = [{**t, "pool": "B_STOCK"} for t in runs["B'"]]
    stream_base, _ = dedup_signals(a_gated + b_all)
    print(f"[输入流] 去重后 {len(stream_base)} 笔 / cumR "
          f"{sum(t['r_net'] for t in stream_base):+.1f}")

    br = load_breadth()
    b200_map = {str(d.date()): float(v)
                for d, v in br["ma200_pct"].items()}
    frames = load_pool_frames()

    def cfg(cap_map: dict[str, float], boost: bool) -> PortfolioConfig:
        cls = BoostConfig if boost else PortfolioConfig
        return cls(risk_pct=0.01, max_concurrent=10, pool_concurrent_cap=6,
                   dd_deescalate=True, cap_fn=cap_fn_from_map(cap_map))

    arms: dict[str, dict] = {}

    # ---- 基线 ----
    unc = simulate_portfolio(stream_base, unconstrained_config(0.01))
    fund = simulate_portfolio(
        stream_base,
        PortfolioConfig(risk_pct=0.01, max_concurrent=10,
                        pool_concurrent_cap=6, dd_deescalate=True))
    cap_v2 = cap_fn_from_map(position_cap_map(b200_map, TIERS_V2))
    full_v2 = simulate_portfolio(
        stream_base,
        PortfolioConfig(risk_pct=0.01, max_concurrent=10,
                        pool_concurrent_cap=6, dd_deescalate=True,
                        cap_fn=cap_v2))

    # ---- 形态二：乘数臂（无强平）----
    tables = {
        "m_8515": dict(low=LO, high=HI, boost=BOOST, cut=CUT, dual=False),
        "m_8020": dict(low=LO2, high=HI2, boost=BOOST, cut=CUT, dual=False),
        "m_8020_comp": dict(low=LO2, high=HI2, boost=1.0, cut=CUT, dual=False),
        "m_8020_zero": dict(low=LO2, high=HI2, boost=BOOST, cut=CUT_ZERO,
                            dual=False),
        "d_8515": dict(low=LO, high=HI, boost=BOOST, cut=CUT, dual=True),
        "d_8020": dict(low=LO2, high=HI2, boost=BOOST, cut=CUT, dual=True),
    }
    for name, tb in tables.items():
        m_map = weekly_multiplier_map(br, **tb)
        res = simulate_portfolio(stream_base, cfg(m_map, tb["boost"] > 1.0))
        arms[name] = {"res": res, "map": m_map, "forced": 0}

    # ---- 形态一：强平臂 ----
    sell_specs = {
        "s85": ("m_8515", HI, False),
        "s80": ("m_8020", HI2, False),
        "s80d": ("d_8020", HI2, True),
    }
    for name, (base, high, dual) in sell_specs.items():
        sd = sell_exec_days(br, high, dual)
        stream_f, n_f = force_sell_stream(stream_base, sd, frames)
        tb = tables[base]
        m_map = weekly_multiplier_map(br, **tb)
        res = simulate_portfolio(stream_f, cfg(m_map, tb["boost"] > 1.0))
        arms[name] = {"res": res, "map": m_map, "forced": n_f,
                      "sell_days": len(sd)}

    # ---- 追加：混合臂（五档闸仅改过热档，J-H2 事前落死见 docstring）----
    for name, tiers in (
        ("h_025", ((20, 1.0), (40, 0.8), (60, 0.6), (85, 0.4), (999, 0.25))),
        ("h_040", ((20, 1.0), (40, 0.8), (60, 0.6), (85, 0.4), (999, 0.40))),
        ("h_80", ((20, 1.0), (40, 0.8), (60, 0.6), (80, 0.5), (999, 0.25))),
    ):
        hmap = position_cap_map(b200_map, tiers)
        res = simulate_portfolio(stream_base, cfg(hmap, False))
        arms[name] = {"res": res, "map": hmap, "forced": 0, "hybrid": True}

    # ---- 第三轮(a)：混合臂微调（J-H3，判据同 J-H2）----
    ha_tiers = {
        "ha_045": ((20, 1.0), (40, 0.8), (60, 0.6), (80, 0.45), (999, 0.25)),
        "ha_050_030": ((20, 1.0), (40, 0.8), (60, 0.6), (80, 0.50), (999, 0.30)),
        "ha_050_040": ((20, 1.0), (40, 0.8), (60, 0.6), (80, 0.50), (999, 0.40)),
        "ha_070_050": ((20, 1.0), (40, 0.8), (60, 0.7), (80, 0.50), (999, 0.40)),
    }
    for name, tiers in ha_tiers.items():
        hmap = position_cap_map(b200_map, tiers)
        res = simulate_portfolio(stream_base, cfg(hmap, False))
        arms[name] = {"res": res, "map": hmap, "forced": 0,
                      "hybrid3": True}

    # ---- 第三轮(b)：跨引擎/跨标的稳健性（J-X1 见 docstring）----
    def brief(r: dict) -> dict:
        return {"final": round(r["final_equity"]),
                "global_dd": r["max_drawdown_pct"],
                "seg_dd": seg_max_dd(r["curve"], SEG_LO, SEG_HI),
                "dd26": r["by_year"].get("2026", {}).get(
                    "max_drawdown_pct")}

    a_all = [{**t, "pool": "A_ETF"} for t in runs["A"]]
    cd_all = [{**t, "pool": "CD_STOCK"} for t in runs["C"] + runs["D"]]
    streams = {
        "main_ABp": stream_base,
        "A_only": dedup_signals(a_all)[0],
        "Bp_only": dedup_signals(b_all)[0],
        "CD_only": dedup_signals(cd_all)[0],
        "full_all": dedup_signals(a_all + b_all + cd_all)[0],
    }
    cap_h80 = cap_fn_from_map(position_cap_map(
        b200_map, ((20, 1.0), (40, 0.8), (60, 0.6), (80, 0.5), (999, 0.25))))
    robust_gates = {"fund_only": None, "full_v2": cap_v2, "h_80": cap_h80}
    robustness: dict[str, dict] = {}
    for sname, s in streams.items():
        row = {"n": len(s), "cumR": round(sum(t["r_net"] for t in s), 1)}
        for gname, gfn in robust_gates.items():
            kw = dict(cap_fn=gfn) if gfn is not None else {}
            res = simulate_portfolio(
                s, PortfolioConfig(risk_pct=0.01, max_concurrent=10,
                                   pool_concurrent_cap=6, dd_deescalate=True,
                                   **kw))
            row[gname] = brief(res)
        robustness[sname] = row

    # ---- 第四轮：背离路牌 / 停新买 / 分账制（预登记见 docstring）----
    bench = load_pool_frames().get("000300.SS")
    dv_map = divergence_map(br, bench)
    f_h80 = cap_fn_from_map(position_cap_map(
        b200_map, ((20, 1.0), (40, 0.8), (60, 0.6), (80, 0.5), (999, 0.25))))
    f_dv = cap_fn_from_map(dv_map)
    dv_h80_fn = lambda day: min(f_h80(day), f_dv(day))  # noqa: E731
    r4_arms = {
        "dv_h80": {"fn": dv_h80_fn, "stream": stream_base},
        "fz_v2_0": {"fn": cap_fn_from_map(position_cap_map(
            b200_map, ((20, 1.0), (40, 0.8), (60, 0.6), (85, 0.4),
                       (999, 0.0)))), "stream": stream_base},
        "fz_80_0": {"fn": cap_fn_from_map(position_cap_map(
            b200_map, ((20, 1.0), (40, 0.8), (60, 0.6), (80, 0.0),
                       (999, 0.0)))), "stream": stream_base},
    }
    for name, spec in r4_arms.items():
        res = simulate_portfolio(
            spec["stream"], PortfolioConfig(
                risk_pct=0.01, max_concurrent=10, pool_concurrent_cap=6,
                dd_deescalate=True, cap_fn=spec["fn"]))
        arms[name] = {"res": res, "map": None, "forced": 0, "round4": True}

    def merge_sims(runs_spec: list[tuple[list, dict, float]]) -> dict:
        """子账户各自模拟后按日合并权益曲线（不再平衡）。"""
        curves = []
        for s, cfg_kw, init in runs_spec:
            r = simulate_portfolio(
                s, PortfolioConfig(
                    risk_pct=0.01, max_concurrent=10, pool_concurrent_cap=6,
                    dd_deescalate=True, initial_equity=init, **cfg_kw))
            curves.append({p["date"]: p["equity"] for p in r["curve"]})
        dates = sorted(set().union(*[set(c) for c in curves]))
        inits = [init for *_x, init in runs_spec]
        last = list(inits)  # 事件日前按初始资金计（不贡献虚假回撤）
        merged = []
        for d in dates:
            last = [c.get(d, last[i]) for i, c in enumerate(curves)]
            merged.append({"date": d, "equity": sum(last)})
        by_year = {}
        prev = sum(inits)
        gpeak, gdd = prev, 0.0
        for y in sorted({p["date"][:4] for p in merged}):
            win = [p for p in merged if p["date"][:4] == y]
            peak, mdd = prev, 0.0
            for p in win:
                peak = max(peak, p["equity"])
                gpeak = max(gpeak, p["equity"])
                if peak > 0:
                    mdd = max(mdd, (peak - p["equity"]) / peak)
                if gpeak > 0:
                    gdd = max(gdd, (gpeak - p["equity"]) / gpeak)
            by_year[y] = {"max_drawdown_pct": round(mdd * 100, 3)}
            prev = win[-1]["equity"]
        return {"final_equity": merged[-1]["equity"], "curve": merged,
                "by_year": by_year,
                "max_drawdown_pct": round(gdd * 100, 3)}

    no_gate = dict()
    split_specs = {
        "split_5050": [(streams["A_only"], dict(cap_fn=f_h80), 500_000),
                       (streams["Bp_only"], no_gate, 500_000)],
        "split_6040": [(streams["A_only"], dict(cap_fn=f_h80), 600_000),
                       (streams["Bp_only"], no_gate, 400_000)],
        "split_full": [(streams["A_only"], dict(cap_fn=f_h80), 500_000),
                       (dedup_signals(
                           b_all + [{**t, "pool": "CD_STOCK"}
                                    for t in runs["C"] + runs["D"]])[0],
                        no_gate, 500_000)],
    }
    for name, spec in split_specs.items():
        arms[name] = {"res": merge_sims(spec), "map": None, "forced": 0,
                      "round4": True, "split": True}

    # ---- 汇总与判定 ----
    base_v2 = brief(full_v2)
    summary, verdicts = {}, {}
    for name, a in arms.items():
        b = brief(a["res"])
        summary[name] = {**b, "n_forced": a["forced"],
                         "stream_R": round(a["res"].get("cum_R_taken", 0.0),
                                           1)}
        v3 = {"q1_seg": b["seg_dd"] <= 0.6 * brief(unc)["seg_dd"],
              "q2_dd26": (b["dd26"] is not None and b["dd26"] <= 10.0),
              "q3_final": b["final"] >= 0.7 * round(unc["final_equity"])}
        v3["all_pass"] = all(v3.values())
        if name in tables:  # J-M1
            verdicts[name] = {
                "JM1": bool(b["final"] >= 1.05 * base_v2["final"]
                            and b["seg_dd"] <= base_v2["seg_dd"] + 3
                            and b["dd26"] is not None
                            and b["dd26"] <= base_v2["dd26"] + 3),
                **{f"q_{k}": v for k, v in v3.items()}}
        elif a.get("hybrid") or a.get("hybrid3"):  # J-H2 / J-H3 同三条件
            verdicts[name] = {
                "JH": bool(b["final"] >= 1.25 * base_v2["final"]
                           and b["seg_dd"] <= 15.0
                           and b["dd26"] is not None and b["dd26"] <= 10.0),
                **{f"q_{k}": v for k, v in v3.items()}}
        elif a.get("round4"):  # J-H4 同三条件（见 docstring）
            verdicts[name] = {
                "JH4": bool(b["final"] >= 1.25 * base_v2["final"]
                            and b["seg_dd"] <= 15.0
                            and b["dd26"] is not None and b["dd26"] <= 10.0),
                **{f"q_{k}": v for k, v in v3.items()}}
        else:  # J-S1 vs 无强平版
            base_arm = brief(arms[sell_specs[name][0]]["res"])
            verdicts[name] = {
                "JS1": bool(base_arm["seg_dd"] - b["seg_dd"] >= 3
                            and b["dd26"] is not None and b["dd26"] <= 10
                            and b["final"] >= 0.95 * base_arm["final"]),
                **{f"q_{k}": v for k, v in v3.items()}}

    # J-X1：全模块流上 h_80 vs full_v2（预登记见 docstring）
    frow = robustness["full_all"]
    verdicts["JX1_full_all"] = {
        "JX1": bool(frow["h_80"]["final"] >= 1.15 * frow["full_v2"]["final"]
                    and frow["h_80"]["seg_dd"]
                    <= frow["full_v2"]["seg_dd"] + 3
                    and frow["h_80"]["dd26"] is not None
                    and frow["h_80"]["dd26"] <= frow["full_v2"]["dd26"] + 2)}

    out = {
        "date": "2026-08-27",
        "stream": {"n": len(stream_base),
                   "cumR": round(sum(t["r_net"] for t in stream_base), 1)},
        "baselines": {"unc": brief(unc), "fund_only": brief(fund),
                      "full_v2_current": base_v2},
        "arms": summary,
        "robustness_streams": robustness,
        "verdicts": verdicts,
        "notes": {
            "boost_rule_conflict": "乘数 1.5 撞 risk_pct<=1% 钉死条款，"
                                   "放大版仅观察；m_8020_comp 为合规对照",
            "fee_approx": "强平笔费用拖累沿用原笔 fee_R 近似",
            "breadth": "全 A 宽度 1993-04-22→2026-08-18（5207 只存续回算，"
                       "早期幸存者偏差）",
        },
    }
    (RAW / "breadth_overlay_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=str))
    print("\n===== 基线 =====")
    print(json.dumps(out["baselines"], ensure_ascii=False, indent=1))
    print("\n===== 臂（终值/全局DD/阴跌DD/2026DD/强平数）=====")
    for k, v in summary.items():
        print(f"{k:14s}", v)
    print("\n===== 判定 =====")
    print(json.dumps(verdicts, ensure_ascii=False, indent=1))
    print("\n===== 跨引擎稳健性（终值/阴跌DD/2026DD）=====")
    for sname, row in robustness.items():
        print(f"[{sname}] n={row['n']} cumR={row['cumR']}")
        for g in ("fund_only", "full_v2", "h_80"):
            b = row[g]
            print(f"  {g:10s} 终值 {b['final']:>9} 阴跌DD {b['seg_dd']}%"
                  f" 2026DD {b['dd26']}%")


if __name__ == "__main__":
    main()
