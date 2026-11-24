import { useQuery } from "@tanstack/react-query";
import { fundamentalsApi } from "../api/client";
import { useState } from "react";
import MarketObservationCards from "../components/MarketObservationCards";
import EtfSentimentComparison from "../components/etf-sentiment/EtfSentimentComparison";
import EtfPriceHeatObservation from "../components/market-observation-alerts/EtfPriceHeatObservation";
import "./reference-reading.css";
import "./sentiment.css";

/**
 * 市场参与与情绪页（可独立通过 /sentiment 访问，也作为「宏观与情绪」的「情绪与热度」页签嵌入）。
 * 仅展示有核对时点的核心情绪指标（ETF 价格情绪/热度、两融、恐慌与调查），已清理旧版未核废卡。
 */
export default function SentimentPage({ embedded = false }: { embedded?: boolean } = {}) {
  const [market, setMarket] = useState<"cn" | "us">("cn");
  const { data: observations, isLoading: observationsLoading, error: observationsError, refetch } = useQuery({
    queryKey: ["fundamentalsObservations", market],
    queryFn: () => fundamentalsApi.observations(market),
    staleTime: 5 * 60_000,
  });

  const latestObsDate = observations?.items
    ?.map((it) => it.observation_date)
    .filter((dt): dt is string => Boolean(dt))
    .sort()
    .slice(-1)[0];

  const body = (
    <>
      <div className="observation-market-switch" role="group" aria-label="观察市场">
        <button type="button" className={market === "cn" ? "on" : ""} onClick={() => setMarket("cn")} aria-pressed={market === "cn"}>A股</button>
        <button type="button" className={market === "us" ? "on" : ""} onClick={() => setMarket("us")} aria-pressed={market === "us"}>美股</button>
        {latestObsDate && (
          <span className="muted" style={{ marginLeft: "auto", fontSize: 12 }}>
            {market === "cn" ? "A股" : "美股"}最新资料日：{latestObsDate}
          </span>
        )}
      </div>
      {market === "cn" && (
        <div id="etf-price-sentiment" style={{ marginBottom: 20, scrollMarginTop: 24 }}>
          <EtfSentimentComparison />
        </div>
      )}
      {market === "cn" && (
        <section id="etf-price-heat" style={{ marginBottom: 20, scrollMarginTop: 24 }}>
          <EtfPriceHeatObservation page />
        </section>
      )}
      {observationsLoading && <p className="muted">情绪资料加载中…</p>}
      {observationsError && (
        <p className="fund-errors">
          情绪资料暂不可用：{(observationsError as Error).message}
          <button type="button" className="btn small" style={{ marginLeft: 8 }} onClick={() => void refetch()}>
            重试
          </button>
        </p>
      )}
      {(observations || (!observationsLoading && !observationsError)) && (
        <MarketObservationCards
          response={observations}
          title={`${market === "cn" ? "A股" : "美股"}核心参与情绪`}
          limit={4}
          metricIds={market === "cn" ? ["margin_balance", "margin_buy", "stock_turnover"] : ["vix", "vxn", "aaii", "naaim"]}
        />
      )}
    </>
  );

  if (embedded) return <div className="sent-page">{body}</div>;

  return (
    <div className="page sent-page">
      <div className="pg-head">
        <div className="pg-head-title">
          <h1>市场参与与情绪</h1>
          <span className="pg-head-sub">观察场内基金热度、杠杆资金、波动率与机构调查</span>
        </div>
      </div>
      {body}
    </div>
  );
}
