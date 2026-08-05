// 与后端 lei_signal/api/schemas.py 对齐的 DTO 类型。

export interface SparkPoint {
  date: string;
  close: number;
}

export interface Explanation {
  title: string;
  definition: string;
  formula: string;
  usage: string;
  invalidation: string;
  next_step: string;
  caveat: string;
}

export interface StructureBrief {
  structure_id: string;
  structure_type: string;
  structure_type_cn: string;
  side: "bottom" | "top";
  status: string;
  status_cn: string;
  c_price: number | null;
  neckline: number | null;
  detected_date: string;
  confirmed_date: string | null;
  invalidated_date: string | null;
  invalidated_reason: string | null;
  distance_to_c_pct: number | null;
  explanation: Explanation | null;
}

export interface EventItem {
  event_id: string;
  rule_id: string;
  rule_cn: string;
  sub_rule: string | null;
  sub_rule_cn: string | null;
  direction: string;
  direction_cn: string;
  severity: string;
  severity_cn: string;
  reason_cn: string;
  event_date: string;
  available_date: string;
  structure_id: string | null;
  lifecycle_id: string | null;
  is_new_today: boolean;
  evidence: Record<string, unknown>;
  invalidation: Record<string, unknown>;
  explanation: Explanation | null;
}

export interface Card {
  symbol: string;
  display_name: string;
  market_cn: string;
  group: "index" | "watchlist";
  price: number | null;
  prev_close: number | null;
  change_pct: number | null;
  data_time: string | null;
  last_bar_date: string | null;
  is_intraday_forming: boolean;
  provider: string | null;
  stale: boolean;
  error: string | null;
  persist_warning: string | null;
  color: string | null;
  color_cn: string | null;
  color_since: string | null;
  color_days: number | null;
  key_change_cn: string | null;
  key_change_date: string | null;
  stage: string | null;
  stage_cn: string | null;
  risk_state: string | null;
  risk_state_cn: string | null;
  primary_structure: StructureBrief | null;
  b1_price: number | null;
  distance_to_b1_pct: number | null;
  sparkline: SparkPoint[];
}

export interface DashboardResponse {
  generated_at: string;
  quote_ttl_seconds: number;
  cards: Card[];
  disclaimer_cn: string;
}

export interface WatchlistItem {
  symbol: string;
  display_name: string | null;
  market: string;
  market_cn: string;
  note: string | null;
  sort_order: number;
  added_at: string;
  group_id: number | null;
}

export interface WatchlistGroup {
  group_id: number | null;
  name: string;
  sort_order: number;
  builtin: boolean;
  symbols: string[];
}

export interface Metric {
  key: string;
  label_cn: string;
  value: number | null;
  text: string | null;
  unit: string;
  tone: "neutral" | "up" | "down" | "warn";
  hint_cn: string;
  concept: string | null;
}

export interface TodayOverview {
  as_of: string;
  quote_available: boolean;
  quote_note_cn: string;
  price: Metric[];
  technical: Metric[];
  volume: Metric[];
  capital: Metric[];
  signal: Metric[];
}

export interface ColorPerformance {
  key: string;
  label_cn: string;
  sample_count: number;
  win_rate: number | null;
  mean_return: number | null;
  median_return: number | null;
  mean_mfe: number | null;
  mean_mae: number | null;
  mean_holding_days: number | null;
}

export interface ColorBacktestSide {
  side: "long" | "short";
  title_cn: string;
  entry_rule_cn: string;
  exit_rule_cn: string;
  total_signals: number;
  open_trades: number;
  stats: ColorPerformance[];
}

export interface ColorBacktest {
  start_date: string;
  end_date: string;
  total_bars: number;
  long: ColorBacktestSide;
  short: ColorBacktestSide;
  methodology_cn: string;
}

export interface PullbackPerformance {
  key: string;
  label_cn: string;
  sample_count: number;
  incomplete_count: number;
  win_rate: number | null;
  mean_return: number | null;
  median_return: number | null;
  mean_mfe: number | null;
  mean_mae: number | null;
  mean_holding_days: number | null;
}

export interface PullbackBacktestSide {
  ma_period: number;
  title_cn: string;
  entry_rule_cn: string;
  exit_rule_cn: string;
  total_signals: number;
  open_trades: number;
  stats: PullbackPerformance[];
}

export interface PullbackBacktest {
  start_date: string;
  end_date: string;
  total_bars: number;
  research_disclaimer_cn: string;
  sides: PullbackBacktestSide[];
}

