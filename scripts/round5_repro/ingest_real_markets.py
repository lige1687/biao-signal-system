"""Real CSI_300 + STAR_50 ingestion — Round 5.

For each market in `{CSI_300, STAR_50}`:
  1. Pull the current constituent list from Eastmoney's datacenter
     (this is "current" only — no historical PIT rebalance yet, so the
     universe is tagged `source_kind=research_proxy`).
  2. Pull 前复权 (qfq) daily bars per constituent from the repo's
     TencentPriceProvider.
  3. Pull the index daily series from the same source.
  4. Write a manifest with source, license, version, sha256 hashes, and
     `updated_at` timestamps.

Outputs land in ``tests/fixtures/market_context/{universes,component_bars,indices}``
and a ``manifest.json`` next to them. The pipeline reads these via
``LocalMarketBarsProvider`` + ``LocalUniverseProvider``.

This script is **idempotent** — re-runs overwrite the same files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

# Repo-local provider for A-share 前复权 daily bars.
from lei_signal.data.providers import TencentPriceProvider
from lei_signal.data.symbols import is_a_share, resolve_symbol
from lei_signal.data.validation import validate_bars

# ── Constants ──────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "market_context"
MANIFEST_PATH = FIXTURE_ROOT / "manifest.json"

# Eastmoney datacenter board id mapping (TYPE column in RPT_INDEX_TS_COMPONENT).
BOARD_CODE = {
    "CSI_300": "b:MK0300",  # 沪深300
    "STAR_50": "b:MK0400",  # 科创50
}

# Eastmoney `RPT_INDEX_TS_COMPONENT` `TYPE` column. 1 = 沪深300, 4 = 科创50.
BOARD_TYPE = {
    "CSI_300": "1",
    "STAR_50": "4",
}

INDEX_SYMBOL = {
    "CSI_300": "sh000300",  # 沪深300 指数
    "STAR_50": "sh000688",  # 科创50 指数
}

SOURCE_LICENSE = {
    "tencent_qfq": "tencent-public/qfq",
    "eastmoney_constituents": "eastmoney-public/datacenter",
}

SOURCE_KIND = "research_proxy"  # current-only constituent list


# ── Eastmoney constituent pull ─────────────────────────────────────────


def fetch_eastmoney_constituents(market_id: str) -> list[str]:
    """Pull the current constituent list for a market from Eastmoney.

    Eastmoney's `RPT_INDEX_TS_COMPONENT` exposes one row per
    (board, security) pair with a `TYPE` column that maps to which
    index the security is in. Board code filtering (`fs=b:MKxxxx`) only
    works for some boards (CSI 300), and combining it with `TYPE=`
    returns 9201 "empty data". The reliable pattern is to filter by
    `TYPE=` directly with no `fs`.
    """
    host = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    target_type = BOARD_TYPE[market_id]

    symbols: list[str] = []
    page = 1
    while True:
        params = {
            "reportName": "RPT_INDEX_TS_COMPONENT",
            "columns": "SECUCODE,TYPE,MAXTRADEDATE",
            "pageNumber": str(page),
            "pageSize": "1000",
            "sortColumns": "SECUCODE",
            "sortTypes": "1",
            "filter": f'(TYPE="{target_type}")',
        }
        url = f"{host}?{urllib.parse.urlencode(params)}"

        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://emweb.eastmoney.com/"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))

        result = payload.get("result") or {}
        rows = result.get("data") or []
        if not rows:
            break

        for r in rows:
            if r.get("SECUCODE"):
                symbols.append(r["SECUCODE"])

        pages = int(result.get("pages", 1))
        if page >= pages:
            break
        page += 1

    if not symbols:
        raise RuntimeError(
            f"Eastmoney returned no constituents for {market_id} (TYPE={target_type})"
        )

    return sorted(set(symbols))


# ── Tencent bars pull ──────────────────────────────────────────────────


def _to_tencent_prefix(symbol: str) -> str:
    """`600519.SH` → `sh600519`. Used by Tencent's `appstock/app/fqkline/get`."""
    if not is_a_share(resolve_symbol(symbol)):
        raise ValueError(f"{symbol} is not an A-share")
    bare = symbol.split(".")[0]
    if symbol.endswith(".SH") or symbol.endswith(".SS"):
        return f"sh{bare}"
    return f"sz{bare}"


def fetch_tencent_bars(symbol: str) -> pd.DataFrame:
    """Fetch 前复权 daily bars via the repo's TencentPriceProvider.

    Eastmoney returns `.SH`/`.SZ`; the repo's Tencent provider only
    accepts the canonical `.SS` for Shanghai, so re-canonicalise before
    fetching.
    """
    provider = TencentPriceProvider()
    canonical = symbol[:-3] + ".SS" if symbol.endswith(".SH") else symbol
    data = provider.fetch(canonical)
    bars = data.bars.copy()
    bars.index = bars.index.rename("date")
    bars = bars.reset_index()
    return bars


