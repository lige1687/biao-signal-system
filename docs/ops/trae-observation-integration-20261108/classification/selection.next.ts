import { OBSERVATION_CATALOG } from "../observation-library/catalog";

export const OVERVIEW_KEY = "ws.marketOverviewCards.v2";
export const PREVIOUS_OVERVIEW_KEY = "ws.marketOverviewCards.v1";
export const COLLAPSED_KEY = "ws.marketOverviewCollapsed.v1";
export const LEGACY_PINS_KEY = "ws.marketPins.v1";
export const OVERVIEW_CHANGE_EVENT = "lei:market-overview-cards-changed";
export const CORE_IDS = ["erp-cn", "breadth-cn", "erp-us", "breadth-us"] as const;
export const EXTRA_IDS = ["breadth-cn", "breadth-us", "hv-cn", "hv-us", "dr007", "cn-session", "cn-institution",
  "cn-style-relative", "vix-term-structure", "us-semiconductor-relative", "us-equal-weight-relative", "industry-structure-cn"] as const;
export const CANDIDATE_IDS = new Set([...OBSERVATION_CATALOG.map((item) => item.id), ...EXTRA_IDS]);

// Known automatic defaults, before users were given a compact homepage.
export const LEGACY_DEFAULT_IDS = ["erp-cn", "breadth-cn", "focus-momentum", "hv-cn", "cn-financing", "turnover-concentration", "dr007",
  "cn-session", "cn-institution", "breadth-us", "erp-us", "hv-us", "vix", "hy-oas", "nfci",
  "cn-style-relative", "vix-term-structure", "us-semiconductor-relative", "us-equal-weight-relative"] as const;
const LEGACY_DEFAULTS: readonly (readonly string[])[] = [LEGACY_DEFAULT_IDS, LEGACY_DEFAULT_IDS.slice(0, 15),
  LEGACY_DEFAULT_IDS.slice(0, 15).filter(id => id !== "cn-session" && id !== "cn-institution")];

export function normalizeSelection(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return [...new Set(value.filter((id): id is string => typeof id === "string" && CANDIDATE_IDS.has(id)))];
}

function readArray(value: string | null): unknown[] | null {
  if (value === null) return null;
  try { const parsed: unknown = JSON.parse(value); return Array.isArray(parsed) ? parsed : null; }
  catch { return null; }
}

export function parseCollapsed(current: string | null): string[] {
  return normalizeSelection(readArray(current));
}

export function parseSelection(current: string | null, legacyPins: string | null): string[] {
  if (current !== null) return readArray(current) === null ? [...CORE_IDS] : normalizeSelection(readArray(current));
  return normalizeSelection([...CORE_IDS, ...normalizeSelection(readArray(legacyPins))]);
}

/** v1 stays untouched. Only known automatic sets shrink; custom subsets remain personal. */
export function migrateSelection(current: string | null, previous: string | null, legacyPins: string | null, collapsed: string | null): string[] {
  if (current !== null) return parseSelection(current, null);
  const old = readArray(previous);
  const hidden = new Set(parseCollapsed(collapsed));
  if (old === null) return parseSelection(null, legacyPins).filter(id => !hidden.has(id));
  const selected = normalizeSelection(old);
  const defaults = LEGACY_DEFAULTS.find(ids => ids.every(id => selected.includes(id)));
  const next = defaults ? normalizeSelection([...CORE_IDS, ...selected.filter(id => !defaults.includes(id))]) : selected;
  return next.filter(id => !hidden.has(id));
}
