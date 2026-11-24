import { useEffect, useId, useMemo, useState, type ReactNode } from "react";
import ChartLegend, { CHART_COLORS } from "../market-observation-alerts/ChartLegend";
import { hyOasReading, isOasValue } from "./hyOasReading";
import type { Point } from "./marketRiskMetrics";

const WARNING_COLOR = "#b55224";
const REFERENCE_NOTE = "虚线是截至当前读数的参考带：前 756 个有效观测的第 15／85 分位，橙线标出高于上轨的部分。";
const COVERAGE_NOTE = "FRED 公开序列约覆盖近 3 年，暂无同源 5 年或 10 年分位。";
const percent = (value: number) => `${value.toFixed(2)}%`;

type Band = { low: number; high: number };

function HyOasTrend({ points, band }: { points: Point[]; band: Band | null }) {
  const clipId = useId();
  const values = points.map(({ value }) => value).filter(isOasValue);
  if (values.length < 2) return <div className="moa-mini-empty">趋势资料不足</div>;
  if (band) values.push(band.low, band.high);
  const max = Math.max(...values), min = Math.min(...values);
  const pad = Math.max((max - min) * .1, .02);
  const y = (value: number) => 10 + (max + pad - value) / (max - min + 2 * pad) * 100;
  const firstDate = points[0].date, lastDate = points[points.length - 1].date;
  const start = Date.parse(firstDate), span = Date.parse(lastDate) - start;
  const width = 320, height = 120;
  let connected = false;
  const path = points.map(({ date, value }) => {
    if (!isOasValue(value)) { connected = false; return ""; }
    const x = (Date.parse(date) - start) / span * width;
    const part = `${connected ? "L" : "M"}${x.toFixed(2)},${y(value).toFixed(2)}`;
    connected = true;
    return part;
  }).join(" ");
  const rails = band ? [
    { key: "high", label: `高 ${percent(band.high)}`, y: y(band.high), color: CHART_COLORS.high },
    { key: "low", label: `低 ${percent(band.low)}`, y: y(band.low), color: CHART_COLORS.low },
  ] : [];
  const [upper, lower] = rails;
  // Keep edge labels legible even if an unusually large spike compresses the band.
  const labelNudge = upper && lower ? Math.max(0, 16 - (lower.y - upper.y)) / 2 : 0;
  return <div className={`cmo-hy-trend moa-mini${band ? " has-rails" : ""}`}>
    <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" role="img" aria-label="高收益债信用利差走势">
      {upper && lower && <>
        <defs><clipPath id={clipId}><rect x="0" y="0" width={width} height={upper.y} /></clipPath></defs>
        <rect className="cmo-hy-band" x="0" y={upper.y} width={width} height={lower.y - upper.y} />
        {rails.map(rail => <line key={rail.key} x1="0" x2={width} y1={rail.y} y2={rail.y} stroke={rail.color}
          strokeDasharray="5 4" vectorEffect="non-scaling-stroke" />)}
      </>}
      <path d={path} fill="none" stroke={CHART_COLORS.primary} strokeWidth="2" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
      {upper && <path className="cmo-hy-above" d={path} clipPath={`url(#${clipId})`} fill="none" stroke={WARNING_COLOR}
        strokeWidth="2.4" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />}
    </svg>
    {band && <div className="cmo-hy-rail-labels" aria-label="参考区间">
      {rails.map(rail => <span key={rail.key} className="cmo-hy-rail-label" style={{ color: rail.color,
        top: `${(rail.y + (rail.key === "high" ? -labelNudge : labelNudge)) / height * 100}%` }}>{rail.label}</span>)}
    </div>}
    <div className="moa-mini-dates"><span>{firstDate}</span><span>{lastDate}</span></div>
  </div>;
}

