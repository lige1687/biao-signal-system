# Round 4 Market Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an auditable, point-in-time market-context layer for A-share and U.S. breadth, index drawdown, NAAIM, and AAII without changing or blocking any Round 3 single-symbol technical signal.

**Architecture:** Build a new `lei_signal.market_context` package with independent domain types, point-in-time universe membership, breadth/drawdown/sentiment engines, storage, UI, and research joins. The existing `compose.pipeline`, `DayState`, `opportunity_stage`, structure IDs, and lifecycles remain authoritative and isolated; the UI displays market context beside technical state rather than feeding it back into the state machine.

**Tech Stack:** Python 3.11, pandas 2.x, numpy 2.x, SQLite, Streamlit, Plotly, pytest, ruff, mypy.

## Global Constraints

- Read `docs/superpowers/specs/2026-08-02-market-context-design.md` completely before editing.
- Work only on `recovery/lei-round2`; do not modify or merge `master`.
- Round 3 technical parameters, `DayState.opportunity_stage`, `structure_id`, and `lifecycle_id` are immutable for this feature.
- Market context is display/research only: no hard block, buy/sell instruction, position sizing, or automatic trading.
- Formal breadth uses point-in-time historical membership; current-membership backfills are `research_proxy` only.
- Missing, stale, conflicted, or low-coverage data must remain explicit and must never silently become `neutral`.
- NAAIM/AAII become visible only at their real `available_at`; no backward filling to the survey period.
- Do not scrape MacroMicro, Patreon, NAAIM, or AAII pages as a production data pipeline.
- Use TDD: every behavior change starts with a failing test that is demonstrated to fail for the intended reason.
- Preserve all existing tests and assertions. Do not add broad `noqa`, `type: ignore`, or exception swallowing.
- Create WIP commits after Tasks 2, 4, 6, 8, and 10 so a context reset can resume safely.

---

## File Structure

Create:

```text
src/lei_signal/market_context/__init__.py
src/lei_signal/market_context/types.py
src/lei_signal/market_context/mapping.py
src/lei_signal/market_context/universe.py
src/lei_signal/market_context/data_sources.py
src/lei_signal/market_context/breadth.py
src/lei_signal/market_context/drawdown.py
src/lei_signal/market_context/classifier.py
src/lei_signal/market_context/sentiment.py
src/lei_signal/market_context/storage.py
src/lei_signal/market_context/pipeline.py
src/lei_signal/research/market_context.py
src/lei_signal/ui/market_context.py
tests/unit/test_market_context_types.py
tests/unit/test_market_mapping.py
tests/unit/test_universe_point_in_time.py
tests/unit/test_market_context_data_sources.py
tests/unit/test_market_breadth.py
tests/unit/test_market_context_classifier.py
tests/unit/test_market_sentiment.py
tests/unit/test_market_context_storage.py
tests/integration/test_market_context_pipeline.py
tests/integration/test_market_context_isolation.py
tests/integration/test_market_context_research.py
tests/integration/test_market_context_ui.py
tests/integration/test_market_context_real_replay.py
scripts/round4_repro/repro1_point_in_time_membership.py
scripts/round4_repro/repro2_context_does_not_block.py
scripts/round4_repro/repro3_release_time_alignment.py
ROUND4_DELIVERY_REPORT.md
```

Modify only where required:

```text
src/lei_signal/storage/sqlite_store.py       register migration 006 or delegate it safely
src/lei_signal/ui/app.py                     add the independent market-context page
src/lei_signal/ui/charts.py                  add breadth/drawdown charts
src/lei_signal/research/__init__.py           export market-context research helpers
README.md                                    document Round 4 scope and data inputs
```

Do not move existing Round 3 files or refactor the single-symbol state machine.

---

### Task 1: Domain Types and Reference-Market Mapping

**Files:**
- Create: `src/lei_signal/market_context/__init__.py`
- Create: `src/lei_signal/market_context/types.py`
- Create: `src/lei_signal/market_context/mapping.py`
- Test: `tests/unit/test_market_context_types.py`
- Test: `tests/unit/test_market_mapping.py`

**Interfaces:**
- Produces: `MarketId`, `ContextSummary`, `BreadthDirection`, `LongRegime`, `HeatState`, `ContextDataStatus`, `ContextSourceKind`, `UniverseSnapshot`, `BreadthSnapshot`, `MarketContextEvent`, `SentimentObservation`, `MarketContextSnapshot`, `MarketMapping`.
- Produces: `map_reference_markets(symbol: str, memberships: AbstractSet[MarketId] = frozenset()) -> MarketMapping`.

