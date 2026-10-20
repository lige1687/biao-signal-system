"""通用计算适配层：一份定义、多种用途。

薄封装既有实现，不复制第二套公式：
- 数值特征 → ``definitions.quote_features``（momentum/rv20/distance 列暴露）；
- 宽度 → ``definitions.breadth``（E200 共同合格分母）；
- 双均线候选 → 只读调用 ``dual_ma.dual_ma_bull_state``，颜色来自
  ``lei_color.classify_colors``、EMA20 来自 ``indicators.compute_features``；
  未就绪行记录 readiness，不混成有效看空样本。

候选身份单列：``candidate:lei.dual_ma.bull_state@draft-1`` 不进登记表。
"""
from __future__ import annotations

import pandas as pd

from lei_signal.features.indicators import compute_features
from lei_signal.research import definitions
from lei_signal.research.factor_lab.contracts import (
    IdentityFormatError,
    ResearchBatch,
    build_metadata,
    fingerprint_path,
    validate_protocol,
    validate_values_frame,
)
from lei_signal.rules.dual_ma import dual_ma_bull_state
from lei_signal.rules.lei_color import classify_colors

CANDIDATE_DUAL_MA = "candidate:lei.dual_ma.bull_state@draft-1"

_RESEARCH_PACKAGE = "src/lei_signal/research/definitions.py"
_CANDIDATE_CODE_FILES = [
    "src/lei_signal/rules/dual_ma.py",
    "src/lei_signal/rules/lei_color.py",
    "src/lei_signal/features/indicators.py",
    "src/lei_signal/domain/rules_config.py",
]

#: 候选卡的机器绑定（人类可读草案见 raw/candidate-card-*.md）。
CANDIDATE_CARDS = {
    CANDIDATE_DUAL_MA: {
        "id": "candidate:lei.dual_ma.bull_state",
        "version": "draft-1",
        "name": "双均线共同确认状态（候选）",
        "type": "state_signal",
        "definition": {
            "formula": (
                "Close>EMA20 且 Close>SMA20，两均线相比前一观察上升，"
                "signal_color=green（读取当前状态，不要求同日上穿）"
            ),
            "parameters": {"ema": 20, "sma": 20, "color": "green"},
            "unit": "boolean",
        },
        "card_draft_path": (
            "docs/experiments/raw/factor-research-workbench-v1-2026-09-14/"
            "candidate-card-dual-ma-bull-state-draft-1.md"
        ),
        "status": {
            "definition_clarity": "explicit",
            "data_qualification": "synthetic_only",
            "implementation": "bound_to_existing_functions",
            "effectiveness": "no_evidence",
            "production": "not_authorized",
        },
        "readiness_semantics": (
            "warmup/缺失行原函数输出False；适配层单列 readiness，"
            "未就绪行 value=NaN、missing_reason=warmup_not_ready"
        ),
    },
}


def _code_identity(files: list[str]) -> dict:
    from lei_signal.research.definitions import ROOT

    return {"modules": [dict(fingerprint_path(ROOT / f), path=f) for f in files]}


def _registered_card(reference: str, registry: dict | None) -> dict:
    reg = registry if registry is not None else definitions.load_registry()
    try:
        return definitions.resolve(reg, reference)
    except ValueError as exc:
        raise IdentityFormatError(f"reference not resolvable: {reference}: {exc}") from exc


def _require_params(card: dict, expected: dict, reference: str) -> None:
    actual = card["definition"]["parameters"]
    if actual != expected:
        raise IdentityFormatError(
            f"implementation binding differs from registered parameters for "
            f"{reference}: card={actual} expected={expected}"
        )


def _prices_from_inputs(reference: str, inputs: dict) -> pd.DataFrame:
    prices = inputs.get("prices")
    if not isinstance(prices, pd.DataFrame) or prices.empty:
        raise IdentityFormatError(f"{reference}: inputs.prices must be a non-empty DataFrame")
    if not prices.index.is_unique or not prices.index.is_monotonic_increasing:
        raise IdentityFormatError(f"{reference}: prices need unique increasing dates")
    if len(prices.columns) == 0 or not prices.columns.is_unique:
        raise IdentityFormatError(f"{reference}: prices need unique non-empty entity columns")
    if any(not str(c).strip() for c in prices.columns):
        raise IdentityFormatError(f"{reference}: entity ids must be non-empty")
    return prices


