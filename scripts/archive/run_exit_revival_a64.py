#!/usr/bin/env python3
"""a6_4 复活实验：A6③ 纯结构止损 + 独立止盈（Prompt G，2026-09-01）。

背景（exit-matrix-report-2026-08-31.md）：a6_3（纯结构止损、无止盈）三模块
全灾难（A: expR −2.174/PF 0.02；B': −1.704/0.01；C: −1.297/0.0）。报告诊断
失败原因是**缺止盈机制**（盈利单全部回吐到初始止损位，PF 趋近 0），不是
结构止损思路本身不行。本实验保留 a6_3 的止损部分不动，额外补独立止盈规则，
组合为新出场变体 a6_4，检验能否从「全灾难」恢复到至少「不劣于默认 a6_1」。

===========================================================================
判定标准（预注册，跑之前写死，跑完不得调整）
===========================================================================
口径：与 exit-matrix 完全一致——全池（load_pool_frames 默认池）、rr_min=None、
fee=standard（单边 5bp）、limit_guard=True、模块冻结配置
A=early+volume_filter:shrink+clock_mult0.5；B'=breakout+cb30/cl3%；C=v3+bias−15%。

止盈候选（预注册，共 5 臂 + 2 基线）：
- a6_4a（ATR 档）：止盈价 = 入场价 + k × ATR20(信号日)，
  k ∈ {1.5, 2.0, 3.0}（2.0 为 prompt 锚点，1.5/3.0 为邻域）。
- a6_4b（结构目标档）：止盈价 = 入场价 + f × (B − 入场价)，B = 规格第 10 节
  目标价（信号日已算出、无泄漏），f ∈ {0.8, 1.0}（1.0 为「到目标位」，
  0.8 为「略前于目标位」邻域）。B 不可计算（None）或 B ≤ 入场价的笔，
  止盈不启用（该笔退化为纯 a6_3，单独计数披露）。

执行纪律（与引擎现有约定一致，不发明新 convention）：
- 止盈/止损均**收盘确认、下一根开盘执行**（§3.3）；跳空按开盘价记账；
- 同一根收盘同时满足止损与止盈时，**止损优先**（保守）；
- A 股跌停卖不出顺延（limit_guard 与引擎同一实现）；
- 止损部分 = a6_3 原逻辑逐字保留（close < C → 次日开盘离场）。

判定（均以 standard 费用、net 口径（工作台「总览」同源 compute_metrics）：
- J1 初步复活（模块级）：expR > 0 且 PF > 1；
- J2 不劣于默认（模块级）：expR ≥ 同模块 a6_1 的 expR 且 PF ≥ 同模块 a6_1 的 PF
  （严格无容差）；
- J3 邻域稳健（模块级）：该候选族在**全部**预注册邻域档位（a6_4a 的 3 档 /
  a6_4b 的 2 档）都满足 J1；
- J4 跨模块判定：同一参数档位在 ≥2/3 模块满足 J2 → 「跨模块复活候选」；
  恰好 1 个模块满足 J2 → 「模块特定候选」；0 个模块满足 J2 → 复活失败
  （即使 J1 通过也只能表述为「止血成功但仍逊于默认」）。
conservative 费用（10bp）仅作压力披露，不参与 J1–J4 判定。

基线复现门槛（不通过则本次作废，不得写报告）：本脚本复跑的 a6_1/a6_3
必须逐位复现归档数字（exit-matrix-report 结果矩阵）：
  A: a6_1 1469 笔/expR 1.179228/PF 1.966303；a6_3 1261/−2.173784/0.020028
  B: a6_1 552/0.358533/1.578290；          a6_3 441/−1.704019/0.008965
  C: a6_1 224/0.127748/1.382214；          a6_3 165/−1.296691/0.000000

实现说明（与「复用工作台 API」的偏差，必须在报告中披露）：工作台
BacktestParams.validate() 只认 4 个内置出场变体，a6_4 无法从 API 注入。
本脚本改为直接调用与工作台 run 完全相同的生产代码路径
（load_pool_frames / prepare_frame / entry_specs_from_events /
filter_specs_by_shrink / filter_specs_by_bias / FeeModel / compute_metrics /
账本 overrides 补丁，全部原样复用），唯一新增代码是带止盈分支的交易循环
（从 engine.simulate_trade 逐行复制 + 一个止盈分支）。可比性由上面的基线
复现门槛保证。

输出：docs/experiments/raw/exit_revival_a64/exit_revival_results.json
（无时间戳字段，字节确定，供 PYTHONHASHSEED=0/42 双跑哈希核对）。
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

# 兼容 shim（2026-09-01 10:52 工作区规则文件被回退到已提交版本，丢掉了
# 未跟踪 backtest 包依赖的两个常量；值取自运行中工作台服务的 /options
# 输出，仅在本脚本进程内补齐，不改动 src/ 任何文件）。
import lei_signal.rules.first_ma_pullback as _fmp  # noqa: E402

if not hasattr(_fmp, "ENTRY_EARLY"):
    _fmp.ENTRY_EARLY = "early"
if not hasattr(_fmp, "ENTRY_CONFIRMED"):
    _fmp.ENTRY_CONFIRMED = "confirmed"

from lei_signal.backtest import service as bt_service  # noqa: E402
from lei_signal.backtest.engine import (  # noqa: E402
    EXIT_COSTBASIS,
    EXIT_STRUCTURE_STOP,
    EntrySpec,
    FeeModel,
    Trade,
    entry_specs_from_events,
    prepare_frame,
    simulate_trade,
)
from lei_signal.backtest.entry_filters import (  # noqa: E402
    filter_specs_by_bias,
    filter_specs_by_shrink,
)
from lei_signal.backtest.metrics import compute_metrics  # noqa: E402
from lei_signal.backtest.runner import _benchmark_clock, load_pool_frames  # noqa: E402
from lei_signal.features.pivots import confirmed_pivots  # noqa: E402

#: 模块冻结配置（与 scripts/run_exit_matrix.py 逐字段一致）。
MODULES = {
    "A": {"module": "A", "entry_variant": "early", "volume_filter": "shrink",
          "bias_filter": None, "overrides": (("clock_mult", 0.5),)},
    "B": {"module": "B", "entry_variant": "breakout", "volume_filter": "none",
          "bias_filter": None,
          "overrides": (("cluster_threshold", 0.03), ("consolidation_bars", 30))},
    "C": {"module": "C", "entry_variant": "v3", "volume_filter": "none",
          "bias_filter": -0.15, "overrides": ()},
}

#: 预注册止盈参数（docstring 判定标准的机器可读副本，两边必须一致）。
ATR_LEVELS = (1.5, 2.0, 3.0)
TARGET_FRACTIONS = (0.8, 1.0)

#: 归档基线（exit-matrix-report-2026-08-31.md / raw JSON，复现门槛）。
ARCHIVED = {
    ("A", "a6_1_costbasis"): (1469, 1.1792278030442684, 1.9663033302762718),
    ("A", "a6_3_structure_stop"): (1261, -2.17378395013909, 0.02002791262066753),
    ("B", "a6_1_costbasis"): (552, 0.3585329893728971, 1.5782903349521902),
    ("B", "a6_3_structure_stop"): (441, -1.7040192746783636, 0.008965459438021954),
    ("C", "a6_1_costbasis"): (224, 0.1277477082902095, 1.382214463867003),
    ("C", "a6_3_structure_stop"): (165, -1.2966910448145645, 0.0),
}

FEE_LABELS = ("standard", "conservative")


@contextmanager
def patched_ledger(overrides: tuple[tuple[str, float], ...]):
    """复刻 service.execute_run 的账本覆盖补丁（overrides 白名单替换文本）。"""
    from lei_signal.domain import rules_config as rc

    text = bt_service._overrides_yaml(overrides)
    if text is None:
        yield
        return
    tmp = Path(tempfile.mkdtemp()) / "rules.yaml"
    tmp.write_text(text, encoding="utf-8")
    rc.load_ruleset.cache_clear()
    orig_path = rc._default_config_path
    rc._default_config_path = lambda: tmp  # type: ignore[assignment]
    try:
        yield
    finally:
        rc.load_ruleset.cache_clear()
        rc._default_config_path = orig_path  # type: ignore[assignment]


def simulate_trade_a64(
    frame,
    spec: EntrySpec,
    *,
    tp_price: float | None,
    fee: FeeModel,
    prepared: dict,
    limit_guard: bool = False,
    tp_reason: str = "tp_hit",
) -> Trade:
    """a6_4 交易循环：engine.simulate_trade 的逐行副本，仅新增止盈分支。

    与 a6_3 的差异只有一处：循环内 `close >= tp_price` 时次日开盘离场。
    止损优先于止盈（同根收盘同时满足时先查止损）。tp_price=None 即纯 a6_3。
    """
    from lei_signal.backtest.engine import is_cn_symbol

    exit_variant = "a6_4_structure_stop_plus_tp"
    entry_position = spec.signal_position + 1
    if (
        limit_guard
        and is_cn_symbol(spec.symbol)
        and entry_position < len(frame)
        and entry_position >= 1
    ):
        prev_close = float(frame["close"].iloc[entry_position - 1])
        open_price = float(frame["open"].iloc[entry_position])
        if prev_close > 0 and open_price >= prev_close * 1.095:
            return Trade(
                symbol=spec.symbol, entry_variant=spec.entry_variant,
                exit_variant=exit_variant, is_first_touch=spec.is_first_touch,
                ma_period=spec.ma_period, clock_type=spec.clock_type,
                weekly_bull_env=spec.weekly_bull_env, trend_stage=spec.trend_stage,
                signal_date=spec.signal_date,
                entry_date=frame.index[entry_position].date(),
                entry_price=open_price, stop_price=spec.stop_price,
                target_price=spec.target_price, reward_risk=spec.reward_risk,
                exit_reason="skipped_limit_up_at_entry",
            )
    if entry_position >= len(frame):
        return Trade(
            symbol=spec.symbol, entry_variant=spec.entry_variant,
            exit_variant=exit_variant, is_first_touch=spec.is_first_touch,
            ma_period=spec.ma_period, clock_type=spec.clock_type,
            weekly_bull_env=spec.weekly_bull_env, trend_stage=spec.trend_stage,
            signal_date=spec.signal_date, entry_date=spec.signal_date,
            entry_price=spec.entry_ref_price, stop_price=spec.stop_price,
            target_price=spec.target_price, reward_risk=spec.reward_risk,
            exit_reason="signal_at_end_not_entered",
        )
    trade = Trade(
        symbol=spec.symbol, entry_variant=spec.entry_variant,
        exit_variant=exit_variant, is_first_touch=spec.is_first_touch,
        ma_period=spec.ma_period, clock_type=spec.clock_type,
        weekly_bull_env=spec.weekly_bull_env, trend_stage=spec.trend_stage,
        signal_date=spec.signal_date,
        entry_date=frame.index[entry_position].date(),
        entry_price=float(frame["open"].iloc[entry_position]),
        stop_price=spec.stop_price, target_price=spec.target_price,
        reward_risk=spec.reward_risk,
        meta={"entry_reason": spec.entry_reason},
    )
    risk = trade.entry_price - spec.stop_price
    if risk <= 0:
        trade.exit_reason = "invalid_nonpositive_risk"
        trade.exit_date = trade.entry_date
        trade.exit_price = trade.entry_price
        trade.r_gross = 0.0
        trade.r_net = 0.0
        return trade

    def close_at(position: int, reason: str) -> Trade:
        exit_position = position + 1
        while (
            limit_guard
            and is_cn_symbol(spec.symbol)
            and exit_position < len(frame)
            and exit_position >= 1
            and float(frame["close"].iloc[exit_position - 1]) > 0
            and float(frame["open"].iloc[exit_position])
            <= float(frame["close"].iloc[exit_position - 1]) * 0.905
        ):
            exit_position += 1
        if exit_position >= len(frame):
            trade.exit_reason = f"{reason}(数据末尾未执行)"
            trade.holding_bars = position - entry_position
            return trade
        trade.exit_date = frame.index[exit_position].date()
        trade.exit_price = float(frame["open"].iloc[exit_position])
        trade.exit_reason = reason
        trade.holding_bars = exit_position - entry_position
        gross = (trade.exit_price - trade.entry_price) / risk
        fees = fee.round_trip_fraction(trade.entry_price)
        trade.r_gross = gross
        trade.r_net = ((trade.exit_price / trade.entry_price - 1.0) - fees) * (
            trade.entry_price / risk
        )
        return trade

    for position in range(entry_position, len(frame)):
        close = float(frame["close"].iloc[position])
        if close < spec.stop_price:
            return close_at(position, "structure_stop_C")
        if tp_price is not None and close >= tp_price:
            return close_at(position, tp_reason)
    trade.holding_bars = len(frame) - 1 - entry_position
    trade.exit_reason = "open_at_end"
    return trade


def detector_for(module: str):
    if module == "A":
        from lei_signal.rules.first_ma_pullback import detect_first_ma_pullback_events
        return detect_first_ma_pullback_events
    if module == "B":
        from lei_signal.rules.dense_breakout import detect_dense_breakout_events
        return detect_dense_breakout_events
    if module == "C":
        from lei_signal.rules.two_b_reversal import detect_two_b_reversal_events
        return detect_two_b_reversal_events
    from lei_signal.rules.module_d_false_breakout import detect_module_d_events
    return detect_module_d_events


def exit_reason_counts(trades: list[Trade]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for t in trades:
        key = t.exit_reason or "(none)"
        if key.endswith("(数据末尾未执行)"):
            key = key[: -len("(数据末尾未执行)")] + "@数据末尾"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def variant_metrics(trades: list[Trade]) -> dict:
    return asdict(compute_metrics(trades, label="全部", net=True))


def main() -> None:
    print("加载回测深池（load_pool_frames）...", flush=True)
    frames = load_pool_frames()
    benchmarks = _benchmark_clock(frames)
    print(f"池内标的 {len(frames)} 个", flush=True)

    results: dict = {"modules": {}, "meta": {"pool_symbols": len(frames)}}
    repro_failures = []

    for mkey, mcfg in MODULES.items():
        print(f"\n===== 模块 {mkey}（{mcfg['entry_variant']}）=====", flush=True)
        with patched_ledger(mcfg["overrides"]):
            detector = detector_for(mcfg["module"])
            symbol_specs: list[tuple] = []  # (frame, prepared, spec)
            dropped_shrink = dropped_bias = 0
            for symbol, frame in sorted(frames.items()):
                prepared = prepare_frame(frame)
                events = detector(frame, symbol)
                pivots = confirmed_pivots(frame)
                specs, _f_rr, _no_t = entry_specs_from_events(
                    frame, events, symbol,
                    module=mcfg["module"],
                    entry_variant=mcfg["entry_variant"],
                    rr_min=None,
                    pivots=pivots,
                )
                if mcfg["volume_filter"] == "shrink":
                    specs, dropped = filter_specs_by_shrink(frame, specs)
                    dropped_shrink += dropped
                if mcfg["bias_filter"] is not None:
                    specs, dropped = filter_specs_by_bias(
                        frame, specs, bias_max=mcfg["bias_filter"]
                    )
                    dropped_bias += dropped
                for spec in specs:
                    symbol_specs.append((frame, prepared, spec))
        print(f"入场 spec 总数 {len(symbol_specs)}"
              f"（shrink 过滤 {dropped_shrink} / bias 过滤 {dropped_bias}）",
              flush=True)

        market_of = {}
        for symbol, frame in frames.items():
            market_of[symbol] = (
                "cn" if symbol.endswith((".SS", ".SZ")) or symbol.startswith("TH")
                else ("hk" if symbol.startswith("^HS") else "us")
            )

        def run_variant(name, sim_fn) -> dict:
            fees = {label: FeeModel.from_ledger(label) for label in FEE_LABELS}
            out = {}
            for label, fee in fees.items():
                trades = []
                for frame, prepared, spec in symbol_specs:
                    trade = sim_fn(frame, spec, fee=fee, prepared=prepared,
                                   limit_guard=True)
                    bench = benchmarks.get(market_of[spec.symbol])
                    if bench is not None:
                        trade.benchmark_clock_type = bench.get(spec.signal_date, 0)
                    trades.append(trade)
                out[label] = {
                    "metrics": variant_metrics(trades),
                    "exit_reasons": exit_reason_counts(trades),
                }
            print(f"  [{mkey}/{name}] "
                  + " | ".join(
                      f"{lbl}: {out[lbl]['metrics']['trade_count']}笔 "
                      f"expR {out[lbl]['metrics']['expectancy_r']:.3f} "
                      f"PF {out[lbl]['metrics']['profit_factor']:.3f}"
                      for lbl in FEE_LABELS), flush=True)
            return out

        variants: dict = {}

        def baseline_sim(exit_variant):
            def _sim(frame, spec, *, fee, prepared, limit_guard):
                return simulate_trade(
                    frame, spec, exit_variant=exit_variant, fee=fee,
                    prepared=prepared, limit_guard=limit_guard,
                )
            return _sim

        variants["a6_1_costbasis"] = run_variant("a6_1_costbasis",
                                                baseline_sim(EXIT_COSTBASIS))
        variants["a6_3_structure_stop"] = run_variant("a6_3_structure_stop",
                                                      baseline_sim(EXIT_STRUCTURE_STOP))

        # 复现门槛核对（standard 档）
        for vname in ("a6_1_costbasis", "a6_3_structure_stop"):
            m = variants[vname]["standard"]["metrics"]
            a_trades, a_expR, a_pf = ARCHIVED[(mkey, vname)]
            ok = (
                m["trade_count"] == a_trades
                and abs((m["expectancy_r"] or 0) - a_expR) < 1e-9
                and abs((m["profit_factor"] or 0) - a_pf) < 1e-9
            )
            print(f"  复现核对 {vname}: "
                  f"{m['trade_count']}/{m['expectancy_r']:.6f}/"
                  f"{m['profit_factor']:.6f} vs 归档 "
                  f"{a_trades}/{a_expR:.6f}/{a_pf:.6f} -> "
                  f"{'OK' if ok else 'FAIL'}", flush=True)
            if not ok:
                repro_failures.append(f"{mkey}/{vname}")

        def tp_sim(tp_price_fn, reason):
            def _sim(frame, spec, *, fee, prepared, limit_guard):
                tp = tp_price_fn(frame, spec, prepared)
                return simulate_trade_a64(
                    frame, spec, tp_price=tp, fee=fee, prepared=prepared,
                    limit_guard=limit_guard, tp_reason=reason,
                )
            return _sim

        for k in ATR_LEVELS:
            def atr_tp_fn(frame, spec, prepared, _k=k):
                if spec.signal_position + 1 >= len(frame):
                    return None
                atr = float(prepared["atr20"].iloc[spec.signal_position])
                if not atr > 0:
                    return None
                entry = float(frame["open"].iloc[spec.signal_position + 1])
                return entry + _k * atr

            name = f"a6_4a_atr{k:g}"
            variants[name] = run_variant(
                name, tp_sim(atr_tp_fn, f"tp_atr{k:g}"))

        for f in TARGET_FRACTIONS:
            def target_tp_fn(frame, spec, prepared, _f=f):
                if spec.target_price is None or spec.target_price <= spec.entry_ref_price:
                    return None  # B 缺失或非正向目标：该笔不启用止盈
                if spec.signal_position + 1 >= len(frame):
                    return None
                entry = float(frame["open"].iloc[spec.signal_position + 1])
                tp = entry + _f * (spec.target_price - entry)
                return tp if tp > entry else None

            name = f"a6_4b_target{f:.1f}"
            variants[name] = run_variant(
                name, tp_sim(target_tp_fn, f"tp_target{f:.1f}"))

        # 止盈启用率诊断（a6_4b 的 B 缺失占比）
        no_target = sum(
            1 for _fr, _p, spec in symbol_specs
            if spec.target_price is None or spec.target_price <= spec.entry_ref_price
        )
        results["modules"][mkey] = {
            "entry_specs": len(symbol_specs),
            "filtered_by_shrink": dropped_shrink,
            "filtered_by_bias": dropped_bias,
            "tp_inactive_no_positive_target": no_target,
            "variants": variants,
        }

    results["reproduction"] = (
        "OK" if not repro_failures else f"FAIL: {repro_failures}"
    )
    out_dir = REPO / "docs/experiments/raw/exit_revival_a64"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(results, ensure_ascii=False, indent=1, sort_keys=True)
    out_path = out_dir / "exit_revival_results.json"
    out_path.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    print(f"\n复现门槛: {results['reproduction']}")
    print(f"落盘: {out_path}")
    print(f"sha256(canonical json) = {digest}")
    if repro_failures:
        sys.exit(2)


if __name__ == "__main__":
    main()
