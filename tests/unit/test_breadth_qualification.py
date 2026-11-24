"""Same-day breadth qualification keeps sample evidence separate from full coverage."""

import hashlib
import importlib.util
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from lei_signal.market_context import a_share_breadth
from lei_signal.market_context.breadth_qualification import (
    merge_kline_series,
    qualify_breadth,
)


def _series(day: str, count: int = 210, *, rising: bool = True):
    closes = list(range(1, count + 1)) if rising else list(range(count, 0, -1))
    past = [
        (f"2025-{i // 31 + 1:02d}-{i % 31 + 1:02d}", float(close))
        for i, close in enumerate(closes[:-1])
    ]
    return past + [(day, float(closes[-1]))]


def test_one_latest_and_5208_old_cannot_claim_latest_market():
    codes = [f"sh{i:06d}" for i in range(5209)] + ["sz000001", "bj000001"]
    series = {symbol: _series("2026-10-15") for symbol in codes}
    series[codes[0]] = _series("2026-10-16")
    result = qualify_breadth(
        target_day="2026-10-16",
        codes=codes,
        code_sources={"sh": True, "sz": True, "bj": True},
        series_by_symbol=series,
    )
    assert result["same_day_available"] == 1
    assert result["missing"] == 5210
    assert result["eligible20"] == result["eligible50"] == result["eligible200"] == 1
    assert result["calculation_status"] == "verified_same_day_sample"
    assert result["status"] == "needs_check"
    assert "same_day_bars_missing" in result["reasons"]


def test_partial_exchange_source_never_qualifies_full_market():
    series = {symbol: _series("2026-10-16") for symbol in ("sh1", "sz1")}
    result = qualify_breadth(
        target_day="2026-10-16",
        codes=list(series),
        code_sources={"sh": True, "sz": True, "bj": False},
        series_by_symbol=series,
    )
    assert result["same_day_available"] == result["universe_total"] == 2
    assert result["universe_qualification"] == "partial_sources"
    assert result["status"] == "needs_check"
    assert "universe_sources_incomplete" in result["reasons"]


def test_full_same_day_with_independent_horizon_denominators():
    codes = ["sh1", "sz1", "bj1"]
    series = {
        "sh1": _series("2026-10-16", 210),
        "sz1": _series("2026-10-16", 55, rising=False),
        "bj1": _series("2026-10-16", 19),
    }
    result = qualify_breadth(
        target_day="2026-10-16",
        codes=codes,
        code_sources={"sh": True, "sz": True, "bj": True},
        series_by_symbol=series,
    )
    assert result["same_day_available"] == 3 and result["missing"] == 0
    assert (result["eligible20"], result["eligible50"], result["eligible200"]) == (2, 2, 1)
    assert (result["missing20"], result["missing50"], result["missing200"]) == (1, 1, 2)
    assert result["ma20_pct"] == result["ma50_pct"] == 50.0
    assert result["ma200_pct"] == 100.0
    assert result["calculation_status"] == "verified_same_day_sample"
    assert result["status"] == "needs_check"
    assert "incomplete_history_200" in result["reasons"]

    full = qualify_breadth(
        target_day="2026-10-16",
        codes=codes,
        code_sources={"sh": True, "sz": True, "bj": True},
        series_by_symbol={symbol: _series("2026-10-16") for symbol in codes},
    )
    assert full["status"] == "verified"
    assert full["coverage200"] == 1.0

    with_future = {symbol: _series("2026-10-16") + [("2026-10-19", 999.0)] for symbol in codes}
    historical = qualify_breadth(
        target_day="2026-10-16",
        codes=codes,
        code_sources={"sh": True, "sz": True, "bj": True},
        series_by_symbol=with_future,
    )
    assert historical["status"] == "verified"
    assert historical["ma200_pct"] == 100.0


def test_exact_price_boundary_excludes_equal_but_includes_real_increase():
    prices = [2.94] * 24 + [2.96] * 24 + [2.95, 2.95]
    # The exact 50-bar average is 2.95; binary-float summation can put it below 2.95.
    def reading(last: float):
        bars = [((date(2026, 8, 1) + timedelta(days=i)).isoformat(), close)
                for i, close in enumerate(prices[:-1])]
        bars.append(("2026-10-16", last))
        return qualify_breadth(
            target_day="2026-10-16", codes=["sh1"],
            code_sources={"sh": True, "sz": False, "bj": False},
            series_by_symbol={"sh1": bars},
        )

    equal = reading(2.95)
    assert equal["eligible50"] == 1 and equal["above50"] == 0
    truly_above = reading(2.9500000001)
    assert truly_above["above50"] == 1


