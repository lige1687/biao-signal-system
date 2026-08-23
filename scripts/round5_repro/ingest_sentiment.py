"""Ingest NAAIM / AAII investor-sentiment data into LEI_SENTIMENT_ROOT.

Round 4 already ships the loaders and classifiers
(``lei_signal.market_context.sentiment``); what was missing is a way to get
real data onto disk. This script is that missing half — and it is deliberately
**offline / manual**, not a scraper. The Round 4 design spec forbids scraping
MacroMicro / Patreon / NAAIM / AAII pages as a production pipeline.

Three ways to produce data:

  1. ``append``            — hand-enter one week's reading (offline, fully
                             compliant, the primary path).
  2. ``from-naaim-xlsx``   — convert the official NAAIM historical Excel file
                             (naaim.org → Exposure Index → historical download).
  3. ``from-aaii-csv``     — convert an AAII member export CSV into the loader
                             schema.

Output files (written to ``--root``, default ``LEI_SENTIMENT_ROOT`` or
``tests/fixtures/market_context/sentiment``):

    naaim.csv   →  survey_week, available_at, exposure_index, source,
                   license_status, publication_delay_days
    aaii.csv    →  survey_week, available_at, bullish, neutral, bearish,
                   source, license_status

These column sets are exactly what ``load_naaim_observations`` /
``load_aaii_observations`` require.

Release-time semantics: ``available_at`` must be the *publication* time, never
the survey-week start (the loader refuses to default it). Because we cannot
verify each vendor's exact release clock offline, every path defaults
``available_at`` to the **Thursday on or after the survey date** at 07:00 UTC
(NAAIM) / 08:00 UTC (AAII) — matching the Round 4 test convention — and lets
you override it with ``--available-at``. **Confirm the real release time when
you import vendor data.**

Examples:

    # Manual weekly entry
    python scripts/round5_repro/ingest_sentiment.py append \\
        --series naaim --survey-week 2026-08-10 --exposure 72.5

    python scripts/round5_repro/ingest_sentiment.py append \\
        --series aaii --survey-week 2026-08-10 --bullish 35 --neutral 28 --bearish 37

    # Convert vendor exports
    python scripts/round5_repro/ingest_sentiment.py from-naaim-xlsx \\
        --path /path/to/naaim_history.xlsx --license public_delayed
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = REPO_ROOT / "tests" / "fixtures" / "market_context" / "sentiment"

# Canonical output schemas (must match the Round 4 loaders exactly).
NAAIM_COLUMNS = [
    "survey_week", "available_at", "exposure_index", "source",
    "license_status", "publication_delay_days",
]
AAII_COLUMNS = [
    "survey_week", "available_at", "bullish", "neutral", "bearish",
    "source", "license_status",
]

NAAIM_FILENAME = "naaim.csv"
AAII_FILENAME = "aaii.csv"

# Release-time defaults: both series publish Thursday per the Round 4 test
# convention; NAAIM at 07:00 UTC, AAII at 08:00 UTC. Override with --available-at.
_RELEASE_HOURS = {"naaim": 7, "aaii": 8}
# Maximum age (calendar days) used by the loaders for "current" eligibility.
_MAX_AGE_DAYS = {"naaim": 14, "aaii": 10}


# ── Pure helpers (unit-tested) ────────────────────────────────────────


def thursday_on_or_after(d: date) -> date:
    """Return the Thursday on or after ``d`` (0 offset if already Thursday)."""
    return d + timedelta(days=(3 - d.weekday()) % 7)


def default_release_datetime(series: str, survey_date: date) -> datetime:
    """Default ``available_at`` for a series and survey date.

    NAAIM → Thursday-on-or-after at 07:00 UTC; AAII → 08:00 UTC.
    """
    series = series.lower()
    if series not in _RELEASE_HOURS:
        raise ValueError(f"Unknown series {series!r}; expected 'naaim' or 'aaii'")
    thursday = thursday_on_or_after(survey_date)
    return datetime(thursday.year, thursday.month, thursday.day, _RELEASE_HOURS[series])


def _parse_survey_week(value: str | date) -> date:
    return pd.Timestamp(value).date()


def _parse_available_at(value: str | datetime | None, series: str, survey_date: date) -> datetime:
    if value is None or str(value).strip() == "":
        return default_release_datetime(series, survey_date)
    return pd.Timestamp(value).to_pydatetime()


def build_naaim_row(
    survey_week: date,
    exposure_index: float,
    available_at: datetime | str | None = None,
    source: str = "official",
    license_status: str = "licensed",
    publication_delay_days: int = 3,
) -> dict:
    """Build one NAAIM row in the canonical schema."""
    return {
        "survey_week": survey_week.isoformat(),
        "available_at": _parse_available_at(available_at, "naaim", survey_week).isoformat(),
        "exposure_index": float(exposure_index),
        "source": source,
        "license_status": license_status,
        "publication_delay_days": int(publication_delay_days),
    }


def build_aaii_row(
    survey_week: date,
    bullish: float,
    neutral: float,
    bearish: float,
    available_at: datetime | str | None = None,
    source: str = "official",
    license_status: str = "licensed",
) -> dict:
    """Build one AAII row in the canonical schema."""
    return {
        "survey_week": survey_week.isoformat(),
        "available_at": _parse_available_at(available_at, "aaii", survey_week).isoformat(),
        "bullish": float(bullish),
        "neutral": float(neutral),
        "bearish": float(bearish),
        "source": source,
        "license_status": license_status,
    }


def dedupe_and_sort(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Drop duplicate survey_week rows (keep last) and sort by available_at."""
    df = df[columns].copy()
    df = df.drop_duplicates(subset=["survey_week"], keep="last")
    df["_sort"] = pd.to_datetime(df["available_at"], utc=True)
    df = df.sort_values("_sort").drop(columns="_sort")
    return df.reset_index(drop=True)


