"""Narrow adapters for three pinned Alphalens Reloaded analysis functions.

Only the unchanged function bodies named below are compiled from the vendored
sources. This does not load Alphalens as a package or construct forward returns.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import warnings
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
from scipy import stats


_VENDOR = Path(__file__).with_name("vendor") / "alphalens_components"
_PROVENANCE = _VENDOR / "PROVENANCE.json"


def _load_pinned_functions():
    provenance = json.loads(_PROVENANCE.read_text(encoding="utf-8"))
    expected = {item["path"]: item["sha256"] for item in provenance["files"]}
    sources = {}
    for filename in ("performance.py", "utils.py", "LICENSE"):
        path = _VENDOR / filename
        key = path.relative_to(_VENDOR.parents[4]).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if expected.get(key) != digest:
            raise RuntimeError(f"vendored Alphalens source hash mismatch: {filename}")
        if filename.endswith(".py"):
            sources[filename] = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    namespace = {
        "np": np,
        "pd": pd,
        "stats": stats,
        "re": re,
        "warnings": warnings,
        "utils": SimpleNamespace(),
    }

    def extract(module_name, function_name):
        module = sources[module_name]
        nodes = [node for node in module.body
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and node.name == function_name]
        if len(nodes) != 1:
            raise RuntimeError(f"expected one {function_name} in {module_name}")
        node = nodes[0]
        ast.fix_missing_locations(node)
        exec(compile(ast.Module(body=[node], type_ignores=[]),
                     f"{module_name}:{function_name}", "exec"), namespace)
        return namespace[function_name]

    get_columns = extract("utils.py", "get_forward_returns_columns")
    namespace["utils"].get_forward_returns_columns = get_columns
    ic = extract("performance.py", "factor_information_coefficient")
    by_quantile = extract("performance.py", "mean_return_by_quantile")
    return ic, by_quantile


_factor_information_coefficient, _mean_return_by_quantile = _load_pinned_functions()


def component_analysis(frame: pd.DataFrame) -> dict:
    """Compute date-wise rank IC and raw date/quantile mean returns.

    ``frame`` must contain supplied forward returns in ``20D`` and use a
    ``(date, asset)`` MultiIndex. No labels are generated or filtered here.
    Returned source standard errors are retained for traceability only; their
    independent-observation assumption is not a reliable inference here.
    """
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("frame must be a pandas DataFrame")
    if not isinstance(frame.index, pd.MultiIndex) or frame.index.nlevels != 2:
        raise ValueError("frame index must be a two-level (date, asset) MultiIndex")
    if list(frame.index.names) != ["date", "asset"]:
        raise ValueError("MultiIndex levels must be named 'date' and 'asset'")
    required = {"factor", "factor_quantile", "20D"}
    if not required.issubset(frame.columns):
        raise ValueError(f"frame is missing required columns: {sorted(required - set(frame.columns))}")
    if frame.index.has_duplicates:
        raise ValueError("frame must have unique (date, asset) rows")
    dates = pd.DatetimeIndex(frame.index.get_level_values("date").unique()).sort_values()
    if dates.empty:
        raise ValueError("frame must contain at least one date")

    selected = frame.loc[:, ["factor", "factor_quantile", "20D"]].copy()
    ic = _factor_information_coefficient(
        selected, group_adjust=False, by_group=False
    )
    # The upstream function may fill calendar dates via asfreq. Keep only dates
    # actually present in this supplied panel, preserving the original axis.
    ic = ic.reindex(dates)
    ic.index.name = "date"
    means, source_iid_stderr = _mean_return_by_quantile(
        selected,
        by_date=True,
        by_group=False,
        demeaned=False,
        group_adjust=False,
    )
    return {
        "information_coefficient": ic,
        "mean_return_by_date_and_quantile": means,
        "source_iid_standard_error_unreliable": source_iid_stderr,
        "standard_error_note": (
            "Source IID standard errors are exposed for traceability only; "
            "they are not reliable inference for dependent or overlapping observations."
        ),
    }
