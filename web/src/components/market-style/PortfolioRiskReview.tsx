import { useState } from "react";
import TrendChart, { type LineSeries } from "./MarketTrendChart";
import "./portfolio-risk-review.css";

type CurvePoint = { date: string; nav: number | null; equity: number | null; drawdown: number | null };
type AccountSummary = { cumulative_return: number | null; max_drawdown: number | null; cost: number | null };
type Account = { name: string | null; summary: AccountSummary; curve: CurvePoint[] };
type Overlap = {
  status: "available" | "empty" | "incomplete" | "missing";
  left_count: number | null; right_count: number | null;
  common_count: number | null; union_count: number | null;
  count_overlap: number | null; weight_overlap: number | null;
  common_symbols: string[];
};

export type PortfolioReview = {
  market: string; available: boolean; reason?: string;
  generated_at?: string | null; source_date?: string | null;
  history?: {
    period_start: string | null; period_end: string | null;
    common_curve_days: number; common_valid_return_days: number;
    initialization_dates_excluded: string[];
    both_down_days: number; either_down_days: number;
    both_down_share_all_valid_days: number | null;
    both_down_share_either_down_days: number | null;
    return_correlation_recomputed: number | null;
    return_correlation_reported: number | null;
    return_correlation_difference: number | null;
    monthly: { common_months: number; both_down_months: number;
      series: { month: string; start: string; end: string; mv_return: number; rv_return: number; both_down: boolean }[] };
    targets: { status: string; count_overlap: number | null; weight_overlap: number | null; date: string | null };
    accounts: { mv: Account; rv: Account };
    combined: { summary_source: string; summary: AccountSummary; curve: CurvePoint[] };
  };
  forward?: {
    started_at: string | null; common_recorded_days: number; common_valid_return_days: number;
    both_down_days: number | null; both_down_loss_50_50_initial_capital: number | null;
    targets: Overlap; holdings: Overlap;
  };
  conclusion?: string; limitations?: string[];
};

const valid = (value: number | null | undefined): value is number =>
  typeof value === "number" && Number.isFinite(value);
const pct = (value: number | null | undefined, digits = 1) => valid(value) ? `${(value * 100).toFixed(digits)}%` : "未取得";
const signed = (value: number | null | undefined) => valid(value) ? `${value > 0 ? "+" : ""}${pct(value)}` : "未取得";

function curveData(history: NonNullable<PortfolioReview["history"]>, mode: "return" | "drawdown") {
  const accounts = [
    { name: history.accounts.mv.name ?? "中期上涨＋低波动", curve: history.accounts.mv.curve, color: "#366eaa" },
    { name: history.accounts.rv.name ?? "近期偏冷＋低波动", curve: history.accounts.rv.curve, color: "#c17842" },
    { name: "初始资金各半", curve: history.combined.curve, color: "#6658a4" },
  ];
  const dates = [...new Set(accounts.flatMap((account) => account.curve.map((point) => point.date)))].sort();
  const series: LineSeries[] = accounts.map((account) => {
    const byDate = new Map(account.curve.map((point) => [point.date, point]));
    return { name: account.name, color: account.color,
      values: dates.map((date) => {
        const point = byDate.get(date);
        const value = mode === "return" ? point?.nav : point?.drawdown;
        return valid(value) ? (mode === "return" ? value - 1 : value) * 100 : null;
      }) };
  });
  return { dates, series };
}

