import { useEffect, useMemo, useRef, useState } from "react";
import * as echarts from "echarts";
import type { LineSeriesOption } from "echarts";
import ChartLegend from "./ChartLegend";
import type { MemberDispersionCard, MemberDispersionPoint, MemberDispersionRegime } from "./memberDispersionData";
import "./member-dispersion.css";

const colors = {
  raw: "#8b9baa", ma5: "#244e73", ma20: "#48786a", p20: "#396f9c", p50: "#697789", p80: "#ad583a",
  sector: "#9a6886", index: "#5c6677", b20: "#247f76", b60: "#887048", ratio: "#75588b", warning: "#bc653e",
};

const regimes: Record<MemberDispersionRegime, { title: string; hint: string; tools: string }> = {
  PANIC: { title: "泥沙俱下 / 恐慌", hint: "警惕系统性杀跌", tools: "观察空仓等待或宽基左侧极值" },
  VOLATILE_DISAGREEMENT: { title: "分歧巨震洗牌", hint: "多空剧烈博弈", tools: "观察收缩总仓位以防范尾部风险" },
  SIPHON_WARNING: { title: "虹吸 / 抱团预警", hint: "留意少数权重虹吸或局部瓦解", tools: "谨慎追高，关注移动止盈" },
  HEALTHY_ROTATION: { title: "良性结构轮动", hint: "观察主线扩散", tools: "优先跟踪强势行业 ETF" },
  BROAD_TREND: { title: "宽基共振趋势", hint: "观察普涨 Beta 与行业超额收敛", tools: "优先跟踪宽基 ETF" },
  BALANCED: { title: "低波磨底 / 均衡", hint: "观察分化与宽度是否回归中性", tools: "以均线配置为基准" },
};

function lastReadingIndex(points: MemberDispersionPoint[]) {
  for (let i = points.length - 1; i >= 0; i--) {
    if (points[i].disp_raw !== null) return i;
  }
  return points.length - 1;
}

function number(value: number | null | undefined, unit = "%", precision = 2) {
  return value == null ? "—" : `${value.toFixed(precision)}${unit}`;
}

function bandPosition(percentile: number | null) {
  if (percentile === null) return { label: "分位待齐", tone: "neutral" };
  if (percentile >= 80) return { label: "高位", tone: "high" };
  if (percentile <= 20) return { label: "低位", tone: "low" };
  return { label: "中间区间", tone: "neutral" };
}

function sectorReading(point: MemberDispersionPoint) {
  const ratio = number(point.sector_dominance_ratio, " 倍");
  if (point.sector_dominance_pct === null) {
    return `${ratio}${point.sector_dominance_ratio === null ? " · 行业资料待齐" : " · 历史分位待齐"}`;
  }
  const { label } = bandPosition(point.sector_dominance_pct);
  const interpretation = point.sector_dominance_pct >= 80 ? "优先观察行业ETF轮动"
    : point.sector_dominance_pct <= 20 ? "结合宽度看宽基或个股" : "对照宽度判断参与面";
  return `${ratio} · ${label}（${number(point.sector_dominance_pct, "%", 1)}） · ${interpretation}`;
}

