export type AlertEvent =
  | "enter_high" | "enter_low" | "exit_high" | "exit_low"
  | "stay_high" | "stay_low" | "none" | "unknown";

export type AlertPoint = {
  date: string;
  value: number | null;
  lower: number | null;
  upper: number | null;
  phase: "high" | "low" | "middle" | "flat" | "unknown";
  event: AlertEvent;
};

export type AlertInput = {
  id: string;
  label: string;
  kind: "erp" | "breadth";
  method: string;
  historicalOnly: boolean;
  points: AlertPoint[];
  loadError?: boolean;
};

export type SeenCursor = { date: string; fingerprint: string };
export type SeenMap = Record<string, SeenCursor>;
export type AlertQuality = "ready" | "historical" | "stale" | "missing" | "error";
export type AlertSnapshot = {
  id: string;
  label: string;
  kind: AlertInput["kind"];
  method: string;
  latest: AlertPoint | null;
  quality: AlertQuality;
  qualityLabel: string;
  positionLabel: string;
  lastEvent: AlertPoint | null;
  newEvents: AlertPoint[];
  revised: boolean;
  fingerprint: string;
};

const DAY_MS = 24 * 60 * 60 * 1000;
const FRESH_DAYS = 7; // Display freshness only; never a financial signal threshold.
const TRIGGERS = new Set<AlertEvent>(["enter_high", "enter_low", "exit_high", "exit_low"]);
const PHASES = new Set<AlertPoint["phase"]>(["high", "low", "middle", "flat", "unknown"]);
const EVENTS = new Set<AlertEvent>([
  "enter_high", "enter_low", "exit_high", "exit_low",
  "stay_high", "stay_low", "none", "unknown",
]);

