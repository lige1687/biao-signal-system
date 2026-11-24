/** Descriptive observations only. No score, forecast, position, stop or trade action. */
export const OBSERVATION_REFERENCE = { version: "context-draft-2026-11-02", lowPercentile: 15, highPercentile: 85 } as const;

export type MarketId = "cn" | "us";
export type SignalId = "breadth50" | "erp" | "hv20" | "hv20Percentile" | "hv20Hv60Ratio" |
  "priceVsMa200" | "trend" | "financingFlow" | "financingBalanceChange20d" |
  "vix" | "hyOasChange20d" | "nfci" | "dr007OmoSpread" |
  "earningsRevisionBreadth" | "turnoverPercentile";
export type SignalQuality = "verified" | "provisional" | "missing" | "stale";
export type ContextSignal = {
  /** Current numerical observation. trend alone uses -1/0/1 for the original LEI direction. */
  value: number | null;
  /** Earlier comparable observation, for direction; never inferred from current level. */
  previous?: number | null;
  /** Historical position, 0..100, calculated only from prior observations. */
  percentile?: number | null;
  asOf: string;
  /** Actual publication/arrival date, if established. */
  publishedAt?: string;
  source: string;
  /** Exact stock or index universe, e.g. SP500, CN_ALL_A, CSI300, SHCOMP. */
  universe: string;
  /** Macro context has its own honest source universe; it never becomes stock-pool breadth. */
  scope?: "same_pool" | "market_context" | "background";
  /** Required when scope is market_context. */
  market?: MarketId;
  unit?: string;
  comparison?: string;
  frequency: "daily" | "weekly" | "monthly" | "snapshot";
  quality: SignalQuality;
  /** Required for DR007−OMO: verified policy reference actually applicable on asOf. Never default to an old fixed rate. */
  policyReference?: { rate: number; effectiveOn: string; verifiedFor: string; basis: string; verified: boolean };
  note?: string;
};
export type MarketContextInput = {
  market: MarketId;
  /** Date against which synchronous claims are checked. */
  asOf: string;
  /** Exact universe for a combined interpretation. Other universes remain background. */
  anchorUniverse: string;
  signals: Partial<Record<SignalId, ContextSignal>>;
};
export type ContextLayer = {
  id: "valuation" | "participation" | "leverage" | "stress";
  title: string;
  facts: string[];
  missing: string[];
};
export type CandidateId = "low_repair" | "low_pressure" | "rising_broad" | "rising_narrow_crowded" | "falling_funding_pressure";
export type ContextCandidate = {
  id: CandidateId;
  title: string;
  /** A supported explanation is still observational, never a market prediction. */
  status: "supported" | "partial" | "conflicted" | "unknown";
  facts: string[];
  interpretation: string;
  counterevidence: string[];
  missing: string[];
  nextObservation: string;
};
export type MarketContextResult = {
  asOf: string;
  anchorUniverse: string;
  layers: ContextLayer[];
  candidates: ContextCandidate[];
  limitations: string[];
};

const finite = (n: unknown): n is number => typeof n === "number" && Number.isFinite(n);
const titles: Record<SignalId, string> = {
  breadth50: "B50参与面", erp: "股债利差", hv20: "HV20实现波动", hv20Percentile: "HV20历史位置",
  hv20Hv60Ratio: "HV20/HV60", priceVsMa200: "价格相对MA200", trend: "原趋势方向",
  financingFlow: "股票融资买入占比", financingBalanceChange20d: "融资余额20日变化",
  vix: "VIX", hyOasChange20d: "HY OAS 20日变化", nfci: "NFCI",
  dr007OmoSpread: "DR007−OMO", earningsRevisionBreadth: "盈利预期修正广度",
  turnoverPercentile: "同池自由流通换手历史位置",
};
const layerIds: { id: ContextLayer["id"]; title: string; keys: SignalId[] }[] = [
  { id: "valuation", title: "估值与盈利", keys: ["erp", "earningsRevisionBreadth"] },
  { id: "participation", title: "趋势与宽度", keys: ["trend", "priceVsMa200", "breadth50"] },
  { id: "leverage", title: "热度与杠杆", keys: ["turnoverPercentile", "financingFlow", "financingBalanceChange20d"] },
  { id: "stress", title: "波动与资金", keys: ["hv20", "hv20Percentile", "hv20Hv60Ratio", "vix", "hyOasChange20d", "nfci", "dr007OmoSpread"] },
];

const macroMarket: Partial<Record<SignalId, MarketId>> = {
  vix: "us", hyOasChange20d: "us", nfci: "us", dr007OmoSpread: "cn",
};
function signalScope(key: SignalId, s: ContextSignal): ContextSignal["scope"] {
  return s.scope === "background" ? "background" : macroMarket[key] ? "market_context" : s.scope ?? "same_pool";
}

