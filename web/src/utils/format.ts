/** 全站共享的数字/价格格式化，避免各组件小数位不一致。 */

/** 价格：≥100 用 2 位小数，<100 用 3 位（ETF 低价需要精度）。 */
export function fmtPrice(v: number | null | undefined): string {
  if (v == null) return "--";
  return v >= 100 ? v.toFixed(2) : v.toFixed(3);
}

/** 涨跌幅：带正负号 + %。 */
export function fmtChange(v: number | null | undefined): { text: string; cls: string } {
  if (v == null) return { text: "--", cls: "flat" };
  const cls = v > 0 ? "up" : v < 0 ? "down" : "flat";
  return { text: `${v > 0 ? "+" : ""}${v.toFixed(2)}%`, cls };
}

/** 大数收敛：成交量/成交额用万/亿。 */
export function fmtBig(n: number | null | undefined): string {
  if (n == null) return "--";
  const abs = Math.abs(n);
  if (abs >= 1e8) return `${(n / 1e8).toFixed(2)}亿`;
  if (abs >= 1e4) return `${(n / 1e4).toFixed(0)}万`;
  return String(n);
}

/** ISO 时间 -> HH:MM。 */
export function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "--";
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}
