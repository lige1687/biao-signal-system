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
    "dense_breakout": "均线密集区突破",
    "two_b_reversal": "2B/破底翻",
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
    "dense_breakout_watch": "密集区观察",
    "dense_breakout_confirmed": "密集区突破确认",
    "dense_breakout_failed": "密集区突破失败",
    "two_b_reversal_v1_confirmed": "2B·v1确认",
    "two_b_reversal_v2_confirmed": "2B·v2确认",
    "two_b_reversal_v3_confirmed": "2B·v3确认",
    "two_b_reversal_failed": "2B失败",
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


#: 同花顺行业板块代码 -> 中文名（90 个，2026-08 快照）。
THS_INDUSTRY_NAMES: dict[str, str] = {
    "881121": "半导体",
    "881273": "白酒",
    "881131": "白色家电",
    "881156": "保险",
    "881138": "包装印刷",
    "881174": "厨卫电器",
    "881281": "电池",
    "881277": "电机",
    "881145": "电力",
    "881278": "电网设备",
    "881283": "多元金融",
    "881172": "电子化学品",
    "881153": "房地产",
    "881280": "风电设备",
    "881167": "非金属材料",
    "881136": "服装家纺",
    "881135": "纺织制造",
    "881268": "工程机械",
    "881279": "光伏设备",
    "881169": "贵金属",
    "881269": "轨交设备",
    "881148": "港口航运",
    "881149": "公路铁路运输",
    "881112": "钢铁",
    "881122": "光学光电子",
    "881168": "工业金属",
    "881284": "环保设备",
    "881181": "环境治理",
    "881177": "互联网电商",
    "881132": "黑色家电",
    "881264": "化学纤维",
    "881108": "化学原料",
    "881109": "化学制品",
    "881140": "化学制药",
    "881271": "IT服务",
    "881151": "机场航运",
    "881276": "军工电子",
    "881166": "军工装备",
    "881139": "家居用品",
    "881130": "计算机设备",
    "881114": "金属新材料",
    "881178": "教育",
    "881115": "建筑材料",
    "881116": "建筑装饰",
    "881158": "零售",
    "881160": "旅游及酒店",
    "881182": "美容护理",
    "881105": "煤炭开采加工",
    "881159": "贸易",
    "881103": "农产品加工",
    "881263": "农化制品",
    "881267": "能源金属",
    "881128": "汽车服务及其他",
    "881126": "汽车零部件",
    "881125": "汽车整车",
    "881282": "其他电源设备",
    "881123": "其他电子",
    "881179": "其他社会服务",
    "881272": "软件开发",
    "881146": "燃气",
    "881265": "塑料制品",
    "881134": "食品加工制造",
    "881142": "生物制品",
    "881180": "石油加工贸易",
    "881162": "通信服务",
    "881129": "通信设备",
    "881117": "通用设备",
    "881164": "文化传媒",
    "881152": "物流",
    "881124": "消费电子",
    "881173": "小家电",
    "881170": "小金属",
    "881266": "橡胶制品",
    "881270": "元件",
    "881175": "医疗服务",
    "881144": "医疗器械",
    "881133": "饮料制造",
    "881107": "油气开采及服务",
    "881274": "影视院线",
    "881275": "游戏",
    "881155": "银行",
    "881143": "医药商业",
    "881102": "养殖业",
    "881171": "自动化设备",
    "881165": "综合",
    "881157": "证券",
    "881141": "中药",
    "881118": "专用设备",
    "881137": "造纸",
    "881101": "种植业与林业",
}