- [ ] **Step 1: Write failing type and mapping tests**

```python
def test_a_share_defaults_to_all_a_and_keeps_secondary_memberships() -> None:
    mapping = map_reference_markets(
        "300750.SZ",
        memberships={MarketId.CHINEXT, MarketId.CSI_300},
    )
    assert mapping.primary_market_id is MarketId.CN_ALL_A
    assert mapping.secondary_market_ids == (MarketId.CHINEXT, MarketId.CSI_300)


def test_chinext_etf_uses_tracking_index_as_primary() -> None:
    mapping = map_reference_markets("159915.SZ")
    assert mapping.primary_market_id is MarketId.CHINEXT
    assert mapping.secondary_market_ids == (MarketId.CN_ALL_A,)


def test_summary_enum_has_no_buy_or_sell_state() -> None:
    assert {item.value for item in ContextSummary} == {
        "tailwind", "neutral", "headwind", "unknown"
    }
```

- [ ] **Step 2: Run tests and confirm the intended import failures**

Run:

```bash
/opt/homebrew/bin/python3.11 -m pytest \
  tests/unit/test_market_context_types.py \
  tests/unit/test_market_mapping.py -q
```

Expected: FAIL because `lei_signal.market_context` does not exist.

- [ ] **Step 3: Implement focused immutable types**

Use `StrEnum` and frozen slot dataclasses. Required core shapes:

```python
class MarketId(StrEnum):
    CN_ALL_A = "CN_ALL_A"
    SSE_50 = "SSE_50"
    CSI_300 = "CSI_300"
    CSI_500 = "CSI_500"
    CSI_1000 = "CSI_1000"
    CHINEXT = "CHINEXT"
    SP500 = "SP500"
    NASDAQ_100 = "NASDAQ_100"
    RUSSELL_2000 = "RUSSELL_2000"


class ContextSummary(StrEnum):
    TAILWIND = "tailwind"
    NEUTRAL = "neutral"
    HEADWIND = "headwind"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class MarketMapping:
    symbol: str
    primary_market_id: MarketId | None
    secondary_market_ids: tuple[MarketId, ...]
    mapping_incomplete: bool
    reason_cn: str
```

`BreadthSnapshot` must carry each breadth value, eligible count, coverage, universe version, `as_of`, `available_at`, source kind, provenance, and data status. `MarketContextSnapshot` must keep raw dimensions plus `reasons` and `conflicts`; it must not contain `Stage`, `RiskState`, `structure_id`, or `lifecycle_id`.

- [ ] **Step 4: Implement deterministic mapping without network calls**

Use a versioned static ETF mapping for known ETF codes. For A-share individual stocks, make `CN_ALL_A` primary and sort all supplied secondary memberships by the declared enum order. Unknown symbols return `primary_market_id=None`, `mapping_incomplete=True`.

- [ ] **Step 5: Run the focused tests**

Expected: all Task 1 tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/lei_signal/market_context tests/unit/test_market_context_types.py \
  tests/unit/test_market_mapping.py
