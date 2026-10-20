import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import * as echarts from "echarts";
import { api, fundamentalsApi } from "../../api/client";
import type { BreadthHistoryPoint, RatesHistorySeries } from "../../types";
import { BREADTH_HIGHLIGHT_RULES, BREADTH_LINES, computeHighlightBands, type HighlightBand } from "../trend/zones";
import "./breadth-comparison.css";

type Market = "cn" | "us";
type PriceKey = "sse" | "sp500" | "nasdaq";
type View = { dates: string[]; price: (number | null)[]; breadth: (number | null)[][]; bands: HighlightBand[] };
const EMPTY_BREADTH: BreadthHistoryPoint[] = [];

const WINDOWS = [
  { label: "1年", days: 365 },
  { label: "3年", days: 1095 },
  { label: "5年", days: 1825 },
] as const;
const PRICE_NAMES: Record<PriceKey, string> = { sse: "上证指数", sp500: "标普500", nasdaq: "纳斯达克综合指数" };
const exists = (value: number | null | undefined): value is number => typeof value === "number" && Number.isFinite(value);

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

function viewFor(series: RatesHistorySeries | undefined, breadth: BreadthHistoryPoint[], days: number,
  active: ReadonlySet<string>, market: Market): View {
  if (!series?.dates.length) return { dates: [], price: [], breadth: [[], [], []], bands: [] };
  const last = series.dates[series.dates.length - 1];
  const cutoff = new Date(`${last}T00:00:00Z`);
  cutoff.setUTCDate(cutoff.getUTCDate() - days);
  const minDate = cutoff.toISOString().slice(0, 10);
  const prices = seriesMap(series);
  const bmap = new Map(breadth.map((point) => [point.date, point]));
  // Price trading dates are the shared axis. A missing same-day breadth stays null.
  const dates = [...new Set(series.dates.filter((date) => date >= minDate && date <= last))].sort();
  const values = dates.map((date) => prices.get(date) ?? null);
  const b20 = dates.map((date) => bmap.get(date)?.breadth_20 ?? null);
  const b50 = dates.map((date) => bmap.get(date)?.breadth_50 ?? null);
  const b200 = dates.map((date) => bmap.get(date)?.breadth_200 ?? null);
  const bands = computeHighlightBands(active, market === "cn" ? "CN" : "US", dates, b20, b50, b200);
  return { dates, price: values, breadth: [b20, b50, b200], bands };
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

function BreadthProjectionChart({ view, priceName }: { view: View; priceName: string }) {
  const node = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);
  useEffect(() => {
    if (!node.current) return;
    const instance = echarts.init(node.current, undefined, { renderer: "canvas" });
    chart.current = instance;
    const resize = new ResizeObserver(() => instance.resize());
    resize.observe(node.current);
    return () => { resize.disconnect(); instance.dispose(); chart.current = null; };
  }, []);
  useEffect(() => {
    if (!chart.current) return;
    const marks = shade(view.bands);
    chart.current.setOption({
      animation: false,
      grid: [{ left: 52, right: 18, top: 28, height: "36%" }, { left: 52, right: 18, top: "52%", height: "34%" }],
      legend: { top: 0, left: 50, data: [priceName, "20日", "50日", "200日"], textStyle: { fontSize: 11 } },
      tooltip: { trigger: "axis", axisPointer: { type: "cross", link: [{ xAxisIndex: [0, 1] }] },
        valueFormatter: (value: unknown) => value == null ? "—" : Number(value).toFixed(1) },
      axisPointer: { link: [{ xAxisIndex: [0, 1] }] },
      xAxis: [
        { type: "category", gridIndex: 0, data: view.dates, boundaryGap: false, axisLabel: { show: false } },
        { type: "category", gridIndex: 1, data: view.dates, boundaryGap: false, axisLabel: { fontSize: 11, hideOverlap: true } },
      ],
      yAxis: [
        { type: "value", gridIndex: 0, scale: true, name: "指数点位", nameTextStyle: { fontSize: 11 }, axisLabel: { fontSize: 11 } },
        { type: "value", gridIndex: 1, min: 0, max: 100, name: "宽度 %", nameTextStyle: { fontSize: 11 }, axisLabel: { fontSize: 11, formatter: "{value}%" } },
      ],
      dataZoom: [{ type: "inside", xAxisIndex: [0, 1], start: 0, end: 100 }, { type: "slider", xAxisIndex: [0, 1], start: 0, end: 100, bottom: 6, height: 18 }],
      series: [
        { name: priceName, type: "line", xAxisIndex: 0, yAxisIndex: 0, data: view.price, showSymbol: false, connectNulls: false, lineStyle: { width: 2, color: "#334e75" }, itemStyle: { color: "#334e75" } },
        ...view.breadth.map((values, index) => ({ name: BREADTH_LINES[index].name, type: "line" as const,
          xAxisIndex: 1, yAxisIndex: 1, data: values, showSymbol: false, connectNulls: false,
          lineStyle: { width: index === 1 ? 2 : 1.2, color: BREADTH_LINES[index].color, opacity: index === 1 ? 1 : 0.75 }, itemStyle: { color: BREADTH_LINES[index].color } })),
        { name: "__price_conditions", type: "line", xAxisIndex: 0, yAxisIndex: 0, data: [], silent: true, tooltip: { show: false }, lineStyle: { opacity: 0 }, ...marks },
        { name: "__breadth_conditions", type: "line", xAxisIndex: 1, yAxisIndex: 1, data: [], silent: true, tooltip: { show: false }, lineStyle: { opacity: 0 }, ...marks },
      ],
    }, true);
  }, [view, priceName]);
  return <div ref={node} className="bc-chart" role="img" aria-label={`${priceName}价格与同日20、50、200日市场宽度曲线，条件色带同步标在两图；详情可用鼠标或触屏查看`} />;
}

