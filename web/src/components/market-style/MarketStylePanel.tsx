import { useQuery } from "@tanstack/react-query";
import { api, fundamentalsApi } from "../../api/client";
import type { MarketObservation, MarketObservationsResponse, RatesHistoryResponse, RatesHistorySeries } from "../../types";
import StyleComparison from "./StyleComparison";
import StrategyOverlap from "./StrategyOverlap";
import "./market-style-panel.css";

type Market = "cn" | "us";
type Point = { date: string; value: number | null };

const valid = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
const decimal = (value: number, digits = 2) => value.toFixed(digits);

/** Render the existing observations; this component does not calculate trading states. */
function MiniHistory({ points, label, failed = false }: { points: Point[]; label: string; failed?: boolean }) {
  if (failed) return <span className="ms-error">历史资料读取失败</span>;
  const end = points[points.length - 1]?.date;
  if (!end) return <span className="ms-history-empty">暂无历史资料</span>;
  const cutoff = Date.parse(end) - 90 * 86400000;
  const recent = points.filter((point) => Date.parse(point.date) >= cutoff);
  const values = recent.map((point) => point.value).filter(valid);
  if (values.length < 2) return <span className="ms-history-empty">历史不足</span>;
  const low = Math.min(...values);
  const high = Math.max(...values);
  const first = Date.parse(recent[0].date);
  const duration = Math.max(1, Date.parse(end) - first);
  let newSegment = true;
  const path = recent.map((point) => {
    if (!valid(point.value)) { newSegment = true; return ""; }
    const x = 3 + (Date.parse(point.date) - first) / duration * 154;
    const y = high === low ? 23 : 39 - (point.value - low) / (high - low) * 32;
    const part = `${newSegment ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
    newSegment = false;
    return part;
  }).join(" ");
  return <svg className="ms-history" viewBox="0 0 160 46" role="img"
    aria-label={`${label}，${recent[0].date}至${end}的已有历史，范围${decimal(low)}至${decimal(high)}`}>
    <title>{`${label} · ${recent[0].date}—${end} · ${decimal(low)}—${decimal(high)}`}</title>
    <path d="M3,42 L157,42" className="ms-history-base" />
    <path d={path} className="ms-history-line" />
  </svg>;
}

function toPoints(series: RatesHistorySeries | undefined, until?: string | null): Point[] {
  if (!series) return [];
  return series.dates.map((date, index) => ({ date, value: series.values[index] ?? null }))
    .filter((point) => !until || point.date <= until);
}

function RiskObservation({ item, name, history, description, historyFailed }: {
  item?: MarketObservation; name: string; history?: RatesHistorySeries; description: string; historyFailed?: boolean;
}) {
  const usable = item && valid(item.value) && item.observation_date && item.quality_status !== "missing";
  return <div className="ms-risk-row">
    <div className="ms-risk-label"><strong>{name}</strong><span>{description}</span></div>
    <div className="ms-risk-reading">
      <div><b>{usable ? decimal(item.value!) : "—"}</b><span>{usable ? item.unit : "暂无读数"}</span></div>
      <small>{usable ? item.observation_date : "资料待补"}</small>
    </div>
    <div className="ms-risk-chart">
      {usable ? <MiniHistory points={toPoints(history, item.observation_date)} label={name} failed={historyFailed} /> : null}
    </div>
    {usable && <div className="ms-risk-foot">
      <span>{item.change == null ? "变化未核" : `${item.comparison_period ?? "较前期"} ${item.change > 0 ? "+" : ""}${decimal(item.change)}${item.change_unit ?? item.unit}`}</span>
      <span>{item.quality_status === "current" ? "已核对" : item.quality_status === "stale" ? "旧数据" : "可用时点待核"}</span>
    </div>}
  </div>;
}

function RiskConditions({ market, onMarketChange, observations, ratesHistory, ratesHistoryFailed }: {
  market: Market; onMarketChange: (market: Market) => void;
  observations?: MarketObservationsResponse; ratesHistory?: RatesHistoryResponse; ratesHistoryFailed?: boolean;
}) {
  const breadth = useQuery({
    queryKey: ["stylePanelBreadth", market],
    queryFn: () => api.marketContextBreadthHistory(market === "cn" ? "CN_ALL_A" : "SP500", 1260),
    staleTime: 5 * 60_000,
    enabled: market === "cn",
  });
  const credit = useQuery({
    queryKey: ["fundamentalsUsMacro"],
    queryFn: () => fundamentalsApi.usMacro(),
    staleTime: 30 * 60_000,
    enabled: market === "us",
  });
  const history = breadth.data?.history ?? [];
  const last = history[history.length - 1];
  const getItem = (id: string) => observations?.market === market
    ? observations.items.find((item) => item.metric_id === id) : undefined;

  return <section className="ms-risk" aria-labelledby="ms-risk-heading">
    <header className="ms-section-head">
      <div><h2 id="ms-risk-heading">风险条件</h2><p>观察波动与参与程度</p></div>
      <div className="ms-switch" role="group" aria-label="风险与策略观察市场">
        <button type="button" aria-pressed={market === "cn"} onClick={() => onMarketChange("cn")}>A股</button>
        <button type="button" aria-pressed={market === "us"} onClick={() => onMarketChange("us")}>美股</button>
      </div>
    </header>
    {market === "cn" ? <>
      <div className="ms-risk-row">
        <div className="ms-risk-label"><strong>市场宽度</strong><span>站上50日均线的股票比例</span></div>
        <div className="ms-risk-reading"><div><b>{valid(last?.breadth_50) ? decimal(last.breadth_50, 1) : "—"}</b><span>%</span></div><small>{last?.date ?? (breadth.isLoading ? "加载中" : "资料待补")}</small></div>
        <div className="ms-risk-chart"><MiniHistory label="A股市场宽度50日" points={history.map((point) => ({ date: point.date, value: point.breadth_50 }))} failed={breadth.isError} /></div>
        <div className="ms-risk-foot"><span>20日 {valid(last?.breadth_20) ? decimal(last.breadth_20, 1) : "—"}% · 200日 {valid(last?.breadth_200) ? decimal(last.breadth_200, 1) : "—"}%</span><span>已有历史 · 非实时</span></div>
      </div>
      <div className="ms-missing-row"><strong>本地市场波动率</strong><span>待接入</span><p>需要市场指数的实际涨跌序列，当前没有合格读数。</p></div>
      {breadth.isError && <p className="ms-error">市场宽度读取失败，暂不能比较参与程度。</p>}
    </> : <>
      <RiskObservation name="VIX 预期波动" item={getItem("vix")} history={ratesHistory?.series.vix}
        historyFailed={ratesHistoryFailed || ratesHistory?.errors.some((error) => /VIX/i.test(error))}
        description="标普500期权反映的未来波动" />
      <RiskObservation name="高收益债信用利差" item={getItem("hy_oas")} history={credit.data?.series.hy_oas}
        historyFailed={credit.isError || credit.data?.errors.some((error) => /hy_oas|高收益债/i.test(error))}
        description="ICE BofA · 企业借款的风险补偿" />
      <div className="ms-missing-inline"><span>NFCI 金融条件 · 周频</span><span>尚未接入</span></div>
    </>}
    <details className="ms-source-notes">
      <summary>来源与读法</summary>
      {market === "cn" ? <p>宽度表示有多少股票参与上涨。这里复用系统的全A历史序列；当前返回未附逐日有效股票覆盖率，历史末日不等于实时可用时点。不同期限的均线用于观察不同速度的变化，不能直接判定买卖。</p>
        : <><p>VIX 看预期波动，信用利差看融资风险补偿，两者都不直接预告股票涨跌。小图各自显示截至资料日最近约3个月的已有历史，纵轴尺度不同。</p>
          {["vix", "hy_oas"].map((id) => { const item = getItem(id); return item ? <p key={id}>{item.label}：<a href={item.source_url ?? undefined} target="_blank" rel="noreferrer">{item.source_name}</a>。{item.quality_reason}</p> : null; })}
          <p><a href="https://www.chicagofed.org/research/data/nfci/current-data" target="_blank" rel="noreferrer">芝加哥联储 NFCI</a>适合周频观察，完整历史可能修订。本预览不以缺项推断金融条件。</p></>}
    </details>
  </section>;
}

export default function MarketStylePanel(props: {
  market: Market; onMarketChange: (market: Market) => void;
  observations?: MarketObservationsResponse; ratesHistory?: RatesHistoryResponse; ratesHistoryFailed?: boolean;
}) {
  return <div className="market-style-panel">
    <div className="ms-reading-heading"><span>先看风格，再看风险和策略是否重叠</span><small>每周观察 · 每月完整复盘</small></div>
    <div className="ms-main-grid">
      <StyleComparison />
      <RiskConditions {...props} />
    </div>
    <StrategyOverlap market={props.market} />
    <details className="ms-review-guide">
      <summary><span>周观察与月复盘</span><small>按五个问题阅读，避免只看涨幅榜</small></summary>
      <div className="ms-review-columns">
        <div><h3>每周：看变化</h3><p>先看资料是否更新，再看风格相对市场是否转强、波动与信用条件是否变化、策略是否同时亏损。资料仍停在月末时，保留原结论和日期。</p></div>
        <div><h3>每月：把五问看完整</h3><ol><li>自身收益、回撤和波动如何？</li><li>同期间有没有跑赢母指数？</li><li>行业与少数重仓股影响有多大？</li><li>表现、估值处于什么位置？</li><li>多个策略是否依赖相同持仓和风格？</li></ol></div>
        <div><h3>解读要有依据</h3><p>摘要需带资料日期、比较对象和来源，把已知、推测与缺项分开。这版先展示可核事实；收益贡献、历史估值位置和完整风格暴露仍需补齐。</p><a href="/library?report=docs%2Fexperiments%2Fmarket-style-observation-2026-10-20.md">查看研究依据 →</a></div>
      </div>
    </details>
  </div>;
}
