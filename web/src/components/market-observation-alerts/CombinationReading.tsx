import type { marketConnections } from "./conditionalReading";
import "./combination-reading.css";

type Reading = ReturnType<typeof marketConnections>;
export default function CombinationReading({ market, reading }: { market: "cn" | "us"; reading: Reading }) {
  const facts = [...new Map(reading.chains.flatMap(chain => chain.facts)
    .map(fact => [`${fact.date ?? ""}:${fact.text}`, fact])).values()];
  return <section className="moa-combination" aria-label={`${market === "cn" ? "A股" : "美股"}组合解读`}>
    <header><span>{market === "cn" ? "A股" : "美股"}</span><h4>{reading.headline}</h4></header>
    {reading.chains.length ? <ol className="moa-connections">{reading.chains.map(chain => <li key={chain.id}>
      {chain.meaning}
    </li>)}</ol> : <p className="moa-combination-empty">组合所需读数待补齐，当前可先查看各卡已有的水平与变化。</p>}
    {reading.chains.length > 0 && <details className="moa-combination-evidence">
      <summary>读数、日期与后续观察</summary>
      <ul className="moa-connection-facts">{facts.map(fact => <li key={`${fact.date}:${fact.text}`}>
        <span>{fact.text}</span>{fact.date && <time dateTime={fact.date}>{fact.date}</time>}
      </li>)}</ul>
      <div className="moa-connection-next">
        <p><b>改善看</b>{reading.improve}</p><p><b>警惕看</b>{reading.deteriorate}</p>
      </div>
      <p className="moa-combination-limit">{reading.limitation}</p>
    </details>}
  </section>;
}