git commit -m "feat(round4): add market context domain types and mapping"
```

---

### Task 2: Point-in-Time Universe Membership

**Files:**
- Create: `src/lei_signal/market_context/universe.py`
- Test: `tests/unit/test_universe_point_in_time.py`
- Create: `scripts/round4_repro/repro1_point_in_time_membership.py`

**Interfaces:**
- Consumes: `MarketId`, `ContextSourceKind`.
- Produces: `UniverseMembershipProvider` protocol.
- Produces: `LocalUniverseProvider(root: str | Path)`.
- Produces: `load_universe_snapshot(provider, market_id, as_of) -> UniverseSnapshot`.

- [ ] **Step 1: Write exact point-in-time tests**

Create a fixture with member `AAA` effective through 2024-06-30 and member `BBB` effective from 2024-07-01. Assert:

```python
assert snapshot_on("2024-06-28").symbols == ("AAA",)
assert snapshot_on("2024-07-01").symbols == ("BBB",)
```

Also assert:

- a future membership row is invisible before `effective_from`;
- overlapping contradictory rows for the same symbol raise `UniverseConflictError`;
- current-constituent backfill returns `ContextSourceKind.RESEARCH_PROXY`;
- missing universe data raises `ContextDataUnavailableError`, not an empty universe.

- [ ] **Step 2: Run the new tests and confirm failure**

Expected: FAIL on missing provider and exceptions.

- [ ] **Step 3: Implement the provider protocol and local Parquet/CSV provider**

Required schema:

```text
universe_id,symbol,effective_from,effective_until,source,source_version,source_kind
```

Treat `effective_until` as an exclusive upper bound. Normalize dates without using future rows. `LocalUniverseProvider` reads `<root>/<market_id>.parquet` first, then `<root>/<market_id>.csv`; if neither exists, raise explicitly.

- [ ] **Step 4: Add overlap validation**

For each `(market_id, symbol)`, sort intervals and reject `next.effective_from < current.effective_until`. Permit adjacent intervals. Return symbols in stable sorted order and include a deterministic `universe_version` hash of the active rows.

- [ ] **Step 5: Add the independent reproduction script**

The script must print membership before and after the rebalance and prove that appending a future row does not change the earlier snapshot.

- [ ] **Step 6: Run focused tests and reproduction**

Expected: exact symbol tuples and stable historical hash.

- [ ] **Step 7: Commit the WIP checkpoint**

```bash
git add src/lei_signal/market_context/universe.py \
  tests/unit/test_universe_point_in_time.py \
  scripts/round4_repro/repro1_point_in_time_membership.py
git commit -m "wip(round4): add point-in-time universe membership"
```

---

### Task 3: Breadth Engine and Data Quality

**Files:**
- Create: `src/lei_signal/market_context/data_sources.py`
- Create: `src/lei_signal/market_context/breadth.py`
- Test: `tests/unit/test_market_context_data_sources.py`
- Test: `tests/unit/test_market_breadth.py`

**Interfaces:**
- Consumes: `UniverseSnapshot`, mapping of symbol to validated OHLCV frames, market sessions.
- Produces: `LocalMarketBarsProvider(component_root: Path, index_root: Path)` with
  `load_components(symbols, as_of)` and `load_index(market_id, as_of)`.
- Produces: `BreadthConfig(ma_windows=(20, 50, 200), minimum_coverage=0.90, stale_sessions=5, percentile_lookback=1260, percentile_min_periods=252)`.
- Produces: `compute_breadth_snapshot(*, universe: UniverseSnapshot, bars_by_symbol: Mapping[str, pd.DataFrame], sessions: pd.DatetimeIndex, as_of: date, config: BreadthConfig = BreadthConfig()) -> BreadthSnapshot`.
- Produces: `build_breadth_history(*, universe_provider: UniverseMembershipProvider, bars_provider: LocalMarketBarsProvider, market_id: MarketId, sessions: pd.DatetimeIndex, start: date, end: date, config: BreadthConfig = BreadthConfig()) -> pd.DataFrame`.

- [ ] **Step 1: Write local data-source contract tests**

The provider reads component files from `<component_root>/<symbol>.parquet` (CSV fallback)
and index files from `<index_root>/<market_id>.parquet` (CSV fallback). Assert that it:

- normalizes OHLCV through the existing `validate_bars` path;
- crops every frame at `as_of`;
- rejects unadjusted/invalid schemas instead of returning an empty frame;
- reports missing symbols separately so the breadth engine can calculate coverage;
- never discovers or loads a file for a symbol absent from the supplied universe snapshot.

- [ ] **Step 2: Implement `LocalMarketBarsProvider` minimally**

Return an immutable result containing `bars_by_symbol`, `missing_symbols`, source version,
and adjusted-data status. Do not make network calls and do not silently replace missing component
files with synthetic prices.

- [ ] **Step 3: Write formula and denominator tests**

Use four symbols where only three have 200 observations. Assert that Breadth20, Breadth50, and Breadth200 use different eligible denominators. Include exact expected percentages rather than non-empty assertions.

```python
assert snapshot.eligible_20 == 4
assert snapshot.eligible_50 == 4
assert snapshot.eligible_200 == 3
assert snapshot.breadth_200 == pytest.approx(2 / 3 * 100)
```

Add tests for:

- coverage 89% gives `DATA_INCOMPLETE` for that horizon and emits no cold event;
- a suspended constituent can reuse its last state for at most five market sessions and is marked stale;
- the sixth missing session excludes it and lowers coverage;
- moving averages use actual observed bars, not duplicated suspension-day bars;
- adding future bars cannot change an earlier `as_of` snapshot.

- [ ] **Step 4: Demonstrate failures before implementation**

Run both Task 3 test files; expected failure is missing functions, not malformed fixtures.

- [ ] **Step 5: Implement per-symbol eligibility and breadth calculation**

Crop every frame at `as_of`. For each MA window, require at least N actual observations. Determine staleness using positions in the supplied market-session index. Calculate `close > rolling(N).mean()` with no forward data.

- [ ] **Step 6: Implement coverage and provenance**

Coverage is `eligible_count / constituent_count`. Keep raw values even when coverage is low, but mark the horizon unusable and prevent classifier events from consuming it. Preserve source kind: formal, external check, or research proxy.

- [ ] **Step 7: Implement point-in-time percentiles**

For each day, compute rank within the trailing 1,260 observations ending that day, with 252 minimum observations. Insufficient history returns `NaN/unknown`, not 50th percentile.

- [ ] **Step 8: Run focused tests and commit**

```bash
git add src/lei_signal/market_context/data_sources.py \
  src/lei_signal/market_context/breadth.py \
  tests/unit/test_market_context_data_sources.py tests/unit/test_market_breadth.py
