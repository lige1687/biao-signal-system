"""每日操作清单组装（纯读，零 LLM）：页面与每日跑批推送共用。

五段：① 持仓要处理的（EXIT 类待办 + 组合 observations）
     ② 今日推荐（推荐账本当日存证，缺省 None）
     ③ 计划待办催办（open 待办，EXIT 优先）
     ④ 观察触发（当日扫描 waiting 项还缺什么）
     ⑤ 重大事件（客观字段 only，newsfeed 侧组装后传入）
"""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

from lei_signal.api.schemas import (
    MajorEventsBlockDTO,
    OpsCardDTO,
    OpsLineDTO,
    OpsTodoDTO,
    RecommendCardDTO,
)

_KIND_CN = {"ENTER": "入场", "EXIT": "退出", "REVIEW": "复核"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def build_ops_today(
    conn: sqlite3.Connection,
    *,
    run_date: str,
    recommend_card: RecommendCardDTO | None,
    major_events: dict | None = None,
) -> OpsCardDTO:
    rows = conn.execute(
        """SELECT a.action_id, a.plan_id, a.kind, a.due_from, a.nag_count,
                  p.symbol
           FROM plan_action_items a
           JOIN trade_plans p ON p.plan_id = a.plan_id
           WHERE a.state = 'open'
           ORDER BY CASE a.kind WHEN 'EXIT' THEN 0 WHEN 'ENTER' THEN 1 ELSE 2 END,
                    a.nag_count DESC"""
    ).fetchall()
    todos = [
        OpsTodoDTO(
            action_id=r["action_id"],
            plan_id=r["plan_id"],
            symbol=r["symbol"],
            kind=r["kind"],
            kind_cn=_KIND_CN.get(r["kind"], r["kind"]),
            next_step_cn="见计划卡（判定层已给出 next_step）",
            due_from=r["due_from"] or "",
            nag_count=int(r["nag_count"] or 0),
        )
        for r in rows
    ]
    holdings: list[OpsLineDTO] = [
        OpsLineDTO(
            symbol=t.symbol,
            text_cn=f"{t.kind_cn}待办（已催 {t.nag_count} 次）——按计划处理",
        )
        for t in todos
        if t.kind == "EXIT"
    ]
    obs_row = conn.execute(
        "SELECT value FROM portfolio_meta WHERE key = 'observations'"
    ).fetchone()
    if obs_row:
        try:
            for note in json.loads(obs_row["value"]) or []:
                if isinstance(note, str):
                    holdings.append(
                        OpsLineDTO(symbol="-", text_cn=f"组合提示：{note}")
                    )
        except (TypeError, ValueError):
            pass
    watch: list[OpsLineDTO] = []
    for r in conn.execute(
        "SELECT symbol, display_name, missing_summary_cn FROM "
        "daily_opportunity_scan WHERE scan_date = ? AND verdict = 'waiting'",
        (run_date,),
    ).fetchall():
        watch.append(OpsLineDTO(
            symbol=r["symbol"],
            display_name=r["display_name"] or r["symbol"],
            text_cn=(
                f"还缺：{r['missing_summary_cn'] or '条件未齐'}"
                "（条件成立即构成系统买点）"
            ),
        ))
    exit_n = sum(1 for t in todos if t.kind == "EXIT")
    enter_n = sum(1 for t in todos if t.kind == "ENTER")
    parts = []
    if exit_n:
        parts.append(f"{exit_n} 个退出待办（最优先）")
    if enter_n:
        parts.append(f"{enter_n} 个入场待办")
    if recommend_card and recommend_card.items:
        parts.append(f"今日推荐 {len(recommend_card.items)} 个标的")
    major_block = _build_major_events_block(major_events)
    if major_block and major_block.available:
        parts.append(f"重大事件 {len(major_block.items)} 条")
    summary = "；".join(parts) + "。" if parts else "今日无必须处理的待办。"
    return OpsCardDTO(
        run_date=run_date,
        generated_at=_now(),
        holdings_actions=holdings,
        recommendations=recommend_card,
        plan_todos=todos,
        watch_triggers=watch,
        sentiment=_build_sentiment_block(conn),
        major_events=major_block,
        push_summary_cn=summary,
    )


def _build_major_events_block(major_events: dict | None) -> MajorEventsBlockDTO | None:
    """重大事件区块：newsfeed service 的 major_events_brief 直转 DTO。

    传入 None（服务未就绪/未接）时区块整体缺省，页面不显示该段；
    客观字段 only 的口径在 service 层保证（无 llm_note）。
    """
    if not isinstance(major_events, dict):
        return None
    from lei_signal.api.schemas import MajorEventDTO

    items = [
        MajorEventDTO(
            title=str(it.get("title") or ""),
            category_cn=str(it.get("category_cn") or ""),
            direction_cn=str(it.get("direction_cn") or ""),
            importance=int(it.get("importance") or 0),
            when_cn=str(it.get("when_cn") or ""),
            published_at=str(it.get("published_at") or ""),
        )
        for it in (major_events.get("items") or [])
        if isinstance(it, dict)
    ]
    return MajorEventsBlockDTO(
        available=bool(major_events.get("available")),
        items=items,
        note_cn=str(major_events.get("note_cn") or ""),
    )


def _build_sentiment_block(conn: sqlite3.Connection):
    """情绪面区块：两融一句话 + 过热Top3 + 持仓赛道状态（只标注）。

    板块热度快照重建期 available=False，只回融资环境并提示累积中——
    措辞中性（偏热/冰点），不写方向性结论（红线见 handoff 文档 §4）。
    """
    from lei_signal.api.schemas import SentimentBlockDTO  # noqa: PLC0415
    from lei_signal.copilot import sentiment as sentiment_mod  # noqa: PLC0415
    from lei_signal.portfolio.advisor import GROUP_SECTORS  # noqa: PLC0415

    pack = sentiment_mod.load_sector_sentiment()
    by_board = pack.get("by_board") or {}
    name_index = {
        (rec.get("name") or ""): rec for rec in by_board.values()
        if isinstance(rec, dict)
    }
    margin = sentiment_mod.margin_regime_cn()
    hot = [
        {
            "name": b.get("name"),
            "heat_pctile": b.get("heat_pctile"),
            "stage_cn": b.get("stage_cn"),
        }
        for b in (pack.get("hot_boards") or [])[:3]
        if isinstance(b, dict)
    ]
    holdings_states: list[dict] = []
    for row in conn.execute(
        "SELECT group_key, name FROM portfolio_groups ORDER BY sort_order"
    ).fetchall():
        states = []
        for sector_name in GROUP_SECTORS.get(row["group_key"], []):
            rec = name_index.get(sector_name)
            if rec is not None:
                states.append(f"{sector_name}{rec.get('state_cn') or ''}")
        if states:
            holdings_states.append({
                "group_cn": row["name"],
                "state_cn": "；".join(states),
            })
    from lei_signal.copilot import breadth as breadth_mod  # noqa: PLC0415

    try:
        a_cn = breadth_mod.a_share_breadth_cn()
        u_cn = breadth_mod.us_breadth_cn()
    except Exception:  # noqa: BLE001
        a_cn = u_cn = None
    return SentimentBlockDTO(
        available=bool(pack.get("available")),
        margin_cn=(margin or {}).get("regime_cn", ""),
        margin_detail=margin,
        breadth_cn="；".join(x for x in (a_cn, u_cn) if x) or None,
        hot_boards=hot,
        holdings_states=holdings_states,
        note_cn=pack.get("note_cn", "") or (
            "情绪面：数据累积中（约需 20 个交易日资金流）"
            if not pack.get("available") else ""
        ),
    )
