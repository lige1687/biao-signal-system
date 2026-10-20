"""factor_lab 归因层单测：资金核对、受控决策差额、风险模型诚实 not_run。"""
from __future__ import annotations

import pandas as pd
import pytest

from lei_signal.research.factor_lab.attribution import explain_strategy
from lei_signal.research.factor_lab.contracts import IdentityFormatError


def make_protocol(**overrides):
    protocol = {
        "protocol_id": "test-protocol",
        "version": "0.0.1",
        "kind": "strategy_explanation",
        "data_mode": "synthetic",
        "synthetic": True,
        "timezone": "Asia/Shanghai",
        "evaluation_cutoff": "2030-01-01T15:00:00+08:00",
    }
    protocol.update(overrides)
    return protocol


def base_account() -> dict:
    """初始100；买1份@50费1→现金49；分红到账2→51；期末价55→权益106。"""
    return {
        "initial": 100.0,
        "equity": pd.DataFrame({
            "date": ["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08"],
            "cash": [100.0, 49.0, 51.0, 51.0],
            "receivable": [0.0, 0.0, 0.0, 0.0],
            "equity": [100.0, 99.0, 103.0, 106.0],
            "units_100001": [0.0, 1.0, 1.0, 1.0],
        }),
        "trades": pd.DataFrame({
            "date": ["2026-01-06"], "symbol": ["100001"], "side": ["buy"],
            "notional": [50.0], "fee": [1.0],
        }),
        "events": pd.DataFrame({
            "event_id": ["div-001", "div-001"], "date": ["2026-01-07", "2026-01-07"],
            "event": ["receivable", "cash_paid"], "amount": [2.0, 2.0],
        }),
        "actions": [{"event_id": "div-001", "symbol": "100001", "type": "cash_dividend",
                     "effective_date": "2026-01-07", "cash": 2.0}],
        "prices": pd.DataFrame({
            "date": ["2026-01-06", "2026-01-07", "2026-01-08"], "symbol": ["100001"] * 3,
            "close": [50.0, 52.0, 55.0],
        }),
    }


def variant_account() -> dict:
    """唯一动作差异：d3 以55卖出（卖费率1%→0.55）。期末权益105.45。"""
    account = base_account()
    account["equity"] = pd.DataFrame({
        "date": ["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08"],
        "cash": [100.0, 49.0, 51.0, 105.45],
        "receivable": [0.0, 0.0, 0.0, 0.0],
        "equity": [100.0, 99.0, 103.0, 105.45],
        "units_100001": [0.0, 1.0, 1.0, 0.0],
    })
    account["trades"] = pd.DataFrame({
        "date": ["2026-01-06", "2026-01-08"], "symbol": ["100001", "100001"],
        "side": ["buy", "sell"], "notional": [50.0, 55.0], "fee": [1.0, 0.55],
    })
    return account


