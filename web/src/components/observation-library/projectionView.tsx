import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import * as echarts from "echarts";
import { fundamentalsApi } from "../../api/client";
import BreadthComparison from "../market-style/BreadthComparison";
import type { ScreenedEpisode } from "../market-style/breadthRegimeScreener";
import type { BreadthReadingResponse } from "../market-style/breadthReadingTypes";
import ValuationReferenceReading from "./ValuationReferenceReading";
import { marketReferenceBands } from "./marketReferenceBands";
import { projectionReference } from "./projectionReference";
import { buildMetricThresholds, cleanDatedPoints } from "./projectionThresholds";
import { alignProjection } from "./projectionAlignment";
import ErpBandSummary from "./ErpBandSummary";
import ErpCrossChart from "./ErpCrossChart";
import MetricComboWorkbench from "./MetricComboWorkbench";
import { evaluateMetricComboScreener, isComboSupportedMetric } from "./metricCrossScreener";
import { RecentFocusProjection } from "../focus-momentum/overview";
import { ERP_BAND_METHOD } from "./erpBands";
import { PROJECTION_METRICS, useProjectionSource } from "./projectionSources";
import { PANEL_QUERY_KEY, PANEL_URL, type ObservationPanelData } from "../market-observation-panel/model";
import { OBSERVATION_BY_ID, OBSERVATION_SECTIONS, observationReadingRank, observationSection } from "./catalog";
import "./projection.css";

type Market = "cn" | "us";
type Context = { windowDays: number; ruleIds: string[]; priceKey: string; fingerprint: string };
type PriceKey = "sse" | "hs300" | "sp500" | "nasdaq";
const PRICE_NAMES: Record<PriceKey, string> = { sse: "上证指数", hs300: "沪深300", sp500: "标普500", nasdaq: "纳斯达克综合指数" };
const WINDOWS = [{ years: 1, label: "1年" }, { years: 3, label: "3年" }, { years: 5, label: "5年" }, { years: 10, label: "10年" }, { years: 20, label: "20年" }, { years: null, label: "全部" }];
const EMPTY_PRICE = { dates: [] as string[], values: [] as (number | null)[] };
const exists = (v: number | null | undefined): v is number => typeof v === "number" && Number.isFinite(v);
const fmt = (v: number | null | undefined, digits = 2) => !exists(v) ? "缺值" : v.toLocaleString("zh-CN", { maximumFractionDigits: digits, minimumFractionDigits: digits });

export function MetricProjection({ id, market }: { id: string; market: Market }) {
  return id === "focus-momentum" ? <RecentFocusProjection /> : id === "erp-cn" || id === "erp-us" ? <ErpCrossChart key={id} market={id === "erp-us" ? "us" : "cn"} /> : <GenericMetricProjection id={id} market={market} />;
}

