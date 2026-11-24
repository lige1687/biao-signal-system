import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import * as echarts from "echarts";
import { fundamentalsApi } from "../../api/client";
import BreadthComparison from "../market-style/BreadthComparison";
import { projectionReference } from "./projectionReference";
import { alignProjection } from "./projectionAlignment";
import ErpBandSummary from "./ErpBandSummary";
import ErpCrossChart from "./ErpCrossChart";
import { ERP_BAND_METHOD } from "./erpBands";
import { PROJECTION_METRICS, useProjectionSource } from "./projectionSources";
import { OBSERVATION_BY_ID, OBSERVATION_SECTIONS, observationReadingRank, observationSection } from "./catalog";
import "./projection.css";

type Market = "cn" | "us";
type Context = { windowDays: number; ruleIds: string[]; priceKey: string; fingerprint: string };
type PriceKey = "sse" | "hs300" | "sp500" | "nasdaq";
const PRICE_NAMES: Record<PriceKey, string> = { sse: "上证指数", hs300: "沪深300", sp500: "标普500", nasdaq: "纳斯达克综合指数" };
const WINDOWS = [{ years: 1, label: "1年" }, { years: 3, label: "3年" }, { years: 5, label: "5年" }, { years: 10, label: "10年" }, { years: null, label: "全部" }];
const EMPTY_PRICE = { dates: [] as string[], values: [] as (number | null)[] };
const fmt = (v: number | null, digits = 2) => v === null ? "缺值" : v.toLocaleString("zh-CN", { maximumFractionDigits: digits, minimumFractionDigits: digits });

