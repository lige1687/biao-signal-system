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
  const ema60 = lastNum(payload.ema60);
  const ema120 = lastNum(payload.ema120);
  const sma20 = lastNum(payload.sma20);
  const sma60 = lastNum(payload.sma60);
  const sma120 = lastNum(payload.sma120);
  const ref20 = lastNum(payload.ref20); // 20 周期抵扣价
  const [difPrev, difCur] = lastTwoNums(payload.macdDif);
  const [deaPrev, deaCur] = lastTwoNums(payload.macdDea);
  const [histPrev, histCur] = lastTwoNums(payload.macdHist);

  // 1. 破线（系统资源 · LEI 颜色）：收盘 vs EMA20
  let breakLine: TrendCondition;
  if (close == null || ema20 == null) {
    breakLine = mk("break_line", "破线", "数据不足", "unknown", "LEI 颜色", "system");
  } else if (close > ema20) {
    breakLine = mk("break_line", "破线", "站上 EMA20", "bull", "LEI 颜色", "system",
      assessment?.color_cn ? `LEI 颜色 ${assessment.color_cn}` : undefined);
  } else if (close < ema20) {
    breakLine = mk("break_line", "破线", "跌破 EMA20", "bear", "LEI 颜色", "system",
      assessment?.color_cn ? `LEI 颜色 ${assessment.color_cn}` : undefined);
  } else {
    breakLine = mk("break_line", "破线", "贴近 EMA20", "neutral", "LEI 颜色", "system",
      assessment?.color_cn ? `LEI 颜色 ${assessment.color_cn}` : undefined);
  }

  // 2. 均线拐头（系统资源 · 抵扣价）：close vs close_lag20
  let maTurn: TrendCondition;
  if (close == null || ref20 == null) {
    maTurn = mk("ma_turn", "均线拐头", "数据不足", "unknown", "抵扣价", "system");
  } else {
    const pct = close > 0 ? (close - ref20) / close : 0;
    if (pct > 0.001) {
      maTurn = mk("ma_turn", "均线拐头", "MA20 向上", "bull", "抵扣价", "system", `抵扣价 ${fmt(ref20)}`);
    } else if (pct < -0.001) {
      maTurn = mk("ma_turn", "均线拐头", "MA20 向下", "bear", "抵扣价", "system", `抵扣价 ${fmt(ref20)}`);
    } else {
      maTurn = mk("ma_turn", "均线拐头", "MA20 走平", "neutral", "抵扣价", "system", `抵扣价 ${fmt(ref20)}`);
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

  // 4. 多头排列（MACD 佐证 · 研究代理）：六线排列 + DIF 0 轴佐证（规格 §4.5）
  let align: TrendCondition;
  if (ema20 == null || ema60 == null || ema120 == null || sma20 == null || sma60 == null || sma120 == null) {
    align = mk("alignment", "多头排列", "数据不足", "unknown", "均线+MACD", "macd", undefined, true);
  } else {
    const bullArr = ema20 > ema60 && ema60 > ema120 && sma20 > sma60 && sma60 > sma120;
    const bearArr = ema20 < ema60 && ema60 < ema120 && sma20 < sma60 && sma60 < sma120;
    let status: string;
    let stance: Stance;
    if (bullArr) { status = "多头排列"; stance = "bull"; }
    else if (bearArr) { status = "空头排列"; stance = "bear"; }
    else { status = "均线纠缠"; stance = "neutral"; }
    const corrob = difCur != null ? (difCur > 0 ? "DIF>0 佐证" : "DIF<0 不佐证") : undefined;
    align = mk("alignment", "多头排列", status, stance, "均线+MACD", "macd", corrob, true);
  }

  // 5. 乖离率（MACD 佐证 · 研究代理）：close vs EMA120 偏离 + 柱体扩散/收敛
  let bias: TrendCondition;
  if (close == null || ema120 == null || ema120 <= 0) {
    bias = mk("bias", "乖离率", "数据不足", "unknown", "MACD", "macd", undefined, true);
  } else {
    const biasPct = (close / ema120 - 1) * 100;
    const extreme = Math.abs(biasPct) >= 50; // 规格 §4.7：50% 以上为极端区域
    const expanding = histCur != null && histPrev != null && Math.abs(histCur) > Math.abs(histPrev);
    let status: string;
    let stance: Stance;
    if (extreme) {
      status = "极端乖离"; stance = biasPct > 0 ? "bull" : "bear";
    } else if (expanding) {
      status = "乖离扩散"; stance = biasPct > 0 ? "bull" : "bear";
    } else {
      status = "乖离收敛"; stance = "neutral";
    }
    bias = mk("bias", "乖离率", status, stance, "MACD", "macd",
      `偏离 EMA120 ${biasPct >= 0 ? "+" : ""}${biasPct.toFixed(1)}%`, true);
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