def test_short_refresh_preserves_history_and_revisions_remain_unresolved():
    old = [(f"d{i:04d}", float(i + 1)) for i in range(2600)]
    new = old[-800:] + [("d2600", 2601.0)]
    merged, reason = merge_kline_series(old, new)
    assert reason is None and len(merged) == 2600
    assert merged[0] == old[1] and merged[-1] == ("d2600", 2601.0)
    revised = list(new)
    revised[0] = (revised[0][0], revised[0][1] * 0.9)
    retained, reason = merge_kline_series(old, revised)
    assert reason == "adjustment_revision" and retained == old
    assert merge_kline_series(old, [("new", 1.0)])[1] == "no_adjustment_anchor"


def test_fetch_uses_only_current_codes_and_respects_budget(monkeypatch):
    all_cache = {
        "sh1": _series("2026-10-15"),
        "sz1": _series("2026-10-16"),
        "bj1": _series("2026-10-16"),
        "sh999": _series("2026-10-16"),  # saved but absent from today's member list
    }
    monkeypatch.setattr(a_share_breadth, "load_qfq_kline_cache", lambda path: (all_cache, True))
    monkeypatch.setattr(a_share_breadth, "_fetch_kline", lambda symbol: None)
    result = a_share_breadth.fetch_ma_breadth(
        ["sh1", "sz1", "bj1"],
        target_day="2026-10-16",
        code_sources={"sh": True, "sz": True, "bj": True},
        max_fetch=0,
    )
    quality = result["qualification"]
    assert quality["universe_total"] == 3
    assert quality["same_day_available"] == 2
    assert quality["eligible200"] == 2
    assert quality["deferred_fetches"] == 1
    assert "fetch_budget_deferred" in quality["reasons"]
    assert quality["status"] == "needs_check"


def test_kline_fetch_does_not_substitute_unadjusted_or_backward_adjusted(monkeypatch):
    import requests

    calls = []

    class Response:
        def json(self):
            rows = [["2026-10-16", "2.9", "2.95"]] * 250
            return {"data": {"sz001239": {"day": rows, "hfqday": rows}}}

    def get(*args, **kwargs):
        calls.append(args)
        return Response()

    monkeypatch.setattr(requests, "get", get)
    assert a_share_breadth._fetch_kline("sz001239") is None
    assert len(calls) == 1


def test_partial_sources_never_fetch_and_old_history_is_untouched(monkeypatch, tmp_path):
    monkeypatch.setenv("LEI_CACHE_ROOT", str(tmp_path))
    monkeypatch.setattr(
        a_share_breadth, "load_qfq_kline_cache",
        lambda path: ({"sh1": _series("2026-10-16")}, True)
    )

    def unexpected_fetch(_symbol):
        raise AssertionError("partial source must not trigger a bulk refresh")

    monkeypatch.setattr(a_share_breadth, "_fetch_kline", unexpected_fetch)
    result = a_share_breadth.fetch_ma_breadth(
        ["sh1"], target_day="2026-10-16", code_sources={"sh": True, "sz": False, "bj": False}
    )
    assert result["qualification"]["status"] == "needs_check"
    history = tmp_path / "a_share_ma_breadth_history.json"
    history.write_text(json.dumps([{"date": "2026-10-16", "ma50_pct": 99.0}]))
    old_bytes = history.read_bytes()
    a_share_breadth.append_ma_breadth_history(10.0, 10.0, 10.0, trading_day="2026-10-16")
    assert history.read_bytes() == old_bytes
    a_share_breadth.save_ma_breadth_qualification(result["qualification"])
    sidecar = a_share_breadth.get_cached_ma_breadth_qualification()
    assert sidecar["target_day"] == "2026-10-16"
    assert sidecar["status"] == "needs_check"


