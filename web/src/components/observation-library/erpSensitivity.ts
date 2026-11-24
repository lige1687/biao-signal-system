import type { ErpBandPoint } from "./erpBands";

export type ErpSigma = 1 | 1.5 | 2;
/** Display sensitivity only; the homepage's original 2-sigma alerts remain unchanged. */
export function withErpSigma(rows: readonly ErpBandPoint[], sigma: ErpSigma): ErpBandPoint[] {
  if (![1, 1.5, 2].includes(sigma)) throw new Error("未知轨道倍数");
  return rows.map(row => ({ ...row,
    upper: row.upper !== null && row.middle !== null && row.sigma !== null ? row.middle + sigma * row.sigma : null,
    lower: row.lower !== null && row.middle !== null && row.sigma !== null ? row.middle - sigma * row.sigma : null,
  }));
}
