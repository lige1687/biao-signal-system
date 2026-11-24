export const DEFAULT_HOME_IDS = ["cn-financing", "vix", "hy-oas", "turnover-concentration"];
export const HOME_BUILT_IN_IDS = new Set(["erp-cn", "focus-momentum"]);
export const HOME_HISTORICAL_IDS = new Set(["turnover-concentration", "focus-momentum", "downside-price-impact",
  "salience-str", "smallcap-turnover", "baker-wurgler", "ofr-fsi", "nfci", "finra-margin"]);
export const HOME_READINGS: Record<string, { label: string; dimension: string; reading: string }> = {
  "cn-financing": { label: "A股两融三合一", dimension: "杠杆参与", reading: "融资买入占比看交易热度，余额占比看存量杠杆水位；两者都不是净流入。" },
  vix: { label: "VIX · 标普500", dimension: "期权波动", reading: "升高＝预期波动加大，不代表涨跌方向。" },
  "hy-oas": { label: "美国高收益债利差", dimension: "信用压力", reading: "扩大＝企业借债的风险补偿要求增加。" },
  "turnover-concentration": { label: "沪深A股成交集中度", dimension: "交易集中", reading: "成交前5%股票占比越高，交易越集中。" },
  aaii: { label: "AAII · 看涨减看跌", dimension: "个人观点", reading: "正值＝受访个人中看涨者比看跌者多。" },
  naaim: { label: "NAAIM · 自报敞口", dimension: "管理人观点", reading: "受访管理人自报均值，不是全市场仓位。" },
};
type Point = { date: string; value: number | null };
/** Do not carry an older value across a missing last row or silently repair invalid dates. */
export function summarizeHomeSeries(id: string, input: readonly Point[], today: string) {
  const empty = { points: [] as Point[], value: null as number | null, date: null as string | null,
    change: null as number | null, previousDate: null as string | null, invalid: false };
  let previous = "";
  for (const row of input) {
    const day = row.date.length === 7 ? `${row.date}-01` : row.date;
    const time = Date.parse(day);
    if (!/^\d{4}-\d{2}(-\d{2})?$/.test(row.date) || !Number.isFinite(time)
      || new Date(time).toISOString().slice(0, 10) !== day || day > today || day <= previous) return { ...empty, invalid: true };
    previous = day;
  }
  const points = input.map(row => ({ ...row, value: typeof row.value === "number" && Number.isFinite(row.value) ? row.value : null }));
  const last = points[points.length - 1];
  const before = points[points.length - 2];
  return { points, value: last?.value ?? null, date: last?.date ?? null, invalid: false,
    change: id !== "baker-wurgler" && last?.value != null && before?.value != null ? last.value - before.value : null,
    previousDate: before?.date ?? null };
}