def load_existing(root: Path, filename: str, columns: list[str]) -> pd.DataFrame:
    """Load an existing CSV if present, else an empty schema-valid frame."""
    path = root / filename
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame(columns=columns)


def _atomic_write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(path)


def append_observation(
    root: Path, series: str, row: dict, columns: list[str], filename: str,
) -> Path:
    """Append one row to the series file, dedupe by survey_week, and write."""
    existing = load_existing(root, filename, columns)
    new_row = pd.DataFrame([row])
    combined = new_row if existing.empty else pd.concat(
        [existing, new_row], ignore_index=True,
    )
    clean = dedupe_and_sort(combined, columns)
    path = root / filename
    _atomic_write_csv(clean, path)
    return path


# ── Vendor-export converters ──────────────────────────────────────────


def _find_column(df: pd.DataFrame, *candidates: str) -> str | None:
    """Case-insensitive, whitespace-tolerant column lookup."""
    norm = {str(c).strip().lower(): str(c) for c in df.columns}
    for cand in candidates:
        if cand.lower() in norm:
            return norm[cand.lower()]
    return None


def from_naaim_xlsx(
    path: Path,
    *,
    date_column: str | None = None,
    value_column: str | None = None,
    source: str = "naaim.org",
    license_status: str = "public_delayed",
    publication_delay_days: int = 3,
    release_offset_days: int | None = None,
) -> pd.DataFrame:
    """Convert the official NAAIM historical Excel into the canonical schema.

    Auto-detects the date column (Date) and the headline exposure column
    (Average / Mean). ``release_offset_days`` overrides the Thursday-on-or-after
    default: set it to the exact gap between the file's date and the real
    publication date when you know it.
    """
    df = pd.read_excel(path)
    date_col = date_column or _find_column(df, "date", "survey_week", "survey week")
    val_col = value_column or _find_column(df, "average", "mean", "exposure index", "exposure")
    if date_col is None:
        raise ValueError(f"Could not auto-detect a date column in {path}; pass --date-column.")
    if val_col is None:
        raise ValueError(
            f"Could not auto-detect an exposure column in {path}; pass --value-column."
        )

    rows = []
    for _, r in df.iterrows():
        survey = _parse_survey_week(r[date_col])
        available = default_release_datetime("naaim", survey)
        if release_offset_days is not None:
            available = datetime.combine(
                survey + timedelta(days=int(release_offset_days)),
                datetime.min.time(),
            )
        rows.append({
            "survey_week": survey.isoformat(),
            "available_at": available.isoformat(),
            "exposure_index": float(r[val_col]),
            "source": source,
            "license_status": license_status,
            "publication_delay_days": int(publication_delay_days),
        })
    return dedupe_and_sort(pd.DataFrame(rows), NAAIM_COLUMNS)


