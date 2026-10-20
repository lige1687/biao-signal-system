/**
 * K 线周期视图：把后端下发的**日线** ChartPayload 聚合成周线/月线。
 *
 * 纪律（重要）：聚合只做「展示」，**不产生任何新信号**。
 * 后端所有判定（LEI 三色 states、结构标记、参考线、MACD 事件、关键性波动）
 * 都是按日线口径算出来的，把它们平移到周/月线上会变成前端自造判定——
 * 因此聚合结果里这些字段一律清空，由 KlineChart 的 effectiveDisplay 同步
 * 关掉对应开关，并在图例区显式告知用户。
 *
 * 允许重算的只有均线（EMA/SMA）：它是纯数值指标，与「买卖/状态判定」无关，
 * 口径与后端 features/indicators.py::seeded_ema 保持一致（首窗口 SMA 作种子）。
 */
import type { ChartPayload } from "../types";

/** 周期：日（原始）/ 周（ISO 周聚合）/ 月（自然月聚合）。 */
export type Timeframe = "D" | "W" | "M";

export const TIMEFRAME_META: { key: Timeframe; label: string; title: string }[] = [
  { key: "D", label: "日", title: "日线：后端原始数据，LEI 信号与结构标记完整可用" },
  {
    key: "W",
    label: "周",
    title: "周线：按 ISO 周聚合日线的展示视图，不产生新信号（LEI 信号/结构标记不可用）",
  },
  {
    key: "M",
    label: "月",
    title: "月线：按自然月聚合日线的展示视图，不产生新信号（LEI 信号/结构标记不可用）",
  },
];

const TF_STORAGE_KEY = "kline.timeframe";

export function timeframeLabel(tf: Timeframe): string {
  return TIMEFRAME_META.find((t) => t.key === tf)?.label ?? "日";
}

/** 读取用户上次选的周期；无记录/异常一律回落日线（默认日线）。 */
export function loadTimeframe(): Timeframe {
  if (typeof window === "undefined") return "D";
  try {
    const raw = window.localStorage.getItem(TF_STORAGE_KEY);
    return raw === "W" || raw === "M" ? raw : "D";
  } catch {
    return "D"; // localStorage 不可用（隐私模式等）时仅本次会话有效
  }
}

export function saveTimeframe(tf: Timeframe): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(TF_STORAGE_KEY, tf);
  } catch {
    /* ignore */
  }
}

/**
 * 分组键。交易日历直接沿用日线序列本身的日期（不引入日历库）：
 * 相邻日期算出同一个键就归到同一根聚合 K 线，因此停牌/长假天然被跳过。
 *
 * 周用 ISO 周（以周四定 ISO 年，跨年那一周不会被切成两段）；月用自然月。
 */
function groupKey(date: string, tf: Timeframe): string {
  const y = Number(date.slice(0, 4));
  const m = Number(date.slice(5, 7));
  const d = Number(date.slice(8, 10));
  // 非预期日期格式：退化为「按日自成一组」，宁可不聚合也不错聚
  if (!y || !m || !d) return date;
  if (tf === "M") return `${y}-${String(m).padStart(2, "0")}`;
  const dt = new Date(Date.UTC(y, m - 1, d));
  const dayNum = dt.getUTCDay() || 7; // 周一=1 … 周日=7
  dt.setUTCDate(dt.getUTCDate() + 4 - dayNum); // 移到本 ISO 周的周四
  const isoYear = dt.getUTCFullYear();
  const yearStart = Date.UTC(isoYear, 0, 1);
  const week = Math.ceil(((dt.getTime() - yearStart) / 86400000 + 1) / 7);
  return `${isoYear}-W${String(week).padStart(2, "0")}`;
}

/** TradingView 风格 EMA，与后端 seeded_ema 同口径：首窗口 SMA 作种子，alpha=2/(n+1)。 */
function seededEma(values: number[], period: number): (number | null)[] {
  const out = new Array<number | null>(values.length).fill(null);
  if (period <= 0 || values.length < period) return out;
  let sum = 0;
  for (let i = 0; i < period; i++) sum += values[i];
  let prev = sum / period;
  out[period - 1] = prev;
  const alpha = 2 / (period + 1);
  for (let i = period; i < values.length; i++) {
    prev = alpha * values[i] + (1 - alpha) * prev;
    out[i] = prev;
  }
  return out;
}

