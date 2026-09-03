"""信号解释知识库：点击图上标记后右侧面板的内容来源。

结构与 ui/app.py 的 ``TERM_EXPLANATIONS`` 保持一致（title / definition /
formula / usage 四段），并在其基础上补齐**事件规则级**解释——原术语库只覆盖
概念（三色、C 点、B1…），不覆盖 ``higher_low_bottom`` /
``ema20_reclaim_rising_early_watch`` 这类具体规则。

口径纪律
--------
- ``usage`` 一律描述「怎么看」，不写「买/卖」指令；early_watch 必须明确
  「仅观察，不构成买入」。
- ``invalidation`` 描述客观失效条件，与 SignalEvent.invalidation 字段对应。
- ``next_step`` 只描述档位阶梯上的下一个条件，不预测价格。
- 与 LEI 原文口径存在推断成分的，在 ``caveat`` 里标注「研究口径」。
"""
from __future__ import annotations

from typing import TypedDict


class Explanation(TypedDict, total=False):
    title: str
    definition: str
    formula: str
    usage: str
    invalidation: str
    next_step: str
    caveat: str


#: 概念级解释（与 ui/app.py TERM_EXPLANATIONS 同源，逐条对齐后扩展）。
CONCEPTS: dict[str, Explanation] = {
    "signal_color": {
        "title": "绿灰黑三色",
        "definition": "LEI 用 EMA20 和 20 周期抵扣价共同判断当前趋势方向。",
        "formula": "绿色 = 收盘 > EMA20 且 收盘 > 20日前收盘；黑色 = 两者均小于；灰色 = 方向分歧",
        "usage": "绿色=多头状态，黑色=空头状态，灰色=需要关注但不等于卖出。",
    },
    "c_point": {
        "title": "C 点（结构低点 / 失效线）",
        "definition": "底部结构的最低点，也是该结构的止损参考位。",
        "formula": "由摆动点序列中「更高低点」或「双底」等形态确认",
        "usage": "距 C 点的距离是这个结构还剩多少安全垫；跌破即结构死亡。",
        "invalidation": "结构确认后的下一交易日起，最低价触及或跌破 C 即**永久失效**，之后不能复活。",
    },
    "b1": {
        "title": "B1 第一阻力",
        "definition": "信号发生时向前看最近且高于当前价的历史摆动高点。",
        "formula": "在已确认结构之前约 2 年内，取最近一个高于入场价的摆动高点",
        "usage": "参考前高/第一阻力位，不是强制止盈目标，也不是入场门槛。",
        "caveat": "曾把「B1 至少预留 3R」当作入场硬门槛，导致几乎所有信号被过滤，已移除该门槛。",
    },
    "neckline": {
        "title": "顶部颈线",
        "definition": "顶部结构的支撑线，确认后跌破意味着趋势可能反转。",
        "formula": "由「更低高点」序列中两个低点连线确定",
        "usage": "有效顶部颈线确认后，价格在其下方运行属于风险信号。",
        "invalidation": "价格创出新高可解除顶部警告（top_warning_invalidated_by_new_high）。",
    },
    "ref20": {
        "title": "20 周期抵扣价",
        "definition": "约 20 个交易日前进入均线计算、将在当前时点被替换掉的价格。",
        "formula": "close_lag20 = close(t-20)",
        "usage": "当前价高于抵扣价 → MA20 方向向上；低于 → 向下。",
    },
    "bias": {
        "title": "均线乖离率",
        "definition": "最新价相对某条均线的百分比偏离程度；正值在均线上方，负值在下方。",
        "formula": "乖离率 = (最新价 / 均线值 - 1) × 100%",
        "usage": "用于识别价格离短期或长期趋势中枢有多远。绝对值快速放大，代表偏离和回归波动风险上升；但强趋势中高乖离也可能持续。",
        "invalidation": "乖离率没有单独的永久失效线；价格和均线每日变化，指标会动态收敛或扩大。",
        "next_step": "结合均线方向、双均线开口、量能与结构 C 点判断，不能只因乖离率高低做买卖决定。",
        "caveat": "不同品种波动特征不同，不设置跨品种通用的极端阈值。ETF、指数与高波动个股必须分别观察。",
    },
    "atr": {
        "title": "ATR14 波动率",
        "definition": "最近 14 个交易日真实波幅的平均值，再除以最新价得到可比较的百分比波动尺度。",
        "formula": "TR=max(高-低, |高-昨收|, |低-昨收|)；ATR14=近14日TR简单平均；波动率=ATR14/最新价",
        "usage": "数值越高，近期日内波动和价格跳动越大。可用于理解安全垫是否过窄、仓位和容错是否匹配，不判断涨跌方向。",
        "invalidation": "ATR 是滚动波动指标，没有方向性失效条件；随着新交易日加入会持续更新。",
        "caveat": "本系统采用 14 日 TR 简单平均，不是 Wilder 平滑 ATR，口径不能与其他软件直接混用。",
    },
    "ma_spread": {
        "title": "EMA20 / SMA20 双均线开口",
        "definition": "两条 20 日均线之间的距离及其扩张或收窄状态。",
        "formula": "开口 = |EMA20-SMA20| / 最新价 × 100%",
        "usage": "EMA20 在 SMA20 上方且开口扩张，通常表示短期动能增强；EMA20 在下方且开口扩张，表示弱势加速；开口收窄说明分歧减弱或趋势动能衰减。",
        "invalidation": "开口不是独立结构，不存在永久失效；均线位置反转或开口由扩张转收窄即代表状态改变。",
        "next_step": "结合价格是否站上两线、两线斜率及结构确认判断，不把开口扩张单独视作入场信号。",
    },
    "key_volatility": {
        "title": "关键性波动",
        "definition": "颜色从非绿→绿或非黑→黑的转换日，标志动能方向变化。",
        "formula": "color_changed == True 且 signal_color ∈ {green, black}",
        "usage": "绿色关键波动=动能转强；黑色关键波动=动能转弱，是较早的退出参考。",
    },
    "stage": {
        "title": "机会阶段",
        "definition": "从「无线索」到「趋势增强」的递进，反映结构确认程度。",
        "formula": "no_clue → bottom_watch → structure_confirmed → early_strength → joint_confirmed → trend_reinforced",
        "usage": "阶段越高，结构确认越充分；early_watch 只是观察，不构成买入。",
    },
    "volume_state": {
        "title": "量能分级",
        "definition": "根据当日成交量与 20 日均量的比值分四级。",
        "formula": "≥2x=放量，1.2-2x=温和，0.8-1.2x=正常，<0.8x=缩量",
        "usage": "放量突破更可信；缩量上涨需警惕；放量下跌偏空。",
        "caveat": "量能目前是辅助证据与研究代理，不作为硬过滤器。",
    },
    "risk_state": {
        "title": "风险状态",
        "definition": "与机会阶段分离的独立维度，描述当前的风险层级。",
        "formula": "normal → gray_watch → active_top → black → top_plus_black → c_invalidated",
        "usage": "风险状态升高不等于机会阶段被抹掉；两者独立记录，便于分辨「结构还在但当前有风险」。",
    },
    "lifecycle": {
        "title": "生命周期",
        "definition": "同一底部结构从候选、观察、确认到失效的完整过程，用 lifecycle_id 串联。",
        "formula": "候选+EMA20早期转强 → early_watch → 结构确认 → 双均线共同确认 → 长周期改善",
        "usage": "同一结构后续升级沿用同一生命周期，不要求重新出现交叉——这是避免错失主升浪前半段的关键。",
        "invalidation": "转黑结束本轮强势生命周期（结构本身仍存活）；触及 C 则结构永久终止。",
    },
    "long_trend": {
        "title": "日线 / 周线长周期趋势",
        "definition": "基于 EMA60 与 EMA120 的相对位置、斜率和开口变化，描述更慢一级的趋势背景。",
        "formula": "稳定多头：EMA60>EMA120 且两线不下降；改善中：至少一线上升且 EMA60-EMA120 向多头方向改善；反之为恶化或空头",
        "usage": "日线反应更快，周线更慢、更稳。长周期只作为背景权重和档位升级条件，不会删除已经发生的底部、EMA20 或量能事实。",
        "invalidation": "长周期状态随 EMA60/EMA120 的位置、斜率或开口变化而切换；不是永久结构。",
        "caveat": "周线严格只使用已完成周线；不足 120 根周线时显示数据不足，不用短周期 EMA 冒充。",
    },
}

