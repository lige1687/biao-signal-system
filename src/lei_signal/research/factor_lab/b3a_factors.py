"""B3-a 批次候选因子：抵扣价距离与入场均线组最近距离（2026-09-20）。

新文件实现，不修改 factor_lab 既有模块；复用既有合同层
（contracts.validate_protocol / build_metadata / validate_values_frame）
与既有特征实现（indicators.compute_features 只读调用，产出
close_lag20 / sma{20,60,120} / ema{20,60,120}），不复制第二套公式。

两候选均为 B1 表单准入（admit_as_candidate）后的定义级验证实现：
- ``trend.cost_basis_distance20``：close[t]/close[t-20] − 1（B1 表单 1）。
  这里的"抵扣价"是均线口径的 N 期前价格，**不是账户真实持仓成本**。
- ``mixed.pullback_ma_distance``：收盘价到六均线（EMA/SMA×20/60/120）中
  最近一条的绝对相对距离（B1 表单 3）。只描述距离，不判定"回调成立"，
  不新增任何交易判断规则。

不可算行以 NaN + missing_reason 返回原因，不补零、不外推。
"""
from __future__ import annotations

import pandas as pd

from lei_signal.features.indicators import compute_features
from lei_signal.research.factor_lab.contracts import (
    IdentityFormatError,
    ResearchBatch,
    build_metadata,
    fingerprint_path,
    validate_protocol,
    validate_values_frame,
)

CANDIDATE_COST_BASIS20 = "candidate:trend.cost_basis_distance20@draft-1"
CANDIDATE_PULLBACK_MA = "candidate:mixed.pullback_ma_distance@draft-1"

COST_BASIS_WINDOW = 20
PULLBACK_MA_WINDOWS = (20, 60, 120)
PULLBACK_MA_TYPES = ("ema", "sma")

_RESEARCH_PACKAGE = "src/lei_signal/research/definitions.py"
_B3A_CODE_FILES = [
    "src/lei_signal/features/indicators.py",
    "src/lei_signal/research/factor_lab/b3a_factors.py",
    "src/lei_signal/research/factor_lab/contracts.py",
]

#: 候选卡机器绑定（人类可读草案见 raw/factor-b3a-2026-09-20/）。
B3A_CANDIDATE_CARDS = {
    CANDIDATE_COST_BASIS20: {
        "id": "candidate:trend.cost_basis_distance20",
        "version": "draft-1",
        "name": "20 日抵扣价距离（候选）",
        "type": "feature",
        "definition": {
            "formula": "close[t] / close[t-20] - 1",
            "parameters": {"window": 20},
            "unit": "ratio",
        },
        "spec_anchor": ["trading-spec-v1 §4.2（抵扣价与 SMA 方向，cost_basis_N=N 周期前价格）"],
        "spec_layer": "road",
        "card_draft_path": (
            "docs/experiments/raw/factor-b3a-2026-09-20/definition-cost-basis20.md"
        ),
        "status": {
            "definition_clarity": "explicit",
            "data_qualification": "synthetic_only",
            "implementation": "bound_to_existing_functions",
            "effectiveness": "no_evidence",
            "production": "not_authorized",
        },
        "readiness_semantics": (
            "t<20 或 close[t-20] 缺失→NaN(warmup_history_insufficient)；"
            "观察日 close 缺失→NaN(price_missing)；close[t-20]=0→NaN(zero_denominator)"
        ),
    },
    CANDIDATE_PULLBACK_MA: {
        "id": "candidate:mixed.pullback_ma_distance",
        "version": "draft-1",
        "name": "入场均线组最近距离（候选）",
        "type": "feature",
        "definition": {
            "formula": "min(|close - M| / M)，M ∈ {EMA,SMA} × {20,60,120}",
            "parameters": {
                "windows": list(PULLBACK_MA_WINDOWS),
                "ma_types": list(PULLBACK_MA_TYPES),
            },
            "unit": "ratio（非负）",
        },
        "spec_anchor": [
            "trading-spec-v1 §9 模块 A A2（回调至 20/60/120 均线组；"
            "触及允许距离 ma_touch_distance 是规则层参数，不写入本卡）"
        ],
        "spec_layer": "entry_trigger",
        "card_draft_path": (
            "docs/experiments/raw/factor-b3a-2026-09-20/definition-pullback-ma-distance.md"
        ),
        "status": {
            "definition_clarity": "explicit",
            "data_qualification": "synthetic_only",
            "implementation": "bound_to_existing_functions",
            "effectiveness": "no_evidence",
            "production": "not_authorized",
        },
        "readiness_semantics": (
            "六均线任一不可算（预热不足或窗口含缺失）→NaN(warmup_history_insufficient)，"
            "不部分计算；观察日 close 缺失→NaN(price_missing)；均线值为 0→NaN(zero_denominator)"
        ),
    },
}

