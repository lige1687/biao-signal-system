"""参数化回测服务：用户可调参数、后台执行、记录留存（web 回测工作台后端）。

与 runner.run_round1 的区别：runner 是第一轮的固定 18 组合批跑；本服务面向
界面，单组合、参数全开放（盈亏比门槛/入场版本/退出方式/费用档/标的范围），
结果以 JSON 落盘 ``~/.lei_signal_lab/backtest_runs/`` 供历史查阅。

术语表（GLOSSARY）是回测指标的「人话」唯一来源：界面悬浮提示直接取自这里，
与 explanations.py「文案集中在后端」的项目惯例一致。
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from lei_signal.backtest.engine import (
    ENTRY_CONFIRMED,
    ENTRY_EARLY,
    EXIT_COSTBASIS,
    EXIT_VARIANT_CN,
    MODULE_ENTRY_CONTRACT,
    FeeModel,
    Trade,
    entry_specs_from_events,
    prepare_frame,
    simulate_trade,
)
from lei_signal.backtest.entry_filters import (
    PROFILE_MODES,
    filter_specs_by_bias,
    filter_specs_by_gap_momentum,
    filter_specs_by_profile,
    filter_specs_by_shrink,
    filter_specs_by_volume,
)
from lei_signal.backtest.metrics import full_group_metrics
from lei_signal.backtest.runner import (
    RESEARCH_DISCLAIMER,
    _benchmark_clock,
    load_pool_frames,
)

BACKTEST_RUNS_DIR = Path.home() / ".lei_signal_lab" / "backtest_runs"

ENTRY_VARIANT_CN = {
    ENTRY_EARLY: "A4 早期版（站上 EMA20 且 EMA20 上行即入场）",
    ENTRY_CONFIRMED: "A4 确认版（再加 SMA20 上行确认）",
}
FEE_LABEL_CN = {
    "none": "不计费用（0bp）",
    "standard": "标准档（单边 5bp）",
    "conservative": "保守档（单边 10bp）",
}

#: 检测器参数覆盖白名单：键 -> (账本替换模板, 说明)。档位来源规格 §17 敏感性。
OVERRIDE_SPECS: dict[str, dict] = {
    "consolidation_bars": {
        "label": "横盘根数", "default": 126,
        "levels": [40, 63, 90, 126, 180],
        "tip": "B1 密集区的整理时间下限（规格 §17 已定（原则）≈126；矩阵实验显示本池 40-63 更优）",
        "replacements": [("minimum_consolidation_bars: 126", "minimum_consolidation_bars: {v}")],
    },
    "cluster_threshold": {
        "label": "均线带宽", "default": 0.02,
        "levels": [0.02, 0.03, 0.04, 0.05],
        "tip": "六线 max/min-1 的密集上限（规格已定（原则）2%；§4.6 要求敏感性）",
        "replacements": [("cluster_threshold: 0.02", "cluster_threshold: {v:.4f}")],
    },
    "touch_atr": {
        "label": "触碰距离(ATR倍数)", "default": 1.0,
        "levels": [0.5, 1.0, 1.5],
        "tip": "模块 A 的 A2 触碰带：Low <= SMA_N + N x ATR(20)（规格 §17 敏感性 0.5/1/1.5）",
        "replacements": [("ma_touch_distance_atr: 1.0", "ma_touch_distance_atr: {v}")],
    },
    "clock_mult": {
        "label": "时钟边界倍率", "default": 1.0,
        "levels": [0.5, 1.0, 2.0],
        "tip": "时钟分档边界（三类10%/一类100%）整体缩放（规格 §4.4 x0.5/x2 敏感性）",
        "replacements": [
            ("type3_max_abs_s60: 0.10", "type3_max_abs_s60: {v0.10}"),
            ("type2_min_s60: 0.10", "type2_min_s60: {v0.10}"),
            ("type1_min_s60: 1.00", "type1_min_s60: {v1.00}"),
        ],
    },
    "two_b_bars": {
        "label": "2B收复窗口", "default": 5,
        "levels": [3, 5, 8],
        "tip": "C 模块快速收复最大 K 线数（规格 §17 敏感性 3/5/8）",
        "replacements": [("two_b_reclaim_bars: 5", "two_b_reclaim_bars: {vi}")],
    },
}

_OVERRIDES_LOCK = threading.Lock()
_OVERRIDES_ACTIVE = False  # execute_run 串行段保护（防并发 run 互相污染账本）


def _overrides_yaml(overrides: tuple[tuple[str, float], ...]) -> str | None:
    """按白名单生成替换后的账本文本；无合法覆盖时返回 None。"""
    if not overrides:
        return None
    from lei_signal.domain.rules_config import _default_config_path

    text = _default_config_path().read_text(encoding="utf-8")
    for key, value in overrides:
        spec = OVERRIDE_SPECS.get(key)
        if spec is None:
            raise ValueError(f"未知参数覆盖: {key}")
        for old_tpl, new_tpl in spec["replacements"]:
            old = old_tpl.format(**{}) if False else old_tpl
            new = (
                new_tpl.replace("{v0.10}", f"{0.10 * value:.4f}")
                .replace("{v1.00}", f"{1.00 * value:.4f}")
                .replace("{v:.4f}", f"{value:.4f}")
                .replace("{vi}", f"{int(value)}")
                .replace("{v}", f"{value}")
            )
            if old not in text:
                raise ValueError(f"参数锚点未找到: {old}")
            text = text.replace(old, new)
    return text


#: 交易模块中文名（工作台下拉；变体说明由 /options 动态给出）。
MODULE_CN: dict[str, str] = {
    "A": "A·稳定上涨趋势回调（主战场）",
    "B": "B·均线密集区突破（埋伏/突破）",
    "C": "C·2B 破底翻反转",
    "D": "D·假跌破反转",
}

#: 模块变体中文名。
MODULE_VARIANT_CN: dict[str, dict[str | None, str]] = {
    "A": {
        "early": "早期版（站上 EMA20 且 EMA20 上行）",
        "confirmed": "确认版（再加 SMA20 上行）",
    },
    "B": {
        "ambush": "埋伏版（多头排列刚形成时入场等突破）",
        "breakout": "突破版（收盘破密集区上沿）",
    },
    "C": {
        "v1": "v1（收回 L1 当日入场）",
        "v2": "v2（收回后 EMA20 拐头）",
        "v3": "v3（收回后双均线共同向上）",
    },
    "D": {None: "唯一版（两动作齐备）"},
}

#: 盈亏比门槛可选档（None = 不设门槛，但仍要求目标可计算）。
RR_LEVELS: tuple[float | None, ...] = (None, 2.0, 2.5, 3.0, 4.0, 5.0)

#: 指标术语表：界面悬浮提示的「人话」解释，唯一来源。
GLOSSARY: dict[str, dict[str, str]] = {
    "rr_min": {
        "label": "盈亏比门槛",
        "tip": "开仓前用「(目标价−入场价) ÷ (入场价−止损价)」算出的纸面赔率，"
        "低于门槛的信号不进场。3 是手册原则值（赚 3 块的潜力才冒 1 块的风险）；"
        "不设门槛 = 只要能算出目标价就允许进场（对照组）。",
    },
    "trade_count": {
        "label": "笔数",
        "tip": "期间内完成买入并已卖出的交易笔数。",
    },
    "open_count": {
        "label": "未平仓",
        "tip": "回测结束时仍未触发退出、还拿着的笔数。这些不参与胜率与收益统计。",
    },
    "win_rate": {
        "label": "胜率",
        "tip": "赚钱的交易占已平仓的比例。趋势系统的胜率通常只有三到四成——"
        "靠少数大盈利覆盖多次小亏损，低胜率是设计特征不是缺陷。",
    },
    "expectancy_r": {
        "label": "期望 R",
        "tip": "平均每笔赚多少个 R。R = 这笔交易开仓时准备承受的最大亏损"
        "（入场价 − 止损价）。+1.5R 的意思是：每冒 1 块钱风险，平均赚 1.5 块。",
    },
    "avg_win_r": {"label": "均盈 R", "tip": "赚钱的交易平均每笔赚多少 R。"},
    "avg_loss_r": {
        "label": "均亏 R",
        "tip": "亏钱的交易平均每笔亏多少 R。亏损超过 1R 说明跳空穿越了止损位。",
    },
    "profit_factor": {
        "label": "盈利因子",
        "tip": "全部盈利之和 ÷ 全部亏损之和。>1 是赚钱，>1.5 不错，>2 优秀。",
    },
    "max_consecutive_losses": {
        "label": "最大连亏",
        "tip": "最多连续亏损几笔——最考验心态的数字，决定你能不能拿住系统。",
    },
    "max_drawdown_1r": {
        "label": "1R 最大回撤",
        "tip": "以 R 为单位的权益最大回撤：从盈利峰值最多回吐了多少个 R。"
        "若每笔固定用账户 1% 冒险，数值 ×1% 约等于权益回撤幅度的下限估计。",
    },
    "avg_holding_bars": {
        "label": "平均持仓",
        "tip": "平均每笔交易拿多少根日 K 线。",
    },
    "total_r": {"label": "累计 R", "tip": "所有已平仓交易的 R 加总。"},
    "in_sample": {
        "label": "样本内期望",
        "tip": "较早年份（切分日之前）的表现——参数主要「看着」这段调出来的。",
    },
    "out_of_sample": {
        "label": "样本外期望",
        "tip": "最近 2 年的表现，模拟系统上线后遇到的新行情。样本外仍赚钱，"
        "才说明结果不是照着历史拟合出来的。",
    },
    "is_first_touch": {
        "label": "首次/非首次",
        "tip": "趋势刚形成后的第一次回撤（手册 4.4「第一次要特别重视”）标记为"
        "首次；同一趋势里的后续回撤为非首次。两者表现须分开看。",
    },
    "entry_variant": {
        "label": "入场版本",
        "tip": "A4 早期版 = 收盘站回 EMA20 且 EMA20 上行就进场（更早、更敏感）；"
        "确认版 = 再等 SMA20 也上行（更晚、更稳）。",
    },
    "exit_variant": {
        "label": "退出方式",
        "tip": "A6① 收盘同时跌破 EMA20 与 20 日抵扣价即退出；A6② 出现顶部构造后"
        "再出现关键性波动才退出（拿得更久）；A6③ 只用初始止损、不跟随趋势退出。"
        "「什么逻辑进场就什么逻辑出场」——A6③ 在回测里被证明会深度亏损。",
    },
    "reward_risk": {
        "label": "盈亏比（这笔）",
        "tip": "这笔交易开仓时的纸面赔率：(目标价−入场价) ÷ (入场价−止损价)。",
    },
    "r_multiple": {
        "label": "R 倍数",
        "tip": "这笔交易实际赚/亏了几个 R。R = 开仓时设定的最大可承受亏损。",
    },
    "volume_confirm": {
        "label": "量能确认",
        "tip": "手册 2.5「小草与大树」：近 N 日（默认 5，可选 1=仅信号日）任一日"
        "成交量 >= 2 倍 20 日均量才入场。只做「有/无异常大量」的确认过滤，"
        "不做连续量能序列分析；默认关。",
    },
    "profile_filter": {
        "label": "筹码过滤",
        "tip": "筹码分布代理的两个可选条件：踩峰买 = 入场参考价下方 1×ATR 内"
        "存在成交量峰 POC；上方无套牢 = 入场价以上代理量占比 <= 30%。"
        "筹码只改善入场位置和盈亏比，不取代趋势判断（手册 4.5）；默认关。",
    },
    "gap_target": {
        "label": "缺口目标位",
        "tip": "盈亏比目标 B 优先级第 2 档（规格 §10）：摆动高点之后、筹码峰之前，"
        "用信号日上方最近的未回补向上缺口上沿作目标。默认关。",
    },
    "gap_momentum": {
        "label": "缺口动能",
        "tip": "标志性动作确认：信号日近 10 日内存在未回补向上缺口才入场"
        "（手册 2.5 缺口属标志性动作）。默认关，实验档。",
    },
    "volume_filter": {
        "label": "缩量回调",
        "tip": "手册 2.5「交投清淡的行情可以走很久」：近 3 日均量低于前 3 日均量"
        "（缩量回调 = 卖压衰竭）才入场；可选叠加「量比 < 0.7」严格档。"
        "窗口默认读账本 volume_proxies；默认关。",
    },
    "bias_filter": {
        "label": "深乖离增强",
        "tip": "规格 §4.7/§9 C1：信号日收盘低于 EMA120 超过给定幅度"
        "（如 -15% = 深度超跌）才入场。乖离只作增强条件、不单独触发；"
        "个股池专用实验档，默认关。",
    },
}


@dataclass(frozen=True, slots=True)
class BacktestParams:
    symbols: tuple[str, ...] | None = None   # None = 回测深池全部
    module: str = "A"
    rr_min: float | None = 3.0
    entry_variant: str | None = None         # None = 该模块默认变体
    exit_variant: str = EXIT_COSTBASIS
    fee_label: str = "standard"
    limit_guard: bool = True   # A 股涨跌停约束（涨停买不进/跌停顺延卖）
    overrides: tuple[tuple[str, float], ...] = ()  # 检测器参数覆盖（实验档）
    # 入场确认过滤器（第四轮落地，全部默认关，不改变既有结论的可复现性）：
    volume_confirm: bool = False             # 量能确认（账本 volume_proxies 口径）
    volume_confirm_window: int = 5           # 近 N 日任一日异常大量即算（1=仅信号日）
    profile_filter: str = "none"             # 筹码峰确认（none/poc_support/vacuum/both）
    gap_target: bool = False                 # 目标 B 启用未回补缺口档（规格 §10 第 2 档）
    gap_momentum: bool = False               # 缺口动能确认（近 N 日未回补向上缺口才做）
    gap_momentum_lookback: int = 10
    # 缩量回调确认（第四轮补充验证，默认关）：
    volume_filter: str = "none"              # none / shrink（近N日均量<前M日均量）
    shrink_recent: int | None = None         # None = 读账本 shrink_recent_window（3）
    shrink_prior: int | None = None          # None = 读账本 shrink_prior_window（3）
    volume_filter_vr_max: float | None = None  # 叠加：信号日 volume_ratio20 < 此值（严格档）
    # 深乖离增强（BCD 重测轮，规格 §4.7/§9 C1；默认关）：
    bias_filter: float | None = None         # None=关；-0.15 = 信号日低于 EMA120 15% 以上才入

    def validate(self) -> None:
        if self.module not in MODULE_ENTRY_CONTRACT:
            raise ValueError(f"未知交易模块: {self.module}")
        valid_variants = MODULE_ENTRY_CONTRACT[self.module]["variants"]
        if self.entry_variant is not None and self.entry_variant not in valid_variants:
            raise ValueError(f"模块 {self.module} 不支持入场变体: {self.entry_variant}")

        if self.exit_variant not in EXIT_VARIANT_CN:
            raise ValueError(f"未知退出方式: {self.exit_variant}")
        if self.fee_label not in FEE_LABEL_CN:
            raise ValueError(f"未知费用档: {self.fee_label}")
        if self.rr_min is not None and not (0 < self.rr_min <= 100):
            raise ValueError(f"盈亏比门槛不合理: {self.rr_min}")
        if self.volume_confirm_window < 1:
            raise ValueError(f"volume_confirm_window 必须 >= 1: {self.volume_confirm_window}")
        if self.profile_filter not in PROFILE_MODES:
            raise ValueError(
                f"未知筹码过滤档: {self.profile_filter}（可选 {PROFILE_MODES}）"
            )
        if self.gap_momentum_lookback < 1:
            raise ValueError(
                f"gap_momentum_lookback 必须 >= 1: {self.gap_momentum_lookback}"
            )
        if self.volume_filter not in ("none", "shrink"):
            raise ValueError(f"未知量能过滤档: {self.volume_filter}（可选 none/shrink）")
        for name, value in (("shrink_recent", self.shrink_recent),
                            ("shrink_prior", self.shrink_prior)):
            if value is not None and value < 1:
                raise ValueError(f"{name} 必须 >= 1: {value}")
        if self.volume_filter_vr_max is not None and self.volume_filter_vr_max <= 0:
            raise ValueError(
                f"volume_filter_vr_max 必须为正: {self.volume_filter_vr_max}"
            )
        if self.bias_filter is not None and self.bias_filter >= 0:
            raise ValueError(
                f"bias_filter 必须为负（深乖离档，如 -0.15）: {self.bias_filter}"
            )


def _metrics_dict(metrics: Any) -> dict:  # noqa: ANN401 - Metrics dataclass
    return asdict(metrics)


def _trade_dict(trade: Trade) -> dict:
    return {
        "symbol": trade.symbol,
        "entry_variant": trade.entry_variant,
        "exit_variant": trade.exit_variant,
        "is_first_touch": trade.is_first_touch,
        "ma_period": trade.ma_period,
        "signal_date": trade.signal_date.isoformat(),
        "entry_date": trade.entry_date.isoformat(),
        "entry_price": trade.entry_price,
        "stop_price": trade.stop_price,
        "target_price": trade.target_price,
        "reward_risk": trade.reward_risk,
        "exit_date": trade.exit_date.isoformat() if trade.exit_date else None,
        "exit_price": trade.exit_price,
        "exit_reason": trade.exit_reason,
        "holding_bars": trade.holding_bars,
        "r_gross": trade.r_gross,
        "r_net": trade.r_net,
        "benchmark_clock_type": trade.benchmark_clock_type,
        "trend_stage": trade.trend_stage,
        "entry_reason": trade.meta.get("entry_reason", ""),
    }


def execute_run(params: BacktestParams) -> dict[str, Any]:
    """同步执行一次参数化回测。调用方负责放后台线程。

    overrides 非空时：全局锁内把账本替换为覆盖版本运行（检测器从账本读参，
    无需改代码），事件缓存按覆盖指纹隔离，跑完恢复原账本。参数实验（规格
    §16/§17 敏感性）与正式参数（拍板入账本）由此分离。
    """
    params.validate()
    import contextlib

    @contextlib.contextmanager
    def _patched_ledger():
        global _OVERRIDES_ACTIVE
        text = _overrides_yaml(params.overrides)
        if text is None:
            yield
            return
        import tempfile

        from lei_signal.domain import rules_config as rc

        with _OVERRIDES_LOCK:
            if _OVERRIDES_ACTIVE:
                raise RuntimeError("另一个参数覆盖回测正在运行，请稍后重试")
            _OVERRIDES_ACTIVE = True
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
                _OVERRIDES_ACTIVE = False

    with _patched_ledger():
        return _execute_run_unlocked(params)


def _execute_run_unlocked(params: BacktestParams) -> dict[str, Any]:
    frames = _cached_frames()
    if params.symbols is not None:
        missing = [s for s in params.symbols if s not in frames]
        selected = {s: f for s, f in frames.items() if s in params.symbols}
        if not selected:
            raise ValueError(f"所选标的均不在回测池中（缺: {missing[:5]}）")
        frames = selected

    last_date = max(f.index[-1] for f in frames.values()).date()
    first_date = min(f.index[0] for f in frames.values()).date()
    oos_start = last_date - timedelta(days=365 * 2)
    benchmarks = _benchmark_clock(frames)
    fee = FeeModel.from_ledger(params.fee_label)

    trades: list[Trade] = []
    per_symbol: list[dict] = []
    touched_total = confirmed_total = filtered_rr_total = no_target_total = 0
    volume_filtered_total = profile_filtered_total = gap_filtered_total = shrink_filtered_total = 0
    bias_filtered_total = 0
    use_gaps = params.gap_target or params.gap_momentum
    for symbol, frame in sorted(frames.items()):
        prepared = prepare_frame(frame)
        fingerprint = ";".join(f"{k}={v}" for k, v in sorted(params.overrides))
        events = _cached_events(symbol, frame, params.module, fingerprint)
        touched_total += sum(
            1 for e in events
            if str(e.evidence.get("sub_rule", "")).endswith(("_touched", "_watch"))
        )
        confirmed_total += sum(
            1 for e in events
            if "confirmed" in str(e.evidence.get("sub_rule", ""))
            and "strict" not in str(e.evidence.get("sub_rule", ""))
        )
        gaps = _cached_gaps(symbol, frame) if use_gaps else None
        specs, filtered_rr, no_target = entry_specs_from_events(
            frame, events, symbol,
            module=params.module,
            entry_variant=params.entry_variant,
            rr_min=params.rr_min,
            pivots=_cached_pivots(symbol, frame),
            gaps=gaps if params.gap_target else None,
        )
        filtered_rr_total += filtered_rr
        no_target_total += no_target
        if params.volume_confirm:
            specs, dropped = filter_specs_by_volume(
                frame, specs, window=params.volume_confirm_window
            )
            volume_filtered_total += dropped
        if params.volume_filter == "shrink":
            specs, dropped = filter_specs_by_shrink(
                frame,
                specs,
                recent_window=params.shrink_recent,
                prior_window=params.shrink_prior,
                vr_max=params.volume_filter_vr_max,
            )
            shrink_filtered_total += dropped
        if params.profile_filter != "none":
            specs, dropped = filter_specs_by_profile(
                frame,
                specs,
                mode=params.profile_filter,
                prepared=prepared,
                cache=_PROFILE_CACHE,
            )
            profile_filtered_total += dropped
        if params.gap_momentum:
            specs, dropped = filter_specs_by_gap_momentum(
                specs,
                gaps=gaps or [],
                bar_dates=[ts.date() for ts in frame.index],
                lookback_bars=params.gap_momentum_lookback,
            )
            gap_filtered_total += dropped
        if params.bias_filter is not None:
            specs, dropped = filter_specs_by_bias(
                frame, specs, bias_max=params.bias_filter
            )
            bias_filtered_total += dropped
        market = (
            "cn"
            if symbol.endswith((".SS", ".SZ")) or symbol.startswith("TH")
            else ("hk" if symbol.startswith("^HS") else "us")
        )
        bench = benchmarks.get(market)
        for spec in specs:
            trade = simulate_trade(
                frame, spec,
                exit_variant=params.exit_variant, fee=fee, prepared=prepared,
                limit_guard=params.limit_guard,
            )
            if bench is not None:
                trade.benchmark_clock_type = bench.get(spec.signal_date, 0)
            trades.append(trade)
        per_symbol.append({"symbol": symbol, "bars": len(frame), "trades": len(specs)})

    groups_net = full_group_metrics(trades, net=True, sample_split=oos_start)
    return {
        "run_id": new_run_id(),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": "done",
        "disclaimer": RESEARCH_DISCLAIMER,
        "params": {
            "symbols": list(params.symbols) if params.symbols else "all",
            "module": params.module,
            "rr_min": params.rr_min,
            "entry_variant": params.entry_variant,
            "exit_variant": params.exit_variant,
            "fee_label": params.fee_label,
            "limit_guard": params.limit_guard,
            "overrides": dict(params.overrides) if params.overrides else {},
            "volume_confirm": params.volume_confirm,
            "volume_confirm_window": params.volume_confirm_window,
            "profile_filter": params.profile_filter,
            "gap_target": params.gap_target,
            "gap_momentum": params.gap_momentum,
            "gap_momentum_lookback": params.gap_momentum_lookback,
            "volume_filter": params.volume_filter,
            "shrink_recent": params.shrink_recent,
            "shrink_prior": params.shrink_prior,
            "volume_filter_vr_max": params.volume_filter_vr_max,
            "bias_filter": params.bias_filter,
        },
        "data_range": {
            "start": first_date.isoformat(),
            "end": last_date.isoformat(),
            "symbols_count": len(frames),
            "out_of_sample_start": oos_start.isoformat(),
        },
        "funnel": {
            "touched": touched_total,
            "confirmed": confirmed_total,
            "filtered_by_rr": filtered_rr_total,
            "no_target": no_target_total,
            "filtered_by_volume": volume_filtered_total,
            "filtered_by_shrink": shrink_filtered_total,
            "filtered_by_profile": profile_filtered_total,
            "filtered_by_gap": gap_filtered_total,
            "filtered_by_bias": bias_filtered_total,
        },
        "groups": {
            str(net): {
                section: [_metrics_dict(m) for m in metric_list]
                for section, metric_list in section_map.items()
            }
            for net, section_map in ((False, full_group_metrics(
                trades, net=False, sample_split=oos_start
            )), (True, groups_net))
        },
        "per_symbol": per_symbol,
        "trades": [_trade_dict(t) for t in trades],
    }


def klines(symbol: str, limit: int = 3000) -> dict[str, Any]:
    """回测池某标的的日 K（OHLC 数组），供前端叠加回测买卖点标记。"""
    frames = _cached_frames()
    frame = frames.get(symbol)
    if frame is None:
        raise ValueError(f"标的不在回测池中: {symbol}")
    tail = frame.tail(limit)
    return {
        "symbol": symbol,
        "count": len(tail),
        "dates": [ts.date().isoformat() for ts in tail.index],
        "ohlc": [
            [
                float(row["open"]),
                float(row["close"]),
                float(row["low"]),
                float(row["high"]),
            ]
            for _ts, row in tail.iterrows()
        ],
    }


# ---------------------------------------------------------------- 缓存与后台执行

_FRAME_CACHE: dict[str, pd.DataFrame] | None = None
_EVENT_CACHE: dict[str, list] = {}
_PIVOT_CACHE: dict[str, tuple] = {}
_GAP_CACHE: dict[str, list] = {}
_PROFILE_CACHE: dict[tuple[str, int, int], object] = {}
_STATE_LOCK = threading.Lock()
_RUN_STATE: dict[str, dict[str, str]] = {}


def _cached_frames() -> dict[str, pd.DataFrame]:
    global _FRAME_CACHE
    if _FRAME_CACHE is None:
        _FRAME_CACHE = load_pool_frames()
    return _FRAME_CACHE


def _cached_events(
    symbol: str, frame: pd.DataFrame, module: str, fingerprint: str = ""
) -> list:
    key = f"{module}:{fingerprint}:{symbol}"
    if key not in _EVENT_CACHE:
        if module == "A":
            from lei_signal.rules.first_ma_pullback import (
                detect_first_ma_pullback_events,
            )

            detector = detect_first_ma_pullback_events
        elif module == "B":
            from lei_signal.rules.dense_breakout import detect_dense_breakout_events

            detector = detect_dense_breakout_events
        elif module == "C":
            from lei_signal.rules.two_b_reversal import detect_two_b_reversal_events

            detector = detect_two_b_reversal_events
        else:
            from lei_signal.rules.module_d_false_breakout import detect_module_d_events

            detector = detect_module_d_events
        _EVENT_CACHE[key] = detector(frame, symbol)
    return _EVENT_CACHE[key]


def _cached_pivots(symbol: str, frame: pd.DataFrame) -> tuple:
    if symbol not in _PIVOT_CACHE:
        from lei_signal.features.pivots import confirmed_pivots

        _PIVOT_CACHE[symbol] = confirmed_pivots(frame)
    return _PIVOT_CACHE[symbol]


def _cached_gaps(symbol: str, frame: pd.DataFrame) -> list:
    """缺口事件按标的缓存（缺口口径不受 overrides 白名单影响，直接复用）。"""
    if symbol not in _GAP_CACHE:
        from lei_signal.rules.gap_events import detect_gaps

        _GAP_CACHE[symbol] = detect_gaps(frame)
    return _GAP_CACHE[symbol]


def new_run_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]


def _run_path(run_id: str) -> Path:
    return BACKTEST_RUNS_DIR / f"{run_id}.json"


def start_run(params: BacktestParams) -> str:
    """后台线程执行；立即返回 run_id。结果落盘后可被 list/load 读取。"""
    params.validate()
    run_id = new_run_id()

    def worker() -> None:
        with _STATE_LOCK:
            _RUN_STATE[run_id] = {"status": "running"}
        try:
            import json

            result = execute_run(params)
            result["run_id"] = run_id
            BACKTEST_RUNS_DIR.mkdir(parents=True, exist_ok=True)
            _run_path(run_id).write_text(
                json.dumps(result, ensure_ascii=False), encoding="utf-8"
            )
            with _STATE_LOCK:
                _RUN_STATE[run_id] = {"status": "done"}
        except Exception as exc:  # noqa: BLE001 - 后台线程不能向上抛
            with _STATE_LOCK:
                _RUN_STATE[run_id] = {"status": "failed", "error": str(exc)}

    threading.Thread(target=worker, daemon=True).start()
    return run_id


def run_status(run_id: str) -> dict | None:
    with _STATE_LOCK:
        if run_id in _RUN_STATE:
            return {"run_id": run_id, **_RUN_STATE[run_id]}
    if _run_path(run_id).exists():
        return {"run_id": run_id, "status": "done"}
    return None


def list_runs(limit: int = 50) -> list[dict]:
    """历史记录摘要（新→旧）。包含仍在跑的内存态。"""
    import json

    runs: dict[str, dict] = {}
    if BACKTEST_RUNS_DIR.exists():
        for path in sorted(BACKTEST_RUNS_DIR.glob("*.json"), reverse=True)[:limit]:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            overview = data.get("groups", {}).get("True", {}).get("总览", [{}])[0]
            runs[data.get("run_id", path.stem)] = {
                "run_id": data.get("run_id", path.stem),
                "created_at": data.get("created_at", ""),
                "status": "done",
                "params": data.get("params", {}),
                "symbols_count": data.get("data_range", {}).get("symbols_count"),
                "trade_count": overview.get("trade_count"),
                "expectancy_r": overview.get("expectancy_r"),
                "profit_factor": overview.get("profit_factor"),
            }
    with _STATE_LOCK:
        for run_id, state in _RUN_STATE.items():
            if state["status"] != "done":
                runs.setdefault(run_id, {"run_id": run_id, "status": state["status"]})
    ordered = sorted(runs.values(), key=lambda r: r.get("created_at", ""), reverse=True)
    return ordered[:limit]


def load_run(run_id: str) -> dict | None:
    import json

    path = _run_path(run_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


__all__ = [
    "BACKTEST_RUNS_DIR",
    "BacktestParams",
    "ENTRY_VARIANT_CN",
    "FEE_LABEL_CN",
    "GLOSSARY",
    "RR_LEVELS",
    "execute_run",
    "klines",
    "list_runs",
    "load_run",
    "new_run_id",
    "run_status",
    "start_run",
]