#: 结构类型级解释（点击图上菱形标记）。
STRUCTURES: dict[str, Explanation] = {
    "higher_low_bottom": {
        "title": "更高低点底部",
        "definition": "摆动低点逐个抬高形成的底部结构，是最基础的反转结构形态。",
        "formula": "确认的摆动低点序列中出现「后一个低点高于前一个低点」",
        "usage": "结构确认后即具备参考意义；用 C 点作为失效线衡量还剩多少安全垫。",
        "invalidation": "最低价触及或跌破 C 点 → 永久失效，不能复活。",
        "next_step": "等待 EMA20 早期转强 → 双均线共同确认 → 长周期改善，逐级升级同一生命周期。",
    },
    "double_bottom": {
        "title": "双底",
        "definition": "两个相近低点 + 中间反弹高点（颈线）构成的经典反转结构。",
        "formula": "两个摆动低点价格接近，中间高点作为颈线",
        "usage": "突破颈线（尤其放量突破）是结构生效的重要证据。",
        "invalidation": "最低价触及或跌破 C 点 → 永久失效。",
        "next_step": "等待放量突破颈线与双均线共同确认。",
    },
    "bullish_reversal_bottom": {
        "title": "反转底部",
        "definition": "由看涨吞没 / 外包反转等单根或两根 K 线反转形态直接确立的底部。",
        "formula": "阳线实体反包前一根阴线（允许极端行情中第二根阳线直接反包）",
        "usage": "确认更快但样本质量参差，需结合量能与后续均线表现共同判断。",
        "invalidation": "最低价触及或跌破 C 点 → 永久失效。",
        "caveat": "「底部不是固定长相」——该口径包含研究推断成分。",
    },
    "top_structure": {
        "title": "顶部结构",
        "definition": "摆动高点逐个降低形成的顶部，用于判断趋势可能结束。",
        "formula": "确认的摆动高点序列出现「更低高点」，两低点连线为颈线",
        "usage": "与黑色状态组合成 Top+Black，是比单纯关键性波动更晚、更保留右尾收益的退出参考。",
        "invalidation": "价格创出新高 → 顶部警告解除。",
    },
}

