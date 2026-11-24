import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import * as echarts from "echarts";
import { fundamentalsApi } from "../../api/client";
import type { ScreenedEpisode } from "../market-style/breadthRegimeScreener";
import type { BreadthReadingResponse } from "../market-style/breadthReadingTypes";
import { alignProjection } from "./projectionAlignment";
import { useProjectionSource } from "./projectionSources";
import { buildMetricThresholds, cleanDatedPoints } from "./projectionThresholds";
import MetricComboWorkbench from "./MetricComboWorkbench";
import { evaluateMetricComboScreener } from "./metricCrossScreener";

export type CnFinancingTab = "buy" | "balance";
type PriceKey = "sse" | "hs300";

const PRICE_NAMES: Record<PriceKey, string> = {
  sse: "上证指数",
  hs300: "沪深300",
};

const BUY_WINDOWS = [
  { years: 0.5, label: "半年" },
  { years: 1, label: "1年" },
  { years: 3, label: "3年" },
  { years: null, label: "全部" },
] as const;

const BAL_WINDOWS = [
  { years: 1, label: "1年" },
  { years: 3, label: "3年" },
  { years: 5, label: "5年" },
  { years: 10, label: "10年" },
  { years: 20, label: "20年" },
  { years: null, label: "全部" },
] as const;

const FUNDING_PACKET_URL = "/api/fundamentals/cn-financing-history";
type FundingCard = {
  id: string;
  points: { date: string; value: number | null }[];
  lines?: { key: string; values: (number | null)[] }[];
};

const exists = (v: number | null | undefined): v is number =>
  typeof v === "number" && Number.isFinite(v);
const fmt = (v: number | null | undefined, digits = 2) =>
  exists(v) ? v.toFixed(digits) : "—";