def from_aaii_csv(
    path: Path,
    *,
    date_column: str | None = None,
    bullish_column: str | None = None,
    neutral_column: str | None = None,
    bearish_column: str | None = None,
    source: str = "aaii",
    license_status: str = "licensed",
    release_offset_days: int | None = None,
) -> pd.DataFrame:
    """Convert an AAII member-export CSV into the canonical schema.

    Auto-detects the Date / Bullish / Neutral / Bearish columns case-insensitively.
    ``release_offset_days`` overrides the Thursday-on-or-after default.
    """
    df = pd.read_csv(path)
    date_col = date_column or _find_column(df, "date", "survey_week", "survey week")
    b_col = bullish_column or _find_column(df, "bullish", "bull")
    n_col = neutral_column or _find_column(df, "neutral")
    s_col = bearish_column or _find_column(df, "bearish", "bear")
    for name, col in (("date", date_col), ("bullish", b_col),
                      ("neutral", n_col), ("bearish", s_col)):
        if col is None:
            raise ValueError(f"Could not auto-detect the {name} column in {path}.")

    rows = []
    for _, r in df.iterrows():
        survey = _parse_survey_week(r[date_col])
        available = default_release_datetime("aaii", survey)
        if release_offset_days is not None:
            available = datetime.combine(
                survey + timedelta(days=int(release_offset_days)),
                datetime.min.time(),
            )
        rows.append({
            "survey_week": survey.isoformat(),
            "available_at": available.isoformat(),
            "bullish": float(r[b_col]),
            "neutral": float(r[n_col]),
            "bearish": float(r[s_col]),
            "source": source,
            "license_status": license_status,
        })
    return dedupe_and_sort(pd.DataFrame(rows), AAII_COLUMNS)


# ── CLI ───────────────────────────────────────────────────────────────


def _resolve_root(args) -> Path:
    if getattr(args, "root", None):
        return Path(args.root).expanduser()
    env = os.environ.get("LEI_SENTIMENT_ROOT")
    if env:
        return Path(env).expanduser()
    return DEFAULT_ROOT


def _cmd_append(args) -> int:
    root = _resolve_root(args)
    series = args.series.lower()
    survey = _parse_survey_week(args.survey_week)
    available = getattr(args, "available_at", None)

    if series == "naaim":
        if args.exposure is None:
            raise SystemExit("append --series naaim requires --exposure")
        row = build_naaim_row(
            survey, args.exposure, available_at=available,
            source=args.source, license_status=args.license_status,
            publication_delay_days=args.publication_delay_days,
        )
        path = append_observation(root, series, row, NAAIM_COLUMNS, NAAIM_FILENAME)
    elif series == "aaii":
        if args.bullish is None or args.neutral is None or args.bearish is None:
            raise SystemExit("append --series aaii requires --bullish --neutral --bearish")
        row = build_aaii_row(
            survey, args.bullish, args.neutral, args.bearish,
            available_at=available, source=args.source,
            license_status=args.license_status,
        )
        path = append_observation(root, series, row, AAII_COLUMNS, AAII_FILENAME)
    else:
        raise SystemExit("--series must be 'naaim' or 'aaii'")

    if series == "naaim":
        out_cols, out_file = NAAIM_COLUMNS, NAAIM_FILENAME
    else:
        out_cols, out_file = AAII_COLUMNS, AAII_FILENAME

    print(f"appended {series} observation → {path}")
    print(f"  survey_week={row['survey_week']}  available_at={row['available_at']}")
    print(f"  rows now: {len(load_existing(root, out_file, out_cols))}")
    return 0


