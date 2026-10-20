/** 只引用系统返回的原价位，不根据自然语言生成信号或推算价位。 */
export interface AgentPriceLevel {
  role: string;
  price: number;
  kind: "below" | "above";
  dist_pct: number;
  from_cn: string;
}
export interface AgentPriceFocus {
  level: AgentPriceLevel;
  levels: AgentPriceLevel[];
  asOf?: string;
}
export function validPriceLevels(levels: AgentPriceLevel[]) {
  return levels.filter(l => Number.isFinite(l.price) && l.price > 0 && typeof l.role === "string" && l.role.length > 0);
}
export function findPriceMentions(text: string, levels: AgentPriceLevel[]) {
  const matches: { start: number; end: number; level: AgentPriceLevel }[] = [];
  for (const number of text.matchAll(/[+-]?\d+(?:\.\d+)?/g)) {
    const start = number.index!;
    const end = start + number[0].length;
    if (/[\w.\-]/.test(text[start - 1] ?? "") || /^[\w.%％年月日]/.test(text.slice(end).replace(/^[*`]+/, ""))) continue;
    const prefix = text.slice(Math.max(0, start - 64), start).replace(/[*`]/g, "");
    const candidates = validPriceLevels(levels).filter(level => {
      if (level.price !== Number(number[0])) return false;
      const role = level.role.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      return new RegExp(`${role}[\\s：:（(]*(?:为|是|在|约)?[\\s：:]*$`).test(prefix);
    });
    if (candidates.length === 1) matches.push({ start, end, level: candidates[0] });
  }
  return matches;
}
export function priceLineKind(level: AgentPriceLevel): "entry" | "stop" | "target" | "reference" {
  if (["失效位", "止损位", "止损价"].includes(level.role)) return "stop";
  if (["触发价", "入场价"].includes(level.role)) return "entry";
  if (["目标价", "目标位"].includes(level.role)) return "target";
  return "reference";
}
/**
 * 正文「买点①」序号是否可定位：只有系统返回的结构化候选（buyPointReview 的
 * notable 候选）覆盖到该序号时才可点；否则必须渲染为普通文字，不留假按钮。
 * 序号只在「回答生成时系统返回了候选数据」的上下文里才有意义——历史回答或
 * 无候选时一律不可定位，不从文本猜测。
 */
export function bpLocatable(index: number | null, notableCount: number): boolean {
  return index != null && index >= 0 && index < notableCount;
}

/** 仅改变图表纵轴的显示范围，确保已选参考线不会落在画面外。 */
export function priceAxisBounds(min: number, max: number, prices: number[]) {
  const valid = prices.filter(p => Number.isFinite(p) && p > 0);
  if (!valid.length || !Number.isFinite(min) || !Number.isFinite(max)) return null;
  const low = Math.min(min, ...valid), high = Math.max(max, ...valid);
  const padding = Math.max(high - low, Math.abs(high) * 0.01) * 0.05;
  return { min: low - padding, max: high + padding };
}