#: 事件规则级解释（点击事件或图上标记时按 rule_id / sub_rule 查找）。
RULES: dict[str, Explanation] = {
    "lei_color_green_started": {
        "title": "转绿（关键性波动）",
        "definition": "颜色由非绿转为绿色的当日，代表动能转强。",
        "formula": "收盘 > EMA20 且 收盘 > 20日前收盘，且前一日不满足",
        "usage": "动能转强的早期提示；需与结构、量能共同判断，单独一根不等于买入。",
    },
    "lei_color_gray_started": {
        "title": "转灰",
        "definition": "颜色进入灰色，表示原趋势动能减弱或处于过渡/转折状态。",
        "formula": "EMA20 与抵扣价方向分歧",
        "usage": "**灰色不等于卖出**，是需要提高关注度的过渡状态。",
    },
    "lei_color_black_started": {
        "title": "转黑（关键性波动）",
        "definition": "颜色转为黑色，代表进入空头/风险规避状态。",
        "formula": "收盘 < EMA20 且 收盘 < 20日前收盘",
        "usage": "较早的退出参考。转黑会结束本轮强势生命周期，但**不会**自动销毁底部结构。",
    },
    "ema20_reclaim_rising_early_watch": {
        "title": "EMA20 早期转强 · 候选观察档",
        "definition": "已出现 EMA20 早期转强，但所绑定的底部结构尚未确认。",
        "formula": "收盘重新站上 EMA20 且 EMA20 向上，绑定到某个候选底部结构",
        "usage": "**仅作观察，不构成买入信号，也不抬升机会阶段。**",
        "next_step": "等待同一结构被确认 → 升级为「结构确认档」。",
    },
    "ema20_reclaim_rising_structure_confirmed": {
        "title": "EMA20 早期转强 · 结构确认档",
        "definition": "同一底部结构已确认，转强发生在已确认结构之上。",
        "formula": "结构确认 + EMA20 重新站上且向上",
        "usage": "具备买入参考意义（参考，非指令）；风险用该结构的 C 点衡量。",
        "next_step": "等待双均线共同向上 → 升级为「共同确认档」。",
    },
    "ema20_reclaim_rising_joint_confirmed": {
        "title": "EMA20 早期转强 · 共同确认档",
        "definition": "EMA20 与 SMA20 当前共同向上，沿用同一观察实例的升级。",
        "formula": "EMA20 与 SMA20 同时向上且收盘站上两者",
        "usage": "历史回测中共同确认版胜率与跨窗口稳定性更好，但入场更晚会牺牲部分 R 空间。",
        "next_step": "等待长周期支持/改善 → 升级为「长周期改善档」。",
    },
    "ema20_reclaim_rising_long_trend_improved": {
        "title": "EMA20 早期转强 · 长周期改善档",
        "definition": "日线或周线长周期（EMA60/EMA120）转为支持或改善，已是最高档。",
        "formula": "共同确认 + 日线或周线长趋势 supportive/improving",
        "usage": "最高档位；长周期顺风时同类信号的历史表现更好。",
        "next_step": "已是最高档；继续观察：触及 C → 永久失效；转黑 → 关闭本条转强。",
    },
    "first_ma_pullback": {
        "title": "均线回撤（模块 A，研究代理）",
        "definition": "时钟二类稳定上涨 + 双组多头排列 + 周线多头环境中，价格回撤至 SMA20/60/120 组附近的前向状态机（V2 重写版）。",
        "formula": "A1 门禁 → 武装（站上均线）→ A2 触碰（Low≤SMA_N+1×ATR20 且 SMA 仍上行）→ A3 结构（底部构造或 EMA20 收复）→ A4 入场（早期/确认两版）→ A5 结构低点失效",
        "usage": "用于把趋势中继回撤转成可解释、可回测的条件化场景；首次/非首次分别统计。",
        "invalidation": "收盘跌破本轮回撤结构低点，或趋势生命周期重置（排列破坏/跌破SMA120/转黑）。",
        "caveat": "研究代理：模块 A 的 V2 量化（规格 §9），不冒充 LEI 原始规则。",
    },
    "first_ma_pullback_touched": {
        "title": "均线回撤 · 触碰观察",
        "definition": "回撤价格第一次（或后续）返回 SMA20/60/120 触碰带（Low≤SMA_N+1×ATR(20)）。",
        "formula": "时钟二类 + 多头排列 + 周线环境 + close>close_lag_N（该 SMA 仍上行）+ Low 进入触碰带",
        "usage": "这是等待 A3/A4 的观察状态，不是入场指令。",
        "invalidation": "收盘跌破本轮回撤结构低点，或价格离开回撤区未触发入场。",
        "next_step": "等待 A3（底部构造或 EMA20 收复）与 A4（站上 EMA20 且 EMA20 上行）。",
        "caveat": "研究代理：触碰深度允许击穿均线，深度由 A5 结构失效兜底。",
    },
    "first_ma_pullback_confirmed": {
        "title": "均线回撤 · 入场信号",
        "definition": "回撤后满足 A3 结构条件并触发 A4 入场（早期版/确认版分别出事件）。",
        "formula": "早期版=close>EMA20 且 EMA20 上行；确认版=再加 SMA20 上行（close>close_lag20）；A3=底部构造或 EMA20 收复",
        "usage": "信号收盘生成、下一根开盘入场；回测按 A6 三版退出分别统计。",
        "invalidation": "收盘跌破本轮回撤结构低点（stop_price），A/C 不得漂移（规格 §14）。",
        "next_step": "以结构低点为失效价管理；目标 B 与盈亏比由 reward_risk_filter 计算。",
        "caveat": "研究代理；早期/确认两版与首次/非首次必须分开统计表现。",
    },
    "first_ma_pullback_failed": {
        "title": "均线回撤 · 失败",
        "definition": "本轮回撤周期结束：结构低点被破坏、价格离开回撤区未触发入场，或趋势生命周期重置。",
        "formula": "close 跌破回撤此前全部 low，或 close 回到触碰带上方而未入场，或排列破坏/跌破SMA120/转黑",
        "usage": "等待重新武装后的下一轮触碰；新趋势生命周期会重新产生“首次”。",
        "invalidation": "失败事件是历史事实，不会被后续上涨改写。",
        "caveat": "研究代理；失败不等于无条件卖出，只表示本轮回撤预期未被确认。",
    },
    "false_breakout_reclaim": {
        "title": "假突破快速收回（研究代理）",
        "definition": "突破前高/结构颈线后被打回（盘中刺穿参考位），但在确认窗口内快速收回且不破坏趋势的前向状态机。",
        "formula": "参考位=此前 N 根最高 high → 收盘突破 → 被打回 → 窗口内收回且排列保持",
        "usage": "把“洗盘后延续”转成可解释、可回测的条件化做多场景，不输出无条件买入指令。",
        "invalidation": "收盘真跌破参考位、完整多头排列破坏、转黑或确认窗口耗尽。",
        "caveat": "研究代理：源自用户交易笔记，以日线 OHLC 判定，不冒充 LEI 原始规则。",
    },
    "false_breakout_reclaim_watch": {
        "title": "假突破快速收回 · 被打回观察",
        "definition": "有效突破前高/结构位后，盘中刺穿参考位（被打回），等待窗口内重新收回。",
        "formula": "突破后 Low<=参考位 即标记被打回；随后窗口内 Close>=参考位 且排列保持=确认",
        "usage": "这是等待收回的观察状态，不是入场指令；重点看参考位得失与完整多头排列。",
        "invalidation": "确认窗口耗尽、收盘真跌破参考位或完整多头趋势破坏。",
        "next_step": "等待最多 3 根已完成日 K 内重新站回参考位上方且趋势保持。",
        "caveat": "研究代理；以日线 OHLC 判定，不冒充 LEI 原始规则。",
    },
    "false_breakout_reclaim_confirmed": {
        "title": "假突破快速收回 · 条件确认",
        "definition": "被打回后，在确认窗口内重新站回参考位上方，且完整多头趋势仍成立。",
        "formula": "被打回后 Close>=参考位 + 完整多头排列保持 +（require_green 时绿色）",
        "usage": "可作为趋势延续的条件化做多参考；历史表现按事件独立统计、分笔回测。",
        "invalidation": "收盘真跌破参考位、完整多头排列破坏或转黑。",
        "next_step": "结合市场环境、结构与首次回撤管理风险，决定是否继续观察。",
        "caveat": "研究代理；每次确认是独立事件研究样本，不等于单账户可同时执行。",
    },
    "false_breakout_reclaim_failed": {
        "title": "假突破快速收回 · 失败",
        "definition": "本轮突破已消耗，但确认条件未成立（真跌破或窗口耗尽）。",
        "formula": "收盘真跌破参考位，或确认窗口耗尽仍未收回",
        "usage": "本轮突破不再把后续波动冒充‘快速收回’；等待下一次有效突破。",
        "invalidation": "失败事件是历史事实，不会被后续上涨改写。",
        "next_step": "出场/放弃本轮；等待新的有效突破重新开始计数。",
        "caveat": "研究代理；失败不等于无条件卖出，只表示假突破收回未被确认。",
    },
    "dense_breakout": {
        "title": "均线密集区突破（研究代理）",
        "definition": "横盘密集区（六线纠缠压缩）形成后，价格收盘突破密集区上沿且完整多头排列成立的前向状态机。",
        "formula": "横盘识别(复用tradability_gate纠缠度) -> 收盘突破近N根最高high + 完整多头排列 -> 跌回上沿下方+SMA20下弯失效",
        "usage": "把“横盘后标志性突破”转成可解释、可回测的条件化做多场景，不输出无条件买入指令。",
        "invalidation": "确认后收盘跌回密集区上沿下方且 SMA20 方向向下弯曲，或完整多头排列破坏、转黑。",
        "caveat": "研究代理：源自规格 §9 模块 B，横盘阈值复用 tradability_gate（V2 §17 已定（原则）：2%/126 交易日），不冒充 LEI 原始规则。",
    },
    "dense_breakout_watch": {
        "title": "密集区突破 · 横盘观察",
        "definition": "六线纠缠压缩至 cluster_threshold 内并持续，横盘密集区成立，等待标志性突破动作。",
        "formula": "entanglement<=cluster_threshold 且近 entanglement_lookback 日均纠缠<=cluster_threshold*1.5 且 position>=minimum_consolidation_bars",
        "usage": "观察状态，不是入场指令；横盘阶段不频繁交易，只等待价格收盘突破密集区上沿。",
        "invalidation": "密集区连续 entanglement_lookback 日消散（静默结束），或突破后跌回失效。",
        "next_step": "等待收盘突破密集区上沿且完整多头排列成立。",
        "caveat": "研究代理；横盘阈值已定（原则，V2 §17）：纠缠 2%、126 交易日；V2 时钟三类门禁（pending_v2）落地后切换口径。",
    },
    "dense_breakout_confirmed": {
        "title": "密集区突破 · 条件确认",
        "definition": "收盘突破密集区上沿，且完整多头排列成立（SMA20>SMA60>SMA120 且三线方向向上）。",
        "formula": "close > reference(近breakout_lookback根最高high) + SMA20>SMA60>SMA120 且三线斜率均>0",
        "usage": "可作为横盘突破的条件化做多参考；信号收盘后生成，下一根开盘入场。每个密集区生命周期只确认一次。",
        "invalidation": "收盘跌回密集区上沿下方且 SMA20 方向向下弯曲，或完整多头排列破坏、转黑。",
        "next_step": "结合市场环境、结构与盈亏比管理风险，决定是否继续观察。",
        "caveat": "研究代理；每次确认是独立事件研究样本，不等于单账户可同时执行。",
    },
    "dense_breakout_failed": {
        "title": "密集区突破 · 失败",
        "definition": "确认后收盘跌回密集区上沿下方，同时 SMA20 方向向下弯曲，突破逻辑失效。",
        "formula": "close < breakout_reference 且 sma20_slope < 0",
        "usage": "本轮突破失效；等待新的密集区生命周期重新开始。",
        "invalidation": "失败事件是历史事实，不会被后续上涨改写。",
        "next_step": "出场/放弃本轮；等待新的横盘密集区形成。",
        "caveat": "研究代理；失败不等于无条件卖出，只表示突破逻辑已被否决。",
    },
    "two_b_reversal": {
        "title": "2B/破底翻反转（研究代理）",
        "definition": "L2（更低确认低点）/L1（更高确认低点）结构中，价格跌破 L1 后快速收回其上方的前向状态机，分三版本入场。",
        "formula": "L2/L1确认摆动低点+颈线 -> 跌破L1(不破L2) -> two_b_reclaim_bars根内收回L1 -> v1/v2/v3确认 -> 跌破L2失效",
        "usage": "把“破底翻”转成可解释、可回测的条件化做多场景，不输出无条件买入指令。三版本分别统计。",
        "invalidation": "收盘跌破 L2（结构最低点），2B 彻底失效；或快速收复窗口耗尽。",
        "caveat": "研究代理：V2 规格 §9 C1 已填实结构定义（L1=前低，跌破创新低 L2），代码仍为 v1 L1/L2 口径（pending_v2 重写排期）；two_b_reclaim_bars=5〔标定 V2.1，待彪哥确认〕，不冒充 LEI 原始规则。",
    },
    "two_b_reversal_v1_confirmed": {
        "title": "2B/破底翻 · v1 确认",
        "definition": "跌破 L1 后在快速收复窗口内收盘重新站上 L1，v1 当日确认。",
        "formula": "breakdown(close<L1, close>L2) 后 two_b_reclaim_bars 根内 close>=L1",
        "usage": "三版本中最激进入场；信号在站上当日生成，下一根开盘入场。L2 为结构失效线。",
        "invalidation": "收盘跌破 L2，2B 结构彻底失效。",
        "next_step": "结合 v2/v3 与市场环境管理风险；跌破 L2 即失效。",
        "caveat": "研究代理；每次确认是独立事件研究样本。",
    },
    "two_b_reversal_v2_confirmed": {
        "title": "2B/破底翻 · v2 确认",
        "definition": "收回 L1 后，EMA20 拐头向上（复用 ema20_reclaim_state）。",
        "formula": "reclaim + EMA20 重新站上且向上（前日 Close<=前日EMA20，当日 Close>EMA20 且 EMA20 上升）",
        "usage": "比 v1 多一层 EMA20 转强确认，入场更晚但过滤更严。可在收回当日或之后触发。",
        "invalidation": "收盘跌破 L2，2B 结构彻底失效。",
        "next_step": "结合 v3 与市场环境管理风险；跌破 L2 即失效。",
        "caveat": "研究代理；EMA20 转强口径复用 dual_ma，不冒充 LEI 原始规则。",
    },
    "two_b_reversal_v3_confirmed": {
        "title": "2B/破底翻 · v3 确认",
        "definition": "收回 L1 后，EMA20 与 SMA20 共同向上（复用 dual_ma_bull_state）。",
        "formula": "reclaim + Close>EMA20 且 Close>SMA20 且两线向上 且 颜色为绿",
        "usage": "三版本中最保守入场；双均线共同确认，入场最晚但确认最强。",
        "invalidation": "收盘跌破 L2，2B 结构彻底失效。",
        "next_step": "已是最强确认；继续管理 L2 失效线与顶部风险。",
        "caveat": "研究代理；双均线确认口径复用 dual_ma，不冒充 LEI 原始规则。",
    },
    "two_b_reversal_failed": {
        "title": "2B/破底翻 · 失败",
        "definition": "2B 结构失效：收盘跌破 L2（结构彻底失效），或快速收复窗口耗尽未收回 L1。",
        "formula": "close<L2（C3 失效），或跌破 L1 后 two_b_reclaim_bars 根内未收回（窗口耗尽）",
        "usage": "本轮 2B 不再把后续波动冒充‘破底翻’；等待新的 L1/L2 结构。",
        "invalidation": "失败事件是历史事实，不会被后续上涨改写。",
        "next_step": "出场/放弃本轮；等待新的 L1/L2 结构形成。",
        "caveat": "研究代理；失败不等于无条件卖出，只表示 2B 逻辑已被否决。",
    },
    "low_level_confirmation": {
        "title": "次级别确认（日线代理，研究代理）",
        "definition": "日线做多信号触发后，用更低级别确认增强可信度的前向状态机；当前以日线 OHLC 代理 60 分钟。",
        "formula": "日线做多信号 → 窗口内出现盘中刺穿参考支撑后收回，或反转 K 线",
        "usage": "把“日线信号获次级别确认”转成条件化场景；不输出无条件买入指令。",
        "invalidation": "日线做多信号失效（排列/双均线共同确认不再成立）或收盘跌破参考支撑。",
        "caveat": "研究代理：日线 OHLC 代理，系统未接入真 60 分钟数据，不冒充 LEI 原始规则。",
    },
    "low_level_confirmation_watch": {
        "title": "次级别确认 · 等待（日线代理）",
        "definition": "日线做多信号已触发，等待次级别确认特征（盘中收回或反转 K 线）。",
        "formula": "触发后窗口内 Low<=参考支撑*(1+tol) 且 Close>=参考支撑，或 bullish_engulfing/outside_reversal",
        "usage": "观察状态，不是入场指令；重点看参考支撑得失与反转 K 线。",
        "invalidation": "窗口耗尽、日线做多信号失效或收盘跌破参考支撑。",
        "next_step": "等待最多 2 根已完成日 K 内出现盘中收回或反转 K 线。",
        "caveat": "研究代理；日线代理，未接 60 分钟。",
    },
    "low_level_confirmation_confirmed": {
        "title": "次级别确认 · 已确认（日线代理）",
        "definition": "日线做多信号触发后，窗口内出现次级别确认特征，增强信号可信度。",
        "formula": "窗口内出现盘中刺穿后收回，或反转 K 线，且收盘仍在参考支撑上方",
        "usage": "可作为日线信号增强的条件化做多参考；历史表现按事件独立统计。",
        "invalidation": "日线做多信号失效或收盘跌破参考支撑。",
        "next_step": "结合市场环境与结构管理风险，决定是否继续观察。",
        "caveat": "研究代理；日线代理，未接 60 分钟；每次确认是独立事件样本。",
    },
    "ma_full_alignment": {
        "title": "完整均线排列 + EMA 斜率加速度（研究代理）",
        "definition": "把 20/60/120 完整多头/空头排列作为场景卡底层确认维度，并用 EMA20 斜率与加速度标准化描述动能。",
        "formula": "多头排列=SMA20>SMA60>SMA120 且三线方向向上；空头反之；EMA20 斜率/加速度=相邻斜率差",
        "usage": "排列提供方向背景，斜率/加速度描述动能变化；均为确认维度，不单独产生买卖指令。",
        "invalidation": "均线相对位置或方向不再满足完整排列（多头/空头）。",
        "caveat": "研究代理：源自用户交易笔记，斜率/加速度为标准化代理指标，不冒充 LEI 原始规则。",
    },
    "ma_alignment_bullish_start": {
        "title": "完整多头排列 · 成立",
        "definition": "SMA20>SMA60>SMA120 且三条 SMA 方向均向上，完整多头排列成立。",
        "formula": "SMA20>SMA60>SMA120 且 SMA20/60/120 斜率均 > 0",
        "usage": "作为做多场景卡的底层确认维度；本身是状态型事件，有起止。",
        "invalidation": "任意均线方向或相对位置不再满足完整多头排列。",
        "next_step": "排列保持期间，结合颜色、结构与回撤管理做多风险。",
        "caveat": "研究代理；不单独决定买卖，只作确认背景。",
    },
    "ma_alignment_bearish_start": {
        "title": "完整空头排列 · 成立",
        "definition": "SMA20<SMA60<SMA120 且三条 SMA 方向均向下，完整空头排列成立。",
        "formula": "SMA20<SMA60<SMA120 且 SMA20/60/120 斜率均 < 0",
        "usage": "作为做空场景卡的底层确认维度；本身是状态型事件，有起止。",
        "invalidation": "任意均线方向或相对位置不再满足完整空头排列。",
        "next_step": "排列保持期间，结合颜色、结构与反弹管理做空风险。",
        "caveat": "研究代理；不单独决定买卖，只作确认背景。",
    },
    "ma_alignment_broken": {
        "title": "完整均线排列 · 破坏",
        "definition": "原完整排列不再满足（均线方向或相对位置破坏）。",
        "formula": "非排列 -> 排列 切换为成立；排列 -> 非排列 切换为破坏",
        "usage": "排列破坏后，原方向背景失效；等待重新形成排列。",
        "invalidation": "破坏是历史事实，不会被后续波动改写。",
        "next_step": "原排列背景失效；重新观察排列重建。",
        "caveat": "研究代理；破坏只表示排列状态结束。",
    },
    "dual_ma_bull_confirmed": {
        "title": "双均线共同确认",
        "definition": "EMA20 与 SMA20 同时向上，收盘站上两者。",
        "formula": "close > EMA20 且 close > SMA20 且两者斜率向上",
        "usage": "比单看 EMA20 更稳的确认层次；本身是状态型事件，有起止。",
    },
    "dual_ma_spread": {
        "title": "双均线张口",
        "definition": "EMA20 与 SMA20 之间开口的扩张或收窄。",
        "formula": "|EMA20 - SMA20| 的连续变化方向",
        "usage": "辅助信号：开口扩张=动能加强，收窄=动能衰减。",
    },
    "key_wave_black_started": {
        "title": "关键性波动（黑）开始",
        "definition": "进入黑色关键性波动状态，是较早的退出条件。",
        "formula": "颜色转黑并满足关键性波动规则",
        "usage": "Confirm-Key 版本用它退出：通常更早离场，允许较快重入。",
    },
    "key_wave_black_ended": {
        "title": "关键性波动（黑）结束",
        "definition": "黑色关键性波动状态结束。",
        "formula": "颜色脱离黑色状态",
        "usage": "标志上一轮风险状态收束，可重新评估机会。",
    },
    "top_plus_black": {
        "title": "顶部 + 黑色（Top+Black）",
        "definition": "有效顶部结构与黑色状态同时成立的组合风险状态。",
        "formula": "存在有效顶部警报 且 当前为黑色",
        "usage": "Confirm-TopBlack 版本用它退出：比 Key 版更晚，目标是保留大趋势右尾收益。",
        "caveat": "回测显示 Top+Black 平均改善 +0.156R，但中位数为负、逐笔占优仅约 37%，并非普遍更优。",
    },
    "top_plus_black_ended": {
        "title": "顶部 + 黑色结束",
        "definition": "Top+Black 组合状态结束。",
        "formula": "顶部警报解除或脱离黑色",
        "usage": "该轮组合风险收束。",
    },
    "top_warning_invalidated_by_new_high": {
        "title": "新高解除顶部警告",
        "definition": "价格创出新高，原顶部结构的警告被客观解除。",
        "formula": "收盘/最高价突破顶部结构的参考高点",
        "usage": "说明此前的顶部判断被市场否决，风险层级下降。",
    },
    "long_trend": {
        "title": "长周期趋势",
        "definition": "基于 EMA60/EMA120 的长周期状态（多头/空头/改善/恶化）。",
        "formula": "EMA60 与 EMA120 的相对位置与斜率",
        "usage": "作为背景权重推动档位升级，**不删除**已发生的 EMA20、底部或量能事实。",
    },
    "volume_proxies": {
        "title": "量能代理",
        "definition": "放量突破、回调缩量等基于滚动均量的简化量能判断。",
        "formula": "当日量 / 20日均量 的分级，以及近 N 日均量对比",
        "usage": "辅助证据，用于判断突破可信度与承接强度。",
        "caveat": "研究代理口径，尚未验证其增量价值，不作硬过滤器。",
    },
    "swing_pivots": {
        "title": "摆动点",
        "definition": "经三左三右确认的局部高点或低点，是所有结构的构造基础。",
        "formula": "左右各 3 根 K 线均不越过该极值，于第 3 根后确认",
        "usage": "注意拐点日与确认日不同；研究统计一律使用确认日（available_date）。",
    },
    "bottom_c_lifecycle": {
        "title": "C 点生命周期事件",
        "definition": "底部结构因价格触及 C 点而永久失效的记录。",
        "formula": "确认后的下一交易日起，最低价 ≤ C",
        "usage": "结构死亡的客观记录；该结构之后不能复活。",
    },
    "bullish_engulfing": {
        "title": "看涨吞没",
        "definition": "阳线实体完全包住前一根阴线实体。",
        "formula": "open < prev_close 且 close > prev_open",
        "usage": "单根反转形态，可作为反转底部的构造来源之一。",
    },
    "bullish_outside_reversal": {
        "title": "看涨外包反转",
        "definition": "当日高低点完全包住前一日，且收阳。",
        "formula": "high > prev_high 且 low < prev_low 且 close > open",
        "usage": "比吞没更强的反转形态。",
    },
    "bearish_engulfing": {
        "title": "看跌吞没",
        "definition": "阴线实体完全包住前一根阳线实体。",
        "formula": "open > prev_close 且 close < prev_open",
        "usage": "偏空的单根反转形态。",
    },
    "bearish_outside_reversal": {
        "title": "看跌外包反转",
        "definition": "当日高低点完全包住前一日，且收阴。",
        "formula": "high > prev_high 且 low < prev_low 且 close < open",
        "usage": "偏空的强反转形态。",
    },
    "exit_ema20_costbasis": {
        "title": "抵扣价退出（研究代理）",
        "definition": "持仓期间收盘同时跌破 EMA20 与 20 日抵扣价（20 周期前收盘）即触发退出，对应规格 A6①。",
        "formula": "Close < EMA20 且 Close < close_lag20；条件由不成立转成立的当日触发（上升沿）",
        "usage": "持仓退出参考，不是自动卖出指令；信号收盘后生成，下一交易日开盘执行。该条件与 LEI 黑色定义同构，但作为独立退出规则单独统计。",
        "invalidation": "退出触发为单次事件，不因后续价格回升而回溯改写。",
        "caveat": "研究代理：源自规格 A6①，break_basis=close 已定（拍板，V2 §17），不冒充 LEI 原始规则。",
    },
    "exit_ema20_costbasis_triggered": {
        "title": "抵扣价退出 · 触发",
        "definition": "收盘同时跌破 EMA20 与 20 日抵扣价，触发 A6① 退出。",
        "formula": "Close < EMA20 且 Close < close_lag20（上升沿触发）",
        "usage": "当日收盘后成立即记为退出触发日，下一交易日开盘退出；与顶部+关键波动、结构止损并列作为模块 A 的三种退出方式分别回测。",
        "invalidation": "单次触发事件，不会被后续行情改写。",
        "caveat": "研究代理；与黑色定义同构，但独立成事件以便单独统计退出表现。",
    },
    "reward_risk": {
        "title": "盈亏比（研究代理，只算不强制）",
        "definition": "入场前用信号时已存在的目标 B 计算盈亏比 R/R = (B - 入场价) / (入场价 - 失效价)。",
        "formula": "目标B优先级：已确认摆动高点 > 筹码峰VAH/POC > 区间另一侧高点；无法确定时标“目标不可计算”",
        "usage": "只计算展示，不做硬过滤。规格参考：R/R>3 比较理想，作者案例倾向 5 以上；R/R<3 时规格建议放弃，但本系统只标注不拦截。",
        "invalidation": "R/R 随入场价/失效价/目标变化而重算；目标 B 只用信号时已确认数据，不得事后选最优目标。",
        "caveat": "研究代理：缺口与均线密集区两档目标尚未实现（V2 §15 第四轮排期，gap_events pending_v2）；rr_min=3 已定（原则，V2 §17），range_lookback 待确认。",
    },
    "reward_risk_filter": {
        "title": "盈亏比计算（研究代理）",
        "definition": "规格第 10 节的盈亏比过滤的研究代理量化，只算不强制。",
        "formula": "R/R=(B-A)/(A-S)，目标B按摆动高点>筹码峰>区间另一侧优先级取，无目标则“目标不可计算”",
        "usage": "回测分别看 R/R≥3 与 R/R≥5 两组表现；界面展示每笔入场的 R/R 与目标来源。",
        "caveat": "研究代理：源自规格第 10 节，只算不强制，不冒充 LEI 原始规则。",
    },
    "reward_risk_computed": {
        "title": "盈亏比 · 计算结果",
        "definition": "单笔入场信号的盈亏比计算结果（研究代理，只算不强制）。",
        "formula": "R/R=(B-A)/(A-S)；目标不可计算或风险非正时记为不可计算",
        "usage": "附在买点卡上展示；R/R≥3 较理想，≥5 更佳，但本系统只标注不拦截。",
        "caveat": "研究代理；不向主事件日志写事件，避免污染只追加日志的计数不变量。",
    },
    "tradability": {
        "title": "可交易性门禁（研究代理）",
        "definition": "规格第 13 节 9 条无交易条件 + 第 2.2 节趋势类型分类的横切层。",
        "formula": "趋势类型=均线纠缠度+ATR分位+斜率分 横盘反复/横盘末期/趋势/加速衰竭；9条无交易条件逐条检查",
        "usage": "环境层阻断条件不成立才可交易；只算展示不做硬拦截。入场时条件（模块/入场目标失效/盈亏比）结合信号判断。",
        "invalidation": "随行情每日重算；不向主事件日志写每日事件，由界面读取当前状态。",
        "caveat": "研究代理：cluster_threshold=2% / minimum_consolidation_bars=126 已定（原则，V2 §17）；acceleration/bias 为 v1 判据，V2 时钟五类 s60 口径 pending_v2；多周期(条件7)用日线颜色翻转代理，60min 未接入。",
    },
    "tradability_gate": {
        "title": "可交易性门禁（研究代理）",
        "definition": "规格第 13 节无交易条件 + 第 2.2 节趋势类型分类的研究代理量化。",
        "formula": "纠缠度+ATR分位+斜率 分类；9条无交易条件逐条；环境层阻断=1/5/6/7/8",
        "usage": "输出可交易性状态 + 阻断原因清单，接入评估横切层。",
        "caveat": "研究代理：参数待确认，不冒充 LEI 原始规则。",
    },
    "tradability_evaluated": {
        "title": "可交易性 · 评估结果",
        "definition": "当日可交易性评估结果（趋势类型 + 9 条无交易条件）。",
        "formula": "tradable = 环境层阻断条件均不成立",
        "usage": "界面展示当前是否可交易及阻断原因；只算不强制。",
        "caveat": "研究代理；不写每日事件，避免污染事件日志。",
    },
    "false_breakout_reclaim_short_watch": {
        "title": "假突破做空镜像 · 观察",
        "definition": "价格向上突破压力位后被打回，等待 SMA20 下行 + 空头排列确认做空（模块 D2 骨架）。",
        "formula": "突破压力位 -> 收盘拉回压力位下方 -> sma20_slope<0 + 完整空头排列 = 确认做空",
        "usage": "做空方向的条件化场景骨架；direction=short。跌用绿色（A股惯例）。",
        "invalidation": "重新强势站上压力位、空头排列破坏、SMA20 重新上行，或窗口耗尽。",
        "caveat": "研究代理·骨架：做空镜像接口，参数沿用做多侧默认值待确认，不冒充作者做空标准。",
    },
    "false_breakout_reclaim_short_confirmed": {
        "title": "假突破做空镜像 · 确认",
        "definition": "突破压力位后拉回，SMA20 方向下行且完整空头排列成立，确认为做空参考。",
        "formula": "拉回压力位下方 + sma20_slope<0 + SMA20<SMA60<SMA120",
        "usage": "做空方向条件化参考；与做多侧对称、分桶统计，不在同一笔交易中改写理由。",
        "invalidation": "重新站上压力位、空头排列破坏或 SMA20 重新上行。",
        "caveat": "研究代理·骨架；direction=short，待确认参数，不冒充 LEI 原始规则。",
    },
    "false_breakout_reclaim_short_failed": {
        "title": "假突破做空镜像 · 失败",
        "definition": "本轮突破已消耗，但做空确认未成立（重新强势站上压力位或窗口耗尽）。",
        "formula": "收盘重新强势站上压力位，或确认窗口耗尽",
        "usage": "本轮不再把后续波动冒充做空镜像；等待下一次有效突破。",
        "invalidation": "失败事件是历史事实，不被后续上涨改写。",
        "caveat": "研究代理·骨架；direction=neutral（失败）。",
    },
    "macd_strength": {
        "title": "MACD 强度（研究代理）",
        "definition": "MACD 研究均线的扩散和密集状态，本质是乖离率，表示强度而非转折趋势节点。",
        "formula": "DIF=EMA(12)-EMA(26)，DEA=EMA(9,DIF)，hist=2*(DIF-DEA)。趋势转折5步骤中 MACD 只能表达「交叉」(DIF/DEA 金叉死叉；DIF 穿越 0 轴 = EMA12 穿越 EMA26) 与「多头排列+乖离率」(DIF 的 0 轴方向=两线排列；|DIF| 间距趋势=乖离扩散/密集)；「破线」与「均线拐头」不能表达。",
        "usage": "看强度不看拐点：DIF 远离 0 轴=两线间距拉大=乖离扩散(强)，靠近 0 轴=密集(收敛)；金叉/死叉与穿越 0 轴=强度/排列转向描述。柱体 hist 是 DIF 与 DEA 交叉的可视化，不作扩散判定。破线看 LEI 颜色，均线拐头看均线斜率补齐。金叉/死叉只是强度描述，不构成买点。",
        "caveat": "研究代理：标准 12/26/9，非转折指标；不产生交易事件，不当买点。盲区(破线/拐头)由系统既有 LEI 颜色与均线斜率补齐。",
    },
}

