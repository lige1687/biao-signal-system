import { useState } from "react";
import { CHART_COLORS } from "./ChartLegend";

type Line = { name: string; color: string; values: (number | null)[] };
type ReferenceLine = Line & { dashed?: boolean; endLabel?: string };
const finite = (v: number | null | undefined): v is number => typeof v === "number" && Number.isFinite(v);

/** A small, date-aligned view of supplied observations; missing points break the line. */
export default function MiniTrend({
  dates,
  lines,
  lower,
  upper,
  references = [],
  percent = false,
  label,
  showScale = false,
  height = 120,
  windowTag,
  shadeAbove,
  shadeBelow,
  invertShade = false,
  unitSuffix = "",
}: {
  dates: string[];
  lines: Line[];
  lower?: (number | null)[];
  upper?: (number | null)[];
  references?: ReferenceLine[];
  percent?: boolean;
  label: string;
  showScale?: boolean;
  height?: number;
  windowTag?: string;
  shadeAbove?: (number | null)[];
  shadeBelow?: (number | null)[];
  invertShade?: boolean;
  unitSuffix?: string;
}) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  if (dates.length < 2 || !lines.some((line) => line.values.filter(finite).length >= 2)) {
    return <div className="moa-mini-empty">趋势资料不足</div>;
  }
  const timestamps = dates.map((date) => Date.parse(date));
  if (timestamps.some((time, i) => !Number.isFinite(time) || (i > 0 && time <= timestamps[i - 1]))) {
    return <div className="moa-mini-empty">日期资料无效，趋势暂停</div>;
  }
  const values = [
    ...lines.flatMap((line) => line.values),
    ...references.flatMap((line) => line.values),
    ...(lower ?? []),
    ...(upper ?? []),
  ].filter(finite);
  if (!values.length) return <div className="moa-mini-empty">趋势资料不足</div>;

  const observedLow = Math.min(...values);
  const observedHigh = Math.max(...values);
  const padding = Math.max(
    (observedHigh - observedLow) * 0.1,
    percent ? 2 : Math.abs(observedHigh) * 0.005,
    0.01,
  );
  const low = percent && showScale ? 0 : percent ? Math.max(0, observedLow - padding) : observedLow - padding;
  const high =
    percent && showScale ? 100 : percent ? Math.min(100, observedHigh + padding) : observedHigh + padding;
  const span = high - low || 1;
  const start = timestamps[0];
  const elapsed = timestamps[timestamps.length - 1] - start || 1;

  const lowColor = percent ? CHART_COLORS.low : CHART_COLORS.high;
  const highColor = percent ? CHART_COLORS.high : CHART_COLORS.low;
  const latestLow = lower?.[dates.length - 1];
  const latestHigh = upper?.[dates.length - 1];

  const refEndItems = references
    .filter((line) => line.endLabel && finite(line.values[dates.length - 1]))
    .map((line) => ({
      key: `${line.name}-label`,
      rawValue: line.values[dates.length - 1] as number,
      color: line.color,
      text: line.endLabel!,
    }));
  const pctEndItems =
    percent && !showScale
      ? [
          ...(finite(latestHigh)
            ? [{ key: "__pct_high", rawValue: latestHigh, color: highColor, text: `高 ${latestHigh.toFixed(1)}%` }]
            : []),
          ...(finite(latestLow)
            ? [{ key: "__pct_low", rawValue: latestLow, color: lowColor, text: `低 ${latestLow.toFixed(1)}%` }]
            : []),
        ]
      : [];
  const allRightItems = [...refEndItems, ...pctEndItems];
  const useRightGutter = !showScale && allRightItems.length > 0;

  const left = showScale ? 43 : 8;
  const right = useRightGutter ? 256 : 312;
  const topPad = height < 108 ? 11 : 12;
  const plotSpan = height === 120 ? 94 : Math.max(40, height - topPad - 13);
  const x = (i: number) => left + ((timestamps[i] - start) / elapsed) * (right - left);
  const y = (v: number) => topPad + ((high - v) / span) * plotSpan;

  const path = (data: (number | null)[]) => {
    let drawing = false;
    return dates
      .map((_, i) => {
        const value = data[i];
        if (!finite(value)) {
          drawing = false;
          return "";
        }
        const command = `${drawing ? "L" : "M"}${x(i).toFixed(2)},${y(value).toFixed(2)}`;
        drawing = true;
        return command;
      })
      .join(" ");
  };

  const band = (data: (number | null)[], boundary: number) => {
    const areas: string[] = [];
    let run: number[] = [];
    const flush = () => {
      if (run.length >= 2) {
        areas.push(
          `M${x(run[0])},${y(boundary)} ${run.map((i) => `L${x(i)},${y(data[i]!)}`).join(" ")} L${x(run[run.length - 1])},${y(boundary)} Z`,
        );
      }
      run = [];
    };
    dates.forEach((_, i) => {
      if (finite(data[i])) run.push(i);
      else flush();
    });
    flush();
    return areas.join(" ");
  };

  // De-collide right-gutter labels vertically so two close rails never overlap.
  const laidOutRightLabels = (() => {
    if (!useRightGutter) return [];
    const sorted = allRightItems
      .map((item) => ({ ...item, yPos: Math.max(10, Math.min(height - 5, y(item.rawValue) + 3)) }))
      .sort((a, b) => a.yPos - b.yPos);
    const minGap = 11;
    for (let i = 1; i < sorted.length; i++) {
      if (sorted[i].yPos - sorted[i - 1].yPos < minGap) {
        sorted[i].yPos = sorted[i - 1].yPos + minGap;
      }
    }
    if (sorted.length > 0 && sorted[sorted.length - 1].yPos > height - 4) {
      sorted[sorted.length - 1].yPos = height - 4;
      for (let i = sorted.length - 2; i >= 0; i--) {
        if (sorted[i + 1].yPos - sorted[i].yPos < minGap) {
          sorted[i].yPos = Math.max(10, sorted[i + 1].yPos - minGap);
        }
      }
    }
    return sorted;
  })();

  let lastPrimaryIdx = lines[0].values.length - 1;
  while (lastPrimaryIdx >= 0 && !finite(lines[0].values[lastPrimaryIdx])) lastPrimaryIdx--;

  const upperFill = invertShade ? "rgba(54,141,128,.12)" : "rgba(187,139,75,.11)";
  const lowerFill = invertShade ? "rgba(187,139,75,.11)" : "rgba(54,141,128,.12)";

  const activeHover =
    hoverIdx !== null && hoverIdx >= 0 && hoverIdx < dates.length ? hoverIdx : null;
  const suffix = unitSuffix || (percent ? "%" : "");

  return (
    <div className="moa-mini">
      <svg
        viewBox={`0 0 320 ${height}`}
        role="img"
        aria-label={label}
        onMouseMove={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          if (!rect.width) return;
          const svgX = ((e.clientX - rect.left) / rect.width) * 320;
          const ratio = Math.max(0, Math.min(1, (svgX - left) / Math.max(1, right - left)));
          const targetTs = start + ratio * elapsed;
          let best = 0;
          let bestDiff = Infinity;
          for (let i = 0; i < timestamps.length; i++) {
            const d = Math.abs(timestamps[i] - targetTs);
            if (d < bestDiff) {
              bestDiff = d;
              best = i;
            }
          }
          setHoverIdx(best);
        }}
        onMouseLeave={() => setHoverIdx(null)}
      >
        <title>{label}</title>
        {showScale &&
          [high, (high + low) / 2, low].map((value, index) => (
            <g key={index}>
              <path d={`M${left},${y(value)}H${right}`} stroke="#e6ebe4" strokeWidth="0.8" />
              <text
                x={left - 5}
                y={Math.max(13, Math.min(height - 7, y(value) + 4))}
                textAnchor="end"
                fill="#687665"
                fontSize="14"
              >
                {percent ? `${value.toFixed(0)}%` : value.toFixed(2)}
              </text>
            </g>
          ))}
        {percent && lower && <path d={band(lower, low)} fill="rgba(54,141,128,.12)" />}
        {percent && upper && <path d={band(upper, high)} fill="rgba(187,139,75,.12)" />}
        {shadeAbove && <path d={band(shadeAbove, high)} fill={upperFill} />}
        {shadeBelow && <path d={band(shadeBelow, low)} fill={lowerFill} />}
        {percent && !lower && !upper && (
          <>
            <path d={`M${left},${y(50)}H${right}`} stroke="#9caaba" strokeDasharray="3 4" fill="none" />
            {!showScale && (
              <text x="9" y={y(50) - 5} fill="#78889a" fontSize="10">
                50% · 半数股票
              </text>
            )}
          </>
        )}
        {lower && <path d={path(lower)} stroke={lowColor} strokeWidth="1.8" fill="none" />}
        {upper && <path d={path(upper)} stroke={highColor} strokeWidth="1.8" fill="none" />}
        {references.map((line) => (
          <path
            key={line.name}
            d={path(line.values)}
            stroke={line.color}
            strokeDasharray={line.dashed === false ? undefined : "5 3.5"}
            strokeWidth="1.6"
            fill="none"
          >
            <title>{line.name}</title>
          </path>
        ))}
        {lines.map((line, i) => (
          <path
            key={line.name}
            d={path(line.values)}
            stroke={line.color}
            strokeWidth={i === 0 ? 2.4 : 1.65}
            strokeLinejoin="round"
            strokeLinecap="round"
            fill="none"
          />
        ))}
        {lastPrimaryIdx >= 0 && (
          <circle
            cx={x(lastPrimaryIdx)}
            cy={y(lines[0].values[lastPrimaryIdx]!)}
            r="2.8"
            fill={lines[0].color}
            stroke="#fff"
            strokeWidth="1.2"
          />
        )}
        {useRightGutter && (
          <line x1={right + 2} x2={right + 2} y1={6} y2={height - 6} stroke="#eef2f6" strokeWidth="1" />
        )}
        {useRightGutter
          ? laidOutRightLabels.map((item) => (
              <text
                key={item.key}
                x={right + 5}
                y={item.yPos}
                textAnchor="start"
                fill={item.color}
                fontSize="9.5"
                fontWeight="600"
              >
                {item.text}
              </text>
            ))
          : (
            <>
              {percent && showScale && finite(latestHigh) && (
                <text
                  x="310"
                  y={Math.max(10, y(latestHigh) - 4)}
                  textAnchor="end"
                  fill={highColor}
                  fontSize="14"
                  stroke="#fbfcfe"
                  strokeWidth="2.5"
                  paintOrder="stroke"
                >
                  高位 {latestHigh.toFixed(1)}%
                </text>
              )}
              {percent && showScale && finite(latestLow) && (
                <text
                  x="310"
                  y={Math.min(height - 2, y(latestLow) + 11)}
                  textAnchor="end"
                  fill={lowColor}
                  fontSize="14"
                  stroke="#fbfcfe"
                  strokeWidth="2.5"
                  paintOrder="stroke"
                >
                  低位 {latestLow.toFixed(1)}%
                </text>
              )}
            </>
          )}
        {windowTag && activeHover === null && (
          <g pointerEvents="none">
            <rect x={left} y={3} width={windowTag.length * 8 + 10} height={13} rx={3} fill="rgba(241,245,249,0.88)" />
            <text x={left + 5} y={12.5} fill="#64748b" fontSize="9.2" fontWeight="500">
              {windowTag}
            </text>
          </g>
        )}
        {activeHover !== null && (
          <g pointerEvents="none">
            <line
              x1={x(activeHover)}
              x2={x(activeHover)}
              y1={4}
              y2={height - 4}
              stroke="#64748b"
              strokeWidth="1"
              strokeDasharray="2 2"
            />
            {finite(lines[0].values[activeHover]) && (
              <circle
                cx={x(activeHover)}
                cy={y(lines[0].values[activeHover]!)}
                r="3.2"
                fill={lines[0].color}
                stroke="#fff"
                strokeWidth="1.2"
              />
            )}
            <rect x={left} y={2} width={Math.min(242, right - left)} height={15} rx={3} fill="rgba(255,255,255,0.94)" stroke="#cbd5e1" strokeWidth="0.7" />
            <text x={left + 5} y={12.5} fill="#1e293b" fontSize="9.5" fontWeight="600">
              {dates[activeHover]} ·{" "}
              {lines
                .slice(0, 3)
                .map((l) =>
                  finite(l.values[activeHover])
                    ? `${l.name} ${l.values[activeHover]!.toFixed(percent ? 1 : 2)}${suffix}`
                    : null,
                )
                .filter(Boolean)
                .join(" / ")}
            </text>
          </g>
        )}
      </svg>
      <div className="moa-mini-dates">
        <span>{dates[0]}</span>
        <span>{dates[dates.length - 1]}</span>
      </div>
    </div>
  );
}
