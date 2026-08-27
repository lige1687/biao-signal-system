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
    INSTRUMENTS,
    TIMING_CACHE_DIR,
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

_BREADTH_LABELS = {"cn_all": "全A B20/B50/B200", "sp500": "SP500 B20/B50/B200"}


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
    try:
        breadth = load_breadth(spec.breadth, cache_dir=cache)
    except FileNotFoundError as e:
        raise TimingDataUnavailable(
            f"DATA_UNAVAILABLE: {spec.breadth} 宽度数据缺失，"
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
    ) if merged["strategy"] == "ladder" else None
    reversal = ReversalParams(
        indicator=merged["indicator"], low_extreme=float(merged["low_extreme"]),
        high_extreme=float(merged["high_extreme"]), confirm=float(merged["confirm"]),
        batch_mode=merged["batch_mode"], batches=int(merged["batches"]),
    ) if merged["strategy"] == "reversal" else None
    gate = TrendGate(mode=merged["gate_mode"], cap=float(merged["gate_cap"]))
    warmup = aligned.loc[:start_ts].iloc[:-1]
    target_full = build_target(aligned, ladder, reversal, gate, warmup)
    target = target_full.loc[window.index]

    fee = float(merged["fee_bps"]) if merged["fee_bps"] is not None else spec.fee_default_bps
    result = simulate(window, target, fee_bps=fee)
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
