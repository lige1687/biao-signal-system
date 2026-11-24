"""Read a SHA-bound OSAP reference vintage without changing its source files.

The published long-short returns are descriptive US-stock reference data. They
are not LEI signals, point-in-time observations, or trading instructions.
"""

from __future__ import annotations

import argparse
import csv
from datetime import date, datetime
import hashlib
import json
import math
from pathlib import Path


SCHEMA = "osap-reference/1"
CATALOG_FIELDS = (
    "Acronym", "Cat.Signal", "Predictability in OP", "Signal Rep Quality",
    "Authors", "Year", "LongDescription", "Journal", "Cat.Form", "Cat.Data",
    "Cat.Economic", "SampleStartYear", "SampleEndYear", "Acronym2",
    "Evidence Summary", "Key Table in OP", "Test in OP", "Sign", "Return",
    "T-Stat", "Stock Weight", "LS Quantile", "Quantile Filter",
    "Portfolio Period", "Start Month", "Filter", "Notes", "Detailed Definition",
)
MISSING = {"", "NA"}
LIMITATIONS = [
    "Published US aggregate long-short returns are descriptive reference data.",
    "Historical stock-level availability and source-code vintage are not qualified.",
    "No production or trading use is authorized.",
]


def _object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _source(manifest_path: Path, binding: dict) -> Path:
    if not isinstance(binding, dict) or set(binding) != {"path", "sha256"}:
        raise ValueError("source binding requires path and sha256")
    relative = binding["path"]
    sha = binding["sha256"]
    if not isinstance(relative, str) or not relative or ".." in Path(relative).parts:
        raise ValueError("source path must be an absolute path or relative without '..'")
    if not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError("invalid source sha256")
    base = manifest_path.parent.resolve()
    supplied = Path(relative)
    path = (supplied if supplied.is_absolute() else base / supplied).resolve()
    if (not supplied.is_absolute() and not path.is_relative_to(base)) or not path.is_file():
        raise ValueError(f"source missing or outside manifest directory: {relative}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != sha:
        raise ValueError(f"source SHA-256 mismatch: {relative}")
    return path


def _csv_rows(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle, strict=True)
        try:
            header = next(reader)
        except StopIteration:
            raise ValueError(f"empty CSV: {path.name}") from None
        if not header or any(not field for field in header) or len(set(header)) != len(header):
            raise ValueError(f"blank or duplicate CSV column: {path.name}")
        rows = []
        for line, values in enumerate(reader, start=2):
            if len(values) != len(header):
                raise ValueError(f"CSV width mismatch: {path.name}:{line}")
            rows.append(dict(zip(header, values)))
    return header, rows


def _date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"invalid ISO date: {value}") from None
    if parsed.isoformat() != value:
        raise ValueError(f"invalid ISO date: {value}")
    return value


def load_reference(manifest):
    """Validate and load a local vintage. All returned source rows are unmodified."""
    manifest_path = Path(manifest).resolve()
    spec = json.loads(manifest_path.read_text(encoding="utf-8"), object_pairs_hook=_object_pairs)
    required = {"schema", "vintage", "market", "retrieved_at", "published_at",
                "catalog", "returns", "return_unit", "return_direction"}
    if not isinstance(spec, dict) or set(spec) != required:
        raise ValueError("manifest fields differ from osap-reference/1")
    if spec["schema"] != SCHEMA or spec["market"] != "US":
        raise ValueError("unsupported schema or market")
    if not isinstance(spec["vintage"], str) or not spec["vintage"].strip():
        raise ValueError("vintage is required")
    for field in ("retrieved_at", "published_at"):
        value = spec[field]
        if field == "published_at" and value is None:
            continue
        if not isinstance(value, str):
            raise ValueError(f"{field} requires timezone-aware timestamp or null")
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            raise ValueError(f"invalid {field}") from None
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError(f"{field} requires timezone")
    if spec["return_unit"] != "percent" or spec["return_direction"] != "published_long_short":
        raise ValueError("undeclared or unsupported return unit/direction")
    catalog_path = _source(manifest_path, spec["catalog"])
    returns_path = _source(manifest_path, spec["returns"])
    catalog_header, catalog_rows = _csv_rows(catalog_path)
    if not catalog_rows:
        raise ValueError("empty catalog rows")
    missing_fields = set(CATALOG_FIELDS) - set(catalog_header)
    if missing_fields:
        raise ValueError(f"catalog missing columns: {sorted(missing_fields)}")
    catalog = {}
    for row in catalog_rows:
        acronym = row["Acronym"]
        if not acronym or acronym in catalog:
            raise ValueError(f"blank or duplicate Acronym: {acronym}")
        catalog[acronym] = row
    returns_header, raw_returns = _csv_rows(returns_path)
    if not raw_returns:
        raise ValueError("empty returns rows")
    date_columns = [name for name in returns_header if name.casefold() == "date"]
    if len(date_columns) != 1:
        raise ValueError("returns require one date column")
    date_column = date_columns[0]
    signals = [name for name in returns_header if name != date_column]
    if not signals or any(name not in catalog for name in signals):
        raise ValueError("returns contain unknown or no signals")
    rows = []
    dates = set()
    months = set()
    for row in raw_returns:
        day = _date(row[date_column])
        month = day[:7]
        if day in dates or month in months:
            raise ValueError(f"duplicate return date or month: {day}")
        dates.add(day)
        months.add(month)
        values = {}
        for signal in signals:
            raw = row[signal]
            if raw.strip() in MISSING:
                values[signal] = None
            else:
                try:
                    value = float(raw)
                except ValueError:
                    raise ValueError(f"non-numeric return {signal} at {day}: {raw}") from None
                if not math.isfinite(value):
                    raise ValueError(f"non-finite return {signal} at {day}")
                values[signal] = value
        rows.append({"date": day, "values": values})
    rows.sort(key=lambda item: item["date"])
    return {"manifest": spec, "manifest_path": str(manifest_path),
            "catalog_columns": catalog_header, "catalog": catalog,
            "return_columns": signals, "rows": rows}


