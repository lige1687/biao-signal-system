import type { ChartPayload } from "../types";
import type { ChartDisplay, MarkPick } from "./KlineChart";

type StructureDisplay = Pick<
  ChartDisplay,
  "bottomMarks" | "topMarks" | "invalidatedMarks"
>;

export interface StructureMarkPoint {
  coord: [string, number];
  symbol: "diamond" | "x";
  symbolSize: number;
  symbolRotate?: number;
  itemStyle: { color: string };
  label: { show: false };
  pick: MarkPick;
  tooltip: { formatter: string };
}

/**
 * 只负责把结构 DTO 转成 ECharts markPoint。
 *
 * 保持为纯函数，确保底部、顶部、失效三个显示开关可以独立回归测试，
 * 不需要挂载 React 或创建真实 Canvas。
 */
export function buildStructureMarkPoints(
  payload: Pick<ChartPayload, "bottomMarks" | "topMarks" | "invalidatedMarks">,
  display: StructureDisplay,
): StructureMarkPoint[] {
  const points: StructureMarkPoint[] = [];

  if (display.bottomMarks) {
    for (const mark of payload.bottomMarks) {
      points.push({
        coord: [mark.date, mark.price],
        symbol: "diamond",
        symbolSize: 13,
        itemStyle: { color: mark.live ? "#0b9b64" : "#98a2b3" },
        label: { show: false },
        pick: {
          kind: "bottom_mark",
          date: mark.date,
          price: mark.price,
          structureId: mark.info.structure_id,
          structureType: mark.info.structure_type,
        },
        tooltip: {
          formatter: `${mark.label}<br/>确认日 ${mark.info.confirmed_date ?? "-"}<br/>失效日 ${mark.info.invalidated_date ?? "-"}`,
        },
      });
    }
  }

  if (display.topMarks) {
    for (const mark of payload.topMarks) {
      points.push({
        coord: [mark.date, mark.price],
        symbol: "diamond",
        symbolSize: 13,
        symbolRotate: 180,
        itemStyle: { color: mark.live ? "#dc2626" : "#98a2b3" },
        label: { show: false },
        pick: {
          kind: "top_mark",
          date: mark.date,
          price: mark.price,
          structureId: mark.info.structure_id,
          structureType: mark.info.structure_type,
        },
        tooltip: {
          formatter: `${mark.label}<br/>确认日 ${mark.info.confirmed_date ?? "-"}<br/>失效日 ${mark.info.invalidated_date ?? "-"}`,
        },
      });
    }
  }

  if (display.invalidatedMarks) {
    for (const mark of payload.invalidatedMarks) {
      points.push({
        coord: [mark.date, mark.price],
        symbol: "x",
        symbolSize: 12,
        itemStyle: { color: "#98a2b3" },
        label: { show: false },
        pick: {
          kind: "invalidated_mark",
          date: mark.date,
          price: mark.price,
          structureId: mark.info.structure_id,
          structureType: mark.info.structure_type,
        },
        tooltip: { formatter: `${mark.label} ${mark.info.invalidated_date ?? ""}` },
      });
    }
  }

  return points;
}
