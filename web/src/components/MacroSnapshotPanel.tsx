import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import * as echarts from "echarts";
import { fundamentalsApi } from "../api/client";
import type { RatesResponse, RatesHistorySeries } from "../types";

/* ------------------------------------------------------------------ */
/*  阈值与判断依据（全部标注来源）                                      */
/* ------------------------------------------------------------------ */

/** 美国 10Y 国债收益率风险区间 */
const US_10Y_ZONES = [
  { max: 3.5, label: "宽松/衰退信号", tone: "opportunity", note: "< 3.5%：美债避险需求强，通常对应经济放缓或衰退预期（BofA Hartnett，2025.03）" },
  { max: 4.0, label: "中性偏松", tone: "neutral", note: "3.5–4.0%：货币政策偏鸽，对股市估值压力有限" },
  { max: 4.5, label: "甜蜜点区间", tone: "caution", note: "4.0–4.5%：Morgan Stanley 称为美股估值「甜蜜点」（2025.01）" },
  { max: 4.75, label: "压力区", tone: "warning", note: "4.5–4.75%：Evercore ISI 指出突破此区将导致「更长更深的调整」（2024.12）" },
  { max: Infinity, label: "危险区", tone: "danger", note: "> 5.0%：Evercore ISI 警戒线，对周期性牛市构成重大威胁；2018年触发点为 3%，本轮周期阈值上移至 5%" },
] as const;

/** 中国 10Y 国债收益率风险区间 */
const CN_10Y_ZONES = [
  { max: 1.8, label: "极度宽松/资产荒", tone: "opportunity", note: "< 1.8%：10Y 破「2」进入 1 字头时代（2024.12），资产荒加剧，权益相对性价比提升（招商策略）" },
  { max: 2.2, label: "合理区间", tone: "neutral", note: "1.8–2.2%：平安理财预期 2025 年运行区间；开源证券 H2 目标 1.9–2.2%（DR007+40~70bp 历史中枢）" },
  { max: 2.5, label: "偏紧缩", tone: "caution", note: "2.2–2.5%：若通胀正常化 DR007 回升至 1.8%，对应 10Y 或达 2.5%（开源证券）" },
  { max: Infinity, label: "明显收紧", tone: "warning", note: "> 2.5%：货币政策转向收紧信号，对成长股估值构成压制" },
] as const;

/** 两融余额风险区间（单位：万亿元，辅助口径；标准风险口径为占流通市值比） */
const MARGIN_ZONES = [
  { max: 1.5, label: "低杠杆/情绪谨慎", tone: "caution", note: "< 1.5万亿：市场参与度低，可能处于底部区域但也反映信心不足" },
  { max: 2.2, label: "正常区间", tone: "neutral", note: "1.5–2.2万亿：历史常态区间；2015 年峰值 2.27 万亿" },
  { max: 2.8, label: "偏高但可控", tone: "warning", note: "2.2–2.8万亿：绝对值偏高，风险以占流通市值比为准（近一年约 2.1–2.9%）" },
  { max: Infinity, label: "警戒线附近", tone: "danger", note: "> 2.8万亿：绝对值创历史新高，需结合占流通市值比判断（占比 > 3.5% 才进入 2015 式警戒区，当时 4.2–4.7%）" },
] as const;

/** 10-2 利差（收益率曲线）解读 */
function interpretSpread(spread: number | null): { label: string; tone: string; note: string } {
  if (spread == null) return { label: "数据缺失", tone: "neutral", note: "" };
  if (spread < 0) return { label: "倒挂（衰退预警）", tone: "danger", note: "2Y > 10Y 收益率倒挂，历史上 2000/2007 年倒挂后均出现经济衰退（陈新燊，星岛日报 2025.06）" };
  if (spread < 25) return { label: "极度平坦", tone: "warning", note: "利差 < 25bp，曲线趋平预示增长放缓；2025年5月收窄至约 5bp 接近倒挂" };
  if (spread < 50) return { label: "平坦", tone: "caution", note: "利差 25–50bp，市场对未来增长预期偏保守" };
  return { label: "正常陡峭", tone: "neutral", note: "利差 > 50bp，正常的向上倾斜收益率曲线" };
}