function MiniDispersion({ points }: { points: MemberDispersionPoint[] }) {
  const latest = points[points.length - 1];
  const hasTrend = points.some((point, i) => i > 0 && point.disp_raw !== null && points[i - 1].disp_raw !== null);
  if (!hasTrend) return <p className="md-note">分化趋势资料不足</p>;
  const values = points.flatMap(point => [point.disp_raw, point.disp_ma5]).concat(latest.disp_p20, latest.disp_p80)
    .filter((value): value is number => value !== null);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pad = Math.max((max - min) * .12, .02);
  const low = Math.max(0, min - pad);
  const high = max + pad;
  const x = (i: number) => 8 + i * 244 / (points.length - 1);
  const y = (v: number) => 12 + 84 * (high - v) / (high - low);
  const path = (field: "disp_raw" | "disp_ma5") => {
    let connected = false;
    return points.map((point, i) => {
      const value = point[field];
      if (value === null) { connected = false; return ""; }
      const command = connected ? "L" : "M";
      connected = true;
      return `${command}${x(i).toFixed(2)},${y(value).toFixed(2)}`;
    }).join(" ");
  };
  const rails = [
    { label: "P80", value: latest.disp_p80, color: colors.p80, offset: -3 },
    { label: "P20", value: latest.disp_p20, color: colors.p20, offset: 10 },
  ];
  return <div className="md-mini">
    <svg viewBox="0 0 320 108" role="img" aria-label="近期单日分化、5日均值与最新历史高低参考，单位为百分点">
      {latest.disp_p80 !== null && <rect x={8} y={12} width={244} height={y(latest.disp_p80) - 12} fill="#fbede6" />}
      {latest.disp_p20 !== null && <rect x={8} y={y(latest.disp_p20)} width={244} height={96 - y(latest.disp_p20)} fill="#edf4fb" />}
      {rails.map(({ label, value, color, offset }) => value === null ? null : <g key={label}>
        <path d={`M8,${y(value)}H252`} fill="none" stroke={color} strokeDasharray="4 3" />
        <text x={258} y={y(value) + offset} fill={color}>{label} {number(value, "")}</text>
      </g>)}
      <path d={path("disp_raw")} fill="none" stroke={colors.raw} strokeWidth={1.2} />
      <path d={path("disp_ma5")} fill="none" stroke={colors.ma5} strokeWidth={2.4} strokeLinejoin="round" />
    </svg>
    <div className="md-dates"><span>{points[0].date}</span><span>{latest.date}</span></div>
  </div>;
}

export function MemberDispersionSummary({ card }: { card: MemberDispersionCard }) {
  const index = lastReadingIndex(card.points);
  const current = card.points[index];
  const status = current.regime_diagnosis && regimes[current.regime_diagnosis];
  const badge = bandPosition(current.disp_pct_252d);
  const badgeLabel = badge.tone === "high" ? "高分化" : badge.tone === "low" ? "低分化"
    : current.disp_pct_252d === null ? badge.label : "常见";
  return <div className="md-summary">
    <div className="md-current">
      <strong>{number(current.disp_raw, "百分点")}</strong>
      <span className={`md-badge is-${badge.tone}`}>
        {current.disp_pct_252d !== null && `P${number(current.disp_pct_252d, "", 1)} · `}{badgeLabel}
      </span>
      <span className="md-ma5">MA5 <b>{number(current.disp_ma5)}</b></span>
    </div>
    <div className="md-asof">单日分化 · <time dateTime={current.date}>{current.date}</time></div>
    <p><b>环境</b> {status ? `${status.title} · ${status.hint}` : "诊断资料待齐"}</p>
    <p><b>工具观察</b> 宽度（MA20） {number(current.pct_above_ma20, "%", 1)} · 行业主导率 {sectorReading(current)}{status && ` · ${status.tools}`}</p>
    <ChartLegend items={[
      { label: "单日分化", color: colors.raw }, { label: "5日均值", color: colors.ma5 },
    ]} />
    <MiniDispersion points={card.points.slice(Math.max(0, index - 59), index + 1)} />
  </div>;
}

type ValueField = Exclude<keyof MemberDispersionPoint, "date" | "regime_diagnosis" | "high_disp_low_breadth" | "breadth_divergence">;

type SeriesSpec = {
  name: string;
  field: ValueField;
  color: string;
  axis: number;
  yAxis?: number;
  dashed?: boolean;
  width?: number;
  unit?: string;
};

const raw: SeriesSpec = { name: "单日分化", field: "disp_raw", color: colors.raw, axis: 0, width: 1.2 };
const ma5: SeriesSpec = { name: "分化5日均值", field: "disp_ma5", color: colors.ma5, axis: 0, width: 2.6 };
const ma20: SeriesSpec = { name: "分化20日均值", field: "disp_ma20", color: colors.ma20, axis: 0 };
const sector: SeriesSpec = { name: "行业单日分化", field: "sector_disp_raw", color: colors.sector, axis: 0 };
const rails: SeriesSpec[] = [
  { name: "P20", field: "disp_p20", color: colors.p20, axis: 0, dashed: true },
  { name: "P50", field: "disp_p50", color: colors.p50, axis: 0, dashed: true },
  { name: "P80", field: "disp_p80", color: colors.p80, axis: 0, dashed: true },
];
const breadth: SeriesSpec[] = [
  { name: "宽基收盘（右轴）", field: "index_close", color: colors.index, axis: 1, yAxis: 2, unit: " 点" },
  { name: "站上20日线", field: "pct_above_ma20", color: colors.b20, axis: 1 },
  { name: "站上60日线", field: "pct_above_ma60", color: colors.b60, axis: 1 },
];
const ratio: SeriesSpec = { name: "行业/个股分化（5日均值）", field: "sector_dominance_ratio", color: colors.ratio, axis: 2, yAxis: 3, unit: " 倍" };

