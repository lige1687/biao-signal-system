import { useQuery } from "@tanstack/react-query";
import "./erpEffectSummary.css";

type EffectRow = {
  side: "upper" | "lower"; n: number; positiveN: number; negativeN: number;
  meanReturn: number; baselineReturn: number; matchedN: number;
  matchedReturn: number | null; increment: number | null; incrementInterval: [number, number] | null;
};
type EventOutcome = {
  date: string; side: "upper" | "lower"; entryDate: string; exitDate: string;
  returnPct: number; minPct: number; maxPct: number;
};
type EffectData = {
  schemaVersion: 1; asOf: string; summary: string; horizon: number;
  rows: EffectRow[]; events: EventOutcome[];
};
const pct = (n: number | null) => n === null ? "不可估" : `${n > 0 ? "+" : ""}${n.toFixed(1)}%`;
const pp = (n: number | null) => n === null ? "不可估" : `${n > 0 ? "+" : ""}${n.toFixed(1)}个百分点`;

export default function ErpEffectSummary({ selectedDate }: { selectedDate: string | null }) {
  const result = useQuery<EffectData>({
    queryKey: ["erpBandEffect", "20261101"], staleTime: Infinity, retry: false,
    queryFn: async () => {
      const response = await fetch("/research/erp-bands/evaluation.json");
      if (!response.ok) throw new Error("效果资料暂时无法读取");
      const data = await response.json();
      if (data.schemaVersion !== 1 || !Array.isArray(data.rows) || !Array.isArray(data.events)) throw new Error("效果资料格式不符");
      return data;
    },
  });
  if (result.isPending) return <p className="erp-effect-note" role="status">历史检验读取中…</p>;
  if (result.isError) return <p className="erp-effect-note" role="status">历史检验暂不可用。<button type="button" onClick={() => void result.refetch()}>重试</button></p>;
  const data = result.data;
  const event = data.events.find((item) => item.date === selectedDate);
  return <section className="erp-effect" aria-label="股债轨道历史效果">
    {selectedDate && <div className="erp-effect-event">
      <strong>这次穿轨之后 · 沪深300</strong>
      {event ? <><span>{event.entryDate}—{event.exitDate}，{data.horizon}个交易日</span>
        <span>期末涨跌 <b>{pct(event.returnPct)}</b></span>
        <span>期间最低 <b>{pct(event.minPct)}</b> / 最高 <b>{pct(event.maxPct)}</b></span></>
        : <span>没有完整的后续{data.horizon}个交易日，暂不评价。</span>}
    </div>}
    <div className="erp-effect-title"><strong>历史上有用吗？</strong><span>沪深300 · 随后约3个月</span></div>
    <p>{data.summary}</p>
    <div className="erp-effect-table-wrap"><table><caption className="erp-effect-sr">沪深300穿轨后63交易日价格表现</caption>
      <thead><tr><th scope="col">首次穿轨</th><th scope="col">后来涨 / 跌</th><th scope="col">平均涨跌</th></tr></thead>
      <tbody>{data.rows.map((row) => <tr key={row.side}><th scope="row">{row.side === "upper" ? "上穿上轨" : "下穿下轨"}<small>{row.n}次</small></th>
        <td>{row.positiveN} / {row.negativeN}次</td><td>{pct(row.meanReturn)}</td></tr>)}</tbody>
    </table></div>
    <details><summary>比只看价格多了多少信息？</summary>
      {data.rows.map((row) => <p key={row.side}><b>{row.side === "upper" ? "上轨" : "下轨"}</b>：相似价格状态的对照平均{pct(row.matchedReturn)}，穿轨组实际涨幅相差{pp(row.increment)}（{row.matchedN}次可比）。
        {row.side === "lower" && "下轨后平均更涨，未支持顶部提示。"}
        {row.incrementInterval && <>差值的95%重抽样区间：{pp(row.incrementInterval[0])}至{pp(row.incrementInterval[1])}。</>}</p>)}
      <p>按此前3个月涨跌、200日均线位置和历史时期分组比较；同组日期仍有差异。区间按两年一组重抽样，样本少、事件重叠，不能视作未来概率。</p>
      <a href="/library?report=docs%2Fexperiments%2Fequity-bond-bands-effect-2026-11-01.md">查看完整检验与反例</a>
    </details>
    <p className="erp-effect-note">统计从穿轨后的下一交易日收盘起算；期间高低相对该收盘价。历史周频、当前版本数据，截至{data.asOf}，涨跌次数不等于顶底命中率。</p>
  </section>;
}
