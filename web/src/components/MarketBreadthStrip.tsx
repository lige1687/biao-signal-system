import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import type { BreadthAlert, GlobalPanel } from "../types";
import MarketBreadthModal from "./MarketBreadthModal";
import {
  isRealAShare,
  fmtPct as fmtPctAD,
  fmtNum as fmtNumAD,
  fmtRatio as fmtRatioAD,
  UP_COLOR,
  DOWN_COLOR,
} from "./aShareBreadthView";

function fmtPct(v: number | null | undefined, digits = 1): string {
  if (v == null) return "--";
  return `${v.toFixed(digits)}%`;
}

const REGIME_CN: Record<string, string> = {
  bull: "牛",
  bear: "熊",
  unknown: "",
};

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
 * Collapsed (default): thin single-line bar, just market name + B20 + arrow.
 * Expanded: compact 2-panel grid with B20/B50/5日/分位.
 * State persisted to localStorage.
 *
 * When breadth extremes fire (B50 ≥85 or ≤15, or B50+B200 both at an
 * extreme), a prominent alert badge pulses on the panel so the user
 * can't miss a potential reversal signal.
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
                    : `${p.display_name} · 点击展开详情`
                }
              >
                <span className="strip-chip-name">{p.display_name}</span>
                {REGIME_CN[p.long_regime] && (
                  <span className={`strip-chip-regime regime-${p.long_regime}`}>
                    {REGIME_CN[p.long_regime]}
                  </span>
                )}
                {isRealAShare(p) ? (
                  <span className="strip-chip-val">
                    涨{fmtNumAD(p.up)}·跌{fmtNumAD(p.down)}
                  </span>
                ) : (
                  <>
                    <span className={`strip-chip-val ${deltaClass(p.breadth_20_delta_5)}`}>
                      {fmtPct(p.breadth_20)}
                    </span>
                    <span className={`strip-chip-arrow ${deltaClass(p.breadth_20_delta_5)}`}>
                      {deltaArrow(p.breadth_20_delta_5)}
                    </span>
                    {p.percentile_20 != null && (
                      <span className="strip-chip-pct">P{p.percentile_20.toFixed(0)}</span>
                    )}
                  </>
                )}
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
          return (
            <button
              key={p.market_id}
              className={`breadth-strip-panel status-${p.data_status} ${
                reversal ? "alert-reversal" : anyAlert ? "alert-stage" : ""
              }`}
              onClick={() => setOpenPanel(p)}
              title={`${p.display_name} · 点击查看完整宽度与历史分位收益`}
            >
              <div className="strip-panel-head">
                <span className="strip-panel-name">{p.display_name}</span>
                {REGIME_CN[p.long_regime] && (
                  <span className={`strip-chip-regime regime-${p.long_regime}`}>
                    {REGIME_CN[p.long_regime]}
                  </span>
                )}
                {p.percentile_20 != null && (
                  <span className="strip-pct-badge">P{p.percentile_20.toFixed(0)}</span>
                )}
                {anyAlert && <span className="strip-alert-bell">⚠</span>}
              </div>
              <div className="strip-panel-body">
                {isRealAShare(p) ? (
                  <>
                    <div className="strip-cell">
                      <span className="muted">涨/跌</span>
                      <strong style={{ color: UP_COLOR }}>
                        {fmtNumAD(p.up)}/{fmtNumAD(p.down)}
                      </strong>
                      <span className="strip-delta">占比{fmtPctAD(p.up_pct)}</span>
                    </div>
                    <div className="strip-cell">
                      <span className="muted">涨跌比</span>
                      <strong style={{ color: (p.adv_dec_ratio ?? 0) >= 1 ? UP_COLOR : DOWN_COLOR }}>
                        {fmtRatioAD(p.adv_dec_ratio)}
                      </strong>
                    </div>
                  </>
                ) : (
                  <>
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
                  </>
                )}
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
