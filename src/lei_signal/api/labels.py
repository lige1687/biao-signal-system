"""中文标签映射（从 ui/app.py 移植，保持两端口径一致）。

任何新标签必须先在这里登记，前端不自行翻译规则 ID。
"""
from __future__ import annotations

#: 风险状态（与 app.py 的 _RISK_STATE_CN 一致）
RISK_STATE_CN: dict[str, str] = {
    "normal": "正常",
    "gray_watch": "转灰观察",
    "active_top": "有效顶部",
    "black": "黑色",
    # 顶部结构有效 + 当日黑色，两个风险维度同时成立（Streamlit 侧原文为 "Top+Black"）
    "top_plus_black": "有效顶部+黑色",
    "c_invalidated": "C 失效",
}

#: EMA20 早期转强档位（与 app.py 的 _TIER_CN 一致）。
#: early_watch 必须保持中性表述「候选观察」，不得暗示买入。
TIER_CN: dict[str, str] = {
    "early_watch": "候选观察",
    "structure_confirmed": "结构确认",
    "joint_confirmed": "共同确认",
    "long_trend_improved": "长周期改善",
}

STRUCTURE_STATUS_CN: dict[str, str] = {
    "candidate": "候选",
    "confirmed": "已确认",
    "active": "活跃",
    "invalidated": "已失效",
    "expired": "已过期",
}

STRUCTURE_TYPE_CN: dict[str, str] = {
    "higher_low_bottom": "更高低点底部",
    "double_bottom": "双底",
    "bullish_reversal_bottom": "反转底部",
    "top_structure": "顶部结构",
}

#: rule_id → 中文名（时间轴/事件列表展示）
RULE_CN: dict[str, str] = {
    "lei_color": "颜色转换",
    "dual_ma_bull_confirmed": "双均线共同确认",
    "dual_ma_spread": "双均线张口",
    "ema20_reclaim_rising": "EMA20 早期转强",
    "first_ma_pullback": "首次均线回撤",
    "exit_ema20_costbasis": "抵扣价退出",
    "reward_risk_filter": "盈亏比",
    "tradability_gate": "可交易性门禁",
    "long_trend": "长周期趋势",
    "key_wave_black_started": "关键性波动（黑）",
    "key_wave_black_ended": "关键性波动结束",
    "top_plus_black": "顶部+黑色",
    "top_plus_black_ended": "顶部+黑色结束",
    "higher_low_bottom": "更高低点底部",
    "double_bottom": "双底",
    "bullish_reversal_bottom": "反转底部",
    "top_structure": "顶部结构",
    "top_warning_invalidated_by_new_high": "新高解除顶部警告",
    "swing_pivots": "摆动点",
    "volume_proxies": "量能",
    "bottom_c_lifecycle": "C 点生命周期",
    "bullish_engulfing": "看涨吞没",
    "bullish_outside_reversal": "看涨外包反转",
    "bearish_engulfing": "看跌吞没",
    "bearish_outside_reversal": "看跌外包反转",
}

#: evidence["sub_rule"] → 中文名。ema20_reclaim_rising_<tier> 单独映射。
SUB_RULE_CN: dict[str, str] = {
    "lei_color_green_started": "转绿",
    "lei_color_gray_started": "转灰",
    "lei_color_black_started": "转黑",
    "ema20_reclaim_rising_early_watch": TIER_CN["early_watch"],
    "ema20_reclaim_rising_structure_confirmed": TIER_CN["structure_confirmed"],
    "ema20_reclaim_rising_joint_confirmed": TIER_CN["joint_confirmed"],
    "ema20_reclaim_rising_long_trend_improved": TIER_CN["long_trend_improved"],
    "first_ma_pullback_touched": "首次回撤触碰",
    "first_ma_pullback_confirmed": "首次回撤确认",
    "first_ma_pullback_failed": "首次回撤失败",
    "exit_ema20_costbasis_triggered": "抵扣价退出触发",
    "reward_risk_computed": "盈亏比计算",
    "tradability_evaluated": "可交易性评估",
    "false_breakout_reclaim_short_watch": "假突破做空观察",
    "false_breakout_reclaim_short_confirmed": "假突破做空确认",
    "false_breakout_reclaim_short_failed": "假突破做空失败",
}

SEVERITY_CN: dict[str, str] = {
    "info": "信息",
    "watch": "关注",
    "important": "重要",
    "critical": "关键",
}

DIRECTION_CN: dict[str, str] = {
    "bullish": "偏多",
    "bearish": "偏空",
    "neutral": "中性",
}

CONTEXT_SUMMARY_CN: dict[str, str] = {
    "tailwind": "顺风",
    "neutral": "中性",
    "headwind": "逆风",
    "unknown": "环境未知",
}
