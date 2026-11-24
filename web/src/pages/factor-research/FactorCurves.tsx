import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import * as echarts from "echarts";
import { safeReportHref } from "./model";
import { CURVE_QUERY_KEYS, GROUP_COLORS, assessmentView, comparisonRows, defaultSelection, defaultReturnMode, diagnosticView, feeLabel, metricNumber, percent, percentagePoints, priceSegments, returnDisplay, selectCurves, type CurveDocument, type CurveSelection, type DisplaySeries, type CurveReturnMode } from "./factorCurvesModel";
import { loadCurveLibrary } from "./factorCurvesModel";
import "./factor-curves.css";

type Selected = ReturnType<typeof selectCurves>;
const metricColumns = [
  ["return", "累计变化"], ["cagr", "年均变化"], ["max_drawdown", "区间最大跌幅"],
  ["volatility", "日变动幅度 / 年化"], ["cash_mean", "平均现金"],
  ["unknown_mean", "平均缺价"], ["gross_turnover_monthly", "每月买卖金额 / 资产"],
] as const;

function CurvesChart({ selected, visible, display, mode }: { selected: Selected; visible: string[]; display: ReturnType<typeof returnDisplay>; mode: CurveReturnMode }) {
  const ref = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);
  const [plotSize, setPlotSize] = useState({ width: 0, height: 0 });
  useEffect(() => {
    if (!ref.current) return;
    const instance = echarts.init(ref.current, undefined, { renderer: "svg" });
    chart.current = instance;
    const observer = new ResizeObserver(() => {
      instance.resize();
      const width = ref.current?.clientWidth || 0; const height = ref.current?.clientHeight || 0;
      setPlotSize(previous => previous.width === width && previous.height === height ? previous : { width, height });
    });
    observer.observe(ref.current);
    return () => { observer.disconnect(); instance.dispose(); chart.current = null; };
  }, []);
  useEffect(() => {
    if (!chart.current) return;
    const dates = display.dates;
    const shown = display.series.filter(s => visible.includes(s.id));
    const lines: echarts.LineSeriesOption[] = [];
    shown.forEach(s => {
      const aligned = s.points;
      priceSegments(aligned.map(p => ({ ...p, unknownMax: mode === "excess" && p.comparisonUncertain ? null : p.unknownMax })), true).forEach((segment, index) => lines.push({
        id: `${s.id}-price-${index}`, name: s.label, type: "line", xAxisIndex: 0, yAxisIndex: 0,
        data: segment.values, showSymbol: false, connectNulls: false,
        lineStyle: { color: s.color, width: s.id === "pool" || s.id === "G5" ? 2.5 : 1.5, type: segment.uncertain ? "dashed" : "solid", opacity: s.id === "pool" || s.id === "G5" ? 1 : .75 },
        itemStyle: { color: s.color }, emphasis: { disabled: true },
      }));
      lines.push({ id: `${s.id}-drawdown`, name: s.label, type: "line", xAxisIndex: 1, yAxisIndex: 1, data: aligned.map(p => p.drawdown), showSymbol: false, connectNulls: false, lineStyle: { color: s.color, width: s.id === "G5" || s.id === "pool" ? 2 : 1, opacity: .85 }, itemStyle: { color: s.color }, emphasis: { disabled: true } });
    });
    const axis = { type: "category" as const, data: dates, boundaryGap: false, axisLabel: { color: "#526273", fontSize: 12, hideOverlap: true, formatter: (v: string) => v.slice(0, 7) }, axisLine: { lineStyle: { color: "#d7dee3" } }, axisTick: { show: false } };
    const regimeAreas = selected.regime.id === "all" ? [] : selected.regime.intervals.map(interval => [{ xAxis: interval.start, itemStyle: { color: "rgba(22,116,97,.08)" } }, { xAxis: interval.end }]);
    // Explicit index mapping keeps regime shading on the existing continuous monthly calendar.
    const areas = regimeAreas.map((_, i) => {
      const interval = selected.regime.intervals[i];
      const index = dates.findIndex(date => date >= interval.start);
      const first = index < 0 ? undefined : dates[Math.max(0, index - 1)];
      const last = [...dates].reverse().find(date => date <= interval.end);
      return first && last && first <= last ? [{ xAxis: first }, { xAxis: last }] : null;
    }).filter((v): v is { xAxis: string }[] => v !== null);
    if (areas.length && lines.length) lines[0].markArea = { silent: true, itemStyle: { color: selected.regime.id === "strong" ? "rgba(22,116,97,.08)" : "rgba(92,108,124,.11)" }, data: areas as echarts.MarkAreaComponentOption["data"] };
    const firstBottom = Math.round((ref.current?.clientHeight || 420) * .56);
    chart.current.setOption({
      animation: false,
      grid: [{ top: 35, left: 54, right: 38, height: firstBottom - 35 }, { top: firstBottom + 66, left: 54, right: 38, bottom: 34 }],
      title: [{ text: mode === "excess" ? "相对同池基准超额（百分点）" : "绝对累计收益（%）", left: 10, top: 4, textStyle: { fontSize: 12, fontWeight: "normal", color: "#526273" } }, { text: currentDrawdownTitle(selected), left: 10, top: firstBottom + 36, textStyle: { fontSize: 11, fontWeight: "normal", color: "#526273" } }],
      xAxis: [{ ...axis, gridIndex: 0 }, { ...axis, gridIndex: 1 }],
      yAxis: [0, 1].map(gridIndex => ({ type: "value", gridIndex, scale: gridIndex === 0, axisLabel: { formatter: (v: number) => `${v.toFixed(0)}${gridIndex === 0 && mode === "excess" ? "" : "%"}`, color: "#6b7785" }, splitLine: { lineStyle: { color: "#edf0f3" } } })),
      axisPointer: { link: [{ xAxisIndex: "all" }] },
      tooltip: { trigger: "axis", renderMode: "richText", confine: true, formatter: (input: unknown) => {
        const params = input as { axisValue?: string; axisIndex?: number }[];
        const day = params[0]?.axisValue || "";
        const drawdown = params[0]?.axisIndex === 1;
        return `${day}\n${shown.map(s => {
          const p = s.points.find(p => p.date === day);
          const fmt = (v: number | null | undefined, unit = "%") => v == null ? "缺少报价" : `${v.toFixed(2)}${unit}`;
          const value = drawdown ? `原账户回撤 ${fmt(p?.drawdown)}` : mode === "excess" ? `超额 ${fmt(p?.excessValue, "个百分点")} | 自身 ${fmt(p?.absoluteValue)} | 基准 ${fmt(p?.benchmarkValue)}` : `自身 ${fmt(p?.absoluteValue)} | 基准 ${fmt(p?.benchmarkValue)}`;
          return `${s.label}  ${value} | 本组月内缺价最高 ${fmt(p?.unknownMax)} | 基准月内缺价最高 ${fmt(p?.benchmarkUnknownMax)}`;
        }).join("\n")}`;
      } }, series: lines,
    }, true);
  }, [selected, visible, display, mode, plotSize]);
  return <div className="fc-chart" ref={ref} role="img" aria-label={mode === "excess" ? "五组相对同池基准累计超额，单位百分点，基准为零线；下图仍为原账户每月最深日回撤。" : "五组与共同池基准绝对累计收益，单位百分比；下图为原账户每月最深日回撤。"} />;
}

