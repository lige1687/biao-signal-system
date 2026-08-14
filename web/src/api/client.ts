import type {
  ActionItem,
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
  SubscribeWatchRequest,
  SymbolDetail,
  TodayOpportunityResponse,
  WatchSubscription,
  WatchlistGroup,
  WatchlistItem,
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
  return (await resp.json()) as T;
}

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
  marketContextBreadthHistory: (marketId: string, lookbackDays = 120) =>
    request<BreadthHistoryResponse>(
      `/market-context/breadth-history?market_id=${encodeURIComponent(marketId)}&lookback_days=${lookbackDays}`,
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
  buyPointChat: (symbol: string, message: string) =>
    request<BuyPointChatReply>(
      `/symbols/${encodeURIComponent(symbol)}/buy-point-chat`,
      { method: "POST", body: JSON.stringify({ message }) },
    ),
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
  ratesHistory: (lookbackDays = 730) =>
    request<RatesHistoryResponse>(
      `/fundamentals/rates-history?lookback_days=${lookbackDays}`,
    ),
  macroHistory: (pageSize = 60) =>
    request<MacroHistoryResponse>(
      `/fundamentals/macro-history?page_size=${pageSize}`,
    ),
  commodities: (refresh = false) =>
    request<{ commodities: CommodityRatios | null }>(
      `/fundamentals/commodities${refresh ? "?refresh=true" : ""}`,
    ),
  etfStrength: (refresh = false) =>
    request<{ etf: { items: EtfItem[]; regime: string; spy_1m: number } | null }>(
      `/fundamentals/etf-strength${refresh ? "?refresh=true" : ""}`,
    ),
};
