export type DatedPoint = { date: string; value: number | null };

export interface FixedThresholdRail {
  value: number;
  label: string;
  shortLabel: string;
  color: string;
  meaning: string;
}

export interface DynamicThresholdSeries {
  key: string;
  name: string;
  shortLabelPrefix: string;
  color: string;
  dashed: boolean;
  byDate: Map<string, number>;
  latest: number | null;
}

export interface MetricThresholdBundle {
  id: string;
  unit: string;
  fixedRails: FixedThresholdRail[];
  dynamicSeries: DynamicThresholdSeries[];
  rationale: string;
  sizingGuide: string;
}

const isFiniteNum = (v: number | null | undefined): v is number =>
  typeof v === "number" && Number.isFinite(v);

function quantile(sorted: number[], p: number): number {
  const pos = (sorted.length - 1) * p;
  const lo = Math.floor(pos);
  const hi = Math.ceil(pos);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
}

/** Strict prior-window rolling quantile on clean sorted dated observations. */
export function rollingPriorQuantile(
  clean: { date: string; value: number }[],
  lookback: number,
  minObs: number,
  fraction: number,
): { byDate: Map<string, number>; latest: number | null } {
  const byDate = new Map<string, number>();
  let latest: number | null = null;
  for (let i = 0; i < clean.length; i++) {
    const prior = clean.slice(Math.max(0, i - lookback), i);
    if (prior.length < minObs) continue;
    const sorted = prior.map((p) => p.value).sort((a, b) => a - b);
    const val = quantile(sorted, fraction);
    byDate.set(clean[i].date, val);
    latest = val;
  }
  return { byDate, latest };
}

/** Rolling N-observation arithmetic mean on clean dated observations. */
export function rollingCleanMean(
  clean: { date: string; value: number }[],
  window = 20,
): { byDate: Map<string, number>; latest: number | null } {
  const byDate = new Map<string, number>();
  let latest: number | null = null;
  let running = 0;
  for (let i = 0; i < clean.length; i++) {
    running += clean[i].value;
    if (i >= window) running -= clean[i - window].value;
    if (i + 1 >= window) {
      const avg = running / window;
      byDate.set(clean[i].date, avg);
      latest = avg;
    }
  }
  return { byDate, latest };
}

export function cleanDatedPoints(points: DatedPoint[]): { date: string; value: number }[] {
  return points.filter(
    (p): p is { date: string; value: number } =>
      Boolean(p?.date) && /^\d{4}-\d{2}-\d{2}$/.test(p.date) && isFiniteNum(p.value),
  );
}

/**
 * 统一的小图 × 大图阈值与经验分位计算器。
 *
 * 设计原则：
 * 1. 右偏脉冲型（VIX / VXN / HY OAS）绝不套用对称 ±2σ（下轨触及率为0%），
 *    采用「期权/信贷定价机制线 + 20日均线斜率 + 滚动P85高波分位」三层参照；
 * 2. A股融资买入占比近正态对称，6.5% / 10.5% 分别对应近一年经验 P5 / P95；
 * 3. A股融资余额占比受市场扩容影响，采用过去3年（756交易日）滚动 P15 / P50 / P85。
 */