function currentDrawdownTitle(selected: Selected) {
  return selected.drawdownRebased ? "区间内每月最深日回撤" : "每月最深日回撤（沿全历史高点）";
}

function ExactMetrics({ series }: { series: DisplaySeries[] }) {
  return <section className="fc-metrics" aria-labelledby="fc-metrics-title"><div className="fc-section-title"><h3 id="fc-metrics-title">收益、风险与代价</h3><span>所选区间的原始日度统计</span></div><div className="fc-table-scroll"><table><thead><tr><th scope="col">分组</th>{metricColumns.map(([key, label]) => <th key={key} scope="col">{label}</th>)}</tr></thead><tbody>{series.map(s => <tr key={s.id} className={s.id === "pool" ? "fc-baseline" : s.id === "G5" ? "fc-preferred" : ""}><th scope="row"><i style={{ background: s.color }} />{s.label}</th>{metricColumns.map(([key]) => <td key={key}>{percent(metricNumber(s.metrics, key), key === "return" || key === "cagr")}</td>)}</tr>)}</tbody></table></div><p>年化变动幅度说明资金起伏；平均现金、缺价和换手体现等待与操作代价。各组不按结果重新排序。</p></section>;
}

function IncrementTable({ selected, selection }: { selected: Selected; selection: CurveSelection }) {
  const rows = comparisonRows(selected.dataset, selection);
  if (!rows.length) return <p className="fc-small">相对简单方法的差额尚未接入。</p>;
  const number = (v: unknown) => typeof v === "number" && Number.isFinite(v) ? v : null;
  return <details className="fc-fold"><summary>G5 相对简单方法的差额 <small>固定单边费用0.25%</small></summary><p>下表沿用原研究的含费对比；独立于上方费用切换。上涨月少赚、下跌月少亏需一起看。</p><div className="fc-table-scroll"><table><thead><tr><th>简单对手</th><th>每月平均差额</th><th>历史不确定范围</th><th>上涨月差额</th><th>下跌月差额</th><th>最大跌幅改善</th></tr></thead><tbody>{rows.map(({ key, label, item }) => <tr key={key}><th>{label}</th><td>{percentagePoints(number(item!.mean))}</td><td>{Array.isArray(item!.descriptive95) ? `${percentagePoints(number(item!.descriptive95[0]))} 至 ${percentagePoints(number(item!.descriptive95[1]))}` : "未提供"}</td><td>{percentagePoints(number(item!.up_month_difference))}</td><td>{percentagePoints(number(item!.down_month_difference))}</td><td>{percentagePoints(number(item!.drawdown_difference))}</td></tr>)}</tbody></table></div><p>差额为百分点，按已有相关月份计算；不代表已经排除缺价、选池或多次查看历史的影响。</p></details>;
}