function zoneToneColor(tone: string): string {
  switch (tone) {
    case "opportunity": return "#16a34a"; // green
    case "neutral": return "#6b7280";     // gray
    case "caution": return "#f59e0b";     // amber
    case "warning": return "#ea580c";      // orange
    case "danger": return "#dc2626";       // red
    default: return "#6b7280";
  }
}

function findZone(value: number | null, zones: readonly Readonly<{ max: number; label: string; tone: string; note: string }>[]) {
  if (value == null) return zones[0];
  return zones.find((z) => value <= z.max) ?? zones[zones.length - 1];
}

/* 各指标趋势图的分界线（风险/机会边界），与上方阈值框架一致 */
type MarkLine = { y: number; label: string; color: string };
const METRIC_MARKLINES: Record<string, MarkLine[]> = {
  us_10y: [
    { y: 3.5, label: "3.5 宽松", color: "#16a34a" },
    { y: 4.5, label: "4.5 甜蜜点", color: "#f59e0b" },
    { y: 5.0, label: "5.0 危险", color: "#dc2626" },
  ],
  cn_10y: [
    { y: 1.8, label: "1.8 资产荒", color: "#16a34a" },
    { y: 2.2, label: "2.2 合理", color: "#6b7280" },
    { y: 2.5, label: "2.5 收紧", color: "#f59e0b" },
  ],
  cn_us_spread_10y: [
    { y: 0, label: "0 多空分界", color: "#6b7280" },
    { y: -1, label: "-1 深度倒挂", color: "#dc2626" },
  ],
  vix: [
    { y: 15, label: "15 低波动", color: "#16a34a" },
    { y: 20, label: "20 正常", color: "#6b7280" },
    { y: 30, label: "30 恐慌", color: "#dc2626" },
  ],
  margin_rzrqye: [
    { y: 15000, label: "1.5万亿", color: "#f59e0b" },
    { y: 22000, label: "2.2万亿", color: "#6b7280" },
    { y: 28000, label: "2.8万亿", color: "#dc2626" },
  ],
};

/* ------------------------------------------------------------------ */
/*  组件                                                                  */
/* ------------------------------------------------------------------ */

interface Props {
  data: RatesResponse | null;
  isLoading?: boolean;
}

