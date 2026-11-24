import { finite, formatNumber, formatValue, type ObservationCardData, type Point, type Rail } from "./model";

const COLORS = ["#25766c", "#b78246", "#6b7eae", "#ad6171", "#797581"];
const RAIL_COLORS = { amber: "#a96a20", red: "#bc4c44", darkred: "#8d302d", blue: "#426e9e", gray: "#7e888d" };
const referenceColor = (rail: Rail) => RAIL_COLORS[rail.color
  ?? (rail.tone === "high" ? "red" : rail.tone === "watch" ? "amber" : rail.tone === "low" ? "blue" : "gray")];
function path(points: Point[], x: (date: string) => number, y: (value: number) => number): string {
  let drawing = false;
  return points.map(point => {
    if (!finite(point.value)) { drawing = false; return ""; }
    const part = `${drawing ? "L" : "M"}${x(point.date).toFixed(1)} ${y(point.value).toFixed(1)}`;
    drawing = true; return part;
  }).join(" ");
}
function shadedRuns(upper: Point[], lower: Point[], x: (date: string) => number, y: (value: number) => number): string[] {
  const areas: string[] = []; let run: number[] = [];
  const flush = () => {
    if (run.length > 1) areas.push(`M${run.map(i => `${x(upper[i].date).toFixed(1)} ${y(upper[i].value!).toFixed(1)}`).join(" L")} L${[...run].reverse().map(i => `${x(lower[i].date).toFixed(1)} ${y(lower[i].value!).toFixed(1)}`).join(" L")} Z`);
    run = [];
  };
  upper.forEach((point, index) => { if (finite(point.value) && finite(lower[index]?.value) && point.date === lower[index].date) run.push(index); else flush(); });
  flush(); return areas;
}
export default function TrendChart({ data, rails = [], label, large = false }: { data: ObservationCardData; rails?: Rail[]; label: string; large?: boolean }) {
  const limit = large ? Number.POSITIVE_INFINITY : data.frequency === "daily" ? 252 : data.frequency === "weekly" ? 156 : 60;
  const primary = data.points.slice(-limit);
  const firstDate = primary[0]?.date;
  const series = [{ id: "main", label: data.mainLabel || "当前序列", points: primary, dashed: false }, ...(data.lines ?? []).map(line => ({ ...line, points: line.points.filter(point => !firstDate || point.date >= firstDate) }))];
  const maLabel = data.frequency === "weekly" ? "4周均值" : "20日均值";
  const dynamic = ["ma20", "band_upper_1_5", "band_lower_1_5", "band_upper_2_0", "band_lower_2_0"] as const;
  const bands: { id: string; points: Point[]; dashed: boolean }[] = dynamic
    .filter(field => primary.some(point => finite(point[field])))
    .map(field => ({ id: field, points: primary.map(point => ({ date: point.date, value: point[field] ?? null })), dashed: field !== "ma20" }));
  if (label.includes("Baker") && primary.some(point => finite(point.mean) && finite(point.std))) {
    for (const sign of [1, -1]) bands.push({ id: `sigma_${sign}`, points: primary.map(point => ({ date: point.date, value: finite(point.mean) && finite(point.std) ? point.mean + sign * point.std : null })), dashed: true });
  }
  if (primary.length < 2 || primary.filter(point => finite(point.value)).length < 2) return <div className="mop-chart-empty">历史点不足，暂无法绘制趋势</div>;
  const dates = [...series, ...bands].flatMap(line => line.points.map(point => point.date));
  const timestamps = dates.map(date => Date.parse(date));
  if (timestamps.some(time => !Number.isFinite(time)) || primary.some((point, index) => index > 0 && point.date <= primary[index - 1].date)) return <div className="mop-chart-empty">日期顺序异常，趋势暂不可用</div>;
  const xmin = Math.min(...timestamps), xmax = Math.max(...timestamps);
  const values = [...series, ...bands].flatMap(line => line.points.map(point => point.value)).concat(rails.map(item => item.value)).filter(finite);
  const min = Math.min(...values), max = Math.max(...values), pad = Math.max((max - min) * .1, Math.abs(max) * .01, .01);
  const yMin = min - pad, yMax = max + pad, width = 600, height = large ? 260 : 112;
  const x = (date: string) => 52 + ((Date.parse(date) - xmin) / (xmax - xmin || 1)) * (width - 66);
  const y = (value: number) => 10 + (yMax - value) / (yMax - yMin) * (height - 24);
  const refs: Rail[] = [...rails, ...(min < 0 && max > 0 && !rails.some(item => item.value === 0) ? [{ value: 0, label: "零线" }] : [])];
  const upper = bands.find(item => item.id === "band_upper_1_5"), lower = bands.find(item => item.id === "band_lower_1_5");
  const shade = upper && lower ? shadedRuns(upper.points, lower.points, x, y) : [];
  const downside = label.includes("下跌价格冲击");
  const official = primary[primary.length - 1];
  const proxyStart = series.find(line => line.id === "nowcast")?.points[0];
  const connector = finite(official.value) && finite(proxyStart?.value) && official.date < proxyStart.date
    ? [official, proxyStart] : [];
  const bandColor = (id: string) => id === "ma20" ? "#89918f"
    : downside && id === "band_upper_1_5" ? RAIL_COLORS.amber
    : downside && id === "band_upper_2_0" ? RAIL_COLORS.red : "#9aa3a2";
  const hasStats = bands.some(line => line.id.startsWith("band_"));
  return <div className={`mop-chart ${large ? "mop-chart-large" : ""}`}>
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={label} preserveAspectRatio="none">
      <title>{label}</title>
      {shade.map((area, index) => <path key={index} d={area} fill="#79888a20" stroke="none" />)}
      {[max, (min + max) / 2, min].filter((tick, index, ticks) => ticks.indexOf(tick) === index).map(tick => <g key={tick}>
        <path d={`M52 ${y(tick)}H${width - 14}`} stroke="#e9eeec" fill="none" />
        <text x="46" y={y(tick) + 4} textAnchor="end" fontSize={large ? 10 : 13} fill="#65736e">{formatNumber(tick, max - min > 20 ? 0 : 2)}</text>
      </g>)}
      {refs.map(ref => <path key={ref.label} d={`M52 ${y(ref.value)}H${width - 14}`} stroke={referenceColor(ref)}
        strokeWidth="1.7" strokeDasharray="5 4" fill="none"><title>{ref.label}</title></path>)}
      {bands.map(line => {
        const visible = line.points.filter(point => finite(point.value));
        return visible.length === 1 ? <circle key={line.id} cx={x(visible[0].date)} cy={y(visible[0].value!)} r="2.5" fill={bandColor(line.id)} />
          : <path key={line.id} d={path(line.points, x, y)} fill="none" stroke={bandColor(line.id)} strokeWidth={line.id === "ma20" ? "1.6" : "1.2"} strokeDasharray={line.dashed ? "4 4" : undefined} />;
      })}
      {connector.length > 0 && <path d={path(connector, x, y)} fill="none" stroke={COLORS[1]} strokeDasharray="2 4">
        <title>作者历史与代理的衔接</title>
      </path>}
      {series.map((line, index) => <path key={line.id} d={path(line.points, x, y)} fill="none" stroke={line.id === "hv60" ? "#607a93" : COLORS[index % COLORS.length]} strokeWidth={index === 0 ? "2.4" : "1.7"} strokeDasharray={line.dashed ? "5 4" : undefined} strokeLinejoin="round" />)}
    </svg>
    <div className="mop-chart-dates"><span>{new Date(xmin).toISOString().slice(0, 10)}</span><span>{new Date(xmax).toISOString().slice(0, 10)}</span></div>
    <div className="mop-chart-legend">
      {(series.length > 1 || large) && series.map((line, index) => {
        const last = line.points[line.points.length - 1];
        return <span key={line.id}><i className={line.dashed ? "mop-line-dash" : ""} style={{ color: line.id === "hv60" ? "#607a93" : COLORS[index % COLORS.length] }} />
          {line.label}{line.id !== "main" && finite(last?.value) ? ` ${formatValue(last.value, data.unit)}` : ""}</span>;
      })}
      {bands.some(line => line.id === "ma20") && <span><i style={{ color: "#89918f" }} />{maLabel}</span>}
      {hasStats && <span><i className="mop-band-swatch" />±1.5σ / ±2σ{bands.some(line => line.id === "sigma_1") ? " / ±1σ" : ""}</span>}
      {rails.map(rail => <span key={rail.label}><i className="mop-line-dash" style={{ color: referenceColor(rail) }} />{rail.label}</span>)}
    </div>
  </div>;
}
