import { useState } from "react";
import MicrostructureObservations from "./MicrostructureObservations";

type Mode = "daily5" | "daily10" | "monthly5";
const KEY = "ws.concentrationView.v1";
const OPTIONS = [
  { id: "daily5", label: "日频 · 前5%" },
  { id: "daily10", label: "日频 · 前10%" },
  { id: "monthly5", label: "月频 · 前5%" },
] as const;
function initialMode(): Mode {
  try { const saved = localStorage.getItem(KEY); return OPTIONS.some(item => item.id === saved) ? saved as Mode : "daily5"; }
  catch { return "daily5"; }
}
export default function ConcentrationObservationCard({ onCollapse }: {
  onCollapse: () => void;
}) {
  const [mode, setMode] = useState<Mode>(initialMode);
  return <section className="moa-concentration moa-standalone" data-overview-card="turnover-concentration" aria-label="成交额集中度 · 周期与口径">
    <div className="moa-concentration-controls">
      <div role="group" aria-label="成交额集中度周期">{OPTIONS.map(item => <button key={item.id}
        aria-pressed={mode === item.id} onClick={() => { setMode(item.id); try { localStorage.setItem(KEY, item.id); } catch { /* The current view remains usable. */ } }}>{item.label}</button>)}</div>
      <button onClick={onCollapse}>收起</button>
    </div>
    <MicrostructureObservations market="cn" selectedIds={[mode === "monthly5" ? "cn-monthly-amount-top5"
      : mode === "daily5" ? "cn-daily-amount-top5" : "cn-daily-amount-top10"]} />
    {mode !== "monthly5" && <p className="moa-card-limit">小图看近120个交易日；更早日线可在「看历史与口径」中选「全部」。</p>}
    <p className="moa-card-limit">日频按当天成交额排名；月频先累加每只股票整月成交额再排名。前5%与前10%使用相同股票池，观察集中程度的不同范围。</p>
  </section>;
}
