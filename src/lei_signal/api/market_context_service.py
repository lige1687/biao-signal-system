"""API service: market context snapshots per symbol.

Reads the local fixture universes + component bars + index bars + the
SQLite cache (for breadth history and persisted assessments), and runs
the market-context pipeline per reference market.

The service is the single source of truth for both the badge (summary
only) and the full snapshot — they always come from the same
``MarketContextSnapshot`` so the UI cannot show a "tailwind" badge
backed by a snapshot whose own summary is "unknown".
"""

from __future__ import annotations

import sqlite3
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from lei_signal.api import config
from lei_signal.market_context.breadth import rolling_percentile_at as _rolling_percentile_at
from lei_signal.market_context.data_sources import LocalMarketBarsProvider
from lei_signal.market_context.mapping import map_reference_markets, to_repo_symbol
from lei_signal.market_context.pipeline import (
    MarketContextRequest,
    analyze_market_context,
)
from lei_signal.market_context.storage import write_market_context
from lei_signal.market_context.types import (
    BreadthDirection,
    ContextDataStatus,
    ContextSummary,
    LongRegime,
    MarketContextSnapshot,
    MarketId,
    SentimentLabel,
)
from lei_signal.market_context.universe import LocalUniverseProvider
from lei_signal.storage.sqlite_store import apply_migrations, connect


@dataclass(frozen=True, slots=True)
class MarketContextDTO:
    """API payload: badge + full snapshot, all from the same source."""

    symbol: str
    as_of: date
    summary: str
    summary_cn: str
    data_status: str
    reasons_cn: list[str]
    conflicts_cn: list[str]
    source_kind: str
    provenance: str
    updated_at: str
    snapshots: list[dict[str, Any]]


class _LocalMarketDataProvider:
    """Per-market data source backed by fixture directories + SQLite."""

    def __init__(
        self,
        *,
        markets: tuple[MarketId, ...],
        universe_root: Path,
        component_root: Path,
        index_root: Path,
        connection: sqlite3.Connection,
    ) -> None:
        self._markets = markets
        self._universe_root = universe_root
        self._component_root = component_root
        self._index_root = index_root
        self._connection = connection
        self._universes: dict[MarketId, LocalUniverseProvider] = {
            mid: LocalUniverseProvider(universe_root) for mid in markets
        }
        self._bars = LocalMarketBarsProvider(component_root, index_root)

    def universe(self, market_id: MarketId, as_of: date):
        provider = self._universes.get(market_id)
        if provider is None:
            return None
        try:
            return provider.snapshot(market_id, as_of)
        except Exception:
            return None

    def sessions(self, market_id: MarketId) -> pd.DatetimeIndex:
        if market_id not in self._markets:
            return pd.DatetimeIndex([], name="date")
        index = self._bars.load_index(market_id.value, date(2099, 12, 31))
        if index.empty or not isinstance(index.index, pd.DatetimeIndex):
            return pd.DatetimeIndex([], name="date")
        return index.index

    def index_bars(self, market_id: MarketId, as_of: date) -> pd.DataFrame:
        if market_id not in self._markets:
            return pd.DataFrame()
        return self._bars.load_index(market_id.value, as_of)

    def breadth_history(self, market_id: MarketId, *, up_to: date) -> pd.DataFrame:
        if market_id not in self._markets:
            return pd.DataFrame()
        return _read_breadth_history(self._connection, market_id, up_to=up_to)

    def component_bars(
        self, market_id: MarketId, symbols: tuple[str, ...], as_of: date,
    ) -> dict[str, pd.DataFrame]:
        if market_id not in self._markets:
            return {}
        result = self._bars.load_components(set(symbols), as_of)
        return result.bars_by_symbol


def _read_breadth_history(
    connection: sqlite3.Connection,
    market_id: MarketId,
    *,
    up_to: date,
) -> pd.DataFrame:
    """Latest revision per as_of for the given market, up to `up_to`."""
    rows = connection.execute(
        """SELECT as_of, breadth_20, breadth_50, breadth_200,
                  coverage_20, coverage_50, coverage_200,
                  percentile_20, percentile_50, percentile_200,
                  provenance, revision_no, data_status
             FROM market_breadth_snapshot_revisions
            WHERE market_id = ?
              AND as_of <= ?
              AND data_status NOT IN ('stale', 'unavailable')
         ORDER BY as_of, revision_no DESC""",
        (market_id.value, str(up_to)),
    ).fetchall()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame([dict(r) for r in rows])
    df = df.drop_duplicates(subset=["as_of"], keep="first")
    df["as_of"] = pd.to_datetime(df["as_of"])
    df = df.set_index("as_of").sort_index()
    df.index.name = "date"
    return df


