import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import * as echarts from "echarts";
import { fundamentalsApi } from "../../api/client";
import type { FocusMomentumObservation } from "./data";
import { adjacentEventIndices, normalizeWindow, panWindow, visibleDateRange, windowAroundDate, zoomWindow, type ChartWindow } from "./chart-navigation";
import { buildFocusPriceView, type FocusPriceView, type ProjectionRange } from "./price-projection-data";
import { crossingMarkerSeries, filterCrossings, type CrossingFilter } from "./crossing-markers";
import "./price-projection.css";

type PriceKey = "hs300" | "sse";
const PRICE_NAMES: Record<PriceKey, string> = { hs300: "沪深300", sse: "上证指数" };
const RANGES: Array<{ label: string; value: ProjectionRange }> = [
  { label: "近1年", value: 1 }, { label: "近3年", value: 3 },
  { label: "近5年", value: 5 }, { label: "全部", value: "all" },
];
const COLORS = { price: "#48524f", focus: "#83708e", up: "#287e71", down: "#ad6735", zero: "#95958e", text: "#60635e", grid: "#e9e9e3" };

function ProjectionChart({ view, priceName, markNegative }: {
  view: FocusPriceView; priceName: string; markNegative: boolean;
}) {
  const node = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);
  const previousChartData = useRef<{ view: FocusPriceView; priceName: string; markNegative: boolean } | null>(null);
  const windowRef = useRef<ChartWindow>({ start: 0, end: 100 });
  const [window, setWindow] = useState(windowRef.current);
  const [selectedDate, setSelectedDate] = useState(view.zeroCrossings[view.zeroCrossings.length - 1]?.date ?? "");
  const [eventFilter, setEventFilter] = useState<CrossingFilter>("all");
  const visible = useMemo(() => visibleDateRange(view.dates, window), [view.dates, window]);
  const filteredEvents = useMemo(() => filterCrossings(view.zeroCrossings, eventFilter), [view.zeroCrossings, eventFilter]);
  const allVisibleEvents = view.zeroCrossings.filter(item => visible.start && visible.end && item.date >= visible.start && item.date <= visible.end);
  const visibleEvents = filterCrossings(allVisibleEvents, eventFilter);
  const selected = visibleEvents.find(item => item.date === selectedDate) ?? visibleEvents[visibleEvents.length - 1];
  const adjacent = adjacentEventIndices(filteredEvents.map(item => item.date), selected?.date, visible.start, visible.end);
  const eventColor = selected?.direction === "up" ? COLORS.up : COLORS.down;

  useEffect(() => {
    if (!node.current) return;
    const instance = echarts.init(node.current, undefined, { renderer: "svg" });
    chart.current = instance;
    previousChartData.current = null;
    const resize = new ResizeObserver(() => instance.resize());
    resize.observe(node.current);
    const onZoom = () => {
      const option = instance.getOption() as { dataZoom?: Array<{ start?: number; end?: number }> };
      const next = normalizeWindow({ start: Number(option.dataZoom?.[0]?.start ?? 0), end: Number(option.dataZoom?.[0]?.end ?? 100) });
      windowRef.current = next;
      setWindow(old => old.start === next.start && old.end === next.end ? old : next);
    };
    instance.on("datazoom", onZoom);
    const onClick = (params: unknown) => {
      const point = params as { seriesId?: string; name?: string; data?: { date?: string } };
      if (["price-crossings", "focus-crossings"].includes(point.seriesId ?? "") && point.data?.date) setSelectedDate(point.data.date);
    };
    instance.on("click", onClick);
    return () => { instance.off("datazoom", onZoom); instance.off("click", onClick); resize.disconnect(); instance.dispose(); chart.current = null; };
  }, []);

  useEffect(() => {
    if (!chart.current) return;
    const crossings = markNegative ? new Map(view.zeroCrossings.map(item => [item.date, item])) : new Map();
    const selectedLine = selected && markNegative ? [{ xAxis: selected.date, lineStyle: { color: eventColor, width: 1.5, type: "dashed" as const }, label: { show: false } }] : [];
    const pointLabelPosition = selected && view.dates.indexOf(selected.date) > view.dates.length * (windowRef.current.start + (windowRef.current.end - windowRef.current.start) * 0.65) / 100 ? "left" : "right";
    const selectedPoint = (value: number, label: string) => ({
      symbol: "circle", symbolSize: 10, silent: true,
      itemStyle: { color: "#fff", borderColor: eventColor, borderWidth: 2.5 },
      label: { show: true, position: pointLabelPosition, distance: 9, color: eventColor, fontWeight: 600, backgroundColor: "#fffffff2", padding: [5, 7], borderRadius: 4, formatter: label },
      data: selected && markNegative ? [{ coord: [selected.date, value] }] : [],
    });
    const option = {
      animation: false,
      textStyle: { color: COLORS.text, fontFamily: "inherit" },
      title: [
        { text: `${priceName}价格（点）`, left: 4, top: 4, textStyle: { fontSize: 13, fontWeight: 600, color: COLORS.price } },
        { text: "焦点动量 · 过去20日平均涨跌", left: 4, top: "50%", textStyle: { fontSize: 13, fontWeight: 600, color: COLORS.focus } },
      ],
      grid: [
        { left: 62, right: 30, top: 38, height: "31%" },
        { left: 62, right: 30, top: "58%", height: "27%" },
      ],
      tooltip: {
        trigger: "axis", confine: true, backgroundColor: "#fffffff5", borderColor: "#d8dcd4", textStyle: { color: "#373d38" },
        axisPointer: { type: "line" },
        formatter: (raw: unknown) => {
          const points = Array.isArray(raw) ? raw : [raw];
          const first = points[0] as { axisValue?: string; dataIndex?: number } | undefined;
          const date = first?.axisValue ?? view.dates[Number(first?.dataIndex)];
          const index = view.dates.indexOf(date);
          if (index < 0) return "—";
          const price = view.prices[index]; const focus = view.focusPercent[index]; const crossing = crossings.get(date);
          const label = crossing ? `<br/>${crossing.direction === "down" ? "↓ 动量由正转负" : "↑ 动量由负转正"}` : "";
          return `<strong>${date}</strong><br/>${priceName}：${price === null ? "—" : `${price.toFixed(2)} 点`}<br/>焦点动量：${focus === null ? "—" : `${focus.toFixed(2)}%`}${label}`;
        },
      },
      axisPointer: { link: [{ xAxisIndex: [0, 1] }], lineStyle: { color: "#8d948a", type: "dashed" }, label: { backgroundColor: "#5e675e" } },
      xAxis: [0, 1].map(gridIndex => ({ type: "category", gridIndex, data: view.dates, boundaryGap: false,
        axisLabel: { color: COLORS.text, hideOverlap: true, showMinLabel: true, showMaxLabel: true, alignMinLabel: "left", alignMaxLabel: "right", margin: 12, formatter: (date: string) => date },
        axisLine: { lineStyle: { color: "#b8bdb4" } }, axisTick: { show: false } })),
      yAxis: [
        { type: "value", gridIndex: 0, scale: true, axisLabel: { color: COLORS.text }, splitLine: { lineStyle: { color: COLORS.grid } } },
        { type: "value", gridIndex: 1, scale: true, min: ({ min }: { min: number }) => Math.min(0, Math.floor(min / 5) * 5), max: ({ max }: { max: number }) => Math.max(0, Math.ceil(max / 5) * 5), axisLabel: { color: COLORS.text, formatter: "{value}%" }, splitLine: { lineStyle: { color: COLORS.grid } } },
      ],
      dataZoom: [
        { type: "inside", xAxisIndex: [0, 1], ...windowRef.current, zoomOnMouseWheel: true, moveOnMouseWheel: "shift", moveOnMouseMove: true },
        { type: "slider", xAxisIndex: [0, 1], ...windowRef.current, bottom: 2, height: 18, showDetail: true, labelFormatter: (_index: number, date: string) => date,
          borderColor: "#d8dcd4", backgroundColor: "#f6f6f2", fillerColor: "#6c79651c", handleStyle: { color: "#fff", borderColor: "#8b9585" }, moveHandleStyle: { color: "#a8afa3" }, textStyle: { color: COLORS.text },
          dataBackground: { lineStyle: { color: "#b6bdb0" }, areaStyle: { color: "#edf0e8" } }, selectedDataBackground: { lineStyle: { color: "#8f9b87" }, areaStyle: { color: "#dce3d5" } } },
      ],
      series: [
        { id: "price", name: priceName, type: "line", xAxisIndex: 0, yAxisIndex: 0, data: view.prices, showSymbol: false, connectNulls: false, lineStyle: { width: 2, color: COLORS.price }, itemStyle: { color: COLORS.price },
          markLine: { silent: true, symbol: "none", data: selectedLine }, markPoint: selectedPoint(selected?.price ?? 0, `${selected?.date ?? ""} ${selected?.direction === "up" ? "转正 ↑" : "转负 ↓"}\n${priceName} ${selected?.price.toFixed(2) ?? ""} 点`) },
        { id: "focus", name: "焦点动量", type: "line", xAxisIndex: 1, yAxisIndex: 1, data: view.focusPercent, showSymbol: false, connectNulls: false, lineStyle: { width: 2, color: COLORS.focus }, itemStyle: { color: COLORS.focus },
          markLine: { silent: true, symbol: "none", data: [{ yAxis: 0, label: { show: true, formatter: "0% · 涨跌分界", position: "insideEndTop", color: COLORS.text }, lineStyle: { color: COLORS.zero, type: "dashed", width: 1 } }, ...selectedLine] },
          markPoint: selectedPoint(selected?.focusPercent ?? 0, `${selected?.date ?? ""}\n动量 ${selected?.focusPercent.toFixed(2) ?? ""}%`) },
        ...crossingMarkerSeries(markNegative ? visibleEvents : [], visible.count),
        { id: "negative-focus", name: "__negative_focus", type: "line", xAxisIndex: 1, yAxisIndex: 1, data: markNegative ? view.focusPercent.map(value => value === null ? null : Math.min(0, value)) : [], silent: true, showSymbol: false, connectNulls: false, tooltip: { show: false }, lineStyle: { opacity: 0 }, areaStyle: { color: "#c69b72", opacity: 0.13, origin: 0 }, emphasis: { disabled: true }, z: 0 },
      ],
    };
    const previous = previousChartData.current;
    if (!previous || previous.view !== view || previous.priceName !== priceName || previous.markNegative !== markNegative) {
      chart.current.setOption(option, true);
      previousChartData.current = { view, priceName, markNegative };
    } else {
      // Keep the active dataZoom gesture intact while the selected date follows the viewport.
      chart.current.setOption({ series: option.series.filter(series => ["price", "focus", "price-crossings", "focus-crossings"].includes(series.id)).map(series => series.id.endsWith("-crossings") ? series : {
        id: series.id, markLine: "markLine" in series ? series.markLine : undefined, markPoint: "markPoint" in series ? series.markPoint : undefined,
      }) });
    }
  }, [view, priceName, markNegative, selected, eventFilter, visible.count, visible.start, visible.end]);

  const navigate = (next: ChartWindow) => {
    const bounded = normalizeWindow(next); windowRef.current = bounded;
    chart.current?.dispatchAction({ type: "dataZoom", ...bounded }); setWindow(bounded);
  };
  const selectEvent = (date: string) => { setSelectedDate(date); navigate(windowAroundDate(view.dates, date, windowRef.current)); };
  return <>
    {markNegative && <div className="fmp-event-filter">
      <div className="fmp-controls" role="group" aria-label="穿零标记方向">
        <span>图中标记</span>
        {([['all', '全部'], ['up', '仅转正'], ['down', '仅转负']] as const).map(([value, label]) =>
          <button key={value} type="button" aria-pressed={eventFilter === value} onClick={() => setEventFilter(value)}>{label}</button>)}
      </div>
      <span aria-live="polite">当前区间 {allVisibleEvents.filter(item => item.direction === 'up').length} 次转正 · {allVisibleEvents.filter(item => item.direction === 'down').length} 次转负{eventFilter !== 'all' ? ` · 显示${visibleEvents.length}处` : ' · 全部标出'}</span>
    </div>}
    {markNegative && <div className="fmp-event-reader" aria-label="选择动量转正或转负日期">
      <div className="fmp-event-picker">
        <label htmlFor="fmp-event-date">定位穿零日期</label>
        <div className="fmp-event-picker-controls">
          <button type="button" aria-label="上一次穿零" disabled={adjacent.previous < 0} onClick={() => selectEvent(filteredEvents[adjacent.previous].date)}>‹</button>
          <select id="fmp-event-date" value={selected?.date ?? ""} onChange={event => selectEvent(event.target.value)}>
            {!selected && <option value="">当前区间无穿零</option>}
            {filteredEvents.map(item => <option key={item.date} value={item.date}>{item.date} · {item.direction === "up" ? "由负转正 ↑" : "由正转负 ↓"}</option>)}
          </select>
          <button type="button" aria-label="下一次穿零" disabled={adjacent.next < 0} onClick={() => selectEvent(filteredEvents[adjacent.next].date)}>›</button>
        </div>
      </div>
      {selected && <><div className="fmp-event-values" aria-live="polite"><strong style={{ color: eventColor }}>{selected.direction === "up" ? "↑ 由负转正" : "↓ 由正转负"}</strong><span>{priceName} <b>{selected.price.toFixed(2)}</b> 点</span><span>动量 <b>{selected.focusPercent.toFixed(2)}%</b></span></div><button type="button" className="fmp-nearby" onClick={() => navigate(windowAroundDate(view.dates, selected.date, windowRef.current, true))}>看这一天附近 ↗</button></>}
    </div>}
    <div className="fmp-navigation">
      <div className="fmp-controls" role="group" aria-label="图表缩放和平移">
        <button type="button" onClick={() => navigate(zoomWindow(window, 0.6))} disabled={window.end - window.start <= 0.51}>＋ 放大</button>
        <button type="button" onClick={() => navigate(zoomWindow(window, 1.6))} disabled={window.start === 0 && window.end === 100}>－ 缩小</button>
        <button type="button" onClick={() => navigate(panWindow(window, -0.5))} disabled={window.start <= 0}>← 左移</button>
        <button type="button" onClick={() => navigate(panWindow(window, 0.5))} disabled={window.end >= 100}>右移 →</button>
        <button type="button" onClick={() => navigate({ start: 0, end: 100 })} disabled={window.start === 0 && window.end === 100}>还原</button>
      </div>
      <span>{visible.start ?? "—"} — {visible.end ?? "—"}</span>
    </div>
    <div ref={node} className="fmp-chart" role="img" aria-label={`${priceName}价格与焦点动量。石墨色价格线，灰紫色动量线；${markNegative ? `上下两图各显示${visibleEvents.length}个穿零标记，绿色向上三角为转正，橙色向下三角为转负。` : "穿零标记已隐藏。"}圆环只定位选中日期。${selected && markNegative ? `已定位${selected.date}，动量${selected.direction === "up" ? "转正" : "转负"}，指数${selected.price.toFixed(2)}点，动量${selected.focusPercent.toFixed(2)}%。` : ""}可用按钮、滚轮或底部手柄缩放。`} />
  </>;
}