function HyOasInfo({ children }: { children: ReactNode }) {
  const id = useId();
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const open = (hovered || focused) && !dismissed;
  useEffect(() => {
    if (!open) return;
    const dismiss = (event: KeyboardEvent) => { if (event.key === "Escape") setDismissed(true); };
    document.addEventListener("keydown", dismiss);
    return () => document.removeEventListener("keydown", dismiss);
  }, [open]);
  return <span className="cmo-hy-info" onMouseEnter={() => { setHovered(true); setDismissed(false); }} onMouseLeave={() => setHovered(false)}>
    <button type="button" className="cmo-hy-info-trigger" aria-label="图表说明" aria-describedby={id}
      onFocus={() => { setFocused(true); setDismissed(false); }} onBlur={() => setFocused(false)} onClick={() => setDismissed(false)}>ⓘ</button>
    <span className="cmo-hy-tooltip" id={id} role="tooltip" hidden={!open}>{children}</span>
  </span>;
}

export default function HyOasCard({ title, points, state, source, sourceUrl, onCollapse, onDetail }: {
  title: string; points: Point[]; state?: string; source: string; sourceUrl?: string;
  onCollapse: () => void; onDetail: (reading: string, limit: string) => void;
}) {
  const { current, status, basis, year, band, history, change, plot } = useMemo(() => hyOasReading(state ? [] : points), [points, state]);
  const reading = "利差走阔表示企业借债需要更高风险补偿。";
  const historyText = history ? `可用历史分位 ${history.percentile.toFixed(1)}%` : null;
  const limit = `${history ? `${historyText}（${history.from} 至 ${history.to}）。` : ""}${COVERAGE_NOTE}`;
  return <article className="moa-item cmo-home-card cmo-hy-card" aria-label={title} data-tone="neutral" data-overview-card="hy-oas">
    <div className="moa-item-head"><h3>{title}</h3><div className="moa-item-actions">
      {(state || plot.length < 2) && <span className="moa-quality">{state ?? (current ? "仅有当前值" : "暂无读数")}</span>}
      <HyOasInfo>
        <span>仅绘制已发布的读数，明确缺值处保留断线。</span>
        {year && <span>近 1 年第 20／80 分位：{percent(year.low)}／{percent(year.high)}；不含当日。</span>}
        {band && <span>{REFERENCE_NOTE}</span>}
        <span>{limit}</span>
      </HyOasInfo>
      <button type="button" onClick={onCollapse}>收起</button>
    </div></div>
    <h4 className="moa-conclusion">{state ? "资料暂不可读" : status}{basis && <span className="cmo-hy-basis">{basis}</span>}</h4>
    <div className="moa-erp-value"><strong>{current ? percent(current.value) : "未知"}</strong></div>
    {historyText && <p className="cmo-hy-history">{historyText}</p>}
    <ChartLegend label={`${title}曲线与参考`} items={[
      { label: "利差", color: CHART_COLORS.primary },
      ...(band ? [{ label: "近 3 年参考上轨", color: CHART_COLORS.high, dashed: true },
        { label: "高于上轨", color: WARNING_COLOR }] : []),
    ]} />
    <HyOasTrend points={plot} band={band} />
    <p className="moa-card-change">{change ? <>较 {change.from}{" "}
      <b className={`cmo-hy-change is-${change.direction}`}>
        {change.direction !== "flat" && <span aria-hidden="true">{change.direction === "up" ? "↑" : "↓"} </span>}{change.text}
      </b></> : "近期变化暂不可比"}</p>
    <p className="moa-card-reading">{reading}</p>
    {!state && !band && plot.length > 1 && <p className="moa-card-limit">可比历史还不够，暂不显示参考带。</p>}
    <p className="moa-card-meta">资料截至 {current?.date ?? "未提供"} · 日频</p>
    <footer><button type="button" onClick={() => onDetail(reading, limit)}>看大图 ↗</button>
      <details><summary>来源与参考</summary><p>{limit}</p><p>{sourceUrl ? <a href={sourceUrl} target="_blank" rel="noreferrer">{source}</a> : source}</p></details>
    </footer>
  </article>;
}
