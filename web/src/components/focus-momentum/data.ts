import { useQuery } from "@tanstack/react-query";

export const FOCUS_MOMENTUM_URL = "/research/focus-momentum/observation.v1.json";
export const FOCUS_MOMENTUM_QUERY_KEY = ["focusMomentumObservationV1"] as const;

export interface FocusMomentumPoint {
  date: string;
  focus: number;
  poolMomentum: number;
  breadth: number;
  concentration: number;
  qualifiedCount: number;
  focusCount: number;
  top1Contribution: number;
}

export interface FocusMomentumMappingTarget {
  target: "CSI300" | "CSI1000";
  label: string;
  baselineMean: number;
  points: Array<{ date: string; labelEnd: string; focus: number; forwardReturn: number }>;
}

export interface FocusMomentumMapping {
  horizonSessions: 20;
  frequency: "weekly";
  sampleStart: string;
  sampleEnd: string;
  labelEndMax: string;
  targets: FocusMomentumMappingTarget[];
  us: { status: "unavailable"; reason: string };
}

export interface FocusMomentumObservation {
  schemaVersion: 1;
  definitionId: string;
  label: string;
  market: "cn";
  historicalOnly: true;
  asOf: string;
  current: null;
  scope: {
    label: string;
    sampleSize: number;
    selection: string;
    method: string;
    limitations: string[];
  };
  series: FocusMomentumPoint[];
  latest: FocusMomentumPoint & { members: string[]; changeFocus: number | null };
  mapping: FocusMomentumMapping;
  research: {
    asOf: string;
    conclusion: string;
    reportPath: string;
    period: string;
    horizonSessions: number;
    comparisons: Array<{
      target: "CSI300" | "CSI1000";
      label: string;
      baselineMae: number;
      withZeroMae: number;
      improvement: number;
      interval: [number, number];
    }>;
  };
  source: { paths: string[]; sha256: Record<string, string> };
}

