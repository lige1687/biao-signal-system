/**
 * 持仓赛道（portfolio_groups.group_key）→ 同方向公开市场参考指数/ETF 映射。
 *
 * 严格身份边界（遵循 docs/ops/agent-answer-style.md）：
 * - 这里仅提供「同方向公开市场趋势参考」，绝不冒充场外主动/联接基金的「自身行情」；
 * - 优先映射到流动性好的主流场内可交易 ETF，全部复用 /api/dashboard 既有缓存。
 */
export interface TrackBenchmarkSpec {
  groupKey: string;
  shortLabel: string;
  referenceSymbols: string[];
  noteCn?: string;
}

export const TRACK_BENCHMARKS: Record<string, TrackBenchmarkSpec> = {
  us_tech_active: {
    groupKey: "us_tech_active",
    shortLabel: "全球科技主动",
    referenceSymbols: ["XLK", "QQQ", "SOXX"],
  },
  cn_info: {
    groupKey: "cn_info",
    shortLabel: "A股科技/半导体",
    referenceSymbols: ["512480.SS", "159819.SZ", "515880.SS"],
  },
  us_growth_em: {
    groupKey: "us_growth_em",
    shortLabel: "全球成长/新兴",
    referenceSymbols: ["SPY", "QQQ", "^KS11"],
  },
  us_index: {
    groupKey: "us_index",
    shortLabel: "美股纳指/标普",
    referenceSymbols: ["SPY", "QQQ"],
  },
  cn_metal: {
    groupKey: "cn_metal",
    shortLabel: "A股有色金属",
    referenceSymbols: ["512400.SS", "518850.SS"],
  },
  hk_tech: {
    groupKey: "hk_tech",
    shortLabel: "恒生科技/互联网",
    referenceSymbols: ["^HSTECH", "^HSI"],
  },
  cn_green_other: {
    groupKey: "cn_green_other",
    shortLabel: "绿电/红利/消费",
    referenceSymbols: ["512890.SS", "515170.SS", "TH881145.SECTOR"],
  },
  stable: {
    groupKey: "stable",
    shortLabel: "稳健偏债",
    referenceSymbols: [],
    noteCn: "偏债底仓，不适用股票均线趋势参考",
  },
};