class TestLayer1Capital:
    def test_synthetic_reconciliation_example(self):
        result = explain_strategy({"accounts": {"base": base_account()}},
                                  model_card=None,
                                  protocol=make_protocol())
        layer1 = result["layer1_capital"]["base"]
        assert layer1["status"] == "reconciled"
        assert layer1["reconciliation"]["passed"] is True
        assert layer1["reconciliation"]["ending_equity"] == pytest.approx(106.0)
        row = layer1["contributions"][0]
        assert row["symbol"] == "100001"
        assert row["net_contribution"] == pytest.approx(6.0)
        assert row["cash_dividends_paid"] == pytest.approx(2.0)
        assert row["ending_market_value"] == pytest.approx(55.0)
        assert row["gross_purchases"] == pytest.approx(51.0)

    def test_missing_holding_breaks_reconciliation(self):
        account = base_account()
        account["equity"] = account["equity"].drop(columns=["units_100001"])
        result = explain_strategy({"accounts": {"bad": account}}, model_card=None,
                                  protocol=make_protocol())
        layer1 = result["layer1_capital"]["bad"]
        # 缺期末持仓 → 期末市值归零 → 核对失败被如实暴露，不假装账平
        assert layer1["status"] == "reconciliation_failed"
        assert layer1["reconciliation"]["passed"] is False

    def test_receivable_unpaid_variant(self):
        account = base_account()
        account["equity"] = pd.DataFrame({
            "date": ["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08"],
            "cash": [100.0, 49.0, 49.0, 49.0],
            "receivable": [0.0, 0.0, 2.0, 2.0],
            "equity": [100.0, 99.0, 101.0, 106.0],
            "units_100001": [0.0, 1.0, 1.0, 1.0],
        })
        account["events"] = pd.DataFrame({
            "event_id": ["div-001"], "date": ["2026-01-07"], "event": ["receivable"],
            "amount": [2.0],
        })
        result = explain_strategy({"accounts": {"rec": account}}, model_card=None,
                                  protocol=make_protocol())
        layer1 = result["layer1_capital"]["rec"]
        assert layer1["status"] == "reconciled"
        assert layer1["contributions"][0]["ending_receivable"] == pytest.approx(2.0)
        assert layer1["contributions"][0]["net_contribution"] == pytest.approx(6.0)

    def test_no_trade_all_cash(self):
        account = {
            "initial": 100.0,
            "equity": pd.DataFrame({
                "date": ["2026-01-05", "2026-01-08"],
                "cash": [100.0, 100.0], "receivable": [0.0, 0.0],
                "equity": [100.0, 100.0], "units_100001": [0.0, 0.0],
            }),
            "trades": pd.DataFrame(columns=["date", "symbol", "side", "notional", "fee"]),
            "events": pd.DataFrame(columns=["event_id", "date", "event", "amount"]),
            "actions": [],
            "prices": pd.DataFrame({
                "date": ["2026-01-06"], "symbol": ["100001"], "close": [50.0]}),
        }
        result = explain_strategy({"accounts": {"cash": account}}, model_card=None,
                                  protocol=make_protocol())
        layer1 = result["layer1_capital"]["cash"]
        assert layer1["status"] == "reconciled"
        assert layer1["reconciliation"]["net_pnl" if False else "ending_equity"] == 100.0

    def test_unknown_event_id_rejected(self):
        account = base_account()
        account["events"] = pd.DataFrame({
            "event_id": ["div-999"], "date": ["2026-01-07"], "event": ["cash_paid"],
            "amount": [2.0],
        })
        with pytest.raises(ValueError, match="no action->symbol mapping"):
            explain_strategy({"accounts": {"bad": account}}, model_card=None,
                             protocol=make_protocol())

    def test_one_to_many_mapping_rejected(self):
        account = base_account()
        account["actions"] = [
            {"event_id": "div-001", "symbol": "100001", "type": "cash_dividend",
             "effective_date": "2026-01-07", "cash": 2.0},
            {"event_id": "div-001", "symbol": "Y", "type": "cash_dividend",
             "effective_date": "2026-01-07", "cash": 2.0},
        ]
        with pytest.raises(IdentityFormatError, match="duplicate action event_id"):
            explain_strategy({"accounts": {"bad": account}}, model_card=None,
                             protocol=make_protocol())

    def test_account_field_in_actions_rejected(self):
        account = base_account()
        account["actions"] = [{"event_id": "div-001", "symbol": "100001",
                               "type": "cash_dividend", "effective_date": "2026-01-07",
                               "cash": 2.0, "fee": 1.0}]
        with pytest.raises(IdentityFormatError, match="账户字段"):
            explain_strategy({"accounts": {"bad": account}}, model_card=None,
                             protocol=make_protocol())


