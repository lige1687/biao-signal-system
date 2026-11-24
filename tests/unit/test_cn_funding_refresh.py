"""Unit tests for incremental CN margin buy share live cache refresh."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path

from lei_signal.market_context import cn_funding_refresh as mod


def _repo_frozen() -> Path:
    return Path(__file__).resolve().parents[2] / "web/public/research/microstructure-observations-20261108/funding.json"


def test_read_cn_funding_falls_back_to_frozen_when_live_missing(tmp_path: Path) -> None:
    pkt = mod.read_cn_funding(cache=tmp_path)
    cards = {c["id"]: c for c in pkt["cards"]}
    assert cards["cn-margin-buy-share-a-stocks"]["points"][-1]["date"] == "2026-11-05"
    assert cards["cn-margin-buy-share-a-stocks"]["refreshMode"] == "snapshot"


def test_refresh_cn_funding_appends_only_new_sessions_and_preserves_frozen(tmp_path: Path) -> None:
    frozen = _repo_frozen()
    frozen_before = hashlib.sha256(frozen.read_bytes()).hexdigest()

    seen_days: list[str] = []

    def fake_fetcher(day: str, _work_dir: Path):
        seen_days.append(day)
        if day == "2026-11-06":
            return {
                "date": day,
                "value": 8.0,
                "shMarginBuyYuan": Decimal("40000000000"),
                "szMarginBuyYuan": Decimal("40000000000"),
                "shTurnoverYuan": Decimal("500000000000"),
                "szTurnoverYuan": Decimal("500000000000"),
                "shEligibleCount": 1680,
                "szEligibleCount": 1860,
                "shExcludedEtfCount": 330,
                "szExcludedEtfCount": 250,
                "shMarginRows": 2010,
                "szMarginRows": 2110,
            }
        # 2026-11-09 模拟休市或未披露，应跳过
        return None

    stage = tmp_path / "stage"
    cache = tmp_path / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    result = mod.refresh_cn_funding(stage, cutoff="2026-11-09", cache=cache, day_fetcher=fake_fetcher)

    assert seen_days == ["2026-11-06", "2026-11-09"]
    assert result["added"] == 1
    assert result["date"] == "2026-11-06"
    assert result["latest"] == 8.0

    # Frozen file must remain byte-for-byte identical.
    assert hashlib.sha256(frozen.read_bytes()).hexdigest() == frozen_before

    live = mod.read_cn_funding(cache=cache)
    cards = {c["id"]: c for c in live["cards"]}
    main = cards["cn-margin-buy-share-a-stocks"]
    ma20 = cards["cn-margin-buy-share-a-stocks-ma20"]
    assert main["refreshMode"] == "live"
    assert main["points"][-1] == {"date": "2026-11-06", "value": 8.0}
    assert ma20["points"][-1]["date"] == "2026-11-06"
    assert ma20["points"][-1]["value"] is not None
    assert len(main["percentiles"]) == len(main["points"])
    assert any(item["label"] == "源样本结束日" and item["value"] == "2026-11-06" for item in main["latestDetails"])
    # Existing live packet stays readable on incremental rerun without duplicate dates.
    dates = [p["date"] for p in main["points"]]
    assert dates == sorted(set(dates))


def test_sse_detail_url_supports_arbitrary_pages() -> None:
    url = mod._sse_detail_url("20261117", 3)
    assert "detailsDate=20261117" in url
    assert "pageHelp.pageNo=3" in url
    assert "pageHelp.endPage=3" in url
