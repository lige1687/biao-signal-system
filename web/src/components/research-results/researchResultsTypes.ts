export const OLD_MODULE_A_REPORT = "docs/experiments/module-a-strategy-readiness-2026-10-17.md";
export const RULE_AUDIT_REPORT = "docs/experiments/module-a-rule-audit-2026-10-18.md";
export const RESEARCH_RESULTS_SCHEMA = "research-results/module-a/1";

export type ModuleAPolicy = "buy_hold" | "a_fixed" | "a_risk" | "a_risk_degrade";

export interface ResearchResultsPayload {
  schema_version: typeof RESEARCH_RESULTS_SCHEMA;
  report_names: string[];
  generated_at: string;
  sources: { path: string; sha256: string }[];
  scope: string;
  limitations: string[];
  coverage: { label: string; value: string; note?: string }[];
  versions: { id: string; label: string; note: string; funnel: { label: string; count: number; unit: string }[] }[];
  groups: { id: string; label: string; count: number }[];
  runs: {
    version: string;
    group: string;
    policy: ModuleAPolicy;
    cost_bps: number;
    summary: {
      total_return: number | null;
      max_observed_drawdown: number | null;
      average_exposure: number | null;
      entries: number;
      exits: number;
      nav_gap_days: number;
      fees_total: number | null;
      degraded_entries: number | null;
      execution_summary: { accepted_signals: number; bought: number; rejected: number; already_held: number; unknown: number } | null;
    };
    daily: { date: string; nav: number | null; exposure: number | null }[];
    drawdown: (number | null)[];
    assets: { name: string; contribution: number | null }[];
    monthly?: { month: string; return: number | null }[];
  }[];
  cases: {
    id: string;
    version: string;
    group: string;
    asset: string;
    name: string;
    reason: string;
    execution_status: "bought" | "rejected" | "already_held" | "unknown";
    execution_note: string;
    signal_date: string;
    episode_start: string;
    same_day_start: boolean;
    ma_period: number;
    entry_reference: number;
    touch_date: string | null;
    target: number | null;
    stop: number | null;
    rr: number | null;
    bars: {
      date: string;
      open: number | null;
      high: number | null;
      low: number | null;
      close: number | null;
      ema20?: number | null;
      sma20?: number | null;
    }[];
    trades?: { date: string; side: "buy" | "sell"; price: number | null }[];
  }[];
}

export const POLICY_LABELS: Record<ModuleAPolicy, string> = {
  buy_hold: "资料就绪后买入持有",
  a_fixed: "模块 A：固定投入",
  a_risk: "模块 A：控制单笔投入",
  a_risk_degrade: "模块 A：回撤后缩小新买入",
};

export const POLICY_ORDER: ModuleAPolicy[] = ["buy_hold", "a_fixed", "a_risk", "a_risk_degrade"];
