/** MSCI 官方事实表的有限月末摘录，仅供本地阅读样例。 */
export type StylePeriod = "oneMonth" | "threeMonths" | "ytd" | "oneYear";
export type SectorName =
  | "信息技术" | "金融" | "工业" | "能源" | "医疗保健" | "通信服务"
  | "原材料" | "可选消费" | "日常消费" | "公用事业" | "房地产";

export type StyleReturns = Record<StylePeriod, number>;
export type StyleHolding = { name: string; weightPct: number };
export type StyleSnapshot = {
  id: "momentum" | "quality" | "value" | "minimumVolatility";
  name: string;
  officialName: string;
  launchDate: string;
  sourceUrl: string;
  returnsPct: StyleReturns;
  threeYearAnnualizedVolPct: number;
  pe: number;
  pb: number;
  dividendYieldPct: number;
  topTenTotalPct: number;
  topTen: StyleHolding[];
  sectorWeightsPct: Record<SectorName, number | null>;
  note?: string;
};

export const STYLE_SNAPSHOT_DATE = "2026-09-30";
export const STYLE_RETURN_BASIS = "美元毛总回报";
export const STYLE_RISK_BASIS = "截至 2026-09-30 的近 3 年年化波动，按月度毛收益计算";
export const SECTOR_ORDER: SectorName[] = [
  "信息技术", "金融", "工业", "能源", "医疗保健", "通信服务",
  "原材料", "可选消费", "日常消费", "公用事业", "房地产",
];

export const WORLD_PARENT = {
  name: "MSCI World",
  returnsPct: { oneMonth: -1.15, threeMonths: 1.96, ytd: 12.09, oneYear: 15.68 },
  threeYearAnnualizedVolPct: 11.86,
  pe: 22.69,
  pb: 4.10,
  dividendYieldPct: 1.52,
} as const;