class MarketContextService:
    """Repository for market context snapshots."""

    _CACHE_TTL_SECONDS = 600

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cache: dict[tuple[str, date], tuple[datetime, MarketContextDTO]] = {}

    def get_snapshot(
        self,
        symbol: str,
        as_of: date,
        *,
        memberships: set[MarketId] | None = None,
    ) -> MarketContextDTO:
        cache_key = (symbol, as_of)
        now = datetime.now(UTC)
        cached = self._cache.get(cache_key)
        if cached and (now - cached[0]).total_seconds() < self._CACHE_TTL_SECONDS:
            return cached[1]

        # Default memberships: every A-share and US symbol also gets the
        # two global reference panels — CN_ALL_A (A 股整体) and SP500
        # (美股整体). The user only needs to track A股/美股, so this
        # decouples the symbol-level market mapping from the breadth view.
        seeded: set[MarketId] = set(memberships or set())
        seeded.update(_DEFAULT_GLOBAL_MARKETS)
        dto = self._build(symbol, as_of, memberships=seeded)
        with self._lock:
            self._cache[cache_key] = (now, dto)
        return dto

    def get_global_snapshots(self, as_of: date) -> list[MarketContextDTO]:
        """Return the breadth snapshots for the two global panels.

        Prefers the newest **stored** revision over recomputing from bars.
        A stored row already carries its point-in-time percentile, and for
        CN_ALL_A it comes from 大盘云图's whole-market aggregate — which is
        a different scale from our own per-stock count. Recomputing on
        every request would append a same-day row on the other scale and
        leave the percentile empty, so the stored series wins unless
        there is nothing stored at all.
        """
        out: list[MarketContextDTO] = []
        for market_id in _DEFAULT_GLOBAL_MARKETS:
            key = (_global_panel_symbol(market_id), as_of)
            cached = self._cache.get(key)
            age = (datetime.now(UTC) - cached[0]).total_seconds() if cached else None
            if cached is not None and age is not None and age < self._CACHE_TTL_SECONDS:
                out.append(cached[1])
                continue

            dto = self._stored_panel(market_id, as_of)
            if dto is None:
                dto = self._build_for_market(market_id, as_of)
            with self._lock:
                self._cache[key] = (datetime.now(UTC), dto)
            out.append(dto)
        return out

    def _stored_panel(
        self, market_id: MarketId, as_of: date,
    ) -> MarketContextDTO | None:
        """Build a panel DTO from the newest stored revision, or None.

        Also derives the exact 5-session breadth delta from the stored
        series, so the strip can show direction on day one instead of
        waiting for the live pipeline to accumulate history.
        """
        connection = self._open_connection()
        try:
            history = _read_breadth_history(connection, market_id, up_to=as_of)
        finally:
            connection.close()
        if history.empty or "breadth_20" not in history.columns:
            return None

        readings = history["breadth_20"].dropna()
        if readings.empty:
            return None

        latest_ts = readings.index[-1]
        latest = float(readings.iloc[-1])
        prior = float(readings.iloc[-6]) if len(readings) >= 6 else None
        delta_5 = latest - prior if prior is not None else None

        row = history.loc[latest_ts]
        percentile = row.get("percentile_20")
        percentile = None if percentile is None or pd.isna(percentile) else float(percentile)
        b50 = row.get("breadth_50")
        b50 = None if b50 is None or pd.isna(b50) else float(b50)
        b200 = row.get("breadth_200")
        b200 = None if b200 is None or pd.isna(b200) else float(b200)
        status = str(row.get("data_status") or ContextDataStatus.COMPLETE.value)

        heat = _heat_from_percentile(percentile)
        long_regime = LongRegime.UNKNOWN
        if b200 is not None:
            if b200 > 50.0:
                long_regime = LongRegime.BULL
            elif b200 < 50.0:
                long_regime = LongRegime.BEAR

        return MarketContextDTO(
            symbol=_global_panel_symbol(market_id),
            as_of=latest_ts.date(),
            summary=ContextSummary.UNKNOWN.value,
            summary_cn=_summary_cn(ContextSummary.UNKNOWN.value),
            data_status=status,
            reasons_cn=[],
            conflicts_cn=[],
            source_kind="research_proxy",
            provenance=str(row.get("provenance") or ""),
            updated_at=datetime.now(UTC).isoformat(timespec="seconds"),
            snapshots=[{
                "market_id": market_id.value,
                "as_of": latest_ts.date().isoformat(),
                "available_at": latest_ts.date().isoformat(),
                "universe_version": "",
                "breadth_20": latest,
                "breadth_50": b50,
                "breadth_200": b200,
                "breadth_20_delta_5": delta_5,
                "breadth_50_delta_5": None,
                "breadth_200_delta_20": None,
                "coverage_20": float(row.get("coverage_20") or 0.0),
                "coverage_50": float(row.get("coverage_50") or 0.0),
                "coverage_200": float(row.get("coverage_200") or 0.0),
                "constituent_count": 0,
                "percentile_20": percentile,
                "percentile_50": None,
                "percentile_200": None,
                "breadth_direction": BreadthDirection.UNKNOWN.value,
                "long_regime": long_regime.value,
                "heat_state": heat,
                "drawdown_from_ath": None,
                "market_rv20_ann": None,
                "market_rv_pct": None,
                "vol_regime": "unknown",
                "summary": ContextSummary.UNKNOWN.value,
                "reasons": [],
                "conflicts": [],
                "extreme_events": [],
                "divergence_events": [],
                "naaim_label": SentimentLabel.UNKNOWN.value,
                "aaii_label": SentimentLabel.UNKNOWN.value,
                "naaim_current_eligible": False,
                "aaii_current_eligible": False,
                "source_kind": "research_proxy",
                "provenance": str(row.get("provenance") or ""),
                "data_status": status,
            }],
        )

    def get_forward_stats(
        self,
        market_id: MarketId,
        percentile: float,
        *,
        bucket_half_width: float = 5.0,
        horizons: tuple[int, ...] = (5, 20, 60),
        min_samples: int = 1,
    ) -> dict[str, Any]:
        """Forward returns grouped by current breadth percentile bucket.

        For every session in the breadth history where the
        `breadth_20` percentile was within
        `[percentile - bucket_half_width, percentile + bucket_half_width]`,
        take the index close at that session and at
        `t+horizon` for each horizon in `horizons`. Return the median,
        mean, hit rate, and N for each horizon.

        The user can look at the current percentile and ask "in past
        similar percentile regimes, what did the index do over the next
        5/20/60 days?" — a one-glance answer to "what does this breadth
        level typically lead to".
        """
        history_rows = self.get_breadth_history(market_id, lookback_days=1260)
        if not history_rows:
            return {"market_id": market_id.value, "percentile": percentile,
                    "bucket": [], "stats": {}}

        root = Path(config.cache_root())
        index_path = root / "fixtures" / "market_context" / "indices" / f"{market_id.value}.parquet"
        if not index_path.exists():
            return {"market_id": market_id.value, "percentile": percentile,
                    "bucket": [], "stats": {}, "error": "no_index_bars"}
        index_bars = pd.read_parquet(index_path)
        # Fixture files store the session axis as a `date` column; promote it
        # to the index so `.loc`/positional lookups below work.
        if "date" in index_bars.columns:
            index_bars = index_bars.assign(
                date=pd.to_datetime(index_bars["date"])
            ).set_index("date")
        if "close" not in index_bars.columns or not isinstance(index_bars.index, pd.DatetimeIndex):
            return {"market_id": market_id.value, "percentile": percentile,
                    "bucket": [], "stats": {}, "error": "bad_index_bars"}
        index_bars = index_bars.sort_index()
        closes = index_bars["close"]

        # Rank each historical breadth reading into a percentile, so the
        # bucket below compares like with like. The caller passes a
        # percentile (P0-P100), not a raw breadth percentage - bucketing
        # directly on `breadth_20` would mix the two scales.
        hist_dates = pd.to_datetime([r["date"] for r in history_rows])
        breadth_values = [r.get("breadth_20") for r in history_rows]
        breadth_series = pd.Series(breadth_values, index=hist_dates, dtype=float).dropna()
        if breadth_series.empty:
            return {"market_id": market_id.value, "percentile": percentile,
                    "bucket": [], "stats": {}, "error": "no_percentile_history"}
        percentile_series = breadth_series.rank(pct=True) * 100.0

        bucket = percentile_series[
            (percentile_series >= percentile - bucket_half_width) &
            (percentile_series <= percentile + bucket_half_width)
        ]
        if len(bucket) < min_samples:
            return {
                "market_id": market_id.value, "percentile": percentile,
                "bucket_half_width": bucket_half_width,
                "bucket_size": int(len(bucket)),
                "min_samples": min_samples,
                "stats": {},
            }

        stats: dict[str, dict[str, float | int | None]] = {}
        for h in horizons:
            rets: list[float] = []
            for anchor in bucket.index:
                # Find index close at anchor and at anchor + h sessions.
                if anchor not in closes.index:
                    continue
                pos = closes.index.get_loc(anchor)
                if isinstance(pos, slice):
                    pos = pos.start
                future_pos = pos + h
                if future_pos >= len(closes):
                    continue
                now_close = float(closes.iloc[pos])
                future_close = float(closes.iloc[future_pos])
                if now_close <= 0:
                    continue
                rets.append(future_close / now_close - 1.0)
            if not rets:
                stats[str(h)] = {"n": 0, "median": None, "mean": None, "hit_rate": None}
                continue
            arr = pd.Series(rets)
            stats[str(h)] = {
                "n": int(len(arr)),
                "median": float(arr.median()),
                "mean": float(arr.mean()),
                "hit_rate": float((arr > 0).mean()),
                "min": float(arr.min()),
                "max": float(arr.max()),
            }
        return {
            "market_id": market_id.value,
            "percentile": percentile,
            "bucket_half_width": bucket_half_width,
            "bucket_size": int(len(bucket)),
            "stats": stats,
        }

    def get_breadth_history(
        self,
        market_id: MarketId,
        *,
        lookback_days: int = 120,
        up_to: date | None = None,
    ) -> list[dict[str, Any]]:
        connection = self._open_connection()
        try:
            up_to = up_to or date.today()
            df = _read_breadth_history(connection, market_id, up_to=up_to)
        finally:
            connection.close()
        if df.empty:
            return []
        df = df.tail(lookback_days)
        return [
            {
                "date": ts.date().isoformat(),
                "breadth_20": row.get("breadth_20"),
                "breadth_50": row.get("breadth_50"),
                "breadth_200": row.get("breadth_200"),
                "coverage_20": row.get("coverage_20"),
                "coverage_50": row.get("coverage_50"),
                "coverage_200": row.get("coverage_200"),
            }
            for ts, row in df.iterrows()
        ]

    def data_status(self, market_id: MarketId) -> dict[str, Any]:
        root = Path(config.cache_root())
        uni = LocalUniverseProvider(root / "fixtures" / "market_context" / "universes")
        try:
            snap = uni.snapshot(market_id, date.today())
        except Exception:
            snap = None
        return {
            "market_id": market_id.value,
            "universe_source": snap.source if snap else "",
            "universe_source_version": snap.source_version if snap else "",
            "universe_source_kind": snap.source_kind.value if snap else "",
            "universe_count": len(snap.symbols) if snap else 0,
            "fixtures_root": str(root / "fixtures" / "market_context"),
        }

    def _build(
        self,
        symbol: str,
        as_of: date,
        *,
        memberships: set[MarketId],
    ) -> MarketContextDTO:
        root = Path(config.cache_root())
        fixture_root = root / "fixtures" / "market_context"
        component_root = fixture_root / "component_bars"
        universe_root = fixture_root / "universes"
        index_root = fixture_root / "indices"

        repo_symbol = to_repo_symbol(symbol)
        # Seed memberships from the dashboard index table so well-known
        # symbols (`^IXIC`, `^GSPC`, `^HSTECH`, `000300.SS`, ...) get a
        # primary market without needing the caller to inject it.
        seeded = set(memberships)
        for primary in _dashboard_primary(repo_symbol):
            seeded.add(primary)
        mapping = map_reference_markets(repo_symbol, memberships=seeded)
        ordered: list[MarketId] = []
        if mapping.primary_market_id is not None:
            ordered.append(mapping.primary_market_id)
        ordered.extend(mapping.secondary_market_ids)
        return self._run_pipeline(
            repo_symbol, as_of, ordered,
            component_root=component_root,
            universe_root=universe_root,
            index_root=index_root,
        )

    def _build_for_market(self, market_id: MarketId, as_of: date) -> MarketContextDTO:
        """Build a DTO for a single, fixed reference market (used by the
        global topbar strip). Bypasses per-symbol mapping so the user
        always gets CN_ALL_A / SP500 instead of whatever the default
        membership injection would route to.
        """
        root = Path(config.cache_root())
        fixture_root = root / "fixtures" / "market_context"
        return self._run_pipeline(
            _global_panel_symbol(market_id), as_of, [market_id],
            component_root=fixture_root / "component_bars",
            universe_root=fixture_root / "universes",
            index_root=fixture_root / "indices",
        )

    def _run_pipeline(
        self,
        symbol: str,
        as_of: date,
        ordered: list[MarketId],
        *,
        component_root: Path,
        universe_root: Path,
        index_root: Path,
    ) -> MarketContextDTO:
        connection = self._open_connection()
        try:
            provider = _LocalMarketDataProvider(
                markets=tuple(ordered),
                universe_root=universe_root,
                component_root=component_root,
                index_root=index_root,
                connection=connection,
            )
            snapshots = analyze_market_context(
                MarketContextRequest(
                    symbol=symbol,
                    as_of=as_of,
                    memberships=set(ordered),
                    provider=provider,
                )
            )
            # Augment each snapshot with point-in-time percentiles using
            # the breadth history we've already persisted (or are about
            # to persist for this run).
            for snap in snapshots:
                for window in (20, 50, 200):
                    col = f"breadth_{window}"
                    hist = _read_breadth_history(
                        connection, snap.market_id, up_to=as_of,
                    )
                    if hist.empty or col not in hist.columns:
                        continue
                    pct = _rolling_percentile_at(
                        hist[col],
                        as_of=as_of,
                        lookback=1260,
                        min_periods=252,
                    )
                    if pct is not None:
                        snap = _replace_percentile(snap, window, pct)
            for snap in snapshots:
                write_market_context(
                    connection, snap, snap.extreme_events,
                    run_id=f"api:{as_of.isoformat()}",
                )
            connection.commit()
        finally:
            connection.close()
        return _to_dto(symbol, as_of, snapshots)

    def _open_connection(self) -> sqlite3.Connection:
        path = Path(config.sqlite_path())
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            # Touch the file so connect() can attach to it; the migrations
            # are then applied on first use.
            path.touch()
        # 迁移在并发多连接下仍可能「写 vs 写」互斥，5s busy_timeout 不一定
        # 覆盖所有场景（apply_migrations 跨多语句）。应用层重试兜底。
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                return connect(path)
            except sqlite3.OperationalError as exc:
                if "locked" not in str(exc):
                    raise
                last_exc = exc
                time.sleep(0.2 * (attempt + 1))
        raise last_exc  # type: ignore[misc]


