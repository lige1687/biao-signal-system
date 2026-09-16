"""冻结终版三份合成协议 v1.2.0（排他创建；S2 收口）。

关键变化（相对 v1.1.x）：
- 必查集合不再由协议声明：``required_checks`` 字段被 runner 拒绝；
  唯一权威是 independent-expectations-v2.json 的 ``protocol_expectations[case]``
  （独立算术脚本产出，哈希冻结于协议 expectation_source）；
- runner 对协议 ``expectations`` 与文件段做值级完全核对（缺项/多项/改值即拒）。
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
EXPECT_V2 = json.loads((HERE / "independent-expectations-v2.json").read_text(encoding="utf-8"))

from lei_signal.research import definitions  # noqa: E402
from lei_signal.research.factor_lab.adapters import CANDIDATE_CARDS  # noqa: E402
from lei_signal.research.factor_lab.runner import (  # noqa: E402
    REQUIRED_CODE_KEYS,
    _canonical_sha256,
)


def sha_inputs(name: str) -> str:
    return hashlib.sha256((ORIG / "synthetic_inputs" / name).read_bytes()).hexdigest()


def spec(name: str, fmt: str) -> dict:
    return {"path": f"{INPUTS_REL}/{name}", "sha256": sha_inputs(name), "format": fmt}


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
    path = HERE / "independent-expectations-v2.json"
    return {"path": "independent-expectations-v2.json",
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def base_protocol(protocol_id: str, kind: str, case: str, title: str,
                  refs: list[str]) -> dict:
    expectations = dict(EXPECT_V2["protocol_expectations"][case])
    return {
        "protocol_id": protocol_id,
        "version": "1.2.0",
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
        "expectation_source": expectation_source(),
        "expectations": expectations,
        "expectation_basis": (
            "必查集合与期望值完全来自 independent-expectations-v2.json 的"
            "protocol_expectations 段（独立算术脚本产出，哈希冻结）；"
            "协议不得声明或裁剪 required_checks（runner 拒绝该字段）"
        ),
        "attempt_history": [
            {"attempt": "closeout-protocol-v1.2.0", "outcome": "success",
             "reason": "S2收口：必查集合改由独立期望产物权威化；"
                       "v1.1.1协议保留为上一版冻结历史"},
        ],
    }


def numerical_protocol() -> dict:
    refs = ["mixed.momentum.raw@1.0.0", "mixed.rv20@1.0.0",
            "trend.distance50@1.0.0", "trend.distance200@1.0.0"]
    protocol = base_protocol(
        "factor-lab-demo-1-numerical", "predictive_diagnostic", "numerical",
        "①多产品数值与排名研究（终版：必查集合来自独立期望产物）", refs)
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
        "observations": {"start": "2017-12-20", "end": "2018-01-24"},
        "note": "固定 t+1→t+22 经济价格变化；是测量目标，不是可成交开盘或完整账户收益",
    }
    protocol["diagnostics"] = {"type": "cross_section_ic", "min_pairs": 3,
                               "quantiles": {"q": 2}}
    protocol["validation"] = {
        "split": {
            "dev": ["2017-12-20", "2017-12-29"],
            "validation": ["2018-01-01", "2018-01-10"],
            "holdout": ["2018-01-11", "2018-01-24"],
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
        "row252_date": "2017-12-20",
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
    return protocol


def state_protocol() -> dict:
    refs = ["candidate:lei.dual_ma.bull_state@draft-1",
            "breadth.csi300.b50.common@1.0.0", "breadth.csi300.b200.common@1.0.0"]
    protocol = base_protocol(
        "factor-lab-demo-2-state", "state_diagnostic", "state",
        "②双均线候选/共同分母宽度+状态诊断（终版）", refs)
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
    bars_dates = pd.bdate_range("2019-01-01", periods=65)
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
        "breadth": {"change_date": "2018-11-05", "day_before_date": "2018-11-02"},
        "breadth_close_input": "state_breadth_close",
    }
    return protocol


def attribution_protocol() -> dict:
    protocol = base_protocol(
        "factor-lab-demo-3-attribution", "strategy_explanation", "attribution",
        "③策略三层归因入口（终版：固定比较合同+分侧输入身份）", [])
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
        "pool_versions": {"base": "synthetic-pool-100001",
                          "variant": "synthetic-pool-100001"},
        "entity_sets": {"base": ["100001"], "variant": ["100001"]},
        "period": {"start": "2026-01-05", "end": "2026-01-08"},
        "initial_cash": 100.0,
        "external_flows": {"base": [], "variant": []},
        "fee_schedule": {"base": {"buy": 0.02, "sell": 0.01},
                         "variant": {"buy": 0.02, "sell": 0.01}},
        "benchmark": {"base": "hold_cash_synthetic", "variant": "hold_cash_synthetic"},
        "frozen_rules": {"base": "entry_fixed_synthetic",
                         "variant": "entry_fixed_synthetic"},
        "input_identity": {"base": {"prices": "attribution_prices_base.csv@v1"},
                           "variant": {"prices": "attribution_prices_base.csv@v1"}},
    }
    protocol["model_card"] = None
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
        print(f"frozen {path.name} v{protocol['version']} "
              f"expectations={len(protocol['expectations'])} "
              f"code_keys={len(protocol['code_identity'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
