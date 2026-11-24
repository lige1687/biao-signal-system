"""The catalog exposes frozen research evidence without inventing live readings."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from lei_signal.copilot import factor_readonly
from lei_signal.research import factor_access


SOURCE_ROOT = factor_access.ROOT
CATALOG_PATH = Path(__file__).resolve().parents[2] / "configs/factor-access.v1.json"
RAW = SOURCE_ROOT / "docs/experiments/raw/price-volume-universe-qualification-2026-10-04"
FAMILIES = {
    "price-only-six-candidate-comparison.json": 6,
    "quantity-twelve-candidate-comparison.json": 12,
}


def _catalog_json():
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _family_rows():
    for filename in FAMILIES:
        summary = json.loads((RAW / filename).read_text(encoding="utf-8"))
        for row in summary["table"]:
            yield filename, row


def test_frozen_bindings_keep_original_three_and_add_exact_eighteen():
    index = _catalog_json()
    before_path = (
        CATALOG_PATH.parents[1]
        / "docs/experiments/raw/factor-evidence-integration-2026-10-12/factor-access.before.json"
    )
    baseline_path = before_path.with_name("baseline.json")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert hashlib.sha256(before_path.read_bytes()).hexdigest() == baseline[
        "configs/factor-access.v1.json"
    ]
    original = json.loads(before_path.read_text(encoding="utf-8"))
    assert index["bindings"][:3] == original["bindings"]
    assert index["comparisons"] == original["comparisons"]
    rows = list(_family_rows())
    assert len(rows) == 18
    expected_refs = {f"research.price_volume.{row['candidate']}@1.0.0" for _, row in rows}
    added = index["bindings"][3:]
    assert len(added) == len(expected_refs)
    assert {binding["reference"] for binding in added} == expected_refs
    assert len({alias for binding in added for alias in binding["aliases"]}) == 18
    assert all(binding["kind"] == "registered" for binding in added)
    observed = [binding for binding in added if binding["batches"]]
    assert [binding["reference"] for binding in observed] == ["research.price_volume.range_mean20@1.0.0"]
    assert len(observed[0]["batches"]) == 1
    assert observed[0]["batches"][0]["path"] == (
        "docs/research/factor-observations/510300-range-mean20-20261012/packet.json"
    )
    registered = {
        (obj["id"], obj["version"])
        for obj in json.loads(
            (SOURCE_ROOT / "docs/research/definitions.v1.json").read_text(encoding="utf-8")
        )["objects"]
    }
    assert all((f"research.price_volume.{row['candidate']}", "1.0.0") in registered for _, row in rows)


def test_every_binding_has_real_sources_and_agrees_with_frozen_numbers():
    bindings = {item["reference"]: item for item in _catalog_json()["bindings"]}
    for filename, row in _family_rows():
        ref = f"research.price_volume.{row['candidate']}@1.0.0"
        binding = bindings[ref]
        assert len(binding["sources"]) == 2
        assert binding["sources"] == binding["evidence"][0]["sources"]
        paths = [source["path"] for source in binding["sources"]]
        assert paths[0].endswith("-eight-etf-2026-10-04.md")
        assert paths[1].endswith(filename)
        for source in binding["sources"]:
            actual = hashlib.sha256((SOURCE_ROOT / source["path"]).read_bytes()).hexdigest()
            assert source["sha256"] == actual
        b1, b2 = row["mse"]["B1"], row["mse"]["B2"]
        simple = row["mse"]["asset_mature_mean"]
        lo, hi = row["single_candidate_interval"]
        narrative = binding["evidence"][0]
        for number in (b1, b2, b1 - b2, simple, b2 - simple, lo):
            assert f"{number:.3f}" in narrative["summary"]
        assert (f"{hi:.4f}" if -0.0005 < hi < 0 else f"{hi:.3f}") in narrative["summary"]
        if lo <= 0 <= hi:
            assert "范围包含零" in narrative["summary"]
        elif lo > 0:
            assert "价格六项一并考虑后的范围容许变差" in narrative["summary"]
        else:
            assert "18项共同辅助检查仍容纳零" in narrative["summary"]
        assert f"{row['rows']}条ETF日期" in narrative["scope"]
        assert f"{row['dates']}个日期" in narrative["scope"]
        assert "20个收盘间隔" in narrative["scope"]
        assert "已见历史" in narrative["scope"]
        assert "不是买卖、账户收益、仓位或当前因子值" in narrative["limitations"][0]


def test_natural_question_explains_one_frozen_result_and_current_value_is_unavailable():
    options = {"root": SOURCE_ROOT, "catalog_path": CATALOG_PATH, "panel_loader": lambda: None}
    evidence = factor_readonly.build_factor_reply("20日平均日内波动的研究证据有用吗？", None, **options)
    assert evidence["status"] == "limited"
    assert evidence["definition_refs"] == ["research.price_volume.range_mean20@1.0.0"]
    assert "15.499" in evidence["reply"] and "14.058" in evidence["reply"]
    assert "不是买卖" in evidence["reply"]
    current = factor_readonly.build_factor_reply("20日平均日内波动现在的读数是多少？", None, **options)
    assert current["status"] == "unqualified_current"
    assert "不能把已有研究行当作当前值" in current["reply"]


def test_source_hash_drift_refuses_bound_explanation(monkeypatch):
    target = _catalog_json()["bindings"][3]
    report = SOURCE_ROOT / target["sources"][0]["path"]
    original_sha256 = factor_access._sha256

    def changed_report_digest(path):
        return "0" * 64 if path == report else original_sha256(path)

    monkeypatch.setattr(factor_access, "_sha256", changed_report_digest)
    result = factor_readonly.build_factor_reply(
        f"{target['label']}的研究证据有用吗？", None,
        root=SOURCE_ROOT, catalog_path=CATALOG_PATH, panel_loader=lambda: None,
    )
    assert result["status"] == "source_drift"
    assert "内容指纹不一致" in result["reply"]
