import { useState } from "react";
import type { TradeOpportunity } from "../types";
import type { Selection } from "./ExplanationPanel";

interface Props {
  opportunities: TradeOpportunity[];
  onSelect: (selection: Selection) => void;
}

function fmtPrice(value: number | null): string {
  return value == null ? "—" : value.toFixed(2);
}

function OpportunityRow({
  opportunity: item,
  onSelect,
}: {
  opportunity: TradeOpportunity;
  onSelect: Props["onSelect"];
}) {
  const tone = item.state === "confirmed" ? "confirmed" : item.state === "weakened" ? "weakened" : "watch";
  const pick = () =>
    onSelect({
      source: "买点提醒 · 持续状态",
      date: item.last_upgraded_on,
      price: item.structure.c_price ?? undefined,
      explanation: item.explanation,
      structure: item.structure,
      events: item.supporting_event ? [item.supporting_event] : [],
      eventsLoading: false,
    });

  return (
    <button className={`trade-opportunity-row ${tone}`} type="button" onClick={pick}>
      <span className={`trade-state ${tone}`}>{item.state_cn}</span>
      <span className="trade-tier">
        <b>{item.reached_tier_cn}</b>
        <small>本轮达到</small>
      </span>
      <span className="trade-structure">
        <b>{item.structure.structure_type_cn}</b>
        <small>{item.structure.status_cn} · C {fmtPrice(item.structure.c_price)}</small>
      </span>
      <span className="trade-current">
        {item.current_conditions_confirmed ? "当前条件仍成立" : item.missing_conditions[0] ?? "等待条件恢复"}
      </span>
      <span className="trade-buffer">
        {item.structure.distance_to_c_pct == null
          ? "C 安全垫 —"
          : `C 安全垫 ${item.structure.distance_to_c_pct.toFixed(1)}%`}
      </span>
      <span className="trade-open">查看解释</span>
    </button>
  );
}

export default function TradeOpportunityPanel({ opportunities, onSelect }: Props) {
  const [expanded, setExpanded] = useState(false);
  if (opportunities.length === 0) return null;

  const confirmed = opportunities.filter((item) => item.is_buy_reference).length;
  const weakened = opportunities.filter((item) => item.state === "weakened").length;
  const rows = expanded ? opportunities : opportunities.slice(0, 3);

  return (
    <section className="trade-opportunity-panel" aria-label="买点提醒">
      <div className="trade-opportunity-head">
        <div>
          <div className="trade-eyebrow">条件化提醒 · 非交易指令</div>
          <h3>潜在买点</h3>
        </div>
        <div className="trade-summary">
          <span>{confirmed} 条确认参考</span>
          {weakened > 0 && <span className="warning">{weakened} 条确认减弱</span>}
          <button
            className="trade-toggle"
            type="button"
            aria-expanded={expanded}
            onClick={() => setExpanded((value) => !value)}
          >
            {expanded ? "收起" : opportunities.length > 3 ? `展开全部 ${opportunities.length}` : "展开条件"}
          </button>
        </div>
      </div>

      <div className="trade-opportunity-list">
        {rows.map((item) => (
          <OpportunityRow key={item.lifecycle_id} opportunity={item} onSelect={onSelect} />
        ))}
      </div>

      {expanded && (
        <div className="trade-method">
          <span>确认参考：结构确认档及以上</span>
          <span>转黑：关闭本轮生命周期</span>
          <span>触及 C：结构永久失效</span>
          <span>B1：仅作第一阻力参考</span>
        </div>
      )}
    </section>
  );
}
