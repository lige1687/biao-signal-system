import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import type { GlobalPanel } from "../types";
import MarketBreadthModal from "./MarketBreadthModal";

function fmtPct(v: number | null | undefined, digits = 1): string {
  if (v == null) return "--";
  return `${v.toFixed(digits)}%`;
}

function fmtSigned(v: number | null | undefined, digits = 1): string {
  if (v == null) return "";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(digits)}`;
}

function deltaArrow(v: number | null | undefined): string {
  if (v == null) return "";
  return v > 0 ? "↑" : v < 0 ? "↓" : "→";
}

function deltaClass(v: number | null | undefined): string {
  if (v == null) return "";
  return v > 0 ? "up" : v < 0 ? "down" : "";
}

/**
 * Collapsible market-breadth strip for the topbar.
 *
 * Collapsed (default): thin single-line bar, just market name + B20 + arrow.
 * Expanded: compact 2-panel grid with B20/B50/5日/分位.
 * State persisted to localStorage.
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
          {panels.map((p) => (
            <button
              key={p.market_id}
              className={`strip-chip status-${p.data_status}`}
              onClick={() => setOpenPanel(p)}
              title={`${p.display_name} · 点击展开详情`}
            >
              <span className="strip-chip-name">{p.display_name}</span>
              <span className={`strip-chip-val ${deltaClass(p.breadth_20_delta_5)}`}>
                {fmtPct(p.breadth_20)}
              </span>
              <span className={`strip-chip-arrow ${deltaClass(p.breadth_20_delta_5)}`}>
                {deltaArrow(p.breadth_20_delta_5)}
              </span>
              {p.percentile_20 != null && (
                <span className="strip-chip-pct">P{p.percentile_20.toFixed(0)}</span>
              )}
            </button>
          ))}
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
        {panels.map((p) => (
          <button
            key={p.market_id}
            className={`breadth-strip-panel status-${p.data_status}`}
            onClick={() => setOpenPanel(p)}
            title={`${p.display_name} · 点击查看完整宽度与历史分位收益`}
          >
            <div className="strip-panel-head">
              <span className="strip-panel-name">{p.display_name}</span>
              {p.percentile_20 != null && (
                <span className="strip-pct-badge">P{p.percentile_20.toFixed(0)}</span>
              )}
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
          </button>
        ))}
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
