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
    created_at: str = ""
    updated_at: str = ""
