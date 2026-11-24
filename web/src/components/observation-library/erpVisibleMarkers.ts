import type { ComparedErpEvent } from "./erpComparisonDisplay";
import type { UsErpMarkerGroup } from "./usErpMarkerGroups";

/** A narrowed date axis must expose each original crossing; the chart zoom filters out-of-view dates. */
export function erpEventsForZoom(
  events: readonly ComparedErpEvent[], groups: readonly UsErpMarkerGroup[],
  grouped: boolean, start = 0, end = 100,
): readonly ComparedErpEvent[] {
  const narrowed = start > .1 || end < 99.9;
  return grouped && !narrowed ? groups.map(group => group.representative) : events;
}
