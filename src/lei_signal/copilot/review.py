"""复盘组装：纪律面与结果面分开（监督员 v2 路线第 5 条的落地）。

纪律面全部直读 plans 库既有事实（预案原文、催办次数、推迟原因、复议记录），
不重跑判定、不做评价；结果面来自基金台账核算。R 倍数 = 实际盈亏 ÷ 初始风险额
（风险额 = 卖出金额 × |参考入场价 − 失效价| ÷ 参考入场价），仅有关联计划且
两价齐备时计算，否则明说不可算。
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from lei_signal.api.schemas import ReviewCardDTO, ReviewSectionDTO
from lei_signal.copilot import trades as trades_mod
from lei_signal.plans.store import get_plan


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _counts(conn: sqlite3.Connection, plan_id: str) -> dict[str, int]:
    def one(sql: str) -> int:
        row = conn.execute(sql, (plan_id,)).fetchone()
        return int(row[0]) if row else 0

    return {
        "nags": one(
            "SELECT COALESCE(SUM(nag_count),0) FROM plan_action_items "
            "WHERE plan_id = ?"
        ),
        "defers": one(
            "SELECT COUNT(*) FROM plan_annotations WHERE plan_id = ? "
            "AND kind = 'defer_reason'"
        ),
        "revisions": one(
            "SELECT COUNT(*) FROM trade_plan_revisions WHERE plan_id = ? "
            "AND revision_no > 0"
        ),
    }


def build_trade_review(
    conn: sqlite3.Connection, trade_id: str
) -> ReviewCardDTO | None:
    rows = trades_mod.list_trades(conn)
    trade = next((t for t in rows if t.trade_id == trade_id), None)
    if trade is None:
        return None
    pnl_info = trades_mod.realized_pnl_of(conn, trade_id)
    sections: list[ReviewSectionDTO] = []

    plan = get_plan(conn, trade.plan_id) if trade.plan_id else None
    if plan is not None:
        c = _counts(conn, plan.plan_id)
        sections.append(ReviewSectionDTO(
            heading_cn="当初怎么说的（纪律面）",
            lines=[
                f"入场理由：{plan.entry_rule_id or '-'}（模块 {plan.module}）",
                f"交易假设：{plan.thesis_cn or '-'}",
                f"失效标准：{plan.invalidation_criteria_cn or '-'}",
                "建计划时盈亏比参考："
                + (f"{plan.reward_risk_at_plan}" if plan.reward_risk_at_plan is not None
                   else "当时未算出"),
                f"催办 {c['nags']} 次、推迟 {c['defers']} 次、"
                f"修订 {c['revisions']} 次（都是监督留痕）",
            ],
        ))
    else:
        sections.append(ReviewSectionDTO(
            heading_cn="当初怎么说的（纪律面）",
            lines=["无关联计划——这笔是计划外操作，复盘时先问自己为什么没走计划流程。"],
        ))

    result_lines = [
        f"{trade.trade_date} {trade.side_cn} {trade.fund_name}"
        f"（{trade.fund_code}） {trade.amount:.0f} 元",
    ]
    if pnl_info.get("realized_pnl") is not None:
        result_lines.append(
            f"已实现盈亏 {pnl_info['realized_pnl']:+.0f} 元"
            f"（定价净值 {pnl_info['priced_nav']}）"
        )
    else:
        result_lines.append(
            "已实现盈亏：该笔未定价或非卖出，暂不可算（跑批补定价后再看）"
        )
    r_multiple: float | None = None
    if plan is not None and pnl_info.get("realized_pnl") is not None:
        entry = getattr(plan, "entry_price_ref", None)
        inv = getattr(plan, "invalidation_price", None)
        if entry and inv and entry > 0 and entry != inv:
            risk_amount = float(trade.amount) * abs(entry - inv) / entry
            if risk_amount > 0:
                r_multiple = pnl_info["realized_pnl"] / risk_amount
                result_lines.append(
                    f"R 倍数 {r_multiple:.2f}（大白话：当初准备亏的钱为 1 份，"
                    f"这笔结果等于 {r_multiple:.2f} 份）"
                )
    sections.append(ReviewSectionDTO(
        heading_cn="结果怎么样（结果面）", lines=result_lines,
    ))

    return ReviewCardDTO(
        review_id=f"rv_trade_{trade_id}",
        kind="trade",
        ref_key=trade_id,
        title_cn=f"单笔复盘 · {trade.fund_name} {trade.side_cn} {trade.trade_date}",
        sections=sections,
        r_multiple=r_multiple,
        realized_pnl=pnl_info.get("realized_pnl"),
    )


def save_review(conn: sqlite3.Connection, review: ReviewCardDTO) -> None:
    conn.execute(
        """INSERT INTO trade_reviews (review_id, kind, ref_key, payload,
                                      narrative, grounded, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?)
           ON CONFLICT(kind, ref_key) DO UPDATE SET
               payload = excluded.payload,
               narrative = excluded.narrative,
               grounded = excluded.grounded,
               updated_at = excluded.updated_at""",
        (review.review_id, review.kind, review.ref_key, review.model_dump_json(),
         review.narrative, int(review.grounded), _now(), _now()),
    )


def get_review(
    conn: sqlite3.Connection, kind: str, ref_key: str
) -> ReviewCardDTO | None:
    row = conn.execute(
        "SELECT payload FROM trade_reviews WHERE kind = ? AND ref_key = ?",
        (kind, ref_key),
    ).fetchone()
    if row is None:
        return None
    return ReviewCardDTO.model_validate_json(row["payload"])
