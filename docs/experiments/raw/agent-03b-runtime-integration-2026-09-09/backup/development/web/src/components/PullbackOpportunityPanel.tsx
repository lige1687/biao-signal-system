import type { PullbackOpportunity } from "../types";
import type { Selection } from "./ExplanationPanel";

interface Props {
  opportunities: PullbackOpportunity[];
  onSelect: (selection: Selection) => void;
}

export default function PullbackOpportunityPanel({ opportunities, onSelect }: Props) {
  if (opportunities.length === 0) return null;
  return (
    <section className="pullback-opportunity-panel" aria-label="首次均线回撤提醒">
      <div className="pullback-opportunity-head">
        <div>
          <div className="trade-eyebrow">研究代理 · 条件化提醒 · 非交易指令</div>
          <h3>首次回撤机会</h3>
        </div>
        <span>{opportunities.filter((item) => item.state === "confirmed").length} 条当前确认</span>
      </div>
      <div className="pullback-opportunity-list">
        {opportunities.map((item) => (
          <button
            key={`${item.lifecycle_id}-${item.ma_period}`}
            className={`pullback-opportunity-row ${item.state}`}
            type="button"
            onClick={() =>
              onSelect({
                source: "首次回撤 · 当前场景",
                date: item.confirmed_date ?? item.touch_date,
                price: item.ma_value,
                explanation: item.explanation,
                events: item.supporting_event ? [item.supporting_event] : [],
                eventsLoading: false,
              })
            }
          >
            <span className={`trade-state ${item.state}`}>{item.state_cn}</span>
            <span className="pullback-ma">
              <b>{item.ma_name}</b>
              <small>锚点 {item.trend_anchor_date}</small>
            </span>
            <span className="pullback-distance">
              距均线 {item.distance_to_ma_pct > 0 ? "+" : ""}{item.distance_to_ma_pct.toFixed(2)}%
            </span>
            <span className="pullback-current">
              {item.state === "confirmed"
                ? "当前趋势与均线条件仍成立"
                : item.missing_conditions[0] ?? "等待收盘确认"}
            </span>
            <span
              className="pullback-rr"
              title={
                item.reward_risk_computable
                  ? `盈亏比（研究代理·只算不强制）：目标 ${item.reward_risk_target?.toFixed(2)}（${item.reward_risk_target_source_cn}）`
                  : "盈亏比：目标不可计算（研究代理·只算不强制）"
              }
            >
              {item.reward_risk_computable && item.reward_risk_ratio != null
                ? `R/R ${item.reward_risk_ratio.toFixed(1)}`
                : "R/R 不可计算"}
            </span>
            <span className="trade-open">查看解释</span>
          </button>
        ))}
      </div>
    </section>
  );
}
