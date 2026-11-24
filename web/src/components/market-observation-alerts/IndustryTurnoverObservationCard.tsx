import { useState } from "react";
import MicrostructureObservations from "./MicrostructureObservations";
import { INDUSTRY_TURNOVER_ID, INDUSTRY_TURNOVER_OPTIONS } from "./industryTurnoverOptions";

const VIEW_KEY = "ws.industryTurnoverView.v1";

function initialIndustry() {
  try { return localStorage.getItem(VIEW_KEY); }
  catch { return null; }
}

export default function IndustryTurnoverObservationCard({ onCollapse }: { onCollapse: () => void }) {
  const [selectedId, setSelectedId] = useState(initialIndustry);
  const industry = INDUSTRY_TURNOVER_OPTIONS.find(({ id }) => id === selectedId) ?? INDUSTRY_TURNOVER_OPTIONS[0];

  function selectIndustry(id: string) {
    setSelectedId(id);
    try { localStorage.setItem(VIEW_KEY, id); }
    catch { /* The selection remains usable for this open card. */ }
  }

  return <section className="moa-standalone" data-overview-card={INDUSTRY_TURNOVER_ID} aria-label="行业换手率">
    <div className="moa-item-head">
      <h3>行业换手率</h3>
      <button type="button" onClick={onCollapse}>收起</button>
    </div>
    <label className="micro-select">选择行业
      <select value={industry.id} onChange={event => selectIndustry(event.target.value)}>
        {INDUSTRY_TURNOVER_OPTIONS.map(({ id, label }) => <option key={id} value={id}>{label}</option>)}
      </select>
    </label>
    <MicrostructureObservations market="cn" selectedIds={[industry.id]} />
  </section>;
}
