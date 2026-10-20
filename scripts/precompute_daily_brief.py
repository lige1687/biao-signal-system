#!/usr/bin/env python3
"""收盘简报预计算（14:45 盘中预判版 / 16:45 收盘复核版）。

流程（全部复用既有确定性链路，判定权在 Python）：
  1. 环境异常：A/美宽度历史分位 + 宏观背景一行（两融/VIX/中美利差）；
  2. 自选重点变化：机会扫描 verdict 档位 × 与上一份简报的状态 diff；
  3. 板块观察池：/sectors 快照（临近升级/资金印证/动能前五）+ 连续天数；
  4. LLM 表达层（可选，--no-llm 跳过）→ 禁用词校验 → 模板降级兜底；
  5. 原子写 {LEI_CACHE_ROOT}/daily_brief/YYYY-MM-DD.json 的对应槽位。

用法：
  python3 scripts/precompute_daily_brief.py               # 槽位按当前时间自动判定
  python3 scripts/precompute_daily_brief.py --slot 1445   # 强制盘中预判版
  python3 scripts/precompute_daily_brief.py --slot 1645 --no-llm
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from lei_signal import dailybrief as db  # noqa: E402
from lei_signal.env import load_env  # noqa: E402
from lei_signal.market_context import sector_trend as st  # noqa: E402

# .env 里的表达层 LLM 凭据（DEEPSEEK_*）与 API 进程同口径注入
load_env()

logger = logging.getLogger("daily_brief")


def _auto_slot(now: datetime) -> str:
    minutes = now.hour * 60 + now.minute
    return db.SLOT_INTRADAY if minutes < 15 * 60 + 30 else db.SLOT_CLOSE


def _load_json(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:  # noqa: BLE001 - 缺数按空处理，不阻断简报
        return []


def _macro_line() -> dict:
    """宏观背景一行（两融/VIX/中美利差）。失败返回空（不冒充）。"""
    try:
        from lei_signal.fundamentals.service import FundamentalsService

        rates = FundamentalsService().rates() or {}
    except Exception as exc:  # noqa: BLE001
        logger.warning("宏观背景取数失败（留空）: %s", exc)
        return {}
    margin = rates.get("margin") or {}
    vix = rates.get("vix") or {}
    treasury = rates.get("treasury") or {}
    spread = treasury.get("cn_us_spread_10y")
    parts: list[str] = []
    if margin.get("rzye_yi") is not None:
        parts.append(f"两融 {margin['rzye_yi']:.0f}亿（{margin.get('date', '-')}）")
    if vix.get("value") is not None:
        parts.append(f"VIX {vix['value']:.1f}")
    if spread is not None:
        parts.append(f"中美10Y利差 {spread:+.2f}pct")
    return {
        "line_cn": " · ".join(parts),
        "raw": {k: rates.get(k) for k in ("margin", "vix")} | {"cn_us_spread_10y": spread},
    }


def _build_env() -> dict:
    a_hist = _load_json(db.ROOT / "a_share_ma_breadth_history.json")
    us_hist = _load_json(db.ROOT / "sp500_ma_breadth_history.json")
    anomalies, context = db.detect_breadth_anomalies(a_hist, us_hist)
    return {
        "anomalies": anomalies,
        "breadth_context": context,
        "macro": _macro_line(),
    }


def _build_watchlist(day: str, slot: str) -> dict:
    from contextlib import closing

    from lei_signal.api.config import sqlite_path
    from lei_signal.api.opportunity_scan import today_date  # noqa: F401 - 语义参照
    from lei_signal.api.routes.opportunities import run_opportunity_scan
    from lei_signal.api.services import AnalysisService
    from lei_signal.api.watchlist import list_watchlist
    from lei_signal.storage.sqlite_store import connect

    db_path = os.environ.get("LEI_SQLITE_PATH") or str(sqlite_path())
    with closing(connect(db_path)) as conn:
        all_items = list_watchlist(conn)
    stocks = [it for it in all_items if not it.symbol.endswith(".SECTOR")]
    n_sector_items = len(all_items) - len(stocks)
    if not stocks:
        return {"items": [], "unchanged_count": 0, "sector_watch_count": n_sector_items}

    service = AnalysisService(max_workers=8)
    # 串行预热 V8（照抄 daily_scan：mini_racer 并发初始化会崩）
    service.get(stocks[0].symbol, refresh=True)
    scan = run_opportunity_scan(
        service, db_path, symbols=[it.symbol for it in stocks],
        refresh=True, only_with_candidates=False,
    )
    verdicts = {it.symbol: (it.verdict, it.verdict_cn) for it in scan.items}

    baseline = db.load_baseline_before(day, slot)
    prev_states: dict[str, dict] = {}
    if baseline:
        for it in (baseline.get("watchlist") or {}).get("items") or []:
            if it.get("state"):
                prev_states[it["symbol"]] = it["state"]

    items: list[dict] = []
    for wit in stocks:
        entry = service.get(wit.symbol)
        if entry.result is None:
            items.append({
                "symbol": wit.symbol, "display_name": wit.display_name or wit.symbol,
                "verdict": "none", "verdict_cn": "数据不可用",
                "changes": [f"分析失败：{(entry.error or '')[:60]}"],
                "n_changes": 1, "is_new": False, "state": None,
            })
            continue
        state = db.extract_symbol_state(entry.result.assessment)
        diff = db.diff_symbol_state(prev_states.get(wit.symbol), state)
        verdict, verdict_cn = verdicts.get(wit.symbol, ("none", ""))
        items.append({
            "symbol": wit.symbol,
            "display_name": wit.display_name or wit.symbol,
            "verdict": verdict,
            "verdict_cn": verdict_cn or verdict,
            "changes": diff["changes"],
            "n_changes": diff["n_changes"],
            "is_new": diff["is_new"],
            "state": state,
        })
    items = db.rank_watchlist_changes(items)
    unchanged = sum(1 for it in items if not it["n_changes"] and not it["is_new"])
    return {
        "items": items,
        "unchanged_count": unchanged,
        "sector_watch_count": n_sector_items,
    }


def _build_pool(day: str, slot: str) -> dict:
    import datetime as _dt

    today_pool = db.today_sector_pool(st.load_snapshot())
    recent: list[dict] = []
    try:
        cur = _dt.date.fromisoformat(day)
    except ValueError:
        cur = _dt.date.today()
    for i in range(1, db.POOL_LOOKBACK + 1):
        prev_day = (cur - _dt.timedelta(days=i)).isoformat()
        doc = db.load_brief(prev_day)
        if not doc:
            continue
        for s in ("1645", "1445"):
            v = doc.get("versions", {}).get(s)
            if v:
                codes = [it.get("code") for it in (v.get("pool") or {}).get("items") or []]
                recent.append({"codes": [c for c in codes if c]})
                break
    streaks = db.pool_streaks(today_pool, recent)
    items = sorted(
        today_pool.values(),
        key=lambda it: (-streaks.get(it["code"], 1), -(it.get("rs_pctile") or 0)),
    )
    for it in items:
        it["streak"] = streaks.get(it["code"], 1)
    return {"items": items, "codes": [it["code"] for it in items]}


def main() -> int:
    parser = argparse.ArgumentParser(description="收盘简报预计算（14:45/16:45）")
    parser.add_argument("--slot", choices=("auto", db.SLOT_INTRADAY, db.SLOT_CLOSE), default="auto")
    parser.add_argument("--no-llm", action="store_true", help="跳过 LLM 表达层，只用模板")
    parser.add_argument("--date", help="YYYY-MM-DD（默认今天，调试用）")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    now = datetime.now()
    day = args.date or now.date().isoformat()
    slot = _auto_slot(now) if args.slot == "auto" else args.slot

    payload: dict = {
        "date": day,
        "slot": slot,
        "generated_at": now.strftime("%Y-%m-%d %H:%M"),
        "env": _build_env(),
        "watchlist": _build_watchlist(day, slot),
        "pool": _build_pool(day, slot),
    }

    generated_by = "template"
    summary_text = db.render_template(payload)
    if not args.no_llm:
        try:
            from lei_signal.plans.llm import load_ark_config

            config = load_ark_config()
            if config is not None:
                # LLM 只需要展示字段：剥掉 diff 用的内部 state 与 codes，缩载荷防超时
                llm_payload = {
                    **payload,
                    "watchlist": {
                        **payload["watchlist"],
                        "items": [
                            {k: v for k, v in it.items() if k != "state"}
                            for it in payload["watchlist"]["items"]
                        ],
                    },
                    "pool": {k: v for k, v in payload["pool"].items() if k != "codes"},
                }
                llm_out = db.summarize_with_llm(llm_payload, config)
                if llm_out:
                    summary_text = llm_out
                    generated_by = "llm"
        except Exception as exc:  # noqa: BLE001 - LLM 环境问题不阻断
            logger.warning("LLM 配置不可用（走模板）: %s", exc)
    payload["summary"] = {"text": summary_text, "generated_by": generated_by}

    db.save_brief_version(day, slot, payload)
    print(summary_text)
    print(f"\n✓ 已落盘 daily_brief/{day}.json [{slot}] · 表达层={generated_by}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
