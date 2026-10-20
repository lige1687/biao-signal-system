"""冻结三份正式合成协议（v1.0.0，排他创建）。

期望值来源：independent-expectations.json（由 derive_expectations.py 生成，
该脚本不 import lei_signal，独立于被测代码）。本脚本只组装协议并计算输入
哈希，不改任何期望数值。协议一经冻结不得修改；重跑需另立版本。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
INPUTS = HERE / "synthetic_inputs"
EXPECT = json.loads((HERE / "independent-expectations.json").read_text(encoding="utf-8"))


def sha(name: str) -> str:
    return hashlib.sha256((INPUTS / name).read_bytes()).hexdigest()


def spec(name: str, fmt: str) -> dict:
    return {"path": f"synthetic_inputs/{name}", "sha256": sha(name), "format": fmt}


def base_protocol(protocol_id: str, kind: str, case: str, title: str) -> dict:
    return {
        "protocol_id": protocol_id,
        "version": "1.0.0",
        "kind": kind,
        "data_mode": "synthetic",
        "synthetic": True,
        "timezone": "Asia/Shanghai",
        "evaluation_cutoff": "2030-01-01T15:00:00+08:00",
        "case": case,
        "title": title,
        "expectation_tolerance_abs": 1e-6,
        "attempt_history": [
            {"attempt": "fixture-v1", "outcome": "abandoned",
             "reason": "合成产品代码 'X' 与复用 build_marks 的6位代码 zfill 假设冲突；"
                       "协议冻结前改用 '100001' 重建夹具（未运行任何正式案例）"},
            {"attempt": "fixture-v2", "outcome": "success",
             "reason": "当前 synthetic_inputs 内容；期望全部来自独立手算脚本"},
        ],
    }


def numerical_protocol() -> dict:
    n = EXPECT["numerical"]
    protocol = base_protocol(
        "factor-lab-demo-1-numerical", "predictive_diagnostic", "numerical",
        "①多产品数值与排名研究：同一API适配3/5实体、手算IC、时间切分")
    protocol["inputs"] = {
        "prices_3": spec("numerical_prices_3.csv", "wide_prices"),
        "prices_5": spec("numerical_prices_5.csv", "wide_prices"),
    }
    protocol["calculations"] = [
        {"id": "mom3", "reference": "mixed.momentum.raw@1.0.0", "input": "prices_3",
         "evaluate_with_targets": True},
        {"id": "mom5", "reference": "mixed.momentum.raw@1.0.0", "input": "prices_5",
         "evaluate_with_targets": True},
        {"id": "rv3", "reference": "mixed.rv20@1.0.0", "input": "prices_3"},
        {"id": "d50_3", "reference": "trend.distance50@1.0.0", "input": "prices_3"},
        {"id": "d200_3", "reference": "trend.distance200@1.0.0", "input": "prices_3"},
    ]
    protocol["targets"] = {
        "source": "prices_3", "entry_offset": 1, "exit_offset": 22,
        "observations": {"start": n["split_dates"]["dev_start"],
                         "end": n["split_dates"]["hold_end"]},
        "note": "固定 t+1→t+22 经济价格变化；是测量目标，不是可成交开盘或完整账户收益",
    }
    protocol["diagnostics"] = {"type": "cross_section_ic", "min_pairs": 3,
                               "quantiles": {"q": 2}}
    protocol["validation"] = {
        "split": {
            "dev": [n["split_dates"]["dev_start"], n["split_dates"]["dev_end"]],
            "validation": [n["split_dates"]["val_start"], n["split_dates"]["val_end"]],
            "holdout": [n["split_dates"]["hold_start"], n["split_dates"]["hold_end"]],
        },
        "seen": {"dev": True, "validation": True, "holdout": False},
        "preprocessing": "none",
    }
    protocol["trials"] = [
        {"trial_id": "t-001", "definition_reference": "mixed.momentum.raw@1.0.0",
         "parameters": {}, "split_id": "s1", "outcome": "abandoned",
         "selection_basis": "夹具v1放弃（符号冲突），非结果挑选",
         "seen_segments": ["dev"], "run_version": "fixture-v1"},
        {"trial_id": "t-002", "definition_reference": "mixed.momentum.raw@1.0.0",
         "parameters": {}, "split_id": "s1", "outcome": "success",
         "selection_basis": "预注册合成演示；无参数挑选", "seen_segments": ["dev"],
         "run_version": "fixture-v2"},
    ]
    protocol["checks"] = {
        "price_scale_invariance": {"input": "prices_3",
                                   "reference": "mixed.momentum.raw@1.0.0",
                                   "factor": 2.0},
        "append_future_invariance": {"input": "prices_3",
                                     "reference": "mixed.rv20@1.0.0",
                                     "keep_rows": 280},
    }
    protocol["expectations_probe"] = {
        "row252_date": n["row252_date"],
        "primary_id": "mom3",
        "secondary_id": "mom5",
        "first_valid_probe": {"calculation": "mom3", "entity": "alpha"},
        "value_probes": {
            "momentum_alpha_row252": {"calculation": "mom3", "entity": "alpha"},
            "rv20_alpha_row252": {"calculation": "rv3", "entity": "alpha"},
            "distance50_alpha_row252": {"calculation": "d50_3", "entity": "alpha"},
            "distance200_alpha_row252": {"calculation": "d200_3", "entity": "alpha"},
        },
        "audit_pairs_from": "mom3",
        "audit_targets_of": "prices_3",
    }
    protocol["expectations"] = {
        "momentum_first_valid_row": 253,
        "momentum_alpha_row252": n["momentum_alpha_at_row252"],
        "rv20_alpha_row252": n["rv20_alpha_at_row252"],
        "distance50_alpha_row252": n["distance50_alpha_at_row252"],
        "distance200_alpha_row252": n["distance200_alpha_at_row252"],
        "ic_mean_3": 1.0,
        "n_periods_3": len(n["ic_periods_3"]),
        "min_n_3": 3,
        "ic_mean_5": 1.0,
        "min_n_5": 4,
        "max_n_5": 5,
        "scale_invariance_max_diff": 0.0,
        "append_invariance_max_diff": 0.0,
        "dev_label_crossing_n": 24,
        "validation_label_crossing_n": 24,
        "trial_history_status": "provided",
    }
    protocol["expectation_basis"] = (
        "全部期望取自 independent-expectations.json（derive_expectations.py 独立算术，"
        "不 import lei_signal）：等比增长路径的动量/目标排序完全一致 → 每期IC=1；"
        "epsilon缺5天 → 5实体某些期n=4；标签窗21天 → dev/validation各8个观察日"
        "×3实体=24个样本对跨段（审计按样本对计数）。"
    )
    return protocol


def state_protocol() -> dict:
    s = EXPECT["state"]
    bars_dates = pd.bdate_range("2019-01-01", periods=65)
    dm_a = s["dm_a"]
    dm_b = s["dm_b"]
    protocol = base_protocol(
        "factor-lab-demo-2-state", "state_diagnostic", "state",
        "②双均线候选/共同分母宽度+状态诊断：常数宽度横向IC不适用")
    protocol["inputs"] = {
        "bars_dm_a": spec("state_bars_dm_a.csv", "bars"),
        "bars_dm_b": spec("state_bars_dm_b.csv", "bars"),
        "state_breadth_close": spec("state_breadth_close.csv", "wide_prices"),
        "state_membership": spec("state_membership.json", "membership"),
    }
    protocol["state_candidate"] = {
        "reference": "candidate:lei.dual_ma.bull_state@draft-1",
        "note": "源代码绑定候选，不冒充已登记因子",
    }
    protocol["breadth"] = {
        "close": "state_breadth_close", "membership": "state_membership",
        "references": {
            "b50": "breadth.csi300.b50.common@1.0.0",
            "b200": "breadth.csi300.b200.common@1.0.0",
        },
        "note": "合成成员链，不得称真实沪深300证据",
    }
    protocol["diagnostics"] = {"type": "state_outcomes"}
    protocol["diagnostic_requests"] = {
        "constant_breadth_ic": {"batch": "b50",
                                "diagnostics": {"type": "cross_section_ic"}},
        "state_outcomes": {"batch": "dm",
                           "diagnostics": {"type": "state_outcomes"}},
        "time_series_state": {"batch": "b200",
                              "diagnostics": {"type": "time_series_state",
                                              "target_entities": ["m1"]}},
    }
    protocol["extra_card_references"] = list(protocol["breadth"]["references"].values())
    protocol["expectations_probe"] = {
        "state_rows": {
            "dm_a": {
                "dm_a_state_at_row21": [str(bars_dates[20].date()), True],
                "dm_a_state_at_row25": [str(bars_dates[24].date()), True],
                "dm_a_state_at_last_row": [str(bars_dates[64].date()), True],
            },
            "dm_b": {
                "dm_b_state_at_last_row": [str(bars_dates[64].date()), True],
            },
        },
        "breadth": {"change_date": s["breadth"]["change_date"],
                    "day_before_date": s["breadth_day_before_change_date"]},
        "breadth_close_input": "state_breadth_close",
    }
    protocol["expectations"] = {
        "dm_a_not_ready_rows": dm_a["not_ready_rows"],
        "dm_a_state_true_rows": dm_a["state_true_rows"],
        "dm_a_state_false_rows": dm_a["state_false_rows"],
        "dm_a_state_at_row21": 0,
        "dm_a_state_at_row25": 0,
        "dm_a_state_at_last_row": 1,
        "dm_b_not_ready_rows": dm_b["not_ready_rows"],
        "dm_b_state_true_rows": dm_b["state_true_rows"],
        "dm_b_state_false_rows": dm_b["state_false_rows"],
        "dm_b_state_at_last_row": 0,
        "breadth_first_valid_date": s["breadth"]["first_valid_date"],
        "breadth_valid_days": s["breadth"]["n_valid_days"],
        "breadth_coverage_missing_days": len(s["breadth"]["missing_coverage_days"]),
        "breadth_b50_at_first_valid": s["breadth"]["b50_at_first_valid"],
        "breadth_b50_day_before_change": s["breadth"]["b50_day_before_change"],
        "breadth_b50_at_change": s["breadth"]["b50_after_change"],
        "constant_breadth_ic_status": "not_applicable",
        "so_dm_a_true_n": 8,
        "so_dm_a_false_n": 15,
        "so_dm_b_true_n": 0,
        "so_dm_b_false_n": 23,
        "ts_m1_status": "descriptive_only",
        "ts_m1_n": 39,
    }
    protocol["expectation_basis"] = (
        "状态计数取自 independent-expectations.json（独立EMA/SMA/颜色/状态算术）；"
        "状态结果分组的可用样本按'观察日t需满足t+22在65根内(t<=42)'手算：dm_a真=35..42共8、"
        "假=20..34共15、dm_b假=20..42共23；宽度跨日期诊断可用样本=合格日199..249∩t<=237=39。"
    )
    return protocol


def attribution_protocol() -> dict:
    a = EXPECT["attribution"]
    protocol = base_protocol(
        "factor-lab-demo-3-attribution", "strategy_explanation", "attribution",
        "③策略三层归因入口：6元资金对账+受控差额比较+风险模型未运行说明")
    protocol["inputs"] = {
        "equity_base": spec("attribution_equity_base.csv", "table"),
        "trades_base": spec("attribution_trades_base.csv", "table"),
        "events_base": spec("attribution_events_base.csv", "table"),
        "actions_base": spec("attribution_actions_base.json", "actions"),
        "prices_base": spec("attribution_prices_base.csv", "table"),
        "equity_variant": spec("attribution_equity_variant.csv", "table"),
        "trades_variant": spec("attribution_trades_variant.csv", "table"),
        "equity_receivable": spec("attribution_equity_receivable.csv", "table"),
        "events_receivable": spec("attribution_events_receivable.csv", "table"),
        "actions_receivable": spec("attribution_actions_receivable.json", "actions"),
    }
    protocol["accounts"] = {
        "base": {"initial": 100.0, "equity": "equity_base", "trades": "trades_base",
                 "events": "events_base", "actions": "actions_base",
                 "prices": "prices_base"},
        "variant_exit_on_d3": {"initial": 100.0, "equity": "equity_variant",
                               "trades": "trades_variant", "events": "events_base",
                               "actions": "actions_base", "prices": "prices_base"},
        "receivable": {"initial": 100.0, "equity": "equity_receivable",
                       "trades": "trades_base", "events": "events_receivable",
                       "actions": "actions_receivable", "prices": "prices_base"},
    }
    protocol["comparison"] = {
        "variant": "variant_exit_on_d3", "base": "base",
        "declared_action": "exit_on_d3_at_close",
        "must_match": ["initial", "pool", "period", "fee_schedule",
                       "external_deposits", "benchmark", "frozen_rules"],
    }
    protocol["model_card"] = None
    protocol["expectations"] = {
        "base_status": "reconciled",
        "base_net_contribution": a["base"]["contribution_X"],
        "base_reconcile_error": 0.0,
        "receivable_status": "reconciled",
        "receivable_net_contribution": a["receivable"]["contribution_X"],
        "variant_exit_on_d3_status": "reconciled",
        "variant_exit_on_d3_net_contribution": a["variant_exit_on_d3"]["contribution_X"],
        "l2_status": "attributable_to_declared_action_only",
        "l2_net_pnl_diff": a["variant_exit_on_d3"]["net_pnl_difference_vs_base"],
        "l3_status": "not_run",
        "l3_reason": "no_model_card_provided",
    }
    protocol["expectation_basis"] = (
        "独立手算：100元本金，买1份@50费1→现金49，分红2到账→51，期末价55→"
        "总资产106、净损益6、产品净贡献6；应收未付变体权益同为106（含应收2）；"
        "变体d3以55卖出（费率1%→0.55）→净损益5.45，差额-0.55只归给该卖出动作。"
        "层3无模型卡是合法not_run。"
    )
    return protocol


def main() -> int:
    protocols = [
        ("protocol-1-numerical.json", numerical_protocol()),
        ("protocol-2-state.json", state_protocol()),
        ("protocol-3-attribution.json", attribution_protocol()),
    ]
    for name, protocol in protocols:
        path = HERE / name
        if path.exists():
            print(f"refusing to overwrite {path}")
            return 3
        path.write_text(json.dumps(protocol, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        print(f"frozen {path.name} inputs={len(protocol['inputs'])} "
              f"expectations={len(protocol['expectations'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
