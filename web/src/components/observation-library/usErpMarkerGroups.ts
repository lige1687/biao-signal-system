import type { ComparedErpEvent } from "./erpComparisonDisplay";

export type UsErpMarkerGroup = {
  representative: ComparedErpEvent;
  members: ComparedErpEvent[];
  count: number;
  endDate: string;
};

/** Condense plotted markers only. Every original event stays available in members. */
export function groupUsErpMarkers(
  events: readonly ComparedErpEvent[],
  dates: readonly string[],
  maxSpanObservations: number,
): UsErpMarkerGroup[] {
  const span = Number.isInteger(maxSpanObservations) && maxSpanObservations >= 1 ? maxSpanObservations : 1;
  const positions = new Map(dates.map((date, index) => [date, index]));
  const seen = new Set<string>();
  const eligible = events.filter(event => {
    if (!positions.has(event.date) || seen.has(event.id)) return false;
    seen.add(event.id);
    return true;
  }).sort((a, b) => positions.get(a.date)! - positions.get(b.date)! || a.sigma - b.sigma);

  const groups: UsErpMarkerGroup[] = [];
  let firstIndex = -1;
  for (const event of eligible) {
    const index = positions.get(event.date)!;
    const group = groups[groups.length - 1];
    if (!group || event.kind !== group.representative.kind || index - firstIndex > span) {
      groups.push({ representative: event, members: [event], count: 1, endDate: event.date });
      firstIndex = index;
      continue;
    }
    group.members.push(event);
    group.count++;
    group.endDate = event.date;
    // Representative is fixed to the earliest date. For a same-date tie, show the stronger rail.
    if (event.date === group.representative.date && event.sigma > group.representative.sigma) {
      group.representative = event;
    }
  }
  return groups;
}
