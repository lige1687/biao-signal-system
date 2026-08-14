import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { GlobalPanel } from "../types";
import BreadthTrendChart from "./BreadthTrendChart";

/* ------------------------------------------------------------------ */
/*  阈值与判断依据（全部标注来源）                                      */
/* ------------------------------------------------------------------ */

// 短期/中期宽度（20日、50日）极值框架
// 来源：国内券商（中信/华泰）市场宽度周报常用阈值——20日宽度 >85% 阶段顶(超买)、<15% 短期底(超卖)
const SHORT_BREADTH_ZONES = [
  { max: 15, label: "短期底/超卖（机会）", tone: "opportunity", note: "<15%：短期超卖，反弹概率较高（券商市场宽度框架）" },
  { max: 85, label: "中性区", tone: "neutral", note: "15–85%：常态区，宽度本身不构成极值信号" },
  { max: Infinity, label: "阶段顶/超买（风险）", tone: "danger", note: ">85%：阶段顶/超买，追高性价比低；与200日同处极端需警惕反转（券商框架）" },
] as const;

// 长期宽度（200日）框架：200日均线为长期多空分界
// 来源：经典技术分析中 200 日（≈200交易日）均线作为长期趋势分界
const LONG_BREADTH_ZONES = [
  { max: 50, label: "长期空头", tone: "danger", note: "<50%：长期宽度在 200 日均线下方，整体格局偏空" },
  { max: Infinity, label: "长期多头", tone: "opportunity", note: ">50%：长期宽度站上 200 日均线，长期多头确认（经典长期趋势分界）" },
] as const;

// Zweig Breadth Thrust 经典阈值（用于整体解读）
// 来源：Martin Zweig, Breadth Thrust Indicator——BTI <40% 超卖、>61.5% 超买
const ZWEIG_NOTE =
  "Martin Zweig 广量冲力(Breadth Thrust)：BTI <40% 超卖(机会)、>61.5% 超买(风险)；若10日内从<40%冲到>61.5% 为重大多头信号（1945年以来14次信号平均涨幅24%，来源：tradingsim / 360百科）";

function toneColor(tone: string): string {
  switch (tone) {
    case "opportunity": return "#16a34a";
    case "neutral": return "#6b7280";
    case "caution": return "#f59e0b";
    case "warning": return "#ea580c";
    case "danger": return "#dc2626";
    default: return "#6b7280";
  }
}

type Zone = Readonly<{ max: number; label: string; tone: string; note: string }>;

function findZone(value: number | null, zones: readonly Zone[]): Zone {
  if (value == null) return zones[0];
  return zones.find((z) => value <= z.max) ?? zones[zones.length - 1];
}

/** 短期/中期宽度着色（>85红 / <15绿 / 中间灰） */
function shortBreadthTone(v: number | null): string {
  if (v == null) return "neutral";
  if (v >= 85) return "danger";
  if (v <= 15) return "opportunity";
  return "neutral";
}

