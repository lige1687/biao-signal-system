import type {
  BreadthHistoryResponse,
  DashboardResponse,
  EventItem,
  ForwardStatsResponse,
  GlobalStripResponse,
  MarketContextFull,
  MarketDataStatus,
  ResolveResult,
  SymbolDetail,
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
    try {
      const body = await resp.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      /* 保持默认错误 */
    }
    throw new Error(detail);
  }
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

export const api = {
  dashboard: (refresh = false) =>
    request<DashboardResponse>(`/dashboard/cards${refresh ? "?refresh=true" : ""}`),
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
  marketContextForwardStats: (
    marketId: string,
    percentile: number,
    bucketHalfWidth = 5,
  ) =>
    request<ForwardStatsResponse>(
      `/market-context/forward-stats?market_id=${encodeURIComponent(marketId)}&percentile=${percentile}&bucket_half_width=${bucketHalfWidth}`,
    ),
};
