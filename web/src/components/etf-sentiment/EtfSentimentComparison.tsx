import { useEffect, useMemo, useRef, useState } from "react";
import * as echarts from "echarts";
import { referenceLabel } from "./metricReading";
import "./etf-sentiment.css";

type CatalogEntry = {
  symbol: string;
  name: string;
  category: string;
  sectorName: string;
  status: "available" | "unavailable";
  reason?: string;
  dataFile: string;
};

type Catalog = {
  schemaVersion: number;
  generatedAt: string;
  defaultSymbol: string;
  notes: string[];
  etfs: CatalogEntry[];
};

type Metric = {
  id: string;
  label: string;
  unit: string;
  description: string;
  sourceLabel: string;
  asOf: string | null;
  availableFrom: string | null;
  availableTo: string | null;
  qualityNote: string;
  values: (number | null)[];
  scaleMin?: number;
  scaleMax?: number;
  referenceLines?: { value: number; label: string }[];
};

type Snapshot = {
  symbol: string;
  name: string;
  priceLabel: string;
  snapshotAt: string;
  mappingNote: string;
  priceSource: { provider: string; asOf: string; adjustment: string; note: string };
  sector: { code: string; name: string; kind: string };
  dates: string[];
  close: (number | null)[];
  metrics: Metric[];
  notes: string[];
};

type Range = "1y" | "3y" | "all";

type OverviewState = "hot" | "cold" | "normal" | "unverified" | "stale" | "missing";
type OverviewItem = {
  symbol: string;
  name: string;
  sectorName: string;
  state: OverviewState;
  heat: number | null;
  asOf: string | null;
  reason: string | null;
  sourceLabel: string;
  sourceUrl: string;
  dataFile?: string;
};
type Overview = {
  schemaVersion: 1;
  asOf: string;
  title: string;
  sourceLabel: string;
  sourceUrl: string;
  notice: string | null;
  items: OverviewItem[];
};

const CATALOG_URL = "/data/sector-etf-sentiment/catalog.json";
const OVERVIEW_URL = "/data/sector-etf-sentiment/overview.json";
const OVERVIEW_GROUPS: { key: string; label: string; states: OverviewState[] }[] = [
  { key: "hot", label: "交易偏热", states: ["hot"] },
  { key: "cold", label: "交易偏冷", states: ["cold"] },
  { key: "normal", label: "交易常态", states: ["normal"] },
  { key: "unqualified", label: "待核验", states: ["unverified", "stale", "missing"] },
];
const STATE_LABELS: Record<OverviewState, string> = {
  hot: "交易偏热", cold: "交易偏冷", normal: "交易常态",
  unverified: "待核验", stale: "资料过期", missing: "缺少资料",
};

function valid(value: number | null | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function latest(values: (number | null)[], dates: string[]) {
  for (let i = Math.min(values.length, dates.length) - 1; i >= 0; i -= 1) {
    if (valid(values[i])) return { index: i, date: dates[i], value: values[i] as number };
  }
  return null;
}

function display(value: number | null | undefined, unit: string) {
  if (!valid(value)) return "无数据";
  const digits = unit === "元" ? 3 : Math.abs(value) < 10 ? 2 : 1;
  return `${value.toLocaleString("zh-CN", { maximumFractionDigits: digits })}${unit ? ` ${unit}` : ""}`;
}

function escapeHtml(value: string) {
  return value.replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char] ?? char);
}

function startForRange(dates: string[], range: Range): number {
  if (!dates.length || range === "all") return 0;
  const last = new Date(`${dates[dates.length - 1]}T00:00:00`);
  const threshold = new Date(last);
  threshold.setFullYear(threshold.getFullYear() - (range === "1y" ? 1 : 3));
  const index = dates.findIndex((date) => new Date(`${date}T00:00:00`) >= threshold);
  return index < 0 ? 0 : index;
}

