import { useCallback, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fundamentalsApi, request } from "../../api/client";
import type { MarketObservation, MarketObservationsResponse, RatesHistoryResponse, RatesHistorySeries } from "../../types";
import TrendChart from "./MarketTrendChart";
import StyleComparison from "./StyleComparison";
import ObservationConditions from "./ObservationConditions";
import FiveQuestionReview, { type MarketReview } from "./FiveQuestionReview";
import ObservationProjection from "../observation-library/projectionView";
import MarketReading from "./MarketReading";
import "./market-style-panel.css";

type Market = "cn" | "us";
type BreadthContext = { windowDays: number; ruleIds: string[]; priceKey: string; fingerprint: string };
const valid = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);

function RiskHistory({ item, name, series, failed, days, description, limitedHistory }: {
  item?: MarketObservation; name: string; series?: RatesHistorySeries; failed: boolean;
  days: number | null; description: string; limitedHistory?: boolean;
}) {
  const allPoints = series?.dates.map((date, index) => ({ date, value: series.values[index] ?? null })) ?? [];
  const availablePoints = allPoints.filter((point) => valid(point.value));
  const latestHistory = availablePoints[availablePoints.length - 1];
  const until = latestHistory?.date;
  const cutoff = until && days !== null
    ? new Date(Date.parse(until) - days * 86400000).toISOString().slice(0, 10) : "";
  const points = allPoints.filter((point) => point.date >= cutoff && (!until || point.date <= until));
  const visiblePoints = points.filter((point) => valid(point.value));
  const latestFromObservation = valid(item?.value) && !!item?.observation_date;
  const latestValue = latestFromObservation ? item.value : latestHistory?.value;
  const latestDate = latestFromObservation ? item.observation_date : latestHistory?.date;
  const unit = item?.unit ?? series?.unit ?? "";
  const differentReading = latestHistory && item && valid(item.value) && latestFromObservation
    && (latestHistory.date !== item.observation_date || Math.abs(latestHistory.value - item.value) >= 0.005);
  return <section className="ms-risk-history" aria-label={name}>
    <div className="ms-risk-title"><div><h3>{name}</h3><p>{description}</p></div>
      <span>{valid(latestValue) ? <><b>{latestValue.toFixed(2)}</b> {unit}</> : "最新值待补"}
        <small>{latestFromObservation ? "最新读数" : "历史末值"} · {latestDate ?? "日期未核"}</small></span>
    </div>
    {failed ? <p className="ms-error" role="alert">历史资料读取失败，暂不能比较变化。</p>
      : visiblePoints.length > 1 ? <TrendChart dates={points.map((p) => p.date)}
        series={[{ name, values: points.map((p) => p.value), color: "#718399" }]}
        unit={unit} height={240} />
        : <p className="ms-empty">历史资料加载中或不足，暂不画趋势。</p>}
    <div className="ms-chart-caption"><span>显示：{visiblePoints[0]?.date ?? "—"} — {visiblePoints[visiblePoints.length - 1]?.date ?? "—"}</span>
      <span>可用：{availablePoints[0]?.date ?? "—"} — {latestHistory?.date ?? "—"}</span></div>
    {limitedHistory && <p className="ms-history-difference">所选窗口长于信用利差实际可用范围时，只显示可取得的日期。<a href="https://fred.stlouisfed.org/series/BAMLH0A0HYM2" target="_blank" rel="noreferrer">FRED公开序列</a> 自2026年4月起仅保留近三年；更早数据须另向原始供应商取得。</p>}
    {differentReading && <p className="ms-history-difference">历史末值 {latestHistory.value.toFixed(2)} {unit}（{latestHistory.date}），与最新读数不同；两路资料更新批次尚未对齐。</p>}
  </section>;
}

