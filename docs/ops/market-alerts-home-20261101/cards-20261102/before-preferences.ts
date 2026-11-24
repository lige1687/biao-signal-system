import { READABLE_IDS } from "./catalog";

export const PINS_STORAGE_KEY = "ws.marketPins.v1";
export const PINS_CHANGE_EVENT = "lei:market-pins-changed";

export interface PinsRead { ids: string[]; warning: string | null }

export function normalizePins(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  const found = new Set<string>();
  for (const id of value) {
    if (typeof id === "string" && READABLE_IDS.has(id)) found.add(id);
  }
  return [...found];
}

export function parsePins(raw: string | null): PinsRead {
  if (raw === null) return { ids: [], warning: null };
  try {
    const value: unknown = JSON.parse(raw);
    if (!Array.isArray(value)) return { ids: [], warning: "已忽略损坏的首页观察偏好，请重新选择。" };
    return { ids: normalizePins(value), warning: null };
  } catch {
    return { ids: [], warning: "已忽略损坏的首页观察偏好，请重新选择。" };
  }
}

export function readPins(storage?: Pick<Storage, "getItem">): PinsRead {
  if (!storage) return { ids: [], warning: null };
  try { return parsePins(storage.getItem(PINS_STORAGE_KEY)); }
  catch { return { ids: [], warning: "浏览器存储不可用；本次选择只在当前页面有效。" }; }
}

export function writePins(storage: Pick<Storage, "setItem"> | undefined, ids: readonly string[]): boolean {
  if (!storage) return false;
  try { storage.setItem(PINS_STORAGE_KEY, JSON.stringify(normalizePins(ids))); return true; }
  catch { return false; }
}