export default function CnFinancingProjection({ initialTab = "buy" }: { initialTab?: CnFinancingTab }) {
  const [tab, setTab] = useState<CnFinancingTab>(initialTab);
  const [priceKey, setPriceKey] = useState<PriceKey>("sse");
  const [years, setYears] = useState<number | null>(initialTab === "buy" ? 1 : 5);
  const [activeRules, setActiveRules] = useState<ReadonlySet<string>>(() => new Set());
  const [selectedEpId, setSelectedEpId] = useState("");
  const [cursorIdx, setCursorIdx] = useState<number | null>(null);
  const [zoomPct, setZoomPct] = useState<{ start: number; end: number; seq: number } | null>(null);

  useEffect(() => {
    setTab(initialTab);
    setYears(initialTab === "buy" ? 1 : 5);
    setActiveRules(new Set());
    setSelectedEpId("");
    setCursorIdx(null);
    setZoomPct(null);
  }, [initialTab]);

  const pricesQuery = useQuery({
    queryKey: ["fundOverlay", 47],
    queryFn: () => fundamentalsApi.overlayHistory(47),
    staleTime: 5 * 60_000,
    retry: false,
  });
  const ratesQuery = useQuery({
    queryKey: ["fundamentalsRatesHistory", 18250],
    queryFn: () => fundamentalsApi.ratesHistory(18250),
    staleTime: 5 * 60_000,
    retry: false,
  });
  const fundingQuery = useQuery({
    queryKey: ["homeFinancingPacketV1"],
    queryFn: async ({ signal }) => {
      const resp = await fetch(FUNDING_PACKET_URL, { signal });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return (await resp.json()) as { cards?: FundingCard[] };
    },
    staleTime: 30 * 60_000,
    retry: false,
  });
  const cnObsQuery = useQuery({
    queryKey: ["marketStyleCnObservations"],
    queryFn: () => fundamentalsApi.observations("cn"),
    staleTime: 5 * 60_000,
    retry: false,
  });
  const breadthQuery = useQuery({
    queryKey: ["overlayBreadthReading", "CN_ALL_A", 12600],
    queryFn: async ({ signal }): Promise<BreadthReadingResponse> => {
      const resp = await fetch(
        "/api/market-context/breadth-history?market_id=CN_ALL_A&lookback_days=12600&include_observation=true",
        { signal },
      );
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return resp.json();
    },
    staleTime: 5 * 60_000,
    retry: false,
  });
  const erpSource = useProjectionSource("erp-cn");

  const buyPoints = useMemo(() => {
    const card = fundingQuery.data?.cards?.find((c) => c.id === "cn-margin-buy-share-a-stocks");
    return card?.points ?? [];
  }, [fundingQuery.data]);

  const balancePoints = useMemo(() => {
    const s = ratesQuery.data?.series.margin_rzyezb;
    if (!s || s.dates.length !== s.values.length) return [];
    return s.dates.map((date, idx) => ({ date, value: s.values[idx] ?? null }));
  }, [ratesQuery.data]);

  const totalYiByDate = useMemo(() => {
    const s = ratesQuery.data?.series.margin_rzrqye;
    if (!s || s.dates.length !== s.values.length) return new Map<string, number>();
    return new Map(
      s.dates.flatMap((d, i) => (exists(s.values[i]) ? [[d, s.values[i]]] : [])),
    );
  }, [ratesQuery.data]);

  const activePoints = tab === "buy" ? buyPoints : balancePoints;
  const activeId = tab === "buy" ? "cn-margin-buy" : "cn-margin-balance";
  const thresholds = useMemo(
    () => buildMetricThresholds(activeId, activePoints),
    [activeId, activePoints],
  );

  const priceSeries = pricesQuery.data?.series[priceKey] ?? { dates: [], values: [] };
  const view = useMemo(
    () => alignProjection(priceSeries, activePoints, "daily", years),
    [priceSeries, activePoints, years],
  );

  const fullPricePoints = useMemo(
    () =>
      priceSeries.dates.length === priceSeries.values.length
        ? priceSeries.dates.map((date, idx) => ({ date, value: priceSeries.values[idx] ?? null }))
        : [],
    [priceSeries],
  );

  const comboEval = useMemo(() => {
    return evaluateMetricComboScreener({
      id: activeId,
      frequency: "daily",
      dates: view.dates,
      prices: view.price,
      fullPricePoints,
      metricValues: view.values,
      fullMetricPoints: activePoints,
      breadthPoints: breadthQuery.data?.history ?? [],
      erpBands: erpSource.bands ?? [],
      marginRatioPoints: balancePoints,
      activeIds: activeRules,
    });
  }, [activeId, view, fullPricePoints, activePoints, breadthQuery.data, erpSource.bands, balancePoints, activeRules]);

  useEffect(() => {
    setCursorIdx(null);
    setSelectedEpId("");
    setZoomPct(null);
  }, [tab, priceKey, years]);

  const cleanActive = useMemo(() => cleanDatedPoints(activePoints), [activePoints]);
  const latest = cleanActive[cleanActive.length - 1];
  const liveBuy = cnObsQuery.data?.items.find((i) => i.metric_id === "margin_buy");

  const inspectIdx = cursorIdx != null && cursorIdx >= 0 && cursorIdx < view.dates.length
    ? cursorIdx
    : view.dates.length - 1;
  const inspectDate = inspectIdx >= 0 ? view.dates[inspectIdx] : latest?.date ?? null;
  const inspectMetricDate = inspectIdx >= 0 ? view.metricDates[inspectIdx] ?? inspectDate : latest?.date ?? null;
  const inspectValue = inspectIdx >= 0 ? view.values[inspectIdx] : latest?.value ?? null;
  const ctxAtInspect = inspectDate ? comboEval.contextByDate.get(inspectDate) : undefined;
  const inspectTotalYi = inspectMetricDate ? totalYiByDate.get(inspectMetricDate) : undefined;

  const chartRef = useRef<HTMLDivElement>(null);
  const chartInst = useRef<echarts.ECharts | null>(null);
  const enough = view.price.filter((v, i) => v !== null && view.values[i] !== null).length >= 2;
  const screeningActive = activeRules.size > 0;

  useEffect(() => {
    if (!chartRef.current || !enough || !thresholds) return;
    const chart = echarts.init(chartRef.current, undefined, { renderer: "svg" });
    chartInst.current = chart;

    const markLines = thresholds.fixedRails.map((rail) => ({
      yAxis: rail.value,
      lineStyle: { color: rail.color, width: 1.9, type: "dashed" as const },
      label: {
        formatter: rail.shortLabel,
        position: "insideEndTop" as const,
        color: rail.color,
        fontWeight: 600,
        backgroundColor: "rgba(255,255,255,0.92)",
        padding: [2, 4],
      },
    }));

    const dynamicLines = thresholds.dynamicSeries.map((dyn) => ({
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

    const metricLabel = tab === "buy" ? "融资买入占A股成交比" : "融资余额占流通市值比";
    const activeMarkArea = screeningActive && comboEval.markAreas.length
      ? { silent: true, itemStyle: { borderWidth: 0 }, data: comboEval.markAreas }
      : undefined;

    chart.setOption({
      animation: false,
      textStyle: { fontFamily: 'system-ui, -apple-system, "PingFang SC", sans-serif' },
      legend: {
        top: 0,
        left: 0,
        data: [PRICE_NAMES[priceKey], metricLabel, ...thresholds.dynamicSeries.map((d) => d.name)],
        textStyle: { fontSize: 12, color: "#344256" },
      },
      grid: [
        { left: 60, right: 36, top: 52, height: "44%" },
        { left: 60, right: 36, top: "69%", height: "19%" },
      ],
      title: [
        {
          text: `${PRICE_NAMES[priceKey]}（点）${screeningActive ? " · 已高亮所选组合命中区间" : ""}`,
          left: 0,
          top: 28,
          textStyle: { fontSize: 12.5, fontWeight: 600, color: "#243f63" },
        },
        {
          text: `${metricLabel}（%） · 含参考轨道`,
          left: 0,
          top: "63%",
          textStyle: { fontSize: 12.5, fontWeight: 600, color: "#173d68" },
        },
      ],
      axisPointer: { link: [{ xAxisIndex: [0, 1] }] },
      tooltip: {
        trigger: "axis",
        confine: true,
        axisPointer: { type: "cross" },
        formatter: (raw: unknown) => {
          const arr = Array.isArray(raw) ? raw : [raw];
          const i = Number((arr[0] as { dataIndex?: number })?.dataIndex);
          if (!Number.isInteger(i) || !view.dates[i]) return "—";
          const mDate = view.metricDates[i] ?? "";
          const dynRows = thresholds.dynamicSeries
            .map((d) => `${d.name}：${fmt(mDate ? d.byDate.get(mDate) : null)}%`)
            .join(" · ");
          const yi = mDate ? totalYiByDate.get(mDate) : undefined;
          const ctx = comboEval.contextByDate.get(view.dates[i]);
          return [
            `<b>${view.dates[i]}</b>`,
            `${PRICE_NAMES[priceKey]}：${fmt(view.price[i])}`,
            `${metricLabel}：<b>${fmt(view.values[i])}%</b>`,
            dynRows,
            exists(ctx?.b50) ? `全A 50日宽度：${ctx.b50.toFixed(1)}%` : "",
            yi != null ? `两融总余额：${(yi / 10000).toFixed(2)}万亿` : "",
          ]
            .filter(Boolean)
            .join("<br/>");
        },
      },
      xAxis: [0, 1].map((index) => ({
        type: "category",
        gridIndex: index,
        data: view.dates,
        boundaryGap: false,
        axisLabel: {
          show: index === 1,
          hideOverlap: true,
          showMinLabel: true,
          showMaxLabel: true,
          color: "#64748b",
          formatter: (d: string) => (view.dates.length < 180 ? d.slice(5) : d.slice(0, 7)),
        },
      })),
      yAxis: [0, 1].map((index) => ({
        type: "value",
        gridIndex: index,
        scale: true,
        splitNumber: 3,
        min: ({ min, max }: { min: number; max: number }) => {
          const railVals = index === 1 ? thresholds.fixedRails.map((r) => r.value) : [];
          const lo = railVals.length ? Math.min(min, ...railVals) : min;
          const hi = railVals.length ? Math.max(max, ...railVals) : max;
          if (!Number.isFinite(lo) || !Number.isFinite(hi)) return undefined;
          const raw = lo - Math.max(hi - lo, 0.05) * 0.1;
          return index === 0 ? Math.floor(raw) : raw;
        },
        max: ({ min, max }: { min: number; max: number }) => {
          const railVals = index === 1 ? thresholds.fixedRails.map((r) => r.value) : [];
          const lo = railVals.length ? Math.min(min, ...railVals) : min;
          const hi = railVals.length ? Math.max(max, ...railVals) : max;
          if (!Number.isFinite(lo) || !Number.isFinite(hi)) return undefined;
          const raw = hi + Math.max(hi - lo, 0.05) * 0.12;
          return index === 0 ? Math.ceil(raw) : raw;
        },
        axisLabel: {
          color: "#64748b",
          formatter: (v: number) => (index === 1 ? `${v.toFixed(1)}%` : Math.round(v).toLocaleString("zh-CN")),
        },
        splitLine: { lineStyle: { color: "#e2e8ef" } },
      })),
      dataZoom: [
        { type: "inside", xAxisIndex: [0, 1], filterMode: "filter" },
        { type: "slider", xAxisIndex: [0, 1], filterMode: "filter", bottom: 4, height: 20, showDetail: false },
      ],
      series: [
        {
          name: PRICE_NAMES[priceKey],
          type: "line",
          xAxisIndex: 0,
          yAxisIndex: 0,
          data: view.price,
          connectNulls: false,
          showSymbol: false,
          lineStyle: { color: "#243d61", width: 2.6 },
          itemStyle: { color: "#243d61" },
          markArea: activeMarkArea,
        },
        {
          name: metricLabel,
          type: "line",
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: view.values,
          connectNulls: false,
          showSymbol: false,
          lineStyle: { color: "#2f6b8a", width: 2.4 },
          itemStyle: { color: "#2f6b8a" },
          markLine: markLines.length ? { silent: true, symbol: "none", data: markLines } : undefined,
          markArea: activeMarkArea,
        },
        ...dynamicLines,
      ],
    });

    chart.on("updateAxisPointer", (ev: unknown) => {
      const idx = (ev as { dataIndex?: number; axesInfo?: { value?: number }[] }).dataIndex
        ?? (ev as { axesInfo?: { value?: number }[] }).axesInfo?.[0]?.value;
      if (typeof idx === "number" && idx >= 0 && idx < view.dates.length) {
        setCursorIdx(idx);
      }
    });

    const resize = new ResizeObserver(() => chart.resize());
    resize.observe(chartRef.current);
    return () => {
      resize.disconnect();
      chart.dispose();
      chartInst.current = null;
    };
  }, [view, priceKey, tab, enough, thresholds, totalYiByDate, screeningActive, comboEval.markAreas, comboEval.contextByDate]);

  useEffect(() => {
    if (!zoomPct || !chartInst.current) return;
    chartInst.current.dispatchAction({
      type: "dataZoom",
      dataZoomIndex: 0,
      start: zoomPct.start,
      end: zoomPct.end,
    });
  }, [zoomPct]);

  const toggleRule = (id: string) => {
    setSelectedEpId("");
    setActiveRules((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleSelectEpisode = (ep: ScreenedEpisode) => {
    setSelectedEpId(ep.id);
    setCursorIdx(ep.startIndex);
    const total = Math.max(1, view.dates.length - 1);
    let sPct = Math.max(0, ((ep.startIndex - 30) / total) * 100);
    let ePct = Math.min(100, ((ep.endIndex + 60) / total) * 100);
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

  const windows = tab === "buy" ? BUY_WINDOWS : BAL_WINDOWS;
  const loading =
    pricesQuery.isPending || (tab === "buy" ? fundingQuery.isPending : ratesQuery.isPending);

  return (
    <div className="op-metric">
      <div className="op-toolbar" role="group" aria-label="两融维度、对照股指与期间切换">
        <div className="op-seg-group op-seg-pillbox" role="group" aria-label="两融观察维度">
          <button
            type="button"
            aria-pressed={tab === "buy"}
            onClick={() => {
              setTab("buy");
              setYears(1);
              setActiveRules(new Set());
            }}
          >
            融资买入占比（交易热度）
          </button>
          <button
            type="button"
            aria-pressed={tab === "balance"}
            onClick={() => {
              setTab("balance");
              setYears(5);
              setActiveRules(new Set());
            }}
          >
            融资余额占比（存量水位）
          </button>
        </div>

        <div className="op-seg-group op-seg-pillbox" role="group" aria-label="对照股指">
          <button type="button" aria-pressed={priceKey === "sse"} onClick={() => setPriceKey("sse")}>
            上证指数
          </button>
          <button type="button" aria-pressed={priceKey === "hs300"} onClick={() => setPriceKey("hs300")}>
            沪深300
          </button>
        </div>

        <div className="op-seg-group" style={{ marginLeft: "auto" }} role="group" aria-label="对照期间">
          {windows.map((w) => (
            <button
              type="button"
              key={w.label}
              aria-pressed={years === w.years}
              onClick={() => setYears(w.years)}
            >
              {w.label}
            </button>
          ))}
        </div>
      </div>

      <div className="op-spec-box" aria-label="两融联立读数与阈值口径">
        <div className="op-spec-row">
          <strong>{inspectDate ?? "—"} 读数：</strong>
          <span>
            {tab === "buy" ? "融资买入占比" : "融资余额占比"} <b>{fmt(inspectValue)}%</b>
            {tab === "balance" && exists(ctxAtInspect?.marginPercentile)
              ? ` (3年P${Math.round(ctxAtInspect.marginPercentile)})`
              : ""}
          </span>
          {thresholds?.dynamicSeries.map((dyn) => {
            const val = inspectMetricDate ? dyn.byDate.get(inspectMetricDate) : dyn.latest;
            return (
              <span key={dyn.key}>
                {dyn.shortLabelPrefix} <b>{fmt(val)}%</b>
              </span>
            );
          })}
          {tab === "buy" && exists(ctxAtInspect?.marginRatio) && (
            <span>
              存量占比 <b>{ctxAtInspect.marginRatio.toFixed(2)}%</b>
              {exists(ctxAtInspect?.marginPercentile) ? ` (P${Math.round(ctxAtInspect.marginPercentile)})` : ""}
            </span>
          )}
          {tab === "buy" && typeof liveBuy?.value === "number" && !cursorIdx && (
            <span>
              日买入 <b>{Math.round(liveBuy.value)}亿</b>
            </span>
          )}
          {tab === "balance" && inspectTotalYi != null && (
            <span>
              两融余额 <b>{(inspectTotalYi / 10000).toFixed(2)}万亿</b>
            </span>
          )}
          {exists(ctxAtInspect?.b50) && (
            <span>
              全A 50日宽度 <b>{ctxAtInspect.b50.toFixed(1)}%</b>
            </span>
          )}
          {exists(ctxAtInspect?.erpValue) && (
            <span>
              股债利差 <b>{ctxAtInspect.erpValue.toFixed(2)}pp</b>
              {exists(ctxAtInspect?.erpZ) ? ` (${ctxAtInspect.erpZ >= 0 ? "+" : ""}${ctxAtInspect.erpZ.toFixed(2)}σ)` : ""}
            </span>
          )}
          {cursorIdx != null && (
            <button type="button" className="op-spec-reset" onClick={() => setCursorIdx(null)}>
              回最新日
            </button>
          )}
        </div>
        <div className="op-spec-row op-spec-muted">
          {tab === "buy" ? (
            <span>
              <b>官方同池口径</b>（剔除ETF）：6.5% 偏冷冰点(≈P5) / 10.5% 追涨拥挤(≈P95) ｜ 跌破偏冷后配宽度回暖看右侧买点，冲破10.5%配宽度转弱防追高
            </span>
          ) : (
            <span>
              <b>滚动3年(756日)动态轨</b>：P15 存量出清 / P50 中枢 / P85 存量偏重 ｜ 低杠杆配高ERP与宽度回升看大底，高于P85配宽度破位防负反馈减仓
            </span>
          )}
        </div>
      </div>

      <MetricComboWorkbench
        evaluation={comboEval}
        priceName={PRICE_NAMES[priceKey]}
        frequency="daily"
        latestDate={view.dates[view.dates.length - 1] ?? latest?.date}
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

      {loading ? (
        <p role="status">价格与两融历史读取中…</p>
      ) : enough ? (
        <div
          ref={chartRef}
          className="op-chart"
          role="img"
          aria-label={`${PRICE_NAMES[priceKey]}与${tab === "buy" ? "融资买入占比" : "融资余额占比"}同日联动投影图（含参考阈值轨道）`}
        />
      ) : (
        <p className="op-empty">所选窗口内共同历史点数不足。</p>
      )}

      {thresholds && (
        <details className="op-source" style={{ marginTop: 8 }}>
          <summary>阈值专业依据与实战仓位用法</summary>
          <p>{thresholds.rationale}</p>
          <p>{thresholds.sizingGuide}</p>
        </details>
      )}
    </div>
  );
}
