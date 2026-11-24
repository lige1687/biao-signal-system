type Inputs = { breadth50?: number | null; breadthLow?: number | null;
  hvRatio?: number | null; hvPercentile?: number | null; financingChange?: number | null };
const valid = (value: number | null | undefined): value is number => typeof value === "number" && Number.isFinite(value);

/** Local, conditional reading of already displayed observations; no composite state. */
export function conditionalReading(input: Inputs): string[] {
  const readings: string[] = [];
  if (valid(input.breadth50) && valid(input.breadthLow) && input.breadth50 <= input.breadthLow &&
    valid(input.hvPercentile) && input.hvPercentile >= 15 && input.hvPercentile <= 85 &&
    valid(input.hvRatio) && input.hvRatio <= 1) {
    readings.push("参与面处于低位观察区，短期波动与中期持平或更小；这组读数反映上涨支撑偏弱，接着看参与面能否持续回升。");
  } else if (valid(input.hvRatio) && input.hvRatio > 1 && valid(input.hvPercentile) && input.hvPercentile < 85) {
    readings.push("短期波动高于中期，绝对水平仍低于历史高波参考；接着看价格起伏放大时，参与面和信用环境如何变化。");
  }
  if (valid(input.financingChange) && input.financingChange < 0) {
    readings.push("当前融资余额在下降，反映融资债务存量收缩；后续看降幅收窄还是扩大。");
  }
  return readings;
}

export type MarketReadingInput = Inputs & {
  market: "cn" | "us";
  breadthChange20?: number | null;
  erp?: number | null; erpLow?: number | null; erpHigh?: number | null;
  financingPercentile?: number | null;
  financingRatioChange?: number | null;
  hyChange20?: number | null;
};