function EnvironmentStats({ selected, selection }: { selected: Selected; selection: CurveSelection }) {
  if (selected.regime.id === "all") return null;
  const columns = [["meanReturn", "每月平均变化"], ["meanBenchmarkDifference", "比共同池每月差额"], ["lossMonthFraction", "下跌月份占比"], ["meanUpBenchmarkDifference", "共同池上涨月差额"], ["meanDownBenchmarkDifference", "共同池下跌月差额"], ["meanMonthlyPeakUnknown", "月内缺价最高值的平均"]] as const;
  return <section className="fc-metrics"><div className="fc-section-title"><h3>{selected.regime.regimeLabel}时怎样</h3><span>只读该类月份的条件统计，主曲线保持完整</span></div><div className="fc-table-scroll"><table><thead><tr><th>分组</th><th>月份数</th>{columns.map(([key, label]) => <th key={key}>{label}</th>)}</tr></thead><tbody>{selected.series.map(s => {
    const key = s.id === "pool" ? `${selection.pool}__pool__fee${selection.fee}` : `${selection.pool}__${selection.curveFactor}__${s.id}__fee${selection.fee}`;
    const stats = selected.dataset.regimeStatistics?.[key]?.[selection.period]?.[selected.regime.id];
    return <tr key={s.id}><th><i style={{ background: s.color }} />{s.label}</th><td>{typeof stats?.months === "number" ? stats.months : "未提供"}</td>{columns.map(([field]) => <td key={field}>{field.includes("Difference") ? percentagePoints(typeof stats?.[field] === "number" ? stats[field] as number : null) : percent(typeof stats?.[field] === "number" ? stats[field] as number : null)}</td>)}</tr>;
  })}</tbody></table></div><p>每月平均为算术平均；差额以百分点表示。这些不连续月份未拼成账户，也未计算该状态内的累计收益、年均收益或最大跌幅。</p></section>;
}

function DiagnosticChart({ option, label, height = 230 }: { option: echarts.EChartsOption; label: string; height?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);
  useEffect(() => {
    if (!ref.current) return;
    const instance = echarts.init(ref.current, undefined, { renderer: "canvas" });
    chart.current = instance;
    const observer = new ResizeObserver(() => instance.resize()); observer.observe(ref.current);
    return () => { observer.disconnect(); instance.dispose(); chart.current = null; };
  }, []);
  useEffect(() => { chart.current?.setOption(option, true); }, [option]);
  return <div className="fc-diagnostic-chart" ref={ref} style={{ height }} role="img" aria-label={label} />;
}

function ResearchHighlights({ selected, selection, generatedAt, onOpen }: { selected: Selected; selection: CurveSelection; generatedAt?: string; onOpen: () => void }) {
  const view = assessmentView(selected.dataset, selection);
  const rank = view.rankIC[0];
  const value = (n: number | null) => n === null ? "未评价" : n.toFixed(3);
  return <aside className="fc-research-highlights" aria-label="主图旁的RankIC与夏普摘要">
    <h3>排序与风险收益</h3><p className="fc-highlight-period">{selected.range[0]} 至 {selected.range[1]}</p>
    <section><h4>排序预测能力 <span>RankIC</span></h4>
      {rank ? <><strong className="fc-highlight-value">{value(rank.mean)}</strong><p>{rank.horizon} · 有效{rank.nPeriods}期</p><p>每期至少{rank.minAssets}只 · 标的结果覆盖{percent(rank.coverage)}</p><p>不确定范围 {value(rank.uncertainty.lower)} 至 {value(rank.uncertainty.upper)}</p></> : <><strong className="fc-highlight-empty">未评价</strong><p>本组合尚无合格的逐标的排序统计。</p></>}
      <small>检查排在前面的标的之后是否更好；不等于胜率。</small>
    </section>
    <section><h4>收益与波动的比值 <span>夏普</span></h4>
      {view.sharpe.length ? <><dl className="fc-highlight-sharpe">{view.sharpe.map(r => <div key={r.streamId}><dt>{r.streamId.includes("__pool__") ? "同池基准" : "G5高分组"}</dt><dd>{value(r.value)}</dd></div>)}</dl><p>{feeLabel(Number(selection.fee))}</p><small>{view.sharpe.every(r => r.riskFree.kind === "zero_assumption") ? "无风险收益假设为0。" : "无风险参考按原来源。"}频率和计算限制见详细口径。</small></> : <><strong className="fc-highlight-empty">未评价</strong><p>本组合尚无口径完整的夏普值。</p></>}
    </section>
    <a href="#fc-assessment-details" onClick={onOpen}>逐期曲线、覆盖与计算口径</a>
    <small className="fc-highlight-source">目录生成 {generatedAt?.slice(0, 10) || "未记录"}；已看历史报价模拟。</small>
  </aside>;
}