function asLine(spec: SeriesSpec, points: MemberDispersionPoint[]): LineSeriesOption {
  return {
    type: "line", name: spec.name, xAxisIndex: spec.axis, yAxisIndex: spec.yAxis ?? spec.axis,
    data: points.map(point => point[spec.field]), showSymbol: points.length < 3,
    connectNulls: false, clip: true, z: spec.field === "disp_ma5" ? 4 : 3,
    itemStyle: { color: spec.color }, lineStyle: { color: spec.color, type: spec.dashed ? "dashed" : "solid", width: spec.width ?? 1.7 },
  };
}

function thresholdBand(points: MemberDispersionPoint[]): LineSeriesOption[] {
  return [
    {
      type: "line", stack: "参考区间", data: points.map(point => point.disp_p20),
      showSymbol: false, silent: true, tooltip: { show: false }, lineStyle: { opacity: 0 },
    },
    {
      type: "line", stack: "参考区间", data: points.map(point =>
        point.disp_p20 !== null && point.disp_p80 !== null ? point.disp_p80 - point.disp_p20 : null),
      showSymbol: false, silent: true, tooltip: { show: false }, lineStyle: { opacity: 0 },
      areaStyle: { color: "#d8e2ed", opacity: .42 }, z: 1,
    },
  ];
}

function warningAreas(points: MemberDispersionPoint[]) {
  const areas: [{ xAxis: string }, { xAxis: string }][] = [];
  let start: string | undefined;
  points.forEach((point, i) => {
    if (point.high_disp_low_breadth) {
      start ??= point.date;
      if (!points[i + 1]?.high_disp_low_breadth) {
        areas.push([{ xAxis: start }, { xAxis: point.date }]);
        start = undefined;
      }
    }
  });
  return areas;
}

function chartOption(points: MemberDispersionPoint[], series: SeriesSpec[], showRails: boolean): echarts.EChartsOption {
  const dates = points.map(point => point.date);
  const dateToPoint = new Map(points.map(point => [point.date, point]));
  const axisText = { color: "#506074", fontSize: 11 };
  const splitLine = { lineStyle: { color: "#e4ebf1" } };
  const lines = series.map(spec => asLine(spec, points));
  const b20 = lines.find(line => line.name === breadth[1].name);
  if (b20) b20.markArea = {
    silent: true, itemStyle: { color: "rgba(188,101,62,.12)" }, label: { show: false }, data: warningAreas(points),
  };
  return {
    animation: false,
    textStyle: { fontFamily: 'system-ui, -apple-system, "PingFang SC", sans-serif' },
    title: [
      { text: "分化 · 百分点", top: 5 },
      { text: "宽度 · %　 /　 宽基收盘 · 点", top: 248 },
      { text: "行业/个股分化 · 倍", top: 488 },
    ].map(title => ({ ...title, left: 0, textStyle: { color: "#35465a", fontSize: 13, fontWeight: 600 } })),
    grid: [34, 277, 517].map((top, i) => ({ left: 60, right: 64, top, height: i === 2 ? 133 : 185 })),
    xAxis: [0, 1, 2].map(gridIndex => ({
      gridIndex, type: "category", data: dates, boundaryGap: false,
      axisLabel: { ...axisText, show: gridIndex === 2, hideOverlap: true, showMinLabel: true, showMaxLabel: true },
      axisTick: { show: false }, axisLine: { lineStyle: { color: "#aab7c4" } },
      axisPointer: { show: true, label: { show: false } },
    })),
    yAxis: [
      { gridIndex: 0, type: "value", scale: true, splitNumber: 4, axisLabel: axisText, splitLine },
      { gridIndex: 1, type: "value", min: 0, max: 100, interval: 25, axisLabel: axisText, splitLine },
      { gridIndex: 1, type: "value", position: "right", scale: true, splitNumber: 4, axisLabel: axisText, splitLine: { show: false } },
      { gridIndex: 2, type: "value", scale: true, splitNumber: 3, axisLabel: axisText, splitLine },
    ],
    axisPointer: { link: [{ xAxisIndex: "all" }] },
    tooltip: {
      trigger: "axis", confine: true, renderMode: "richText", axisPointer: { type: "line" },
      formatter: params => {
        const item = Array.isArray(params) ? params[0] : params;
        const point = item && dateToPoint.get(item.name);
        if (!point) return "";
        const diagnosis = point.regime_diagnosis && regimes[point.regime_diagnosis].title;
        return [
          point.date,
          ...series.map(spec => `${spec.name}  ${number(point[spec.field], spec.axis === 0 ? " 个百分点" : spec.unit)}`),
          `分化历史分位  ${number(point.disp_pct_252d, "%", 1)} · ${point.disp_sample_count ?? "—"}期`,
          `20日实现波动率  ${number(point.index_rv20)} · 分位 ${number(point.rv20_pct_252d, "%", 1)}`,
          ...(point.high_disp_low_breadth ? ["高分化、低宽度"] : []),
          ...(diagnosis ? [diagnosis] : []),
        ].join("\n");
      },
    },
    dataZoom: [
      { type: "inside", xAxisIndex: [0, 1, 2], filterMode: "none" },
      { type: "slider", xAxisIndex: [0, 1, 2], filterMode: "none", height: 18, bottom: 10, showDetail: false, textStyle: axisText },
    ],
    series: [
      ...(showRails ? thresholdBand(points) : []), ...lines,
      {
        name: "高分化、低宽度", type: "scatter", xAxisIndex: 1, yAxisIndex: 1, symbolSize: 5,
        data: points.map(point => point.high_disp_low_breadth ? point.pct_above_ma20 : null),
        itemStyle: { color: colors.warning }, z: 5,
      },
    ],
  };
}

