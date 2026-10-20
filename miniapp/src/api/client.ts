import Taro from '@tarojs/taro'
import { getBaseUrl } from '../store/settings'
import type {
  SignalsToday,
  DashboardResponse,
  DailyBriefResponse,
  SymbolDetail,
  TodayOpportunityResponse,
  GlobalStripResponse,
  Plan,
  PlansSummary,
  PlanAlert,
  ActionItem,
} from '../types'

export class ApiError extends Error {
  status: number
  body: unknown
  constructor(message: string, status: number, body?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

interface ReqOpts {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: unknown
  timeout?: number
}

async function request<T>(path: string, opts: ReqOpts = {}): Promise<T> {
  const base = await getBaseUrl()
  let res: any
  try {
    res = await Taro.request({
      url: `${base}${path}`,
      method: opts.method || 'GET',
      data: opts.data as Record<string, unknown> | undefined,
      header: { 'Content-Type': 'application/json' },
      // 微信 wx.request 超时上限 60s，再大也会被截断；cards/detail 首屏冷拉可达 60s
      timeout: opts.timeout ?? 60000,
    })
  } catch (e) {
    // Taro.request 在网络错/超时/DNS 失败时会 reject 非 ApiError 对象，
    // 统一包成 ApiError 并提取 errMsg/message，避免页面 catch 拿到 [object Object]。
    const anyE = e as { errMsg?: string; message?: string } | null
    const msg = anyE?.errMsg || anyE?.message || '网络错误，无法连接后端'
    throw new ApiError(msg, 0, { network_error: true })
  }
  if (res.statusCode >= 200 && res.statusCode < 300) {
    return res.data as T
  }
  // 显式把后端错误（含 DATA_UNAVAILABLE）原样抛出，由页面展示，不静默。
  let detail = `HTTP ${res.statusCode}`
  const d = (res.data as { detail?: unknown })?.detail
  if (d != null) {
    detail =
      typeof d === 'string' ? d : ((d as { message?: string })?.message ?? JSON.stringify(d))
  }
  throw new ApiError(detail, res.statusCode, res.data)
}

// 所有路由前缀 /api；判定权在 Python 后端，这里只做展示与转发。
export const api = {
  /** GET /api/signals/today —— 今日自选信号（买点 daily_opportunity_scan + 卖点 signal_alerts） */
  signalsToday: () => request<SignalsToday>('/api/signals/today'),

  /** POST /api/signals/today/refresh?as_of=close|intraday —— 立即重扫（买+卖） */
  refreshSignals: (asOf: 'intraday' | 'close' = 'close') =>
    request<SignalsToday>(`/api/signals/today/refresh?as_of=${asOf}`, {
      method: 'POST',
      data: {},
    }),

  /** GET /api/dashboard/cards —— 自选看板卡片墙（可只取 index / watchlist） */
  dashboardCards: (group?: 'index' | 'watchlist') => {
    const qs = group ? `?group=${group}` : ''
    return request<DashboardResponse>(`/api/dashboard/cards${qs}`, { timeout: 60000 })
  },

  /** GET /api/daily-brief/latest —— 收盘简报（1445 盘中预判 / 1645 收盘复核两槽位） */
  dailyBrief: () => request<DailyBriefResponse>('/api/daily-brief/latest'),

  /** GET /api/symbols/{symbol}/detail —— 标的详情（不含任何前端判定） */
  symbolDetail: (symbol: string) =>
    request<SymbolDetail>(`/api/symbols/${encodeURIComponent(symbol)}/detail`, { timeout: 60000 }),

  /** GET /api/opportunities/today —— 今日机会雷达（读库快照，launchd 15:00 写入） */
  opportunitiesToday: () => request<TodayOpportunityResponse>('/api/opportunities/today'),

  /** POST /api/opportunities/today/refresh —— 立即重扫自选并落库 */
  refreshOpportunities: () =>
    request<TodayOpportunityResponse>('/api/opportunities/today/refresh', {
      method: 'POST',
      data: {},
      timeout: 60000,
    }),

  /** GET /api/market-context/global-strip —— 全球市场宽度条（各市场面板 + 情绪） */
  globalStrip: () => request<GlobalStripResponse>('/api/market-context/global-strip', { timeout: 30000 }),

  /** GET /api/plans —— 计划列表（可选状态过滤） */
  plans: (state?: string) =>
    request<Plan[]>(`/api/plans${state ? `?state=${encodeURIComponent(state)}` : ''}`),

  /** GET /api/plans/summary —— 顶栏红点（未处理待办 / 活跃计划 / 今日机会） */
  plansSummary: () => request<PlansSummary>('/api/plans/summary'),

  /** GET /api/plans/{id}/alerts —— 计划提醒（block/remind/hint，判定在后端） */
  planAlerts: (planId: string) =>
    request<PlanAlert[]>(`/api/plans/${encodeURIComponent(planId)}/alerts`, { timeout: 60000 }),

  /** GET /api/plans/{id}/actions —— 计划待办（可选状态过滤） */
  planActions: (planId: string, state?: string) =>
    request<ActionItem[]>(
      `/api/plans/${encodeURIComponent(planId)}/actions${state ? `?state=${encodeURIComponent(state)}` : ''}`,
    ),
}
