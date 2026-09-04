import type {
  ActionItem,
  AgentChatReply,
  AgentChatRequest,
  AgentMessageDTO,
  AgentSessionDTO,
  AShareBreadthResponse,
  BreadthHistoryResponse,
  BuyPointChatReply,
  BuyPointReview,
  CheckReport,
  ConformanceReport,
  CreateHoldingWatchPayload,
  CreatePlanPayload,
  DashboardResponse,
  DraftUpdatePayload,
  EventItem,
  ForwardStatsResponse,
  FundamentalsOverview,
  GlobalStripResponse,
  CommodityRatios,
  EtfItem,
  IndustryFlowResponse,
  MacroHistoryResponse,
  RatesResponse,
  RatesHistoryResponse,
  UsMacroResponse,
  XlyXlpRatio,
  MarketContextFull,
  MarketDataStatus,
  Plan,
  PlanAlert,
  PlanChatReply,
  PlansSummary,
  PromoteWatchRequest,
  PromoteWatchResponse,
  ResolveResult,
  ScanResponse,
  SentimentHistoryResponse,
  PositionBandResponse,
  CorrelationMapResponse,
  SignalsToday,
  SubscribeWatchRequest,
  SymbolDetail,
  TodayOpportunityResponse,
  WatchSubscription,
  WatchlistGroup,
  WatchlistItem,
  SectorTrendResponse,
  SectorHistoryPoint,
  SectorMembersResponse,
  SectorWatchlistResponse,
  DailyBriefResponse,
  SentimentIngest,
  BacktestOptions,
  BacktestRunSummary,
  BacktestRunResult,
  TimingOptions,
  TimingRunResult,
  TimingRunSummary,
  TimingSignal,
  TimingPortfolio,
  TimingEtfDefense,
  TimingPortfolioEquity,
  NewsDigest,
  NewsItemsResponse,
  NewsStatus,
  NewsWatchlistBrief,
  ExperimentsResponse,
  ExperimentReportDetail,
} from "../types";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    let body: unknown = null;
    try {
      body = await resp.json();
      const d = (body as { detail?: unknown })?.detail;
      if (d != null) {
        // detail 可能是字符串（普通错误）或 {message, hard_issues}（confirm 硬阻断）。
        detail =
          typeof d === "string"
            ? d
            : (d as { message?: string })?.message ?? JSON.stringify(d);
      }
    } catch {
      /* 保持默认错误 */
    }
    const err = new Error(detail);
    // 保留完整响应体，供调用方读取结构化错误（如 422 的 hard_issues）。
    (err as Error & { body?: unknown }).body = body;
    throw err;
  }
  if (resp.status === 204) return undefined as T;
  // 200 但返回 HTML = 这个后端没有该路由, 被 SPA 兜底接走了。
  // 最常见的原因是页面连到了一个旧的后端实例(比如手动 --port 起的、忘了关),
  // 它读同一份 dist 所以界面是新的, 路由表却是旧的。直接把源点报出来, 免得
  // 只看到一句 "Unexpected token '<'" 无从下手。
  const ctype = resp.headers.get("content-type") ?? "";
  if (!ctype.includes("json")) {
    throw new Error(
      `接口返回了 ${ctype || "非 JSON"} 而不是 JSON —— ` +
        `当前页面来自 ${window.location.origin}，请求 ${resp.url}。` +
        `很可能这个后端没有该接口（旧实例/未重启）：` +
        `请确认页面开在 biao 启动的 http://localhost:5173，并执行 biao restart。`,
    );
  }
  return (await resp.json()) as T;
}


