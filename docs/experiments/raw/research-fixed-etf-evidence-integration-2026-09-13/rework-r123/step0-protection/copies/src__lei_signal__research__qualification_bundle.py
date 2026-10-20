"""任务级证据包校验与 listing 证据桥接（fixed-etf-evidence-integration-2026-09-13）。

不是新的质量引擎，也不是第二份对象登记表：只做两件事——

1. :func:`validate_evidence_bundle`：对 Task 2 产出的任务级证据包做
   结构/来源/身份/事实字段校验。**不信任 ``facts_verified`` 自述值**——
   来源哈希与必需字段由本函数独立重查；校验失败的记录进 ``rejected``
   并带 record_id 与原因，不从报告中消失。
2. :func:`listing_evidence_from_validated`：把已校验的上市事实生成为
   既有 ``check_snapshot(..., listing_evidence=...)`` 验证器支持的桥接
   JSON（含原始公告路径/SHA/页码/抽取规则旁置字段）。桥接不"认证"事实：
   底层验证器对真实资格仍然恒为未授予（准入标准未建立）。
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path

FACT_TYPES = {"cash_dividend", "split", "listing", "trading_halt"}
_ALLOWED_FOR_VALUES = {
    "description", "fact_verification", "listing_evidence_bridge",
    "research_signal", "attribution",
}
_REQUIRED_TOP = {"schema_version", "synthetic", "records"}


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


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


def validate_evidence_bundle(bundle: dict, *, root: Path,
                             universe: set[str]) -> dict:
    """校验证据包；返回 validated/rejected/conflicts/unresolved。

    - 结构：必需顶层字段与逐记录字段齐全；
    - 来源：path 存在、sha256 实际重算一致（不采信自述）；
    - 身份：instrument_id 必须精确 ``.SS/.SZ`` 形式且在固定池内；
    - 事实：listing 必须有 ``listing_trade_date``；分红/拆分必须有
      ``event_id`` 且与冻结行动对得上由调用方另行比对；金额换算若给出
      则必须自洽（per_share == per_10/10）；日期字段相互矛盾即拒绝；
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
    if errors:
        return {"validated": [], "rejected": [{"record_id": None, "reasons": errors}],
                "conflicts": [], "unresolved": []}

    validated: list[dict] = []
    rejected: list[dict] = []
    unresolved: list[dict] = []
    seen_ids: dict[str, dict] = {}
    seen_fingerprints: dict[str, str] = {}

    for rec in bundle.get("records", []):
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

        source = rec.get("source") or {}
        src_path = source.get("path")
        src_sha = source.get("sha256")
        if not (isinstance(src_path, str) and src_path.strip()):
            reasons.append("来源缺少 path")
        elif not (isinstance(src_sha, str) and re.fullmatch(r"[0-9a-f]{64}", src_sha)):
            reasons.append("来源缺少合法 sha256（64 位十六进制）")
        else:
            p = (root / src_path) if not Path(src_path).is_absolute() else Path(src_path)
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

        te = rec.get("time_evidence") or {}
        if not isinstance(te, dict):
            reasons.append("time_evidence 不是对象")
        else:
            if te.get("available_at") is not None and not _tz_aware_or_none(
                    te.get("available_at")):
                reasons.append("time_evidence.available_at 必须为 null 或带时区时刻")
            for bound in ("published_date", "not_before", "not_after"):
                v = te.get(bound)
                if v is not None and not _iso_date(v):
                    reasons.append(f"time_evidence.{bound} 不是合法日期：{v!r}")
            if te.get("available_at") is not None:
                reasons.append("时间证据不得填写精确 available_at（只能记下界）")

        facts = rec.get("facts") or {}
        if rec.get("fact_type") == "listing":
            if not _iso_date(facts.get("listing_trade_date")):
                reasons.append("listing 记录缺少合法 listing_trade_date")
            kind = facts.get("effective_date_kind")
            if kind == "fund_establishment_not_listing":
                reasons.append("基金成立日不得冒充上市交易日")
        if rec.get("fact_type") in {"cash_dividend", "split"} and not rec.get("event_id"):
            reasons.append("分红/拆分记录缺少 event_id")
        per10, per1 = facts.get("cash_per_10_shares_announced"), facts.get(
            "cash_per_share_computed")
        if per10 is not None and per1 is not None:
            try:
                if abs(float(per10) / 10.0 - float(per1)) > 1e-9:
                    reasons.append("金额换算矛盾：per_share != per_10/10")
            except (TypeError, ValueError):
                reasons.append("金额字段不是数值")
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
        if not isinstance(locator, dict) or not (
                locator.get("page") or locator.get("section")):
            reasons.append("缺少原文定位（page/section）")

        allowed_for = rec.get("allowed_for") or []
        if not isinstance(allowed_for, list) or any(
                a not in _ALLOWED_FOR_VALUES for a in allowed_for):
            reasons.append(f"allowed_for 含未登记值：{allowed_for!r}")
        elif rec.get("facts_verified") is not True and allowed_for:
            reasons.append("facts_verified=false 的记录不得声明任何用途")

        fingerprint = json.dumps(rec, ensure_ascii=False, sort_keys=True)
        seen_fingerprints[rid] = fingerprint

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
                                    out_dir: Path) -> dict:
    """把已校验的 listing 记录生成为既有验证器支持的桥接文件与引用映射。

    桥接 JSON 除底层验证器读取的 ``symbol``/``listing_date``/``qualification``
    外，附带原始公告路径/SHA/定位/抽取规则等旁置字段（不影响底层校验）。
    返回 ``{symbol: {"source": {...}, "listing_date": ...}}``，可直接并入
    ``check_snapshot(..., listing_evidence=...)`` 的入参映射。
    """
    out_dir.mkdir(parents=True, exist_ok=False)
    mapping: dict[str, dict] = {}
    for rec in validated:
        if rec.get("fact_type") != "listing":
            continue
        instrument = rec["instrument_id"]
        bare = instrument.split(".")[0]
        trade_date = rec["facts"].get("listing_trade_date")
        bridge = {
            "symbol": bare,
            "listing_date": trade_date,
            "qualification": "task_verified_fact_only",
            "provenance": {
                "original_path": rec["source"]["path"],
                "original_sha256": rec["source"]["sha256"],
                "locator": rec.get("locator"),
                "extract_rule": ("task2_extract_facts.py：上市交易日取自官方"
                                 "上市(交易)公告书正文；区别于成立日/募集日"),
                "time_evidence": rec.get("time_evidence"),
                "limitations": rec.get("limitations", []),
            },
        }
        out_path = out_dir / f"listing-bridge-{bare}.json"
        out_path.write_text(
            json.dumps(bridge, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        mapping[instrument] = {
            "source": {"path": str(out_path), "sha256": _sha(out_path)},
            "listing_date": trade_date,
        }
    return mapping


__all__ = [
    "validate_evidence_bundle", "listing_evidence_from_validated",
    "FACT_TYPES",
]