function reason(input: MarketContextInput, key: SignalId): string | null {
  const s = input.signals[key];
  if (!s || !finite(s.value)) return `${titles[key]}缺少有效读数`;
  if (s.quality === "missing" || s.quality === "stale") return `${titles[key]}${s.quality === "stale" ? "已过期" : "尚未核准"}`;
  if (!s.source || !s.universe || !s.asOf) return `${titles[key]}来源、范围或日期未核`;
  if (key === "dr007OmoSpread" && (!s.policyReference?.verified ||
      !finite(s.policyReference.rate) || !s.policyReference.effectiveOn ||
      s.policyReference.effectiveOn > input.asOf || s.policyReference.verifiedFor !== s.asOf || !s.policyReference.basis))
    return "DR007−OMO政策参照利率、适用日或招标机制未核；不能沿用旧固定利率";
  const scope = signalScope(key, s);
  if (scope === "background") return `${titles[key]}仅标为背景资料`;
  if (scope === "market_context" && !macroMarket[key]) return `${titles[key]}不是已定义的市场环境指标`;
  if (scope === "same_pool" && s.universe !== input.anchorUniverse) return `${titles[key]}属于${s.universe}，只作跨池背景`;
  if (scope === "market_context" && (macroMarket[key] !== input.market || (s.market && s.market !== input.market)))
    return `${titles[key]}不是${input.market === "cn" ? "A股" : "美股"}市场环境`;
  if (s.asOf > input.asOf) return `${titles[key]}观察日晚于当前观察日`;
  if (scope === "same_pool" && s.asOf !== input.asOf) return `${titles[key]}截至${s.asOf}，与同池观察日不同步`;
  if (s.publishedAt && s.publishedAt.slice(0, 10) > input.asOf) return `${titles[key]}在观察日之后才可知`;
  if (scope === "same_pool" && s.frequency !== "daily") return `${titles[key]}为${s.frequency}资料，不作日频同池确认`;
  return null;
}

function confirmationLimit(input: MarketContextInput, key: SignalId, s: ContextSignal): string[] {
  const out: string[] = [];
  if (s.quality !== "verified") out.push(`${titles[key]}读数尚未核准`);
  if (!s.publishedAt) out.push(`${titles[key]}首次可知时间未核`);
  if (s.asOf !== input.asOf) out.push(`${titles[key]}截至${s.asOf}，慢变量只作环境背景`);
  if (s.frequency !== "daily") out.push(`${titles[key]}为${s.frequency}资料，按真实发布后沿用`);
  return out;
}

function reading(input: MarketContextInput, key: SignalId): ContextSignal | null {
  return reason(input, key) === null ? input.signals[key]! : null;
}
function direction(s: ContextSignal | null): -1 | 0 | 1 | null {
  if (!s || !finite(s.previous)) return null;
  return s.value! > s.previous ? 1 : s.value! < s.previous ? -1 : 0;
}
function fact(key: SignalId, s: ContextSignal): string {
  const change = direction(s);
  const movement = change === null ? "变化未核" : change > 0 ? "较前次上升" : change < 0 ? "较前次下降" : "较前次不变";
  const pct = finite(s.percentile) && s.percentile >= 0 && s.percentile <= 100 ? `，历史位置P${s.percentile.toFixed(0)}` : "";
  const policy = key === "dr007OmoSpread" && s.policyReference
    ? `；政策参照${s.policyReference.rate}，${s.policyReference.basis}，${s.policyReference.effectiveOn}` : "";
  const window = s.comparison && change !== null ? `${s.comparison}${movement.replace("较前次", "")}` : movement;
  const value = key === "trend" ? s.value === 1 ? "向上" : s.value === -1 ? "向下" : "中性" : `${s.value}${s.unit ?? ""}`;
  return `${titles[key]} ${value}${pct}（${window}；${s.asOf}；${s.source}；${s.universe}${policy}）`;
}
function backgroundFact(input: MarketContextInput, key: SignalId): string | null {
  const s = input.signals[key];
  if (!s || !finite(s.value) || s.quality === "missing" || !s.source || !s.universe || !s.asOf ||
      s.asOf > input.asOf || (s.publishedAt && s.publishedAt.slice(0, 10) > input.asOf)) return null;
  if (key === "dr007OmoSpread" && (!s.policyReference?.verified || !finite(s.policyReference.rate) ||
      !s.policyReference.effectiveOn || s.policyReference.effectiveOn > input.asOf ||
      s.policyReference.verifiedFor !== s.asOf || !s.policyReference.basis)) return null;
  const why = reason(input, key);
  const qualification = why ?? confirmationLimit(input, key, s).join("；");
  return `${fact(key, s)}；${qualification || "背景资料，不作同池同日确认"}`;
}

