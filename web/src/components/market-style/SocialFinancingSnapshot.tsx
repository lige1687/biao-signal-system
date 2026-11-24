import { useEffect, useState } from "react";
import "./social-financing.css";

type SocialFinancingData = {
  period: string; publishedAt: string; retrievedAt: string; status: string; unit: string;
  total: number; government: number; other: number; governmentShare: number; otherShare: number;
  totalYoy: number; governmentYoy: number; sourceUrl: string; sourceSha256: string;
};
type YoyRow = { period: string; totalStock: number | null; governmentStock: number | null; otherStock: number | null; priorOtherStock: number | null; otherYoyEstimate: number | null; totalYoyReported: number | null; governmentYoyReported: number | null };
type YoyData = { retrievedAt: string; historicalReleaseVersionKnown: false; sources: { label: string; url: string }[]; rows: YoyRow[] };

export function isSocialFinancingYoy(value: unknown): value is YoyData {
  if (!value || typeof value !== "object") return false;
  const d = value as Partial<YoyData>;
  if (d.retrievedAt !== "2026-11-15" || d.historicalReleaseVersionKnown !== false
    || !Array.isArray(d.sources) || d.sources.length !== 2
    || !d.sources.every((source) => source?.url?.startsWith("https://www.pbc.gov.cn/"))
    || !Array.isArray(d.rows) || d.rows.length !== 12) return false;
  return d.rows.every((row, i) => {
    if (row.period !== `2026-${String(i + 1).padStart(2, "0")}`) return false;
    const fields = [row.totalStock, row.governmentStock, row.otherStock, row.priorOtherStock, row.otherYoyEstimate, row.totalYoyReported, row.governmentYoyReported];
    if (i >= 10) return fields.every((n) => n === null);
    if (!fields.every((n) => typeof n === "number" && Number.isFinite(n))) return false;
    return row.totalStock! > 0 && row.governmentStock! >= 0 && row.priorOtherStock! > 0
      && Math.abs(row.totalStock! - row.governmentStock! - row.otherStock!) < 0.02
      && Math.abs((row.otherStock! / row.priorOtherStock! - 1) * 100 - row.otherYoyEstimate!) < 0.02;
  });
}

export function socialYoyLineSegments(rows: YoyRow[]) {
  const segments: { month: number; value: number }[][] = [];
  rows.forEach((row, i) => {
    if (row.otherYoyEstimate === null) return;
    if (i === 0 || rows[i - 1].otherYoyEstimate === null) segments.push([]);
    segments[segments.length - 1].push({ month: i, value: row.otherYoyEstimate });
  });
  return segments;
}

export function SocialFinancingYoyView({ data }: { data: YoyData }) {
  const latest = data.rows[9];
  const top = 8;
  const x = (month: number) => 43 + month * 28;
  const y = (value: number) => 142 - value / top * 116;
  return <section className="socfin-yoy" aria-label="政府债以外社融余额同比估算月线">
    <h4>政府债以外社融余额同比估算</h4>
    <p><strong>{latest.otherYoyEstimate?.toFixed(2)}%</strong><span> {latest.period}，按两份已舍入年表计算</span></p>
    <svg viewBox="0 0 380 176" role="img" aria-label="2026年1月至10月政府债以外社融余额同比估算，1月5.94%，10月5.24%；11月和12月暂无数据">
      {[0, 2, 4, 6, 8].map((tick) => <g key={tick}><line x1="43" x2="351" y1={y(tick)} y2={y(tick)} className={tick === 0 ? "socfin-axis" : "socfin-grid"} /><text x="35" y={y(tick) + 4} textAnchor="end">{tick}%</text></g>)}
      {socialYoyLineSegments(data.rows).map((segment, i) => <polyline key={i} className="socfin-yoy-line" points={segment.map((p) => `${x(p.month)},${y(p.value)}`).join(" ")} />)}
      {data.rows.map((row, i) => <g key={row.period}>{row.otherYoyEstimate !== null && <circle cx={x(i)} cy={y(row.otherYoyEstimate)} r="2.5" className="socfin-yoy-point"><title>{`${row.period}: ${row.otherYoyEstimate.toFixed(2)}%`}</title></circle>}{[0, 2, 4, 6, 8, 9, 10, 11].includes(i) && <text x={x(i)} y="161" textAnchor="middle">{i + 1}月</text>}</g>)}
    </svg>
    <p>11—12月暂无数据。10月同期总社融余额同比 {latest.totalYoyReported?.toFixed(1)}%，政府债余额同比 {latest.governmentYoyReported?.toFixed(1)}%；两项为央行公布的各自同比，不能相减求本图数值。</p>
    <p>2025、2026年表均于 {data.retrievedAt} 取得，历史各期原始发布与修订版本未知。差额含居民、国企等融资，并非当月新增。债务置换等结构变化可能影响读数，具体影响未拆分。</p>
    <p>资料：{data.sources.map((source, i) => <span key={source.url}>{i > 0 ? "、" : ""}<a href={source.url} target="_blank" rel="noreferrer">{source.label}</a></span>)}</p>
  </section>;
}

