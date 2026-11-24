/** Published interpretation examples; these never participate in alert or trading calculations. */
export const BREADTH_EXTERNAL_REFERENCES = {
  stockcharts: {
    name: "StockCharts",
    url: "https://chartschool.stockcharts.com/table-of-contents/market-indicators/percent-above-moving-average",
    verifiedOn: "2026-11-02",
    sma50: { lower: 30, upper: 70 },
    sma200: { majority: 50 },
  },
  schwab: {
    name: "Charles Schwab",
    url: "https://www.schwab.com/learn/story/breadth-check-strength-and-weakness-trend-tracker",
    publishedOn: "2025-06-26",
    verifiedOn: "2026-11-02",
    market: "SP500",
    sma50: { extremeWeaknessBelow: 10, broadParticipationAround: 80 },
  },
} as const;
