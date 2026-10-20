"""策略三层归因入口：资金贡献、决策增量、风险/因子解释。

三层不能相加成伪精确总账：
- 层1 资金贡献：复用 ``factor_diagnostics.capital_contributions/reconcile``，
  从实际成交、公司行动事件与名义市值重建；events 必须经 event_id 映射到
  独立的公司行动资料，账户字段混入 actions 即拒绝。
- 层2 决策增量：只消费两份完整账户结果与受控协议；结构条件不满足时只报
  "不可归给该动作"。复用 ``compare_accounts`` 输出路径摘要；各维度差额是
  描述，不相加成资金贡献。
- 层3 风险/因子解释：本轮只做模型卡与输入资格检查；模型卡缺失或不适配
  一律 not_run 并给原因，不产出 alpha 数字。model_card=None 是合法状态。
"""
from __future__ import annotations

import pandas as pd

from lei_signal.research import definitions
from lei_signal.research.factor_diagnostics import (
    RECONCILE_TOLERANCE,
    capital_contributions,
    compare_accounts,
    reconcile,
)
from lei_signal.research.factor_lab.contracts import (
    IdentityFormatError,
    validate_protocol,
)

#: 公司行动记录不允许出现的账户字段（出现即结构不合法，不猜同名字段）。
_ACCOUNT_ONLY_FIELDS = {"fee", "notional", "amount", "side", "units", "cash_paid",
                        "receivable", "equity", "mark"}
ACTION_REQUIRED = {"event_id", "symbol", "type"}

MODEL_CARD_REQUIRED = {
    "dependent_return", "factor_returns", "form", "frequency", "window",
    "risk_free", "currency", "missing_alignment", "estimation", "uncertainty",
    "status",
}

CASH_ZERO_REF = "cash.zero@1.0.0"


def _validate_actions(actions: list[dict]) -> None:
    if not isinstance(actions, list):
        raise IdentityFormatError("account.actions must be a list when declared")
    if not actions:
        return  # 无公司行动是合法状态（如全现金账户）
    seen: set[str] = set()
    for index, action in enumerate(actions):
        if not isinstance(action, dict) or not set(action) >= ACTION_REQUIRED:
            raise IdentityFormatError(
                f"actions[{index}] needs {sorted(ACTION_REQUIRED)}: {action!r}"
            )
        foreign = _ACCOUNT_ONLY_FIELDS & set(action)
        if foreign:
            raise IdentityFormatError(
                f"actions[{index}] 带账户字段 {sorted(foreign)}；公司行动资料必须独立于账户"
            )
        event_id = str(action["event_id"])
        if event_id in seen:
            raise IdentityFormatError(f"duplicate action event_id: {event_id}")
        seen.add(event_id)


def _account_tables(name: str, account: dict) -> tuple[pd.DataFrame, pd.DataFrame,
                                                        pd.DataFrame, pd.DataFrame]:
    for key in ("equity", "trades", "events", "prices"):
        if not isinstance(account.get(key), pd.DataFrame):
            raise IdentityFormatError(f"account[{name}].{key} must be a DataFrame")
    if "initial" not in account or not isinstance(account["initial"], (int, float)):
        raise IdentityFormatError(f"account[{name}].initial must be a number")
    return account["equity"], account["trades"], account["events"], account["prices"]


def _layer1_capital(name: str, account: dict) -> dict:
    equity, trades, events, prices = _account_tables(name, account)
    actions = account.get("actions", [])
    if len(events) and not actions:
        raise IdentityFormatError(
            f"account[{name}] has cash events but no company-action source to map them"
        )
    _validate_actions(actions)
    contributions = capital_contributions(
        equity=equity, trades=trades, events=events, actions=actions, prices=prices,
        initial=float(account["initial"]),
    )
    check = reconcile(contributions=contributions, equity=equity,
                      initial=float(account["initial"]))
    result = {
        "account": name,
        "contributions": contributions.to_dict(orient="records"),
        "reconciliation": check,
        "tolerance_cny": RECONCILE_TOLERANCE,
    }
    if not check["passed"]:
        result["status"] = "reconciliation_failed"
        result["detail"] = "贡献合计与净损益差额超过容差；不得宣称账已算对"
    else:
        result["status"] = "reconciled"
    result["note"] = (
        "资金贡献只说明钱在哪里赚到，不能单独证明为什么赚到；"
        "缺期末持仓或手续费记录会破坏核对"
    )
    return result


