import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import * as echarts from "echarts";
import { request } from "../../api/client";
import type { ObservationRange, StrategyAccount, StrategyDashboard, StrategyDecision } from "./model";
import { accountRole, accountStatus, availableDays, chartValues, dayDecisions, decisionReasons, displayDate, displayNumber, eventText, firstUsableDay, healthText, metricReason, metricText, orderStatusText, plotDates, plottedAccounts, ruleText, runnerView, RULE_FIELDS, validPoint } from "./viewModel";
import "./strategyForward.css";

const COLORS = ["#2563eb", "#a36312", "#596d85", "#0b9b64"];

function useDashboard(range: ObservationRange) {
  return useQuery({
    queryKey: ["strategyForward", range],
    queryFn: () => request<StrategyDashboard>(`/fwd-ledger/strategies?range=${range}`),
    staleTime: 60_000,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
    retry: false,
  });
}

function PointChart({ accounts, recordedDates, selectedDay, onDay }: { accounts: StrategyAccount[]; recordedDates: string[]; selectedDay: string; onDay: (day: string) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);
  const dates = useMemo(() => plotDates(accounts, recordedDates), [accounts, recordedDates]);

  useEffect(() => {
    if (!ref.current) return;
    const inst = echarts.init(ref.current, undefined, { renderer: "canvas" });
    chart.current = inst;
    const resize = new ResizeObserver(() => inst.resize());
    resize.observe(ref.current);
    return () => { resize.disconnect(); inst.dispose(); chart.current = null; };
  }, []);

  useEffect(() => {
    const inst = chart.current;
    if (!inst) return;
    const names = accounts.map((a) => a.name);
    const makeSeries = (key: "nav" | "drawdown_pct" | "cash", axis: number, suffix: string) => accounts.map((a, i) => ({
      name: `${a.name}${suffix}`,
      type: "line" as const,
      xAxisIndex: axis,
      yAxisIndex: axis,
      showSymbol: dates.length < 12,
      connectNulls: false,
      smooth: false,
      symbolSize: 6,
      lineStyle: { width: 2, color: COLORS[i % COLORS.length] },
      itemStyle: { color: COLORS[i % COLORS.length] },
      data: chartValues(a, dates, key),
    }));
    inst.setOption({
      animation: false,
      color: COLORS,
      grid: [
        { left: 54, right: 24, top: 38, height: "43%" },
        { left: 54, right: 24, top: "57%", height: "15%" },
        { left: 54, right: 24, top: "79%", height: "14%" },
      ],
      legend: { type: "scroll", data: names.map((n) => `${n}净值`), top: 2, left: 95, right: 10, textStyle: { color: "#5b6473", fontSize: 11 } },
      tooltip: { trigger: "axis", axisPointer: { type: "cross" }, valueFormatter: (value: unknown) => typeof value === "number" ? displayNumber(value) : "—" },
      axisPointer: { link: [{ xAxisIndex: "all" }] },
      xAxis: [0, 1, 2].map((i) => ({ type: "category" as const, gridIndex: i, data: dates, axisLabel: { show: i === 2, color: "#7b8494" }, axisLine: { lineStyle: { color: "#dfe5ee" } }, axisTick: { show: false } })),
      yAxis: [
        { type: "value", gridIndex: 0, name: "净值", scale: true, nameTextStyle: { color: "#5b6473" }, axisLabel: { color: "#7b8494" }, splitLine: { lineStyle: { color: "#edf0f5" } } },
        { type: "value", gridIndex: 1, name: "回撤 %", max: 0, nameTextStyle: { color: "#5b6473" }, axisLabel: { color: "#7b8494" }, splitLine: { lineStyle: { color: "#edf0f5" } } },
        { type: "value", gridIndex: 2, name: "现金 元", scale: true, nameTextStyle: { color: "#5b6473" }, axisLabel: { color: "#7b8494" }, splitLine: { lineStyle: { color: "#edf0f5" } } },
      ],
      series: [
        ...makeSeries("nav", 0, "净值"),
        ...makeSeries("drawdown_pct", 1, "回撤"),
        ...makeSeries("cash", 2, "现金"),
      ],
    }, true);
    const click = (event: { name?: string }) => { if (event.name && dates.includes(event.name)) onDay(event.name); };
    inst.on("click", click);
    return () => { inst.off("click", click); };
  }, [accounts, dates, onDay]);

  return <div className="sf-chart-wrap"><div ref={ref} className="sf-chart" role="img" aria-label={`账户净值、回撤与现金曲线，已选日期 ${selectedDay || "未选择"}`} /></div>;
}

