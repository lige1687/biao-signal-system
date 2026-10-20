import type { ChartPayload, StructureMark } from "../types";
import type { ChartDisplay, MarkPick } from "./KlineChart";

type StructureDisplay = Pick<
  ChartDisplay,
  "bottomMarks" | "topMarks" | "invalidatedMarks" | "marksScope"
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
 * 结构标记口径。
 *
 * - "alive"（默认）：只画存活结构的确认标记。历史标的可有数百个确认
 *   （上证指数底部确认 234 个、结构失效 313 个），全画会遮挡 K 线到不可读；
 *   已失效的灰色标记对「现在还有效的结构是什么」这个问题是噪音。
 * - "all"：研究者视角，全量铺开。
 */
export type MarksScope = "alive" | "all";

/** 可见窗口超过该根数时进入「降密」档：远端失效标记截断，只留最近的。 */
export const MARK_DENSE_WINDOW_BARS = 600;

/** 降密档下，非存活确认标记最多保留的个数（按日期取最近）。存活标记始终全画。 */
export const MARK_DENSE_RECENT_DEAD = 60;

/**
 * 按口径过滤确认类标记（底部/顶部）。
 *
 * alive 口径：只留 live 标记；all 口径：全留。
 * dense（可视窗口 > MARK_DENSE_WINDOW_BARS）时额外截断：
 * 存活标记始终全画，非存活的只保留最近 MARK_DENSE_RECENT_DEAD 个——
 * 降密档保护的是「全量铺开时几百个灰菱形」的场景，存活的本来就少。
 */
function filterConfirmMarks(
  marks: StructureMark[],
  scope: MarksScope,
  dense: boolean,
): StructureMark[] {
  let out = scope === "alive" ? marks.filter((m) => m.live) : marks;
  if (dense && out.length > MARK_DENSE_RECENT_DEAD) {
    // StructureMark 按日期升序（与 K 线序列同源），取尾部即最近。
    // 注意截断只丢非存活：先把存活挑出来保全量，再从非存活的里取最近。
    const alivePart = out.filter((m) => m.live);
    const deadPart = out.filter((m) => !m.live).slice(-MARK_DENSE_RECENT_DEAD);
    const merged = [...alivePart, ...deadPart];
    // 恢复日期升序，保证 markPoint 顺序与图上时间轴一致
    merged.sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));
    out = merged;
  }
  return out;
}

/**
 * 当前口径下「会画」的结构标记计数（供开关徽章显示 n/总数）。
 * dense 降密是随缩放窗口动态变化的，不进徽章——徽章反映口径，不反映缩放。
 */
export function scopeMarkCounts(
  payload: Pick<ChartPayload, "bottomMarks" | "topMarks" | "invalidatedMarks">,
  scope: MarksScope,
): { bottomMarks: number; topMarks: number; invalidatedMarks: number } {
  return {
    bottomMarks: scope === "alive" ? payload.bottomMarks.filter((m) => m.live).length : payload.bottomMarks.length,
    topMarks: scope === "alive" ? payload.topMarks.filter((m) => m.live).length : payload.topMarks.length,
    invalidatedMarks: scope === "alive" ? 0 : payload.invalidatedMarks.length,
  };
}

/**
 * 只负责把结构 DTO 转成 ECharts markPoint。
 *
 * 保持为纯函数，确保底部、顶部、失效三个显示开关可以独立回归测试，
 * 不需要挂载 React 或创建真实 Canvas。
 *
 * 密度治理（口径 + 降密）也在这里收敛，KlineChart 只负责把 zoom 窗口
 * 折算成 dense 布尔传进来。
 */
export function buildStructureMarkPoints(
  payload: Pick<ChartPayload, "bottomMarks" | "topMarks" | "invalidatedMarks">,
  display: StructureDisplay,
  dense = false,
): StructureMarkPoint[] {
  const points: StructureMarkPoint[] = [];
  const scope = display.marksScope;

  if (display.bottomMarks) {
    for (const mark of filterConfirmMarks(payload.bottomMarks, scope, dense)) {
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
    for (const mark of filterConfirmMarks(payload.topMarks, scope, dense)) {
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

  if (display.invalidatedMarks && scope === "all") {
    // 失效×让位确认◆：同一结构既有确认标记（底部/顶部开关开着）又有失效
    // 标记时，只画确认——两颗标记同屏平铺只会互相遮挡，确认标记带交互解释。
    const confirmedIds = new Set<string>();
    if (display.bottomMarks)
      for (const m of payload.bottomMarks) confirmedIds.add(m.info.structure_id);
    if (display.topMarks)
      for (const m of payload.topMarks) confirmedIds.add(m.info.structure_id);

    for (const mark of payload.invalidatedMarks) {
      if (confirmedIds.has(mark.info.structure_id)) continue;
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
