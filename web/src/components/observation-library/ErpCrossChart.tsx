import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import * as echarts from "echarts";
import { fundamentalsApi } from "../../api/client";
import { alignProjection } from "./projectionAlignment";
import { ERP_BAND_METHOD } from "./erpBands";
import { erpPositionObservation, erpTrendObservation, erpResearchMapping, ERP_RESEARCH_MATRIX, TREND_STATE_NAMES } from "./erpTrendObservation";
import { useProjectionSource } from "./projectionSources";
import ErpEffectSummary from "./ErpEffectSummary";
import { withErpSigma, type ErpSigma } from "./erpSensitivity";
import { comparedErpEvents, erpEventMarkers, hasErpPriceHistory, DEFAULT_ERP_SIGMAS } from "./erpComparisonDisplay";
import ErpSensitivitySummary from "./ErpSensitivitySummary";
import { usErpBands, usErpEvents } from "./usErpBands";
import {
  buildErpChartRuleSpecs,
  evaluateErpChartScreener,
  type EpisodeOutcomeSummary,
  type ErpChartRuleMeta,
  type HorizonForwardStats,
  type RuleIntent,
  type ScreenedEpisode,
} from "../market-style/breadthRegimeScreener";
import type { BreadthReadingResponse } from "../market-style/breadthReadingTypes";
import { normalizeWindow, panWindow, zoomWindow, type ChartWindow } from "../focus-momentum/chart-navigation";
import {
  buildErpRegimeEpisodes,
  buildErpRegimeMarkAreas,
  denseTimePoints,
  extractErpRegimeSpans,
  formatAxisPointerDate,
} from "./erpRegimeIntervals";
import "./erpCrossChart.css";

type PriceKey = "hs300" | "sse" | "sp500";
const names: Record<PriceKey, string> = { hs300: "沪深300", sse: "上证指数", sp500: "标普500" };
const windows = [
  { label: "1年", years: 1 },
  { label: "3年", years: 3 },
  { label: "5年", years: 5 },
  { label: "10年", years: 10 },
  { label: "20年", years: 20 },
  { label: "全部", years: null },
] as const;
const colors = { upper: "#327c72", lower: "#986737", middle: "#8a9aa9" };
const exists = (v: number | null | undefined): v is number => typeof v === "number" && Number.isFinite(v);
const fmt = (value: number | null | undefined, digits = 2) => exists(value) ? value.toFixed(digits) : "—";
const fmtPct = (value: number | null | undefined, digits = 1) => exists(value) ? `${value.toFixed(digits)}%` : "—";
const fmtSignedPct = (value: number | null | undefined, digits = 2, suffix = "%") =>
  exists(value) ? `${value >= 0 ? "+" : ""}${value.toFixed(digits)}${suffix}` : "—";

const shiftMonths = (date: string, months: number) => {
  const day = new Date(`${date}T00:00:00Z`), originalDay = day.getUTCDate();
  day.setUTCDate(1); day.setUTCMonth(day.getUTCMonth() + months);
  const monthEnd = new Date(Date.UTC(day.getUTCFullYear(), day.getUTCMonth() + 1, 0)).getUTCDate();
  day.setUTCDate(Math.min(originalDay, monthEnd)); return day.toISOString().slice(0, 10);
};

function timeAxisRecentWindow(minDate: string | undefined, maxDate: string | undefined, months: number): ChartWindow {
  if (!minDate || !maxDate) return { start: 0, end: 100 };
  const minMs = Date.parse(`${minDate}T00:00:00Z`);
  const maxMs = Date.parse(`${maxDate}T00:00:00Z`);
  if (!Number.isFinite(minMs) || !Number.isFinite(maxMs) || maxMs <= minMs) return { start: 0, end: 100 };
  const cutMs = Date.parse(`${shiftMonths(maxDate, -months)}T00:00:00Z`);
  if (!Number.isFinite(cutMs) || cutMs <= minMs) return { start: 0, end: 100 };
  return normalizeWindow({ start: ((cutMs - minMs) / (maxMs - minMs)) * 100, end: 100 });
}

function timeAxisVisibleRange(minDate: string | undefined, maxDate: string | undefined, win: ChartWindow): { start: string | null; end: string | null } {
  if (!minDate || !maxDate) return { start: null, end: null };
  const minMs = Date.parse(`${minDate}T00:00:00Z`);
  const maxMs = Date.parse(`${maxDate}T00:00:00Z`);
  if (!Number.isFinite(minMs) || !Number.isFinite(maxMs) || maxMs <= minMs) return { start: minDate, end: maxDate };
  const cur = normalizeWindow(win);
  const sMs = minMs + (maxMs - minMs) * (cur.start / 100);
  const eMs = minMs + (maxMs - minMs) * (cur.end / 100);
  return { start: new Date(sMs).toISOString().slice(0, 10), end: new Date(eMs).toISOString().slice(0, 10) };
}

function jumpTimeWindowToLatest(win: ChartWindow): ChartWindow {
  const cur = normalizeWindow(win);
  const width = cur.end - cur.start;
  if (width >= 99.9) return { start: 0, end: 100 };
  const span = Math.max(0.5, width);
  return { start: Math.max(0, 100 - span), end: 100 };
}

