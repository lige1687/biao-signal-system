import { useState } from "react";
import CreatePlanDialog, { type PlanPrefill } from "./CreatePlanDialog";
import ReviewDrawer from "./ReviewDrawer";

/**
 * 建计划完整流程：填表建 draft -> 监督员核对抽屉（符合性 + 协商 + 确认）。
 *
 * 对外暴露与原 CreatePlanDialog 同构的接口（symbol / prefill / onClose），
 * 三处挂载点只需把 CreatePlanDialog 换成 PlanCreateFlow。
 * create 成功不再自动 confirm：先建 draft，交核对抽屉过符合性后再确认。
 */
export default function PlanCreateFlow({
  symbol,
  prefill,
  onClose,
}: {
  symbol: string;
  prefill?: PlanPrefill;
  onClose: () => void;
}) {
  const [planId, setPlanId] = useState<string | null>(null);

  if (planId) {
    return <ReviewDrawer planId={planId} onClose={onClose} />;
  }
  return (
    <CreatePlanDialog
      symbol={symbol}
      prefill={prefill}
      onClose={onClose}
      onCreated={(id) => setPlanId(id)}
    />
  );
}
