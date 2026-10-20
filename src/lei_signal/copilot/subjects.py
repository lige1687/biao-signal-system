"""讨论对象的本地名称与板块资料。只读目录，不拉行情、不产生交易判断。"""

from __future__ import annotations

import json
import re
from pathlib import Path

from lei_signal.api.config import STRATEGY_INDICES, US_ETFS, cache_root
from lei_signal.api.labels import THS_INDUSTRY_NAMES

PRODUCT_NAMES = {
    "515880.SS": "通信ETF",
    "512890.SS": "红利低波ETF",
    "601689.SS": "拓普集团",
    "IGV": "美国软件IGV",
}
# 已有行业目录的一级板块身份；缓存缺失仍不得改认成ETF。
SECTOR_NAMES = {"BK1215.SECTOR": "通信"}


def sector_snapshot() -> dict:
    try:
        value = json.loads((Path(cache_root()) / "sector_trend_snapshot.json").read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def sector_rows() -> list[dict]:
    rows = sector_snapshot().get("boards", [])
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def catalog_names() -> dict[str, str]:
    names = {x.symbol: x.display_name for x in (*STRATEGY_INDICES, *US_ETFS)}
    names.update(PRODUCT_NAMES)
    names.update({f"TH{k}.SECTOR": v for k, v in THS_INDUSTRY_NAMES.items()})
    names.update(SECTOR_NAMES)
    names.update(
        {
            f"{r['code']}.SECTOR": r["name"]
            for r in sector_rows()
            if re.fullmatch(r"BK\d{4}", str(r.get("code", ""))) and isinstance(r.get("name"), str)
        }
    )
    return names


def display_name(symbol: str, supplied: str | None = None) -> str:
    name = str(supplied or "").strip()
    # 行情提供者可能把代码塞进名称字段，不能把它当真名。
    if name and name.upper() not in {symbol.upper(), symbol.split(".")[0].upper()}:
        return name
    return catalog_names().get(symbol, "")


def subject_label(symbol: str, supplied: str | None = None) -> str:
    name = display_name(symbol, supplied)
    return f"{name or '名称待核实'}（{symbol}）"


def asks_for_sector(message: str) -> bool:
    return bool(re.search(r"板块|版块|行业", message)) and not bool(
        re.search(r"ETF|基金", message, re.I)
    )


def named_subject(message: str) -> str | None:
    names = catalog_names()
    flat = re.sub(r"\s+", "", message).upper()
    # ETF字样是产品类型，不是美股代码；产品专名优先于其中的行业片段。
    products = [
        (len(n), s)
        for s, n in names.items()
        if "ETF" in n.upper() and n.upper().replace(" ", "") in flat
    ]
    if products:
        return max(products)[1]
    if re.search(r"ETF|基金", message, re.I):
        return None
    sectors = [
        (len(n), s) for s, n in names.items() if s.endswith(".SECTOR") and n and n in message
    ]
    if sectors:
        # 同名时优先本地板块快照，对应行业板块页面同一份资料。
        return max(sectors, key=lambda x: (x[0], x[1].startswith("BK")))[1]
    return None


def sector_context(symbol: str) -> dict | None:
    if not symbol.startswith("BK") or not symbol.endswith(".SECTOR"):
        return None
    snapshot = sector_snapshot()
    row = next((r for r in sector_rows() if r.get("code") == symbol.split(".")[0]), None)
    name = display_name(symbol)
    if not row and not name:
        return None
    row = row or {}
    stage = {
        "accumulation": "筑底",
        "markup": "上升",
        "distribution": "派发",
        "decline": "下降",
    }.get(row.get("stage"), "资料不足")
    # 日期取行情日期，不用generated_at/as_of的文件生成时刻冒充。
    date = snapshot.get("trading_day") or snapshot.get("date") if row else None
    note = (
        "这是行业板块整体观察，不是ETF或可直接交易的产品；合成指数以当前成分回看历史，"
        "仅作形态参考，不据此产生买卖计划或借用ETF胜率。"
    )
    facts = {
        k: row.get(k)
        for k in (
            "member_count",
            "hit_count",
            "stage_basis",
            "next_watch",
            "rs_pctile",
            "rs_chg_20",
            "rs_chg_60",
            "b20",
            "b50",
            "b200",
            "breadth_divergence",
            "long_trend_cn",
            "alignment_cn",
            "macd_label_cn",
        )
    }
    summary = (
        f"成分股站上50日均线的比例：{row['b50']}%"
        if row.get("b50") is not None
        else "成分股站上50日均线的比例：数据不足"
    )
    return {
        "context_kind": "sector",
        "symbol": symbol,
        "display_name": name or "名称待核实",
        "as_of": date,
        "assessment": {
            "stage_cn": stage,
            "color_cn": row.get("signal_color_cn"),
            "risk_state_cn": "板块观察，非买卖信号",
        },
        "dual_ma": {"close": row.get("close")},
        "sector": facts,
        "subject_note_cn": note,
        "data_available": bool(row),
        "evidence_card": {
            "facts": {
                "symbol": symbol,
                "display_name": name or "名称待核实",
                "subject_kind": "sector",
                "as_of": date,
                "verdict_cn": f"板块阶段：{stage}",
                "sector_summary_cn": summary,
            },
            "history_and_scope": {"note_cn": note},
            "explanations": {"note_cn": "宽度指成分股中站上相应均线的比例；缺失数据不补造。"},
            "pending_conditions": [row["next_watch"]] if row.get("next_watch") else [],
        },
    }
