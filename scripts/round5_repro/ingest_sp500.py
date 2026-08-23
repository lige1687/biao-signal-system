"""Real SP500 ingestion - Round 5.

Fetches the S&P 500 constituent list from Wikipedia, then pulls daily
bars for each constituent + the ^GSPC index via YahooV8PriceProvider
(v7 is rate-limited; v8 is stable). Writes universe, index, and
component bars to the fixture dirs + updates the manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from lei_signal.data.providers import YahooV8PriceProvider

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "market_context"
MANIFEST_PATH = FIXTURE_ROOT / "manifest.json"

MARKET_ID = "SP500"
INDEX_SYMBOL = "^GSPC"
SOURCE_KIND = "research_proxy"


def fetch_sp500_constituents() -> list[str]:
    """Pull the S&P 500 ticker list from Wikipedia."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8")
    tables = pd.read_html(io.StringIO(html))
    df = tables[0]
    # Wikipedia uses dots (BRK.B); Yahoo uses hyphens (BRK-B).
    tickers = [str(t).replace(".", "-") for t in df["Symbol"].tolist()]
    return sorted(set(tickers))


def fetch_yahoo_bars(provider: YahooV8PriceProvider, symbol: str) -> pd.DataFrame | None:
    try:
        data = provider.fetch(symbol, min_rows=21)
        bars = data.bars.copy()
        bars.index = bars.index.rename("date")
        return bars.reset_index()
    except Exception:  # noqa: BLE001
        return None


def _atomic_write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_parquet(tmp, index=False)
    tmp.replace(path)


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _today_iso() -> str:
    return datetime.now(UTC).date().isoformat()


def ingest(max_workers: int = 6, max_bars: int = 250) -> dict:
    print("  fetching S&P 500 constituents from Wikipedia…", file=sys.stderr)
    tickers = fetch_sp500_constituents()
    print(f"  got {len(tickers)} constituents", file=sys.stderr)

    today = _today_iso()
    universe_df = pd.DataFrame({
        "universe_id": [MARKET_ID] * len(tickers),
        "symbol": tickers,
        "effective_from": [today] * len(tickers),
        "effective_until": ["9999-12-31"] * len(tickers),
        "source": ["wikipedia_sp500"] * len(tickers),
        "source_version": [_today_iso()] * len(tickers),
        "source_kind": [SOURCE_KIND] * len(tickers),
    })

    provider = YahooV8PriceProvider()
    comp_root = FIXTURE_ROOT / "component_bars"
    comp_root.mkdir(parents=True, exist_ok=True)

    entries: list[dict] = []
    ok = 0
    fail = 0
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(fetch_yahoo_bars, provider, t): t for t in tickers}
        for i, fut in enumerate(as_completed(futures)):
            sym = futures[fut]
            bars = fut.result()
            if bars is None or bars.empty:
                fail += 1
                entries.append({"symbol": sym, "error": "fetch_failed", "rows": 0, "hash": ""})
                continue
            if max_bars and len(bars) > max_bars:
                bars = bars.iloc[-max_bars:].reset_index(drop=True)
            path = comp_root / f"{sym}.parquet"
            _atomic_write_parquet(bars, path)
            ok += 1
            entries.append({
                "symbol": sym, "rows": int(len(bars)),
                "first_date": str(pd.Timestamp(bars["date"].min()).date()),
                "last_date": str(pd.Timestamp(bars["date"].max()).date()),
                "hash": _hash_file(path),
            })
            if (i + 1) % 50 == 0:
                print(f"  ...{i+1}/{len(tickers)} done ({ok} ok, {fail} fail)", file=sys.stderr)

    print(f"  components: {ok} ok, {fail} fail", file=sys.stderr)

    # Index bars
    print(f"  fetching index bars for {INDEX_SYMBOL}…", file=sys.stderr)
    index_df = fetch_yahoo_bars(provider, INDEX_SYMBOL)
    if index_df is None:
        raise RuntimeError("failed to fetch ^GSPC index bars")
    if max_bars and len(index_df) > max_bars:
        index_df = index_df.iloc[-max_bars:].reset_index(drop=True)
    idx_path = FIXTURE_ROOT / "indices" / f"{MARKET_ID}.parquet"
    _atomic_write_parquet(index_df, idx_path)

    # Universe
    uni_path = FIXTURE_ROOT / "universes" / f"{MARKET_ID}.parquet"
    _atomic_write_parquet(universe_df, uni_path)

    return {
        "market_id": MARKET_ID,
        "constituent_count": len(tickers),
        "universe_path": str(uni_path.relative_to(REPO_ROOT)),
        "index_path": str(idx_path.relative_to(REPO_ROOT)),
        "universe_hash": _hash_file(uni_path),
        "index_hash": _hash_file(idx_path),
        "index_first_date": str(pd.Timestamp(index_df["date"].min()).date()),
        "index_last_date": str(pd.Timestamp(index_df["date"].max()).date()),
        "components": entries,
    }


def update_manifest(entry: dict) -> None:
    manifest = {}
    if MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    markets = {m["market_id"]: m for m in manifest.get("markets", [])}
    markets[entry["market_id"]] = entry
    manifest["manifest_version"] = manifest.get("manifest_version", "lei_market_data.v1")
    manifest["generated_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    src = manifest.get("source_license", {})
    src["yahoo_v8"] = "yahoo-finance/public-v8"
    src["wikipedia_sp500"] = "wikipedia/public"
    manifest["source_license"] = src
    manifest["source_kind"] = SOURCE_KIND
    manifest["markets"] = list(markets.values())
    tmp = MANIFEST_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(MANIFEST_PATH)
    print(f"wrote manifest -> {MANIFEST_PATH.relative_to(REPO_ROOT)}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-workers", type=int, default=6)
    parser.add_argument(
        "--max-bars",
        type=int,
        default=0,
        help="每只成分股保留的最大K线数(0=不截断,拉取Yahoo全量历史)",
    )
    args = parser.parse_args(argv)
    entry = ingest(max_workers=args.max_workers, max_bars=args.max_bars)
    update_manifest(entry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