function accountClass(account: StrategyAccount): string {
  return account.status === "observing" ? "is-live" : account.status === "blocked" || account.status === "stale" ? "is-alert" : "is-pending";
}

function DecisionDetail({ decision, account, source }: { decision: StrategyDecision; account?: StrategyAccount; source?: StrategyDecision }) {
  const p = decision.payload || {};
  const quote = source?.payload || p;
  const input = quote.source ? `${quote.source} · 行情时间 ${displayDate(String(quote.source_time || ""))}` : quote.source_time ? `行情时间 ${displayDate(String(quote.source_time))}` : "未关联行情来源";
  const reasons = decisionReasons(p);
  const hasFill = decision.kind === "fill" && p.qty != null && p.price != null;
  const fill = hasFill ? `${displayNumber(Number(p.qty))} 份 × ${displayNumber(Number(p.price), " 元", 6)}，费用 ${displayNumber(Number(p.fee), " 元")}` : decision.kind === "partially_filled" ? `剩余 ${displayNumber(Number(p.remaining_qty))} 份待成交` : "本条未记模拟成交";
  const order = decision.kind === "order_queued" ? "订单已排队，尚未成交" : p.order_id ? "关联已记录订单" : "本条无订单";
  return <li className="sf-decision">
    <div><strong>{account?.name || "共同运行记录"}</strong><span className="sf-quiet">{displayDate(decision.at)} · {eventText(decision.kind, p.action)}</span></div>
    {reasons.length > 0 && <p>{reasons.join("；")}</p>}
    <dl><div><dt>当时资料</dt><dd>{input}</dd></div><div><dt>订单</dt><dd>{order}</dd></div><div><dt>模拟成交</dt><dd>{fill}</dd></div></dl>
    <details><summary>查看当时记录细节</summary><pre>{JSON.stringify(p, (key, value) => /hash|digest|checksum|fingerprint/i.test(key) ? undefined : value, 2)}</pre></details>
  </li>;
}

