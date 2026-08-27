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
  // 真全A涨跌家数（CN_ALL_A 走真源；标普500 等无此字段）
  is_real_a_share?: boolean;
  up?: number | null;
  down?: number | null;
  flat?: number | null;
  total?: number | null;
  up_pct?: number | null;
  adv_dec_ratio?: number | null;
  limit_up?: number | null;
  limit_down?: number | null;
  // 冻结快照元信息（CN_ALL_A 宽度来自收盘后预计算的磁盘缓存）
  breadth_as_of?: string | null;
  breadth_trading_day?: string | null;
  breadth_source?: string | null;
  source_detail?: string;
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
  /** 投资者情绪（NAAIM/AAII），来自 LEI_SENTIMENT_ROOT，与 Streamlit 市场环境页同源。 */
  sentiment?: GlobalSentiment;
}

/** 单个情绪序列（NAAIM 或 AAII）的最新摘要。 */
export interface GlobalSentimentSeries {
  /** 分档枚举：extreme_low/low/neutral/high/extreme_high/unknown */
  label: string;
  label_cn: string;
  survey_week: string | null;
  available_at: string | null;
  source: string | null;
  license_status: string | null;
  current_eligible: boolean;
  // NAAIM 专用
  exposure_index?: number | null;
  percentile?: number | null;
  // AAII 专用
  bullish?: number | null;
  neutral?: number | null;
  bearish?: number | null;
  bull_bear?: number | null;
}

/** 情绪总览：root_set 表示后端是否读到了 LEI_SENTIMENT_ROOT 环境变量。 */
export interface GlobalSentiment {
  root_set: boolean;
  naaim: GlobalSentimentSeries | null;
  aaii: GlobalSentimentSeries | null;
}

/** 前端手动录入一期情绪读数（POST /market-context/sentiment）。 */
export interface SentimentIngest {
  series: "naaim" | "aaii";
  survey_week: string;
  exposure?: number | null;
  bullish?: number | null;
  neutral?: number | null;
  bearish?: number | null;
  available_at?: string | null;
}

/** 真全A市场宽度（涨跌家数 + 可选 MA 上方占比）。
 *  后端 /market-context/a-share-breadth 返回；来源：腾讯快照+沪深交易所代码列表（涨跌家数）、
 *  akshare 东财历史K线（MA 占比，需正常网络环境）。 */
