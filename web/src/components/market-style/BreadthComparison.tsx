import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import * as echarts from "echarts";
import { fundamentalsApi } from "../../api/client";
import type { BreadthHistoryPoint, RatesHistorySeries } from "../../types";
import { useProjectionSource } from "../observation-library/projectionSources";
import { usErpBands } from "../observation-library/usErpBands";
import { BREADTH_LINES, type HighlightBand } from "../trend/zones";
import { normalizeWindow, panWindow, recentMonthWindow, visibleDateRange, zoomWindow, type ChartWindow } from "../focus-momentum/chart-navigation";
import BreadthReading from "./BreadthReading";
import BreadthInstitutionalReference from "./BreadthInstitutionalReference";
import StarBreadthSnapshot from "./StarBreadthSnapshot";
import { breadthChangeAnnotations } from "./breadthInterpretation";
import { BREADTH_HORIZONS, type BreadthHorizon, type BreadthTrack, type BreadthReadingPoint, type BreadthReadingResponse } from "./breadthReadingTypes";
import { BACKGROUND_STYLES, backgroundRuns, gapText, type BackgroundRun, type BackgroundMode } from "./breadthChartDisplay";
import {
  BASELINE_RULE_IDS_BY_MARKET,
  buildScreenerRuleSpecs,
  evaluateBreadthScreener,
  type AlignedErpPoint,
  type AlignedMacroPoint,
  type BreadthScreenerRuleMeta,
  type DailyValuePoint,
  type EpisodeOutcomeSummary,
  type HorizonForwardStats,
  type RuleIntent,
  type ScreenedEpisode,
  type ScreenerEvaluation,
} from "./breadthRegimeScreener";
import "./breadth-comparison.css";

type Market = "cn" | "us";
type PriceKey = "sse" | "hs300" | "sp500" | "nasdaq";
type View = { dates: string[]; price: (number | null)[]; breadth: (number | null)[][]; bands: HighlightBand[] };
type ZoomRequest = { start: number; end: number; seq: number };
const JOINT_RULES = new Set(["reversal_bottom", "reversal_top"]);
const EMPTY_BREADTH: BreadthHistoryPoint[] = [];

const WINDOWS = [
  { label: "1年", days: 365 },
  { label: "3年", days: 1095 },
  { label: "5年", days: 1825 },
  { label: "全部", days: 12600 },
] as const;
const PRICE_NAMES: Record<PriceKey, string> = { sse: "上证指数", hs300: "沪深300", sp500: "标普500", nasdaq: "纳斯达克综合指数" };
const exists = (value: number | null | undefined): value is number => typeof value === "number" && Number.isFinite(value);
const fmtPct = (value: number | null | undefined, digits = 1) => exists(value) ? `${value.toFixed(digits)}%` : "—";
const fmtSignedPct = (value: number | null | undefined, digits = 2, suffix = "%") =>
  exists(value) ? `${value >= 0 ? "+" : ""}${value.toFixed(digits)}${suffix}` : "—";

function toDailyPoints(series?: RatesHistorySeries): DailyValuePoint[] {
  if (!series || series.dates.length !== series.values.length) return [];
  return series.dates.map((date, idx) => ({
    date,
    value: exists(series.values[idx]) ? series.values[idx] : null,
  }));
}

/** A compact version key for the exact facts visible in this window, including same-date revisions. */
export function fingerprintForView(view: View, market: Market, priceKey: PriceKey,
  windowDays: number, ruleIds: string[], breadthLastDate?: string): string {
  const raw = JSON.stringify([
    market, priceKey, windowDays, ruleIds, breadthLastDate ?? null,
    view.dates, view.price, ...view.breadth,
  ]);
  let hash = 2166136261;
  for (let i = 0; i < raw.length; i++) {
    hash = Math.imul(hash ^ raw.charCodeAt(i), 16777619);
  }
  return `${raw.length}-${(hash >>> 0).toString(16).padStart(8, "0")}`;
}

function seriesMap(series?: RatesHistorySeries) {
  return new Map(series?.dates.map((date, index) => [date, series.values[index] ?? null]) ?? []);
}

function viewFor(series: RatesHistorySeries | undefined, breadth: BreadthHistoryPoint[], days: number): View {
  if (!series?.dates.length) return { dates: [], price: [], breadth: [[], [], []], bands: [] };
  const rawLast = series.dates[series.dates.length - 1];
  let lastValidBreadthDate: string | undefined;
  for (let i = breadth.length - 1; i >= 0; i--) {
    const pt = breadth[i];
    if (BREADTH_HORIZONS.some((h) => exists(pt[`breadth_${h}`]))) {
      lastValidBreadthDate = pt.date;
      break;
    }
  }
  const trailingLagDays = lastValidBreadthDate && lastValidBreadthDate < rawLast
    ? Math.round((Date.parse(`${rawLast}T00:00:00Z`) - Date.parse(`${lastValidBreadthDate}T00:00:00Z`)) / 86_400_000)
    : 0;
  // Align right edge to completed breadth session during routine post-close background refresh (<=7d).
  const last = lastValidBreadthDate && trailingLagDays > 0 && trailingLagDays <= 7
    ? lastValidBreadthDate
    : rawLast;
  const cutoff = new Date(`${last}T00:00:00Z`);
  cutoff.setUTCDate(cutoff.getUTCDate() - days);
  const minDate = cutoff.toISOString().slice(0, 10);
  const prices = seriesMap(series);
  const bmap = new Map(breadth.map((point) => [point.date, point]));
  const firstBreadthDate = breadth.find((point) => BREADTH_HORIZONS.some((h) => exists(point[`breadth_${h}`])))?.date ?? minDate;
  const dates = [...new Set(series.dates.filter((date) => date >= minDate && date >= firstBreadthDate && date <= last))].sort();
  const values = dates.map((date) => prices.get(date) ?? null);
  const b20 = dates.map((date) => bmap.get(date)?.breadth_20 ?? null);
  const b50 = dates.map((date) => bmap.get(date)?.breadth_50 ?? null);
  const b200 = dates.map((date) => bmap.get(date)?.breadth_200 ?? null);
  return { dates, price: values, breadth: [b20, b50, b200], bands: [] };
}

function shade(bands: HighlightBand[]) {
  const areas: Array<[Record<string, unknown>, Record<string, unknown>]> = [];
  const singleDays: Array<Record<string, unknown>> = [];
  for (const band of bands) {
    for (const [start, end] of band.ranges) {
      if (start === end) {
        singleDays.push({ xAxis: start, name: band.label, lineStyle: { color: band.color, opacity: Math.min(0.55, band.opacity + 0.18), width: 2, type: "solid" }, label: { show: false } });
      } else {
        areas.push([{ xAxis: start }, { xAxis: end, itemStyle: { color: band.color, opacity: band.opacity }, name: band.label }]);
      }
    }
  }
  return {
    markArea: areas.length ? { silent: true, label: { show: false }, data: areas as never } : undefined,
    markLine: singleDays.length ? { silent: true, symbol: "none", data: singleDays as never } : undefined,
  };
}

/** Joint display needs both same-day values; never move a marker to a later valid price. */
export function jointProjection(view: View) {
  const values = view.dates.map((_, i) => exists(view.breadth[1][i]) && exists(view.breadth[2][i]) ? view.breadth[1][i] : null);
  const dateIndex = new Map(view.dates.map((date, i) => [date, i]));
  const markers = view.bands.filter((band) => JOINT_RULES.has(band.key)).flatMap((band) =>
    band.ranges.flatMap(([start]) => {
      const i = dateIndex.get(start);
      if (i === undefined || !exists(values[i]) || !exists(view.price[i])) return [];
      return [{ name: band.key === "reversal_bottom" ? "双低" : "双高", value: [start, view.price[i]],
        itemStyle: { color: band.color }, label: { color: band.color, backgroundColor: "rgba(255,255,255,.94)" } }];
    }));
  return { values, markers };
}

