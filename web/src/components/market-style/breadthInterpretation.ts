import type { BreadthReadingPoint } from "./breadthReadingTypes";

type Interpretation = { headline: string; meaning: string; watch: string; tone: "supportive" | "caution" | "neutral" | "unknown" };

const BY_CODE: Record<string, Interpretation> = {
  recovering: { headline: "低位参与回暖", meaning: "此前站上20日、50日均线的股票比例都很低，现在一起回升。", watch: "留意回升能否延续；这还不是底部确认。", tone: "supportive" },
  expanding: { headline: "上涨支撑增强", meaning: "站上20日、50日均线的股票比例一起上升，三个周期都已过半。", watch: "留意广泛参与能否维持。", tone: "supportive" },
  improving: { headline: "修复尚未完成", meaning: "站上20日、50日均线的股票比例一起上升，但还不能确认三个周期都已过半。", watch: "继续看较长期的参与能否跟上。", tone: "supportive" },
  retreating: { headline: "高位参与转弱", meaning: "此前站上20日、50日均线的股票比例都很高，现在一起回落。", watch: "留意回落是否继续；这还不是顶部确认。", tone: "caution" },
  weakening: { headline: "弱势仍在扩散", meaning: "站上20日、50日均线的股票比例一起下降，站上200日均线的仍不足半数。", watch: "先看参与面是否停止收缩。", tone: "caution" },
  contracting: { headline: "上涨支撑减弱", meaning: "站上20日、50日均线的股票比例一起下降。", watch: "留意下跌是否扩散到长期参与。", tone: "caution" },
  flat: { headline: "参与变化不大", meaning: "站上20日、50日均线的股票比例较5条记录前没有变化。", watch: "继续看下一段参与方向。", tone: "neutral" },
  mixed: { headline: "短中期方向不一", meaning: "站上20日、50日均线的股票比例变化方向不一致。", watch: "先看短中期参与能否趋于一致。", tone: "neutral" },
};

const UNKNOWN: Interpretation = { headline: "参与状态未知", meaning: "同日宽度或此前可比读数不足。", watch: "等待有效的同日资料。", tone: "unknown" };

/** Plain-language rendering of the existing backend state; no new thresholds or score. */
export function breadthInterpretation(reading?: BreadthReadingPoint | null): Interpretation {
  return reading ? BY_CODE[reading.state.code] ?? UNKNOWN : UNKNOWN;
}

const DIRECTION: Record<string, "up" | "down"> = {
  recovering: "up", expanding: "up", improving: "up",
  retreating: "down", weakening: "down", contracting: "down",
};

/** Mark sparse state changes using only that date and earlier states. */
export function breadthChangeAnnotations(
  dates: readonly string[], prices: readonly (number | null)[], readings: ReadonlyMap<string, BreadthReadingPoint>,
): { date: string; price: number; label: string; tone: "supportive" | "caution" }[] {
  const marks: { date: string; price: number; label: string; tone: "supportive" | "caution" }[] = [];
  let prior: "up" | "down" | undefined;
  let lastMark = -90;
  dates.forEach((date, index) => {
    const code = readings.get(date)?.state.code ?? "";
    const direction = DIRECTION[code];
    const price = prices[index];
    if (direction && direction !== prior && typeof price === "number" && Number.isFinite(price) && index - lastMark >= 90) {
      marks.push({ date, price, label: direction === "up" ? "参与回升" : "参与转弱", tone: direction === "up" ? "supportive" : "caution" });
      lastMark = index;
    }
    prior = direction;
  });
  return marks;
}
