import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { request } from "../api/client";
import StrategyForward from "../components/strategy-forward/StrategyForward";
import StrategyPortfolios from "../components/strategy-portfolios/StrategyPortfolios";
import StrategyRiskWorkspace from "../components/market-style/StrategyRiskWorkspace";

type FwdBucketStat = { n: number; winRatePct?: number; meanPct?: number };
type FwdLedgerResponse = {
  sentiment: { available: boolean; reason: string; records?: number; reviewedRecords?: number; buckets?: Array<FwdBucketStat & { key: string; labelCn: string }> };
  recommendation: { available: boolean; reason: string; scoredDates?: number; latestDate?: string; bySymbol?: Array<{ symbol: string; nameCn: string | null; samples: number; t1: FwdBucketStat | null; t5: FwdBucketStat | null; t20: FwdBucketStat | null }> };
  disclaimerCn: string;
};
const pctText = (v: number | null | undefined) => v == null ? "—" : `${v > 0 ? "+" : ""}${v.toFixed(2)}%`;
function sentimentView(section: FwdLedgerResponse["sentiment"] | undefined) {
  if (!section) return { status: "loading" as const, reason: "账本数据加载中", data: null };
  if (!section.available) return { status: "degraded" as const, reason: section.reason, data: null };
  return { status: "ok" as const, reason: "", data: { records: section.records ?? 0, reviewed: section.reviewedRecords ?? 0, cards: (section.buckets ?? []).map((b) => ({ ...b, meanPct: b.n > 0 ? b.meanPct ?? null : null, winRatePct: b.n > 0 ? b.winRatePct ?? null : null })) } };
}
function recommendationView(section: FwdLedgerResponse["recommendation"] | undefined) {
  if (!section) return { status: "loading" as const, reason: "账本数据加载中", data: null };
  if (!section.available) return { status: "degraded" as const, reason: section.reason, data: null };
  return { status: "ok" as const, reason: "", data: { scoredDates: section.scoredDates ?? 0, latestDate: section.latestDate ?? "", rows: (section.bySymbol ?? []).map((s) => ({ symbol: s.symbol, name: s.nameCn ?? s.symbol, samples: s.samples, horizons: { t1: s.t1, t5: s.t5, t20: s.t20 } })) } };
}

/**
 * 前向验证成绩单：两套"说过的判断事后自动算成绩"的账本并排只读展示。
 * A 情绪线 = 板块冰点机会/强热警报信号的 10/20 日到期涨跌（四桶）；
 * B 推荐线 = 当日推荐标的的 1/5/20 日到期涨跌（按标的）。
 * 数据缺失时显示后端给出的降级原因，不编数；本页不写任何账本。
 * 展示模型在 fwdLedgerLogic.ts（供回归脚本断言）。
 */

function MeanCell({ stat }: { stat: FwdBucketStat | null }) {
  if (!stat) return <span className="fwd-na">—</span>;
  const cls = stat.meanPct == null ? "" : stat.meanPct > 0 ? "up" : "down";
  return (
    <span className={`fwd-pct ${cls}`}>
      {pctText(stat.meanPct)}
      <small className="fwd-sub"> n={stat.n} · 胜率{(stat.winRatePct ?? 0).toFixed(0)}%</small>
    </span>
  );
}