function RiskConditions({ ratesHistory, ratesHistoryFailed, onDataChange }: {
  ratesHistory?: RatesHistoryResponse; ratesHistoryFailed?: boolean; onDataChange: (basis: string) => void;
}) {
  const [days, setDays] = useState<number | null>(1825);
  const observations = useQuery({
    queryKey: ["marketStyleUsObservations"], queryFn: () => fundamentalsApi.observations("us"),
    staleTime: 5 * 60_000, retry: false,
  });
  const credit = useQuery({
    queryKey: ["fundamentalsUsMacro"], queryFn: () => fundamentalsApi.usMacro(),
    staleTime: 30 * 60_000, retry: false,
  });
  const items = observations.data?.items ?? [];
  useEffect(() => {
    onDataChange(JSON.stringify({
      observations: observations.data, vix: ratesHistory?.series.vix,
      credit: credit.data?.series.hy_oas, failed: [ratesHistoryFailed, observations.isError, credit.isError],
    }));
  }, [observations.data, ratesHistory, credit.data, ratesHistoryFailed, observations.isError, credit.isError, onDataChange]);
  return <section className="ms-risk" aria-labelledby="ms-risk-heading">
    <header className="ms-section-head">
      <div><h2 id="ms-risk-heading">美国风险条件</h2><p>预期波动与融资压力分别看；作为跨市场背景，不代替A股自身证据。</p></div>
      <div className="ms-switch" role="group" aria-label="风险曲线时间范围">
        {[{ days: 90, label: "3个月" }, { days: 365, label: "1年" }, { days: 1095, label: "3年" },
          { days: 1825, label: "5年" }, { days: 3650, label: "10年" }, { days: null, label: "全部" }].map((range) =>
          <button key={range.label} type="button" aria-pressed={days === range.days} onClick={() => setDays(range.days)}>{range.label}</button>)}
      </div>
    </header>
    <div className="ms-risk-grid">
      <RiskHistory name="VIX · 预期波动" description="来自标普500期权，观察未来约30天的波动预期"
        item={items.find((item) => item.metric_id === "vix")} series={ratesHistory?.series.vix} days={days}
        failed={!!ratesHistoryFailed || !!ratesHistory?.errors.some((error) => /VIX/i.test(error))} />
      <RiskHistory name="高收益债信用利差" description="ICE BofA · 企业融资相对国债多付的风险补偿"
        item={items.find((item) => item.metric_id === "hy_oas")} series={credit.data?.series.hy_oas} days={days} limitedHistory
        failed={credit.isError || !!credit.data?.errors.some((error) => /hy_oas|高收益债/i.test(error))} />
    </div>
    <details className="ms-source-notes">
      <summary>怎样读 · 来源 · 尚缺资料</summary>
      <p>VIX上升表示期权市场预期起伏更大；信用利差扩大表示企业融资需要更多风险补偿。看各自变化与日期，两图纵轴单位不同，不能直接比较线的高度。本页没有验证过两者对应股指阶段顶底的固定风险或机会阈值，也不据此预言涨跌。</p>
      {items.filter((item) => ["vix", "hy_oas"].includes(item.metric_id)).map((item) =>
        <p key={item.metric_id}><a href={item.source_url ?? undefined} target="_blank" rel="noreferrer">{item.source_name} · {item.label}</a>：{item.quality_reason}</p>)}
      <p>本地市场已实现波动与NFCI在下方单列；NFCI目前只有最近5周已核快照，完整历史与自动更新未接通。</p>
    </details>
  </section>;
}

export default function MarketStylePanel(props: {
  market: Market; onMarketChange: (market: Market) => void;
  observations?: MarketObservationsResponse; ratesHistory?: RatesHistoryResponse; ratesHistoryFailed?: boolean;
}) {
  const [context, setContext] = useState<BreadthContext>({ windowDays: 365, ruleIds: [], priceKey: "", fingerprint: "" });
  const [viewRevision, setViewRevision] = useState(0);
  const [riskBasis, setRiskBasis] = useState("");
  const [styleBasis, setStyleBasis] = useState("");
  const [backgroundOpen, setBackgroundOpen] = useState(false);
  const review = useQuery({
    queryKey: ["marketStyleFiveQuestions", props.market],
    queryFn: () => request<MarketReview>(`/market-style/review?market=${props.market}`),
    staleTime: 60_000, retry: false,
  });
  const reviewBasis = JSON.stringify(review.data ? { ...review.data, asof: undefined } : null);
  const onContextChange = useCallback((next: BreadthContext) => setContext((previous) =>
    JSON.stringify(previous) === JSON.stringify(next) ? previous : next), []);
  return <div className="market-style-panel" onClickCapture={(event) => {
    const target = event.target as HTMLElement;
    if (target.closest("button") && !target.closest(".market-reading")) setViewRevision((value) => value + 1);
  }}>
    <details className="ms-review-guide" onToggle={(event) => setBackgroundOpen(event.currentTarget.open)}>
      <summary>深入历史对照与复盘<small>长期走势叠加、全球风格、金融条件与五问复盘</small></summary>
      {backgroundOpen && <>
        <ObservationProjection market={props.market} onMarketChange={props.onMarketChange} onContextChange={onContextChange} />
        <RiskConditions ratesHistory={props.ratesHistory} ratesHistoryFailed={props.ratesHistoryFailed} onDataChange={setRiskBasis} />
        <StyleComparison onBasisChange={setStyleBasis} />
        <ObservationConditions volatility={review.data?.volatility} nfci={review.data?.nfci}
          loading={review.isPending} error={review.isError} />
        <FiveQuestionReview data={review.data} loading={review.isPending} error={review.isError} />
        <MarketReading market={props.market} context={context} viewRevision={viewRevision} riskBasis={riskBasis + reviewBasis + styleBasis} />
      </>}
    </details>
  </div>;
}
