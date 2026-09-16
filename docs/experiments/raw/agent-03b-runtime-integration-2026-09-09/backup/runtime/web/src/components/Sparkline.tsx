import type { SparkPoint } from "../types";

interface Props {
  points: SparkPoint[];
  up: boolean | null; // null = 无涨跌信息（用中性色）
  width?: number;
  height?: number;
}

/** 迷你收盘价折线（近 60 日），SVG 实现，无依赖。 */
export default function Sparkline({ points, up, width = 260, height = 48 }: Props) {
  if (points.length < 2) return <div className="spark" style={{ height }} />;
  const closes = points.map((p) => p.close);
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const span = max - min || 1;
  const stepX = width / (points.length - 1);
  const coords = points
    .map((p, i) => `${(i * stepX).toFixed(1)},${(height - ((p.close - min) / span) * (height - 4) - 2).toFixed(1)}`)
    .join(" ");
  const stroke = up == null ? "#9aa4b2" : up ? "#e33d47" : "#0b9b64";
  const last = points[points.length - 1];
  const lastX = ((points.length - 1) * stepX).toFixed(1);
  const lastY = (height - ((last.close - min) / span) * (height - 4) - 2).toFixed(1);
  return (
    <svg className="spark" width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      <polyline points={coords} fill="none" stroke={stroke} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={lastX} cy={lastY} r="2.5" fill={stroke} />
    </svg>
  );
}
