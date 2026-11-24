import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import type { BakerSeries } from "./metricData";
/** Monthly historical sentiment. No inferred opportunity/risk bands. */
export default function BakerReading({ data, compact, variant, onVariant }: {
  data: BakerSeries; compact: boolean; variant: "orth" | "raw";
  onVariant: (value: "orth" | "raw") => void;
}) {
  const points = data.series.map((p) => ({ date: p.date.slice(0, 7), value: variant === "raw" ? p.rawValue ?? null : p.value }));
  const value = variant === "raw" ? data.latest.rawValue ?? null : data.latest.value;
  const validCount = points.filter((p) => p.value !== null).length;
  const chart = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (compact || !chart.current || validCount < 2) return;
    const instance = echarts.init(chart.current, undefined, { renderer: "svg" });
    const valid = points.flatMap((p) => p.value === null ? [] : [p.value]);
    const min = Math.floor(Math.min(...valid) * 2) / 2;
    const max = Math.ceil(Math.max(...valid) * 2) / 2;
    instance.setOption({
      animation: false,
      textStyle: { fontFamily: 'system-ui, -apple-system, "PingFang SC", sans-serif' },
      grid: { left: 40, right: 42, top: 24, bottom: 65 },
      tooltip: { trigger: "axis", confine: true, valueFormatter: (v: unknown) => v == null ? "缺值" : Number(v).toFixed(3) },
      xAxis: { type: "category", data: points.map((p) => p.date), boundaryGap: false,
        axisLabel: { hideOverlap: true, showMinLabel: true, showMaxLabel: true, color: "#64748b" } },
      yAxis: { type: "value", min, max, splitNumber: 4, axisLabel: { color: "#64748b" }, splitLine: { lineStyle: { color: "#e8edf2" } } },
      dataZoom: [{ type: "inside" }, { type: "slider", bottom: 4, height: 20, showDetail: false }],
      series: [{ type: "line", name: variant === "orth" ? "Baker 情绪（剔除宏观影响）" : "Baker 情绪（原始版）",
        data: points.map((p) => p.value), connectNulls: false, showSymbol: false,
        lineStyle: { width: 2, color: "#436886" },
      }],
    });
    const resize = new ResizeObserver(() => instance.resize()); resize.observe(chart.current);
    return () => { resize.disconnect(); instance.dispose(); };
  }, [data, compact, variant]);

  return <div className={`ol-baker ${compact ? "compact" : ""}`}>
    {!compact && <p className="ol-baker-definition">Baker–Wurgler 综合美国市场活动，观察较慢的情绪水平；数值越高，情绪越乐观。</p>}
    <div className="ol-baker-value"><strong>{value === null ? "暂无值" : value.toFixed(3)}</strong><span className="ol-baker-state">月度背景</span></div>
    <div className="ol-baker-meta">{data.latest.date.slice(0,7)} · 历史月值 · {variant === "orth" ? "剔除宏观影响" : "原始版"}</div>
    {!compact && <>
      <a className="op-open-link" href="/fundamentals?observation=baker-wurgler#fund-sec-market">与股指价格对照 →</a>
      <div className="ol-baker-switch" role="group" aria-label="Baker版本">
        <button type="button" aria-pressed={variant === "orth"} onClick={() => onVariant("orth")}>剔除宏观影响</button>
        <button type="button" aria-pressed={variant === "raw"} onClick={() => onVariant("raw")}>原始版</button>
      </div>
      <p className="ol-baker-footnote">月频、历史会修订；原研究没有建立大盘阶段顶底阈值。本图保留原值，不标机会／风险区间。</p>
      {validCount >= 2 ? <div ref={chart} className="ol-baker-chart" role="img" aria-label="Baker月度历史情绪曲线，无机会风险阈值" />
        : <p>历史资料不足，暂不画曲线。</p>}
      <details className="ol-baker-details"><summary>计算口径与来源</summary>
        <p>资料范围：{points[0]?.date ?? "—"}—{points[points.length - 1]?.date ?? "—"}，{validCount}个有效月。</p>
        <p>原研究主要比较不同类型股票的相对收益，不能据此认定大盘顶底。不要用相邻月差值解释情绪变化。</p>
        <p>{data.definition} {data.version} {data.publicationTiming}</p>
        <p>{data.limitations.join("；")}</p>
        <p><a href={data.sourceUrl} target="_blank" rel="noreferrer">作者数据表</a> · <a href="https://pages.stern.nyu.edu/~jwurgler/papers/wurgler_baker_cross_section.pdf" target="_blank" rel="noreferrer">原研究</a></p>
      </details>
    </>}
  </div>;
}
