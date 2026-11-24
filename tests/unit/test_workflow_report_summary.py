"""Only the T03 report's saved-number presentation is under test."""
from __future__ import annotations

import importlib.util
import hashlib
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[2] / "src/lei_signal/research/workflow.py"
spec = importlib.util.spec_from_file_location("isolated_report_workflow", WORKFLOW)
workflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow)


def _contract(kind="double_ma_order_information"):
    return {
        "feature": {"kind": kind},
        "data": {"mode": "synthetic"},
        "publication": {"conclusion": "insufficient"},
        "question": {"question_id": "T03-display", "added_information": "均线排列", "period": ["2025-01-01", "2025-12-31"]},
        "universe": {"assets": ["ETF-A"]},
        "controller_review": {"reason": "synthetic display check"},
    }


def _proof():
    return {"coverage": {"actual_assets": ["ETF-A"], "evaluation_rows": 10,
                         "evaluation_dates": 10, "partial": False}, "warnings": []}


def _result():
    return {
        "performance": [
            {"model": model, "metric": "RMSE", "value": value, "unit": "percentage_point",
             "rows": 10, "dates": 10, "assets": 1}
            for model, value in (("B0", 3.7), ("B1", 4.0), ("B2", 3.99))
        ],
        "increments": [], "descriptions": {}, "warnings": [],
        "primary_rmse": {"absolute_error_improvement": 0.01, "lo": -0.05, "hi": 0.06},
        "primary_rmse_block60": {"lo": -0.08, "hi": 0.09},
    }


def test_t03_primary_display_precedes_secondary_table_and_names_strong_simple_baseline():
    report = workflow.render_report(_contract(), _proof(), _result())
    assert report.index("## T03 主比较") < report.index("## 预测表现")
    assert "| B0 简单平均 | 3.7000 |" in report
    assert "| B1 已有信息 | 4.0000 |" in report
    assert "| B2 加入排列 | 3.9900 |" in report
    assert "B1减B2：+0.0100 个百分点" in report
    assert "-0.0500 至 +0.0600" in report
    assert "-0.0800 至 +0.0900" in report
    assert "B2相对B0：多错0.2900 个百分点" in report
    assert "B0比较区间未提供" in report
    assert "没有验证买卖动作或完整账户的资金收益" in report


def test_t03_sign_and_missing_fields_are_explicit():
    result = _result()
    result["performance"] = [p for p in result["performance"] if p["model"] != "B0"]
    result["primary_rmse"] = {"absolute_error_improvement": -0.04, "lo": None, "hi": None}
    result.pop("primary_rmse_block60")
    report = workflow.render_report(_contract(), _proof(), result)
    assert "B1减B2：-0.0400 个百分点" in report
    assert "按连续20日共同重取的范围：未提供" in report
    assert "按连续60日共同重取的范围：未提供" in report
    assert "B2相对B0的误差差额：未提供；B0比较区间未提供" in report


def test_non_t03_report_keeps_original_order_and_no_primary_summary():
    report = workflow.render_report(_contract("other_information"), _proof(), _result())
    assert "## T03 主比较" not in report
    assert report.index("## 预测表现") < report.index("## 相对已有信息的增量")
    # Golden output of the pre-change renderer for these exact local fixtures.
    # Source workflow.py SHA-256: 967d92adc77a18c42f16fda27c80eb5a136eadd72e4918515302003216a43cb6.
    assert hashlib.sha256(report.encode()).hexdigest() == "9df656b402e33a1e3a1c6a2f7dd914c792010709ee48167626f34e316cf65d1f"


def test_saved_t03_result_renders_existing_primary_values_without_recalculation():
    # Minimal fixed fields from sealed T03 core-01/result.json (SHA-256:
    # c3e4e88aa41b341e3e468678148c1d126588f1dece4367f0b65c860501c3c6a7).
    # Original contract/preflight/result were separately read and hashed in render-fix-receipt.json;
    # normal unit tests do not require the historical archive to be mounted.
    result = _result()
    for row, value in zip(result["performance"], (3.7092705129115178, 4.0148768345144425,
                                                    4.011620250600831)):
        row["value"] = value
    result["primary_rmse"] = {
        "absolute_error_improvement": 0.0032565839136111663,
        "lo": -0.04851697891531781, "hi": 0.05895800888331882,
    }
    result["primary_rmse_block60"] = {"lo": -0.07227060354273926, "hi": 0.08221086232861101}
    report = workflow.render_report(_contract(), _proof(), result)
    assert report.index("## T03 主比较") < report.index("## 预测表现")
    assert "| B0 简单平均 | 3.7093 |" in report
    assert "| B1 已有信息 | 4.0149 |" in report
    assert "| B2 加入排列 | 4.0116 |" in report
    assert "B1减B2：+0.0033 个百分点" in report
    assert "-0.0485 至 +0.0590" in report
    assert "-0.0723 至 +0.0822" in report
    assert "B2相对B0：多错0.3023 个百分点" in report
