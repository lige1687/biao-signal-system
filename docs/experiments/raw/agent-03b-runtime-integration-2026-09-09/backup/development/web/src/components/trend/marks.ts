import type * as echarts from "echarts";
import { zoneToneColor, type MarkLine, type ZoneLevel } from "./zones";

/**
 * 区间 -> markArea 色带：相邻区间边界围成一个矩形，首尾贴 y 轴 min/max。
 * 挂到哪条 series 上，就用那条 series 的 yAxisIndex 作坐标系
 * ——叠图里要挂到右轴(利率/占比)的线上，而不是左轴(指数点位)。
 */
export function zoneBands(
  zones: readonly ZoneLevel[],
  opacity = 0.06,
): NonNullable<echarts.LineSeriesOption["markArea"]> {
  return {
    silent: true,
    data: zones.map((z, i) => {
      const lo = i === 0 ? "min" : zones[i - 1].max;
      const hi = z.max === Infinity ? "max" : z.max;
      return [
        { yAxis: lo, xAxis: 0 },
        { yAxis: hi, xAxis: "max", itemStyle: { color: zoneToneColor(z.tone), opacity } },
      ];
    }),
  };
}

/** 分界线 -> markLine：虚线 + 右上角标签。 */
export function zoneMarkLines(
  lines: readonly MarkLine[],
): NonNullable<echarts.LineSeriesOption["markLine"]> {
  return {
    silent: true,
    symbol: "none",
    data: lines.map((mk) => ({
      yAxis: mk.y,
      lineStyle: { color: mk.color, type: "dashed", width: 1 },
      label: { formatter: mk.label, color: mk.color, fontSize: 10, position: "insideEndTop" },
    })),
  };
}
