import IndicatorThumbnail from "./IndicatorThumbnail";
import StarBreadthSnapshot from "../market-style/StarBreadthSnapshot";
import SocialFinancingSnapshot from "../market-style/SocialFinancingSnapshot";
import EarningsCoverageSnapshot from "../market-style/EarningsCoverageSnapshot";
import { INDUSTRY_TURNOVER_ID } from "./industryTurnoverOptions";
import "./compact-overview.css";

const MARKETS = [
  { label: "A股", cards: [
    { id: "erp-cn", title: "沪深300 · 股债利差", note: "估值背景 · 周频历史" },
    { id: "breadth-cn", title: "全A · 市场宽度", note: "50日均线 · 有效成分数未提供" },
  ] },
  { label: "美股", cards: [
    { id: "erp-us", title: "标普500 · 股债利差", note: "估值背景 · 盈利端为月频" },
    { id: "breadth-us", title: "标普500 · 市场宽度", note: "50日均线 · 有效成分数未提供" },
  ] },
] as const;

export default function CompactOverview({ onOpen }: { onOpen: (id: string) => void }) {
  return <div className="compact-overview" aria-label="中美市场总览">
    <div className="compact-markets">{MARKETS.map(market => <section className="compact-market" key={market.label} aria-label={`${market.label}核心观察`}>
      <h3>{market.label}<small>各指标按自身日期与股票池阅读</small></h3>
      <div className="compact-cards">{market.cards.map(card => <article key={card.id} className="compact-card" data-compact-card={card.id}>
        <header><h4>{card.title}</h4><button type="button" onClick={() => onOpen(card.id)} aria-label={`查看${card.title}大图`}>大图</button></header>
        <p className="compact-card-note">{card.note}</p>
        <IndicatorThumbnail id={card.id} showScale />
      </article>)}</div>
    </section>)}</div>
    <div className="compact-more" aria-label="其他观察入口">
      <div className="compact-star"><StarBreadthSnapshot><EarningsCoverageSnapshot onOpenGuide={() => onOpen("earnings-revisions")} /></StarBreadthSnapshot><small>历史试算，非实时</small></div>
      <button type="button" onClick={() => onOpen("us-equal-weight-relative")}>美股等权 / 市值权 · ETF代理</button>
      <button type="button" onClick={() => onOpen("us-cor3m")} title="按市值选取的50股期权约3个月隐含相关">COR3M · 50股期权隐含相关（3个月）</button>
      <button type="button" onClick={() => onOpen(INDUSTRY_TURNOVER_ID)} title="通信设备、半导体及设备与材料；按各行业自身历史看换手活跃程度">行业换手率 · 通信 / 半导体</button>
    </div>
    <div className="compact-macro"><SocialFinancingSnapshot /></div>
    <p className="compact-footnote">沪深300股债利差与全A宽度的股票池不同；各图按自身日期阅读，参考线用于观察。</p>
  </div>;
}
