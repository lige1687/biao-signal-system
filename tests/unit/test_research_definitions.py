"""Research-only contracts; expected values are hand calculations, not copied engines."""

import importlib
import json
from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


def api():
    return importlib.import_module("lei_signal.research.definitions")


def prices(n=280):
    return pd.Series(np.arange(1.0, n + 1), index=pd.bdate_range("2020-01-01", periods=n))


def test_momentum_exact_endpoints_and_scale():
    p = prices()
    r = api().quote_features(p)
    assert np.isnan(r.momentum.iloc[251])
    assert r.momentum.iloc[252] == 232 / 1 - 1
    assert r.momentum.iloc[272] == 252 / 21 - 1
    pd.testing.assert_series_equal(r.momentum, api().quote_features(p * 100).momentum)


def test_valid_observations_halt_and_sma_equality():
    p = prices(201)
    p.iloc[30] = np.nan
    r = api().quote_features(p)
    assert r.loc[p.index[30]].isna().all()
    assert np.isnan(r.sma200.iloc[199])
    assert r.sma200.iloc[200] == (sum(range(1, 202)) - 31) / 200
    flat = api().quote_features(prices() * 0 + 10)
    assert flat.above200.iloc[-1] == 0
    assert flat.distance200.iloc[-1] == 0
    assert flat.recovered200.iloc[-1] == 1


def test_cross_is_event_not_level():
    a = api().trend_state(pd.Series([1.0, 1.0, 2.0, 2.0]), pd.Series([1.0, 1.0, 1.0, 1.0]))
    assert list(a.above) == [0, 0, 1, 1]
    assert list(a.cross_up.iloc[1:]) == [0, 1, 0]
    assert np.isnan(a.cross_up.iloc[0])


def test_rank_percent_average_current_included_and_threshold():
    r = api().historical_percentile(pd.Series([1.0, 2.0, 2.0, 4.0]), window=4, minimum=3)
    assert np.isnan(r.iloc[1])
    assert r.iloc[2] == pytest.approx(2.5 / 3)
    assert r.iloc[3] == 1
    assert api().select_mixed(
        {"b": 0.2, "a": 0.2, "c": 0.5},
        {"a": np.nan, "b": 0.799, "c": 0.8},
        {"a": 273, "b": 273, "c": 273},
        current_quotes={"a", "b", "c"},
    ) == ["a", "b"]
    assert api().select_mixed({"a": 1}, {"a": 0.1}, {"a": 272}, current_quotes={"a"}) == []
    assert api().equal_targets([], 0.75) == {}
    assert api().equal_targets(["a", "b"], 0.75) == {"a": 0.375, "b": 0.375}


def test_rv_is_sample_std_of_simple_returns():
    p = pd.Series([100.0, 110.0, 99.0, 99.0])
    r = api().realized_volatility(p, window=3)
    assert r.iloc[-1] == pytest.approx(0.1 * np.sqrt(252))


def test_common_breadth_new_listing_membership_and_missing():
    ix = pd.bdate_range("2020-01-01", periods=201)
    p = pd.DataFrame({"a": np.arange(1.0, 202), "b": 5.0, "new": np.nan}, index=ix)
    p.loc[ix[-1], "new"] = 6
    members = {d: ["a", "b"] for d in ix}
    members[ix[-1]] = ["a", "b", "new"]
    r = api().breadth(p, members, minimum_coverage=0.9)
    assert r.loc[ix[199], "b50"] == 0.5
    assert r.loc[ix[199], "b200"] == 0.5
    assert r.loc[ix[-1], "eligible"] == 2
    assert r.loc[ix[-1], "coverage"] == pytest.approx(2 / 3)
    assert r.loc[ix[-1], "missing_reason"] == "coverage_below_minimum"
    assert np.isnan(r.loc[ix[-1], "b50"])
    p.loc[ix[-1], ["a", "b"]] = np.nan
    r = api().breadth(p, members)
    assert r.iloc[-1].missing_reason == "no_eligible_quotes"
    assert np.isnan(r.iloc[-1].b200)
    r = api().breadth(p, {})
    assert r.iloc[-1].missing_reason == "membership_missing"


def test_breadth_threshold_units_delta_and_scale():
    assert [api().three_tier(x) for x in [0.4329, 0.433, 0.5669, 0.567]] == [1, 0.5, 0.5, 0]
    assert np.isnan(api().three_tier(np.nan))
    with pytest.raises(ValueError):
        api().three_tier(43.3)
    s = pd.Series([0.2] * 20 + [0.25])
    assert api().breadth_delta(s).iloc[-1] == pytest.approx(0.05)
    assert api().breadth_delta(s * 100, unit="percent").iloc[-1] == pytest.approx(5)


