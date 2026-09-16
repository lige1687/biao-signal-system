import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import { FLAGSHIP_COMBOS } from "../data/flagshipCombos";

/**
 * 旗舰组合回测展示：净值+买卖点（上）与仓位占比面积图（下，0-100% 直读）。
 * 数据由 scripts/export_flagship_data.py 生成（静态，来源 docs/experiments）。
 */
export default function FlagshipSection() {
  return (
    <div style={{ margin: "14px 0" }}>
      <div className="section-title">旗舰组合 · 净值 / 买卖点 / 仓位占比</div>
      {FLAGSHIP_COMBOS.map((c) => <ComboChart key={c.name} idx={FLAGSHIP_COMBOS.indexOf(c)} />)}
    </div>
  );
}

function ComboChart({ idx }: { idx: number }) {
  const c = FLAGSHIP_COMBOS[idx];
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    const buy = c.events.filter((e) => e.t === "买").map((e) => ({
      coord: [e.i, c.equity[e.i]] as [number, number],
      value: "",
      symbolSize: 5,
      itemStyle: { color: "#34d399" },
    }));
    const sell = c.events.filter((e) => e.t === "卖").map((e) => ({
      coord: [e.i, c.equity[e.i]] as [number, number],
      value: "",
      symbolSize: 5,
      itemStyle: { color: "#f87171" },
    }));
    chart.setOption({
      animation: false,
      tooltip: { trigger: "axis", axisPointer: { type: "cross" } },
      axisPointer: { link: [{ xAxisIndex: "all" }] },
      legend: { top: 0, data: ["组合净值", "等权持有"], textStyle: { fontSize: 11 } },
      grid: [
        { left: 56, right: 20, top: 28, height: "48%" },
        { left: 56, right: 20, top: "68%", bottom: 46 },
      ],
      xAxis: [
        { type: "category", data: c.dates, gridIndex: 0, show: false },
        { type: "category", data: c.dates, gridIndex: 1,
          axisLabel: { fontSize: 10, interval: Math.floor(c.dates.length / 8) } },
      ],
      yAxis: [
        { type: "log", gridIndex: 0, axisLabel: { fontSize: 10 } },
        { type: "value", gridIndex: 1, min: 0, max: 100,
          axisLabel: { fontSize: 10, formatter: "{value}%" } },
      ],
      dataZoom: [{ type: "inside", xAxisIndex: [0, 1] }],
      series: [
        {
          name: "组合净值", type: "line", xAxisIndex: 0, yAxisIndex: 0,
          data: c.equity, showSymbol: false, lineStyle: { width: 2, color: "#34d399" },
          markPoint: { data: [...buy, ...sell], animation: false, silent: true,
            label: { show: false } },
        },
        {
          name: "等权持有", type: "line", xAxisIndex: 0, yAxisIndex: 0,
          data: c.hold, showSymbol: false, lineStyle: { width: 1.3, color: "#64748b" },
        },
        {
          name: "仓位占比", type: "line", xAxisIndex: 1, yAxisIndex: 1, data: c.pos,
          step: "end", showSymbol: false, lineStyle: { width: 1, color: "#38bdf8" },
          areaStyle: { color: "rgba(56,189,248,0.35)" },
        },
      ],
    });
    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);
    return () => { window.removeEventListener("resize", onResize); chart.dispose(); };
  }, [idx]);
  const kpi: React.CSSProperties = {
    background: "var(--bg-card)", borderRadius: 8, padding: "8px 12px",
    fontSize: 12, flex: 1, minWidth: 130,
  };
  return (
    <div style={{ background: "var(--bg-card)", borderRadius: 10, padding: "12px 14px",
      margin: "12px 0", border: "1px solid var(--border)" }}>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 8 }}>
        <div style={kpi}><b>{c.name}</b><div style={{ opacity: 0.6, fontSize: 11 }}>{c.desc}</div></div>
        <div style={kpi}>组合年化 <b style={{ color: "#34d399" }}>{c.ann}%</b>（持有 {c.annHold}%）</div>
        <div style={kpi}>最大回撤 <b style={{ color: "#f87171" }}>{c.dd}%</b>（持有 {c.ddHold}%）</div>
        <div style={kpi}>调仓 {c.nEvents} 次 · 绿点=买入 红点=卖出</div>
      </div>
      <div ref={ref} style={{ width: "100%", height: 430 }} />
    </div>
  );
}
