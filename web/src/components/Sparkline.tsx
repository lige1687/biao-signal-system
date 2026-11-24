import type { SparkPoint } from "../types";

interface Props {
  points: SparkPoint[];
  up?: boolean | null;
  width?: number;
  height?: number;
}

/**
 * 左栏近 60 日走势迷你图：实线 = 收盘价，虚线 = EMA20 均线参考（无均线时退回 60 日起点水平参考线）。
 * 配色独立于 BIAO 绿灰黑与单日涨跌红绿，用钢蓝（站上均线）/ 岩灰（均线下方）表达中期相对位置，
 * 终点圆点用独立 DOM 渲染避免 SVG 拉伸变形。
 */
export default function Sparkline({ points, width = 200, height = 28 }: Props) {
  if (points.length < 2) return <div className="spark-box" style={{ height }} />;

  const closes = points.map((p) => p.close);
  const hasEma = points.some((p) => p.ema20 != null && Number.isFinite(p.ema20));
  const refSeries: (number | null)[] = hasEma
    ? points.map((p) => (p.ema20 != null && Number.isFinite(p.ema20) ? p.ema20 : null))
    : points.map(() => points[0].close);

  const allValues = [
    ...closes,
    ...refSeries.filter((v): v is number => v != null),
  ];
  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  const span = max - min || 1;
  const padY = 3;
  const innerH = Math.max(4, height - padY * 2);
  const stepX = width / (points.length - 1);

  const toY = (val: number) => height - padY - ((val - min) / span) * innerH;

  const closeCoords = points
    .map((p, i) => `${(i * stepX).toFixed(1)},${toY(p.close).toFixed(1)}`)
    .join(" ");

  const areaCoords = `0,${height} ${closeCoords} ${width.toFixed(1)},${height}`;

  const refSegments: string[] = [];
  let currentSeg: string[] = [];
  refSeries.forEach((val, i) => {
    if (val == null) {
      if (currentSeg.length >= 2) refSegments.push(currentSeg.join(" "));
      currentSeg = [];
    } else {
      currentSeg.push(`${(i * stepX).toFixed(1)},${toY(val).toFixed(1)}`);
    }
  });
  if (currentSeg.length >= 2) refSegments.push(currentSeg.join(" "));

  const first = points[0];
  const last = points[points.length - 1];
  const lastRef = refSeries[refSeries.length - 1];
  const aboveRef = lastRef != null ? last.close >= lastRef : last.close >= first.close;

  const stroke = aboveRef ? "#2f5fa7" : "#64748b";
  const areaFill = aboveRef ? "rgba(47, 95, 167, 0.08)" : "rgba(100, 116, 139, 0.06)";
  const lastYPct = (toY(last.close) / height) * 100;

  const minClose = Math.min(...closes);
  const maxClose = Math.max(...closes);
  const rangePos = maxClose > minClose ? Math.round(((last.close - minClose) / (maxClose - minClose)) * 100) : 50;
  const ret60 = first.close > 0 ? ((last.close / first.close - 1) * 100) : null;
  const ret60Text = ret60 != null ? `${ret60 > 0 ? "+" : ""}${ret60.toFixed(1)}%` : "--";
  const tooltip = [
    `近${points.length}个交易日走势（实线=收盘，虚线=${hasEma ? "EMA20均线" : "区间起点"}）`,
    `${first.date} → ${last.date} · 区间涨跌 ${ret60Text}`,
    `区间最低 ${minClose.toFixed(2)} / 最高 ${maxClose.toFixed(2)}（当前位于 ${rangePos}% 位置）`,
  ].join("\n");

  return (
    <div className="spark-box" style={{ height }} title={tooltip}>
      <svg
        className="spark"
        width="100%"
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
      >
        <polygon points={areaCoords} fill={areaFill} />
        {refSegments.map((seg, idx) => (
          <polyline
            key={idx}
            points={seg}
            fill="none"
            stroke="#94a3b8"
            strokeWidth="1.2"
            strokeDasharray="3 2.5"
            vectorEffect="non-scaling-stroke"
          />
        ))}
        <polyline
          points={closeCoords}
          fill="none"
          stroke={stroke}
          strokeWidth="1.6"
          strokeLinejoin="round"
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
      <span
        className="spark-end-dot"
        style={{ top: `${lastYPct.toFixed(1)}%`, backgroundColor: stroke }}
      />
    </div>
  );
}
