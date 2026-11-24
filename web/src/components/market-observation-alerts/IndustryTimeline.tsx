import { useEffect, useRef, useState } from "react";
import * as echarts from "echarts";
import { CHART_COLORS } from "./ChartLegend";
import { industryRange, industryRangeFromZoom, industryTimelineOption } from "./industryTimelineOptions";
import type { IndustryStructureSnapshot } from "./industryStructureData";

const signed = (value: number, digits = 2) => `${value > 0 ? "+" : ""}${value.toFixed(digits)}`;

export default function IndustryTimeline({ snapshot, large = false }: { snapshot: IndustryStructureSnapshot; large?: boolean }) {
  const { history, latest } = snapshot;
  const height = large ? 330 : 250;
  const node = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);
  const [range, setRange] = useState(() => industryRange(history.length));
  const before = history[history.length - 6]?.date;

  useEffect(() => {
    const element = node.current;
    if (!element) return;
    let instance: echarts.ECharts | null = null;
    const onZoom = () => {
      const option = instance?.getOption() as { dataZoom?: Array<{ start?: number; end?: number }> } | undefined;
      const current = option?.dataZoom?.[0];
      if (typeof current?.start === "number" && typeof current.end === "number") {
        const next = industryRangeFromZoom(history.length, current.start, current.end);
        setRange(previous => previous.start === next.start && previous.end === next.end ? previous : next);
      }
    };
    const resize = () => {
      // Dialogs can initially be hidden; wait for their first usable layout before initializing.
      if (!element.clientWidth || !element.clientHeight) return;
      if (instance) { instance.resize(); return; }
      instance = echarts.init(element, undefined, { renderer: "svg" });
      chart.current = instance;
      instance.setOption(industryTimelineOption(history, height));
      instance.on("datazoom", onZoom);
      setRange(industryRange(history.length));
    };
    const observer = new ResizeObserver(resize);
    observer.observe(element);
    resize();
    return () => { observer.disconnect(); instance?.off("datazoom", onZoom); instance?.dispose(); chart.current = null; };
  }, [history, height]);

  const select = (days: 60 | 120 | "all") => {
    const next = industryRange(history.length, days);
    chart.current?.dispatchAction({ type: "dataZoom", startValue: next.start, endValue: next.end });
    setRange(next);
  };
  return <div className="is-timeline">
    <div className="is-metrics">
      <section className="is-metric">
        <h4 className="is-metric-label"><i style={{ background: CHART_COLORS.primary }} />行业同步程度</h4>
        <strong>{latest.correlation.toFixed(3)}</strong>
        <p className="is-metric-meta">较5个交易日前（{before}）<b>{signed(latest.correlationChange5, 3)}</b></p>
        <p className="is-metric-meta">近1年历史分位 {latest.correlationPastPercentile.toFixed(0)}%</p>
      </section>
      <section className="is-metric">
        <h4 className="is-metric-label"><i style={{ background: CHART_COLORS.secondary }} />行业分化程度</h4>
        <strong>{latest.dispersion5.toFixed(2)}<em>个百分点</em></strong>
        <p className="is-metric-meta">较5个交易日前（{before}）<b>{signed(latest.dispersion5Change5)} 个百分点</b></p>
        <p className="is-metric-meta">近1年历史分位 {latest.dispersion5PastPercentile.toFixed(0)}%</p>
      </section>
    </div>
    <div className="is-timeline-controls">
      <div className="is-range-buttons" role="group" aria-label="两图共同时间范围">
        {([60, 120, "all"] as const).map(days => {
          const candidate = industryRange(history.length, days);
          return <button type="button" key={days} aria-pressed={range.start === candidate.start && range.end === candidate.end}
            onClick={() => select(days)}>{days === "all" ? "全部历史" : `近${days}交易日`}</button>;
        })}
      </div>
      <span>两图联动缩放</span>
    </div>
    <p className="is-timeline-range" aria-live="polite">{history[range.start]?.date} 至 {history[range.end]?.date} · {range.end - range.start + 1}个交易日</p>
    <div ref={node} className="is-linked-chart" style={{ height, minWidth: 0 }} role="img"
      aria-label={`行业同步与分化历史曲线，共同时间范围${history[range.start]?.date}至${history[range.end]?.date}；上图相关系数，下图分化百分点；滚轮缩放，拖动平移，下方手柄选择时间。`} />
    <details className="is-timeline-method"><summary>怎么看这两条线</summary>
      <p>同步程度取十行业日涨跌的20日平均两两相关系数，越高表示同涨同跌越明显。</p>
      <p>分化程度取十行业同日涨跌幅的标准差，再求最近5日平均；越高表示行业表现差异越大。两条线配合上涨行业数，观察市场是普遍同行还是行业分化。</p>
    </details>
  </div>;
}