function LinkedCharts({ points, series, showRails }: { points: MemberDispersionPoint[]; series: SeriesSpec[]; showRails: boolean }) {
  const node = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);
  useEffect(() => {
    if (!node.current) return;
    const element = node.current;
    chart.current = echarts.init(element, undefined, { renderer: "svg" });
    const observer = new ResizeObserver(() => chart.current?.resize());
    observer.observe(element);
    return () => {
      observer.disconnect();
      chart.current?.dispose();
      chart.current = null;
    };
  }, []);
  useEffect(() => {
    chart.current?.setOption(chartOption(points, series, showRails), { replaceMerge: ["series"] });
  }, [points, series, showRails]);
  return <div ref={node} className="md-linked-charts" role="img" aria-label="同一交易日联动展示成员分化、宽度与指数收盘、行业和个股分化比值" />;
}

function Rules({ card }: { card: MemberDispersionCard }) {
  const r = card.rules;
  return <details className="md-definitions">
    <summary>诊断条件与资料口径</summary>
    <p>使用分化5日均值历史分位、站上20日线的成员占比和指数20日年化实现波动率历史分位。三项齐备后，依次匹配以下条件，以首个命中为准。</p>
    <ol>
      <li>{regimes.PANIC.title}。分化分位 ≤ {r.low_disp}%，宽度 ≤ {r.panic_breadth}%，波动率分位 ≥ {r.high_rv}%。</li>
      <li>{regimes.VOLATILE_DISAGREEMENT.title}。分化分位 ≥ {r.extreme_disp}%，波动率分位 ≥ {r.high_rv}%。</li>
      <li>{regimes.SIPHON_WARNING.title}。分化分位 ≥ {r.extreme_disp}% 且宽度 &lt; {r.thin_breadth}%，或宽度连续{r.divergence_days}个交易日下降而指数收盘不低于这段开始前的收盘。</li>
      <li>{regimes.HEALTHY_ROTATION.title}。分化分位 ≥ {r.high_disp}%，宽度 ≥ {r.healthy_breadth}%，波动率分位 &lt; {r.high_rv}%。</li>
      <li>{regimes.BROAD_TREND.title}。分化分位 ≤ {r.low_disp}%，宽度 ≥ {r.broad_breadth}%。</li>
      <li>{regimes.BALANCED.title}。其余组合。</li>
    </ol>
    <p>单日分化取固定样本成员日收益率的横截面标准差。分化参考线取此前最多 {r.window} 个交易日内5日均值的 P20、P50、P80，至少需要 {r.min_samples} 条有效历史读数。宽度是站上对应均线的成员占比。</p>
    <p>行业/个股分化是两者单日分化之比的5日均值，用于观察两层分化的相对强弱。比值分位 ≥ 80% 记为高位，≤ 20% 记为低位。阴影与圆点标示高分化、低宽度。</p>
    <dl className="md-sources">
      <dt>成员</dt><dd>{card.sources.members}</dd>
      <dt>宽度</dt><dd>{card.sources.breadth}</dd>
      <dt>宽基</dt><dd>{card.sources.index}</dd>
      <dt>行业</dt><dd>{card.sources.sectors}</dd>
    </dl>
  </details>;
}

