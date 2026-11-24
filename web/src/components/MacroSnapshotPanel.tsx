import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import * as echarts from "echarts";
import { fundamentalsApi } from "../api/client";
import type { RatesResponse, RatesHistorySeries } from "../types";
import { MARKLINES, SOURCE_NOTES, type MarkLine } from "./trend/zones";

/** 10年减2年国债收益率，接口单位为百分点；0只表示两期限收益率相等。 */
function describeSpread(spread: number | null): string {
  if (spread == null || !Number.isFinite(spread)) return "资料缺失";
  if (spread < 0) return "倒挂（10年低于2年）";
  if (spread > 0) return "正利差（10年高于2年）";
  return "两期限相等";
}

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
  const us10y = t?.us.us_10y ?? null;
  const cn10y = t?.cn.cn_10y ?? null;
  const usSpread = t?.us.us_10_2_spread ?? null;
  const marginWanYi = m?.rzrqye_yi != null ? m.rzrqye_yi / 10000 : null;

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
            <span className="macro-chip neutral" title={SOURCE_NOTES.us_10y}>
              美10Y {us10y.toFixed(1)}%
            </span>
          )}
          {cn10y != null && (
            <span className="macro-chip neutral" title={SOURCE_NOTES.cn_10y}>
              中10Y {cn10y.toFixed(1)}%
            </span>
          )}
          {marginWanYi != null && (
            <span className="macro-chip neutral" title={SOURCE_NOTES.margin_rzrqye}>
              两融 {marginWanYi.toFixed(1)}万亿
            </span>
          )}
        </span>
        <span className="macro-toggle">{expanded ? "收起" : "展开资料"}</span>
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
                  <th>期限</th><th>中国</th><th>美国</th>
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
                    <td>{cn == null ? "—" : `${Number(cn).toFixed(3)}${label === "10-2利差" ? "个百分点" : "%"}`}</td>
                    <td>{us == null ? "—" : `${Number(us).toFixed(3)}${label === "10-2利差" ? "个百分点" : "%"}`}</td>
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
                {" · "}融资买入 {m.buy_yi != null ? `${m.buy_yi.toFixed(0)}亿` : "—"}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ---- 展开模式：趋势图 + 指标口径 ---- */}
      {expanded && (
        <div className="macro-expanded">
          <div className="breadth-trends">
            {history && Object.entries(history.series).map(([key, s]) => (
              <MacroTrendChart key={key} series={s} markLines={MARKLINES[key] ?? []} />
            ))}
            {historyLoading && <div className="loading">加载历史趋势…</div>}
            {historyError && <div className="fund-errors">趋势数据加载失败</div>}
            {!historyLoading && !historyError && !history && (
              <div className="muted">暂无历史（利率数据源未返回序列）</div>
            )}
          </div>

          <div className="macro-zones">
            <h5>读数含义与资料来源</h5>

            <div className="zone-block">
              <strong>美国10年国债收益率：{us10y != null ? `${us10y.toFixed(2)}%` : "资料缺失"}</strong>
              <p className="zone-note">{SOURCE_NOTES.us_10y}</p>
            </div>

            <div className="zone-block">
              <strong>中国10年国债收益率：{cn10y != null ? `${cn10y.toFixed(2)}%` : "资料缺失"}</strong>
              <p className="zone-note">{SOURCE_NOTES.cn_10y}</p>
            </div>

            <div className="zone-block">
              <strong>两融余额：{marginWanYi != null ? `${marginWanYi.toFixed(2)}万亿元` : "资料缺失"}</strong>
              <p className="zone-note">{SOURCE_NOTES.margin_rzrqye}</p>
            </div>

            <div className="zone-block">
              <strong>美国10年减2年国债收益率：{usSpread != null ? `${usSpread.toFixed(3)}个百分点` : "资料缺失"}</strong>
              <p className="zone-note">{describeSpread(usSpread)}。0仅表示两期限收益率相等，不是股市方向线。</p>
            </div>

            <div className="macro-disclaimer">
              以上仅展示利率与融资读数，固定股市交易分界未经验证。当前数值来源：
              <code>/fundamentals/rates</code>；趋势序列来源：<code>/fundamentals/rates-history</code>。
            </div>
          </div>
        </div>
      )}

      {isLoading && !data && <div className="loading">正在加载宏观数据…</div>}
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  单指标趋势图（仅保留来源定义的参考线）                              */
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
        lineStyle: { width: 1.6, color: "#2563eb" },
        itemStyle: { color: "#2563eb" },
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