function ResearchMetrics({ selected, selection, open, onOpenChange }: { selected: Selected; selection: CurveSelection; open: boolean; onOpenChange: (open: boolean) => void }) {
  const [horizon, setHorizon] = useState("");
  const view = assessmentView(selected.dataset, selection);
  const rank = view.rankIC.find(r => r.horizon === horizon) ?? view.rankIC[0];
  const number = (v: number | null) => v === null ? "未评价" : v.toFixed(3);
  const frequencies = { daily: "日", weekly: "周", monthly: "月" };
  const option: echarts.EChartsOption = {
    animation: false, grid: { top: 20, left: 50, right: 20, bottom: 35 },
    xAxis: { type: "category", data: rank?.points.map(p => p[0]) ?? [], axisLabel: { hideOverlap: true } },
    yAxis: { type: "value", min: -1, max: 1 },
    tooltip: { trigger: "axis", renderMode: "richText" },
    series: [{ type: "line", name: "RankIC", showSymbol: false, connectNulls: false, itemStyle: { color: "#167461" }, data: rank?.points.map(p => p[1]) ?? [] }],
  };
  return <details id="fc-assessment-details" className="fc-fold fc-assessment" open={open} onToggle={e => onOpenChange(e.currentTarget.open)}><summary>排序预测与风险收益：RankIC、夏普比率</summary>
    <p className="fc-diagnostic-context">{selected.factor.name} · {selected.dataset.name} · {selected.dataset.pools.find(p => p.id === selection.pool)?.label} · {feeLabel(Number(selection.fee))} · {selected.range[0]} 至 {selected.range[1]}</p>
    {selected.dataset.assessmentError && <p role="status">{selected.dataset.assessmentError}</p>}
    <section><h3>排序预测能力（RankIC）</h3><p>检查同一天排在前面的标的，之后是否表现更好。取值在−1与1之间，正数表示排序方向一致；它不等于胜率或账户收益。</p>
      {rank ? <><label>观察期限<select aria-label="预测观察期限" value={rank.horizon} onChange={e => setHorizon(e.target.value)}>{view.rankIC.map(r => <option key={r.horizon} value={r.horizon}>{r.horizon}</option>)}</select></label>
      <p>形成月份 {rank.range[0]} 至 {rank.range[1]}；后续结果范围 {(rank.evaluationRange ?? rank.range)[0]} 至 {(rank.evaluationRange ?? rank.range)[1]}。</p>
      <p><strong>平均 {number(rank.mean)}</strong> · 有效 {rank.nPeriods}期 · 每期至少 {rank.minAssets}只、中位 {rank.medianAssets}只 · 有效覆盖 {percent(rank.coverage)}</p>
      <p>结果可能波动的范围：{number(rank.uncertainty.lower)} 至 {number(rank.uncertainty.upper)}。{rank.uncertainty.lower !== null && rank.uncertainty.upper !== null && rank.uncertainty.lower <= 0 && rank.uncertainty.upper >= 0 ? "范围跨过0，暂不能确认排序有稳定帮助。" : "仅描述这段已看历史，不代表未来有效。"}</p>
      <DiagnosticChart option={option} label="逐形成日期的RankIC，空缺保持断开" />
      <details><summary>逐期覆盖、标签与来源</summary><p>方向：{rank.scoreDirection}；之后的结果：{rank.labelDefinition}</p><p>不确定范围的算法原文：{rank.uncertainty.method}</p><p>{rank.limitations}</p><small>逐标的来源指纹 {rank.sourceManifestSha256}</small><div className="fc-table-scroll"><table><thead><tr><th>形成日期</th><th>RankIC</th><th>有效/候选标的数</th></tr></thead><tbody>{rank.points.map(p => <tr key={p[0]}><th>{p[0]}</th><td>{number(p[1])}</td><td>{p[2]} / {p[3]}</td></tr>)}</tbody></table></div></details></> : <p><strong>未评价。</strong> 当前因子、范围和分期尚未交付逐标的分数与成熟结果的合格统计，账户曲线不代替这项资料。</p>}
    </section>
    <section><h3>收益与波动的比值（夏普比率）</h3><p>比较超过无风险参考的收益与波动；数值读取研究端，需连同费用、频率和无风险参考一起看。</p>
      {view.sharpe.length ? <><div className="fc-table-scroll"><table><thead><tr><th>账户</th><th>夏普比率</th><th>收益频率与条数</th><th>费用</th></tr></thead><tbody>{view.sharpe.map(r => <tr key={r.streamId}><th>{r.streamId.includes("__pool__") ? "同池共同基准" : "G5定义高分组"}</th><td>{number(r.value)}</td><td>{frequencies[r.frequency]}收益 · {r.observations}条</td><td>{feeLabel(r.feeBps)}<br />{r.feesDeducted ? "已计入所选费用" : "未扣费用"}</td></tr>)}</tbody></table></div>
      <p>{view.sharpe.every(r => r.riskFree.kind === "zero_assumption") ? "无风险收益假设为0；实际报价与缺价会影响结果。" : "无风险参考按各账户来源，详见计算口径。"}</p>
      <details><summary>夏普的计算口径与限制</summary>{view.sharpe.map(r => <section key={r.streamId}><h4>{r.streamId.includes("__pool__") ? "同池共同基准" : "G5定义高分组"}</h4><p>年化乘数{r.annualization.toFixed(3)}；{r.method}</p><p>{r.riskFree.description} {r.riskFree.source} {r.riskFree.sourceDate}</p><p>{r.limitations}</p></section>)}</details></> : <p><strong>未评价。</strong> 当前组合尚未交付包含收益频率、费用和无风险参考说明的预计算值。</p>}

    </section><p>市场环境仅高亮主图，以上指标保留所选完整分期；不会把不连续月份拼成账户。</p>
  </details>;
}