def test_precompute_rejects_unqualified_without_overwriting_old_files(monkeypatch, tmp_path):
    script = Path(__file__).resolve().parents[2] / "scripts/precompute_a_share_ma.py"
    spec = importlib.util.spec_from_file_location("precompute_a_share_ma_under_test", script)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    monkeypatch.setenv("LEI_CACHE_ROOT", str(tmp_path))
    monkeypatch.setattr(sys, "argv", [str(script)])
    monkeypatch.setattr(
        module,
        "get_a_share_codes_with_status",
        lambda include_bj: {"codes": ["sh1", "sz1", "bj1"], "sources": {
            "sh": True, "sz": True, "bj": False
        }},
    )
    monkeypatch.setattr(
        module,
        "fetch_advance_decline",
        lambda codes: {"total": 2, "up": 1, "down": 1, "flat": 0, "bad": 1,
                       "limit_up": 0, "limit_down": 0},
    )
    quality = qualify_breadth(
        target_day="2026-10-16", codes=["sh1", "sz1", "bj1"],
        code_sources={"sh": True, "sz": True, "bj": False},
        series_by_symbol={"sh1": _series("2026-10-16")},
    )
    monkeypatch.setattr(
        module,
        "fetch_ma_breadth",
        lambda *args, **kwargs: {"trading_day": "2026-10-16", "qualification": quality},
    )
    snapshot = tmp_path / "a_share_ma_breadth.json"
    history = tmp_path / "a_share_ma_breadth_history.json"
    snapshot.write_text("old snapshot")
    history.write_text("old history")
    assert module.main() == 2
    assert snapshot.read_text() == "old snapshot"
    assert history.read_text() == "old history"
    sidecar = a_share_breadth.get_cached_ma_breadth_qualification()
    assert sidecar["status"] == "needs_check" and sidecar["applied_to_snapshot"] is False


def test_new_snapshot_keeps_quote_count_separate_from_ma_denominators(monkeypatch, tmp_path):
    monkeypatch.setenv("LEI_CACHE_ROOT", str(tmp_path))
    quality = qualify_breadth(
        target_day="2026-10-16",
        codes=["sh1", "sz1", "bj1"],
        code_sources={"sh": True, "sz": True, "bj": True},
        series_by_symbol={symbol: _series("2026-10-16") for symbol in ("sh1", "sz1", "bj1")},
    )
    assert a_share_breadth.save_ma_breadth_cache(
        quality["ma20_pct"], quality["ma50_pct"], quality["ma200_pct"],
        eligible=quality["eligible20"], total=2, trading_day="2026-10-16", qualification=quality,
    )
    saved = a_share_breadth.get_cached_ma_breadth()
    assert saved["total"] == saved["quote_parsed"] == 2
    assert saved["quote_expected"] == saved["breadth_universe_total"] == 3
    assert saved["ma_eligible200"] == 3
    assert saved["breadth_status"] == "verified"


def test_unproved_legacy_cache_never_skips_qfq_or_enters_qualified_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("LEI_CACHE_ROOT", str(tmp_path))
    old = tmp_path / "a_share_klines.parquet"
    symbols = ["sh1", "sz1", "bj1"]
    legacy = {symbol: _series("2026-10-16", rising=False) for symbol in symbols}
    assert a_share_breadth.save_kline_cache(legacy, old)
    old_bytes = old.read_bytes()
    calls = []

    def qfq(symbol):
        calls.append(symbol)
        return _series("2026-10-16")

    monkeypatch.setattr(a_share_breadth, "_fetch_kline", qfq)
    result = a_share_breadth.fetch_ma_breadth(
        symbols, target_day="2026-10-16",
        code_sources={"sh": True, "sz": True, "bj": True}, max_fetch=3,
    )
    assert calls == symbols  # Old prices dated today cannot skip qfq retrieval.
    assert result["qualification"]["status"] == "verified"
    assert result["qualification"]["above50"] == 3  # The old descending series is excluded.
    assert old.read_bytes() == old_bytes
    proved = tmp_path / "a_share_klines_qfq.parquet"
    qualified, valid = a_share_breadth.load_qfq_kline_cache(proved)
    assert valid and set(qualified) == set(symbols)
    assert result["qualification"]["price_adjustment"] == "qfqday"
    assert result["qualification"]["price_provenance"] == "qfq_cache_v1"
    assert result["qualification"]["price_source_ref"] == (
        "https://proxy.finance.qq.com/ifzqgtimg/appstock/app/fqkline/get"
    )
    assert set(a_share_breadth.pd.read_parquet(proved)["schema_version"]) == {1}
    assert result["qualification"]["price_cache_sha256"] == hashlib.sha256(
        proved.read_bytes()
    ).hexdigest()

    # A later qfq-only refresh merges the proved cache without changing the legacy file.
    monkeypatch.setattr(
        a_share_breadth, "_fetch_kline",
        lambda symbol: _series("2026-10-16") + [("2026-10-19", 211.0)],
    )
    second = a_share_breadth.fetch_ma_breadth(
        symbols, target_day="2026-10-19",
        code_sources={"sh": True, "sz": True, "bj": True}, max_fetch=3,
    )
    assert second["qualification"]["status"] == "verified"
    assert old.read_bytes() == old_bytes
    after, valid = a_share_breadth.load_qfq_kline_cache(proved)
    assert valid and all(after[s][-1] == ("2026-10-19", 211.0) for s in symbols)


