import type { ConditionalScenario } from "../types";
import type { Selection } from "./ExplanationPanel";

interface Props {
  scenarios: ConditionalScenario[];
  onSelect: (selection: Selection) => void;
}

export default function ConditionalScenarioPanel({ scenarios, onSelect }: Props) {
  if (scenarios.length === 0) return null;
  return (
    <section className="conditional-scenario-panel" aria-label="条件化交易场景提醒">
      <div className="conditional-scenario-head">
        <div>
          <div className="trade-eyebrow">研究代理 · 条件化提醒 · 非交易指令</div>
          <h3>条件化场景</h3>
        </div>
        <span>
          {scenarios.filter((item) => item.state === "confirmed").length} 条当前确认
        </span>
      </div>
      <div className="conditional-scenario-list">
        {scenarios.map((item) => (
          <button
            key={item.scenario_id}
            className={`conditional-scenario-row ${item.state} ${item.direction}`}
            type="button"
            onClick={() =>
              onSelect({
                source: `${item.scenario_cn} · 当前场景`,
                date: item.trigger_date ?? item.anchor_date,
                price: item.reference_price ?? item.key_price,
                explanation: item.explanation,
                events: item.supporting_event ? [item.supporting_event] : [],
                eventsLoading: false,
              })
            }
          >
            <span className={`trade-state ${item.state}`}>{item.state_cn}</span>
            <span className="scenario-name">
              <b>{item.scenario_cn}</b>
              <small>
                {item.direction_cn} · 锚点 {item.anchor_date}
                {item.distance_pct != null
                  ? ` · 距参考 ${item.distance_pct > 0 ? "+" : ""}${item.distance_pct.toFixed(2)}%`
                  : ""}
              </small>
            </span>
            <span className="scenario-conditions">
              {item.satisfied_conditions.slice(0, 2).map((c) => (
                <span key={c} className="cond ok">
                  {c}
                </span>
              ))}
              {item.missing_conditions.slice(0, 1).map((c) => (
                <span key={c} className="cond miss">
                  {c}
                </span>
              ))}
            </span>
            <span
              className="scenario-rr"
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
