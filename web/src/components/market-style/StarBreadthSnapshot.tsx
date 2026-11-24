import { useEffect, useState, type ReactNode } from "react";
import MiniTrend from "../market-observation-alerts/MiniTrend";
import { BREADTH_LINES } from "../trend/zones";
import StarWeightedBreadthSnapshot from "./StarWeightedBreadthSnapshot";
import "./star-breadth.css";

type WindowReading = { above: number; eligible: number; total: number; percent: number | null };
type Observation = { date: string; windows: Record<string, WindowReading> };
type Comparison = {
  start: string; end: string; indexReturnPct: number; equalMeanReturnPct: number | null;
  outperformCount: number; eligible: number; total: number; outperformPct: number | null;
};
type Snapshot = {
  asOf: string;
  membershipDate: string;
  retrievedDate: string;
  indices: { code: string; name: string; observations: Observation[]; comparison?: Comparison }[];
};

const PERIODS = ["20", "50", "200"] as const;
const COLORS: Record<string, string> = { "20": BREADTH_LINES[0].color, "50": BREADTH_LINES[1].color, "200": BREADTH_LINES[2].color };

/** Display only the supplied dated snapshot; fixed members do not reconstruct historical index membership. */
export function StarBreadthView({ data }: { data: Snapshot }) {
  return <div className="star-breadth-view">
    <p className="star-breadth-date">{data.asOf} 收盘 · {data.membershipDate} 固定名单</p>
    <div className="star-breadth-legend" aria-label="均线周期图例">
      {PERIODS.map(period => <span key={period} style={{ color: COLORS[period] }}>● {period}日</span>)}
    </div>
    <div className="star-breadth-grid">{data.indices.map(index => {
      const rows = index.observations.slice(-60);
      const current = rows.find(row => row.date === data.asOf);
      const values50 = rows.map(row => row.windows["50"]?.percent).filter((value): value is number => typeof value === "number" && Number.isFinite(value));
      const low50 = values50.length ? Math.min(...values50) : null;
      const high50 = values50.length ? Math.max(...values50) : null;
      const references = low50 === null || high50 === null ? [] : [
        { name: "本段50日最低", color: "#398579", values: rows.map(() => low50), dashed: true },
        { name: "本段50日最高", color: "#a3825c", values: rows.map(() => high50), dashed: true },
      ];
      return <section className="star-breadth-index" key={index.code} aria-label={`${index.name}固定名单回看`}>
        <h4>{index.name}</h4>
        <div className="star-breadth-readings">{PERIODS.map(period => {
          const value = current?.windows[period];
          return <div key={period} className="star-breadth-reading" style={{ borderColor: COLORS[period] }}>
            <span>{period}日</span><strong>{value?.percent == null ? "—" : `${value.percent.toFixed(1)}%`}</strong>
            <small>{value ? `${value.above}/${value.eligible} 只有效` : "有效数待补"}</small>
          </div>;
        })}</div>
        <MiniTrend dates={rows.map(row => row.date)} percent showScale
          label={`${index.name}固定名单回看：20日、50日、200日均线上方比例，纵轴0%至100%`}
          lines={PERIODS.map(period => ({ name: `${period}日`, color: COLORS[period], values: rows.map(row => row.windows[period]?.percent ?? null) }))} references={references} />
        {low50 !== null && high50 !== null && <p className="star-breadth-range"><span>近{rows.length}日50日宽度：</span><span style={{ color: "#398579" }}>┄ 最低 {low50.toFixed(1)}%</span><span style={{ color: "#a3825c" }}>┄ 最高 {high50.toFixed(1)}%</span></p>}

      </section>;
    })}</div>
    <p className="star-breadth-note">看站上各自均线的股票比例；固定 {data.membershipDate} 名单回看，期间成分及有效股票数可能变化。历史高低仅供观察。</p>
  </div>;
}

/** A dated research snapshot; it is deliberately separate from live market breadth. */
export default function StarBreadthSnapshot({ children, variant = "details", onCollapse }: { children?: ReactNode; variant?: "details" | "card"; onCollapse?: () => void }) {
  const [open, setOpen] = useState(variant === "card");
  const [data, setData] = useState<Snapshot | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!open || data) return;
    const controller = new AbortController();
    setError(false);
    fetch("/research/star-breadth-20261115.json", { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("snapshot unavailable");
        return response.json() as Promise<Snapshot>;
      })
      .then(setData)
      .catch(() => { if (!controller.signal.aborted) setError(true); });
    return () => controller.abort();
  }, [open, data]);

  const content = <>
    {error && <p role="alert">科创宽度快照读取失败，请稍后重试。</p>}
    {open && !data && !error && <p role="status">正在读取快照…</p>}
    {data && <StarBreadthView data={data} />}
  </>;
  if (variant === "card") return <article className="moa-item star-breadth-card" data-overview-card="star-breadth" aria-label="科创50与科创100数量宽度">
    <div className="moa-item-head"><h3>科创50 / 科创100 · 数量宽度</h3>{onCollapse && <button type="button" onClick={onCollapse}>收起</button>}</div>
    {content}{children}
  </article>;
  return <details className="bc-source star-breadth-details" onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>科创50 / 科创100内部宽度 · 试算快照</summary>
    {content}<StarWeightedBreadthSnapshot active={open} />{open && children}
  </details>;
}
