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

/* ------------------------------------------------------------------ */
/*  阈值与判断依据（全部标注来源）                                      */
/* ------------------------------------------------------------------ */

// 压力位 / 机会位（短期/中期宽度 20日、50日 极值框架）
// 来源（行业通用标准，非自定）：% 站上均线个股占比的广度极值以
// 「80% 超买 / 20% 超卖 / 50% 多空分界」为准——
// TradingView 官方宽度脚本、marketinout(%Above50MA)、thetrading.tools / pomegra.io
// 等多家 quant 框架均以此为准。华泰证券《A股择时之技术面指标测试》(2021) 亦建议
// 对 A 股采用默认/标准参数、警惕参数寻优过拟合，故 A股/美股共用此标准值。
// 注：Martin Zweig Breadth Thrust 的 40%/61.5% 针对「涨跌家数比率」(另一类指标)，
// 与本文「% 站上均线占比」不可混用，仅作整体解读参考。
const SHORT_BREADTH_ZONES = [
  { max: 20, label: "机会位（超卖）", tone: "opportunity", note: "≤20%：广度过冷、恐慌释放，短期反弹概率较高（压力/机会位框架）" },
  { max: 80, label: "中性区", tone: "neutral", note: "20–80%：常态区，宽度本身不构成极值信号" },
  { max: Infinity, label: "压力位（超买）", tone: "danger", note: "≥80%：广度过热、获利盘拥挤，阶段顶部 / 回调风险高（压力/机会位框架）" },
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

/** 短期/中期宽度着色（>80红 / <20绿 / 中间灰，行业通用 80/20 极值） */
function shortBreadthTone(v: number | null): string {
  if (v == null) return "neutral";
  if (v >= 80) return "danger";
  if (v <= 20) return "opportunity";
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
                <span className={`macro-chip ${shortBreadthTone(cnAll.breadth_50)}`} title="全A 50日宽度（真·MA上方占比）">
                  50日 {fmtPct(cnAll.breadth_50)}
                </span>
              )}
              {cnAll?.breadth_200 != null && (
                <span className={`macro-chip ${longBreadthTone(cnAll.breadth_200)}`} title="全A 200日宽度（真·MA上方占比）">
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

      {/* ---- 展开模式：趋势图 + 压力/机会位说明 ---- */}
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

            <div className="zone-block">
              <strong>压力位 / 机会位（20日、50日宽度）</strong>
              <ol className="zone-levels">
                {SHORT_BREADTH_ZONES.map((z) => (
                  <li key={z.label} style={{ color: toneColor(z.tone) }}>
                    {z.label}
                    {z.max !== Infinity ? `（${z.max === 20 ? "≤" : "20–"}${z.max}%）` : ""}
                    ：{z.note}
                  </li>
                ))}
              </ol>
            </div>

            <div className="zone-block">
              <strong>长期多空分界（200日宽度）</strong>
              <ol className="zone-levels">
                {LONG_BREADTH_ZONES.map((z) => (
                  <li key={z.label} style={{ color: toneColor(z.tone) }}>
                    {z.label}：{z.note}
                  </li>
                ))}
              </ol>
            </div>

            <div className="zone-block">
              <strong>经典广度理论（整体解读）</strong>
              <p className="zone-note">{ZWEIG_NOTE}</p>
            </div>

            <div className="macro-disclaimer">
              ⚠️ 宽度极值阈值采用行业通用标准：<b>80% 超买 / 20% 超卖 / 50% 多空分界</b>
              （% 站上均线个股占比框架）。出处：TradingView 官方宽度脚本、marketinout(%Above50MA)、
              thetrading.tools / pomegra.io 等多家 quant 框架；华泰证券《A股择时之技术面指标测试》(2021)
              亦建议对 A 股采用标准/默认参数、警惕参数过拟合，故 A股/美股共用此标准值。
              Martin Zweig Breadth Thrust 的 40%/61.5% 针对「涨跌家数比率」（另一类指标），
              与本文「% 站上均线占比」不可混用，仅作整体解读参考；以上为分析框架归纳，非交易指令。
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

/* ---- 当前所处位置（压力/机会/中性 + 长多/长空） ---- */
function CurrentPosition({ panel }: { panel: GlobalPanel }) {
  const b50Zone = findZone(panel.breadth_50, SHORT_BREADTH_ZONES);
  const b200Zone = findZone(panel.breadth_200, LONG_BREADTH_ZONES);
  return (
    <div className="zone-block current-position">
      <strong>当前位置</strong>
      <div className="current-position-row">
        <span>50日宽度 <b className={shortBreadthTone(panel.breadth_50)}>{fmtPct(panel.breadth_50)}</b></span>
        <span className={`macro-chip ${shortBreadthTone(panel.breadth_50)}`}>{b50Zone.label}</span>
      </div>
      <div className="current-position-row">
        <span>200日宽度 <b className={longBreadthTone(panel.breadth_200)}>{fmtPct(panel.breadth_200)}</b></span>
        <span className={`macro-chip ${longBreadthTone(panel.breadth_200)}`}>{b200Zone.label}</span>
      </div>
      <div className="current-position-row">
        <span>20日宽度 <b className={shortBreadthTone(panel.breadth_20)}>{fmtPct(panel.breadth_20)}</b></span>
        {panel.breadth_20_delta_5 != null && (
          <span className={`macro-chip ${shortBreadthTone(panel.breadth_20_delta_5 > 0 ? 50 : 50)}`}>
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
  const b50Zone = findZone(panel.breadth_50, SHORT_BREADTH_ZONES);
  const b200Zone = findZone(panel.breadth_200, LONG_BREADTH_ZONES);
  const positionLabel = b50Zone.label.split("（")[0];
  return (
    <div className="macro-card breadth-mini">
      <div className="macro-head">
        <span className="macro-name">{panel.display_name} 市场宽度</span>
        <span
          className={`macro-chip ${shortBreadthTone(panel.breadth_50)}`}
          title={b50Zone.note}
        >
          {positionLabel}
        </span>
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