class TestLayer2DecisionIncrement:
    """迁移到固定比较合同（R3）；语义由 TestComparisonContractR3 详测。"""

    def comparison_protocol(self):
        return make_protocol(comparison={
            "variant": "variant_exit_on_d3", "base": "base",
            "declared_action": "exit_on_d3_at_close",
            "pool_versions": {"base": "p1", "variant": "p1"},
            "entity_sets": {"base": ["100001"], "variant": ["100001"]},
            "period": {"start": "2026-01-05", "end": "2026-01-08"},
            "initial_cash": 100.0,
            "external_flows": {"base": [], "variant": []},
            "fee_schedule": {"base": {"buy": 0.02, "sell": 0.01},
                             "variant": {"buy": 0.02, "sell": 0.01}},
            "benchmark": {"base": "hold_cash_synthetic",
                          "variant": "hold_cash_synthetic"},
            "frozen_rules": {"base": "entry_fixed", "variant": "entry_fixed"},
            "input_identity": {"prices": "synthetic-prices-1"},
        })

    def test_controlled_difference_attributable(self):
        accounts = {"accounts": {"base": base_account(),
                                 "variant_exit_on_d3": variant_account()}}
        result = explain_strategy(accounts, model_card=None,
                                  protocol=self.comparison_protocol())
        layer2 = result["layer2_decision_increment"]
        assert layer2["status"] == "attributable_to_declared_action_only"
        assert layer2["differences"]["net_pnl"] == pytest.approx(-0.55, abs=1e-9)
        # 变体多付一笔卖出费0.55；净利差=卖出价55入账但损失持仓涨跌与费用
        assert layer2["differences"]["fees"] == pytest.approx(0.55, abs=1e-9)
        assert layer2["differences"]["trades"] == 1
        assert "不可相加" in layer2["note"]
        # 全部固定条件都已核对且相等，合成标识在案
        assert layer2["checks"]["external_flows_equal"] is True
        assert layer2["checks"]["benchmark_equal"] is True

    def test_initial_mismatch_not_attributable(self):
        accounts = {"accounts": {"base": base_account(),
                                 "variant_exit_on_d3": variant_account()}}
        accounts["accounts"]["variant_exit_on_d3"]["initial"] = 200.0
        result = explain_strategy(accounts, model_card=None,
                                  protocol=self.comparison_protocol())
        layer2 = result["layer2_decision_increment"]
        assert layer2["status"] == "not_attributable"
        codes = {m["check"] for m in layer2["mismatches"]}
        assert "initial_cash_matches_accounts" in codes

    def test_pool_mismatch_not_attributable(self):
        accounts = {"accounts": {"base": base_account(),
                                 "variant_exit_on_d3": variant_account()}}
        protocol = self.comparison_protocol()
        protocol["comparison"]["entity_sets"] = {"base": ["100001"],
                                                 "variant": ["100001", "Y"]}
        result = explain_strategy(accounts, model_card=None, protocol=protocol)
        layer2 = result["layer2_decision_increment"]
        assert layer2["status"] == "not_attributable"
        assert any(m["check"] == "pool_entities_equal"
                   for m in layer2["mismatches"])


class TestLayer3RiskModel:
    def test_model_card_none_is_legal_not_run(self):
        result = explain_strategy({"accounts": {"base": base_account()}},
                                  model_card=None, protocol=make_protocol())
        layer3 = result["layer3_risk_model"]
        assert layer3["status"] == "not_run"
        assert layer3["reason"] == "no_model_card_provided"
        assert "alpha" in layer3["note"]

    def test_breadth_level_cannot_be_return_factor(self):
        result = explain_strategy(
            {"accounts": {"base": base_account()}},
            model_card={
                "dependent_return": "mixed.asset.total_return@1.0.0",
                "factor_returns": ["breadth.csi300.b200.common@1.0.0"],
                "form": "linear",
                "frequency": "daily",
                "window": "252d",
                "risk_free": "cash.zero@1.0.0",
                "currency": "CNY",
                "missing_alignment": "drop",
                "estimation": "ols",
                "uncertainty": "none",
                "status": "draft",
            },
            protocol=make_protocol())
        layer3 = result["layer3_risk_model"]
        assert layer3["status"] == "not_run"
        assert "状态" in layer3["reason"]

    def test_cash_zero_note_present(self):
        result = explain_strategy(
            {"accounts": {"base": base_account()}},
            model_card={
                "dependent_return": "mixed.asset.total_return@1.0.0",
                "factor_returns": ["mixed.asset.total_return@1.0.0"],
                "form": "linear",
                "frequency": "daily",
                "window": "252d",
                "risk_free": "cash.zero@1.0.0",
                "currency": "CNY",
                "missing_alignment": "drop",
                "estimation": "ols",
                "uncertainty": "none",
                "status": "draft",
            },
            protocol=make_protocol())
        layer3 = result["layer3_risk_model"]
        assert layer3["status"] == "not_run"
        assert layer3["reason"] == "risk_model_regression_not_implemented_this_round"
        assert any("无风险" in note for note in layer3["notes"])

    def test_incomplete_model_card_rejected(self):
        with pytest.raises(IdentityFormatError, match="model_card missing"):
            explain_strategy({"accounts": {"base": base_account()}},
                             model_card={"dependent_return": "x"}, protocol=make_protocol())


