import type { LineSeries } from "../market-style/MarketTrendChart";
import { amountMA20, priorMonthReference } from "./concentrationReferenceMath";
import type { MicroCard } from "./microstructureData";

export const CONCENTRATION_DAILY_SOURCE = "https://m.gelonghui.com/p/6907065";
const percent = (value: number) => `${value.toFixed(2)}%`;

type ReferenceDisplay = {
  overlays: LineSeries[];
  note: string;
  reading?: string;
  comparison?: string;
  dailySource?: string;
};

export function concentrationDisplay(card: MicroCard): ReferenceDisplay | null {
  const points = card.points;
  const latest = points[points.length - 1]?.value;
  if (card.id === "cn-monthly-amount-top5" && card.frequency === "monthly") {
    const main = priorMonthReference(points, 120);
    const recent = priorMonthReference(points, 60);
    const comparison = recent ? `近5年对照（${recent.sampleCount}月）：P80 ${percent(recent.p80)} · P90 ${percent(recent.p90)} · P95 ${percent(recent.p95)}；高于 ${recent.rank.toFixed(1)}% 的月份。` : undefined;
    if (!main || latest == null) return { overlays: [], note: "近10年可比月值不足，暂不画历史分位线。", comparison };
    const level = latest >= main.p95 ? "达到P95" : latest >= main.p90 ? "P90至P95" : latest >= main.p80 ? "P80至P90" : "低于P80";
    return {
      overlays: ([
        ["P80", main.p80, "#8a7761"], ["P90", main.p90, "#9d6236"], ["P95", main.p95, "#8b4d6f"],
      ] as const).map(([label, value, color]) => ({ name: `${label} ${percent(value)}`, color, dashed: true, values: points.map(() => value) })),
      reading: `高于近10年 ${main.rank.toFixed(1)}% 的月份 · ${level}`,
      note: `虚线仅作最新月参照：此前10年 ${main.sampleCount} 个有效月，不含本月和缺值。`,
      comparison,
    };
  }
  const top5 = card.id === "cn-daily-amount-top5";
  if (card.frequency !== "daily" || (!top5 && card.id !== "cn-daily-amount-top10")) return null;
  const ma = amountMA20(points);
  const lastAverage = ma[ma.length - 1];
  const overlays: LineSeries[] = ma.some(value => value !== null)
    ? [{ name: "20日均值", color: "#657770", dashed: false, values: ma }] : [];
  if (top5) overlays.push({ name: "中金研报参考 46%", color: "#986737", dashed: true, values: points.map(() => 46) });
  return {
    overlays,
    reading: lastAverage == null ? undefined : `20日均值 ${percent(lastAverage)}`,
    note: top5 ? "46% 对应研报的日频前5%原值；研报使用 Wind，本图使用 BaoStock。"
      : "20日均值只在连续20个交易日资料齐全时绘制。",
    dailySource: top5 ? CONCENTRATION_DAILY_SOURCE : undefined,
  };
}
