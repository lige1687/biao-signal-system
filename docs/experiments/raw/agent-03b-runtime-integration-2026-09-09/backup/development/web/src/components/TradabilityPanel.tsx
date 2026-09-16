import type { Tradability } from "../types";

interface Props {
  tradability: Tradability | null;
}

/** 可交易性门禁（研究代理·只算不强制）：趋势类型 + 9 条无交易条件 + 阻断原因。 */
export default function TradabilityPanel({ tradability }: Props) {
  if (!tradability) return null;
  const t = tradability;
  return (
    <section className={`panel tradability-panel ${t.tradable ? "ok" : "blocked"}`} aria-label="可交易性门禁">
      <div className="tradability-head">
        <div>
          <div className="trade-eyebrow">研究代理 · 横切层 · 只算不强制</div>
          <h3>可交易性门禁</h3>
        </div>
        <span className={`tradability-state ${t.tradable ? "ok" : "blocked"}`}>
          {t.tradable ? "可交易" : "阻断"}
        </span>
      </div>
      <div className="tradability-type">
        趋势类型：<b>{t.trend_type_cn}</b>
        {t.blocking_reasons.length > 0 && (
          <span className="tradability-blocks">
            {" "}· 阻断：{t.blocking_reasons.join("；")}
          </span>
        )}
      </div>
      <ul className="tradability-checks">
        {t.condition_checks.map((c) => (
          <li key={c.code} className={c.blocked ? "blocked" : "ok"}>
            <span className="ck-mark">{c.blocked ? "✕" : "✓"}</span>
            <span className="ck-label">{c.label_cn}</span>
            <span className="muted ck-detail">{c.detail_cn}</span>
          </li>
        ))}
      </ul>
      {t.caveat_cn && <div className="tradability-caveat muted">{t.caveat_cn}</div>}
    </section>
  );
}