def test_explicit_legacy_cache_path_is_not_overwritten_or_proved(monkeypatch, tmp_path):
    old = tmp_path / "old.parquet"
    assert a_share_breadth.save_kline_cache({"sh1": _series("2026-10-16")}, old)
    before = old.read_bytes()
    calls = []
    monkeypatch.setattr(
        a_share_breadth, "_fetch_kline",
        lambda symbol: calls.append(symbol) or _series("2026-10-16"),
    )
    result = a_share_breadth.fetch_ma_breadth(
        ["sh1", "sz1", "bj1"], target_day="2026-10-16",
        code_sources={"sh": True, "sz": True, "bj": True}, cache_path=old, max_fetch=3,
    )
    assert calls == ["sh1", "sz1", "bj1"]
    assert old.read_bytes() == before
    assert result["qualification"]["status"] == "needs_check"
    assert result["qualification"]["price_provenance"] == "unverified"
    assert "qfq_cache_provenance_unverified" in result["qualification"]["reasons"]


def test_only_known_invalidated_snapshot_date_is_hidden_and_invalidation_persists(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("LEI_CACHE_ROOT", str(tmp_path))
    quality = {"target_day": "2026-10-16", "status": "needs_check",
               "invalidates_legacy_dates": ["2026-10-16"]}
    assert a_share_breadth.save_ma_breadth_qualification(quality)
    assert a_share_breadth.save_ma_breadth_cache(1.0, 2.0, 3.0, trading_day="2026-10-16")
    assert a_share_breadth.get_cached_ma_breadth() is None
    # The next daily check must not silently make the proven bad legacy day visible again.
    assert a_share_breadth.save_ma_breadth_qualification(
        {"target_day": "2026-10-19", "status": "needs_check"}
    )
    assert a_share_breadth.get_cached_ma_breadth_qualification()["invalidates_legacy_dates"] == [
        "2026-10-16"
    ]
    assert a_share_breadth.get_cached_ma_breadth() is None
    # An unrelated historical date is unaffected.
    assert a_share_breadth.save_ma_breadth_cache(1.0, 2.0, 3.0, trading_day="2026-10-15")
    assert a_share_breadth.get_cached_ma_breadth()["date"] == "2026-10-15"


def test_invalidated_date_requires_matching_verified_correction(monkeypatch, tmp_path):
    monkeypatch.setenv("LEI_CACHE_ROOT", str(tmp_path))
    invalid = {"target_day": "2026-10-16", "status": "needs_check",
               "invalidates_legacy_dates": ["2026-10-16"]}
    assert a_share_breadth.save_ma_breadth_qualification(invalid)
    assert a_share_breadth.save_ma_breadth_cache(10.0, 20.0, 30.0, trading_day="2026-10-16")
    verified = {"target_day": "2026-10-16", "status": "verified",
                "applied_to_snapshot": True,
                "ma20_pct": 10.0, "ma50_pct": 20.0, "ma200_pct": 30.0,
                "eligible20": 3, "eligible50": 3, "eligible200": 3}
    assert a_share_breadth.save_ma_breadth_qualification(verified)
    assert a_share_breadth.get_cached_ma_breadth() is None  # legacy has no denominator proof
    assert a_share_breadth.save_ma_breadth_cache(
        10.0, 20.0, 30.0, trading_day="2026-10-16", qualification=verified
    )
    assert a_share_breadth.get_cached_ma_breadth()["date"] == "2026-10-16"