def test_actions_are_causal_and_not_double_counted():
    d = pd.date_range("2020-01-01", periods=4)
    p = pd.Series([100.0, 99.0, 49.5, 50.0], index=d)
    events = [
        dict(
            effective_date="2020-01-02",
            available_at="2020-01-01T12:00:00+08:00",
            type="cash_dividend",
            cash=1.0,
            event_id="d",
        ),
        dict(
            effective_date="2020-01-03",
            available_at="2020-01-02T12:00:00+08:00",
            type="split",
            ratio=2.0,
            event_id="s",
        ),
    ]
    r = api().economic_index(p, events)
    assert list(r.iloc[:3]) == [1, 1, 1]
    assert r.iloc[-1] == pytest.approx(50 / 49.5)
    future = dict(
        effective_date="2021-01-01",
        available_at="2020-12-30T00:00:00+08:00",
        type="split",
        ratio=10,
        event_id="future",
    )
    pd.testing.assert_series_equal(r, api().economic_index(p, events + [future]))
    bad = deepcopy(events)
    bad[0]["available_at"] = "2020-01-03T00:00:00+08:00"
    with pytest.raises(ValueError, match="available"):
        api().economic_index(p, bad)
    with pytest.raises(ValueError, match="duplicate"):
        api().economic_index(p, events + [events[0]])


def test_prefix_invariance_and_no_backfill():
    p = prices(850)
    cut = 450
    pd.testing.assert_frame_equal(
        api().quote_features(p).iloc[:cut], api().quote_features(p.iloc[:cut])
    )
    revised = p.copy()
    revised.iloc[0] *= 2
    assert (
        api().quote_features(p).momentum.iloc[252]
        != api().quote_features(revised).momentum.iloc[252]
    )


def test_concentration_denominator_and_overlap_rejected():
    assert api().concentration({"a": 20.0, "b": 30.0}, 100.0, {"a": "tech", "b": "tech"}) == {
        "product_weights": {"a": 0.2, "b": 0.3},
        "group_weights": {"tech": 0.5},
        "exposure": 0.5,
    }
    r = api().concentration(
        {"a": 20.0, "b": 30.0}, 100.0, {"a": "tech", "b": "tech"}, denominator="invested"
    )
    assert r["group_weights"]["tech"] == 1
    with pytest.raises(ValueError):
        api().concentration({"a": 20.0}, 100.0, {"a": ["tech", "growth"]})
    with pytest.raises(ValueError):
        api().concentration({"a": 120.0}, 100.0, {"a": "tech"})


def test_registry_resolution_dependencies_and_use():
    reg = api().load_registry()
    api().validate_registry(reg)
    c = api().resolve(reg, "mixed.momentum.raw@1.0.0", purpose="ranking")
    assert c["type"] == "feature"
    with pytest.raises(ValueError):
        api().resolve(reg, "mixed.momentum.raw@latest")
    with pytest.raises(ValueError):
        api().resolve(reg, "mixed.momentum.raw@1.0.0", purpose="production_trade")
    for mutation in ("duplicate", "version", "dependency", "required", "cycle", "use"):
        bad = deepcopy(reg)
        if mutation == "duplicate":
            bad["objects"].append(deepcopy(bad["objects"][0]))
        if mutation == "version":
            bad["objects"][0]["version"] = "latest"
        if mutation == "dependency":
            bad["objects"][0]["dependencies"] = ["missing@1.0.0"]
        if mutation == "required":
            del bad["objects"][0]["name"]
        if mutation == "cycle":
            bad["objects"][0]["dependencies"] = [
                bad["objects"][0]["id"] + "@" + bad["objects"][0]["version"]
            ]
        if mutation == "use":
            bad["objects"][0]["uses"] = ["production_trade"]
        with pytest.raises(ValueError):
            api().validate_registry(bad)


def test_manifest_accepts_explicit_matching_registry_path(tmp_path):
    reg = api().load_registry()
    snapshot = tmp_path / "frozen-registry.json"
    snapshot.write_bytes(api().REGISTRY.read_bytes())
    kwargs = dict(
        registry=reg,
        references=["mixed.momentum.raw@1.0.0"],
        code_files=[Path(__file__)],
        input_files=[Path(__file__)],
        data_cutoff="2020-12-01T15:00:00+08:00",
        available_at="2026-09-09T12:00:00+08:00",
        decision_at="2026-09-09T13:00:00+08:00",
        protocol=Path(__file__),
        pool_version="synthetic-v1",
        quality="synthetic",
    )
    m = api().make_manifest(registry_path=snapshot, **kwargs)
    assert m["registry_file"]["path"].endswith("frozen-registry.json")
    # default path behaviour is unchanged
    default = api().make_manifest(**kwargs)
    assert default["registry_file"]["path"].endswith("definitions.v1.json")


def test_manifest_rejects_registry_path_content_mismatch(tmp_path):
    reg = api().load_registry()
    other = tmp_path / "other.json"
    bad = deepcopy(reg)
    bad["objects"][0]["definition"]["parameters"] = {"tampered": True}
    other.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="exact bytes"):
        api().make_manifest(
            registry=reg,
            references=["mixed.momentum.raw@1.0.0"],
            code_files=[Path(__file__)],
            input_files=[Path(__file__)],
            data_cutoff="2020-12-01T15:00:00+08:00",
            available_at="2026-09-09T12:00:00+08:00",
            decision_at="2026-09-09T13:00:00+08:00",
            protocol=Path(__file__),
            pool_version="synthetic-v1",
            quality="synthetic",
            registry_path=other,
        )