def _cmd_from_naaim(args) -> int:
    root = _resolve_root(args)
    df = from_naaim_xlsx(
        Path(args.path), value_column=args.value_column, date_column=args.date_column,
        source=args.source, license_status=args.license_status,
        publication_delay_days=args.publication_delay_days,
        release_offset_days=args.release_offset_days,
    )
    _atomic_write_csv(df, root / NAAIM_FILENAME)
    print(f"wrote {len(df)} NAAIM rows → {root / NAAIM_FILENAME}")
    print("REMINDER: confirm available_at reflects the real publication time "
          "(--release-offset-days), and set --license-status appropriately.")
    return 0


def _cmd_from_aaii(args) -> int:
    root = _resolve_root(args)
    df = from_aaii_csv(
        Path(args.path), date_column=args.date_column,
        bullish_column=args.bullish_column, neutral_column=args.neutral_column,
        bearish_column=args.bearish_column, source=args.source,
        license_status=args.license_status, release_offset_days=args.release_offset_days,
    )
    _atomic_write_csv(df, root / AAII_FILENAME)
    print(f"wrote {len(df)} AAII rows → {root / AAII_FILENAME}")
    print("REMINDER: confirm available_at reflects the real publication time "
          "(--release-offset-days), and set --license-status appropriately.")
    return 0


def _add_common_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", help="输出目录（默认 LEI_SENTIMENT_ROOT 或 fixtures/sentiment）")
    parser.add_argument("--source", default="official")
    parser.add_argument("--license-status", default="licensed",
                        help="licensed / public_delayed 等（public_delayed 不参与当前摘要）")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_append = sub.add_parser("append", help="手工录入一期读数")
    p_append.add_argument("--series", required=True, choices=["naaim", "aaii"])
    p_append.add_argument("--survey-week", required=True,
                          help="调查周起始日（ISO 日期，例如 2026-08-10）")
    p_append.add_argument("--exposure", type=float, help="NAAIM 暴露指数")
    p_append.add_argument("--bullish", type=float, help="AAII 看多 %")
    p_append.add_argument("--neutral", type=float, help="AAII 中性 %")
    p_append.add_argument("--bearish", type=float, help="AAII 看空 %")
    p_append.add_argument("--available-at",
                          help="发布时间（ISO 时间戳；缺省用 series 默认的周四 07:00/08:00）")
    p_append.add_argument("--publication-delay-days", type=int, default=3)
    _add_common_parser(p_append)

    p_naaim = sub.add_parser("from-naaim-xlsx", help="转换 NAAIM 官方历史 Excel")
    p_naaim.add_argument("--path", required=True)
    p_naaim.add_argument("--date-column")
    p_naaim.add_argument("--value-column", help="暴露指数列（默认自动识别 Average/Mean）")
    p_naaim.add_argument("--publication-delay-days", type=int, default=3)
    p_naaim.add_argument("--release-offset-days", type=int,
                         help="调查日到发布日的精确天数偏移（缺省用周四自动对齐）")
    _add_common_parser(p_naaim)

    p_aaii = sub.add_parser("from-aaii-csv", help="转换 AAII 会员导出 CSV")
    p_aaii.add_argument("--path", required=True)
    p_aaii.add_argument("--date-column")
    p_aaii.add_argument("--bullish-column")
    p_aaii.add_argument("--neutral-column")
    p_aaii.add_argument("--bearish-column")
    p_aaii.add_argument("--release-offset-days", type=int)
    _add_common_parser(p_aaii)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "append":
        return _cmd_append(args)
    if args.command == "from-naaim-xlsx":
        return _cmd_from_naaim(args)
    if args.command == "from-aaii-csv":
        return _cmd_from_aaii(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