_BARS_REQUIRED_COLUMNS = {"open", "high", "low", "close", "volume"}


def _bars_from_inputs(reference: str, inputs: dict) -> dict[str, pd.DataFrame]:
    bars = inputs.get("bars")
    if not isinstance(bars, dict) or not bars:
        raise IdentityFormatError(f"{reference}: inputs.bars must map entity->frame")
    for entity, frame in bars.items():
        if not isinstance(frame, pd.DataFrame) or "close" not in frame.columns:
            raise IdentityFormatError(f"{reference}: bars[{entity}] needs close column")
        missing = _BARS_REQUIRED_COLUMNS - set(frame.columns)
        if missing:
            raise IdentityFormatError(
                f"{reference}: bars[{entity}] missing columns {sorted(missing)}"
            )
        if not frame.index.is_unique or not frame.index.is_monotonic_increasing:
            raise IdentityFormatError(f"{reference}: bars[{entity}] dates invalid")
    return bars


def _features_for(frame: pd.DataFrame) -> pd.DataFrame:
    """只读复用 compute_features：显式钉 20/60/120 周期，避免依赖全局配置漂移。"""
    config = {
        "ema_periods": list(PULLBACK_MA_WINDOWS),
        "sma_periods": list(PULLBACK_MA_WINDOWS),
        "lag_periods": [COST_BASIS_WINDOW],
        "atr_period": 14,
    }
    return compute_features(frame, config)


def _reason(close_t, denominator) -> str | None:
    if pd.isna(close_t):
        return "price_missing"
    if denominator is None or pd.isna(denominator):
        return "warmup_history_insufficient"
    if float(denominator) == 0.0:
        return "zero_denominator"
    return None


def _cost_basis_values(reference: str, bars: dict[str, pd.DataFrame]):
    rows, findings = [], []
    for entity, frame in bars.items():
        features = _features_for(frame)
        close = features["close"].astype(float)
        lag = features[f"close_lag{COST_BASIS_WINDOW}"].astype(float)
        not_ready = 0
        for day in features.index:
            c, l = close.at[day], lag.at[day]
            if pd.isna(c) or pd.isna(l) or l == 0.0:
                not_ready += 1
                rows.append({
                    "observation_date": day, "entity_id": str(entity),
                    "value": None, "missing_reason": _reason(c, l),
                })
            else:
                rows.append({
                    "observation_date": day, "entity_id": str(entity),
                    "value": float(c / l - 1.0), "missing_reason": None,
                })
        findings.append({
            "code": "entity_readiness", "entity_id": str(entity),
            "not_ready_rows": not_ready,
            "detail": "warmup/缺失/零分母行保留为 NaN 并给出原因，不补零",
        })
    return pd.DataFrame(rows, columns=["observation_date", "entity_id", "value",
                                       "missing_reason"]), findings


