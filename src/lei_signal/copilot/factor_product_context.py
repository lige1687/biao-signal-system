"""Read only product identity and existing factor material for product questions."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from lei_signal.copilot.factor_readonly import build_factor_reply
from lei_signal.research.factor_access import AccessError, load_access_catalog, read_materials

ROOT = Path(__file__).resolve().parents[3]
PRODUCTS = Path("configs/factor-products.v1.json")
_FACTOR_INTENT = re.compile(r"因子|研究依据|从.*因子.*看|从.*研究.*看")
_CURRENT = re.compile(r"今天|现在|当前|最新|实时|截至目前")
_DATE = re.compile(r"(?<!\d)20\d{2}-\d{2}-\d{2}(?!\d)")
_EXPLICIT_REF = re.compile(r"(?:candidate:)?[a-z][a-z0-9_.-]+@(?:\d+\.\d+\.\d+|draft-\d+)", re.I)
_CODE = re.compile(r"(?<!\d)\d{6}(?:\.(?:SS|SH|SZ))?(?!\d)", re.I)


def is_product_factor_question(message: str) -> bool:
    text = str(message or "")
    if not _FACTOR_INTENT.search(text) or _EXPLICIT_REF.search(text):
        return False
    if _CODE.search(text):
        return True
    # Intent routing only needs product names. Full source verification belongs
    # to build_product_factor_reply after a product-specific question is found.
    try:
        raw = json.loads((ROOT / PRODUCTS).read_text(encoding="utf-8"))
        products = raw["products"]
    except (OSError, ValueError, TypeError, KeyError):
        return False
    return any(isinstance(product, dict) and any(
        isinstance(term, str) and term and term in text
        for term in [product.get("name"), *(product.get("aliases") or []),
                     *(product.get("ambiguous_terms") or [])]
    ) for product in products)


def _load_products(root: Path, path: Path | None = None) -> tuple[list[dict], dict]:
    catalog_path = (path if path is not None else root / PRODUCTS).resolve(strict=True)
    if not catalog_path.is_relative_to(root.resolve()):
        raise AccessError("product catalog outside root")
    raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != 1 or not isinstance(raw.get("products"), list):
        raise AccessError("invalid product catalog")
    products = raw["products"]
    codes = [p.get("code") for p in products]
    if len(codes) != len(set(codes)):
        raise AccessError("duplicate product code")
    for product in products:
        source = product.get("identity_source") or {}
        rel = source.get("path")
        if not isinstance(rel, str) or rel.startswith("/") or ".." in Path(rel).parts:
            raise AccessError("invalid identity source")
        file = (root / rel).resolve(strict=True)
        if not file.is_relative_to(root.resolve()) or hashlib.sha256(file.read_bytes()).hexdigest() != source.get("sha256"):
            raise AccessError("product identity source drift")
        refs = product.get("factor_refs")
        if (not isinstance(refs, list) or any(not isinstance(ref, str) or "@" not in ref for ref in refs)
                or len(refs) != len(set(refs))):
            raise AccessError("invalid product factor refs")
    return products, {"path": str(catalog_path.relative_to(root)),
                      "sha256": hashlib.sha256(catalog_path.read_bytes()).hexdigest()}


def _norm_code(code: str | None) -> str | None:
    if code is None:
        return None
    text = str(code).upper()
    if text in {"159915", "159915.SZ"}:
        return "159915.SZ"
    if text in {"588000", "588000.SS", "588000.SH"}:
        return "588000.SS"
    return "012920" if text == "012920" else text


def _observations(material: dict, code: str) -> list[tuple[dict, dict]]:
    return [(packet, row) for packet in material["batches"] for row in packet["values"]
            if row["entity_id"] == code]


def _value_text(packet: dict, row: dict) -> str:
    value = row["value"]
    unit = packet["metadata"]["unit"]
    if unit in {"ratio", "fraction", "decimal_return", "fraction_bounded"}:
        return f"{value:.4%}"
    return f"{value:g}（单位：{unit}）"


def _historical_conclusion(product: dict, packet: dict, row: dict,
                           material: dict) -> tuple[str, str, list[str]]:
    code = product["code"]
    when = row["observation_date"]
    value = _value_text(packet, row)
    ref = product["factor_refs"][0]
    evidence = material.get("evidence") or []
    if ref == "mixed.momentum.raw@1.0.0":
        interpretation = "这是剔除最近21个报价日后的一年价格变化，不是预期收益。"
        checked = any(item["kind"] == "calculation_check" and "不能证明" in item["summary"]
                      for item in evidence)
        increment = ("现有报告只核对计算，未证明它能改善预测或操作判断。" if checked else
                     "现有材料不足以证明它能改善预测或操作判断。")
        brief = ("报告只核对计算，未证明它能改善预测或操作判断。" if checked else
                 "现有材料不足以证明它能改善预测或操作判断。")
    elif ref == "research.price_volume.range_mean20@1.0.0":
        interpretation = "这是此前20个报价日的平均日内波动幅度。"
        compared = any(item["kind"] == "predictive_study" and "简单对照" in item["summary"]
                       and "比新增模型少错" in item["summary"]
                       and "4只宽基与4只行业ETF" in item["scope"] for item in evidence)
        increment = (("封存比较中，它没有胜过按各ETF较早已成熟历史结果取平均的简单对照，"
                      "不支持新增买卖依据。") if compared else
                     "现有材料不足以证明它能提供新增买卖依据。")
        brief = ("既有八只ETF研究中，它未胜过简单历史平均，暂不支持新增买卖依据。"
                 if compared else "现有材料不足以证明它能提供新增买卖依据。")
    else:
        interpretation = "这是已保存资料中的历史读数。"
        increment = "现有材料不足以证明它能改变操作判断。"
        brief = increment
    conclusion = f"{product['name']}（{code}）截至{when}的历史因子读数为{value}。{interpretation}{increment}"
    return conclusion, brief, [f"历史读数：{value}。", interpretation]


def _pack(reply: str, status: str, intent: str, *, symbol: str | None = None,
          title: str = "产品因子依据", facts: list[str] | None = None,
          presentation_conclusion: str | None = None,
          next_step: str | None = None, refs: list[str] | None = None,
          sources: list[dict] | None = None, metadata: dict | None = None,
          detail: str | None = None, as_of: str | None = None) -> dict:
    presentation = {"title": title, "conclusion": presentation_conclusion or reply,
                    "facts": (facts or [])[:3],
                    "as_of": as_of, "date_note": "历史研究日期不等于当前读数。"}
    if next_step:
        presentation["next_step"] = next_step
    return {"reply": reply, "status": status, "intent": intent, "symbol": symbol,
            "definition_refs": refs or [], "sources": sources or [], "metadata": metadata or {},
            "presentation": presentation, "detail_text": detail or reply}


def _multi_factor_reply(product: dict, refs: list[str], catalog: dict, text: str,
                        now: datetime, base: Path, factor_catalog_path: Path | None,
                        sources: list[dict], metadata: dict) -> dict:
    """Show every bound item separately; a shared date is not a joint signal."""
    code = product["code"]
    dated = list(dict.fromkeys(_DATE.findall(text)))
    if len(dated) > 1:
        return _pack("请一次明确一个观察日期。", "needs_clarification", "product_factor",
                     symbol=code, title=product["name"], refs=refs, sources=sources,
                     metadata=metadata)
    if dated:
        from datetime import date
        try:
            date.fromisoformat(dated[0])
        except ValueError:
            return _pack("观察日期无效，请给出YYYY-MM-DD。", "needs_clarification",
                         "product_factor", symbol=code, title=product["name"],
                         refs=refs, sources=sources, metadata=metadata)

    items: list[dict] = []
    for ref in refs:
        binding = catalog["bindings"].get(ref)
        label = (binding or catalog["definitions"].get(ref) or {}).get("label", ref)
        item = {"reference": ref, "label": label, "status": "unavailable",
                "version": ref.rsplit("@", 1)[-1],
                "observation_date": None, "value": None, "unit": None,
                "evidence": [], "sources": [],
                "source_claims": (binding or {}).get("sources", []) + (binding or {}).get("batches", []),
                "historical_availability": "unknown"}
        try:
            material = read_materials(catalog, ref, root=base)
        except (AccessError, OSError, ValueError):
            item["status"] = "source_drift"
            items.append(item)
            continue
        item["label"] = material["label"]
        item["evidence"] = material["evidence"]
        item["sources"] = material["sources_verified"]
        item["observations"] = _observations(material, code)
        items.append(item)

    # A current request has no qualified current value even if historical rows exist.
    if _CURRENT.search(text):
        for item in items:
            item["source_status"] = "source_drift" if item["status"] == "source_drift" else "verified"
            item["status"] = "unqualified_current"
            item.pop("observations", None)
        metadata.update(factor_items=items, combination_status="not_evaluated",
                        combination_weights=None, decision_authorization="none")
        current_sources = sources + [source for item in items for source in item["sources"]]
        detail = "\n".join(f"{item['label']}（{item['reference']}）："
                           f"{'来源核验失败，且当前值资格未核准' if item['source_status'] == 'source_drift' else '当前值资格未核准'}。"
                           for item in items)
        reply = f"{product['name']}（{code}）的当前因子值尚不能核实。各项历史资料不能当作今天的读数。"
        return _pack(reply, "unqualified_current", "current_observation", symbol=code,
                     title=product["name"], refs=refs, sources=current_sources,
                     metadata=metadata, detail=reply + "\n" + detail,
                     next_step="可查看已封存历史证据，不能当作今天的读数。")

    if dated:
        chosen_date = dated[0]
    else:
        date_sets = [{row["observation_date"] for _, row in item.get("observations", [])}
                     for item in items]
        common = set.intersection(*date_sets) if date_sets else set()
        chosen_date = max(common) if common else None
    base_refs = [ref.rsplit("@", 1)[0] for ref in refs]
    version_conflict = len(base_refs) != len(set(base_refs))
    complete = chosen_date is not None and not version_conflict
    for item in items:
        if item["status"] == "source_drift":
            complete = False
            continue
        observations = item.pop("observations")
        item_date = chosen_date or max((row["observation_date"] for _, row in observations), default=None)
        item["observation_date"] = item_date
        matches = [(packet, row) for packet, row in observations if row["observation_date"] == item_date]
        if len(matches) != 1:
            item["status"] = "unavailable" if not matches else "ambiguous"
            complete = False
            continue
        packet, row = matches[0]
        item["unit"] = packet["metadata"]["unit"]
        if row["value"] is None or row["missing_reason"]:
            item["status"] = "missing"
            item["missing_reason"] = row["missing_reason"]
            complete = False
            continue
        detail = build_factor_reply(f"{item['reference']} entity_id={code} {item_date}对判断有什么帮助？",
                                    code, panel_loader=lambda: None, now=now, root=base,
                                    catalog_path=factor_catalog_path)
        item["status"] = detail["status"]
        item["sources"] = list({(source["path"], source["sha256"]): source
                                for source in item["sources"] + detail["sources"]}.values())
        if detail["status"] == "historical_only":
            item["value"] = row["value"]
            item["value_text"] = _value_text(packet, row)
            item["observation_copy_sha256"] = detail["metadata"].get("observation_copy_sha256")
        else:
            complete = False

    metadata.update(factor_items=items, combination_status="not_evaluated",
                    combination_weights=None, decision_authorization="none",
                    common_observation_date=chosen_date if complete else None,
                    version_conflict=version_conflict)
    lines = []
    all_sources = list(sources)
    for item in items:
        all_sources.extend(item["sources"])
        if item["status"] == "historical_only":
            description = f"{item['observation_date']}历史读数 {item['value_text']}"
        elif item["status"] == "source_drift":
            description = "来源指纹未通过核对"
        elif item["status"] == "missing":
            description = f"{item['observation_date']}缺失：{item['missing_reason']}"
        elif item["status"] == "ambiguous":
            description = f"{item['observation_date']}有多条记录，无法唯一核对"
        else:
            description = f"{item['observation_date'] or '指定日期'}无可核对读数"
        lines.append(f"{item['label']}（{item['reference']}）：{description}。")
        if item["evidence"]:
            lines.append("已有证据：" + "；".join(
                f"{entry['summary']}（范围：{entry['scope']}；限制：{'；'.join(entry['limitations'])}）"
                for entry in item["evidence"]))
    date_note = ("同一因子绑定了多个版本，须明确选择版本；这些读数不可合成一个组合。" if version_conflict else
                 f"共同历史观察日期为{chosen_date}。" if complete else
                 "各项没有完整的同日可核对读数；所列日期不可合成一个组合。")
    reply = (f"{product['name']}（{code}）：{date_note}现有组合效果未评价，"
             "没有组合权重或新增买卖判断；同源、不同窗口的读数不能当作独立确认。")
    detail = reply + "\n" + "\n".join(lines) + "\n历史资料当时何时可得尚未核准。"
    status = "historical_only" if complete else "incomplete_historical"
    state_text = {"source_drift": "来源未核准", "missing": "读数缺失",
                  "ambiguous": "记录不唯一", "unavailable": "无可核对读数"}
    facts = [f"{item['label']}（{item['observation_date'] or '日期未知'}）："
             f"{item['value_text'] if item['status'] == 'historical_only' else state_text.get(item['status'], '资料未核准')}。"
             for item in items]
    return _pack(reply, status, "historical_observation", symbol=code,
                 title=f"{product['name']}（{code}）", refs=refs, sources=all_sources,
                 metadata=metadata, detail=detail, as_of=chosen_date if complete else None,
                 facts=facts,
                 presentation_conclusion=("同一因子多个版本需先选定；尚不能据此判断买入或卖出。" if version_conflict else
                                          "组合效果尚未评价，尚不能据此判断买入或卖出。" if complete else
                                          "多项资料未能同日核齐，尚不能据此判断买入或卖出。"))


def build_product_factor_reply(message: str, selected_symbol: str | None = None, *,
                               root: Path | None = None, product_catalog_path: Path | None = None,
                               factor_catalog_path: Path | None = None, panel_loader=None,
                               now: datetime | None = None) -> dict:
    base = (root or ROOT).resolve()
    now = now or datetime.now(ZoneInfo("Asia/Shanghai"))
    text = str(message or "")
    try:
        products, product_source = _load_products(base, product_catalog_path)
    except (AccessError, OSError, ValueError, TypeError, json.JSONDecodeError):
        return _pack("产品目录无法核对，暂不能关联因子材料。", "unavailable", "product_factor")
    by_code = {p["code"]: p for p in products}
    explicit_codes = {_norm_code(m.group(0)) for m in _CODE.finditer(text)}
    exact_names = {p["code"] for p in products
                   if p["name"] in text or any(alias in text for alias in p["aliases"])}
    named = explicit_codes | exact_names
    # A full product name may contain its broader topic; only exact identities win.
    if len(named) > 1:
        return _pack("问题提到多个产品，请一次明确一个产品代码。", "needs_clarification",
                     "product_factor", next_step="请给出一个基金或ETF代码。")
    if named:
        code = next(iter(named))
    else:
        broad = {p["code"] for p in products if any(term in text for term in p["ambiguous_terms"])}
        if broad:
            hints = "、".join(f"{by_code[c]['name']}（{c}）" for c in sorted(broad))
            return _pack(f"请明确是指数、ETF还是基金份额；已登记产品有{hints}。", "needs_clarification",
                         "product_factor", next_step="请给出准确产品代码和份额。")
        return _pack("请给出准确基金或ETF代码，再查看对应因子依据。", "needs_clarification",
                     "product_factor", next_step="请给出产品代码。")
    product = by_code.get(code)
    if product is None:
        return _pack("该产品身份未在本地目录核准，不能借其他产品的研究结果。", "unavailable",
                     "product_factor", symbol=code)
    selected = _norm_code(selected_symbol)
    metadata = {"product_identity": product["name"], "product_kind": product["kind"],
                "subject_source": "message", "selected_symbol_ignored": selected not in (None, code),
                "assembled_at": now.isoformat(), "assembled_at_role": "response_assembly_not_factor_calculation"}
    sources = [product_source, product["identity_source"]]
    if not product["factor_refs"]:
        conclusion = f"{product['name']}（{code}）目前没有接入专属因子研究结果，不能拿ETF或成分股结果代替。"
        return _pack(conclusion, "evidence_not_bound", "product_factor", symbol=code,
                     title=product["name"], sources=sources, metadata=metadata)
    if len(product["factor_refs"]) > 1:
        refs = product["factor_refs"]
        try:
            catalog = load_access_catalog(root=base, catalog_path=factor_catalog_path)
        except (AccessError, OSError, ValueError):
            return _pack("因子登记或接入索引无法核对。", "source_drift", "product_factor",
                         symbol=code, title=product["name"], refs=refs,
                         sources=sources, metadata=metadata)
        return _multi_factor_reply(product, refs, catalog, text, now, base,
                                   factor_catalog_path, sources, metadata)
    ref = product["factor_refs"][0]
    try:
        catalog = load_access_catalog(root=base, catalog_path=factor_catalog_path)
        material = read_materials(catalog, ref, root=base)
    except (AccessError, OSError, ValueError):
        return _pack("对应因子材料或来源指纹未通过核对，已停止解释。", "source_drift",
                     "product_factor", symbol=code, title=product["name"], refs=[ref],
                     sources=sources, metadata=metadata)
    query_date = list(dict.fromkeys(_DATE.findall(text)))
    if len(query_date) > 1:
        return _pack("请一次明确一个观察日期。", "needs_clarification", "product_factor",
                     symbol=code, title=product["name"], refs=[ref], sources=sources, metadata=metadata)
    if _CURRENT.search(text):
        # The old factor consumer owns live eligibility and currently refuses it.
        detail = build_factor_reply(f"{ref}现在的读数是多少？", code,
                                    panel_loader=panel_loader or (lambda: None), now=now,
                                    root=base, catalog_path=factor_catalog_path)
        return _pack(f"{product['name']}（{code}）的当前因子值尚不能核实。", "unqualified_current",
                     "current_observation", symbol=code, title=product["name"], refs=[ref],
                     sources=sources + detail["sources"], metadata=metadata,
                     detail=detail["reply"], next_step="可查看已封存历史证据，不能当作今天的读数。")
    observations = _observations(material, code)
    chosen_date = query_date[0] if query_date else max(
        (row["observation_date"] for _, row in observations), default=None)
    matches = [(packet, row) for packet, row in observations
               if row["observation_date"] == chosen_date]
    if len(matches) != 1:
        conclusion = ("没有可核对的该日因子读数。" if query_date else
                      "没有唯一的历史观察，暂不能给出读数。")
        return _pack(f"{product['name']}（{code}）：{conclusion}",
                     "unavailable" if not matches else "needs_clarification",
                     "historical_observation", symbol=code, title=product["name"],
                     refs=[ref], sources=sources, metadata=metadata,
                     next_step="请明确一个历史观察日期。" if not query_date else None)
    packet, row = matches[0]
    detail = build_factor_reply(f"{ref} entity_id={code} {chosen_date}对判断有什么帮助？", code,
                                panel_loader=panel_loader or (lambda: None), now=now,
                                root=base, catalog_path=factor_catalog_path)
    if detail["status"] != "historical_only":
        return _pack(f"{product['name']}（{code}）的历史读数尚不能核实。", detail["status"],
                     "historical_observation", symbol=code, title=product["name"],
                     refs=[ref], sources=sources + detail["sources"], metadata=metadata,
                     detail=detail["reply"])
    conclusion, brief, facts = _historical_conclusion(product, packet, row, material)
    metadata.update(detail["metadata"])
    return _pack(conclusion, "historical_only", "historical_observation", symbol=code,
                 title=f"{product['name']}（{code}）", facts=facts,
                 presentation_conclusion=brief, refs=[ref],
                 sources=sources + detail["sources"], metadata=metadata,
                 detail=detail["reply"], as_of=chosen_date)