def _quote_column_values(prices: pd.DataFrame, column: str) -> pd.DataFrame:
    """逐实体取 quote_features 指定列，缺值行保留并给缺失原因。"""
    rows = []
    for entity in prices.columns:
        features = definitions.quote_features(prices[entity])
        series = features[column]
        price = prices[entity]
        for day, value in series.items():
            reason = None
            if pd.isna(value):
                reason = ("price_missing" if pd.isna(price.at[day])
                          else "warmup_history_insufficient")
            rows.append(
                {
                    "observation_date": day,
                    "entity_id": str(entity),
                    "value": None if pd.isna(value) else float(value),
                    "missing_reason": reason,
                }
            )
    return pd.DataFrame(rows, columns=["observation_date", "entity_id", "value",
                                       "missing_reason"])


def _breadth_values(prices: pd.DataFrame, inputs: dict, reference: str,
                    window: int) -> pd.DataFrame:
    membership = inputs.get("membership_by_date")
    if not isinstance(membership, dict) or not membership:
        raise IdentityFormatError(f"{reference}: explicit dated membership required")
    normalized = {}
    for day, members in membership.items():
        key = pd.Timestamp(day)
        if key in normalized:
            raise IdentityFormatError(f"{reference}: duplicate membership date {key.date()}")
        if isinstance(members, str) or not isinstance(members, (list, tuple)):
            raise IdentityFormatError(f"{reference}: membership must be a list per date")
        if any(isinstance(m, str) and not m.strip() for m in members) or any(
            not isinstance(m, str) for m in members
        ):
            raise IdentityFormatError(f"{reference}: membership members must be non-empty strings")
        # 空成员列表是合法资料状态：breadth 返回 membership_missing，不伪装成零宽度。
        normalized[key] = [str(m) for m in members]
    missing_members = sorted(
        {m for members in normalized.values() for m in members}
        - {str(c) for c in prices.columns}
    )
    if missing_members:
        raise IdentityFormatError(
            f"{reference}: membership symbols missing from close panel: {missing_members}"
        )
    table = definitions.breadth(prices, normalized)
    universe = str(inputs.get("universe_id") or reference)
    column = f"b{window}"
    rows = []
    for day, row in table.iterrows():
        rows.append(
            {
                "observation_date": day,
                "entity_id": universe,
                "value": None if pd.isna(row[column]) else float(row[column]),
                "missing_reason": row["missing_reason"],
            }
        )
    return pd.DataFrame(rows, columns=["observation_date", "entity_id", "value",
                                       "missing_reason"])


def _dual_ma_values(inputs: dict) -> tuple[pd.DataFrame, list[dict]]:
    bars = inputs.get("bars")
    if not isinstance(bars, dict) or not bars:
        raise IdentityFormatError(f"{CANDIDATE_DUAL_MA}: inputs.bars must map entity->frame")
    rows, findings = [], []
    for entity, frame in bars.items():
        if not isinstance(frame, pd.DataFrame) or "close" not in frame.columns:
            raise IdentityFormatError(f"{CANDIDATE_DUAL_MA}: bars[{entity}] needs close column")
        if not frame.index.is_unique or not frame.index.is_monotonic_increasing:
            raise IdentityFormatError(f"{CANDIDATE_DUAL_MA}: bars[{entity}] dates invalid")
        required = {"open", "high", "low", "volume"}
        missing = required - set(frame.columns)
        if missing:
            raise IdentityFormatError(
                f"{CANDIDATE_DUAL_MA}: bars[{entity}] missing columns {sorted(missing)}"
            )
        features = compute_features(frame)
        colored = classify_colors(features)
        state = dual_ma_bull_state(colored)
        color_ready = colored["color_ready"].fillna(False)
        not_ready = 0
        for day, value in state.items():
            if not bool(color_ready.at[day]):
                not_ready += 1
                rows.append({"observation_date": day, "entity_id": str(entity),
                             "value": None, "missing_reason": "warmup_not_ready"})
            else:
                rows.append({"observation_date": day, "entity_id": str(entity),
                             "value": int(bool(value)), "missing_reason": None})
        true_rows = sum(1 for r in rows if r["entity_id"] == str(entity)
                        and r["value"] == 1)
        false_rows = sum(1 for r in rows if r["entity_id"] == str(entity)
                         and r["value"] == 0)
        findings.append({
            "code": "entity_readiness",
            "entity_id": str(entity),
            "not_ready_rows": not_ready,
            "state_true_rows": true_rows,
            "state_false_rows": false_rows,
            "detail": "未就绪行不计为有效看空样本（候选卡 readiness 语义）",
        })
    return pd.DataFrame(rows, columns=["observation_date", "entity_id", "value",
                                       "missing_reason"]), findings