function dayNumber(date: unknown): number | null {
  if (typeof date !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return null;
  const parsed = new Date(`${date}T00:00:00Z`);
  if (!Number.isFinite(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== date) return null;
  return parsed.getTime() / DAY_MS;
}

function validCursor(raw: unknown): raw is SeenCursor {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return false;
  const cursor = raw as Partial<SeenCursor>;
  return dayNumber(cursor.date) !== null && typeof cursor.fingerprint === "string" && cursor.fingerprint.length > 0;
}

function validPoint(point: AlertPoint, nowDay: number): boolean {
  const day = dayNumber(point.date);
  return day !== null && day <= nowDay &&
    point.value !== null && Number.isFinite(point.value) &&
    point.lower !== null && Number.isFinite(point.lower) &&
    point.upper !== null && Number.isFinite(point.upper) &&
    point.lower <= point.upper && PHASES.has(point.phase) && point.phase !== "unknown" &&
    EVENTS.has(point.event) &&
    (point.lower === point.upper ? point.phase === "flat" : point.phase !== "flat") &&
    ((point.event === "enter_high" || point.event === "stay_high") ? point.phase === "high" : true) &&
    ((point.event === "enter_low" || point.event === "stay_low") ? point.phase === "low" : true) &&
    ((point.event === "exit_high" || point.event === "exit_low") ? point.phase === "middle" : true);
}

function fingerprintOf(input: AlertInput, latest: AlertPoint): string {
  return JSON.stringify([
    input.id, input.method, latest.date, latest.value, latest.lower,
    latest.upper, latest.phase, latest.event,
  ]);
}

function triggerPoint(point: AlertPoint, nowDay: number): boolean {
  return validPoint(point, nowDay) && point.phase !== "flat" && TRIGGERS.has(point.event);
}

function positionLabel(kind: AlertInput["kind"], phase: AlertPoint["phase"] | null): string {
  if (phase === "flat") return kind === "erp" ? "轨道重合" : "高低区间重合";
  if (kind === "erp") {
    if (phase === "high") return "上轨外·相对便宜";
    if (phase === "low") return "下轨外·相对偏贵";
    if (phase === "middle") return "轨道内";
  } else {
    if (phase === "high") return "历史高位";
    if (phase === "low") return "历史低位";
    if (phase === "middle") return "历史中段";
  }
  return "位置未知";
}

export function eventLabel(kind: AlertInput["kind"], event: AlertEvent): string {
  const erp: Record<AlertEvent, string> = {
    enter_high: "上穿上轨", enter_low: "下穿下轨",
    exit_high: "回到上轨内", exit_low: "回到下轨内",
    stay_high: "持续在上轨外", stay_low: "持续在下轨外",
    none: "无新增穿轨", unknown: "事件未知",
  };
  const breadth: Record<AlertEvent, string> = {
    enter_high: "进入历史高位", enter_low: "进入历史低位",
    exit_high: "离开历史高位", exit_low: "离开历史低位",
    stay_high: "持续处于历史高位", stay_low: "持续处于历史低位",
    none: "无新增变化", unknown: "事件未知",
  };
  return (kind === "erp" ? erp : breadth)[event];
}

export function buildAlertSnapshot(input: AlertInput, nowDate: string, seen?: SeenCursor): AlertSnapshot {
  const nowDay = dayNumber(nowDate);
  const points = Array.isArray(input.points) ? input.points : [];
  let ordered = nowDay !== null;
  let priorDay = -Infinity;
  for (const point of points) {
    const day = dayNumber(point?.date);
    if (day === null || day <= priorDay || (nowDay !== null && day > nowDay)) ordered = false;
    if (day !== null) priorDay = day;
  }
  const latest = ordered && points.length > 0 ? points[points.length - 1] : null;
  const complete = latest !== null && nowDay !== null && validPoint(latest, nowDay);
  const fingerprint = complete ? fingerprintOf(input, latest) : "";
  const cursorValid = seen === undefined || validCursor(seen);
  const rollback = complete && seen !== undefined && cursorValid && latest.date < seen.date;
  const age = complete && nowDay !== null ? nowDay - dayNumber(latest.date)! : Infinity;

  let quality: AlertQuality;
  let qualityLabel: string;
  if (input.loadError) {
    quality = "error";
    qualityLabel = "资料读取失败";
  } else if (!ordered || !complete || !cursorValid) {
    quality = "missing";
    qualityLabel = "资料缺失或无效";
  } else if (input.historicalOnly) {
    quality = "historical";
    qualityLabel = "历史观察·不发送新提醒";
  } else if (rollback) {
    quality = "stale";
    qualityLabel = "资料日期早于上次已读记录";
  } else if (age > FRESH_DAYS) {
    quality = "stale";
    qualityLabel = "资料已超过 7 天";
  } else {
    quality = "ready";
    qualityLabel = `截至 ${latest.date}·可用`;
  }

  const lastEvent = ordered && nowDay !== null
    ? [...points].reverse().find(point => triggerPoint(point, nowDay)) ?? null
    : null;
  const revised = complete && seen !== undefined && cursorValid &&
    latest.date === seen.date && fingerprint !== seen.fingerprint;
  let newEvents: AlertPoint[] = [];
  if (quality === "ready" && !revised && nowDay !== null) {
    if (seen === undefined) {
      // A first visit never replays older historical crossings.
      newEvents = triggerPoint(latest!, nowDay) ? [latest!] : [];
    } else if (latest!.date > seen.date) {
      newEvents = points.filter(point => {
        const day = dayNumber(point.date);
        return point.date > seen.date && day !== null && nowDay - day <= FRESH_DAYS &&
          triggerPoint(point, nowDay);
      });
    }
  }

  return {
    id: input.id, label: input.label, kind: input.kind, method: input.method,
    latest, quality, qualityLabel,
    positionLabel: positionLabel(input.kind, complete ? latest!.phase : null),
    lastEvent, newEvents, revised, fingerprint,
  };
}

export function parseSeen(raw: string | null): SeenMap {
  if (raw === null) return {};
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    const container = parsed as { version?: unknown; seen?: unknown };
    if (container.version !== 1 || !container.seen || typeof container.seen !== "object" || Array.isArray(container.seen)) return {};
    return Object.fromEntries(Object.entries(container.seen).filter(([id, cursor]) =>
      id.length > 0 && validCursor(cursor))) as SeenMap;
  } catch {
    return {};
  }
}

export function serializeSeen(map: SeenMap): string {
  const seen = Object.fromEntries(Object.entries(map)
    .filter(([id, cursor]) => id.length > 0 && validCursor(cursor))
    .sort(([a], [b]) => a.localeCompare(b)));
  return JSON.stringify({ version: 1, seen });
}