export function MemberDispersionDetail({ card }: { card: MemberDispersionCard }) {
  const [period, setPeriod] = useState(252);
  const [showRails, setShowRails] = useState(true);
  const [showIndustry, setShowIndustry] = useState(false);
  const points = useMemo(() => period ? card.points.slice(-period) : card.points, [card.points, period]);
  const current = card.points[lastReadingIndex(card.points)];
  const latestChartDate = points[points.length - 1].date;
  const lastRatio = current.sector_dominance_ratio === null
    ? card.points.slice(0, lastReadingIndex(card.points) + 1).reverse().find(point => point.sector_dominance_ratio !== null)
    : undefined;
  const industryAvailable = points.some(point => point.sector_disp_raw !== null);
  const ratioAvailable = points.some(point => point.sector_dominance_ratio !== null);
  const status = current.regime_diagnosis && regimes[current.regime_diagnosis];
  const series = useMemo(() => [
    raw, ma5, ma20, ...(showRails ? rails : []), ...(showIndustry && industryAvailable ? [sector] : []), ...breadth, ratio,
  ], [showRails, showIndustry, industryAvailable]);
  return <section className="md-detail" aria-label="成员分化历史与复合诊断">
    <div className="md-controls">
      <div className="md-periods" role="group" aria-label="图表日期范围">
        {[60, 120, 252, 0].map(n => <button key={n} type="button" aria-pressed={period === n}
          onClick={() => setPeriod(n)}>{n ? `近${n}期` : "全部"}</button>)}
      </div>
      <label><input type="checkbox" checked={showRails} onChange={event => setShowRails(event.target.checked)} /> 历史参考线</label>
      <label><input type="checkbox" checked={showIndustry && industryAvailable} disabled={!industryAvailable}
        onChange={event => setShowIndustry(event.target.checked)} /> 行业分化{!industryAvailable && "（本区间待补）"}</label>
    </div>
    <div className="md-readings">
      <p><b>历史快照</b> {points[0].date} 至 {latestChartDate}</p>
      <p><b>分化读数日期</b> <time dateTime={current.date}>{current.date}</time> · 分化有效参考 {current.disp_sample_count ?? "—"} 期（最多 {card.rules.window} 期）</p>
      <p><b>环境</b> {status ? `${status.title} · ${status.hint}` : "诊断资料待齐"} · 站上20日线 {number(current.pct_above_ma20, "%", 1)}</p>
      {status && <p><b>工具观察</b> {status.tools}</p>}
      <p><b>最新参考（百分点）</b> P20 {number(current.disp_p20, "")} · P50 {number(current.disp_p50, "")} · P80 {number(current.disp_p80, "")}</p>
      <p><b>指数20日年化实现波动率</b> {number(current.index_rv20)} · 历史分位 {number(current.rv20_pct_252d, "%", 1)} · 有效参考 {current.rv_sample_count ?? "—"} 期</p>
      <p><b>行业主导率</b> {sectorReading(current)}{!ratioAvailable && " · 本区间暂无有效比值"}</p>
      {lastRatio && <p><b>最近有效行业主导率</b> <time dateTime={lastRatio.date}>{lastRatio.date}</time> · {sectorReading(lastRatio)}</p>}
    </div>
    <ChartLegend items={[
      ...series.map(spec => ({ label: spec.name, color: spec.color, dashed: spec.dashed })),
      { label: "高分化、低宽度", color: colors.warning },
    ]} />
    <LinkedCharts key={`${card.id}-${period}`} points={points} series={series} showRails={showRails} />
    <Rules card={card} />
  </section>;
}