function GenericMetricProjection({ id, market }: { id: string; market: Market }) {
  const definition = PROJECTION_METRICS.find((item) => item.id === id)!;
  const [priceChoice, setPriceChoice] = useState<PriceKey>(market === "cn" ? "hs300" : "sp500");
  const priceKey = (market === "cn" ? ["sse", "hs300"] : ["sp500", "nasdaq"]).includes(priceChoice)
    ? priceChoice : market === "cn" ? "hs300" : "sp500";
  const [years, setYears] = useState<number | null>(id === "turnover-concentration" ? 10 : 5);
  const [variant, setVariant] = useState<"orth" | "raw">("orth");
  const [activeRules, setActiveRules] = useState<ReadonlySet<string>>(() => new Set());
  const [selectedEpId, setSelectedEpId] = useState("");
  const [cursorIdx, setCursorIdx] = useState<number | null>(null);
  const [zoomPct, setZoomPct] = useState<{ start: number; end: number; seq: number } | null>(null);

  useEffect(() => {
    setActiveRules(new Set());
    setSelectedEpId("");
    setCursorIdx(null);
    setZoomPct(null);
  }, [id]);

  useEffect(() => {
    setCursorIdx(null);
    setSelectedEpId("");
    setZoomPct(null);
  }, [priceKey, years, variant]);

  const hasCombo = isComboSupportedMetric(id);
  const source = useProjectionSource(id, variant);
  const panelQuery = useQuery({
    queryKey: PANEL_QUERY_KEY,
    queryFn: async ({ signal }) => {
      const resp = await fetch(PANEL_URL, { signal });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return (await resp.json()) as ObservationPanelData;
    },
    enabled: id === "hy-oas" || id === "vix" || hasCombo,
    staleTime: 10 * 60_000,
    retry: false,
  });

  const breadthId = market === "cn" ? "CN_ALL_A" : "SP500";
  const breadthQuery = useQuery({
    queryKey: ["overlayBreadthReading", breadthId, 12600],
    queryFn: async ({ signal }): Promise<BreadthReadingResponse> => {
      const resp = await fetch(
        `/api/market-context/breadth-history?market_id=${breadthId}&lookback_days=12600&include_observation=true`,
        { signal },
      );
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return resp.json();
    },
    enabled: hasCombo,
    staleTime: 5 * 60_000,
    retry: false,
  });
  const ratesAuxQuery = useQuery({
    queryKey: ["fundamentalsRatesHistory", 18250],
    queryFn: () => fundamentalsApi.ratesHistory(18250),
    enabled: hasCombo,
    staleTime: 5 * 60_000,
    retry: false,
  });
  const usMacroAuxQuery = useQuery({
    queryKey: ["fundamentalsUsMacro"],
    queryFn: () => fundamentalsApi.usMacro(),
    enabled: hasCombo && market === "us",
    staleTime: 30 * 60_000,
    retry: false,
  });

  const effectivePoints = useMemo(() => {
    if (id !== "hy-oas" && id !== "vix") return source.points;
    const panelPts = panelQuery.data?.cards[id]?.points;
    if (!panelPts?.length) return source.points;
    const byDate = new Map<string, number>();
    for (const p of cleanDatedPoints(panelPts)) byDate.set(p.date, p.value);
    for (const p of cleanDatedPoints(source.points)) byDate.set(p.date, p.value);
    return [...byDate.entries()]
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([date, value]) => ({ date, value }));
  }, [id, panelQuery.data, source.points]);

  const auxPoints = useMemo(() => {
    const mapSeries = (s?: { dates: string[]; values: (number | null)[] }) =>
      s && s.dates.length === s.values.length
        ? s.dates.map((date, idx) => ({ date, value: exists(s.values[idx]) ? s.values[idx] : null }))
        : [];
    const hyLive = mapSeries(usMacroAuxQuery.data?.series.hy_oas);
    const hyPanel = panelQuery.data?.cards["hy-oas"]?.points ?? [];
    const hyMergedMap = new Map<string, number>();
    for (const p of cleanDatedPoints(hyPanel)) hyMergedMap.set(p.date, p.value);
    for (const p of cleanDatedPoints(hyLive)) hyMergedMap.set(p.date, p.value);
    const hyMerged = [...hyMergedMap.entries()]
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([date, value]) => ({ date, value }));

    return {
      marginRatio: mapSeries(ratesAuxQuery.data?.series.margin_rzyezb),
      vix: mapSeries(ratesAuxQuery.data?.series.vix),
      vixTerm: mapSeries(ratesAuxQuery.data?.series.vix_term),
      hyOas: hyMerged,
    };
  }, [ratesAuxQuery.data, usMacroAuxQuery.data, panelQuery.data]);

  const usesReferencePrice = id === "erp-cn" && priceKey === "hs300";
  const frequency = source.frequency ?? definition.frequency;
  const prices = useQuery({ queryKey: ["fundOverlay", 47], queryFn: () => fundamentalsApi.overlayHistory(47),
    enabled: !usesReferencePrice, staleTime: 5 * 60_000, retry: false });
  const series = (usesReferencePrice ? source.referencePrice : prices.data?.series[priceKey]) ?? EMPTY_PRICE;
  const view = useMemo(() => alignProjection(series, effectivePoints, frequency, years), [series, effectivePoints, frequency, years]);
  const bandByDate = useMemo(() => new Map(source.bands?.map((p) => [p.date, p]) ?? []), [source.bands]);
  const viewBands = view.metricDates.map((date) => date ? bandByDate.get(date) : undefined);
  const lastPoint = effectivePoints[effectivePoints.length - 1];
  const reference = projectionReference(id);
  const thresholdBundle = useMemo(() => buildMetricThresholds(id, effectivePoints), [id, effectivePoints]);
  const marketBands = useMemo(() => marketReferenceBands(id, effectivePoints, source.valuationFull), [id, effectivePoints, source.valuationFull]);
  const referenceByDate = useMemo(() => new Map(marketBands?.rows.map(row => [row.date, row]) ?? []), [marketBands]);
  const zero = reference?.value ?? null;

  const comboEval = useMemo(() => {
    return evaluateMetricComboScreener({
      id,
      frequency,
      dates: view.dates,
      prices: view.price,
      metricValues: view.values,
      fullMetricPoints: effectivePoints,
      breadthPoints: breadthQuery.data?.history ?? [],
      marginRatioPoints: auxPoints.marginRatio,
      vixPoints: auxPoints.vix,
      vixTermPoints: auxPoints.vixTerm,
      hyOasPoints: auxPoints.hyOas,
      activeIds: activeRules,
    });
  }, [id, frequency, view, effectivePoints, breadthQuery.data, auxPoints, activeRules]);

  const inspectIdx = cursorIdx != null && cursorIdx >= 0 && cursorIdx < view.dates.length
    ? cursorIdx
    : view.dates.length - 1;
  const inspectDate = inspectIdx >= 0 ? view.dates[inspectIdx] : lastPoint?.date ?? null;
  const inspectMetricDate = inspectIdx >= 0 ? view.metricDates[inspectIdx] ?? inspectDate : lastPoint?.date ?? null;
  const inspectValue = inspectIdx >= 0 ? view.values[inspectIdx] : lastPoint?.value ?? null;
  const ctxAtInspect = inspectDate ? comboEval.contextByDate.get(inspectDate) : undefined;

  const node = useRef<HTMLDivElement>(null);
  const chartInst = useRef<echarts.ECharts | null>(null);
  const enough = view.price.filter((v, i) => v !== null && view.values[i] !== null).length >= 2;
  const screeningActive = activeRules.size > 0;

  useEffect(() => {
    if (!node.current || !enough) return;
    const chart = echarts.init(node.current, undefined, { renderer: "svg" });
    chartInst.current = chart;
    const referenceLines = [
      ...(reference ? [{ yAxis: reference.value,
        lineStyle: { color: "#536a82", width: 1.7, type: "dashed" as const },
        label: { formatter: reference.label, position: "insideEndTop" as const } }] : []),
      ...(thresholdBundle?.fixedRails.map((rail) => ({
        yAxis: rail.value,
        lineStyle: { color: rail.color, width: 1.9, type: "dashed" as const },
        label: {
          formatter: rail.shortLabel,
          position: "insideEndTop" as const,
          color: rail.color,
          fontWeight: 600,
          backgroundColor: "rgba(255,255,255,.92)",
          padding: [2, 4],
        },
      })) ?? []),
    ];
    const dynamicThresholdSeries = (thresholdBundle?.dynamicSeries ?? []).map((dyn) => ({
      name: dyn.name,
      type: "line" as const,
      xAxisIndex: 1,
      yAxisIndex: 1,
      showSymbol: false,
      connectNulls: false,
      data: view.metricDates.map((d) => (d ? dyn.byDate.get(d) ?? null : null)),
      lineStyle: {
        color: dyn.color,
        width: dyn.dashed ? 1.9 : 2.0,
        type: dyn.dashed ? ("dashed" as const) : ("solid" as const),
      },
      itemStyle: { color: dyn.color },
    }));
    const legendNames = [
      PRICE_NAMES[priceKey],
      definition.label,
      ...dynamicThresholdSeries.map((s) => s.name),
    ];
    const activeMarkArea = screeningActive && comboEval.markAreas.length
      ? { silent: true, itemStyle: { borderWidth: 0 }, data: comboEval.markAreas }
      : undefined;

    chart.setOption({
      animation: false,
      textStyle: { fontFamily: 'system-ui, -apple-system, "PingFang SC", sans-serif' },
      legend: dynamicThresholdSeries.length > 0 ? {
        top: 0, left: 0, data: legendNames, textStyle: { fontSize: 12, color: "#344256" },
      } : undefined,
      grid: [{ left: 60, right: 32, top: dynamicThresholdSeries.length > 0 ? 52 : 40, height: "45%" }, { left: 60, right: 32, top: "70%", height: "19%" }],
      title: [{ text: `${PRICE_NAMES[priceKey]}（点）${screeningActive ? " · 已高亮所选组合命中区间" : ""}`, left: 0, top: dynamicThresholdSeries.length > 0 ? 27 : 4, textStyle: { fontSize: 12.5, fontWeight: 600, color: "#243f63" } },
        { text: `${definition.label}（${source.unit}）${thresholdBundle ? " · 含参考阈值轨道" : ""}`, left: 0, top: "63%", textStyle: { fontSize: 12.5, fontWeight: 600, color: "#173d68" } }],
      tooltip: { trigger: "axis", confine: true, axisPointer: { type: "cross" }, formatter: (raw: unknown) => {
        const values = Array.isArray(raw) ? raw : [raw];
        const i = Number((values[0] as { dataIndex?: number })?.dataIndex);
        if (!Number.isInteger(i) || !view.dates[i]) return "—";
        const mDate = view.metricDates[i] ?? "";
        const coverage = source.coverage?.[mDate || view.dates[i]];
        const band = viewBands[i];
        const valuation = marketBands?.kind === "valuation" ? referenceByDate.get(mDate) : undefined;
        const dynInfo = thresholdBundle?.dynamicSeries
          .map((d) => `${d.name}：${fmt(mDate ? d.byDate.get(mDate) ?? null : null)} ${source.unit}`)
          .join(" · ");
        const ctx = comboEval.contextByDate.get(view.dates[i]);
        const extraVixTerm = id === "vix" && exists(ctx?.vixTerm) ? `<br/>期限比 VIX/VIX3M：<b>${ctx.vixTerm.toFixed(2)}</b>` : "";
        const extraBreadth = hasCombo && exists(ctx?.b50) ? `<br/>${market === "cn" ? "全A" : "标普"} 50日宽度：${ctx.b50.toFixed(1)}%` : "";
        return `<b>${view.dates[i]}</b><br/>${PRICE_NAMES[priceKey]}：${fmt(view.price[i])}<br/>${definition.label}：<b>${fmt(view.values[i], id === "baker-wurgler" ? 3 : 2)} ${source.unit}</b>${extraVixTerm}${extraBreadth}${dynInfo ? `<br/>${dynInfo}` : ""}${band ? `<br/>上轨：${fmt(band.upper)} · 中轨：${fmt(band.middle)} · 下轨：${fmt(band.lower)}` : ""}${valuation?.lower != null && valuation.upper != null ? `<br/>近10年 P20：${fmt(valuation.lower)} · P80：${fmt(valuation.upper)}` : ""}${coverage ? `<br/>有效 / 候选：${coverage.n} / ${coverage.universeN}只` : ""}`;
      } },
      axisPointer: { link: [{ xAxisIndex: [0, 1] }] },
      xAxis: [0, 1].map((index) => ({ type: "category", gridIndex: index, data: view.dates, boundaryGap: false,
        axisLabel: { show: index === 1, hideOverlap: true, showMinLabel: true, showMaxLabel: true, color: "#64748b", formatter: (date: string) => frequency !== "monthly" && view.dates.length < 80 ? date.slice(5) : date.slice(0, 7) } })),
      yAxis: [0, 1].map((index) => ({ type: "value", gridIndex: index, scale: true, splitNumber: 3,
        min: ({ min, max }: { min: number; max: number }) => {
          const rails = index === 1 && thresholdBundle ? thresholdBundle.fixedRails.map((r) => r.value) : [];
          const lo = rails.length ? Math.min(min, ...rails) : min;
          const hi = rails.length ? Math.max(max, ...rails) : max;
          if (!Number.isFinite(lo) || !Number.isFinite(hi)) return undefined;
          const raw = lo - Math.max(hi - lo, Math.abs(lo) * .005, .01) * .08;
          return index === 0 ? Math.floor(raw) : raw;
        },
        max: ({ min, max }: { min: number; max: number }) => {
          const rails = index === 1 && thresholdBundle ? thresholdBundle.fixedRails.map((r) => r.value) : [];
          const lo = rails.length ? Math.min(min, ...rails) : min;
          const hi = rails.length ? Math.max(max, ...rails) : max;
          if (!Number.isFinite(lo) || !Number.isFinite(hi)) return undefined;
          const raw = hi + Math.max(hi - lo, Math.abs(hi) * .005, .01) * .1;
          return index === 0 ? Math.ceil(raw) : raw;
        },
        axisLabel: { color: "#64748b", formatter: (value: number) => index === 0 ? Math.round(value).toLocaleString("zh-CN") : Math.abs(value) >= 100000 ? `${(value / 10000).toFixed(0)}万` : `${Number(value.toFixed(2))}` },
        splitLine: { lineStyle: { color: "#e2e8ef" } } })),
      dataZoom: [{ type: "inside", xAxisIndex: [0, 1], filterMode: "filter" }, { type: "slider", xAxisIndex: [0, 1], filterMode: "filter", bottom: 4, height: 20, showDetail: false }],
      series: [
        { name: PRICE_NAMES[priceKey], type: "line", xAxisIndex: 0, yAxisIndex: 0, data: view.price, connectNulls: false, showSymbol: false,
          lineStyle: { color: "#243d61", width: 2.8 }, markArea: activeMarkArea },
        { name: definition.label, type: "line", xAxisIndex: 1, yAxisIndex: 1, data: view.values, connectNulls: false, showSymbol: view.dates.length < 12,
          lineStyle: { color: "#34698f", width: 2.4 },
          markLine: { silent: true, symbol: "none", label: { color: "#667085", backgroundColor: "rgba(255,255,255,.9)", padding: [2, 3] }, data: referenceLines },
          markArea: activeMarkArea },
        ...dynamicThresholdSeries,
        ...(marketBands ? ([ ["lower", marketBands.lowerLabel, "#3c867a"], ["upper", marketBands.upperLabel, "#ac7032"] ] as const).map(([key, name, color]) => ({
          name, type: "line", xAxisIndex: 1, yAxisIndex: 1, showSymbol: false, connectNulls: false,
          data: view.metricDates.map(date => date ? referenceByDate.get(date)?.[key] ?? null : null),
          lineStyle: { color, width: 2, type: "dashed" }, endLabel: { show: true, formatter: key === "lower" ? marketBands.lowerShort : marketBands.upperShort, color, fontSize: 11 },
        })) : []),
        ...(source.bands ? ([
          ["upper", "上轨 +2σ", "#94622d"], ["middle", "中轨 · 3年均值", "#536a82"], ["lower", "下轨 −2σ", "#41617d"],
        ] as const).map(([key, name, color]) => ({ name, type: "line", xAxisIndex: 1, yAxisIndex: 1,
          data: viewBands.map((p) => p?.[key] ?? null), connectNulls: false, showSymbol: false,
          lineStyle: { color, width: key === "middle" ? 1.6 : 2.2, type: key === "middle" ? "dashed" : "solid" } })) : []),
      ],
    });
    chart.on("updateAxisPointer", (ev: unknown) => {
      const idx = (ev as { dataIndex?: number; axesInfo?: { value?: number }[] }).dataIndex
        ?? (ev as { axesInfo?: { value?: number }[] }).axesInfo?.[0]?.value;
      if (typeof idx === "number" && idx >= 0 && idx < view.dates.length) {
        setCursorIdx(idx);
      }
    });
    const resize = new ResizeObserver(() => chart.resize()); resize.observe(node.current);
    return () => { resize.disconnect(); chart.dispose(); chartInst.current = null; };
  }, [view, priceKey, definition, id, market, hasCombo, source.unit, source.coverage, source.bands, frequency, enough, reference, zero, marketBands, referenceByDate, thresholdBundle, screeningActive, comboEval.markAreas, comboEval.contextByDate]);

  useEffect(() => {
    if (!zoomPct || !chartInst.current) return;
    chartInst.current.dispatchAction({
      type: "dataZoom",
      dataZoomIndex: 0,
      start: zoomPct.start,
      end: zoomPct.end,
    });
  }, [zoomPct]);

  const toggleRule = (ruleId: string) => {
    setSelectedEpId("");
    setActiveRules((prev) => {
      const next = new Set(prev);
      if (next.has(ruleId)) next.delete(ruleId);
      else next.add(ruleId);
      return next;
    });
  };

  const handleSelectEpisode = (ep: ScreenedEpisode) => {
    setSelectedEpId(ep.id);
    setCursorIdx(ep.startIndex);
    const total = Math.max(1, view.dates.length - 1);
    const padBefore = frequency === "daily" ? 30 : 8;
    const padAfter = frequency === "daily" ? 60 : 16;
    let sPct = Math.max(0, ((ep.startIndex - padBefore) / total) * 100);
    let ePct = Math.min(100, ((ep.endIndex + padAfter) / total) * 100);
    if (ePct - sPct < 8) {
      const mid = (sPct + ePct) / 2;
      sPct = Math.max(0, mid - 4);
      ePct = Math.min(100, mid + 4);
    }
    setZoomPct((prev) => ({ start: sPct, end: ePct, seq: (prev?.seq ?? 0) + 1 }));
  };

  const handleResetZoom = () => {
    setSelectedEpId("");
    setCursorIdx(null);
    setZoomPct((prev) => ({ start: 0, end: 100, seq: (prev?.seq ?? 0) + 1 }));
  };

  const priceKeys = (market === "cn" ? ["sse", "hs300"] : ["sp500", "nasdaq"]) as PriceKey[];

  return <div className="op-metric">
    <div className="op-toolbar" role="group" aria-label="股指与期间切换">
      <div className="op-seg-group op-seg-pillbox" role="group" aria-label="对照股指">
        {priceKeys.map((key) => (
          <button type="button" key={key} aria-pressed={priceKey === key} onClick={() => setPriceChoice(key)}>
            {PRICE_NAMES[key]}
          </button>
        ))}
      </div>
      {id === "baker-wurgler" && (
        <div className="op-seg-group op-seg-pillbox" role="group" aria-label="对照图Baker版本">
          <button type="button" aria-pressed={variant === "orth"} onClick={() => setVariant("orth")}>剔除宏观影响</button>
          <button type="button" aria-pressed={variant === "raw"} onClick={() => setVariant("raw")}>原始版</button>
        </div>
      )}
      <div className="op-seg-group" style={{ marginLeft: "auto" }} role="group" aria-label="对照期间">
        {WINDOWS.map((w) => (
          <button type="button" key={w.label} aria-pressed={years === w.years} onClick={() => setYears(w.years)}>
            {w.label}
          </button>
        ))}
      </div>
    </div>

    <div className="op-spec-box" aria-label="指标联立读数与口径">
      <div className="op-spec-row">
        <strong>{inspectDate ?? "—"} 读数：</strong>
        <span>
          {definition.label} <b>{fmt(inspectValue, id === "baker-wurgler" ? 3 : 2)}</b> {source.unit}
        </span>
        {thresholdBundle?.dynamicSeries.map((dyn) => {
          const val = inspectMetricDate ? dyn.byDate.get(inspectMetricDate) : dyn.latest;
          return (
            <span key={dyn.key}>
              {dyn.shortLabelPrefix} <b>{fmt(val)}</b> {source.unit}
            </span>
          );
        })}
        {thresholdBundle?.fixedRails.map((r) => (
          <span key={r.value} style={{ color: r.color, fontWeight: 600 }}>
            {r.shortLabel}
          </span>
        ))}
        {id === "vix" && exists(ctxAtInspect?.vixTerm) && (
          <span>
            期限比 VIX/VIX3M <b>{ctxAtInspect.vixTerm.toFixed(2)}</b>
          </span>
        )}
        {id !== "vix" && market === "us" && hasCombo && exists(ctxAtInspect?.vix) && (
          <span>VIX <b>{ctxAtInspect.vix.toFixed(1)}</b></span>
        )}
        {id !== "hy-oas" && market === "us" && hasCombo && exists(ctxAtInspect?.hyOas) && (
          <span>HY OAS <b>{ctxAtInspect.hyOas.toFixed(2)}%</b></span>
        )}
        {hasCombo && exists(ctxAtInspect?.b50) && (
          <span>
            {market === "cn" ? "全A" : "标普"}50日宽度 <b>{ctxAtInspect.b50.toFixed(1)}%</b>
          </span>
        )}
        {market === "cn" && hasCombo && exists(ctxAtInspect?.marginRatio) && (
          <span>
            两融占比 <b>{ctxAtInspect.marginRatio.toFixed(2)}%</b>
          </span>
        )}
        {cursorIdx != null && (
          <button type="button" className="op-spec-reset" onClick={() => setCursorIdx(null)}>
            回最新期
          </button>
        )}
      </div>
      <div className="op-spec-row op-spec-muted">
        <span>
          <b>{definition.meaning}</b> · {thresholdBundle ? thresholdBundle.sizingGuide : definition.reading}
        </span>
      </div>
    </div>

    {hasCombo && (
      <MetricComboWorkbench
        evaluation={comboEval}
        priceName={PRICE_NAMES[priceKey]}
        frequency={frequency}
        latestDate={view.dates[view.dates.length - 1] ?? lastPoint?.date}
        activeIds={activeRules}
        selectedEpisodeId={selectedEpId}
        onToggleRule={toggleRule}
        onClearRules={() => {
          setActiveRules(new Set());
          handleResetZoom();
        }}
        onSelectEpisode={handleSelectEpisode}
        onResetZoom={handleResetZoom}
      />
    )}

    {marketBands?.kind === "valuation" && !source.isPending && !source.error && !hasCombo &&
      <div className="ol-reference-reading"><ValuationReferenceReading reference={marketBands} /></div>}
    {marketBands?.kind === "concentration" && marketBands.latest?.lower != null && marketBands.latest.upper != null && <div className="op-reading">
      <span><strong>{marketBands.lowerLabel} {fmt(marketBands.latest.lower)}{marketBands.unit}</strong> ／ <strong>{marketBands.upperLabel} {fmt(marketBands.latest.upper)}{marketBands.unit}</strong><br />{marketBands.meaning}<br /><small>{marketBands.coverage}</small></span>
    </div>}
    {source.bands && <ErpBandSummary row={source.bands[source.bands.length - 1]} />}
    {((!usesReferencePrice && prices.isPending) || (source.isPending && !effectivePoints.length)) ? <p role="status">价格与指标资料读取中…</p>
      : ((!usesReferencePrice && prices.isError) || (source.error && !effectivePoints.length)) ? <p role="alert">对照资料暂时不可用。<button type="button" onClick={() => { source.retry(); if (!usesReferencePrice) void prices.refetch(); }}>重试</button></p>
      : enough ? <div ref={node} className="op-chart" role="img" aria-label={`${PRICE_NAMES[priceKey]}价格与${definition.label}，上方价格下方指标，共用日期轴`} />
      : <p className="op-empty">两条序列没有足够的共同历史，暂不画投影。</p>}
    <p className="op-footnote op-evidence">{marketBands ? <>{marketBands.detail} <a href={marketBands.source.url} target="_blank" rel="noreferrer">{marketBands.source.source} ↗</a></> : thresholdBundle
      ? <><b>阈值依据：</b>{thresholdBundle.rationale}</>
      : reference
      ? <>{reference.label}：{reference.meaning} <a href={reference.url} target="_blank" rel="noreferrer">{reference.source}</a></>
      : source.bands ? <>轨道依据：<a href={ERP_BAND_METHOD.url} target="_blank" rel="noreferrer">{ERP_BAND_METHOD.source}</a>。{ERP_BAND_METHOD.difference}</>
      : id === "baker-wurgler" ? "月度、可修订的情绪背景；原研究未建立大盘阶段顶底阈值。"
      : "未建立经验证的固定机会／风险阈值，图中仅展示原值。"}</p>
    {id === "hy-oas" && <p className="op-footnote">FRED 自2026年4月起仅公开最近3年；选择更长窗口也不会补出更早历史。<a href="https://fred.stlouisfed.org/series/BAMLH0A0HYM2" target="_blank" rel="noreferrer">来源说明</a></p>}
    {id === "turnover-concentration" && <p className="op-footnote">{source.status}2023-01—2026-07及个别月份输入不完整，曲线保留断线。</p>}
    {source.coverage && <p className="op-footnote">光标显示每期有效／候选只数；候选数按供应商上市、退出日期推算，非官方全A覆盖率。已存历史，未自动更新。</p>}
    <p className="op-footnote">{frequency === "monthly" ? "按所属月对齐当月最后可得收盘价；历史修订值不等于当时已公布。" : frequency === "weekly" ? "股价取观测日或此前6天内最近收盘价；发布日期另见来源。" : "按交易日对齐，缺值不补。"}
      {enough && ` 图示 ${view.dates[0]}—${view.dates[view.dates.length - 1]}。`}</p>
    <details className="op-source"><summary>范围与来源</summary><p>{definition.scope}</p><p>{source.note}</p>
      {source.bands && <p>{ERP_BAND_METHOD.definition}每期使用当期及此前资料；历史数据是否修订与实际发布时间仍需区分。</p>}
      <p>指标：{source.sourceUrl ? <a href={source.sourceUrl} target="_blank" rel="noreferrer">{source.sourceName}</a> : source.sourceName}。价格：{usesReferencePrice ? "本次已核沪深300历史副本" : market === "us" ? "FRED（标普500／纳斯达克综合）" : "现有指数行情接口"}，价格源截至 {series.dates[series.dates.length - 1] ?? "—"}。</p>
      <p>指标可用历史：{source.points[0]?.date ?? "—"}—{lastPoint?.date ?? "—"}。价格可用历史：{series.dates[0] ?? "—"}—{series.dates[series.dates.length - 1] ?? "—"}；对照图只显示共同期间。</p>
    </details>
  </div>;
}