export const backtestApi = {
  options: () => request<BacktestOptions>("/backtest/options"),
  createRun: (body: {
    symbols?: string[] | null;
    module?: string;
    rr_min?: number | null;
    entry_variant?: string | null;
    exit_variant: string;
    fee_label: string;
    overrides?: Record<string, number>;
    volume_confirm?: boolean;
    volume_confirm_window?: number;
    profile_filter?: string;
  }) =>
    request<{ run_id: string }>("/backtest/runs", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listRuns: () => request<BacktestRunSummary[]>("/backtest/runs"),
  getRun: (runId: string) => request<BacktestRunResult | BacktestRunSummary>(`/backtest/runs/${runId}`),
};

export const timingBacktestApi = {
  options: () => request<TimingOptions>("/timing-backtest/options"),
  signals: () => request<TimingSignal[]>("/timing-backtest/signals"),
  portfolio: () => request<TimingPortfolio>("/timing-backtest/portfolio"),
  etfDefense: (symbol: string) =>
    request<TimingEtfDefense>(`/timing-backtest/etf-defense?symbol=${symbol}`),
  portfolioEquity: () => request<TimingPortfolioEquity>("/timing-backtest/portfolio-equity"),
  createRun: (body: Record<string, string | number | null>) =>
    request<TimingRunResult>("/timing-backtest/runs", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listRuns: () => request<TimingRunSummary[]>("/timing-backtest/runs"),
  getRun: (runId: string) => request<TimingRunResult>(`/timing-backtest/runs/${runId}`),
};

export const api = {
  dashboard: (group?: "index" | "watchlist", refresh = false) => {
    const params = new URLSearchParams();
    if (group) params.set("group", group);
    if (refresh) params.set("refresh", "true");
    const qs = params.toString();
    return request<DashboardResponse>(`/dashboard/cards${qs ? `?${qs}` : ""}`);
  },
  refresh: (symbols?: string[]) =>
    request<DashboardResponse>(`/refresh`, {
      method: "POST",
      body: JSON.stringify({ symbols: symbols ?? null }),
    }),
  watchlist: () => request<WatchlistItem[]>(`/watchlist`),
  addWatchlist: (symbol: string, groupId?: number | null) =>
    request<WatchlistItem>(`/watchlist`, {
      method: "POST",
      body: JSON.stringify({ symbol, group_id: groupId ?? null }),
    }),
  moveToGroup: (symbol: string, groupId: number | null) =>
    request<WatchlistItem>(`/watchlist/${encodeURIComponent(symbol)}/group`, {
      method: "POST",
      body: JSON.stringify({ group_id: groupId }),
    }),
  groups: () => request<WatchlistGroup[]>(`/groups`),
  createGroup: (name: string) =>
    request<WatchlistGroup>(`/groups`, { method: "POST", body: JSON.stringify({ name }) }),
  renameGroup: (groupId: number, name: string) =>
    request<WatchlistGroup>(`/groups/${groupId}`, {
      method: "PATCH",
      body: JSON.stringify({ name }),
    }),
  deleteGroup: (groupId: number) =>
    request<void>(`/groups/${groupId}`, { method: "DELETE" }),
  removeWatchlist: (symbol: string) =>
    request<void>(`/watchlist/${encodeURIComponent(symbol)}`, { method: "DELETE" }),
  resolve: (q: string, probe = false) =>
    request<ResolveResult>(`/symbols/resolve?q=${encodeURIComponent(q)}&probe=${probe}`),
  sectors: () =>
    request<{
      sectors: { code: string; name: string; symbol: string }[];
      indices: { code: string; name: string; symbol: string }[];
      us_etfs: { code: string; name: string; symbol: string }[];
      concepts: { code: string; name: string; symbol: string }[];
    }>(`/sectors`),
  events: (
    symbol: string,
    opts: { structureId?: string; onDate?: string; ruleId?: string; limit?: number } = {},
  ) => {
    const q = new URLSearchParams();
    if (opts.structureId) q.set("structure_id", opts.structureId);
    if (opts.onDate) q.set("on_date", opts.onDate);
    if (opts.ruleId) q.set("rule_id", opts.ruleId);
    if (opts.limit) q.set("limit", String(opts.limit));
    return request<EventItem[]>(
      `/symbols/${encodeURIComponent(symbol)}/events?${q.toString()}`,
    );
  },
  detail: (symbol: string, refresh = false) =>
    request<SymbolDetail>(
      `/symbols/${encodeURIComponent(symbol)}/detail${refresh ? "?refresh=true" : ""}`,
    ),
  marketContextFull: (symbol: string) =>
    request<MarketContextFull>(
      `/symbols/${encodeURIComponent(symbol)}/market-context/full`,
    ),
  marketBreadthHistory: (symbol: string, marketId: string, lookbackDays = 120) =>
    request<BreadthHistoryResponse>(
      `/symbols/${encodeURIComponent(symbol)}/market-context/breadth-history?market_id=${encodeURIComponent(
        marketId,
      )}&lookback_days=${lookbackDays}`,
    ),
  marketDataStatus: (marketId: string) =>
    request<MarketDataStatus>(
      `/market-context/data-status?market_id=${encodeURIComponent(marketId)}`,
    ),
  marketContextGlobalStrip: () =>
    request<GlobalStripResponse>(`/market-context/global-strip`),
  marketContextSentimentHistory: (series: "naaim" | "aaii", limit = 1040) =>
    request<SentimentHistoryResponse>(
      `/market-context/sentiment/history?series=${series}&limit=${limit}`,
    ),
  updateSentiment: (payload: SentimentIngest) =>
    request<{ ok: boolean; path: string }>(`/market-context/sentiment`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  marketContextBreadthHistory: (marketId: string, lookbackDays = 1260) =>
    request<BreadthHistoryResponse>(
      `/market-context/breadth-history?market_id=${encodeURIComponent(marketId)}&lookback_days=${lookbackDays}`,
    ),
  // 真全A市场宽度（涨跌家数 + 可选 MA 上方占比），替换原 fixture 假样本
  marketContextAShareBreadth: (includeMa = false) =>
    request<AShareBreadthResponse>(
      `/market-context/a-share-breadth${includeMa ? "?include_ma=true" : ""}`,
    ),
  marketContextForwardStats: (
    marketId: string,
    percentile: number,
    bucketHalfWidth = 5,
  ) =>
    request<ForwardStatsResponse>(
      `/market-context/forward-stats?market_id=${encodeURIComponent(marketId)}&percentile=${percentile}&bucket_half_width=${bucketHalfWidth}`,
    ),
  // ---- 计划台账 / 监督员 agent ----
  listPlans: (params: { symbol?: string; state?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.symbol) q.set("symbol", params.symbol);
    if (params.state) q.set("state", params.state);
    const qs = q.toString();
    return request<Plan[]>(`/plans${qs ? `?${qs}` : ""}`);
  },
  getPlan: (planId: string) => request<Plan>(`/plans/${encodeURIComponent(planId)}`),
  plansSummary: () => request<PlansSummary>(`/plans/summary`),
  createPlan: (body: CreatePlanPayload) =>
    request<Plan>("/plans", { method: "POST", body: JSON.stringify(body) }),
  createHoldingWatch: (body: CreateHoldingWatchPayload) =>
    request<Plan>("/plans/holding-watch", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  confirmPlan: (planId: string) =>
    request<Plan>(`/plans/${encodeURIComponent(planId)}/confirm`, { method: "POST" }),
  conformance: (planId: string) =>
    request<ConformanceReport>(
      `/plans/${encodeURIComponent(planId)}/conformance`,
    ),
  updateDraft: (planId: string, body: DraftUpdatePayload) =>
    request<Plan>(`/plans/${encodeURIComponent(planId)}/draft`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  planAlerts: (planId: string) =>
    request<PlanAlert[]>(`/plans/${encodeURIComponent(planId)}/alerts`),
  planActions: (planId: string, state?: string) => {
    const qs = state ? `?state=${encodeURIComponent(state)}` : "";
    return request<ActionItem[]>(
      `/plans/${encodeURIComponent(planId)}/actions${qs}`,
    );
  },
  doneAction: (planId: string, actionId: string) =>
    request<ActionItem>(
      `/plans/${encodeURIComponent(planId)}/actions/${encodeURIComponent(actionId)}/done`,
      { method: "POST" },
    ),
  deferAction: (
    planId: string,
    actionId: string,
    body: { reason_cn: string; resume_on: Record<string, unknown> },
  ) =>
    request<ActionItem>(
      `/plans/${encodeURIComponent(planId)}/actions/${encodeURIComponent(actionId)}/defer`,
      { method: "POST", body: JSON.stringify(body) },
    ),
  planChat: (planId: string, message: string) =>
    request<PlanChatReply>(`/plans/${encodeURIComponent(planId)}/chat`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  // ---- 买点审阅 / 扫描 / 问答 ----
  buyPointReview: (symbol: string, refresh = false) =>
    request<BuyPointReview>(
      `/symbols/${encodeURIComponent(symbol)}/buy-point-review${refresh ? "?refresh=true" : ""}`,
    ),
  opportunityScan: (symbols?: string, onlyWithCandidates = true) => {
    const q = new URLSearchParams();
    if (symbols) q.set("symbols", symbols);
    if (!onlyWithCandidates) q.set("only_with_candidates", "false");
    const qs = q.toString();
    return request<ScanResponse>(`/opportunities/scan${qs ? `?${qs}` : ""}`);
  },
  todayOpportunities: () => request<TodayOpportunityResponse>(`/opportunities/today`),
  refreshTodayOpportunities: () =>
    request<TodayOpportunityResponse>(`/opportunities/today/refresh`, { method: "POST" }),
  signalsToday: () => request<SignalsToday>(`/signals/today`),
  refreshSignals: (asOf: "intraday" | "close" = "close") =>
    request<SignalsToday>(`/signals/today/refresh?as_of=${asOf}`, { method: "POST" }),
  signalsDay: (day: string) => request<SignalsToday>(`/signals/day/${day}`),
  replayDay: (day: string) =>
    request<SignalsToday>(`/signals/day/${day}/replay`, { method: "POST" }),
  buyPointChat: (symbol: string, message: string) =>
    request<BuyPointChatReply>(
      `/symbols/${encodeURIComponent(symbol)}/buy-point-chat`,
      { method: "POST", body: JSON.stringify({ message }) },
    ),
  // ---- agent 统一会话 ----
  agentChat: (body: AgentChatRequest) =>
    request<AgentChatReply>(`/agent/chat`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  agentSessions: (symbol?: string) =>
    request<AgentSessionDTO[]>(
      `/agent/sessions${symbol ? `?symbol=${encodeURIComponent(symbol)}` : ""}`,
    ),
  agentSessionMessages: (sessionId: string) =>
    request<AgentMessageDTO[]>(`/agent/sessions/${encodeURIComponent(sessionId)}/messages`),
  agentCreateSession: (body: { symbol: string | null; title_cn: string }) =>
    request<AgentSessionDTO>(`/agent/sessions`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  // ---- 提醒订阅 (Step 2) ----
  subscribeWatch: (body: SubscribeWatchRequest) =>
    request<WatchSubscription>("/watch/subscribe", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listWatches: (params: { state?: string; symbol?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.state) q.set("state", params.state);
    if (params.symbol) q.set("symbol", params.symbol);
    const qs = q.toString();
    return request<WatchSubscription[]>(`/watch${qs ? `?${qs}` : ""}`);
  },
  getWatch: (watchId: string) =>
    request<WatchSubscription>(`/watch/${encodeURIComponent(watchId)}`),
  dismissWatch: (watchId: string, reason: string) =>
    request<WatchSubscription>(
      `/watch/${encodeURIComponent(watchId)}/dismiss`,
      { method: "POST", body: JSON.stringify({ reason }) },
    ),
  promoteWatch: (watchId: string, body: PromoteWatchRequest) =>
    request<PromoteWatchResponse>(
      `/watch/${encodeURIComponent(watchId)}/promote`,
      { method: "POST", body: JSON.stringify(body) },
    ),
  triggerWatchCheck: () =>
    request<CheckReport>("/watch/check-now", { method: "POST" }),
};

// ---- 基本面参考层 ----
export const fundamentalsApi = {
  overview: (refresh = false) =>
    request<FundamentalsOverview>(`/fundamentals/overview${refresh ? "?refresh=true" : ""}`),
  industryFlow: (code: string, days = 20) =>
    request<IndustryFlowResponse>(
      `/fundamentals/industry/${encodeURIComponent(code)}/flow?days=${days}`,
    ),
  rates: (refresh = false) =>
    request<RatesResponse>(`/fundamentals/rates${refresh ? "?refresh=true" : ""}`),
  ratesHistory: (lookbackDays = 1095) =>
    request<RatesHistoryResponse>(
      `/fundamentals/rates-history?lookback_days=${lookbackDays}`,
    ),
  macroHistory: (pageSize = 60) =>
    request<MacroHistoryResponse>(
      `/fundamentals/macro-history?page_size=${pageSize}`,
    ),
  overlayHistory: (years = 20) =>
    request<RatesHistoryResponse>(
      `/fundamentals/overlay-history?years=${years}`,
    ),
  commodities: (refresh = false) =>
    request<{ commodities: CommodityRatios | null }>(
      `/fundamentals/commodities${refresh ? "?refresh=true" : ""}`,
    ),
  positionBand: () => request<PositionBandResponse>("/fundamentals/position-band"),
  correlationMap: () => request<CorrelationMapResponse>("/fundamentals/correlation-map"),
  etfStrength: (refresh = false) =>
    request<{
      etf: {
        dates?: string[];
        items: EtfItem[];
        regime: string;
        spy_1m: number;
        xly_xlp?: XlyXlpRatio | null;
      } | null;
    }>(`/fundamentals/etf-strength${refresh ? "?refresh=true" : ""}`),
  usMacro: (refresh = false) =>
    request<UsMacroResponse>(`/fundamentals/us-macro${refresh ? "?refresh=true" : ""}`),
};

// ---- 行业板块趋势工作台 ----
export const sectorsApi = {
  trend: (refresh = false, level = "all") =>
    request<SectorTrendResponse>(
      `/sectors/trend?level=${level}${refresh ? "&refresh=true" : ""}`,
    ),
  history: (code: string, days = 250) =>
    request<{ code: string; points: SectorHistoryPoint[] }>(
      `/sectors/${encodeURIComponent(code)}/history?days=${days}`,
    ),
  members: (code: string, limit = 50) =>
    request<SectorMembersResponse>(
      `/sectors/${encodeURIComponent(code)}/members?limit=${limit}`,
    ),
  watchlist: (topN = 5) =>
    request<SectorWatchlistResponse>(`/sectors/watchlist?top_n=${topN}`),
};

// ---- 收盘简报 ----
export const dailyBriefApi = {
  latest: () => request<DailyBriefResponse>("/daily-brief/latest"),
  byDate: (date: string, slot?: string) =>
    request<DailyBriefResponse>(
      `/daily-brief/${encodeURIComponent(date)}${slot ? `?slot=${slot}` : ""}`,
    ),
  dates: () => request<{ dates: string[] }>("/daily-brief/dates"),
};

// ---- 因子观测台（factor panel，本机 WIP）----
export interface FactorMeta {
  label: string;
  formula: string;
  verdict: string;
  verdict_level: "pass" | "weak" | "inverse" | "fail";
  evidence: string;
  usage: string;
}

export interface FactorRow {
  code: string;
  name: string | null;
  group: string;
  subgroup: string;
  as_of: string;
  close: number | null;
  rv20_ann: number | null;
  rv_pct: number | null;
  mom_121: number | null;
  mom_20: number | null;
  mom_20_group_pct: number | null;
  mom_121_rank?: number | null;
  adx14: number | null;
  vol_ok: boolean | null;
  above_ema20: boolean | null;
  above_ema120: boolean | null;
  notes: string[];
}

export interface FactorPanelResponse {
  generated_at: string;
  provenance: string;
  research_proxy_note: string;
  study_date: string;
  study_ref: string;
  data_as_of: string | null;
  counts: { symbols: number; sectors: number; skipped_too_short_or_broken: string[] };
  market: {
    market_rv_pct: number | null;
    market_rv20_ann: number | null;
    market_as_of: string | null;
    market_basis: string;
  } | null;
  factors: Record<string, FactorMeta>;
  symbols: FactorRow[];
  sectors: FactorRow[];
}

export const factorsApi = {
  panel: (refresh = false) =>
    request<FactorPanelResponse>(`/factors/panel${refresh ? "?refresh=true" : ""}`),
};

export const newsApi = {
  items: (params: {
    category?: string; q?: string; source?: string; symbol?: string;
    direction?: string; from?: string; to?: string;
    scored?: string; min_importance?: number; limit?: number; offset?: number;
  }) => {
    const search = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== "") search.set(k, String(v));
    }
    return request<NewsItemsResponse>(`/news/items?${search.toString()}`);
  },
  digests: (limit = 7) => request<{ digests: NewsDigest[] }>(`/news/digests?limit=${limit}`),
  watchlistBrief: (days = 3) =>
    request<NewsWatchlistBrief>(`/news/watchlist-brief?days=${days}`),
  run: (full = false) => request<{ run: string }>(`/news/run${full ? "?full=true" : ""}`, { method: "POST" }),
  status: () => request<NewsStatus>("/news/status"),
};

export const experimentsApi = {
  list: () => request<ExperimentsResponse>("/experiments"),
  detail: (name: string) =>
    request<ExperimentReportDetail>(`/experiments/${name}`),
};