def _build_path_summary(name: str, account: dict) -> dict:
    """为 compare_accounts 生成最小路径摘要（诚实算术，不拟合）。"""
    equity = account["equity"]
    equity = equity.copy()
    equity["date"] = pd.to_datetime(equity["date"])
    final = float(equity["equity"].iloc[-1])
    initial = float(account["initial"])
    days = (equity["date"].iloc[-1] - equity["date"].iloc[0]).days
    years = max(days, 1) / 365.25
    cagr = (final / initial) ** (1 / years) - 1 if years > 0 else 0.0
    running_max = equity["equity"].cummax()
    max_drawdown = float(((equity["equity"] - running_max) / running_max).min())
    fees = (float(account["trades"]["fee"].sum())
            if len(account["trades"]) else 0.0)
    return {
        "summary": {
            "initial": initial, "final": final, "cagr": float(cagr),
            "max_drawdown": float(max_drawdown),
            "trades": int(len(account["trades"])), "fees": fees, "fee": fees,
        },
        "equity": equity,
        "trades": account["trades"],
        "periods": pd.DataFrame({"period": ["full"],
                                 "return_": [final / initial - 1]}),
    }


COMPARISON_REQUIRED = {
    "variant", "base", "declared_action", "pool_versions", "entity_sets",
    "period", "initial_cash", "external_flows", "fee_schedule", "benchmark",
    "frozen_rules", "input_identity",
}
#: 固定必查集合；协议不得用 must_match 之类字段裁剪检查面。
FORBIDDEN_COMPARISON_KEYS = {"must_match", "skip_checks", "optional"}


def validate_comparison_contract(comparison: dict) -> None:
    """比较合同完整性：缺必需键或带裁剪键即格式错误（不可删字段逃过检查）。"""
    if not isinstance(comparison, dict):
        raise IdentityFormatError("protocol.comparison must be a dict")
    forbidden = FORBIDDEN_COMPARISON_KEYS & set(comparison)
    if forbidden:
        raise IdentityFormatError(
            f"protocol.comparison contains escape keys {sorted(forbidden)}; "
            "必查集合固定，不得由协议裁剪")
    missing = COMPARISON_REQUIRED - set(comparison)
    if missing:
        raise IdentityFormatError(
            f"protocol.comparison missing required fields: {sorted(missing)}")
    for key in ("variant", "base", "declared_action"):
        if not isinstance(comparison[key], str) or not comparison[key].strip():
            raise IdentityFormatError(f"comparison.{key} must be a non-empty string")
    for key in ("pool_versions", "entity_sets", "external_flows", "fee_schedule",
                "benchmark", "frozen_rules"):
        value = comparison[key]
        if not isinstance(value, dict) or {"base", "variant"} - set(value):
            raise IdentityFormatError(
                f"comparison.{key} must be a dict with 'base' and 'variant' entries")
    if not isinstance(comparison["period"], dict) or \
            {"start", "end"} - set(comparison["period"]):
        raise IdentityFormatError("comparison.period must have start/end")
    if not isinstance(comparison["initial_cash"], (int, float)) \
            or isinstance(comparison["initial_cash"], bool):
        raise IdentityFormatError("comparison.initial_cash must be a number")