export default function ObservationProjection({ market, onMarketChange, onContextChange }: {
  market: Market; onMarketChange: (market: Market) => void; onContextChange?: (context: Context) => void;
}) {
  const location = useLocation();
  const navigate = useNavigate();
  const [choice, setChoice] = useState("breadth");
  const card = useRef<HTMLElement>(null);
  const previousMarket = useRef(market);
  const selected = PROJECTION_METRICS.find((item) => item.id === choice);
  const id = !selected || selected.market === market ? choice : "breadth";
  const selectUrl = (next: string, nextMarket: Market) => {
    const params = new URLSearchParams(location.search);
    params.set("observation", next);
    params.set("market", nextMarket);
    navigate({ search: params.toString(), hash: "#fund-sec-market" }, { replace: true });
  };
  const selectObservation = (next: string) => {
    const entry = PROJECTION_METRICS.find((item) => item.id === next);
    const nextMarket = entry?.market ?? market;
    setChoice(next);
    if (nextMarket !== market) onMarketChange(nextMarket);
    selectUrl(next, nextMarket);
    requestAnimationFrame(() => card.current?.scrollIntoView({ block: "start" }));
  };
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const requested = params.get("observation");
    if (requested === "breadth") {
      setChoice("breadth");
      const targetMarket = params.get("market");
      if (targetMarket === "cn" || targetMarket === "us") onMarketChange(targetMarket);
      const frame = requestAnimationFrame(() => card.current?.scrollIntoView({ block: "start" }));
      return () => cancelAnimationFrame(frame);
    }
    const entry = PROJECTION_METRICS.find((item) => item.id === requested);
    if (!entry) return;
    setChoice(entry.id); onMarketChange(entry.market);
    const frame = requestAnimationFrame(() => card.current?.scrollIntoView({ block: "start" }));
    return () => cancelAnimationFrame(frame);
  }, [location.search, onMarketChange]);
  useEffect(() => {
    if (previousMarket.current === market) return;
    previousMarket.current = market;
    if (selected && selected.market !== market) {
      setChoice("breadth");
      selectUrl("breadth", market);
    } else if (choice === "breadth") {
      const params = new URLSearchParams(location.search);
      if ((!params.has("observation") || params.get("observation") === "breadth") && params.get("market") !== market) selectUrl("breadth", market);
    }
  }, [market]);
  useEffect(() => {
    // Existing Agent snapshot knows breadth only; do not bind it to an unrelated selected model.
    if (id !== "breadth") onContextChange?.({ windowDays: 365, ruleIds: [], priceKey: "", fingerprint: "" });
  }, [id, onContextChange]);
  return <section className="observation-projection" ref={card} aria-label="价格与指标对照">
    <header className="op-header"><div><h2>价格与指标对照</h2><p>{id === "erp-cn" ? "上方看股债利差与三年轨道，下方看股指价格；日期、光标与缩放联动。" : "上方看价格，下方看指标；日期、光标与缩放联动。"}</p></div>
      <label>观察指标<select aria-label="选择对照指标" value={id} onChange={(e) => selectObservation(e.target.value)}><option value="breadth">市场宽度 · {market === "cn" ? "全A" : "标普500"}</option>
        {OBSERVATION_SECTIONS.map((section) => {
          const items = PROJECTION_METRICS.filter((item) => {
            const entry = OBSERVATION_BY_ID.get(item.id);
            return entry && observationSection(entry) === section.id;
          }).sort((a, b) => observationReadingRank(OBSERVATION_BY_ID.get(a.id)!) - observationReadingRank(OBSERVATION_BY_ID.get(b.id)!));
          return items.length > 0 && <optgroup key={section.id} label={section.label}>
            {items.map((item) => <option key={item.id} value={item.id}>{item.market === "cn" ? "A股" : "美股"} · {item.label}</option>)}
          </optgroup>;
        })}
      </select></label>
    </header>
    <div className="op-quick" role="group" aria-label={`${market === "cn" ? "A股" : "美股"}常用对照`}>
      <span>快速查看</span>
      <button type="button" aria-pressed={id === "breadth"} onClick={() => selectObservation("breadth")}>市场宽度 · {market === "cn" ? "全A" : "标普500"}</button>
      <button type="button" aria-pressed={id === (market === "cn" ? "erp-cn" : "erp-us")} onClick={() => selectObservation(market === "cn" ? "erp-cn" : "erp-us")}>{market === "cn" ? "沪深300股债利差 · 上下轨" : "标普500股债利差 · 上下轨"}</button>
      {market === "us" && <>
        <button type="button" aria-pressed={id === "vix"} onClick={() => selectObservation("vix")}>VIX</button>
        <button type="button" aria-pressed={id === "hy-oas"} onClick={() => selectObservation("hy-oas")}>高收益债利差</button>
      </>}
    </div>
    {id === "breadth" ? <BreadthComparison market={market} onMarketChange={onMarketChange} onContextChange={onContextChange} />
      : id === "erp-cn" ? <ErpCrossChart /> : <MetricProjection id={id} market={market} />}
  </section>;
}
