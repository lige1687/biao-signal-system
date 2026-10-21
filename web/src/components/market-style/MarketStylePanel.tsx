import { useCallback, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fundamentalsApi, request } from "../../api/client";
import type { MarketObservation, MarketObservationsResponse, RatesHistoryResponse, RatesHistorySeries } from "../../types";
import TrendChart from "./MarketTrendChart";
import StyleComparison from "./StyleComparison";
import PortfolioRiskReview from "./PortfolioRiskReview";
import ObservationConditions from "./ObservationConditions";
import FiveQuestionReview, { type MarketReview } from "./FiveQuestionReview";
import BreadthComparison from "./BreadthComparison";
import MarketReading from "./MarketReading";
import "./market-style-panel.css";

type Market = "cn" | "us";
type BreadthContext = { windowDays: number; ruleIds: string[]; priceKey: string; fingerprint: string };
const valid = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);

function RiskHistory({ item, name, series, failed, days, description }: {
  item?: MarketObservation; name: string; series?: RatesHistorySeries; failed: boolean; days: number; description: string;
}) {
  const until = item?.observation_date ?? series?.dates[series.dates.length - 1];
  const cutoff = until ? new Date(Date.parse(until) - days * 86400000).toISOString().slice(0, 10) : "";
  const points = series?.dates.map((date, index) => ({ date, value: series.values[index] ?? null }))
    .filter((point) => point.date >= cutoff && (!until || point.date <= until)) ?? [];
  const historyAvailable = points.filter((point) => valid(point.value)).length > 1;
  const lastPoint = [...points].reverse().find((point) => valid(point.value));
  const differentReading = lastPoint && valid(item?.value) && valid(lastPoint.value)
    && (lastPoint.date !== item.observation_date || Math.abs(lastPoint.value - item.value) >= 0.005);
  return <section className="ms-risk-history" aria-label={name}>
    <div className="ms-risk-title"><div><h3>{name}</h3><p>{description}</p></div>
      <span>{valid(item?.value) ? <><b>{item.value.toFixed(2)}</b> {item.unit}</> : "最新值待补"}<small>最新读数 · {item?.observation_date ?? "日期未核"}</small></span>
    </div>
    {failed ? <p className="ms-error" role="alert">历史资料读取失败，暂不能比较变化。</p>
      : historyAvailable ? <TrendChart dates={points.map((p) => p.date)}
        series={[{ name, values: points.map((p) => p.value), color: "#718399" }]}
        unit={item?.unit ?? series?.unit ?? ""} height={240} />
        : <p className="ms-empty">历史资料加载中或不足，暂不画趋势。</p>}
    <div className="ms-chart-caption"><span>{points[0]?.date} — {points[points.length - 1]?.date}</span>
      <span>{item?.quality_status === "current" ? "来源已核" : "可用时点待核"}</span></div>
    {differentReading && <p className="ms-history-difference">历史末值 {lastPoint.value?.toFixed(2)} {item?.unit}（{lastPoint.date}），与最新读数不同；两路资料更新批次尚未对齐。</p>}
  </section>;
}

function RiskConditions({ ratesHistory, ratesHistoryFailed, onDataChange }: {
  ratesHistory?: RatesHistoryResponse; ratesHistoryFailed?: boolean; onDataChange: (basis: string) => void;
}) {
  const [days, setDays] = useState(365);
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
        {[{ days: 90, label: "3个月" }, { days: 365, label: "1年" }, { days: 1095, label: "3年" }].map((range) =>
          <button key={range.days} type="button" aria-pressed={days === range.days} onClick={() => setDays(range.days)}>{range.label}</button>)}
      </div>
    </header>
    <div className="ms-risk-grid">
      <RiskHistory name="VIX · 预期波动" description="来自标普500期权，观察未来约30天的波动预期"
        item={items.find((item) => item.metric_id === "vix")} series={ratesHistory?.series.vix} days={days}
        failed={!!ratesHistoryFailed || observations.isError || !!ratesHistory?.errors.some((error) => /VIX/i.test(error))} />
      <RiskHistory name="高收益债信用利差" description="ICE BofA · 企业融资相对国债多付的风险补偿"
        item={items.find((item) => item.metric_id === "hy_oas")} series={credit.data?.series.hy_oas} days={days}
        failed={credit.isError || observations.isError || !!credit.data?.errors.some((error) => /hy_oas|高收益债/i.test(error))} />
    </div>
    <details className="ms-source-notes">
      <summary>怎样读 · 来源 · 尚缺资料</summary>
      <p>VIX上升表示期权市场预期起伏更大；信用利差扩大表示企业融资需要更多风险补偿。看各自变化与日期，两图纵轴单位不同，不能直接比较线的高度，也不据此预言涨跌。</p>
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
    <header className="ms-reading-heading">
      <div><strong>市场环境观察</strong><span>风格表现 → 市场参与 → 风险与策略重叠</span></div>
      <div className="ms-switch" role="group" aria-label="宽度与策略观察市场">
        <button type="button" aria-pressed={props.market === "cn"} onClick={() => props.onMarketChange("cn")}>A股</button>
        <button type="button" aria-pressed={props.market === "us"} onClick={() => props.onMarketChange("us")}>美股</button>
      </div>
    </header>
    <MarketReading market={props.market} context={context} viewRevision={viewRevision} riskBasis={riskBasis + reviewBasis} />
    <FiveQuestionReview data={review.data} loading={review.isPending} error={review.isError} />
    <div className="ms-chart-grid">
      <StyleComparison />
      <BreadthComparison market={props.market} onContextChange={onContextChange} />
    </div>
    <RiskConditions ratesHistory={props.ratesHistory} ratesHistoryFailed={props.ratesHistoryFailed} onDataChange={setRiskBasis} />
    <ObservationConditions volatility={review.data?.volatility} nfci={review.data?.nfci}
      loading={review.isPending} error={review.isError} />
    <PortfolioRiskReview portfolio={review.data?.portfolio} loading={review.isPending} error={review.isError} />
    <details className="ms-review-guide">
      <summary><span>每周观察 · 每月复盘五问</span><small>自身表现 / 相对表现 / 集中程度 / 估值位置 / 策略重叠</small></summary>
      <div className="ms-review-columns">
        <div><h3>每周看变化</h3><p>先核资料日，再看相对曲线是否转强、参与上涨的股票是否变多、波动与信用条件是否变化。风格仍是旧月末数据时，不把旧排名当作本周切换。</p></div>
        <div><h3>每月看完整</h3><ol><li>自身收益、回撤和波动如何？</li><li>同期有没有跑赢母指数？</li><li>来自哪些行业和少数重仓股？</li><li>表现与估值处于什么位置？</li><li>多个策略是否同时赚钱、同时亏损？</li></ol></div>
        <div><h3>目前能回答到哪里</h3><p>五问答案与未答部分已逐项列在上方。共同亏损和同资金组合效果已补；收益贡献、当前回撤、历史估值位置及完整风格暴露仍有资料缺口。下一阶段再单独检验能否改善选股与风险控制。</p><a href="/library?report=docs%2Fexperiments%2Fmarket-style-observation-2026-10-20.md">完整研究依据 →</a></div>
      </div>
    </details>
  </div>;
}
