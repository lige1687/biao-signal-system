import { useQuery } from "@tanstack/react-query";
import type { ErpSigma } from "./erpSensitivity";

type Row = { sigma: ErpSigma; side: "upper" | "lower"; n: number; riseN: number; fallN: number; mean: number };
const pct = (v: number) => `${v > 0 ? "+" : ""}${v.toFixed(1)}%`;
export default function ErpSensitivitySummary({ sigma }: { sigma: ErpSigma }) {
  const query = useQuery({ queryKey: ["erpSensitivity20261102"], staleTime: Infinity, retry: false,
    queryFn: async (): Promise<{ rows: Row[] }> => {
      const response = await fetch("/research/erp-bands/sensitivity.v1.json");
      if (!response.ok) throw new Error("灵敏度结果暂不可用");
      const result = await response.json();
      if (result.schemaVersion !== 1 || result.rows?.length !== 6) throw new Error("结果格式不符");
      return result;
    } });
  if (!query.data) return <p className="erp-effect-note">{query.isError ? "灵敏度检验资料暂不可用" : "灵敏度检验读取中…"}</p>;
  return <section className="erp-effect" aria-label="轨道灵敏度比较">
    <div className="erp-effect-title"><strong>{sigma}σ · 提示变多，有没有用？</strong><span>同一历史 · 随后63个交易日</span></div>
    <p>{sigma === 1 ? "1σ提示更多，但上穿后27次中有16次继续下跌；尚未显示可靠增量，不能当买点。" : sigma === 1.5 ? "1.5σ上穿有反弹线索，15次中仍有5次下跌；这是历史候选观察线。" : "2σ更少、更极端。样本少，过去7次上穿后上涨不代表今后必然上涨。"} 下轨尚未可靠地提示顶部。</p>
    <div className="erp-effect-table-wrap"><table><thead><tr><th>轨道</th><th>上穿后上涨</th><th>平均涨跌</th><th>下穿后下跌</th><th>平均涨跌</th></tr></thead><tbody>
      {([1, 1.5, 2] as const).map(k => { const up = query.data.rows.find(r => r.sigma === k && r.side === "upper")!; const down = query.data.rows.find(r => r.sigma === k && r.side === "lower")!;
        return <tr key={k} style={sigma === k ? { background: "#edf3fa" } : undefined}><th>{k}σ{sigma === k && " · 当前"}</th><td>{up.riseN}/{up.n}次</td><td>{pct(up.mean)}</td><td>{down.fallN}/{down.n}次</td><td>{pct(down.mean)}</td></tr>;
      })}
    </tbody></table></div>
    <p className="erp-effect-note">2008-11—2026-10的周频回看；从信号后下一交易日收盘计算。不同轨道的穿越日期不同，次数不能相减当新增独立机会。首页历史变化仍按2σ；图中可同时看1.5σ与2σ。</p>
    <details><summary>新增信息与依据</summary><p>在当时尚未到2σ、且此前涨跌和200日均线状态相似时，1.5σ上穿组随后涨幅比对照高约6.98个百分点（95%重抽样区间0.63至9.60）；1σ约高1.11个百分点（−2.60至5.49）。同一历史反复研究、样本少且重叠，尚无独立新样本确认。</p>
      <p>1σ、2σ有国信等机构图示依据；1.5σ仅标本地灵敏度检验，不能冒充机构通用机会线。</p>
      <a href="/library?report=docs%2Fexperiments%2Ferp-band-sensitivity-2026-11-02.md">完整比较、反例与不确定性 ↗</a></details>
  </section>;
}