export default function MacroSnapshotPanel({ data, isLoading }: Props) {
  const [expanded, setExpanded] = useState(false);

  // 展开时才拉历史趋势（避免默认加载）
  const { data: history, isLoading: historyLoading, isError: historyError } = useQuery({
    queryKey: ["fundamentalsRatesHistory", 730],
    queryFn: () => fundamentalsApi.ratesHistory(730),
    enabled: expanded,
    staleTime: 30 * 60_000,
  });

  const t = data?.treasury;
  const m = data?.margin;
  const us10y = t?.us.cn_10y ?? null;
  const cn10y = t?.cn.cn_10y ?? null;
  const usSpread = t?.us.us_10_2_spread ?? null;
  const marginWanYi = m?.rzrqye_yi != null ? m.rzrqye_yi / 10000 : null;

  const usZone = findZone(us10y, US_10Y_ZONES);
  const cnZone = findZone(cn10y, CN_10Y_ZONES);
  const marginZone = findZone(marginWanYi, MARGIN_ZONES);
  const spreadInterp = interpretSpread(usSpread);

  return (
    <section className={`macro-snapshot${expanded ? " expanded" : ""}`}>
      {/* ---- 折叠头（紧凑模式也显示核心数字） ---- */}
      <button
        type="button"
        className="macro-head"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        <span className="macro-chevron">{expanded ? "▾" : "▸"}</span>
        <span className="macro-title">宏观快照</span>
        <span className="macro-badges">
          {us10y != null && (
            <span className={`macro-chip ${usZone.tone}`} title={usZone.note}>
              美10Y {us10y.toFixed(1)}%
            </span>
          )}
          {cn10y != null && (
            <span className={`macro-chip ${cnZone.tone}`} title={cnZone.note}>
              中10Y {cn10y.toFixed(1)}%
            </span>
          )}
          {marginWanYi != null && (
            <span className={`macro-chip ${marginZone.tone}`} title={marginZone.note}>
              两融 {marginWanYi.toFixed(1)}万亿
            </span>
          )}
        </span>
        <span className="macro-toggle">{expanded ? "收起" : "展开分析"}</span>
      </button>

      {/* ---- 紧凑模式：两张小卡 ---- */}
      {!expanded && (
        <div className="macro-compact">
          {/* 中美国债收益率表 */}
          <div className="macro-card">
            <h4>中美国债收益率</h4>
            <span className="macro-date">
              中国 {t?.as_of_cn ?? "--"} · 美国 {t?.as_of_us ?? "--"}
            </span>
            <table className="macro-table">
              <thead>
                <tr>
                  <th>期限</th><th>中国 %</th><th>美国 %</th>
                </tr>
              </thead>
              <tbody>
                {[["2年", t?.cn.cn_2y, t?.us.us_2y] as const,
                  ["5年", t?.cn.cn_5y, t?.us.us_5y] as const,
                  ["10年", t?.cn.cn_10y, t?.us.us_10y] as const,
                  ["30年", t?.cn.cn_30y, t?.us.us_30y] as const,
                  ["10-2利差", t?.cn.cn_10_2_spread, t?.us.us_10_2_spread] as const,
                ].map(([label, cn, us]) => (
                  <tr key={String(label)}>
                    <td>{label}</td>
                    <td>{cn == null ? "—" : Number(cn).toFixed(3)}</td>
                    <td>{us == null ? "—" : Number(us).toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 两融余额 */}
          <div className="macro-card">
            <h4>两融余额（沪深）</h4>
            <span className="macro-date">{m?.date ?? "--"}</span>
            <div className="margin-big">
              {marginWanYi != null ? `${marginWanYi.toFixed(2)}万亿` : "暂不可用"}
            </div>
            {m && (
              <div className="margin-detail">
                占流通市值 {m.rzyezb_pct != null ? `${m.rzyezb_pct.toFixed(2)}%` : "-"}
                {" · "}融资 {m.rzye_yi != null ? `${m.rzye_yi.toFixed(0)}亿` : "—"}
                {" · "}融券 {m.rqye_yi != null ? `${m.rqye_yi.toFixed(0)}亿` : "—"}
                {" · "}买入 {m.buy_yi != null ? `${m.buy_yi.toFixed(0)}亿` : "—"}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ---- 展开模式：趋势图 + 阈值说明 ---- */}
      {expanded && (
        <div className="macro-expanded">
          <div className="breadth-trends">
            {history && Object.entries(history.series).map(([key, s]) => (
              <MacroTrendChart key={key} series={s} markLines={METRIC_MARKLINES[key] ?? []} />
            ))}
            {historyLoading && <div className="loading">加载历史趋势…</div>}
            {historyError && <div className="fund-errors">趋势数据加载失败</div>}
            {!historyLoading && !historyError && !history && (
              <div className="muted">暂无历史（利率数据源未返回序列）</div>
            )}
          </div>

          <div className="macro-zones">
            <h5>📊 判断依据与信息来源</h5>

            <div className="zone-block">
              <strong style={{ color: zoneToneColor(usZone.tone) }}>
                美 10Y 当前 {us10y != null ? `${us10y.toFixed(2)}%` : "—"} → {usZone.label}
              </strong>
              <p className="zone-note">{usZone.note}</p>
              <ol className="zone-levels">
                {US_10Y_ZONES.map((z) => (
                  <li key={z.label} style={{ color: zoneToneColor(z.tone) }}>
                    {z.label}{z.max !== Infinity ? `（≤ ${z.max}%）` : ""}：{z.note}
                  </li>
                ))}
              </ol>
            </div>

            <div className="zone-block">
              <strong style={{ color: zoneToneColor(cnZone.tone) }}>
                中 10Y 当前 {cn10y != null ? `${cn10y.toFixed(2)}%` : "—"} → {cnZone.label}
              </strong>
              <p className="zone-note">{cnZone.note}</p>
              <ol className="zone-levels">
                {CN_10Y_ZONES.map((z) => (
                  <li key={z.label} style={{ color: zoneToneColor(z.tone) }}>
                    {z.label}{z.max !== Infinity ? `（≤ ${z.max}%）` : ""}：{z.note}
                  </li>
                ))}
              </ol>
            </div>

            <div className="zone-block">
              <strong style={{ color: zoneToneColor(marginZone.tone) }}>
                两融余额 当前 {marginWanYi != null ? `${marginWanYi.toFixed(1)} 万亿` : "—"} → {marginZone.label}
              </strong>
              <p className="zone-note">{marginZone.note}</p>
              <ol className="zone-levels">
                {MARGIN_ZONES.map((z) => (
                  <li key={z.label} style={{ color: zoneToneColor(z.tone) }}>
                    {z.label}{z.max !== Infinity ? `（≤ ${z.max} 万亿）` : ""}：{z.note}
                  </li>
                ))}
              </ol>
            </div>

            <div className="zone-block">
              <strong style={{ color: zoneToneColor(spreadInterp.tone) }}>
                美 10-2 利差 当前 {usSpread != null ? `${usSpread.toFixed(3)}%` : "—"} → {spreadInterp.label}
              </strong>
              <p className="zone-note">{spreadInterp.note}</p>
            </div>

            <div className="macro-disclaimer">
              ⚠️ 以上阈值为研究机构公开观点的综合归纳，非交易指令。不同经济周期下阈值会漂移，
              仅作「当前处于什么环境」的参考框架。当前数值来源：<code>/fundamentals/rates</code>；
              趋势序列来源：<code>/fundamentals/rates-history</code>（历史从既有数据源取回，前端零计算）。
            </div>
          </div>
        </div>
      )}

      {isLoading && !data && <div className="loading">正在加载宏观数据…</div>}
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  单指标趋势图（折线 + 分界线）                                        */
/* ------------------------------------------------------------------ */

function MacroTrendChart({
  series,
  markLines,
}: {
  series: RatesHistorySeries;
  markLines: MarkLine[];
}) {
  const chartRef = useRef<HTMLDivElement>(null);
  const instRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;
    const inst = echarts.init(chartRef.current, undefined, { renderer: "canvas" });
    instRef.current = inst;
    const ro = new ResizeObserver(() => inst.resize());
    ro.observe(chartRef.current);
    return () => {
      ro.disconnect();
      inst.dispose();
      instRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!instRef.current) return;
    instRef.current.setOption(buildMacroTrendOption(series, markLines), true);
  }, [series, markLines]);

  return (
    <div className="breadth-trend-card">
      <div className="breadth-trend-title">
        {series.label}（近 {series.dates.length} 日）
      </div>
      <div ref={chartRef} className="macro-chart" style={{ height: 220 }} />
    </div>
  );
}

function buildMacroTrendOption(
  series: RatesHistorySeries,
  markLines: MarkLine[],
): echarts.EChartsOption {
  return {
    tooltip: {
      trigger: "axis",
      valueFormatter: (v) => (v == null ? "—" : `${Number(v).toFixed(2)}${series.unit}`),
    },
    grid: { left: 46, right: 16, top: 28, bottom: 24 },
    xAxis: {
      type: "category",
      data: series.dates,
      boundaryGap: false,
      axisLabel: { fontSize: 10, color: "#6b7280", hideOverlap: true },
      axisLine: { lineStyle: { color: "#d6dde6" } },
    },
    yAxis: {
      type: "value",
      scale: true,
      axisLabel: { fontSize: 10, color: "#6b7280" },
      splitLine: { lineStyle: { color: "#eef1f5" } },
    },
    series: [
      {
        name: series.label,
        type: "line",
        data: series.values,
        showSymbol: false,
        lineStyle: { width: 1.6, color: "#3a7bd5" },
        itemStyle: { color: "#3a7bd5" },
        markLine: {
          silent: true,
          symbol: "none",
          data: markLines.map((mk) => ({
            yAxis: mk.y,
            lineStyle: { color: mk.color, type: "dashed", width: 1 },
            label: {
              formatter: mk.label,
              color: mk.color,
              fontSize: 10,
              position: "insideEndTop",
            },
          })),
        },
      },
    ],
  };
}
