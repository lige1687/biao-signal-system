import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import "./sector-structure.css";

type Forecast = { reportId: string; reportDateInPdf: string; organizationCode: string; analystIds: string[]; target: string;
  epsCnyPerShare: number; attributableNetIncomeMillionCny: number; sourceShareCountConflict: boolean; pdfUrl: string };
type Comparison = { code: string; name: string; organization: string; target: string; from: Forecast; to: Forecast;
  epsChangeCnyPerShare: number; netIncomeChangeMillionCny: number; shareBasisChanged: boolean; sourceShareCountConflict: boolean };
type Samples = { schema: string; retrievalDate: string; target: string; sampleStocks: number; verifiedReports: number; comparisons: Comparison[] };
const finite = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
export function isEarningsRevisionSamples(value: unknown): value is Samples {
  if (!value || typeof value !== "object") return false;
  const d = value as Samples;
  if (d.schema !== "lei-earnings-report-revisions/1" || d.target !== "2027E" || !/^\d{4}-\d{2}-\d{2}$/.test(d.retrievalDate)
    || !Array.isArray(d.comparisons) || !d.comparisons.length || !Number.isInteger(d.sampleStocks) || !Number.isInteger(d.verifiedReports)) return false;
  const identities = new Map<string, string>();
  const reports = new Set<string>();
  for (const c of d.comparisons) {
    if (!c || !c.code || !c.name || !c.organization || c.target !== d.target || typeof c.shareBasisChanged !== "boolean"
      || typeof c.sourceShareCountConflict !== "boolean" || ![c.epsChangeCnyPerShare, c.netIncomeChangeMillionCny].every(finite)) return false;
    for (const f of [c.from, c.to]) {
      if (!f || f.target !== d.target || !f.reportId || !/^\d{4}-\d{2}-\d{2}$/.test(f.reportDateInPdf) || !Number.isFinite(Date.parse(f.reportDateInPdf))
        || !f.organizationCode || !Array.isArray(f.analystIds) || !f.analystIds.length || !f.analystIds.every(x => typeof x === "string")
        || ![f.epsCnyPerShare, f.attributableNetIncomeMillionCny].every(finite)
        || typeof f.sourceShareCountConflict !== "boolean" || !f.pdfUrl?.startsWith("https://pdf.dfcfw.com/pdf/")) return false;
      const identity = `${f.organizationCode}:${[...f.analystIds].sort().join(",")}`;
      if (identities.has(c.code) && identities.get(c.code) !== identity) return false;
      identities.set(c.code, identity); reports.add(f.reportId);
    }
    if (c.from.reportDateInPdf >= c.to.reportDateInPdf || Math.abs(c.to.epsCnyPerShare - c.from.epsCnyPerShare - c.epsChangeCnyPerShare) > .001
      || Math.abs(c.to.attributableNetIncomeMillionCny - c.from.attributableNetIncomeMillionCny - c.netIncomeChangeMillionCny) > .01) return false;
  }
  return identities.size === d.sampleStocks && reports.size === d.verifiedReports;
}

export function EarningsSampleView({ data, code }: { data: Samples; code: string }) {
  const comparisons = data.comparisons.filter(c => c.code === code);
  const first = comparisons[0];
  if (!first) return null;
  const reports = [...new Map(comparisons.flatMap(c => [c.from, c.to]).map(f => [f.reportId, f])).values()].sort((a, b) => a.reportDateInPdf.localeCompare(b.reportDateInPdf));
  return <>
    <p className="sector-date">{first.organization} · 同一研究团队 · 目标均为2027年</p>
    <table className="earnings-sample-table"><thead><tr><th>报告日</th><th>EPS（元/股）</th><th>归母净利（亿元）</th></tr></thead>
      <tbody>{reports.map(f => <tr key={f.reportId}><td><a href={f.pdfUrl} target="_blank" rel="noreferrer">{f.reportDateInPdf.slice(5)} ↗</a></td>
        <td>{f.epsCnyPerShare.toFixed(2)}</td><td>{(f.attributableNetIncomeMillionCny / 100).toFixed(2)}</td></tr>)}</tbody>
    </table>
    {comparisons.some(c => c.shareBasisChanged) && <p className="sector-note">期间股本口径有变化，每股预测与净利一起看。</p>}
    {comparisons.some(c => c.sourceShareCountConflict) && <p className="sector-note">原报告的股本数字存在不一致，EPS变化的分母解释仍待核。</p>}
    <p className="sector-note">{data.retrievalDate}事后取得 · 已核{data.sampleStocks}家公司、{data.verifiedReports}份研报；全指数修正广度及首次可得时间未知。</p>
  </>;
}

export default function EarningsRevisionSampleCard({ onCollapse }: { onCollapse: () => void }) {
  const [code, setCode] = useState("688008");
  const q = useQuery({ queryKey: ["earningsRevisionSamples", "20261115"], queryFn: async ({ signal }) => {
    const response = await fetch("/research/earnings-revisions-20261115.json", { signal, cache: "no-cache" });
    if (!response.ok) throw new Error("unavailable");
    const data: unknown = await response.json();
    if (!isEarningsRevisionSamples(data)) throw new Error("invalid");
    return data;
  }, staleTime: 60_000, retry: false });
  const stocks = q.data ? [...new Map(q.data.comparisons.map(c => [c.code, c.name])).entries()] : [];
  return <article className="moa-item" data-overview-card="earnings-revision-samples" aria-label="2027年盈利预测研报样例">
    <div className="moa-item-head"><h3>2027E盈利预测 · 研报样例</h3><button type="button" onClick={onCollapse}>收起</button></div>
    {q.isPending && <p role="status">正在读取已核研报…</p>}
    {q.isError && <p role="alert">研报样例暂不可读。</p>}
    {q.data && <><label className="sector-select">公司<select value={code} onChange={e => setCode(e.target.value)}>{stocks.map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>
      <EarningsSampleView data={q.data} code={code} /></>}
  </article>;
}