/** 简单移动平均，前 period-1 根为 null（与后端 rolling(period).mean() 一致）。 */
function simpleMa(values: number[], period: number): (number | null)[] {
  const out = new Array<number | null>(values.length).fill(null);
  if (period <= 0 || values.length < period) return out;
  let sum = 0;
  for (let i = 0; i < values.length; i++) {
    sum += values[i];
    if (i >= period) sum -= values[i - period];
    if (i >= period - 1) out[i] = sum / period;
  }
  return out;
}

/**
 * 日线 → 周/月线聚合。
 *
 * 开盘 = 区间首个交易日开盘，收盘 = 区间末个交易日收盘，
 * 高/低 = 区间极值，量 = 区间求和；x 轴标签取区间**末个交易日**，
 * 这样最后一根聚合 K 线的收盘价与顶栏「最新价」天然一致。
 *
 * tf === "D" 时原样返回同一个对象引用（调用方 useMemo 依赖不变，零开销）。
 */
export function aggregateChartPayload(payload: ChartPayload, tf: Timeframe): ChartPayload {
  if (tf === "D") return payload;
  const n = payload.dates.length;
  if (n === 0) return payload;

  const dates: string[] = [];
  const ohlc: [number, number, number, number][] = [];
  const volumes: number[] = [];
  let curKey: string | null = null;

  for (let i = 0; i < n; i++) {
    const bar = payload.ohlc[i];
    if (!bar) continue;
    const [o, c, l, h] = bar; // ECharts 口径：[open, close, low, high]
    const vol = payload.volumes[i] ?? 0;
    const key = groupKey(payload.dates[i], tf);
    if (key !== curKey) {
      curKey = key;
      dates.push(payload.dates[i]);
      ohlc.push([o, c, l, h]);
      volumes.push(vol);
      continue;
    }
    const j = ohlc.length - 1;
    const g = ohlc[j];
    g[1] = c; // 收盘持续被区间内更晚的一天覆盖 → 末日收
    if (l < g[2]) g[2] = l;
    if (h > g[3]) g[3] = h;
    dates[j] = payload.dates[i]; // 标签持续覆盖 → 末个交易日
    volumes[j] += vol;
  }

  const m = ohlc.length;
  const closes = ohlc.map((b) => b[1]);
  const nulls = () => new Array<number | null>(m).fill(null);

  return {
    ...payload,
    dates,
    ohlc,
    volumes,
    // 均线：纯指标，在聚合后的收盘序列上重算（允许）
    ema20: seededEma(closes, 20),
    sma20: simpleMa(closes, 20),
    ema60: seededEma(closes, 60),
    sma60: simpleMa(closes, 60),
    ema120: seededEma(closes, 120),
    sma120: simpleMa(closes, 120),
    // ↓↓↓ 以下全是日线口径的判定结果，聚合视图一律清空，不做任何平移 ↓↓↓
    ref20: nulls(), // 抵扣价属于日线双均线判定的输入，不在聚合视图给出
    macdDif: nulls(),
    macdDea: nulls(),
    macdHist: nulls(),
    macdEvents: [],
    states: new Array<string>(m).fill("unknown"),
    b1Line: null,
    bottomLines: [],
    topLines: [],
    bottomMarks: [],
    topMarks: [],
    invalidatedMarks: [],
    keyVolatility: [],
    // 量能颜色改为纯涨跌（红涨绿跌，A股惯例）：日线的放量/缩量分级同样是
    // 日线口径判定，不平移到聚合视图。
    volStates: new Array<string>(m).fill(""),
    volColors: ohlc.map((b) => (b[1] >= b[0] ? payload.priceUp : payload.priceDown)),
    colorMode: "red_green",
    // symbol / displayName / priceUp / priceDown / stateColors / lastClose 沿用日线
  };
}
