"""Agent 超级入口 · 每日跑批（16:10 收盘扫描之后触发）。

职责（顺序）：
1. 补定价 pending 基金成交（QDII T+1 次日补）。
2. 确保当日机会扫描落库（15:00 launchd 已跑；空表则现场重扫兜底）。
3. 组装今日推荐并存证 recommendation_journal（确定性，零 LLM）。
4. 组装 /ops 清单；有 EXIT/actionable 级事件时飞书+macOS 双通道推送
   （纯观察只亮红点不推，设计定稿 §E）。
5. 给历史推荐账本补 T+N 对账（score_journal_outcomes）。

判定权全部在既有规则层与 copilot 纯函数；本脚本只编排、落库、投递。
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from contextlib import closing

_PROJECT_ROOT = None


def _setup_path() -> None:
    global _PROJECT_ROOT
    from pathlib import Path

    _PROJECT_ROOT = Path(__file__).resolve().parents[1]
    if str(_PROJECT_ROOT / "src") not in sys.path:
        sys.path.insert(0, str(_PROJECT_ROOT / "src"))
    from lei_signal.env import load_env  # noqa: F401  仓库根 .env 注入（飞书/GLM 等）

    load_env()


def main() -> int:
    _setup_path()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--db",
        default=os.environ.get("LEI_SQLITE_PATH")
        or str(__import__("lei_signal.api.config", fromlist=["sqlite_path"]).sqlite_path()),
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )

    # 延迟 import：路径注入完成后才能导入 lei_signal
    from lei_signal.api.opportunity_scan import (
        list_scan,
        today_date,
        upsert_scan_results,
    )
    from lei_signal.api.routes.opportunities import (
        _row_to_scan_item,
        run_opportunity_scan,
    )
    from lei_signal.api.sectors_service import SectorsService
    from lei_signal.api.services import AnalysisService
    from lei_signal.copilot import journal, ops as ops_mod, trades as trades_mod
    from lei_signal.copilot.recommend import build_recommendation
    from lei_signal.newsfeed.service import NewsfeedService
    from lei_signal.notify.base import NotificationPayload
    from lei_signal.storage.sqlite_store import connect

    def _notifiers(dry_run: bool) -> list:
        from lei_signal.notify.feishu_webhook import FeishuWebhookNotifier
        from lei_signal.notify.macos import MacNotifier

        out = [MacNotifier(dry_run=dry_run)]
        url = os.environ.get("FEISHU_WEBHOOK_URL")
        if url:
            out.append(FeishuWebhookNotifier(url, dry_run=dry_run))
        return out

    service = AnalysisService(max_workers=8)
    db = args.db
    run_date = today_date()

    with closing(connect(db)) as conn:
        priced = trades_mod.price_pending_trades(conn)
        conn.commit()
    logging.info("补定价完成：%d 笔", priced)

    with closing(connect(db)) as conn:
        rows = list_scan(conn, run_date)
    if not rows:
        response = run_opportunity_scan(service, db)
        with closing(connect(db)) as conn:
            upsert_scan_results(conn, run_date, response.items)
            conn.commit()
        with closing(connect(db)) as conn:
            rows = list_scan(conn, run_date)
    scan_items = [_row_to_scan_item(r) for r in rows]

    sector_rows = None
    try:
        data = SectorsService().trend(refresh=False, level="l1")
        if isinstance(data, dict):
            sector_rows = next(
                (data[k] for k in ("sectors", "rows", "items")
                 if isinstance(data.get(k), list)),
                None,
            )
    except Exception:  # noqa: BLE001  快照缺席不阻断推荐
        sector_rows = None
    news_brief = None
    try:
        newsfeed_svc = NewsfeedService()
        news_brief = newsfeed_svc.watchlist_brief([], days=3) or None
    except Exception:  # noqa: BLE001
        newsfeed_svc = None
        news_brief = None
    major_events = None
    try:
        major_events = (
            newsfeed_svc.major_events_brief()
            if newsfeed_svc is not None else None
        )
    except Exception:  # noqa: BLE001
        major_events = None

    card = build_recommendation(
        scan_items, run_date=run_date,
        sector_rows=sector_rows, news_brief=news_brief,
    )
    with closing(connect(db)) as conn:
        if card.items:
            journal.save_recommendation(conn, card)
        ops_card = ops_mod.build_ops_today(
            conn, run_date=run_date, recommend_card=card,
            major_events=major_events,
        )
        scored = journal.score_journal_outcomes(conn, service)
        conn.commit()
    logging.info(
        "推荐 %d 项；对账补写 %d 日", len(card.items), scored
    )

    has_exit = any(t.kind == "EXIT" for t in ops_card.plan_todos)
    has_actionable = any(i.verdict == "actionable" for i in card.items)
    if (has_exit or has_actionable) and not args.dry_run:
        payload = NotificationPayload(
            title=f"LEI 今日操作（{run_date}）",
            body_md=(
                ops_card.push_summary_cn
                + "\n详情打开看板 /ops 页。退出待办最优先。"
            ),
            tier=1,
            plan_id="copilot-daily",
        )
        for notifier in _notifiers(args.dry_run):
            try:
                notifier.send(payload)
            except Exception as exc:  # noqa: BLE001
                print(
                    f"[{type(notifier).__name__}] 投递失败：{exc}", file=sys.stderr
                )
    else:
        logging.info(
            "无推送级事件（exit=%s actionable=%s）", has_exit, has_actionable
        )

    # 情绪信号推送（2026-09-06 用户口径：冰点+宽度的「入口外提醒」）——
    # 全A三票冰点环境出现即推（一天不等的黄金坑前提），宽度读数附上
    # 佐证；热警报在板块热度数据可用时自动扫描（数据重建期如实跳过）。
    try:
        _push_sentiment_signals(run_date, args.dry_run, _notifiers(args.dry_run))
    except Exception as exc:  # noqa: BLE001 — 情绪推送失败不阻断跑批
        print(f"[sentiment-push] 失败：{exc}", file=sys.stderr)
    return 0


def _push_sentiment_signals(run_date: str, dry_run: bool, notifiers) -> None:
    from lei_signal.notify.base import NotificationPayload

    from lei_signal.market_context import market_mood as mm

    cn = mm.cn_mood() or {}
    if str(cn.get("state")) != "cold":
        logging.info("情绪信号推送：全A非冰点（%s），无冰点级提醒", cn.get("state"))
        return
    breadth_note = ""
    try:
        from lei_signal.copilot import breadth as breadth_mod

        b = breadth_mod.a_share_breadth() or {}
        if b.get("available"):
            breadth_note = (
                f"\n宽度佐证：20日线上方 {b.get('ma20_pct', 0):.0f}%、"
                f"200日线上方 {b.get('ma200_pct', 0):.0f}%"
                f"（历史双≤20% 后 120 日 13/13 标的上涨）"
            )
    except Exception:  # noqa: BLE001
        breadth_note = ""
    heat = mm.sector_heat_boards() or {}
    boards = heat.get("boards") or []
    scan_note = (
        f"\n板块扫描：热度覆盖 {len(boards)} 个（冰点机会明细=深弱板块×"
        "散户逆势涌入，历史 10 日超额 +6~8%、154 例 92% 同向）"
        if boards else
        "\n板块热度数据重建中，冰点机会明细暂不可算——但环境本身已值得留意"
    )
    payload = NotificationPayload(
        title=f"❄ 情绪面·全A冰点环境出现（{run_date}）",
        body_md=(
            f"全A情绪三票冰点：{cn.get('state_cn') or '多数冷'}。"
            f"{breadth_note}{scan_note}"
            "\n\n*研究代理·叙事层信号，不构成买卖点；冰点机会需板块级"
            "四条件齐备，详情问 Agent 或看 /ops*"
        ),
        tier=1,
        plan_id="sentiment-icepoint",
    )
    for notifier in notifiers:
        try:
            notifier.send(payload)
        except Exception as exc:  # noqa: BLE001
            print(f"[{type(notifier).__name__}] 情绪推送失败：{exc}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