def _provenance(reference):
    spec = reference["manifest"]
    return {"manifest_path": reference["manifest_path"], "vintage": spec["vintage"],
            "market": spec["market"], "retrieved_at": spec["retrieved_at"],
            "published_at": spec["published_at"],
            "bindings": {"catalog": spec["catalog"], "returns": spec["returns"]},
            "execution_authorized": False, "limitations": LIMITATIONS}


def catalog(reference, *, signal=None, term=None):
    if signal is not None and signal not in reference["catalog"]:
        raise ValueError(f"unknown signal: {signal}")
    items = reference["catalog"].items()
    if signal is not None:
        items = [(signal, reference["catalog"][signal])]
    if term:
        needle = term.casefold()
        items = [(key, row) for key, row in items
                 if any(needle in value.casefold() for value in row.values())]
    rows = [row for _, row in items]
    return {**_provenance(reference), "columns": reference["catalog_columns"],
            "count": len(rows), "rows": rows}


def series(reference, signals):
    selected = list(dict.fromkeys(signals))
    if not selected:
        raise ValueError("at least one signal required")
    for signal in selected:
        if signal not in reference["return_columns"]:
            raise ValueError(f"unknown return signal: {signal}")
    rows = [{"date": row["date"], "returns": {
        signal: {"percent": row["values"][signal],
                 "decimal": None if row["values"][signal] is None else row["values"][signal] / 100}
        for signal in selected}} for row in reference["rows"]]
    missing = {signal: sum(row["returns"][signal]["percent"] is None for row in rows)
               for signal in selected}
    return {**_provenance(reference), "signals": selected,
            "date_range": [rows[0]["date"], rows[-1]["date"]] if rows else None,
            "row_count": len(rows), "missing_count": missing,
            "unit": "percent", "direction": "published_long_short", "rows": rows}


def diff(left, right):
    """Compare two published vintages; revisions are not point-in-time evidence."""
    old_cat, new_cat = left["catalog"], right["catalog"]
    old_sig, new_sig = set(old_cat), set(new_cat)
    catalog_changes = {}
    for signal in sorted(old_sig & new_sig):
        fields = {field: {"old": old_cat[signal].get(field), "new": new_cat[signal].get(field)}
                  for field in sorted(set(old_cat[signal]) | set(new_cat[signal]))
                  if old_cat[signal].get(field) != new_cat[signal].get(field)}
        if fields:
            catalog_changes[signal] = fields
    old_dates = {row["date"]: row["values"] for row in left["rows"]}
    new_dates = {row["date"]: row["values"] for row in right["rows"]}
    old_cols, new_cols = set(left["return_columns"]), set(right["return_columns"])
    missing_old = {signal: sum(values[signal] is None for values in old_dates.values())
                   for signal in sorted(old_cols)}
    missing_new = {signal: sum(values[signal] is None for values in new_dates.values())
                   for signal in sorted(new_cols)}
    return_changes = []
    missing_changes = []
    for day in sorted(set(old_dates) & set(new_dates)):
        for signal in sorted(old_cols & new_cols):
            before, after = old_dates[day][signal], new_dates[day][signal]
            if before != after:
                item = {"date": day, "signal": signal, "old_percent": before, "new_percent": after}
                return_changes.append(item)
                if (before is None) != (after is None):
                    missing_changes.append(item)
    return {"old": _provenance(left), "new": _provenance(right),
            "execution_authorized": False, "limitations": LIMITATIONS,
            "old_vintage": left["manifest"]["vintage"],
            "new_vintage": right["manifest"]["vintage"],
            "old_date_range": [min(old_dates), max(old_dates)] if old_dates else None,
            "new_date_range": [min(new_dates), max(new_dates)] if new_dates else None,
            "missing_count_old": missing_old, "missing_count_new": missing_new,
            "catalog_added": sorted(new_sig - old_sig), "catalog_removed": sorted(old_sig - new_sig),
            "catalog_changed": catalog_changes,
            "return_signals_added": sorted(new_cols - old_cols),
            "return_signals_removed": sorted(old_cols - new_cols),
            "dates_added": sorted(set(new_dates) - set(old_dates)),
            "dates_removed": sorted(set(old_dates) - set(new_dates)),
            "return_changes": return_changes, "missing_changes": missing_changes,
            "return_change_count": len(return_changes), "missing_change_count": len(missing_changes),
            "interpretation_note": "Vintage differences do not establish when historical data became available."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    catalog_cmd = commands.add_parser("catalog")
    catalog_cmd.add_argument("--signal")
    catalog_cmd.add_argument("--term")
    series_cmd = commands.add_parser("series")
    series_cmd.add_argument("--signal", action="append", required=True)
    diff_cmd = commands.add_parser("diff")
    diff_cmd.add_argument("--other-manifest", required=True)
    args = parser.parse_args(argv)
    try:
        reference = load_reference(args.manifest)
        if args.command == "catalog":
            result = catalog(reference, signal=args.signal, term=args.term)
        elif args.command == "series":
            result = series(reference, args.signal)
        else:
            result = diff(reference, load_reference(args.other_manifest))
    except (ValueError, OSError, csv.Error, json.JSONDecodeError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