export function buildMetricThresholds(id: string, rawPoints: DatedPoint[]): MetricThresholdBundle | null {
  const clean = cleanDatedPoints(rawPoints);

  if (id === "vix") {
    const ma20 = rollingCleanMean(clean, 20);
    const p85 = rollingPriorQuantile(clean, 756, 252, 0.85);
    return {
      id,
      unit: "点",
      fixedRails: [
        {
          value: 20,
          label: "恐慌升温线 20",
          shortLabel: "升温 20",
          color: "#bc9974",
          meaning: "VIX 升破 20 代表市场开始紧张、波动明显加大。",
        },
        {
          value: 30,
          label: "极度恐慌线 30",
          shortLabel: "恐慌 30",
          color: "#986737",
          meaning: "VIX 升破 30 代表市场极度恐慌，很多机构被迫砍仓。",
        },
      ],
      dynamicSeries: [
        {
          key: "ma20",
          name: "20日均值",
          shortLabelPrefix: "20日均",
          color: "#64748b",
          dashed: false,
          byDate: ma20.byDate,
          latest: ma20.latest,
        },
        {
          key: "p85_3y",
          name: "近3年P85高位轨",
          shortLabelPrefix: "3年P85",
          color: "#7c6a96",
          dashed: true,
          byDate: p85.byDate,
          latest: p85.latest,
        },
      ],
      rationale:
        "VIX 平时趴在12~18附近，遇到风吹草动才会突然蹿高，所以用 20（开始紧张）和 30（极度恐慌）两道参考线搭配20日均线看最直观。",
      sizingGuide:
        "怎么看：VIX 超20但企业债利差很稳，多半只是情绪吓跌；若 VIX 超30，或企业借钱利差跟着飙升，新买仓位先减半；等它从高点回落再进场更稳。",
    };
  }

  if (id === "vxn") {
    const ma20 = rollingCleanMean(clean, 20);
    const p85 = rollingPriorQuantile(clean, 504, 180, 0.85);
    return {
      id,
      unit: "点",
      fixedRails: [
        {
          value: 25,
          label: "科技波动偏大 25",
          shortLabel: "偏大 25",
          color: "#bc9974",
          meaning: "纳指100科技股平时波动比标普大，25点大致相当于标普 VIX 的20点。",
        },
        {
          value: 35,
          label: "科技极恐慌 35",
          shortLabel: "恐慌 35",
          color: "#986737",
          meaning: "科技股进入剧烈恐慌区间。",
        },
      ],
      dynamicSeries: [
        {
          key: "ma20",
          name: "20日均值",
          shortLabelPrefix: "20日均",
          color: "#64748b",
          dashed: false,
          byDate: ma20.byDate,
          latest: ma20.latest,
        },
        {
          key: "p85_2y",
          name: "滚动P85高位轨",
          shortLabelPrefix: "P85",
          color: "#7c6a96",
          dashed: true,
          byDate: p85.byDate,
          latest: p85.latest,
        },
      ],
      rationale: "纳指100科技股波动天生比标普高4~5个点，因此用 25 / 35 两档参考线搭配20日均线观察。",
      sizingGuide: "对比 VXN 和 VIX，就能看出这波下跌是只跌科技股，还是整个美股都在跌。",
    };
  }

  if (id === "hy-oas") {
    const ma20 = rollingCleanMean(clean, 20);
    const p85 = rollingPriorQuantile(clean, 252, 126, 0.85);
    return {
      id,
      unit: "%",
      fixedRails: [
        {
          value: 4.0,
          label: "借钱偏贵警戒 4.0%",
          shortLabel: "警戒 4.0%",
          color: "#bc9974",
          meaning: "企业发债比美债多付4%利息，说明企业借钱开始变贵变难。",
        },
        {
          value: 5.0,
          label: "借钱极贵高压 5.0%",
          shortLabel: "高压 5.0%",
          color: "#986737",
          meaning: "超过5%往往说明市场开始担心经济衰退或公司违约（如2020年3月、2022年）。",
        },
      ],
      dynamicSeries: [
        {
          key: "ma20",
          name: "20日均值",
          shortLabelPrefix: "20日均",
          color: "#64748b",
          dashed: false,
          byDate: ma20.byDate,
          latest: ma20.latest,
        },
        {
          key: "p85_1y",
          name: "近1年P85高位轨",
          shortLabelPrefix: "1年P85",
          color: "#7c6a96",
          dashed: true,
          byDate: p85.byDate,
          latest: p85.latest,
        },
      ],
      rationale:
        "看美国公司发债借钱要比国债多付多少利息：平时好年景趴在3%左右，真出事时才会猛涨，所以用 4.0%（警戒）和 5.0%（危险）两道线把关。",
      sizingGuide:
        "怎么看：只要利差稳在 4% 以下，美股急跌多半只是虚惊一场；一旦20天猛涨超0.5个百分点或冲过4%~5%，说明真缺钱了，破位要果断减仓。",
    };
  }

  if (id === "cn-margin-buy") {
    const ma20 = rollingCleanMean(clean, 20);
    return {
      id,
      unit: "%",
      fixedRails: [
        {
          value: 6.5,
          label: "冷清线 6.5%（近1年最低5%）",
          shortLabel: "冷清 6.5%",
          color: "#327c72",
          meaning: "借钱买股占A股成交额不到6.5%，说明大家都不敢加杠杆买了。",
        },
        {
          value: 10.5,
          label: "过热线 10.5%（近1年最高5%）",
          shortLabel: "过热 10.5%",
          color: "#986737",
          meaning: "超过10.5%，说明短线成交很大一块都在靠借钱追涨。",
        },
      ],
      dynamicSeries: [
        {
          key: "ma20",
          name: "20日均值",
          shortLabelPrefix: "20日均",
          color: "#d97706",
          dashed: false,
          byDate: ma20.byDate,
          latest: ma20.latest,
        },
      ],
      rationale:
        "用当日借钱买股金额除以A股总成交额，平时大多在 6.5%～10.5% 之间来回摆动，用来看场内短线客冷热最直观。",
      sizingGuide:
        "怎么看：跌破 6.5% 代表情绪冷透了，等大盘站稳再进；冲破 10.5% 且大半股票开始掉队跌破20日线时，别再去追高。",
    };
  }

  if (id === "cn-margin-balance") {
    const p15 = rollingPriorQuantile(clean, 756, 504, 0.15);
    const p50 = rollingPriorQuantile(clean, 756, 504, 0.5);
    const p85 = rollingPriorQuantile(clean, 756, 504, 0.85);
    return {
      id,
      unit: "%",
      fixedRails: [],
      dynamicSeries: [
        {
          key: "p85_3y",
          name: "近3年P85上轨（盘子偏重）",
          shortLabelPrefix: "P85",
          color: "#986737",
          dashed: true,
          byDate: p85.byDate,
          latest: p85.latest,
        },
        {
          key: "p50_3y",
          name: "近3年P50中位线",
          shortLabelPrefix: "中位",
          color: "#64748b",
          dashed: true,
          byDate: p50.byDate,
          latest: p50.latest,
        },
        {
          key: "p15_3y",
          name: "近3年P15下轨（盘子已轻）",
          shortLabelPrefix: "P15",
          color: "#327c72",
          dashed: true,
          byDate: p15.byDate,
          latest: p15.latest,
        },
      ],
      rationale:
        "看全市场累计借了多少钱炒股（占流通市值比例），跟过去3年比一比，就能看出当前借钱盘子算重还是算轻。",
      sizingGuide:
        "怎么看：高于 P85 且多数股票走弱跌破均线时，小心上面融资套牢盘往下砸；低于 P15 说明借钱盘子已经卸得很轻了。",
    };
  }

  return null;
}