git commit -m "feat(round4): compute auditable market breadth"
```

---

### Task 4: Drawdown, Breadth Events, Direction, and Summary

**Files:**
- Create: `src/lei_signal/market_context/drawdown.py`
- Create: `src/lei_signal/market_context/classifier.py`
- Test: `tests/unit/test_market_context_classifier.py`

**Interfaces:**
- Produces: `compute_drawdown(index_bars: pd.DataFrame, as_of: date) -> float`.
- Produces: `classify_breadth(current: BreadthSnapshot, history: pd.DataFrame) -> MarketContextSnapshot`.
- Produces LEI threshold events with version `lei_market_breadth.v1`.

- [ ] **Step 1: Write precise threshold boundary tests**

Assert 15.0 and 85.0 are inclusive for extreme events, while Breadth200 exactly 50.0 is neither bull nor bear. Assert 14.999/85.001 on both sides. For A-share markets, each fixed-threshold event must have `Provenance.RESEARCH_PROXY` and evidence `threshold_origin="lei_threshold_research"`.

- [ ] **Step 2: Write summary direction tests**

Use exact 5-day deltas:

```text
B20 +2, B50 +1 -> tailwind / expanding
B20 -2, B50 -1 -> headwind / contracting
B20 +2, B50 -1 -> neutral / diverging
B20  0, B50 +1 -> neutral / diverging
coverage failure -> unknown
```

Assert Breadth200, drawdown, and sentiment can add reasons/conflicts but cannot change this v1 summary.

Also assert heat and divergence exactly:

```text
median(B20 percentile, B50 percentile) <=10 -> extreme_cold
<=25 -> cold
>=90 -> extreme_hot
>=75 -> hot
otherwise -> neutral
20-day index return >0 and both breadth deltas <0 -> negative divergence
20-day index return <0 and both breadth deltas >0 -> positive divergence
```

- [ ] **Step 3: Write point-in-time drawdown tests**

Future highs appended after `as_of` must not change the earlier drawdown. Use closing highs only, not intraday highs.

- [ ] **Step 4: Implement minimal deterministic classifiers**

Implement LEI events, long regime, heat state, direction, divergence, and summary exactly as the spec. Keep every rule version and evidence value in the resulting event.

- [ ] **Step 5: Run focused tests, then create checkpoint commit**

```bash
git add src/lei_signal/market_context/drawdown.py \
  src/lei_signal/market_context/classifier.py \
  tests/unit/test_market_context_classifier.py