class TestComparisonContractR3:
    """集中返修 R3：比较合同在protocol，未核对条件不得宣称only。"""

    def full_comparison(self, *, base_pool=None, variant_pool=None, **overrides):
        contract = {
            "variant": "variant_exit_on_d3", "base": "base",
            "declared_action": "exit_on_d3_at_close",
            "pool_versions": {"base": "synthetic-pool-1", "variant": "synthetic-pool-1"},
            "entity_sets": {"base": base_pool or ["100001"],
                            "variant": variant_pool or ["100001"]},
            "period": {"start": "2026-01-05", "end": "2026-01-08"},
            "initial_cash": 100.0,
            "external_flows": {"base": [], "variant": []},
            "fee_schedule": {"base": {"buy": 0.02, "sell": 0.01},
                             "variant": {"buy": 0.02, "sell": 0.01}},
            "benchmark": {"base": "hold_cash_synthetic", "variant": "hold_cash_synthetic"},
            "frozen_rules": {"base": "entry_fixed", "variant": "entry_fixed"},
            "input_identity": {"prices": "synthetic-prices-1"},
        }
        contract.update(overrides)
        return make_protocol(comparison=contract)

    def test_declared_pool_mismatch_not_attributable(self):
        # 主控反例：候选池 base=[100001,A] vs variant=[100001,B]
        accounts = {"accounts": {"base": base_account(),
                                 "variant_exit_on_d3": variant_account()}}
        result = explain_strategy(accounts, model_card=None, protocol=self.full_comparison(
            base_pool=["100001", "A"], variant_pool=["100001", "B"]))
        layer2 = result["layer2_decision_increment"]
        assert layer2["status"] != "attributable_to_declared_action_only"
        assert layer2["status"] == "not_attributable"
        assert any("pool" in m["check"] for m in layer2["mismatches"])

    def test_must_match_escape_key_rejected(self):
        accounts = {"accounts": {"base": base_account(),
                                 "variant_exit_on_d3": variant_account()}}
        protocol = self.full_comparison(must_match=["initial"])
        with pytest.raises(IdentityFormatError):
            explain_strategy(accounts, model_card=None, protocol=protocol)

    def test_missing_required_contract_field_rejected(self):
        accounts = {"accounts": {"base": base_account(),
                                 "variant_exit_on_d3": variant_account()}}
        protocol = self.full_comparison()
        del protocol["comparison"]["fee_schedule"]
        with pytest.raises(IdentityFormatError, match="fee_schedule"):
            explain_strategy(accounts, model_card=None, protocol=protocol)

    def test_unknown_condition_degrades_status_and_keeps_differences(self):
        accounts = {"accounts": {"base": base_account(),
                                 "variant_exit_on_d3": variant_account()}}
        result = explain_strategy(accounts, model_card=None, protocol=self.full_comparison(
            benchmark={"base": None, "variant": None}))
        layer2 = result["layer2_decision_increment"]
        assert layer2["status"] == "not_attributable_conditions_unknown"
        assert "differences" in layer2  # 算术差额保留展示
        assert layer2["differences"]["net_pnl"] == pytest.approx(-0.55, abs=1e-9)

    def test_fee_rule_mismatch_not_attributable(self):
        accounts = {"accounts": {"base": base_account(),
                                 "variant_exit_on_d3": variant_account()}}
        result = explain_strategy(accounts, model_card=None, protocol=self.full_comparison(
            fee_schedule={"base": {"buy": 0.02, "sell": 0.01},
                          "variant": {"buy": 0.02, "sell": 0.005}}))
        layer2 = result["layer2_decision_increment"]
        assert layer2["status"] == "not_attributable"
        assert any("fee" in m["check"] for m in layer2["mismatches"])

    def test_declared_fee_rule_contradicted_by_trades(self):
        accounts = {"accounts": {"base": base_account(),
                                 "variant_exit_on_d3": variant_account()}}
        # 声明卖费0.02，实际0.55/55=0.01 → 声明与成交不一致，不得归因
        result = explain_strategy(accounts, model_card=None, protocol=self.full_comparison(
            fee_schedule={"base": {"buy": 0.02, "sell": 0.01},
                          "variant": {"buy": 0.02, "sell": 0.02}}))
        layer2 = result["layer2_decision_increment"]
        assert layer2["status"] != "attributable_to_declared_action_only"

    def test_declared_period_differs_from_accounts(self):
        accounts = {"accounts": {"base": base_account(),
                                 "variant_exit_on_d3": variant_account()}}
        result = explain_strategy(accounts, model_card=None, protocol=self.full_comparison(
            period={"start": "2026-01-01", "end": "2026-01-08"}))
        layer2 = result["layer2_decision_increment"]
        assert layer2["status"] == "not_attributable"

    def test_positive_control_still_limited_attributable(self):
        accounts = {"accounts": {"base": base_account(),
                                 "variant_exit_on_d3": variant_account()}}
        result = explain_strategy(accounts, model_card=None,
                                  protocol=self.full_comparison())
        layer2 = result["layer2_decision_increment"]
        assert layer2["status"] == "attributable_to_declared_action_only"
        assert layer2["differences"]["net_pnl"] == pytest.approx(-0.55, abs=1e-9)
        assert "合成" in layer2["note"] or "synthetic" in layer2["note"].lower()


