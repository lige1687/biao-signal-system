import type { BreadthReadingResponse } from "../market-style/breadthReadingTypes";
import { BREADTH_LINES } from "../trend/zones";
import { breadthInput, type BreadthMarket } from "./adapters";
import { CHART_COLORS } from "./ChartLegend";
import { formatMicro, reading, type MicroCard } from "./microstructureData";
import { concentrationDisplay } from "./concentrationDisplay";

export type ThumbnailLine = { name: string; color: string; values: (number | null)[] };
export type ThumbnailReference = ThumbnailLine & { dashed?: boolean; endLabel?: string };
export type ThumbnailChart = {
  dates: string[];
  lines: ThumbnailLine[];
  references?: ThumbnailReference[];
  lower?: (number | null)[];
  upper?: (number | null)[];
  percent?: boolean;
};
export type ThumbnailReading = { value: string; date?: string; note?: string; chart?: ThumbnailChart };

const finite = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);

export function thumbnailWindow(chart: ThumbnailChart, count = 90): ThumbnailChart {
  const tail = <T extends ThumbnailLine>(line: T): T => ({ ...line, values: line.values.slice(-count) });
  return {
    dates: chart.dates.slice(-count),
    lines: chart.lines.map(tail),
    references: chart.references?.map(tail),
    lower: chart.lower?.slice(-count),
    upper: chart.upper?.slice(-count),
    percent: chart.percent,
  };
}

export function historyState(lines: readonly ThumbnailLine[]) {
  if (lines.some(({ values }) => values.some((value, index) => finite(value) && finite(values[index - 1])))) return "chart";
  if (lines.some(({ values }) => values.filter(finite).length >= 2)) return "disconnected";
  return lines.some(({ values }) => values.some(finite)) ? "snapshot" : "empty";
}

export function microThumbnailId(id: string) {
  return id === "turnover-concentration" ? "cn-daily-amount-top5" : id;
}

const LINE_COLORS = ["#28629e", "#c0563b", "#327c72", "#80678a"] as const;

export function microThumbnail(card: MicroCard): ThumbnailReading {
  const latest = reading(card);
  const context = concentrationDisplay(card);
  const lastKnown = latest.value === null ? [...card.points].reverse().find((point) => point.value !== null) : undefined;
  const merged = card.lines?.length
    ? card.lines.map((line, index) => ({
        name: `${line.label} · ${card.unit}`,
        color: LINE_COLORS[index % LINE_COLORS.length],
        values: line.values,
      }))
    : [{ name: `${card.title} · ${card.unit}`, color: "#28629e", values: card.points.map((point) => point.value) }];
  return {
    value: formatMicro(latest.value, card.unit),
    date: latest.date,
    note: lastKnown ? `最近有效读数 ${formatMicro(lastKnown.value, card.unit)}（${lastKnown.date}）`
      : latest.value === null ? "本期缺读数 · 历史快照" : context?.reading ? `${context.reading} · 历史快照` : "历史快照",
    chart: {
      dates: card.points.map((point) => point.date),
      lines: merged,
      references: [...(card.references ?? []).map((reference) => ({
        name: reference.label, color: "#9b7953", values: card.points.map(() => reference.value),
      })), ...(context?.overlays ?? [])],
    },
  };
}

export function breadthThumbnail(market: BreadthMarket, data: BreadthReadingResponse): ThumbnailReading {
  const history = data.history;
  const rails = new Map(breadthInput(market, data).points.map((point) => [point.date, point]));
  const latest = history[history.length - 1];
  const value = latest?.breadth_50;
  return {
    date: latest?.date,
    value: finite(value) ? `50日 ${value.toFixed(1)}%` : "待补",
    note: "50日宽度 · 高低线为历史参照",
    chart: {
      dates: history.map((point) => point.date),
      lines: [{ name: "50日宽度", color: BREADTH_LINES[1]?.color ?? CHART_COLORS.primary,
        values: history.map((point) => finite(point.breadth_50) ? point.breadth_50 : null) }],
      lower: history.map((point) => rails.get(point.date)?.lower ?? null),
      upper: history.map((point) => rails.get(point.date)?.upper ?? null),
      percent: true,
    },
  };
}
