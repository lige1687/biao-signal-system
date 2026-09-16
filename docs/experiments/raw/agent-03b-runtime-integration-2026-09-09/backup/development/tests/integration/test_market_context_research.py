"""Task 8 integration tests — market context research without filtering."""

from __future__ import annotations

import pandas as pd

from lei_signal.research.market_context import (
    attach_market_context,
    summarize_outcomes_by_context,
)


class TestAttachMarketContext:
    def test_preserves_row_count(self) -> None:
        outcomes = pd.DataFrame({
            "signal_date": ["2024-06-01", "2024-06-15", "2024-07-01"],
            "forward_return_20": [0.05, -0.02, 0.10],
            "mfe_20": [0.08, 0.01, 0.12],
            "mae_20": [-0.02, -0.05, 0.0],
        })

        contexts = pd.DataFrame({
            "summary": ["tailwind", "headwind"],
            "long_regime": ["bull", "bear"],
            "heat_state": ["neutral", "cold"],
            "breadth_direction": ["expanding", "contracting"],
        }, index=pd.to_datetime(["2024-05-30", "2024-06-10"]))

        enriched = attach_market_context(outcomes, contexts)

        assert len(enriched) == 3  # row count preserved
        assert "forward_return_20" in enriched.columns
        assert "context_summary" in enriched.columns

    def test_missing_context_yields_unknown(self) -> None:
        outcomes = pd.DataFrame({
            "signal_date": ["2024-06-01"],
            "forward_return_20": [0.05],
        })

        contexts = pd.DataFrame({
            "summary": ["tailwind"],
        }, index=pd.to_datetime(["2024-07-01"]))  # context is AFTER signal

        enriched = attach_market_context(outcomes, contexts)
        assert enriched.loc[0, "context_summary"] == "unknown"

    def test_adds_columns_does_not_drop_signals(self) -> None:
        outcomes = pd.DataFrame({
            "signal_date": ["2024-06-15"],
            "forward_return_20": [0.05],
            "mfe_20": [0.08],
            "mae_20": [-0.02],
            "signal_type": ["bottom_watch"],
        })

        contexts = pd.DataFrame({
            "summary": ["tailwind"],
        }, index=pd.to_datetime(["2024-06-10"]))

        enriched = attach_market_context(outcomes, contexts)

        # Original columns preserved
        assert enriched.loc[0, "forward_return_20"] == 0.05
        assert enriched.loc[0, "signal_type"] == "bottom_watch"
        # Context added
        assert enriched.loc[0, "context_summary"] == "tailwind"


class TestSummarizeByContext:
    def test_empty_input_returns_empty(self) -> None:
        result = summarize_outcomes_by_context(pd.DataFrame())
        assert len(result) == 0

    def test_groups_by_summary(self) -> None:
        enriched = pd.DataFrame({
            "context_summary": ["tailwind", "tailwind", "headwind"],
            "forward_return_20": [0.05, 0.03, -0.02],
            "mfe_20": [0.08, 0.05, 0.01],
            "mae_20": [-0.01, -0.02, -0.05],
        })

        result = summarize_outcomes_by_context(enriched)
        assert len(result) == 2
        assert result.loc[result["context_summary"] == "tailwind", "sample_count"].iloc[0] == 2
        assert result.loc[result["context_summary"] == "headwind", "sample_count"].iloc[0] == 1
