import * as echarts from "echarts";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  OLD_MODULE_A_REPORT, POLICY_LABELS, POLICY_ORDER, RESEARCH_RESULTS_SCHEMA,
  RULE_AUDIT_REPORT, type ModuleAPolicy, type ResearchResultsPayload,
} from "./researchResultsTypes";
import "./research-results.css";

const DATA_URL = "/research-results/module-a-rule-audit-2026-10-18.json";
const TABS = ["收益与风险", "机会筛选", "逐笔核对", "规则覆盖"] as const;
type Tab = typeof TABS[number];
const COLORS: Record<ModuleAPolicy, string> = {
  buy_hold: "#3974ad", a_fixed: "#bd7555", a_risk: "#77725f", a_risk_degrade: "#7a619b",
};
const pct = (value: number | null | undefined, digits = 2) => value == null || !Number.isFinite(value)
  ? "未知" : `${value >= 0 ? "+" : ""}${(value * 100).toFixed(digits)}%`;
const money = (value: number | null | undefined) => value == null || !Number.isFinite(value)
  ? "未知" : `${value >= 0 ? "+" : ""}${value.toFixed(5)} 元`;
const price = (value: number | null | undefined) => value == null || !Number.isFinite(value) ? "未知" : value.toFixed(3);

function Chart({ option, height = 280, label }: { option: echarts.EChartsOption; height?: number; label: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current, undefined, { renderer: "canvas" });
    chart.setOption(option, true);
    const resize = new ResizeObserver(() => chart.resize());
    resize.observe(ref.current);
    return () => { resize.disconnect(); chart.dispose(); };
  }, [option]);
  return <div ref={ref} className="rr-chart" style={{ height }} role="img" aria-label={label} />;
}

function axisOption(dates: string[]): echarts.EChartsOption {
  return {
    animation: false,
    grid: { left: 54, right: 18, top: 28, bottom: 58, containLabel: false },
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: dates, axisLabel: { hideOverlap: true, color: "#6d7581" } },
    yAxis: { type: "value", scale: true, axisLabel: { color: "#6d7581" }, splitLine: { lineStyle: { color: "#e4e8ed" } } },
    dataZoom: [{ type: "inside" }, { type: "slider", height: 16, bottom: 8 }],
  };
}

function validPayload(raw: unknown, reportName: string): raw is ResearchResultsPayload {
  if (!raw || typeof raw !== "object") return false;
  const data = raw as Partial<ResearchResultsPayload>;
  return data.schema_version === RESEARCH_RESULTS_SCHEMA
    && Array.isArray(data.report_names) && data.report_names.includes(reportName)
    && Array.isArray(data.versions) && data.versions.length >= 2
    && Array.isArray(data.groups) && Array.isArray(data.runs) && Array.isArray(data.cases)
    && Array.isArray(data.coverage) && Array.isArray(data.limitations) && Array.isArray(data.sources);
}

