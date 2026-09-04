"""季报穿透：拉每只基金最新前十大持仓 -> 市场暴露聚合。

红线遵守：穿透结果是「叙事标注层」——帮你认清基金实际买的是什么，
修正资产暴露认知；永不参与技术信号判定、不做硬过滤。
"""
from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from lei_signal.portfolio.funddata import fetch_top10_holdings
from lei_signal.portfolio.store import list_holdings

MARKET_CN = {"cn": "A股", "hk": "港股", "us": "美股", "other": "其他"}


def refresh_top10(conn: sqlite3.Connection) -> dict[str, int]:
    """全量刷新前十大持仓（每只基金只保留最新一期）。"""
    stats = {"fetched": 0, "empty": 0, "skipped": 0, "failed": 0}
    for h in list_holdings(conn):
        if not h.code:
            stats["skipped"] += 1
            continue
        try:
            result = fetch_top10_holdings(h.code)
        except Exception:  # noqa: BLE001 - 单只失败不中断批次
            stats["failed"] += 1
            continue
        if result is None:
            stats["empty"] += 1
            continue
        quarter, report_date, rows = result
        conn.execute(
            "DELETE FROM portfolio_fund_top10 WHERE holding_id = ?", (h.holding_id,)
        )
        conn.executemany(
            """
            INSERT OR REPLACE INTO portfolio_fund_top10
                (holding_id, report_quarter, report_date, stock_code,
                 stock_name, market, weight_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [(h.holding_id, quarter, report_date, r.stock_code, r.stock_name,
              r.market, r.weight_pct) for r in rows],
        )
        stats["fetched"] += 1
    conn.commit()
    return stats


@dataclass(slots=True)
class FundExposure:
    """单只基金的穿透结果（前十大口径，覆盖不完整是常态）。"""

    holding_id: str
    report_quarter: str
    top10_total_pct: float                  # 前十大合计占净值 %
    by_market_pct: dict[str, float] = field(default_factory=dict)  # 各市场占净值 %


def load_exposures(conn: sqlite3.Connection) -> dict[str, FundExposure]:
    """holding_id -> 前十大市场暴露。无数据的基金不在返回里。"""
    rows = conn.execute(
        """
        SELECT holding_id, report_quarter, market, weight_pct
        FROM portfolio_fund_top10
        """
    ).fetchall()
    agg: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    quarters: dict[str, str] = {}
    for r in rows:
        quarters[r["holding_id"]] = r["report_quarter"]
        agg[r["holding_id"]][r["market"]] += r["weight_pct"]
    out: dict[str, FundExposure] = {}
    for hid, by_market in agg.items():
        total = sum(by_market.values())
        out[hid] = FundExposure(
            holding_id=hid,
            report_quarter=quarters[hid],
            top10_total_pct=round(total, 1),
            by_market_pct={k: round(v, 1) for k, v in sorted(
                by_market.items(), key=lambda kv: -kv[1])},
        )
    return out


def group_real_market_share(
    exposures: dict[str, FundExposure],
    holdings_by_id: dict,
    group_holding_ids: list[str],
) -> dict[str, float] | None:
    """一组持仓穿透后的市场分布（按市值加权，只统计已穿透部分）。

    返回各市场在「已识别持仓内部」的占比（合计 100），供与名义分组对照。
    """
    sums: dict[str, float] = defaultdict(float)
    for hid in group_holding_ids:
        exp, h = exposures.get(hid), holdings_by_id.get(hid)
        if exp is None or h is None:
            continue
        for market, pct in exp.by_market_pct.items():
            sums[market] += h.market_value * pct / 100.0
    total = sum(sums.values())
    if total <= 0:
        return None
    return {k: round(v / total * 100, 1) for k, v in sorted(
        sums.items(), key=lambda kv: -kv[1])}


def load_sector_stages() -> dict[str, dict]:
    """读行业板块趋势冻结快照 -> {板块名: {stage, as_of}}。

    快照缺失/损坏时返回空 dict，调用方按「数据未就绪」降级。
    """
    candidates = [
        Path.home() / ".lei_signal_lab" / "cache" / "sector_trend_snapshot.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        out: dict[str, dict] = {}
        for b in data.get("boards", []):
            if b.get("stage"):
                out[b.get("name", "")] = {
                    "stage": b["stage"],
                    "rs_pctile": b.get("rs_pctile"),
                    "close": b.get("close"),
                }
        out["_as_of"] = data.get("as_of", "")  # type: ignore[assignment]
        return out
    return {}
