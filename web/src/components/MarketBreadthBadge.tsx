import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import type { GlobalPanel } from "../types";
import MarketBreadthModal from "./MarketBreadthModal";

interface PanelStatus {
  /** 短状态词：热 / 冷 / 反转 / 平。 */
  label: string;
  /** 着色基调，对应 CSS 类后缀。 */
  tone: "hot" | "cold" | "reversal" | "neutral";
}

/**
 * 顶栏市场宽度徽章：把原先常驻、占横向空间的 MarketBreadthStrip 收成一颗
 * 紧凑徽章（如「宽度 B20 59.8%·热」），点击打开 MarketBreadthModal 浮层。
 * 多市场（如全A + 标普500）时点开后出现小浮层列出各市场，再进对应浮层。
 *
 * 状态口径与 MarketBreadthStrip / 后端 _breadth_alerts 一致：
 *   - 双周期共振极值（B50+B200 同时 ≥80 / ≤20）→ 反转（红）
 *   - 中周期极值（B50 ≥80 顶部 / ≤20 底部）→ 热 / 冷
 *   - 其余 → 平
 */
function panelStatus(p: GlobalPanel): PanelStatus {
  const reversal = (p.alerts ?? []).some((a) => a.level === "reversal");
  if (reversal) return { label: "反转", tone: "reversal" };
  const medium = p.breadth_50 != null ? p.breadth_50 : p.breadth_20;
  if (medium != null) {
    if (medium >= 80) return { label: "热", tone: "hot" };
    if (medium <= 20) return { label: "冷", tone: "cold" };
  }
  return { label: "平", tone: "neutral" };
}

function fmtPct(v: number | null | undefined, digits = 1): string {
  if (v == null) return "--";
  return `${v.toFixed(digits)}%`;
}

/** 优先选 A 股主市场面板，否则取第一个。 */
function pickPrimary(panels: GlobalPanel[]): GlobalPanel | null {
  if (panels.length === 0) return null;
  return (
    panels.find((p) => p.market_id.toUpperCase().includes("CN")) ?? panels[0]
  );
}

export default function MarketBreadthBadge() {
  const { data, isLoading } = useQuery({
    queryKey: ["marketContextGlobalStrip"],
    queryFn: () => api.marketContextGlobalStrip(),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
  const [openPanel, setOpenPanel] = useState<GlobalPanel | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);

  const panels = data?.panels ?? [];
  const primary = useMemo(() => pickPrimary(panels), [panels]);

  if (isLoading && !data) {
    return <span className="breadth-badge loading">宽度 --</span>;
  }
  if (!primary) {
    return <span className="breadth-badge missing">宽度 --</span>;
  }

  const status = panelStatus(primary);

  const openPrimary = () => {
    if (panels.length > 1) {
      setPickerOpen((v) => !v);
    } else {
      setOpenPanel(primary);
    }
  };

  return (
    <div className="breadth-badge-wrap">
      <button
        type="button"
        className={`breadth-badge ${status.tone}`}
        onClick={openPrimary}
        title={
          primary.alerts?.length
            ? primary.alerts.map((a) => a.title).join(" · ")
            : `${primary.display_name} · 宽度 B20 ${fmtPct(primary.breadth_20)}（B50 ${fmtPct(
                primary.breadth_50,
              )} / B200 ${fmtPct(primary.breadth_200)}）`
        }
      >
        <span className="bb-label">宽度</span>
        <span className="bb-key">B20</span>
        <span className="bb-pct">{fmtPct(primary.breadth_20)}</span>
        <span className="bb-status">·{status.label}</span>
      </button>

      {panels.length > 1 && pickerOpen && (
        <>
          <div className="breadth-badge-backdrop" onClick={() => setPickerOpen(false)} />
          <div className="breadth-badge-picker">
            {panels.map((p) => {
              const s = panelStatus(p);
              return (
                <button
                  key={p.market_id}
                  type="button"
                  className={`breadth-badge-pick ${s.tone}`}
                  onClick={() => {
                    setPickerOpen(false);
                    setOpenPanel(p);
                  }}
                >
                  <span className="bb-pick-name">{p.display_name}</span>
                  <span className="bb-pick-val">B20 {fmtPct(p.breadth_20)}</span>
                  <span className="bb-pick-status">·{s.label}</span>
                </button>
              );
            })}
          </div>
        </>
      )}

      {openPanel && (
        <MarketBreadthModal panel={openPanel} onClose={() => setOpenPanel(null)} />
      )}
    </div>
  );
}