function record(value: unknown, at: string): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${at} 结构无效`);
  return value as Record<string, unknown>;
}

function string(value: unknown, at: string): string {
  if (typeof value !== "string" || !value.trim()) throw new Error(`${at} 缺失`);
  return value;
}

function day(value: unknown, at: string): string {
  const v = string(value, at);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(v) || Number.isNaN(Date.parse(`${v}T00:00:00Z`))) {
    throw new Error(`${at} 日期无效`);
  }
  return v;
}

function number(value: unknown, at: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) throw new Error(`${at} 数值无效`);
  return value;
}

function count(value: unknown, at: string): number {
  const v = number(value, at);
  if (!Number.isInteger(v) || v < 0) throw new Error(`${at} 数量无效`);
  return v;
}

function ratio(value: unknown, at: string): number {
  const v = number(value, at);
  if (v < 0 || v > 1) throw new Error(`${at} 比例超出范围`);
  return v;
}

function strings(value: unknown, at: string): string[] {
  if (!Array.isArray(value) || !value.every(v => typeof v === "string" && v.trim())) {
    throw new Error(`${at} 列表无效`);
  }
  return value;
}

function point(value: unknown, at: string): FocusMomentumPoint {
  const v = record(value, at);
  const qualifiedCount = count(v.qualifiedCount, `${at}.qualifiedCount`);
  const focusCount = count(v.focusCount, `${at}.focusCount`);
  if (qualifiedCount < 100 || focusCount < 1 || focusCount > qualifiedCount) {
    throw new Error(`${at} 样本覆盖无效`);
  }
  return {
    date: day(v.date, `${at}.date`),
    focus: number(v.focus, `${at}.focus`),
    poolMomentum: number(v.poolMomentum, `${at}.poolMomentum`),
    breadth: ratio(v.breadth, `${at}.breadth`),
    concentration: ratio(v.concentration, `${at}.concentration`),
    qualifiedCount,
    focusCount,
    top1Contribution: ratio(v.top1Contribution, `${at}.top1Contribution`),
  };
}

function mapping(input: unknown, series: FocusMomentumPoint[]): FocusMomentumMapping {
  const v = record(input, "映射资料");
  if (v.horizonSessions !== 20 || v.frequency !== "weekly") throw new Error("映射期限或频率不符");
  const sampleStart = day(v.sampleStart, "mapping.sampleStart");
  const sampleEnd = day(v.sampleEnd, "mapping.sampleEnd");
  const labelEndMax = day(v.labelEndMax, "mapping.labelEndMax");
  const daily = new Map(series.map(p => [p.date, p.focus]));
  if (!Array.isArray(v.targets) || v.targets.length !== 2) throw new Error("映射目标缺失");
  const targets = v.targets.map((raw): FocusMomentumMappingTarget => {
    const t = record(raw, "映射目标");
    if (t.target !== "CSI300" && t.target !== "CSI1000") throw new Error("映射目标无效");
    if (!Array.isArray(t.points) || t.points.length !== 560) throw new Error("映射样本数不符");
    const points = t.points.map(raw => {
      const p = record(raw, "映射点");
      const date = day(p.date, "mapping.date");
      const labelEnd = day(p.labelEnd, "mapping.labelEnd");
      const focus = number(p.focus, "mapping.focus");
      if (date < sampleStart || date > sampleEnd || labelEnd <= date || labelEnd > labelEndMax || daily.get(date) !== focus) {
        throw new Error("映射日期或横轴与来源不一致");
      }
      return { date, labelEnd, focus, forwardReturn: number(p.forwardReturn, "mapping.forwardReturn") };
    });
    if (points.some((p, i) => i > 0 && p.date <= points[i - 1].date) || points[0].date !== sampleStart || points[points.length - 1].date !== sampleEnd) {
      throw new Error("映射日期重复或覆盖不符");
    }
    const baselineMean = number(t.baselineMean, "mapping.baselineMean");
    if (Math.abs(baselineMean - points.reduce((sum, p) => sum + p.forwardReturn, 0) / points.length) > 1e-12) {
      throw new Error("映射总体基准与样本不一致");
    }
    return { target: t.target, label: string(t.label, "mapping.label"), baselineMean, points };
  });
  if (new Set(targets.map(t => t.target)).size !== 2 || targets[0].points.some((p, i) => p.date !== targets[1].points[i].date || p.labelEnd !== targets[1].points[i].labelEnd)) {
    throw new Error("映射目标或共同日期不一致");
  }
  const us = record(v.us, "mapping.us");
  if (us.status !== "unavailable") throw new Error("美股映射状态不符");
  return { horizonSessions: 20, frequency: "weekly", sampleStart, sampleEnd, labelEndMax, targets, us: { status: "unavailable", reason: string(us.reason, "mapping.us.reason") } };
}

export function parseFocusMomentumObservation(input: unknown): FocusMomentumObservation {
  const v = record(input, "观察资料");
  if (v.schemaVersion !== 1 || v.market !== "cn" || v.historicalOnly !== true || v.current !== null) {
    throw new Error("观察资料版本或历史状态不符");
  }
  const scope = record(v.scope, "scope");
  const research = record(v.research, "research");
  const source = record(v.source, "source");
  if (!Array.isArray(v.series) || !v.series.length) throw new Error("历史曲线缺失");
  const series = v.series.map((item, i) => point(item, `series[${i}]`));
  for (let i = 1; i < series.length; i++) {
    if (series[i - 1].date >= series[i].date) throw new Error("历史曲线日期未严格递增");
  }
  const latestRaw = record(v.latest, "latest");
  const latest = {
    ...point(latestRaw, "latest"),
    members: strings(latestRaw.members, "latest.members"),
    changeFocus: latestRaw.changeFocus === null ? null : number(latestRaw.changeFocus, "latest.changeFocus"),
  };
  const asOf = day(v.asOf, "asOf");
  const last = series[series.length - 1];
  if (asOf !== last.date || latest.date !== asOf ||
    (["focus", "poolMomentum", "breadth", "concentration", "qualifiedCount", "focusCount", "top1Contribution"] as const)
      .some(key => latest[key] !== last[key])) {
    throw new Error("最新历史读数与曲线末日不一致");
  }
  if (latest.members.length !== latest.focusCount) throw new Error("焦点成员数量不一致");
  if (!Array.isArray(research.comparisons) || research.comparisons.length !== 2) {
    throw new Error("研究对照缺失");
  }
  const comparisons = research.comparisons.map((item, i) => {
    const r = record(item, `comparison[${i}]`);
    if (r.target !== "CSI300" && r.target !== "CSI1000") throw new Error("研究目标无效");
    const target: "CSI300" | "CSI1000" = r.target;
    if (!Array.isArray(r.interval) || r.interval.length !== 2) throw new Error("误差范围无效");
    return {
      target,
      label: string(r.label, `comparison[${i}].label`),
      baselineMae: number(r.baselineMae, `comparison[${i}].baselineMae`),
      withZeroMae: number(r.withZeroMae, `comparison[${i}].withZeroMae`),
      improvement: number(r.improvement, `comparison[${i}].improvement`),
      interval: [number(r.interval[0], "interval lower"), number(r.interval[1], "interval upper")] as [number, number],
    };
  });
  if (new Set(comparisons.map(item => item.target)).size !== 2) throw new Error("研究目标重复");
  return {
    schemaVersion: 1,
    definitionId: string(v.definitionId, "definitionId"),
    label: string(v.label, "label"),
    market: "cn",
    historicalOnly: true,
    asOf,
    current: null,
    scope: {
      label: string(scope.label, "scope.label"),
      sampleSize: count(scope.sampleSize, "scope.sampleSize"),
      selection: string(scope.selection, "scope.selection"),
      method: string(scope.method, "scope.method"),
      limitations: strings(scope.limitations, "scope.limitations"),
    },
    series,
    latest,
    mapping: mapping(v.mapping, series),
    research: {
      asOf: day(research.asOf, "research.asOf"),
      conclusion: string(research.conclusion, "research.conclusion"),
      reportPath: string(research.reportPath, "research.reportPath"),
      period: string(research.period, "research.period"),
      horizonSessions: count(research.horizonSessions, "research.horizonSessions"),
      comparisons,
    },
    source: {
      paths: strings(source.paths, "source.paths"),
      sha256: record(source.sha256, "source.sha256") as Record<string, string>,
    },
  };
}

async function loadFocusMomentumObservation(): Promise<FocusMomentumObservation> {
  const response = await fetch(FOCUS_MOMENTUM_URL, { cache: "no-cache" });
  if (!response.ok) throw new Error(`观察资料读取失败（HTTP ${response.status}）`);
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("json")) throw new Error("观察资料格式不符，服务器返回了非 JSON 内容");
  let raw: unknown;
  try { raw = await response.json(); } catch { throw new Error("观察资料 JSON 损坏"); }
  return parseFocusMomentumObservation(raw);
}

export function useFocusMomentumObservation() {
  return useQuery({
    queryKey: FOCUS_MOMENTUM_QUERY_KEY,
    queryFn: loadFocusMomentumObservation,
    staleTime: 5 * 60_000,
    retry: false,
    refetchOnWindowFocus: false,
  });
}