export default function BreadthComparison({ market, onContextChange }: {
  market: Market;
  onContextChange?: (context: { windowDays: number; ruleIds: string[]; priceKey: string; fingerprint: string }) => void;
}) {
  const [windowDays, setWindowDays] = useState<number>(365);
  const [usPrice, setUsPrice] = useState<"sp500" | "nasdaq">("sp500");
  const [active, setActive] = useState<ReadonlySet<string>>(() => new Set(["bull_base", "bear_base"]));
  const priceKey: PriceKey = market === "cn" ? "sse" : usPrice;
  const breadthId = market === "cn" ? "CN_ALL_A" : "SP500";
  const breadth = useQuery({ queryKey: ["overlayBreadth", breadthId, 1260],
    queryFn: () => api.marketContextBreadthHistory(breadthId, 1260), staleTime: 12 * 3600_000 });
  const overlay = useQuery({ queryKey: ["fundOverlay", 20],
    queryFn: () => fundamentalsApi.overlayHistory(20), staleTime: 12 * 3600_000 });
  const priceSeries = overlay.data?.series[priceKey];
  const points = breadth.data?.history ?? EMPTY_BREADTH;
  const view = useMemo(() => viewFor(priceSeries, points, windowDays, active, market), [priceSeries, points, windowDays, active, market]);
  const lastBreadthDate = points[points.length - 1]?.date;
  const lastPriceDate = priceSeries?.dates[priceSeries.dates.length - 1];
  const breadthBehindPrice = !!(lastBreadthDate && lastPriceDate && lastBreadthDate < lastPriceDate);
  const activeRuleIds = useMemo(() => BREADTH_HIGHLIGHT_RULES.filter((rule) => active.has(rule.key)).map((rule) => rule.key), [active]);
  const fingerprint = useMemo(
    () => fingerprintForView(view, market, priceKey, windowDays, activeRuleIds, lastBreadthDate),
    [view, market, priceKey, windowDays, activeRuleIds, lastBreadthDate],
  );
  const callback = useRef(onContextChange);
  callback.current = onContextChange;
  useEffect(() => { callback.current?.({ windowDays, ruleIds: activeRuleIds, priceKey, fingerprint }); }, [fingerprint]);
  const toggle = (id: string) => setActive((previous) => {
    const next = new Set(previous);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  });

  return <section className="breadth-comparison" aria-labelledby="bc-title">
    <header className="bc-heading">
      <div><h2 id="bc-title">价格与市场宽度</h2><p>同日曲线与条件标注 · 历史观察</p></div>
      <div className="bc-controls" role="group" aria-label="价格范围与期间">
        {market === "us" && <span className="bc-price-switch"><button type="button" aria-pressed={usPrice === "sp500"} onClick={() => setUsPrice("sp500")}>标普500</button><button type="button" aria-pressed={usPrice === "nasdaq"} onClick={() => setUsPrice("nasdaq")}>纳斯达克</button></span>}
        <span className="bc-window-switch">{WINDOWS.map((window) => <button key={window.days} type="button" aria-pressed={windowDays === window.days} onClick={() => setWindowDays(window.days)}>{window.label}</button>)}</span>
      </div>
    </header>
    <p className="bc-scope">{market === "cn" ? "全A股票宽度 × 上证指数价格" : `标普500成分股宽度 × ${PRICE_NAMES[priceKey]}价格`}</p>
    <p className={`bc-dates${breadthBehindPrice ? " bc-stale" : ""}`}>价格截至 {lastPriceDate ?? "未提供"} · 宽度截至 {lastBreadthDate ?? "未提供"}{breadthBehindPrice ? "（宽度后续缺失；图上留白）" : ""}</p>
    {breadth.isPending || overlay.isPending ? <p className="bc-state" role="status">正在读取历史曲线…</p> : null}
    {breadth.isError || overlay.isError ? <p className="bc-state bc-error" role="alert">{breadth.isError ? "宽度历史读取失败。" : "指数价格历史读取失败。"}暂不能显示同期对照。</p> : null}
    {!breadth.isPending && !overlay.isPending && !breadth.isError && !overlay.isError && (!view.dates.length || !view.breadth.some((line) => line.some(exists))) &&
      <p className="bc-state">此期间没有价格与宽度同日可比资料。</p>}
    {view.dates.length > 0 && view.breadth.some((line) => line.some(exists)) && !breadth.isError && !overlay.isError && <BreadthProjectionChart view={view} priceName={PRICE_NAMES[priceKey]} />}
    <div className="bc-rules" role="group" aria-label="在两图标记历史宽度条件">
      <span>同期条件：</span>{BREADTH_HIGHLIGHT_RULES.map((rule) => <button key={rule.key} type="button" aria-pressed={active.has(rule.key)} onClick={() => toggle(rule.key)} title={rule.full}><span className="bc-rule-dot" style={{ background: rule.color }} aria-hidden="true" />{rule.short}</button>)}
    </div>
    <p className="bc-caption">色带把已有宽度条件投影到同期价格，不代表未来走势。沿用本系统图表条件：A股80/20、美股85/15，200日底色按50%划分；20日为短期对照，未纳入现有六条件。</p>
    <details className="bc-source"><summary>来源与如何读</summary><p>宽度是股票中有多少比例站在各自20、50或200日均线上方。将指数价格和宽度放在相同日期轴上，可对照价格变化有多少股票一起参与。<a href="https://chartschool.stockcharts.com/table-of-contents/market-indicators/percent-above-moving-average" target="_blank" rel="noreferrer">StockCharts 指标定义</a>仅供解释，不是本系统数据来源。</p><p>本图价格来自现有指数历史接口，宽度来自现有市场宽度历史接口。两者交易日严格对齐，缺值不连线；全A与上证、标普500宽度与纳指都不是同一股票范围。历史名单、有效股票分母与修订可能不同，当前接口未给出逐日完整覆盖率，不能用这张图直接判定交易或证明未来效果。</p></details>
  </section>;
}
