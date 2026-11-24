import { useEffect, useState } from "react";

type Reading = { period: number; above: number; eligible: number; total: number; countPct: number; weightedPct: number; eligibleWeightPct: number; aboveWeightPct: number; excludedWeightPct: number };
type Index = { code: string; name: string; totalWeightPct: number; sourceUrl: string; readings: Reading[] };
type Snapshot = { observationDate: string; membershipDate: string; weightDate: string; weightRetrievedDate: string; priceVersion: string; indices: Index[] };
const PERIODS = [20, 50, 200] as const;
type Period = typeof PERIODS[number];
const COUNT_COLOR = "#2563eb";
const WEIGHT_COLOR = "#28806e";
function Bar({ value, label, color }: { value: number; label: string; color: string }) {
  return <svg className="star-weighted-bar" viewBox="0 0 100 9" role="img" aria-label={label} preserveAspectRatio="none">
    <title>{label}</title><rect x="0" y="1" width="100" height="7" fill="#e9eee9" />
    <rect x="0" y="1" width={Math.max(0, Math.min(100, value))} height="7" fill={color} />
    <path d="M50 0V9" stroke="#fff" strokeWidth="0.8" />
  </svg>;
}
const date = (value: unknown) => typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(value));
const near = (a: number, b: number, tolerance = 0.02) => Math.abs(a - b) <= tolerance;

export function isStarWeightedBreadth(value: unknown): value is Snapshot {
  if (!value || typeof value !== "object") return false;
  const d = value as Partial<Snapshot>;
  if (!date(d.observationDate) || !date(d.weightDate) || d.observationDate !== "2026-10-30" || d.weightDate !== d.observationDate
    || !date(d.membershipDate) || !date(d.weightRetrievedDate) || d.membershipDate !== "2026-11-11"
    || d.weightRetrievedDate !== "2026-11-15" || typeof d.priceVersion !== "string" || !d.priceVersion
    || !Array.isArray(d.indices) || d.indices.length !== 2) return false;
  return d.indices.every((index) => {
    if (!index || !["000688", "000698"].includes(index.code) || typeof index.name !== "string"
      || !Number.isFinite(index.totalWeightPct) || !near(index.totalWeightPct, 100, 0.01)
      || !index.sourceUrl?.startsWith("https://oss-ch.csindex.com.cn/")
      || !Array.isArray(index.readings) || index.readings.length !== 3) return false;
    return PERIODS.every((period) => {
      const r = index.readings.find((row) => row.period === period);
      if (!r || ![r.above, r.eligible, r.total].every(Number.isInteger)
        || ![r.countPct, r.weightedPct, r.eligibleWeightPct, r.aboveWeightPct, r.excludedWeightPct].every(Number.isFinite)
        || r.total !== (index.code === "000688" ? 50 : 100) || r.above < 0 || r.above > r.eligible || r.eligible <= 0 || r.eligible > r.total
        || r.eligibleWeightPct <= 0 || r.aboveWeightPct < 0 || r.aboveWeightPct > r.eligibleWeightPct || r.excludedWeightPct < 0
        || !near(r.eligibleWeightPct + r.excludedWeightPct, index.totalWeightPct, 0.005)
        || !near(r.countPct, 100 * r.above / r.eligible)
        || !near(r.weightedPct, 100 * r.aboveWeightPct / r.eligibleWeightPct)) return false;
      return true;
    });
  }) && new Set(d.indices.map((index) => index.code)).size === 2;
}

export function StarWeightedBreadthView({ data, initialPeriod = 50 }: { data: Snapshot; initialPeriod?: Period }) {
  const [period, setPeriod] = useState<Period>(initialPeriod);
  return <section className="star-weighted" aria-label="科创数量与权重宽度单日对照">
    <p className="star-breadth-date">{data.observationDate} 收盘 · 数量与有效权重</p>
    <div className="star-weighted-periods" role="group" aria-label="选择均线周期">
      {PERIODS.map(item => <button key={item} type="button" aria-pressed={period === item} onClick={() => setPeriod(item)}>{item}日</button>)}
    </div>
    <div className="star-weighted-grid">{data.indices.map(index => <section key={index.code} aria-label={`${index.name}单日对照`}>
      <h4>{index.name}</h4>
      <div className="star-weighted-scale"><span />{["数量", "权重"].map(series => <div key={series}><span>0</span><span>50</span><span>100%</span></div>)}</div>
      {index.readings.filter(r => r.period === period).map(r => <div className="star-weighted-row" key={r.period}>
        <strong>{r.period}日</strong>
        <div className="star-weighted-pair">
          <div><span><i className="star-count-key" />数量 <b>{r.countPct.toFixed(1)}%</b></span><Bar value={r.countPct} color={COUNT_COLOR} label={`${index.name}${r.period}日数量宽度${r.countPct.toFixed(1)}%，横轴0至100%`} /><small>{r.above}/{r.eligible} 只有效</small></div>
          <div><span><i className="star-weight-key" />权重 <b>{r.weightedPct.toFixed(1)}%</b></span><Bar value={r.weightedPct} color={WEIGHT_COLOR} label={`${index.name}${r.period}日有效权重宽度${r.weightedPct.toFixed(1)}%，横轴0至100%`} /><small>{r.aboveWeightPct.toFixed(3)} / {r.eligibleWeightPct.toFixed(3)}% 有效权重</small></div>
        </div>
      </div>)}
    </section>)}</div>
    <p className="star-breadth-note">数量是有效股票中站上均线的比例；权重是这些股票占有效权重的比例，未纳入者不计作跌破。</p>
    <p className="star-breadth-note">{data.weightDate} 单日权重，按 {data.membershipDate} 固定名单事后回看；历史当时成分与可得性未核。{data.weightRetrievedDate} 取得{data.indices.map((index, i) => <span key={index.code}>{i > 0 ? "、" : ""}<a href={index.sourceUrl} target="_blank" rel="noreferrer">{index.name}官方权重</a></span>)}。</p>
  </section>;
}

export default function StarWeightedBreadthSnapshot({ active = true, variant = "inline", onCollapse }: { active?: boolean; variant?: "inline" | "card"; onCollapse?: () => void }) {
  const [data, setData] = useState<Snapshot | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    if (!active || data) return;
    const controller = new AbortController();
    setError(false);
    fetch("/research/star-weighted-breadth-20261030.json", { signal: controller.signal })
      .then((response) => { if (!response.ok) throw new Error("unavailable"); return response.json() as Promise<unknown>; })
      .then((value) => { if (!isStarWeightedBreadth(value)) throw new Error("invalid data"); setData(value); })
      .catch(() => { if (!controller.signal.aborted) setError(true); });
    return () => controller.abort();
  }, [active, data]);
  const content = <div className="star-weighted-state">
    {error && <p role="alert">10月30日权重对照读取不可用。</p>}
    {active && !data && !error && <p role="status">正在读取10月30日权重对照…</p>}
    {data && <StarWeightedBreadthView data={data} />}
  </div>;
  if (variant === "card") return <article className="moa-item star-weighted-card" data-overview-card="star-weighted-breadth" aria-label="科创50与科创100权重宽度">
    <div className="moa-item-head"><h3>科创50 / 科创100 · 权重宽度</h3>{onCollapse && <button type="button" onClick={onCollapse}>收起</button>}</div>
    {content}
  </article>;
  return content;
}
