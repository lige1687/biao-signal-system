"""机会侦察（opportunity scout）：主动扫全场，聚合三类当下机会。

用户口径（2026-09-07）：快捷功能「看看最近机会」——发掘当下比较好的
几个机会：有趋势信号的、下跌途中进入埋伏区的、其他（情绪信号）。

三类来源全部是既有基建的直读（无新判定）：
1. 趋势信号机会：当日扫描表 actionable/waiting 标的（技术判定层产出）；
2. 埋伏机会：自选标的中「形态=下跌型 且 现价距筹码价值区下沿 ≤5%」
   （已跌穿=可启动埋伏；接近=候埋伏）——触发口径来自 ambush 系列验证
   （跌穿 VAL×1.02，10/10 全胜）；退出菜单与胜率引用经验索引；
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
                    f"{state}（价值区下沿 {val:.3f}，现价 {close:.3f}；"
                    "触发口径：跌穿密集区下沿埋伏，历史 10/10 全胜且投入省半）"
                ),
            })
        except Exception:  # noqa: BLE001 — 单标的失败跳过
            continue
    return out[:5]


def scout_sentiment() -> list[dict]:
    """情绪信号机会状态（冰点环境/热警报，alerts 同源轻量版）。"""
    try:
        from lei_signal.market_context import market_mood as mm

        cn = mm.cn_mood() or {}
        out = []
        if str(cn.get("state")) == "cold":
            out.append({
                "kind": "sentiment", "kind_cn": "冰点机会（激活）",
                "detail_cn": "全A三票冰点——冰点机会信号前提成立（历史10日超额+6~8%、154例92%同向）",
            })
        heat = mm.sector_heat_boards() or {}
        boards = heat.get("boards") or []
        if boards:
            for b in boards:
                if str(b.get("signal") or "") in ("heat_alarm", "strong_heat_alarm"):
                    out.append({
                        "kind": "sentiment", "kind_cn": f"散户热警报：{b.get('name','')}",
                        "detail_cn": "全面强势板块散户涌入（历史29例无一幸免）——风险提示非机会",
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