/** 长期宽度着色（>50绿 / <50红） */
function longBreadthTone(v: number | null): string {
  if (v == null) return "neutral";
  return v >= 50 ? "opportunity" : "danger";
}

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
  // 优先取全A(CN_ALL_A) 与 标普500(SP500)
  const cnAll = panels.find((p) => p.market_id === "CN_ALL_A") ?? null;
  const spx = panels.find((p) => p.market_id === "SP500") ?? null;
  const primaryPanels = [cnAll, spx].filter(Boolean) as GlobalPanel[];

  return (
    <section className={`macro-snapshot market-breadth-snapshot${expanded ? " expanded" : ""}`}>
      <button
        type="button"
        className="macro-head"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        <span className="macro-chevron">{expanded ? "▾" : "▸"}</span>
        <span className="macro-title">市场宽度 + 情绪</span>
        <span className="macro-badges">
          {cnAll?.breadth_50 != null && (
            <span className={`macro-chip ${shortBreadthTone(cnAll.breadth_50)}`} title="全A 50日宽度">
              全A50 {fmtPct(cnAll.breadth_50)}
            </span>
          )}
          {cnAll?.breadth_200 != null && (
            <span className={`macro-chip ${longBreadthTone(cnAll.breadth_200)}`} title="全A 200日宽度">
              全A200 {fmtPct(cnAll.breadth_200)}
            </span>
          )}
        </span>
        <span className="macro-toggle">{expanded ? "收起" : "展开分析"}</span>
      </button>

      {/* ---- 紧凑模式：各市场宽度小卡 ---- */}
      {!expanded && !isLoading && !error && (
        <div className="macro-compact">
          {primaryPanels.map((p) => (
            <BreadthMiniCard key={p.market_id} panel={p} />
          ))}
        </div>
      )}

      {isLoading && !data && <div className="loading">正在加载市场宽度…</div>}
      {error && <div className="fund-errors">市场宽度加载失败</div>}

      {/* ---- 展开模式：趋势图 + 阈值说明 ---- */}
      {expanded && primaryPanels.length > 0 && (
        <div className="macro-expanded">
          <div className="breadth-trends">
            {cnAll && (
              <BreadthTrendChart marketId="CN_ALL_A" displayName={cnAll.display_name} />
            )}
            {spx && (
              <BreadthTrendChart marketId="SP500" displayName={spx.display_name} />
            )}
          </div>
          <div className="macro-zones">
            <h5>📊 判断依据与信息来源</h5>

            <div className="zone-block">
              <strong>短期/中期宽度（20日、50日）</strong>
              <ol className="zone-levels">
                {SHORT_BREADTH_ZONES.map((z) => (
                  <li key={z.label} style={{ color: toneColor(z.tone) }}>
                    {z.label}{z.max !== Infinity ? `（≤ ${z.max}%）` : ""}：{z.note}
                  </li>
                ))}
              </ol>
            </div>

            <div className="zone-block">
              <strong>长期宽度（200日）</strong>
              <ol className="zone-levels">
                {LONG_BREADTH_ZONES.map((z) => (
                  <li key={z.label} style={{ color: toneColor(z.tone) }}>
                    {z.label}{z.max !== Infinity ? `（≤ ${z.max}%）` : ""}：{z.note}
                  </li>
                ))}
              </ol>
            </div>

            <div className="zone-block">
              <strong>Zweig 广量冲力（整体解读）</strong>
              <p className="zone-note">{ZWEIG_NOTE}</p>
            </div>

            <div className="zone-block">
              <strong>投资者情绪（待接入）</strong>
              <p className="zone-note">
                AAII 散户情绪（±25% 极值）、NAAIM 机构情绪（40%/100%）— 第二批接入（周报数据需配置）。
                数据来源：美国散户协会 AAII 周报、NAAIM 机构敞口调查。
              </p>
            </div>

            <div className="macro-disclaimer">
              ⚠️ 以上阈值为市场宽度分析经典框架与券商研报惯例的综合归纳，非交易指令。
              市场宽度反映「上涨家数占比」，用于判断行情广度与健康度；
              当前数值来源：项目内建 <code>/market-context/global-strip</code> 接口，
              趋势序列来源：<code>/market-context/breadth-history</code> 接口
              （后端已算好并持久化，前端零计算）。
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

/* ---- 紧凑小卡 ---- */
function BreadthMiniCard({ panel }: { panel: GlobalPanel }) {
  const b50Zone = findZone(panel.breadth_50, SHORT_BREADTH_ZONES);
  const b200Zone = findZone(panel.breadth_200, LONG_BREADTH_ZONES);
  return (
    <div className="macro-card breadth-mini">
      <div className="macro-head">
        <span className="macro-name">{panel.display_name} 市场宽度</span>
        <span className="macro-period">{panel.updated_at?.slice(0, 10)}</span>
      </div>
      <div className="breadth-row">
        <span className="b-label">20 日</span>
        <span className={`b-val ${shortBreadthTone(panel.breadth_20)}`}>
          {fmtPct(panel.breadth_20)}
          {panel.breadth_20_delta_5 != null && (
            <small className="b-delta">{fmtDelta(panel.breadth_20_delta_5)}</small>
          )}
        </span>
      </div>
      <div className="breadth-row">
        <span className="b-label">50 日</span>
        <span className={`b-val ${shortBreadthTone(panel.breadth_50)}`}>
          {fmtPct(panel.breadth_50)}
          {panel.breadth_50_delta_5 != null && (
            <small className="b-delta">{fmtDelta(panel.breadth_50_delta_5)}</small>
          )}
        </span>
      </div>
      <div className="breadth-row">
        <span className="b-label">200 日</span>
        <span className={`b-val ${longBreadthTone(panel.breadth_200)}`}>{fmtPct(panel.breadth_200)}</span>
      </div>
      <div className="macro-note">
        50日 {b50Zone.label.split("（")[0]} · 200日 {b200Zone.label.split("（")[0]}
      </div>
      {panel.alerts?.length > 0 && (
        <div className="breadth-alerts">
          {panel.alerts.map((a, i) => (
            <div key={i} className={a.level === "reversal" ? "up" : ""}>
              · {a.title}{a.desc ? `：${a.desc}` : ""}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
