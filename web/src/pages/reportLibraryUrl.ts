/** Keep the current library context when a filter or report selection changes. */
export function patchReportLibraryParams(current: URLSearchParams, key: string, value: string | null): URLSearchParams {
  const next = new URLSearchParams(current);
  if (value == null || value === "") next.delete(key);
  else next.set(key, value);
  return next;
}

export function reportLibrarySearch(current: URLSearchParams, name: string): string {
  return `?${patchReportLibraryParams(current, "report", name).toString()}`;
}
