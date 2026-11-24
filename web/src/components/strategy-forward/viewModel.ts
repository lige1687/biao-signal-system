import type { AccountPoint, StrategyAccount, StrategyDashboard } from "./model";

const shanghaiDate = new Intl.DateTimeFormat("en-US", { timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit" });

export function dayInShanghai(instant: string): string {
  const date = new Date(instant);
  if (!Number.isFinite(date.getTime())) return "";
  const parts = Object.fromEntries(shanghaiDate.formatToParts(date).map((part) => [part.type, part.value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
}

export const RULE_FIELDS = [
  ["universe", "观察标的与准入"],
  ["entry", "入场"],
  ["ranking", "候选排序"],
  ["sizing", "仓位"],
  ["holding", "持有"],
  ["exit", "退出与风控"],
  ["reentry", "重新进入"],
  ["cash_conflict", "资金与成交"],
] as const;

export function accountStatus(status: StrategyAccount["status"]): string {
  return ({ not_started: "尚未启动", waiting_quote: "等待合格行情", waiting_execution: "等待模拟成交", observing: "观察中", blocked: "规则待补", external_pending: "其他任务建设中", stale: "资料或运行已过期" })[status];
}

export function accountRole(account: StrategyAccount): string {
  if (account.role === "cash_reference") return "现金参照";
  if (account.role === "passive_baseline") return "被动持有基准";
  if (account.kind === "blocked") return "候选待补";
  return "完整策略候选";
}

export function displayNumber(value: number | null | undefined, suffix = "", digits = 2): string {
  return value == null || !Number.isFinite(value) ? "—" : `${value.toLocaleString("zh-CN", { maximumFractionDigits: digits })}${suffix}`;
}

export function displayDate(value: string | null | undefined): string {
  if (!value) return "未形成";
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return value;
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-US", { timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).formatToParts(date).map((part) => [part.type, part.value]));
  return `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute}`;
}

export function validPoint(point: AccountPoint): boolean {
  return point.valid && !point.stale && point.nav != null && Number.isFinite(point.nav);
}

export function plottedAccounts(data: StrategyDashboard, selectedIds: string[]): StrategyAccount[] {
  return data.accounts.filter((a) => selectedIds.includes(a.id) && a.kind !== "blocked" && a.kind !== "external_pending" && a.status !== "blocked" && a.status !== "external_pending" && a.series.some(validPoint));
}

export function plotDates(accounts: StrategyAccount[], recordedDates: string[] = []): string[] {
  const known = [...new Set([...recordedDates, ...accounts.flatMap((a) => a.series.filter(validPoint).map((p) => p.date))])].sort();
  if (known.length < 2) return known;
  const all = new Set(known);
  const end = Date.parse(`${known[known.length - 1]}T00:00:00Z`);
  for (let ms = Date.parse(`${known[0]}T00:00:00Z`); ms <= end; ms += 86_400_000) {
    const date = new Date(ms);
    // A weekday with no valuation stays empty. Holidays can also be gaps; this
    // display grid is not an exchange calendar or a claim that a run was missed.
    if (date.getUTCDay() !== 0 && date.getUTCDay() !== 6) all.add(date.toISOString().slice(0, 10));
  }
  return [...all].sort();
}

export function chartValues(account: StrategyAccount, dates: string[], key: "nav" | "drawdown_pct" | "exposure_pct" | "cash"): Array<number | null> {
  const byDate = new Map(account.series.filter(validPoint).map((p) => [p.date, p]));
  return dates.map((date) => byDate.get(date)?.[key] ?? null);
}

export function dayDecisions(data: StrategyDashboard, day: string, accountIds: string[]) {
  return data.decisions.filter((d) => dayInShanghai(d.at) === day && (!d.account_id || accountIds.includes(d.account_id)));
}

export function availableDays(data: StrategyDashboard, accountIds: string[]): string[] {
  return [...new Set([
    ...data.accounts.filter((a) => accountIds.includes(a.id)).flatMap((a) => a.series.map((p) => p.date)),
    ...data.decisions.filter((d) => !d.account_id || accountIds.includes(d.account_id)).map((d) => dayInShanghai(d.at)),
  ].filter(Boolean))].sort();
}

export function firstUsableDay(data: StrategyDashboard, accountIds: string[]): string {
  const dates = availableDays(data, accountIds);
  return dates[dates.length - 1] ?? "";
}

export function runnerView(run: StrategyDashboard["run"], generatedAt: string): { label: string; detail: string; tone: "is-live" | "is-pending" | "is-alert" } {
  const runner = run.runner;
  if (!runner) return { label: "未记录持续运行", detail: "可手动采集；目前没有持续运行心跳", tone: "is-pending" };
  const status = runner.status;
  if (status === "error") return { label: "持续运行报错", detail: runner.last_error || "请检查运行记录", tone: "is-alert" };
  if (status === "stopped") return { label: "持续运行已停止", detail: `最后心跳 ${displayDate(runner.heartbeat_at)}`, tone: "is-alert" };
  if (runner.pid_alive === false || runner.active === false) return { label: "持续运行未通过核对", detail: "进程或心跳未通过服务端检查", tone: "is-alert" };
  const heartbeat = Date.parse(runner.heartbeat_at || "");
  const now = Date.parse(generatedAt);
  if (!Number.isFinite(heartbeat) || !Number.isFinite(now) || heartbeat > now + 15_000 || now - heartbeat > 90_000) {
    return { label: "持续运行心跳过期", detail: `最后心跳 ${displayDate(runner.heartbeat_at)}；需核对进程`, tone: "is-alert" };
  }
  if (status === "waiting") return { label: "持续运行正常", detail: `最近心跳 ${displayDate(runner.heartbeat_at)}`, tone: "is-live" };
  if (status === "starting") return { label: "持续运行启动中", detail: `最近心跳 ${displayDate(runner.heartbeat_at)}`, tone: "is-pending" };
  return { label: "持续运行状态待核对", detail: `最近心跳 ${displayDate(runner.heartbeat_at)}`, tone: "is-alert" };
}

export function metricText(value: number | null, reason: string | null, suffix = "%"): string {
  if (value == null || !Number.isFinite(value)) return metricReason(reason);
  return displayNumber(value, suffix);
}

export function metricReason(reason: string | null): string {
  return ({
    no_valid_eod_valuation: "尚无有效收盘估值",
    insufficient_duration_or_variation: "观察时间不足或波动为零",
  } as Record<string, string>)[reason || ""] || reason || "资料不足";
}

export function healthText(code: string): string {
  return ({
    not_started: "账户尚未实际启动",
    simulated_only_no_broker: "仅记录模拟账户，未连接券商",
    runner_status_unknown_or_stale: "最近检查已过期；请核对运行状态",
    runner_heartbeat_unreadable: "持续运行心跳记录无法读取",
    runner_heartbeat_missing: "尚未找到持续运行心跳",
    runner_not_active: "持续采集进程未正常运行，请查看运行状态",
    current_config_differs_frozen: "当前配置已变化，旧账户仍按冻结版本显示",
    reconciliation_unreadable: "账户核对记录无法读取",
  } as Record<string, string>)[code] || code;
}

export function eventText(kind: string, action?: unknown): string {
  if (kind === "decision") {
    if (action === "queue_initial_buy") return "决定排队买入";
    if (action === "hold_cash") return "决定保持现金";
    return "当时决策";
  }
  return ({
    frozen: "规则已冻结", order_queued: "订单已排队", source: "收到行情资料",
    waiting: "等待处理", fill: "模拟成交", partially_filled: "部分模拟成交",
    cancelled: "订单取消", valuation: "收盘估值", split: "份额变动",
    dividend_ex: "分红列为应收", dividend_pay: "分红到账",
  } as Record<string, string>)[kind] || `其他记录（${kind}）`;
}

export function orderStatusText(status: string): string {
  return ({ queued: "排队中", open: "等待成交", partial: "部分成交", filled: "已成交", cancelled: "已取消", rejected: "已拒绝" } as Record<string, string>)[status] || `状态待核对（${status}）`;
}

export function reasonText(reason: string): string {
  const known: Record<string, string> = {
    source_time_outside_forward_sequence: "行情时间不在规则启用后的合法顺序内",
    stale_quote: "报价到达或使用时已过期",
    source_quality_not_valid: "行情来源质量未通过检查",
    market_not_open: "当前不在可交易时段",
    last_missing_or_invalid: "最新价缺失或无效",
    bid_missing_or_invalid: "买一价缺失或无效",
    ask_missing_or_invalid: "卖一价缺失或无效",
    bid_ask_missing_or_crossed: "买卖报价缺失或交叉",
    source_time_in_future: "行情时间晚于接收时间",
    corporate_actions_not_checked: "分红与份额变动尚未核对",
    corporate_actions_coverage_unknown: "分红与份额变动的覆盖日期未知",
    corporate_actions_coverage_invalid: "分红与份额变动的覆盖日期不合格",
    corporate_actions_coverage_gap: "持有期间的分红或份额变动资料有缺口",
    corporate_action_identity_or_date_missing: "分红或份额变动缺编号或生效日期",
    corporate_action_revision_pending: "分红或份额变动资料修订待核对",
    late_corporate_action_pending_reconciliation: "迟到的分红或份额变动待对账",
    duplicate_source_time: "同一行情时间已有记录",
    out_of_order_source_time: "行情到达顺序晚于已有记录",
    cannot_afford_one_lot: "资金不足以买入一整手",
    no_quote_size_or_cash_or_lot: "报价数量、可用资金或整手限制使订单暂未成交",
    latest_eod_valuation_missing: "最近收盘估值缺失",
  };
  return known[reason] || `未归类原因（${reason}）`;
}

export function decisionReasons(payload: Record<string, unknown>): string[] {
  const raw = [payload.reason, ...(Array.isArray(payload.reasons) ? payload.reasons : []), ...(Array.isArray(payload.valuation_reasons) ? payload.valuation_reasons : [])];
  return [...new Set(raw.filter((value): value is string => typeof value === "string" && value.length > 0))].map(reasonText);
}

export function ruleText(value: string | string[] | null | undefined): string {
  if (value == null || value === "") return "尚未冻结此项规则";
  if (Array.isArray(value)) return value.join("、");
  return ({
    "one queued order at freeze; next eligible observed quote only": "规则冻结后排一笔单；只在下一次合格报价到达后模拟成交",
    "single asset; no ranking": "只观察一个标的，无候选排序",
    "whole 100 share lots within initial cash including fees": "连同费用一起控制在初始资金内，按100份整数倍下单",
    "hold acquired shares; no rebalance": "成交后持有，不定期再平衡",
    "none for passive baseline": "被动持有基准没有主动退出规则",
    "none": "无",
    "separate reference accounts; no common cash": "各参照账户独立记账，不共用现金",
  } as Record<string, string>)[value] || value;
}
