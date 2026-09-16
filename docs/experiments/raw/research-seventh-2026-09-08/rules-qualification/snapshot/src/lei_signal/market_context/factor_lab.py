"""因子实验台扩展 · 预计算层（文主任增量 #6，research_proxy）。

三个实验模块（全部只读展示，不进主判定链/过滤链）：

1. 全市场因子组合（long-only 前 30%，月度再平衡）：
   - 低波（60 日已实现波动升序）——BAB 低波动异象的 long-only 视角
     （原版含做空高波腿，本实验不做空，如实标注）；
   - 12-1 动量（降序）——已知个股层证据弱（factor_panel.FACTOR_META），如实标注；
   - 价值 / 质量：本地无 PE/PB/财务数据源 → 标「数据受限·缓做」，不用价格冒充。
   基准 = 等权全市场。数据 = a_share_klines 全史矩阵（仅收盘价）。

2. L1-L6 周度市场难度分级（评分卡，权重与分档阈值进 rules.v2.yaml）：
   宽度 B50 分位(40%) + 市场已实现波动分位(40%) + 宽度 5 日变化(20%) → L1..L6；
   离线回放 33 年历史给周度评级序列，并验证「高档之后市场波动是否更大」。

3. 估值分位 chips：蛋卷指数估值接口（市值加权 PE-TTM + 历史分位，约近 10 年
   口径）；等权口径本机无数据源，如实标注（博主教训：两口径可差 35 分位）。

落盘：LEI_CACHE_ROOT/factor_lab_snapshot.json（原子写），API 只读快照不重算。
页面顶部固定「实验」标识；下架条件见页脚（连续 8 周无有效结论即下架）。
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from lei_signal.data.cache import DEFAULT_CACHE_DIR
from lei_signal.domain.rules_config import get_rule

logger = logging.getLogger(__name__)

ROOT = Path(os.environ.get("LEI_CACHE_ROOT", str(DEFAULT_CACHE_DIR)))
RISK_RULE_ID = "risk_grade_l1l6"

LAB_NOTE = (
    "实验台（research_proxy，文主任调研 2026-09-05 增量 #6）：全部输出为研究观测，"
    "不流入主判定链/过滤链、不出买卖点。组合回测未计手续费/滑点/涨跌停，"
    "月度再平衡、等权持有；估值分位为外部接口口径。下架条件：连续 8 周无有效结论"
    "即下架本页对应模块。"
)


def _snapshot_path() -> Path:
    return ROOT / "factor_lab_snapshot.json"


def _json_safe(value):
    """递归把 NaN/inf 换成 None（json.dumps allow_nan=False 的前置清洗）。"""
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def _save_atomic(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(_json_safe(payload), ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )
    tmp.replace(path)


def load_lab_snapshot() -> dict | None:
    p = _snapshot_path()
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("因子实验台快照读取失败: %s", exc)
        return None


# ── 数据 ────────────────────────────────────────────────────────────────

def load_stock_matrix(min_history: int = 253) -> pd.DataFrame:
    """全A收盘宽表（33 年全史 + live 尾部，同 vulnerability 口径）。"""
    frames: list[pd.DataFrame] = []
    full = ROOT / "a_share_klines_full.parquet"
    if full.exists():
        frames.append(pd.read_parquet(full).astype("float32"))
    from lei_signal.market_context.a_share_breadth import load_kline_cache

    cache = load_kline_cache()
    if cache:
        rows = [(d, s, c) for s, series in cache.items() for d, c in series]
        live = pd.DataFrame(rows, columns=["date", "symbol", "close"])
        live["date"] = pd.to_datetime(live["date"])
        frames.append(live.pivot(index="date", columns="symbol", values="close").astype("float32"))
    if not frames:
        return pd.DataFrame()
    # 统一列名：剥前缀 → 6 位码。合并语义与 a_share_breadth 读侧一致：
    # 全史铺底（1990 起），live 覆盖重叠期（越新越准）——绝不能让 2023 起的
    # live 列把 33 年全史列顶掉（列名去重 keep=last 的坑）。
    normalized = []
    for f in frames:
        f = f.copy()
        f.columns = [str(c)[-6:] for c in f.columns]
        normalized.append(f.loc[:, ~f.columns.duplicated(keep="last")])
    # live 在后：live.combine_first(全史) = live 值优先、缺失用全史铺底
    combined = normalized[0]
    for f in normalized[1:]:
        combined = f.combine_first(combined)
    return combined.sort_index()


# ── 模块 1：全市场因子组合（纯函数，单测覆盖）──────────────────────────

def factor_scores_monthly(piv: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """每月末的因子截面打分（行=月末，列=6位码；只用当日及此前数据）。

    low_vol = 近 60 日收益波动（升序=低波在前）；
    mom_121 = close(t-21)/close(t-252)-1（降序=强动量在前）。
    """
    ret = piv.pct_change()
    vol60 = ret.rolling(60).std()
    mom121 = piv.shift(21) / piv.shift(252) - 1.0
    month_last = piv.groupby([piv.index.year, piv.index.month]).tail(1).index
    return {
        "low_vol": vol60.loc[vol60.index.isin(month_last)],
        "mom_121": mom121.loc[mom121.index.isin(month_last)],
    }


def portfolio_returns(
    piv: pd.DataFrame, score_me: pd.DataFrame, *,
    top_frac: float = 0.30, min_eligible: int = 300, low_is_good: bool = False,
) -> pd.Series:
    """月度 long-only 组合月收益序列（等权，未计费用）。

    t 月末按 score 选前 top_frac、持有 t+1 月；收益 = t+1 月末相对 t 月末
    的等权均值（next-bar 语义，无前视）。low_is_good=True 取最小值前 k。
    """
    month_ends = piv.groupby([piv.index.year, piv.index.month]).tail(1).index
    closes_me = piv.loc[piv.index.isin(month_ends)].copy()
    closes_me = closes_me[closes_me.index.isin(score_me.index)]
    monthly_ret = closes_me.pct_change()
    out: dict[pd.Timestamp, float] = {}
    dates = list(score_me.index)
    for i in range(len(dates) - 1):
        score = score_me.iloc[i].dropna()
        if len(score) < min_eligible:
            continue
        nxt_ret = monthly_ret.loc[dates[i + 1]] if dates[i + 1] in monthly_ret.index else None
        if nxt_ret is None:
            continue
        k = max(1, int(len(score) * top_frac))
        picked = score.nsmallest(k) if low_is_good else score.nlargest(k)
        rets = nxt_ret.reindex(picked.index).dropna()
        if len(rets):
            out[dates[i + 1]] = float(rets.mean())
    return pd.Series(out).sort_index()


def summarize_series(r: pd.Series, benchmark: pd.Series, label: str) -> dict:
    """组合摘要：终值/年化/分年/相对基准超额（全部简单收益口径，注明未计费用）。"""
    aligned_b = benchmark.reindex(r.index).dropna()
    r = r.dropna()
    common = r.index.intersection(aligned_b.index)
    r, b = r.loc[common], aligned_b.loc[common]
    if r.empty:
        return {"label": label, "n_months": 0}
    total = float((1.0 + r).prod() - 1.0)
    years = len(r) / 12.0
    cagr = float((1.0 + total) ** (1.0 / years) - 1.0) if years > 0 else None
    by_year: dict[str, float] = {}
    for year, sub in r.groupby(r.index.year):
        by_year[str(year)] = round(float((1.0 + sub).prod() - 1.0) * 100, 1)
    b_total = float((1.0 + b).prod() - 1.0)
    b_cagr = float((1.0 + b_total) ** (1.0 / years) - 1.0) if years > 0 else None
    return {
        "label": label,
        "n_months": len(r),
        "start": str(r.index[0].date()),
        "end": str(r.index[-1].date()),
        "total_return_pct": round(total * 100, 1),
        "cagr_pct": round(cagr * 100, 2) if cagr is not None else None,
        "benchmark_total_pct": round(b_total * 100, 1),
        "benchmark_cagr_pct": round(b_cagr * 100, 2) if b_cagr is not None else None,
        "excess_cagr_pct": (
            round((cagr - b_cagr) * 100, 2) if cagr and b_cagr is not None else None
        ),
        "by_year_pct": by_year,
    }


def build_portfolio_section(piv: pd.DataFrame, top_frac: float = 0.30) -> dict:
    scores = factor_scores_monthly(piv)
    # 基准：等权全市场（同再平衡频率）
    month_ends = piv.groupby([piv.index.year, piv.index.month]).tail(1).index
    closes_me = piv.loc[piv.index.isin(month_ends)]
    benchmark = closes_me.pct_change().mean(axis=1, skipna=True).dropna()
    rows = []
    for key, score in scores.items():
        low_is_good = key == "low_vol"
        r = portfolio_returns(
            piv, score, top_frac=top_frac, min_eligible=300, low_is_good=low_is_good
        )
        label = (
            "低波前30%（BAB·long-only 视角，不做空高波腿）"
            if key == "low_vol"
            else "12-1动量前30%（个股层证据弱，见评级卡）"
        )
        rows.append(summarize_series(r, benchmark, label))
    return {
        "title_cn": "全市场因子组合（long-only 前 30%，月度再平衡，等权，未计费用）",
        "top_frac": top_frac,
        "portfolios": rows,
        "restricted": [
            "价值（PE/PB 复合）：本机无估值数据源——数据受限，缓做（不用价格冒充）",
            "质量（ROE/盈利质量）：本机无财务数据源——数据受限，缓做",
        ],
        "benchmark_cn": "等权全市场（同月度再平衡）",
        "note_cn": (
            "BAB 原版=做多低波组+做空高波组的对冲组合；本实验只做多低波组"
            "（long-only 视角），如实标注差异。样本早年（<300 只合格）自动跳过。"
        ),
    }


# ── 模块 2：L1-L6 市场难度分级（评分卡）─────────────────────────────────

def risk_score(b50_pct: float | None, rv_pct: float | None, b50_delta5: float | None,
               weights: dict) -> float | None:
    """0-100 评分（高分=市场难度高）。任一主分量缺失返回 None。"""
    if b50_pct is None or rv_pct is None:
        return None
    score = weights["breadth"] * (1.0 - b50_pct) + weights["rv"] * rv_pct
    if b50_delta5 is not None and weights.get("delta", 0) > 0:
        # 宽度 5 日下行 = 难度加分（0~delta 满配）
        norm = max(-20.0, min(0.0, b50_delta5)) / -20.0
        score += weights["delta"] * norm
    return float(score * 100.0)  # 0-100（与 grade_bands 同量纲）


def grade_from_score(score: float | None, bands: list[float]) -> str | None:
    """评分 → L1..L6（bands=5 个分界，从小到大）。None → None。"""
    if score is None:
        return None
    for i, band in enumerate(bands):
        if score <= band:
            return f"L{i + 1}"
    return "L6"


def build_risk_grade_section(piv: pd.DataFrame, weights: dict, bands: list[float]) -> dict:
    """33 年回放：宽度 B50 分位 + 等权市场 RV 分位 → 周度评分/分级 + 后验。"""
    from lei_signal.market_context.a_share_breadth import get_ma_breadth_history

    hist = get_ma_breadth_history(lookback_days=9000)
    if not hist:
        return {"available": False, "reason_cn": "宽度历史文件缺失（先跑宽度回填）"}
    b50 = pd.Series(
        {h["date"]: h.get("ma50_pct") for h in hist if h.get("ma50_pct") is not None},
        dtype=float,
    ).sort_index()
    b50.index = pd.to_datetime(b50.index)

    # 市场等权日收益 → RV20 → 756 日分位（min 300 只合格）
    eligible = piv.notna().sum(axis=1)
    ret = piv.pct_change().where(eligible >= 300)
    mkt_ret = ret.mean(axis=1, skipna=True).dropna()
    rv = mkt_ret.rolling(20).std() * np.sqrt(252.0)
    rv_pct = rv.rolling(756, min_periods=250).rank(pct=True)

    b50_pct = b50.rolling(756, min_periods=250).rank(pct=True)
    b50_delta5 = b50 - b50.shift(5)

    frame = pd.DataFrame({
        "b50_pct": b50_pct, "rv_pct": rv_pct, "b50_delta5": b50_delta5,
        "fwd_rv20": rv.shift(-20), "fwd_ret20": mkt_ret.shift(-20).rolling(20).sum(),
    }).dropna(subset=["b50_pct", "rv_pct"])

    frame["score"] = [
        risk_score(r.b50_pct, r.rv_pct, r.b50_delta5, weights)
        for r in frame.itertuples()
    ]
    frame["grade"] = [grade_from_score(s, bands) for s in frame["score"]]
    frame = frame.dropna(subset=["grade"])
    if frame.empty:
        return {"available": False, "reason_cn": "评分样本不足（历史过短）"}

    # 周度采样（每周最后一个交易日）+ 当前档
    weekly = frame.resample("W-FRI").last().dropna(subset=["grade"])
    current = frame.iloc[-1]

    # 后验：各档之后 20 日的市场波动与收益（点时切片，重叠样本仅描述统计）
    by_grade: dict[str, dict] = {}
    for grade, sub in frame.groupby("grade"):
        by_grade[grade] = {
            "n_days": int(len(sub)),
            "fwd_rv20_mean_pct": round(float(sub["fwd_rv20"].dropna().mean() * 100), 1),
            "fwd_ret20_mean_pct": round(float(sub["fwd_ret20"].dropna().mean() * 100), 1),
        }
    history = [
        {"date": str(ts.date()), "score": round(float(r.score), 1), "grade": r.grade}
        for ts, r in weekly.tail(520).iterrows()
    ]
    return {
        "available": True,
        "as_of": str(frame.index[-1].date()),
        "current": {
            "date": str(frame.index[-1].date()),
            "score": round(float(current.score), 1),
            "grade": current.grade,
            "b50_pct": round(float(current.b50_pct), 3),
            "rv_pct": round(float(current.rv_pct), 3),
        },
        "weights": weights,
        "bands": bands,
        "by_grade": by_grade,
        "history": history,
        "note_cn": (
            "评分卡（文主任 L1-L6 灵感，A 股参数自定，research_proxy）："
            "宽度越弱/波动越高/宽度恶化 → 难度越高。分级只是「环境难易」的"
            "叙事标注，不参与任何技术判定、不做硬过滤。后验表为重叠样本的"
            "描述统计（非独立事件检验）。"
        ),
    }


# ── 模块 3：估值分位 chips（蛋卷接口，市值加权口径）────────────────────

_DANJUAN_URL = "https://danjuanfunds.com/djapi/index_eva/dj"

#: 主要宽基（蛋卷 index_code → 展示名）
_VALUATION_INDEXES: dict[str, str] = {
    "SH000300": "沪深300", "SH000016": "上证50", "SH000905": "中证500",
    "SZ399006": "创业板指", "SH000922": "中证红利",
}


def fetch_valuation_chips() -> dict:
    """蛋卷指数估值 → 主要宽基 PE-TTM + 历史分位（约近10年口径，市值加权）。

    等权口径本机无数据源——如实标注（博主教训：两口径可差 35 分位）。
    失败返回 available=False，页面显示不可得，不冒充。
    """
    try:
        req = urllib.request.Request(_DANJUAN_URL, headers={"User-Agent": "Mozilla/5.0"})
        payload = json.loads(urllib.request.urlopen(req, timeout=10).read().decode("utf-8"))
        items = (payload.get("data") or {}).get("items") or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("估值分位接口失败: %s", exc)
        return {"available": False, "reason_cn": f"估值接口不可达：{exc}"}
    chips = []
    for it in items:
        code = str(it.get("index_code", ""))
        if code not in _VALUATION_INDEXES:
            continue
        pe = it.get("pe")
        pctile = it.get("pe_percentile")
        if pe in (None, 0) or pctile is None:
            continue
        chips.append({
            "index_code": code,
            "name_cn": _VALUATION_INDEXES[code],
            "pe_ttm": round(float(pe), 2),
            "pe_percentile": round(float(pctile) * 100, 1),
        })
    if not chips:
        return {"available": False, "reason_cn": "接口返回无匹配宽基"}
    return {
        "available": True,
        "as_of": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "chips": chips,
        "note_cn": (
            "估值分位=当前贵贱程度在历史（约近10年）中的位置，只做背景标注，"
            "不构成买卖依据（低估不是止损豁免理由）。口径=市值加权（蛋卷）；"
            "等权口径本机无数据源，如实标注——两口径历史上可差 35 分位。"
        ),
    }


# ── 组装 ────────────────────────────────────────────────────────────────

def build_lab_snapshot(now: datetime | None = None) -> dict:
    """构建实验台快照并原子落盘（由 scripts/precompute_factor_lab.py 调用）。"""
    now = now or datetime.now()
    spec = get_rule(RISK_RULE_ID)
    weights = {
        "breadth": float(spec.param("weight_breadth", 0.40)),
        "rv": float(spec.param("weight_rv", 0.40)),
        "delta": float(spec.param("weight_breadth_delta", 0.20)),
    }
    bands = [float(b) for b in spec.param("grade_bands", [20, 35, 50, 65, 80])]
    top_frac = float(spec.param("portfolio_top_frac", 0.30))

    piv = load_stock_matrix()
    sections: dict = {"generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                      "provenance": "research_proxy", "note_cn": LAB_NOTE}
    if piv.empty:
        sections["portfolios"] = {"available": False, "reason_cn": "全A矩阵不可用"}
        sections["risk_grades"] = {"available": False, "reason_cn": "全A矩阵不可用"}
    else:
        sections["portfolios"] = build_portfolio_section(piv, top_frac=top_frac)
        sections["risk_grades"] = build_risk_grade_section(piv, weights, bands)
    sections["valuation"] = fetch_valuation_chips()
    _save_atomic(sections, _snapshot_path())
    logger.info("因子实验台快照落盘: %s", _snapshot_path())
    return sections


__all__ = [
    "LAB_NOTE",
    "build_lab_snapshot",
    "build_portfolio_section",
    "build_risk_grade_section",
    "factor_scores_monthly",
    "fetch_valuation_chips",
    "grade_from_score",
    "load_lab_snapshot",
    "load_stock_matrix",
    "portfolio_returns",
    "risk_score",
    "summarize_series",
]