export interface ScenarioBacktestSide {
  key: string;
  title_cn: string;
  entry_rule_cn: string;
  exit_rule_cn: string;
  total_signals: number;
  open_trades: number;
  stats: PullbackPerformance[];
}

export interface ScenarioBacktest {
  scenario_id: string;
  scenario_cn: string;
  start_date: string;
  end_date: string;
  total_bars: number;
  research_disclaimer_cn: string;
  sides: ScenarioBacktestSide[];
}

export interface ConditionalScenario {
  scenario_id: string;
  scenario_cn: string;
  direction: "long" | "short";
  direction_cn: string;
  state: "watch" | "confirmed" | "weakened" | "invalidated";
  state_cn: string;
  anchor_date: string;
  trigger_date: string | null;
  latest_date: string;
  key_price: number;
  reference_price: number | null;
  distance_pct: number | null;
  current_conditions_confirmed: boolean;
  satisfied_conditions: string[];
  missing_conditions: string[];
  next_step_cn: string;
  invalidation_cn: string;
  caveat_cn: string;
  research_proxy: boolean;
  explanation: Explanation | null;
  supporting_event: EventItem | null;
  reward_risk_ratio: number | null;
  reward_risk_target: number | null;
  reward_risk_target_source_cn: string | null;
  reward_risk_computable: boolean;
}

export interface ResolveResult {
  symbol: string;
  market: string;
  market_cn: string;
  bare_code: string;
  timezone: string;
  display_name: string | null;
  probe_ok: boolean | null;
  probe_error: string | null;
}

export interface Factor {
  dimension: string;
  label_cn: string;
  detail_cn: string;
  rule_id: string;
}

export interface RiskAlert {
  priority: number;
  code: string;
  label_cn: string;
  detail_cn: string;
}

export interface PullbackOpportunity {
  state: "watch" | "confirmed";
  state_cn: string;
  ma_period: number;
  ma_name: string;
  lifecycle_id: string;
  trend_anchor_date: string;
  touch_date: string;
  confirmed_date: string | null;
  latest_date: string;
  ma_value: number;
  close: number;
  distance_to_ma_pct: number;
  current_conditions_confirmed: boolean;
  satisfied_conditions: string[];
  missing_conditions: string[];
  next_step_cn: string;
  invalidation_cn: string;
  research_proxy: boolean;
  explanation: Explanation | null;
  supporting_event: EventItem | null;
  reward_risk_ratio: number | null;
  reward_risk_target: number | null;
  reward_risk_target_source_cn: string | null;
  reward_risk_computable: boolean;
}

export interface TradeOpportunity {
  direction: "long";
  direction_cn: string;
  state: "watch" | "confirmed" | "weakened";
  state_cn: string;
  structure: StructureBrief;
  lifecycle_id: string;
  reached_tier: string;
  reached_tier_cn: string;
  reached_tier_rank: number;
  opened_on: string;
  last_upgraded_on: string;
  is_buy_reference: boolean;
  is_active: boolean;
  current_conditions_confirmed: boolean;
  satisfied_conditions: string[];
  missing_conditions: string[];
  next_step_cn: string;
  invalidation_cn: string;
  b1_price: number | null;
  distance_to_b1_pct: number | null;
  explanation: Explanation | null;
  supporting_event: EventItem | null;
}

export interface ExitSignal {
  rule_id: string;
  rule_cn: string;
  sub_rule: string | null;
  sub_rule_cn: string | null;
  direction: string;
  direction_cn: string;
  state: "active" | "inactive";
  state_cn: string;
  last_trigger_date: string | null;
  close: number | null;
  reference_values: Record<string, number>;
  reason_cn: string;
  invalidation_cn: string;
  research_proxy: boolean;
  explanation: Explanation | null;
  supporting_event: EventItem | null;
}

export interface ConditionCheck {
  code: string;
  label_cn: string;
  blocked: boolean;
  detail_cn: string;
}

export interface Tradability {
  trend_type: string;
  trend_type_cn: string;
  tradable: boolean;
  blocking_reasons: string[];
  condition_checks: ConditionCheck[];
  research_proxy: boolean;
  caveat_cn: string;
}

export interface Assessment {
  as_of: string;
  color: string;
  color_cn: string;
  stage: string;
  stage_cn: string;
  opportunity_stage: string;
  opportunity_stage_cn: string;
  risk_state: string;
  risk_state_cn: string;
  stage_change_reason_cn: string;
  dimensions: Record<string, string>;
  supports: Factor[];
  conflicts: Factor[];
  risks: RiskAlert[];
  joint_confirmed_now: boolean;
  trade_opportunities: TradeOpportunity[];
  pullback_opportunities: PullbackOpportunity[];
  conditional_scenarios: ConditionalScenario[];
  exit_signals: ExitSignal[];
  tradability: Tradability | null;
}