type Criterion = { key: SignalId; test: (s: ContextSignal) => boolean; label: string; needs?: ("previous" | "percentile")[] };
type CandidateSpec = { id: CandidateId; title: string; criteria: Criterion[]; completeness: SignalId[]; counter: string; next: string; explanation: string };
const low = (s: ContextSignal) => finite(s.percentile) && s.percentile <= OBSERVATION_REFERENCE.lowPercentile;
const high = (s: ContextSignal) => finite(s.percentile) && s.percentile >= OBSERVATION_REFERENCE.highPercentile;
const specs: CandidateSpec[] = [
  { id: "low_repair", title: "低位修复观察", completeness: ["trend"], explanation: "低参与面出现扩散，估值和高波回落可作为并列线索；尚不能确认底部。", counter: "HV20下降也可能只是旧剧烈日滚出窗口；盈利预期可能仍下修，反弹也可能再创新低。", next: "看同池参与面能否继续扩散、原趋势是否确认，以及盈利预期有无恶化。", criteria: [
    { key: "breadth50", test: s => low(s) && direction(s) === 1, label: "低位B50开始扩散", needs: ["previous", "percentile"] },
    { key: "erp", test: high, label: "股债利差处较高历史位置", needs: ["percentile"] },
    { key: "hv20", test: s => direction(s) === -1, label: "HV20实际水平回落", needs: ["previous"] },
    { key: "hv20Percentile", test: s => s.value! >= OBSERVATION_REFERENCE.highPercentile && s.value! <= 100, label: "HV20仍处高历史位置" },
    { key: "hv20Hv60Ratio", test: s => s.previous! > 1 && s.value! < s.previous!, label: "HV20/HV60从高于1回落", needs: ["previous"] },
    { key: "hyOasChange20d", test: s => s.value! <= 0, label: "信用利差未走阔" },
    { key: "earningsRevisionBreadth", test: s => s.value! >= 0, label: "同池盈利预期未净下修" },
  ] },
  { id: "low_pressure", title: "低位承压", completeness: ["earningsRevisionBreadth"], explanation: "参与面和价格偏弱时，估值表面有吸引力仍可能被融资或盈利压力抵消。", counter: "低波阴跌不代表安全；短暂冷清也可能随后修复。", next: "核同池盈利修正与信用变化，再看参与面是否止跌。", criteria: [
    { key: "breadth50", test: s => low(s) && direction(s) !== 1, label: "B50处低位且未扩散", needs: ["previous", "percentile"] },
    { key: "trend", test: s => s.value === -1, label: "原趋势偏弱" },
    { key: "erp", test: high, label: "估值相对有吸引力", needs: ["percentile"] },
    { key: "hyOasChange20d", test: s => s.value! > 0, label: "信用利差走阔" },
  ] },
  { id: "rising_broad", title: "上涨扩散", completeness: [], explanation: "原趋势转强且同池参与面改善，说明上涨有更广的股票参与。", counter: "短反弹或行业集中仍可使指数上涨；盈利支持尚需另核。", next: "看B50扩散是否延续，以及盈利修正是否同步改善。", criteria: [
    { key: "trend", test: s => s.value === 1, label: "原趋势向上" },
    { key: "breadth50", test: s => direction(s) === 1, label: "B50参与面改善", needs: ["previous"] },
    { key: "hyOasChange20d", test: s => s.value! <= 0, label: "信用压力未增加" },
    { key: "earningsRevisionBreadth", test: s => s.value! >= 0, label: "同池盈利预期未净下修" },
  ] },
  { id: "rising_narrow_crowded", title: "上涨收窄且拥挤", completeness: ["earningsRevisionBreadth"], explanation: "价格仍强而同池参与面收窄，交易拥挤需由合格换手和融资流量另证。", counter: "龙头盈利上修、行业和市值结构变化也会导致等权参与面走弱；趋势可能延续。", next: "核同池换手与股票融资流量，拆分行业及权重，并观察原趋势是否转弱。", criteria: [
    { key: "trend", test: s => s.value === 1, label: "原趋势仍向上" },
    { key: "breadth50", test: s => direction(s) === -1, label: "B50参与面收窄", needs: ["previous"] },
    { key: "erp", test: s => direction(s) === -1, label: "股债利差下降", needs: ["previous"] },
    { key: "turnoverPercentile", test: high, label: "同池换手处较高历史位置", needs: ["percentile"] },
    { key: "financingBalanceChange20d", test: s => s.value! > 0, label: "融资余额20日增加" },
    { key: "financingFlow", test: high, label: "融资买入占比处较高历史位置", needs: ["percentile"] },
  ] },
  { id: "falling_funding_pressure", title: "下跌伴融资压力", completeness: ["financingFlow", "financingBalanceChange20d"], explanation: "趋势与参与面转弱，同时波动和资金压力增加，属于风险观察，不证明被动去杠杆。", counter: "融资余额下降也可能是主动还款；价格下跌改变市值分母，不能据此认定强平。", next: "看融资余额与同池股票融资流量，并核资金压力和波动是否延续。", criteria: [
    { key: "trend", test: s => s.value === -1, label: "原趋势向下" },
    { key: "breadth50", test: s => direction(s) === -1, label: "B50参与面下降", needs: ["previous"] },
    { key: "hv20", test: s => direction(s) === 1, label: "HV20实际水平上升", needs: ["previous"] },
    { key: "hyOasChange20d", test: s => s.value! > 0, label: "信用利差走阔" },
  ] },
];