/** Paint whole date cells, including a single missing day; never bridge a gap. */
export function backgroundSeries(runs: readonly BackgroundRun[], axis: number): echarts.CustomSeriesOption {
  return {
    name: `__reading_background_${axis}`, type: "custom", coordinateSystem: "cartesian2d",
    xAxisIndex: axis, yAxisIndex: axis, silent: true, z: -1, clip: true,
    tooltip: { show: false }, dimensions: ["start", "end", "run"], encode: { x: [0, 1], y: -1 },
    data: runs.map((run, index) => [run.start, run.end, index]),
    renderItem: (params, api) => {
      const run = runs[Number(api.value(2))];
      if (!run) return;
      const grid = params.coordSys as typeof params.coordSys & { x: number; y: number; width: number; height: number };
      const start = api.coord([api.value(0), 0])[0];
      const end = api.coord([api.value(1), 0])[0];
      const size = api.size?.([1, 0]);
      const half = (Array.isArray(size) ? size[0] : size ?? 1) / 2;
      const left = Math.max(grid.x, start - half);
      const right = Math.min(grid.x + grid.width, end + half);
      if (right <= left) return;
      const style = BACKGROUND_STYLES[run.key];
      const rect = { type: "rect" as const, shape: { x: left, y: grid.y, width: right - left, height: grid.height },
        style: { fill: style.fill, stroke: run.key === "missing" ? "#abb5c1" : "none", lineWidth: .7, lineDash: run.key === "missing" ? [3, 3] : undefined } };
      return { type: "group", children: run.key === "missing" && axis === 1 && right - left >= 25 ? [rect,
        { type: "text", style: { x: (left + right) / 2, y: grid.y + 7, text: "缺测", align: "center", verticalAlign: "top", font: "11px sans-serif", fill: "#526172" } },
      ] : [rect] };
    },
  };
}

/** Snap the current zoomed viewport to the rightmost latest edge while preserving its zoom span. */
export function jumpToLatestWindow(window: ChartWindow): ChartWindow {
  const current = normalizeWindow(window);
  const width = current.end - current.start;
  if (width >= 99.9) return { start: 0, end: 100 };
  const span = Math.max(0.5, width);
  return { start: Math.max(0, 100 - span), end: 100 };
}

/** Convert a horizontal trackpad/wheel delta into a bounded pan of the active zoomed viewport. */
export function panWindowByPixels(window: ChartWindow, deltaPx: number, viewportWidthPx: number): ChartWindow {
  const current = normalizeWindow(window);
  const width = current.end - current.start;
  if (width >= 99.9 || !Number.isFinite(deltaPx) || viewportWidthPx <= 0) return current;
  const fraction = deltaPx / Math.max(180, viewportWidthPx);
  return panWindow(current, fraction);
}

/** Replace display series without losing the user's current zoom in the same chart scope. */
export function createBreadthChartUpdater(chart: echarts.ECharts) {
  let previousScope: string | undefined;
  return (option: echarts.EChartsCoreOption & Pick<echarts.EChartsOption, "dataZoom">, scope: string) => {
    const zoom = previousScope === scope
      ? (chart.getOption().dataZoom as { start?: number; end?: number }[] | undefined)?.[0]
      : undefined;
    const zoomOptions = option.dataZoom;
    const next = zoomOptions && exists(zoom?.start) && exists(zoom?.end)
      ? { ...option, dataZoom: (Array.isArray(zoomOptions) ? zoomOptions : [zoomOptions])
        .map((entry) => ({ ...entry, start: zoom.start, end: zoom.end })) }
      : option;
    chart.setOption(next, true);
    previousScope = scope;
  };
}