function OriginalSignalLedger() {
  const { data, error, isLoading } = useQuery({
    queryKey: ["fwdLedger"],
    queryFn: () => request<FwdLedgerResponse>("/fwd-ledger/scorecard"),
    staleTime: 5 * 60_000,
  });

  if (error) {
    return (
      <div className="page">
        <div className="header"><h1>前向成绩</h1></div>
        <div className="fund-errors">加载失败：{(error as Error).message}</div>
      </div>
    );
  }

  const sent = sentimentView(data?.sentiment);
  const rec = recommendationView(data?.recommendation);

  return (
    <div className="page fwd-page">
      <div className="header">
        <h1>前向成绩</h1>
        <span className="generated">
          {isLoading ? "加载中…" : "两套前向存证账本的到期对账成绩（只读）"}
        </span>
      </div>

      <div className="fwd-layout">
        {/* A 情绪线四桶 */}
        <section className="fwd-panel">
          <h2>情绪信号（冰点机会 / 强热警报）</h2>
          {sent.status === "ok" ? (
            <>
              <p className="fwd-note">
                存证 {sent.data.records} 天、已完成对账 {sent.data.reviewed} 天；
                每个信号在 10 / 20 个交易日后回头看涨跌，四桶成绩并排如下。
              </p>
              <div className="fwd-buckets">
                {sent.data.cards.map((c) => (
                  <div key={c.key} className={`metric fwd-bucket${c.n > 0 ? "" : " empty"}`}>
                    <div className="m-label">{c.labelCn}</div>
                    {c.n > 0 ? (
                      <>
                        <div className={`m-value ${(c.meanPct ?? 0) > 0 ? "up" : "down"}`}>
                          {pctText(c.meanPct)}
                        </div>
                        <div className="metric-delta">
                          样本 {c.n} · 胜率{(c.winRatePct ?? 0).toFixed(0)}%（涨了才算赢）
                        </div>
                      </>
                    ) : (
                      <div className="fwd-empty-note">暂无到期样本</div>
                    )}
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="fwd-degraded">
              暂无可看成绩：{sent.reason}
              {sent.status === "degraded" && (
                <small>
                  情绪信号触发后需等 10 / 20 个交易日到期才有成绩；到期对账每天收盘后自动跑。
                </small>
              )}
            </div>
          )}
        </section>

        {/* B 推荐线按标的 */}
        <section className="fwd-panel">
          <h2>今日推荐（标的到期涨跌）</h2>
          {rec.status === "ok" ? (
            <>
              <p className="fwd-note">
                已对账 {rec.data.scoredDates} 天（最新 {rec.data.latestDate}）；
                每个推荐标的在次日 / 5 日 / 20 日后回头看涨跌。
              </p>
              <table className="fwd-table">
                <thead>
                  <tr>
                    <th>标的</th>
                    <th>次日</th>
                    <th>5日</th>
                    <th>20日</th>
                  </tr>
                </thead>
                <tbody>
                  {rec.data.rows.map((s) => (
                    <tr key={s.symbol}>
                      <td>
                        {s.name}
                        <small className="fwd-sub"> {s.symbol} · {s.samples} 样本</small>
                      </td>
                      <td><MeanCell stat={s.horizons.t1} /></td>
                      <td><MeanCell stat={s.horizons.t5} /></td>
                      <td><MeanCell stat={s.horizons.t20} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : (
            <div className="fwd-degraded">
              暂无可看成绩：{rec.reason}
              {rec.status === "degraded" && (
                <small>推荐账本由每日跑批自动存证与对账，首个到期样本出现后此处点亮。</small>
              )}
            </div>
          )}
        </section>
      </div>

      {data && <p className="fwd-disclaimer">{data.disclaimerCn}</p>}
    </div>
  );
}

export default function FwdLedgerPage() {
  const [params, setParams] = useSearchParams();
  const rawTab = params.get("tab");
  const tab = rawTab === "portfolios" || rawTab === "strategy" || rawTab === "signal" ? rawTab : "comparison";
  const setTab = (next: typeof tab) => {
    const updated = new URLSearchParams(params);
    if (next === "comparison") updated.delete("tab"); else updated.set("tab", next);
    setParams(updated);
  };
  return <div className="fwd-tabs-page">
    <div className="page"><div className="header"><h1>策略跟踪与复盘</h1><span className="generated">前向新记录与过去行情的历史对照分开查看</span></div>
      <div className="sf-page-tabs" role="tablist" aria-label="前向记录类型">
        <button type="button" role="tab" aria-selected={tab === "comparison"} onClick={() => setTab("comparison")}>共同风险复盘</button>
        <button type="button" role="tab" aria-selected={tab === "portfolios"} onClick={() => setTab("portfolios")}>个股双策略账户</button>
        <button type="button" role="tab" aria-selected={tab === "strategy"} onClick={() => setTab("strategy")}>完整策略前向</button>
        <button type="button" role="tab" aria-selected={tab === "signal"} onClick={() => setTab("signal")}>信号前向记录</button>
      </div>
      <div role="tabpanel">{tab === "comparison" ? <StrategyRiskWorkspace /> : tab === "portfolios" ? <StrategyPortfolios /> : tab === "strategy" ? <StrategyForward /> : <OriginalSignalLedger />}</div>
    </div>
  </div>;
}