export interface AShareBreadthResponse {
  as_of: string;
  up: number;
  down: number;
  flat: number;
  total: number;
  up_pct: number | null; // 上涨家数占比 %
  adv_dec_ratio: number | null; // 涨跌比 = up / down
  limit_up: number;
  limit_down: number;
  ma20_pct: number | null; // MA20 上方占比 %（券商金工口径，需联网）
  ma50_pct: number | null;
  ma200_pct: number | null;
  data_status: string; // ok | partial | unavailable
  source_detail: string;
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
  macdDif: (number | null)[];
  macdDea: (number | null)[];
  macdHist: (number | null)[];
  /** MACD 副图事件日（金叉/死叉/上穿0轴/下穿0轴），后端 macd_strength 规则判定。 */
  macdEvents: MacdEvent[];
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

/** MACD 副图事件日。研究代理：强度描述，不构成买卖点（macd-reading 口径）。 */
export interface MacdEvent {
  date: string;
  type: "golden_cross" | "death_cross" | "zero_cross_up" | "zero_cross_down";
  statusCn: string; // 金叉 / 死叉 / 上穿0轴 / 下穿0轴
  dimension: string; // 支持 / 冲突
  dif: number;
  dea: number;
  hist: number;
  detailCn: string;
  /** 盲区补齐：当日 LEI 颜色（破线）与 EMA20 斜率（均线拐头）。 */
  colorCn: string;
  slopeCn: string;
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

/** 草稿符合性核对报告（对齐 ConformanceReportDTO）。 */
export interface ConformanceReport {
  can_confirm: boolean;
  hard_issues: PlanAlert[]; // 阻断确认
  soft_issues: PlanAlert[]; // 仅提醒
  system_detected: Record<string, unknown>; // 系统实测 module/direction/场景
}

/** 编辑 draft 字段的载荷（对齐 DraftUpdateRequest，全可选）。 */
export interface DraftUpdatePayload {
  module?: string;
  direction?: string;
  valid_until?: string;
  reason?: string;
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
  take_profit_price?: number | null;
  stop_price?: number | null;
  watch_signal_rule_ids?: string[];
}

export interface PlansSummary {
  open_actions: number;
  active_plans: number;
  today_opportunities: number;
  today_signal_total: number;
}

// ---- 买点审阅 / 扫描 ----

export interface BuyPointCandidate {
  scenario_id: string;
  scenario_cn: string;
  module: string | null;
  direction: string;
  state: string;
  state_cn: string;
  rule_id: string | null;
  lifecycle_id: string | null;
  satisfied_conditions: string[];
  missing_conditions: string[];
  key_price: number | null;
  invalidation_price: number | null;
  invalidation_cn: string;
  reward_risk_ratio: number | null;
  reward_risk_target: number | null;
  reward_risk_computable: boolean;
  next_step_cn: string;
  caveat_cn: string;
  research_proxy: boolean;
  last_state_change_date: string | null;
  opened_date: string | null;
}

export interface ResonanceGroup {
  level: number;
  tolerance_pct: number;
  rule_ids: string[];
  candidates: BuyPointCandidate[];
}

export interface HistoricalStructure {
  rule_id: string | null;
  lifecycle_id: string | null;
  state: string;
  state_cn: string;
  scenario_cn: string;
  direction: string;
  opened_date: string | null;
  last_state_change_date: string | null;
  days_since: number;
  key_price: number | null;
  note: string;
}

export interface WatchCondition {
  text_cn: string;
  kind: string; // price | state
  price: number | null;
  as_signal_rule_ids: string[];
}

// ---- Step 2: 提醒订阅 ----
export type WatchState =
  | "active"
  | "pending_confirmation"
  | "dismissed"
  | "promoted";

export interface WatchSubscription {
  watch_id: string;
  symbol: string;
  direction: string;
  module: string;
  source_candidate_id: string | null;
  source_rule_id: string | null;
  level: number | null;
  watch_kind: string; // price | state
  watch_text_cn: string;
  as_signal_rule_ids: string[];
  state: WatchState;
  created_at: string;
  last_checked_at: string | null;
  triggered_at: string | null;
  triggered_price: number | null;
  triggered_reason_cn: string | null;
  promoted_plan_id: string | null;
  dismissed_at: string | null;
  dismissed_reason: string | null;
}

// ---- Step 3: 从 watch 落计划 (POST /api/watch/{id}/promote) ----
// 与 src/lei_signal/api/schemas.py:WatchPromoteRequest 字段一一对应.
// 后端硬编码 plan_kind=entry / ruleset_version=watch_promoted_v1, 客户端不可改.
export interface PromoteWatchRequest {
  module?: string | null;
  direction?: string | null;
  valid_until: string;              // required (armed 必填)
  reason: string;                   // required (armed 必填)
  entry_rule_id?: string | null;
  entry_lifecycle_id?: string | null;
  entry_trigger_cn?: string | null;
  entry_price_ref?: number | null;
  invalidation_price?: number | null;
  target_b_price?: number | null;
  target_b_source?: string | null;
  reward_risk_at_plan?: number | null;
  thesis_cn: string;                // required
  invalidation_criteria_cn: string; // required
  drawdown_playbook_cn: string;     // required
  take_profit_plan_cn: string;      // required
  stop_plan_cn: string;             // required
  watch_signal_rule_ids?: string[] | null;
  auto_enter?: boolean;             // 后端默认 true
}

export interface PromoteWatchResponse {
  plan: Plan;
  watch: WatchSubscription;
}

export interface SubscribeWatchRequest {
  symbol: string;
  direction: string;
  module: string;
  watch_kind: string;
  watch_text_cn: string;
  level: number | null;
  source_candidate_id: string | null;
  source_rule_id: string | null;
  as_signal_rule_ids: string[];
}

export interface CheckReport {
  total_active: number;
  triggered_count: number;
  triggered_watch_ids: string[];
  skipped: Array<{ watch_id: string; reason: string }>;
  checked_at: string;
}

export interface SuggestedPlan {
  symbol: string;
  module: string;
  direction: string;
  entry_rule_id: string | null;
  entry_lifecycle_id: string | null;
  invalidation_price: number | null;
  target_b_price: number | null;
  reward_risk_at_plan: number | null;
}

export interface BuyPointReview {
  symbol: string;
  display_name: string;
  as_of: string;
  last_close: number | null;
  verdict: string; // actionable | blocked | waiting | none
  verdict_cn: string;
  summary_cn: string;
  candidates: BuyPointCandidate[];
  resonance_groups: ResonanceGroup[];
  historical_structures: HistoricalStructure[];
  watch_conditions: WatchCondition[];
  suggested_plan: SuggestedPlan | null;
  has_active_plan: boolean;
  ruleset_version: string;
  disclaimer_cn: string;
}

export interface ScanItem {
  symbol: string;
  display_name: string;
  verdict: string;
  verdict_cn: string;
  best_scenario_cn: string | null;
  best_state: string | null;
  reward_risk_ratio: number | null;
  reward_risk_computable: boolean;
  blocking_reasons: string[];
  missing_summary_cn: string;
  has_active_plan: boolean;
  error: string | null;
}

export interface ScanResponse {
  generated_at: string;
  scanned: number;
  items: ScanItem[];
}

export interface TodayOpportunityResponse {
  scan_date: string;
  scanned: number;
  generated_at: string;
  actionable: ScanItem[];
  waiting: ScanItem[];
  blocked: ScanItem[];
}

export interface SignalAlert {
  symbol: string;
  display_name: string;
  tier: "hard" | "warn" | "soft" | string;
  kind: string;
  kind_cn: string;
  title: string;
  reason_cn: string;
  is_new: boolean;
  key_prices: Record<string, number>;
  provenance: string;
  available_date: string | null;
}

export interface UnavailableItem {
  symbol: string;
  error: string | null;
}

export interface SignalsToday {
  scan_date: string;
  as_of: string | null;
  generated_at: string;
  scanned: number;
  available?: boolean;
  actionable: ScanItem[];
  waiting: ScanItem[];
  blocked: ScanItem[];
  sell_hard: SignalAlert[];
  sell_warn: SignalAlert[];
  sell_soft: SignalAlert[];
  unavailable: UnavailableItem[];
}

export interface BuyPointChatReply {
  reply: string;
  grounded: boolean;
  symbol: string;
  review: BuyPointReview | null;
}

// ---- 基本面参考层 (/api/fundamentals) ----

export interface MacroIndicator {
  key: string; // pmi | cpi | ppi
  name_cn: string;
  period: string | null;
  value: number | null;
  yoy: number | null;
  note_cn: string;
}

export interface IndustryBoard {
  code: string; // 东财 BK 代码
  name: string;
  latest: number | null;
  pct_change: number | null;
  turnover_rate: number | null;
  pe_ttm: number | null;
  total_mv_yi: number | null;
  main_net_inflow_yi: number | null;
  main_net_inflow_pct: number | null;
  up_count: number | null;
  down_count: number | null;
}

export interface FundamentalsOverview {
  generated_at: string;
  macro: MacroIndicator[];
  boards: IndustryBoard[];
  board_count: number;
  errors: string[];
  disclaimer_cn: string;
}

export interface IndustryFlowPoint {
  date: string;
  main_yi: number | null;
  small_yi: number | null;
  medium_yi: number | null;
  large_yi: number | null;
  super_large_yi: number | null;
}

export interface IndustryFlowResponse {
  code: string;
  days: number;
  points: IndustryFlowPoint[];
}

// ---- 利率面板 (/api/fundamentals/rates) ----

export interface TreasurySide {
  cn_2y: number | null;
  cn_5y: number | null;
  cn_10y: number | null;
  cn_30y: number | null;
  cn_10_2_spread: number | null;
  us_2y: number | null;
  us_5y: number | null;
  us_10y: number | null;
  us_30y: number | null;
  us_10_2_spread: number | null;
}

export interface TreasuryYields {
  as_of_cn: string | null;
  as_of_us: string | null;
  cn: TreasurySide;
  us: TreasurySide;
  cn_us_spread_10y: number | null;
}

export interface RatesResponse {
  treasury: TreasuryYields;
  vix: { value: number; as_of: string } | null;
  margin: MarginData | null;
  /** 股债收益差（Fed Model 口径）= 盈利收益率(1/PE_TTM×100) − 10Y 国债收益率（%）。 */
  erp: { us: ErpData | null; cn: ErpData | null };
  /** 估值分位对照（不受利率水平污染），用于校正股债收益差的债券端污染。 */
  valuation: { us_cape: ValuationData | null; cn_pe: ValuationData | null };
  errors: string[];
}

/**
 * 估值分位快照。
 *
 * percentile 用标定窗口（口径可比），percentile_full 用全史（长周期背景）——
 * 两个都给，因为分位是取样窗口的函数，只报一个会误导。
 */
export interface ValuationData {
  value: number; // 现值（CAPE 或 PE_TTM，倍）
  as_of: string;
  percentile: number; // 标定窗口内分位（0–100，越高越贵）
  percentile_full: number; // 全史分位
  calib_from: string; // 标定窗口起始年份，如 "1950"
  calib_n: number; // 标定窗口样本数
  full_from: string; // 全史起始年份
  full_n: number;
}

/** 股债收益差（Fed Model 口径）单市场快照。ERP 的粗略代理，非严格 ERP。 */
export interface ErpData {
  earnings_yield: number; // 盈利收益率 %（1 / PE_TTM × 100）
  risk_free: number; // 10Y 国债收益率 %
  erp: number; // 股债收益差 %（= earnings_yield − risk_free）
  as_of: string | null;
  pe_ttm?: number | null; // A 股含 PE_TTM，美股无此字段
  ey_source: string; // 盈利收益率数据来源
}

// ---- 宏观利率历史序列（趋势图）----
export interface RatesHistorySeries {
  label: string;
  unit: string;
  dates: string[];
  values: number[];
}

export interface RatesHistoryResponse {
  as_of: string;
  series: Record<string, RatesHistorySeries>;
  errors: string[];
}

// ---- 宏观月度历史序列（PMI/CPI/PPI，趋势图）----
export interface MacroHistoryResponse {
  as_of: string;
  series: Record<string, RatesHistorySeries>;
  errors: string[];
}

// ---- 资金面 / 商品 / ETF 相对强度 ----

export interface MarginData {
  date: string;
  rzye_yi: number | null; // 融资余额（亿）
  rqye_yi: number | null; // 融券余额（亿）
  rzrqye_yi: number | null; // 融资融券余额（亿）
  buy_yi: number | null; // 融资买入额（亿）
  rzyezb_pct: number | null; // 融资余额占流通市值比（%）--标准风险口径
}

export interface CommodityRatios {
  copper_gold: number;
  crude_gold: number;
  copper: number;
  gold: number;
  crude: number;
}

export interface EtfItem {
  code: string;
  name: string;
  bias: string; // risk_on | risk_off | neutral
  ret_1m: number;
  rel_1m: number; // 相对 SPY 的超额（%）
}

// ---- 行业板块趋势工作台 (/api/sectors, research_proxy) ----
// 判定均为研究代理，不冒充 LEI 原始规则，不出买卖点。
export interface SectorTrendRow {
  code: string;
  name: string;
  level: 1 | 2 | 3;
  aliases: string[];
  parent: string | null;
  member_count: number;
  hit_count: number;
  // 阶段：②上升=markup / ①筑底=accumulation / ③派发=distribution / ④下降=decline / null=样本不足
  stage: "accumulation" | "markup" | "distribution" | "decline" | null;
  stage_basis: string[];
  // 道路层观察点（策略溯源 trading-spec §2.2「均线方向是道路」，research_proxy）
  dist_to_sma60_pct: number | null; // (价格/SMA60−1)×100，负值=距上穿还差多少
  checkpoints: SectorCheckpoint[]; // 道路确立三条件清单
  next_watch: string | null; // 一句话「下一观察点」
  next_watch_kind: "upgrade" | "risk" | "watch" | null;
  rs_pctile: number | null;
  rs_pctile_delta_20: number | null;
  rs_chg_20: number | null;
  rs_chg_60: number | null;
  rs_above_ma20: boolean | null;
  b20: number | null;
  b50: number | null;
  b200: number | null; // MA200 留痕中（320 日窗口内仅 121 天），前端显示「留痕中」
  nh60: number | null;
  breadth_divergence: boolean;
  signal_color: string | null; // green | gray | black | unknown
  signal_color_cn: string | null;
  ema20_slope_pct: number | null; // 跨板块可排序（百分比口径）
  long_trend_cn: string | null;
  macd_status: string | null;
  macd_label_cn: string | null;
  macd_detail_cn: string | null;
  macd_dimension: string | null;
  alignment_cn: string | null;
  close: number | null; // 板块等权指数最新收盘（供抽屉主图）
  // 当日参考（来自 clist 快照，非趋势判定依据）
  pct_change: number | null;
  pe_ttm: number | null;
  main_net_inflow_yi: number | null;
  up_count: number | null;
  down_count: number | null;
  total_mv_yi: number | null;
  // 资金流（单据规模代理：主力=超大+大单、散户=中+小单；research_proxy，只交叉验证不参与判定）
  flow_5d_main_yi: number | null;
  flow_20d_main_yi: number | null;
  flow_60d_main_yi: number | null;
  flow_5d_retail_yi: number | null;
  flow_20d_retail_yi: number | null;
  flow_60d_retail_yi: number | null;
  flow_20d_struct: string | null;
  flow_note_cn: string | null;
  flow_vs_stage: "confirm" | "conflict" | null;
  flow_vs_stage_cn: string | null;
  provenance: "research_proxy";
}

export interface SectorTrendResponse {
  as_of: string;
  date: string;
  trading_day: string;
  bench: { all_equal_close: number | null; hs300_close: number | null };
  boards: SectorTrendRow[];
  warnings: string[];
  errors: string[];
  research_proxy_note: string; // 常驻声明：等权合成/当前成分回溯含前视/不含北交所/MA200留痕中
}

export interface SectorHistoryPoint {
  date: string;
  close: number | null;
  b50: number | null;
  rs_pctile: number | null;
  rs_pctile_delta_20: number | null;
  stage: string | null;
}

export interface SectorMembersResponse {
  as_of: string;
  code: string;
  name: string | null;
  members: {
    symbol: string;
    name: string | null;
    pct_change: number | null;
    market_value_yi: number | null;
    in_kline_cache: boolean;
  }[];
}

// 道路确立三条件（价格>SMA60 / SMA60 斜率向上 / RS 强于基准）
export interface SectorCheckpoint {
  key: string;
  label: string;
  met: boolean;
  detail: string | null;
}

export interface SectorWatchItem {
  code: string;
  name: string | null;
  level: 1 | 2 | 3;
  stage: string | null;
  rs_pctile: number | null;
  rs_pctile_delta_20: number | null;
  b50: number | null;
  dist_to_sma60_pct: number | null;
  next_watch: string | null;
  next_watch_kind: "upgrade" | "risk" | "watch" | null;
  stage_basis: string[];
  // 资金流交叉验证（单据规模代理，research_proxy）
  flow_20d_main_yi: number | null;
  flow_20d_retail_yi: number | null;
  flow_vs_stage: "confirm" | "conflict" | null;
  flow_vs_stage_cn: string | null;
  flow_note_cn: string | null;
}

export interface SectorWatchlistResponse {
  as_of: string;
  trading_day: string;
  groups: {
    key: string;
    title: string;
    desc: string;
    items: SectorWatchItem[];
  }[];
  research_proxy_note: string;
}

// ---- 收盘简报 (/api/daily-brief, research_proxy) ----
export interface BriefAnomaly {
  market: string;
  metric: string;
  value: number;
  pctile_250d: number | null;
  day_change: number | null;
  note_cn: string;
}

export interface BriefWatchItem {
  symbol: string;
  display_name: string | null;
  verdict: string | null;
  verdict_cn: string | null;
  changes: string[];
  n_changes: number;
  is_new: boolean;
}

export interface BriefPoolItem {
  code: string;
  name: string | null;
  stage: string | null;
  rs_pctile: number | null;
  rs_pctile_delta_20: number | null;
  pe_ttm: number | null;
  flow_20d_main_yi: number | null;
  flow_vs_stage_cn: string | null;
  next_watch: string | null;
  tags: string[];
  streak: number;
}

export interface DailyBriefPayload {
  date: string;
  slot: string; // "1445" 盘中预判 | "1645" 收盘复核
  generated_at: string;
  env: {
    anomalies: BriefAnomaly[];
    breadth_context: {
      market: string;
      metric: string;
      date: string | null;
      value: number;
      day_change: number | null;
      pctile_250d: number | null;
    }[];
    macro: { line_cn?: string };
  };
  watchlist: {
    items: BriefWatchItem[];
    unchanged_count: number;
    sector_watch_count: number;
  };
  pool: { items: BriefPoolItem[]; codes: string[] };
  summary: { text: string; generated_by: "llm" | "template" };
}

export interface DailyBriefResponse {
  date: string;
  slot: string;
  brief: DailyBriefPayload;
  slots_available: string[];
}

// ---- agent 统一会话（spec 2026-08-23） ----

export interface TraceItem {
  label: string;
  rule_id: string | null;
  evidence_cn: string;
  research_proxy: boolean;
  principle_source: string | null;
}

export interface AgentChatRequest {
  session_id: string | null;
  context_kind: "symbol" | "global";
  symbol: string | null;
  message: string;
}

export interface AgentChatReply {
  session_id: string;
  reply: string;
  grounded: boolean;
  trace: TraceItem[];
}

export interface AgentSessionDTO {
  session_id: string;
  symbol: string | null;
  title_cn: string;
  last_active_at: string;
  last_message_cn: string;
}

export interface AgentMessageDTO {
  role: "user" | "assistant";
  content: string;
  grounded: boolean;
  created_at: string;
}

// ---- 宽度择时回测（timing backtest）----

export interface TimingInstrument {
  symbol: string;
  name: string;
  market: "cn" | "us";
  breadth: "cn_all" | "sp500";
  breadth_label: string;
  fee_default_bps: number;
  note: string;
  data_start: string | null;
  data_end: string | null;
  breadth_start: string | null;
}

export interface TimingPreset {
  key: string;
  label: string;
  description: string;
  source: string;
  params: Record<string, string | number | null>;
}

export interface TimingOptions {
  instruments: TimingInstrument[];
  indicators: Array<{ key: string; label: string }>;
  strategies: {
    ladder: {
      defaults: Record<string, string | number>;
      n_bands_choices: number[];
      edge_mode_choices: string[];
      direction_choices: string[];
    };
    reversal: {
      defaults: Record<string, string | number>;
      batch_mode_choices: string[];
    };
  };
  gate: { mode_choices: string[]; defaults: Record<string, string | number> };
  presets: TimingPreset[];
  disclaimers: string[];
}

export interface TimingTrade {
  date: string;
  prev_weight: number;
  new_weight: number;
  price: number;
  fee: number;
  turnover: number;
}

export interface TimingRunResult {
  run_id: string;
  created_at: string;
  symbol: string;
  name: string;
  params: Record<string, string | number | null>;
  metrics: Record<string, number>;
  yearly: Array<{ year: number; strategy: number; benchmark: number }>;
  trades: TimingTrade[];
  daily: {
    date: string[];
    equity: number[];
    benchmark: number[];
    weight: number[];
    open: number[];
    high: number[];
    low: number[];
    close: number[];
    breadth: Array<number | null>;
  };
}

export interface TimingRunSummary {
  run_id: string;
  created_at: string;
  symbol: string;
  name: string;
  params: Record<string, string | number | null>;
  metrics: Record<string, number>;
}

export interface TimingSignal {
  key: string;
  label: string;
  symbol?: string;
  indicator?: string;
  as_of?: string;
  breadth_now?: number | null;
  weight_now?: number;
  trigger?: string;
  levels?: number[];
  full_cagr?: number;
  full_bh_cagr?: number;
  full_mdd?: number;
  n_trades?: number;
  recent_trades?: TimingTrade[];
  error?: string;
}
