import json

import pandas as pd
import pytest

from lei_signal.research import ranking_diagnostics
from lei_signal.research.ranking_diagnostics import analyze_ranks

ASSETS = tuple("ABCDEF")


def rows(days, values):
    return pd.DataFrame(
        [
            (day, asset, score)
            for day, scores in zip(days, values, strict=True)
            for asset, score in zip(ASSETS, scores, strict=True)
        ],
        columns=["date", "asset", "factor"],
    )


def test_stable_reversed_and_partial_membership():
    days = ["2026-01-02", "2026-01-05", "2026-01-07", "2026-01-08"]
    data = rows(days, [range(6), range(6), range(5, -1, -1), [5, 3, 4, 2, 0, 1]])
    result = analyze_ranks(data, calendar=days, assets=ASSETS, periods=(1,))
    records = result["periods"]["1"]["daily"]
    assert [r["rank_correlation"] for r in records[:3]] == [None, 1.0, -1.0]
    assert records[3]["rank_correlation"] == pytest.approx(1 - 24 / 210)
    assert records[1]["top_turnover"] == 0
    assert records[2]["top_turnover"] == 1
    assert records[3]["top_turnover"] == 0.5
    assert records[3]["bottom_turnover"] == 0


def test_boundary_tie_only_invalidates_affected_group():
    days = ["2026-01-02", "2026-01-05"]
    result = analyze_ranks(
        rows(days, [range(6), [0, 1, 2, 3, 3, 5]]), calendar=days, assets=ASSETS, periods=(1,)
    )
    current = result["periods"]["1"]["daily"][1]
    assert current["bottom_turnover"] == 0
    assert current["top_turnover"] is None
    assert "top_boundary_tie" in current["top_reason"]
    assert current["rank_correlation"] is not None


def test_upstream_group_empty_for_entire_calendar():
    days = ["2026-01-02", "2026-01-05"]
    tied = [0, 1, 2, 3, 3, 5]
    result = analyze_ranks(rows(days, [tied, tied]), calendar=days, assets=ASSETS, periods=(1,))
    second = result["periods"]["1"]["daily"][1]
    assert second["top_turnover"] is None
    assert second["top_reason"] == "top_boundary_tie"
    assert second["bottom_turnover"] == 0


def test_missing_date_kept_and_constant_ranks_invalid():
    days = ["2026-01-02", "2026-01-05", "2026-01-06", "2026-01-09"]
    result = analyze_ranks(
        rows(days, [range(6), [0, 1, None, 3, 4, 5], range(6), [1] * 6]),
        calendar=days,
        assets=ASSETS,
        periods=(1, 2),
    )
    one = result["periods"]["1"]["daily"]
    two = result["periods"]["2"]["daily"]
    assert len(one) == len(days)
    assert one[2]["rank_correlation"] is None
    assert "missing_score" in one[2]["rank_reason"]
    assert two[2]["rank_correlation"] == 1.0
    assert one[3]["rank_correlation"] is None
    assert "constant_rank" in one[3]["rank_reason"]


@pytest.mark.parametrize("change", ["missing", "duplicate", "extra", "infinite"])
def test_input_grid_and_finiteness(change):
    days = ["2026-01-02", "2026-01-05"]
    frame = rows(days, [range(6), range(6)])
    if change == "missing":
        frame = frame.iloc[:-1]
    elif change == "duplicate":
        frame = pd.concat([frame, frame.iloc[[0]]])
    elif change == "extra":
        frame = pd.concat([frame, pd.DataFrame([("2026-01-06", "A", 0)], columns=frame.columns)])
    else:
        frame["factor"] = frame["factor"].astype(float)
        frame.loc[0, "factor"] = float("inf")
    with pytest.raises(ValueError):
        analyze_ranks(frame, calendar=days, assets=ASSETS, periods=(1,))


def test_calls_both_pinned_upstream_functions(monkeypatch):
    days = ["2026-01-02", "2026-01-05"]
    original = ranking_diagnostics._upstream_functions
    seen = []

    def wrapped():
        functions, provenance = original()
        for name in ("quantile_turnover", "factor_rank_autocorrelation"):
            function = functions[name]

            def record(*args, _name=name, _function=function, **kwargs):
                seen.append(_name)
                return _function(*args, **kwargs)

            functions[name] = record
        return functions, provenance

    monkeypatch.setattr(ranking_diagnostics, "_upstream_functions", wrapped)
    analyze_ranks(rows(days, [range(6), range(6)]), calendar=days, assets=ASSETS, periods=(1,))
    assert seen.count("factor_rank_autocorrelation") == 1
    assert seen.count("quantile_turnover") == 2


def test_cli_reads_only_three_columns_and_refuses_overwrite(tmp_path, monkeypatch):
    days = ["2026-01-02", "2026-01-05"]
    source = tmp_path / "scores.csv"
    rows(days, [range(6), range(6)]).assign(
        target_return="not-a-number", valid="future-only"
    ).to_csv(source, index=False)
    calendar = tmp_path / "calendar.json"
    calendar.write_text(json.dumps(days))
    output = tmp_path / "result.json"
    real_read_csv = pd.read_csv
    selected = []

    def read_selected(*args, **kwargs):
        selected.extend(kwargs["usecols"])
        return real_read_csv(*args, **kwargs)

    monkeypatch.setattr(ranking_diagnostics.pd, "read_csv", read_selected)
    arguments = [
        "--input",
        str(source),
        "--calendar",
        str(calendar),
        "--assets",
        ",".join(ASSETS),
        "--periods",
        "1",
        "--output",
        str(output),
    ]
    ranking_diagnostics.main(arguments)
    saved = json.loads(output.read_text())
    assert selected == ["date", "asset", "factor"]
    assert saved["periods"]["1"]["daily"][1]["rank_correlation"] == 1
    assert saved["input"]["columns_read"] == selected
    before = output.read_bytes()
    with pytest.raises(FileExistsError):
        ranking_diagnostics.main(arguments)
    assert output.read_bytes() == before
