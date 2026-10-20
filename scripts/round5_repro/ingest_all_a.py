"""Real 全A ingestion - Round 5.

Fetches ALL A-share stocks (~5889) from Eastmoney's push2 clist endpoint,
pulls 前复权 daily bars per stock via TencentPriceProvider (20 concurrent),
and fetches 中证全A (sh000985) as the reference index.

Output: tests/fixtures/market_context/{universes,indices,component_bars}/CN_ALL_A.*
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from lei_signal.data.providers import TencentPriceProvider

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "market_context"
MANIFEST_PATH = FIXTURE_ROOT / "manifest.json"

MARKET_ID = "CN_ALL_A"
INDEX_TENCENT_CODE = "sh000985"  # 中证全A
SOURCE_KIND = "research_proxy"


def fetch_all_a_tickers() -> list[str]:
    """Fetch all A-share tickers. Uses cached Sina list if available
    (Eastmoney push2 is currently down)."""
    cache = Path("/tmp/all_a_symbols.json")
    if cache.exists():
        return json.loads(cache.read_text())
    raise RuntimeError(
        "No cached A-share list at /tmp/all_a_symbols.json. "
        "Run the Sina pagination script first, or wait for Eastmoney push2."
    )


def fetch_tencent_bars(symbol: str) -> pd.DataFrame | None:
    """Fetch bars for one symbol. Creates its own provider for thread safety."""
    try:
        provider = TencentPriceProvider()
        data = provider.fetch(symbol)
        bars = data.bars.copy()
        bars.index = bars.index.rename("date")
        return bars.reset_index()
    except Exception:  # noqa: BLE001
        return None


def fetch_tencent_index(provider: TencentPriceProvider, code: str, market_id: str) -> pd.DataFrame:
    import urllib.parse
    url = f"{provider._HOST}?{urllib.parse.urlencode({'param': f'{code},day,,,250,qfq'})}"  # noqa: SLF001
    text = provider._fetch_text(url)  # noqa: SLF001
    bars_raw, _ = provider._parse_payload(text, market_id)  # noqa: SLF001
    from lei_signal.data.validation import validate_bars
    bars, _ = validate_bars(bars_raw, symbol=market_id, provider=provider.name, adjusted=False)
    return bars.reset_index().rename(columns={"index": "date"})


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


def ingest(max_workers: int = 20, max_bars: int = 250) -> dict:
    print("  fetching all A-share tickers from Eastmoney…", file=sys.stderr)
    symbols = fetch_all_a_tickers()
    print(f"  got {len(symbols)} A-shares", file=sys.stderr)

    today = _today_iso()
    universe_df = pd.DataFrame({
        "universe_id": [MARKET_ID] * len(symbols),
        "symbol": symbols,
        "effective_from": [today] * len(symbols),
        "effective_until": ["9999-12-31"] * len(symbols),
        "source": ["eastmoney_all_a"] * len(symbols),
        "source_version": [_today_iso()] * len(symbols),
        "source_kind": [SOURCE_KIND] * len(symbols),
    })

    provider = TencentPriceProvider()
    comp_root = FIXTURE_ROOT / "component_bars"
    comp_root.mkdir(parents=True, exist_ok=True)

    # Skip symbols that already have bar files (from a previous partial run).
    to_fetch = [s for s in symbols if not (comp_root / f"{s}.parquet").exists()]
    skipped = len(symbols) - len(to_fetch)
    if skipped:
        print(f"  skipping {skipped} already-fetched, fetching {len(to_fetch)}", file=sys.stderr)

    entries: list[dict] = []
    ok = skipped  # count pre-existing as ok
    fail = 0
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(fetch_tencent_bars, s): s for s in to_fetch}
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
            if (i + 1) % 500 == 0:
                print(f"  ...{i+1}/{len(symbols)} ({ok} ok, {fail} fail)", file=sys.stderr)

    print(f"  components: {ok} ok, {fail} fail", file=sys.stderr)

    # Index bars - 中证全A
    print(f"  fetching index 中证全A ({INDEX_TENCENT_CODE})…", file=sys.stderr)
    index_df = fetch_tencent_index(provider, INDEX_TENCENT_CODE, MARKET_ID)
    if max_bars and len(index_df) > max_bars:
        index_df = index_df.iloc[-max_bars:].reset_index(drop=True)
    idx_path = FIXTURE_ROOT / "indices" / f"{MARKET_ID}.parquet"
    _atomic_write_parquet(index_df, idx_path)

    # Universe
    uni_path = FIXTURE_ROOT / "universes" / f"{MARKET_ID}.parquet"
    _atomic_write_parquet(universe_df, uni_path)

    return {
        "market_id": MARKET_ID,
        "constituent_count": len(symbols),
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
    src["tencent_qfq"] = "tencent-public/qfq"
    src["eastmoney_all_a"] = "eastmoney-public/push2"
    manifest["source_license"] = src
    manifest["source_kind"] = SOURCE_KIND
    manifest["markets"] = list(markets.values())
    tmp = MANIFEST_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(MANIFEST_PATH)
    print(f"wrote manifest -> {MANIFEST_PATH.relative_to(REPO_ROOT)}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-workers", type=int, default=5)
    parser.add_argument("--max-bars", type=int, default=250)
    args = parser.parse_args(argv)
    entry = ingest(max_workers=args.max_workers, max_bars=args.max_bars)
    update_manifest(entry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