export default function ErpCrossChart({ market = "cn" }: { market?: "cn" | "us" }) {
  const isUs = market === "us";
  const marketKey = isUs ? "us" : "cn";
  const source = useProjectionSource(isUs ? "erp-us" : "erp-cn");
  const [priceChoice, setPriceKey] = useState<PriceKey>("hs300");
  const priceKey = isUs ? "sp500" : priceChoice === "sp500" ? "hs300" : priceChoice;
  const [years, setYears] = useState<number | null>(isUs ? 5 : null);
  const [overviewYears, setOverviewYears] = useState<number | null>(isUs ? 5 : null);
  const [showCrossingDots, setShowCrossingDots] = useState(false);
  const [activeRules, setActiveRules] = useState<ReadonlySet<string>>(() => new Set());
  const [showBaselineRules, setShowBaselineRules] = useState(false);
  const [selectedScreenEpId, setSelectedScreenEpId] = useState("");
  const [cursorDate, setCursorDate] = useState<string | null>(null);
  const [zoomRange, setZoomRange] = useState<{ start?: number; end?: number; startValue?: string; endValue?: string; seq: number } | null>(null);
  const [zoomState, setZoomState] = useState<ChartWindow>({ start: 0, end: 100 });

  const bands = useMemo(() => isUs ? usErpBands(source.points) : source.bands ?? [], [isUs, source.points, source.bands]);
  const [selectedId, setSelectedId] = useState("");
  const [showHistory, setShowHistory] = useState(false);
  const [researchTrend, setResearchTrend] = useState<"score" | "band">("score");
  const [sigmas, setSigmas] = useState<readonly ErpSigma[]>(DEFAULT_ERP_SIGMAS);

  const currentRates = useQuery({ queryKey: ["fundamentalsRates"], queryFn: () => fundamentalsApi.rates(), enabled: isUs, staleTime: 30 * 60_000, retry: false });
  const treasury = currentRates.data?.treasury;
  const y5 = treasury?.us?.us_5y;
  const y10 = treasury?.us?.us_10y;
  const curve = exists(y5) && exists(y10) ? y10 - y5 : null;

  const otherPrice = useQuery({ queryKey: ["fundOverlay", 47], queryFn: () => fundamentalsApi.overlayHistory(47), staleTime: 5 * 60_000, retry: false });
  const price = otherPrice.data?.series[priceKey];
  const position = useMemo(() => !isUs && !source.error ? erpPositionObservation(source.points) : null, [isUs, source.error, source.points]);
  const hs300 = otherPrice.data?.series.hs300;
  const trend = useMemo(() => position && hs300 && !otherPrice.isError
    ? erpTrendObservation(hs300.dates.map((date, i) => ({ date, value: hs300.values[i] ?? null })), position.date) : null,
  [position, hs300, otherPrice.isError]);
  const researchState = trend ? researchTrend === "score" ? trend.scoreState : trend.bandState : null;
  const researchMapping = position && researchState ? erpResearchMapping(position.z, researchState) : null;

  const aligned = useMemo(() => alignProjection(price ?? { dates: [], values: [] }, source.points, isUs ? "daily" : "weekly", years), [price, source.points, years, isUs]);
  const dailyPrice = useMemo(() => alignProjection(price ?? { dates: [], values: [] }, source.points, "daily", years), [price, source.points, years]);
  const comparisons = useMemo(() => sigmas.map(sigma => {
    const rails = withErpSigma(bands, sigma);
    const byDate = new Map(rails.map(row => [row.date, row]));
    return { sigma, byDate, visible: aligned.dates.map(date => byDate.get(date)) };
  }), [bands, sigmas, aligned.dates]);

  const events = useMemo(() => {
    if (!isUs) return comparedErpEvents(bands, sigmas);
    const priceDates = new Set(price?.dates.filter((_, i) => exists(price.values[i])));
    return usErpEvents(bands, sigmas).filter(event => priceDates.has(event.date));
  }, [bands, sigmas, isUs, price]);

  const regimeSpans = useMemo(() => extractErpRegimeSpans(bands, sigmas), [bands, sigmas]);
  const episodes = useMemo(() => buildErpRegimeEpisodes(bands, sigmas, !isUs), [bands, sigmas, isUs]);

  const breadthId = isUs ? "SP500" : "CN_ALL_A";
  const breadthQuery = useQuery({
    queryKey: ["overlayBreadthReading", breadthId, 12600],
    queryFn: async ({ signal }): Promise<BreadthReadingResponse> => {
      const response = await fetch(
        `/api/market-context/breadth-history?market_id=${breadthId}&lookback_days=12600&include_observation=true`,
        { signal },
      );
      if (!response.ok) throw new Error(`宽度历史读取失败 (${response.status})`);
      return response.json();
    },
    staleTime: 5 * 60_000,
    retry: false,
  });
  const ratesHistoryQuery = useQuery({
    queryKey: ["fundamentalsRatesHistory", 18250],
    queryFn: () => fundamentalsApi.ratesHistory(18250),
    staleTime: 5 * 60_000,
    retry: false,
  });
  const usMacroQuery = useQuery({
    queryKey: ["fundamentalsUsMacro"],
    queryFn: () => fundamentalsApi.usMacro(),
    enabled: isUs,
    staleTime: 30 * 60_000,
    retry: false,
  });

  const auxSeries = useMemo(() => {
    const mapSeries = (s?: { dates: string[]; values: (number | null)[] }) =>
      s && s.dates.length === s.values.length
        ? s.dates.map((date, idx) => ({
            date,
            value: exists(s.values[idx]) ? s.values[idx] : null,
          }))
        : [];
    return {
      marginRatio: mapSeries(ratesHistoryQuery.data?.series.margin_rzyezb),
      vix: mapSeries(ratesHistoryQuery.data?.series.vix),
      vixTerm: mapSeries(ratesHistoryQuery.data?.series.vix_term),
      hyOas: mapSeries(usMacroQuery.data?.series.hy_oas),
      fullPrice: mapSeries(price),
    };
  }, [ratesHistoryQuery.data, usMacroQuery.data, price]);

  const ruleSpecs = useMemo(() => buildErpChartRuleSpecs(marketKey), [marketKey]);
  const coreBullRules = useMemo(() => ruleSpecs.filter((r) => r.tier === "core" && r.intent === "bull"), [ruleSpecs]);
  const coreRiskRules = useMemo(() => ruleSpecs.filter((r) => r.tier === "core" && r.intent === "risk"), [ruleSpecs]);
  const baselineRules = useMemo(() => ruleSpecs.filter((r) => r.tier === "baseline"), [ruleSpecs]);
  const activeRuleIds = useMemo(() => ruleSpecs.filter((r) => activeRules.has(r.id)).map((r) => r.id), [ruleSpecs, activeRules]);
  const baselineActiveCount = useMemo(() => baselineRules.filter((r) => activeRules.has(r.id)).length, [baselineRules, activeRules]);
  const screeningActive = activeRuleIds.length > 0;

  const erpScreener = useMemo(() => {
    const hist = breadthQuery.data?.history ?? [];
    const obsMap = new Map(breadthQuery.data?.observation?.history.map(row => [row.date, row]) ?? []);
    return evaluateErpChartScreener({
      market: marketKey,
      priceDates: dailyPrice.dates,
      prices: dailyPrice.price,
      breadthPoints: hist,
      readings: obsMap,
      erpBands: bands,
      auxSeries,
      activeIds: activeRules,
    });
  }, [marketKey, dailyPrice, breadthQuery.data, bands, auxSeries, activeRules]);

  useEffect(() => {
    setCursorDate(null);
    setSelectedScreenEpId("");
    setZoomRange(null);
    setZoomState({ start: 0, end: 100 });
  }, [marketKey, priceKey, years]);

  const selected = episodes.find(ep => ep.id === selectedId);
  const selectedRow = useMemo(() => selected ? bands.find(row => row.date === selected.peakDate) : undefined, [bands, selected]);
  const minVisibleAxisDate = dailyPrice.dates[0] ?? aligned.dates[0];
  const maxVisibleAxisDate = dailyPrice.dates[dailyPrice.dates.length - 1] ?? aligned.dates[aligned.dates.length - 1];
  const visibleSpan = useMemo(
    () => timeAxisVisibleRange(minVisibleAxisDate, maxVisibleAxisDate, zoomState),
    [minVisibleAxisDate, maxVisibleAxisDate, zoomState],
  );
  const isZoomed = zoomState.end - zoomState.start < 99.9;
  const atLatestEdge = zoomState.end >= 99.9;
  const hasMultiYearSpan = Boolean(
    minVisibleAxisDate && maxVisibleAxisDate
    && Date.parse(`${maxVisibleAxisDate}T00:00:00Z`) - Date.parse(`${minVisibleAxisDate}T00:00:00Z`) > 380 * 86_400_000,
  );
  const applyPercentZoom = (next: ChartWindow) => {
    const bounded = normalizeWindow(next);
    const scope = `${priceKey}:${years ?? "all"}`;
    chartZoom.current = { scope, start: bounded.start, end: bounded.end };
    zoomWindowRef.current = bounded;
    setZoomState(bounded);
    setZoomRange((prev) => ({ start: bounded.start, end: bounded.end, seq: (prev?.seq ?? 0) + 1 }));
  };
  const recentPresetActive = (months: number) => {
    const target = timeAxisRecentWindow(minVisibleAxisDate, maxVisibleAxisDate, months);
    return Math.abs(zoomState.start - target.start) < 0.25 && Math.abs(zoomState.end - target.end) < 0.25;
  };
  const jumpToLatest = () => {
    setCursorDate(null);
    setSelectedScreenEpId("");
    if (!atLatestEdge) applyPercentZoom(jumpTimeWindowToLatest(zoomState));
  };

  const focusEpisode = (id: string) => {
    chartZoom.current = null;
    setZoomRange(null);
    if (!selected) setOverviewYears(years);
    setSelectedId(id);
    setYears(null);
  };
  const clearFocus = () => {
    chartZoom.current = null;
    setZoomRange(null);
    setZoomState({ start: 0, end: 100 });
    setSelectedId("");
    setSelectedScreenEpId("");
    setYears(isUs ? overviewYears : null);
  };
  const toggleRule = (id: string) => {
    setSelectedScreenEpId("");
    setZoomRange(null);
    if (selectedId) setSelectedId("");
    setActiveRules((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };
  const focusScreenedEpisode = (epId: string) => {
    setSelectedScreenEpId(epId);
    const ep: ScreenedEpisode | undefined = erpScreener.episodes.find((item) => item.id === epId);
    if (!ep || !dailyPrice.dates.length) return;
    const sIdx = Math.max(0, ep.startIndex - 40);
    const eIdx = Math.min(dailyPrice.dates.length - 1, ep.endIndex + 80);
    const startVal = dailyPrice.dates[sIdx];
    const endVal = dailyPrice.dates[eIdx];
    setCursorDate(ep.startDate);
    if (minVisibleAxisDate && maxVisibleAxisDate) {
      const minMs = Date.parse(`${minVisibleAxisDate}T00:00:00Z`);
      const maxMs = Date.parse(`${maxVisibleAxisDate}T00:00:00Z`);
      const sMs = Date.parse(`${startVal}T00:00:00Z`);
      const eMs = Date.parse(`${endVal}T00:00:00Z`);
      if (maxMs > minMs) {
        const nextWin = normalizeWindow({
          start: ((sMs - minMs) / (maxMs - minMs)) * 100,
          end: ((eMs - minMs) / (maxMs - minMs)) * 100,
        });
        zoomWindowRef.current = nextWin;
        setZoomState(nextWin);
        chartZoom.current = { scope: `${priceKey}:${years ?? "all"}`, start: nextWin.start, end: nextWin.end };
      }
    }
    setZoomRange((prev) => ({
      startValue: startVal,
      endValue: endVal,
      seq: (prev?.seq ?? 0) + 1,
    }));
  };
  const resetScreenZoom = () => {
    setSelectedScreenEpId("");
    setCursorDate(null);
    applyPercentZoom({ start: 0, end: 100 });
  };

  const latest = bands[bands.length - 1];
  const latestDailyDate = dailyPrice.dates[dailyPrice.dates.length - 1];
  const activeInspectDate = cursorDate ?? (selected ? selected.peakDate : latestDailyDate ?? latest?.date ?? null);
  const ctxAtInspect = activeInspectDate ? erpScreener.contextByDate.get(activeInspectDate) : undefined;
  const bandByDate = useMemo(() => new Map(bands.map((r) => [r.date, r])), [bands]);
  const readoutBand = useMemo(() => {
    if (selectedRow && !cursorDate) return selectedRow;
    if (activeInspectDate) {
      const exact = bandByDate.get(activeInspectDate);
      if (exact) return exact;
      for (let i = bands.length - 1; i >= 0; i--) {
        if (bands[i].date <= activeInspectDate && exists(bands[i].value)) return bands[i];
      }
    }
    return latest;
  }, [selectedRow, cursorDate, activeInspectDate, bandByDate, bands, latest]);

  const chartNode = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<echarts.ECharts | null>(null);
  const chartZoom = useRef<{ scope: string; start: number; end: number } | null>(null);
  const zoomWindowRef = useRef<ChartWindow>({ start: 0, end: 100 });
  const isPointerDownRef = useRef(false);
  const enough = hasErpPriceHistory(aligned.values, aligned.price);

  const toggleSigma = (sigma: ErpSigma) => {
    if (sigmas.includes(sigma) && sigmas.length === 1) return;
    setSigmas(sigmas.includes(sigma) ? sigmas.filter(k => k !== sigma) : [...sigmas, sigma].sort());
    if (selected) clearFocus();
  };

  useEffect(() => {
    if (!chartNode.current || !enough) return;
    const node = chartNode.current;
    let chart: ReturnType<typeof echarts.init> | undefined;
    let hoverRaf = 0;
    let pendingDate: string | null = null;
    let lastHoveredDate: string | null = null;
    let zoomRaf = 0;
    let pendingZoom: ChartWindow | null = null;
    const zoomScope = `${priceKey}:${years ?? "all"}`;
    const flushHover = () => {
      hoverRaf = 0;
      if (pendingDate && !isPointerDownRef.current) {
        const nextDate = pendingDate;
        pendingDate = null;
        setCursorDate(nextDate);
      }
    };
    const flushZoom = () => {
      zoomRaf = 0;
      if (pendingZoom) {
        const next = pendingZoom;
        pendingZoom = null;
        setZoomState((prev) => (Math.abs(prev.start - next.start) < 0.05 && Math.abs(prev.end - next.end) < 0.05 ? prev : next));
      }
    };
    const onPointerDown = () => { isPointerDownRef.current = true; };
    const onPointerUp = () => { isPointerDownRef.current = false; };
    const onPointerLeave = () => { isPointerDownRef.current = false; lastHoveredDate = null; };
    const onWheel = (event: WheelEvent) => {
      const horizontal = Math.abs(event.deltaX) > Math.abs(event.deltaY)
        ? event.deltaX
        : event.shiftKey ? event.deltaY : 0;
      if (!horizontal || !chart) return;
      const current = zoomWindowRef.current;
      if (current.end - current.start >= 99.9) return;
      event.preventDefault();
      event.stopPropagation();
      const fraction = horizontal / Math.max(180, node.clientWidth || 600);
      const next = panWindow(current, fraction);
      if (Math.abs(next.start - current.start) < 1e-4 && Math.abs(next.end - current.end) < 1e-4) return;
      zoomWindowRef.current = next;
      if (!selected) chartZoom.current = { scope: zoomScope, start: next.start, end: next.end };
      chart.dispatchAction({ type: "dataZoom", start: next.start, end: next.end });
      pendingZoom = next;
      if (!zoomRaf) zoomRaf = requestAnimationFrame(flushZoom);
    };
    node.addEventListener("pointerdown", onPointerDown);
    node.addEventListener("pointerleave", onPointerLeave);
    node.addEventListener("wheel", onWheel, { passive: false });
    window.addEventListener("pointerup", onPointerUp);
    window.addEventListener("pointercancel", onPointerUp);

    const renderWhenVisible = () => {
      if (!node.clientWidth || !node.clientHeight) return;
      if (chart) { chart.resize(); return; }
      chart = echarts.init(node, undefined, { renderer: "canvas" });
      chartInstanceRef.current = chart;
      const dated = new Map(aligned.dates.map((date, index) => [date, index]));
      const dailyByDate = new Map(dailyPrice.dates.map((date, index) => [date, dailyPrice.price[index]]));
      const minVisibleDate = dailyPrice.dates[0] ?? aligned.dates[0];
      const maxVisibleDate = dailyPrice.dates[dailyPrice.dates.length - 1] ?? aligned.dates[aligned.dates.length - 1];
      const regimeAreas = screeningActive
        ? erpScreener.markAreas
        : buildErpRegimeMarkAreas(regimeSpans, minVisibleDate, maxVisibleDate);
      const priorIdx = selected ? aligned.dates.findIndex(date => date >= shiftMonths(selected.startDate, -3)) : 0;
      const prior = priorIdx === -1 ? 0 : priorIdx;
      const after = selected ? aligned.dates.findIndex(date => date > shiftMonths(selected.endDate, 6)) : -1;
      const endIndex = after === -1 ? aligned.dates.length - 1 : Math.max(0, after - 1);
      const startValue = selected ? aligned.dates[Math.max(0, prior)] : minVisibleDate;
      const endValue = selected ? aligned.dates[endIndex] : maxVisibleDate;
      const restoredZoom = !selected && chartZoom.current?.scope === zoomScope ? chartZoom.current : null;
      const initialZoom = restoredZoom
        ? { start: restoredZoom.start, end: restoredZoom.end }
        : { startValue, endValue };
      const selectedLine = !selected ? undefined : {
        silent: true,
        symbol: "none",
        label: { show: false },
        lineStyle: { color: colors[selected.kind], opacity: 0.45, width: 1.5, type: "dashed" as const },
        data: selected.startDate === selected.endDate
          ? [{ xAxis: selected.startDate }]
          : [{ xAxis: selected.startDate }, { xAxis: selected.endDate }],
      };
      const showDateLabel = (value: number) => {
        const date = new Date(value).toISOString().slice(0, 10);
        return years === null || years >= 10 ? date.slice(0, 4) : date.slice(0, 7);
      };
      const axisLabel = { color: "#64748b", fontSize: 12 };
      const axisPointerLabel = { formatter: (params: { value?: unknown }) => formatAxisPointerDate(params?.value) };
      chart.setOption({
        animation: false, textStyle: { fontFamily: 'system-ui, -apple-system, "PingFang SC", sans-serif' },
        title: [
          { text: "股债利差（百分点） · 上轨相对便宜，下轨相对偏贵", left: 0, top: "59%", textStyle: { fontSize: 13, fontWeight: 600, color: "#173d68" } },
          { text: `${names[priceKey]}价格（点） · ${screeningActive ? "已高亮所选组合命中区间" : "与连续估值区间对照"}`, left: 0, top: 4, textStyle: { fontSize: 14, fontWeight: 600, color: "#243f63" } },
        ],
        grid: [{ left: 62, right: 86, top: 34, height: "43%" }, { left: 62, right: 86, top: "66%", height: "18%" }],
        axisPointer: { link: [{ xAxisIndex: [0, 1] }] },
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
          axisPointer: { type: "cross" },
          formatter: (raw: unknown) => {
            const series = Array.isArray(raw) ? raw : [raw];
            const first = series[0] as { axisValue?: unknown; value?: unknown };
            const eventDate = Array.isArray(first?.value) ? first.value[0] : undefined;
            const date = formatAxisPointerDate(first?.axisValue ?? eventDate);
            const index = dated.get(date);
            if (!date) return "—";
            const rails = comparisons.map(({ sigma, byDate }) => `${sigma}σ：下轨 ${fmt(byDate.get(date)?.lower, 3)} ／ 上轨 ${fmt(byDate.get(date)?.upper, 3)}`).join("<br/>");
            const erpVal = index === undefined ? erpScreener.contextByDate.get(date)?.erpValue ?? null : aligned.values[index];
            const regimeHit = comparisons[0]?.byDate.get(date);
            const z = regimeHit?.z ?? erpScreener.contextByDate.get(date)?.erpZ;
            const z1y = isUs ? erpScreener.contextByDate.get(date)?.erpZ1y : null;
            const regimeNote = exists(z)
              ? z >= 2 ? "所处区间：≥ +2σ 偏便宜"
                : z >= 1.5 ? "所处区间：+1.5σ~+2σ 偏便宜"
                : z <= -2 ? "所处区间：≤ −2σ 偏贵"
                : z <= -1.5 ? "所处区间：−1.5σ~−2σ 偏贵"
                : ""
              : "";
            const z1yNote = isUs && exists(z1y) ? `<br/>近1年适应Z：${z1y >= 0 ? "+" : ""}${z1y.toFixed(2)}σ` : "";
            return `<b>${date}</b><br/>${names[priceKey]}：${fmt(dailyByDate.get(date))}<br/>股债利差：${fmt(erpVal, 3)} 个百分点${z1yNote}<br/>${rails}${regimeNote ? `<br/>${regimeNote}` : ""}`;
          },
        },
        xAxis: [0, 1].map(index => ({ type: "time", gridIndex: index, boundaryGap: false,
          splitNumber: years === null || years >= 10 ? 7 : 5,
          axisPointer: { snap: true, label: axisPointerLabel },
          axisLabel: { ...axisLabel, show: index === 1, hideOverlap: true, showMinLabel: true, showMaxLabel: true, formatter: showDateLabel },
          axisLine: { lineStyle: { color: "#cbd5e1" } } })),
        yAxis: [0, 1].map(index => ({ type: "value", gridIndex: index, scale: true, splitNumber: index === 1 ? 3 : 4,
          min: (value: { min: number; max: number }) => Number.isFinite(value.min) && Number.isFinite(value.max)
            ? (index === 0
                ? Math.floor(value.min - Math.max(value.max - value.min, Math.abs(value.min) * .005, 1) * .08)
                : value.min - Math.max(value.max - value.min, Math.abs(value.min) * .005, 1) * .08)
            : undefined,
          max: (value: { min: number; max: number }) => Number.isFinite(value.min) && Number.isFinite(value.max)
            ? (index === 0
                ? Math.ceil(value.max + Math.max(value.max - value.min, Math.abs(value.max) * .005, 1) * .08)
                : value.max + Math.max(value.max - value.min, Math.abs(value.max) * .005, 1) * .08)
            : undefined,
          axisLabel: { ...axisLabel, formatter: (value: number) => index === 1 ? value.toFixed(1) : Math.round(value).toLocaleString("zh-CN") }, splitLine: { lineStyle: { color: "#e5eaf0" } } })),
        dataZoom: [
          {
            type: "inside",
            xAxisIndex: [0, 1],
            filterMode: "filter",
            zoomOnMouseWheel: true,
            moveOnMouseMove: true,
            moveOnMouseWheel: "shift",
            preventDefaultMouseMove: true,
            throttle: 16,
            ...initialZoom,
          },
          {
            type: "slider",
            xAxisIndex: [0, 1],
            filterMode: "filter",
            left: 62,
            right: 86,
            bottom: 6,
            height: 26,
            brushSelect: false,
            realtime: true,
            throttle: 16,
            moveHandleSize: 10,
            handleSize: "115%",
            showDetail: true,
            labelFormatter: (val: number) => formatAxisPointerDate(val),
            borderColor: "#cbd5e1",
            backgroundColor: "#f8fafc",
            fillerColor: "rgba(36, 63, 99, 0.14)",
            handleStyle: { color: "#ffffff", borderColor: "#35678e", borderWidth: 1.5 },
            moveHandleStyle: { color: "#64748b" },
            emphasis: { handleLabel: { show: true }, moveHandleStyle: { color: "#173d68" } },
            textStyle: { color: "#475569", fontSize: 11 },
            ...initialZoom,
          },
        ],
        series: [
          { name: "股债利差", type: "line", xAxisIndex: 1, yAxisIndex: 1, data: denseTimePoints(aligned.dates, aligned.values), showSymbol: false, connectNulls: false, lineStyle: { color: "#173d68", width: 2.5 }, markLine: selectedLine, markArea: { silent: true, itemStyle: { borderWidth: 0 }, data: regimeAreas } },
          { name: isUs ? "此前3年均值" : "3年均值", type: "line", xAxisIndex: 1, yAxisIndex: 1, data: denseTimePoints(aligned.dates, comparisons[0]?.visible.map(row => row?.middle ?? null) ?? []), showSymbol: false, connectNulls: false, lineStyle: { color: "#536a82", width: 1.6, type: "dashed" } },
          ...comparisons.flatMap(({ sigma, visible }) => (["upper", "lower"] as const).map(key => ({
            name: `${key === "upper" ? "上轨" : "下轨"} ${sigma}σ`, type: "line", xAxisIndex: 1, yAxisIndex: 1, data: denseTimePoints(aligned.dates, visible.map(row => row?.[key] ?? null)), connectNulls: false, showSymbol: false,
            endLabel: { show: true, formatter: `${key === "upper" ? "+" : "−"}${sigma}σ`, color: colors[key], fontSize: 12, distance: 7 }, labelLayout: { moveOverlap: "shiftY" },
            lineStyle: { color: colors[key], width: sigma === 2 ? 2.6 : sigma === 1.5 ? 2.2 : 1.8, opacity: 1, type: sigma === 2 ? "solid" : "dashed" },
          }))),
          { name: names[priceKey], type: "line", data: denseTimePoints(dailyPrice.dates, dailyPrice.price), xAxisIndex: 0, yAxisIndex: 0, connectNulls: false, showSymbol: false, lineStyle: { color: "#243f63", width: 2.8 }, markLine: selectedLine, markArea: { silent: true, itemStyle: { borderWidth: 0 }, data: regimeAreas } },
          ...(showCrossingDots ? comparisons.flatMap(({ sigma }) => (["upper", "lower"] as const).flatMap(kind => [0, 1].map(panel => ({
            id: `erp-marker-${panel}-${sigma}-${kind}`, name: `${sigma}σ ${kind === "upper" ? "上穿上轨" : "下穿下轨"}`, type: "scatter", xAxisIndex: panel, yAxisIndex: panel,
            data: erpEventMarkers(events.filter(event => event.sigma === sigma && event.kind === kind), panel === 0 ? dailyPrice.dates : aligned.dates, panel === 0 ? dailyPrice.price : aligned.values),
            symbol: sigma === 2 ? "diamond" : sigma === 1.5 ? "circle" : "rect", symbolSize: sigma === 2 ? 10 : sigma === 1.5 ? 7 : 5,
            itemStyle: { color: sigma === 2 ? colors[kind] : "#fff", borderColor: colors[kind], borderWidth: 1.5, opacity: 0.9 }, z: sigma === 2 ? 8 : 9, emphasis: { scale: 1.5 },
          })))) : []),
        ],
      });
      const readCurrentZoom = (): ChartWindow => {
        const dz = (chart?.getOption().dataZoom as { start?: number; end?: number }[] | undefined)?.[0];
        return normalizeWindow({ start: Number(dz?.start ?? 0), end: Number(dz?.end ?? 100) });
      };
      const initWin = readCurrentZoom();
      zoomWindowRef.current = initWin;
      setZoomState((prev) => (Math.abs(prev.start - initWin.start) < 0.05 && Math.abs(prev.end - initWin.end) < 0.05 ? prev : initWin));

      chart.on("updateAxisPointer", (event: unknown) => {
        if (isPointerDownRef.current) return;
        const val = (event as { axesInfo?: { value?: unknown }[] }).axesInfo?.[0]?.value;
        const d = formatAxisPointerDate(val);
        if (!d || !dailyByDate.has(d) || d === lastHoveredDate) return;
        lastHoveredDate = d;
        pendingDate = d;
        if (!hoverRaf) hoverRaf = requestAnimationFrame(flushHover);
      });
      chart.on("click", (params: { seriesType?: string; data?: unknown }) => {
        const data = params.data as { coord?: [string, number]; value?: [string, number] } | undefined;
        const clickDate = Array.isArray(data?.value) ? data.value[0] : Array.isArray(data?.coord) ? data.coord[0] : undefined;
        if (params.seriesType === "scatter" && typeof clickDate === "string") {
          const hit = episodes.find(ep => ep.startDate <= clickDate && clickDate <= ep.endDate);
          if (hit) focusEpisode(hit.id);
        }
      });
      chart.on("datazoom", () => {
        if (!chart) return;
        const next = readCurrentZoom();
        zoomWindowRef.current = next;
        if (!selected) {
          chartZoom.current = { scope: zoomScope, start: next.start, end: next.end };
        }
        pendingZoom = next;
        if (!zoomRaf) zoomRaf = requestAnimationFrame(flushZoom);
      });
    };
    const resize = new ResizeObserver(renderWhenVisible); resize.observe(node); renderWhenVisible();
    return () => {
      if (hoverRaf) cancelAnimationFrame(hoverRaf);
      if (zoomRaf) cancelAnimationFrame(zoomRaf);
      node.removeEventListener("pointerdown", onPointerDown);
      node.removeEventListener("pointerleave", onPointerLeave);
      node.removeEventListener("wheel", onWheel);
      window.removeEventListener("pointerup", onPointerUp);
      window.removeEventListener("pointercancel", onPointerUp);
      resize.disconnect();
      chart?.dispose();
      chartInstanceRef.current = null;
    };
  }, [aligned, dailyPrice, comparisons, events, regimeSpans, erpScreener.markAreas, screeningActive, episodes, selected, priceKey, years, enough, isUs, showCrossingDots]);

  useEffect(() => {
    if (!zoomRange || !chartInstanceRef.current) return;
    if (exists(zoomRange.start) && exists(zoomRange.end)) {
      const bounded = normalizeWindow({ start: zoomRange.start, end: zoomRange.end });
      zoomWindowRef.current = bounded;
      chartInstanceRef.current.dispatchAction({
        type: "dataZoom",
        start: bounded.start,
        end: bounded.end,
      });
    } else if (zoomRange.startValue && zoomRange.endValue) {
      chartInstanceRef.current.dispatchAction({
        type: "dataZoom",
        startValue: zoomRange.startValue,
        endValue: zoomRange.endValue,
      });
    }
  }, [zoomRange]);

  const renderForwardCell = (label: string, stats: HorizonForwardStats, mode: RuleIntent) => {
    if (stats.sampleCount === 0) {
      return (
        <div className="erp-score-cell">
          <span className="erp-score-horizon">{label}</span>
          <span className="erp-score-empty">样本未满{stats.horizonBars}交易日（待完整走完）</span>
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
      <div className="erp-score-cell">
        <span className="erp-score-horizon">{label} <em>({stats.sampleCount}次)</em></span>
        {isRisk ? (
          <span title={`后续上涨占比 ${fmtPct(stats.winRate)}`}>下跌/走弱率 <b>{fmtPct(fallRate)}</b></span>
        ) : (
          <span>上涨率 <b>{fmtPct(stats.winRate)}</b></span>
        )}
        <span>{isRisk ? "后市均值" : "均值"} <b>{fmtSignedPct(stats.meanReturn)}</b></span>
        {exists(stats.edgeMean) && (
          <span className={`erp-score-edge erp-score-edge-${edgeTone}`}>
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
    <div key={key} className={`erp-quant-scorecard erp-scorecard-${mode}`} aria-label={`${title}历史触发后收益统计`}>
      <div className="erp-score-head">
        <span className={`erp-score-badge erp-score-badge-${mode}`}>{title} · {names[priceKey]}</span>
        <span>
          这段时间共出现 <b>{outcome.dedupEpisodeCount}</b> 次（{outcome.cooldownBars}日内重复算1次，共 {outcome.rawEpisodeCount} 段 · 按每次刚出现那天收盘价往后算）
        </span>
      </div>
      <div className="erp-score-grid">
        {renderForwardCell("后 20 交易日", outcome.d20, mode)}
        {renderForwardCell("后 60 交易日", outcome.d60, mode)}
      </div>
    </div>
  );

  const renderRulePill = (rule: ErpChartRuleMeta) => {
    const count = erpScreener.byRule[rule.id]?.episodeCount ?? 0;
    return (
      <button
        key={rule.id}
        type="button"
        aria-pressed={activeRules.has(rule.id)}
        title={`${rule.formula}｜${rule.basis}`}
        onClick={() => toggleRule(rule.id)}
      >
        <span className="erp-rule-dot" style={{ background: rule.color }} aria-hidden="true" />
        <span>{rule.short}</span>
        <em className="erp-pill-count">{count}段</em>
      </button>
    );
  };

  return <div className={`erp-cross${isUs ? " erp-cross-us" : ""}`}>
    <div className="erp-cross-toolbar" role="group" aria-label="股指、统计轨道与期间切换">
      <div className="erp-seg-group" role="group" aria-label="对照股指">
        {isUs ? (
          <button type="button" aria-pressed="true">标普500</button>
        ) : (
          <>
            <button type="button" aria-pressed={priceKey === "hs300"} onClick={() => setPriceKey("hs300")}>沪深300</button>
            <button type="button" aria-pressed={priceKey === "sse"} onClick={() => setPriceKey("sse")}>上证指数</button>
          </>
        )}
      </div>
      <div className="erp-seg-group" role="group" aria-label="同时显示轨道">
        <span className="erp-toolbar-label">轨道</span>
        {(isUs ? [1.5, 2] as const : [1, 1.5, 2] as const).map(sigma => (
          <button
            type="button"
            key={sigma}
            aria-pressed={sigmas.includes(sigma)}
            disabled={sigmas.length === 1 && sigmas.includes(sigma)}
            onClick={() => toggleSigma(sigma)}
          >
            {sigma === 2 ? "◆ 2σ 极端" : sigma === 1.5 ? "○ 1.5σ 观察" : "□ 1σ 敏感"}
          </button>
        ))}
        <label className="erp-cross-density">
          <input type="checkbox" checked={showCrossingDots} onChange={event => setShowCrossingDots(event.target.checked)} />
          穿轨点
        </label>
      </div>
      <div className="erp-seg-group erp-windows-right" role="group" aria-label="对照期间">
        {windows.map(window => (
          <button
            type="button"
            key={window.label}
            aria-pressed={years === window.years && !selected}
            onClick={() => { chartZoom.current = null; setZoomRange(null); setSelectedId(""); setYears(window.years); setOverviewYears(window.years); }}
          >
            {window.label}
          </button>
        ))}
      </div>
    </div>

    <div className="erp-spec-box" aria-label="股债利差读数与非对称准则">
      <div className="erp-spec-row">
        <strong>{activeInspectDate ?? readoutBand?.date ?? "—"} 读数：</strong>
        <span>
          股债利差 <b>{fmt(readoutBand?.value)}pp</b>
          {isUs
            ? exists(readoutBand?.z) || exists(ctxAtInspect?.erpZ1y)
              ? ` (3年 ${exists(readoutBand?.z) ? `${readoutBand.z >= 0 ? "+" : ""}${readoutBand.z.toFixed(2)}σ` : "—"} · 1年 ${exists(ctxAtInspect?.erpZ1y) ? `${ctxAtInspect.erpZ1y >= 0 ? "+" : ""}${ctxAtInspect.erpZ1y.toFixed(2)}σ` : "—"})`
              : ""
            : exists(readoutBand?.z) ? ` (${readoutBand.z >= 0 ? "+" : ""}${readoutBand.z.toFixed(2)}σ)` : ""}
        </span>
        {comparisons.map(({ sigma, byDate }) => {
          const row = readoutBand ? byDate.get(readoutBand.date) : undefined;
          return (
            <span key={sigma}>
              {sigma}σ轨 <b className="erp-cross-down">{fmt(row?.lower)}</b>~<b className="erp-cross-up">{fmt(row?.upper)}</b>
            </span>
          );
        })}
        {exists(ctxAtInspect?.b50) && <span>50日宽度 <b>{fmtPct(ctxAtInspect.b50)}</b></span>}
        {!isUs && exists(ctxAtInspect?.marginRatio) && (
          <span>
            两融占比 <b>{ctxAtInspect.marginRatio.toFixed(2)}%</b>
            {exists(ctxAtInspect?.marginPercentile) ? ` (3年P${Math.round(ctxAtInspect.marginPercentile)})` : ""}
          </span>
        )}
        {isUs && exists(ctxAtInspect?.vix) && <span>VIX <b>{ctxAtInspect.vix.toFixed(1)}</b></span>}
        {isUs && exists(ctxAtInspect?.hyOas) && <span>HY OAS <b>{ctxAtInspect.hyOas.toFixed(2)}%</b></span>}
        {cursorDate && (
          <button type="button" className="erp-spec-reset" onClick={jumpToLatest}>
            回最新日
          </button>
        )}
      </div>
      <div className="erp-spec-row erp-spec-muted">
        <span>
          <b>滚动3年均值 ±σ</b>（{isUs ? "日频不含当期" : "周频"}）：
          <span className="erp-cross-up"> +1.5σ/+2σ 上轨代表买股比买债划算</span>
          {isUs ? "（美股买点改用近1年适应Z≥+1σ，避免加息换挡期失明）" : "（搭配大盘走稳买更稳）"} ｜{" "}
          <span className="erp-cross-down">−1.5σ/−2σ 下轨代表偏贵</span>
          {isUs ? "（高利率或牛市常长期偏贵，仅在过热后跌破50/60日线时预警退潮）" : "（牛市与高利率时常一直偏贵照样涨，别光看它就卖）"}
        </span>
      </div>
    </div>

    <div className="erp-screener-panel" aria-label="股债利差历史验证信号">
      <div className="erp-screener-head">
        <strong>历史验证信号</strong>
        <span>只留长期真管用的 {coreBullRules.length + coreRiskRules.length} 个（买点 {coreBullRules.length} · 卖点 {coreRiskRules.length}）</span>
        <div className="erp-screener-actions">
          <button
            type="button"
            className="erp-screener-toggle"
            aria-expanded={showBaselineRules}
            onClick={() => setShowBaselineRules((prev) => !prev)}
          >
            {showBaselineRules ? "收起单看贵贱 ▴" : baselineActiveCount > 0 ? `只看贵贱极值 (已选${baselineActiveCount}) ▾` : `只看贵贱极值 (${baselineRules.length}) ▾`}
          </button>
          {screeningActive && (
            <button type="button" className="erp-screener-clear" onClick={() => { setActiveRules(new Set()); resetScreenZoom(); }}>
              清空
            </button>
          )}
        </div>
      </div>

      {erpScreener.latestActiveRuleIds.length > 0 && (
        <div className="erp-latest-hit" aria-label="最新交易日已触发估值信号">
          <span className="erp-latest-hit-label">最新日 ({latestDailyDate?.slice(5) ?? "—"}) 命中</span>
          {erpScreener.latestActiveRuleIds.map((ruleId) => {
            const rule = ruleSpecs.find((item) => item.id === ruleId);
            if (!rule) return null;
            return (
              <button
                key={rule.id}
                type="button"
                aria-pressed={activeRules.has(rule.id)}
                onClick={() => toggleRule(rule.id)}
              >
                <span className="erp-rule-dot" style={{ background: rule.color }} aria-hidden="true" />
                {rule.short}
              </button>
            );
          })}
        </div>
      )}

      <div className="erp-screener-core-grid">
        <div className="erp-screener-cluster" role="group" aria-label="估值联动买点">
          <span className="erp-cluster-tag erp-cluster-bull">买点</span>
          <div className="erp-screener-pills">{coreBullRules.map(renderRulePill)}</div>
        </div>
        <div className="erp-screener-cluster" role="group" aria-label="估值联动卖点与风控">
          <span className="erp-cluster-tag erp-cluster-risk">卖点</span>
          <div className="erp-screener-pills">{coreRiskRules.map(renderRulePill)}</div>
        </div>
      </div>

      {showBaselineRules && (
        <div className="erp-screener-baseline" role="group" aria-label="单纯轨道极值标尺">
          <span className="erp-baseline-label">单纯轨道极值</span>
          <div className="erp-screener-pills">{baselineRules.map(renderRulePill)}</div>
        </div>
      )}

      {screeningActive && (
        <div className="erp-screener-active">
          <div className="erp-screener-notes">
            {activeRuleIds.map((ruleId) => {
              const rule = ruleSpecs.find((item) => item.id === ruleId);
              if (!rule) return null;
              return (
                <p key={rule.id}>
                  <span className="erp-rule-dot" style={{ background: rule.color }} aria-hidden="true" />
                  <b>{rule.short}</b>：{rule.formula} — <span>{rule.basis}</span>
                </p>
              );
            })}
          </div>
          {(() => {
            const hasBull = erpScreener.activeIntents.includes("bull");
            const hasRisk = erpScreener.activeIntents.includes("risk");
            const hasNeutral = erpScreener.activeIntents.includes("neutral");
            if (hasBull && hasRisk) {
              return (
                <div className="erp-scorecard-split">
                  <p className="erp-scorecard-mix-note">已同时勾选买点与卖点，已按方向拆开统计以免正负收益互相抵消：</p>
                  {renderScorecardBlock("买点组合战绩", erpScreener.outcomeByIntent.bull, "bull", "bull")}
                  {renderScorecardBlock("卖点风控校验", erpScreener.outcomeByIntent.risk, "risk", "risk")}
                </div>
              );
            }
            if (hasRisk) {
              return renderScorecardBlock("卖点风控校验", erpScreener.outcomeByIntent.risk, "risk", "risk");
            }
            if (hasBull) {
              return renderScorecardBlock("买点历史战绩", erpScreener.outcomeByIntent.bull, "bull", "bull");
            }
            if (hasNeutral) {
              return renderScorecardBlock("水位观察统计", erpScreener.outcomeByIntent.neutral, "neutral", "neutral");
            }
            return renderScorecardBlock("历史触发战绩", erpScreener.outcome, "bull", "all");
          })()}
          <div className="erp-screener-jump">
            <label>
              命中区间 ({erpScreener.episodes.length}段)
              <select
                aria-label="查看组合命中区间"
                value={selectedScreenEpId}
                onChange={(event) => {
                  const id = event.target.value;
                  if (!id) { resetScreenZoom(); return; }
                  focusScreenedEpisode(id);
                }}
              >
                <option value="">选择区间并定位缩放…</option>
                {[...erpScreener.episodes].reverse().map((ep) => (
                  <option key={ep.id} value={ep.id}>
                    {ep.startDate}{ep.endDate !== ep.startDate ? `—${ep.endDate}` : ""} · {ep.days}日 · {ep.ruleLabel}
                  </option>
                ))}
              </select>
            </label>
            <button type="button" onClick={resetScreenZoom}>重置缩放</button>
          </div>
        </div>
      )}
    </div>

    {!screeningActive && (
      <div className="erp-inline-bar">
        <span className="erp-cross-legend">
          <i className="erp-cross-swatch erp-cross-erp" />股债利差
          <i className="erp-cross-swatch erp-cross-price" />{names[priceKey]}
          <i className="erp-cross-zone erp-cross-zone-up" />偏便宜区间 (+1.5σ/+2σ)
          <i className="erp-cross-zone erp-cross-zone-down" />偏贵区间 (−1.5σ/−2σ)
        </span>
        <div className="erp-episode-picker">
          <label>极值区间回看
            <select aria-label="查看极值区间" value={selectedId} onChange={event => {
              const id = event.target.value;
              if (!id) { clearFocus(); return; }
              focusEpisode(id);
            }}>
              <option value="">{isUs ? "当前窗口 · 最新读数" : "完整历史 · 最新读数"}</option>
              {[...episodes].reverse().map(ep => (
                <option key={ep.id} value={ep.id}>
                  {ep.startDate}{ep.endDate !== ep.startDate ? `—${ep.endDate}` : ""} · {ep.pointsCount}{isUs ? "日" : "周"} · 极值{ep.peakSigma}σ {ep.kind === "upper" ? "偏便宜" : "偏贵"}
                </option>
              ))}
            </select>
          </label>
          {selected && <button type="button" onClick={clearFocus}>返回概览</button>}
        </div>
      </div>
    )}

    {enough && !source.isPending && !otherPrice.isPending && !source.error && !otherPrice.isError && (
      <div className="erp-zoom-nav" role="toolbar" aria-label="股债利差图表缩放与区间导航">
        <div className="erp-zoom-group" role="group" aria-label="快捷近端视图">
          <button type="button" aria-pressed={recentPresetActive(3)} onClick={() => { setSelectedScreenEpId(""); setCursorDate(null); applyPercentZoom(timeAxisRecentWindow(minVisibleAxisDate, maxVisibleAxisDate, 3)); }}>近3月</button>
          <button type="button" aria-pressed={recentPresetActive(6)} onClick={() => { setSelectedScreenEpId(""); setCursorDate(null); applyPercentZoom(timeAxisRecentWindow(minVisibleAxisDate, maxVisibleAxisDate, 6)); }}>近6月</button>
          {hasMultiYearSpan && (
            <button type="button" aria-pressed={recentPresetActive(12)} onClick={() => { setSelectedScreenEpId(""); setCursorDate(null); applyPercentZoom(timeAxisRecentWindow(minVisibleAxisDate, maxVisibleAxisDate, 12)); }}>近1年</button>
          )}
          <button type="button" aria-pressed={!isZoomed} onClick={resetScreenZoom}>全览</button>
        </div>
        <div className="erp-zoom-group" role="group" aria-label="平移与缩放">
          <button type="button" onClick={() => applyPercentZoom(panWindow(zoomState, -0.5))} disabled={zoomState.start <= 0.05} title="向左平移半屏">← 左移</button>
          <button type="button" onClick={() => applyPercentZoom(panWindow(zoomState, 0.5))} disabled={atLatestEdge} title="向右平移半屏">右移 →</button>
          <button type="button" className={!atLatestEdge ? "erp-zoom-latest-cta" : undefined} onClick={jumpToLatest} disabled={atLatestEdge && cursorDate == null} title="保持当前缩放比例并一键跳到最右侧最新日期">跳到最新 ⇥</button>
          <button type="button" onClick={() => applyPercentZoom(zoomWindow(zoomState, 0.6))} disabled={zoomState.end - zoomState.start <= 0.6} aria-label="放大" title="放大时间轴">＋</button>
          <button type="button" onClick={() => applyPercentZoom(zoomWindow(zoomState, 1.6))} disabled={!isZoomed} aria-label="缩小" title="缩小时间轴">－</button>
        </div>
        <span className="erp-zoom-range" title="可直接拖拽底部滑块、拖动画布，或双指横向滑动平移">
          {visibleSpan.start ?? "—"} — {visibleSpan.end ?? "—"}
        </span>
      </div>
    )}

    {source.isPending || otherPrice.isPending ? <p role="status">历史资料读取中…</p> : source.error || otherPrice.isError ? <p role="alert">对照资料暂时不可用。<button type="button" onClick={() => { source.retry(); void otherPrice.refetch(); }}>重试</button></p>
      : enough ? <div ref={chartNode} className={`erp-cross-chart${isZoomed ? " erp-chart-pannable" : ""}`} role="img" aria-label={`上方${names[priceKey]}逐日价格主图，下方股债利差与${sigmas.join("和")}倍标准差轨道；区间阴影按实际日期标在两图，支持拖拽平移、双指横滑与快捷导航`} /> : <p className="op-empty">股债利差与价格缺少足够的共同历史。</p>}
    <details className="erp-standard-ref">
      <summary>阈值专业性与业界标准对照（滚动 ±σ vs 分位数 · 为什么上轨看赔率、下轨防钝化）</summary>
      <p><b>为何采用 3 年滚动均值 ±1.5σ / ±2σ：</b>传统 Fed Model 若死守固定数值（如 ERP &gt; 4% 或 0%），在中债利率长期下行或美债利率周期抬升时会失效；国信、方正金工研报普遍以 3–5 年滚动 Z-Score 或滚动分位做「非平稳去趋势」。1.5σ（约单侧前 6.7%）用于较早观察，2σ（约前 2.3%）用于极端估值对照。</p>
      <p><b>为何非对称阅读：</b>估值本质是「中期赔率尺」却欠缺「左侧择时能力」。上轨（+1.5σ/+2σ）便宜时股票相对债券安全边际高，但左侧常继续阴跌，业界习惯搭配宽度止跌回升（上方「估值便宜+宽度回暖」）确认右侧买点；下轨（−1.5σ/−2σ）在 A 股流动性牛市与美股高盈利成长阶段常持续钝化，因此仅作风险提示而不单作减仓线，需见 50 日宽度跌破半数退潮才加重防卫。</p>
      <p><b>本库实证边界：</b>本系统 2018–2026 年沪深 300 历史复测显示，机械地在 B50&lt;50% 且下降时强行将 ERP 仓位减半会使扣费年化从 2.64% 降至 1.28%（如 2024 年 9 月急涨错过修复）。因此联动筛选供研究对照与结构验证，仍以 BIAO 主图趋势管理方向与买卖。</p>
    </details>
    {!isUs && position && <details className="erp-trend-observation">
      <summary>沪深300当前估值与趋势 · {position.date} · Z {fmt(position.z)}{trend ? ` · 均线 ${trend.score}/3项成立` : " · 价格资料待补"}</summary>
      <div className="erp-position-values">
        <span>3年均值 <b>{fmt(position.mean)} 个百分点</b></span>
        <span>标准差 <b>{fmt(position.sigma)} 个百分点</b></span>
        <span>历史分位 <b>{fmt(position.percentile, 1)}%</b></span>
        <span>观测数 <b>{position.n} 周</b></span>
      </div>
      <p>Z 表示离3年均值几个标准差；分位比较同一窗口的周频读数。分位越高，利差在自身历史中越高。</p>
      {trend && <>
        <div className="erp-trend-methods">
          <section><h4>均线计分 · {TREND_STATE_NAMES[trend.scoreState]}</h4>
            <ul>{["收盘价 > MA20", "MA20 > MA60", "MA60 > MA120"].map((label, i) => <li key={label}><span>{label}</span><b>{trend.conditions[i] ? "成立" : "未成立"}</b></li>)}</ul>
            <p>3项成立为偏强，0项为偏弱，1–2项为分歧；分歧不等于窄幅横盘。</p>
          </section>
          <section><h4>带宽＋斜率 · {TREND_STATE_NAMES[trend.bandState]}</h4>
            <ul><li><span>均线带宽</span><b>{fmt(trend.spread * 100)}% / 参考 2.50%</b></li>
              <li><span>MA60近5日斜率（年化）</span><b>{fmt(trend.slope * 100)}%</b></li></ul>
            <p>{trend.narrow ? "带宽低于2.5%" : trend.flat ? "MA60斜率在±5%内" : "带宽与斜率均未进入收敛参考"}；满足任一收敛条件归为过渡，再按价格与MA20/60的相对位置区分强弱。</p>
          </section>
        </div>
        <p className="erp-trend-prices">价格截至 {trend.date}：收盘 {fmt(trend.price)} · MA20 {fmt(trend.ma20)} · MA60 {fmt(trend.ma60)} · MA120 {fmt(trend.ma120)} 点</p>
      </>}
      {researchMapping && <details className="erp-research-mapping">
        <summary>仓位映射实验 · 阶梯 {fmt(researchMapping.step, 0)}% ／ 连续 {fmt(researchMapping.continuous, 1)}%</summary>
        <div className="erp-research-toolbar">
          <label>趋势方法 <select aria-label="仓位实验趋势方法" value={researchTrend} onChange={event => setResearchTrend(event.target.value as "score" | "band")}>
            <option value="score">均线计分</option><option value="band">带宽＋斜率</option>
          </select></label>
          <span>框选为当前状态；数值为实验目标仓位</span>
        </div>
        <table>
          <caption>ERP × 趋势阶梯矩阵</caption>
          <thead><tr><th scope="col">ERP位置</th><th scope="col">偏弱</th><th scope="col">分歧／过渡</th><th scope="col">偏强</th></tr></thead>
          <tbody>{ERP_RESEARCH_MATRIX.map((row, index) => <tr key={row.label}>
            <th scope="row">{row.label}</th>{row.weights.map((weight, column) => <td key={column} className={index === researchMapping.row && column === researchMapping.column ? "is-current" : undefined}>{weight}%</td>)}
          </tr>)}</tbody>
        </table>
        <p>连续版在各档代表位置之间平滑过渡；模拟按周判断，目标与实际仓位相差超过10个百分点才调仓，下一交易日收盘成交。</p>
        <p>这里只演示两种映射，不读取账户持仓，也未用于交易。区间仓位取中点；完整定义、费用与历史代价见下方比较。</p>
      </details>}
      <p>两种方法属于本次实验定义。<a href="/library?report=docs%2Fexperiments%2Ferp-trend-matrix-2026-11-07.md">比较阶梯与连续调仓的历史结果 ↗</a></p>
    </details>}
    {isUs ? <>
      <p className="erp-cross-note">背景浅/深阴影分别标出股债利差进入 ±1.5σ / ±2σ 的连续区间，上下两图按实际日期同步着色。两档为本地历史参考；历史检验上轨每档仅3次可比事件，下轨1.5σ风险线索不稳，2σ未见增量。<br/>价格至 {price?.dates[price.dates.length - 1] ?? "—"}；利差至 {latest?.date ?? "—"}，盈利端月度更新。</p>
      <details className="op-source"><summary>5年与10年国债：多提供什么信息</summary>
        {curve !== null ? <p><b>{treasury?.as_of_us}</b> · 5年 <b>{fmt(y5)}%</b> ／ 10年 <b>{fmt(y10)}%</b> ／ 10年−5年 <b>{curve >= 0 ? "+" : ""}{(curve * 100).toFixed(0)} 基点</b>。来源：<a href="https://data.eastmoney.com/cjsj/zmgzsyl.html" target="_blank" rel="noreferrer">东方财富国债收益率</a>。</p> : <p>5年与10年的同日收益率暂未齐备，期限差留空。</p>}
        <p>使用同一盈利收益率时，“盈利收益率−5年国债”比当前10年版本多出的部分，恰好是“10年−5年”的期限差。因此这里直接看两期限及其差值，避免把重复信息当成两份估值支持。</p>
        <p><a href="https://pages.stern.nyu.edu/adamodar/New_Home_Page/valquestions/riskfreerates.htm" target="_blank" rel="noreferrer">Damodaran的期限匹配原则</a>强调利率要与现金流期限匹配。股票长期估值保留10年主参照；5年可用于中期比较，单独换期限没有验证过择时改善。</p>
        <p>进一步解释利率变化，可看同期限的实际利率与通胀补偿。<a href="https://www.federalreserve.gov/data/tips-yield-curve-and-inflation-compensation.htm" target="_blank" rel="noreferrer">美联储研究</a>把名义国债与TIPS之差解释为通胀补偿，其中也含风险溢价；两者反向变动时，名义利率可能几乎不变。</p>
      </details>
      <details className="op-source"><summary>读法、计算与来源</summary>
        <p>股债收益差＝标普500滚动盈利收益率－美国10年国债收益率。上轨看股票相对债券的估值改善，下轨看估值压力；零只表示两种收益率相等。</p>
        <p>每日用此前3个自然年的观测计算均值与总体标准差，不含当日；1.5σ与2σ用同一窗口。完整三年有效历史后显示；窗口内缺值则留空。历史盈利数据按月沿用，修订资料不等于当时已知值。</p>
        <p>图中标记是首次越过统计边界的日期；缺少同日价格时不挪到其他日期。价格停更后的利差仍在小图保留，大图只对照共同期间。</p>
        <p><a href="https://www.ssga.com/nz/en_gb/institutional/insights/mind-on-the-market-01-june-2026" target="_blank" rel="noreferrer">道富：股债相对估值</a>支持这种观察用途；1.5σ/2σ是本地统计参考，机构文献没有为这里的买卖效果背书。<a href="https://www.aqr.com/Insights/Research/Journal-Article/Fight-the-Fed-Model" target="_blank" rel="noreferrer">AQR：择时局限</a>。</p>
        <p>旧30/70分档检验中，高利差组在原加仓信号后60日的平均涨幅比低利差组低0.92个百分点，区间跨零；该结果不等于检验过当前两档标准差。</p>
      </details>
    </> : <>    <p className="erp-cross-note">2008—2026年10月的历史检验：1.5σ上穿后63个交易日10次涨、5次跌；2σ为7次涨、0次跌。样本少且可重叠；下轨的顶部提示效果不稳定。<br/>周频资料 {source.points[0]?.date ?? "—"}—{source.points[source.points.length - 1]?.date ?? "—"}；轨道自 {bands.find(row => row.upper !== null)?.date ?? "—"} 起。</p>
    <details className="op-source" onToggle={event => setShowHistory(event.currentTarget.open)}><summary>历史检验与反例</summary>{showHistory && <><ErpSensitivitySummary sigma={selected?.peakSigma ?? (sigmas.includes(1.5) ? 1.5 : sigmas[0])} />{selected?.peakSigma === 2 && <ErpEffectSummary selectedDate={selected.crossingDate} />}</>}</details>
    <details className="op-source"><summary>轨道怎么算、依据是什么</summary>
      <p>股债利差＝沪深300盈利收益率－中国10年国债收益率。三年均值加减所选倍数的标准差：1.5σ更靠近均值，2σ更极端；轨道随历史滚动变化。</p>
      <p>国信、方正的机构图示可核到1σ与2σ；1.5σ是本地灵敏度参考。三档用相同历史与计算窗口，方便比较提醒的早晚与后续价格。较频繁不等于更可靠。</p>
      <p>{ERP_BAND_METHOD.definition}公开盈利数据与报告的调仓盈利对齐存在差异，因此用于方法参照。穿轨取相邻有效周首次越界；选择事件回看前约3个月、后约6个月。</p>
      <p>数据：{source.sourceUrl ? <a href={source.sourceUrl} target="_blank" rel="noreferrer">{source.sourceName}</a> : source.sourceName}；方法：<a href={ERP_BAND_METHOD.url} target="_blank" rel="noreferrer">{ERP_BAND_METHOD.source}</a>。</p>
      <p>{source.note}；价格为{priceKey === "hs300" ? "沪深300" : "上证指数"}逐日收盘价，利差与轨道仍按实际观测周显示。历史修订值与当时可知值可能不同。</p>
    </details></>}

  </div>;
}