git commit -m "wip(round4): classify breadth and drawdown context"
```

---

### Task 5: NAAIM and AAII Point-in-Time Sentiment

**Files:**
- Create: `src/lei_signal/market_context/sentiment.py`
- Test: `tests/unit/test_market_sentiment.py`
- Create: `scripts/round4_repro/repro3_release_time_alignment.py`

**Interfaces:**
- Produces: `load_naaim_observations(path: str | Path) -> tuple[SentimentObservation, ...]`.
- Produces: `load_aaii_observations(path: str | Path) -> tuple[SentimentObservation, ...]`.
- Produces: `latest_available_sentiment(observations: Sequence[SentimentObservation], decision_at: datetime, max_age_days: int) -> SentimentObservation | None`.
- Produces: `classify_sentiment_percentile(value: float, history: Sequence[float], *, min_periods: int = 52) -> str`.

- [ ] **Step 1: Write strict schema and release tests**

Required NAAIM columns:

```text
survey_week,available_at,exposure_index,source,license_status,publication_delay_days
```

Required AAII columns:

```text
survey_week,available_at,bullish,neutral,bearish,source,license_status
```

Tests must prove that an observation with `available_at=Thursday 07:00` is invisible Wednesday and visible at Thursday market close. Missing `available_at` must raise a validation error; it may not default to `survey_week`.

- [ ] **Step 2: Write stale and license tests**

- Timely licensed NAAIM uses 14 calendar days maximum age.
- AAII uses 10 calendar days maximum age.
- Public NAAIM data marked with a multi-month delay remains available for historical research but has `current_eligible=False`.
- Stale observations do not influence the current summary.

- [ ] **Step 3: Implement CSV/Parquet loaders only**

Do not add web scraping. Parse timezone-aware `available_at`, validate percentages sum to approximately 100 for AAII, calculate `bull_bear`, and calculate 20-observation moving averages using only previously available observations.

- [ ] **Step 4: Implement transparent percentile bands**

Use a versioned research classification: percentile `<=10` extreme low, `<=25` low, `>=90` extreme high, `>=75` high, otherwise neutral; fewer than 52 historical observations returns unknown. These labels remain independent and do not change breadth summary v1.

- [ ] **Step 5: Add the release-time reproduction script and commit**

The script must print the same observation as invisible before release and visible after release.

```bash
git add src/lei_signal/market_context/sentiment.py \
  tests/unit/test_market_sentiment.py \
  scripts/round4_repro/repro3_release_time_alignment.py
git commit -m "feat(round4): add point-in-time NAAIM and AAII inputs"
```

---

### Task 6: Independent Market-Context Storage

**Files:**
- Create: `src/lei_signal/market_context/storage.py`
- Modify: `src/lei_signal/storage/sqlite_store.py`
- Test: `tests/unit/test_market_context_storage.py`

**Interfaces:**
- Produces migration ordinal 6 with tables `universe_membership_versions`, `market_breadth_snapshots`, `market_context_events`, `sentiment_observations`, `market_context_assessments`.
- Produces `write_market_context(connection: sqlite3.Connection, snapshot: MarketContextSnapshot, events: Sequence[MarketContextEvent], *, run_id: str) -> WriteReport`.
- Produces `read_market_context_at(connection: sqlite3.Connection, market_id: MarketId, decision_at: datetime) -> MarketContextSnapshot | None`.

- [ ] **Step 1: Write migration and round-trip tests**

Assert exact table and index names, idempotent migration, JSON reason/conflict round-trip, and retrieval of the latest record satisfying `available_at <= decision_at`.

- [ ] **Step 2: Write revision-history tests**

Two revisions of the same source observation must coexist. A later revision must not overwrite the version that was visible at an earlier decision time.

- [ ] **Step 3: Implement migration 006**

Use append-only composite keys containing source version and `as_of/available_at`; never use `INSERT OR REPLACE` for source observations. Add indexes for `(market_id, as_of)` and `(series_id, available_at)`.

- [ ] **Step 4: Implement focused serializers/readers**

Keep storage code in `market_context/storage.py`; only register the migration through the existing migration mechanism. Do not add market-context columns to `signal_events` or `daily_assessments`.

- [ ] **Step 5: Run tests and create checkpoint commit**

```bash
git add src/lei_signal/market_context/storage.py \
  src/lei_signal/storage/sqlite_store.py \
  tests/unit/test_market_context_storage.py
