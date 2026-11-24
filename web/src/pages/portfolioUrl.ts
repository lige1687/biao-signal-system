/** Patch one or more portfolio URL fields without discarding the other view state. */
export function patchPortfolioParams(current: URLSearchParams, values: Record<string, string | null>): URLSearchParams {
  const next = new URLSearchParams(current);
  for (const [key, value] of Object.entries(values)) {
    if (!value) next.delete(key);
    else next.set(key, value);
  }
  return next;
}
