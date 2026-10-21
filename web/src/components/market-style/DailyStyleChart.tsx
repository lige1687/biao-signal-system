import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import * as echarts from "echarts";
import { request } from "../../api/client";

type DailySeries = { id: string; name: string; code: string; wealth: (number | null)[]; relative: (number | null)[];
  return_pct: number; excess_pp: number; max_drawdown_pct: number | null; volatility_pct: number | null; missing_points: number };
type DailyHistory = { available: boolean; error?: string; start: string; end: string; dates: string[];
  series: DailySeries[]; point_count: number; full_history_start: string; latest_source_date: string;
  stale: boolean; refresh_failed: boolean; retrieved_at: string; source_url: string; fingerprint: string };
const COLORS: Record<string, string> = { momentum: "#dc6f36", quality: "#286db5", value: "#8c5ba8", minimumVolatility: "#369781", world: "#657383" };
const ORDER = ["momentum", "quality", "value", "minimumVolatility", "world"];

function DailyLines({ data, mode }: { data: DailyHistory; mode: "relative" | "wealth" }) {
  const node = useRef<HTMLDivElement>(null);
  const instance = useRef<echarts.ECharts | null>(null);
  useEffect(() => {
    if (!node.current) return;
    const chart = echarts.init(node.current, undefined, { renderer: "svg" });
    instance.current = chart;
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(node.current);
    return () => { observer.disconnect(); chart.dispose(); instance.current = null; };
  }, []);
  useEffect(() => {
    const series = ORDER.map(id => data.series.find(item => item.id === id)!).filter(Boolean);
    instance.current?.setOption({
      animation: false,
      tooltip: { trigger: "axis", confine: true, valueFormatter: (v: unknown) => v == null ? "缺值" : Number(v).toFixed(2) },
      legend: { top: 0, type: "plain", textStyle: { fontSize: 12, color: "#344256" } },
      grid: { left: 40, right: 44, top: 66, bottom: 72, containLabel: true },
      xAxis: { type: "category", data: data.dates, boundaryGap: false,
        axisLabel: { fontSize: 12, color: "#344256", showMinLabel: true, showMaxLabel: true, hideOverlap: true, margin: 12 },
        axisTick: { show: false }, axisLine: { lineStyle: { color: "#9ca3af" } } },
      yAxis: { type: "value", scale: true, name: mode === "relative" ? "相对价值比（起点100）" : "累计价值（起点100）",
        nameTextStyle: { fontSize: 12, color: "#344256", align: "left" }, axisLabel: { fontSize: 12, color: "#344256" },
        splitLine: { lineStyle: { color: "#e2e8f0" } } },
      dataZoom: [{ type: "inside", start: 0, end: 100 }, { type: "slider", start: 0, end: 100, bottom: 8, height: 20, showDetail: false }],
      series: series.map(item => ({ name: item.name, type: "line", data: item[mode], showSymbol: false,
        connectNulls: false, smooth: false, lineStyle: { width: item.id === "world" ? 1.6 : 2,
          color: COLORS[item.id], type: item.id === "world" && mode === "relative" ? "dashed" : "solid" },
        itemStyle: { color: COLORS[item.id] }, emphasis: { focus: "series" } })),
    }, true);
  }, [data, mode]);
  return <div ref={node} className="style-daily-chart" role="img" aria-label={`四类风格${mode === "relative" ? "相对母指数" : "累计价值"}日线，${data.start}至${data.end}，${data.point_count}个观察日`} />;
}