export default function StrategyForward() {
  const [range, setRange] = useState<ObservationRange>("since_start");
  const { data, error, isLoading, isFetching, refetch } = useDashboard(range);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [selectedDay, setSelectedDay] = useState("");
  const [capturing, setCapturing] = useState(false);
  const [captureMessage, setCaptureMessage] = useState("");
  const [captureError, setCaptureError] = useState("");

  useEffect(() => {
    if (!data) return;
    setSelectedIds((previous) => previous.length ? previous.filter((id) => data.accounts.some((a) => a.id === id)) : data.accounts.filter((a) => a.role === "passive_baseline" || a.role === "cash_reference").map((a) => a.id));
  }, [data]);
  const accounts = useMemo(() => data ? plottedAccounts(data, selectedIds) : [], [data, selectedIds]);
  const dates = useMemo(() => data ? availableDays(data, selectedIds) : [], [data, selectedIds]);
  const activeDay = selectedDay && dates.includes(selectedDay) ? selectedDay : data ? firstUsableDay(data, selectedIds) : "";
  const decisions = data && activeDay ? dayDecisions(data, activeDay, selectedIds) : [];
  const sourceByObservation = new Map(data?.decisions.filter((d) => d.kind === "source" && d.observation_id).map((d) => [d.observation_id, d]) || []);
  const runner = data ? runnerView(data.run, data.generated_at) : null;
  const capture = async () => {
    setCaptureError(""); setCaptureMessage(""); setCapturing(true);
    try {
      await request<StrategyDashboard>("/fwd-ledger/strategies/observe", { method: "POST" });
      const readback = await refetch();
      if (readback.error || !readback.data) throw readback.error || new Error("记录后读取失败");
      setCaptureMessage(`已完成一次采集检查，并重新读取状态：${displayDate(readback.data.generated_at)}。${readback.data.run.status === "observing" ? "已有前向记录；是否形成新估值请看日期与来源。" : "尚未形成可展示的完整账户估值。"}`);
    } catch (e) { setCaptureError((e as Error).message); }
    finally { setCapturing(false); }
  };

  return <div className="sf-root">
    <div className="sf-intro"><div><h2>完整策略观察</h2><p>从规则冻结后的真实启动时点记录虚拟账户。等待、未成交和资料缺失也会留下原因；历史行情不计入前向收益。</p></div><button type="button" className="sf-action" onClick={capture} disabled={capturing || isLoading}>{capturing ? "正在核对…" : "采集并核对一次"}</button></div>
    {captureMessage && <p className="sf-feedback" role="status">{captureMessage}</p>}
    {captureError && <p className="sf-feedback sf-error" role="alert">采集或回读失败：{captureError}</p>}
    {isLoading && <p className="sf-empty" role="status">正在读取账户记录…</p>}
    {error && <p className="sf-empty sf-error" role="alert">账户记录读取失败：{(error as Error).message}。请核对当前服务是否包含策略观察接口。</p>}
    {data && <>
      <div className="sf-runline"><span className={`sf-status ${data.run.status === "observing" ? "is-live" : data.run.status === "stale" ? "is-alert" : "is-pending"}`}>{data.run.status === "observing" ? "已开始记录" : data.run.status === "stale" ? "运行资料过期" : data.run.status === "waiting_quote" ? "等待合格行情" : "尚未启动"}</span><span className={`sf-status ${runner?.tone}`}>{runner?.label}</span><span>{runner?.detail}</span><span>规则冻结：{displayDate(data.run.frozen_at)}</span><span>实际启动：{displayDate(data.run.started_at)}</span><span>最近检查：{displayDate(data.run.last_run_at)}</span><span>行情截至：{displayDate(data.run.last_source_at)}</span><span>下次检查：{displayDate(data.run.next_run_at)}</span><span>账户核对：{data.reconciliation?.passed ? `一致（${displayDate(data.reconciliation.checked_at)}）` : data.reconciliation?.status === "checked" ? "未通过，查看运行异常" : "尚未核对"}</span><span>运行范围：本机；尚未设置开机恢复</span>{isFetching && <span>更新中…</span>}</div>
      {(data.health.length > 0 || data.pending.length > 0) && <div className="sf-health"><strong>当前限制</strong><ul>{[...data.health.map(healthText), ...data.pending].map((note, index) => <li key={`${index}-${note}`}>{note}</li>)}</ul></div>}
      <p className="sf-caption">研究接续：<a href="/library?report=docs%2Fexperiments%2Fstrategy-forward-observation-2026-10-20.md">本次实现与边界</a> · <a href="/library?report=docs%2Fexperiments%2Flowturnover-green-account-2026-10-20.md">低换手账户：当前暂不采用</a> · <a href="/library?report=docs%2Fexperiments%2Flowfreq-confirmation-execution-2026-10-20.md">小时确认：暂不升级近似过滤</a></p>
      <section className="sf-panel sf-plot-panel"><div className="sf-section-head"><div><h3>账户变化</h3><p>净值、启用以来回撤与现金。只连接有真实估值的日期，断档不会补成平线。</p></div><div className="sf-range" aria-label="比较日期范围"><button type="button" aria-pressed={range === "since_start"} onClick={() => setRange("since_start")}>启用以来</button><button type="button" aria-pressed={range === "common"} onClick={() => setRange("common")}>共同有效日期</button></div></div>
        <div className="sf-picks">{data.accounts.map((a) => <label key={a.id}><input type="checkbox" checked={selectedIds.includes(a.id)} onChange={() => setSelectedIds((ids) => ids.includes(a.id) ? ids.filter((id) => id !== a.id) : [...ids, a.id])} /><span>{a.name}</span></label>)}</div>
        {accounts.length > 0 && dates.length > 0 ? <PointChart accounts={accounts} recordedDates={dates} selectedDay={activeDay} onDay={setSelectedDay} /> : <div className="sf-empty">暂无可画的账户估值。账户需要规则冻结、实际启动与合格的新行情；待补候选不会显示一条假的平线。</div>}
        {range === "common" && <p className="sf-caption">共同日期和净值起点由服务端按各账户有效估值确定；没有交集时不比较。</p>}
      </section>
      <section className="sf-panel"><div className="sf-section-head"><div><h3>账户与规则版本</h3><p>虚拟资金独立比较，不代表已经用真钱成交，也不把各账户收益相加。</p></div></div><div className="sf-account-scroll"><table className="sf-account-table"><thead><tr><th>账户 / 性质</th><th>状态与时间</th><th>累计净收益</th><th>观测最大回撤</th><th>持仓 / 现金</th><th>统计限制</th></tr></thead><tbody>{data.accounts.map((a) => {
        const latest = [...a.series].reverse().find(validPoint);
        return <tr key={a.id}><td><strong>{a.name}</strong><small>{accountRole(a)} · 虚拟账户 · {a.id}</small></td><td><span className={`sf-status ${accountClass(a)}`}>{a.kind === "blocked" ? "规则待补" : a.kind === "external_pending" ? "等待合格完整版本" : accountStatus(a.status)}</span><small>冻结 {displayDate(a.frozen_at)}<br />启动 {displayDate(a.started_at)}<br />首次决策 {displayDate(a.first_decision_at)}<br />首次模拟成交 {displayDate(a.first_fill_at)}</small>{(a.id === "lowturnover-green" ? ["10月20日账户研究已完成一轮，当前证据暂不支持直接采用；此处等待合格的完整策略版本。"] : a.reasons).map((reason, i) => <small key={i} className="sf-reason">{reason}</small>)}</td><td>{metricText(a.metrics.cumulative_return_pct, a.metrics.reason)}<small>完整账户扣费后</small></td><td>{metricText(a.metrics.max_drawdown_pct, a.metrics.reason)}<small>仅已记录收盘估值</small></td><td>{latest ? <>{displayNumber(latest.exposure_pct, "%")} 仓位<small>现金 {displayNumber(latest.cash, " 元")} · 估值 {latest.date}{latest.provisional ? " · 暂估" : ""}</small></> : <>—<small>暂无可用估值</small></>}</td><td>有效日 {a.metrics.observations}<small>等待日 {a.metrics.wait_days == null ? "尚未记录" : a.metrics.wait_days}</small><small>年化：{a.metrics.annualized_return_pct == null ? "未满一年或资料不足" : displayNumber(a.metrics.annualized_return_pct, "%")}</small><small>夏普：{a.metrics.sharpe == null ? metricReason(a.metrics.reason) : displayNumber(a.metrics.sharpe)}</small></td></tr>;
      })}</tbody></table></div>
        <div className="sf-rules">{data.accounts.map((a) => <details key={a.id}><summary>{a.name} · 查看完整规则与资料</summary><div className="sf-rule-grid">{RULE_FIELDS.map(([key, label]) => <div key={key}><strong>{label}</strong><span>{ruleText(a.rules?.[key])}</span></div>)}</div><p className="sf-caption">规则冻结：{displayDate(a.frozen_at)} · 版本：{a.id}。未冻结候选不能按已运行策略评价。</p></details>)}</div>
      </section>
      <section className="sf-panel"><div className="sf-section-head"><div><h3>按日查看动作</h3><p>选图上的日期，或从下拉框选择已有估值或当时记录的日期。时间按上海时间显示。</p></div><label className="sf-date-label">观察日期 <select value={activeDay} onChange={(event) => setSelectedDay(event.target.value)} disabled={dates.length === 0}><option value="">暂无日期</option>{dates.map((date) => <option key={date} value={date}>{date}</option>)}</select></label></div>
        {activeDay ? <><p className="sf-caption">{activeDay} · {decisions.length} 条当时记录</p>{decisions.length ? <ul className="sf-decision-list">{decisions.map((d) => <DecisionDetail key={d.id} decision={d} account={data.accounts.find((a) => a.id === d.account_id)} source={sourceByObservation.get(d.observation_id)} />)}</ul> : <p className="sf-empty">该日期没有可见决策记录。没有交易、等待和运行缺口只能以当时存证为准。</p>}
          <div className="sf-holdings"><h4>当日账户估值与当前持仓</h4><div className="sf-account-scroll"><table><thead><tr><th>账户</th><th>当日权益</th><th>现金</th><th>仓位</th><th>当前持仓</th><th>订单</th></tr></thead><tbody>{data.accounts.filter((a) => selectedIds.includes(a.id)).map((a) => { const p = a.series.find((point) => point.date === activeDay && validPoint(point)); return <tr key={a.id}><td>{a.name}</td><td>{displayNumber(p?.equity, " 元")}</td><td>{displayNumber(p?.cash, " 元")}</td><td>{displayNumber(p?.exposure_pct, "%")}</td><td>{a.holdings.length ? a.holdings.map((h) => `${h.symbol} ${displayNumber(h.shares)} 份`).join("；") : "暂无持仓"}</td><td>{a.orders.length ? a.orders.map((o) => `${o.symbol} ${orderStatusText(o.status)} ${displayNumber(o.filled_qty)}/${displayNumber(o.requested_qty)} 份`).join("；") : "暂无订单"}</td></tr>; })}</tbody></table></div><p className="sf-caption">持仓与订单为当前账户状态；当日权益、现金、仓位取所选日期。订单不等于成交。</p></div></> : <p className="sf-empty">尚无可选择的观察日期；不会用历史回测生成当日动作。</p>}
      </section>
      <details className="sf-sources"><summary>查看行情来源时间与采集记录</summary>{data.sources.length ? <ul>{data.sources.slice(0, 20).map((source) => <li key={source.id}>行情时间 {displayDate(source.source_time)} · 收到时间 {displayDate(source.received_at)} · 记录 {source.id}</li>)}</ul> : <p>尚无真实行情采集记录。</p>}</details>
      <p className="sf-footnote">本页是研究用虚拟账户观察。前向样本尚未形成或很短时，收益优势无法判断；夏普使用账户日收益，资料不足时不计算。</p>
    </>}
  </div>;
}