export default function PortfolioRiskReview({ portfolio, loading, error, phase = "history" }: {
  portfolio?: PortfolioReview; loading: boolean; error: boolean; phase?: "forward" | "history";
}) {
  const [mode, setMode] = useState<"return" | "drawdown">("return");
  const history = !loading && !error && portfolio?.available ? portfolio.history : undefined;
  const forward = !loading && !error && portfolio?.available ? portfolio.forward : undefined;
  const chart = history ? curveData(history, mode) : null;
  const worstMonths = history?.monthly.series.filter((row) => row.both_down)
    .sort((a, b) => (a.mv_return + a.rv_return) - (b.mv_return + b.rv_return)).slice(0, 3) ?? [];
  const targets = forward?.targets;
  const targetReady = targets?.status === "available";
  const holdingsReady = forward?.holdings.status === "available";
  const sourceLabel = portfolio?.market === "CN" ? "A股" : portfolio?.market === "US" ? "美股" : "市场";

  return <section className="ms-portfolio-risk" aria-label={`${sourceLabel}多策略共同风险`}>
    <header className="ms-portfolio-risk__head">
      <div><h2>{phase === "forward" ? "从启动日起的前向跟踪" : "历史对照：两套策略会一起亏吗？"}</h2><p>{phase === "forward" ? `${sourceLabel} · 启动后逐日记录的报价模拟；未记录的成绩保持空白` : `${sourceLabel} · 过去行情模拟 · ${history?.period_start ?? "日期未取得"} 至 ${history?.period_end ?? "日期未取得"}`}</p></div>
      {phase === "forward" && forward && <span className="ms-portfolio-risk__source">选股资料日 {portfolio?.source_date ?? "未取得"}</span>}
    </header>
    {loading && <p role="status" className="ms-portfolio-risk__state">正在读取策略比较…</p>}
    {error && <p role="alert" className="ms-portfolio-risk__state">策略比较读取失败，暂不能判断共同风险。</p>}
    {!loading && !error && !history && <p className="ms-portfolio-risk__state">{portfolio?.reason ?? "两套主策略的可比资料尚未取得。"}</p>}
    {phase === "forward" && forward && <>
      <div className="ms-portfolio-risk__keyfacts">
        <div><span>启动日期</span><strong>{forward.started_at?.slice(0, 10) ?? "未取得"}</strong></div>
        <div><span>共同有效收益日</span><strong>{forward.common_valid_return_days} 日</strong></div>
        <div><span>共同下跌日</span><strong>{forward.both_down_days == null ? "尚无可比收益" : `${forward.both_down_days} 日`}</strong></div>
      </div>
      <div className="ms-portfolio-risk__forward">
        <strong>{forward?.started_at?.slice(0, 10) ?? "开始日期未取得"}起的新记录</strong>
        {targetReady ? <p>两套目标名单各 {targets?.left_count} / {targets?.right_count} 只，共选 {targets?.common_count} 只；占合并去重名单 {pct(targets?.count_overlap)}，目标资金权重重合 {pct(targets?.weight_overlap)}。这些只是计划选入的股票。</p>
          : <p>两套前向目标名单尚未齐全，不能计算共同选股。</p>}
        <p>{holdingsReady ? `模拟持仓已有记录；共同持仓权重 ${pct(forward?.holdings.weight_overlap)}。`
          : forward?.holdings.status === "empty" ? "目前两套模拟持仓均为空，实际持仓资金重合尚无法计算。"
            : "目前没有两套均可核对的模拟持仓，实际持仓资金重合仍无法判断。"} {forward?.common_valid_return_days ? `已有 ${forward.common_valid_return_days} 个共同收益日。` : "目前没有可比的前向收益。"}这是报价模拟，不代表真实账户持仓或交易。</p>
      </div>
      {targetReady && <details className="ms-portfolio-risk__details"><summary>查看共同候选代码</summary><p>{targets?.common_symbols.join("、") || "无共同候选"}</p><p>这些是计划名单，不表示已持有。</p></details>}
    </>}
    {phase === "forward" && !loading && !error && !forward && <p className="ms-portfolio-risk__state">前向记录尚未取得，暂不以历史收益替代。</p>}
    {phase === "history" && history && <>
      <div className="ms-portfolio-risk__keyfacts">
        <div><span>同一天都亏</span><strong>{history.common_valid_return_days ? `${history.both_down_days} / ${history.common_valid_return_days} 日` : "无可比收益"}</strong></div>
        <div><span>同一月都亏</span><strong>{history.monthly.common_months ? `${history.monthly.both_down_months} / ${history.monthly.common_months} 月` : "无可比月份"}</strong></div>
        <div><span>日收益一起变化程度</span><strong>{valid(history.return_correlation_recomputed) ? history.return_correlation_recomputed.toFixed(2) : "未取得"}</strong></div>
      </div>
      <p className="ms-portfolio-risk__reading">{history.common_valid_return_days
        ? "一起变化的程度越接近1，涨跌越同步；共同下跌不等于持有同一批股票，也不能证明属于同一种市场风格。分散亏损的实际变化见下方三套账户比较。"
        : "没有共同有效收益记录，暂不能判断一起涨跌或分散风险的效果。"}</p>
      <div className="ms-portfolio-risk__comparison" role="table" aria-label="三种账户历史结果比较">
        <div className="ms-portfolio-risk__comparison-head" role="row"><span role="columnheader">相同起点：10万</span><span role="columnheader">累计收益</span><span role="columnheader">最大下跌</span></div>
        {([
          [history.accounts.mv.name ?? "中期上涨＋低波动", history.accounts.mv.summary],
          [history.accounts.rv.name ?? "近期偏冷＋低波动", history.accounts.rv.summary],
          ["初始资金各半", history.combined.summary],
        ] as [string, AccountSummary][]).map(([name, summary]) => <div className="ms-portfolio-risk__comparison-row" role="row" key={name}>
          <span role="cell">{name}</span><strong role="cell">{signed(summary.cumulative_return)}</strong><strong role="cell">{pct(summary.max_drawdown)}</strong>
        </div>)}
      </div>
      <div className="ms-portfolio-risk__chart-head">
        <div><h3>{mode === "return" ? "账户累计收益" : "账户从高点的跌幅"}</h3><p>三条曲线均从10万起步；各半组合之后不在两方案之间调钱。</p></div>
        <div className="ms-portfolio-risk__switch" role="group" aria-label="策略曲线类型">
          <button type="button" aria-pressed={mode === "return"} onClick={() => setMode("return")}>累计收益</button>
          <button type="button" aria-pressed={mode === "drawdown"} onClick={() => setMode("drawdown")}>从高点下跌</button>
        </div>
      </div>
      {chart && chart.dates.length > 1 ? <TrendChart dates={chart.dates} series={chart.series} unit="%" height={285} />
        : <p className="ms-portfolio-risk__state">账户曲线日期不足，暂不能画图。</p>}
      <details className="ms-portfolio-risk__details">
        <summary>查看共同亏损月份、名单与计算口径</summary>
        <div className="ms-portfolio-risk__detail-grid">
          <div><h3>共同亏损最重的月份举例</h3>
            {worstMonths.length ? <ol>{worstMonths.map((row) => <li key={row.month}>{row.month}：两方案分别 {signed(row.mv_return)}、{signed(row.rv_return)}</li>)}</ol>
              : <p>同跌月份资料未取得。</p>}
            <p>仅按两套账户当月收益的平均值排序，列出历史例子；这不是未来亏损预测。</p>
          </div>
          <div><h3>名单与持仓各是什么</h3>
            <p>最后一个历史调仓月，目标名单重合 {pct(history.targets.count_overlap)}；原资料未提供该名单的准确日期、实际持仓权重。</p>
            <p>启动后的候选和持仓记录在“前向跟踪”页签查看；目标名单重合与持仓重合不能合并为一个数。</p>
          </div>
          <div><h3>怎样理解这些数</h3>
            <p>日收益只比较两方案都有有效收益的相同日期；首个未投入资金的零收益记录未算入。共同下跌日还占至少一套下跌的 {pct(history.both_down_share_either_down_days)}。</p>
            <p>曲线及累计收益、最大下跌沿用独立策略服务的已保存账户结果；只换算展示单位，没有重新选股或重算买卖点。</p>
            <p>历史是已看过的个股模拟，不能代表宽基ETF、真实成交或未来效果；没有行业和完整财报资料，暂不能判定两策略是否依赖同一种风格。</p>
          </div>
        </div>
      </details>
    </>}
  </section>;
}