class TestModelCardValidationR3:
    """结构非法报错；合法但未实现保留not_run。"""

    def legal_card(self, **overrides):
        card = {
            "dependent_return": "mixed.asset.total_return@1.0.0",
            "factor_returns": ["mixed.asset.total_return@1.0.0"],
            "form": "linear", "frequency": "daily", "window": "252d",
            "risk_free": "cash.zero@1.0.0", "currency": "CNY",
            "missing_alignment": "drop", "estimation": "ols",
            "uncertainty": "none", "status": "draft",
        }
        card.update(overrides)
        return card

    def test_illegal_frequency_raises(self):
        with pytest.raises(IdentityFormatError, match="frequency"):
            explain_strategy({"accounts": {"base": base_account()}},
                             model_card=self.legal_card(frequency="每秒"),
                             protocol=make_protocol())

    def test_unresolvable_factor_reference_raises(self):
        with pytest.raises(IdentityFormatError, match="not resolvable"):
            explain_strategy({"accounts": {"base": base_account()}},
                             model_card=self.legal_card(factor_returns=["ghost.ref@9.9.9"]),
                             protocol=make_protocol())

    def test_non_string_window_raises(self):
        with pytest.raises(IdentityFormatError, match="window"):
            explain_strategy({"accounts": {"base": base_account()}},
                             model_card=self.legal_card(window=252),
                             protocol=make_protocol())

    def test_legal_card_still_not_run(self):
        result = explain_strategy({"accounts": {"base": base_account()}},
                                  model_card=self.legal_card(),
                                  protocol=make_protocol())
        layer3 = result["layer3_risk_model"]
        assert layer3["status"] == "not_run"
        assert layer3["reason"] == "risk_model_regression_not_implemented_this_round"