export default function ResearchResultsPanel({ reportName }: { reportName: string }) {
  const eligible = reportName === OLD_MODULE_A_REPORT || reportName === RULE_AUDIT_REPORT;
  const [data, setData] = useState<ResearchResultsPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<Tab>(TABS[0]);
  const [version, setVersion] = useState("");
  const [group, setGroup] = useState("");
  const [cost, setCost] = useState(10);
  const [policy, setPolicy] = useState<ModuleAPolicy>("a_fixed");
  const [caseAsset, setCaseAsset] = useState("");

  useEffect(() => {
    if (!eligible) { setData(null); setError(null); setLoading(false); return; }
    const controller = new AbortController();
    setData(null); setError(null); setLoading(true);
    fetch(DATA_URL, { signal: controller.signal }).then(async response => {
      if (!response.ok) throw new Error(`图表资料读取失败（HTTP ${response.status}）`);
      if (!response.headers.get("content-type")?.includes("application/json")) throw new Error("图表资料尚未发布，或返回的资料格式不符");
      return response.json() as Promise<unknown>;
    }).then(raw => {
      if (!validPayload(raw, reportName)) throw new Error("图表资料与本报告身份或格式不符");
      setData(raw);
      setVersion(raw.versions[reportName === OLD_MODULE_A_REPORT ? 0 : 1].id);
      setGroup(raw.groups[0]?.id ?? "");
      setCost(10); setPolicy("a_fixed"); setCaseAsset(""); setTab(TABS[0]);
    }).catch(reason => {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : String(reason));
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [eligible, reportName]);

  const selectedVersion = data?.versions.find(item => item.id === version);
  const selectedGroup = data?.groups.find(item => item.id === group);
  const costOptions = useMemo(() => data
    ? [...new Set(data.runs.filter(run => run.version === version && run.group === group).map(run => run.cost_bps))].sort((a, b) => a - b)
    : [], [data, version, group]);
  useEffect(() => {
    if (costOptions.length && !costOptions.includes(cost)) setCost(costOptions[0]);
  }, [costOptions, cost]);
  const runs = useMemo(() => data?.runs.filter(run => run.version === version && run.group === group && run.cost_bps === cost) ?? [], [data, version, group, cost]);
  const run = runs.find(item => item.policy === policy);
  const execution = runs.find(item => item.policy === "a_fixed")?.summary.execution_summary;
  const cases = data?.cases.filter(item => item.version === version && item.group === group) ?? [];
  const selectedCase = cases.find(item => item.id === caseAsset) ?? cases[0];

  const wealthOption = useMemo<echarts.EChartsOption | null>(() => {
    const reference = runs[0];
    if (!reference) return null;
    const dates = reference.daily.map(row => row.date);
    return { ...axisOption(dates), tooltip: { trigger: "axis", valueFormatter: value => typeof value === "number" ? `${value.toFixed(4)} 元` : "未知" }, legend: { data: POLICY_ORDER.filter(key => runs.some(r => r.policy === key)).map(key => POLICY_LABELS[key]), top: 0, textStyle: { color: "#56606c", fontSize: 11 } },
      yAxis: { type: "value", scale: true, axisLabel: { formatter: (value: number) => value.toFixed(2) } },
      series: POLICY_ORDER.flatMap(key => { const item = runs.find(r => r.policy === key); return item ? [{ name: POLICY_LABELS[key], type: "line" as const, showSymbol: false, connectNulls: false, itemStyle: { color: COLORS[key] }, lineStyle: { width: key === "buy_hold" ? 2 : 2.5 }, data: item.daily.map(row => row.nav) }] : []; }) };
  }, [runs]);
  const drawdownOption = useMemo<echarts.EChartsOption | null>(() => {
    if (!run) return null;
    return { ...axisOption(run.daily.map(row => row.date)), tooltip: { trigger: "axis", valueFormatter: value => typeof value === "number" ? pct(value) : "未知" }, yAxis: { type: "value", max: 0, axisLabel: { formatter: (value: number) => `${(value * 100).toFixed(2)}%` } }, series: [{ type: "line", showSymbol: false, connectNulls: false, data: run.drawdown, itemStyle: { color: COLORS[policy] }, areaStyle: { opacity: 0.12 } }] };
  }, [run, policy]);
  const exposureOption = useMemo<echarts.EChartsOption | null>(() => {
    if (!run) return null;
    return { ...axisOption(run.daily.map(row => row.date)), yAxis: { type: "value", min: 0, axisLabel: { formatter: (value: number) => `${(value * 100).toFixed(0)}%` } }, series: [{ type: "line", showSymbol: false, connectNulls: false, data: run.daily.map(row => row.exposure), itemStyle: { color: COLORS[policy] } }] };
  }, [run, policy]);
  const contributionOption = useMemo<echarts.EChartsOption | null>(() => {
    if (!run?.assets.length) return null;
    return { animation: false, grid: { left: 95, right: 22, top: 15, bottom: 35 }, tooltip: { trigger: "item", valueFormatter: value => typeof value === "number" ? money(value) : "未知" }, xAxis: { type: "value" }, yAxis: { type: "category", data: run.assets.map(item => item.name), axisLabel: { width: 84, overflow: "truncate" } }, series: [{ type: "bar", data: run.assets.map(item => item.contribution), itemStyle: { color: COLORS[policy] } }] };
  }, [run, policy]);
  const caseOption = useMemo<echarts.EChartsOption | null>(() => {
    if (!selectedCase?.bars.length) return null;
    const bars = selectedCase.bars;
    const dates = bars.map(row => row.date);
    const knownFrom = selectedCase.signal_date;
    const level = (value: number | null) => bars.map(row => value != null && row.date >= knownFrom ? value : null);
    return { ...axisOption(dates), legend: { top: 0, data: ["收盘价", "EMA20", "SMA20", "信号收盘 A", "目标 B", "失效价 C"] },
      yAxis: { type: "value", scale: true },
      series: [
        { name: "收盘价", type: "line", showSymbol: false, connectNulls: false, data: bars.map(row => row.close), itemStyle: { color: "#34485e" }, lineStyle: { color: "#34485e", width: 2 } },
        { name: "EMA20", type: "line", showSymbol: false, connectNulls: false, data: bars.map(row => row.ema20 ?? null), itemStyle: { color: "#bf8352" }, lineStyle: { color: "#bf8352" } },
        { name: "SMA20", type: "line", showSymbol: false, connectNulls: false, data: bars.map(row => row.sma20 ?? null), itemStyle: { color: "#76936e" }, lineStyle: { color: "#76936e" } },
        { name: "信号收盘 A", type: "line", showSymbol: false, connectNulls: false, data: level(selectedCase.entry_reference), itemStyle: { color: "#9a8c4f" }, lineStyle: { color: "#9a8c4f", type: "dotted" } },
        { name: "目标 B", type: "line", showSymbol: false, connectNulls: false, data: level(selectedCase.target), itemStyle: { color: "#3974ad" }, lineStyle: { color: "#3974ad", type: "dashed" } },
        { name: "失效价 C", type: "line", showSymbol: false, connectNulls: false, data: level(selectedCase.stop), itemStyle: { color: "#bd7555" }, lineStyle: { color: "#bd7555", type: "dashed" } },
        { name: "买卖记录", type: "scatter", symbolSize: 11, data: (selectedCase.trades ?? []).filter(item => item.price != null && dates.includes(item.date)).map(item => ({ value: [item.date, item.price], name: item.side === "buy" ? "假设买入" : "假设卖出", itemStyle: { color: item.side === "buy" ? "#bd7555" : "#3974ad" } })) },
      ] };
  }, [selectedCase]);

  if (!eligible) return null;
  return <section className="rr-panel" aria-label="模块 A 研究图表" id="module-a-research-results">
    <div className="rr-heading"><div><h2>模块 A · 历史研究图</h2><p>同一批历史资料的不同规则解释；资金曲线是假设成交的研究账户，每组起始 1 元。</p></div><span className="rr-chip">研究资料 · 不代表交易指令</span></div>
    {loading && <p role="status" className="rr-state">正在读取已保存的图表资料…</p>}
    {error && <p role="alert" className="rr-state rr-error">{error}。正文报告仍可阅读，图表暂不可核对。</p>}
    {data && <>
      <div className="rr-controls">
        <label>研究版本<select value={version} onChange={event => { setVersion(event.target.value); setCaseAsset(""); }}>{data.versions.map(item => <option value={item.id} key={item.id}>{item.label}</option>)}</select></label>
        <label>产品组<select value={group} onChange={event => { setGroup(event.target.value); setCaseAsset(""); }}>{data.groups.map(item => <option value={item.id} key={item.id}>{item.label}（{item.count} 只）</option>)}</select></label>
        <label>单边模拟费用<select value={cost} onChange={event => setCost(Number(event.target.value))}>{costOptions.map(value => <option value={value} key={value}>{(value / 100).toFixed(2)}%</option>)}</select></label>
        <label>明细方法<select value={policy} onChange={event => setPolicy(event.target.value as ModuleAPolicy)}>{POLICY_ORDER.map(key => <option value={key} key={key}>{POLICY_LABELS[key]}</option>)}</select></label>
      </div>
      <p className="rr-version-note"><strong>{selectedVersion?.label}</strong>：{selectedVersion?.note || "未记录本版说明"}</p>
      <div className="rr-cards">
        <div><span>扣费后期末收益</span><strong>{pct(run?.summary.total_return)}</strong></div>
        <div><span>观察到的最大跌幅</span><strong>{pct(run?.summary.max_observed_drawdown)}</strong></div>
        <div><span>平均投入比例</span><strong>{pct(run?.summary.average_exposure, 4)}</strong></div>
        <div><span>假设买入 / 卖出</span><strong>{run ? `${run.summary.entries} / ${run.summary.exits}` : "未知"}</strong></div>
      </div>
      {policy === "a_risk_degrade" && run && <p className="rr-note">{run.summary.degraded_entries == null
        ? "缩小新买入的实际次数未记录，不能判断这项保护是否发挥作用。"
        : run.summary.degraded_entries === 0
          ? "本段没有任何一笔新买入因账户回撤而缩小投入；这条曲线不能证明该项保护有效。"
          : `有 ${run.summary.degraded_entries} 笔新买入因账户回撤而缩小投入；效果须与仅控制单笔投入的方法比较。`}</p>}
      <nav className="rr-tabs" aria-label="研究图表视图">{TABS.map(item => <button type="button" key={item} className={tab === item ? "active" : ""} aria-current={tab === item ? "page" : undefined} onClick={() => setTab(item)}>{item}</button>)}</nav>
      {tab === "收益与风险" && <div className="rr-body">
        <section className="rr-graph-main"><h3>资金随日期变化</h3><p>四种方法共用相同起始资金和日期；缺估值时线会断开。点击图例可以暂时隐藏某条曲线，再放大观察其他方法。</p>{wealthOption ? <Chart option={wealthOption} label="四种方法的历史研究资金曲线" height={320} /> : <p className="rr-empty">当前版本、产品组和费用没有可核对的完整资金序列。</p>}</section>
        {run && <><div className="rr-graph-grid"><section><h3>距此前最高资金的跌幅</h3>{drawdownOption && <Chart option={drawdownOption} label="所选方法的历史账户跌幅" />}</section><section><h3>投入比例</h3>{exposureOption && <Chart option={exposureOption} label="所选方法的历史投入比例" />}</section></div><section><h3>各产品对起始 1 元的贡献</h3>{contributionOption ? <Chart option={contributionOption} label="各产品对资金的期末贡献" height={Math.max(230, run.assets.length * 28 + 70)} /> : <p className="rr-empty">未记录逐产品贡献。</p>}</section><p className="rr-note">期末缺价的产品保留未知；最大跌幅仅覆盖可估值日期。少投入会同时减少亏损和上涨参与，不能单靠低跌幅判断规则有效。</p></>}
      </div>}
      {tab === "机会筛选" && <div className="rr-body"><h3>候选如何逐步减少</h3>{execution && <p className="rr-version-note">{selectedGroup?.label}固定投入、单边 {(cost / 100).toFixed(2)}% 费用：收盘通过 {execution.accepted_signals} 条 → 买入 {execution.bought} 笔 · 开盘取消 {execution.rejected} 条 · 已有持仓 {execution.already_held} 条 · 未知 {execution.unknown} 条。</p>}<p>以下为本版全部 14 只产品的筛选记录，不随上方产品组切换。同一产品日期可能有多个候选，不能直接当作独立买入机会。</p>{selectedVersion?.funnel.length ? <div className="rr-funnel">{selectedVersion.funnel.map((item, index) => <div key={`${item.label}-${index}`}><span>{item.label}</span><strong>{item.count.toLocaleString()} {item.unit}</strong></div>)}</div> : <p className="rr-empty">本版未提供可核对的筛选数量。</p>}<p className="rr-note">筛选数量仅描述本版保存的规则路径，不能证明被排除的候选本来会盈利。</p></div>}
      {tab === "逐笔核对" && <div className="rr-body"><h3>信号、目标与失效价</h3><p>目标 B 和失效价 C 只从信号当天起显示，代表当时已知的研究设定；买卖点是假设成交记录。下方两条20日线用于核对入场与退出，触及的均线周期另在文字中列明。</p>{cases.length ? <><label className="rr-case-select">选择产品<select value={selectedCase?.id ?? ""} onChange={event => setCaseAsset(event.target.value)}>{cases.map(item => <option key={item.id} value={item.id}>{item.name} · {item.signal_date}</option>)}</select></label>{selectedCase && <><p className="rr-version-note"><strong>{({bought:"已模拟买入",rejected:"开盘取消",already_held:"已有持仓，不加买",unknown:"去向未知"})[selectedCase.execution_status]}</strong>：{selectedCase.execution_note}</p><p className="rr-case-facts">趋势记录起点：{selectedCase.episode_start} · {selectedCase.ma_period} 日均线组首次触及：{selectedCase.touch_date ?? "未记录"} · 信号：{selectedCase.signal_date} · A：{price(selectedCase.entry_reference)} · B：{price(selectedCase.target)} · C：{price(selectedCase.stop)} · 目标距离 / 失效距离：{selectedCase.rr == null ? "未知" : `${selectedCase.rr.toFixed(2)} 倍`}</p>{caseOption ? <Chart option={caseOption} label={`${selectedCase.name}价格和当时已知目标与失效价`} height={350} /> : <p className="rr-empty">这笔记录没有可核对的价格序列。</p>}<p className="rr-note">{selectedCase.reason}</p></>}</> : <p className="rr-empty">本版与产品组暂无可核对的逐笔价格案例。</p>}</div>}
      {tab === "规则覆盖" && <div className="rr-body"><h3>本次覆盖到哪里</h3><p>{data.scope}</p>{data.coverage.length ? <dl className="rr-coverage">{data.coverage.map((item, index) => <div key={`${item.label}-${index}`}><dt>{item.label}</dt><dd><strong>{item.value}</strong>{item.note && <span>{item.note}</span>}</dd></div>)}</dl> : <p className="rr-empty">未提供覆盖范围明细。</p>}<h3>仍不能判断的部分</h3>{data.limitations.length ? <ul>{data.limitations.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p className="rr-empty">未记录限制说明。</p>}<details><summary>资料来源与生成时间</summary><p>图表资料生成于 {data.generated_at || "未知"}；这不是行情截止日期。</p><ul>{data.sources.map((item, index) => <li key={index}><code>{item.path}</code> · SHA-256 {item.sha256}</li>)}</ul></details></div>}
      <p className="rr-footer">{selectedGroup?.label || "当前产品组"} · 规则版本和费用选择仅切换已保存结果，页面不重新计算信号或账户。</p>
    </>}
  </section>;
}