#: 图上标记类型 → 概念键，供点击标记时回退查找。
MARK_KIND_CONCEPTS: dict[str, str] = {
    "bottom_mark": "c_point",
    "top_mark": "neckline",
    "invalidated_mark": "c_point",
    "key_volatility": "key_volatility",
    "b1_line": "b1",
    "bottom_line": "c_point",
    "top_line": "neckline",
    "macd_event": "macd_strength",
}

#: 无档位信息的规则 → 概念回退。``ema20_reclaim_rising`` 只有分档 sub_rule
#: 才有具体含义；没有档位时，说明「档位阶梯」这一概念本身。
_RULE_FALLBACK_CONCEPTS: dict[str, str] = {
    "ema20_reclaim_rising": "stage",
    # 无独立解释的规则 → 同概念解释（口径与既有概念库一致，不新造文案）
    "resistance_b1": "b1",
    "key_wave_black": "key_volatility",
    "volume_profile_proxy": "volume_state",
}


def lookup(*, rule_id: str | None = None, sub_rule: str | None = None,
           structure_type: str | None = None, concept: str | None = None) -> Explanation | None:
    """按优先级查找解释：子规则 > 规则 > 结构类型 > 概念。

    结构类事件（``higher_low_bottom`` / ``top_structure`` 等）的 rule_id 与
    结构类型同名，直接落到 STRUCTURES；``ema20_reclaim_rising`` 只有分档的
    sub_rule 有意义，无档位时回退到「机会阶段」概念说明档位阶梯。
    """
    if sub_rule and sub_rule in RULES:
        return RULES[sub_rule]
    if rule_id and rule_id in RULES:
        return RULES[rule_id]
    # 结构类事件：rule_id 与结构类型同名
    if rule_id and rule_id in STRUCTURES:
        return STRUCTURES[rule_id]
    if structure_type and structure_type in STRUCTURES:
        return STRUCTURES[structure_type]
    if rule_id and rule_id in _RULE_FALLBACK_CONCEPTS:
        return CONCEPTS[_RULE_FALLBACK_CONCEPTS[rule_id]]
    if concept and concept in CONCEPTS:
        return CONCEPTS[concept]
    return None


__all__ = [
    "CONCEPTS",
    "MARK_KIND_CONCEPTS",
    "RULES",
    "STRUCTURES",
    "Explanation",
    "lookup",
]
