import type { FactorMeta } from "../api/client";

/**
 * 因子观测台展示层口径（纯函数，供页面渲染与回归脚本共用）。
 *
 * 依据：docs/experiments/factor-panel-value-2026-09-05.md（第三次独立重建
 * 8561 条信号×因子对账）。要点：
 * - 有效（pass）：rv_pct / mom_121 / idio_vol —— 前排展开；
 * - 弱/否决（weak/inverse/fail）：默认折叠，不占首屏注意力；
 * - 「高波打折 / 短线超买 / 彩票股」对已确认信号无预测力或方向相反：
 *   文案降级为「读数」或「入口排雷」，不得作为信号否决依据。
 *
 * 红线不变：全部 research_proxy，不挡任何 LEI 技术信号；评级本身来自后端
 * FACTOR_META 实证留痕，本模块只做分组与文案，不另造评级。
 */

export const VERIFY_NOTE = "2026-09-05 复核";

export interface RiskChip {
  text: string;
  tone: "warn" | "caution" | "dim";
  title: string;
}

export interface ChipRow {
  rv_pct?: number | null;
  mom_20_group_pct?: number | null;
  ivol_pct?: number | null;
  notes: string[];
}

/** 风险标注 chips：只标读数与环境，不出买卖建议、不否决信号。 */
export function buildRiskChips(row: ChipRow): RiskChip[] {
  const chips: RiskChip[] = [];
  if (row.rv_pct != null && row.rv_pct >= 0.8) {
    chips.push({
      text: "高波·仅读数",
      tone: "caution",
      title: `${VERIFY_NOTE}：高波分位对已确认 LEI 信号无打折预测力（高波期信号 60 日均值反而更高，C 模块驱动）；读数仅作环境感知，不挡信号`,
    });
  }
  if (row.mom_20_group_pct != null && row.mom_20_group_pct >= 0.8) {
    chips.push({
      text: "短线超买·仅裸标的",
      tone: "caution",
      title: `${VERIFY_NOTE}：短动量反向效应只存在于无结构过滤的裸标的层；对已确认 LEI 信号无预测力（p=0.10），不作为否决依据`,
    });
  }
  if (row.ivol_pct != null && row.ivol_pct >= 0.8) {
    chips.push({
      text: "IVOL高·入口排雷",
      tone: "warn",
      title: `实证：高特质波动个股 18 年系统性跑输——排雷只用于自选池入口（选股前）；${VERIFY_NOTE}：对已确认信号反向（高IVOL信号 60 日 +12.1%），不否决已确认信号`,
    });
  }
  if (row.notes.some((n) => n.startsWith("数据较旧"))) {
    chips.push({ text: "数据较旧", tone: "dim", title: row.notes.join("；") });
  }
  return chips;
}

export interface CardLike {
  verdict_level: FactorMeta["verdict_level"];
}

export interface CardGroups<K extends string, V extends CardLike> {
  /** pass（实证稳健）：前排展开。 */
  primary: Array<[K, V]>;
  /** weak/inverse/fail：默认折叠。 */
  weak: Array<[K, V]>;
}

/** 评级卡按实证裁决分组：pass 展开，其余折叠（顺序保持 FACTOR_META 原序）。 */
export function groupFactorCards<K extends string, V extends CardLike>(
  factors: Record<K, V>,
): CardGroups<K, V> {
  const primary: Array<[K, V]> = [];
  const weak: Array<[K, V]> = [];
  for (const entry of Object.entries(factors) as Array<[K, V]>) {
    (entry[1].verdict_level === "pass" ? primary : weak).push(entry);
  }
  return { primary, weak };
}

/** 市场体制短语（页头 RV 横条右侧）：按 2026-09-05 复核的模块分层口径。 */
export function marketRegimePhrase(rvPct: number | null | undefined): string {
  if (rvPct == null) return "";
  if (rvPct >= 0.8) return "高波环境：2B/破底翻（C 模块）主场——趋势类模块不占优";
  if (rvPct <= 0.2) return "低波环境：C 模块不占优（D/B 优先为理论提示，当前规则下极少触发）";
  return "中波环境";
}

/** 标的表弱因子列（2026-09-05 复核：信号层无预测力或反向，默认折叠）。 */
export const WEAK_COLUMN_KEYS = ["mom_20", "mom_20_group_pct", "vol_ok", "adx14"] as const;