function ProfessionalDiagnostics({ selected, selection }: { selected: Selected; selection: CurveSelection }) {
  const [open, setOpen] = useState(false);
  const [quality, setQuality] = useState(["turnover", "cashEnd", "unknownMax"]);
  const view = diagnosticView(selected.dataset, selection);
  if (!view) return <details className="fc-fold"><summary>专业诊断 · 资料尚未接入</summary><p>{selected.dataset.diagnosticsError || "这批资料尚未提供对应组合的分组、逐月差额与资金占用诊断。"}已有曲线与原始指标仍可查看。</p></details>;
  const years = [...new Set(view.monthly.map(row => row.month.slice(0, 4)))].sort();
  const heat = view.monthly.filter(row => row.excessReturn !== null).map(row => [Number(row.month.slice(5)) - 1, years.indexOf(row.month.slice(0, 4)), row.excessReturn! * 100]);
  const colorLimit = Math.max(.01, ...heat.map(row => Math.abs(row[2])));
  const groupOption: echarts.EChartsOption = {
    animation: false, grid: { top: 25, left: 55, right: 18, bottom: 30 },
    xAxis: { type: "category", data: view.groups.map(row => row.id), axisTick: { show: false } },
    yAxis: { type: "value", axisLabel: { formatter: "{value}%" }, splitLine: { lineStyle: { color: "#edf0f3" } } },
    tooltip: { trigger: "axis", renderMode: "richText", valueFormatter: (v: unknown) => typeof v === "number" ? `${v.toFixed(3)}% / 月` : "未提供" },
    series: [{ type: "bar", barMaxWidth: 52, label: { show: true, position: "top", fontSize: 11, formatter: p => typeof p.value === "number" ? `${p.value.toFixed(2)}%` : "" }, data: view.groups.map((row, i) => ({ value: row.mean === null ? null : row.mean * 100, itemStyle: { color: GROUP_COLORS[i] } })) }],
  };
  const heatOption: echarts.EChartsOption = {
    animation: false, grid: { top: 15, left: 45, right: 15, bottom: 65, show: true, backgroundColor: "#e5eaf0", borderWidth: 0 },
    xAxis: { type: "category", data: Array.from({ length: 12 }, (_, i) => `${i + 1}月`), splitArea: { show: false } },
    yAxis: { type: "category", data: years, inverse: true, splitArea: { show: false } },
    tooltip: { renderMode: "richText", formatter: (input: unknown) => { const v = (input as { data: number[] }).data; return `${years[v[1]]}年${v[0] + 1}月\nG5 比共同池 ${v[2] > 0 ? "+" : ""}${v[2].toFixed(2)}个百分点`; } },
    visualMap: { min: -colorLimit, max: colorLimit, calculable: false, orient: "horizontal", left: "center", bottom: 0, text: ["差额较高", "差额较低"], inRange: { color: ["#bb6d64", "#ffffff", "#3c8b77"] } },
    series: [{ type: "heatmap", data: heat, itemStyle: { borderColor: "#fff", borderWidth: 2 }, emphasis: { itemStyle: { borderColor: "#354f60", borderWidth: 1 } } }],
  };
  const qualityLabels: Record<string, string> = { turnover: "月度换手", cashEnd: "月末现金", unknownMax: "月内最高缺价" };
  const qualityColors: Record<string, string> = { turnover: "#4c6ca7", cashEnd: "#7b8891", unknownMax: "#aa6c34" };
  const qualityOption: echarts.EChartsOption = {
    animation: false, grid: { top: 20, left: 55, right: 38, bottom: 32 },
    xAxis: { type: "category", data: view.monthly.map(row => row.month), boundaryGap: false, axisLabel: { hideOverlap: true } },
    yAxis: { type: "value", axisLabel: { formatter: "{value}%" }, splitLine: { lineStyle: { color: "#edf0f3" } } },
    tooltip: { trigger: "axis", renderMode: "richText", valueFormatter: (v: unknown) => typeof v === "number" ? `${v.toFixed(2)}%` : "未提供" },
    series: quality.map(key => ({ name: qualityLabels[key], type: "line", showSymbol: false, connectNulls: false, itemStyle: { color: qualityColors[key] }, lineStyle: { width: 1.7 }, data: view.monthly.map(row => { const value = row[key as "turnover" | "cashEnd" | "unknownMax"]; return value === null ? null : value * 100; }) })),
  };
  return <details className="fc-fold fc-diagnostics" open={open} onToggle={e => setOpen(e.currentTarget.open)}><summary>专业诊断：分组、逐月差额与资金代价</summary>{open && <div>
    <p className="fc-diagnostic-context">{selected.factor.name} · {selected.dataset.name} · {selected.dataset.pools.find(p => p.id === selection.pool)?.label} · {feeLabel(Number(selection.fee))} · {selected.range[0]} 至 {selected.range[1]}</p><p>以下保留所选分期的全部月份，读取研究端预先算好的结果；市场环境只影响上方高亮与条件表。</p>
    <section><h3>五组的月平均变化</h3><p>按所选费用口径的报价账户，把各月变化相加后取平均。分组顺序保持原定义，图中差异不等于个股预测能力。</p>{view.groups.some(g => g.mean !== null) ? <DiagnosticChart option={groupOption} label="五组报价账户月平均变化柱图" /> : <p>该组合尚无可显示的分组均值。</p>}</section>
    <section><h3>G5 每月相对共同池的差额</h3><p>单位为百分点；正数表示相对多赚或少亏，负数表示相对少赚或多亏。灰格为没有记录，未补成零。</p>{heat.length ? <DiagnosticChart option={heatOption} label="G5相对共同池逐月差额热图" height={Math.max(230, years.length * 24 + 85)} /> : <p>尚无可显示的逐月差额。</p>}</section>
    <section><h3>逐年收益与相对差额</h3><div className="fc-table-scroll"><table><thead><tr><th>年份与覆盖</th><th>G5累计变化</th><th>共同池累计变化</th><th>相对差额</th></tr></thead><tbody>{view.annual.map(row => <tr key={row.year}><th>{row.year} · {row.months}个月{!row.completeYear && <small>部分年度</small>}</th><td>{percent(row.return, true)}</td><td>{percent(row.benchmarkReturn, true)}</td><td>{percentagePoints(row.difference)}</td></tr>)}</tbody></table></div><p>部分年度不年化。若分期截断了原年度记录，就不混用那一整年的统计。</p></section>
    <section><h3>G5 的换手、现金和缺价</h3><fieldset className="fc-diagnostic-toggles"><legend>显示项目</legend>{Object.entries(qualityLabels).map(([id, label]) => <label key={id}><input type="checkbox" checked={quality.includes(id)} onChange={() => setQuality(previous => previous.includes(id) ? previous.filter(v => v !== id) : [...previous, id])} />{label}</label>)}</fieldset><DiagnosticChart option={qualityOption} label="G5月度换手、现金和未知报价占比" /><p>月度换手将每日买卖金额相对当日资金的比例相加，可能超过100%。现金与未知报价分别列出。</p></section>
    {view.data.capabilities.filter(capability => capability.status !== "available" && !(capability.id === "rank_ic" && assessmentView(selected.dataset, selection).rankIC.length > 0)).map(capability => <p className="fc-capability" key={capability.id}><strong>{capability.id === "rank_ic" ? "个股预测关系：本批资金资料未提供" : "未评价项目"}</strong> {capability.id === "rank_ic" ? "账户曲线不能反推出因子对单只股票未来涨跌的预测能力，需要另外核对个股因子值与之后的结果。" : capability.reason}{capability.id === "rank_ic" && <a href="/library?report=docs%2Fexperiments%2Ffactor-sorting-diagnostics-2026-10-21.md">查原四因子的分组与排序报告</a>}</p>)}
  </div>}</details>;
}