function normalizeSnapshot(raw: Snapshot): Snapshot {
  if (!Array.isArray(raw.dates) || !Array.isArray(raw.close) || raw.close.length !== raw.dates.length || !Array.isArray(raw.metrics)) {
    throw new Error("快照日期与价格列长度不一致");
  }
  if (raw.metrics.some((metric) => !Array.isArray(metric.values) || metric.values.length !== raw.dates.length)) {
    throw new Error("快照指标列与日期长度不一致");
  }
  return raw;
}

function Chart({ snapshot, metric, range, onHover }: {
  snapshot: Snapshot;
  metric: Metric;
  range: Range;
  onHover: (index: number | null) => void;
}) {
  const node = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);
  const hoverCallback = useRef(onHover);
  hoverCallback.current = onHover;

  useEffect(() => {
    if (!node.current) return;
    const instance = echarts.init(node.current, undefined, { renderer: "canvas" });
    chart.current = instance;
    const observer = new ResizeObserver(() => instance.resize());
    observer.observe(node.current);
    const pointer = (params: unknown) => {
      const axes = (params as { axesInfo?: { value?: string | number }[] }).axesInfo;
      const value = axes?.[0]?.value;
      const index = typeof value === "number" ? value : snapshot.dates.indexOf(String(value));
      hoverCallback.current(Number.isInteger(index) && index >= 0 && index < snapshot.dates.length ? index : null);
    };
    instance.on("updateAxisPointer", pointer);
    const leave = () => hoverCallback.current(null);
    instance.getZr().on("globalout", leave);
    return () => {
      observer.disconnect();
      instance.off("updateAxisPointer", pointer);
      instance.getZr().off("globalout", leave);
      instance.dispose();
      chart.current = null;
    };
  }, [snapshot.dates]);

  useEffect(() => {
    const instance = chart.current;
    if (!instance) return;
    const dates = snapshot.dates;
    const first = startForRange(dates, range);
    const reference = (metric.referenceLines ?? []).filter((line) => Number.isFinite(line.value));
    const tooltip = (params: unknown) => {
      const points = params as { dataIndex?: number }[];
      const index = points?.[0]?.dataIndex;
      if (index == null || index < 0 || index >= dates.length) return "";
      const date = escapeHtml(dates[index]);
      return `<div class="es-tooltip"><strong>${date}</strong><div><i class="es-dot es-price-dot"></i>${escapeHtml(snapshot.name)}：${escapeHtml(display(snapshot.close[index], "元"))}</div><div><i class="es-dot es-metric-dot"></i>${escapeHtml(metric.label)}：${escapeHtml(display(metric.values[index], metric.unit))}</div></div>`;
    };
    const option: echarts.EChartsOption = {
      animation: false,
      backgroundColor: "transparent",
      color: ["#2563a6", "#bf7c24"],
      grid: [
        { left: 62, right: 44, top: "8%", height: "43%", containLabel: false },
        { left: 62, right: 44, top: "59%", height: "25%", containLabel: false },
      ],
      tooltip: { trigger: "axis", axisPointer: { type: "cross", snap: true }, formatter: tooltip, confine: true },
      axisPointer: { link: [{ xAxisIndex: [0, 1] }], label: { backgroundColor: "#60758a" } },
      xAxis: [
        { type: "category", gridIndex: 0, data: dates, boundaryGap: false, axisLabel: { show: false }, axisTick: { show: false }, axisLine: { lineStyle: { color: "#c8d4df" } }, axisPointer: { show: true } },
        { type: "category", gridIndex: 1, data: dates, boundaryGap: false, axisLabel: { color: "#728396", fontSize: 11, hideOverlap: true }, axisLine: { lineStyle: { color: "#c8d4df" } }, axisPointer: { show: true } },
      ],
      yAxis: [
        { type: "value", gridIndex: 0, scale: true, name: "ETF 收盘价 · 元", nameTextStyle: { color: "#65798d", fontSize: 11 }, axisLabel: { color: "#65798d" }, splitLine: { lineStyle: { color: "#edf1f5" } } },
        { type: "value", gridIndex: 1, scale: metric.scaleMin == null && metric.scaleMax == null, min: metric.scaleMin, max: metric.scaleMax, name: `${metric.label}${metric.unit ? ` · ${metric.unit}` : ""}`, nameTextStyle: { color: "#8c6938", fontSize: 11 }, axisLabel: { color: "#8c6938" }, splitLine: { lineStyle: { color: "#f3efe9" } } },
      ],
      dataZoom: [
        { type: "inside", xAxisIndex: [0, 1], startValue: dates[first], endValue: dates[dates.length - 1], zoomOnMouseWheel: "shift", moveOnMouseWheel: false },
        { type: "slider", xAxisIndex: [0, 1], startValue: dates[first], endValue: dates[dates.length - 1], bottom: 12, height: 18, showDetail: false, borderColor: "#dce4eb", fillerColor: "rgba(67, 113, 160, .13)", handleStyle: { color: "#557ca7" } },
      ],
      series: [
        { type: "line", name: snapshot.priceLabel, xAxisIndex: 0, yAxisIndex: 0, data: snapshot.close, connectNulls: false, showSymbol: false, lineStyle: { width: 2.1, color: "#2563a6" }, itemStyle: { color: "#2563a6" }, emphasis: { focus: "series" } },
        { type: "line", name: metric.label, xAxisIndex: 1, yAxisIndex: 1, data: metric.values, connectNulls: false, showSymbol: false, step: metric.id === "legacy_alarm" ? "end" : false, lineStyle: { width: 2, color: "#bf7c24" }, itemStyle: { color: "#bf7c24" }, emphasis: { focus: "series" },
          markLine: reference.length ? { silent: true, symbol: "none", lineStyle: { color: "#a0aab4", type: "dashed", width: 1 }, label: { position: "insideEndTop", color: "#697887", fontSize: 12, formatter: (item: { name?: string }) => item.name ?? "参考" }, data: reference.map((line) => ({ yAxis: line.value, name: metric.id === "etf_activity_pct" && line.value === 15 ? "交易偏冷参考 · 15" : referenceLabel(metric.id, line.value, line.label) })) } : undefined,
        },
      ],
    };
    instance.setOption(option, true);
  }, [snapshot, metric, range]);

  return <div ref={node} className="es-chart" role="img" aria-label={`${snapshot.name}收盘价与${metric.label}按同一日期排列的上下双图`} />;
}