def calculate_batch(
    reference: str,
    inputs: dict,
    *,
    protocol: dict,
    registry: dict | None = None,
) -> ResearchBatch:
    """对已登记对象或已声明候选计算一批值，附完整元数据。"""
    validate_protocol(protocol, expected_kinds={
        "calculation_only", "predictive_diagnostic", "state_diagnostic"})
    if not isinstance(inputs, dict):
        raise IdentityFormatError("inputs must be a dict")
    findings: list[dict] = []

    if reference in CANDIDATE_CARDS:
        card = dict(CANDIDATE_CARDS[reference])
        card_kind = "candidate"
        values, entity_findings = _dual_ma_values(inputs)
        findings.extend(entity_findings)
        findings.append({"code": "parameter_binding_ok",
                         "detail": "候选只读调用 dual_ma_bull_state/classify_colors/"
                                   "compute_features；未复制公式、未改生产"})
        metadata = build_metadata(
            reference=reference,
            card=card,
            card_kind=card_kind,
            protocol=protocol,
            entity_axis="instrument",
            value_type="boolean",
            data_identity={"inputs": {k: _describe_input(v) for k, v in inputs.items()},
                           "declared_inputs": protocol.get("inputs", {}),
                           "synthetic": True},
            code_identity=_code_identity(_CANDIDATE_CODE_FILES + [_RESEARCH_PACKAGE]),
            calendar={"timezone": protocol["timezone"],
                      "note": "合成日历；真实交易日历资格不在本轮范围"},
            time_evidence={"observation_time": "合成交易日收盘",
                           "evaluation_cutoff": protocol.get("evaluation_cutoff")},
        )
        return ResearchBatch(validate_values_frame(values), metadata, findings)

    card = _registered_card(reference, registry)
    identity = card["id"]
    code_files = [_RESEARCH_PACKAGE]
    universe_identity = None
    entity_axis, value_type = "instrument", "continuous"

    if identity == "mixed.momentum.raw":
        _require_params(card, {"long_lag": 252, "skip_lag": 21}, reference)
        prices = _prices_from_inputs(reference, inputs)
        values = _quote_column_values(prices, "momentum")
    elif identity == "mixed.rv20":
        _require_params(card, {"window": 20, "ddof": 1, "annualization": 252}, reference)
        prices = _prices_from_inputs(reference, inputs)
        values = _quote_column_values(prices, "rv20")
    elif identity in {"trend.distance50", "trend.distance200"}:
        n = 50 if identity.endswith("50") else 200
        _require_params(card, {"window": n}, reference)
        prices = _prices_from_inputs(reference, inputs)
        values = _quote_column_values(prices, f"distance{n}")
    elif identity.startswith("breadth.") and identity.endswith(".common"):
        n = 50 if ".b50." in identity else 200
        _require_params(
            card,
            {"window": n, "eligible_window": 200, "minimum_coverage": 0.9,
             "strict_above": True},
            reference,
        )
        prices = _prices_from_inputs(reference, inputs)
        values = _breadth_values(prices, inputs, reference, n)
        universe_identity = {
            "universe_id": str(inputs.get("universe_id") or reference),
            "membership_source": inputs.get("membership_source", "synthetic_segments"),
            "note": "合成成员链；不得称真实沪深300证据",
        }
        entity_axis, value_type = "universe", "fraction_bounded"
    else:
        raise IdentityFormatError(
            f"{reference}: registered but no factor_lab implementation; "
            "登记不等于已接入"
        )

    findings.append({"code": "parameter_binding_ok",
                     "detail": f"{reference} 参数与登记卡逐一核对一致；经 quote_features/"
                               f"breadth 既有实现计算，未复制公式"})
    reason_counts = values["missing_reason"].value_counts(dropna=True).to_dict()
    counts = {str(k): int(v) for k, v in reason_counts.items()}
    findings.append({"code": "missing_reason_counts", "counts": counts})
    metadata = build_metadata(
        reference=reference,
        card=card,
        card_kind="registered",
        protocol=protocol,
        entity_axis=entity_axis,
        value_type=value_type,
        data_identity={"inputs": {k: _describe_input(v) for k, v in inputs.items()},
                       "declared_inputs": protocol.get("inputs", {}),
                       "synthetic": True},
        code_identity=_code_identity(code_files),
        calendar={"timezone": card["time"]["timezone"],
                  "note": "合成输入按协议时区解释"},
        time_evidence={"observation_time": card["time"]["observation_time"],
                       "evaluation_cutoff": protocol.get("evaluation_cutoff")},
        universe_identity=universe_identity,
    )
    return ResearchBatch(validate_values_frame(values), metadata, findings)


def _describe_input(value) -> dict:
    if isinstance(value, pd.DataFrame):
        return {"kind": "DataFrame", "rows": int(len(value)),
                "columns": [str(c) for c in value.columns]}
    if isinstance(value, dict):
        return {"kind": "dict", "keys": sorted(str(k) for k in value)}
    return {"kind": type(value).__name__}
