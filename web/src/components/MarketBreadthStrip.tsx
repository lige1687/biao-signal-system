import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import type { BreadthAlert, GlobalPanel } from "../types";
import MarketBreadthModal from "./MarketBreadthModal";

function fmtPct(v: number | null | undefined, digits = 1): string {
  if (v == null) return "--";
  return `${v.toFixed(digits)}%`;
}

/**
 * 顶部条要展示的三个“阶段坑位”，相互独立、可同时点亮：
 *   1. 底色  — 长期趋势（B200 > 50 牛 / < 50 熊）
 *   2. 阶段  — 中周期极值（B50 ≥80 阶段性顶部 / ≤20 短期底部）
 *   3. 反转  — 双周期共振极值（B50+B200 同时 ≥80 顶部 / ≤20 底部）
 * 未满足的坑位显示为灰色占位（“—”），满足的按维度染色。
 * 口径与 MarketBreadthModal / 后端 `_breadth_alerts` 一致。
 */

const _HOT = 80;
const _COLD = 20;

interface SlotState {
  /** 是否点亮（满足触发条件）。未满足则为灰色占位。 */
  active: boolean;
  /** 坑位文案（点亮时显示具体信号，未点亮显示占位符）。 */
  text: string;
  /** 着色基调：bull/bear/warn/cold/hot/neutral。 */
  tone: string;
}

function deriveStageSlots(panel: GlobalPanel) {
  const b50 = panel.breadth_50;
  const b20 = panel.breadth_20;
  const b200 = panel.breadth_200;
  // 中周期取 B50，缺失时回退 B20（与后端一致）。
  const medium = b50 != null ? b50 : b20;

  // 1. 底色（长期趋势，永远有状态）
  let base: SlotState;
  if (b200 == null) base = { active: false, text: "无宽度", tone: "neutral" };
  else if (b200 > 50) base = { active: true, text: "🐂 牛市底色", tone: "bull" };
  else if (b200 < 50) base = { active: true, text: "🐻 熊市底色", tone: "bear" };
  else base = { active: false, text: "中性", tone: "neutral" };

  // 2. 阶段（中周期极值）
  let stage: SlotState;
  if (medium == null) stage = { active: false, text: "—", tone: "neutral" };
  else if (medium >= _HOT)
    stage = { active: true, text: "阶段性顶部", tone: "warn" };
  else if (medium <= _COLD)
    stage = { active: true, text: "短期底部", tone: "cold" };
  else stage = { active: false, text: "—", tone: "neutral" };

  // 3. 反转（双周期共振）
  let reversal: SlotState;
  if (medium != null && b200 != null) {
    if (medium >= _HOT && b200 >= _HOT)
      reversal = { active: true, text: "⚠️ 反转顶部", tone: "hot" };
    else if (medium <= _COLD && b200 <= _COLD)
      reversal = { active: true, text: "⚠️ 反转底部", tone: "cold" };
    else reversal = { active: false, text: "—", tone: "neutral" };
  } else {
    reversal = { active: false, text: "—", tone: "neutral" };
  }

  return { base, stage, reversal };
}

