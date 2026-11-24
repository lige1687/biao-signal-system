import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { request } from "../../api/client";
import type { MarketReview } from "./FiveQuestionReview";
import PortfolioRiskReview from "./PortfolioRiskReview";
import "./strategy-risk-workspace.css";

/** A read-only view of the existing strategy records; never starts a run or writes a ledger. */
export default function StrategyRiskWorkspace() {
  const [params, setParams] = useSearchParams();
  const market = params.get("market") === "us" ? "us" : "cn";
  const phase = params.get("phase") === "history" ? "history" : "forward";
  const setView = (key: string, value: string) => setParams(previous => {
    const next = new URLSearchParams(previous); next.set(key, value); return next;
  }, { replace: true });
  const query = useQuery({ queryKey: ["marketStyleFiveQuestions", market],
    queryFn: () => request<MarketReview>(`/market-style/review?market=${market}`),
    staleTime: 60_000, retry: false });
  return <div className="strategy-risk-workspace">
    <div className="srw-toolbar">
      <div role="group" aria-label="策略复盘市场">
        <button type="button" aria-pressed={market === "cn"} onClick={() => setView("market", "cn")}>A股</button>
        <button type="button" aria-pressed={market === "us"} onClick={() => setView("market", "us")}>美股</button>
      </div>
      <div role="group" aria-label="策略复盘资料阶段">
        <button type="button" aria-pressed={phase === "forward"} onClick={() => setView("phase", "forward")}>前向跟踪</button>
        <button type="button" aria-pressed={phase === "history"} onClick={() => setView("phase", "history")}>历史对照</button>
      </div>
      <a href="/fundamentals#fund-sec-market">返回市场环境 →</a>
    </div>
    <PortfolioRiskReview portfolio={query.data?.portfolio} loading={query.isPending} error={query.isError} phase={phase} />
    <p className="srw-note">完整账户、持仓、等待和退出记录在上方“个股双策略账户”查看。这里比较两套策略的共同风险，不启动新实验或交易。</p>
  </div>;
}