git commit -m "wip(round4): persist market context point in time"
```

---

### Task 7: Market-Context Pipeline and Single-Symbol Isolation

**Files:**
- Create: `src/lei_signal/market_context/pipeline.py`
- Test: `tests/integration/test_market_context_pipeline.py`
- Test: `tests/integration/test_market_context_isolation.py`
- Create: `scripts/round4_repro/repro2_context_does_not_block.py`

**Interfaces:**
- Produces `MarketContextRequest` containing mapping, `as_of`, universe provider, bars by symbol, index bars, sessions, optional sentiment, and config.
- Produces `analyze_market_context(request: MarketContextRequest) -> tuple[MarketContextSnapshot, ...]`.
- Does not modify `AnalysisResult` or call `run_state_machine`.

- [ ] **Step 1: Write end-to-end synthetic pipeline tests**

Build a two-rebalance universe and deterministic component prices. Assert exact breadth values, events, summary, source kind, coverage, and reasons for two dates.

- [ ] **Step 2: Write the isolation gate before integration**

Run `analyze_bars()` once. Then run market context separately with tailwind, headwind, and unavailable inputs. Assert the serialized technical result is identical in all cases:

```python
baseline = [(s.day, s.opportunity_stage, s.observations) for s in technical.history]
assert baseline == after_tailwind == after_headwind == after_unknown
```

Also assert no market context type contains `structure_id` or `lifecycle_id`.

- [ ] **Step 3: Implement orchestration and graceful partial availability**

Each mapped market produces its own snapshot. A failure in a secondary market cannot erase the primary result. An unavailable primary market returns an explicit unknown snapshot with reasons, not an exception masquerading as no signal.

- [ ] **Step 4: Add the independent non-blocking reproduction**

Print the same technical stage under tailwind and headwind contexts and show only the context explanation changes.

- [ ] **Step 5: Run focused integration tests and commit**

```bash
git add src/lei_signal/market_context/pipeline.py \
  tests/integration/test_market_context_pipeline.py \
  tests/integration/test_market_context_isolation.py \
  scripts/round4_repro/repro2_context_does_not_block.py
git commit -m "feat(round4): orchestrate isolated market context"
```

---

### Task 8: Historical Research Join Without Filtering

**Files:**
- Create: `src/lei_signal/research/market_context.py`
- Modify: `src/lei_signal/research/__init__.py`
- Test: `tests/integration/test_market_context_research.py`

**Interfaces:**
- Consumes existing `build_forward_outcomes(result)` output.
- Produces `attach_market_context(outcomes, contexts, market_clock) -> pd.DataFrame`.
- Produces `summarize_outcomes_by_context(enriched) -> pd.DataFrame`.

- [ ] **Step 1: Write release-safe as-of join tests**

Create signals before and after the same sentiment release. Assert the earlier signal joins the previous context while the later signal joins the new context. Missing context must yield `context_summary="unknown"`, not neutral.

- [ ] **Step 2: Write preservation tests**

Assert row count, signal keys, returns, MFE, and MAE are unchanged after attaching context. Market context adds columns only; it cannot drop or select signals.

- [ ] **Step 3: Implement explicit market-close decision timestamps**

Use versioned market clocks: Asia/Shanghai 15:00 and America/New_York 16:00. Convert daily `available_date` into a timezone-aware decision timestamp, then use backward as-of join on `available_at`.

- [ ] **Step 4: Implement separate grouped summaries**

Group by signal key plus one context dimension at a time. Include sample count, mean direction-adjusted return, median, MFE, MAE, and missing rate. Do not output an optimized filter or “recommended threshold.”

- [ ] **Step 5: Run tests and checkpoint commit**

```bash
git add src/lei_signal/research/market_context.py \
  src/lei_signal/research/__init__.py \
  tests/integration/test_market_context_research.py
git commit -m "wip(round4): add non-filtering market context research"
```

---

### Task 9: Streamlit UI and Charts

**Files:**
- Create: `src/lei_signal/ui/market_context.py`
- Modify: `src/lei_signal/ui/app.py`
- Modify: `src/lei_signal/ui/charts.py`
- Test: `tests/integration/test_market_context_ui.py`

**Interfaces:**
- Produces `_render_market_context(contexts)` and Plotly breadth/drawdown figure builders.
- Consumes market-context result independently from `AnalysisResult`.

- [ ] **Step 1: Write rendering-recorder tests**

Capture Streamlit calls and assert the page displays primary/secondary market, summary, breadth values, coverage, drawdown, fixed threshold provenance, sentiment `available_at`, stale/license state, support reasons, conflicts, and the exact sentence “市场环境不改变该技术信号阶段”。

- [ ] **Step 2: Write failure-state UI tests**

`DATA_INCOMPLETE`, `DATA_CONFLICT`, `stale`, and `mapping_incomplete` must appear in the main panel. Verify unknown context never renders with a green success component.

- [ ] **Step 3: Implement an independent page/tab**

Add “市场环境” without removing existing pages. Read data roots from explicit environment variables:

```text
LEI_UNIVERSE_ROOT
LEI_COMPONENT_BARS_ROOT
LEI_INDEX_BARS_ROOT
LEI_SENTIMENT_ROOT
```

If roots are absent, render instructions and explicit unavailable status; do not load synthetic production data.

- [ ] **Step 4: Implement charts**

Chart Breadth20/50/200 with 15/50/85 reference lines, coverage, index close, and drawdown. Clearly label research-proxy A-share thresholds.

- [ ] **Step 5: Run UI tests and commit**

```bash
git add src/lei_signal/ui/market_context.py src/lei_signal/ui/app.py \
  src/lei_signal/ui/charts.py tests/integration/test_market_context_ui.py
