"""因子观测台 · 预计算层。

设计要点（照 sector_trend 模式落地）：

- 全部判定标 ``research_proxy``，只产出「读数 / 分位 / 排名」类字段，不出买卖点。
- 因子评级（``factors[*].verdict``）是 **2026-08-27 本地数据实证的静态留痕**，
  不是实时计算；证据与脚本记录见 ``docs/research-momentum-and-system-integration.md``
  第六节。研究更新后需同步修订 FACTOR_META，不允许前端或调用方另造评级。
- 数据不可用显式置 null 并写 ``notes``，绝不冒充（含历史不足、数据过旧）。
- ``mom_20_group_pct`` 为同组（A股 / 美股 / 板块）内截面分位，仅供「短线超买警示」，
  对应实证结论「A股个股短动量为反向因子」——高分位是**风险提示**而非看多理由。
- ADX 未通过分年稳健性检验（2019-2021 方向相反、逐 ETF 仅 5/11 为正），
  评级为 fail：仅留痕观测，禁止用于过滤或排序。
- 原子写落盘（照 ``sector_trend._save_atomic``），日志进 ``logs/``。
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from lei_signal.data.cache import DEFAULT_CACHE_DIR

logger = logging.getLogger(__name__)

ROOT = Path(os.environ.get("LEI_CACHE_ROOT", str(DEFAULT_CACHE_DIR)))

#: 实证研究日期（与 docs/research-momentum-and-system-integration.md 第六节对应）。
STUDY_DATE = "2026-08-27"
STUDY_REF = "docs/research-momentum-and-system-integration.md#六、实证检验"

RESEARCH_PROXY_NOTE = (
    "本页全部为 research_proxy 研究观测：因子读数不构成买卖点、不挡任何 LEI 技术信号；"
    f"评级为 {STUDY_DATE} 本地数据实证的静态留痕（{STUDY_REF}），随研究更新而修订。"
)

# ── 参数（集中于此，不做界面可调）───────────────────────────────────────
RV_WINDOW = 20            # 已实现波动率窗口（日）
RV_RANK_WINDOW = 756      # 分位回看窗口（≈3 年）
RV_RANK_MIN = 252         # 分位最少样本（≈1 年）
MOM_LONG = 252            # 12-1 动量总回看（≈12 个月）
MOM_SKIP = 21             # 跳过最近 21 日（≈1 个月，规避短期反转）
MOM_SHORT = 20            # 短动量窗口（反向警示用）
ADX_WINDOW = 14
MIN_BARS = 300            # 低于此长度的标的不进面板
STALE_DAYS = 14           # 数据截止超过 14 个自然日 → notes 标注数据过旧

#: 因子评级卡（实证留痕，见模块 docstring 的修订纪律）。
FACTOR_META: dict[str, dict] = {
    "rv_pct": {
        "label": "已实现波动率分位",
        "formula": f"近{RV_WINDOW}日收益标准差年化；分位=近{RV_RANK_WINDOW}日滚动百分位",
        "verdict": "实证稳健",
        "verdict_level": "pass",
        "evidence": (
            "①条件收益：ETF池趋势日内高波(≥0.8)前向21日收益 8年中6年跑输（均值约-2%/月）。"
            "②LEI信号对账（3755条入场信号，41标的，2016-2026）：标的高波期信号60日均值 "
            "4.53%→1.83%；**市场RV分位更有预测力：低波4.98% vs 高波0.73%（胜率53%→46%）**。"
            "③策略化：高波空仓有害（2024年V型暴涨砍仓），目标波动中性微正。"
        ),
        "usage": (
            "市场RV分位（页头）与标的RV分位列共同构成「信号可信度打折」提示，仅分组不挡信号。"
            "**分模块语义（LEI对账新发现）**：趋势类模块A（趋势回调）与D（假突破反向）在高波期显著变差"
            "（A: 2.23%→0.85%；D: 2.77%→-0.36%），而**模块C（2B/破底翻）在高波期反而更好"
            "（1.76%→2.67%）——高波提示主要针对A/B/D类信号，C类以高波为燃料**。"
            "另：选强/轮动场景剔除高波候选（ETF池三信号族一致改善）。"
        ),
    },
    "mom_121": {
        "label": "12-1 动量",
        "formula": f"P(t-{MOM_SKIP})/P(t-{MOM_LONG})-1（剔除最近约1个月）",
        "verdict": "板块层有效 · 标的层仅参考",
        "verdict_level": "weak",
        "evidence": (
            "20个板块指数 IC +0.133（t=3.5，63日持有，6/8 年为正）；"
            "A股个股 12 组检验 IC 全负（-0.026~-0.072）；本系统 ETF 池 top3 轮动超额 "
            "+0.34%/月 不显著（t=0.5，n=52 月）。策略化回测（8年含成本）：板块 top3 轮动 "
            "11.5% 跑输等权 14.6%，分年呈周期性失效（2019/2022-2024 输），最差月 -27.6%。"
        ),
        "usage": (
            "板块排序的信息维度（研究分组用）；个股/ETF 层只作参考，不单独驱动决策——"
            "策略化回测证实独立轮动跑不赢等权（docs/research-factor-backtest.md A 段）。"
        ),
    },
    "mom_20": {
        "label": "20日短动量（反向警示）",
        "formula": f"P(t)/P(t-{MOM_SHORT})-1",
        "verdict": "反向因子 · 追高警示",
        "verdict_level": "inverse",
        "evidence": (
            "A股个股 mom_20 截面 IC -0.066（t=-6.1，2010-2026 全市场）："
            "短期涨幅排名对前向收益为负贡献（买前期最强组每月跑输约 1.4%）。"
            "**注意边界**：LEI 信号对账（3755条）显示信号日 mom20≥80分位的信号"
            "前向20日 2.15% 反而略好于低组 1.42%——反向效应存在于**裸标的截面**，"
            "不适用于已通过结构确认的 LEI 信号。"
        ),
        "usage": (
            "读数处于同组高分位（≥0.8）时提示**裸标的层面**的短线超买/追高风险（无入场结构时），"
            "与顶底结构的追高风险判断互为印证；对已触发的 LEI 信号无减分作用。不是看多理由。"
        ),
    },
    "adx14": {
        "label": "ADX14 趋势强度",
        "formula": f"Wilder ADX({ADX_WINDOW})",
        "verdict": "未通过稳健性检验 · 仅留痕",
        "verdict_level": "fail",
        "evidence": (
            "pooled 看：趋势日 ADX≥25 前向 21 日收益 2.03%/月 vs ADX<20 的 1.17%（差 +0.86%）；"
            "但按年拆 2019-2021 方向相反（-5.2%~-1.4%），逐 ETF 仅 5/11 方向为正——"
            "显著性来自 2025-2026 牛市与日频重叠样本，属伪显著。"
        ),
        "usage": (
            "仅观测留痕；禁止用于信号过滤、排序或仓位调整。"
            "此条同时是「必须做分年拆检」的登记案例。"
        ),
    },
    "vol_up": {
        "label": "放量确认",
        "formula": "5日均量 > 20日均量（量能趋势向上）",
        "verdict": "组合级风控参考 · 信号层不一致",
        "verdict_level": "weak",
        "evidence": (
            "组合级（25资产×2趋势规则×8年）：放量确认使组合 Sharpe 0.71→0.88、MaxDD -17.0%→-11.9%"
            "（改善集中在回撤控制）；但逐资产仅 26/50 改善，且 LEI 信号对账（3755条）显示"
            "信号日放量的前向60日 2.99% 反而低于缩量的 3.82%——**信号层面无增强**。"
        ),
        "usage": (
            "标的表「量能」列读数仅作标的状态标注与 LEI 量能异常规则的量化旁证；"
            "其验证过的价值在组合回撤控制，不在单信号收益预测。"
        ),
    },
    "idio_vol": {
        "label": "特质波动率（个股截面 · 知识卡）",
        "formula": "60日超额收益（个股−等权市场）标准差，截面排名",
        "verdict": "实证最稳 · 个股排雷维度",
        "verdict_level": "pass",
        "evidence": (
            "A股全市场月频截面 IC -0.090（t=-9.3），2009-2026 全部 18 年为负——"
            "高特质波动个股系统性跑输（彩票偏好反面）；偏度因子同向佐证（-0.025，17/18 年负）。"
            "为两轮检验中最稳健的截面发现。"
        ),
        "usage": (
            "本卡为个股截面知识留痕（不适用 ETF/板块标的打分）：若未来做个股层，"
            "「低特质波动」进入排雷/选股维度；与标的层 RV 分位互为印证——避高波在两层都成立。"
        ),
    },
}


def _panel_path() -> Path:
    return ROOT / "factor_panel_snapshot.json"


# ════════════════════════════════════════════════════════════════════════
# 纯函数（单元测试覆盖对象）
# ════════════════════════════════════════════════════════════════════════
def realized_vol(close: pd.Series, window: int = RV_WINDOW) -> float | None:
    """年化已实现波动率；样本不足返回 None。"""
    if len(close) < window + 1:
        return None
    ret = close.pct_change().iloc[-(window + 1):]
    if ret.isna().any():
        return None
    rv = float(ret.std(ddof=1) * np.sqrt(252.0))
    return rv if np.isfinite(rv) else None


def realized_vol_percentile(close: pd.Series, window: int = RV_WINDOW,
                            rank_window: int = RV_RANK_WINDOW,
                            min_periods: int = RV_RANK_MIN) -> float | None:
    """当前 RV 在自身近 3 年历史的滚动百分位（0~1）。"""
    rv_hist = close.pct_change().rolling(window).std() * np.sqrt(252.0)
    if len(rv_hist) < min_periods:
        return None
    rank = rv_hist.rolling(rank_window, min_periods=min_periods).rank(pct=True)
    val = rank.iloc[-1]
    if pd.isna(val):
        return None
    return float(val)


def momentum_skip(close: pd.Series, lookback: int = MOM_LONG, skip: int = MOM_SKIP) -> float | None:
    """跳月动量：P(t-skip)/P(t-lookback)-1（12-1 口径，两端均为日历偏移）。"""
    if len(close) < lookback + 1:
        return None
    p_now = close.iloc[-1 - skip]        # index t-skip
    p_past = close.iloc[-(lookback + 1)]  # index t-lookback
    if pd.isna(p_now) or pd.isna(p_past) or p_past == 0:
        return None
    return float(p_now / p_past - 1.0)


def momentum_plain(close: pd.Series, window: int = MOM_SHORT) -> float | None:
    if len(close) < window + 1:
        return None
    p0, p1 = close.iloc[-1 - window], close.iloc[-1]
    if pd.isna(p0) or p0 == 0 or pd.isna(p1):
        return None
    return float(p1 / p0 - 1.0)


def adx14(high: pd.Series, low: pd.Series, close: pd.Series,
          window: int = ADX_WINDOW) -> float | None:
    """Wilder ADX；数据不足或退化（无方向波动）返回 None。"""
    if len(close) < 3 * window:
        return None
    h, lo, c = (high.to_numpy(dtype=float), low.to_numpy(dtype=float),
                close.to_numpy(dtype=float))
    prev_c = np.roll(c, 1)
    tr = np.maximum(h - lo, np.maximum(np.abs(h - prev_c), np.abs(lo - prev_c)))
    up, dn = np.diff(h, prepend=h[0]), -np.diff(lo, prepend=lo[0])
    plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    ewm = pd.Series(tr).ewm(alpha=1.0 / window, adjust=False).mean().to_numpy()
    atr = np.where(ewm > 0, ewm, np.nan)
    pdi = 100.0 * pd.Series(plus_dm).ewm(alpha=1.0 / window, adjust=False).mean().to_numpy() / atr
    mdi = 100.0 * pd.Series(minus_dm).ewm(alpha=1.0 / window, adjust=False).mean().to_numpy() / atr
    dx = 100.0 * np.abs(pdi - mdi) / np.where((pdi + mdi) > 0, pdi + mdi, np.nan)
    adx = pd.Series(dx).ewm(alpha=1.0 / window, adjust=False).mean().iloc[-1]
    if pd.isna(adx):
        return None
    return float(adx)


def classify_symbol(code: str) -> tuple[str, str]:
    """(group, subgroup)：group 用于同组截面分位（A股/美股/板块）。"""
    if code.endswith(".SECTOR") or code.startswith("TH"):
        return "sector", "sector"
    if code.startswith("^"):
        return "us", "us_index"
    if "." not in code:  # SOXX / IGV / XLK 等
        return "us", "us_etf"
    body, _, _suffix = code.partition(".")
    if body.startswith(("51", "56", "58", "15")):
        return "cn", "cn_etf"
    if body.startswith(("000", "399", "899")):
        return "cn", "cn_index"
    return "cn", "cn_stock"


def _fmt(x: float | None, nd: int = 4) -> float | None:
    if x is None or not np.isfinite(x):
        return None
    return round(float(x), nd)


def compute_symbol_factors(df: pd.DataFrame, now: datetime | None = None) -> dict:
    """单标的因子行。缺数显式 None + notes（红线 6）；仅 close 也可用（ADX 置 None）。"""
    if "close" not in df.columns:
        raise KeyError("close")
    close = df["close"].astype(float)
    notes: list[str] = []
    if {"high", "low"}.issubset(df.columns):
        adx = adx14(df["high"].astype(float), df["low"].astype(float), close)
    else:
        adx = None
        notes.append("缺 high/low，ADX 不可算")
    if "volume" in df.columns and df["volume"].notna().sum() >= 20:
        vol = df["volume"].astype(float)
        vol_ok = bool(vol.rolling(5).mean().iloc[-1] > vol.rolling(20).mean().iloc[-1])
    else:
        vol_ok = None
        notes.append("缺 volume，量能确认不可算")
    row: dict = {
        "close": _fmt(float(close.iloc[-1]), 4),
        "rv20_ann": _fmt(realized_vol(close), 4),
        "rv_pct": _fmt(realized_vol_percentile(close), 4),
        "mom_121": _fmt(momentum_skip(close), 4),
        "mom_20": _fmt(momentum_plain(close), 4),
        "adx14": _fmt(adx, 2),
        "vol_ok": vol_ok,
    }
    if len(close) >= 120:
        ema120 = close.ewm(span=120, adjust=False).mean().iloc[-1]
        ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
        row["above_ema20"] = bool(close.iloc[-1] > ema20)
        row["above_ema120"] = bool(close.iloc[-1] > ema120)
    else:
        row["above_ema20"] = None
        row["above_ema120"] = None
        notes.append("历史<120日，EMA 状态未知")

    if row["rv_pct"] is None:
        notes.append(f"RV 分位留痕中（需≥{RV_RANK_MIN} 日）")
    if row["mom_121"] is None:
        notes.append(f"12-1 动量留痕中（需≥{MOM_LONG + 1} 日）")

    as_of = df.index[-1]
    row["as_of"] = str(pd.Timestamp(as_of).date())
    if now is not None:
        age = (now.date() - pd.Timestamp(as_of).date()).days
        if age > STALE_DAYS:
            notes.append(f"数据较旧（截止 {row['as_of']}，已 {age} 天）")
    row["notes"] = notes
    return row


def _group_percentile(rows: list[dict]) -> None:
    """同组内 mom_20 截面分位（反向警示用）。组内 <3 只不排名。"""
    for group in ("cn", "us", "sector"):
        idx = [i for i, r in enumerate(rows) if r["group"] == group and r.get("mom_20") is not None]
        if len(idx) < 3:
            for i in idx:
                rows[i]["mom_20_group_pct"] = None
                rows[i]["group_pct_note"] = "组内样本<3，不排名"
            continue
        vals = sorted(rows[i]["mom_20"] for i in idx)  # type: ignore[misc]
        n = len(vals)
        for i in idx:
            v = rows[i]["mom_20"]
            rank = sum(1 for x in vals if x <= v)  # 同值并列取保守高名次
            rows[i]["mom_20_group_pct"] = round(rank / n, 4)


def build_panel(cache_dir: Path | None = None, name_map: dict[str, str] | None = None,
                now: datetime | None = None) -> dict:
    """扫描 K 线缓存 → 因子面板快照（原子落盘）。"""
    root = Path(cache_dir) if cache_dir else ROOT
    now = now or datetime.now()
    name_map = name_map or {}

    rows: list[dict] = []
    skipped: list[str] = []
    sector_closes: dict[str, pd.Series] = {}
    for f in sorted(root.glob("*.bars.parquet")):
        code = f.name.split(".bars.parquet")[0]
        try:
            df = pd.read_parquet(f)
        except Exception as exc:  # noqa: BLE001 —— 单文件损坏不拖垮整面板，进 warnings
            logger.warning("因子面板读取失败 %s: %s", code, exc)
            skipped.append(code)
            continue
        if len(df) < MIN_BARS:
            skipped.append(code)
            continue
        group, subgroup = classify_symbol(code)
        if group == "sector":
            sector_closes[code] = df["close"].astype(float)
        row = compute_symbol_factors(df, now=now)
        row.update({
            "code": code,
            "name": name_map.get(code),
            "group": group,
            "subgroup": subgroup,
        })
        rows.append(row)

    # 市场 RV 分位（20 板块等权日收益口径，环境层指标）——LEI 信号对账显示其
    # 比标的自身 RV 更能预测信号质量（市场高波期信号 60 日均值 4.98%→0.73%）。
    market: dict[str, float | str | None] = {
        "market_rv_pct": None,
        "market_rv20_ann": None,
        "market_as_of": None,
        "market_basis": "板块等权日收益（缓存内板块合成指数）",
    }
    if len(sector_closes) >= 3:
        sec = pd.DataFrame(sector_closes).ffill()
        mkt_eq = (1.0 + sec.pct_change().mean(axis=1)).cumprod()
        market["market_rv_pct"] = _fmt(realized_vol_percentile(mkt_eq), 4)
        market["market_rv20_ann"] = _fmt(realized_vol(mkt_eq), 4)
        market["market_as_of"] = str(pd.Timestamp(sec.index[-1]).date())

    _group_percentile(rows)

    sectors = [r for r in rows if r["group"] == "sector"]
    sectors.sort(key=lambda r: (r["mom_121"] is None, -(r["mom_121"] or 0.0), r["code"]))
    rank = 0
    for r in sectors:
        if r["mom_121"] is not None:
            rank += 1
            r["mom_121_rank"] = rank
        else:
            r["mom_121_rank"] = None
    symbols = [r for r in rows if r["group"] != "sector"]
    _ORDER = {"cn_etf": 0, "cn_index": 1, "cn_stock": 2, "us_etf": 3, "us_index": 4}
    symbols.sort(key=lambda r: (_ORDER.get(r["subgroup"], 9), r["code"]))

    snapshot = {
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "provenance": "research_proxy",
        "research_proxy_note": RESEARCH_PROXY_NOTE,
        "study_date": STUDY_DATE,
        "study_ref": STUDY_REF,
        "data_as_of": max((r["as_of"] for r in rows), default=None),
        "counts": {
            "symbols": len(symbols),
            "sectors": len(sectors),
            "skipped_too_short_or_broken": skipped,
        },
        "market": market,
        "factors": FACTOR_META,
        "symbols": symbols,
        "sectors": sectors,
    }
    _save_atomic(snapshot, _panel_path())
    logger.info("因子面板快照落盘：%d 标的 / %d 板块（跳过 %d）",
                len(symbols), len(sectors), len(skipped))
    return snapshot


def _save_atomic(payload: dict, path: Path) -> None:
    """照抄 sector_trend._save_atomic 的 tmp.replace(p) 原子写（红线 8）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    tmp.replace(path)


def load_panel() -> dict | None:
    p = _panel_path()
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("因子面板快照读取失败: %s", exc)
        return None


__all__ = [
    "FACTOR_META",
    "RESEARCH_PROXY_NOTE",
    "STUDY_DATE",
    "STUDY_REF",
    "adx14",
    "build_panel",
    "classify_symbol",
    "compute_symbol_factors",
    "load_panel",
    "momentum_plain",
    "momentum_skip",
    "realized_vol",
    "realized_vol_percentile",
]
