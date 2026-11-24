import { useEffect, useMemo, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import * as echarts from "echarts";

type Point = { date: string; nav: number | null; unknown_weight?: number };
type Order = { id: string; symbol: string; side: string; execute_date: string; status: string; created_at: string; observed_at?: string; failure_reason?: string; reason: string };
type Account = {
  id: string; scheme: string; name: string; role: string; cash: number;
  holdings: { symbol: string; name?: string; weight: number }[];
  targets: { symbol: string; name?: string; rank: number; target_weight: number }[];
  orders: Order[]; series: Point[];
  summary: null | { cumulative_return: number; max_drawdown: number; cost: number; max_stale_weight: number };
  relative_to_equal?: { cumulative_difference_pp: number | null; relative_wealth_return: number | null; matched_dates: number };
};
type Data = {
  version: string; started_at: string | null; generated_at: string;
  run: { status: string; error: string | null; next_run_at: string | null; last_run_at: string | null };
  market: { source_date: string | null; expected_date: string | null; qualified_count: number; universe_count: number; status: string; reason?: string };
  accounts: Account[]; limitations: string[];
  parent_index: { name: string; status: string; reason: string };
  pending: { name: string; reason: string }[];
};
const pct = (value: number | null | undefined) => value == null ? "待积累" : `${(value * 100).toFixed(2)}%`;
const time = (value: string | null | undefined) => value ? new Intl.DateTimeFormat("zh-CN", { timeZone: "Asia/Shanghai", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date(value)) : "待记录";

async function load(): Promise<Data> {
  // The independently supervised paper service avoids restarting the shared API.
  if (!["127.0.0.1", "localhost"].includes(window.location.hostname)) throw new Error("模拟账户目前仅在本机可读");
  const response = await fetch(`http://127.0.0.1:8029/api/strategy-paper-live`, { signal: AbortSignal.timeout(12_000) });
  if (!response.ok) throw new Error(`模拟账户服务返回 ${response.status}`);
  return response.json();
}

function Curves({ accounts }: { accounts: Account[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const dates = useMemo(() => [...new Set(accounts.flatMap(a => a.series.map(p => p.date)))].sort(), [accounts]);
  useEffect(() => {
    if (!ref.current || !dates.length) return;
    const chart = echarts.init(ref.current);
    const calendar: string[] = [];
    const cursor = new Date(`${dates[0]}T00:00:00Z`);
    while (cursor.toISOString().slice(0, 10) <= dates[dates.length - 1]) {
      if (cursor.getUTCDay() !== 0 && cursor.getUTCDay() !== 6) calendar.push(cursor.toISOString().slice(0, 10));
      cursor.setUTCDate(cursor.getUTCDate() + 1);
    }
    chart.setOption({ animation: false, color: ["#2464a4", "#a9672b", "#64816a", "#8c8c8c"],
      legend: { top: 0 }, tooltip: { trigger: "axis" }, grid: { top: 50, left: 60, right: 20, bottom: 40 },
      xAxis: { type: "category", data: calendar }, yAxis: { type: "value", scale: true, name: "模拟净值" },
      series: accounts.map(a => { const byDate = new Map(a.series.map(p => [p.date, p.unknown_weight ? null : p.nav]));
        return { name: a.name, type: "line", connectNulls: false, showSymbol: true, data: calendar.map(d => byDate.get(d) ?? null) }; }),
    });
    const observer = new ResizeObserver(() => chart.resize()); observer.observe(ref.current);
    return () => { observer.disconnect(); chart.dispose(); };
  }, [accounts, dates]);
  return dates.length ? <div ref={ref} className="sp-chart" role="img" aria-label="新模拟账户与同池对照的前向收益曲线" /> : <p className="sp-empty">尚无启动后的完整收盘估值。收到后会显示四条曲线，缺日和未知估值保留空缺。</p>;
}

export default function PaperLive() {
  const { data, error, isLoading } = useQuery({ queryKey: ["strategyPaperLive"], queryFn: load, staleTime: 30_000, refetchInterval: 60_000, retry: false });
  return <div>
    <div className="sp-intro"><h2>真实行情模拟账户</h2><p>从本次规则冻结后观察选股、调仓、费用和收益。四个账户各用 10 万美元模拟本金，比较同一起点的表现。</p></div>
    {isLoading && <p role="status">正在读取模拟账户…</p>}
    {error && <p className="sp-alert" role="alert">模拟账户当前不可读：{(error as Error).message}。未取得的行情与收益不按零处理。</p>}
    {data && <>
      <section className="sp-panel"><h3>{data.run.status}</h3>
        <p className="sp-meta">实际启动 {time(data.started_at)} · 下次收盘采集 {time(data.run.next_run_at)} · 最近入账 {time(data.run.last_run_at)}（北京时间）</p>
        <p className="sp-minor">持续记录需要本机运行、联网并连接数据外盘。当前采集进程独立运行；开机自动恢复尚未接通。</p>
        <p>美股固定 {data.market.universe_count} 只股票 · 行情截至 {data.market.source_date ?? "待取得"} · 应有收盘 {data.market.expected_date ?? "待核"} · 当前合格 {data.market.qualified_count} 只</p>
        {data.run.error && <p className="sp-alert">采集或记账异常：{data.run.error}</p>}
        <p className="sp-minor">{data.market.reason}</p>
        <Curves accounts={data.accounts} />
        <div className="sp-scroll"><table><thead><tr><th>策略 / 对照</th><th>模拟累计收益</th><th>最大回撤</th><th>相对同池均分</th><th>持股 / 待单</th><th>现金（美元）</th></tr></thead><tbody>
          {data.accounts.map(a => <tr key={a.id}><td>{a.name}</td><td>{pct(a.summary?.cumulative_return)}</td><td>{pct(a.summary?.max_drawdown)}</td><td>{a.relative_to_equal?.cumulative_difference_pp == null ? "待积累" : `${a.relative_to_equal.cumulative_difference_pp.toFixed(2)} 个百分点`}</td><td>{a.holdings.length} / {a.orders.filter(o => o.status === "等待").length}</td><td>{a.cash.toLocaleString("zh-CN", { maximumFractionDigits: 2 })}</td></tr>)}
        </tbody></table></div>
        <p className="sp-minor">同池均分包含共同的资格与均线过滤，是选股对照。母指数 {data.parent_index.name}：{data.parent_index.reason}。短期不展示年化或夏普。</p>
      </section>
      {data.accounts.map(a => <details className="sp-detail" key={a.id}><summary>{a.name} · 名单、成交与费用</summary>
        <p>持股 {a.holdings.length} 只 · 候选 {a.targets.length} 只 · 费用 ${a.summary?.cost.toFixed(2) ?? "0.00"}（单边 0.10% 假设）· 最高未知估值占比 {pct(a.summary?.max_stale_weight)}</p>
        <p>{a.targets.length ? a.targets.map(t => `${t.name || t.symbol} ${pct(t.target_weight)}`).join("；") : "等待合格的收盘数据生成名单。"}</p>
        {a.orders.length ? <div className="sp-scroll"><table><thead><tr><th>股票</th><th>动作</th><th>计划交易日</th><th>状态 / 原因</th><th>决策记录时间</th></tr></thead><tbody>{[...a.orders].reverse().slice(0, 30).map(o => <tr key={o.id}><td>{o.symbol}</td><td>{o.side === "buy" ? "模拟买入" : "模拟卖出"}</td><td>{o.execute_date}</td><td>{o.status} · {o.failure_reason || o.reason}</td><td>{time(o.created_at)}</td></tr>)}</tbody></table></div> : <p>暂无订单。已错过的开盘不会补成交。</p>}
      </details>)}
      <details className="sp-detail"><summary>规则、适用股票池与研究边界</summary>
        <p>动量、动量＋低波动和单低波动每月选前 20 只、每只目标 5%；均分对照使用全部同池合格股票。新买要求在 120 日均线上，跌破后申请下次开盘退出。单只超过 10% 申请减回 5%。收盘冻结数量，下一交易日开盘报价模拟；不可成交就保留原因。</p>
        <ul>{data.limitations.map(x => <li key={x}>{x}</li>)}</ul>
        <a href="/library?report=docs%2Fexperiments%2Fstrategy-paper-live-start-2026-11-02.md">查看本次启动与候选准入记录</a>
      </details>
      <section className="sp-panel"><h3>财务组合的接入状态</h3><ul>{data.pending.map(p => <li key={p.name}>{p.name}：{p.reason}</li>)}</ul></section>
      <p className="sp-foot">数据读取于 {time(data.generated_at)} · {data.version} · 旧账户保留在“已冻结方案记录”。</p>
    </>}
  </div>;
}