function BreadthProjectionChart({ view, priceName, readings, horizon, track, compare, market, windowDays, runs, activeBands, activeMarkers, screeningActive, selectedDate, zoomRequest, isZoomed, onDateChange, onZoomChange }: {
  view: View; priceName: string; readings: ReadonlyMap<string, BreadthReadingPoint>;
  horizon: BreadthHorizon; track: BreadthTrack; compare: boolean; market: Market; windowDays: number;
  runs: readonly BackgroundRun[];
  activeBands: readonly HighlightBand[];
  activeMarkers: ScreenerEvaluation["markers"];
  screeningActive: boolean;
  selectedDate?: string;
  zoomRequest: ZoomRequest | null;
  isZoomed: boolean;
  onDateChange: (date: string) => void;
  onZoomChange: (window: ChartWindow) => void;
}) {
  const node = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);
  const updateChart = useRef<ReturnType<typeof createBreadthChartUpdater> | null>(null);
  const dateSet = useMemo(() => new Set(view.dates), [view.dates]);
  const cursor = useRef({ dates: view.dates, dateSet, onDateChange, onZoomChange });
  cursor.current = { dates: view.dates, dateSet, onDateChange, onZoomChange };
  const selectedDateRef = useRef<string | undefined>(selectedDate);
  selectedDateRef.current = selectedDate;
  const isPointerDownRef = useRef(false);
  const isHoveringRef = useRef(false);
  const lastHoveredDateRef = useRef<string | null>(null);
  const zoomWindowRef = useRef<ChartWindow>({ start: 0, end: 100 });
  const syncSelectedMarkLine = (date?: string) => {
    if (!chart.current) return;
    const markLine = {
      silent: true,
      symbol: "none",
      label: { show: false },
      lineStyle: { color: "#536b80", width: 1, type: "dotted" as const },
      data: date && cursor.current.dateSet.has(date) ? [{ xAxis: date }] : [],
    };
    chart.current.setOption({ series: [{ id: "reading-price-date", markLine }, { id: "reading-breadth-date", markLine }] });
  };
  useEffect(() => {
    const el = node.current;
    if (!el) return;
    const instance = echarts.init(el, undefined, { renderer: "canvas" });
    chart.current = instance;
    updateChart.current = createBreadthChartUpdater(instance);
    const resize = new ResizeObserver(() => instance.resize());
    resize.observe(el);
    let hoverRaf = 0;
    let pendingDate: string | null = null;
    let zoomRaf = 0;
    let pendingZoom: ChartWindow | null = null;
    const flushHover = () => {
      hoverRaf = 0;
      if (pendingDate && !isPointerDownRef.current) {
        const nextDate = pendingDate;
        pendingDate = null;
        cursor.current.onDateChange(nextDate);
      }
    };
    const flushZoom = () => {
      zoomRaf = 0;
      if (pendingZoom) {
        const nextZoom = pendingZoom;
        pendingZoom = null;
        cursor.current.onZoomChange(nextZoom);
      }
    };
    const readCurrentZoom = (): ChartWindow => {
      const dz = (instance.getOption().dataZoom as { start?: number; end?: number }[] | undefined)?.[0];
      return normalizeWindow({ start: Number(dz?.start ?? 0), end: Number(dz?.end ?? 100) });
    };
    instance.on("updateAxisPointer", (event: unknown) => {
      if (isPointerDownRef.current) return;
      const value = (event as { axesInfo?: { value: number | string }[] }).axesInfo?.[0]?.value;
      const date = typeof value === "number" ? cursor.current.dates[value] : value;
      if (!date || !cursor.current.dateSet.has(date) || date === lastHoveredDateRef.current) return;
      lastHoveredDateRef.current = date;
      pendingDate = date;
      if (!hoverRaf) hoverRaf = requestAnimationFrame(flushHover);
    });
    instance.on("datazoom", () => {
      const next = readCurrentZoom();
      zoomWindowRef.current = next;
      pendingZoom = next;
      if (!zoomRaf) zoomRaf = requestAnimationFrame(flushZoom);
    });
    const onPointerDown = () => { isPointerDownRef.current = true; };
    const onPointerUp = () => { isPointerDownRef.current = false; };
    const onPointerEnter = () => { isHoveringRef.current = true; };
    const onPointerLeave = () => {
      isHoveringRef.current = false;
      isPointerDownRef.current = false;
      lastHoveredDateRef.current = null;
      syncSelectedMarkLine(selectedDateRef.current);
    };
    const onWheel = (event: WheelEvent) => {
      // Allow two-finger horizontal trackpad swipes (or Shift+wheel) to pan smoothly when zoomed in.
      const horizontal = Math.abs(event.deltaX) > Math.abs(event.deltaY)
        ? event.deltaX
        : event.shiftKey ? event.deltaY : 0;
      if (!horizontal) return;
      const current = zoomWindowRef.current;
      if (current.end - current.start >= 99.9) return;
      event.preventDefault();
      event.stopPropagation();
      const next = panWindowByPixels(current, horizontal, el.clientWidth || 600);
      if (Math.abs(next.start - current.start) < 1e-4 && Math.abs(next.end - current.end) < 1e-4) return;
      zoomWindowRef.current = next;
      instance.dispatchAction({ type: "dataZoom", start: next.start, end: next.end });
      pendingZoom = next;
      if (!zoomRaf) zoomRaf = requestAnimationFrame(flushZoom);
    };
    el.addEventListener("pointerdown", onPointerDown);
    el.addEventListener("pointerenter", onPointerEnter);
    el.addEventListener("pointerleave", onPointerLeave);
    el.addEventListener("wheel", onWheel, { passive: false });
    window.addEventListener("pointerup", onPointerUp);
    window.addEventListener("pointercancel", onPointerUp);
    return () => {
      if (hoverRaf) cancelAnimationFrame(hoverRaf);
      if (zoomRaf) cancelAnimationFrame(zoomRaf);
      el.removeEventListener("pointerdown", onPointerDown);
      el.removeEventListener("pointerenter", onPointerEnter);
      el.removeEventListener("pointerleave", onPointerLeave);
      el.removeEventListener("wheel", onWheel);
      window.removeEventListener("pointerup", onPointerUp);
      window.removeEventListener("pointercancel", onPointerUp);
      resize.disconnect();
      instance.dispose();
      chart.current = null;
      updateChart.current = null;
    };
  }, []);
  useEffect(() => {
    if (!updateChart.current) return;
    const marks = shade([...activeBands]);
    const focusIndex = BREADTH_HORIZONS.indexOf(horizon);
    const trackLines = track === "off" ? [] : (["lower", "median", "upper"] as const).map((key, index) => ({
      name: track === "historical"
        ? [`${horizon}日历史下轨 P10`, `${horizon}日历史中位 P50`, `${horizon}日历史上轨 P90`][index]
        : track === "stockcharts"
          ? ["StockCharts低位 30%", "半数股票 50%", "StockCharts高位 70%"][index]
          : ["固定低位参考", "半数股票 50%", "固定高位参考"][index],
      type: "line" as const, xAxisIndex: 1, yAxisIndex: 1, showSymbol: false, connectNulls: false,
      data: view.dates.map((date, i) => view.breadth[focusIndex][i] == null ? null
        : track === "historical" ? readings.get(date)?.horizons[horizon]?.[key] ?? null
        : track === "stockcharts" ? [30, 50, 70][index]
        : [market === "cn" ? 20 : 15, 50, market === "cn" ? 80 : 85][index]),
      lineStyle: { color: ["#0f766e", "#536a82", "#b45309"][index], width: index === 1 ? 1.7 : 2.1, type: index === 1 ? "dashed" as const : "solid" as const },
      itemStyle: { color: ["#0f766e", "#536a82", "#b45309"][index] },
    }));
    const exitNames = { exit_high: "退出历史高位", exit_low: "退出历史低位" };
    const exits = track === "historical" ? view.dates.flatMap((date, i) => {
      const event = readings.get(date)?.horizons[horizon]?.event;
      return event === "exit_high" || event === "exit_low" ? [{ name: exitNames[event], value: [date, view.breadth[focusIndex][i]], itemStyle: { color: event === "exit_high" ? "#b45309" : "#0f766e" } }] : [];
    }) : [];
    const turningLabels = screeningActive
      ? activeMarkers
      : breadthChangeAnnotations(view.dates, view.price, readings).slice(-12).map((mark) => ({
          name: mark.label, value: [mark.date, mark.price],
          itemStyle: { color: mark.tone === "supportive" ? "#0f766e" : "#b45309" },
          label: { color: mark.tone === "supportive" ? "#0f766e" : "#b45309", backgroundColor: "rgba(255,255,255,.94)" },
        }));
    let lastValid = view.breadth[focusIndex].length - 1;
    while (lastValid >= 0 && !exists(view.breadth[focusIndex][lastValid])) lastValid--;
    const endMark = lastValid >= 0 && lastValid < view.dates.length - 1 ? {
      symbol: "circle", symbolSize: 7,
      label: { show: true, formatter: `宽度止于 ${view.dates[lastValid].slice(5)}`, position: "left", color: "#526172", fontSize: 11, backgroundColor: "rgba(255,255,255,.94)", padding: [3, 4] },
      data: [{ coord: [view.dates[lastValid], view.breadth[focusIndex][lastValid]] }],
    } : undefined;
    updateChart.current({
      animation: false,
      grid: [{ left: 44, right: 38, top: 52, height: "43%", containLabel: true }, { left: 44, right: 38, top: "63%", height: "19%", containLabel: true }],
      legend: { type: "scroll", selectedMode: false, top: 0, left: 0, right: 0, data: [priceName, ...(compare ? ["20日", "50日", "200日"] : [`${horizon}日`]), ...trackLines.map((line) => line.name)], textStyle: { fontSize: 12, color: "#344256" } },
      tooltip: {
        trigger: "axis",
        confine: true,
        transitionDuration: 0,
        extraCssText: "pointer-events: none;",
        position: (point: [number, number], _params: unknown, _dom: HTMLElement, _rect: unknown, size: { contentSize: [number, number]; viewSize: [number, number] }) => {
          const [x, y] = point;
          const [boxW, boxH] = size.contentSize;
          const [viewW, viewH] = size.viewSize;
          const left = x > viewW * 0.55 ? Math.max(8, x - boxW - 16) : Math.min(viewW - boxW - 8, x + 16);
          const top = Math.max(8, Math.min(viewH - boxH - 46, y - boxH / 2));
          return [left, top];
        },
        axisPointer: { type: "cross", link: [{ xAxisIndex: [0, 1] }] },
        valueFormatter: (value: unknown) => value == null ? "—" : Number(value).toFixed(1),
      },
      axisPointer: { link: [{ xAxisIndex: [0, 1] }] },
      xAxis: [
        { type: "category", gridIndex: 0, data: view.dates, boundaryGap: false, axisPointer: { snap: true }, axisLabel: { show: false }, axisLine: { lineStyle: { color: "#64748b", width: 1.2 } } },
        { type: "category", gridIndex: 1, data: view.dates, boundaryGap: false, axisPointer: { snap: true }, axisLabel: { color: "#344256", fontSize: 11, hideOverlap: true, showMinLabel: true, showMaxLabel: true, formatter: (date: string) => date.slice(2) }, axisLine: { lineStyle: { color: "#64748b", width: 1.2 } } },
      ],
      yAxis: [
        { type: "value", gridIndex: 0, scale: true, min: ({ min, max }: { min: number; max: number }) => Number.isFinite(min) && Number.isFinite(max) ? Math.floor(min - Math.max(max - min, Math.abs(min) * .005, 1) * .08) : undefined, max: ({ min, max }: { min: number; max: number }) => Number.isFinite(min) && Number.isFinite(max) ? Math.ceil(max + Math.max(max - min, Math.abs(max) * .005, 1) * .08) : undefined, name: "指数点位", nameGap: 12, nameTextStyle: { color: "#26364b", fontSize: 12, padding: [0, 0, 4, 0] }, axisLabel: { color: "#344256", fontSize: 12, formatter: (val: number) => Math.round(val).toLocaleString("zh-CN") }, axisLine: { show: true, lineStyle: { color: "#64748b", width: 1.2 } }, splitLine: { lineStyle: { color: "#cbd3dd" } } },
        { type: "value", gridIndex: 1, min: 0, max: 100, name: "宽度（%）", nameGap: 10, nameTextStyle: { color: "#26364b", fontSize: 12, padding: [0, 0, 4, 0] }, axisLabel: { color: "#344256", fontSize: 12, formatter: "{value}%" }, axisLine: { show: true, lineStyle: { color: "#64748b", width: 1.2 } }, splitLine: { lineStyle: { color: "#cbd3dd" } } },
      ],
      dataZoom: [
        {
          type: "inside",
          xAxisIndex: [0, 1],
          filterMode: "filter",
          start: 0,
          end: 100,
          zoomOnMouseWheel: true,
          moveOnMouseMove: true,
          moveOnMouseWheel: "shift",
          preventDefaultMouseMove: true,
          throttle: 16,
        },
        {
          type: "slider",
          xAxisIndex: [0, 1],
          filterMode: "filter",
          start: 0,
          end: 100,
          left: 56,
          right: 40,
          bottom: 6,
          height: 26,
          brushSelect: false,
          realtime: true,
          throttle: 16,
          moveHandleSize: 10,
          handleSize: "115%",
          showDetail: true,
          labelFormatter: (_value: number, dateStr: string) => dateStr,
          borderColor: "#cbd5e1",
          backgroundColor: "#f8fafc",
          fillerColor: "rgba(36, 61, 97, 0.14)",
          handleStyle: { color: "#ffffff", borderColor: "#35678e", borderWidth: 1.5 },
          moveHandleStyle: { color: "#64748b" },
          emphasis: { handleLabel: { show: true }, moveHandleStyle: { color: "#173d68" } },
          textStyle: { color: "#475569", fontSize: 11 },
        },
      ],
      series: [
        backgroundSeries(runs, 0), backgroundSeries(runs, 1),
        { name: priceName, type: "line", xAxisIndex: 0, yAxisIndex: 0, data: view.price, showSymbol: false, connectNulls: false, lineStyle: { width: 3, color: "#243d61" }, itemStyle: { color: "#243d61" } },
        ...view.breadth.map((values, index) => ({ name: BREADTH_LINES[index].name, type: "line" as const,
          xAxisIndex: 1, yAxisIndex: 1, data: values, showSymbol: false, connectNulls: false, markPoint: index === focusIndex ? endMark : undefined,
          lineStyle: { width: index === focusIndex ? 2.7 : 1.5, color: BREADTH_LINES[index].color, opacity: index === focusIndex ? 1 : .6 }, itemStyle: { color: BREADTH_LINES[index].color } })).filter((_, index) => compare || index === focusIndex),
        ...trackLines,
        { name: screeningActive ? "筛选区段起点" : "参与转折观察", type: "scatter", xAxisIndex: 0, yAxisIndex: 0, data: turningLabels,
          symbol: "circle", symbolSize: 7, z: 6, label: { show: true, formatter: "{b}", position: "top", fontSize: 11, padding: [3, 4], borderRadius: 3 }, labelLayout: { hideOverlap: true } },
        { name: "退出历史极端", type: "scatter", xAxisIndex: 1, yAxisIndex: 1, data: exits, symbol: "diamond", symbolSize: 7, z: 5 },
        { id: "reading-price-date", name: "__reading_price_date", type: "line", xAxisIndex: 0, yAxisIndex: 0, data: [], silent: true, tooltip: { show: false } },
        { id: "reading-breadth-date", name: "__reading_breadth_date", type: "line", xAxisIndex: 1, yAxisIndex: 1, data: [], silent: true, tooltip: { show: false } },
        { name: "__price_conditions", type: "line", xAxisIndex: 0, yAxisIndex: 0, data: [], silent: true, tooltip: { show: false }, lineStyle: { opacity: 0 }, ...marks },
        { name: "__breadth_conditions", type: "line", xAxisIndex: 1, yAxisIndex: 1, data: [], silent: true, tooltip: { show: false }, lineStyle: { opacity: 0 }, ...marks },
      ],
    }, `${market}:${priceName}:${windowDays}`);
    const afterZoom = (chart.current?.getOption().dataZoom as { start?: number; end?: number }[] | undefined)?.[0];
    zoomWindowRef.current = normalizeWindow({ start: Number(afterZoom?.start ?? 0), end: Number(afterZoom?.end ?? 100) });
  }, [view, priceName, readings, horizon, track, compare, market, windowDays, runs, activeBands, activeMarkers, screeningActive]);
  useEffect(() => {
    // Avoid calling chart.setOption while hovering or dragging — ECharts' native axisPointer already tracks at 60fps.
    if (isPointerDownRef.current || isHoveringRef.current) return;
    syncSelectedMarkLine(selectedDate);
  }, [selectedDate, view, priceName, readings, horizon, track, compare, market, windowDays, runs, activeBands, activeMarkers, screeningActive]);
  useEffect(() => {
    if (!zoomRequest || !chart.current) return;
    const bounded = normalizeWindow({ start: zoomRequest.start, end: zoomRequest.end });
    zoomWindowRef.current = bounded;
    chart.current.dispatchAction({ type: "dataZoom", start: bounded.start, end: bounded.end });
  }, [zoomRequest]);
  return <div ref={node} className={`bc-chart${isZoomed ? " bc-chart-pannable" : ""}`} role="img" aria-label={`${priceName}价格与同日${compare ? "20、50、200" : horizon}日市场宽度曲线，${screeningActive ? "着色区间显示已选定筛选条件的起止范围" : "背景可显示历史高低区间或参与升降"}；可悬停、直接拖拽平移、双指横滑或用上方导航控件回看`} />;
}