def _pullback_ma_values(reference: str, bars: dict[str, pd.DataFrame]):
    columns = [f"{typ}{win}" for win in PULLBACK_MA_WINDOWS
               for typ in PULLBACK_MA_TYPES]
    rows, findings = [], []
    for entity, frame in bars.items():
        features = _features_for(frame)
        close = features["close"].astype(float)
        ma_frame = features[columns].astype(float)
        not_ready = 0
        for day in features.index:
            c = close.at[day]
            ma_row = ma_frame.loc[day]
            if pd.isna(c):
                not_ready += 1
                rows.append({
                    "observation_date": day, "entity_id": str(entity),
                    "value": None, "missing_reason": "price_missing",
                })
                continue
            if ma_row.isna().any():
                # 六均线任一不可算（预热不足或窗口含缺失）→ NaN，不部分计算
                not_ready += 1
                rows.append({
                    "observation_date": day, "entity_id": str(entity),
                    "value": None, "missing_reason": "warmup_history_insufficient",
                })
                continue
            if (ma_row == 0.0).any():
                not_ready += 1
                rows.append({
                    "observation_date": day, "entity_id": str(entity),
                    "value": None, "missing_reason": "zero_denominator",
                })
                continue
            distance = (ma_row - c).abs() / ma_row
            rows.append({
                "observation_date": day, "entity_id": str(entity),
                "value": float(distance.min()), "missing_reason": None,
            })
        findings.append({
            "code": "entity_readiness", "entity_id": str(entity),
            "not_ready_rows": not_ready,
            "detail": "六均线整组可算才出值；只描述最近距离，不判定回调成立",
        })
    return pd.DataFrame(rows, columns=["observation_date", "entity_id", "value",
                                       "missing_reason"]), findings


def calculate_b3a_batch(
    reference: str,
    inputs: dict,
    *,
    protocol: dict,
) -> ResearchBatch:
    """对 B3-a 两候选各计算一批值，附合同层完整元数据（synthetic 模式）。"""
    validate_protocol(protocol, expected_kinds={"calculation_only"})
    if not isinstance(inputs, dict):
        raise IdentityFormatError("inputs must be a dict")
    if reference not in B3A_CANDIDATE_CARDS:
        raise IdentityFormatError(f"unknown B3-a candidate reference: {reference}")
    card = dict(B3A_CANDIDATE_CARDS[reference])
    bars = _bars_from_inputs(reference, inputs)

    if reference == CANDIDATE_COST_BASIS20:
        values, entity_findings = _cost_basis_values(reference, bars)
        value_note = "close[t]/close[t-20] − 1（比例，正=价格高于 20 期前抵扣价）"
    else:
        values, entity_findings = _pullback_ma_values(reference, bars)
        value_note = "min(|close−M|/M)，M∈{EMA,SMA}×{20,60,120}（非负比例）"
    findings = list(entity_findings)
    findings.append({
        "code": "parameter_binding_ok",
        "detail": f"{reference} 参数与候选卡逐一核对；只读调用 compute_features，"
                  "未复制公式、未改生产、未新增交易判断规则",
    })

    from lei_signal.research.definitions import ROOT
    metadata = build_metadata(
        reference=reference,
        card=card,
        card_kind="candidate",
        protocol=protocol,
        entity_axis="instrument",
        value_type="continuous",
        data_identity={
            "inputs": {k: {"kind": type(v).__name__} for k, v in inputs.items()},
            "declared_inputs": protocol.get("inputs", {}),
            "value_semantics": value_note,
            "synthetic": True,
        },
        code_identity={"modules": [dict(fingerprint_path(ROOT / f), path=f)
                                   for f in _B3A_CODE_FILES]},
        calendar={"timezone": protocol["timezone"],
                  "note": "合成日历；真实交易日历资格不在本轮范围"},
        time_evidence={"observation_time": "合成交易日收盘（只用当日及此前数据）",
                       "evaluation_cutoff": protocol.get("evaluation_cutoff")},
    )
    return ResearchBatch(validate_values_frame(values), metadata, findings)
