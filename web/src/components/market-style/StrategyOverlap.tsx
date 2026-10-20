import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { request } from "../../api/client";
import "./strategy-overlap.css";

type Account = {
  scheme: string;
  name: string;
  history?: { series?: { date: string }[] };
};

type Market = {
  id: "CN" | "US";
  accounts: Account[];
  comparison?: {
    return_correlation: number | null;
    holding_overlap: number | null;
  };
};

type Dashboard = {
  started_at: string | null;
  markets: Market[];
};

const validNumber = (value: number | null | undefined) =>
  typeof value === "number" && Number.isFinite(value);

function historyRange(accounts: Account[]) {
  const ranges = accounts.map((account) => account.history?.series ?? []).filter((series) => series.length);
  if (ranges.length !== 2) return null;
  const starts = ranges.map((series) => series[0].date);
  const ends = ranges.map((series) => series[series.length - 1].date);
  return `${starts[0] === starts[1] ? starts[0] : starts.join(" / ")} 至 ${ends[0] === ends[1] ? ends[0] : ends.join(" / ")}`;
}

export default function StrategyOverlap({ market }: { market: "cn" | "us" }) {
  const { data, error, isPending } = useQuery({
    queryKey: ["strategyPortfolios"],
    queryFn: () => request<Dashboard>("/strategy-portfolios"),
    staleTime: 60_000,
    retry: false,
  });
  const selected = data?.markets.find((item) => item.id === market.toUpperCase());
  const accounts = selected?.accounts.filter((account) => account.scheme === "mv" || account.scheme === "rv") ?? [];
  const first = accounts.find((account) => account.scheme === "mv");
  const second = accounts.find((account) => account.scheme === "rv");
  const correlation = selected?.comparison?.return_correlation;
  const overlap = selected?.comparison?.holding_overlap;
  const range = first && second ? historyRange([first, second]) : null;
  const marketName = market === "cn" ? "A股" : "美股";

  return <section className="ms-overlap" aria-label={`${marketName}策略是否重复押注`}>
    <div className="ms-overlap-line">
      <div className="ms-overlap-heading"><h3>策略是否重复押注</h3><span>{marketName} · 历史回放</span></div>
      {isPending && <p role="status" className="ms-overlap-state">正在读取策略比较…</p>}
      {error && <p role="alert" className="ms-overlap-state">策略比较读取失败。</p>}
      {data && !selected && <p className="ms-overlap-state">该市场尚无策略比较资料。</p>}
      {selected && (!first || !second) && <p className="ms-overlap-state">两套主方案资料尚未齐全。</p>}
      {first && second && <>
        <p className="ms-overlap-names">{first.name} <span>＋</span> {second.name}</p>
        <div className="ms-overlap-figures">
          <span>日收益相关 <strong>{validNumber(correlation) ? correlation!.toFixed(2) : "未提供"}</strong></span>
          <span>目标名单重合 <strong>{validNumber(overlap) ? `${(overlap! * 100).toFixed(1)}%` : "未提供"}</strong></span>
        </div>
      </>}
    </div>
    {first && second && <details className="ms-overlap-detail">
      <summary>查看口径与不足</summary>
      <div>
        <p>这是过去行情上的虚拟策略回放；历史日收益相关程度越接近 1，两套策略越容易同涨同跌。相关程度不能证明两套方案属于同一种风格。</p>
        <p>目标名单重合是最后一次月度调仓时，两套名单共同股票数占两套名单合计去重股票数的比例；只代表当次名单，不代表持仓资金权重。0% 也表示有数据且名单没有共同股票。</p>
        <p>历史回放系列：{range ?? "日期未提供"}。接口没有给出相关计算所用共同有效天数；这段系列范围不能当作精确统计区间。</p>
        <p>2026-10-20 起的新记录与历史回放分开；{data?.started_at ? `记录开始于 ${data.started_at.slice(0, 10)}` : "开始时间尚未提供"}，此处不沿用历史相关值推断新记录表现。共同下跌、行业及风格暴露需要各自证据。</p>
        <Link to="/fwd">查看前向成绩与完整资料</Link>
      </div>
    </details>}
  </section>;
}
