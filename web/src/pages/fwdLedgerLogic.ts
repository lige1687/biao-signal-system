import type { FwdBucketStat, FwdRecommendationSection, FwdSentimentSection } from "../types";

/**
 * 前向成绩页的纯数据整型（无 React 依赖，供回归脚本直接断言）：
 * 两套成绩各自的展示模型 + 降级文案。缺数据时 status="degraded" 并带原因，
 * 不编数。
 */

export type FwdView<T> =
  | { status: "loading"; reason: string }
  | { status: "degraded"; reason: string }
  | { status: "ok"; reason: ""; data: T };

export interface SentimentCardModel {
  key: string;
  labelCn: string;
  n: number;
  meanPct: number | null;
  winRatePct: number | null;
}

export interface SymbolRowModel {
  symbol: string;
  name: string;
  samples: number;
  horizons: { t1: FwdBucketStat | null; t5: FwdBucketStat | null; t20: FwdBucketStat | null };
}

export function sentimentView(
  section: FwdSentimentSection | undefined,
): FwdView<{ cards: SentimentCardModel[]; records: number; reviewed: number }> {
  if (!section) return { status: "loading", reason: "账本数据加载中" };
  if (!section.available) return { status: "degraded", reason: section.reason };
  return {
    status: "ok",
    reason: "",
    data: {
      cards: (section.buckets ?? []).map((b) => ({
        key: b.key,
        labelCn: b.labelCn,
        n: b.n,
        meanPct: b.n > 0 ? b.meanPct ?? null : null,
        winRatePct: b.n > 0 ? b.winRatePct ?? null : null,
      })),
      records: section.records ?? 0,
      reviewed: section.reviewedRecords ?? 0,
    },
  };
}

export function recommendationView(
  section: FwdRecommendationSection | undefined,
): FwdView<{ rows: SymbolRowModel[]; scoredDates: number; latestDate: string }> {
  if (!section) return { status: "loading", reason: "账本数据加载中" };
  if (!section.available) return { status: "degraded", reason: section.reason };
  return {
    status: "ok",
    reason: "",
    data: {
      rows: (section.bySymbol ?? []).map((s) => ({
        symbol: s.symbol,
        name: s.nameCn ?? s.symbol,
        samples: s.samples,
        horizons: { t1: s.t1, t5: s.t5, t20: s.t20 },
      })),
      scoredDates: section.scoredDates ?? 0,
      latestDate: section.latestDate ?? "",
    },
  };
}

export function pctText(v: number | null | undefined): string {
  return v == null ? "—" : `${v > 0 ? "+" : ""}${v.toFixed(2)}%`;
}
