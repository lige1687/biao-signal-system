"""状态—未来目标描述统计（factor_unit，B0合成入口；核心计算已提取）。

R2 落地：显式消费完整合同（评价起止、带时区研究截止、每产品预定稀疏锚点、
步长固定23）；成熟按标签结束格点的**逐日 close_at** 与截止比较（同日盘前未
成熟、正好收盘成熟、收盘后成熟）；主比较只用共同合法集合（状态已知∧主目标
合法∧成熟），n_true+n_false=n_comparison；全资产背景单列不混称；辅助路径
缺失独立 aux_n。数据键唯一；state 只接受真布尔/空（含上游可空布尔 pd.NA）；
I 只接受正有限或显式缺失；时刻与 session 不匹配拒绝。空输入/全部日期在窗外
返回结构化零计数，不抛 KeyError。连续状态段按完整日程序列，缺整行或未知均
断开；稀疏锚点来自合同，不按第一个已知状态动态改选；稀疏格与主比较同一
合法集合（skipped_reason/main/aux置null，不展示不记分）。

本版唯一变化：逐行目标/统计逻辑**原样提取**到
``description_core``（公共纯计算层，无输入许可概念），本入口保留全部旧校验
（synthetic 身份、固定坐标、输入严校）与旧输出包装（data_mode=synthetic、
overlap_note、no_claims）。旧校验与旧结果不变；真实模式依旧拒绝。

仍只描述合成关系：不加显著性、回归、策略收益；data_mode 必须 synthetic
（真实模式未实现，字符串换身份不放行）。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lei_signal.research.factor_unit.description_core import (
    EMPTY_GROUP,  # noqa: F401 兼容别名：旧导入引用保留
    _close_segment,  # noqa: F401
    _finite,  # noqa: F401
    _stat,  # noqa: F401
    _state_value,  # noqa: F401
    build_observation_rows,
    summarize_observation_rows,
)

FIXED_OFFSETS = {"lookback": 20, "e_offset": 1, "x_offset": 22}
SPARSE_STEP = 23


def _validate_contract(contract: dict) -> tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp]:
    if contract.get("data_mode") != "synthetic":
        raise ValueError(
            "B0 describe_states 仅接受 data_mode='synthetic'；"
            "真实模式未实现（改字符串不构成真实身份，也不是放行开关）"
        )
    for k, v in FIXED_OFFSETS.items():
        if contract.get(k) != v:
            raise ValueError(f"{k} 必须显式等于 {v}（禁止默认掩盖漏声明）")
    if contract.get("object_ref") != "candidate:lei.dual_ma.bull_state@draft-1":
        raise ValueError("object_ref 必须是双均线候选")
    window = contract.get("evaluation_window") or {}
    if not (isinstance(window, dict) and bool(window.get("start")) and bool(window.get("end"))):
        raise ValueError("evaluation_window 必须显式给出 {start, end}")
    eval_start = pd.Timestamp(window["start"])
    eval_end = pd.Timestamp(window["end"])
    if eval_start > eval_end:
        raise ValueError("evaluation_window start 不得晚于 end")
    cutoff_raw = contract.get("research_cutoff")
    if not isinstance(cutoff_raw, str):
        raise ValueError("research_cutoff 必须显式给出（带时区ISO时刻）")
    cutoff = pd.Timestamp(cutoff_raw)
    if cutoff.tzinfo is None:
        raise ValueError("research_cutoff 必须带时区")
    anchors = contract.get("sparse_anchor_session")
    if not isinstance(anchors, dict) or not anchors:
        raise ValueError("sparse_anchor_session 必须显式给出每产品锚点（不允许动态选锚）")
    step = contract.get("sparse_step")
    if step != SPARSE_STEP:
        raise ValueError(f"sparse_step 固定为 {SPARSE_STEP}（0/负/1等一律拒绝）")
    return eval_start, eval_end, cutoff


def _validate_inputs(values: pd.DataFrame, schedule: pd.DataFrame,
                     anchors: dict, eval_start: pd.Timestamp,
                     eval_end: pd.Timestamp) -> dict:
    need = {"symbol", "session", "state", "I"}
    missing = need - set(values.columns)
    if missing:
        raise ValueError(f"values 缺字段: {sorted(missing)}")
    if not {"session", "close_at"}.issubset(schedule.columns):
        raise ValueError("schedule 需要 session/close_at 两列")
    sessions = pd.to_datetime(schedule["session"])
    if not sessions.is_unique or not sessions.is_monotonic_increasing:
        raise ValueError("schedule.session 必须唯一递增")
    parsed_close = [pd.Timestamp(v) for v in schedule["close_at"]]
    for i, ts in enumerate(parsed_close):
        if ts.tzinfo is None:
            raise ValueError("close_at 必须逐日带时区（无时区时刻拒绝）")
        if ts.date() != sessions[i].date():
            raise ValueError(
                f"close_at 日期与 session 不匹配（{sessions[i].date()}）"
            )
    if not values.empty:
        keys = list(zip(values["symbol"], pd.to_datetime(values["session"]), strict=True))
        if len(keys) != len(set(keys)):
            raise ValueError("(symbol, session) 必须唯一")
        for s in values["state"]:
            _state_value(s)  # 可空布尔pd.NA/None/NaN=未知；字符串/数字拒绝
        levels = pd.to_numeric(values["I"], errors="coerce")
        bad_I = levels.dropna()
        if ((bad_I <= 0) | ~np.isfinite(bad_I.astype(float))).any():
            raise ValueError("I 只接受正有限数值或显式缺失（0/负/无穷拒绝）")
        symbols = set(values["symbol"])
        absent = symbols - set(anchors)
        if absent:
            raise ValueError(f"sparse_anchor_session 缺产品锚点：{sorted(absent)}")
    in_window = (sessions >= eval_start) & (sessions <= eval_end)
    if not in_window.any():
        raise ValueError("日程在评价窗内没有任何格点（窗与日程不一致）")
    return {"session_pos": {s: i for i, s in enumerate(sessions)},
            "sched_sessions": sessions}


def describe_states(values: pd.DataFrame, schedule: pd.DataFrame, contract: dict) -> dict:
    """合成状态—目标描述；合同必填显式，输入严校，空集结构化零。"""
    eval_start, eval_end, cutoff = _validate_contract(contract)
    anchors = contract["sparse_anchor_session"]
    _validate_inputs(values, schedule, anchors, eval_start, eval_end)

    if values.empty:
        return {
            "data_mode": "synthetic", "symbols": {},
            "overlap_note": "21日未来窗口互相重叠，不得当作独立多次成功",
            "no_claims": ["strategy_return", "annualization", "IC", "significance",
                          "risk_adjusted_alpha"],
        }

    built = build_observation_rows(
        values, schedule, eval_start=eval_start, eval_end=eval_end,
        cutoff=cutoff, e_offset=FIXED_OFFSETS["e_offset"],
        x_offset=FIXED_OFFSETS["x_offset"])
    out_symbols = summarize_observation_rows(
        built, values, schedule, eval_start=eval_start, eval_end=eval_end,
        anchors=anchors, sparse_step=SPARSE_STEP)

    return {
        "data_mode": "synthetic",
        "overlapping_windows": True,
        "overlap_note": "每日期滚动的21日未来窗口互相重叠，不得当作独立多次成功；"
                        "状态真假差异是历史关联描述，不是因果或可成交利润",
        "no_claims": ["strategy_return", "annualization", "IC", "significance",
                      "risk_adjusted_alpha"],
        "symbols": out_symbols,
    }
