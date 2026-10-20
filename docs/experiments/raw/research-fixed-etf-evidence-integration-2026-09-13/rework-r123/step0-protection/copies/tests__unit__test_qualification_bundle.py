"""qualification_bundle.py 的反例与正向测试（fixed-etf-evidence-integration Task 3）。

覆盖任务书反向矩阵：假路径/错哈希、同名错交易所、成立日冒充上市、无原文
定位、日期/金额矛盾、合成冒充真实、同 ID 冲突、重复记录、未验证用途不允许；
每个反向配合法正向。另对真实证据包（run 产物）做整体校验烟雾检查。
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
    listing_evidence_from_validated,
    validate_evidence_bundle,
)

UNIVERSE = {"515300.SS", "515050.SS", "159915.SZ"}


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _make_source(tmp_path: Path, name="orig.txt", content="官方公告原文内容\n", *,
                 synth_qualification=False) -> dict:
    if synth_qualification:
        content = json.dumps({"symbol": "515300", "listing_date": "2019-10-16",
                              "qualification": "synthetic_algorithm_test"})
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return {"path": str(p), "sha256": _sha_bytes(p.read_bytes())}


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
        "short_supporting_text": "将于 2019-10-16 上市",
        "time_evidence": {
            "kind": "published_date_bound", "available_at": None,
            "published_date": "2019-10-11", "not_before": None,
            "not_after": None, "timezone": "Asia/Shanghai",
            "basis": "公告日期下界",
        },
        "facts_verified": True,
        "historical_availability_verified": False,
        "allowed_for": ["listing_evidence_bridge"],
        "limitations": [],
    }
    rec.update(overrides)
    return rec


def _bundle(tmp_path: Path, records, *, synthetic=False) -> dict:
    tmp_path.mkdir(parents=True, exist_ok=True)
    for r in records:
        if r.get("source", {}).get("path") == "will-be-set":
            r["source"] = _make_source(tmp_path, f"{r['record_id']}.txt")
    return {"schema_version": "fixed-etf-evidence-bundle/1.0",
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
    a = _record(record_id="same", facts={"listing_trade_date": "2019-10-16"})
    b = _record(record_id="same", facts={"listing_trade_date": "2020-01-02"})
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
    rec = _record(facts_verified=False)  # 仍带 allowed_for
    result = validate_evidence_bundle(_bundle(tmp_path / "a", [rec]),
                                      root=tmp_path / "a", universe=UNIVERSE)
    assert result["validated"] == []
    assert any("不得声明任何用途" in r
               for r in result["rejected"][0]["reasons"])

    rec2 = _record(record_id="rec-2", facts_verified=False,
                   allowed_for=[])
    result2 = validate_evidence_bundle(_bundle(tmp_path / "b", [rec2]),
                                       root=tmp_path / "b", universe=UNIVERSE)
    assert result2["validated"] == []
    assert len(result2["unresolved"]) == 1
    assert result2["unresolved"][0]["record_id"] == "rec-2"


def test_forcing_facts_verified_true_cannot_skip_source_checks(tmp_path):
    """自述 facts_verified=true 不能越过来源/结构检查。"""
    rec = _record(source={"path": str(tmp_path / "ghost.txt"),
                          "sha256": "0" * 64})
    rec["facts_verified"] = True
    result = validate_evidence_bundle(_bundle(tmp_path, [rec]),
                                      root=tmp_path, universe=UNIVERSE)
    assert result["validated"] == []


def test_available_at_must_not_be_filled(tmp_path):
    rec = _record(time_evidence={
        "kind": "known", "available_at": "2019-10-11T10:00:00+08:00",
        "published_date": "2019-10-11", "not_before": None,
        "not_after": None, "timezone": "Asia/Shanghai", "basis": "x"})
    result = validate_evidence_bundle(_bundle(tmp_path, [rec]),
                                      root=tmp_path, universe=UNIVERSE)
    assert any("available_at" in r for r in result["rejected"][0]["reasons"])


# ---------------------------------------------------------------------------
# listing 桥接：生成物被既有验证器消费
# ---------------------------------------------------------------------------


def test_listing_bridge_round_trip(tmp_path):
    rec = _record()
    result = validate_evidence_bundle(_bundle(tmp_path / "b", [rec]),
                                      root=tmp_path / "b", universe=UNIVERSE)
    out_dir = tmp_path / "bridge"
    mapping = listing_evidence_from_validated(result["validated"], out_dir=out_dir)
    assert set(mapping) == {"515300.SS"}
    entry = mapping["515300.SS"]
    # 桥接文件哈希一致且内容含底层验证器所需字段
    doc = json.loads(Path(entry["source"]["path"]).read_text(encoding="utf-8"))
    assert doc["symbol"] == "515300"
    assert doc["listing_date"] == "2019-10-16"
    assert entry["listing_date"] == doc["listing_date"]
    assert doc["provenance"]["original_sha256"] == rec["source"]["sha256"]
    # 实际哈希与引用一致
    actual = hashlib.sha256(
        Path(entry["source"]["path"]).read_bytes()).hexdigest()
    assert actual == entry["source"]["sha256"]


# ---------------------------------------------------------------------------
# 真实证据包整体烟雾校验（Task 2 产物，只读）
# ---------------------------------------------------------------------------


REAL_BUNDLE = (ROOT / "docs/experiments/raw/"
               "research-fixed-etf-evidence-integration-2026-09-13/"
               "evidence-bundle.json")


def test_real_bundle_validates_with_expected_split():
    if not REAL_BUNDLE.exists():
        pytest.fail("真实证据包不存在（Task 2 未产出）")
    bundle = json.loads(REAL_BUNDLE.read_text(encoding="utf-8"))
    result = validate_evidence_bundle(bundle, root=ROOT, universe={
        "159652.SZ", "510300.SS", "512400.SS", "512890.SS", "513870.SS",
        "515050.SS", "515130.SS", "515170.SS", "515300.SS", "515880.SS",
        "516220.SS", "518850.SS", "562590.SS", "588000.SS"})
    ids_valid = {r["record_id"] for r in result["validated"]}
    ids_unres = {r["record_id"] for r in result["unresolved"]}
    assert len(ids_valid) + len(ids_unres) == len(bundle["records"])
    assert "515300-no-original-20251215" in ids_unres  # 无官方原文 → 未核
    assert "515050-listing-announcement" in ids_valid
    assert "562590-listing-announcement" in ids_valid
    assert result["rejected"] == []
