import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import * as echarts from "echarts";
import { request } from "../../api/client";
import StrategyResearchReview from "./StrategyResearchReview";
import PaperLive from "./PaperLive";
import "./strategyPortfolios.css";

type Summary = {
  cumulative_return: number | null;
  max_drawdown: number | null;
  annual_return: number | null;
  sharpe: number | null;
  cost: number | null;
  average_exposure: number | null;
  max_stale_weight: number | null;
};
type Point = { date: string; equity: number | null; nav: number | null; drawdown: number | null; cash: number | null; return: number | null };
type Account = {
  id: string; scheme: string; name: string; role: string; status: string; started_at: string | null; rules: string[];
  history: { summary: Summary; series: Point[]; years: { year: number; return: number | null }[] };
  forward: {
    summary: Summary | null; series: Point[];
    holdings: { symbol: string; name: string; shares: number; price: number; value: number; weight: number }[];
    orders: { id: string; date: string; symbol: string; side: string; quantity: number; status: string; reason: string }[];
    decisions: { date: string; symbol: string; reason: string }[];
    targets: { symbol: string; name: string; rank: number; score: number; target_weight: number; reference_price: number }[];
    reason: string;
  };
};
type Market = {
  id: "CN" | "US"; name: string; currency: string; universe_count: number; qualified_count: number;
  source_date: string | null; limitations: string[]; accounts: Account[];
  comparison: {
    return_correlation: number | null; holding_overlap: number | null;
    combined_history: { summary: Summary; series: Point[] };
    combined_forward: { summary: Summary | null; series: Point[] };
    note: string;
  };
};
type Dashboard = {
  version: string; generated_at: string; started_at: string | null;
  run: { status: string; last_run_at: string | null; next_run_at: string | null; error: string | null };
  markets: Market[]; pending: { name: string; reason: string }[];
  sources: { title: string; url: string }[]; limitations: string[];
};
type View = "history" | "forward";

const percent = (n: number | null | undefined, signed = false) => n == null || !Number.isFinite(n) ? "—" : `${signed && n > 0 ? "+" : ""}${(n * 100).toFixed(2)}%`;
const number = (n: number | null | undefined, digits = 2) => n == null || !Number.isFinite(n) ? "—" : n.toLocaleString("zh-CN", { maximumFractionDigits: digits });
const date = (s: string | null | undefined) => s ? s.slice(0, 10) : "待记录";
const shanghaiTime = (s: string | null | undefined) => {
  if (!s) return "待记录";
  const parsed = new Date(s);
  return Number.isNaN(parsed.getTime()) ? s : new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", hour12: false,
  }).format(parsed);
};
const mainAccount = (a: Account) => a.role === "main" || a.scheme === "mv" || a.scheme === "rv";
const referenceNames: Record<string, string> = { m: "只用中期上涨", v: "只用低波动", r: "只用近期偏冷", equal: "合格股票平均分配" };
const currency = (n: number | null | undefined, code: string) => n == null || !Number.isFinite(n) ? "—" : `${code === "CNY" ? "¥" : code === "USD" ? "$" : ""}${number(n)}`;

