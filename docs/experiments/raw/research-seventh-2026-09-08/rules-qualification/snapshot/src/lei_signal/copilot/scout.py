"""机会侦察（opportunity scout）：主动扫全场，聚合三类当下机会。

用户口径（2026-09-07）：快捷功能「看看最近机会」——发掘当下比较好的
几个机会：有趋势信号的、下跌途中进入埋伏区的、其他（情绪信号）。

三类来源全部是既有基建的直读（无新判定）：
1. 趋势信号机会：当日扫描表 actionable/waiting 标的（技术判定层产出）；
2. 埋伏机会：自选标的中「形态=下跌型 且 现价距筹码价值区下沿 ≤5%」
   （已跌穿=可启动埋伏；接近=候埋伏）——触发口径为研究假设（个股层无
   归档回测背书，标注展示限制）；指数层埋伏模板见 dca 证据账本；
3. 情绪信号机会：冰点机会/热警报状态（sentiment alerts 同源）。

叙事标注层纪律：机会清单只聚合既有信号与已验证规则，不产生新信号；
每项带历史依据（winrate/经验索引），AI 讲解时接地校验照常生效。
"""
from __future__ import annotations

from typing import Any


def scout_trend(conn: Any) -> list[dict]:
    """趋势信号机会：当日扫描表 actionable/waiting（判定层直读）。"""
    from lei_signal.api.opportunity_scan import list_scan, today_date

    out = []
    for r in list_scan(conn, today_date()):
        if r.verdict not in ("actionable", "waiting"):
            continue
        out.append({
            "symbol": r.symbol,
            "display_name": r.display_name or r.symbol,
            "kind": "trend",
            "kind_cn": "趋势信号",
            "verdict_cn": r.verdict_cn,
            "detail_cn": (
                f"{r.verdict_cn}"
                + (f"，还缺：{r.missing_summary_cn}" if r.missing_summary_cn else "")
            ),
        })
    return out[:5]


def scout_ambush(symbols: list[str]) -> list[dict]:
    """埋伏机会：下跌型 × 现价距筹码价值区下沿 ≤5%（接近/已跌穿）。

    数据源用回测池 parquet 直读（毫秒级、内存可控）——不走分析服务：
    2026-09-07 真机教训，逐自选重分析曾把后端 OOM（SIGKILL -9）。
    形态与 VAL 均「截至最新一根」计算，无未来数据。
    """
    from pathlib import Path

    import pandas as pd

    from lei_signal.copilot.fit import classify_regime, measure_regime
    from lei_signal.features.volume_profile import compute_volume_profile

    pool = Path.home() / ".lei_signal_lab" / "backtest_pool"
    out = []
    for sym in symbols:
        f = pool / f"{sym}.bars.parquet"
        if not f.exists():
            continue
        try:
            df = pd.read_parquet(f)
            df.index = pd.to_datetime(df.index)
            frame = df.iloc[-400:]  # 取近400根：形态窗口250+筹码窗口120
            m = measure_regime(frame)
            regime = classify_regime(m)
            if regime != "downtrend":
                continue
            vp = compute_volume_profile(frame)
            if vp is None:
                continue
            close = float(frame["close"].iloc[-1])
            val = float(vp.val)
            dist = (close / val - 1) * 100  # <0 已跌穿；0~5 接近
            if dist > 5:
                continue
            state = "已跌穿埋伏区" if dist <= 2 else f"距埋伏区 {dist:.1f}%"
            out.append({
                "symbol": sym,
                "display_name": sym,
                "kind": "ambush",
                "kind_cn": "定投埋伏位",
                "verdict_cn": state,
                "detail_cn": (
                    f"{state}（价值区下沿 {val:.3f}，现价 {close:.3f}，"
                    f"数据截至 {frame.index[-1].date()}；"
                    "触发口径：跌穿筹码密集区下沿的研究假设——个股层暂无归档"
                    "回测背书，已归档的埋伏证据是指数层底部区域/惨档触发模板"
                    "（见 /api/dca/triggers），勿把本位当已验证机会）"
                ),
            })
        except Exception:  # noqa: BLE001 — 单标的失败跳过
            continue
    return out[:5]


def scout_sentiment() -> list[dict]:
    """情绪信号机会状态（冰点环境/热警报，alerts 同源轻量版）。

    数字引用对齐 configs/sentiment_evidence.json（2026-09-06 版）：
    - 冰点机会（CONFIRMED）：四个恐慌时期板块 15 日平均变化 +0.6%~+12.9%
      （时期平均为正，非每笔盈利；57%~94% 为各时期上涨板块占比）——
      完整四条件统计只贴在板块级四条件全部核实时；本卡只检测全市场
      三票冰点环境，须写「环境前提成立，板块条件待核实」；
    - 强热警报（DOWNGRADED 条件版）：历史结论分市场环境（转弱期/牛市期
      方向相反），本卡不判定当前市场环境——适用性未知，不给条件胜率。
    """
    try:
        from lei_signal.market_context import market_mood as mm

        cn = mm.cn_mood() or {}
        out = []
        if str(cn.get("state")) == "cold":
            out.append({
                "kind": "sentiment", "kind_cn": "冰点环境前提成立",
                "detail_cn": "全A三票冰点——冰点机会的环境前提成立；"
                             "板块级四条件（60日跌幅/散户流入强度/板块宽度）"
                             "尚未逐项核实，完整历史统计见证据账本，"
                             "不在本卡引用",
            })
        heat = mm.sector_heat_boards() or {}
        boards = heat.get("boards") or []
        if boards:
            for b in boards:
                if str(b.get("signal") or "") in ("heat_alarm", "strong_heat_alarm"):
                    out.append({
                        "kind": "sentiment", "kind_cn": f"散户热警报：{b.get('name','')}",
                        "detail_cn": "全面强势板块散户涌入——警报适用性与市场是否"
                                     "处于转弱期有关，当前环境未判定，适用性未知"
                                     "（条件版历史结论与边界见证据账本，不在本卡"
                                     "引用条件数字）；风险提示非机会",
                    })
        return out[:3]
    except Exception:  # noqa: BLE001
        return []


def scout(request: Any, conn: Any) -> dict:
    """聚合三类机会 + 各项历史胜率标注。"""
    from lei_signal.api.watchlist import list_watchlist
    from lei_signal.copilot import winrate as winrate_mod

    symbols = [w.symbol for w in list_watchlist(conn)]
    trend = scout_trend(conn)
    ambush = scout_ambush(symbols)
    sentiment = scout_sentiment()
    for item in ambush:
        try:
            from lei_signal.api.routes.agent import _static_symbol_name  # noqa: PLC0415

            item["display_name"] = _static_symbol_name(item["symbol"], "") or item["symbol"]
        except Exception:  # noqa: BLE001
            pass
    for item in trend + ambush:
        try:
            w = winrate_mod.winrate_for(item["symbol"])
            item["winrate_cn"] = (w or {}).get("winrate_cn")
        except Exception:  # noqa: BLE001
            item["winrate_cn"] = None
    has_any = bool(trend or ambush or sentiment)
    return {
        "available": has_any,
        "trend": trend,
        "ambush": ambush,
        "sentiment": sentiment,
        "note_cn": (
            "机会侦察：聚合既有信号与已验证规则（趋势信号/埋伏位/情绪信号），"
            "叙事参考层不构成买卖点；每项带历史依据"
        ),
    }


__all__ = ["scout"]
