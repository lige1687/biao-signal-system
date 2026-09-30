"""通用因子研究材料消费：定义来自正式登记，证据/结果来自纯数据索引。

不按因子ID分支，不计算因子，不运行研究，不将结果接入视为资格或授权。
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

from lei_signal.api.experiment_reports import read_report
from lei_signal.research.factor_access import (
    AccessError,
    load_access_catalog,
    read_comparison,
    read_materials,
)

_ROOT = Path(__file__).resolve().parents[3]
_REF_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_.:-])((?:candidate:)?[A-Za-z][A-Za-z0-9_.-]*@[A-Za-z0-9_.-]+)"
)
_BARE_REF_RE = re.compile(
    r"(?<![A-Za-z0-9_.:-])((?:candidate:)?[A-Za-z][A-Za-z0-9_-]*(?:\.[A-Za-z][A-Za-z0-9_-]*)+)"
)
_COMPARE_RE = re.compile(r"比较|对比|区别|差异|相比")
_EXPLICIT_VALUE_RE = re.compile(r"读数|数值|是多少|面板|已有观测")

_SYMBOL_TOKEN_RE = re.compile(
    r"(?<![A-Z0-9])(?:(SH|SZ))?([01356]\d{5})(?:\.(SS|SH|SZ))?(?![A-Z0-9])",
    re.IGNORECASE,
)

_DATE_RE = re.compile(r"(?<!\d)(20\d{2}-\d{2}-\d{2})(?!\d)")

_UNSUPPORTED_DATE_RE = re.compile(
    r"昨天|前天|上周|上月|去年|"
    r"(?<!\d)20\d{2}/\d{1,2}/\d{1,2}|"
    r"(?<!\d)20\d{2}年\d{1,2}月\d{1,2}日?"
)

_CURRENT_RE = re.compile(r"今天|现在|当前|最新|实时|截至目前")

_PANEL_RE = re.compile(r"读数|数值|是多少|面板|已有观测|已有.*动量")

_EVIDENCE_RE = re.compile(
    r"证据|有效吗|有用吗|有没有用|真的有用|研究结果|测试过|验证过|能证明|已有回测|历史回测|回测结果"
)

_EXPERIMENT_RE = re.compile(r"新实验|实验提案|设计.*实验|怎么验证|研究方案|如何研究")

_RUN_RE = re.compile(r"回测|补测|复跑|启动.*实验|执行.*实验")

_BACKTEST_LOOKUP_RE = re.compile(r"已有回测|历史回测|回测结果|解释.*回测|查看.*回测")

_UNSUPPORTED_USE_RE = re.compile(r"实盘|生产交易|直接.*买|直接.*卖|买卖信号|自动交易")

_LIFECYCLE_CN = {
    "exists": "已登记",
    "verified": "计算定义核验通过",
    "research_ready": "指定范围研究可用",
    "production_approved": "生产采用已获授权",
}

def _result(
    reply: str,
    status: str,
    intent: str,
    symbol: str | None,
    *,
    definition_refs: list[str] | None = None,
    sources: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "reply": reply,
        "status": status,
        "intent": intent,
        "symbol": symbol,
        "definition_refs": definition_refs or [],
        "sources": sources or [],
        "metadata": metadata or {},
    }

def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _json_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def _lifecycle_text(state: Any) -> str:
    code = str(state or "unknown")
    return f"{_LIFECYCLE_CN.get(code, '状态未知')}（{code}）"

def _canonical_symbol(value: str | None) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    match = _SYMBOL_TOKEN_RE.search(str(value).strip())
    if not match:
        return None, "invalid"
    prefix, digits, suffix = match.groups()
    prefix_market = {"SH": "SS", "SZ": "SZ"}.get((prefix or "").upper())
    suffix_market = {"SH": "SS", "SS": "SS", "SZ": "SZ"}.get((suffix or "").upper())
    if prefix_market and suffix_market and prefix_market != suffix_market:
        return None, "invalid"
    market = prefix_market or suffix_market
    if market is None:
        market = "SS" if digits.startswith(("5", "6")) else "SZ"
    return f"{digits}.{market}", None

def _normalize_symbol(value: str | None) -> str | None:
    return _canonical_symbol(value)[0]

def _resolve_symbol(message: str, supplied: str | None) -> tuple[str | None, str | None]:
    mentioned: list[str] = []
    for match in _SYMBOL_TOKEN_RE.finditer(message):
        canonical, error = _canonical_symbol(match.group(0))
        if error:
            return None, error
        if canonical and canonical not in mentioned:
            mentioned.append(canonical)
    if len(mentioned) > 1:
        return None, "multiple"
    if mentioned:
        return mentioned[0], None
    return _canonical_symbol(supplied)

def _has_timezone(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _format_value(value: Any, unit: str) -> str:
    if isinstance(value, bool):
        return "是" if value else "否"
    if unit in {"fraction", "decimal_return", "fraction_bounded"}:
        return f"{value:.2%}"
    return f"{value:g}（单位：{unit}）"

def _panel_reply(
    message: str,
    symbol: str | None,
    *,
    panel_loader: Callable[[], Any],
    now: datetime,
    reference: str,
    label: str,
    field: str,
    sources: list[dict],
    unit: str,
) -> dict[str, Any]:
    if symbol is None:
        return _result(
            "请先给一个六位标的代码；旧面板只能逐个标的核对，不能猜标的。",
            "needs_clarification",
            "observation",
            None,
            definition_refs=[reference],
        )

    try:
        panel = panel_loader()
    except Exception:  # noqa: BLE001 - 外部只读加载失败统一降级，不泄露内部错误
        panel = None
    if panel is None:
        return _result(
            "没有可读的历史面板，因此没有可解释的因子读数。这里不会触发行情或重新计算。",
            "unavailable",
            "observation",
            symbol,
            definition_refs=[reference],
            sources=sources,
        )
    if not isinstance(panel, dict) or not isinstance(panel.get("symbols"), list):
        return _result(
            "历史面板结构不合格，已拒绝解释；这里不会从坏结构猜字段或启动重算。",
            "unavailable",
            "observation",
            symbol,
            definition_refs=[reference],
            sources=sources,
        )

    matches = [
        row for row in panel["symbols"]
        if isinstance(row, dict) and _normalize_symbol(str(row.get("code", ""))) == symbol
    ]
    if len(matches) != 1:
        return _result(
            "历史面板没有这个标的的唯一记录，不能返回读数。",
            "unavailable",
            "observation",
            symbol,
            definition_refs=[reference],
            sources=sources,
        )
    row = matches[0]
    as_of = row.get("as_of")  # 必须逐标的；不拿全局日期替代未知逐标的日期。
    value = row.get(field)
    generated_at = panel.get("generated_at")
    generated_qualified = _has_timezone(generated_at)
    metadata = {
        "observation_as_of": as_of if isinstance(as_of, str) else None,
        "generated_at": generated_at,
        "generated_at_qualified": generated_qualified,
        "panel_schema": "legacy",
        "formal_definition_identity": False,
        "price_basis_known": False,
        "input_fingerprint_known": False,
        "calendar": "unknown",
        "freshness": "unknown",
        "historical_availability": "unknown",
        "calculated_at": None,
        "observation_source": {
            "api": "GET /api/factors/panel",
            "loader": "FactorPanelService.panel(refresh=False)",
        },
        "observation_copy_sha256": _json_sha256(
            {
                "row": row,
                "panel_generated_at": generated_at,
                "panel_data_as_of": panel.get("data_as_of"),
            }
        ),
        "observation_copy_sha256_scope": "read_snapshot_copy_not_input_fingerprint",
    }
    if not isinstance(as_of, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", as_of):
        return _result(
            "这个标的缺少可核的逐标的日期；不能拿面板全局日期补造，因此不返回读数。",
            "unavailable",
            "observation",
            symbol,
            definition_refs=[reference],
            sources=sources,
            metadata=metadata,
        )
    try:
        as_of_date = date.fromisoformat(as_of)
    except ValueError:
        return _result(
            "这个标的的逐标的日期无效，已拒绝解释；不能用面板总日期替换。",
            "unavailable",
            "observation",
            symbol,
            definition_refs=[reference],
            sources=sources,
            metadata=metadata,
        )
    if as_of_date > now.date():
        return _result(
            f"这个标的的逐标的日期 {as_of} 是未来日期，已拒绝解释。",
            "unavailable",
            "observation",
            symbol,
            definition_refs=[reference],
            sources=sources,
            metadata=metadata,
        )
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
    ):
        return _result(
            f"这个标的在 {as_of} 没有可用的有限数值；缺失、NaN或无穷值不能当作0。",
            "unavailable",
            "observation",
            symbol,
            definition_refs=[reference],
            sources=sources,
            metadata=metadata,
        )

    if _CURRENT_RE.search(message):
        reply = (
            f"没有合格的当前值来源。逐标的记录截止 {as_of}，但没有声明交易日历，"
            "尚未核实是否覆盖最近完成交易日；"
            "当前面板又属于 legacy 历史留痕，缺正式定义身份、价格口径和输入指纹。"
            + (
                "generated_at 也不带时区，不能补造成合格可得时刻。"
                if generated_at and not generated_qualified
                else "即使生成时刻带时区，也不能补齐上述身份和口径。"
            )
            + "因此不返回这个数值，也不会触发行情或因子计算。"
        )
        return _result(
            reply,
            "unqualified_current",
            "current_observation",
            symbol,
            definition_refs=[reference],
            sources=sources,
            metadata=metadata,
        )

    time_note = (
        f"生成时刻 {generated_at} 不带时区，不能当作合格可得时刻。"
        if generated_at and not generated_qualified
        else (
            "生成时刻带时区，但不能补齐正式身份、价格口径和输入指纹。"
            if generated_qualified
            else "生成时刻没有合格的带时区记录。"
        )
    )
    reply = (
        f"旧面板里，{symbol} 的{label}历史读数截至 {as_of} 为 {_format_value(value, unit)}。"
        "这只能作为历史参考："
        f"面板缺正式定义身份、价格口径和输入指纹；{time_note}"
        "计算核验不等于投资有效，因子风险说明也不是买卖信号。"
    )
    return _result(
        reply,
        "historical_only",
        "observation",
        symbol,
        definition_refs=[reference],
        sources=sources,
        metadata=metadata,
    )


def _aliases(catalog: dict) -> list[tuple[str, str]]:
    pairs = [(card["name"], ref) for ref, card in catalog["definitions"].items()]
    for ref, binding in catalog["bindings"].items():
        pairs.extend((alias, ref) for alias in binding["aliases"])
    return [(alias, ref) for alias, ref in pairs if len(alias) >= 2]


def _matched_aliases(message: str, catalog: dict) -> list[str]:
    hits = []
    for alias, ref in _aliases(catalog):
        for match in re.finditer(re.escape(alias), message, re.IGNORECASE):
            hits.append((match.start(), match.end(), ref))
    # 长名称覆盖其内部的简称；真正的同名多版本仍全部保留，要求澄清。
    return list(dict.fromkeys(ref for start, end, ref in hits if not any(
        a <= start and end <= b and (a, b) != (start, end) for a, b, _ in hits
    )))


def is_factor_question(message: str, **catalog_options) -> bool:
    text = str(message or "")
    if re.search(r"(?<!成)因子", text) or _REF_TOKEN_RE.search(text) or _BARE_REF_RE.search(text):
        return True
    try:
        return bool(_matched_aliases(text, load_access_catalog(**catalog_options)))
    except (AccessError, OSError, ValueError):
        # 明确因子/编号已在上面接管；普通聊天不能因目录失效而被改写。
        return False


def _bind_references(text: str, catalog: dict) -> tuple[list[str], str | None]:
    explicit = list(dict.fromkeys(_REF_TOKEN_RE.findall(text)))
    stripped = _REF_TOKEN_RE.sub(" ", text)
    bare = list(dict.fromkeys(_BARE_REF_RE.findall(stripped)))
    if bare:
        return bare, "请提供精确版本（ID@版本）；不支持省略版本或自动采用latest。"
    available = set(catalog["definitions"]) | set(catalog["bindings"])
    if any(ref not in available for ref in explicit):
        return explicit, "没有找到这个精确版本；不支持不完整版本，也不会回退到latest。"
    aliases = _matched_aliases(text, catalog)
    if explicit:
        if _COMPARE_RE.search(text):
            ids = {ref.split("@")[0] for ref in explicit}
            explicit.extend(ref for ref in aliases if ref.split("@")[0] not in ids)
        return list(dict.fromkeys(explicit)), None
    return aliases, None


def _definition_text(ref: str, card: dict | None, materials: dict) -> str:
    if card is None:
        return (f"`{ref}`（{materials['label']}）是候选草案，未登记为正式对象。"
                f"{materials['draft_definition']}\n写清公式不等于数据合格，也不等于投资有效。")
    definition = card["definition"]
    lifecycle = card.get("lifecycle", {})
    return (
        f"`{ref}`（{card['name']}）的正式公式：{definition['formula']}。"
        f"单位：{definition['unit']}；价格口径：{card['input']['price_basis']}。\n"
        + "\n".join(materials.get("definition_notes", []))
        + f"\n登记状态：{_lifecycle_text(lifecycle.get('state'))}。"
        + f"核验范围：{lifecycle.get('verification_scope') or '未记录计算核验范围'}。"
        + "计算核验通过不等于投资有效；因子描述不是买卖信号，也不提供收益承诺。"
    )


def _evidence_text(materials: dict) -> str:
    labels = {
        "calculation_check": "计算核验", "data_validation": "资料检查",
        "predictive_study": "预测关系研究", "return_study": "历史收益研究",
        "risk_description": "风险描述",
    }
    blocks = [f"研究材料记载（{labels[item['kind']]}）：{item['summary']}\n"
              f"适用范围：{item['scope']}\n限制：" + "；".join(item["limitations"])
              for item in materials.get("evidence", [])]
    return "\n\n".join(blocks) + (
        "\n\n这里只解释已接入材料；计算核验不等于策略有效，风险描述不是买卖信号，"
        "历史结果不保证未来收益。"
    )


def _batch_reply(text: str, symbol: str | None, ref: str, materials: dict,
                 now: datetime, requested_date: str | None) -> dict:
    sources = materials.get("sources_verified", [])
    if _CURRENT_RE.search(text):
        return _result(
            "结果包已经接入，但本入口尚未开放当前值资格检查；不能把已有研究行当作当前值。",
            "unqualified_current", "current_observation", symbol,
            definition_refs=[ref], sources=sources,
        )
    if symbol is None:
        return _result("请明确标的或用entity_id=指定研究对象，不能自行挑选研究结果中的一行。",
                       "needs_clarification", "observation", None,
                       definition_refs=[ref], sources=sources)
    matches = [(packet, row) for packet in materials["batches"] for row in packet["values"]
               if row["entity_id"] == symbol
               and (requested_date is None or row["observation_date"] == requested_date)]
    if len(matches) != 1:
        return _result(
            "没有唯一的研究观测；请明确对象和日期。多批结果不会自动选最新一条，缺记录也不补零。",
            "needs_clarification" if matches else "unavailable", "observation", symbol,
            definition_refs=[ref], sources=sources,
        )
    packet, row = matches[0]
    meta = packet["metadata"]
    metadata = {
        "observation_as_of": row["observation_date"],
        "calculated_at": packet["calculated_at"],
        "historical_availability": "unknown", "freshness": "unknown",
        "research_metadata": meta, "synthetic": meta["synthetic"],
        "data_cutoff": None,
        "price_basis": meta["card"]["input"]["price_basis"],
        "price_basis_role": "definition_requirement_not_input_qualification",
        "definition_contract_sha256": packet["definition_contract_sha256"],
        "observation_copy_sha256": _json_sha256(packet),
    }
    if date.fromisoformat(row["observation_date"]) > now.date():
        return _result("研究行的日期是未来日期，不能解释为已有读数。", "unavailable",
                       "observation", symbol, definition_refs=[ref], sources=sources,
                       metadata=metadata)
    if row["value"] is None or row["missing_reason"]:
        return _result(f"该研究行没有可用读数：{row['missing_reason']}。不把缺失当成0。",
                       "unavailable", "observation", symbol, definition_refs=[ref],
                       sources=sources, metadata=metadata)
    label = "人工数据测试" if meta["synthetic"] else "已有历史研究"
    reply = (f"{label}中的 `{ref}`：{symbol} 在 {row['observation_date']} 的记录为"
             f" {_format_value(row['value'], meta['unit'])}。用途：{meta['purpose']}。"
             f"定义要求的价格口径：{metadata['price_basis']}。"
             "接入成功只表示材料可读，不能据此认定数据合格或策略有效；"
             "不能证明当时已经知道这个结果，也不是当前值或买卖信号。")
    return _result(reply, "historical_only", "observation", symbol,
                   definition_refs=[ref], sources=sources, metadata=metadata)


def _proposal(refs: list[str], symbol: str | None) -> dict:
    return _result(
        "文本提案：先固定这些对象的准确版本、研究用途、产品范围、日期、价格口径、输入来源、"
        "比较对象、费用及停止条件。具体执行需要对应冻结协议和授权。"
        "这里不会创建任务、运行计算或回测，也不会自动修改资格条件。",
        "proposal_only", "experiment_proposal", symbol, definition_refs=refs,
        metadata={"executed": False, "created_task": False, "proposal_kind": "text_only"},
    )


def _build_reply(text: str, symbol: str | None, catalog: dict,
                 panel_loader: Callable, now: datetime, root: Path) -> dict:
    refs, error = _bind_references(text, catalog)
    if error:
        return _result(error, "unsupported", "definition", symbol, definition_refs=refs)
    if _UNSUPPORTED_USE_RE.search(text):
        return _result("研究材料不能用于实盘买卖或自动交易；不会修改规则、资格条件或授权。",
                       "unsupported_use", "unsupported_use", symbol, definition_refs=refs)
    if _UNSUPPORTED_DATE_RE.search(text):
        return _result("不支持这种日期写法，请给出明确的YYYY-MM-DD；不会用已有快照代替。",
                       "unsupported", "historical_date", symbol, definition_refs=refs)
    dates = list(dict.fromkeys(_DATE_RE.findall(text)))
    if len(dates) > 1:
        return _result("请明确一个观测日期。", "needs_clarification", "historical_date", symbol)
    if dates:
        try:
            date.fromisoformat(dates[0])
        except ValueError:
            return _result("请求日期无效，不支持猜测。", "unsupported", "historical_date", symbol)
    run_requested = _RUN_RE.search(text) and not _BACKTEST_LOOKUP_RE.search(text)
    if run_requested or _EXPERIMENT_RE.search(text):
        return _proposal(refs, symbol)
    if not refs:
        return _result("请点名具体因子及准确版本；泛指‘这个因子’不足以选择材料。",
                       "needs_clarification", "clarification", symbol)
    if len(refs) > 1 and not _COMPARE_RE.search(text):
        return _result("匹配到多个对象或版本，请明确一个：" + "、".join(refs),
                       "needs_clarification", "clarification", symbol, definition_refs=refs)
    if _EVIDENCE_RE.search(text) and _EXPLICIT_VALUE_RE.search(text):
        return _result("已有读数与效果证据是两个问题，请明确先查哪项。",
                       "needs_clarification", "clarification", symbol, definition_refs=refs)

    try:
        if len(refs) > 1:
            comparison = read_comparison(catalog, refs, root=root)
            if comparison:
                return _result(comparison["summary"] + "\n限制："
                               + "；".join(comparison["limitations"]),
                               "proposal_only", "comparison", symbol, definition_refs=refs,
                               sources=comparison["sources_verified"], metadata={"executed": False})
            texts, sources = [], []
            for ref in refs:
                material = read_materials(catalog, ref, root=root)
                texts.append(_definition_text(ref, catalog["definitions"].get(ref), material))
                sources.extend(material.get("sources_verified", []))
            return _result("\n\n".join(texts) + "\n没有接入这组版本的比较研究，不能判断谁更有效；"
                           "若需要新比较，只能另提实验方案。",
                           "comparison_not_bound", "comparison", symbol, definition_refs=refs,
                           sources=sources, metadata={"executed": False})
        ref = refs[0]
        materials = read_materials(catalog, ref, root=root)
    except AccessError:
        return _result("绑定材料缺失、身份错误或内容指纹不一致，已停止原解释；"
                       "不会自动换来源或重算。",
                       "source_drift", "evidence", symbol, definition_refs=refs)

    sources = materials.get("sources_verified", [])
    card = catalog["definitions"].get(ref)
    if _EVIDENCE_RE.search(text):
        if not materials.get("evidence"):
            return _result("这个准确版本尚未接入对应的效果证据索引；这不等于其他材料一定没有证据。",
                           "evidence_not_bound", "evidence", symbol,
                           definition_refs=refs, sources=sources)
        return _result(_evidence_text(materials), "limited", "evidence", symbol,
                       definition_refs=refs, sources=sources,
                       metadata={"evidence_scope": "registered_materials_only"})
    if _CURRENT_RE.search(text) or _PANEL_RE.search(text) or dates:
        if materials.get("batches"):
            return _batch_reply(text, symbol, ref, materials, now, dates[0] if dates else None)
        if materials.get("legacy_panel"):
            if dates and dates[0] != now.date().isoformat():
                return _result("旧面板不支持按历史日期回查；不会拿手头快照替代指定日期。",
                               "unsupported", "historical_date", symbol, definition_refs=refs)
            return _panel_reply(text, symbol, panel_loader=panel_loader, now=now,
                                reference=ref, label=materials["label"],
                                field=materials["legacy_panel"]["field"], sources=sources,
                                unit=card["definition"]["unit"])
        return _result("这个版本尚未接入可查询的计算结果，没有绑定可用读数；"
                       "不能借用其他因子字段，也不会启动计算。",
                       "unavailable", "current_observation" if _CURRENT_RE.search(text)
                       else "observation", symbol, definition_refs=refs, sources=sources,
                       metadata={"executed": False})
    reply = _definition_text(ref, card, materials)
    state = "proposal_only" if card is None else (
        "ok" if card.get("lifecycle", {}).get("state") == "verified" else "limited")
    return _result(reply, state, "candidate_definition" if card is None else "definition",
                   symbol, definition_refs=refs, sources=sources,
                   metadata={"formal_registry_object": card is not None,
                             "lifecycle_state": (card or {}).get("lifecycle", {}).get("state")})


def build_factor_reply(message: str, symbol: str | None, *, panel_loader,
                       now=None, registry_path=None, root=None, catalog_path=None) -> dict:
    """所有因子共用的消费入口；新增接入仅改变资料索引和结果包。"""
    now = now or datetime.now(ZoneInfo("Asia/Shanghai"))
    if now.tzinfo is None:
        now = now.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
    root = Path(root) if root is not None else _ROOT
    text = str(message or "")
    entities = list(dict.fromkeys(re.findall(r"\bentity_id=([A-Za-z0-9_^.:-]+)", text)))
    text = re.sub(r"\bentity_id=[A-Za-z0-9_^.:-]+", "", text)
    resolved, symbol_error = _resolve_symbol(text, symbol)
    if entities:
        explicit_symbol, explicit_error = _resolve_symbol(text, None)
        if len(entities) != 1 or explicit_error or (
            explicit_symbol and _normalize_symbol(entities[0]) != explicit_symbol
        ):
            resolved, symbol_error = None, "ambiguous"
        else:
            resolved, symbol_error = entities[0], None
    catalog = None
    if symbol_error:
        result = _result("一次只支持一个标的，请明确一个完整代码。", "needs_clarification",
                         "clarification", None)
    else:
        try:
            catalog = load_access_catalog(root=root, catalog_path=catalog_path,
                                          registry_path=registry_path)
        except (AccessError, OSError, ValueError):
            result = _result("因子登记或接入索引不可用，已停止查询，不回落行情计算。",
                             "unavailable", "clarification", resolved)
        else:
            result = _build_reply(text, resolved, catalog, panel_loader, now, root)
    metadata = result["metadata"]
    metadata.update(assembled_at=now.isoformat(),
                    assembled_at_role="response_assembly_not_factor_calculation")
    if catalog:
        metadata["catalog_source"] = catalog["catalog_source"]
        metadata["registry_sha256"] = catalog["registry_source"]["sha256"]
        metadata["definition_cards"] = [
            {"reference": ref, "card_sha256": _json_sha256(catalog["definitions"][ref]),
             "lifecycle_state": catalog["definitions"][ref].get("lifecycle", {}).get("state"),
             "status": catalog["definitions"][ref]["status"]}
            for ref in result["definition_refs"] if ref in catalog["definitions"]
        ]
        result["sources"].extend([catalog["catalog_source"], catalog["registry_source"]])
    references_text = "、".join(f"`{ref}`" for ref in result["definition_refs"]) or "未确定"
    lines = ["定义引用：" + references_text]
    links = []
    if result["status"] != "source_drift":
        for source in result["sources"]:
            rel = source.get("path", "")
            if (rel.startswith("docs/experiments/") and rel.endswith(".md")
                    and read_report(rel, base=root) is not None):
                links.append(f"[{Path(rel).stem}](/library?report={quote(rel, safe='')})")
    if links:
        lines.append("已核报告：" + "、".join(dict.fromkeys(links)))
    if result["intent"] in {"observation", "current_observation"}:
        cutoff = (metadata.get("data_cutoff") if "research_metadata" in metadata
                  else metadata.get("observation_as_of"))
        lines.append(f"观测日期：{metadata.get('observation_as_of') or '未知'}；"
                     f"数据截止：{cutoff or '未知'}；"
                     f"计算时间：{metadata.get('calculated_at') or '未记录'}；"
                     f"回复组装时间：{now.isoformat()}（不是因子计算时间）")
    result["reply"] += "\n\n" + "\n".join(lines)
    return result
