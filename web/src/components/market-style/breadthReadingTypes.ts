import type { BreadthHistoryResponse } from "../../types";

export const BREADTH_HORIZONS = ["20", "50", "200"] as const;
export type BreadthHorizon = typeof BREADTH_HORIZONS[number];
export type BreadthTrack = "historical" | "stockcharts" | "fixed" | "off";

export interface BreadthHorizonReading {
  lower: number | null;
  median: number | null;
  upper: number | null;
  percentile: number | null;
  delta_5: number | null;
  sample_count: number;
  status: "ready" | "insufficient" | "missing";
  position: "low" | "middle" | "high" | "flat" | "unknown";
  event: "enter_low" | "exit_low" | "enter_high" | "exit_high" | "stay_low" | "stay_high" | "none" | "unknown";
}
export interface BreadthReadingPoint {
  date: string;
  horizons: Record<BreadthHorizon, BreadthHorizonReading>;
  state: { code: string; label: string; summary: string; tone: "supportive" | "caution" | "neutral" | "unknown" };
}
export interface BreadthObservation {
  method_version: string;
  lookback_observations: number;
  min_observations: number;
  lower_quantile: number;
  upper_quantile: number;
  includes_current: boolean;
  history: BreadthReadingPoint[];
  latest: BreadthReadingPoint | null;
  error?: string;
}
export interface BreadthReadingResponse extends BreadthHistoryResponse {
  observation?: BreadthObservation;
}
