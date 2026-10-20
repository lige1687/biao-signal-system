import type { Assessment, ChartPayload } from "../types";

/**
 * 趋势转折 5 条件提示条（显眼位置，置于 K 线图下方）。
 *
 * 口径来源（用户原则 + 规格 §4-§5）：
 * 趋势转折依次观察 5 步--破线、均线拐头、交叉、多头排列、乖离率。
 * MACD 只能表达后 3 步（交叉 / 多头排列 / 乖离率），前 2 步（破线 / 均线拐头）
 * 由系统既有数据补齐：破线看 LEI 颜色（close vs EMA20），均线拐头看抵扣价
 * （close vs close_lag20，规格 §4.2 / app.py 原则：价高于抵扣价->MA20 向上）。
 *
 * 红线：后 3 步是 MACD 佐证，属研究代理的「强度」描述，**不构成买点**
 * （金叉/死叉只是强度转向，见 macd-reading skill）。本条只作状态陈列，不下结论。
 */

export type Stance = "bull" | "bear" | "neutral" | "unknown";
export type CondGroup = "system" | "macd";

export interface TrendCondition {
  key: string;
  name: string;
  status: string;
  stance: Stance;
  source: string;
  group: CondGroup;
  detail?: string;
  /** 研究代理标记：后 3 步用 MACD，强度非转折。 */
  proxy: boolean;
}

const STANCE_COLOR: Record<Stance, string> = {
  bull: "var(--lei-green)",
  bear: "var(--up)",
  neutral: "var(--text-faint)",
  unknown: "var(--text-faint)",
};

/** 取序列最后一个非空值。 */
function lastNum(arr: (number | null)[]): number | null {
  for (let i = arr.length - 1; i >= 0; i--) {
    if (arr[i] != null) return arr[i] as number;
  }
  return null;
}

/**
 * 取序列最后两个非空值（按原顺序：[prev, cur]）。
 * 用于交叉检测需要前后两根对比。
 */
function lastTwoNums(arr: (number | null)[]): [number | null, number | null] {
  const vals: number[] = [];
  for (let i = arr.length - 1; i >= 0 && vals.length < 2; i--) {
    if (arr[i] != null) vals.push(arr[i] as number);
  }
  if (vals.length === 0) return [null, null];
  if (vals.length === 1) return [null, vals[0]];
  return [vals[1], vals[0]]; // [prev, cur]
}

function fmt(n: number, dp = 4): string {
  return Number.isFinite(n) ? n.toFixed(dp) : "-";
}

