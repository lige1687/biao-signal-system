import { parseSeen, serializeSeen, type AlertSnapshot, type SeenMap } from "./model";

export const SEEN_KEY = "lei.marketObservationSeen.v1";
export const SEEN_EVENT = "lei:market-observation-seen";

/** Merge with the latest persisted cursor so an older tab cannot roll it back. */
export function acknowledge(raw: string | null, snapshots: readonly AlertSnapshot[]): string {
  const seen: SeenMap = parseSeen(raw);
  for (const s of snapshots) {
    if (s.quality !== "ready" || !s.latest || !s.fingerprint) continue;
    const old = seen[s.id];
    if (old && old.date > s.latest.date) continue;
    // Same-date revised data never starts a new notification anyway; retain the existing cursor.
    if (old?.date === s.latest.date) continue;
    seen[s.id] = { date: s.latest.date, fingerprint: s.fingerprint };
  }
  return serializeSeen(seen);
}