export default function EtfSentimentComparison() {
  const chartSectionRef = useRef<HTMLDivElement>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [overviewError, setOverviewError] = useState<string | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(true);
  const [overviewRetry, setOverviewRetry] = useState(0);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [catalogRetry, setCatalogRetry] = useState(0);
  const [category, setCategory] = useState("全部");
  const [symbol, setSymbol] = useState("512480.SS");
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [dataError, setDataError] = useState<string | null>(null);
  const [dataLoading, setDataLoading] = useState(false);
  const [dataRetry, setDataRetry] = useState(0);
  const [metricId, setMetricId] = useState("etf_activity_pct");
  const [range, setRange] = useState<Range>("1y");
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  useEffect(() => {
    const abort = new AbortController();
    setOverviewLoading(true);
    setOverviewError(null);
    fetch(OVERVIEW_URL, { signal: abort.signal, cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error(`总览请求失败（${response.status}）`);
        const result = await response.json() as Overview;
        const validStates = new Set<OverviewState>(["hot", "cold", "normal", "unverified", "stale", "missing"]);
        if (result.schemaVersion !== 1 || !Array.isArray(result.items)
          || result.items.some((item) => !item.symbol || !validStates.has(item.state))) throw new Error("总览格式暂不可用");
        return result;
      })
      .then((result) => { if (!abort.signal.aborted) setOverview(result); })
      .catch((error: unknown) => {
        if (!abort.signal.aborted) { setOverview(null); setOverviewError(error instanceof Error ? error.message : "总览加载失败"); }
      })
      .finally(() => { if (!abort.signal.aborted) setOverviewLoading(false); });
    return () => abort.abort();
  }, [overviewRetry]);

  useEffect(() => {
    const abort = new AbortController();
    setCatalogLoading(true);
    setCatalogError(null);
    fetch(CATALOG_URL, { signal: abort.signal, cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error(`目录请求失败（${response.status}）`);
        const result = await response.json() as Catalog;
        if (result.schemaVersion !== 1 || !Array.isArray(result.etfs)) throw new Error("目录格式暂不可用");
        return result;
      })
      .then((result) => {
        if (abort.signal.aborted) return;
        setCatalog(result);
        const preferred = result.etfs.find((item) => item.symbol === "512480.SS" && item.status === "available")
          ?? result.etfs.find((item) => item.symbol === result.defaultSymbol && item.status === "available")
          ?? result.etfs.find((item) => item.status === "available");
        if (preferred) setSymbol((current) => result.etfs.some((item) => item.symbol === current && item.status === "available") ? current : preferred.symbol);
      })
      .catch((error: unknown) => { if (!abort.signal.aborted) setCatalogError(error instanceof Error ? error.message : "目录加载失败"); })
      .finally(() => { if (!abort.signal.aborted) setCatalogLoading(false); });
    return () => abort.abort();
  }, [catalogRetry]);

  const selected = catalog?.etfs.find((item) => item.symbol === symbol) ?? null;
  const overviewSelected = overview?.items.find((item) => item.symbol === symbol);
  const selectedDataFile = overviewSelected?.dataFile || selected?.dataFile;
  const categories = useMemo(() => ["全部", ...new Set((catalog?.etfs ?? []).map((item) => item.category))], [catalog]);
  const choices = (catalog?.etfs ?? []).filter((item) => category === "全部" || item.category === category);

  useEffect(() => {
    if (!selected || (selected.status !== "available" && !overviewSelected?.dataFile) || !selectedDataFile) {
      setSnapshot(null);
      setDataError(selected?.reason ?? null);
      setDataLoading(false);
      return;
    }
    const abort = new AbortController();
    setSnapshot(null);
    setHoverIndex(null);
    setDataError(null);
    setDataLoading(true);
    fetch(selectedDataFile, { signal: abort.signal, cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error(`快照请求失败（${response.status}）`);
        const result = normalizeSnapshot(await response.json() as Snapshot);
        if (result.symbol !== selected.symbol) throw new Error("快照标的与目录不一致");
        return result;
      })
      .then((result) => {
        if (abort.signal.aborted) return;
        setSnapshot(result);
        setMetricId((previous) => {
          const available = result.metrics.filter((metric) => metric.values.some(valid));
          return available.find((metric) => metric.id === previous)?.id
            ?? available.find((metric) => metric.id === "etf_activity_pct")?.id
            ?? available[0]?.id ?? "";
        });
      })
      .catch((error: unknown) => { if (!abort.signal.aborted) setDataError(error instanceof Error ? error.message : "快照加载失败"); })
      .finally(() => { if (!abort.signal.aborted) setDataLoading(false); });
    return () => abort.abort();
  }, [selected?.symbol, selectedDataFile, selected?.status, selected?.reason, dataRetry]);

  const availableMetrics = snapshot?.metrics.filter((metric) => metric.values.some(valid)) ?? [];
  const metric = availableMetrics.find((item) => item.id === metricId) ?? availableMetrics[0] ?? null;
  const latestPrice = snapshot ? latest(snapshot.close, snapshot.dates) : null;
  const latestMetric = snapshot && metric ? latest(metric.values, snapshot.dates) : null;
  const readingDate = hoverIndex != null ? snapshot?.dates[hoverIndex] : null;
  const readingPrice = hoverIndex != null ? snapshot?.close[hoverIndex] : latestPrice?.value;
  const readingMetric = hoverIndex != null ? metric?.values[hoverIndex] : latestMetric?.value;
  const overlap = snapshot && metric ? snapshot.dates.some((_, i) => valid(snapshot.close[i]) && valid(metric.values[i])) : false;
  const metricInRange = snapshot && metric ? metric.values.some((value, i) => i >= startForRange(snapshot.dates, range) && valid(value)) : false;
  const qualifiedCount = overview?.items.filter((item) => item.state === "hot" || item.state === "cold" || item.state === "normal").length ?? 0;

  function selectFromOverview(item: OverviewItem) {
    setCategory("全部");
    setSymbol(item.symbol);
    setMetricId("etf_activity_pct");
    setHoverIndex(null);
    requestAnimationFrame(() => chartSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
  }

  return <section className="es-panel" aria-label="ETF价格与行业情绪对照">
    <section className="es-overview" aria-label="行业 ETF 冷热总览">
      <div className="es-overview-head"><div><h2>行业 ETF 冷热总览</h2><p>按 ETF 自身交易活跃度展示；点选后查看价格与热度走势。</p></div>
        {overview && <span className="es-overview-date">资料截至 {overview.asOf}</span>}</div>
      {overviewLoading && <p className="es-status" role="status">总览加载中…</p>}
      {overviewError && <div className="es-status es-error" role="alert">{overviewError}<button type="button" onClick={() => setOverviewRetry((n) => n + 1)}>重试</button></div>}
      {overview && <>
        <div className="es-overview-groups">{OVERVIEW_GROUPS.map((group) => {
          const items = overview.items.filter((item) => group.states.includes(item.state))
            .sort((a, b) => group.key === "cold" ? (a.heat ?? 0) - (b.heat ?? 0) : (b.heat ?? 0) - (a.heat ?? 0));
          const count = qualifiedCount === 0 && group.key !== "unqualified" ? "—" : String(items.length);
          return <div className={`es-overview-group es-overview-${group.key}`} key={group.key}>
            <h3>{group.label}<span>{count}</span></h3>
            <div className="es-overview-items">{items.length ? items.map((item) => {
              const available = Boolean(item.dataFile) || (catalog?.etfs.some((entry) => entry.symbol === item.symbol && entry.status === "available") ?? false);
              return <button type="button" key={item.symbol} className="es-overview-item"
                onClick={() => selectFromOverview(item)} aria-label={`查看${item.name}价格与热度走势`}>
                <span className="es-overview-item-main"><strong>{item.name}</strong><small>{item.symbol.split(".")[0]} · {item.sectorName}</small></span>
                <span className="es-overview-item-value">{valid(item.heat) && group.key !== "unqualified" ? `${display(item.heat, "分位")}` : STATE_LABELS[item.state]}{item.asOf && item.asOf !== overview.asOf && <small>{item.asOf}</small>}</span>
                {!available && catalog && <span className="es-overview-item-reason">走势图暂无资料</span>}
                {item.reason && <span className="es-overview-item-reason">{item.reason}</span>}
              </button>;
            }) : <p className="es-overview-empty">{group.key === "unqualified" ? "全部已核验" : qualifiedCount === 0 ? "尚无合格读数" : "暂无"}</p>}</div>
          </div>;
        })}</div>
        <p className="es-overview-source">{overview.notice && <span>{overview.notice} · </span>}来源：{overview.sourceUrl ? <a href={overview.sourceUrl} target="_blank" rel="noreferrer">{overview.sourceLabel}</a> : overview.sourceLabel}；历史位置仅描述交易活跃度，不代表买卖信号。</p>
      </>}
    </section>
    <div className="es-heading" ref={chartSectionRef}><div><h2>价格与热度走势</h2></div><p>上图 ETF 价格，下图所选指标；日期和缩放同步。</p></div>
    {catalogLoading && <p className="es-status" role="status">ETF 目录加载中…</p>}
    {catalogError && <div className="es-status es-error" role="alert">{catalogError}<button type="button" onClick={() => setCatalogRetry((n) => n + 1)}>重试</button></div>}
    {catalog && <>
      <div className="es-controls">
        <div className="es-categories" role="group" aria-label="ETF分类">{categories.map((item) => <button key={item} type="button" className={category === item ? "active" : ""} aria-pressed={category === item} onClick={() => {
          setCategory(item);
          const first = catalog.etfs.find((etf) => (item === "全部" || etf.category === item) && etf.status === "available")
            ?? catalog.etfs.find((etf) => item === "全部" || etf.category === item);
          if (first && !catalog.etfs.some((etf) => etf.symbol === symbol && (item === "全部" || etf.category === item))) setSymbol(first.symbol);
        }}>{item}</button>)}</div>
        <label className="es-select-label">ETF
          <select value={choices.some((item) => item.symbol === symbol) ? symbol : ""} onChange={(event) => setSymbol(event.target.value)}>
            {!choices.some((item) => item.symbol === symbol) && <option value="">选择 ETF</option>}
            {choices.map((item) => <option key={item.symbol} value={item.symbol}>{item.name} · {item.symbol}{item.status === "unavailable" ? "（暂无数据）" : ""}</option>)}
          </select>
        </label>
        <label className="es-select-label">观察指标
          <select value={metric?.id ?? ""} onChange={(event) => { setMetricId(event.target.value); setHoverIndex(null); }} disabled={!availableMetrics.length}>
            {!availableMetrics.length && <option value="">暂无可用指标</option>}
            {snapshot && [true, false].map((own) => {
              const items = snapshot.metrics.filter((item) => item.id.startsWith("etf_") === own);
              return items.length ? <optgroup key={String(own)} label={own ? "ETF自身指标" : "行业历史参考"}>{items.map((item) => <option key={item.id} value={item.id} disabled={!item.values.some(valid)}>{item.label}{!item.values.some(valid) ? "（无同日资料）" : ""}</option>)}</optgroup> : null;
            })}
          </select>
        </label>
        <div className="es-ranges" role="group" aria-label="日期范围">{(["1y", "3y", "all"] as const).map((item) => <button key={item} type="button" aria-pressed={range === item} className={range === item ? "active" : ""} onClick={() => setRange(item)}>{item === "1y" ? "1 年" : item === "3y" ? "3 年" : "全部"}</button>)}</div>
      </div>
      {dataLoading && <p className="es-status" role="status">{selected?.name}快照加载中…</p>}
      {dataError && <div className="es-status es-error" role="alert">{selected?.name}：{dataError}{selected?.status === "available" && <button type="button" onClick={() => setDataRetry((n) => n + 1)}>重试</button>}</div>}
      {snapshot && <>
        {overviewSelected?.state === "unverified" && <p className="es-range-empty">权威历史行情待核验，以下为{snapshot.priceSource.provider}参考。</p>}
        <div className="es-current" aria-live="polite">
          <div><span className="es-current-label">{hoverIndex != null ? "光标日期" : "ETF 最新收盘"}</span><strong>{display(readingPrice, "元")}</strong><small>{readingDate ?? latestPrice?.date ?? "无价格日期"}</small></div>
          <div><span className="es-current-label">{metric?.label ?? "情绪指标"}</span><strong>{metric ? display(readingMetric, metric.unit) : "无数据"}</strong><small>{readingDate ?? latestMetric?.date ?? "该指标无有效日期"}</small></div>
        </div>
        <div className="es-plot-labels"><span>上图 · {snapshot.priceLabel}（元，{snapshot.priceSource.adjustment}）</span><span>下图 · {metric?.label ?? "指标无数据"}{metric?.unit ? `（${metric.unit}）` : ""}</span></div>
        {metric && !metricInRange && <p className="es-range-empty">所选范围内没有该指标的有效值。<button type="button" onClick={() => setRange("all")}>查看全部历史</button></p>}
        {metric && snapshot.dates.length > 1 ? <Chart key={snapshot.symbol} snapshot={snapshot} metric={metric} range={range} onHover={setHoverIndex} /> : <p className="es-status">暂无足够的双图数据。</p>}
        {metric && !overlap && <p className="es-status">价格和所选指标没有同日有效值，当前无法直接对照。</p>}
        {metric && !metric.id.startsWith("etf_") && <p className="es-mapping">{snapshot.mappingNote}</p>}
        <p className="es-provenance">价格：{snapshot.priceSource.provider}，截至 {snapshot.priceSource.asOf}；指标：{metric?.sourceLabel ?? "无"}，截至 {metric?.asOf ?? "未记录"}。{overviewSelected?.sourceUrl && <> <a href={overviewSelected.sourceUrl} target="_blank" rel="noreferrer">行情来源</a>。</>} {snapshot.priceSource.adjustment === "交易所原始报价" && "价格包含除息、折算的影响。"}</p>
      </>}
    </>}
  </section>;
}