/** 计算 5 条件。纯函数，便于将来单测。 */
export function computeTrendChecklist(
  payload: ChartPayload,
  assessment: Assessment | null,
): TrendCondition[] {
  const close = payload.lastClose ?? lastNum(payload.ohlc.map((b) => b[1]));
  const ema20 = lastNum(payload.ema20);
  const ema120 = lastNum(payload.ema120);
  const ref20 = lastNum(payload.ref20); // 20 周期抵扣价
  const [difPrev, difCur] = lastTwoNums(payload.macdDif);
  const [deaPrev, deaCur] = lastTwoNums(payload.macdDea);

  // 1. 破线（系统资源 · LEI 颜色）：收盘 vs EMA20
  let breakLine: TrendCondition;
  if (close == null || ema20 == null) {
    breakLine = mk("break_line", "破线", "数据不足", "unknown", "LEI 颜色", "system");
  } else if (close > ema20) {
    breakLine = mk("break_line", "破线", "站上 EMA20", "bull", "LEI 颜色", "system",
      assessment?.color_cn || undefined);
  } else if (close < ema20) {
    breakLine = mk("break_line", "破线", "跌破 EMA20", "bear", "LEI 颜色", "system",
      assessment?.color_cn || undefined);
  } else {
    breakLine = mk("break_line", "破线", "贴近 EMA20", "neutral", "LEI 颜色", "system",
      assessment?.color_cn || undefined);
  }

  // 2. 均线拐头（系统资源 · 抵扣价）：close vs close_lag20
  let maTurn: TrendCondition;
  if (close == null || ref20 == null) {
    maTurn = mk("ma_turn", "均线拐头", "数据不足", "unknown", "抵扣价", "system");
  } else {
    const pct = close > 0 ? (close - ref20) / close : 0;
    if (pct > 0.001) {
      maTurn = mk("ma_turn", "均线拐头", "MA20 向上", "bull", "抵扣价", "system", fmt(ref20));
    } else if (pct < -0.001) {
      maTurn = mk("ma_turn", "均线拐头", "MA20 向下", "bear", "抵扣价", "system", fmt(ref20));
    } else {
      maTurn = mk("ma_turn", "均线拐头", "MA20 走平", "neutral", "抵扣价", "system", fmt(ref20));
    }
  }

  // 3. 交叉（MACD 佐证 · 研究代理）：DIF 与 DEA 金叉/死叉
  let cross: TrendCondition;
  if (difCur == null || deaCur == null) {
    cross = mk("cross", "交叉", "数据不足", "unknown", "MACD", "macd", undefined, true);
  } else {
    const curDiff = difCur - deaCur;
    const prevDiff = difPrev != null && deaPrev != null ? difPrev - deaPrev : null;
    let status: string;
    let stance: Stance;
    if (prevDiff != null && prevDiff <= 0 && curDiff > 0) {
      status = "金叉"; stance = "bull";
    } else if (prevDiff != null && prevDiff >= 0 && curDiff < 0) {
      status = "死叉"; stance = "bear";
    } else if (curDiff > 0) {
      status = "DIF>DEA 多头态"; stance = "bull";
    } else {
      status = "DIF<DEA 空头态"; stance = "bear";
    }
    cross = mk("cross", "交叉", status, stance, "MACD", "macd",
      `DIF ${fmt(difCur)} / DEA ${fmt(deaCur)}`, true);
  }

  // 4. 多头排列（MACD 佐证 · 研究代理）
  // 口径（对齐系统正式规则 ma_full_alignment）：SMA20>SMA60>SMA120 且三线斜率
  // 均向上 = 完整多头排列（空头对称），否则未完整排列。
  // MACD 佐证 = DIF>0：DIF>0 ⟺ EMA12>EMA26（数学恒等的两线多头排列）。
  // 数据审计（40 标的全历史）：完整多头排列成立日 98.8% 同时 DIF>0，
  // 非排列日仅 38% DIF>0 --故 DIF>0 只作佐证、不作判定。
  let align: TrendCondition;
  const [sma20Prev, sma20Cur] = lastTwoNums(payload.sma20);
  const [sma60Prev, sma60Cur] = lastTwoNums(payload.sma60);
  const [sma120Prev, sma120Cur] = lastTwoNums(payload.sma120);
  const slopeUp = (cur: number | null, prev: number | null) =>
    cur != null && prev != null && cur > prev;
  if (sma20Cur == null || sma60Cur == null || sma120Cur == null) {
    align = mk("alignment", "多头排列", "数据不足", "unknown", "均线+MACD", "macd", undefined, true);
  } else {
    const order = sma20Cur > sma60Cur && sma60Cur > sma120Cur;
    const orderBear = sma20Cur < sma60Cur && sma60Cur < sma120Cur;
    const slopesUp =
      slopeUp(sma20Cur, sma20Prev) && slopeUp(sma60Cur, sma60Prev) && slopeUp(sma120Cur, sma120Prev);
    const slopesDown =
      sma20Prev != null && sma60Prev != null && sma120Prev != null &&
      sma20Cur < sma20Prev && sma60Cur < sma60Prev && sma120Cur < sma120Prev;
    let status: string;
    let stance: Stance;
    if (order && slopesUp) { status = "完整多头排列"; stance = "bull"; }
    else if (orderBear && slopesDown) { status = "完整空头排列"; stance = "bear"; }
    else if (order || orderBear) { status = "有序未同向"; stance = "neutral"; }
    else { status = "未完整排列"; stance = "neutral"; }
    const corrob = difCur != null ? (difCur > 0 ? "DIF>0 佐证" : "DIF<0 不佐证") : undefined;
    align = mk("alignment", "多头排列", status, stance, "均线+MACD", "macd", corrob, true);
  }

  // 5. 乖离率（MACD 佐证 · 研究代理）
  // 均线扩散/密集 = |DIF|（EMA12-EMA26 两线间距）的同号趋势：放大=扩散、缩小=收敛。
  // 这是一阶口径（乖离本身）；hist 是二阶动能，两者趋势 54% 的 bar 不一致，各答各的
  // 问题，不能混用。DIF 变号那根 = EMA12 穿越 EMA26（两线交叉），不算扩散/收敛。
  // 价格乖离 = bias_ema120 = close/EMA120-1（账本登记口径，rules.v1.yaml），
  // |乖离|>=50% 为极端（bias_extreme=0.50，规格 §4.7 待确认值，极端是风险标记非方向支持）。
  let bias: TrendCondition;
  if (close == null || ema120 == null || ema120 <= 0 || difCur == null) {
    bias = mk("bias", "乖离率", "数据不足", "unknown", "MACD", "macd", undefined, true);
  } else {
    const biasPct = (close / ema120 - 1) * 100;
    const difPct = (difCur / close) * 100; // 两线乖离 DIF/收盘，跨标的可比
    const extreme = Math.abs(biasPct) >= 50;
    const sameSignDif = difPrev != null && difCur * difPrev > 0;
    const spreading = sameSignDif && difPrev != null && Math.abs(difCur) > Math.abs(difPrev);
    let status: string;
    let stance: Stance;
    if (extreme) {
      status = "极端乖离"; stance = "neutral";
    } else if (!sameSignDif) {
      status = difCur > 0 ? "两线乖离转正" : "两线乖离转负";
      stance = difCur > 0 ? "bull" : "bear";
    } else if (spreading) {
      status = "均线乖离扩散"; stance = difCur > 0 ? "bull" : "bear";
    } else {
      status = "均线乖离收敛"; stance = "neutral";
    }
    const sign2 = difPct >= 0 ? "+" : "";
    const sign120 = biasPct >= 0 ? "+" : "";
    bias = mk("bias", "乖离率", status, stance, "MACD", "macd",
      `两线乖离 ${sign2}${difPct.toFixed(2)}% · EMA120 ${sign120}${biasPct.toFixed(1)}%`, true);
  }

  return [breakLine, maTurn, cross, align, bias];
}