def _layer2_decision_increment(accounts: dict, comparison: dict) -> dict:
    validate_comparison_contract(comparison)
    variant_name, base_name = comparison["variant"], comparison["base"]
    if variant_name not in accounts or base_name not in accounts:
        raise IdentityFormatError(
            f"comparison accounts missing: {variant_name}/{base_name}"
        )
    declared_action = comparison["declared_action"]
    variant, base = accounts[variant_name], accounts[base_name]
    eq_v, tr_v, _ev_v, _pr_v = _account_tables(variant_name, variant)
    eq_b, tr_b, _ev_b, _pr_b = _account_tables(base_name, base)

    mismatch: list[dict] = []
    unknown_conditions: list[str] = []
    checks: dict[str, bool | None] = {}

    def require_equal(field: str, label: str, value_v, value_b) -> None:
        if value_v is None or value_b is None:
            checks[label] = None
            unknown_conditions.append(
                f"{label}: 声明为未知（None），未经核对不记true")
            return
        equal = value_v == value_b
        checks[label] = equal
        if not equal:
            mismatch.append({"check": label, "detail": f"{value_v} vs {value_b}"})

    # 完整候选池：以协议声明的实体集合为准，不从成交记录反推未成交候选。
    require_equal("pool_versions", "pool_version_equal",
                  comparison["pool_versions"].get("base"),
                  comparison["pool_versions"].get("variant"))
    require_equal("entity_sets", "pool_entities_equal",
                  sorted(map(str, comparison["entity_sets"]["base"])),
                  sorted(map(str, comparison["entity_sets"]["variant"])))
    # 期间：声明值彼此相等，且与两份账户的实际起止一致。
    require_equal("period", "period_declared_equal",
                  comparison["period"], comparison["period"])
    actual_span_v = (str(pd.Timestamp(eq_v["date"].iloc[0]).date()),
                     str(pd.Timestamp(eq_v["date"].iloc[-1]).date()))
    actual_span_b = (str(pd.Timestamp(eq_b["date"].iloc[0]).date()),
                     str(pd.Timestamp(eq_b["date"].iloc[-1]).date()))
    declared_span = (str(comparison["period"]["start"]),
                     str(comparison["period"]["end"]))
    if actual_span_v != declared_span or actual_span_b != declared_span:
        mismatch.append({
            "check": "period_matches_accounts",
            "detail": f"declared={declared_span} actual_variant={actual_span_v} "
                      f"actual_base={actual_span_b}",
        })
    # 初始资金：声明值彼此相等，且等于账户记录。
    require_equal("initial_cash", "initial_cash_equal",
                  comparison["initial_cash"], comparison["initial_cash"])
    if float(comparison["initial_cash"]) != float(variant["initial"]) \
            or float(comparison["initial_cash"]) != float(base["initial"]):
        mismatch.append({
            "check": "initial_cash_matches_accounts",
            "detail": f"declared={comparison['initial_cash']} "
                      f"variant={variant['initial']} base={base['initial']}",
        })
    require_equal("external_flows", "external_flows_equal",
                  comparison["external_flows"].get("base"),
                  comparison["external_flows"].get("variant"))
    # 费用按规则比较；声明不一致或声明与实际成交费率矛盾都拒绝归因。
    require_equal("fee_schedule", "fee_schedule_equal",
                  comparison["fee_schedule"].get("base"),
                  comparison["fee_schedule"].get("variant"))

    def realized_fee_rate(trades: pd.DataFrame, side: str) -> float | None:
        group = trades[trades["side"].astype(str) == side]
        notional = float(group["notional"].sum()) if len(group) else 0.0
        if notional <= 0:
            return None
        return float(group["fee"].sum()) / notional

    for account_name, account, trades in (
        ("variant", comparison["fee_schedule"].get("variant"), tr_v),
        ("base", comparison["fee_schedule"].get("base"), tr_b),
    ):
        if not isinstance(account, dict):
            continue
        for side, declared_rate in account.items():
            realized = realized_fee_rate(trades, str(side))
            if realized is None:
                continue
            if declared_rate is None or abs(float(declared_rate) - realized) > 1e-9:
                mismatch.append({
                    "check": "fee_schedule_consistent_with_trades",
                    "detail": f"{account_name}.{side} declared={declared_rate} "
                              f"realized={realized:.6f}",
                })
    require_equal("benchmark", "benchmark_equal",
                  comparison["benchmark"].get("base"),
                  comparison["benchmark"].get("variant"))
    require_equal("frozen_rules", "frozen_rules_equal",
                  comparison["frozen_rules"].get("base"),
                  comparison["frozen_rules"].get("variant"))
    input_v = comparison["input_identity"]
    input_v = (input_v.get("variant") if isinstance(input_v, dict)
               and "variant" in input_v else input_v)
    input_b = (input_v.get("base") if isinstance(input_v, dict)
               and "base" in input_v else input_v) \
        if isinstance(input_v, dict) else input_v
    require_equal("input_identity", "input_identity_equal", input_v, input_b)

    paths = compare_accounts({variant_name: _build_path_summary(variant_name, variant),
                              base_name: _build_path_summary(base_name, base)})
    path_rows = paths[paths["kind"] == "path"].set_index("key")
    row_v, row_b = path_rows.loc[variant_name], path_rows.loc[base_name]
    differences = {
        "net_pnl": float(row_v["net_pnl"] - row_b["net_pnl"]),
        "net_return": float(row_v["net_return"] - row_b["net_return"]),
        "cagr": float(row_v["cagr"] - row_b["cagr"]),
        "max_drawdown": float(row_v["max_drawdown"] - row_b["max_drawdown"]),
        "fees": float(row_v["fees"] - row_b["fees"]),
        "trades": int(row_v["trades"] - row_b["trades"]),
    }

    base_result = {
        "declared_action": declared_action,
        "variant": variant_name,
        "base": base_name,
        "checks": checks,
        "conditions_unknown": unknown_conditions,
        "differences": differences,
        "note": (
            "各维度差额是同一受控比较的描述，不可相加成资金贡献；"
            "资金归属见层1。相等指纹只证明材料一致，不证明现实执行正确。"
            "本接口消费合成账户结果，合同始终标合成"
        ),
    }
    if unknown_conditions:
        return {**base_result,
                "status": "not_attributable_conditions_unknown",
                "reason": "存在未核对条件（声明为未知）；差额不可归给该动作"}
    if mismatch:
        return {**base_result, "status": "not_attributable",
                "mismatches": mismatch,
                "reason": "受控条件不满足；差额不可归给该动作"}
    return {**base_result,
            "status": "attributable_to_declared_action_only",
            "limitation": "“only”仅指声明动作差异可解释本轮算术差额；"
                          "不证明现实执行正确，不构成收益能力证据"}


