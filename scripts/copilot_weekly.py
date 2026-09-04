"""Agent 超级入口 · 周复盘跑批（每周日 20:00）。

组装上一完整 ISO 周的周复盘（复用 copilot.review，确定性零 LLM；GLM 叙事
由端点按需补），存 trade_reviews，并飞书+macOS 推送摘要。
"""
from __future__ import annotations

import argparse
import os
import sys
from contextlib import closing
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from lei_signal.env import load_env  # noqa: E402

load_env()

from lei_signal.api.config import sqlite_path  # noqa: E402
from lei_signal.api.opportunity_scan import today_date  # noqa: E402
from lei_signal.copilot import review as review_mod  # noqa: E402
from lei_signal.notify.base import NotificationPayload  # noqa: E402
from lei_signal.storage.sqlite_store import connect  # noqa: E402

import logging  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--db",
        default=os.environ.get("LEI_SQLITE_PATH") or str(sqlite_path()),
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    week_iso = review_mod.prev_iso_week(today_date())
    with closing(connect(args.db)) as conn:
        card = review_mod.build_weekly_review(conn, week_iso)
        review_mod.save_review(conn, card)
        conn.commit()
    body = "\n".join(
        f"【{s.heading_cn}】" + "；".join(s.lines[:3]) for s in card.sections
    )
    logging.info("周复盘已存证：%s（本周已实现 %.0f 元）",
                 week_iso, card.realized_pnl or 0.0)
    if not args.dry_run:
        from lei_signal.notify.feishu_webhook import FeishuWebhookNotifier
        from lei_signal.notify.macos import MacNotifier

        payload = NotificationPayload(
            title=f"LEI 周复盘 {week_iso}",
            body_md=body,
            tier=2,
            plan_id="copilot-weekly",
        )
        notifiers = [MacNotifier(dry_run=False)]
        if os.environ.get("FEISHU_WEBHOOK_URL"):
            notifiers.append(
                FeishuWebhookNotifier(
                    os.environ["FEISHU_WEBHOOK_URL"], dry_run=False
                )
            )
        for notifier in notifiers:
            try:
                notifier.send(payload)
            except Exception as exc:  # noqa: BLE001
                print(
                    f"[{type(notifier).__name__}] 投递失败：{exc}", file=sys.stderr
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