function mk(
  key: string, name: string, status: string, stance: Stance,
  source: string, group: CondGroup, detail?: string, proxy = false,
): TrendCondition {
  return { key, name, status, stance, source, group, detail, proxy };
}

interface Props {
  payload: ChartPayload;
  assessment: Assessment | null;
}

export default function TrendChecklist({ payload, assessment }: Props) {
  const conds = computeTrendChecklist(payload, assessment);
  const systemConds = conds.filter((c) => c.group === "system");
  const macdConds = conds.filter((c) => c.group === "macd");

  return (
    <div className="trend-checklist" role="group" aria-label="趋势转折 5 条件">
      <div className="tc-title">
        <span className="tc-title-main">趋势转折 5 条件</span>
        <span className="tc-title-sub">
          前 2 项系统资源 · 后 3 项 MACD 佐证（研究代理，强度非买点）
        </span>
      </div>
      <div className="tc-row">
        <div className="tc-group">
          <span className="tc-group-label">系统资源</span>
          {systemConds.map((c) => <CondChip key={c.key} c={c} />)}
        </div>
        <div className="tc-divider" />
        <div className="tc-group">
          <span className="tc-group-label">MACD 佐证</span>
          {macdConds.map((c) => <CondChip key={c.key} c={c} />)}
        </div>
      </div>
    </div>
  );
}

function CondChip({ c }: { c: TrendCondition }) {
  return (
    <div
      className={`tc-chip ${c.stance}`}
      title={c.proxy ? "研究代理：强度描述，不构成买点" : undefined}
    >
      <span className="tc-dot" style={{ background: STANCE_COLOR[c.stance] }} />
      <span className="tc-name">{c.name}</span>
      <span className="tc-status" style={{ color: STANCE_COLOR[c.stance] }}>{c.status}</span>
      {c.detail && <span className="tc-detail">{c.detail}</span>}
      <span className="tc-source">{c.source}{c.proxy ? " · 研究代理" : ""}</span>
    </div>
  );
}
