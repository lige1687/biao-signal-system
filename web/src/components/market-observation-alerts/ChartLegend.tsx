import type { CSSProperties } from "react";

export const CHART_COLORS = {
  primary: "#52675e",
  secondary: "#80678a",
  low: "#327c72",
  high: "#986737",
  zero: "#70766b",
} as const;

export type LegendItem = { label: string; color: string; dashed?: boolean; value?: string };

/** Labels, line samples and values share the plotted color; dash style carries meaning too. */
export default function ChartLegend({ items, label = "曲线与参考线" }: { items: LegendItem[]; label?: string }) {
  return <div className="moa-chart-legend" role="group" aria-label={label}>
    {items.map((item) => <span className="moa-legend-item" key={item.label}
      style={{ "--legend-color": item.color } as CSSProperties}>
      <i aria-hidden="true" className={item.dashed ? "is-dashed" : undefined} />
      <span>{item.label}{item.value && <> <b>{item.value}</b></>}</span>
    </span>)}
  </div>;
}
