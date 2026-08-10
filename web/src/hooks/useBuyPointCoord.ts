import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import {
  annoToIndex,
  circled,
  notableCandidates,
} from "../components/BuyPointDrawer";
import type {
  HighlightPriceLine,
  HighlightSpec,
  MarkPick,
} from "../components/KlineChart";
import type { BuyPointCandidate, ChartPayload } from "../types";

/**
 * 把一个候选买点翻译成主图高亮指令：关键价/止损/目标画横线，
 * 依据结构（底部/顶部标记 + 支撑阻力线）点亮，其余压暗。
 *
 * 价位线带 annoId（bp-N），供图<->卡双向联动：点图上的线能定位到卡片，
 * 点卡片能点亮图上的线。结构来自主图已有标记，按候选 module 大致归类。
 */
export function buildCandidateHighlight(
  c: BuyPointCandidate,
  payload: ChartPayload,
  index: number,
): HighlightSpec {
  const annoId = `bp-${index}`;
  const priceLines: HighlightPriceLine[] = [];
  if (c.key_price != null) {
    priceLines.push({
      annoId,
      price: c.key_price,
      label: `买点${circled(index)} 关键价`,
      color: "#2563eb",
      kind: "entry",
    });
  }
  if (c.invalidation_price != null) {
    priceLines.push({
      annoId,
      price: c.invalidation_price,
      label: "止损",
      color: "#dc2626",
      kind: "stop",
    });
  }
  if (c.reward_risk_target != null) {
    priceLines.push({
      annoId,
      price: c.reward_risk_target,
      label: "目标B",
      color: "#0b9b64",
      kind: "target",
    });
  }

  const structureIds: string[] = [];
  const mod = c.module;
  // A 稳定上升趋势回调 / B 均线密集突破 / C 2B破底翻：以底部结构 + 支撑/阻力为基础
  const bottomRelevant = mod === "A" || mod === "B" || mod === "C" || !mod;
  // D 假突破反向：以顶部结构 + 颈线为基础
  const topRelevant = mod === "D";
  if (bottomRelevant) {
    for (const m of payload.bottomMarks) if (m.live) structureIds.push(m.info.structure_id);
    for (const l of payload.bottomLines) if (l.structure_id) structureIds.push(l.structure_id);
    if (payload.b1Line?.structure_id) structureIds.push(payload.b1Line.structure_id);
  }
  if (topRelevant) {
    for (const m of payload.topMarks) if (m.live) structureIds.push(m.info.structure_id);
    for (const l of payload.topLines) if (l.structure_id) structureIds.push(l.structure_id);
  }
  // 去重（同一 structure_id 可能同时出现在 marks 与 lines）
  return { priceLines, structureIds: [...new Set(structureIds)], dimOthers: true };
}

/**
 * 买点分析联动协调：当前高亮候选 + review 查询 + 高亮指令。
 *
 * 页面（DetailPage / WorkspacePage）掌握主图与开关，本 hook 负责拉 review、
 * 算 highlightSpec、维护 activeCand。BuyPointDrawer 作为受控对话栏接收这些值。
 *
 * @param symbol  标的
 * @param chart   主图数据（算高亮指令需要里面的结构标记）
 * @param enabled 是否打开买点分析（关闭时清空 activeCand、停掉 review 查询）
 */
export function useBuyPointCoord(
  symbol: string | undefined,
  chart: ChartPayload | undefined,
  enabled: boolean,
) {
  const [activeCand, setActiveCand] = useState<number | null>(null);

  // 关闭买点分析时清空高亮候选，避免下次打开残留上一次的选择
  useEffect(() => {
    if (!enabled) setActiveCand(null);
  }, [enabled]);

  const { data: review, isLoading: reviewLoading } = useQuery({
    queryKey: ["buyPointReview", symbol],
    queryFn: () => api.buyPointReview(symbol!),
    enabled: Boolean(symbol) && enabled,
  });

  // activeCand 是 notable 序号（与抽屉 chips / agent 文本序号一致）
  const highlightSpec: HighlightSpec | null = useMemo(() => {
    if (!enabled || activeCand == null || !review || !chart) return null;
    const cand = notableCandidates(review.candidates)[activeCand];
    if (!cand) return null;
    return buildCandidateHighlight(cand, chart, activeCand);
  }, [enabled, activeCand, review, chart]);

  const activeAnnoId = activeCand != null ? `bp-${activeCand}` : null;

  return { review, reviewLoading, activeCand, setActiveCand, activeAnnoId, highlightSpec };
}

/** 图->卡联动：带 annoId 的点击（价位线）定位到对应候选卡片。 */
export function pickToCandidate(pick: MarkPick): number | null {
  if (!pick.annoId) return null;
  return annoToIndex(pick.annoId);
}