export default function BreadthComparison({ market, onMarketChange, onContextChange, initialRuleId }: {
  market: Market;
  onMarketChange: (market: Market) => void;
  onContextChange?: (context: { windowDays: number; ruleIds: string[]; priceKey: string; fingerprint: string }) => void;
  initialRuleId?: string;
}) {
  const [windowDays, setWindowDays] = useState<number>(1825);
  const [cnPrice, setCnPrice] = useState<"sse" | "hs300">("sse");
  const [usPrice, setUsPrice] = useState<"sp500" | "nasdaq">("sp500");
  const [active, setActive] = useState<ReadonlySet<string>>(() => (initialRuleId ? new Set([initialRuleId]) : new Set()));
  const [horizon, setHorizon] = useState<BreadthHorizon>("50");
  const [track, setTrack] = useState<BreadthTrack>("historical");
  const [compare, setCompare] = useState(true);
  const [showPhases, setShowPhases] = useState(true);
  const [backgroundMode, setBackgroundMode] = useState<BackgroundMode>("levels");
  const [cursorDate, setCursorDate] = useState<string | null>(null);
  const [selectedEpisodeId, setSelectedEpisodeId] = useState("");
  const [zoomRequest, setZoomRequest] = useState<ZoomRequest | null>(null);
  const [zoomState, setZoomState] = useState<ChartWindow>({ start: 0, end: 100 });
  const [showBaselineRules, setShowBaselineRules] = useState<boolean>(() =>
    Boolean(initialRuleId && BASELINE_RULE_IDS_BY_MARKET[market].includes(initialRuleId)),
  );
  const priceKey: PriceKey = market === "cn" ? cnPrice : usPrice;
  const breadthId = market === "cn" ? "CN_ALL_A" : "SP500";
  const breadth = useQuery({ queryKey: ["overlayBreadthReading", breadthId, 12600],
    queryFn: async ({ signal }): Promise<BreadthReadingResponse> => {
      const response = await fetch(`/api/market-context/breadth-history?market_id=${breadthId}&lookback_days=12600&include_observation=true`, { signal });
      if (!response.ok) throw new Error(`宽度历史读取失败 (${response.status})`);
      return response.json();
    }, staleTime: 5 * 60_000, refetchInterval: 5 * 60_000 });
  const overlay = useQuery({ queryKey: ["fundOverlay", 47],
    queryFn: () => fundamentalsApi.overlayHistory(47), staleTime: 5 * 60_000, refetchInterval: 5 * 60_000 });
  const ratesQuery = useQuery({ queryKey: ["fundamentalsRatesHistory", 18250],
    queryFn: () => fundamentalsApi.ratesHistory(18250), staleTime: 5 * 60_000, refetchInterval: 5 * 60_000, retry: false });
  const usMacroQuery = useQuery({ queryKey: ["fundamentalsUsMacro"],
    queryFn: () => fundamentalsApi.usMacro(), enabled: market === "us", staleTime: 30 * 60_000, retry: false });
  const erpSource = useProjectionSource(market === "cn" ? "erp-cn" : "erp-us");
  const erpRows = useMemo(
    () => (market === "cn" ? (erpSource.bands ?? []) : usErpBands(erpSource.points)),
    [market, erpSource.bands, erpSource.points],
  );
  const priceSeries = overlay.data?.series[priceKey];
  const auxSeries = useMemo(() => ({
    marginRatio: toDailyPoints(ratesQuery.data?.series.margin_rzyezb),
    vix: toDailyPoints(ratesQuery.data?.series.vix),
    vixTerm: toDailyPoints(ratesQuery.data?.series.vix_term),
    hyOas: toDailyPoints(usMacroQuery.data?.series.hy_oas),
    fullPrice: toDailyPoints(priceSeries),
  }), [ratesQuery.data, usMacroQuery.data, priceSeries]);
  const points = breadth.data?.history ?? EMPTY_BREADTH;
  const view = useMemo(() => viewFor(priceSeries, points, windowDays), [priceSeries, points, windowDays]);
  const readings = useMemo(() => new Map(breadth.data?.observation?.history.map((row) => [row.date, row]) ?? []), [breadth.data?.observation]);
  const ruleSpecs = useMemo(() => buildScreenerRuleSpecs(market, horizon), [market, horizon]);
  const visibleRuleSpecs = useMemo(
    () => ruleSpecs.filter((rule) => rule.tier !== "hidden" || active.has(rule.id)),
    [ruleSpecs, active],
  );
  const coreBullRules = useMemo(() => visibleRuleSpecs.filter((rule) => rule.tier === "core" && rule.intent === "bull"), [visibleRuleSpecs]);
  const coreRiskRules = useMemo(() => visibleRuleSpecs.filter((rule) => rule.tier === "core" && rule.intent !== "bull"), [visibleRuleSpecs]);
  const baselineRules = useMemo(() => visibleRuleSpecs.filter((rule) => rule.tier !== "core"), [visibleRuleSpecs]);
  const activeRuleIds = useMemo(() => visibleRuleSpecs.filter((rule) => active.has(rule.id)).map((rule) => rule.id), [visibleRuleSpecs, active]);
  const baselineActiveCount = useMemo(() => baselineRules.filter((rule) => active.has(rule.id)).length, [baselineRules, active]);
  const screeningActive = activeRuleIds.length > 0;
  const screener = useMemo(() => evaluateBreadthScreener({
    market,
    horizon,
    dates: view.dates,
    prices: view.price,
    breadth: view.breadth,
    readings,
    erpBands: erpRows,
    activeIds: active,
    auxSeries,
  }), [market, horizon, view, readings, erpRows, active, auxSeries]);
  const runs = useMemo(() => backgroundRuns(
    view.dates,
    view.breadth[BREADTH_HORIZONS.indexOf(horizon)],
    readings,
    showPhases && !screeningActive,
    backgroundMode,
    horizon,
  ), [view, horizon, readings, showPhases, backgroundMode, screeningActive]);
  const gaps = useMemo(() => gapText(runs, view.dates), [runs, view.dates]);
  const pointByDate = useMemo(() => new Map(points.map((row) => [row.date, row])), [points]);
  const lastBreadthDate = points[points.length - 1]?.date;
  const comparableDates = useMemo(() => view.dates.filter((_, index) =>
    exists(view.price[index]) && view.breadth.some((line) => exists(line[index]))), [view]);
  const lastComparableDate = comparableDates[comparableDates.length - 1];
  const selectedDate = cursorDate && view.dates.includes(cursorDate) ? cursorDate : lastComparableDate;
  const reading = selectedDate ? readings.get(selectedDate) : undefined;
  const selectedPoint = selectedDate ? pointByDate.get(selectedDate) : undefined;
  const selectedIndex = useMemo(() => (selectedDate ? view.dates.indexOf(selectedDate) : -1), [selectedDate, view.dates]);
  const erpAtSelected: AlignedErpPoint | null = selectedIndex >= 0 ? screener.alignedErp[selectedIndex] ?? null : null;
  const macroAtSelected: AlignedMacroPoint | null = selectedIndex >= 0 ? screener.alignedMacro[selectedIndex] ?? null : null;
  useEffect(() => {
    setCursorDate(null);
    setSelectedEpisodeId("");
    setZoomRequest(null);
    setZoomState({ start: 0, end: 100 });
  }, [market, windowDays, priceKey]);
  const lastPriceDate = priceSeries?.dates[priceSeries.dates.length - 1];
  const dateSelectOptions = useMemo(
    () => view.dates.map((date) => (
      <option key={date} value={date}>{date}{pointByDate.has(date) ? "" : " · 宽度缺失"}</option>
    )),
    [view.dates, pointByDate],
  );
  const visibleSpan = useMemo(() => visibleDateRange(view.dates, zoomState), [view.dates, zoomState]);
  const isZoomed = zoomState.end - zoomState.start < 99.9;
  const atLatestEdge = zoomState.end >= 99.9;
  const applyZoom = (next: ChartWindow) => {
    const bounded = normalizeWindow(next);
    setZoomState(bounded);
    setZoomRequest((prev) => ({ start: bounded.start, end: bounded.end, seq: (prev?.seq ?? 0) + 1 }));
  };
  const handleChartZoomChange = (next: ChartWindow) => {
    setZoomState((prev) => (
      Math.abs(prev.start - next.start) < 0.05 && Math.abs(prev.end - next.end) < 0.05 ? prev : next
    ));
  };
  const recentPresetActive = (months: number) => {
    const target = recentMonthWindow(view.dates, months);
    return Math.abs(zoomState.start - target.start) < 0.15 && Math.abs(zoomState.end - target.end) < 0.15;
  };
  const jumpToLatest = () => {
    setCursorDate(null);
    setSelectedEpisodeId("");
    if (!atLatestEdge) applyZoom(jumpToLatestWindow(zoomState));
  };
  const fingerprint = useMemo(
    () => fingerprintForView(view, market, priceKey, windowDays, activeRuleIds, lastBreadthDate),
    [view, market, priceKey, windowDays, activeRuleIds, lastBreadthDate],
  );
  const callback = useRef(onContextChange);
  callback.current = onContextChange;
  useEffect(() => { callback.current?.({ windowDays, ruleIds: activeRuleIds, priceKey, fingerprint }); }, [fingerprint]);
  const toggleRule = (id: string) => {
    setSelectedEpisodeId("");
    setActive((previous) => {
      const next = new Set(previous);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };
  const focusEpisode = (episodeId: string) => {
    setSelectedEpisodeId(episodeId);
    const ep: ScreenedEpisode | undefined = screener.episodes.find((item) => item.id === episodeId);
    if (!ep) return;
    setCursorDate(ep.startDate);
    const total = Math.max(1, view.dates.length - 1);
    let startPct = Math.max(0, ((ep.startIndex - 30) / total) * 100);
    let endPct = Math.min(100, ((ep.endIndex + 60) / total) * 100);
    if (endPct - startPct < 6) {
      const mid = (startPct + endPct) / 2;
      startPct = Math.max(0, mid - 3);
      endPct = Math.min(100, mid + 3);
    }
    applyZoom({ start: startPct, end: endPct });
  };
  const resetZoom = () => {
    setSelectedEpisodeId("");
    setCursorDate(null);
    applyZoom({ start: 0, end: 100 });
  };
  const selHorizonStats = reading?.horizons[horizon];
  const coldFixed = market === "cn" ? 20 : 15;
  const hotFixed = market === "cn" ? 80 : 85;
  const renderForwardCell = (label: string, stats: HorizonForwardStats, mode: RuleIntent) => {
    if (stats.sampleCount === 0) {
      return (
        <div className="bc-score-cell">
          <span className="bc-score-horizon">{label}</span>
          <span className="bc-score-empty">样本未满{stats.horizonBars}交易日（待完整走完）</span>
        </div>
      );
    }
    const isRisk = mode === "risk";
    const isNeutral = mode === "neutral";
    const edgeTone = !exists(stats.edgeMean) || isNeutral
      ? "flat"
      : isRisk
        ? (stats.edgeMean <= 0 ? "pos" : "neg")
        : (stats.edgeMean >= 0 ? "pos" : "neg");
    const fallRate = exists(stats.winRate) ? 100 - stats.winRate : null;
    return (
      <div className="bc-score-cell">
        <span className="bc-score-horizon">{label} <em>({stats.sampleCount}次)</em></span>
        {isRisk ? (
          <span title={`后续上涨占比 ${fmtPct(stats.winRate)}`}>下跌/走弱率 <b>{fmtPct(fallRate)}</b></span>
        ) : (
          <span>上涨率 <b>{fmtPct(stats.winRate)}</b></span>
        )}
        <span>{isRisk ? "后市均值" : "均值"} <b>{fmtSignedPct(stats.meanReturn)}</b></span>
        {exists(stats.edgeMean) && (
          <span className={`bc-score-edge bc-score-edge-${edgeTone}`}>
            {isRisk
              ? (stats.edgeMean <= 0 ? `跑输基准 ${fmtSignedPct(stats.edgeMean, 2, "pp")}` : `较基准反涨 ${fmtSignedPct(stats.edgeMean, 2, "pp")}`)
              : `较窗口基准 ${fmtSignedPct(stats.edgeMean, 2, "pp")}`}
          </span>
        )}
        <span>中位 <b>{fmtSignedPct(stats.medianReturn)}</b></span>
        <span>均最大回撤 <b>{fmtSignedPct(stats.avgMaxDrawdown)}</b></span>
      </div>
    );
  };
  const renderScorecardBlock = (title: string, outcome: EpisodeOutcomeSummary, mode: RuleIntent, key: string) => (
    <div key={key} className={`bc-quant-scorecard bc-scorecard-${mode}`} aria-label={`${title}历史触发后收益统计`}>
      <div className="bc-score-head">
        <span className={`bc-score-badge bc-score-badge-${mode}`}>{title} · {PRICE_NAMES[priceKey]}</span>
        <span>
          这段时间共出现 <b>{outcome.dedupEpisodeCount}</b> 次（{outcome.cooldownBars}日内重复算1次，共 {outcome.rawEpisodeCount} 段 · 按每次刚出现那天收盘价往后算）
        </span>
      </div>
      <div className="bc-score-grid">
        {renderForwardCell("后 20 交易日", outcome.d20, mode)}
        {renderForwardCell("后 60 交易日", outcome.d60, mode)}
      </div>
    </div>
  );

  return <section className="breadth-comparison" aria-labelledby="bc-title">
    <header className="bc-heading">
      <div><h2 id="bc-title">价格与市场宽度投影</h2><p>同日曲线与条件标注 · 历史观察</p></div>
      <div className="bc-controls" role="group" aria-label="价格范围与期间">
        <span className="bc-window-switch">{WINDOWS.map((window) => <button key={window.days} type="button" aria-pressed={windowDays === window.days} onClick={() => setWindowDays(window.days)}>{window.label}</button>)}</span>
      </div>
    </header>
    <div className="bc-controls bc-market-controls">
      <div className="bc-price-switch" role="group" aria-label="宽度投影市场"><button type="button" aria-pressed={market === "cn"} onClick={() => onMarketChange("cn")}>A股</button><button type="button" aria-pressed={market === "us"} onClick={() => onMarketChange("us")}>美股</button></div>
      <div className="bc-price-switch" role="group" aria-label="宽度投影价格指数">
        {market === "cn" ? <><button type="button" aria-pressed={cnPrice === "sse"} onClick={() => setCnPrice("sse")}>上证指数</button><button type="button" aria-pressed={cnPrice === "hs300"} onClick={() => setCnPrice("hs300")}>沪深300</button></>
          : <><button type="button" aria-pressed={usPrice === "sp500"} onClick={() => setUsPrice("sp500")}>标普500</button><button type="button" aria-pressed={usPrice === "nasdaq"} onClick={() => setUsPrice("nasdaq")}>纳斯达克</button></>}
      </div>
      <div className="bc-price-switch" role="group" aria-label="主看均线宽度周期">
        <span className="bc-control-label">主看周期</span>
        {BREADTH_HORIZONS.map((period) => (
          <button key={period} type="button" aria-pressed={horizon === period} onClick={() => setHorizon(period)}>
            {period}日
          </button>
        ))}
        <label className="bc-compare-toggle">
          <input type="checkbox" checked={compare} onChange={(event) => setCompare(event.target.checked)} />
          三线同看
        </label>
      </div>
      <div className="bc-price-switch" role="group" aria-label="宽度参考轨道快捷切换">
        <button type="button" aria-pressed={track === "historical"} onClick={() => setTrack("historical")}>动态分位轨 P10/P90</button>
        <button type="button" aria-pressed={track === "stockcharts"} onClick={() => setTrack("stockcharts")}>固定参考 30%/70%</button>
        <button type="button" aria-pressed={track === "fixed"} onClick={() => setTrack("fixed")}>本地 {coldFixed}%/{hotFixed}%</button>
        <button type="button" aria-pressed={track === "off"} onClick={() => setTrack("off")}>关闭轨道</button>
      </div>
    </div>
    <p className="bc-scope">{market === "cn" ? `全A股票宽度 × ${PRICE_NAMES[priceKey]}价格` : `标普500股票样本宽度 × ${PRICE_NAMES[priceKey]}价格`}</p>
    {market === "cn" && <StarBreadthSnapshot />}
    <p className="bc-dates" title={`价格截至 ${lastPriceDate ?? "未提供"}；宽度截至 ${lastBreadthDate ?? "未提供"}；收盘数据由后台定时自动同步`}>图示区间 {view.dates[0] ?? "—"}—{view.dates[view.dates.length - 1] ?? "—"}</p>
    {breadth.isPending || overlay.isPending ? <p className="bc-state" role="status">正在读取历史曲线…</p> : null}
    {breadth.isError || overlay.isError ? <p className="bc-state bc-error" role="alert">{breadth.isError ? "宽度历史读取失败。" : "指数价格历史读取失败。"}暂不能显示同期对照。</p> : null}
    {!breadth.isPending && !overlay.isPending && !breadth.isError && !overlay.isError && (!view.dates.length || !view.breadth.some((line) => line.some(exists))) &&
      <p className="bc-state">此期间没有价格与宽度同日可比资料。</p>}
    {view.dates.length > 0 && view.breadth.some((line) => line.some(exists)) && !breadth.isError && !overlay.isError && <div className="bc-main">
      <div className="bc-chart-pane">
      <div className="bc-threshold-spec" aria-label="宽度阈值与业界口径">
        <div className="bc-spec-row">
          <strong>{selectedDate ?? "—"} 读数：</strong>
          <span>20日 <b>{fmtPct(selectedPoint?.breadth_20)}</b></span>
          <span>50日 <b>{fmtPct(selectedPoint?.breadth_50)}</b></span>
          <span>200日 <b>{fmtPct(selectedPoint?.breadth_200)}</b></span>
          {erpAtSelected?.value != null && (
            <span>
              股债利差 <b>{erpAtSelected.value.toFixed(2)}pp</b>
              {erpAtSelected.z != null ? ` (${erpAtSelected.z >= 0 ? "+" : ""}${erpAtSelected.z.toFixed(2)}σ)` : ""}
            </span>
          )}
          {market === "cn" && exists(macroAtSelected?.marginRatio) && (
            <span>
              两融占流通比 <b>{macroAtSelected.marginRatio.toFixed(2)}%</b>
              {exists(macroAtSelected?.marginPercentile) ? ` (3年P${Math.round(macroAtSelected.marginPercentile)})` : ""}
            </span>
          )}
          {market === "us" && exists(macroAtSelected?.vix) && (
            <span>
              VIX <b>{macroAtSelected.vix.toFixed(1)}</b>
              {exists(macroAtSelected?.vixTerm) ? ` · 期限比 ${macroAtSelected.vixTerm.toFixed(2)}` : ""}
            </span>
          )}
          {market === "us" && exists(macroAtSelected?.hyOas) && (
            <span>HY OAS <b>{macroAtSelected.hyOas.toFixed(2)}%</b></span>
          )}
        </div>
        <div className="bc-spec-row">
          <span>
            <b>{horizon}日历史低位/高位</b>（滚动5年·1260交易日）：
            {selHorizonStats?.status === "ready"
              ? ` 低位 ≤P10 ${fmtPct(selHorizonStats.lower)} ｜ 中枢 P50 ${fmtPct(selHorizonStats.median)} ｜ 高位 ≥P90 ${fmtPct(selHorizonStats.upper)}`
              : ` 样本 ${selHorizonStats?.sample_count ?? 0}/252 预热中`}
          </span>
          <span className="bc-spec-muted">
            业界参考：StockCharts 50日 &lt;30%超卖/&gt;70%强势 · 200日 50%牛熊分界 ｜ 极值固定线：{market === "cn" ? "A股 20%/80%" : "美股 15%/85%，Schwab <10%极端抛售"}
          </span>
        </div>
      </div>
      <div className="bc-screener-panel" aria-label="核心实战信号组合筛选">
        <div className="bc-screener-head">
          <strong>历史验证信号</strong>
          <span>只留长期真管用的 {coreBullRules.length + coreRiskRules.length} 个（买点 {coreBullRules.length} · 卖点 {coreRiskRules.length}）</span>
          <div className="bc-screener-actions">
            <button
              type="button"
              className="bc-screener-toggle"
              aria-expanded={showBaselineRules}
              onClick={() => setShowBaselineRules((prev) => !prev)}
            >
              {showBaselineRules ? "收起单看高低 ▴" : baselineActiveCount > 0 ? `单看高低位置 (已选${baselineActiveCount}) ▾` : `单看高低位置 (${baselineRules.length}) ▾`}
            </button>
            {screeningActive && (
              <button type="button" className="bc-screener-clear" onClick={() => { setActive(new Set()); setSelectedEpisodeId(""); }}>
                清空
              </button>
            )}
          </div>
        </div>
        {screener.latestActiveRuleIds.length > 0 && (
          <div className="bc-latest-hit" aria-label="最新交易日已触发信号">
            <span className="bc-latest-hit-label">最新日 ({lastComparableDate?.slice(5) ?? "—"}) 命中</span>
            {screener.latestActiveRuleIds.map((ruleId) => {
              const rule = visibleRuleSpecs.find((item) => item.id === ruleId);
              if (!rule) return null;
              return (
                <button
                  key={rule.id}
                  type="button"
                  aria-pressed={active.has(rule.id)}
                  onClick={() => toggleRule(rule.id)}
                >
                  <span className="bc-rule-dot" style={{ background: rule.color }} aria-hidden="true" />
                  {rule.short}
                </button>
              );
            })}
          </div>
        )}
        {(() => {
          const renderRulePill = (rule: BreadthScreenerRuleMeta) => {
            const count = screener.byRule[rule.id]?.episodeCount ?? 0;
            return (
              <button
                key={rule.id}
                type="button"
                aria-pressed={active.has(rule.id)}
                title={`${rule.formula}｜${rule.basis}${rule.coverageNote ? `｜${rule.coverageNote}` : ""}`}
                onClick={() => toggleRule(rule.id)}
              >
                <span className="bc-rule-dot" style={{ background: rule.color }} aria-hidden="true" />
                <span>{rule.short}</span>
                {rule.coverageNote && <em className="bc-pill-cov" title={rule.coverageNote}>23-11起</em>}
                <em className="bc-pill-count">{count}段</em>
              </button>
            );
          };
          return (
            <>
              <div className="bc-screener-core-grid">
                <div className="bc-screener-cluster" role="group" aria-label="核心买点参考">
                  <span className="bc-cluster-tag bc-cluster-bull">买点</span>
                  <div className="bc-screener-pills">{coreBullRules.map(renderRulePill)}</div>
                </div>
                <div className="bc-screener-cluster" role="group" aria-label="核心卖点与风控">
                  <span className="bc-cluster-tag bc-cluster-risk">卖点</span>
                  <div className="bc-screener-pills">{coreRiskRules.map(renderRulePill)}</div>
                </div>
              </div>
              {showBaselineRules && (
                <div className="bc-screener-row bc-screener-baseline" role="group" aria-label="基础水位与补充观察">
                  <span className="bc-screener-group">水位与补充</span>
                  <div className="bc-screener-pills">{baselineRules.map(renderRulePill)}</div>
                </div>
              )}
            </>
          );
        })()}
        {screeningActive && (
          <div className="bc-screener-active">
            <div className="bc-screener-notes">
              {activeRuleIds.map((ruleId) => {
                const rule = visibleRuleSpecs.find((item) => item.id === ruleId);
                if (!rule) return null;
                return (
                  <p key={rule.id}>
                    <span className="bc-rule-dot" style={{ background: rule.color }} aria-hidden="true" />
                    <b>{rule.short}</b>：{rule.formula} — <span>{rule.basis}</span>
                    {rule.coverageNote && <span className="bc-note-cov">{rule.coverageNote}</span>}
                  </p>
                );
              })}
            </div>
            {(() => {
              const hasBull = screener.activeIntents.includes("bull");
              const hasRisk = screener.activeIntents.includes("risk");
              const hasNeutral = screener.activeIntents.includes("neutral");
              if (hasBull && hasRisk) {
                return (
                  <div className="bc-scorecard-split">
                    <p className="bc-scorecard-mix-note">已同时勾选买点与卖点，已按方向拆开统计以免正负收益互相抵消：</p>
                    {renderScorecardBlock("买点组合战绩", screener.outcomeByIntent.bull, "bull", "bull")}
                    {renderScorecardBlock("卖点风控校验", screener.outcomeByIntent.risk, "risk", "risk")}
                  </div>
                );
              }
              if (hasRisk) {
                return renderScorecardBlock("卖点风控校验", screener.outcomeByIntent.risk, "risk", "risk");
              }
              if (hasBull) {
                return renderScorecardBlock("买点历史战绩", screener.outcomeByIntent.bull, "bull", "bull");
              }
              if (hasNeutral) {
                return renderScorecardBlock("水位观察统计", screener.outcomeByIntent.neutral, "neutral", "neutral");
              }
              return renderScorecardBlock("历史触发战绩", screener.outcome, "bull", "all");
            })()}
            <div className="bc-screener-jump">
              <label>
                命中区间 ({screener.episodes.length}段)
                <select
                  aria-label="查看命中历史区间"
                  value={selectedEpisodeId}
                  onChange={(event) => {
                    const id = event.target.value;
                    if (!id) { resetZoom(); return; }
                    focusEpisode(id);
                  }}
                >
                  <option value="">选择区间并定位缩放…</option>
                  {[...screener.episodes].reverse().map((ep) => (
                    <option key={ep.id} value={ep.id}>
                      {ep.startDate}{ep.endDate !== ep.startDate ? `—${ep.endDate}` : ""} · {ep.days}日 · {ep.ruleLabel}
                    </option>
                  ))}
                </select>
              </label>
              <button type="button" onClick={resetZoom}>重置缩放</button>
            </div>
          </div>
        )}
      </div>
      {showPhases && !screeningActive && <div className="bc-inline-legend">{backgroundMode === "levels" ? <><span>底色 · {horizon}日宽度</span><span className="bc-low">历史低位 ≤P10</span><span className="bc-high">历史高位 ≥P90</span></> : <><span>底色 · 20/50日参与</span><span className="bc-low">回升</span><span className="bc-high">收缩</span></>}</div>}
      <div className="bc-zoom-nav" role="toolbar" aria-label="图表缩放与区间导航">
        <div className="bc-zoom-group" role="group" aria-label="快捷近端视图">
          <button type="button" aria-pressed={recentPresetActive(3)} onClick={() => { setSelectedEpisodeId(""); setCursorDate(null); applyZoom(recentMonthWindow(view.dates, 3)); }}>近3月</button>
          <button type="button" aria-pressed={recentPresetActive(6)} onClick={() => { setSelectedEpisodeId(""); setCursorDate(null); applyZoom(recentMonthWindow(view.dates, 6)); }}>近6月</button>
          {windowDays > 365 && (
            <button type="button" aria-pressed={recentPresetActive(12)} onClick={() => { setSelectedEpisodeId(""); setCursorDate(null); applyZoom(recentMonthWindow(view.dates, 12)); }}>近1年</button>
          )}
          <button type="button" aria-pressed={!isZoomed} onClick={resetZoom}>全览</button>
        </div>
        <div className="bc-zoom-group" role="group" aria-label="平移与缩放">
          <button type="button" onClick={() => applyZoom(panWindow(zoomState, -0.5))} disabled={zoomState.start <= 0.05} title="向左平移半屏">← 左移</button>
          <button type="button" onClick={() => applyZoom(panWindow(zoomState, 0.5))} disabled={atLatestEdge} title="向右平移半屏">右移 →</button>
          <button type="button" className={!atLatestEdge ? "bc-zoom-latest-cta" : undefined} onClick={jumpToLatest} disabled={atLatestEdge && cursorDate == null} title="保持当前缩放比例并一键跳到最右侧最新日期">跳到最新 ⇥</button>
          <button type="button" onClick={() => applyZoom(zoomWindow(zoomState, 0.6))} disabled={zoomState.end - zoomState.start <= 0.6} aria-label="放大" title="放大时间轴">＋</button>
          <button type="button" onClick={() => applyZoom(zoomWindow(zoomState, 1.6))} disabled={!isZoomed} aria-label="缩小" title="缩小时间轴">－</button>
        </div>
        <span className="bc-zoom-range" title="可直接拖拽底部滑块、拖动画布，或双指横向滑动平移">
          {visibleSpan.start ?? "—"} — {visibleSpan.end ?? "—"}
        </span>
      </div>
      <BreadthProjectionChart view={view} priceName={PRICE_NAMES[priceKey]} readings={readings} horizon={horizon} track={track} compare={compare} market={market} windowDays={windowDays} runs={runs} activeBands={screener.bands} activeMarkers={screener.markers} screeningActive={screeningActive} selectedDate={selectedDate} zoomRequest={zoomRequest} isZoomed={isZoomed} onDateChange={setCursorDate} onZoomChange={handleChartZoomChange} />
      {!screeningActive && <BreadthInstitutionalReference market={market} horizon={horizon} />}
      <details className="bc-chart-settings"><summary>图表设置与资料说明</summary>
      <div className="bc-reader-controls bc-controls">
        <div role="group" aria-label="图中主要宽度周期"><span className="bc-control-label">强调周期</span>{BREADTH_HORIZONS.map((period) => <button type="button" key={period} aria-pressed={horizon === period} onClick={() => setHorizon(period)}>{period}日</button>)}</div>
        <label>参照轨道 <select aria-label="参照轨道" value={track} onChange={(event) => setTrack(event.target.value as BreadthTrack)}><option value="historical">历史分位上下轨 (P10/P90)</option><option value="stockcharts">StockCharts 固定参考 (30%/70%)</option><option value="fixed">本地固定高低参考 ({coldFixed}%/{hotFixed}%)</option><option value="off">关闭轨道</option></select></label>
        <label className="bc-compare-toggle"><input type="checkbox" checked={compare} onChange={(event) => setCompare(event.target.checked)} />三线对照</label>
      </div>
      <div className="bc-background-legend" aria-label="背景颜色图例">
      <label><input type="checkbox" checked={showPhases && !screeningActive} disabled={screeningActive} onChange={(event) => setShowPhases(event.target.checked)} />背景色带</label>
      <select aria-label="背景含义" value={backgroundMode} disabled={!showPhases || screeningActive} onChange={(event) => setBackgroundMode(event.target.value as BackgroundMode)}><option value="levels">宽度高低区间</option><option value="phases">宽度参与升降</option></select>
      {Object.entries(BACKGROUND_STYLES).filter(([key]) => key === "missing" || showPhases && !screeningActive && (backgroundMode === "levels" ? ["low", "high"].includes(key) : !["low", "high"].includes(key))).map(([key, style]) => <span key={key}><i style={{ backgroundColor: style.fill, borderColor: style.color }} aria-hidden="true" />{style.label}</span>)}
      <small>{screeningActive ? "条件筛选启用时仅高亮所选组合与缺测色带" : !showPhases ? "缺测标记始终保留" : backgroundMode === "levels" ? `${horizon}日历史P10/P90 · 看位置；切换「参与升降」看方向` : "20/50日合看 · 空白为分歧、暂稳或状态未知"}</small>
      </div>
      <p className="bc-track-hint">{screeningActive ? "筛选区段同时着色于上方指数图与下方宽度图；点击「命中区间」可自动缩放到对应历史片段。" : track === "historical" ? `${horizon}日宽度 · 虚线：历史10%／90%分位，点线：中位 · 菱形：退出历史高位或低位。高位可以延续，不等于见顶。`
      : track === "fixed" ? `${horizon}日宽度 · 高${hotFixed}%／低${coldFixed}%为固定经验参考，50%表示半数股票。`
      : `${horizon}日宽度 · 轨道已关闭，仍可查看原始曲线与下方读数。`}</p>
      <p className="bc-caption">{screeningActive ? "圆点是图示窗口内各筛选区段的起点，供结构对照，不做孤立买卖指令。" : "为避免拥挤，图上只显示部分参与变化标签；背景保留所选含义的逐日状态，缺测留白。"}</p>
      {gaps && <p className="bc-gap-note" role="note"><b>{horizon}日宽度的断线说明</b><span>{gaps}。灰带内不连接宽度线，也不延用参与状态。</span></p>}
    <details className="bc-source"><summary>联合阈值有机构依据吗？</summary>
      <p>当前A股{coldFixed}/{hotFixed}、美股15/85沿用本系统已有固定极值条件，200日50%线及StockCharts 50日30%/70%来自海外公开技术面文献；本系统更推荐搭配近5年动态P10/P90分位线适应结构变化。</p>
      <p><a href="https://d28lcup14p4e72.cloudfront.net/273862/8818055/BofA%20-%20Hartnett%20-%20The%20Flow%20Show_20240531.pdf" target="_blank" rel="noreferrer">BofA 2024-05-31报告</a>与<a href="https://kathrein.at/assets/Uploads/PDFs/Insti/GECONHND25_08.pdf" target="_blank" rel="noreferrer">Ned Davis Research 2025年4月资料</a>均采用多周期联合与高位宽度背离框架；高宽度在强势多头中可长期持续，应防单纯极值逆势猜顶。</p>
    </details>
    <p className="bc-caption"><a href="/fundamentals?section=overlay#fund-sec-overlay">原长周期叠加：指数 × 利率／两融／VIX →</a></p>
    <details className="bc-source"><summary>轨道口径、状态依据与来源</summary><p>价格资料截至 {lastPriceDate ?? "未提供"}，宽度资料截至 {lastBreadthDate ?? "未提供"}；同日有效区间 {comparableDates[0] ?? "—"}—{lastComparableDate ?? "—"}。</p><p>历史轨道采用截至所示日期最近1260个有效读数（含当日）的10%、50%、90%分位，至少252个有效值才显示；它描述历史分布，不是预测区间。历史百分位采用不高于当日值的样本比例；变化比较5条记录前，不承诺等于5个交易日。缺值留白，不填补。</p><p>“上涨支撑增强”表示20/50日宽度均回升且三周期均≥50%；“低位参与回暖／高位参与转弱”表示此前5条记录中20/50日宽度曾同处固定低位／高位，目前均反向变化。其余状态描述参与回升、收缩或分歧。状态依据固定经验值（A股20/80、美股15/85），越轨事件依据历史分位，两者含义不同。当前没有100日宽度数据。</p><p>宽度是股票中有多少比例站在各自均线上方。<a href="https://chartschool.stockcharts.com/table-of-contents/market-indicators/percent-above-moving-average" target="_blank" rel="noreferrer">StockCharts 指标定义</a>仅供解释，不是本系统数据来源，也不为本图的分位参数背书。</p>{market === "cn" && <p>2026-11-02修复记录：08-19至10-30按当日取得的5,577只股票名单回看，以WeStock前复权日线统一重建；各周期分别排除当日非交易股票及上市后有效记录不足的新股。它不是逐日历史成员还原。更早的旧记录保留原值；本次补齐不代表长期分位阈值已通过效果验证。</p>}<p>价格与宽度沿用现有接口，严格同日对齐。全A宽度不是沪深300成分股专属宽度，美股沿用标普500股票样本，尚非逐日还原的官方成分股，也非纳指专属宽度。当前接口未给出逐日完整覆盖率；这些限制会影响历史对照。新轨道和状态仅帮助读图，尚无顶底识别或收益增量验证。</p></details>
      </details>
      </div>
      <div className="bc-reading-pane">
      <div className="bc-review-controls">
        <label>回看日期 <select aria-label="宽度回看日期" value={selectedDate ?? ""} onChange={(event) => setCursorDate(event.target.value)}>{dateSelectOptions}</select></label>
        <button type="button" onClick={jumpToLatest}>最近同日读数</button><span>图上悬停可同步回看</span>
      </div>
      <BreadthReading date={selectedDate} point={selectedPoint} reading={reading} horizon={horizon} onHorizonChange={setHorizon} error={breadth.data?.observation?.error} />
      </div>
    </div>}

  </section>;
}