def test_manifest_rejects_future_or_missing_identity():
    reg = api().load_registry()
    kwargs = dict(
        registry=reg,
        references=["mixed.momentum.raw@1.0.0"],
        code_files=[Path(__file__)],
        input_files=[Path(__file__)],
        data_cutoff="2020-12-01T15:00:00+08:00",
        available_at="2020-12-01T16:00:00+08:00",
        decision_at="2020-12-01T17:00:00+08:00",
        protocol=Path(__file__),
        pool_version="synthetic-v1",
        quality="synthetic",
    )
    m = api().make_manifest(**kwargs)
    assert m["definition_refs"] == ["mixed.momentum.raw@1.0.0"]
    assert m["inputs"][0]["sha256"]
    kwargs["available_at"] = "2020-12-02T00:00:00+08:00"
    with pytest.raises(ValueError):
        api().make_manifest(**kwargs)


@pytest.mark.parametrize("values", [[1.0, 0.0], [1.0, -1.0], [1.0, np.inf]])
def test_bad_prices_rejected(values):
    with pytest.raises(ValueError):
        api().quote_features(pd.Series(values))


def test_stale_monthly_snapshot_cannot_qualify():
    assert api().select_mixed({"a": 1.0}, {"a": 0.2}, {"a": 273}, current_quotes=set()) == []


def test_economic_index_timezone_aware_dates():
    p = pd.Series([10.0, 5.0], index=pd.date_range("2020-01-01", periods=2, tz="Asia/Shanghai"))
    ev = [
        dict(
            event_id="split",
            type="split",
            ratio=2,
            effective_date="2020-01-02",
            available_at="2020-01-01T20:00:00+08:00",
        )
    ]
    assert api().economic_index(p, ev).iloc[-1] == 1.0
    utc = p.copy()
    utc.index = utc.index.tz_convert("UTC")
    assert api().economic_index(utc, ev).iloc[-1] == 1.0
    naive = p.copy()
    naive.index = naive.index.tz_localize(None)
    assert api().economic_index(naive, ev).iloc[-1] == 1.0


def test_calculate_binds_definition_and_output_identity():
    r = api().calculate("mixed.momentum.raw@1.0.0", prices())
    assert r["reference"] == "mixed.momentum.raw@1.0.0"
    assert r["unit"] == "fraction"
    assert r["values"].iloc[252] == 231
    changed = api().load_registry()
    obj = next(c for c in changed["objects"] if c["id"] == "mixed.momentum.raw")
    obj["definition"]["parameters"]["skip_lag"] = 20
    with pytest.raises(ValueError, match="implementation"):
        api().calculate("mixed.momentum.raw@1.0.0", prices(), registry=changed)


@pytest.mark.parametrize(
    "change",
    [
        "empty_name",
        "bad_uses",
        "negative_tolerance",
        "bad_timezone",
        "empty_policy",
        "bad_source",
        "bad_standard",
        "bad_model",
    ],
)
def test_registry_rejects_malformed_contracts(change):
    bad = api().load_registry()
    if change == "empty_name":
        bad["objects"][0]["name"] = ""
    if change == "bad_uses":
        bad["objects"][0]["uses"] = "ranking"
    if change == "negative_tolerance":
        bad["profiles"]["mixed"]["validation"]["tolerance"]["absolute"] = -1
    if change == "bad_timezone":
        bad["profiles"]["mixed"]["time"]["timezone"] = "not/a/zone"
    if change == "empty_policy":
        next(c for c in bad["objects"] if "policy" in c)["policy"]["cash"] = ""
    if change == "bad_source":
        bad["sources"]["mixed_code"]["sha256"] = "unknown"
    if change == "bad_standard":
        bad["standard"] = "missing-definition-standard.md"
    if change == "bad_model":
        bad["models"] = [
            dict(
                id="wrong",
                version="1.0.0",
                dependent_return="cash.zero@1.0.0",
                factor_returns=["breadth.csi300.b200.common@1.0.0"],
                form="OLS",
                frequency="daily",
                window=252,
                risk_free="missing",
                currency="CNY",
                missing_alignment="inner",
                estimation="OLS",
                uncertainty="missing",
                status="not_authorized",
            )
        ]
    with pytest.raises(ValueError):
        api().validate_registry(bad)


def test_source_drift_is_detected(tmp_path):
    reg = api().load_registry()
    p = tmp_path / "source.txt"
    p.write_text("old")
    reg["sources"] = {"sample": {"path": "source.txt", "sha256": api().fingerprint(p)["sha256"]}}
    assert api().verify_sources(reg, root=tmp_path) == 1
    p.write_text("revised")
    with pytest.raises(ValueError, match="changed"):
        api().verify_sources(reg, root=tmp_path)


def test_trend_cross_uses_previous_valid_quote():
    r = api().trend_state(pd.Series([1.0, np.nan, 2.0]), pd.Series([1.0, np.nan, 1.0]))
    assert r.cross_up.iloc[-1] == 1
    assert np.isnan(r.cross_up.iloc[1])
    with pytest.raises(ValueError):
        api().historical_percentile(pd.Series([1.0, np.inf]))
