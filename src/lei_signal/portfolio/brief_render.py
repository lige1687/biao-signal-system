"""Render a portfolio packet as a concise, deterministic Chinese Markdown brief."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from html import escape

_SOURCE_LABELS = {
    "workspace": "持仓资料",
    "plans": "交易计划",
    "trades": "成交记录",
    "cn": "国内市场背景",
    "us": "海外市场背景",
    "user_context": "补充记录",
    "news": "新闻资料",
    "news_status": "新闻更新状态",
}
_CHANGE_LABELS = {
    "nav_value": "净值变化",
    "nav_date": "净值日期变化",
    "status": "复核状态变化",
    "gaps": "待补资料变化",
    "plan_id": "关联计划变化",
    "plan_version": "计划版本变化",
    "plan": "计划资料变化",
    "technical": "技术资料变化",
    "alerts": "计划提示变化",
    "name": "名称资料变化",
    "code": "代码资料变化",
}
_QUALIFIED_PLAN = "按系统原计划逐项复核"
_QUALITY_LABELS = {
    "time_unverified": "资料发布时间或时效尚未核实",
    "missing": "资料缺失",
}


def _text(value, fallback="未提供") -> str:
    if value is None or value == "":
        return fallback
    return str(value).replace("\r", " ").replace("\n", " ").strip() or fallback


def _date_part(value) -> str:
    value = _text(value, "日期未知")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%Y-%m-%d %H:%M %z") if "T" in value else parsed.date().isoformat()
    except ValueError:
        return value


def _name(row: dict) -> str:
    code = str(row.get("code") or row.get("fund_code") or "").strip()
    for value in (row.get("display_name"), row.get("name"), row.get("fund_name")):
        name = _text(value, "")
        if name and name != code and name not in {"未知", "名称未知", "--"}:
            return name
    return "名称未知"


def _link(label, url) -> str:
    label = _text(label)
    url = str(url or "").strip()
    if url.startswith(("https://", "http://")):
        return f"[{label}]({url})"
    return f"{label}（链接未提供）"


def _format_number(value) -> str:
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return _text(value)


def _failure_lines(packet: dict) -> list[str]:
    failures = []
    for key, source in packet.get("source_status", {}).items():
        if source.get("ok") is False:
            failures.append(f"{_SOURCE_LABELS.get(key, '其他资料')}读取失败（详情保留在诊断记录）")
    for market, source in packet.get("market_background", {}).items():
        if source.get("ok") is False:
            label = "国内" if market == "cn" else "海外"
            failures.append(f"{label}市场背景读取失败（详情保留在诊断记录）")
    run = packet.get("news_coverage", {}).get("last_run") or {}
    authors = {str(x.get("mid")): x.get("name") for x in packet.get("configured_authors", [])}
    failed_news_sources = set()
    for error in run.get("errors", []):
        raw_source = str(error.get("source") or "").strip()
        kind, _, identity = raw_source.partition(":")
        source = authors.get(identity) or ("B站" if kind == "bilibili" else kind) or "未注明来源"
        failed_news_sources.add(source)
    for source in sorted(failed_news_sources):
        failures.append(f"新闻来源 {source} 有更新失败（详情保留在诊断记录）")
    video_errors = (packet.get("video_content_coverage") or {}).get("errors") or []
    if video_errors:
        failures.append(f"视频内容读取有 {len(video_errors)} 项待核，未读到不代表作者没有更新")
    return list(dict.fromkeys(failures))


def _pending_groups(packet: dict) -> list[str]:
    """Merge identical gaps across holdings and reviews without double-counting rows."""
    affected: dict[str, set[str]] = defaultdict(set)

    def add(row, gaps):
        identity = str(
            row.get("holding_id") or row.get("code") or row.get("fund_code") or _name(row)
        )
        for gap in gaps or []:
            affected[_text(gap)].add(identity)

    for row in packet.get("holdings", []):
        add(row, (row.get("facts") or {}).get("gaps"))
    for row in packet.get("plan_review", []):
        add(row, row.get("gaps"))
    result = [f"{gap}（{len(ids)}只）" for gap, ids in sorted(affected.items())]
    result.extend(_failure_lines(packet))
    return result


def _holding_association(item: dict, by_code: dict[str, str]) -> str:
    symbols = item.get("symbols") or []
    if isinstance(symbols, str):
        symbols = [symbols]
    names, unmatched = [], []
    for symbol in symbols:
        code = str(symbol).strip()
        name = by_code.get(code)
        if name and name not in names:
            names.append(name)
        elif code and code not in unmatched:
            unmatched.append(code)
    if names:
        return "关联持仓：" + "、".join(f"**{name}**" for name in names)
    if unmatched:
        return "关联代码：" + "、".join(unmatched) + "（当前持仓未包含这些代码）"
    return "关联持仓：未能从资料确认"


def render_brief(packet: dict) -> str:
    """Render user-readable facts, retaining source dates and avoiding inferred conclusions."""
    lines = ["# 每日持仓简报", "", f"生成时间：{_date_part(packet.get('generated_at'))}", ""]
    slot = packet.get("slot")
    if slot == "1135":
        lines.append("本次为信息汇总，只提供观察资料，不给出买卖建议。")
    elif slot == "1440":
        lines.append("本次只复核资料齐全的已确认计划；资料不足时列出缺口，不推断安全或失效。")
    else:
        lines.append("本次输出时段未识别，请核对简报设置。")

    holdings = packet.get("holdings", [])
    by_code = {
        str(row.get("code") or "").strip(): _name(row)
        for row in holdings
        if row.get("code") and _name(row) != "名称未知"
    }
    holding_by_id = {str(row.get("holding_id")): row for row in holdings if row.get("holding_id")}

    # Substantive changes lead the report.
    lines.extend(["", "## 本次变化", ""])
    changes = packet.get("changes", [])
    if changes:
        for row in changes:
            label = (
                "、".join(
                    _CHANGE_LABELS.get(value, "持仓资料变化") for value in row.get("fields", [])
                )
                or "记录有变化"
            )
            current = holding_by_id.get(str(row.get("holding_id")), {})
            facts = current.get("facts") or {}
            detail = []
            if "nav_value" in row.get("fields", []) and facts.get("nav_value") is not None:
                detail.append(f"当前净值 {_format_number(facts['nav_value'])}")
            if "nav_date" in row.get("fields", []) and facts.get("nav_date"):
                detail.append(f"净值日期 {_text(facts['nav_date'])}")
            if detail:
                label += "（" + "；".join(detail) + "）"
            lines.append(f"- **{_name(row)}**：{label}。")
    elif packet.get("first_observation"):
        lines.append("这是首次记录，暂时没有可比较的变化。")
    else:
        lines.append("没有发现已确认的持仓资料变化。")
    for row in packet.get("removed_since_previous", []):
        if isinstance(row, dict):
            lines.append(
                f"- **{_name(row)}**（代码：{_text(row.get('code'), '未知')}）："
                "本次清单未出现；这不代表已发生卖出。"
            )

    # Plan review comes before the trade ledger.
    if slot == "1440":
        lines.extend(["", "## 原计划复核", ""])
        reviews = packet.get("plan_review", [])
        qualified = [row for row in reviews if row.get("state") == _QUALIFIED_PLAN]
        if not qualified:
            lines.append("目前没有资料齐全、可按已确认计划复核的持仓；具体缺口见下方汇总。")
        for row in qualified:
            alerts = row.get("system_alerts") or []
            if not alerts:
                lines.append(f"- **{_name(row)}**：按原计划复核，系统未报告新提示。")
            for alert in alerts:
                dates = []
                if alert.get("data_as_of"):
                    dates.append(f"资料日期：{_text(alert['data_as_of'])}")
                if alert.get("actionable_from"):
                    dates.append(f"适用日期：{_text(alert['actionable_from'])}")
                if alert.get("next_step_cn"):
                    dates.append(_text(alert["next_step_cn"]))
                suffix = "；".join(dates)
                lines.append(
                    f"- **{_name(row)}**：原计划条件需要复核"
                    + (f"（{suffix}）" if suffix else "")
                    + "。"
                )

    ledger = packet.get("trade_ledger", {})
    lines.extend(["", "## 成交记录", ""])
    if not ledger.get("available"):
        lines.append("成交记录暂不可用。")
    elif ledger.get("changes"):
        for change in ledger["changes"]:
            trade = change.get("record", {})
            side = {"buy": "买入记录", "sell": "卖出记录"}.get(trade.get("side"), "成交记录")
            date = _text(trade.get("trade_date"), "日期未提供")
            if trade.get("price_status") == "priced":
                price = trade.get("priced_nav")
                pricing = "系统已按净值定价" + (
                    f" {_format_number(price)}" if price is not None else ""
                )
                lines.append(
                    f"- **{_name(trade)}**：新增或更新{side}，交易日期 {date}；{pricing}，"
                    "平台成交确认需另行核对。"
                )
            else:
                lines.append(
                    f"- **{_name(trade)}**：新增或更新{side}，交易日期 {date}；系统净值定价待确认。"
                )
    else:
        lines.append("没有新的成交记录变化。")
    if ledger.get("pending_pricing"):
        lines.append(
            f"另有 {len(ledger['pending_pricing'])} 条记录等待系统净值定价；"
            "成交记录变化不代表持仓已更新。"
        )

    # Report source observations as observations only; do not infer market direction.
    lines.extend(["", "## 市场背景资料", ""])
    background_count = 0
    for _market, source in packet.get("market_background", {}).items():
        data = source.get("data") or {}
        for item in data.get("items", []):
            label = _text(item.get("label"), "未命名观察")
            value = _format_number(item.get("value"))
            unit = _text(item.get("unit"), "")
            observation_date = _text(item.get("observation_date"), "日期未提供")
            source_label = _text(item.get("source_name"), "来源未注明")
            source_ref = _link(source_label, item.get("source_url"))
            quality = item.get("quality_reason") or _QUALITY_LABELS.get(item.get("quality_status"))
            suffix = f"；资料说明：{_text(quality)}" if quality else ""
            lines.append(
                f"- {label}：{value}{unit}（资料日期：{observation_date}；"
                f"来源：{source_ref}{suffix}）。"
            )
            background_count += 1
    if not background_count:
        lines.append("本次没有可展示的市场背景观察。")

    window = packet.get("blogger_window") or {}
    bloggers = packet.get("blogger_previous_trading_day", packet.get("blogger_yesterday", []))
    news = packet.get("news", [])
    lines.extend(["", "## 新闻与博主更新", ""])
    if window.get("status") == "verified":
        lines.append(
            f"博主视频筛选日期：上一个 A 股交易日 {_text(window.get('date'))}；"
            "内容依据逐条标明，只有标题时不概括完整建议。"
        )
    else:
        lines.append("上一个 A 股交易日暂无法核实；博主视频只列标题，不概括完整建议。")
    if bloggers:
        for item in bloggers:
            source = _link(item.get("source_name") or item.get("source"), item.get("url"))
            lines.append(
                f"- {_text(item.get('title'), '未提供标题')}（来源：{source}；"
                f"发布时间：{_date_part(item.get('published_at'))}）"
            )
            video = item.get("video_content") or {}
            if video and item.get("content"):
                coverage = (video.get("coverage") or {}).get("fraction")
                suffix = (
                    f"；转写段落覆盖约 {coverage * 100:.1f}% 视频时长"
                    if isinstance(coverage, (int, float))
                    else ""
                )
                lines.append(
                    f"  内容依据：本机语音转写，未人工校正{suffix}；价格和指标数字仍需回听。"
                )
                segments = video.get("segments") or []
                if segments:
                    first = segments[0]
                    stamp = float(first.get("start") or 0)
                    lines.append(
                        f"  开头原话摘录（{int(stamp) // 60:02d}:{int(stamp) % 60:02d}）："
                        f"{_text(first.get('text'))[:240]}"
                    )
            else:
                lines.append("  内容依据：仅标题或简介，未读到完整视频内容。")
    else:
        lines.append("没有可展示的上一个交易日博主视频。")

    total = len(news)
    show_count = min(8, total)
    omitted = total - show_count
    if news:
        lines.append(f"普通新闻：共 {total} 条，以下列出 {show_count} 条，省略 {omitted} 条。")
        ordered = sorted(
            news, key=lambda item: not any(str(s) in by_code for s in (item.get("symbols") or []))
        )
        for item in ordered[:8]:
            source = _link(item.get("source_name") or item.get("source"), item.get("url"))
            association = _holding_association(item, by_code)
            lines.append(
                f"- {_text(item.get('title'), '未提供标题')}（{association}；来源：{source}；"
                f"发布时间：{_date_part(item.get('published_at'))}）"
            )
    else:
        lines.append("普通新闻：本次没有可展示的条目。")
    if packet.get("news_coverage", {}).get("truncated"):
        lines.append("新闻源返回的列表可能不完整，当前条数不能代表全部消息。")
    if packet.get("unqualified_news"):
        lines.append(f"另有 {len(packet['unqualified_news'])} 条新闻因发布时间无法核实而未纳入。")

    pending = _pending_groups(packet)
    lines.extend(["", "## 待补资料", ""])
    if pending:
        lines.extend(f"- {line}" for line in pending)
    else:
        lines.append("没有由本次资料明确报告的待补项。")

    # Keep detailed holdings available without taking over the daily summary.
    lines.extend(
        [
            "",
            f"<details><summary>持仓明细（{len(holdings)}只）</summary>",
            "",
            "| 名称 | 代码 | 持仓记录日期 | 净值 | 净值日期 |",
            "| --- | --- | --- | ---: | --- |",
        ]
    )
    for row in holdings:
        facts = row.get("facts") or {}
        values = [
            _name(row),
            _text(row.get("code"), "未知"),
            _text(row.get("holding_as_of"), "未知"),
            _format_number(facts.get("nav_value"))
            if facts.get("nav_value") is not None
            else "待补",
            _text(facts.get("nav_date"), "未知"),
        ]
        cells = [escape(value).replace("|", "&#124;") for value in values]
        lines.append("| " + " | ".join(cells) + " |")
    lines.extend(["", "</details>"])
    lines.append(
        "注：背景数据只呈现来源记录的数值和日期，不据此形成行情结论；成交系统定价也不等于平台确认。"
    )
    return "\n".join(lines)