def _empty_db() -> sqlite3.Connection:
    """Open a SQLite connection with the schema applied but no rows."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        path = tmp.name
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    apply_migrations(connection)
    return connection


def _to_dto(
    symbol: str,
    as_of: date,
    snapshots: tuple[MarketContextSnapshot, ...],
) -> MarketContextDTO:
    if not snapshots:
        return MarketContextDTO(
            symbol=symbol, as_of=as_of,
            summary="unknown", summary_cn="环境未知",
            data_status=ContextDataStatus.UNAVAILABLE.value,
            reasons_cn=["无参考市场映射"],
            conflicts_cn=[],
            source_kind="formal", provenance="",
            updated_at=datetime.now(UTC).isoformat(timespec="seconds"),
            snapshots=[],
        )

    primary = snapshots[0]
    snap_dicts = [_snapshot_to_dict(s) for s in snapshots]
    return MarketContextDTO(
        symbol=symbol, as_of=as_of,
        summary=primary.summary.value,
        summary_cn=_summary_cn(primary.summary.value),
        data_status=primary.data_status.value,
        reasons_cn=list(primary.reasons),
        conflicts_cn=list(primary.conflicts),
        source_kind=primary.source_kind.value,
        provenance=primary.provenance,
        updated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        snapshots=snap_dicts,
    )


def _snapshot_to_dict(s: MarketContextSnapshot) -> dict[str, Any]:
    return {
        "market_id": s.market_id.value,
        "as_of": s.as_of.isoformat(),
        "available_at": s.available_at.isoformat(),
        "universe_version": s.universe_version,
        "breadth_20": s.breadth_20,
        "breadth_50": s.breadth_50,
        "breadth_200": s.breadth_200,
        "breadth_20_delta_5": s.breadth_20_delta_5,
        "breadth_50_delta_5": s.breadth_50_delta_5,
        "breadth_200_delta_20": s.breadth_200_delta_20,
        "coverage_20": s.coverage_20,
        "coverage_50": s.coverage_50,
        "coverage_200": s.coverage_200,
        "constituent_count": s.constituent_count,
        "percentile_20": s.percentile_20,
        "percentile_50": s.percentile_50,
        "percentile_200": s.percentile_200,
        "breadth_direction": s.breadth_direction.value,
        "long_regime": s.long_regime.value,
        "heat_state": s.heat_state.value,
        "drawdown_from_ath": s.drawdown_from_ath,
        "market_rv20_ann": s.market_rv20_ann,
        "market_rv_pct": s.market_rv_pct,
        "vol_regime": s.vol_regime.value,
        "summary": s.summary.value,
        "reasons": list(s.reasons),
        "conflicts": list(s.conflicts),
        "extreme_events": [
            {
                "event_type": e.event_type,
                "evidence": e.evidence,
                "threshold_origin": e.threshold_origin,
            }
            for e in s.extreme_events
        ],
        "divergence_events": [
            {"event_type": e.event_type, "evidence": e.evidence}
            for e in s.divergence_events
        ],
        "naaim_label": s.naaim_label.value,
        "aaii_label": s.aaii_label.value,
        "naaim_current_eligible": s.naaim_current_eligible,
        "aaii_current_eligible": s.aaii_current_eligible,
        "source_kind": s.source_kind.value,
        "provenance": s.provenance,
        "data_status": s.data_status.value,
    }


def _heat_from_percentile(percentile: float | None) -> str:
    """Map a breadth percentile to a heat label.

    Mirrors the classifier's percentile bands (spec §8) so a stored-row
    panel reads the same as a freshly classified one.
    """
    if percentile is None:
        return "unknown"
    if percentile <= 10.0:
        return "extreme_cold"
    if percentile <= 25.0:
        return "cold"
    if percentile >= 90.0:
        return "extreme_hot"
    if percentile >= 75.0:
        return "hot"
    return "neutral"


def _summary_cn(value: str) -> str:
    return {
        "tailwind": "顺风",
        "neutral": "中性",
        "headwind": "逆风",
        "unknown": "环境未知",
    }.get(value, value)


def _replace_percentile(
    snap: MarketContextSnapshot, window: int, value: float,
) -> MarketContextSnapshot:
    from dataclasses import replace as _replace
    if window == 20:
        return _replace(snap, percentile_20=value)
    if window == 50:
        return _replace(snap, percentile_50=value)
    if window == 200:
        return _replace(snap, percentile_200=value)
    raise ValueError(f"unsupported window: {window}")


#: Global reference panels: 全A (CN_ALL_A) + 标普500 (SP500).
#: 注意：CN_ALL_A 的真实宽度已不再由本模块 fixture 计算——
#: 涨跌家数口径请走 /market-context/a-share-breadth（真全A、腾讯快照+交易所代码列表）。
#: 此处 global-strip 仍保留 MA 上方占比作为补充参考，但其口径 = 二级行业等权平均站上率，并非真全A股票数加权。
_DEFAULT_GLOBAL_MARKETS: tuple[MarketId, ...] = (MarketId.CN_ALL_A, MarketId.SP500)


def _global_panel_symbol(market_id: MarketId) -> str:
    """Driver symbol per global panel. CN_ALL_A uses 上证综指; SP500 uses ^GSPC."""
    return {"CN_ALL_A": "000001.SS", "SP500": "^GSPC"}.get(
        market_id.value, "000001.SS",
    )


#: Dashboard indices whose primary reference market is well-known.
#: Used to inject a default `memberships` set so the pipeline doesn't
#: have to receive explicit memberships from the caller. Without this
#: map, well-known symbols like `^IXIC` return `mapping_incomplete`
#: even though the answer is obvious.
_DASHBOARD_PRIMARY: dict[str, tuple[MarketId, ...]] = {
    "000001.SS": (MarketId.CN_ALL_A,),
    "000300.SS": (MarketId.CSI_300,),
    "000688.SS": (MarketId.STAR_50,),
    "000016.SS": (MarketId.SSE_50,),
    "000905.SS": (MarketId.CSI_500,),
    "000852.SS": (MarketId.CSI_1000,),
    "399006.SZ": (MarketId.CHINEXT,),
    "510050.SS": (MarketId.SSE_50,),
    "510300.SS": (MarketId.CSI_300,),
    "588000.SS": (MarketId.STAR_50,),
    "588080.SS": (MarketId.STAR_50,),
    "^IXIC": (MarketId.NASDAQ_100,),
    "^GSPC": (MarketId.SP500,),
    "^HSTECH": (MarketId.SP500,),
    "^KS11": (MarketId.SP500,),
}


def _dashboard_primary(symbol: str) -> tuple[MarketId, ...]:
    return _DASHBOARD_PRIMARY.get(symbol, ())
