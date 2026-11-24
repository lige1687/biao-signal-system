import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import * as echarts from "echarts";
import type { FocusMomentumObservation, FocusMomentumPoint } from "./data";
import { useRecentFocusMomentum as useFocusMomentumObservation } from "./recent";
import { FocusMomentumMappingPanel } from "./mapping";
import { FocusMomentumPriceProjection } from "./price-projection";
import "./focus-momentum.css";

const OBSERVATION_LINK = "/factors?wb=observation";
const percent = (value: number, digits = 1) => `${(value * 100).toFixed(digits)}%`;
const pp = (value: number, digits = 2) => `${value > 0 ? "+" : ""}${(value * 100).toFixed(digits)}个百分点`;
const ppNumber = (value: number, digits = 3) => (value * 100).toFixed(digits);

function LoadProblem({ message, retry }: { message: string; retry: () => void }) {
  return <div className="fm-error" role="alert">
    <span>{message}；无法确认历史观察读数。</span>
    <button type="button" onClick={retry}>重试读取</button>
  </div>;
}

function HistoryDate({ data }: { data: FocusMomentumObservation }) {
  return <span className="fm-history-date">历史样本截至 {data.asOf} · 今日读数未知</span>;
}

export function FocusMomentumHomeObservation() {
  const query = useFocusMomentumObservation();
  const data = query.data;
  return <section className="fm-home" aria-label="市场与情绪观察：焦点股动量">
    <header className="fm-home-head"><h2>市场与情绪观察</h2><span>A股 · 固定300股独立版本</span><Link to={OBSERVATION_LINK}>曲线与效果 →</Link></header>
    {query.isError ? <LoadProblem message={query.error instanceof Error ? query.error.message : "观察资料读取失败"} retry={() => void query.refetch()} />
      : data ? <>
        <div className="fm-home-date"><HistoryDate data={data} /></div>
        <div className="fm-home-values">
          <div className="fm-home-primary"><span>焦点股动量 · 过去20日</span><div><strong>{percent(data.latest.focus, 2)}</strong><b>{data.latest.focus > 0 ? "当日零线上方" : data.latest.focus < 0 ? "当日零线下方" : "当日在零线"}</b></div><small>{data.latest.changeFocus == null ? "前日变化未知" : `较前一个有效日 ${pp(data.latest.changeFocus)}`}</small></div>
          <div><span>同池平均涨跌 · 20日</span><strong>{percent(data.latest.poolMomentum, 2)}</strong></div>
          <div><span>上涨股票比例 · 20日</span><strong>{percent(data.latest.breadth, 1)}</strong></div>
          <div><span>焦点组成交额占比 · 20日</span><strong>{percent(data.latest.concentration, 1)}</strong></div>
        </div>
        <p className="fm-home-note">历史状态：{data.latest.qualifiedCount}股合格、{data.latest.focusCount}股入选；负值表示过去平均下跌，不能直接判断底部。最新交易日尚未补齐。</p>
      </> : <p className="fm-muted" role="status">正在读取模型历史值；今日读数未知。</p>}
  </section>;
}

export function FocusMomentumSummary() {
  const query = useFocusMomentumObservation();
  return <section className="fm-summary" aria-label="焦点股动量研究观察">
    <div className="fm-summary-heading"><div><span className="fm-eyebrow">市场状态研究</span><h3>焦点股动量</h3></div><span className="fm-tag">独立历史版本</span></div>
    {query.isError ? <LoadProblem message={query.error instanceof Error ? query.error.message : "观察资料读取失败"} retry={() => void query.refetch()} />
      : query.data ? <>
        <HistoryDate data={query.data} />
        <p>固定300股历史样本中的活跃股票，过去20个交易日平均涨跌为 <strong>{percent(query.data.latest.focus)}</strong>。这仅描述该日的市场状态。</p>
        <p className="fm-caveat">研究未见跌破零对下一个交易月宽基走势有稳定预测增量；原视频公式未公开，美股未评价。</p>
        <Link to={OBSERVATION_LINK} className="fm-link">查看曲线与研究依据 →</Link>
      </> : <p className="fm-muted">正在读取历史观察资料；今日读数未知。</p>}
  </section>;
}

