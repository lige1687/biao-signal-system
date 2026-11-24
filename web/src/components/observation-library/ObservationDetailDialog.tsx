import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import type { ObservationEntry } from "./catalog";
import CnFinancingProjection, { type CnFinancingTab } from "./CnFinancingProjection";
import ObservationMetric from "./ObservationMetric";
import { MetricProjection } from "./projectionView";
import { PROJECTION_METRICS } from "./projectionSources";

export default function ObservationDetailDialog({
  item,
  onClose,
  financingTab,
}: {
  item: ObservationEntry;
  onClose: () => void;
  financingTab?: CnFinancingTab;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const projection = PROJECTION_METRICS.find(row => row.id === item.id);
  useEffect(() => {
    const element = dialog.current;
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    element?.showModal();
    return () => { element?.close(); if (trigger?.isConnected) trigger.focus({ preventScroll: true }); };
  }, []);
  return createPortal(<dialog ref={dialog} className="hoc-dialog" aria-labelledby="hoc-dialog-title"
    onCancel={event => { event.preventDefault(); onClose(); }}
    onClick={event => { if (event.target === event.currentTarget) onClose(); }}>
    <div className="hoc-dialog-surface">
      <header className="hoc-dialog-header"><div><span>市场观察 · {item.market === "cn" ? "A股" : item.market === "us" ? "美股" : "跨市场"}</span>
        <h2 id="hoc-dialog-title">{item.label}</h2></div>
        <button type="button" onClick={onClose} aria-label="关闭观察详情">关闭 ×</button></header>
      <div className="hoc-dialog-content observation-projection">
        {item.id === "cn-financing" ? (
          <CnFinancingProjection initialTab={financingTab} />
        ) : projection ? (
          <MetricProjection id={item.id} market={projection.market} />
        ) : (
          <>
            <p className="op-meaning">{item.meaning}</p>
            <ObservationMetric id={item.id} />
          </>
        )}
        <details className="hoc-dialog-limits"><summary>适用范围与限制</summary><p>{item.limitation}</p></details>
      </div>
    </div>
  </dialog>, document.body);
}
