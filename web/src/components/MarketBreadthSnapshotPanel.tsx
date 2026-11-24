import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { GlobalPanel } from "../types";
import BreadthTrendChart from "./BreadthTrendChart";
import {
  BreadthAsOf,
  hasBreadth,
  isRealAShare,
} from "./aShareBreadthView";
import { SOURCE_NOTES } from "./trend/zones";

function fmtPct(v: number | null): string {
  return v == null ? "—" : `${v.toFixed(1)}%`;
}
function fmtDelta(v: number | null): string {
  if (v == null) return "";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(1)}`;
}

/* ------------------------------------------------------------------ */
/*  组件                                                                  */
/* ------------------------------------------------------------------ */

export default function MarketBreadthSnapshotPanel() {
  const [expanded, setExpanded] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ["marketContextGlobalStrip"],
    queryFn: () => api.marketContextGlobalStrip(),
    staleTime: 60_000,
  });

  const panels = data?.panels ?? [];
  // 全A(CN_ALL_A) + 美股(SP500) 双市场宽度，原提交版本即同时展示
  const cnAll = panels.find((p) => p.market_id === "CN_ALL_A") ?? null;
  const spx = panels.find((p) => p.market_id === "SP500") ?? null;

  return (
    <section className={`macro-snapshot market-breadth-snapshot${expanded ? " expanded" : ""}`}>
      <button
        type="button"
        className="macro-head"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        <span className="macro-chevron">{expanded ? "▾" : "▸"}</span>
        <span className="macro-title">市场宽度</span>
        <span className="macro-badges">
          {cnAll && hasBreadth(cnAll) ? (
            <>
              {cnAll?.breadth_50 != null && (
                <span className="macro-chip neutral" title="全A 50日宽度：站上50日均线的股票比例">
                  50日 {fmtPct(cnAll.breadth_50)}
                </span>
              )}
              {cnAll?.breadth_200 != null && (
                <span className="macro-chip neutral" title="全A 200日宽度：站上200日均线的股票比例">
                  200日 {fmtPct(cnAll.breadth_200)}
                </span>
              )}
            </>
          ) : cnAll && isRealAShare(cnAll) ? (
            <span className="macro-chip neutral" title="真全A·宽度计算中（收盘后预计算尚未跑）">
              宽度计算中…
            </span>
          ) : null}
        </span>
        <span className="macro-toggle">{expanded ? "收起" : "展开"}</span>
      </button>

      {/* ---- 紧凑模式：全A + 美股 宽度小卡 ---- */}
      {!expanded && !isLoading && !error && (cnAll || spx) && (
        <div className="macro-compact">
          {cnAll && <BreadthMiniCard panel={cnAll} />}
          {spx && <BreadthMiniCard panel={spx} />}
        </div>
      )}

      {isLoading && !data && <div className="loading">正在加载市场宽度…</div>}
      {error && <span className="muted">市场宽度加载失败</span>}

      {/* ---- 展开模式：趋势图 + 读数说明 ---- */}
      {expanded && (cnAll || spx) && (
        <div className="macro-expanded">
          <div className="breadth-trends">
            {cnAll && (
              <BreadthTrendChart marketId="CN_ALL_A" displayName="全A 真宽度（MA上方占比）" />
            )}
            {spx && <BreadthTrendChart marketId="SP500" displayName={spx.display_name} />}
          </div>
          {cnAll && (
          <div className="macro-zones">
            <CurrentPosition panel={cnAll} />

            <div className="macro-disclaimer">
              {SOURCE_NOTES.breadth} 50%仅表示半数股票站上对应均线，不作股市趋势判定。
              全A 真宽度(B20/B50/B200) = 站上对应均线个股占比，由本机「收盘后预计算」
              （<code>scripts/precompute_a_share_ma.py</code> 逐只拉腾讯日K线）落盘，
              <code>/market-context/global-strip</code> 直接读取，次日整天与周末不重算。
              趋势图需每日收盘后积累（约 252 个交易日形成完整年线，初始阶段仅 1 个数据点属正常）。
            </div>
          </div>
          )}
        </div>
      )}
    </section>
  );
}

/* ---- 当前参与比例 ---- */
function CurrentPosition({ panel }: { panel: GlobalPanel }) {
  return (
    <div className="zone-block current-position">
      <strong>当前参与比例</strong>
      <div className="current-position-row">
        <span>50日宽度 <b className="neutral">{fmtPct(panel.breadth_50)}</b></span>
      </div>
      <div className="current-position-row">
        <span>200日宽度 <b className="neutral">{fmtPct(panel.breadth_200)}</b></span>
      </div>
      <div className="current-position-row">
        <span>20日宽度 <b className="neutral">{fmtPct(panel.breadth_20)}</b></span>
        {panel.breadth_20_delta_5 != null && (
          <span className="macro-chip neutral">
            5日 {fmtDelta(panel.breadth_20_delta_5)}
          </span>
        )}
      </div>
      <BreadthAsOf p={panel} />
    </div>
  );
}

/* ---- 紧凑小卡：全A 真宽度 B20/B50/B200 ---- */
function BreadthMiniCard({ panel }: { panel: GlobalPanel }) {
  return (
    <div className="macro-card breadth-mini">
      <div className="macro-head">
        <span className="macro-name">{panel.display_name} 市场宽度</span>
        <span className="macro-chip neutral" title={SOURCE_NOTES.breadth}>参与比例</span>
        <span className="macro-period">{panel.updated_at?.slice(0, 10)}</span>
      </div>
      <div className="breadth-row">
        <span className="b-label">20 日</span>
        <span className="b-val neutral">
          {fmtPct(panel.breadth_20)}
          {panel.breadth_20_delta_5 != null && (
            <small className="b-delta">{fmtDelta(panel.breadth_20_delta_5)}</small>
          )}
        </span>
      </div>
      <div className="breadth-row">
        <span className="b-label">50 日</span>
        <span className="b-val neutral">
          {fmtPct(panel.breadth_50)}
          {panel.breadth_50_delta_5 != null && (
            <small className="b-delta">{fmtDelta(panel.breadth_50_delta_5)}</small>
          )}
        </span>
      </div>
      <div className="breadth-row">
        <span className="b-label">200 日</span>
        <span className="b-val neutral">{fmtPct(panel.breadth_200)}</span>
      </div>
      <div className="macro-note">
        数值为站上对应均线的股票占比；不代表买卖时点。
      </div>
    </div>
  );
}