type Range = "1y" | "3y" | "all";
function filteredSeries(data: FocusMomentumObservation, range: Range): FocusMomentumPoint[] {
  if (range === "all") return data.series;
  const cutoff = new Date(`${data.asOf}T00:00:00Z`);
  cutoff.setUTCFullYear(cutoff.getUTCFullYear() - (range === "1y" ? 1 : 3));
  const min = cutoff.toISOString().slice(0, 10);
  return data.series.filter(point => point.date >= min);
}

function HistoricalCharts({ points }: { points: FocusMomentumPoint[] }) {
  const node = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!node.current || !points.length) return;
    const chart = echarts.init(node.current, undefined, { renderer: "canvas" });
    const dates = points.map(p => p.date);
    const baseLine = { type: "line" as const, symbol: "none", smooth: false, animation: false, emphasis: { focus: "series" as const } };
    const option: echarts.EChartsOption = {
      aria: { enabled: true, decal: { show: false } },
      animation: false,
      color: ["#176f63", "#967246", "#397ca2", "#b56840"],
      title: [
        { text: "焦点与同池过去20日涨跌", left: 14, top: 5, textStyle: { fontSize: 14, color: "#213c37", fontWeight: 600 } },
        { text: "上涨股票比例与焦点成交额占比", left: 14, top: "51%", textStyle: { fontSize: 14, color: "#213c37", fontWeight: 600 } },
      ],
      legend: [
        { data: ["焦点股动量", "同池平均"], left: 12, top: 34, textStyle: { color: "#53675f" } },
        { data: ["上涨比例", "成交占比"], left: 12, top: "56%", textStyle: { color: "#53675f" } },
      ],
      tooltip: { trigger: "axis", confine: true, valueFormatter: value => typeof value === "number" ? `${value.toFixed(2)}%` : String(value ?? "—") },
      axisPointer: { link: [{ xAxisIndex: [0, 1] }] },
      grid: [
        { top: 78, left: 55, right: 22, height: "29%" },
        { top: "62%", left: 55, right: 22, height: "23%" },
      ],
      xAxis: [0, 1].map((gridIndex) => ({ type: "category" as const, gridIndex, data: dates, boundaryGap: false,
        axisLabel: { hideOverlap: true, color: "#657874", formatter: (value: string) => value.slice(0, 7) },
        axisLine: { lineStyle: { color: "#b8c9c2" } } })),
      yAxis: [
        { type: "value", gridIndex: 0, scale: true, axisLabel: { formatter: "{value}%" }, splitLine: { lineStyle: { color: "#edf1ee" } } },
        { type: "value", gridIndex: 1, min: 0, max: 100, axisLabel: { formatter: "{value}%" }, splitLine: { lineStyle: { color: "#edf1ee" } } },
      ],
      dataZoom: [
        { type: "inside", xAxisIndex: [0, 1], filterMode: "none" },
        { type: "slider", xAxisIndex: [0, 1], filterMode: "none", bottom: 8, height: 22, borderColor: "#d6e2dc", fillerColor: "rgba(23,111,99,.12)" },
      ],
      series: [
        { ...baseLine, name: "焦点股动量", xAxisIndex: 0, yAxisIndex: 0, data: points.map(p => p.focus * 100), lineStyle: { width: 2.2 },
          markLine: { silent: true, symbol: "none", label: { formatter: "0 参考线", position: "insideEndTop", color: "#788a82" }, lineStyle: { color: "#9caea5", type: "dashed" }, data: [{ yAxis: 0 }] } },
        { ...baseLine, name: "同池平均", xAxisIndex: 0, yAxisIndex: 0, data: points.map(p => p.poolMomentum * 100), lineStyle: { width: 1.8 } },
        { ...baseLine, name: "上涨比例", xAxisIndex: 1, yAxisIndex: 1, data: points.map(p => p.breadth * 100), lineStyle: { width: 1.9 } },
        { ...baseLine, name: "成交占比", xAxisIndex: 1, yAxisIndex: 1, data: points.map(p => p.concentration * 100), lineStyle: { width: 1.9 } },
      ],
    };
    chart.setOption(option);
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(node.current);
    return () => { observer.disconnect(); chart.dispose(); };
  }, [points]);
  return <div className="fm-chart" ref={node} role="img" aria-label={`两张历史曲线：焦点股与同池平均涨跌，上涨股票比例与成交额占比，共${points.length}个交易日`} />;
}

