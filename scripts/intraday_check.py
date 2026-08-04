"""LEI 监督员 · 盘中快照判定（14:45 触发）。

人类决策（2026-08-04）：14:45 用盘中价跑判定，触发了就推，没触发不推。
不等收盘确认（收盘后操作不了）。其他时间不通知。

**这是对规格 §3.2「t 收盘后生成信号，t+1 开盘执行」的偏离**，人类已确认并接受风险：
规则基于收盘价设计，14:45 盘中价可能误触发（14:45 跌破但收盘拉回）。
代价是换得 15 分钟执行窗口。

设计：
- **只读判定**：跑 evaluate_plan，有 actionable alert 就推，不碰 DB（不同步待办、
  不催办）。待办同步与催办仍由 daily_nag 在收盘后做。两者不冲突。
- **虚拟今日 bar**：取截至昨日的日线 + 今日盘中价（腾讯实时报价）构造虚拟 bar，
  追加后跑 analyze_bars。所有指标（ema/sma/atr）用截至昨日的日线算，
  只有当日 close 用 14:45 盘中价。
- **actionable_from 仍是 next_trading_day**（保守：如今天未执行，明日开盘仍可）。
  通知文案标注「基于 14:45 盘中价，非收盘价」。
- **只推 actionable**（block/remind 且 action_kind 非空）：EXIT_TRIGGERED、
  INVALIDATION_BREACHED、ENTRY_CONDITIONS_MET。hint 级不推。

用法：
    python3 scripts/intraday_check.py [--symbols 600519.SS,...] [--dry-run] [--db lab.db]
不指定 --symbols 时取所有有 armed/entered 计划的标的。
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from lei_signal.api.config import sqlite_path  # noqa: E402
from lei_signal.api.quotes import TencentQuoteProvider  # noqa: E402
from lei_signal.compose.pipeline import analyze_bars  # noqa: E402
from lei_signal.data.providers import default_provider  # noqa: E402
from lei_signal.data.validation import DataUnavailableError  # noqa: E402
from lei_signal.plans.context import context_from_result  # noqa: E402
from lei_signal.plans.grounding import template_render, verify_grounding  # noqa: E402
from lei_signal.plans.monitor import INVALIDATION_BREACHED, evaluate_plan  # noqa: E402
from lei_signal.plans.store import list_plans  # noqa: E402
from lei_signal.storage.sqlite_store import connect  # noqa: E402

#: 只推 actionable（block/remind 且有 action_kind）。hint 级不推。
_ACTIONABLE_SEVERITIES = ("block", "remind")


def _filter_actionable(alerts: list) -> list:
    """过滤出该推送的 alert：block/remind 且（有 action_kind 或失效价击穿）。

    失效价击穿在 armed 时 action_kind=None（还没进场不需 EXIT 待办），
    但它是「计划失效」信号，用户必须知道。
    阻断（ENTRY_BLOCKED_BY_TRADABILITY, action_kind=None）不推--
    用户说「没触发就不推」，阻断不是「该买/该卖」的触发。
    """
    return [
        a for a in alerts
        if a.severity in _ACTIONABLE_SEVERITIES
        and (a.action_kind or a.code == INVALIDATION_BREACHED)
    ]


def _fetch_intraday_bars(symbol: str, quote_provider: TencentQuoteProvider) -> pd.DataFrame:
    """取截至昨日的日线 + 今日盘中虚拟 bar。

    虚拟 bar 用腾讯实时报价的 open/high/low/price 构造。
    指标（ema/sma/atr）用截至昨日的日线算，只有当日 close 用 14:45 盘中价。
    """
    provider = default_provider()
    price_data = provider.fetch(symbol, min_rows=21)
    bars = price_data.bars.copy()

    # 取盘中报价
    quote = quote_provider.fetch(symbol)
    if quote is None or quote.price is None:
        raise DataUnavailableError(f"{symbol} 盘中报价不可用")

    # 截掉今日未完成 bar（如果日线源返回了今日）
    today = pd.Timestamp.now().normalize()
    if not bars.empty and bars.index[-1].date() == today.date():
        bars = bars.iloc[:-1]

    # 构造虚拟今日 bar
    price = float(quote.price)
    virtual = pd.DataFrame(
        {
            "open": [float(quote.open) if quote.open is not None else price],
            "high": [float(quote.high) if quote.high is not None else price],
            "low": [float(quote.low) if quote.low is not None else price],
            "close": [price],
            "volume": [0.0],  # 盘中 volume 不影响 close-based 判定
        },
        index=[today],
    )
    return pd.concat([bars, virtual])


def _notify(title: str, body: str, *, dry_run: bool = False) -> None:
    if dry_run:
        print(f"[dry-run] {title}: {body}")
        return
    import subprocess
    for cmd in (
        ["terminal-notifier", "-title", title, "-message", body],
        ["osascript", "-e", f'display notification "{body}" with title "{title}"'],
    ):
        try:
            subprocess.run(cmd, check=False, timeout=5)  # noqa: S603
            return
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue


def run_intraday_check(
    symbols: list[str],
    *,
    db_path: str | None = None,
    dry_run: bool = False,
) -> int:
    """14:45 盘中快照判定。有 actionable alert 就推，没有就不推。返回推送条数。"""
    path = db_path or os.environ.get("LEI_SQLITE_PATH") or str(sqlite_path())
    conn = connect(path)
    quote_provider = TencentQuoteProvider()
    pushed = 0
    try:
        for symbol in symbols:
            try:
                bars = _fetch_intraday_bars(symbol, quote_provider)
            except Exception as exc:  # noqa: BLE001
                print(f"[{symbol}] 取数失败：{exc}", file=sys.stderr)
                continue

            result = analyze_bars(symbol, bars)
            ctx = context_from_result(result, cache_fallback_used=False)

            for plan in list_plans(conn, symbol=symbol):
                if plan.state not in ("armed", "entered"):
                    continue
                alerts = evaluate_plan(plan, ctx)
                # 只推 actionable：block/remind 且（有 action_kind 或失效价击穿）。
                # 失效价击穿在 armed 时 action_kind=None（还没进场不需 EXIT 待办），
                # 但它是「计划失效」信号，用户必须知道。
                # 阻断（ENTRY_BLOCKED_BY_TRADABILITY, action_kind=None）不推——
                # 用户说「没触发就不推」，阻断不是「该买/该卖」的触发。
                actionable = _filter_actionable(alerts)
                if not actionable:
                    continue

                pushed += 1
                intraday_price = ctx.current_close
                text = template_render(
                    actionable, plan=plan,
                    context_min={
                        "last_bar_date": ctx.last_bar_date,
                        "provider": "tencent_intraday_14:45",
                        "cache_fallback_used": False,
                        "intraday_snapshot": True,
                        "intraday_price": intraday_price,
                    },
                )
                # 接地校验：盘中推送也要过白名单
                allowed = {a.rule_id for a in actionable if a.rule_id}
                ok, _ = verify_grounding(text, allowed)
                if not ok:
                    text = template_render(actionable, plan=plan)

                body = (
                    f"盘中快照（14:45 价 {intraday_price:.2f}，非收盘价）：\n"
                    + text[:500]
                )
                _notify(f"LEI 监督员 · {symbol}", body, dry_run=dry_run)
                print(f"[{symbol}] 推送 {len(actionable)} 条 actionable alert")
    finally:
        conn.close()
    return pushed


def _symbols_with_active_plans(db_path: str) -> list[str]:
    conn = connect(db_path)
    try:
        symbols = sorted({
            p.symbol for p in list_plans(conn)
            if p.state in ("armed", "entered")
        })
    finally:
        conn.close()
    return symbols


def main() -> int:
    parser = argparse.ArgumentParser(description="LEI 监督员 14:45 盘中快照判定")
    parser.add_argument("--symbols", help="逗号分隔标的；不指定则取有 armed/entered 计划的标的")
    parser.add_argument("--dry-run", action="store_true", help="不弹通知，只打印")
    parser.add_argument("--db", help="SQLite 路径")
    args = parser.parse_args()

    db = args.db or os.environ.get("LEI_SQLITE_PATH") or str(sqlite_path())
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    else:
        symbols = _symbols_with_active_plans(db)

    if not symbols:
        print("无标的（无 armed/entered 计划且未指定 --symbols）")
        return 0
    pushed = run_intraday_check(symbols, db_path=db, dry_run=args.dry_run)
    print(f"完成：推送 {pushed} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