export interface Meta {
  provider: string | null;
  adjusted: boolean | null;
  data_time: string | null;
  last_bar_date: string | null;
  is_intraday_forming: boolean;
  cache_fallback_used: boolean;
  cache_age_seconds: number | null;
  sqlite_persisted: boolean | null;
  persist_warning: string | null;
  data_warnings: string[];
  calendar_note_cn: string;
}

export interface MarketBadge {
  summary: string;
  summary_cn: string;
  data_status: string;
  reasons_cn: string[];
}

export interface MarketContextSnapshot {
  market_id: string;
  as_of: string;
  available_at: string;
  universe_version: string;
  breadth_20: number | null;
  breadth_50: number | null;
  breadth_200: number | null;
  breadth_20_delta_5: number | null;
  breadth_50_delta_5: number | null;
  breadth_200_delta_20: number | null;
  coverage_20: number;
  coverage_50: number;
  coverage_200: number;
  constituent_count: number;
  percentile_20: number | null;
  percentile_50: number | null;
  percentile_200: number | null;
  breadth_direction: string;
  long_regime: string;
  heat_state: string;
  drawdown_from_ath: number | null;
  summary: string;
  reasons: string[];
  conflicts: string[];
  extreme_events: { event_type: string; evidence: Record<string, unknown>; threshold_origin: string }[];
  divergence_events: { event_type: string; evidence: Record<string, unknown> }[];
  naaim_label: string;
  aaii_label: string;
  naaim_current_eligible: boolean;
  aaii_current_eligible: boolean;
  source_kind: string;
  provenance: string;
  data_status: string;
}

export interface MarketContextFull {
  symbol: string;
  as_of: string;
  summary: string;
  summary_cn: string;
  data_status: string;
  reasons_cn: string[];
  conflicts_cn: string[];
  source_kind: string;
  provenance: string;
  updated_at: string;
  snapshots: MarketContextSnapshot[];
}

export interface BreadthHistoryPoint {
  date: string;
  breadth_20: number | null;
  breadth_50: number | null;
  breadth_200: number | null;
  coverage_20: number | null;
  coverage_50: number | null;
  coverage_200: number | null;
}

export interface BreadthHistoryResponse {
  market_id: string;
  lookback_days: number;
  history: BreadthHistoryPoint[];
}

export interface MarketDataStatus {
  market_id: string;
  universe_source: string;
  universe_source_version: string;
  universe_source_kind: string;
  universe_count: number;
  fixtures_root: string;
}

export interface BreadthAlert {
  level: "reversal" | "stage";
  type: string;
  title: string;
  desc: string;
}

export interface GlobalPanel {
  market_id: string;
  display_name: string;
  summary: string;
  summary_cn: string;
  data_status: string;
  breadth_20: number | null;
  breadth_50: number | null;
  breadth_200: number | null;
  breadth_20_delta_5: number | null;
  breadth_50_delta_5: number | null;
  percentile_20: number | null;
  percentile_50: number | null;
  long_regime: string;
  heat_state: string;
  drawdown_from_ath: number | null;
  alerts: BreadthAlert[];
  updated_at: string;
}

export interface GlobalStripResponse {
  panels: GlobalPanel[];
}

export interface ForwardStatBucket {
  n: number;
  median: number | null;
  mean: number | null;
  hit_rate: number | null;
  min: number | null;
  max: number | null;
}

export interface ForwardStatsResponse {
  market_id: string;
  percentile: number;
  bucket_half_width: number;
  bucket_size: number;
  min_samples: number;
  stats: Record<string, ForwardStatBucket>;
}

// echarts_kline.serialize_result 输出（关键字段）
export interface ChartPayload {
  dates: string[];
  ohlc: [number, number, number, number][]; // [open, close, low, high]
  ema20: (number | null)[];
  sma20: (number | null)[];
  ema60: (number | null)[];
  ema120: (number | null)[];
  sma60: (number | null)[];
  sma120: (number | null)[];
  ref20: (number | null)[];
  states: string[];
  volumes: number[];
  volStates: string[];
  volColors: string[];
  b1Line: LevelLine | null;
  bottomLines: LevelLine[];
  topLines: LevelLine[];
  bottomMarks: StructureMark[];
  topMarks: StructureMark[];
  invalidatedMarks: StructureMark[];
  keyVolatility: { date: string; state: string; label: string }[];
  colorMode: string;
  stateColors: Record<string, string>;
  priceUp: string;
  priceDown: string;
  symbol: string;
  displayName: string;
  lastClose: number | null;
}

