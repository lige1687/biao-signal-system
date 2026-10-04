"""Build outcome-free color inventory from the pinned local panel."""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from lei_signal.research.color_history_information import history_rows

ROOT = Path(__file__).resolve().parents[5]
PANEL = ROOT / "docs/experiments/raw/volume-information-2026-09-30/execution/panel.json"
EXPECTED = "382d82ff21cb43758bca8e596026284ba2821038a79e1b4c331135119524679b"
DEST = Path(__file__).with_name("inventory.json")
START, END = "2022-01-04", "2026-06-30"


def summarize(rows):
    return {"rows": len(rows), "dates": len({r["date"] for r in rows}),
            "color_segments_descriptive": len({r["color_run_id"] for r in rows if r["color_run_id"]}),
            "group_segments_descriptive": len({r["group_run_id"] for r in rows if r["group_run_id"]})}


def main():
    digest = sha256(PANEL.read_bytes()).hexdigest()
    if digest != EXPECTED:
        raise ValueError(f"panel SHA changed: {digest}")
    payload = json.loads(PANEL.read_text())
    rows = history_rows(payload)
    selected = [r for r in rows if START <= r["date"] <= END]
    calendar = payload["calendar"]
    positions = {day: i for i, day in enumerate(calendar)}
    def mature(row):
        j = positions[row["date"]] + 21
        return calendar[j] if j < len(calendar) else None
    cells = {}
    gray_by_asset_year_group = {}
    for asset in sorted({r["asset"] for r in selected}):
        for year in range(2022, 2027):
            subset = [r for r in selected if r["asset"] == asset and r["date"].startswith(str(year))]
            cells[f"{asset}|{year}"] = {
                f"{a}->{b}": summarize([r for r in subset if r["prior_color20"] == a and r["color20"] == b])
                for a in ("black", "gray", "green") for b in ("black", "gray", "green")}
            cells[f"{asset}|{year}"]["unknown"] = summarize([
                r for r in subset if r["prior_color20"] is None or r["color20"] is None])
            for group in ("bull", "bear", "overlap"):
                gray_subset = [r for r in subset if r["color20"] == "gray" and r["group"] == group]
                gray_by_asset_year_group[f"{asset}|{year}|{group}"] = {
                    "summary": summarize(gray_subset),
                    "by_origin": dict(Counter(str(r["gray_origin"]) for r in gray_subset)),
                    "by_subtype": dict(Counter(r["state20"] for r in gray_subset))}
    folds = {}
    for name, train_end, eval_start, eval_end in (
        ("train2022_2024_eval2025", "2024-12-31", "2025-01-01", "2025-12-31"),
        ("train2022_2025_eval2026H1", "2025-12-31", "2026-01-01", "2026-06-30"),
    ):
        folds[name] = {}
        for phase in ("train", "evaluation"):
            subset = [r for r in selected if r["group"] == "bull" and r["color20"] == "gray"
                      and mature(r) is not None and
                      ((r["date"] <= train_end and mature(r) < eval_start) if phase == "train"
                       else (eval_start <= r["date"] <= eval_end and mature(r) <= eval_end))]
            folds[name][phase] = {"summary": summarize(subset),
                "by_origin": dict(Counter(str(r["gray_origin"]) for r in subset)),
                "by_subtype": dict(Counter(r["state20"] for r in subset)),
                "by_asset_origin": {asset: dict(Counter(str(r["gray_origin"]) for r in subset
                                                  if r["asset"] == asset))
                                    for asset in sorted({r["asset"] for r in selected})},
                "gray_rows_without_future_resolution_filter": len(subset)}
    out = {"schema": "color-history-inventory/1", "source_panel_sha256": digest,
           "study_period": [START, END], "total": summarize(selected),
           "unknown": summarize([r for r in selected if not r["ready_252"]]),
           "transition_cells_by_asset_year": cells,
           "all_gray_by_asset_year_group": gray_by_asset_year_group,
           "bull_gray_fold_counts": folds,
           "notes": ["No future OHLC values, outcome labels or fitted models were read for a feature row.",
                     "t+21 calendar maturity only limits fold membership; it is not an outcome.",
                     "Segment counts describe runs and are not statistically independent episodes.",
                     "Gray rows include unresolved spells and later expired bull groups; no exit-success filter."]}
    DEST.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"total": out["total"], "unknown": out["unknown"],
                      "folds": folds}, ensure_ascii=False))


if __name__ == "__main__":
    main()