function EquityChart({ accounts, view, combined }: { accounts: Account[]; view: View; combined?: Point[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);
  const lines = useMemo(() => [
    ...accounts.map((a) => ({ name: a.name, points: view === "history" ? a.history.series : a.forward.series })),
    ...(combined?.length ? [{ name: "两方案组合", points: combined }] : []),
  ].filter((line) => line.points.some((p) => p.nav != null && Number.isFinite(p.nav))), [accounts, view, combined]);
  const dates = useMemo(() => {
    const observed = [...new Set(lines.flatMap((line) => line.points.map((p) => p.date)))].sort();
    if (view !== "forward" || observed.length < 2) return observed;
    // Missing observations remain gaps. Calendar dates are only chart labels;
    // the UI neither creates account values nor determines trading sessions.
    const calendar: string[] = [];
    const cursor = new Date(`${observed[0]}T00:00:00Z`);
    const end = observed[observed.length - 1];
    while (cursor.toISOString().slice(0, 10) <= end) {
      calendar.push(cursor.toISOString().slice(0, 10));
      cursor.setUTCDate(cursor.getUTCDate() + 1);
    }
    return calendar;
  }, [lines, view]);

  useEffect(() => {
    if (!ref.current) return;
    const inst = echarts.init(ref.current, undefined, { renderer: "canvas" });
    chart.current = inst;
    const resize = new ResizeObserver(() => inst.resize());
    resize.observe(ref.current);
    return () => { resize.disconnect(); inst.dispose(); chart.current = null; };
  }, [lines.length]);
  useEffect(() => {
    if (!chart.current) return;
    chart.current.setOption({
      animation: false,
      color: ["#2464a4", "#a9672b", "#64816a"],
      grid: { top: 54, right: 22, bottom: 36, left: 53 },
      legend: { type: "scroll", top: 8, left: 8, right: 8, textStyle: { fontSize: 12 } },
      tooltip: { trigger: "axis", valueFormatter: (value: unknown) => typeof value === "number" ? number(value, 4) : "—" },
      xAxis: { type: "category", data: dates, boundaryGap: false, axisLabel: { hideOverlap: true } },
      yAxis: { type: "value", name: "净值", scale: true, axisLabel: { formatter: (v: number) => number(v, 2) } },
      series: lines.map((line) => {
        const byDate = new Map(line.points.map((p) => [p.date, p.nav]));
        return { name: line.name, type: "line", showSymbol: dates.length < 12, connectNulls: false, data: dates.map((day) => byDate.get(day) ?? null), lineStyle: { width: 2 } };
      }),
    }, true);
  }, [dates, lines]);
  if (!lines.length) return <p className="sp-empty">{view === "forward" ? "尚无冻结日之后的合格收盘估值；这里不会补一条平线。" : "历史净值暂无可用数据。"}</p>;
  return <div ref={ref} className="sp-chart" role="img" aria-label={`${view === "history" ? "历史检验" : "前向记录"}净值曲线`} />;
}

function MetricCard({ account, view, currencyCode }: { account: Account; view: View; currencyCode: string }) {
  const summary = view === "history" ? account.history.summary : account.forward.summary;
  return <article className="sp-card">
    <div className="sp-card-head"><h4>{account.name}</h4><span>{view === "forward" ? account.status : "历史检验"}</span></div>
    {summary ? <div className="sp-metrics">
      <div><small>累计净收益</small><strong>{percent(summary.cumulative_return, true)}</strong></div>
      <div><small>最大回撤</small><strong>{percent(summary.max_drawdown)}</strong></div>
      <div><small>累计费用</small><strong>{currency(summary.cost, currencyCode)}</strong></div>
      <div><small>平均投入仓位</small><strong>{percent(summary.average_exposure)}</strong></div>
      <div><small>年化收益</small><strong>{percent(summary.annual_return, true)}</strong></div>
      <div><small>夏普值</small><strong>{number(summary.sharpe)}</strong></div>
      <div><small>最高未知估值占比</small><strong>{percent(summary.max_stale_weight)}</strong></div>
    </div> : <p className="sp-empty">{account.forward.reason || "等待收盘后形成第一条有效账户估值。"}</p>}
    {view === "forward" && <p className="sp-minor">实际开始：{shanghaiTime(account.started_at)}（北京时间）· 有效估值 {account.forward.series.filter((p) => p.nav != null).length} 日</p>}
    <details><summary>查看这套方案的规则</summary>{account.rules.length ? <ul>{account.rules.map((r, i) => <li key={i}>{r}</li>)}</ul> : <p>规则说明尚未提供，请核对来源。</p>}</details>
  </article>;
}

function AccountDetail({ account, market }: { account: Account; market: Market }) {
  const f = account.forward;
  return <details className="sp-detail"><summary>{account.name} · 股票名单、调仓和退出理由</summary>
    <h5>当前持仓</h5>
    {f.holdings.length ? <div className="sp-scroll"><table><thead><tr><th>股票</th><th>研究单位</th><th>参考价格</th><th>市值</th><th>仓位</th></tr></thead><tbody>{f.holdings.map((h) => <tr key={h.symbol}><td>{h.name || h.symbol}<small>{h.symbol}</small></td><td>{number(h.shares)}</td><td>{currency(h.price, market.currency)}</td><td>{currency(h.value, market.currency)}</td><td>{percent(h.weight)}</td></tr>)}</tbody></table></div> : <p className="sp-minor">暂无已记录持仓。</p>}
    <p className="sp-minor">研究单位可含小数，仅供模拟账户计算，不能当作实际股票股数或可成交数量。</p>
    <h5>候选股票与目标仓位</h5>
    {f.targets.length ? <div className="sp-scroll"><table><thead><tr><th>排名</th><th>股票</th><th>评分</th><th>目标仓位</th><th>参考价格</th></tr></thead><tbody>{f.targets.map((t) => <tr key={t.symbol}><td>{t.rank}</td><td>{t.name || t.symbol}<small>{t.symbol}</small></td><td>{number(t.score)}</td><td>{percent(t.target_weight)}</td><td>{currency(t.reference_price, market.currency)}</td></tr>)}</tbody></table></div> : <p className="sp-minor">暂无合格候选名单。</p>}
    <h5>最近调仓记录</h5>
    {f.orders.length ? <ul className="sp-list">{[...f.orders].reverse().slice(0, 12).map((o) => <li key={o.id}><strong>{date(o.date)} · {o.symbol} · {o.side === "buy" ? "申请买入" : o.side === "sell" ? "申请退出" : o.side}</strong> {number(o.quantity)} 研究单位 · {o.status}<span>{o.reason}</span></li>)}</ul> : <p className="sp-minor">暂无订单记录；候选名单不等于已经成交。</p>}
    <h5>等待与退出理由</h5>
    {f.decisions.length ? <ul className="sp-list">{[...f.decisions].reverse().slice(0, 12).map((d, i) => <li key={`${d.date}-${d.symbol}-${i}`}><strong>{date(d.date)} · {d.symbol || "账户"}</strong><span>{d.reason}</span></li>)}</ul> : <p className="sp-minor">暂无当时决策记录。</p>}
  </details>;
}

export default function StrategyPortfolios() {
  const [section, setSection] = useState<"live" | "review" | "ledger">("live");
  const [marketId, setMarketId] = useState<"CN" | "US">("CN");
  const [view, setView] = useState<View>("history");
  const { data, error, isLoading } = useQuery({ queryKey: ["strategyPortfolios"], queryFn: () => request<Dashboard>("/strategy-portfolios"), enabled: section === "ledger", staleTime: 60_000, refetchInterval: 60_000, retry: false });
  const market = data?.markets.find((m) => m.id === marketId);
  const primary = market?.accounts.filter(mainAccount) ?? [];
  const references = market?.accounts.filter((a) => !mainAccount(a)) ?? [];
  const comparison = market?.comparison;
  const historyPoints = primary[0]?.history.series ?? [];
  const historyRange = historyPoints.length ? `${historyPoints[0].date} 至 ${historyPoints[historyPoints.length - 1].date}` : "待提供";

  return <div className="sp-root">
    <div className="sp-section-tabs" role="tablist" aria-label="个股策略内容">
      <button type="button" role="tab" aria-selected={section === "live"} aria-controls="sp-live-panel" id="sp-live-tab" onClick={() => setSection("live")}>真实行情模拟账户</button>
      <button type="button" role="tab" aria-selected={section === "review"} aria-controls="sp-review-panel" id="sp-review-tab" onClick={() => setSection("review")}>下一批策略审核</button>
      <button type="button" role="tab" aria-selected={section === "ledger"} aria-controls="sp-ledger-panel" id="sp-ledger-tab" onClick={() => setSection("ledger")}>已冻结方案记录</button>
    </div>
    <div id="sp-live-panel" role="tabpanel" aria-labelledby="sp-live-tab" hidden={section !== "live"}>{section === "live" && <PaperLive />}</div>
    <div id="sp-review-panel" role="tabpanel" aria-labelledby="sp-review-tab" hidden={section !== "review"}>{section === "review" && <StrategyResearchReview />}</div>
    <div id="sp-ledger-panel" role="tabpanel" aria-labelledby="sp-ledger-tab" hidden={section !== "ledger"}>
    <div className="sp-intro"><h2>A 股与美股个股因子组合</h2><p>两套完整选股、持仓和退出方案分市场看。当前历史检验用已见过的过去行情，尚无独立新资料验证；前向记录只从规则冻结并实际启动后计算。</p></div>
    {isLoading && <p className="sp-empty" role="status">正在读取双策略账户…</p>}
    {error && <p className="sp-empty sp-alert" role="alert">个股策略资料读取失败：{(error as Error).message}</p>}
    {data && <>
      <div className="sp-controls"><div role="tablist" aria-label="股票市场">{(["CN", "US"] as const).map((id) => <button key={id} type="button" role="tab" aria-selected={marketId === id} onClick={() => setMarketId(id)}>{id === "CN" ? "A 股" : "美股"}</button>)}</div><div role="tablist" aria-label="资料阶段"><button type="button" role="tab" aria-selected={view === "history"} onClick={() => setView("history")}>历史检验</button><button type="button" role="tab" aria-selected={view === "forward"} onClick={() => setView("forward")}>从冻结日起前向</button></div></div>
      <p className="sp-meta">当前行情截至 {date(market?.source_date)} · 当前候选范围 {market?.universe_count ?? 0} 只 · 当前选股合格 {market?.qualified_count ?? 0} 只 · 前向开始 {shanghaiTime(data.started_at)} · 最近运行 {shanghaiTime(data.run.last_run_at)} · 下次检查 {shanghaiTime(data.run.next_run_at)}（时间均为北京时间）</p>
      {data.run.error && <p className="sp-alert">运行异常：{data.run.error}</p>}
      {market ? <>
        <section className="sp-panel"><h3>{view === "history" ? "两套主方案的历史净值" : "两套主方案的前向净值"}</h3><p className="sp-minor">{view === "history" ? `实际历史区间：${historyRange}；每套方案初始研究本金 ${currency(100000, market.currency)}。单边费用按 ${market.id === "CN" ? "0.25%" : "0.10%"} 假设，较高费用对照按 ${market.id === "CN" ? "0.50%" : "0.25%"} 假设；累计费用按本币金额列出。这些是过去行情上的假设结果，尚未经过独立新资料验证。` : "仅画真实记录的收盘估值；断档不连接成连续收益。"}</p><EquityChart accounts={primary} view={view} combined={view === "history" ? comparison?.combined_history?.series : comparison?.combined_forward?.series} /><div className="sp-cards">{primary.map((a) => <MetricCard key={a.id} account={a} view={view} currencyCode={market.currency} />)}</div>{primary.length === 0 && <p className="sp-empty">该市场尚无两套可展示的主方案。</p>}</section>
        {view === "history" ? <>
          <section className="sp-panel"><h3>简单方案对照</h3><p className="sp-minor">“只用中期上涨”和“只用低波动”等单一方法是历史简单对手；看组合改善了什么，以及多付出的费用和仓位代价。</p><div className="sp-scroll"><table><thead><tr><th>方案</th><th>累计净收益</th><th>最大回撤</th><th>费用（{market.currency}）</th><th>平均仓位</th><th>年化收益</th><th>夏普值</th></tr></thead><tbody>{references.map((a) => <tr key={a.id}><td>{referenceNames[a.scheme] || a.name}</td><td>{percent(a.history.summary.cumulative_return, true)}</td><td>{percent(a.history.summary.max_drawdown)}</td><td>{currency(a.history.summary.cost, market.currency)}</td><td>{percent(a.history.summary.average_exposure)}</td><td>{percent(a.history.summary.annual_return, true)}</td><td>{number(a.history.summary.sharpe)}</td></tr>)}</tbody></table></div>{references.length === 0 && <p className="sp-empty">历史对照尚未提供。</p>}</section>
        </> : <><p className="sp-minor">当前运行状态：{data.run.status}。没有前向收盘估值时，收益、回撤和夏普值留空；历史候选不能当作已执行订单。</p>{primary.map((a) => <AccountDetail key={a.id} account={a} market={market} />)}</>}
        {comparison && <section className="sp-panel"><h3>{view === "history" ? "两套方案的历史组合" : "两套方案的前向组合"}</h3>
          {view === "history" ? <><div className="sp-compare"><div><small>每日收益一起变动的程度</small><strong>{number(comparison.return_correlation, 3)}</strong></div><div><small>持股重合比例</small><strong>{percent(comparison.holding_overlap)}</strong></div><div><small>组合累计净收益</small><strong>{percent(comparison.combined_history?.summary?.cumulative_return, true)}</strong></div><div><small>组合最大回撤</small><strong>{percent(comparison.combined_history?.summary?.max_drawdown)}</strong></div></div>{comparison.return_correlation != null && comparison.return_correlation >= 0.7 && <p className="sp-minor">两套方案的每日收益常常同向变动，不能把它们当成低相关的两份独立收益来源。</p>}<p className="sp-minor">{comparison.note || "相关程度与持股重合需结合有效日期和市场环境判断。"}</p></> : <>
            {comparison.combined_forward?.summary ? <div className="sp-compare"><div><small>组合累计净收益</small><strong>{percent(comparison.combined_forward.summary.cumulative_return, true)}</strong></div><div><small>组合最大回撤</small><strong>{percent(comparison.combined_forward.summary.max_drawdown)}</strong></div><div><small>实际估值日数</small><strong>{comparison.combined_forward.series.filter((p) => p.nav != null).length}</strong></div></div> : <p className="sp-empty">等待两套方案在冻结后形成共同有效的收盘估值；目前没有前向组合收益。</p>}
            <p className="sp-minor">组合按同一笔研究本金各分一半给两套方案。前向收益相关程度和持股重合仍在积累，不沿用历史检验的数字。</p>
          </>}
        </section>}
        {market.limitations.length > 0 && <section className="sp-panel"><h3>这个市场的资料限制</h3><ul>{market.limitations.map((note, i) => <li key={i}>{note}</li>)}</ul></section>}
      </> : <p className="sp-empty">{marketId === "CN" ? "A 股" : "美股"}资料尚未提供，等待该市场的合格数据。</p>}
      {data.pending.length > 0 && <section className="sp-panel"><h3>待补资料</h3><ul>{data.pending.map((item, i) => <li key={i}>{item.name}：{item.reason}</li>)}</ul></section>}
      {data.limitations.length > 0 && <section className="sp-panel"><h3>共同限制</h3><ul>{data.limitations.map((note, i) => <li key={i}>{note}</li>)}</ul></section>}
      {data.sources.length > 0 && <details className="sp-detail"><summary>资料来源</summary><ul>{data.sources.map((source, i) => <li key={i}><a href={source.url} target="_blank" rel="noreferrer">{source.title}</a></li>)}</ul></details>}
      <p className="sp-foot">页面只读展示研究用虚拟账户。资料生成于 {shanghaiTime(data.generated_at)}（北京时间）；账户成绩不等于真实交易收益。</p>
    </>}
    </div>
  </div>;
}