export const STYLE_SNAPSHOTS: StyleSnapshot[] = [
  {
    id: "momentum", name: "动量", officialName: "MSCI World Momentum Index (USD)",
    launchDate: "2013-12-11",
    sourceUrl: "https://www.msci.com/documents/10199/255599/msci-world-momentum-index-usd-gross.pdf",
    returnsPct: { oneMonth: 3.64, threeMonths: -4.55, ytd: 22.72, oneYear: 23.83 },
    threeYearAnnualizedVolPct: 17.34, pe: 24.48, pb: 4.08, dividendYieldPct: 1.44,
    topTenTotalPct: 29.50,
    topTen: [
      { name: "Micron Technology", weightPct: 5.55 },
      { name: "Advanced Micro Devices", weightPct: 4.62 },
      { name: "Intel Corp", weightPct: 3.09 },
      { name: "ASML Hldg", weightPct: 2.70 },
      { name: "Alphabet A", weightPct: 2.70 },
      { name: "Johnson & Johnson", weightPct: 2.41 },
      { name: "ExxonMobil Holdings", weightPct: 2.28 },
      { name: "Alphabet C", weightPct: 2.14 },
      { name: "Lam Research Corp", weightPct: 2.02 },
      { name: "Applied Materials", weightPct: 2.00 },
    ],
    sectorWeightsPct: {
      信息技术: 40.18, 金融: 15.77, 工业: 11.13, 能源: 10.18, 医疗保健: 8.08,
      通信服务: 5.16, 原材料: 2.90, 可选消费: 2.15, 日常消费: 1.72,
      公用事业: 1.62, 房地产: 1.12,
    },
  },
  {
    id: "quality", name: "质量", officialName: "MSCI World Quality Index (USD)",
    launchDate: "2012-12-18",
    sourceUrl: "https://www.msci.com/documents/10199/255599/msci-world-quality-index.pdf",
    returnsPct: { oneMonth: -0.25, threeMonths: 1.03, ytd: 10.72, oneYear: 15.27 },
    threeYearAnnualizedVolPct: 12.47, pe: 25.97, pb: 8.90, dividendYieldPct: 1.20,
    topTenTotalPct: 39.24,
    topTen: [
      { name: "Microsoft Corp", weightPct: 5.90 },
      { name: "Meta Platforms A", weightPct: 5.50 },
      { name: "Apple", weightPct: 5.35 },
      { name: "Nvidia", weightPct: 4.97 },
      { name: "Broadcom", weightPct: 4.10 },
      { name: "Lilly (Eli) & Company", weightPct: 3.50 },
      { name: "ASML Hldg", weightPct: 2.87 },
      { name: "Visa A", weightPct: 2.63 },
      { name: "Alphabet A", weightPct: 2.38 },
      { name: "Johnson & Johnson", weightPct: 2.02 },
    ],
    sectorWeightsPct: {
      信息技术: 38.63, 金融: 8.89, 工业: 12.68, 能源: 0.07, 医疗保健: 14.58,
      通信服务: 11.56, 原材料: 2.47, 可选消费: 3.57, 日常消费: 7.42,
      公用事业: null, 房地产: 0.13,
    },
    note: "该质量指数允许行业比例偏离母指数，表现可能受行业配置影响；官方表未单列公用事业权重。",
  },
  {
    id: "value", name: "价值", officialName: "MSCI World Value Index (USD)",
    launchDate: "1997-12-08",
    sourceUrl: "https://www.msci.com/documents/10199/255599/msci-world-value-index.pdf",
    returnsPct: { oneMonth: -2.21, threeMonths: 3.97, ytd: 15.27, oneYear: 19.28 },
    threeYearAnnualizedVolPct: 11.27, pe: 18.36, pb: 2.75, dividendYieldPct: 2.34,
    topTenTotalPct: 23.74,
    topTen: [
      { name: "Microsoft Corp", weightPct: 8.01 },
      { name: "Meta Platforms A", weightPct: 3.53 },
      { name: "Micron Technology", weightPct: 2.66 },
      { name: "JPMorgan Chase & Co", weightPct: 1.95 },
      { name: "Berkshire Hathaway B", weightPct: 1.55 },
      { name: "ExxonMobil Holdings", weightPct: 1.49 },
      { name: "Johnson & Johnson", weightPct: 1.41 },
      { name: "Intel Corp", weightPct: 1.17 },
      { name: "AbbVie", weightPct: 1.02 },
      { name: "Cisco Systems", weightPct: 0.94 },
    ],
    sectorWeightsPct: {
      信息技术: 18.78, 金融: 25.12, 工业: 9.26, 能源: 7.36, 医疗保健: 11.46,
      通信服务: 6.45, 原材料: 3.90, 可选消费: 4.23, 日常消费: 7.11,
      公用事业: 3.90, 房地产: 2.43,
    },
  },
  {
    id: "minimumVolatility", name: "最小波动", officialName: "MSCI World Minimum Volatility (USD) Index",
    launchDate: "2008-04-14",
    sourceUrl: "https://www.msci.com/documents/10199/255599/msci-world-minimum-volatility-index.pdf",
    returnsPct: { oneMonth: -3.65, threeMonths: 2.18, ytd: 3.52, oneYear: 3.13 },
    threeYearAnnualizedVolPct: 9.48, pe: 19.82, pb: 3.22, dividendYieldPct: 2.10,
    topTenTotalPct: 13.48,
    topTen: [
      { name: "Johnson & Johnson", weightPct: 1.51 },
      { name: "ExxonMobil Holdings", weightPct: 1.49 },
      { name: "Microsoft Corp", weightPct: 1.44 },
      { name: "Cisco Systems", weightPct: 1.37 },
      { name: "Nvidia", weightPct: 1.37 },
      { name: "Duke Energy Corp", weightPct: 1.32 },
      { name: "Motorola Solutions", weightPct: 1.30 },
      { name: "Berkshire Hathaway B", weightPct: 1.24 },
      { name: "Southern Company (The)", weightPct: 1.23 },
      { name: "AT&T", weightPct: 1.20 },
    ],
    sectorWeightsPct: {
      信息技术: 25.68, 金融: 13.80, 工业: 7.42, 能源: 4.93, 医疗保健: 14.41,
      通信服务: 9.93, 原材料: 0.47, 可选消费: 5.29, 日常消费: 9.73,
      公用事业: 7.14, 房地产: 1.20,
    },
    note: "采用有约束的组合优化来降低整体风险，不等于简单挑出单只波动最低的股票。",
  },
];