def fetch_tencent_index_bars(tencent_code: str, *, market_id: str) -> pd.DataFrame:
    """Fetch daily bars for an index directly (bypassing the A-share guard).

    `tencent_code` is the form Tencent expects, e.g. ``sh000300``. The
    result goes through `validate_bars` like any other Tencent response.
    Indices have no dividend adjustments, so ``qfq`` is moot.
    """
    provider = TencentPriceProvider()
    param = f"{tencent_code},day,,,{provider._max_bars},qfq"
    url = f"{provider._HOST}?{urllib.parse.urlencode({'param': param})}"  # noqa: SLF001
    text = provider._fetch_text(url)  # noqa: SLF001
    bars_raw, _adjusted = provider._parse_payload(text, market_id)  # noqa: SLF001
    bars, _report = validate_bars(
        bars_raw, symbol=market_id, provider=provider.name, adjusted=False,
    )
    out = bars.reset_index()
    out = out.rename(columns={"index": "date"})
    return out


# ── File writers ──────────────────────────────────────────────────────


def _atomic_write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_parquet(tmp, index=False)
    tmp.replace(path)


def _atomic_write_json(obj: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _today_iso() -> str:
    return datetime.now(UTC).date().isoformat()


# ── Ingest one market ─────────────────────────────────────────────────


def ingest_market(market_id: str, *, max_bars: int = 600) -> dict:
    """Pull constituents + bars + index for one market, write to fixture dirs,
    return the manifest entry."""
    print(f"  fetching constituents for {market_id}…", file=sys.stderr)
    secucodes = fetch_eastmoney_constituents(market_id)
    # Repo canonicalises Shanghai to .SS, so re-canonicalise here.
    symbols = tuple(sorted({resolve_symbol(s).symbol for s in secucodes}))
    print(f"  got {len(symbols)} constituents", file=sys.stderr)

    # Constituent universe (single as_of = today).
    today = _today_iso()
    universe_df = pd.DataFrame(
        {
            "universe_id": [market_id] * len(symbols),
            "symbol": list(symbols),
            "effective_from": [today] * len(symbols),
            "effective_until": ["9999-12-31"] * len(symbols),
            "source": ["eastmoney_constituents"] * len(symbols),
            "source_version": [_today_iso()] * len(symbols),
            "source_kind": [SOURCE_KIND] * len(symbols),
        }
    )

    # Component bars.
    component_entries: list[dict] = []
    for sym in symbols:
        try:
            bars = fetch_tencent_bars(sym)
        except Exception as exc:  # noqa: BLE001 - surface every failure for the manifest
            component_entries.append({"symbol": sym, "error": str(exc), "rows": 0, "hash": ""})
            continue
        if max_bars and len(bars) > max_bars:
            bars = bars.iloc[-max_bars:].reset_index(drop=True)
        comp_path = FIXTURE_ROOT / "component_bars" / f"{sym}.parquet"
        _atomic_write_parquet(bars, comp_path)
        component_entries.append({
            "symbol": sym, "rows": int(len(bars)),
            "first_date": str(bars["date"].min().date()),
            "last_date": str(bars["date"].max().date()),
            "hash": _hash_file(comp_path),
        })

    # Index bars.
    idx_symbol = INDEX_SYMBOL[market_id]
    print(f"  fetching index bars for {market_id} via {idx_symbol}…", file=sys.stderr)
    index_df = fetch_tencent_index_bars(idx_symbol, market_id=market_id)
    if max_bars and len(index_df) > max_bars:
        index_df = index_df.iloc[-max_bars:].reset_index(drop=True)
    idx_path = FIXTURE_ROOT / "indices" / f"{market_id}.parquet"
    _atomic_write_parquet(index_df, idx_path)

    # Universe file.
    uni_path = FIXTURE_ROOT / "universes" / f"{market_id}.parquet"
    _atomic_write_parquet(universe_df, uni_path)

    return {
        "market_id": market_id,
        "constituent_count": len(symbols),
        "universe_path": str(uni_path.relative_to(REPO_ROOT)),
        "index_path": str(idx_path.relative_to(REPO_ROOT)),
        "universe_hash": _hash_file(uni_path),
        "index_hash": _hash_file(idx_path),
        "index_first_date": str(index_df["date"].min().date()),
        "index_last_date": str(index_df["date"].max().date()),
        "components": component_entries,
    }


# ── Manifest ──────────────────────────────────────────────────────────


def write_manifest(entries: list[dict]) -> None:
    manifest = {
        "manifest_version": "lei_market_data.v1",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "source_license": SOURCE_LICENSE,
        "source_kind": SOURCE_KIND,
        "note": (
            "Constituents are the current list only — no historical PIT rebalance. "
            "Therefore every universe is labelled `research_proxy`; production "
            "decisions must not use this for backtests crossing rebalance dates."
        ),
        "markets": entries,
    }
    _atomic_write_json(manifest, MANIFEST_PATH)
    print(f"wrote manifest → {MANIFEST_PATH.relative_to(REPO_ROOT)}", file=sys.stderr)


# ── Entry point ───────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--markets", nargs="*", default=list(BOARD_CODE),
        help="Markets to ingest (default: CSI_300 STAR_50)",
    )
    parser.add_argument(
        "--max-bars", type=int, default=600,
        help="Per-symbol daily bars cap (default 600 ≈ 2.5y)",
    )
    args = parser.parse_args(argv)

    entries = []
    for market in args.markets:
        if market not in BOARD_CODE:
            print(f"unknown market: {market}", file=sys.stderr)
            return 2
        entries.append(ingest_market(market, max_bars=args.max_bars))

    write_manifest(entries)
    return 0


if __name__ == "__main__":
    sys.exit(main())