function MetricProjection({ id, market }: { id: string; market: Market }) {
  const definition = PROJECTION_METRICS.find((item) => item.id === id)!;
  const [priceChoice, setPriceChoice] = useState<PriceKey>(market === "cn" ? "hs300" : "sp500");
  const priceKey = (market === "cn" ? ["sse", "hs300"] : ["sp500", "nasdaq"]).includes(priceChoice)
    ? priceChoice : market === "cn" ? "hs300" : "sp500";
  const [years, setYears] = useState<number | null>(id === "turnover-concentration" ? 10 : 5);
  const [variant, setVariant] = useState<"orth" | "raw">("orth");
  const source = useProjectionSource(id, variant);
  const usesReferencePrice = id === "erp-cn" && priceKey === "hs300";
  const frequency = source.frequency ?? definition.frequency;
  const prices = useQuery({ queryKey: ["fundOverlay", 20], queryFn: () => fundamentalsApi.overlayHistory(20),
    enabled: !usesReferencePrice, staleTime: 5 * 60_000, retry: false });
  const series = (usesReferencePrice ? source.referencePrice : prices.data?.series[priceKey]) ?? EMPTY_PRICE;
  const view = useMemo(() => alignProjection(series, source.points, frequency, years), [series, source.points, frequency, years]);
  const bandByDate = useMemo(() => new Map(source.bands?.map((p) => [p.date, p]) ?? []), [source.bands]);
  const viewBands = view.metricDates.map((date) => date ? bandByDate.get(date) : undefined);
  const lastPoint = source.points[source.points.length - 1];
  const reference = projectionReference(id);
  const zero = reference?.value ?? null;
  const node = useRef<HTMLDivElement>(null);
  const enough = view.price.filter((v, i) => v !== null && view.values[i] !== null).length >= 2;

  useEffect(() => {
    if (!node.current || !enough) return;
    const chart = echarts.init(node.current, undefined, { renderer: "svg" });
    const referenceLines = reference ? [{ yAxis: reference.value,
      lineStyle: { color: "#8190a2", type: "dotted" },
      label: { formatter: reference.label, position: "insideEndTop" } }] : [];
    const bounds = reference ? [reference.value] : [];
    chart.setOption({
      animation: false,
      textStyle: { fontFamily: 'system-ui, -apple-system, "PingFang SC", sans-serif' },
      grid: [{ left: 60, right: 32, top: 40, height: "31%" }, { left: 60, right: 32, top: "55%", height: "27%" }],
      title: [{ text: PRICE_NAMES[priceKey], left: 0, top: 2, textStyle: { fontSize: 12, fontWeight: 600, color: "#344256" } },
        { text: `${definition.label}（${source.unit}）`, left: 0, top: "46%", textStyle: { fontSize: 12, fontWeight: 600, color: "#436886" } }],
      tooltip: { trigger: "axis", confine: true, axisPointer: { type: "cross" }, formatter: (raw: unknown) => {
        const values = Array.isArray(raw) ? raw : [raw];
        const i = Number((values[0] as { dataIndex?: number })?.dataIndex);
        if (!Number.isInteger(i) || !view.dates[i]) return "—";
        const coverage = source.coverage?.[view.metricDates[i] ?? view.dates[i]];
        const band = viewBands[i];
        return `<b>${view.dates[i]}</b><br/>${PRICE_NAMES[priceKey]}：${fmt(view.price[i])}<br/>价格日：${view.priceDates[i] ?? "缺值"}<br/>${definition.label}：${fmt(view.values[i], 3)} ${source.unit}<br/>指标期：${view.metricDates[i] ?? "缺值"}${band ? `<br/>上轨：${fmt(band.upper)} · 中轨：${fmt(band.middle)} · 下轨：${fmt(band.lower)}<br/>历史位置：${fmt(band.z)}σ · 窗口有效观测：${band.n}` : ""}${coverage ? `<br/>有效 / 候选：${coverage.n} / ${coverage.universeN}只` : ""}`;
      } },
      axisPointer: { link: [{ xAxisIndex: [0, 1] }] },
      xAxis: [0, 1].map((index) => ({ type: "category", gridIndex: index, data: view.dates, boundaryGap: false,
        axisLabel: { show: index === 1, hideOverlap: true, showMinLabel: true, showMaxLabel: true, color: "#64748b", formatter: (date: string) => frequency !== "monthly" && view.dates.length < 80 ? date.slice(5) : date.slice(0, 7) } })),
      yAxis: [0, 1].map((index) => ({ type: "value", gridIndex: index, scale: true, splitNumber: 3,
        ...(index === 1 && bounds.length ? {
          min: ({ min, max }: { min: number; max: number }) => Math.min(min, ...bounds) - (Math.max(max, ...bounds) - Math.min(min, ...bounds)) * .08,
          max: ({ min, max }: { min: number; max: number }) => Math.max(max, ...bounds) + (Math.max(max, ...bounds) - Math.min(min, ...bounds)) * .08,
        } : {}),
        axisLabel: { color: "#64748b", formatter: (value: number) => Math.abs(value) >= 100000 ? `${(value / 10000).toFixed(0)}万` : `${Number(value.toFixed(2))}` },
        splitLine: { lineStyle: { color: "#e2e8ef" } } })),
      dataZoom: [{ type: "inside", xAxisIndex: [0, 1] }, { type: "slider", xAxisIndex: [0, 1], bottom: 4, height: 20, showDetail: false }],
      series: [
        { name: PRICE_NAMES[priceKey], type: "line", xAxisIndex: 0, yAxisIndex: 0, data: view.price, connectNulls: false, showSymbol: false,
          lineStyle: { color: "#243d61", width: 2 } },
        { name: definition.label, type: "line", xAxisIndex: 1, yAxisIndex: 1, data: view.values, connectNulls: false, showSymbol: view.dates.length < 12,
          lineStyle: { color: "#527f9e", width: 2 },
          markLine: { silent: true, symbol: "none", label: { color: "#667085", backgroundColor: "rgba(255,255,255,.9)", padding: [2, 3] }, data: referenceLines } },
        ...(source.bands ? ([
          ["upper", "上轨 +2σ", "#a16d35"], ["middle", "中轨 · 3年均值", "#8693a3"], ["lower", "下轨 −2σ", "#637ba0"],
        ] as const).map(([key, name, color]) => ({ name, type: "line", xAxisIndex: 1, yAxisIndex: 1,
          data: viewBands.map((p) => p?.[key] ?? null), connectNulls: false, showSymbol: false,
          lineStyle: { color, width: 1.3, type: key === "middle" ? "dashed" : "solid" } })) : []),
      ],
    });
    const resize = new ResizeObserver(() => chart.resize()); resize.observe(node.current);
    return () => { resize.disconnect(); chart.dispose(); };
  }, [view, priceKey, definition, source.unit, source.coverage, source.bands, frequency, enough, reference, zero]);

  return <div className="op-metric">
    <div className="op-controls">
      <label>价格<select aria-label="对照股指" value={priceKey} onChange={(e) => setPriceChoice(e.target.value as PriceKey)}>
        {(market === "cn" ? ["sse", "hs300"] : ["sp500", "nasdaq"]).map((key) => <option value={key} key={key}>{PRICE_NAMES[key as PriceKey]}</option>)}
      </select></label>
      <span className="op-windows" role="group" aria-label="对照期间">{WINDOWS.map((w) => <button type="button" key={w.label} aria-pressed={years === w.years} onClick={() => setYears(w.years)}>{w.label}</button>)}</span>
    </div>
    <p className="op-meaning">{definition.meaning} <span>{definition.reading}</span></p>
    {id === "baker-wurgler" && <div className="op-variants" role="group" aria-label="对照图Baker版本">
      <button type="button" aria-pressed={variant === "orth"} onClick={() => setVariant("orth")}>剔除宏观影响</button>
      <button type="button" aria-pressed={variant === "raw"} onClick={() => setVariant("raw")}>原始版</button>
    </div>}
    <div className="op-reading"><strong>{fmt(lastPoint?.value ?? null, id === "baker-wurgler" ? 3 : 2)}<small>{source.unit}</small></strong>
      <span>{id === "turnover-concentration" ? "历史完整月" : "资料截至"} {lastPoint?.date ?? "—"} · {frequency === "monthly" ? "月频" : frequency === "weekly" ? "周频" : "日频"}{source.bands && " · 历史参照版，未自动更新"}</span>
    </div>
    {source.bands && <ErpBandSummary row={source.bands[source.bands.length - 1]} />}
    {((!usesReferencePrice && prices.isPending) || source.isPending) ? <p role="status">价格与指标资料读取中…</p>
      : ((!usesReferencePrice && prices.isError) || source.error) ? <p role="alert">对照资料暂时不可用。<button type="button" onClick={() => { source.retry(); if (!usesReferencePrice) void prices.refetch(); }}>重试</button></p>
      : enough ? <div ref={node} className="op-chart" role="img" aria-label={`${PRICE_NAMES[priceKey]}价格与${definition.label}，上方价格下方指标，共用日期轴`} />
      : <p className="op-empty">两条序列没有足够的共同历史，暂不画投影。</p>}
    <p className="op-footnote op-evidence">{reference
      ? <>{reference.label}：{reference.meaning} <a href={reference.url} target="_blank" rel="noreferrer">{reference.source}</a></>
      : source.bands ? <>轨道依据：<a href={ERP_BAND_METHOD.url} target="_blank" rel="noreferrer">{ERP_BAND_METHOD.source}</a>。{ERP_BAND_METHOD.difference}</>
      : id === "baker-wurgler" ? "月度、可修订的情绪背景；原研究未建立大盘阶段顶底阈值。"
      : "未建立经验证的固定机会／风险阈值，图中仅展示原值。"}</p>
    {id === "hy-oas" && <p className="op-footnote">FRED 自2026年4月起仅公开最近3年；选择更长窗口也不会补出更早历史。<a href="https://fred.stlouisfed.org/series/BAMLH0A0HYM2" target="_blank" rel="noreferrer">来源说明</a></p>}
    {id === "turnover-concentration" && <p className="op-footnote">已存月度历史，不自动更新。2023-01—2026-07及个别月份输入不完整，曲线保留断线。</p>}
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
      <button type="button" aria-pressed={id === (market === "cn" ? "erp-cn" : "erp-us")} onClick={() => selectObservation(market === "cn" ? "erp-cn" : "erp-us")}>{market === "cn" ? "沪深300股债利差 · 上下轨" : "标普500股债利差 · 原值"}</button>
      {market === "us" && <>
        <button type="button" aria-pressed={id === "vix"} onClick={() => selectObservation("vix")}>VIX</button>
        <button type="button" aria-pressed={id === "hy-oas"} onClick={() => selectObservation("hy-oas")}>高收益债利差</button>
      </>}
    </div>
    {id === "breadth" ? <BreadthComparison market={market} onMarketChange={onMarketChange} onContextChange={onContextChange} />
      : id === "erp-cn" ? <ErpCrossChart /> : <MetricProjection id={id} market={market} />}
  </section>;
}
