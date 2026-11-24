import { request } from "./client";

export interface SymbolSmartPrompt {
  symbol: string;
  name: string;
  kind: "stock" | "etf" | "us" | "off_fund";
  available: boolean;
  reason?: string;
  as_of?: string;
  close?: number;
  ma20?: number;
  ma60?: number;
  ma200?: number | null;
  main_cost_peak?: number;
  profit_holders_pct?: number;
  dist_ma200_pct?: number | null;
  drawdown_1y_pct?: number;
  daily_vol_pct?: number;
  volatility_note_cn?: string;
  suggested_max_position_pct?: number;
  sizing_advice_cn?: string;
  quality_badge?: string;
  quality_detail?: string;
  buy_light?: string;
  buy_advice?: string;
  hold_stage?: string;
  active_stop_price?: number | null;
  stage1_stop_price?: number;
  stage2_ma60_price?: number;
  hold_advice?: string;
}

export interface HoldingHealthItemDTO {
  group_title: string;
  fund_name: string;
  codes_display: string;
  market_value: number;
  weight_in_account_pct: number;
  account_return_pct: number;
  dist_ma200_pct: number | null;
  drawdown_from_1y_high_pct: number | null;
  above_ma20: boolean | null;
  health_light: string;
  action_advice_cn: string;
  penetration_truth_cn: string;
}

export interface UrgentHoldingAction {
  level: "urgent" | "warn" | "opportunity" | "switch";
  code: string;
  name: string;
  title: string;
  detail: string;
}

export interface PortfolioSmartPromptsResponse {
  generated_at: string;
  urgent_actions: UrgentHoldingAction[];
  portfolio_diagnosis: {
    total_market_value: number;
    logical_positions_count: number;
    paycheck_add_ready: string[];
    switch_window_ready: string[];
    summary_tips: string[];
    items: HoldingHealthItemDTO[];
  };
}

export interface CandidatePickItem {
  code: string;
  name: string;
  kind?: string;
  as_of: string;
  close: number;
  stop_ref?: number;
  plain_reason: string;
}

export interface IdleCashHarborAsset {
  code: string;
  symbol: string;
  name: string;
  available: boolean;
  as_of: string | null;
  close: number | null;
  ma60: number | null;
  dist_ma60_pct: number | null;
  is_steady: boolean;
  status_cn: string;
}

export interface IdleCashHarborStatus {
  as_of: string | null;
  headline_cn: string;
  allocation_cn: string;
  gold: IdleCashHarborAsset;
  high_dividend: IdleCashHarborAsset;
}

export interface OnePageOverviewResponse {
  generated_at: string;
  market_weather: {
    cn_plain_verdict: string;
    us_plain_verdict: string;
  };
  idle_cash_harbor?: IdleCashHarborStatus;
  left_portfolio: PortfolioSmartPromptsResponse;
  right_picks: {
    right_side_sector_funds: CandidatePickItem[];
    left_side_turnaround_funds: CandidatePickItem[];
    crowded_warnings: Array<{ code: string; name: string; note: string }>;
    industry_leaders: CandidatePickItem[];
    small_giants: CandidatePickItem[];
  };
}

export const smartPromptsApi = {
  symbol: (symbol: string, entryPrice?: number | null) => {
    const qs = entryPrice && entryPrice > 0 ? `?entry_price=${encodeURIComponent(String(entryPrice))}` : "";
    return request<SymbolSmartPrompt>(`/smart-prompts/symbol/${encodeURIComponent(symbol)}${qs}`);
  },
  portfolio: (force = false) =>
    request<PortfolioSmartPromptsResponse>(`/smart-prompts/portfolio${force ? "?force=true" : ""}`),
  onePage: (top = 8, force = false) =>
    request<OnePageOverviewResponse>(`/smart-prompts/one-page?top=${top}${force ? "&force=true" : ""}`),
};