/** Explain the observed relationship, not a causal claim or a trading state. */
export function marketReading(input: MarketReadingInput) {
  const weak = valid(input.breadth50) && valid(input.breadthLow) && input.breadth50 < input.breadthLow;
  const broad = valid(input.breadth50) && input.breadth50 > 50; // Literally a majority, not a calibrated threshold.
  const thinValue = valid(input.erp) && valid(input.erpLow) && input.erp < input.erpLow;
  const cheap = valid(input.erp) && valid(input.erpHigh) && input.erp > input.erpHigh;
  const ordinaryVol = valid(input.hvPercentile) && input.hvPercentile < 85;
  const highVol = valid(input.hvPercentile) && input.hvPercentile >= 85;
  const expandingVol = valid(input.hvRatio) && input.hvRatio > 1;
  const fundingDown = valid(input.financingChange) && input.financingChange < 0;
  const highLeverage = valid(input.financingPercentile) && input.financingPercentile >= 85;
  let headline = "参与面资料待补，先看已有读数";
  let meaning = "参与面看上涨覆盖，估值看价格缓冲，融资与波动看压力；当前先逐项查看已有读数。";
  let watch = "补齐参与面、估值与价格波动的同日读数后，再判断它们是否相互支持。";

  if (weak) {
    headline = fundingDown ? "参与面低迷、融资收缩，修复仍待确认" : "参与面处于低位，修复仍待确认";
    meaning = ordinaryVol
      ? "低宽度反映上涨支撑不足，指数波动低于历史高位参考；当前突出的是参与面疲弱，重点看支撑能否恢复。"
      : highVol && expandingVol
        ? "参与面偏弱与价格冲击放大同时出现，两项压力叠加；重点跟踪宽度回升与波动降温是否接续。"
        : "站上50日均线的股票偏少，反映上涨参与不足；波动变化可帮助区分持续疲弱与剧烈冲击。";
    if (cheap) meaning += "股债收益差显示较高估值缓冲；盈利与资金改善可为这种价格吸引力增加支持。";
    watch = "先看50日宽度能否回升、融资余额降幅能否收窄；若宽度继续下降且波动升入历史高区，压力可能在加重。";
    if (valid(input.breadthChange20) && input.breadthChange20 > 0) {
      meaning += "宽度较前期已有回升，当前处于低位修复阶段。";
    }
  } else if (broad && thinValue) {
    headline = valid(input.breadthChange20) && input.breadthChange20 > 0 ? "参与面回升，估值缓冲仍偏薄" : "多数股票仍有支撑，估值缓冲偏薄";
    meaning = "站上50日均线的成分股仍占多数，股债收益差低于历史低位线；合起来看，上涨参与较广、估值缓冲偏薄，重点跟踪参与面能否延续。";
    if (valid(input.breadthChange20) && input.breadthChange20 < 0) {
      meaning += "参与面较前期收窄，需要留意支撑是否进一步减弱。";
    } else if (valid(input.breadthChange20) && input.breadthChange20 > 0) {
      meaning += "参与面较前期回升，是目前的积极变化。";
    }
    watch = "重点看参与面是否转弱，以及信用利差是否持续走阔；两者同时恶化，比单看估值偏贵更值得警惕。";
  } else if (broad) {
    headline = "多数股票站上50日均线，关注支撑能否延续";
    meaning = "参与面目前提供支撑；仍需用估值判断价格缓冲，用波动与信用判断这种支撑是否变脆弱。";
    watch = "观察参与面是否保持或扩散，用股债收益差衡量价格缓冲，用资金条件跟踪压力变化。";
  } else if (valid(input.breadth50)) {
    headline = "参与面信号混合，先看改善还是收缩";
    meaning = "当前先看站上50日均线的股票比例是在回升还是下降，再结合估值、融资和波动判断支撑与压力。";
    watch = "优先比较50日宽度的前期变化，再看波动放大是否伴随参与面恶化。";
  }
  let conflict = "盈利预期与趋势资料待补，补齐后可继续观察企业盈利支撑和价格方向。";
  if (input.market === "cn" && highLeverage && fundingDown) {
    conflict = "融资占比仍在历史高位，融资余额正在下降：杠杆负担相对市值较高，近期融资债务在收缩。占比看相对负担，余额看增减。";
  } else if (input.market === "cn" && highLeverage && valid(input.financingChange) && input.financingChange > 0) {
    conflict = weak ? "融资占比偏高且余额增加，参与面却弱：需要警惕杠杆增加没有带来更广泛的价格支撑。"
      : "融资占比偏高且余额增加，反映杠杆负担较高、使用继续增加；参与面是否扩散，是接下来要跟踪的支撑变化。";
  } else if (input.market === "us" && valid(input.hyChange20)) {
    conflict = input.hyChange20 > 0
      ? `${valid(input.breadthChange20) && input.breadthChange20 > 0 ? "参与面回升、信用利差走阔：股市修复与信用压力并存。" : "信用利差较前期走阔，企业借债所需的风险补偿上升。"}观察走阔幅度及持续时间，可判断信用压力是在累积还是缓和。`
      : "信用风险补偿持平或下降，当前信用环境较前期稳定；接着看参与面能否改善。";
  }
  return { headline, meaning, conflict, watch };
}


export type ConnectionFact = { text: string; date?: string };
export type MarketConnection = { id: string; facts: ConnectionFact[]; meaning: string };
export type MarketConnectionInput = MarketReadingInput & {
  breadthDate?: string; breadthPreviousDate?: string;
  erpDate?: string; hvDate?: string; hv20?: number | null;
  financingRatio?: number | null; financingBalanceChangePct?: number | null;
  financingDate?: string; financingPreviousDate?: string; financingBalanceDate?: string; financingBalancePreviousDate?: string;
  hyDate?: string; hyPreviousDate?: string;
  vix?: number | null; vixHigh?: number | null; vixDate?: string;
};
const number = (value: number) => value.toFixed(2);
const changeText = (value: number, unit: string, from?: string) =>
  `${from ? `较${from}` : "较前期"}${value > 0 ? "上升" : value < 0 ? "下降" : "持平"}${value === 0 ? "" : `${number(Math.abs(value))}${unit}`}`;

