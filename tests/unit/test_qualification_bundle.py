"""qualification_bundle.py 的反例与正向测试（fixed-etf-evidence-integration
Task 3；主控复核 v1.3.0 §11.3 R1 返修后）。

覆盖任务书反向矩阵：假路径/错哈希、引用 PDF 哈希脱钩、事实篡改（指纹/
抽取输出双重失配）、NaN 金额、时间区间倒挂、文内时间字段缺失、片段与
文本来源脱钩、同名错交易所、成立日冒充上市、无原文定位、合成冒充真实、
同 ID 冲突、重复记录、未验证用途不允许；每个反向配合法正向。另对真实
证据包 v1.1（及旧 v1.0 包不再作为已核事实消费）做整体校验对照。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lei_signal.research.qualification_bundle import (  # noqa: E402
    fact_tuple_fingerprint,
    listing_evidence_from_validated,
    validate_evidence_bundle,
)

UNIVERSE = {"515300.SS", "515050.SS", "159915.SZ"}


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _make_source(tmp_path: Path, name="orig.txt", content="官方公告原文内容\n",
                 *, synth_qualification=False) -> dict:
    if synth_qualification:
        content = json.dumps({"symbol": "515300", "listing_date": "2019-10-16",
                              "qualification": "synthetic_algorithm_test"})
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return {"path": str(p), "sha256": _sha_bytes(p.read_bytes())}


def _make_extraction(tmp_path: Path, rec: dict, fields: list[str] | None = None) -> dict:
    """登记抽取输出文件并返回 fact_binding（测试上下文的已核绑定）。

    默认绑定集合 = facts 中实质字段 + 已核时间值
    ``time_evidence.published_date``（返修 S1）。
    """
    if fields is None:
        fields = [k for k in rec["facts"]
                  if k not in ("note", "field_checks", "effective_date_kind")]
        if rec.get("time_evidence", {}).get("published_date") is not None:
            fields = fields + ["time_evidence.published_date"]

    def field_value(r: dict, f: str):
        if f.startswith("time_evidence."):
            return (r.get("time_evidence") or {}).get(f.split(".", 1)[1])
        return r["facts"][f]

    entry = {f: field_value(rec, f) for f in fields}
    suffix = hashlib.sha256(
        json.dumps(entry, sort_keys=True, ensure_ascii=False)
        .encode("utf-8")).hexdigest()[:8]
    p = tmp_path / f"extraction-{rec['record_id']}-{suffix}.json"
    p.write_text(json.dumps({"schema_version": "task2-extraction/1.2",
                             "records": {rec["record_id"]: entry}},
                            ensure_ascii=False), encoding="utf-8")
    return {
        "method": "测试夹具抽取（独立测试上下文）",
        "extraction_output": {"path": str(p),
                              "sha256": _sha_bytes(p.read_bytes())},
        "fields": fields,
        "fingerprint": fact_tuple_fingerprint(
            rec["instrument_id"], rec["event_id"], rec["fact_type"], entry),
    }


def _record(**overrides) -> dict:
    rec = {
        "record_id": "rec-1",
        "instrument_id": "515300.SS",
        "fact_type": "listing",
        "event_id": "515300-listing",
        "facts": {
            "listing_trade_date": "2019-10-16",
            "note": "上市交易日，非基金成立日",
        },
        "source": {"path": "will-be-set", "sha256": "will-be-set"},
        "locator": {"page": 1, "section": "上市交易公告书"},
        "short_supporting_text": "官方公告原文内容",
        "source_fragments": ["官方公告原文"],
        "time_evidence": {
            "kind": "in_document_date_bound", "available_at": None,
            "published_date": "2019-10-11", "not_before": None,
            "not_after": None, "date_field": "公告落款及全文上网披露日期",
            "refers_to": "本上市交易公告书提示性公告全文",
            "bound": "not_later_than",
            "timezone": "Asia/Shanghai", "basis": "文内日期；合成测试登记"},
        "facts_verified": True,
        "historical_availability_verified": False,
        "allowed_for": ["listing_evidence_bridge"],
        "limitations": [],
        "fact_binding": "will-be-set",
    }
    rec.update(overrides)
    return rec


def _bundle(tmp_path: Path, records, *, synthetic=False) -> dict:
    tmp_path.mkdir(parents=True, exist_ok=True)
    for r in records:
        if r.get("source", {}).get("path") == "will-be-set":
            r["source"] = _make_source(tmp_path, f"{r['record_id']}.txt")
        if r.get("fact_binding") == "will-be-set":
            r["fact_binding"] = _make_extraction(tmp_path, r)
    return {"schema_version": "fixed-etf-evidence-bundle/1.2",
            "synthetic": synthetic, "records": records}


def test_valid_listing_record_passes(tmp_path):
    result = validate_evidence_bundle(_bundle(tmp_path, [_record()]),
                                      root=tmp_path, universe=UNIVERSE)
    assert len(result["validated"]) == 1
    assert result["rejected"] == []
    assert result["validated"][0]["record_id"] == "rec-1"


def test_missing_path_and_bad_hash_rejected(tmp_path):
    rec = _record()
    rec["source"] = {"path": str(tmp_path / "nope.txt"), "sha256": "0" * 64}
    result = validate_evidence_bundle(_bundle(tmp_path, [rec]),
                                      root=tmp_path, universe=UNIVERSE)
    assert result["validated"] == []
    assert any("不存在" in r for r in result["rejected"][0]["reasons"])

    rec2 = _record(record_id="rec-2")
    rec2["source"] = _make_source(tmp_path, "b.txt")
    rec2["source"]["sha256"] = "0" * 64
    result2 = validate_evidence_bundle(_bundle(tmp_path, [rec2]),
                                       root=tmp_path, universe=UNIVERSE)
    assert any("哈希不匹配" in r for r in result2["rejected"][0]["reasons"])


def test_referenced_pdf_hash_mismatch_rejected(tmp_path):
    """R1 反例：引用 PDF 的 pdf_sha256 与实际文件脱钩 → 拒绝。"""
    rec = _record()
    pdf = tmp_path / "orig.pdf"
    pdf.write_bytes(b"%PDF-1.4 real original")
    rec["source"] = _make_source(tmp_path, "r1-5.txt")
    rec["source"]["pdf_path"] = str(pdf)
    rec["source"]["pdf_sha256"] = "0" * 64  # 声明哈希与实际不符
    result = validate_evidence_bundle(_bundle(tmp_path, [rec]),
                                      root=tmp_path, universe=UNIVERSE)
    assert result["validated"] == []
    assert any("引用原件哈希不匹配" in r
               for r in result["rejected"][0]["reasons"])


def test_referenced_pdf_hash_verified_when_matching(tmp_path):
    """合法正向：引用 PDF 哈希一致 → 通过。"""
    rec = _record()
    pdf = tmp_path / "orig.pdf"
    pdf.write_bytes(b"%PDF-1.4 real original")
    rec["source"] = _make_source(tmp_path, "r1-5ok.txt")
    rec["source"]["pdf_path"] = str(pdf)
    rec["source"]["pdf_sha256"] = _sha_bytes(pdf.read_bytes())
    result = validate_evidence_bundle(_bundle(tmp_path, [rec]),
                                      root=tmp_path, universe=UNIVERSE)
    assert len(result["validated"]) == 1


def test_fact_tamper_detected_by_fingerprint_and_extraction(tmp_path):
    """R1 反例：原文不变而上市日期被改 → 指纹与抽取输出双重失配，拒绝。

    篡改发生在绑定登记之后（绑定保持原核验值），与真实消费顺序一致。"""
    bundle = _bundle(tmp_path, [_record()])
    bundle["records"][0]["facts"]["listing_trade_date"] = "2020-01-02"
    result = validate_evidence_bundle(bundle, root=tmp_path,
                                      universe=UNIVERSE)
    reasons = result["rejected"][0]["reasons"]
    assert any("事实指纹" in r for r in reasons)
    assert any("事实与已核抽取输出不一致" in r for r in reasons)


def test_amount_nan_rejected(tmp_path):
    """R1 反例：每10份与每份金额都改成字符串 NaN → 拒绝。"""
    rec = _record(fact_type="cash_dividend", event_id="d-1",
                  facts={"cash_per_10_shares_announced": "NaN",
                         "cash_per_share_computed": "NaN",
                         "announcement_sent_date": "2023-12-14",
                         "record_date": "2023-12-18", "ex_date": "2023-12-19",
                         "pay_date": "2023-12-22"})
    result = validate_evidence_bundle(_bundle(tmp_path, [rec]),
                                      root=tmp_path, universe=UNIVERSE)
    reasons = result["rejected"][0]["reasons"]
    assert any("有限数值" in r for r in reasons)


def test_negative_amount_rejected(tmp_path):
    rec = _record(fact_type="cash_dividend", event_id="d-2",
                  facts={"cash_per_10_shares_announced": "-0.6610",
                         "cash_per_share_computed": -0.0661,
                         "ex_date": "2023-12-19"})
    result = validate_evidence_bundle(_bundle(tmp_path, [rec]),
                                      root=tmp_path, universe=UNIVERSE)
    assert any("非负" in r for r in result["rejected"][0]["reasons"])


def test_verified_dividend_without_amount_rejected(tmp_path):
    """已核分红缺少金额字段 → 明确拒绝，不默认通过。"""
    rec = _record(fact_type="cash_dividend", event_id="d-3",
                  facts={"ex_date": "2023-12-19"},
                  fact_binding="will-be-set")
    # 绑定字段只登记 ex_date，事实本身声称已核却没有金额
    result = validate_evidence_bundle(_bundle(tmp_path, [rec]),
                                      root=tmp_path, universe=UNIVERSE)
    assert any("缺少金额字段" in r
               for r in result["rejected"][0]["reasons"])


def test_inverted_time_range_rejected(tmp_path):
    """R1 反例：not_before=2026-01-01 > not_after=2019-01-01 → 拒绝。"""
    te = dict(_record()["time_evidence"])
    te["not_before"] = "2026-01-01"
    te["not_after"] = "2019-01-01"
    rec = _record(time_evidence=te)
    result = validate_evidence_bundle(_bundle(tmp_path, [rec]),
                                      root=tmp_path, universe=UNIVERSE)
    assert any("区间倒挂" in r for r in result["rejected"][0]["reasons"])


def test_in_document_time_requires_field_refs_and_bound(tmp_path):
    """文内日期必须登记所指字段/文件与边界语义，缺一即拒绝。"""
    te = dict(_record()["time_evidence"])
    te.pop("date_field")
    rec = _record(time_evidence=te)
    result = validate_evidence_bundle(_bundle(tmp_path, [rec]),
                                      root=tmp_path, universe=UNIVERSE)
    assert any("date_field" in r for r in result["rejected"][0]["reasons"])


def test_unknown_time_kind_with_dates_rejected(tmp_path):
    te = {"kind": "unknown", "available_at": None,
          "published_date": "2019-10-11", "not_before": None,
          "not_after": None, "timezone": "Asia/Shanghai", "basis": "x"}
    rec = _record(time_evidence=te)
    result = validate_evidence_bundle(_bundle(tmp_path, [rec]),
                                      root=tmp_path, universe=UNIVERSE)
    assert any("kind=unknown" in r
               for r in result["rejected"][0]["reasons"])


def test_fragment_missing_from_text_source_rejected(tmp_path):
    """引用片段与文本来源脱钩 → 拒绝（引用不能脱离原文）。"""
    rec = _record()
    rec["source"] = _make_source(tmp_path, "frag.txt",
                                 content="与片段无关的内容\n")
    result = validate_evidence_bundle(_bundle(tmp_path, [rec]),
                                      root=tmp_path, universe=UNIVERSE)
    assert any("原文片段" in r for r in result["rejected"][0]["reasons"])


def test_wrong_exchange_suffix_rejected(tmp_path):
    rec = _record(instrument_id="515300.SZ")
    result = validate_evidence_bundle(_bundle(tmp_path, [rec]),
                                      root=tmp_path, universe=UNIVERSE)
    assert result["validated"] == []
    assert any("交易所" in r or "不在固定池" in r
               for r in result["rejected"][0]["reasons"])


def test_establishment_date_must_not_masquerade_as_listing(tmp_path):
    rec = _record(facts={"effective_date_kind": "fund_establishment_not_listing"})
    result = validate_evidence_bundle(_bundle(tmp_path, [rec]),
                                      root=tmp_path, universe=UNIVERSE)
    assert result["validated"] == []
    assert any("成立日" in r for r in result["rejected"][0]["reasons"])


def test_missing_locator_rejected(tmp_path):
    rec = _record(locator={})
    result = validate_evidence_bundle(_bundle(tmp_path, [rec]),
                                      root=tmp_path, universe=UNIVERSE)
    assert any("原文定位" in r for r in result["rejected"][0]["reasons"])


def test_bad_locator_page_rejected(tmp_path):
    rec = _record(locator={"page": "一", "section": "x"})
    result = validate_evidence_bundle(_bundle(tmp_path, [rec]),
                                      root=tmp_path, universe=UNIVERSE)
    assert any("page" in r for r in result["rejected"][0]["reasons"])


def test_contradictory_amounts_and_dates_rejected(tmp_path):
    rec = _record(fact_type="cash_dividend", event_id="d1",
                  facts={"cash_per_10_shares_announced": "0.6610",
                         "cash_per_share_computed": 0.0714,
                         "announcement_sent_date": "2023-12-20",
                         "ex_date": "2023-12-19"})
    result = validate_evidence_bundle(_bundle(tmp_path, [rec]),
                                      root=tmp_path, universe=UNIVERSE)
    reasons = result["rejected"][0]["reasons"]
    assert any("换算矛盾" in r for r in reasons)
    assert any("次序不成立" in r for r in reasons)


def test_synthetic_source_must_not_masquerade_as_real(tmp_path):
    rec = _record(source=_make_source(tmp_path, "s.json",
                                      synth_qualification=True))
    result = validate_evidence_bundle(
        _bundle(tmp_path, [rec], synthetic=False),
        root=tmp_path, universe=UNIVERSE)
    assert result["validated"] == []
    assert any("合成" in r for r in result["rejected"][0]["reasons"])


def test_conflicting_duplicate_ids_rejected(tmp_path):
    a = _record(record_id="same")
    b = _record(record_id="same")
    b["facts"]["listing_trade_date"] = "2020-01-02"
    result = validate_evidence_bundle(_bundle(tmp_path, [a, b]),
                                      root=tmp_path, universe=UNIVERSE)
    assert result["validated"] == []
    assert all("冲突" in e["reasons"][0] or "重复" in e["reasons"][0]
               for e in result["rejected"])


def test_exact_duplicate_rejected(tmp_path):
    a = _record()
    b = _record()
    result = validate_evidence_bundle(_bundle(tmp_path, [a, b]),
                                      root=tmp_path, universe=UNIVERSE)
    assert len(result["validated"]) == 1
    assert any("重复" in e["reasons"][0] for e in result["rejected"])


def test_unverified_facts_may_not_claim_use(tmp_path):
    """未核事实声明用途 → 拒绝；未声明用途 → 进入未核（unresolved）。"""
    rec = _record(facts_verified=False, fact_binding=None)
    result = validate_evidence_bundle(_bundle(tmp_path, [rec]),
                                      root=tmp_path, universe=UNIVERSE)
    assert result["validated"] == []
    assert any("不得声明任何用途" in r
               for r in result["rejected"][0]["reasons"])

    rec2 = _record(record_id="rec-2", facts_verified=False,
                   fact_binding=None, allowed_for=[])
    result2 = validate_evidence_bundle(_bundle(tmp_path / "b", [rec2]),
                                       root=tmp_path / "b", universe=UNIVERSE)
    assert result2["validated"] == []
    assert len(result2["unresolved"]) == 1
    assert result2["unresolved"][0]["record_id"] == "rec-2"


def test_verified_without_fact_binding_rejected(tmp_path):
    """已核记录没有事实绑定（核验方法/抽取输出/指纹）→ 拒绝。"""
    rec = _record(fact_binding=None)
    result = validate_evidence_bundle(_bundle(tmp_path, [rec]),
                                      root=tmp_path, universe=UNIVERSE)
    assert any("fact_binding" in r
               for r in result["rejected"][0]["reasons"])


def test_tampered_extraction_output_rejected(tmp_path):
    """抽取输出文件被改（哈希对不上登记）→ 拒绝。"""
    rec = _record()
    binding = _make_extraction(tmp_path, rec, ["listing_trade_date"])
    p = Path(binding["extraction_output"]["path"])
    p.write_text(json.dumps({"schema_version": "x", "records": {}}),
                 encoding="utf-8")  # 原地篡改
    rec["fact_binding"] = binding
    result = validate_evidence_bundle(_bundle(tmp_path, [rec]),
                                      root=tmp_path, universe=UNIVERSE)
    assert any("抽取输出哈希不匹配" in r
               for r in result["rejected"][0]["reasons"])


def test_available_at_must_not_be_filled(tmp_path):
    te = dict(_record()["time_evidence"])
    te["available_at"] = "2019-10-11T10:00:00+08:00"
    rec = _record(time_evidence=te)
    result = validate_evidence_bundle(_bundle(tmp_path, [rec]),
                                      root=tmp_path, universe=UNIVERSE)
    assert any("available_at" in r for r in result["rejected"][0]["reasons"])


def test_unknown_schema_version_rejected(tmp_path):
    bundle = _bundle(tmp_path, [_record()])
    bundle["schema_version"] = "fixed-etf-evidence-bundle/9.9"
    result = validate_evidence_bundle(bundle, root=tmp_path,
                                      universe=UNIVERSE)
    assert result["validated"] == []
    assert any("schema_version" in r["reasons"][0]
               for r in result["rejected"])


def test_s1_shrinking_fields_cannot_escape_verification(tmp_path):
    """S1 反例：把仍在消费的字段移出绑定并按剩余字段重算指纹 → 拒绝
    （消费必需集合固定，不能由输入删减）。"""
    bundle = _bundle(tmp_path, [_record()])
    rec = bundle["records"][0]
    shrunk = [f for f in rec["fact_binding"]["fields"]
              if f != "listing_trade_date"]
    entry = {f: (rec["time_evidence"]["published_date"]
                 if f == "time_evidence.published_date"
                 else rec["facts"][f]) for f in shrunk}
    rec["fact_binding"]["fields"] = shrunk
    rec["fact_binding"]["fingerprint"] = fact_tuple_fingerprint(
        rec["instrument_id"], rec["event_id"], rec["fact_type"], entry)
    result = validate_evidence_bundle(bundle, root=tmp_path,
                                      universe=UNIVERSE)
    assert any("消费必需字段未绑定" in r
               for r in result["rejected"][0]["reasons"])


def test_s1_time_value_tamper_detected(tmp_path):
    """S1 反例：只改已核时间值 published_date（原文/抽取输出不动）→
    指纹与抽取输出双重失配，拒绝。"""
    bundle = _bundle(tmp_path, [_record()])
    bundle["records"][0]["time_evidence"]["published_date"] = "2021-10-01"
    result = validate_evidence_bundle(bundle, root=tmp_path,
                                      universe=UNIVERSE)
    reasons = result["rejected"][0]["reasons"]
    assert any("事实指纹" in r for r in reasons)
    assert any("time_evidence.published_date" in r for r in reasons)


def test_s1_field_reorder_still_passes(tmp_path):
    """字段重排（集合语义）不影响校验：正常通过。"""
    rec = _record()
    bundle = _bundle(tmp_path, [rec])
    rec["fact_binding"]["fields"] = list(
        reversed(rec["fact_binding"]["fields"]))
    result = validate_evidence_bundle(bundle, root=tmp_path,
                                      universe=UNIVERSE)
    assert len(result["validated"]) == 1


def test_s1_split_record_missing_required_ex_date_rejected(tmp_path):
    """S1 反例（拆分日场景）：split 记录绑定缺 ex_date → 消费必需字段
    未绑定，拒绝（与主控 512890 反例同型）。"""
    rec = _record(fact_type="split", event_id="sp-1",
                  facts={"split_ratio_announced": "1:2",
                         "record_date": "2021-10-21", "ex_date": "2021-10-22"})
    bundle = _bundle(tmp_path, [rec])
    r = bundle["records"][0]
    shrunk = [f for f in r["fact_binding"]["fields"] if f != "ex_date"]
    entry = {f: (r["time_evidence"]["published_date"]
                 if f == "time_evidence.published_date" else r["facts"][f])
             for f in shrunk}
    r["fact_binding"]["fields"] = shrunk
    r["fact_binding"]["fingerprint"] = fact_tuple_fingerprint(
        r["instrument_id"], r["event_id"], r["fact_type"], entry)
    r["facts"]["ex_date"] = "2021-10-23"  # 篡改拆分日
    result = validate_evidence_bundle(bundle, root=tmp_path,
                                      universe=UNIVERSE)
    assert any("消费必需字段未绑定" in r_
               for r_ in result["rejected"][0]["reasons"])


# ---------------------------------------------------------------------------
# listing 桥接：用途与冲突消费条件（返修 R1）
# ---------------------------------------------------------------------------


def test_listing_bridge_round_trip(tmp_path):
    rec = _record()
    result = validate_evidence_bundle(_bundle(tmp_path / "b", [rec]),
                                      root=tmp_path / "b", universe=UNIVERSE)
    out_dir = tmp_path / "bridge"
    mapping, report = listing_evidence_from_validated(
        result["validated"], out_dir=out_dir)
    assert set(mapping) == {"515300.SS"}
    entry = mapping["515300.SS"]
    doc = json.loads(Path(entry["source"]["path"]).read_text(encoding="utf-8"))
    assert doc["symbol"] == "515300"
    assert doc["listing_date"] == "2019-10-16"
    assert entry["listing_date"] == doc["listing_date"]
    assert doc["provenance"]["original_sha256"] == rec["source"]["sha256"]
    assert doc["provenance"]["fact_fingerprint"] == \
        rec["fact_binding"]["fingerprint"]
    assert report["consumed"][0]["record_id"] == "rec-1"
    actual = hashlib.sha256(
        Path(entry["source"]["path"]).read_bytes()).hexdigest()
    assert actual == entry["source"]["sha256"]


def test_listing_bridge_excludes_without_bridge_purpose(tmp_path):
    """R1 反例：allowed_for=[] 的已核上市记录 → validated 但不生成桥接。"""
    rec = _record(allowed_for=[])
    result = validate_evidence_bundle(_bundle(tmp_path, [rec]),
                                      root=tmp_path, universe=UNIVERSE)
    assert len(result["validated"]) == 1  # 事实本身可以保持已核
    mapping, report = listing_evidence_from_validated(
        result["validated"], out_dir=tmp_path / "bridge")
    assert mapping == {}
    assert report["excluded_purpose"][0]["record_id"] == "rec-1"
    assert not any((tmp_path / "bridge").iterdir())


def test_listing_bridge_conflicting_dates_exclude_all(tmp_path):
    """R1 反例：同产品不同记录上市日期冲突 → 全部排除，后写不覆盖前写。"""
    a = _record(record_id="rec-a")
    b = _record(record_id="rec-b")
    b["facts"] = {"listing_trade_date": "2020-01-02", "note": "冲突记录"}
    # 独立绑定：b 的事实自成一条已核登记
    result = validate_evidence_bundle(_bundle(tmp_path, [a, b]),
                                      root=tmp_path, universe=UNIVERSE)
    assert len(result["validated"]) == 2  # 各自结构合法
    mapping, report = listing_evidence_from_validated(
        result["validated"], out_dir=tmp_path / "bridge")
    assert mapping == {}
    assert report["excluded_conflict"][0]["instrument_id"] == "515300.SS"
    assert sorted(report["excluded_conflict"][0]["record_ids"]) == [
        "rec-a", "rec-b"]


# ---------------------------------------------------------------------------
# 真实证据包整体校验（Task 2 v2 产物，只读；旧 v1.0 包不再作已核消费）
# ---------------------------------------------------------------------------

TASK_DIR = (ROOT / "docs/experiments/raw/"
            "research-fixed-etf-evidence-integration-2026-09-13")
REAL_BUNDLE_V12 = TASK_DIR / "evidence-bundle-v1.2.json"
REAL_BUNDLE_V11 = TASK_DIR / "evidence-bundle-v1.1.json"
REAL_BUNDLE_V10 = TASK_DIR / "evidence-bundle.json"
POOL = {"159652.SZ", "510300.SS", "512400.SS", "512890.SS", "513870.SS",
        "515050.SS", "515130.SS", "515170.SS", "515300.SS", "515880.SS",
        "516220.SS", "518850.SS", "562590.SS", "588000.SS"}


def test_real_bundle_v12_validates_with_expected_split():
    """真实 v1.2 包：已核时间值随消费必需字段一并绑定（返修 S1）。"""
    if not REAL_BUNDLE_V12.exists():
        pytest.fail("真实证据包 v1.2 不存在")
    bundle = json.loads(REAL_BUNDLE_V12.read_text(encoding="utf-8"))
    assert bundle["schema_version"] == "fixed-etf-evidence-bundle/1.2"
    from lei_signal.research.qualification_bundle import REQUIRED_BINDING_FIELDS

    result = validate_evidence_bundle(bundle, root=ROOT, universe=POOL)
    ids_valid = {r["record_id"] for r in result["validated"]}
    ids_unres = {r["record_id"] for r in result["unresolved"]}
    assert len(ids_valid) + len(ids_unres) == len(bundle["records"])
    assert "515300-no-original-20251215" in ids_unres
    assert result["rejected"] == []
    # 每条已核记录的绑定集合覆盖该类型的固定必需集合
    for r in result["validated"]:
        required = REQUIRED_BINDING_FIELDS[r["fact_type"]]
        assert set(required) <= set(r["fact_binding"]["fields"]), r["record_id"]
    # R3 登记修正保持：512890 文内日期与落款、515050 公布日
    r512890 = next(r for r in result["validated"]
                   if r["record_id"] == "512890-official-split")
    assert r512890["facts"]["record_date"] == "2021-10-21"
    assert r512890["facts"]["ex_date"] == "2021-10-22"
    assert r512890["time_evidence"]["published_date"] == "2021-10-25"
    r515050 = next(r for r in result["validated"]
                   if r["record_id"] == "515050-listing-announcement")
    assert r515050["time_evidence"]["published_date"] == "2019-10-11"
    assert r515050["facts"]["listing_trade_date"] == "2019-10-16"
    rec_ = bundle["summary"]["reconciliation"]
    assert rec_["frozen_actions_total"] == 21
    assert rec_["frozen_actions_in_bundle"] == 10
    assert rec_["bundle_action_records_with_official_original"] == 9
    assert rec_["listing_originals_missing_count"] == 12


def test_real_bundle_v11_no_longer_passes_time_unbound():
    """旧 v1.1 包（已核时间值未入绑定）在新接口下不得作为已核事实消费。"""
    if not REAL_BUNDLE_V11.exists():
        pytest.fail("真实证据包 v1.1 不存在")
    bundle = json.loads(REAL_BUNDLE_V11.read_text(encoding="utf-8"))
    result = validate_evidence_bundle(bundle, root=ROOT, universe=POOL)
    assert result["validated"] == []
    assert any("消费必需字段未绑定" in "; ".join(r["reasons"])
               for r in result["rejected"])


def test_real_bundle_v10_no_longer_passes_as_fact_verified():
    """旧 v1.0 包（无事实绑定）在收紧后的接口下不得作为已核事实消费。"""
    if not REAL_BUNDLE_V10.exists():
        pytest.fail("旧真实证据包不存在")
    bundle = json.loads(REAL_BUNDLE_V10.read_text(encoding="utf-8"))
    result = validate_evidence_bundle(bundle, root=ROOT, universe=POOL)
    assert result["validated"] == []
    assert any("fact_binding" in "; ".join(r["reasons"])
               for r in result["rejected"])