export function isSocialFinancingSnapshot(value: unknown): value is SocialFinancingData {
  if (!value || typeof value !== "object") return false;
  const d = value as Partial<SocialFinancingData>;
  const numbers = [d.total, d.government, d.other, d.governmentShare, d.otherShare, d.totalYoy, d.governmentYoy];
  if (!numbers.every((x) => typeof x === "number" && Number.isFinite(x))) return false;
  if (!d.period || !d.publishedAt || !d.retrievedAt || !d.status || d.unit !== "万亿元" || !d.sourceSha256) return false;
  if (!d.sourceUrl?.startsWith("https://www.pbc.gov.cn/")) return false;
  const total = d.total!, government = d.government!, other = d.other!;
  const governmentShare = d.governmentShare!, otherShare = d.otherShare!;
  return total > 0 && government >= 0 && government <= total && other >= 0 && Math.abs(total - government - other) < 0.02
    && governmentShare >= 0 && governmentShare <= 100 && otherShare >= 0 && otherShare <= 100
    && Math.abs(governmentShare + otherShare - 100) < 0.11 && Math.abs(governmentShare - government / total * 100) < 0.11;
}

export function SocialFinancingView({ data }: { data: SocialFinancingData }) {
  return <div className="socfin-view">
    <h4><time dateTime={data.period}>{data.period.replace("-", "年")}月末</time>社融存量结构（初步统计）</h4>
    <p>央行页面标示发布 {data.publishedAt}（A股收盘后）；本地取得 {data.retrievedAt}。当期为{data.status}。</p>
    <div className="socfin-numbers">
      <div><span>社融存量</span><strong>{data.total.toFixed(2)} 万亿元</strong><small>同比 {data.totalYoy.toFixed(1)}%</small></div>
      <div><span>政府债余额</span><strong>{data.government.toFixed(2)} 万亿元</strong><small>同比 {data.governmentYoy.toFixed(1)}%</small></div>
      <div><span>其他项目合计（差额计算）</span><strong>{data.other.toFixed(2)} 万亿元</strong><small>总量减政府债</small></div>
    </div>
    <div className="socfin-bar" role="img" aria-label={`政府债约${data.governmentShare.toFixed(1)}%，其他项目合计约${data.otherShare.toFixed(1)}%`}>
      <span className="socfin-bar-government" style={{ width: `${data.governmentShare}%` }} />
      <span className="socfin-bar-other" style={{ width: `${data.otherShare}%` }} />
    </div>
    <div className="socfin-legend"><span>政府债约 {data.governmentShare.toFixed(1)}%</span><span>其他项目约 {data.otherShare.toFixed(1)}%</span></div>
    <p>这是期末余额，不是当月新增融资。其他项目合计按已公布的总额减政府债计算，包含国企、居民等融资，不是民营信用或纯企业信用。</p>
    <p>同比各对应总存量和政府债余额，不能相减得到其他项目同比。比例根据已舍入的公布余额计算，仅作结构观察；本地快照不会自动更新。</p>
    <p>一起看：可与已发布的 PMI、利率和市场趋势对照，先核对各自的统计期及发布日期；社融不是当日股市资金流，也不是择时触发信号。</p>
    <p><a href={data.sourceUrl} target="_blank" rel="noreferrer">中国人民银行原文 ↗</a> · 页面标示时间不代表已核实全市场最早可得时刻。</p>
  </div>;
}

export default function SocialFinancingSnapshot() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<SocialFinancingData | null>(null);
  const [error, setError] = useState(false);
  const [yoy, setYoy] = useState<YoyData | null>(null);
  const [yoyError, setYoyError] = useState(false);

  useEffect(() => {
    if (!open || data) return;
    const controller = new AbortController();
    setError(false);
    fetch("/research/social-financing-20261115.json", { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("snapshot unavailable");
        return response.json() as Promise<unknown>;
      })
      .then((value) => {
        if (!isSocialFinancingSnapshot(value)) throw new Error("invalid snapshot");
        setData(value);
      })
      .catch(() => { if (!controller.signal.aborted) setError(true); });
    return () => controller.abort();
  }, [open, data]);

  useEffect(() => {
    if (!open || yoy) return;
    const controller = new AbortController();
    setYoyError(false);
    fetch("/research/social-financing-yoy-20261115.json", { signal: controller.signal })
      .then((response) => { if (!response.ok) throw new Error("unavailable"); return response.json() as Promise<unknown>; })
      .then((value) => { if (!isSocialFinancingYoy(value)) throw new Error("invalid data"); setYoy(value); })
      .catch(() => { if (!controller.signal.aborted) setYoyError(true); });
    return () => controller.abort();
  }, [open, yoy]);

  return <details className="socfin-snapshot" onToggle={(event) => setOpen(event.currentTarget.open)}>
    <summary>宏观背景：中国社融 · 月度观察</summary>
    {yoyError && <p role="alert">社融月度曲线读取不可用；下方单月结构仍可查看。</p>}
    {open && !yoy && !yoyError && <p role="status">正在读取社融月度曲线…</p>}
    {yoy && <SocialFinancingYoyView data={yoy} />}
    {error && <p role="alert">社融快照读取失败，请稍后重试。</p>}
    {open && !data && !error && <p role="status">正在读取社融快照…</p>}
    {data && <SocialFinancingView data={data} />}
  </details>;
}