export default function DailyStyleChart({ onBasisChange }: { onBasisChange?: (basis: string) => void }) {
  const [days, setDays] = useState(365);
  const [mode, setMode] = useState<"relative" | "wealth">("relative");
  const query = useQuery({ queryKey: ["marketStyleDailyHistory", days],
    queryFn: () => request<DailyHistory>(`/market-style/daily-history?days=${days}`), staleTime: 300_000, retry: false });
  const data = !query.isError && query.data?.available ? query.data : undefined;
  useEffect(() => { onBasisChange?.(JSON.stringify({ fingerprint: data?.fingerprint, end: data?.end,
    refresh_failed: data?.refresh_failed, stale: data?.stale, failed: query.isError })); }, [data, query.isError, onBasisChange]);
  return <div className="style-daily">
    <div className="style-history-header">
      <div><h3>{mode === "relative" ? "每天看：哪类风格跑赢母指数？" : "每天看：风格本身赚了多少？"}</h3>
        <p>{mode === "relative" ? "向上表示该段跑赢；高于100表示从所选起点累计领先。" : "同日起点设为100，比较含股息再投资后的累计变化。"}</p></div>
    </div>
    <div className="style-daily-controls">
      <div className="style-chart-modes" role="group" aria-label="日线图表视角">
        <button type="button" aria-pressed={mode === "relative"} className={mode === "relative" ? "is-active" : ""} onClick={() => setMode("relative")}>相对母指数</button>
        <button type="button" aria-pressed={mode === "wealth"} className={mode === "wealth" ? "is-active" : ""} onClick={() => setMode("wealth")}>累计路径</button>
      </div>
      <div className="style-chart-modes" role="group" aria-label="风格日线日期范围">
        {[{ days: 90, label: "3个月" }, { days: 365, label: "1年" }, { days: 1095, label: "3年" }].map(item =>
          <button key={item.days} type="button" aria-pressed={days === item.days} className={days === item.days ? "is-active" : ""} onClick={() => setDays(item.days)}>{item.label}</button>)}
      </div>
    </div>
    {query.isPending && <p role="status" className="style-daily-state">正在读取官方日收盘…</p>}
    {query.isError && <p role="alert" className="style-daily-state">日线请求失败，暂不画图；可重新载入页面重试。</p>}
    {query.data && !query.data.available && <p role="alert" className="style-daily-state">{query.data.error ?? "日线资料不足，未以年度点替代。"}</p>}
    {data && <>
      <p className="style-daily-date"><b>日收盘 · {data.start} — {data.end}</b><span>{data.point_count}个观察日 · 美元毛总回报</span></p>
      {(data.stale || data.refresh_failed) && <p className="ms-history-difference" role="alert">{data.refresh_failed ? "本次更新失败，展示上次已核资料。" : "来源日期已落后，暂不能称当前风格。"}请以图中资料日为准。</p>}
      <DailyLines data={data} mode={mode} />
      <p className="style-history-note">每个交易日一个真实观察点；拖动下方滑块可放大查看，比较起点保持不变。行业、持仓和估值仍见下方独立标日的月末资料。</p>
      <details className="style-history-method"><summary>日线口径、同期间风险与来源</summary>
        <p>母指数为MSCI World，四种风格均为原定义的全球发达市场指数；含股息再投资、未扣预提税和产品费用。相对线为同日起点归一后的风格价值除以母指数价值，再乘100；它不是收益差额的百分点。</p>
        <div className="style-daily-metrics" role="table" aria-label="所选日线期间收益与风险">
          <div role="row"><b role="columnheader">风格</b><b role="columnheader">收益</b><b role="columnheader">较母指数</b><b role="columnheader">最大下跌</b></div>
          {ORDER.map(id => data.series.find(s => s.id === id)!).filter(Boolean).map(s => <div role="row" key={s.id}>
            <span role="cell">{s.name}</span><span role="cell">{s.return_pct.toFixed(2)}%</span><span role="cell">{s.excess_pp > 0 ? "+" : ""}{s.excess_pp.toFixed(2)}点</span><span role="cell">{s.max_drawdown_pct == null ? "缺资料" : `${s.max_drawdown_pct.toFixed(2)}%`}</span>
          </div>)}
        </div>
        <p>差额的“点”指百分点；最大下跌只在所选期间内计算。缺值不填零、不插值、不跨缺口连线。最新共同日 {data.end}；已取历史起点 {data.full_history_start}。</p>
        <p><a href="https://app2.msci.com/products/index-data-search/" target="_blank" rel="noreferrer">MSCI 官方日末数据工具 ↗</a> · <a href={data.source_url} target="_blank" rel="noreferrer">本次原始导出 ↗</a> · 获取于 {new Date(data.retrieved_at).toLocaleString("zh-CN")}。页面被读取时按日检查更新，无后台定时采集或模型调用；数据仅供本机个人观察，持续使用及对外展示资格未作确认。</p>
      </details>
    </>}
  </div>;
}
