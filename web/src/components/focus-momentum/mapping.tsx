import { useEffect, useRef, useState } from "react";
import * as echarts from "echarts";
import type { FocusMomentumMapping, FocusMomentumMappingTarget } from "./data";

const pct = (value: number) => `${value > 0 ? "+" : ""}${(value * 100).toFixed(2)}%`;

function Scatter({ mapping, target }: { mapping: FocusMomentumMapping; target: FocusMomentumMappingTarget }) {
  const node = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!node.current) return;
    const chart = echarts.init(node.current);
    const all = mapping.targets.flatMap(t => t.points);
    const xMin = Math.floor(Math.min(0, ...all.map(p => p.focus * 100)) / 10) * 10;
    const xMax = Math.ceil(Math.max(0, ...all.map(p => p.focus * 100)) / 10) * 10;
    const yMax = Math.ceil(Math.max(...all.map(p => Math.abs(p.forwardReturn * 100))) / 10) * 10;
    chart.setOption({
      animation: false,
      aria: { enabled: true, description: `${target.label}的560个历史周观察点。横轴为焦点股过去20日动量，纵轴为之后20交易日指数涨跌，均为百分比。散点表示历史关联，不表示已验证预测。` },
      grid: { top: 40, right: 23, left: 58, bottom: 65 },
      xAxis: { type: "value", min: xMin, max: xMax, name: "焦点动量值 (%)", nameLocation: "middle", nameGap: 37, axisLabel: { formatter: "{value}%" }, splitLine: { lineStyle: { color: "#eff2f0" } } },
      yAxis: { type: "value", min: -yMax, max: yMax, name: "后20日指数涨跌 (%)", nameLocation: "end", nameTextStyle: { align: "left" }, axisLabel: { formatter: "{value}%" }, splitLine: { lineStyle: { color: "#eff2f0" } } },
      tooltip: {
        trigger: "item", confine: true,
        formatter: (raw: unknown) => {
          const item = raw as { dataIndex?: number; seriesType?: string };
          if (item.seriesType !== "scatter" || item.dataIndex == null) return "";
          const p = target.points[item.dataIndex];
          if (!p) return "";
          return `${p.date} → ${p.labelEnd}<br/>焦点动量：${pct(p.focus)}<br/>后20日指数涨跌：${pct(p.forwardReturn)}`;
        },
      },
      series: [{
        type: "scatter", name: target.label, symbolSize: 6,
        data: target.points.map(p => [p.focus * 100, p.forwardReturn * 100]),
        itemStyle: { color: "#397ca2", opacity: 0.5 },
        emphasis: { itemStyle: { opacity: 1, color: "#176f63", borderColor: "#fff", borderWidth: 1 } },
        markLine: { silent: true, symbol: "none", label: { show: false }, data: [
          { xAxis: 0, lineStyle: { color: "#8d9f98", type: "dashed" } },
          { yAxis: 0, lineStyle: { color: "#8d9f98", type: "dashed" } },
          { yAxis: target.baselineMean * 100, lineStyle: { color: "#b17c38", type: "solid", width: 1.5 } },
        ] },
      }],
    });
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(node.current);
    return () => { observer.disconnect(); chart.dispose(); };
  }, [mapping, target]);
  return <div className="fm-mapping-chart" ref={node} role="img" aria-label={`${target.label}模型值与后20交易日涨跌映射`} />;
}

export function FocusMomentumMappingPanel({ mapping }: { mapping: FocusMomentumMapping }) {
  const [selected, setSelected] = useState<"CSI300" | "CSI1000" | "US">("CSI300");
  const target = mapping.targets.find(t => t.target === selected);
  return <section className="fm-mapping" aria-label="焦点动量与市场后续表现映射">
    <header><h3>模型值 → 后续市场表现</h3><p>横轴是观察当日的焦点动量值，纵轴是之后20个交易日的指数涨跌；一个点代表一个周观察日。</p></header>
    <div className="fm-range" role="group" aria-label="映射市场">
      {mapping.targets.map(t => <button key={t.target} type="button" aria-pressed={selected === t.target} onClick={() => setSelected(t.target)}>A股 · {t.target === "CSI300" ? "沪深300" : "中证1000"}</button>)}
      <button type="button" aria-pressed={selected === "US"} onClick={() => setSelected("US")}>美股 · 资料待补</button>
    </div>
    {target ? <>
      <div className="fm-mapping-meta"><strong>{target.label}</strong><span>{target.points.length}个共同观察周 · {mapping.sampleStart} 至 {mapping.sampleEnd}</span><span className="fm-baseline-key">金色线：同样本整体平均 {pct(target.baselineMean)}</span></div>
      <Scatter mapping={mapping} target={target} />
      <p className="fm-mapping-note">左侧＝模型低于零，右侧＝高于零；上方＝之后指数上涨，下方＝下跌。灰虚线为零。两张A股图保持相同坐标范围，悬停可查日期与精确值。</p>
      <details className="fm-details"><summary>查看映射点数值（最近20个观察周）</summary><div className="fm-table-scroll"><table><thead><tr><th>观察日</th><th>焦点动量值</th><th>后20日指数涨跌</th><th>结果截止日</th></tr></thead><tbody>{target.points.slice(-20).reverse().map(p => <tr key={p.date}><th scope="row">{p.date}</th><td>{pct(p.focus)}</td><td>{pct(p.forwardReturn)}</td><td>{p.labelEnd}</td></tr>)}</tbody></table></div></details>
      <p className="fm-mapping-note">仅显示已成熟结果，最晚结果日为{mapping.labelEndMax}。相邻周的未来窗口重叠，这560个点不是560次独立试验；散点和整体均值是历史描述，不是预测概率或策略收益。固定300股模型与两条宽基作参照，宽基不是该股票池的母指数。</p>
    </> : <div className="fm-mapping-empty" role="status"><strong>美股映射尚无可用数据</strong><p>{mapping.us.reason}</p><p>需要美股自身的焦点动量序列，以及同日期、同期限的标普500等指数结果。这里保留缺口，不用A股模型值替代。</p></div>}
  </section>;
}
