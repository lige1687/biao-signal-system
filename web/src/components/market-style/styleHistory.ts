/** MSCI 事实表 2026-09-30 版的年度美元毛总回报（%）。 */
export type HistoryStyleId = "momentum" | "quality" | "value" | "minimumVolatility" | "world";

export type AnnualStyleReturns = {
  date: string;
  momentum: number;
  quality: number;
  value: number;
  minimumVolatility: number;
  world: number;
};

export const STYLE_HISTORY_SOURCE_DATE = "2026-09-30";
export const STYLE_HISTORY_BASE_DATE = "2013-12-31";
export const STYLE_HISTORY_SOURCES = {
  momentum: "https://www.msci.com/documents/10199/255599/msci-world-momentum-index-usd-gross.pdf",
  quality: "https://www.msci.com/documents/10199/255599/msci-world-quality-index.pdf",
  value: "https://www.msci.com/documents/10199/255599/msci-world-value-index.pdf",
  minimumVolatility: "https://www.msci.com/documents/10199/255599/msci-world-minimum-volatility-index.pdf",
} as const;

// 2014 起四个指数都已正式发布。2026-09-30 是年初至今收益，不能当作完整年度。
export const STYLE_ANNUAL_RETURNS: readonly AnnualStyleReturns[] = [
  { date: "2014-12-31", momentum: 7.03, quality: 9.01, value: 4.42, minimumVolatility: 12.06, world: 5.50 },
  { date: "2015-12-31", momentum: 4.54, quality: 4.25, value: -4.11, minimumVolatility: 5.82, world: -0.32 },
  { date: "2016-12-31", momentum: 4.75, quality: 5.12, value: 13.23, minimumVolatility: 8.18, world: 8.15 },
  { date: "2017-12-31", momentum: 32.59, quality: 26.64, value: 17.95, minimumVolatility: 18.04, world: 23.07 },
  { date: "2018-12-31", momentum: -2.38, quality: -5.06, value: -10.09, minimumVolatility: -1.42, world: -8.20 },
  { date: "2019-12-31", momentum: 28.26, quality: 36.70, value: 22.74, minimumVolatility: 23.97, world: 28.40 },
  { date: "2020-12-31", momentum: 28.70, quality: 22.73, value: -0.38, minimumVolatility: 3.26, world: 16.50 },
  { date: "2021-12-31", momentum: 14.95, quality: 26.10, value: 22.79, minimumVolatility: 14.84, world: 22.35 },
  { date: "2022-12-31", momentum: -17.34, quality: -21.90, value: -5.82, minimumVolatility: -9.28, world: -17.73 },
  { date: "2023-12-31", momentum: 12.25, quality: 32.97, value: 12.41, minimumVolatility: 8.14, world: 24.42 },
  { date: "2024-12-31", momentum: 30.56, quality: 18.85, value: 12.26, minimumVolatility: 11.53, world: 19.19 },
  { date: "2025-12-31", momentum: 21.75, quality: 16.94, value: 21.62, minimumVolatility: 11.16, world: 21.60 },
  { date: "2026-09-30", momentum: 22.72, quality: 10.72, value: 15.27, minimumVolatility: 3.52, world: 12.09 },
];

export const STYLE_HISTORY_IDS: readonly HistoryStyleId[] = ["momentum", "quality", "value", "minimumVolatility", "world"];

/** 100 是人为统一起点；以后只在官方年度终点连乘，不生成月度或日度收益。 */
export function buildStyleWealthHistory() {
  const first = {
    date: STYLE_HISTORY_BASE_DATE,
    momentum: 100, quality: 100, value: 100, minimumVolatility: 100, world: 100,
  };
  return STYLE_ANNUAL_RETURNS.reduce<(typeof first)[]>((points, row) => {
    const previous = points[points.length - 1];
    points.push({
      date: row.date,
      momentum: previous.momentum * (1 + row.momentum / 100),
      quality: previous.quality * (1 + row.quality / 100),
      value: previous.value * (1 + row.value / 100),
      minimumVolatility: previous.minimumVolatility * (1 + row.minimumVolatility / 100),
      world: previous.world * (1 + row.world / 100),
    });
    return points;
  }, [first]);
}