git commit -m "feat(round4): show independent market context dashboard"
```

---

### Task 10: Real-Data Gates, Documentation, and Delivery

**Files:**
- Create: `tests/integration/test_market_context_real_replay.py`
- Modify: `README.md`
- Create: `ROUND4_DELIVERY_REPORT.md`

**Interfaces:**
- Real fixture roots: `tests/fixtures/market_context/universes/`, `component_bars/`, `indices/`, `sentiment/`.
- Missing real fixtures produce one explicit skip per unavailable dataset family.

- [ ] **Step 1: Add exact real-fixture contracts**

For each of `CN_ALL_A`, `SSE_50`, `CSI_300`, `CSI_500`, `CSI_1000`, and `CHINEXT`, require a declared replay manifest containing expected dates, universe versions, component count, exact breadth values, and tolerance. Do not accept “result not empty.”

- [ ] **Step 2: Add cross-source sampling tests**

When fixtures exist, compare several declared dates against independently recorded external values. Keep source URL/name, retrieval date, and allowed tolerance in the manifest. If fixtures do not exist, skip with the exact missing path and never fabricate data.

- [ ] **Step 3: Run all three reproductions**

```bash
PYTHONPATH=src /opt/homebrew/bin/python3.11 scripts/round4_repro/repro1_point_in_time_membership.py
PYTHONPATH=src /opt/homebrew/bin/python3.11 scripts/round4_repro/repro2_context_does_not_block.py
PYTHONPATH=src /opt/homebrew/bin/python3.11 scripts/round4_repro/repro3_release_time_alignment.py
```

Paste real output into `ROUND4_DELIVERY_REPORT.md`.

- [ ] **Step 4: Update README and write the delivery report**

Document data schemas, environment variables, source/licensing limitations, A-share `lei_threshold_research`, missing real fixtures, and the statement that context never blocks technical signals.

- [ ] **Step 5: Run complete gates**

```bash
/opt/homebrew/bin/python3.11 -m pytest -q -rs
/opt/homebrew/bin/python3.11 -m ruff check src tests
/opt/homebrew/bin/python3.11 -m mypy src
git diff --check
```

Expected: all existing and new non-real tests pass; real tests either pass with declared fixtures or skip with exact missing paths.

- [ ] **Step 6: Inspect the final diff and commit**

Confirm no changes to Round 3 thresholds or state progression. Then:

```bash
git add README.md ROUND4_DELIVERY_REPORT.md tests/integration/test_market_context_real_replay.py
git commit -m "docs(round4): record market context delivery evidence"
```

Do not merge master.

---

## Final Review Checklist

- [ ] Every design-spec section maps to at least one task above.
- [ ] No production path uses current constituents as formal history.
- [ ] No context path writes to `signal_events`, `DayState`, or structure lifecycle tables.
- [ ] No missing/stale/conflicted input becomes neutral.
- [ ] Summary v1 depends only on Breadth20/Breadth50 five-session direction.
- [ ] Breadth200, extremes, drawdown, divergence, NAAIM, and AAII remain explainable dimensions.
- [ ] Every event and snapshot has `as_of`, `available_at`, version, provenance, and data status.
- [ ] A-share fixed LEI thresholds are visibly marked research-only.
- [ ] Real-data absence is disclosed, not disguised with synthetic fixtures.
- [ ] Round 3’s one skipped `159915` real replay remains disclosed separately.
- [ ] Final report says “市场环境研究与提示模块可用,” not “strategy proven” or “ready for automatic trading.”