function fmtSigned(v: number | null | undefined, digits = 1): string {
  if (v == null) return "";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(digits)}`;
}

function deltaArrow(v: number | null | undefined): string {
  if (v == null) return "";
  return v > 0 ? "↑" : v < 0 ? "↓" : "->";
}

function deltaClass(v: number | null | undefined): string {
  if (v == null) return "";
  return v > 0 ? "up" : v < 0 ? "down" : "";
}

function hasReversalAlert(alerts: BreadthAlert[] | undefined): boolean {
  return !!alerts?.some((a) => a.level === "reversal");
}

function hasAnyAlert(alerts: BreadthAlert[] | undefined): boolean {
  return !!alerts && alerts.length > 0;
}

/**
 * Collapsible market-breadth strip for the topbar.
 *
 * Dashboard style: just 全A + 标普500, B20/B50 + 5日 delta.
 * No A-share up/down/adv-dec ratio clutter on this top-level strip.
 * Extremes (B50 ≥80 or ≤20, or B50+B200 both extreme) surface as alert badges.
 */
export default function MarketBreadthStrip() {
  const { data, isLoading } = useQuery({
    queryKey: ["marketContextGlobalStrip"],
    queryFn: () => api.marketContextGlobalStrip(),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
  const [openPanel, setOpenPanel] = useState<GlobalPanel | null>(null);
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    return localStorage.getItem("ws.breadthCollapsed") === "1";
  });

  const toggle = () => {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem("ws.breadthCollapsed", next ? "1" : "0");
  };

  if (isLoading && !data) {
    return (
      <div className="breadth-strip loading">
        <span className="muted">市场宽度加载中…</span>
      </div>
    );
  }

  const panels = data?.panels ?? [];
  if (panels.length === 0) return null;

  if (collapsed) {
    return (
      <>
        <div className="breadth-strip-collapsed">
          {panels.map((p) => {
            const reversal = hasReversalAlert(p.alerts);
            const anyAlert = hasAnyAlert(p.alerts);
            const slots = deriveStageSlots(p);
            return (
              <button
                key={p.market_id}
                className={`strip-chip status-${p.data_status} ${
                  reversal ? "alert-reversal" : anyAlert ? "alert-stage" : ""
                }`}
                onClick={() => setOpenPanel(p)}
                title={
                  p.alerts?.length
                    ? p.alerts.map((a) => a.title).join(" · ")
                    : `${p.display_name} · 底色：${slots.base.text}｜阶段：${slots.stage.text}｜反转：${slots.reversal.text}`
                }
              >
                <span className="strip-chip-name">{p.display_name}</span>
                <span className="stage-dots" title={`底色：${slots.base.text}｜阶段：${slots.stage.text}｜反转：${slots.reversal.text}`}>
                  <i className={`stage-dot tone-${slots.base.tone} ${slots.base.active ? "on" : ""}`} />
                  <i className={`stage-dot tone-${slots.stage.tone} ${slots.stage.active ? "on" : ""}`} />
                  <i className={`stage-dot tone-${slots.reversal.tone} ${slots.reversal.active ? "on" : ""}`} />
                </span>
                <span className={`strip-chip-val ${deltaClass(p.breadth_20_delta_5)}`}>
                  {fmtPct(p.breadth_20)}
                </span>
                <span className={`strip-chip-arrow ${deltaClass(p.breadth_20_delta_5)}`}>
                  {deltaArrow(p.breadth_20_delta_5)}
                </span>
                {anyAlert && <span className="strip-chip-bell">⚠</span>}
              </button>
            );
          })}
          <button className="strip-toggle" onClick={toggle} title="展开市场宽度">
            ▾
          </button>
        </div>
        {openPanel && (
          <MarketBreadthModal panel={openPanel} onClose={() => setOpenPanel(null)} />
        )}
      </>
    );
  }

  return (
    <>
      <div className="breadth-strip">
        {panels.map((p) => {
          const reversal = hasReversalAlert(p.alerts);
          const anyAlert = hasAnyAlert(p.alerts);
          const slots = deriveStageSlots(p);
          return (
            <button
              key={p.market_id}
              className={`breadth-strip-panel status-${p.data_status} ${
                reversal ? "alert-reversal" : anyAlert ? "alert-stage" : ""
              }`}
              onClick={() => setOpenPanel(p)}
              title={`${p.display_name} · 底色：${slots.base.text}｜阶段：${slots.stage.text}｜反转：${slots.reversal.text}`}
            >
              <div className="strip-panel-head">
                <span className="strip-panel-name">{p.display_name}</span>
                {anyAlert && <span className="strip-alert-bell">⚠</span>}
              </div>
              <div className="stage-slots-row">
                <span
                  className={`strip-chip-regime stage-${slots.base.tone}`}
                  title="长期底色（B200 上方占比）"
                >
                  {slots.base.text}
                </span>
                <span
                  className={`strip-chip-regime stage-${slots.stage.tone}`}
                  title="阶段极值（B50 上方占比 ≥80 顶部 / ≤20 底部）"
                >
                  {slots.stage.text}
                </span>
                <span
                  className={`strip-chip-regime stage-${slots.reversal.tone}`}
                  title="反转共振（B50 与 B200 同时 ≥80 顶部 / ≤20 底部）"
                >
                  {slots.reversal.text}
                </span>
              </div>
              <div className="strip-panel-body">
                <div className="strip-cell">
                  <span className="muted">B20</span>
                  <strong>{fmtPct(p.breadth_20)}</strong>
                  <span className={`strip-delta ${deltaClass(p.breadth_20_delta_5)}`}>
                    {deltaArrow(p.breadth_20_delta_5)} {fmtSigned(p.breadth_20_delta_5)}
                  </span>
                </div>
                <div className="strip-cell">
                  <span className="muted">B50</span>
                  <strong>{fmtPct(p.breadth_50)}</strong>
                  <span className={`strip-delta ${deltaClass(p.breadth_50_delta_5)}`}>
                    {deltaArrow(p.breadth_50_delta_5)} {fmtSigned(p.breadth_50_delta_5)}
                  </span>
                </div>
              </div>
              {anyAlert && (
                <div className="strip-alert-row">
                  {p.alerts!.map((a) => (
                    <span
                      key={a.type}
                      className={`strip-alert-badge ${a.level} ${a.type}`}
                    >
                      {a.title}
                    </span>
                  ))}
                </div>
              )}
            </button>
          );
        })}
        <button className="strip-toggle" onClick={toggle} title="收起市场宽度">
          ▴
        </button>
      </div>
      {openPanel && (
        <MarketBreadthModal panel={openPanel} onClose={() => setOpenPanel(null)} />
      )}
    </>
  );
}