function ResearchComparison({ data }: { data: FocusMomentumObservation }) {
  return <details className="fm-details">
    <summary>展开研究对照：跌破零有没有提高预测准确度</summary>
    <p>比较未来{data.research.horizonSessions}个交易日宽基涨跌的平均预测误差；误差越低越好。以下数值单位均为收益率百分点。</p>
    <div className="fm-table-scroll"><table><thead><tr><th scope="col">宽基</th><th scope="col">仅用已有市场信息</th><th scope="col">加入焦点低于零</th><th scope="col">误差减少</th><th scope="col">误差减少的95%估计范围</th></tr></thead>
      <tbody>{data.research.comparisons.map(item => <tr key={item.target}><th scope="row">{item.label}</th><td>{ppNumber(item.baselineMae)}</td><td>{ppNumber(item.withZeroMae)}</td><td>{pp(item.improvement, 3)}</td><td>{pp(item.interval[0], 3)} 至 {pp(item.interval[1], 3)}</td></tr>)}</tbody></table></div>
    <p>正的“误差减少”才表示改善。历史窗口重叠，范围不是未来保证；本研究未见稳定增量，也未评价账户收益。</p>
  </details>;
}

export function FocusMomentumPanel() {
  const query = useFocusMomentumObservation();
  const [range, setRange] = useState<Range>("1y");
  const [chartView, setChartView] = useState<"projection" | "history" | "mapping">("projection");
  const data = query.data;
  const points = useMemo(() => data ? filteredSeries(data, range) : [], [data, range]);
  const reportLink = data ? `/library?report=${encodeURIComponent(data.research.reportPath)}` : OBSERVATION_LINK;
  return <div className="fm-panel">
    <header className="fm-panel-head"><div><span className="fm-eyebrow">A股 · 市场状态研究</span><h2>焦点股动量</h2><p>看固定历史样本里成交活跃股票近期是涨是跌；不参与系统买卖判定。</p></div><span className="fm-tag">独立历史版本</span></header>
    {query.isError ? <LoadProblem message={query.error instanceof Error ? query.error.message : "观察资料读取失败"} retry={() => void query.refetch()} />
      : !data ? <p className="fm-muted" role="status">正在读取历史观察资料；今日读数未知。</p>
      : <>
        <div className="fm-notice"><HistoryDate data={data} /><span>当前值未提供，普通刷新不会增加新交易日。</span></div>
        <div className="fm-metrics" aria-label="最新历史日观察读数">
          <div className="fm-metric-primary"><span>焦点股过去20日平均涨跌</span><strong>{percent(data.latest.focus, 2)}</strong><small>{data.latest.changeFocus == null ? "前日变化未知" : `较前一个有效日 ${pp(data.latest.changeFocus)}`}</small></div>
          <div><span>同池平均涨跌</span><strong>{percent(data.latest.poolMomentum, 2)}</strong></div>
          <div><span>20日上涨股票比例</span><strong>{percent(data.latest.breadth, 1)}</strong></div>
          <div><span>焦点组成交额占比</span><strong>{percent(data.latest.concentration, 1)}</strong></div>
          <div><span>当日合格 / 入选</span><strong>{data.latest.qualifiedCount} / {data.latest.focusCount}</strong><small>固定300股历史池内</small></div>
        </div>
        <div className="fm-range fm-view-switch" role="group" aria-label="焦点动量图表视图"><button type="button" aria-pressed={chartView === "projection"} onClick={() => setChartView("projection")}>价格投影</button><button type="button" aria-pressed={chartView === "history"} onClick={() => setChartView("history")}>模型历史走势</button><button type="button" aria-pressed={chartView === "mapping"} onClick={() => setChartView("mapping")}>后续涨跌研究</button></div>
        {chartView === "projection" ? <FocusMomentumPriceProjection data={data} /> : chartView === "mapping" ? (data.mapping ? <FocusMomentumMappingPanel mapping={data.mapping} /> : <p className="fm-muted">映射资料尚未读取，请重新加载页面。</p>) : <>
        <div className="fm-range" role="group" aria-label="历史曲线范围"><span>查看范围（截至资料末日）</span>
          {([ ["1y", "近1年"], ["3y", "近3年"], ["all", "全部"] ] as const).map(([key, label]) => <button key={key} type="button" aria-pressed={range === key} onClick={() => setRange(key)}>{label}</button>)}
        </div>
        {points.length ? <HistoricalCharts points={points} /> : <p className="fm-muted">所选范围暂无历史读数。</p>}
        <details className="fm-details"><summary>查看所选范围最近20个交易日数值</summary><div className="fm-table-scroll"><table><thead><tr><th>日期</th><th>焦点涨跌</th><th>同池涨跌</th><th>上涨比例</th><th>成交占比</th></tr></thead><tbody>{points.slice(-20).reverse().map(p => <tr key={p.date}><th scope="row">{p.date}</th><td>{percent(p.focus, 2)}</td><td>{percent(p.poolMomentum, 2)}</td><td>{percent(p.breadth, 1)}</td><td>{percent(p.concentration, 1)}</td></tr>)}</tbody></table></div></details>
        </>}
        <section className="fm-reading"><h3>怎么读这条线</h3><p>焦点股动量低于零，表示这批成交活跃股票过去20个交易日平均下跌。曲线成员每天随成交额重新选择；零线是涨跌分界，历史检验没有发现它能稳定预示宽基反弹。</p>
          <p><strong>范围：</strong>{data.scope.label}。{data.scope.selection}{data.scope.method}原视频完整算法未公开，本页不是原式复现，也不是全A股读数。</p>
          <p><strong>边界：</strong>美股尚未评价，今日读数未知，不能据这条线推断当前买卖或账户收益。</p>
        </section>
        <details className="fm-details"><summary>配套观察指标：金融含义与使用边界</summary>
          <p><strong>焦点股动量：</strong>成交活跃那部分股票过去20日的平均涨跌，观察热门部分的价格强弱；大成交额不等于行业龙头，低于零不直接等于冰点。</p>
          <p><strong>同池平均动量：</strong>全部合格样本过去20日的等权平均涨跌。与焦点值对照，可辨认活跃股票是否比样本整体更强。</p>
          <p><strong>上涨股票比例：</strong>合格样本中过去20日上涨的股票占比，观察上涨参与面。它与首页另一项“站上均线的比例”定义不同，不能混用阈值。</p>
          <p><strong>焦点组成交额占比：</strong>焦点组近20日平均成交额占全部合格样本对应成交额的比例，观察交易关注的集中程度；不是全A股当日占比，也不是资金净流入。</p>
          <p>一起看时：焦点较强而上涨比例低，表示强势较集中；两者同时改善，表示价格回升与参与面扩大同时出现。这里描述历史状态，不推断下一步必然涨跌。</p>
        </details>
        <ResearchComparison data={data} />
        <p className="fm-source"><Link to={`/library?report=${encodeURIComponent("docs/experiments/focus-momentum-turning-points-2026-10-25.md")}`}>阶段顶底检验：沪深300、创业板指与科创50 →</Link><span> · 提前命中、误报漏报与已有信息对照</span></p>
        <p className="fm-source">研究资料截至 {data.research.asOf} · {data.research.period} · {data.research.conclusion}。<Link to={reportLink}>查看完整报告与反例 →</Link></p>
      </>}
  </div>;
}
