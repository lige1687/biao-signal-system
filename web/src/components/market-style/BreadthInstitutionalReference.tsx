import type { BreadthHorizon } from "./breadthReadingTypes";
import { BREADTH_EXTERNAL_REFERENCES as refs } from "./breadthInstitutionalReferences";
import "./breadth-comparison.css";

/** Fixed external examples alongside, never substituted for, the local dynamic percentiles. */
export default function BreadthInstitutionalReference({ market, horizon, showValues = true }: {
  market: "cn" | "us"; horizon?: BreadthHorizon; showValues?: boolean;
}) {
  return <aside className="bc-external-reference" aria-label="外部来源宽度固定参考">
    {showValues && <div className="bc-external-values">
      <a href={refs.stockcharts.url} target="_blank" rel="noreferrer">StockCharts 固定参考 ↗</a>
      <span data-selected={horizon === "50"}>50日 <b>&lt;{refs.stockcharts.sma50.lower}%低 / &gt;{refs.stockcharts.sma50.upper}%高</b></span>
      <span data-selected={horizon === "200"}>200日 <b>{refs.stockcharts.sma200.majority}%半数线</b></span>
    </div>}
    {horizon === "20" && <p className="bc-external-note">20日宽度暂无已核实的机构固定参考值。</p>}
    <details className="bc-external-detail">
      <summary>{market === "cn" ? "参考美股经验，观察全A参与面" : "高位看广泛支撑，低位看卖压"} · 用法与来源</summary>
      <p><a href={refs.stockcharts.url} target="_blank" rel="noreferrer">StockCharts 指标说明</a>：50日宽度低于30%、高于70%作为超卖／超买经验参考；不同指数可不同，极端状态可持续。200日的50%表示半数股票站上长期均线，用于观察长期参与面。</p>
      <p><a href={refs.schwab.url} target="_blank" rel="noreferrer">Charles Schwab（{refs.schwab.publishedOn}）</a>：标普500的50日宽度在上涨中约80%，可体现广泛强势；下跌中低于10%可提示卖压极端。高位看支撑能否维持，低位看参与面何时回升。</p>
      <p>{market === "cn" ? "原文示例来自美国指数，当前用于与全A作跨市场对照；全A的适用性仍待检验。" : "两份原文提供参与面强弱的经验读法，预测效果仍待检验。"}动态P10/P90来自本系统历史统计，用于比较本市场自身的位置。</p>
    </details>
  </aside>;
}
