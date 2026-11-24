import { useQuery } from "@tanstack/react-query";
import { todayShanghai } from "./microstructureData";

const ids = ["cn-current-members-daily-dispersion", "us-current-members-daily-dispersion"] as const;
const regimes = ["PANIC", "VOLATILE_DISAGREEMENT", "SIPHON_WARNING", "HEALTHY_ROTATION", "BROAD_TREND", "BALANCED"] as const;
const rules = [
  "window", "min_samples", "high_disp", "extreme_disp", "low_disp", "healthy_breadth", "thin_breadth",
  "broad_breadth", "panic_breadth", "high_rv", "divergence_days",
] as const;
const percentFields = [
  "pct_above_ma20", "pct_above_ma60", "disp_pct_252d", "rv20_pct_252d", "sector_dominance_pct",
] as const;
const nonnegativeFields = [
  "disp_raw", "index_close", "sector_disp_raw", "disp_ma5", "disp_ma20", "disp_p20", "disp_p50",
  "disp_p80", "index_rv20", "sector_dominance_ratio",
] as const;
const sources = ["members", "breadth", "index", "sectors"] as const;

export type MemberDispersionRegime = typeof regimes[number];
export type MemberDispersionPoint = {
  date: string;
  disp_sample_count: number | null;
  rv_sample_count: number | null;
  high_disp_low_breadth: boolean | null;
  breadth_divergence: boolean | null;
  regime_diagnosis: MemberDispersionRegime | null;
} & Record<typeof percentFields[number] | typeof nonnegativeFields[number], number | null>;

type PacketCard = {
  id: typeof ids[number];
  sources: Record<typeof sources[number], string>;
  points: MemberDispersionPoint[];
};

type MemberDispersionPacket = {
  schemaVersion: 1;
  generatedAt: string;
  rules: Record<typeof rules[number], number>;
  cards: PacketCard[];
};

export type MemberDispersionCard = PacketCard & Pick<MemberDispersionPacket, "rules">;

export function isMemberDispersion(id: string | undefined): id is PacketCard["id"] {
  return ids.some(candidate => candidate === id);
}

const record = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);
const finite = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
const nullableRange = (value: unknown, max = Infinity) => value === null || finite(value) && value >= 0 && value <= max;
const count = (value: unknown, max: number) => value === null || finite(value) && Number.isInteger(value) && value >= 0 && value <= max;

export function parseMemberDispersion(raw: unknown, today = todayShanghai()): MemberDispersionPacket {
  if (!record(raw) || raw.schemaVersion !== 1 || typeof raw.generatedAt !== "string"
    || !Number.isFinite(Date.parse(raw.generatedAt)) || !Array.isArray(raw.cards) || !record(raw.rules)) {
    throw new Error("分化资料结构无效");
  }
  const definition = raw.rules;
  if (!rules.every(key => finite(definition[key]) && Number.isInteger(definition[key]) && definition[key] > 0)
    || !finite(definition.window) || !finite(definition.min_samples) || definition.min_samples > definition.window) {
    throw new Error("分化参考口径无效");
  }
  const seen = new Set<string>();
  for (const card of raw.cards) {
    if (!record(card) || typeof card.id !== "string" || !isMemberDispersion(card.id)
      || seen.has(card.id) || !Array.isArray(card.points) || !card.points.length || !record(card.sources)) {
      throw new Error("分化观察标识无效");
    }
    const cardSources = card.sources;
    if (!sources.every(key => typeof cardSources[key] === "string" && cardSources[key].trim())) {
      throw new Error("分化资料来源缺失");
    }
    seen.add(card.id);
    let previous = "";
    for (const point of card.points) {
      if (!record(point) || typeof point.date !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(point.date)
        || !Number.isFinite(Date.parse(point.date)) || new Date(point.date).toISOString().slice(0, 10) !== point.date
        || point.date <= previous || point.date > today
        || !percentFields.every(key => nullableRange(point[key], 100))
        || !nonnegativeFields.every(key => nullableRange(point[key]))
        || !count(point.disp_sample_count, definition.window) || !count(point.rv_sample_count, definition.window)
        || ![point.high_disp_low_breadth, point.breadth_divergence].every(flag => flag === null || typeof flag === "boolean")
        || point.regime_diagnosis !== null && !regimes.some(regime => regime === point.regime_diagnosis)) {
        throw new Error("分化观察日期或读数无效");
      }
      previous = point.date;
    }
  }
  return raw as unknown as MemberDispersionPacket;
}

export function useMemberDispersion(id: string | undefined): MemberDispersionCard | undefined {
  const query = useQuery({
    queryKey: ["memberDispersionV1"],
    queryFn: async ({ signal }) => {
      const response = await fetch("/research/member-dispersion/v1.json", { signal, cache: "no-cache" });
      if (!response.ok) throw new Error("分化资料暂不可读");
      return parseMemberDispersion(await response.json());
    },
    enabled: isMemberDispersion(id), staleTime: 5 * 60_000, retry: false,
  });
  const card = query.data?.cards.find(entry => entry.id === id);
  return card && query.data ? { ...card, rules: query.data.rules } : undefined;
}