/** 图上的水平参考线（B1 / C 点 / 顶部颈线），带身份供点击解释。 */
export interface LevelLine {
  yAxis: number;
  color: string;
  dash: string;
  width: number;
  label_cn?: string;
  structure_id?: string;
  structure_type?: string;
  pivot_date?: string | null;
  distance_pct?: number | null;
}

export interface StructureMark {
  date: string;
  price: number;
  label: string;
  live?: boolean;
  info: {
    structure_id: string;
    structure_type: string;
    source_rule: string;
    detected_date: string | null;
    confirmed_date: string | null;
    invalidated_date: string | null;
  };
}

export interface SymbolDetail {
  symbol: string;
  display_name: string;
  market_cn: string;
  meta: Meta;
  chart: ChartPayload;
  assessment: Assessment;
  new_events: EventItem[];
  recent_events: EventItem[];
  live_structures: StructureBrief[];
  closed_structures: StructureBrief[];
  market_badge: MarketBadge | null;
  today: TodayOverview | null;
  color_backtest: ColorBacktest | null;
  first_ma_pullback_backtest: PullbackBacktest | null;
  scenario_backtests: ScenarioBacktest[];
  concepts: Record<string, Explanation>;
  mark_concepts: Record<string, string>;
  disclaimer_cn: string;
}

// ---- 计划台账 / 监督员 agent（对齐 schemas.py）----

export interface Plan {
  plan_id: string;
  symbol: string;
  module: string; // A/B/C/D
  direction: string; // long/short
  entry_rule_id: string | null;
  entry_lifecycle_id: string | null;
  entry_trigger_cn: string | null;
  entry_price_ref: number | null;
  invalidation_price: number | null;
  target_b_price: number | null;
  target_b_source: string | null;
  reward_risk_at_plan: number | null;
  valid_until: string;
  state: string; // draft/armed/entered/exited/...
  ruleset_version: string;
  reason: string;
  thesis_cn: string;
  invalidation_criteria_cn: string;
  drawdown_playbook_cn: string;
  take_profit_plan_cn: string;
  stop_plan_cn: string;
  entered_on: string | null;
  exited_on: string | null;
  plan_kind: string; // entry | holding_watch
  take_profit_price: number | null;
  stop_price: number | null;
  watch_signal_rule_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface CreateHoldingWatchPayload {
  symbol: string;
  direction: string;
  ruleset_version: string;
  valid_until: string;
  take_profit_plan_cn: string;
  stop_plan_cn: string;
  take_profit_price?: number | null;
  stop_price?: number | null;
  watch_signal_rule_ids?: string[];
  entered_on?: string | null;
  module?: string;
  reason?: string;
}

export interface ActionItem {
  action_id: string;
  plan_id: string;
  kind: string; // ENTER/EXIT/REVIEW
  source_alert_code: string;
  state: string; // open/done/deferred/expired
  due_from: string | null;
  nag_count: number;
  resume_on: string | null;
  closed_on: string | null;
  close_kind: string | null;
}

export interface PlanAlert {
  code: string;
  severity: string; // block/remind/hint
  rule_id: string | null;
  evidence: Record<string, unknown>;
  principle_source: string | null;
  logic_provenance: string;
  caveat_cn: string;
  actionable_from: string;
  data_as_of: string;
  next_step_cn: string;
  action_kind: string | null;
}

export interface CreatePlanPayload {
  symbol: string;
  module: string;
  direction: string;
  ruleset_version: string;
  reason?: string;
  valid_until?: string;
  entry_rule_id?: string | null;
  entry_lifecycle_id?: string | null;
  entry_trigger_cn?: string | null;
  entry_price_ref?: number | null;
  invalidation_price?: number | null;
  target_b_price?: number | null;
  target_b_source?: string | null;
  reward_risk_at_plan?: number | null;
  thesis_cn?: string;
  invalidation_criteria_cn?: string;
  drawdown_playbook_cn?: string;
  take_profit_plan_cn?: string;
  stop_plan_cn?: string;
}

export interface PlanChatReply {
  reply: string;
  grounded: boolean;
  plan_id: string;
  alerts: PlanAlert[];
}

export interface PlansSummary {
  open_actions: number;
  active_plans: number;
}
