"""宽度择时回测服务：选项构建、单次执行、运行记录落盘与列表。

窗口语义：start/end 裁剪回测区间，但策略状态用**全历史**热启动
（反转状态机/MA200 闸门/preq 分位预热都用窗口前的数据，无未来函数）。
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd

from lei_signal.timing_backtest.data import (
    BREADTH_FILES,
    INSTRUMENTS,
    TIMING_CACHE_DIR,
    _read_parquet_cached,
    align_index_breadth,
    data_unavailable_detail,
    load_breadth,
    load_index_bars,
)
from lei_signal.timing_backtest.engine import simulate
from lei_signal.timing_backtest.metrics import summarize_run, yearly_returns
from lei_signal.timing_backtest.presets import PRESETS
from lei_signal.timing_backtest.strategies import (
    LadderParams,
    ReversalParams,
    TrendGate,
    _fixed_edges,
    build_target,
)

RUNS_DIR = Path(
    os.environ.get("LEI_TIMING_RUNS_DIR", str(Path.home() / ".lei_signal_lab/timing_backtest_runs"))
)

DEFAULTS: dict = {
    "symbol": "000300",
    "strategy": "ladder",
    "indicator": "b200",
    "n_bands": 5,
    "edge_mode": "fixed",
    "direction": "contrarian",
    "low_extreme": 20.0,
    "high_extreme": 80.0,
    "confirm": 5.0,
    "batch_mode": "time",
    "batches": 5,
    "gate_mode": "off",
    "gate_cap": 0.0,
    "min_weight": 0.0,
    "gamma": 1.0,
    "low_edge": 0.0,
    "high_edge": 100.0,
    "batch_ratio": 1.0,
    "band_step": 10.0,
    "sell_batches": None,
    "sell_ratio": None,
    "trigger_mode": "rebound",
    "breadth": None,
    "min_trade": 0.0,
    "vol_target": 0.0,
    "cash_rate": 0.0,
    "fee_bps": None,
    "start": None,
    "end": None,
}

DISCLAIMERS = [
    "宽度由当前存续个股回算，早年存在幸存者偏差",
    "全A宽度底表为新浪不复权价，除权对 MA 上方判断有微小影响",
    "宽度数据截至最近一次回填日，重跑 scripts/backfill_timing_data.py 可刷新",
    "A股指数为价格指数不含股息，绝对收益被低估（策略与基准同口径）",
    "历史最优不等于未来最优，参数扫描结果存在过拟合风险，仅供研究",
]

_BREADTH_LABELS = {
    "cn_all": "全A B20/B50/B200",
    "sp500": "SP500 B20/B50/B200",
    "cn_cyb": "创业板专属 B20/B50/B200",
    "cn_csi300": "沪深300成分 B20/B50/B200",
}


class TimingDataUnavailable(RuntimeError):
    """本地行情/宽度数据缺失（API 层转 409）。"""


def _fmt_day(ts: pd.Timestamp | None) -> str | None:
    return None if ts is None else ts.strftime("%Y-%m-%d")


def build_options(cache_dir: Path | None = None) -> dict:
    cache = cache_dir or TIMING_CACHE_DIR
    instruments = []
    for spec in INSTRUMENTS.values():
        bars_path = cache / spec.data_file
        breadth_path = cache / {
            "cn_all": "breadth_cn_all.parquet", "sp500": "breadth_sp500.parquet"
        }[spec.breadth]
        data_start = data_end = None
        breadth_start = None
        if bars_path.exists():
            idx = pd.read_parquet(bars_path).index
            data_start, data_end = _fmt_day(idx.min()), _fmt_day(idx.max())
        if breadth_path.exists():
            bidx = pd.read_parquet(breadth_path).index
            breadth_start = _fmt_day(bidx.min())
        instruments.append(
            {
                "symbol": spec.symbol,
                "name": spec.name,
                "market": spec.market,
                "breadth": spec.breadth,
                "breadth_label": _BREADTH_LABELS[spec.breadth],
                "fee_default_bps": spec.fee_default_bps,
                "note": spec.note,
                "data_start": data_start,
                "data_end": data_end,
                "breadth_start": breadth_start,
            }
        )
    return {
        "instruments": instruments,
        "indicators": [
            {"key": "b20", "label": "B20 · 站上20日线占比"},
            {"key": "b50", "label": "B50 · 站上50日线占比"},
            {"key": "b200", "label": "B200 · 站上200日线占比"},
            {"key": "ad", "label": "AD · 当日上涨家数占比"},
            {"key": "ad20", "label": "AD20 · 上涨占比20日均值"},
        ],
        "strategies": {
            "ladder": {
                "defaults": {
                    "indicator": "b200", "n_bands": 5, "edge_mode": "fixed",
                    "direction": "contrarian",
                },
                "n_bands_choices": [3, 5, 9],
                "edge_mode_choices": ["fixed", "preq"],
                "direction_choices": ["contrarian", "momentum"],
            },
            "reversal": {
                "defaults": {
                    "indicator": "b200", "low_extreme": 20.0, "high_extreme": 80.0,
                    "confirm": 5.0, "batch_mode": "time", "batches": 5,
                },
                "batch_mode_choices": ["time", "band"],
            },
        },
        "gate": {
            "mode_choices": ["off", "ma200"],
            "defaults": {"gate_mode": "off", "gate_cap": 0.0},
        },
        "presets": PRESETS,
        "disclaimers": DISCLAIMERS,
    }


def compute_run(cfg: dict, cache_dir: Path | None = None) -> dict:
    """执行一次回测并返回结果 dict（不落盘；execute_run/sweep 共用）。"""
    merged = {**DEFAULTS, **{k: v for k, v in cfg.items() if v is not None}}
    symbol = merged["symbol"]
    spec = INSTRUMENTS.get(symbol)
    if spec is None:
        raise ValueError(f"未知标的 {symbol}（可用：{', '.join(INSTRUMENTS)}）")
    cache = cache_dir or TIMING_CACHE_DIR
    try:
        bars = load_index_bars(symbol, cache_dir=cache)
    except FileNotFoundError as e:
        raise TimingDataUnavailable(data_unavailable_detail(symbol)) from e
    breadth_key = merged.get("breadth") or spec.breadth
    if breadth_key not in BREADTH_FILES:
        raise ValueError(f"未知宽度来源 {breadth_key}（可用：{', '.join(BREADTH_FILES)}）")
    try:
        breadth = load_breadth(breadth_key, cache_dir=cache)
    except FileNotFoundError as e:
        raise TimingDataUnavailable(
            f"DATA_UNAVAILABLE: {breadth_key} 宽度数据缺失，"
            f"请先运行 scripts/backfill_timing_data.py（{e}）"
        ) from e

    aligned = align_index_breadth(bars, breadth)
    start_ts = pd.Timestamp(merged["start"]) if merged["start"] else aligned.index[0]
    end_ts = pd.Timestamp(merged["end"]) if merged["end"] else aligned.index[-1]
    window = aligned.loc[start_ts:end_ts]
    if len(window) < 60:
        raise TimingDataUnavailable(
            f"DATA_UNAVAILABLE: 回测窗口过短（{len(window)} 个交易日 < 60），请放宽 start/end"
        )

    ladder = LadderParams(
        indicator=merged["indicator"], n_bands=int(merged["n_bands"]),
        edge_mode=merged["edge_mode"], direction=merged["direction"],
        min_weight=float(merged["min_weight"]), gamma=float(merged["gamma"]),
        low_edge=float(merged["low_edge"]), high_edge=float(merged["high_edge"]),
    ) if merged["strategy"] == "ladder" else None
    reversal = ReversalParams(
        indicator=merged["indicator"], low_extreme=float(merged["low_extreme"]),
        high_extreme=float(merged["high_extreme"]), confirm=float(merged["confirm"]),
        batch_mode=merged["batch_mode"], batches=int(merged["batches"]),
        batch_ratio=float(merged["batch_ratio"]),
        band_step=float(merged["band_step"]),
        sell_batches=(
            int(merged["sell_batches"]) if merged["sell_batches"] is not None else None
        ),
        sell_ratio=(
            float(merged["sell_ratio"]) if merged["sell_ratio"] is not None else None
        ),
        trigger_mode=merged["trigger_mode"],
    ) if merged["strategy"] == "reversal" else None
    gate = TrendGate(mode=merged["gate_mode"], cap=float(merged["gate_cap"]))
    warmup = aligned.loc[:start_ts].iloc[:-1]
    target_full = build_target(
        aligned, ladder, reversal, gate, warmup,
        vol_target=float(merged["vol_target"]),
    )
    target = target_full.loc[window.index]

    fee = float(merged["fee_bps"]) if merged["fee_bps"] is not None else spec.fee_default_bps
    result = simulate(
        window, target, fee_bps=fee, cash_rate=float(merged["cash_rate"]),
        min_trade=float(merged["min_trade"]),
    )
    metrics = summarize_run(result.daily, result.trades)

    yearly = []
    strat_y = yearly_returns(result.daily["equity"])
    bench_y = yearly_returns(result.daily["benchmark"])
    for year in sorted(set(strat_y.index) | set(bench_y.index)):
        yearly.append(
            {
                "year": int(year),
                "strategy": float(strat_y.get(year, float("nan"))),
                "benchmark": float(bench_y.get(year, float("nan"))),
            }
        )

    indicator = merged["indicator"]
    return {
        "run_id": f"{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "symbol": symbol,
        "name": spec.name,
        "params": merged,
        "metrics": metrics,
        "yearly": yearly,
        "trades": result.trades,
        "daily": {
            "date": [d.strftime("%Y-%m-%d") for d in result.daily.index],
            "equity": [round(float(v), 6) for v in result.daily["equity"]],
            "benchmark": [round(float(v), 6) for v in result.daily["benchmark"]],
            "weight": [round(float(v), 4) for v in result.daily["weight"]],
            "open": [round(float(v), 4) for v in result.daily["open"]],
            "high": [round(float(v), 4) for v in result.daily["high"]],
            "low": [round(float(v), 4) for v in result.daily["low"]],
            "close": [round(float(v), 4) for v in result.daily["close"]],
            "breadth": [
                None if pd.isna(v) else round(float(v), 2)
                for v in result.daily[indicator]
            ],
        },
    }


def execute_run(
    cfg: dict, cache_dir: Path | None = None, runs_dir: Path | None = None
) -> dict:
    """执行一次回测并落盘运行记录（页面/API 用）。"""
    run = compute_run(cfg, cache_dir=cache_dir)
    out_dir = runs_dir or RUNS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{run['run_id']}.json").write_text(
        json.dumps(run, ensure_ascii=False), encoding="utf-8"
    )
    return run


def load_run(run_id: str, runs_dir: Path | None = None) -> dict | None:
    """读取单次运行记录（含 daily 曲线），不存在返回 None。"""
    out_dir = runs_dir or RUNS_DIR
    path = out_dir / f"{run_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def list_runs(limit: int = 50, runs_dir: Path | None = None) -> list[dict]:
    out_dir = runs_dir or RUNS_DIR
    if not out_dir.exists():
        return []
    headers = []
    for path in out_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        headers.append(
            {
                "run_id": data.get("run_id"),
                "created_at": data.get("created_at"),
                "symbol": data.get("symbol"),
                "name": data.get("name"),
                "params": data.get("params"),
                "metrics": data.get("metrics"),
            }
        )
    headers.sort(key=lambda h: h.get("created_at") or "", reverse=True)
    return headers[:limit]


# 执行手册配置（ETF 可交易口径，全部带最小调仓阈值与真实费率）
EXEC_CONFIGS: list[dict] = [
    {
        "key": "cyb_attack", "label": "创业板指 · 进攻主仓（执行用159915）",
        "params": {"symbol": "399006", "strategy": "ladder", "indicator": "b200",
                   "n_bands": 3, "direction": "contrarian", "low_edge": 30.0,
                   "high_edge": 70.0, "min_trade": 0.05, "fee_bps": 1.0},
    },
    {
        "key": "broker_attack", "label": "证券公司指数 · 进攻（执行用512880）",
        "params": {"symbol": "399975", "strategy": "ladder", "indicator": "b200",
                   "n_bands": 3, "direction": "contrarian", "low_edge": 30.0,
                   "high_edge": 70.0, "gamma": 1.0, "min_trade": 0.05, "fee_bps": 1.0},
    },
    {
        "key": "nev_attack", "label": "新能源汽车指数 · 进攻（执行用515030）",
        "params": {"symbol": "399976", "strategy": "ladder", "indicator": "b200",
                   "n_bands": 3, "direction": "contrarian", "low_edge": 40.0,
                   "high_edge": 60.0, "min_trade": 0.05, "fee_bps": 1.0},
    },
    {
        "key": "liquor_attack", "label": "中证白酒指数 · 进攻（执行用512690）",
        "params": {"symbol": "399997", "strategy": "ladder", "indicator": "b200",
                   "n_bands": 3, "direction": "contrarian", "low_edge": 40.0,
                   "high_edge": 60.0, "min_trade": 0.05, "fee_bps": 1.0},
    },
    {
        "key": "metal_attack", "label": "有色金属指数 · 进攻（执行用512400）",
        "params": {"symbol": "000819", "strategy": "ladder", "indicator": "b200",
                   "n_bands": 3, "direction": "contrarian", "low_edge": 40.0,
                   "high_edge": 60.0, "min_trade": 0.05, "fee_bps": 1.0},
    },
    {
        "key": "bank_attack", "label": "中证银行指数 · 进攻（执行用512800）",
        "params": {"symbol": "399986", "strategy": "ladder", "indicator": "b200",
                   "n_bands": 3, "direction": "contrarian", "low_edge": 40.0,
                   "high_edge": 60.0, "min_trade": 0.05, "fee_bps": 1.0},
    },
    {
        "key": "re_attack", "label": "房地产ETF · 进攻（低宽区年化+86%）",
        "params": {"symbol": "512200", "strategy": "ladder", "indicator": "b200",
                   "n_bands": 3, "direction": "contrarian", "low_edge": 30.0,
                   "high_edge": 70.0, "min_trade": 0.05, "fee_bps": 1.0},
    },
    {
        "key": "travel_attack", "label": "旅游ETF · 进攻",
        "params": {"symbol": "159766", "strategy": "ladder", "indicator": "b200",
                   "n_bands": 3, "direction": "contrarian", "low_edge": 30.0,
                   "high_edge": 70.0, "gate_mode": "ma200", "min_trade": 0.05,
                   "fee_bps": 1.0},
    },
    {
        "key": "csi1000_attack", "label": "中证1000ETF · 进攻",
        "params": {"symbol": "512100", "strategy": "ladder", "indicator": "b200",
                   "n_bands": 3, "direction": "contrarian", "low_edge": 30.0,
                   "high_edge": 70.0, "min_trade": 0.05, "fee_bps": 1.0},
    },
    {
        "key": "innovdrug_attack", "label": "创新药ETF · 进攻",
        "params": {"symbol": "159992", "strategy": "ladder", "indicator": "b200",
                   "n_bands": 3, "direction": "contrarian", "low_edge": 30.0,
                   "high_edge": 70.0, "min_trade": 0.05, "fee_bps": 1.0},
    },
    {
        "key": "food_attack", "label": "食品饮料ETF · 进攻（MA200闸）",
        "params": {"symbol": "515170", "strategy": "ladder", "indicator": "b200",
                   "n_bands": 3, "direction": "contrarian", "low_edge": 30.0,
                   "high_edge": 70.0, "gate_mode": "ma200", "min_trade": 0.05,
                   "fee_bps": 1.0},
    },
    {
        "key": "steel_attack", "label": "钢铁ETF · 进攻（MA200闸）",
        "params": {"symbol": "515210", "strategy": "ladder", "indicator": "b200",
                   "n_bands": 3, "direction": "contrarian", "low_edge": 30.0,
                   "high_edge": 70.0, "gate_mode": "ma200", "min_trade": 0.05,
                   "fee_bps": 1.0},
    },
    {
        "key": "dividend_attack", "label": "红利ETF沪 · 低波进攻",
        "params": {"symbol": "515180", "strategy": "ladder", "indicator": "b200",
                   "n_bands": 3, "direction": "contrarian", "low_edge": 30.0,
                   "high_edge": 70.0, "min_trade": 0.05, "fee_bps": 1.0},
    },
    {
        "key": "comm_attack", "label": "通信指数 · 进攻（RS灯亮时技术引擎接管）",
        "params": {"symbol": "980030", "strategy": "ladder", "indicator": "b200",
                   "n_bands": 3, "direction": "contrarian", "low_edge": 30.0,
                   "high_edge": 70.0, "min_trade": 0.05, "fee_bps": 1.0},
    },
    {
        "key": "hs300_defense", "label": "沪深300 · 攻守兼备（执行用510300）",
        "params": {"symbol": "000300", "strategy": "reversal", "indicator": "b200",
                   "low_extreme": 10.0, "high_extreme": 90.0, "confirm": 5.0,
                   "batch_mode": "band", "batches": 8, "batch_ratio": 0.6,
                   "sell_batches": 1, "gate_mode": "ma200", "min_trade": 0.05,
                   "fee_bps": 1.0},
    },
    {
        "key": "spy_defense", "label": "SPY · 防守（长持底仓+控回撤，40/80 美股边界）",
        "params": {"symbol": "SPY", "strategy": "ladder", "indicator": "b200",
                   "n_bands": 3, "direction": "momentum", "low_edge": 40.0,
                   "high_edge": 80.0, "gamma": 1.5, "vol_target": 0.15,
                   "gate_mode": "ma200", "min_trade": 0.05, "fee_bps": 1.0},
    },
    {
        "key": "qqq_defense", "label": "QQQ · 防守（长持底仓+控回撤）",
        "params": {"symbol": "QQQ", "strategy": "ladder", "indicator": "b200",
                   "n_bands": 5, "direction": "momentum", "low_edge": 20.0,
                   "high_edge": 80.0, "gamma": 1.5, "vol_target": 0.15,
                   "min_weight": 0.3, "gate_mode": "ma200", "min_trade": 0.05,
                   "fee_bps": 1.0},
    },
]


_SIPHON_N, _SIPHON_THR, _SIPHON_PERSIST = 120, 20.0, 10
_EW_CACHE: dict[tuple[str, float], pd.Series] = {}


def _equal_weight_index(parquet_name: str) -> pd.Series | None:
    """市场等权净值（A股=全A底表，美股=SP500 底表；与宽度同源同偏差）。

    底表缺失返回 None（提示灯静默，不阻塞信号构建）；缓存按 mtime 失效。
    """
    path = TIMING_CACHE_DIR.parent / parquet_name
    if not path.exists():
        return None
    mtime = path.stat().st_mtime
    key = (parquet_name, mtime)
    if key not in _EW_CACHE:
        wide = _read_parquet_cached(path)
        ret = wide.pct_change(fill_method=None)
        ew = (1 + ret.mean(axis=1, skipna=True).fillna(0)).cumprod()
        _EW_CACHE.clear()
        _EW_CACHE[key] = ew
    return _EW_CACHE[key]


def alert_state(market: str, cache_dir: Path | None = None) -> str | None:
    """系统双极值警报现值：双≤20（定心丸）/ 双≥85（热度警戒），取该市场宽度末行。"""
    if market == "cn":
        breadth_key = "cn_all"
    elif market == "us":
        breadth_key = "sp500"
    else:
        return None
    try:
        b = load_breadth(breadth_key, cache_dir=cache_dir or TIMING_CACHE_DIR)
    except FileNotFoundError:
        return None
    if len(b) == 0 or "b50" not in b or "b200" not in b:
        return None
    last = b.iloc[-1]
    b50, b200 = float(last["b50"]), float(last["b200"])
    if b50 <= 20 and b200 <= 20:
        return "双≤20 定心丸"
    if b50 >= 85 and b200 >= 85:
        return "双≥85 热度警戒"
    return None


def siphon_status(symbol: str, cache_dir: Path | None = None) -> dict:
    """RS120 虹吸提示灯（第十三轮定案）：RS120>+20pp 连续10日 → 独立行情。

    灯亮 = 该标的宽度引擎下岗、技术信号主导；灯灭 = 与全场同频，宽度引擎有效。
    A股对比全A等权、美股对比 SP500 等权；数据不足时各字段为 None。
    """
    unknown = {"rs120": None, "siphon": None, "engine": None}
    spec = INSTRUMENTS.get(symbol)
    if spec is None:
        return unknown
    parquet = "a_share_klines_full.parquet" if spec.market == "cn" else "sp500_klines.parquet"
    ew = _equal_weight_index(parquet)
    if ew is None:
        return unknown
    try:
        close = load_index_bars(symbol, cache_dir=cache_dir or TIMING_CACHE_DIR)["close"]
    except FileNotFoundError:
        return unknown
    both = pd.concat([close, ew], axis=1, join="inner").dropna()
    if len(both) < _SIPHON_N + _SIPHON_PERSIST:
        return unknown
    rs = (
        both.iloc[:, 0] / both.iloc[:, 0].shift(_SIPHON_N)
        - both.iloc[:, 1] / both.iloc[:, 1].shift(_SIPHON_N)
    ).dropna() * 100
    if rs.empty:
        return unknown
    fired = bool((rs > _SIPHON_THR).rolling(_SIPHON_PERSIST).min().iloc[-1])
    return {
        "rs120": round(float(rs.iloc[-1]), 1),
        "siphon": fired,
        "engine": "技术引擎·虹吸" if fired else "宽度引擎",
    }


def build_signals(cache_dir: Path | None = None) -> list[dict]:
    """执行手册当前信号：每配置的最新宽度值、目标仓位、引擎状态与近期调仓。"""
    out = []
    alerts: dict[str, str | None] = {}
    for cfg in EXEC_CONFIGS:
        params = cfg["params"]
        try:
            run = compute_run(params, cache_dir=cache_dir)
        except Exception as e:  # noqa: BLE001 - 单配置失败不挡其余
            out.append({"key": cfg["key"], "label": cfg["label"], "error": str(e)[:80]})
            continue
        daily = run["daily"]
        m = run["metrics"]
        market = INSTRUMENTS[params["symbol"]].market
        if market not in alerts:
            alerts[market] = alert_state(market, cache_dir)
        breadth_now = daily["breadth"][-1]
        weight_now = daily["weight"][-1]
        if params["strategy"] == "ladder":
            edges = _fixed_edges(
                int(params["n_bands"]),
                float(params.get("low_edge", 0.0)),
                float(params.get("high_edge", 100.0)),
            )
            known = breadth_now is not None
            next_down = next(
                (e for e in sorted(edges) if known and breadth_now < e), None
            )
            next_up = next(
                (e for e in sorted(edges, reverse=True) if known and breadth_now > e),
                None,
            )
            levels = [round(float(e), 1) for e in edges]
            dn = f"{next_down:.0f}" if next_down else "—"
            up = f"{next_up:.0f}" if next_up else "—"
            trigger = f"B 下穿 {dn} 加仓 / 上穿 {up} 减仓"
        else:
            levels = [float(params["low_extreme"]), float(params["high_extreme"])]
            trigger = (
                f"B ≤ {params['low_extreme']} 后回升 {params['confirm']} 点分批买；"
                f"B ≥ {params['high_extreme']} 后回落清仓"
            )
        out.append({
            "key": cfg["key"],
            "label": cfg["label"],
            "symbol": params["symbol"],
            "indicator": params["indicator"],
            "as_of": daily["date"][-1],
            "breadth_now": breadth_now,
            "weight_now": weight_now,
            **siphon_status(params["symbol"], cache_dir),
            "alert": alerts.get(market),
            "trigger": trigger,
            "levels": levels,
            "recent_trades": run["trades"][-3:],
            "full_cagr": m["strategy_cagr"],
            "full_bh_cagr": m["benchmark_cagr"],
            "full_mdd": m["strategy_mdd"],
            "n_trades": int(m["n_trades"]),
        })
    return out


def build_portfolio(cache_dir: Path | None = None, signals: list[dict] | None = None) -> dict:
    """组合层现状（第 19/20/21 轮）：A 股进攻 sleeve 的三档组合仓位。

    - balanced_weight：进攻配置目标仓位均值（平衡型 = 第19轮冠军组合现值）
    - defensive_weight：目标仓位 × (收盘>MA20) 的均值（防守型 = 协同组合现值）
    - 宽度闸 sleeve（食品饮料/钢铁/旅游等 gate=ma200）其目标仓位已含闸门效应。
    """
    sigs = signals if signals is not None else build_signals(cache_dir)
    sleeves = []
    for s in sigs:
        if s.get("error") or not str(s.get("key", "")).endswith("_attack"):
            continue
        sym = s.get("symbol", "")
        if not sym[:1].isdigit():
            continue
        ma20_on = None
        try:
            close = load_index_bars(sym, cache_dir=cache_dir or TIMING_CACHE_DIR)["close"]
            ma20_on = bool(close.iloc[-1] > close.rolling(20).mean().iloc[-1])
        except FileNotFoundError:
            pass
        w = float(s.get("weight_now") or 0.0)
        sleeves.append({
            "key": s.get("key"), "symbol": sym, "label": s.get("label"),
            "weight": w, "ma20_on": ma20_on,
            "defensive_weight": (w if ma20_on else 0.0) if ma20_on is not None else w,
            "engine": s.get("engine"), "alert": s.get("alert"),
        })
    atk = [x for x in sleeves if x["ma20_on"] is not None]
    return {
        "as_of": max((str(x.get("as_of")) for x in sigs if x.get("as_of")), default=None),
        "balanced_weight": (
            round(sum(x["weight"] for x in atk) / len(atk), 4) if atk else None
        ),
        "defensive_weight": (
            round(sum(x["defensive_weight"] for x in atk) / len(atk), 4) if atk else None
        ),
        "n_sleeves": len(atk),
        "full_count": sum(1 for x in atk if x["weight"] >= 0.95),
        "empty_count": sum(1 for x in atk if x["weight"] <= 0.05),
        "siphon_count": sum(1 for x in sleeves if x.get("engine") and "虹吸" in x["engine"]),
        "sleeves": sleeves,
    }