function CurveWorkspace({ document }: { document: CurveDocument }) {
  const [params, setParams] = useSearchParams();
  const [visible, setVisible] = useState(["G1", "G2", "G3", "G4", "G5", "pool"]);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [metricsOpen, setMetricsOpen] = useState(false);
  const selection = defaultSelection(document, params);
  const returnMode = defaultReturnMode(params);
  const setReturnMode = (mode: CurveReturnMode) => { const next = new URLSearchParams(params); next.set("returnView", mode); setParams(next); };
  const selected = useMemo(() => {
    try { return { value: selectCurves(document, selection), error: null }; }
    catch (error) { return { value: null, error: error instanceof Error ? error.message : "当前资料无法比较。" }; }
  }, [document, selection.dataset, selection.curveFactor, selection.pool, selection.fee, selection.period, selection.regime]);
  const update = (changes: Partial<CurveSelection>) => {
    const next = new URLSearchParams(params); next.set("tab", "curves"); next.set("dataset", selection.dataset);
    for (const [key, value] of Object.entries(changes)) next.set(key, value);
    setParams(next);
  };
  const reset = () => { const next = new URLSearchParams(params); for (const key of CURVE_QUERY_KEYS) next.delete(key); next.set("tab", "curves"); setParams(next); };
  const d = selected.value?.dataset ?? document.datasets.find(d => d.id === selection.dataset);
  if (!selected.value || !d) return <section className="fc-state" role="alert"><h2>这个组合暂无可比曲线</h2><p>{selected.error}</p><button type="button" onClick={reset}>返回已接入的研究样本</button></section>;
  const current = selected.value;
  const preferred = current.series.find(s => s.id === "G5")!;
  const report = safeReportHref(d.source_report || "");
  let display: ReturnType<typeof returnDisplay> | null = null; let displayError = "";
  try { display = returnDisplay(current.series, returnMode); } catch (error) { displayError = error instanceof Error ? error.message : "该基准超额未评价。"; }
  const ending = display?.lastG5;
  const displayNumber = (value: number | null | undefined, unit: string) => value == null ? "未评价" : `${value > 0 ? "+" : ""}${value.toFixed(2)}${unit}`;
  return <div className="fc-workspace">
    <aside className="fc-sidebar" aria-label="资金曲线因子"><h2>已接入资金线</h2><label className="fc-mobile-factor">因子<select aria-label="因子" value={selection.curveFactor} onChange={e => update({ curveFactor: e.target.value })}>{d.factors.filter(f => f.available).map(f => <option key={f.id} value={f.id}>{f.name}</option>)}</select></label><div className="fc-factor-list">{d.factors.filter(f => f.available).map(f => <button type="button" key={f.id} aria-pressed={f.id === selection.curveFactor} onClick={() => update({ curveFactor: f.id })}><strong>{f.name}</strong><small>{f.primaryUse || f.purpose || "分组资金对照"}</small></button>)}</div>{d.factors.some(f => !f.available) && <div className="fc-pending"><h3>待接资金线</h3>{d.factors.filter(f => !f.available).map(f => <div key={f.id} title={f.unavailableReason || undefined}><strong>{f.name}</strong><span>{f.unavailableReason}</span></div>)}</div>}<a className="fc-catalog-link" href="/factors?tab=catalog">查因子定义与旧研究</a></aside>
    <div className="fc-main">
      <button type="button" className="fc-mobile-filters" aria-expanded={filtersOpen} aria-controls="fc-filter-controls" onClick={() => setFiltersOpen(v => !v)}><strong>对照设置</strong><span>{d.pools.find(p => p.id === selection.pool)?.label} / {feeLabel(Number(selection.fee))} / {current.range[0]}—{current.range[1]}</span></button>
      <div id="fc-filter-controls" className={`fc-controls${filtersOpen ? " fc-filters-open" : ""}`}><label>研究样本<select aria-label="研究样本" value={selection.dataset} onChange={e => { const next = new URLSearchParams(params); CURVE_QUERY_KEYS.forEach(key => next.delete(key)); next.set("tab", "curves"); next.set("dataset", e.target.value); setParams(next); }}>{document.datasets.map(dataset => <option key={dataset.id} value={dataset.id} disabled={!dataset.available}>{dataset.name}{!dataset.available ? `（${dataset.statusLabel || "资料未接入"}）` : ""}</option>)}</select></label><label>候选范围<select aria-label="候选范围" value={selection.pool} onChange={e => update({ pool: e.target.value })}>{d.pools.map(pool => <option value={pool.id} key={pool.id}>{pool.label}</option>)}</select></label><label>买卖费用<select aria-label="买卖费用" value={selection.fee} onChange={e => update({ fee: e.target.value })}>{d.fees_bps.map(fee => <option key={fee} value={fee}>{feeLabel(fee)}</option>)}</select></label><label>历史分期<select aria-label="历史分期" value={selection.period} onChange={e => update({ period: e.target.value })}>{Object.entries(d.periods).map(([id, [start, end]]) => <option value={id} key={id}>{start} 至 {end}{id === "all" ? " 全段" : ""}</option>)}</select></label></div>
      {document.datasets.some(dataset => !dataset.available) && <details className="fc-universe-status"><summary>历史成员资料状态 · {document.datasets.filter(dataset => !dataset.available).length}个范围暂不可选</summary><p>发现公开资料后仍要核对历史成员、日期和报价衔接；以下原因来自当前研究目录，候选资料不代表已通过核验。</p><dl>{document.datasets.filter(dataset => !dataset.available).map(dataset => <div key={dataset.id}><dt>{dataset.name}<span className="fc-universe-label">{dataset.statusLabel || "资料未接入"}</span></dt><dd>{dataset.unavailableReason}</dd></div>)}</dl></details>}
      <div className="fc-chart-and-metrics">
      <section className="fc-plot-panel" aria-labelledby="fc-factor-heading"><div className="fc-plot-heading"><div><h2 id="fc-factor-heading">{current.factor.name}<span>五组与共同基准</span></h2><p>{current.factor.group5Meaning ? `G5：${current.factor.group5Meaning}；G1 为相反一端。` : current.factor.preference || "分组方向待研究端补充。"}</p></div>{report && <a href={report}>原始研究报告</a>}</div>
        <div className="fc-boundary"><strong>报价资金示意</strong><details className="fc-scope"><summary>{d.market} · {d.name} · 样本范围</summary><p>{d.universeLabel}</p></details><span>{d.history_role || "已看历史；独立新验证尚未完成"}</span></div>
        <div className="fc-environment"><label>市场环境<select aria-label="市场环境" value={selection.regime} onChange={e => update({ regime: e.target.value })}>{d.regimes.map(g => <option value={g.id} key={g.id} disabled={!g.available}>{g.regimeLabel}{!g.available ? "（不可用）" : ""}</option>)}</select></label><details className="fc-environment-definition"><summary>{current.regime.id === "all" ? "环境定义与使用范围" : "仅高亮月份，账户保持连续"}</summary><p>{current.regime.regimeDefinition || d.regimes.find(g => g.available && g.id !== "all")?.regimeDefinition || "环境定义尚未接入。"} 环境参照与研究股票池分别定义；条件统计只作解释，不改变资金线。</p></details></div>
        <div className="fc-return-view" role="group" aria-label="收益展示方式"><button type="button" aria-pressed={returnMode === "excess"} onClick={() => setReturnMode("excess")}>相对基准超额</button><button type="button" aria-pressed={returnMode === "absolute"} onClick={() => setReturnMode("absolute")}>绝对累计收益</button><span>基准：同池共同基准（无唯一母指数）</span></div>
        <div className="fc-legend" aria-label="曲线图例">{current.series.map(s => <button type="button" key={s.id} aria-pressed={visible.includes(s.id)} disabled={s.id === "pool"} onClick={() => setVisible(prev => prev.includes(s.id) ? prev.filter(id => id !== s.id) : [...prev, s.id])}><i style={{ background: s.color }} />{s.id === "pool" && returnMode === "excess" ? "同池基准零线" : s.label}{s.id === "G5" && <small>定义高分组</small>}</button>)}</div>
        {display ? <CurvesChart selected={current} visible={visible} display={display} mode={returnMode} /> : <div className="fc-state" role="alert">{displayError}</div>}
        {display && <p className="fc-return-summary">截至{display.lastDate}：G5绝对收益 <strong>{displayNumber(ending?.absoluteValue, "%")}</strong> · 同池基准 <strong>{displayNumber(ending?.benchmarkValue, "%")}</strong> · 累计超额 <strong>{displayNumber(ending?.excessValue, "个百分点")}</strong></p>}
        <div className="fc-chart-notes"><p>{returnMode === "excess" ? "双方按同一起始日归零；先用未四舍五入的累计收益相减，显示保留两位小数，单位百分点。" : "绝对收益按各自原区间起点归零；比较双方收益需要相同起始日。"}<strong>{returnMode === "excess" ? "任一方或起点估值未知时用虚线，不能当作可兑现净值。" : "各账户月内缺价用虚线，不能当作可兑现净值。"}</strong></p><p>下图保留原账户回撤，夏普仍按原无风险参考；均未从超额曲线重算。</p><p>{current.drawdownRebased ? "跌幅点采用研究端提供的所选区间高点基准。" : d.drawdown_basis || "跌幅点为当月最深日回撤，沿原连续账户历史高点；分期不重设高点。"}</p></div>
        <div className="fc-quality"><span>G5 区间最高缺价 <strong>{percent(metricNumber(preferred.metrics, "unknown_max"))}</strong></span><span>平均现金 <strong>{percent(metricNumber(preferred.metrics, "cash_mean"))}</strong></span><span>有效月份 <strong>{metricNumber(preferred.metrics, "months") ?? "未提供"}</strong></span><span>日度记账，月末采样</span></div>
      </section>
      <ResearchHighlights selected={current} selection={selection} generatedAt={document.generated_at} onOpen={() => setMetricsOpen(true)} />
      </div>
      <EnvironmentStats selected={current} selection={selection} />
      <ExactMetrics series={current.series} />
      <ResearchMetrics selected={current} selection={selection} open={metricsOpen} onOpenChange={setMetricsOpen} />
      <ProfessionalDiagnostics selected={current} selection={selection} />
      <IncrementTable selected={current} selection={selection} />
      <details className="fc-fold"><summary>公式、样本与资料状态</summary><dl className="fc-definition"><div><dt>分组方向</dt><dd>{current.factor.preference || "未提供"}</dd></div><div><dt>计算口径</dt><dd>{current.factor.formula || "尚未接入公式说明"}</dd></div><div><dt>研究用途</dt><dd>{current.factor.purpose || "尚未接入用途说明"}</dd></div><div><dt>样本范围</dt><dd>{d.sample_note || d.universeLabel}</dd></div><div><dt>方法边界</dt><dd>{d.method || current.factor.scope || "以原报告为准"}</dd></div></dl>{document.datasets.filter(v => !v.available).map(v => <p key={v.id}>{v.name}：{v.unavailableReason}</p>)}{d.factors.filter(v => !v.available).map(v => <p key={v.id}>{v.name}：{v.unavailableReason}</p>)}{d.regimes.filter(v => !v.available).map(v => <p key={v.id}>{v.regimeLabel}：{v.unavailableReason || "定义和环境资料尚未接入。"}</p>)}{d.regimeSourceNote && <p>环境来源限制：{d.regimeSourceNote}</p>}<small>资料生成 {document.generated_at?.slice(0, 10) || "未记录"}；生成日期不代表验证期。{d.source_manifest_sha256 && `来源指纹 ${d.source_manifest_sha256.slice(0, 12)}`}</small></details>
    </div>
  </div>;
}

export default function FactorCurves() {
  const { data, error, isLoading, refetch, isFetching } = useQuery({ queryKey: ["factorCurveLibrary"], queryFn: ({ signal }) => loadCurveLibrary(signal), staleTime: 60_000, retry: false });
  if (isLoading) return <section className="fc-state" role="status">正在读取资金曲线与资料范围…</section>;
  if (error || !data) return <section className="fc-state" role="alert"><h2>资金曲线资料暂未接入</h2><p>{error instanceof Error ? error.message : "暂时无法读取研究结果。"}</p><button type="button" disabled={isFetching} onClick={() => void refetch()}>重新读取资料</button><a href="/factors?tab=overview">查看已有研究概览</a></section>;
  return <CurveWorkspace document={data} />;
}
