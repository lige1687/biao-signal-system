import { useQuery } from "@tanstack/react-query";
import { FOCUS_MOMENTUM_URL, parseFocusMomentumObservation } from "./data";
import { mergeFocusContinuation } from "./recentData";

export const FOCUS_DISPLAY_KEY = ["focusMomentumDisplayV2"] as const;
export const FOCUS_CONTINUATION_URL = "/research/focus-momentum/continuation.v1.json";

async function read(url: string) {
  const response = await fetch(url, { cache: "no-cache" });
  if (!response.ok || !response.headers.get("content-type")?.includes("json")) throw new Error("模型资料读取失败");
  return response.json();
}
export function useRecentFocusMomentum(enabled = true) {
  return useQuery({ queryKey: FOCUS_DISPLAY_KEY, enabled, queryFn: async () => {
    const [base, recent] = await Promise.all([read(FOCUS_MOMENTUM_URL), read(FOCUS_CONTINUATION_URL)]);
    return mergeFocusContinuation(parseFocusMomentumObservation(base), recent);
  }, staleTime: 5 * 60_000, refetchInterval: 5 * 60_000, retry: false });
}
