export type ObservationRange = "since_start" | "common";

export interface AccountPoint {
  date: string;
  equity: number | null;
  cash: number | null;
  receivable: number | null;
  market_value: number | null;
  nav: number | null;
  drawdown_pct: number | null;
  exposure_pct: number | null;
  fees: number | null;
  valid: boolean;
  stale: boolean;
  source_time: string | null;
  provisional: boolean;
}

export interface StrategyAccount {
  id: string;
  name: string;
  kind: string;
  role: string;
  status: "not_started" | "waiting_quote" | "waiting_execution" | "observing" | "blocked" | "external_pending" | "stale";
  reasons: string[];
  rules: Record<string, string | string[] | null>;
  frozen_at: string | null;
  started_at: string | null;
  first_decision_at: string | null;
  first_fill_at: string | null;
  metrics: {
    cumulative_return_pct: number | null;
    annualized_return_pct: number | null;
    sharpe: number | null;
    max_drawdown_pct: number | null;
    observations: number;
    wait_days?: number | null;
    reason: string | null;
  };
  series: AccountPoint[];
  holdings: Array<{ symbol: string; shares: number; last: number | null; market_value: number | null }>;
  orders: Array<{ id: string; symbol: string; created_at: string; requested_qty: number; filled_qty: number; status: string }>;
}

export interface StrategyDecision {
  id: string;
  at: string;
  kind: string;
  account_id: string | null;
  observation_id: string | null;
  payload: Record<string, unknown>;
}

export interface StrategyDashboard {
  schema_version: number;
  generated_at: string;
  range: ObservationRange;
  run: {
    status: "not_started" | "waiting_quote" | "observing" | "stale";
    frozen_at: string | null;
    started_at: string | null;
    last_run_at: string | null;
    last_source_at: string | null;
    next_run_at: string | null;
    runner: {
      pid?: number;
      mode?: string;
      status?: string;
      heartbeat_at?: string | null;
      next_run_at?: string | null;
      last_success_at?: string | null;
      last_error?: string | null;
      schedule_note?: string | null;
      active?: boolean;
      pid_alive?: boolean;
    } | null;
  };
  accounts: StrategyAccount[];
  decisions: StrategyDecision[];
  health: string[];
  sources: Array<{ id: string; source_time: string; received_at: string; hash?: string }>;
  pending: string[];
  reconciliation?: { passed?: boolean; status?: string; checked_at?: string; reasons?: string[] };
}