#: 本版本允许的模型卡基础频率；结构合法性按此校验。
MODEL_CARD_FREQUENCIES = {"daily", "weekly", "monthly"}


def _validate_model_card_structure(model_card: dict,
                                   registry: dict | None = None) -> None:
    """模型卡结构非法（缺键/类型错/引用不可解析）→ 格式错误，与 not_run 分开。"""
    missing = MODEL_CARD_REQUIRED - set(model_card)
    if missing:
        raise IdentityFormatError(f"model_card missing keys: {sorted(missing)}")
    for key in ("dependent_return", "form", "window", "risk_free", "currency",
                "missing_alignment", "estimation", "uncertainty", "status"):
        if not isinstance(model_card[key], str) or not model_card[key].strip():
            raise IdentityFormatError(f"model_card.{key} must be a non-empty string")
    if model_card["frequency"] not in MODEL_CARD_FREQUENCIES:
        raise IdentityFormatError(
            f"model_card.frequency must be one of {sorted(MODEL_CARD_FREQUENCIES)}; "
            f"got {model_card['frequency']!r}")
    returns = model_card["factor_returns"]
    if (not isinstance(returns, list) or not returns
            or any(not isinstance(r, str) or not r.strip() for r in returns)):
        raise IdentityFormatError(
            "model_card.factor_returns must be a non-empty list of reference strings")
    reg = registry if registry is not None else definitions.load_registry()
    for ref in returns + [model_card["dependent_return"]]:
        try:
            definitions.resolve(reg, str(ref))
        except ValueError as exc:
            raise IdentityFormatError(
                f"model reference not resolvable: {ref}: {exc}") from exc


def _layer3_risk_model(model_card: dict | None, registry: dict | None = None) -> dict:
    if model_card is None:
        return {
            "status": "not_run",
            "reason": "no_model_card_provided",
            "note": "本轮未做风险模型是合法状态；剩余收益不自动叫独特alpha或运气",
        }
    if not isinstance(model_card, dict):
        raise IdentityFormatError("model_card must be a dict or null")
    reg = registry if registry is not None else definitions.load_registry()
    _validate_model_card_structure(model_card, reg)
    for ref in model_card["factor_returns"] + [model_card["dependent_return"]]:
        card = definitions.resolve(reg, str(ref))
        if card["type"] == "state_signal" or card["definition"]["unit"] == "boolean":
            return {
                "status": "not_run",
                "reason": (
                    f"{ref} 是状态/布尔对象：宽度水平或双均线布尔不能无说明当收益因子"
                ),
            }
        if card["type"] not in {"factor_return", "benchmark"}:
            return {
                "status": "not_run",
                "reason": f"{ref} 类型 {card['type']} 不是收益序列（factor_return/benchmark）",
            }
    notes = ["本轮未实现风险模型回归，资格检查通过也不产出alpha数字"]
    if model_card.get("risk_free") == CASH_ZERO_REF:
        notes.append("现金零息是声明，不是无风险序列为零的证明")
    return {
        "status": "not_run",
        "reason": "risk_model_regression_not_implemented_this_round",
        "model_card_checks": {
            "required_fields": "present",
            "factor_return_types": "resolvable factor_return/benchmark",
        },
        "notes": notes,
    }


def explain_strategy(accounts: dict, *, model_card: dict | None,
                     protocol: dict) -> dict:
    """三层归因入口；层3 未实现回归时诚实 not_run。"""
    validate_protocol(protocol, expected_kinds={"strategy_explanation"})
    named = accounts.get("accounts") if isinstance(accounts, dict) else None
    if not isinstance(named, dict) or not named:
        raise IdentityFormatError("accounts must be {'accounts': {name: account}}")
    layer1 = {name: _layer1_capital(name, acc) for name, acc in named.items()}
    comparison = protocol.get("comparison")
    layer2 = (_layer2_decision_increment(named, comparison)
              if comparison else {"status": "not_requested"})
    layer3 = _layer3_risk_model(model_card)
    return {
        "layer1_capital": layer1,
        "layer2_decision_increment": layer2,
        "layer3_risk_model": layer3,
        "note": "三层分别回答不同的钱的问题；不能相加成伪精确总账",
    }