export function interpretMarketContext(input: MarketContextInput): MarketContextResult {
  const layers = layerIds.map(({ id, title, keys }) => ({ id, title,
    facts: keys.filter(key => !macroMarket[key] || macroMarket[key] === input.market).flatMap(key => { const s = reading(input, key); const background = !s && backgroundFact(input, key);
      return s ? [`${fact(key, s)}${confirmationLimit(input, key, s).length ? `；${confirmationLimit(input, key, s).join("；")}` : ""}`] : background ? [background] : []; }),
    missing: keys.filter(key => !macroMarket[key] || macroMarket[key] === input.market).flatMap(key => { const why = reason(input, key); const s = reading(input, key);
      return why ? [why] : s ? confirmationLimit(input, key, s) : []; }),
  }));
  const candidates = specs.map(spec => {
    const supported: string[] = [];
    const contradicted: string[] = [];
    const missing: string[] = [];
    const criteria = spec.criteria.map(criterion => criterion.key !== "hyOasChange20d" || input.market === "us"
      ? criterion : { ...criterion, key: "dr007OmoSpread" as const,
        label: criterion.test({ value: -1 } as ContextSignal) ? "银行间资金价差未高于政策参照" : "银行间资金价差高于政策参照" });
    for (const criterion of criteria) {
      const s = reading(input, criterion.key);
      if (!s) missing.push(reason(input, criterion.key)!);
      else if (criterion.needs?.some(need => !finite(s[need]) ||
        (need === "percentile" && (s.percentile! < 0 || s.percentile! > 100))))
        missing.push(`${titles[criterion.key]}缺少可比前值或有效历史位置`);
      else if (criterion.test(s)) { supported.push(criterion.label); missing.push(...confirmationLimit(input, criterion.key, s)); }
      else if (criterion.key === "earningsRevisionBreadth" && s.value! < 0)
        contradicted.push(`同池盈利预期修正广度为${s.value}${s.unit ?? ""}，显示净下修，与该解释的盈利支撑相反`);
      else contradicted.push(`${criterion.label}未见支持`);
    }
    for (const key of spec.completeness) {
      const why = reason(input, key);
      if (why && !missing.includes(why)) missing.push(why);
      else { const s = reading(input, key); if (s) missing.push(...confirmationLimit(input, key, s)); }
    }
    const uniqueMissing = [...new Set(missing)];
    const status: ContextCandidate["status"] = contradicted.length ? "conflicted" :
      supported.length === criteria.length && uniqueMissing.length === 0 ? "supported" : supported.length ? "partial" : "unknown";
    return { id: spec.id, title: spec.title, status, facts: supported,
      interpretation: supported.length ? spec.explanation : "当前合格资料不足，不能形成该组合解释。",
      counterevidence: [spec.counter, ...contradicted], missing: uniqueMissing,
      nextObservation: spec.next };
  });
  const pressureConfirmed = candidates.some(row => row.id === "falling_funding_pressure" && row.status === "supported");
  const orderedCandidates = pressureConfirmed
    ? [...candidates].sort((a, b) => Number(b.id === "falling_funding_pressure") - Number(a.id === "falling_funding_pressure"))
    : candidates;
  return { asOf: input.asOf, anchorUniverse: input.anchorUniverse, layers, candidates: orderedCandidates,
    limitations: ["P15/P85仅为有版本的历史位置观察参考，未经收益验证。", "不同股票池只作背景；慢变量按真实发布后沿用，首次可知时间未核不作完整确认。", "候选解释不触发仓位、过滤、止损或交易动作。"] };
}
