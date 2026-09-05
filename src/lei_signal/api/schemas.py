"""API 边界 DTO（Pydantic）。

只承载 JSON 可序列化数据；领域对象（AnalysisResult 等）不得穿越本层。
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class SparkPoint(BaseModel):
    date: str
    close: float


class ExplanationDTO(BaseModel):
    """信号解释：点击图上标记后右侧面板显示的内容。"""

    title: str
    definition: str = ""
    formula: str = ""
    usage: str = ""
    invalidation: str = ""
    next_step: str = ""
    caveat: str = ""


class StructureBriefDTO(BaseModel):
    structure_id: str
    structure_type: str
    structure_type_cn: str
    side: str  # "bottom" | "top"
    status: str
    status_cn: str
    c_price: float | None = None
    neckline: float | None = None
    detected_date: str
    confirmed_date: str | None = None
    invalidated_date: str | None = None
    invalidated_reason: str | None = None
    #: (close - c_price)/close*100；仅对存活的底部结构计算。
    #: 正 = 价格高于 C（安全垫），负 = 已跌破 C。
    distance_to_c_pct: float | None = None
    explanation: ExplanationDTO | None = None


class EventDTO(BaseModel):
    event_id: str
    rule_id: str
    rule_cn: str
    sub_rule: str | None = None
    sub_rule_cn: str | None = None
    direction: str
    direction_cn: str
    severity: str
    severity_cn: str
    reason_cn: str
    event_date: str
    available_date: str
    structure_id: str | None = None
    lifecycle_id: str | None = None
    is_new_today: bool = False
    evidence: dict[str, Any] = {}  # 成立时所用的真实数值
    invalidation: dict[str, Any] = {}  # 客观失效条件
    explanation: ExplanationDTO | None = None


class CardDTO(BaseModel):
    symbol: str
    display_name: str
    market_cn: str
    group: str  # "index" | "watchlist"

    # 报价
    price: float | None = None
    prev_close: float | None = None
    change_pct: float | None = None
    data_time: str | None = None  # 服务端抓取时刻（行情延迟诚实标注）
    last_bar_date: str | None = None
    is_intraday_forming: bool = False  # 最后一根是当日形成中的 bar
    provider: str | None = None
    stale: bool = False  # 使用了本地缓存兜底
    error: str | None = None  # 中文分类错误；成功时为 None
    #: 分析成功但研究库拒绝写入（事件身份字段冲突）。不影响看盘展示，
    #: 但必须让用户知道「这次没入库」，不假装已持久化。
    persist_warning: str | None = None

    # LEI 信号
    color: str | None = None
    color_cn: str | None = None
    color_since: str | None = None
    color_days: int | None = None  # 当前颜色持续的交易日数
    key_change_cn: str | None = None  # 最近关键变化（回退链推导）
    key_change_date: str | None = None
    stage: str | None = None
    stage_cn: str | None = None
    risk_state: str | None = None
    risk_state_cn: str | None = None
    primary_structure: StructureBriefDTO | None = None
    b1_price: float | None = None
    distance_to_b1_pct: float | None = None

    sparkline: list[SparkPoint] = []


class MetricDTO(BaseModel):
    """今日概述里的一个指标。value 为 None 表示数据源不覆盖，界面显示「—」。"""

    key: str
    label_cn: str
    value: float | None = None
    text: str | None = None  # 已格式化文本（分级标签等）
    unit: str = ""
    tone: str = "neutral"  # neutral | up | down | warn
    hint_cn: str = ""  # 悬停说明
    concept: str | None = None  # 可点开的概念解释键


class TodayOverviewDTO(BaseModel):
    """中间栏「今日信息概述」：价格、趋势波动、量能、资金和信号。"""

    as_of: str
    quote_available: bool  # 盘口源是否覆盖该标的
    quote_note_cn: str = ""
    price: list[MetricDTO] = []  # 四价 + 振幅 + 抵扣价乖离
    technical: list[MetricDTO] = []  # 均线乖离 + ATR + 均线开口 + 长周期趋势
    volume: list[MetricDTO] = []  # 量能倍数 + 分级 + 换手 + 量比
    capital: list[MetricDTO] = []  # 流通/总市值 + 成交额
    signal: list[MetricDTO] = []  # LEI 信号概况


class ColorPerformanceDTO(BaseModel):
    """绿灰黑回测表中的一列统计。百分比保留原始数值，例如 3.25 表示 3.25%。"""

    key: str
    label_cn: str
    sample_count: int
    win_rate: float | None = None
    mean_return: float | None = None
    median_return: float | None = None
    mean_mfe: float | None = None
    mean_mae: float | None = None
    mean_holding_days: float | None = None


class ColorBacktestSideDTO(BaseModel):
    side: str  # long | short
    title_cn: str
    entry_rule_cn: str
    exit_rule_cn: str
    total_signals: int
    open_trades: int
    stats: list[ColorPerformanceDTO] = []


class ColorBacktestDTO(BaseModel):
    start_date: str
    end_date: str
    total_bars: int
    long: ColorBacktestSideDTO
    short: ColorBacktestSideDTO
    methodology_cn: str


class PullbackPerformanceDTO(BaseModel):
    key: str
    label_cn: str
    sample_count: int
    incomplete_count: int
    win_rate: float | None = None
    mean_return: float | None = None
    median_return: float | None = None
    mean_mfe: float | None = None
    mean_mae: float | None = None
    mean_holding_days: float | None = None


class PullbackBacktestSideDTO(BaseModel):
    ma_period: int
    title_cn: str
    entry_rule_cn: str
    exit_rule_cn: str
    total_signals: int
    open_trades: int
    stats: list[PullbackPerformanceDTO] = []


class PullbackBacktestDTO(BaseModel):
    start_date: str
    end_date: str
    total_bars: int
    research_disclaimer_cn: str
    sides: list[PullbackBacktestSideDTO] = []


class ScenarioBacktestSideDTO(BaseModel):
    key: str
    title_cn: str
    entry_rule_cn: str
    exit_rule_cn: str
    total_signals: int
    open_trades: int
    stats: list[PullbackPerformanceDTO] = []


class ScenarioBacktestDTO(BaseModel):
    scenario_id: str
    scenario_cn: str
    start_date: str
    end_date: str
    total_bars: int
    research_disclaimer_cn: str
    sides: list[ScenarioBacktestSideDTO] = []


class ConditionalScenarioDTO(BaseModel):
    """条件化交易场景卡（P2 三项研究代理共用）：观察→准备→确认→风险→失效。"""

    scenario_id: str
    scenario_cn: str
    direction: str  # long | short
    direction_cn: str
    state: str  # watch | confirmed | weakened | invalidated
    state_cn: str
    anchor_date: str
    trigger_date: str | None = None
    latest_date: str
    key_price: float
    reference_price: float | None = None
    distance_pct: float | None = None
    current_conditions_confirmed: bool
    satisfied_conditions: list[str] = []
    missing_conditions: list[str] = []
    next_step_cn: str
    invalidation_cn: str
    caveat_cn: str
    research_proxy: bool = True
    explanation: ExplanationDTO | None = None
    supporting_event: EventDTO | None = None
    # 盈亏比（研究代理，只算不强制）；computable=False 时 ratio 为 None
    reward_risk_ratio: float | None = None
    reward_risk_target: float | None = None
    reward_risk_target_source_cn: str | None = None
    reward_risk_computable: bool = False


class DashboardResponse(BaseModel):
    generated_at: str
    quote_ttl_seconds: int
    cards: list[CardDTO]
    disclaimer_cn: str


class WatchlistItemDTO(BaseModel):
    symbol: str
    display_name: str | None = None
    market: str
    market_cn: str
    note: str | None = None
    sort_order: int = 0
    added_at: str
    group_id: int | None = None


class WatchlistGroupDTO(BaseModel):
    group_id: int | None  # None = 内置组（大盘）或未分组
    name: str
    sort_order: int = 0
    builtin: bool = False  # 内置组不可改名/删除
    symbols: list[str] = []


class GroupCreateRequest(BaseModel):
    name: str


class GroupRenameRequest(BaseModel):
    name: str


class MoveToGroupRequest(BaseModel):
    group_id: int | None = None  # None = 移出分组


class WatchlistAddRequest(BaseModel):
    symbol: str
    note: str | None = None
    group_id: int | None = None


class ResolveResultDTO(BaseModel):
    symbol: str
    market: str
    market_cn: str
    bare_code: str
    timezone: str
    display_name: str | None = None
    probe_ok: bool | None = None  # None = 未探测
    probe_error: str | None = None


class FactorDTO(BaseModel):
    dimension: str
    label_cn: str
    detail_cn: str
    rule_id: str


class RiskAlertDTO(BaseModel):
    priority: int
    code: str
    label_cn: str
    detail_cn: str


class PullbackOpportunityDTO(BaseModel):
    """首次均线回撤的当前条件化场景；只暴露待确认或仍有效的确认。"""

    state: str  # watch | confirmed
    state_cn: str
    ma_period: int
    ma_name: str
    lifecycle_id: str
    trend_anchor_date: str
    touch_date: str
    confirmed_date: str | None = None
    latest_date: str
    ma_value: float
    close: float
    distance_to_ma_pct: float
    current_conditions_confirmed: bool
    satisfied_conditions: list[str] = []
    missing_conditions: list[str] = []
    next_step_cn: str
    invalidation_cn: str
    research_proxy: bool = True
    explanation: ExplanationDTO | None = None
    supporting_event: EventDTO | None = None
    # 盈亏比（研究代理，只算不强制）；computable=False 时 ratio 为 None
    reward_risk_ratio: float | None = None
    reward_risk_target: float | None = None
    reward_risk_target_source_cn: str | None = None
    reward_risk_computable: bool = False


class TradeOpportunityDTO(BaseModel):
    """按底部结构持续维护的条件化做多观察。

    reached_tier 表示本轮生命周期曾达到的最高档；current_* 表示今天原子条件
    是否仍成立。二者必须分开，避免把历史升级误写成今日仍处于共同确认。
    """

    direction: str = "long"
    direction_cn: str = "潜在做多"
    state: str  # watch | confirmed | weakened
    state_cn: str
    structure: StructureBriefDTO
    lifecycle_id: str
    reached_tier: str
    reached_tier_cn: str
    reached_tier_rank: int
    opened_on: str
    last_upgraded_on: str
    is_buy_reference: bool
    is_active: bool = True
    current_conditions_confirmed: bool
    satisfied_conditions: list[str] = []
    missing_conditions: list[str] = []
    next_step_cn: str
    invalidation_cn: str
    b1_price: float | None = None
    distance_to_b1_pct: float | None = None
    explanation: ExplanationDTO | None = None
    supporting_event: EventDTO | None = None


class ExitSignalDTO(BaseModel):
    """持仓退出状态（研究代理）：当前退出条件是否成立 + 最近一次触发。

    与买点卡分离的"持仓退出"层。exit_ema20_costbasis（A6①）等退出规则在此展示
    当前是否触发、最近触发日与客观失效条件；不做自动卖出指令。
    """

    rule_id: str
    rule_cn: str
    sub_rule: str | None = None
    sub_rule_cn: str | None = None
    direction: str
    direction_cn: str
    state: str  # active | inactive
    state_cn: str
    last_trigger_date: str | None = None
    close: float | None = None
    reference_values: dict[str, Any] = {}  # ema20 / close_lag / 距离百分比等
    reason_cn: str
    invalidation_cn: str
    research_proxy: bool = True
    explanation: ExplanationDTO | None = None
    supporting_event: EventDTO | None = None


class ConditionCheckDTO(BaseModel):
    """9 条无交易条件之一的逐条检查结果。"""

    code: str
    label_cn: str
    blocked: bool
    detail_cn: str


class TradabilityDTO(BaseModel):
    """可交易性门禁（研究代理）：趋势类型 + 9 条无交易条件 + 阻断原因。

    横切层，只算展示不做硬拦截。环境层阻断条件不成立才可交易；
    入场时条件（模块/入场目标失效/盈亏比）结合信号判断、只算不强制。
    """

    trend_type: str
    trend_type_cn: str
    tradable: bool
    blocking_reasons: list[str] = []
    condition_checks: list[ConditionCheckDTO] = []
    research_proxy: bool = True
    caveat_cn: str = ""


class AssessmentDTO(BaseModel):
    as_of: str
    color: str
    color_cn: str
    stage: str
    stage_cn: str
    opportunity_stage: str
    opportunity_stage_cn: str
    risk_state: str
    risk_state_cn: str
    stage_change_reason_cn: str
    dimensions: dict[str, str] = {}
    supports: list[FactorDTO] = []
    conflicts: list[FactorDTO] = []
    risks: list[RiskAlertDTO] = []
    joint_confirmed_now: bool = False
    trade_opportunities: list[TradeOpportunityDTO] = []
    pullback_opportunities: list[PullbackOpportunityDTO] = []
    conditional_scenarios: list[ConditionalScenarioDTO] = []
    exit_signals: list[ExitSignalDTO] = []
    tradability: TradabilityDTO | None = None


class MetaDTO(BaseModel):
    provider: str | None = None
    adjusted: bool | None = None
    data_time: str | None = None
    last_bar_date: str | None = None
    is_intraday_forming: bool = False
    cache_fallback_used: bool = False
    cache_age_seconds: float | None = None
    sqlite_persisted: bool | None = None
    persist_warning: str | None = None
    data_warnings: list[str] = []
    calendar_note_cn: str


class MarketBadgeDTO(BaseModel):
    summary: str  # tailwind | neutral | headwind | unknown
    summary_cn: str
    data_status: str
    reasons_cn: list[str] = []


class SymbolDetailDTO(BaseModel):
    symbol: str
    display_name: str
    market_cn: str
    meta: MetaDTO
    chart: dict[str, Any]  # echarts_kline.serialize_result 输出
    assessment: AssessmentDTO
    new_events: list[EventDTO] = []
    recent_events: list[EventDTO] = []
    live_structures: list[StructureBriefDTO] = []
    closed_structures: list[StructureBriefDTO] = []
    market_badge: MarketBadgeDTO | None = None
    today: TodayOverviewDTO | None = None
    color_backtest: ColorBacktestDTO | None = None
    first_ma_pullback_backtest: PullbackBacktestDTO | None = None
    scenario_backtests: list[ScenarioBacktestDTO] = []
    #: 概念术语库：前端点击颜色/阶段/风险等徽章时查表，无需再请求。
    concepts: dict[str, ExplanationDTO] = {}
    #: 图上标记类型 → 概念键，点击标记找不到规则解释时回退用。
    mark_concepts: dict[str, str] = {}
    disclaimer_cn: str


class RefreshRequest(BaseModel):
    symbols: list[str] | None = None  # None = 大盘 + 自选全部


# ---------------- 计划台账（监督员 v1）----------------


class CreatePlanRequest(BaseModel):
    """建计划草案。draft 阶段允许五项预案/valid_until/reason 为空，确认时校验。"""

    symbol: str
    module: str  # A/B/C/D
    direction: str  # long/short
    ruleset_version: str
    reason: str = ""
    valid_until: str = ""
    entry_rule_id: str | None = None
    entry_lifecycle_id: str | None = None
    entry_trigger_cn: str | None = None
    entry_price_ref: float | None = None
    invalidation_price: float | None = None
    target_b_price: float | None = None
    target_b_source: str | None = None
    reward_risk_at_plan: float | None = None
    thesis_cn: str = ""
    invalidation_criteria_cn: str = ""
    drawdown_playbook_cn: str = ""
    take_profit_plan_cn: str = ""
    stop_plan_cn: str = ""


class RevisionRequest(BaseModel):
    """修订请求。verdict 由 drift.check_revision 判定后填入。"""

    changed_field: str
    new_value: str | None = None
    verdict_reason_cn: str | None = None
    changed_by: str = "user"


class DeferRequest(BaseModel):
    """推迟待办。必填 reason_cn + resume_on 谓词（决策 4c）。"""

    reason_cn: str
    resume_on: dict[str, Any]


class PlanAlertDTO(BaseModel):
    code: str
    severity: str
    rule_id: str | None = None
    evidence: dict[str, Any] = {}
    principle_source: str | None = None
    logic_provenance: str = "research_proxy"
    caveat_cn: str = ""
    actionable_from: str = ""
    data_as_of: str = ""
    next_step_cn: str = ""
    action_kind: str | None = None


class ActionItemDTO(BaseModel):
    action_id: str
    plan_id: str
    kind: str
    source_alert_code: str
    state: str
    due_from: str | None = None
    nag_count: int = 0
    last_nagged_bar_date: str | None = None
    resume_on: str | None = None
    closed_on: str | None = None
    close_kind: str | None = None


class PlanDTO(BaseModel):
    plan_id: str
    symbol: str
    module: str
    direction: str
    entry_rule_id: str | None = None
    entry_lifecycle_id: str | None = None
    entry_trigger_cn: str | None = None
    entry_price_ref: float | None = None
    invalidation_price: float | None = None
    target_b_price: float | None = None
    target_b_source: str | None = None
    reward_risk_at_plan: float | None = None
    valid_until: str
    state: str
    ruleset_version: str
    reason: str
    thesis_cn: str = ""
    invalidation_criteria_cn: str = ""
    drawdown_playbook_cn: str = ""
    take_profit_plan_cn: str = ""
    stop_plan_cn: str = ""
    entered_on: str | None = None
    exited_on: str | None = None
    exit_reason_rule_id: str | None = None
    superseded_by: str | None = None
    plan_kind: str = "entry"
    take_profit_price: float | None = None
    stop_price: float | None = None
    watch_signal_rule_ids: list[str] = []
    source: str = "user"
    created_at: str = ""
    updated_at: str = ""


class CreateHoldingWatchRequest(BaseModel):
    """建持仓盯盘（已在场内，只监督退出）。

    必填：两项退出预案 + valid_until + 至少一个触发条件（止盈价/止损价/信号）。
    入场理由不强制--你已经在场内了。仍不记数量/金额/账户。
    """

    symbol: str
    direction: str = "long"
    ruleset_version: str
    valid_until: str
    take_profit_plan_cn: str
    stop_plan_cn: str
    take_profit_price: float | None = None
    stop_price: float | None = None
    watch_signal_rule_ids: list[str] = []
    entered_on: str | None = None      # 缺省为当日
    module: str = "A"
    reason: str = ""


class BuyPointCandidateDTO(BaseModel):
    """一个候选买点：全部字段来自既有机会/场景 DTO，无新判定、无新数值。"""

    scenario_id: str
    scenario_cn: str
    module: str | None = None          # A/B/C/D，由 rule_id 经 MODULE_MAP 反查
    direction: str = "long"
    state: str                          # watch/confirmed/weakened/invalidated
    state_cn: str = ""
    rule_id: str | None = None          # 入场理由锚点（建计划用）
    lifecycle_id: str | None = None
    #: 图什么信号进：已满足 / 还缺什么。照抄机会 DTO，不重写措辞。
    satisfied_conditions: list[str] = []
    missing_conditions: list[str] = []
    key_price: float | None = None      # 场景关键价（突破位/站上位等）
    #: 止损只能引这个：来自场景 invalidation（结构 C 点/密集区下沿等）
    invalidation_price: float | None = None
    invalidation_cn: str = ""
    reward_risk_ratio: float | None = None
    reward_risk_target: float | None = None
    reward_risk_target_source_cn: str | None = None
    reward_risk_computable: bool = False
    next_step_cn: str = ""
    caveat_cn: str = ""
    research_proxy: bool = True
    #: 该候选最近一次状态变更日 (= 触发日 / 失效日), 供 recency 过滤用
    last_state_change_date: str | None = None
    #: lifecycle 首次锚定日 (= B1 观察日), 仅作文案历史参考
    opened_date: str | None = None


class ResonanceGroupDTO(BaseModel):
    """同一价位 ±tolerance_pct 范围内多个 rule_id 共同认可的共振买点。

    用户场景: 多个独立结构在相近价位给出买点, 单独展示容易让人疑惑;
    合并为「共振」一行, 列出所有 rule_id 及其依据, 信息密度更清晰。
    """

    level: float                        # 共振价位 (中位数 key_price)
    tolerance_pct: float                # 实际使用的容差
    rule_ids: list[str] = []            # 共振的 rule_id 列表 (去重)
    candidates: list[BuyPointCandidateDTO] = []  # 组内所有候选


class HistoricalStructureDTO(BaseModel):
    """被 recency 过滤掉的过期结构。不当买点候选, 仅作文案历史参考。

    设计动机: B1 观察/确认事件可能来自几周/几月/几年前, lifecycle 还活着但
    不再属于「最近 N 个交易日」的买点范畴; 静默丢掉会让用户疑惑, 显式列出
    又会污染买点卡片。折中: 单独移入 historical_structures, 默认折叠。
    """

    rule_id: str | None = None
    lifecycle_id: str | None = None
    state: str
    state_cn: str
    scenario_cn: str
    direction: str = "long"
    opened_date: str | None = None
    last_state_change_date: str | None = None
    days_since: int = 0                 # 距 as_of 的日历天数
    key_price: float | None = None
    note: str = ""


class WatchConditionDTO(BaseModel):
    """「到什么情况才算买点」的单条条件。

    刻意区分价位型与状态型：并非所有缺失条件都对应一个价格。
    缺「完整多头排列未成立」时没有单一价位可言，硬贴数字就是编造。
    """

    text_cn: str                        # 照抄 missing_conditions 原文
    kind: str                           # price | state
    price: float | None = None          # 仅 kind=price 时有值
    #: 可跟踪化建议：把该条件交给系统盯盘（复用 holding_watch / resume_on 形态）
    as_signal_rule_ids: list[str] = []


class SuggestedPlanDTO(BaseModel):
    """可直接落计划的预填。只给系统已算出的值；五项预案必须人写，故不含。"""

    symbol: str
    module: str
    direction: str
    entry_rule_id: str | None = None
    entry_lifecycle_id: str | None = None
    entry_trigger_cn: str | None = None
    invalidation_price: float | None = None
    target_b_price: float | None = None
    target_b_source: str | None = None
    reward_risk_at_plan: float | None = None


class BuyPointReviewDTO(BaseModel):
    """买点审阅：汇总既有确定性判定，供 agent 讲解与协商落计划。

    verdict 由字段组合派生，不是新判定：
      actionable = 有 confirmed 机会且可交易；
      blocked    = 有机会但可交易性阻断（规格 §13，按规则不开新仓）；
      waiting    = 只有 watch 机会，等条件成立；
      none       = 当前无任何机会。
    """

    symbol: str
    display_name: str = ""
    as_of: str
    last_close: float | None = None
    verdict: str
    verdict_cn: str
    summary_cn: str
    tradability: TradabilityDTO | None = None
    #: 近 N 个交易日的独立候选（不在任何共振组里、且非历史结构）
    candidates: list[BuyPointCandidateDTO] = []
    #: 近 N 个交易日内, 多个 rule 在相近价位共同认可的共振候选
    resonance_groups: list[ResonanceGroupDTO] = []
    #: 被 recency 过滤掉的过期结构, 默认折叠, 不计入 verdict
    historical_structures: list[HistoricalStructureDTO] = []
    #: verdict != actionable 时给出：到什么情况才算买点
    watch_conditions: list[WatchConditionDTO] = []
    #: 仅 verdict=actionable 时给出
    suggested_plan: SuggestedPlanDTO | None = None
    has_active_plan: bool = False
    active_plan_ids: list[str] = []
    ruleset_version: str = ""
    disclaimer_cn: str = ""


class ScanItemDTO(BaseModel):
    """批量扫描的单标的精简结果。"""

    symbol: str
    display_name: str = ""
    verdict: str
    verdict_cn: str
    best_scenario_cn: str | None = None
    best_state: str | None = None
    reward_risk_ratio: float | None = None
    reward_risk_computable: bool = False
    blocking_reasons: list[str] = []
    missing_summary_cn: str = ""
    has_active_plan: bool = False
    error: str | None = None


class ScanResponse(BaseModel):
    generated_at: str
    scanned: int
    items: list[ScanItemDTO] = []


class SignalAlertDTO(BaseModel):
    """统一信号面板的一行卖点提醒。"""

    symbol: str
    display_name: str = ""
    tier: str  # hard | warn | soft
    kind: str
    kind_cn: str = ""
    title: str = ""
    reason_cn: str = ""
    is_new: bool = False
    key_prices: dict[str, float] = {}
    provenance: str = "system"
    available_date: str | None = None


class UnavailableItemDTO(BaseModel):
    """数据不可用清单的一项（显式 DATA_UNAVAILABLE，不静默）。"""

    symbol: str
    error: str | None = None


class SignalsTodayResponse(BaseModel):
    """今日自选信号（买点 + 卖点合并响应，看盘主页横幅数据源）。"""

    scan_date: str
    as_of: str | None = None
    generated_at: str = ""
    scanned: int = 0
    available: bool = True
    actionable: list[ScanItemDTO] = []
    waiting: list[ScanItemDTO] = []
    blocked: list[ScanItemDTO] = []
    sell_hard: list[SignalAlertDTO] = []
    sell_warn: list[SignalAlertDTO] = []
    sell_soft: list[SignalAlertDTO] = []
    unavailable: list[UnavailableItemDTO] = []


class TodayOpportunityResponse(BaseModel):
    """今日机会雷达：按 verdict 分组的当日扫描结果（dashboard 面板 + 红点数据源）。

    actionable / waiting 是"有机会"的标的（红点计数 = actionable + waiting）；
    blocked 是"环境阻断"的标的，单独列出供用户了解为何按规则不开新仓。
    verdict=none 的标的不入库、不出现在本响应。
    """

    scan_date: str
    scanned: int
    generated_at: str
    actionable: list[ScanItemDTO] = []
    waiting: list[ScanItemDTO] = []
    blocked: list[ScanItemDTO] = []


class BuyPointChatRequest(BaseModel):
    """就买点审阅提问。message 为空时返回审阅摘要。"""

    message: str = ""


class BuyPointChatReply(BaseModel):
    reply: str
    grounded: bool
    symbol: str
    review: BuyPointReviewDTO | None = None


class PlanChatRequest(BaseModel):
    """向监督员 agent 提问。message 为空时返回当前 alert 的接地摘要。"""

    message: str = ""


class PlanChatReply(BaseModel):
    """agent 回复。grounded=False 表示 LLM 不可用或校验失败，已降级模板。"""

    reply: str
    grounded: bool
    plan_id: str
    alerts: list[PlanAlertDTO] = []


class PlansSummaryDTO(BaseModel):
    """监督待办顶栏红点：未处理待办数 + 活跃计划数 + 今日机会数。

    today_opportunities = 今日雷达中 actionable + waiting 的标的数
    （blocked 不计，环境阻断按规则不开新仓）。当日未扫描时为 0。
    today_signal_total = 今日机会数 + 卖点数（hard+warn）合计，红点用。
    """

    open_actions: int
    active_plans: int
    today_opportunities: int = 0
    today_signal_total: int = 0


class ConformanceReportDTO(BaseModel):
    """草稿符合性核对结果。can_confirm = 无硬项；issue 形态同 PlanAlertDTO。

    hard_issues 阻断确认（confirm 端点据此 422），soft_issues 仅提醒。
    system_detected = 系统实际检测到的 module/direction/场景，供人对照。
    """

    can_confirm: bool
    hard_issues: list[PlanAlertDTO] = []
    soft_issues: list[PlanAlertDTO] = []
    system_detected: dict[str, Any] = {}


class DraftUpdateRequest(BaseModel):
    """编辑 draft 字段（仅 draft 态可改，无 drift）。

    全字段可选；路由用 ``model_dump(exclude_unset=True)`` 取仅传入的字段，
    故「未传 = 不改」「传 null = 清空」语义清晰。
    """

    module: str | None = None
    direction: str | None = None
    valid_until: str | None = None
    reason: str | None = None
    entry_rule_id: str | None = None
    entry_lifecycle_id: str | None = None
    entry_trigger_cn: str | None = None
    entry_price_ref: float | None = None
    invalidation_price: float | None = None
    target_b_price: float | None = None
    target_b_source: str | None = None
    reward_risk_at_plan: float | None = None
    thesis_cn: str | None = None
    invalidation_criteria_cn: str | None = None
    drawdown_playbook_cn: str | None = None
    take_profit_plan_cn: str | None = None
    stop_plan_cn: str | None = None
    take_profit_price: float | None = None
    stop_price: float | None = None
    watch_signal_rule_ids: list[str] | None = None


# ========================================================================
# Step 2: 提醒订阅 (watch_subscription)
# ========================================================================


class WatchSubscribeRequest(BaseModel):
    """POST /api/watch/subscribe 请求体.

    字段名与 WatchConditionDTO 对齐: 用户从 review 拉一条 watch_condition
    出来, 把 kind/price/text_cn/as_signal_rule_ids 传过来, 加上该
    candidate 的 direction/module/rule_id.
    """

    symbol: str
    direction: str                                  # long/short
    module: str                                     # A/B/C/D
    watch_kind: str                                 # price | state
    watch_text_cn: str
    level: float | None = None
    source_candidate_id: str | None = None
    source_rule_id: str | None = None
    as_signal_rule_ids: list[str] = []


class WatchDismissRequest(BaseModel):
    """POST /api/watch/{id}/dismiss 请求体."""

    reason: str


class WatchSubscriptionDTO(BaseModel):
    watch_id: str
    symbol: str
    direction: str
    module: str
    source_candidate_id: str | None = None
    source_rule_id: str | None = None
    level: float | None = None
    watch_kind: str
    watch_text_cn: str
    as_signal_rule_ids: list[str] = []
    state: str
    created_at: str
    last_checked_at: str | None = None
    triggered_at: str | None = None
    triggered_price: float | None = None
    triggered_reason_cn: str | None = None
    promoted_plan_id: str | None = None
    dismissed_at: str | None = None
    dismissed_reason: str | None = None


class CheckReportDTO(BaseModel):
    """POST /api/watch/check-now 响应体."""

    total_active: int
    triggered_count: int
    triggered_watch_ids: list[str] = []
    skipped: list[dict] = []      # [{watch_id, reason}]
    checked_at: str


# ========================================================================
# Step 3: 从 watch 落计划 (watch -> plan)
# ========================================================================


class WatchPromoteRequest(BaseModel):
    """POST /api/watch/{watch_id}/promote 请求体.

    字段语义与 CreatePlanRequest 一致 -- 用户在 [据此建计划] 弹窗里填的
    五项预案 + 止损/止盈价/有效期等. 必填项与 armed 完全相同
    (五项预案 + reason + valid_until), 服务端不二次校验 -- 委托给 confirm_plan.

    invalidation_price / target_b_price 默认从 watch.level 预填, 用户可改.
    """

    module: str | None = None             # 缺省从 watch 取
    direction: str | None = None          # 缺省从 watch 取
    valid_until: str = ""                 # 必填 (armed)
    reason: str = ""                      # 必填 (armed)
    entry_rule_id: str | None = None
    entry_lifecycle_id: str | None = None
    entry_trigger_cn: str | None = None
    entry_price_ref: float | None = None
    invalidation_price: float | None = None
    target_b_price: float | None = None
    target_b_source: str | None = None
    reward_risk_at_plan: float | None = None
    thesis_cn: str = ""                   # 必填
    invalidation_criteria_cn: str = ""   # 必填
    drawdown_playbook_cn: str = ""       # 必填
    take_profit_plan_cn: str = ""        # 必填
    stop_plan_cn: str = ""               # 必填
    watch_signal_rule_ids: list[str] | None = None
    #: 是否 confirm 后立即 entered (默认 True -- watch_promoted 已经是触发确认)
    auto_enter: bool = True


class WatchPromoteResponse(BaseModel):
    """POST /api/watch/{watch_id}/promote 响应体."""

    plan: PlanDTO
    watch: WatchSubscriptionDTO


# ---------------- agent 统一会话（spec 2026-08-23） ----------------


class TraceItem(BaseModel):
    """溯源角标数据：前端 ProvenanceBadge 展开 renders，默认不显示。"""
    label: str
    rule_id: str | None = None
    evidence_cn: str = ""
    research_proxy: bool = False
    principle_source: str | None = None


class AgentChatRequest(BaseModel):
    session_id: str | None = None
    context_kind: str = "symbol"  # symbol | global
    symbol: str | None = None
    message: str = ""


class AgentChatReply(BaseModel):
    session_id: str
    reply: str
    grounded: bool
    trace: list[TraceItem] = []
    resolved_symbol: str | None = None


class RecommendItemDTO(BaseModel):
    """今日推荐的单位。数值全部来自扫描/审阅既有字段，无新判定。"""

    symbol: str
    display_name: str = ""
    verdict: str
    verdict_cn: str = ""
    best_scenario_cn: str | None = None
    reward_risk_ratio: float | None = None
    reward_risk_computable: bool = False
    news_heat: int = 0
    news_tags: list[str] = []
    sentiment_cn: str | None = None   # 情绪面叙事标注（只标注不评分）
    score: float = 0.0
    reasons: list[str] = []


class SectorPickDTO(BaseModel):
    """板块推荐（阶段快照直读，只排序不判定）。"""

    code: str
    name: str = ""
    stage: str = ""
    stage_cn: str = ""
    heat_state_cn: str | None = None  # 散户热度叙事标注（偏热/冰点，中性措辞）
    note: str = ""


class RecommendCardDTO(BaseModel):
    """今日推荐卡（流水线输出 + 存证账本载体）。"""

    run_date: str
    generated_at: str = ""
    items: list[RecommendItemDTO] = []
    sectors: list[SectorPickDTO] = []
    sentiment_status: str = "暂未接入"
    fundamental_note: str = "宏观/基本面按叙事标注展示，不参与技术判定"
    disclaimer_cn: str = (
        "排序仅影响展示顺序，不构成新判定；技术结论以各标的买点审阅为准。"
        "消息面/基本面为叙事标注层，永不硬过滤信号。"
    )


class SizingAdviceDTO(BaseModel):
    """仓位档位建议（组合层管理建议，最终金额由用户决定）。"""

    symbol: str
    tier: str                     # 试仓 | 标准 | 偏重
    tier_pct_cn: str              # 如「10–15%（占总资金）」
    cap_pct: float = 30.0         # 单标的硬顶 %
    reasons: list[str] = []
    strength: str = "observation" # observation=观察级（advisor.py 口径）
    strength_cn: str = "观察级建议（无回测依据的组合层管理建议）"
    disclaimer_cn: str = "档位只是建议，最终买多少由你决定。"


class TradePreviewDTO(BaseModel):
    """报单预解析（best-effort）：确认卡展示、用户可改字段后才落库。"""

    fund_code: str | None = None
    fund_name: str | None = None
    side: str = "buy"
    side_cn: str = "申购"
    amount: float | None = None
    trade_date: str = ""
    missing: list[str] = []       # 缺什么（fund_code/amount/date...）
    note_cn: str = "请核对以下信息，确认后记入基金台账；金额单位为元。"


class CopilotDispatchRequest(BaseModel):
    message: str = ""
    symbol: str | None = None


class CopilotDispatchReply(BaseModel):
    """意图分发结果：命中流水线回 card/preview，否则 chat_fallback 走 /agent/chat。"""

    intent: str
    symbol: str | None = None
    card: dict | None = None        # {card_type, data}
    preview: TradePreviewDTO | None = None
    chat_fallback: bool = False
    note_cn: str = ""


class FundTradeDTO(BaseModel):
    """基金成交台账一行（手动报单，用户确认落库；不接券商）。"""

    trade_id: str
    fund_code: str
    fund_name: str
    side: str
    side_cn: str
    amount: float
    trade_date: str
    priced_nav: float | None
    price_status: str          # pending | priced | failed
    price_status_cn: str
    plan_id: str | None = None
    source: str = "web"
    note: str = ""
    created_at: str = ""


class FundPositionDTO(BaseModel):
    """单基金持仓汇总（份额/成本/最新净值/浮盈/已实现）。"""

    fund_code: str
    fund_name: str
    shares: float
    cost: float                     # 剩余成本（元）
    latest_nav: float | None
    latest_nav_date: str = ""
    market_value: float | None      # shares × latest_nav（无净值则 None）
    unrealized_pnl: float | None
    realized_pnl: float = 0.0
    note: str = ""


class TradesResponseDTO(BaseModel):
    trades: list[FundTradeDTO] = []
    positions: list[FundPositionDTO] = []


class ReviewSectionDTO(BaseModel):
    heading_cn: str
    lines: list[str] = []


class ReviewCardDTO(BaseModel):
    """复盘卡：纪律面（我照系统做了吗）与结果面（结果怎样）分开陈述。"""

    review_id: str
    kind: str                    # trade | weekly
    ref_key: str
    title_cn: str
    sections: list[ReviewSectionDTO] = []
    r_multiple: float | None = None
    realized_pnl: float | None = None
    narrative: str = ""          # GLM 叙事，空=模板
    grounded: bool = False


class OpsTodoDTO(BaseModel):
    action_id: str
    plan_id: str
    symbol: str
    kind: str
    kind_cn: str
    next_step_cn: str = ""
    due_from: str = ""
    nag_count: int = 0


class OpsLineDTO(BaseModel):
    symbol: str
    display_name: str = ""
    text_cn: str


class SentimentBlockDTO(BaseModel):
    """情绪面叙事区块（只标注，不构成判定/买卖点）。"""

    available: bool = False
    margin_cn: str = ""              # 两融环境一句话
    margin_detail: dict | None = None
    breadth_cn: str | None = None    # 市场宽度一句话（A股+美股直读）
    hot_boards: list[dict] = []      # [{name, heat_pctile, stage_cn}]
    holdings_states: list[dict] = [] # [{group_cn, state_cn}]
    note_cn: str = ""


class MajorEventDTO(BaseModel):
    """重大事件条目（客观字段 only：标题/类别/方向/分数/时间）。

    2026-09-05 用户口径：影响资本开支级别的产业大事（英伟达/谷歌类）+
    宏观/风险/政策，≥7 分；博主观点与 AI 主观小结（llm_note）不进 Agent。
    """

    title: str
    category_cn: str = ""
    direction_cn: str = ""
    importance: int = 0
    when_cn: str = ""
    published_at: str = ""


class MajorEventsBlockDTO(BaseModel):
    """重大事件叙事区块（参考层，不参与技术判定）。"""

    available: bool = False
    items: list[MajorEventDTO] = []
    note_cn: str = ""


class OpsCardDTO(BaseModel):
    """每日操作清单（确定性组装，零 LLM；页面与推送共用）。"""

    run_date: str
    generated_at: str = ""
    holdings_actions: list[OpsLineDTO] = []
    recommendations: RecommendCardDTO | None = None
    plan_todos: list[OpsTodoDTO] = []
    watch_triggers: list[OpsLineDTO] = []
    sentiment: SentimentBlockDTO | None = None
    major_events: MajorEventsBlockDTO | None = None
    push_summary_cn: str = ""


class CreateSessionRequest(BaseModel):
    symbol: str | None = None
    title_cn: str = ""


class AgentSessionDTO(BaseModel):
    session_id: str
    symbol: str | None
    title_cn: str
    last_active_at: str
    last_message_cn: str = ""


class AgentMessageDTO(BaseModel):
    role: str
    content: str
    grounded: bool
    created_at: str


# ---- 我的持仓（portfolio，2026-09-04）----


class PortfolioHoldingDTO(BaseModel):
    holding_id: str
    name: str
    code: str | None = None  # 截图未含代码，待补
    market_value: float
    return_pct: float | None = None
    tags: list[str] = []
    note: str = ""
    # 季报穿透（无数据为 None；叙事标注层，不进信号）
    top10_total_pct: float | None = None        # 前十大合计占净值 %
    top10_by_market_pct: dict[str, float] = {}  # cn/hk/us/other -> 占净值 %
    report_quarter: str | None = None


class PortfolioAdviceDTO(BaseModel):
    advice_id: str
    priority: int
    strength: str           # certified / candidate / observation / management
    strength_cn: str
    title_cn: str
    detail_cn: str
    evidence: list[dict] = []
    trigger_cn: str = ""
    execution_cn: str = ""


class PortfolioGroupDTO(BaseModel):
    group_key: str
    name: str
    market: str
    market_cn: str
    amount: float                 # 组内市值合计（元）
    pct: float                    # 占组合比例（%）
    avg_return_pct: float | None  # 金额加权持有收益率（%），全部缺失时 None
    verdict_cn: str               # 系统怎么看（大白话结论）
    verdict_basis: str = ""       # 结论依据（文档指针，给开发者看）
    real_market_share: dict[str, float] | None = None  # 穿透后市场分布（%）
    holdings: list[PortfolioHoldingDTO] = []


class PortfolioResponse(BaseModel):
    as_of: str
    data_source_cn: str
    total_value: float
    holdings_count: int
    observations: list[str] = []  # 组合级提示（大白话）
    advices: list[PortfolioAdviceDTO] = []  # 调仓建议（R1~R7）
    groups: list[PortfolioGroupDTO] = []


# ── 基金净值序列对比（/portfolio/nav-series）─────────────────────────────
# 补救重建（2026-09-05）：原定义随一次误操作 checkout 丢失（未提交），
# 按 routes/portfolio.py::get_nav_series 用法与 funddata.fetch_nav_full
# 字段重建；若与作者原版有出入，以作者版本为准直接覆盖。
class FundNavItemDTO(BaseModel):
    code: str
    name: str = ""
    dates: list[str] = []
    unit_nav: list[float] = []
    acc_nav: list[float] = []
    day_pct: list[float] = []


class FundNavErrorDTO(BaseModel):
    code: str
    reason_cn: str


class FundNavSeriesResponse(BaseModel):
    days: int = 0
    items: list[FundNavItemDTO] = []
    errors: list[FundNavErrorDTO] = []