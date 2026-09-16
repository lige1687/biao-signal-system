"""集中返修：冻结三份正式合成协议 v1.1.0（排他创建，新目录新版本）。

相对 v1.0.0 的合同增强（R2/R4）：
- code_identity：必需代码键全集哈希，运行前逐文件核对；
- registry / definition_cards_sha256：登记表与卡指纹冻结，计算前比对；
- data_declarations：合成数据的价格尺度/日历/时间/币种显式声明；
- segment_cutoffs：每段评价截止（带时区）且不晚于全局截止；
- required_checks + expectation_source：必需检查ID与独立期望来源冻结，
  删检查必须拒绝；容差只允许固定值。
期望数值仍全部来自 independent-expectations.json（独立算术，不 import 被测代码）。
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
ORIG = REPO / "docs/experiments/raw/factor-research-workbench-v1-2026-09-14"
INPUTS_REL = "../factor-research-workbench-v1-2026-09-14/synthetic_inputs"
EXPECT = json.loads((ORIG / "independent-expectations.json").read_text(encoding="utf-8"))

from lei_signal.research import definitions  # noqa: E402
from lei_signal.research.factor_lab.adapters import CANDIDATE_CARDS  # noqa: E402
from lei_signal.research.factor_lab.runner import (  # noqa: E402
    REQUIRED_CODE_KEYS,
    _canonical_sha256,
)


def sha(name: str) -> str:
    return hashlib.sha256((ORIG / "synthetic_inputs" / name).read_bytes()).hexdigest()


def spec(name: str, fmt: str) -> dict:
    return {"path": f"{INPUTS_REL}/{name}", "sha256": sha(name), "format": fmt}


def code_identity() -> dict:
    return {rel: hashlib.sha256((REPO / rel).read_bytes()).hexdigest()
            for rel in sorted(REQUIRED_CODE_KEYS)}


def registry_block() -> dict:
    registry = definitions.load_registry()
    return {"version": registry["version"],
            "canonical_sha256": _canonical_sha256(registry)}


def cards_block(refs: list[str]) -> dict:
    registry = definitions.load_registry()
    out = {}
    for reference in refs:
        card = (CANDIDATE_CARDS[reference] if reference.startswith("candidate:")
                else definitions.resolve(registry, reference))
        out[reference] = _canonical_sha256(card)
    return out


def expectation_source() -> dict:
    path = ORIG / "independent-expectations.json"
    return {"path": "../factor-research-workbench-v1-2026-09-14/independent-expectations.json",
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def base_protocol(protocol_id: str, kind: str, case: str, title: str,
                  refs: list[str]) -> dict:
    return {
        "protocol_id": protocol_id,
        "version": "1.1.1",
        "kind": kind,
        "data_mode": "synthetic",
        "synthetic": True,
        "timezone": "Asia/Shanghai",
        "evaluation_cutoff": "2030-01-01T15:00:00+08:00",
        "case": case,
        "title": title,
        "expectation_tolerance_abs": 1e-6,
        "registry": registry_block(),
        "code_identity": code_identity(),
        "definition_cards_sha256": cards_block(refs),
        "data_declarations": {
            "price_scale": "arbitrary_positive_units_synthetic",
            "calendar": "pandas_bdate_range_synthetic_not_exchange_calendar",
            "timezone": "Asia/Shanghai",
            "currency": "synthetic_units_not_cny",
        },
        "required_checks": [],
        "expectation_source": expectation_source(),
        "attempt_history": [
            {"attempt": "repair-fixture-reuse", "outcome": "success",
             "reason": "复用首轮 synthetic_inputs（哈希冻结）；本轮未改夹具"},
            {"attempt": "protocol-v1.1.0-freeze", "outcome": "abandoned",
             "reason": "正式批次后发现manifest的outputs哈希在写盘前构建恒为空；修复_write_manifest后代码哈希变化，升版重冻结（已交付run-01保留原样，新正式批次待主控授权）"},
            {"attempt": "protocol-v1.1.1-freeze", "outcome": "success",
             "reason": "代码定稿（outputs现算哈希）后重冻结；期望仍取自独立算术文件"},
        ],
    }


def numerical_protocol() -> dict:
    n = EXPECT["numerical"]
    refs = ["mixed.momentum.raw@1.0.0", "mixed.rv20@1.0.0",
            "trend.distance50@1.0.0", "trend.distance200@1.0.0"]
    protocol = base_protocol(
        "factor-lab-demo-1-numerical", "predictive_diagnostic", "numerical",
        "①多产品数值与排名研究（返修版：时间资格实际消费统计）", refs)
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
        "segment_cutoffs": {
            "dev": "2017-12-29T15:00:00+08:00",
            "validation": "2018-01-10T15:00:00+08:00",
            "holdout": "2018-02-23T15:00:00+08:00",
        },
    }
    protocol["trials"] = [
        {"trial_id": "t-001", "definition_reference": "mixed.momentum.raw@1.0.0",
         "parameters": {}, "pool": "synthetic-3-entity",
         "target": "protocol:t22-price-change@1.0.0",
         "input_identity": {"prices": "numerical_prices_3.csv"},
         "split_id": "s1", "outcome": "abandoned",
         "selection_basis": "首轮夹具v1放弃（符号冲突），非结果挑选",
         "seen_segments": ["dev"], "run_version": "fixture-v1"},
        {"trial_id": "t-002", "definition_reference": "mixed.momentum.raw@1.0.0",
         "parameters": {}, "pool": "synthetic-3-entity",
         "target": "protocol:t22-price-change@1.0.0",
         "input_identity": {"prices": "numerical_prices_3.csv"},
         "split_id": "s1", "outcome": "success",
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
        "first_valid_probe": {"calculation": "mom3", "entity": "alpha",
                              "input": "prices_3"},
        "value_probes": {
            "momentum_alpha_row252": {"calculation": "mom3", "entity": "alpha"},
            "rv20_alpha_row252": {"calculation": "rv3", "entity": "alpha"},
            "distance50_alpha_row252": {"calculation": "d50_3", "entity": "alpha"},
            "distance200_alpha_row252": {"calculation": "d200_3", "entity": "alpha"},
        },
        "audit_pairs_from": "mom3",
        "audit_targets_of": "prices_3",
    }
    expectations = {
        "momentum_first_valid_row": 253,
        "momentum_alpha_row252": n["momentum_alpha_at_row252"],
        "rv20_alpha_row252": n["rv20_alpha_at_row252"],
        "distance50_alpha_row252": n["distance50_alpha_at_row252"],
        "distance200_alpha_row252": n["distance200_alpha_at_row252"],
        "ic_mean_3": 1.0,
        "n_periods_3": 300,
        "n_periods_with_value_3": 26,
        "min_n_3": 0,
        "min_n_with_value_3": 3,
        "ic_mean_5": 1.0,
        "n_periods_with_value_5": 26,
        "min_n_5": 0,
        "min_n_with_value_5": 4,
        "max_n_5": 5,
        "scale_invariance_max_diff": 0.0,
        "append_invariance_max_diff": 0.0,
        "dev_label_crossing_n": 24,
        "validation_label_crossing_n": 24,
        "dev_n_usable_clean": 0,
        "validation_n_usable_clean": 0,
        "holdout_n_usable_clean": 30,
        "trial_history_status": "provided",
    }
    protocol["expectations"] = expectations
    protocol["required_checks"] = sorted(expectations)
    protocol["expectation_basis"] = (
        "全部期望取自 independent-expectations.json（derive_expectations.py 独立算术，"
        "不 import lei_signal）。返修版语义：全部300个观察日都保留（无目标日n=0）；"
        "26个有目标日IC=1；标签窗21天 → dev/validation各8观察日×3实体=24对跨段，"
        "跨段/未成熟样本从干净集剔除 → dev/validation clean=0，holdout 30对全部成熟 "
        "（holdout段截止=面板末日2018-02-23T15:00，最晚标签结束于同日）→ clean=30。"
    )
    return protocol


def state_protocol() -> dict:
    s = EXPECT["state"]
    bars_dates = pd.bdate_range("2019-01-01", periods=65)
    dm_a = s["dm_a"]
    dm_b = s["dm_b"]
    refs = ["candidate:lei.dual_ma.bull_state@draft-1",
            "breadth.csi300.b50.common@1.0.0", "breadth.csi300.b200.common@1.0.0"]
    protocol = base_protocol(
        "factor-lab-demo-2-state", "state_diagnostic", "state",
        "②双均线候选/共同分母宽度+状态诊断（返修版：检查点按对象ID命名）", refs)
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
    b = s["breadth"]
    expectations = {
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
        "b50_first_valid_date": b["first_valid_date"],
        "b50_valid_days": 60,
        "b50_coverage_missing_days": 1,
        "b50_at_first_valid": b["b50_at_first_valid"],
        "b50_day_before_change": b["b50_day_before_change"],
        "b50_at_change": b["b50_after_change"],
        "b200_first_valid_date": b["first_valid_date"],
        "b200_valid_days": 60,
        "b200_coverage_missing_days": 1,
        "b200_at_first_valid": b["b200_at_first_valid"],
        "b200_at_change": b["b200_after_change"],
        "constant_breadth_ic_status": "not_applicable",
        "so_dm_a_true_n": 8,
        "so_dm_a_false_n": 15,
        "so_dm_b_true_n": 0,
        "so_dm_b_false_n": 23,
        "ts_m1_status": "descriptive_only",
        "ts_m1_n": 39,
    }
    protocol["expectations"] = expectations
    protocol["required_checks"] = sorted(expectations)
    protocol["expectation_basis"] = (
        "状态计数取自 independent-expectations.json（独立EMA/SMA/颜色/状态算术）；"
        "宽度检查点按对象ID前缀b50_/b200_命名（B200不得覆盖B50）；成员缺1天报价后，"
        "SMA按有效收盘滚动（卡语义）→ 只有缺报价当日coverage不足（1天）；"
        "状态结果分组可用样本按t<=42手算：dm_a真=8、假=15、dm_b假=23；"
        "宽度跨日期诊断可用样本=199..249∩t<=237=39。"
    )
    return protocol


def attribution_protocol() -> dict:
    a = EXPECT["attribution"]
    protocol = base_protocol(
        "factor-lab-demo-3-attribution", "strategy_explanation", "attribution",
        "③策略三层归因入口（返修版：固定比较合同，未知条件降级）", [])
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
        "pool_versions": {"base": "synthetic-pool-100001", "variant": "synthetic-pool-100001"},
        "entity_sets": {"base": ["100001"], "variant": ["100001"]},
        "period": {"start": "2026-01-05", "end": "2026-01-08"},
        "initial_cash": 100.0,
        "external_flows": {"base": [], "variant": []},
        "fee_schedule": {"base": {"buy": 0.02, "sell": 0.01},
                         "variant": {"buy": 0.02, "sell": 0.01}},
        "benchmark": {"base": "hold_cash_synthetic", "variant": "hold_cash_synthetic"},
        "frozen_rules": {"base": "entry_fixed_synthetic", "variant": "entry_fixed_synthetic"},
        "input_identity": {"prices": "attribution_prices_base.csv@v1"},
    }
    protocol["model_card"] = None
    expectations = {
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
    protocol["expectations"] = expectations
    protocol["required_checks"] = sorted(expectations)
    protocol["expectation_basis"] = (
        "独立手算：100元本金，买1份@50费1→现金49，分红2到账→51，期末价55→"
        "总资产106、净损益6、产品净贡献6；应收未付变体权益同为106（含应收2）；"
        "变体d3以55卖出（费率1%→0.55）→净损益5.45，差额-0.55只归给该卖出动作"
        "（全部合同条件核对相等后才允许only，且仅限合成材料一致）。"
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
        protocol["required_checks"] = sorted(protocol["expectations"])
        path = HERE / name
        if path.exists():
            print(f"refusing to overwrite {path}")
            return 3
        path.write_text(json.dumps(protocol, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        print(f"frozen {path.name} v{protocol['version']} "
              f"inputs={len(protocol['inputs'])} "
              f"expectations={len(protocol['expectations'])} "
              f"code_keys={len(protocol['code_identity'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
