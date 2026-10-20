"""任务级证据包校验与 listing 证据桥接（fixed-etf-evidence-integration-2026-09-13）。

不是新的质量引擎，也不是第二份对象登记表：只做两件事——

1. :func:`validate_evidence_bundle`：对任务级证据包做结构/来源/身份/事实
   校验。**不信任 ``facts_verified`` 自述值**——来源哈希、引用原件哈希、
   事实绑定（:func:`fact_tuple_fingerprint` + 抽取输出逐字段比对）、金额
   有限非负、拆分比例为正、时间区间先后、定位与容器类型都由本函数独立
   重查；校验失败的记录进 ``rejected`` 并带 record_id 与原因，不从报告
   中消失。"结构/哈希通过"与"事实已核"分开：已核记录必须携带
   ``fact_binding``（核验方法、抽取输出位置与哈希、被绑定字段、事实元组
   指纹），且绑定字段必须覆盖 :data:`REQUIRED_BINDING_FIELDS` 固定的
   消费必需集合（含已核时间字段 ``time_evidence.published_date``）——
   集合不能由输入删减；同一已核原文不变而产品/日期/金额/已核时间值被
   改动，指纹与抽取输出双重失配，该记录不得作为已核事实消费。
   **已核范围 = 绑定字段与固定必需集合的相符；不宣称所有原文事实
   都被机器自动证真。**
2. :func:`listing_evidence_from_validated`：把**显式获得
   ``listing_evidence_bridge`` 用途**且同产品无上市日期冲突的已核 listing
   记录，生成为既有 ``check_snapshot(..., listing_evidence=...)`` 验证器
   支持的桥接 JSON（含原始公告路径/SHA/页码/抽取规则旁置字段）。桥接不
   "认证"事实：底层验证器对真实资格仍然恒为未授予（准入标准未建立）。

时间证据（v1.1）：只登记**文内日期**（date_field 指明是哪个字段、
refers_to 指明该日期属于哪份文件/哪个事实、bound 指明不晚于/不早于/
仅成文），不伪造精确 ``available_at``；不把文内日期笼统宣称为
"真实公布下界"。
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date
from pathlib import Path

FACT_TYPES = {"cash_dividend", "split", "listing", "trading_halt"}
_ALLOWED_FOR_VALUES = {
    "description", "fact_verification", "listing_evidence_bridge",
    "research_signal", "attribution",
}
_REQUIRED_TOP = {"schema_version", "synthetic", "records"}
_KNOWN_SCHEMAS = {
    "fixed-etf-evidence-bundle/1.0", "fixed-etf-evidence-bundle/1.1",
    "fixed-etf-evidence-bundle/1.2",
}
_TIME_KINDS = {"in_document_date_bound", "unknown"}
_TIME_BOUNDS = {"not_later_than", "not_before", "document_dated"}

# 消费必需字段（返修 S1）：按本任务三类事实固定，绑定集合不得由输入任意
# 删减——从 fields 里删掉仍在消费的字段（如拆分日）并重算指纹不能逃过
# 核验。``time_evidence.published_date`` 是已核时间字段：改动已核时间值
# 同样必须与抽取依据比对，不能只验字符串格式。必需之外的已核字段允许
# 附加绑定；facts 中未绑定的字段视为未核，不得宣称所有原文事实已核。
REQUIRED_BINDING_FIELDS: dict[str, tuple[str, ...]] = {
    "listing": ("listing_trade_date", "time_evidence.published_date"),
    "cash_dividend": (
        "announcement_sent_date", "cash_per_10_shares_announced",
        "cash_per_share_computed", "record_date", "ex_date", "pay_date",
        "time_evidence.published_date",
    ),
    "split": (
        "split_ratio_announced", "record_date", "ex_date",
        "time_evidence.published_date",
    ),
}


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical_value(value):
    """指纹与逐字段比对的统一取值规范化：数值统一为浮点表示。"""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return repr(float(value))
    return value


def fact_tuple_fingerprint(instrument_id: str, event_id: str, fact_type: str,
                           fields: dict) -> str:
    """已核事实元组的固定指纹：改动产品/事件/任一绑定字段即失配。

    供抽取脚本在核验时登记、校验器在消费前重算；不是全文真实性证明，
    只绑定"这一条记录核验过的字段取值"。
    """
    payload = {
        "instrument_id": instrument_id,
        "event_id": event_id,
        "fact_type": fact_type,
        "fields": {k: _canonical_value(fields[k]) for k in sorted(fields)},
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True)
        .encode("utf-8")).hexdigest()


def _finite_number(value) -> float | None:
    """严格数值解析：bool/NaN/inf/不可解析一律 None（拒绝依据）。"""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        f = float(value)
        return f if math.isfinite(f) else None
    if isinstance(value, str) and value.strip():
        try:
            f = float(value.strip())
        except ValueError:
            return None
        return f if math.isfinite(f) else None
    return None


def _iso_date(value) -> bool:
    if not isinstance(value, str) or len(value) != 10:
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def _tz_aware_or_none(value) -> bool:
    if value is None:
        return True
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        import pandas as pd

        return pd.Timestamp(value).tzinfo is not None
    except (ValueError, TypeError):
        return False


def _resolve(root: Path, path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else root / p


def _check_time_evidence(te, reasons: list[str]) -> None:
    if not isinstance(te, dict):
        reasons.append("time_evidence 不是对象")
        return
    if te.get("available_at") is not None and not _tz_aware_or_none(
            te.get("available_at")):
        reasons.append("time_evidence.available_at 必须为 null 或带时区时刻")
    for bound in ("published_date", "not_before", "not_after"):
        v = te.get(bound)
        if v is not None and not _iso_date(v):
            reasons.append(f"time_evidence.{bound} 不是合法日期：{v!r}")
    if te.get("available_at") is not None:
        reasons.append("时间证据不得填写精确 available_at（只能记文内日期界）")
    kind = te.get("kind")
    if kind not in _TIME_KINDS:
        reasons.append(f"time_evidence.kind 未登记：{kind!r}")
        return
    if kind == "unknown":
        if any(te.get(k) is not None
               for k in ("published_date", "not_before", "not_after")):
            reasons.append("kind=unknown 时不得同时填写任何日期界")
        return
    # in_document_date_bound：文内日期必须登记字段指向与边界语义
    if not te.get("published_date"):
        reasons.append("in_document_date_bound 缺少文内日期 published_date")
    for key in ("date_field", "refers_to", "bound", "basis"):
        v = te.get(key)
        if not (isinstance(v, str) and v.strip()):
            reasons.append(f"time_evidence.{key} 缺少非空说明（文内日期必须"
                           "登记所指字段/文件与边界语义）")
    if te.get("bound") is not None and te.get("bound") not in _TIME_BOUNDS:
        reasons.append(f"time_evidence.bound 未登记：{te.get('bound')!r}")
    # 区间先后：互相矛盾即拒绝
    nb, na, pub = (te.get("not_before"), te.get("not_after"),
                   te.get("published_date"))
    if nb and na and nb > na:
        reasons.append(f"time_evidence 区间倒挂：not_before {nb} > not_after {na}")
    if pub and na and pub > na:
        reasons.append(f"time_evidence 矛盾：published_date {pub} 晚于 "
                       f"not_after {na}")
    if pub and nb and pub < nb:
        reasons.append(f"time_evidence 矛盾：published_date {pub} 早于 "
                       f"not_before {nb}")


def _field_value(rec: dict, field: str):
    """按字段名取记录值：``time_evidence.X`` 点路径取时间证据字段，
    其余取 facts 字段。"""
    if field.startswith("time_evidence."):
        return (rec.get("time_evidence") or {}).get(
            field.split(".", 1)[1])
    return (rec.get("facts") or {}).get(field)


def _check_fact_binding(rec: dict, rid: str, root: Path,
                        reasons: list[str]) -> None:
    """已核记录必须有可回查的事实绑定：抽取输出 + 指纹双重一致。

    绑定字段集合必须覆盖 :data:`REQUIRED_BINDING_FIELDS` 中该事实类型的
    全部消费必需字段（含已核时间字段）；缺必需字段即拒绝，不能靠删减
    fields 把仍在消费的字段变成未检查。
    """
    binding = rec.get("fact_binding")
    if not isinstance(binding, dict):
        reasons.append("已核事实缺少 fact_binding（核验方法/抽取输出/指纹）")
        return
    method = binding.get("method")
    if not (isinstance(method, str) and method.strip()):
        reasons.append("fact_binding.method 缺少非空核验方法说明")
    fields = binding.get("fields")
    if not (isinstance(fields, list) and fields
            and all(isinstance(f, str) and f.strip() for f in fields)):
        reasons.append("fact_binding.fields 必须为非空字段名列表")
        return
    fact_type = rec.get("fact_type") or ""
    required = REQUIRED_BINDING_FIELDS.get(fact_type, ())
    if required:
        missing_required = [f for f in required if f not in fields]
        if missing_required:
            reasons.append(
                f"消费必需字段未绑定：{missing_required}；"
                "必需集合固定，不能由输入删减")
    out_ref = binding.get("extraction_output") or {}
    out_path = out_ref.get("path")
    out_sha = out_ref.get("sha256")
    extraction = None
    if not (isinstance(out_path, str) and out_path.strip()):
        reasons.append("fact_binding.extraction_output 缺少 path")
    elif not (isinstance(out_sha, str)
              and re.fullmatch(r"[0-9a-f]{64}", out_sha)):
        reasons.append("fact_binding.extraction_output 缺少合法 sha256")
    else:
        p = _resolve(root, out_path)
        if not p.is_file():
            reasons.append(f"事实抽取输出不存在：{out_path}")
        elif _sha(p) != out_sha:
            reasons.append(
                f"事实抽取输出哈希不匹配（已变化或登记错误）：{out_path}")
        else:
            try:
                extraction = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                reasons.append(f"事实抽取输出不可读：{exc}")
    if isinstance(extraction, dict):
        entry = (extraction.get("records") or {}).get(rid)
        if not isinstance(entry, dict):
            reasons.append(f"抽取输出中没有记录 {rid} 的事实条目")
        else:
            for field in fields:
                if field not in entry:
                    reasons.append(f"抽取输出缺少字段 {field} 的登记值")
                    continue
                got, want = entry.get(field), _field_value(rec, field)
                if _canonical_value(got) != _canonical_value(want):
                    reasons.append(
                        f"事实与已核抽取输出不一致：{field} "
                        f"记录={want!r} vs 抽取={got!r}；改动后的事实"
                        "（含已核时间值）不得作为已核事实消费")
    fingerprint = binding.get("fingerprint")
    if not (isinstance(fingerprint, str)
            and re.fullmatch(r"[0-9a-f]{64}", fingerprint)):
        reasons.append("fact_binding.fingerprint 缺少合法指纹")
    else:
        recomputed = fact_tuple_fingerprint(
            rec.get("instrument_id") or "", rec.get("event_id") or "",
            fact_type, {f: _field_value(rec, f) for f in fields})
        if recomputed != fingerprint:
            reasons.append(
                "事实指纹与已核登记不一致（产品/日期/金额/已核时间值在"
                "核验后被改动）；该记录不得作为已核事实消费")


def _check_source_fragments(rec: dict, rid: str, root: Path,
                            reasons: list[str]) -> None:
    """已核记录必须登记原文片段锚点；文本类来源逐字核对存在。

    PDF 等二进制来源只登记片段（机器核对原件哈希，不解析正文）；
    文本类来源的片段必须逐字出现在来源文件内容中。
    """
    fragments = rec.get("source_fragments")
    if not (isinstance(fragments, list) and fragments
            and all(isinstance(x, str) and x.strip() for x in fragments)):
        reasons.append("已核记录缺少 source_fragments（原文片段锚点）")
        return
    src_path = (rec.get("source") or {}).get("path")
    if not (isinstance(src_path, str)
            and src_path.lower().endswith((".txt", ".md", ".csv"))):
        return
    p = _resolve(root, src_path)
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        reasons.append(f"原文片段核对无法读取来源：{exc}")
        return
    missing = [f for f in fragments if f not in content]
    if missing:
        reasons.append(
            f"原文片段在来源文本中未找到（引用与原文脱钩）：{missing}")


def validate_evidence_bundle(bundle: dict, *, root: Path,
                             universe: set[str]) -> dict:
    """校验证据包；返回 validated/rejected/conflicts/unresolved。

    - 结构/容器：schema_version 登记、records 为列表、逐记录必需字段；
    - 来源：path 存在、sha256 实际重算一致（不采信自述）；声明的
      ``pdf_path``/``pdf_sha256``（引用原件）同样实际重算核对；
    - 身份：instrument_id 必须精确 ``.SS/.SZ`` 形式且在固定池内；
    - 事实：listing 必须有 ``listing_trade_date``；分红/拆分必须有
      ``event_id``；已核分红金额必须有限且非负、已核拆分比例必须为正，
      出现即拒绝（NaN 字符串/缺字段不得默认通过）；日期字段相互矛盾
      即拒绝；时间区间先后矛盾（not_before/not_after/published_date）
      即拒绝；
    - 事实绑定：``facts_verified=true`` 的记录必须携带 ``fact_binding``，
      指纹重算与抽取输出逐字段比对双重一致，否则拒绝；
    - 合成冒充：bundle.synthetic=false 时，来源 JSON 含
      ``qualification=synthetic_algorithm_test`` 的记录拒绝；
    - 用途：``facts_verified=false`` 的记录 ``allowed_for`` 必须为空，
      且进入 ``unresolved`` 而非 ``validated``。
    """
    errors: list[str] = []
    if not isinstance(bundle, dict):
        return {"validated": [], "rejected": [{"record_id": None, "reasons": [
            "bundle 不是对象"]}], "conflicts": [], "unresolved": []}
    for key in _REQUIRED_TOP:
        if key not in bundle:
            errors.append(f"bundle 缺少必需字段 {key}")
    schema = bundle.get("schema_version")
    if schema is not None and schema not in _KNOWN_SCHEMAS:
        errors.append(f"bundle schema_version 未登记：{schema!r}")
    if errors:
        return {"validated": [], "rejected": [{"record_id": None, "reasons": errors}],
                "conflicts": [], "unresolved": []}
    if not isinstance(bundle.get("records"), list):
        return {"validated": [], "rejected": [{"record_id": None, "reasons": [
            "records 必须为列表"]}], "conflicts": [], "unresolved": []}

    validated: list[dict] = []
    rejected: list[dict] = []
    unresolved: list[dict] = []
    seen_ids: dict[str, dict] = {}

    for rec in bundle["records"]:
        rid = rec.get("record_id") if isinstance(rec, dict) else None
        reasons: list[str] = []

        if not isinstance(rec, dict) or not rid:
            rejected.append({"record_id": rid, "reasons": ["缺少 record_id 或记录不是对象"]})
            continue
        if rid in seen_ids:
            if seen_ids[rid] == rec:
                rejected.append({"record_id": rid,
                                 "reasons": ["重复记录（与先前记录完全相同）"]})
            else:
                rejected.append({"record_id": rid,
                                 "reasons": ["record_id 冲突：同 ID 不同内容，全部拒绝"]})
            continue
        seen_ids[rid] = rec

        for field in ("instrument_id", "fact_type", "event_id", "facts",
                      "source", "locator", "time_evidence"):
            if field not in rec:
                reasons.append(f"缺少必需字段 {field}")
        if reasons:
            rejected.append({"record_id": rid, "reasons": reasons})
            continue

        if rec.get("fact_type") not in FACT_TYPES:
            reasons.append(f"未知 fact_type：{rec.get('fact_type')!r}")
        instrument = rec.get("instrument_id")
        if not (isinstance(instrument, str)
                and re.fullmatch(r"\d{6}\.(SS|SZ)", instrument)):
            reasons.append(f"instrument_id 非精确带交易所身份：{instrument!r}")
        elif instrument not in universe:
            reasons.append(f"instrument_id 不在固定池内：{instrument!r}")

        # ---- 来源：主来源哈希 + 引用原件哈希都实际重算 ----
        source = rec.get("source") or {}
        src_path = source.get("path")
        src_sha = source.get("sha256")
        if not (isinstance(src_path, str) and src_path.strip()):
            reasons.append("来源缺少 path")
        elif not (isinstance(src_sha, str) and re.fullmatch(r"[0-9a-f]{64}", src_sha)):
            reasons.append("来源缺少合法 sha256（64 位十六进制）")
        else:
            p = _resolve(root, src_path)
            if not p.is_file():
                reasons.append(f"来源文件不存在：{src_path}")
            elif _sha(p) != src_sha:
                reasons.append(f"来源哈希不匹配：内容已变化，不得沿用 {src_sha[:12]}…")
            else:
                if p.suffix.lower() == ".json":
                    try:
                        doc = json.loads(p.read_text(encoding="utf-8"))
                        if (isinstance(doc, dict)
                                and doc.get("qualification") == "synthetic_algorithm_test"):
                            reasons.append(
                                "来源为显式合成记录，不得在 synthetic=false 的"
                                "证据包中冒充真实记录")
                    except json.JSONDecodeError:
                        pass  # 非 JSON 来源（PDF/TXT/CSV）由 facts 层核对
        pdf_path = source.get("pdf_path")
        pdf_sha = source.get("pdf_sha256")
        if pdf_path is not None or pdf_sha is not None:
            if not (isinstance(pdf_path, str) and pdf_path.strip()
                    and isinstance(pdf_sha, str)
                    and re.fullmatch(r"[0-9a-f]{64}", pdf_sha)):
                reasons.append("引用原件 pdf_path/pdf_sha256 必须成对且合法")
            else:
                pp = _resolve(root, pdf_path)
                if not pp.is_file():
                    reasons.append(f"引用原件不存在：{pdf_path}")
                elif _sha(pp) != pdf_sha:
                    reasons.append(
                        f"引用原件哈希不匹配：声明的 PDF 与实际文件不一致"
                        f"（{pdf_path}）；文本引用不能脱离原件")

        _check_time_evidence(rec.get("time_evidence"), reasons)

        facts = rec.get("facts") or {}
        verified = rec.get("facts_verified") is True
        if rec.get("fact_type") == "listing":
            if not _iso_date(facts.get("listing_trade_date")):
                reasons.append("listing 记录缺少合法 listing_trade_date")
            elif verified:
                _check_fact_binding(rec, rid, root, reasons)
                _check_source_fragments(rec, rid, root, reasons)
            kind = facts.get("effective_date_kind")
            if kind == "fund_establishment_not_listing":
                reasons.append("基金成立日不得冒充上市交易日")
        elif rec.get("fact_type") in {"cash_dividend", "split"}:
            if not rec.get("event_id"):
                reasons.append("分红/拆分记录缺少 event_id")
            per10 = facts.get("cash_per_10_shares_announced")
            per1 = facts.get("cash_per_share_computed")
            if per10 is not None or per1 is not None:
                f10, f1 = _finite_number(per10), _finite_number(per1)
                if f10 is None or f1 is None:
                    reasons.append(
                        f"金额字段必须是有限数值：per_10={per10!r} "
                        f"per_share={per1!r}（NaN/非数值不得通过）")
                else:
                    if f10 < 0 or f1 < 0:
                        reasons.append("分红金额必须非负")
                    if abs(f10 / 10.0 - f1) > 1e-9:
                        reasons.append("金额换算矛盾：per_share != per_10/10")
            elif verified and rec.get("fact_type") == "cash_dividend":
                reasons.append("已核分红记录缺少金额字段（缺必需字段即未核，"
                               "不得默认通过）")
            if rec.get("fact_type") == "split":
                ratio = facts.get("split_ratio_announced")
                if ratio is not None:
                    m = re.fullmatch(r"1\s*[：:]\s*(\d+(?:\.\d+)?)",
                                     str(ratio))
                    n = float(m.group(1)) if m else None
                    if n is None or not math.isfinite(n) or n <= 0:
                        reasons.append(f"拆分比例必须是 1:N 且 N>0：{ratio!r}")
                elif verified:
                    reasons.append("已核拆分记录缺少拆分比例")
            if verified and rec.get("fact_type") in {
                    "cash_dividend", "split"}:
                _check_fact_binding(rec, rid, root, reasons)
                _check_source_fragments(rec, rid, root, reasons)
        dates = [facts.get(k) for k in ("record_date", "ex_date", "pay_date",
                                        "announcement_sent_date")
                 if facts.get(k) is not None]
        bad_dates = [d for d in dates if not _iso_date(d)]
        if bad_dates:
            reasons.append(f"日期字段非法：{bad_dates}")
        ordered = [d for d in (facts.get("announcement_sent_date"),
                               facts.get("record_date"), facts.get("ex_date"),
                               facts.get("pay_date")) if d]
        if ordered != sorted(ordered):
            reasons.append("日期相互矛盾：公告/登记/除息/发放次序不成立")
        locator = rec.get("locator") or {}
        if not isinstance(locator, dict):
            reasons.append("locator 不是对象")
        else:
            page, section = locator.get("page"), locator.get("section")
            if page is None and not (isinstance(section, str) and section.strip()):
                reasons.append("缺少原文定位（page/section）")
            if page is not None and (
                    isinstance(page, bool) or not isinstance(page, int)
                    or page < 1):
                reasons.append(f"locator.page 必须为正整数：{page!r}")

        allowed_for = rec.get("allowed_for") or []
        if not isinstance(allowed_for, list) or any(
                a not in _ALLOWED_FOR_VALUES for a in allowed_for):
            reasons.append(f"allowed_for 含未登记值：{allowed_for!r}")
        elif rec.get("facts_verified") is not True and allowed_for:
            reasons.append("facts_verified=false 的记录不得声明任何用途")

        if reasons:
            rejected.append({"record_id": rid, "reasons": reasons})
        elif rec.get("facts_verified") is True:
            validated.append(rec)
        else:
            unresolved.append({
                "record_id": rid,
                "reason": "结构/来源合法但事实未核（facts_verified=false）",
            })

    # 同 ID 内容冲突：该 ID 下全部记录不得消费；完全相同的重复保留首条。
    conflict_ids = {r["record_id"] for r in rejected
                    if any("冲突" in x for x in r["reasons"])}
    if conflict_ids:
        validated = [r for r in validated if r["record_id"] not in conflict_ids]
        unresolved = [r for r in unresolved if r["record_id"] not in conflict_ids]
        for rid in sorted(conflict_ids):
            rejected.append({
                "record_id": rid,
                "reasons": ["同 ID 冲突：该 ID 下全部记录不得消费（含首个）"],
            })

    return {
        "validated": validated,
        "rejected": rejected,
        "conflicts": list(bundle.get("conflicts", [])),
        "unresolved": unresolved,
    }


def listing_evidence_from_validated(validated: list[dict], *,
                                    out_dir: Path) -> tuple[dict, dict]:
    """把已校验 listing 记录生成为既有验证器支持的桥接文件与引用映射。

    消费条件（缺一即排除并留痕，不只是计数）：

    - 记录必须显式声明 ``listing_evidence_bridge`` 用途；
    - 同产品出现不同 record_id 且上市日期互相冲突时，该产品全部记录
      都不得进桥接（后写不得覆盖前写）。

    返回 ``(mapping, report)``：mapping 为
    ``{instrument_id: {"source": {...}, "listing_date": ...}}``；
    report 记录 consumed/excluded_purpose/excluded_conflict 逐条原因。
    """
    out_dir.mkdir(parents=True, exist_ok=False)
    by_symbol: dict[str, list[dict]] = {}
    report: dict[str, list] = {"consumed": [], "excluded_purpose": [],
                               "excluded_conflict": []}
    for rec in validated:
        if rec.get("fact_type") != "listing":
            continue
        if "listing_evidence_bridge" not in (rec.get("allowed_for") or []):
            report["excluded_purpose"].append({
                "record_id": rec["record_id"],
                "instrument_id": rec["instrument_id"],
                "reason": "未显式声明 listing_evidence_bridge 用途",
            })
            continue
        by_symbol.setdefault(rec["instrument_id"], []).append(rec)
    mapping: dict[str, dict] = {}
    for instrument, recs in by_symbol.items():
        dates = {r["facts"].get("listing_trade_date") for r in recs}
        if len(dates) > 1:
            report["excluded_conflict"].append({
                "instrument_id": instrument,
                "record_ids": sorted(r["record_id"] for r in recs),
                "dates": sorted(d for d in dates if d),
                "reason": ("同产品不同记录的上市日期互相冲突：全部排除，"
                           "后写不得覆盖前写"),
            })
            continue
        rec = recs[0]
        bare = instrument.split(".")[0]
        trade_date = rec["facts"].get("listing_trade_date")
        bridge = {
            "symbol": bare,
            "listing_date": trade_date,
            "qualification": "task_verified_fact_only",
            "provenance": {
                "record_id": rec["record_id"],
                "original_path": rec["source"]["path"],
                "original_sha256": rec["source"]["sha256"],
                "referenced_pdf": {
                    k: rec["source"][k]
                    for k in ("pdf_path", "pdf_sha256")
                    if k in rec["source"]},
                "locator": rec.get("locator"),
                "fact_fingerprint": (rec.get("fact_binding") or {})
                .get("fingerprint"),
                "extract_rule": ("task2_extract_facts_v2.py：上市交易日取自"
                                 "官方上市(交易)公告书正文；区别于成立日/募集日"),
                "time_evidence": rec.get("time_evidence"),
                "limitations": rec.get("limitations", []),
            },
        }
        out_path = out_dir / f"listing-bridge-{bare}.json"
        out_path.write_text(
            json.dumps(bridge, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")
        mapping[instrument] = {
            "source": {"path": str(out_path), "sha256": _sha(out_path)},
            "listing_date": trade_date,
        }
        report["consumed"].append({
            "record_id": rec["record_id"], "instrument_id": instrument,
            "listing_date": trade_date,
        })
    return mapping, report


__all__ = [
    "validate_evidence_bundle", "listing_evidence_from_validated",
    "fact_tuple_fingerprint", "FACT_TYPES", "REQUIRED_BINDING_FIELDS",
]
