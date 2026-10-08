"""Compare qualified briefing facts for a low-noise, read-only notification trial.

State records observations, not message delivery. Durable event files are written
before state changes so a failed chat run can recover the prepared report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from uuid import uuid4


def _digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def extract_facts(packet: dict) -> dict:
    facts = {}

    def add(key: str, category: str, title: str, value, evidence=None):
        facts[key] = {
            "category": category,
            "title": title,
            "value": deepcopy(value),
            "fingerprint": _digest(value),
            "evidence": deepcopy(evidence),
        }

    statuses = packet.get("source_status", {})
    for name, source in statuses.items():
        if name in {"news", "news_status"}:
            continue
        label = {
            "workspace": "持仓",
            "plans": "交易计划",
            "trades": "成交台账",
            "cn": "国内基本面",
            "us": "海外基本面",
            "user_context": "补充交易理由",
        }.get(name, "系统")
        add(f"source:{name}", "system", f"{label}资料读取状态变化", bool(source.get("ok")), source)

    # Free bytes/time are evidence only. Warn on stable capacity/volume status
    # transitions, not on every write. Absent old-packet fields are not recovery.
    health = packet.get("storage_health") or {}
    for name, label in (("internal", "内置盘"), ("external", "外接盘")):
        disk = health.get(name) or {}
        if disk.get("status"):
            add(
                f"storage:{name}",
                "system",
                f"{label}运行存储状态变化",
                disk["status"],
                {
                    "checked_at": health.get("checked_at"),
                    "reasons": health.get("reasons"),
                    "disk": disk,
                    "note": "容量检查不修改交易记录，不代表全系统写入已受控。",
                },
            )

    # Source-authored quality status only; a date gap alone is not an outage.
    for market, source in packet.get("market_background", {}).items():
        if not source.get("ok"):
            continue
        for item in (source.get("data") or {}).get("items", []):
            if item.get("metric_id") and item.get("quality_status"):
                add(
                    f"quality:{market}:{item['metric_id']}",
                    "data_quality",
                    f"{item.get('label', item['metric_id'])}资料资格变化",
                    item["quality_status"],
                    {
                        key: item.get(key)
                        for key in ("quality_reason", "observation_date", "source_url")
                    },
                )

    news = packet.get("news_coverage", {}).get("last_run") or {}
    for name in news.get("per_source", {}):
        add(
            f"news:{name}",
            "system",
            "新闻来源状态变化",
            "ok",
            {"source": name, "checked_at": news.get("finished_at")},
        )
    for error in news.get("errors", []):
        name = error.get("source", "unknown")
        add(
            f"news:{name}",
            "system",
            "新闻来源状态变化",
            "failed",
            {**error, "checked_at": news.get("finished_at")},
        )

    holdings = packet.get("holdings", [])
    if statuses.get("workspace", {}).get("ok") and packet.get("coverage", {}).get("total") == len(
        holdings
    ):
        add(
            "membership",
            "holding_record",
            "系统持仓清单变化",
            sorted(x["holding_id"] for x in holdings),
            {"note": "清单变化不等于已发生交易；金额与份额仍须对账。"},
        )
        for row in holdings:
            value = row.get("facts", {})
            add(
                f"gaps:{row['holding_id']}",
                "data_quality",
                f"{row.get('display_name') or row.get('name') or '名称未知'}资料缺口变化",
                sorted(value.get("gaps", [])),
                {"fund_code": row.get("code"), "holding_as_of": row.get("holding_as_of")},
            )

    # An unavailable/intraday plan is omitted, preserving the previous known
    # observation rather than inventing recovery or a disappeared stop warning.
    for row in packet.get("plan_review", []):
        plan = row.get("plan") or {}
        if (
            plan.get("state") != "entered"
            or row.get("gaps")
            or row.get("state") != "按系统原计划逐项复核"
        ):
            continue
        conditions = {
            key: plan.get(key)
            for key in (
                "plan_id",
                "stop_price",
                "take_profit_price",
                "target_b_price",
                "invalidation_price",
                "invalidation_criteria_cn",
                "stop_plan_cn",
                "take_profit_plan_cn",
                "watch_signal_rule_ids",
            )
        }
        alerts = row.get("system_alerts", [])
        conditions["alerts"] = sorted(
            {(str(x.get("code")), str(x.get("severity"))) for x in alerts}
        )
        add(
            f"plan:{plan['plan_id']}",
            "confirmed_plan",
            f"{row.get('display_name') or row.get('name') or '名称未知'}原计划条件变化",
            conditions,
            {
                "alerts": alerts,
                "note": "保留原data_as_of和actionable_from；不在本提醒新增买卖建议。",
            },
        )

    ledger = packet.get("trade_ledger", {})
    if ledger.get("available"):
        for trade in ledger.get("records", []):
            add(
                f"trade:{trade['trade_id']}",
                "trade_record",
                f"{trade.get('display_name') or '名称未知'}成交台账变化",
                trade,
                {"note": ledger.get("reconciliation_note")},
            )
    return facts


def compare(packet: dict, previous: dict | None = None) -> tuple[dict, dict]:
    now = datetime.fromisoformat(packet["generated_at"])
    if now.tzinfo is None:
        raise ValueError("packet timestamp must include a timezone")
    if previous is not None:
        if previous.get("schema_version") != 1:
            raise ValueError("unknown notification state; preserve it for inspection")
        if now < datetime.fromisoformat(previous["observed_at"]):
            raise ValueError("older packet cannot replace the latest observation")
    first = previous is None
    before = (previous or {}).get("facts", {})
    current = extract_facts(packet)
    events = []
    if not first:
        for key, value in current.items():
            prior = before.get(key)
            if prior is None or prior.get("fingerprint") != value["fingerprint"]:
                # New healthy sources or new clean holdings do not need a ping.
                if (
                    prior is None
                    and value["category"] in {"system", "data_quality"}
                    and value["value"] in (True, "ok", [])
                ):
                    continue
                events.append(
                    {
                        "event_id": _digest(
                            [key, value["fingerprint"], (prior or {}).get("fingerprint")]
                        ),
                        "fact_key": key,
                        "change": "new" if prior is None else "changed",
                        "before": prior,
                        "after": value,
                    }
                )
    state = {"schema_version": 1, "observed_at": now.isoformat(), "facts": {**before, **current}}
    result = {
        "schema_version": 1,
        "generated_at": now.isoformat(),
        "initial_baseline": first,
        "should_notify": bool(events),
        "events": events,
        "delivery_confirmed": False,
        "limits": [
            "仅比较系统已报告的事实，不计算新的交易条件。",
            "未核交易日历，不以日期间隔自行判断数据停止更新。",
            "第一次建立起点；历史缺口已知且未变化时不重复提醒。",
            "读取与准备提醒不等于已送达。",
        ],
    }
    return result, state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--state-dir", required=True, type=Path)
    parser.add_argument("--record-observation", action="store_true")
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text())
    state_path = args.state_dir / "state.json"
    previous = json.loads(state_path.read_text()) if state_path.exists() else None
    report, state = compare(packet, previous)
    args.state_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.fromisoformat(packet["generated_at"]).strftime("%Y%m%dT%H%M%S%f")
    report_path = args.state_dir / f"events-{stamp}-{uuid4().hex[:8]}.json"
    with report_path.open("x") as stream:
        json.dump(
            {**report, "source_packet": str(args.packet.resolve())},
            stream,
            ensure_ascii=False,
            indent=2,
        )
    if args.record_observation:
        temporary = args.state_dir / f"state-{uuid4().hex}.tmp"
        with temporary.open("x") as stream:
            json.dump(
                {**state, "prepared_report": str(report_path.resolve())},
                stream,
                ensure_ascii=False,
                indent=2,
            )
        temporary.replace(state_path)
    print(
        json.dumps(
            {
                "report": str(report_path.resolve()),
                "initial_baseline": report["initial_baseline"],
                "should_notify": report["should_notify"],
                "event_count": len(report["events"]),
                "observation_recorded": args.record_observation,
                "delivery_confirmed": False,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
