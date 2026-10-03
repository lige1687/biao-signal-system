import numpy as np
import pandas as pd
import pytest

from lei_signal.research.alphalens_component import component_analysis
from lei_signal.research.momentum_prototype import rank_diagnostic


def _panel(factor_values=(1.0, 2.0, 3.0, 4.0), dates=None, returns=(0.1, 0.2, 0.3, 0.4)):
    if dates is None:
        dates = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-04", "2024-01-05"])
    assets = ["a", "b", "c", "d"]
    rows = []
    for date in dates:
        for i, asset in enumerate(assets):
            rows.append((date, asset, factor_values[i], 1 if i < 2 else 2, returns[i]))
    index = pd.MultiIndex.from_tuples(
        [(row[0], row[1]) for row in rows], names=["date", "asset"]
    )
    return pd.DataFrame(
        {"factor": [r[2] for r in rows],
         "factor_quantile": [r[3] for r in rows],
         "20D": [r[4] for r in rows]},
        index=index,
    )


def test_positive_reverse_and_group_means_match_hand_calculation():
    dates = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-04", "2024-01-05"])
    positive = component_analysis(_panel(dates=dates))
    negative = component_analysis(
        _panel(factor_values=(4.0, 3.0, 2.0, 1.0), dates=dates)
    )

    assert np.allclose(positive["information_coefficient"]["20D"], 1.0)
    assert np.allclose(negative["information_coefficient"]["20D"], -1.0)
    means = positive["mean_return_by_date_and_quantile"]["20D"]
    assert np.allclose(means.xs(1, level="factor_quantile"), 0.15)
    assert np.allclose(means.xs(2, level="factor_quantile"), 0.35)
    assert list(positive["information_coefficient"].index) == list(dates)
    assert list(means.index.get_level_values("date").unique()) == list(dates)
    assert "not reliable inference" in positive["standard_error_note"]


def test_tied_ranks_match_project_average_rank_diagnostic():
    tied = _panel(factor_values=(1.0, 2.0, 2.0, 4.0), dates=pd.to_datetime(["2024-01-01"]))
    result = component_analysis(tied)["information_coefficient"].iloc[0]["20D"]
    independent = rank_diagnostic(pd.DataFrame({"momentum": [1.0, 2.0, 2.0, 4.0],
                                                "target": [0.1, 0.2, 0.3, 0.4]}))["value"]
    assert result == pytest.approx(independent)
    assert result == pytest.approx(pd.Series([1.0, 2.0, 2.0, 4.0]).rank().corr(
        pd.Series([0.1, 0.2, 0.3, 0.4]).rank()
    ))


def test_constant_factor_has_nan_ic():
    constant = _panel(factor_values=(7.0, 7.0, 7.0, 7.0), dates=pd.to_datetime(["2024-01-01"]))
    result = component_analysis(constant)["information_coefficient"]["20D"]
    assert result.isna().all()