export function FocusMomentumPriceProjection({ data }: { data: FocusMomentumObservation }) {
  const [market, setMarket] = useState<"cn" | "us">("cn");
  const [priceKey, setPriceKey] = useState<PriceKey>("hs300");
  const [range, setRange] = useState<ProjectionRange>(1);
  const [markNegative, setMarkNegative] = useState(true);
  const overlay = useQuery({
    queryKey: ["fundOverlay", 20],
    queryFn: () => fundamentalsApi.overlayHistory(20),
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
  });
  const priceSeries = overlay.data?.series[priceKey];
  const view = useMemo(() => buildFocusPriceView(priceSeries, data.series, data.asOf, range),
    [priceSeries, data.series, data.asOf, range]);

  return <section className="fmp-projection" aria-labelledby="fmp-title">
    <header className="fmp-heading"><div><h3 id="fmp-title">价格与焦点动量</h3><p>上图看指数，下图看活跃股表现。</p></div>
      <div className="fmp-controls" role="group" aria-label="历史范围">
        {RANGES.map((option) => <button key={option.value} type="button" aria-pressed={range === option.value} onClick={() => setRange(option.value)}>{option.label}</button>)}
      </div>
    </header>
    <div className="fmp-switches">
      <div className="fmp-controls" role="group" aria-label="市场"><button type="button" aria-pressed={market === "cn"} onClick={() => setMarket("cn")}>A股</button><button type="button" aria-pressed={market === "us"} onClick={() => setMarket("us")}>美股</button></div>
      {market === "cn" && <div className="fmp-controls" role="group" aria-label="价格指数"><button type="button" aria-pressed={priceKey === "hs300"} onClick={() => setPriceKey("hs300")}>沪深300</button><button type="button" aria-pressed={priceKey === "sse"} onClick={() => setPriceKey("sse")}>上证指数</button></div>}
    </div>
    {market === "us" ? <p className="fmp-state" role="status">美股焦点动量尚无独立历史序列，暂不能显示同期曲线。</p> : <>
      <p className="fmp-scope">动量：固定300股中的活跃股 · 价格对照：{PRICE_NAMES[priceKey]}</p>
      <p className="fmp-dates">资料截至 {view.commonEnd ?? "无同日资料"}{view.priceSourceLast !== view.modelLast && view.priceSourceLast && view.modelLast ? `（价格至${view.priceSourceLast}，动量至${view.modelLast}）` : ""}</p>
      <div className="fmp-legend" aria-label="图例"><span><i className="fmp-line price" />{PRICE_NAMES[priceKey]}价格</span><span><i className="fmp-line focus" />焦点动量</span><span><i className="fmp-line zero" />0% 涨跌分界</span>{markNegative && <><span><i className="fmp-event up">▲</i>负转正</span><span><i className="fmp-event down">▼</i>正转负</span><span><i className="fmp-selected-ring" />选中日期</span></>}</div>
      <p className="fmp-tip">点任一三角，两图定位同一天。转正看活跃股修复，转负看表现降温；标记表示已发生的变化。</p>
      {overlay.isPending && <p className="fmp-state" role="status">正在读取指数历史价格…</p>}
      {overlay.isError && <div className="fmp-state fmp-error" role="alert">指数价格读取失败，暂不能显示同期曲线。<button type="button" onClick={() => void overlay.refetch()}>重试</button></div>}
      {!overlay.isPending && !overlay.isError && !view.commonEnd && <p className="fmp-state">价格与模型没有同日有效资料，无法绘图。</p>}
      {!overlay.isPending && !overlay.isError && view.commonEnd && <ProjectionChart key={`${priceKey}:${range}`} view={view} priceName={PRICE_NAMES[priceKey]} markNegative={markNegative} />}
      <div className="fmp-controls fmp-mark"><button type="button" aria-pressed={markNegative} onClick={() => setMarkNegative((old) => !old)}> {markNegative ? "隐藏" : "显示"}动量负值区与穿零事件</button></div>
      {markNegative && view.zeroCrossings.length > 0 && <details className="fmp-source"><summary>查看焦点动量穿零日期与数值（{view.zeroCrossings.length}处）</summary><ul>{view.zeroCrossings.map((item) => <li key={item.date}>{item.date} · 焦点动量{item.direction === "down" ? "转负" : "转正"} · {PRICE_NAMES[priceKey]} {item.price.toFixed(2)} 点 · 焦点动量 {item.focusPercent.toFixed(2)}%</li>)}</ul></details>}
      <p className="fmp-note">穿零在当日收盘后确认。浅橙区域表示动量为负，不能据此确认见底。</p>
      <details className="fmp-source"><summary>这条动量线怎么计算</summary><p>每日在固定300股样本中，按20日平均成交额选最活跃的5%，取它们过去20日涨跌的平均值。样本不代表全A股，活跃股每天会变化；指数价格线只作同期对照，不含分红。这是独立观察版，原视频完整参数未公开。</p></details>
    </>}
  </section>;
}