/** Relationships among displayed observations only. Does not emit a signal, score or position. */
export function marketConnections(input: MarketConnectionInput) {
  const chains: MarketConnection[] = [];
  const weak = valid(input.breadth50) && valid(input.breadthLow) && input.breadth50 < input.breadthLow;
  const broad = valid(input.breadth50) && input.breadth50 > 50;
  const rising = valid(input.breadthChange20) && input.breadthChange20 > 0;
  const falling = valid(input.breadthChange20) && input.breadthChange20 < 0;
  const thinValue = valid(input.erp) && valid(input.erpLow) && input.erp < input.erpLow;
  const cheap = valid(input.erp) && valid(input.erpHigh) && input.erp > input.erpHigh;
  const highVol = valid(input.hvPercentile) && input.hvPercentile >= 85;
  const knownVol = valid(input.hvPercentile) && valid(input.hvRatio) && valid(input.hv20);
  const fundingDown = valid(input.financingChange) && input.financingChange < 0;
  const fundingUp = valid(input.financingChange) && input.financingChange > 0;
  const highLeverage = valid(input.financingPercentile) && input.financingPercentile >= 85;
  const creditWider = valid(input.hyChange20) && input.hyChange20 > 0;
  const breadth: ConnectionFact | null = valid(input.breadth50) ? {
    text: `${input.market === "cn" ? "全A" : "标普500"}宽度 ${number(input.breadth50)}%${valid(input.breadthChange20) ? `，${changeText(input.breadthChange20, "个百分点", input.breadthPreviousDate)}` : ""}${weak ? `；低于低位参考${number(input.breadthLow!) }%` : broad ? "；多数股票站上50日均线" : ""}`,
    date: input.breadthDate,
  } : null;
  const volatility: ConnectionFact | null = knownVol ? {
    text: `${input.market === "cn" ? "上证" : "标普500"}20日波动 ${number(input.hv20!)}%（年化），历史分位${number(input.hvPercentile!)}%；20/60日之比 ${number(input.hvRatio!)}`,
    date: input.hvDate,
  } : null;
  const valuation: ConnectionFact | null = valid(input.erp) && valid(input.erpLow) && valid(input.erpHigh) ? {
    text: `${input.market === "cn" ? "沪深300" : "标普500"}股债收益差 ${number(input.erp)} 个百分点${thinValue ? `，低于低位参考${number(input.erpLow)}` : cheap ? `，高于高位参考${number(input.erpHigh)}` : `，在历史参考${number(input.erpLow)}～${number(input.erpHigh)}之间`}`,
    date: input.erpDate,
  } : null;
  if (weak && breadth && volatility) {
    chains.push({ id: "participation-volatility", facts: [breadth, volatility], meaning: highVol
      ? input.hvRatio! > 1 ? "参与面疲弱，近期价格冲击也偏大；两项压力叠加，重点跟踪宽度回升与波动降温是否接续。"
        : "参与面仍弱，波动也仍在高位；短期起伏与中期持平或更小，后续看高波环境中上涨支撑能否恢复。"
      : `${rising ? "参与面虽有回升，仍在低位" : "参与面疲弱"}，指数波动低于历史高位参考；当前重点是上涨支撑何时恢复。` });
  }
  if (breadth && valuation) {
    chains.push({ id: "participation-valuation", facts: [breadth, valuation], meaning:
      thinValue ? `${rising ? "参与面在改善" : falling ? "参与面在收缩" : broad ? "参与面仍有支撑" : "参与面有待改善"}，估值缓冲却偏薄；${falling ? "参与收缩叠加偏薄的估值缓冲，需重点观察下跌压力。" : "当前可重点跟踪宽度：参与面继续扩散看支撑增强，转弱则留意估值与支撑两方面的压力。"}`
      : cheap ? `${weak ? "估值缓冲较高，参与面却弱" : "股债比较显示较高估值缓冲"}；股票相对债券的收益率差较大，后续用盈利与资金变化观察估值支撑。`
      : weak ? "参与面在低位，估值处历史中间区；重点看宽度能否持续回升。"
      : "估值处于历史中间区，重点跟踪参与面的扩散或收缩。" });
  }
  if (input.market === "cn" && valid(input.financingRatio) && valid(input.financingBalanceChangePct) && valid(input.financingChange)) {
    const ratio: ConnectionFact = { text: `融资占比 ${number(input.financingRatio)}%${valid(input.financingPercentile) ? `，高于历史${number(input.financingPercentile)}%的时期` : ""}${valid(input.financingRatioChange) ? `；${changeText(input.financingRatioChange, "个百分点", input.financingPreviousDate)}` : ""}`, date: input.financingDate };
    const balance: ConnectionFact = { text: `融资余额${changeText(input.financingBalanceChangePct, "%", input.financingBalancePreviousDate)}`, date: input.financingBalanceDate };
    chains.push({ id: "leverage-stock-flow", facts: [ratio, balance], meaning:
      fundingDown ? highLeverage ? "融资占比仍高，余额正在收缩；相对市值的杠杆负担较高，近期融资使用减少。占比看负担，余额看增减。"
        : `${weak ? rising ? "参与面虽回升，融资余额仍在收缩" : "参与面疲弱，融资余额也在收缩" : "融资余额在收缩"}；关注融资降幅能否收窄、宽度能否回升。`
      : fundingUp ? highLeverage && (weak || falling) ? "融资占比高且余额增加，参与面却弱；杠杆负担增加叠加支撑不足，需留意波动放大时的压力。"
        : "融资余额增加，反映杠杆使用回升；若参与面也持续改善，可一起观察融资增长与上涨支撑的扩散。"
      : "融资余额持平，表示融资债务存量稳定；占比的变化需结合流通市值一起读。" });
  }
  if (input.market === "us" && breadth && valid(input.hyChange20) && valid(input.breadthChange20)) {
    chains.push({ id: "participation-credit", facts: [breadth, {
      text: `高收益债利差${input.hyPreviousDate ? `较${input.hyPreviousDate}` : "较前期"}${creditWider ? "走阔" : input.hyChange20 < 0 ? "收窄" : "持平"}${input.hyChange20 === 0 ? "" : `${number(Math.abs(input.hyChange20) * 100)}基点`}`, date: input.hyDate,
    }], meaning: creditWider ? rising ? "股市修复与信用压力并存：参与面回升，信用利差却走阔；关注利差能否收窄。"
      : falling ? "参与面收缩，信用风险补偿也在上升；两项压力同向，需留意是否继续扩大。"
        : "信用风险补偿上升，股市参与面持平；当前新增压力来自信用端，重点跟踪利差走阔的幅度和持续时间。"
      : rising ? "参与面改善，信用风险补偿持平或下降；股市支撑与信用环境方向较协调，后续看改善能否延续。"
        : "信用风险补偿持平或下降，参与面仍在收缩或持平；当前重点是股市自身的上涨支撑何时恢复。" });
  }
  if (input.market === "us" && volatility && valid(input.vix) && valid(input.vixHigh) && input.vix > input.vixHigh && !highVol) {
    chains.push({ id: "realized-expected-volatility", facts: [volatility, { text: `VIX ${number(input.vix)} 指数点，高于历史高位参考${number(input.vixHigh)}`, date: input.vixDate }],
      meaning: "实际波动未入高位，期权却预期未来起伏较大；关注实际波动是否放大。" });
  }
  const headline = !breadth ? "参与面资料待补，先看已有指标"
    : input.market === "us" && rising && creditWider ? "参与面修复与信用压力并存"
    : thinValue && falling && fundingUp && highLeverage ? "参与面转弱，杠杆仍在增加"
    : weak ? rising ? "低位有修复，支撑仍需确认" : fundingDown ? "参与面低迷，融资也在收缩" : "参与面低迷，留意压力是否扩散"
    : broad && thinValue ? "多数股票有支撑，估值缓冲偏薄"
    : rising ? "参与面改善，核对其他条件是否跟上" : falling ? "参与面收缩，关注压力是否叠加" : "先看参与面，再核对估值与压力";
  return { headline, chains,
    improve: input.market === "cn" ? "宽度持续回升，融资余额降幅收窄或转增。"
      : "宽度回升，信用利差停止走阔。",
    deteriorate: input.market === "cn" ? "宽度回落，叠加波动进入高区或融资收缩加快。"
      : "宽度转弱，信用利差继续走阔。",
    limitation: input.market === "cn" ? "资金利率趋势与盈利预期仍待补齐。"
      : "盈利预期与趋势资料仍待补齐。",
  };
}
