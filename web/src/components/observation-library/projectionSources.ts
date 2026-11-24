import { useQuery } from "@tanstack/react-query";
import { api, fundamentalsApi } from "../../api/client";
import { VALUATION_SOURCES, valuationMonthlyPoints } from "./marketReferenceBands";
import type { RatesHistorySeries } from "../../types";
import { useRecentFocusMomentum } from "../focus-momentum/recent";
import { fromErpHistory, fromSurveyHistory, parseBaker, parseReused } from "./metricData";
import { ERP_REFERENCE_QUERY_KEY, ERP_REFERENCE_URL, fromErpReference, parseErpReference } from "./erpReferenceData";
import { erpBands, type ErpBandPoint } from "./erpBands";
import { CONCENTRATION_QUERY_KEY, CONCENTRATION_URL, fromConcentration, parseConcentration } from "./concentrationData";
import { CANDIDATE_QUERY_KEY, CANDIDATE_URL, HISTORICAL_CANDIDATE_IDS, fromCandidateHistory,
  parseCandidateHistory, type HistoricalCandidateId } from "./candidateData";

export interface ProjectionMetric {
  id: string;
  label: string;
  market: "cn" | "us";
  frequency: "daily" | "weekly" | "monthly";
  meaning: string;
  reading: string;
  scope: string;
}

/** Availability means a historical display adapter exists, not that today's value is current. */
export const PROJECTION_METRICS: readonly ProjectionMetric[] = [
  { id: "downside-price-impact", label: "下跌价格冲击 · 20日", market: "cn", frequency: "daily", meaning: "下跌幅度相对于成交额有多大，再取样本股票中位数。", reading: "升高表示单位成交额对应的跌幅变大；也受小市值股、成交萎缩与波动影响，不等于抛售资金量。", scope: "供应商覆盖沪深A股；20交易日观察，历史截至2026-10-23，非官方完整全A名单" },
  { id: "salience-str", label: "凸显收益偏向 · 20日", market: "cn", frequency: "daily", meaning: "更突出交易日的加权收益，相对普通平均收益偏高还是偏低。", reading: "正值表示加权平均收益高于普通均值，负值反之；即使每天都下跌也可能为正，不能用正负号判断市场方向。", scope: "供应商覆盖沪深A股；文献参数的独立20日改编，非论文月频模型或视频原式复刻" },
  { id: "turnover-concentration", label: "沪深A股成交额集中度", market: "cn", frequency: "monthly", meaning: "供应商覆盖的沪深A股中，月成交额前5%股票占同池成交额的比例。", reading: "越高说明交易越集中；不说明涨跌方向，也不是持仓或净流入比例。", scope: "供应商覆盖的沪深A股，含ST、期间上市和退出股票；2023-01—2026-07等输入不完整月份留空，非官方全市场精确复刻" },
  { id: "erp-cn", label: "沪深300股债利差", market: "cn", frequency: "daily", meaning: "沪深300盈利收益率减中国10年国债利率", reading: "上轨表示相对债券偏便宜，下轨表示相对偏贵；上下轨随历史移动。", scope: "沪深300；参照国信证券三年统计轨道，尚非作者视频逐点复刻" },
  { id: "erp-us", label: "标普500股债利差", market: "us", frequency: "daily", meaning: "标普500盈利收益率减美国10年国债利率", reading: "看股票相对债券的估值背景；日线包含月频盈利输入，不直接提示顶底。", scope: "标普500盈利口径；对照其他股指时仅观察同期联动" },
  { id: "focus-momentum", label: "焦点股动量", market: "cn", frequency: "daily", meaning: "成交活跃股票过去20日的涨跌", reading: "负值表示这组股票此前平均下跌，不能据此判断底部。", scope: "A股固定300股历史研究样本；截至2026-10-23，最新交易日尚未补齐" },
  { id: "vix", label: "VIX", market: "us", frequency: "daily", meaning: "标普500期权隐含的预期波动", reading: "越高表示期权市场预计波动越大，没有涨跌方向。", scope: "标普500期权；非美国所有股票" },
  { id: "vxn", label: "VXN", market: "us", frequency: "daily", meaning: "纳指100期权隐含的预期波动", reading: "越高表示期权市场预计波动越大，没有涨跌方向；与VIX不可互相替代。", scope: "纳指100（NDX）期权；非美国所有股票" },
  { id: "hy-oas", label: "高收益债信用利差", market: "us", frequency: "daily", meaning: "美国高收益企业债的额外借款成本", reading: "扩大表示风险补偿要求增加；与VIX可能重复反映压力。", scope: "ICE BofA美国高收益债指数" },
  { id: "ofr-fsi", label: "OFR金融压力", market: "us", frequency: "daily", meaning: "多市场的金融压力", reading: "高于自身参照表示压力较大；约滞后两个工作日且历史可能修订。", scope: "全球金融市场压力；作为美股跨市场背景" },
  { id: "nfci", label: "NFCI金融条件", market: "us", frequency: "weekly", meaning: "美国风险、信用和杠杆的综合条件", reading: "上升表示相对自身历史均值趋紧；零线为长期平均，负值表示相对宽松。", scope: "美国金融条件；FRED NFCI 周频，近两年历史，发布约滞后一周且历史会修订" },
  { id: "finra-margin", label: "FINRA客户融资余额", market: "us", frequency: "monthly", meaning: "证券账户保证金融资负债", reading: "名义余额上升不等于净流入股市；月报通常次月发布。", scope: "FINRA相关客户账户；非全部机构" },
  { id: "aaii", label: "AAII调查", market: "us", frequency: "weekly", meaning: "受访个人投资者的看涨减看跌意见", reading: "只代表受访者；调查周不等于首次公开日。", scope: "AAII受访个人投资者" },
  { id: "naaim", label: "NAAIM调查", market: "us", frequency: "weekly", meaning: "主动管理人自报股票敞口", reading: "是自报样本均值，不是美国机构真实总仓位。", scope: "NAAIM受访主动管理人" },
  { id: "baker-wurgler", label: "Baker–Wurgler情绪", market: "us", frequency: "monthly", meaning: "美国市场月度情绪背景", reading: "用于观察较慢的情绪水平；未验证为阶段顶底模型，不能用相邻月差衡量情绪变化。", scope: "作者美国股票市场历史表；末行2025-12" },
  { id: "hs300-pe", label: "沪深300 PE_TTM", market: "cn", frequency: "monthly", meaning: "沪深300滚动市盈率", reading: "观察自身估值位置；不能借给创业板或科创50。", scope: "沪深300指数" },
  { id: "sp500-cape", label: "标普500 Shiller CAPE", market: "us", frequency: "monthly", meaning: "美国市场长期平滑盈利市盈率", reading: "月初日期代表所属月，历史首次公开时点未核。", scope: "Shiller美国市场口径；现代标普500成立前的部分使用早期美国股市资料。" },
  { id: "pmi-cn", label: "中国制造业PMI", market: "cn", frequency: "monthly", meaning: "制造业调查的扩张或收缩", reading: "50是调查扩张分界，不是股市涨跌界线。", scope: "中国制造业调查；所属月非公布日" },
  { id: "wei", label: "WEI周经济指数", market: "us", frequency: "weekly", meaning: "美国周度经济活动合成估计", reading: "观察经济活动变化，不能当作已公布GDP或股价方向。", scope: "纽约联储美国周经济活动" },
];

export interface ProjectionSource {
  points: { date: string; value: number | null }[];
  unit: string;
  sourceName: string;
  sourceUrl?: string;
  note: string;
  status?: string;
  isPending: boolean;
  error: unknown;
  retry: () => void;
  coverage?: Record<string, { n: number; universeN: number }>;
  bands?: ErpBandPoint[];
  frequency?: "daily" | "weekly" | "monthly";
  valuationFull?: boolean;
  referencePrice?: { dates: string[]; values: (number | null)[] };
}

const STATIC_PREFIX = "/research/observation-library-20261026/";
async function readJson(url: string): Promise<unknown> {
  const response = await fetch(url, { cache: "no-cache" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  if (!(response.headers.get("content-type") ?? "").includes("json")) throw new Error("返回的不是 JSON");
  return response.json();
}
function fromSeries(series?: RatesHistorySeries, month = false): { date: string; value: number | null }[] {
  if (!series || series.dates.length !== series.values.length) return [];
  return series.dates.map((date, index) => ({ date: month ? date.slice(0, 7) : date,
    value: Number.isFinite(series.values[index]) ? series.values[index] : null }));
}

/** All hooks are unconditional; only the selected source has an enabled request. */
export function useProjectionSource(id: string, variant: "orth" | "raw" = "orth"): ProjectionSource {
  const erpReference = useQuery({ queryKey: ERP_REFERENCE_QUERY_KEY,
    queryFn: async () => parseErpReference(await readJson(ERP_REFERENCE_URL)),
    enabled: id === "erp-cn", staleTime: 5 * 60_000, refetchInterval: 5 * 60_000, retry: false });
  const isCandidate = (HISTORICAL_CANDIDATE_IDS as readonly string[]).includes(id);
  const candidate = useQuery({ queryKey: CANDIDATE_QUERY_KEY,
    queryFn: async () => parseCandidateHistory(await readJson(CANDIDATE_URL)),
    enabled: isCandidate, staleTime: Infinity, retry: false, refetchOnWindowFocus: false });
  const concentration = useQuery({ queryKey: CONCENTRATION_QUERY_KEY,
    queryFn: async () => parseConcentration(await readJson(CONCENTRATION_URL)),
    enabled: id === "turnover-concentration", staleTime: Infinity, retry: false, refetchOnWindowFocus: false });
  const isFocus = id === "focus-momentum";
  const isStatic = ["ofr-fsi", "nfci", "vxn", "finra-margin", "baker-wurgler"].includes(id);
  const staticUrl = `${STATIC_PREFIX}${id === "baker-wurgler" ? "baker.json" : "reused-series.json"}`;
  const focus = useRecentFocusMomentum(isFocus);
  const saved = useQuery({ queryKey: ["observationLibraryStatic", staticUrl],
    queryFn: async () => id === "baker-wurgler" ? parseBaker(await readJson(staticUrl)) : parseReused(await readJson(staticUrl)),
    enabled: isStatic, staleTime: Infinity, retry: false, refetchOnWindowFocus: false });
  const rates = useQuery({ queryKey: ["fundamentalsRatesHistory", 18250],
    queryFn: () => fundamentalsApi.ratesHistory(18250),
    enabled: ["vix", "erp-us"].includes(id), staleTime: 5 * 60_000, refetchInterval: 5 * 60_000, retry: false });
  const valuation = useQuery({ queryKey: ["fundamentalsValuationHistory"],
    queryFn: () => fundamentalsApi.valuationHistory(), enabled: id === "hs300-pe" || id === "sp500-cape",
    staleTime: 5 * 60_000, refetchInterval: 5 * 60_000, retry: false });
  const macro = useQuery({ queryKey: ["fundamentalsMacroHistory", 60],
    queryFn: () => fundamentalsApi.macroHistory(60), enabled: id === "pmi-cn", staleTime: 30 * 60_000, retry: false });
  const usMacro = useQuery({ queryKey: ["fundamentalsUsMacro"],
    queryFn: () => fundamentalsApi.usMacro(), enabled: ["hy-oas", "wei"].includes(id), staleTime: 30 * 60_000, retry: false });
  const surveySeries: "aaii" | "naaim" = id === "naaim" ? "naaim" : "aaii";
  const survey = useQuery({ queryKey: ["sentimentHistory", surveySeries],
    queryFn: () => api.marketContextSentimentHistory(surveySeries),
    enabled: ["aaii", "naaim"].includes(id), staleTime: 5 * 60_000, retry: false });

  let points: ProjectionSource["points"] = [];
  let unit = "";
  let sourceName = "";
  let sourceUrl: string | undefined;
  let coverage: ProjectionSource["coverage"];
  let bands: ProjectionSource["bands"];
  let frequency: ProjectionSource["frequency"];
  let status: string | undefined;
  let referencePrice: ProjectionSource["referencePrice"];
  let note = PROJECTION_METRICS.find((item) => item.id === id)?.reading ?? "未登记的观察项";
  let active: typeof erpReference | typeof candidate | typeof concentration | typeof focus | typeof saved | typeof rates | typeof macro | typeof usMacro | typeof survey | null = null;
  if (isCandidate) {
    active = candidate;
    const data = candidate.data ? fromCandidateHistory(candidate.data, id as HistoricalCandidateId) : null;
    points = data?.points ?? []; unit = data?.unit ?? "";
    sourceName = data?.sourceName ?? "沪深A股历史样本观察"; sourceUrl = data?.sourceUrl ?? undefined;
    note = data?.note ?? "历史样本，缺失值不补。";
    if (candidate.data) coverage = Object.fromEntries(candidate.data.series[id as HistoricalCandidateId].points
      .map((p) => [p.date, { n: p.n, universeN: p.universeN }]));
  } else if (id === "turnover-concentration") {
    active = concentration;
    const data = concentration.data ? fromConcentration(concentration.data) : null;
    points = data?.points ?? []; unit = "%"; status = data?.status;
    sourceName = data?.sourceName ?? "供应商覆盖沪深A股月度成交额";
    sourceUrl = data?.sourceUrl ?? undefined;
    note = data?.note ?? "月度历史，缺失月份不补值。";
  } else if (isFocus) {
    active = focus;
    points = focus.data?.series.map((row) => ({ date: row.date, value: row.focus * 100 })) ?? [];
    unit = "%"; sourceName = "A股固定300股焦点动量历史研究";
    note = `固定300股样本截至${focus.data?.asOf ?? "未知"}，过去20交易日收益；并非今日全A信号。`;
  } else if (isStatic) {
    active = saved;
    if (saved.data) {
      if (id === "baker-wurgler") {
        const data = parseBaker(saved.data);
        points = data.series.map((row) => ({ date: row.date.slice(0, 7), value: variant === "raw" ? row.rawValue ?? null : row.value }));
        unit = data.unit; sourceName = data.sourceName; sourceUrl = data.sourceUrl;
        note = `${variant === "raw" ? "SENT原版" : "SENT_ORTH宏观调整后版"}；所属月不是首次公布日，2025-10宏观调整后值缺失，不能以相邻月差推断情绪变化。`;
      } else {
        const data = parseReused(saved.data).series[id];
        if (data) {
          points = data.points.map((point) => ({ date: id === "finra-margin" ? point.date.slice(0, 7) : point.date, value: point.value }));
          unit = data.unit; sourceName = data.sourceName; sourceUrl = data.sourceUrl;
          if (id === "nfci") note = "FRED NFCI周频近两年；零线为长期平均，负值表示条件相对宽松，历史会修订。";
          if (id === "vxn") note = "FRED VXNCLS日频近两年；VXN是纳指100期权隐含波动，不是VIX，也没有涨跌方向。";
          if (id === "finra-margin") note = "月度客户保证金融资余额，通常次月才公布；当前历史不是逐月首发版本。";
          if (id === "ofr-fsi") note = "全球金融压力历史当前版本，约滞后两个工作日且历史会修订；不是当日已知值。";
        }
      }
    }
  } else if (id === "erp-cn") {
    active = erpReference;
    const data = erpReference.data ? fromErpReference(erpReference.data) : null;
    points = data?.points ?? []; unit = "百分点";
    sourceName = data?.sourceName ?? "沪深300股债利差三年轨道"; sourceUrl = data?.sourceUrl ?? undefined;
    note = data?.note ?? "历史资料读取中";
    frequency = erpReference.data?.frequency;
    if (erpReference.data) {
      bands = erpBands(points);
      referencePrice = { dates: erpReference.data.points.map((p) => p.date), values: erpReference.data.points.map((p) => p.close) };
    }
  } else if (id === "erp-us") {
    active = rates;
    const data = fromErpHistory(rates.data, id);
    points = data?.points ?? [];
    unit = "百分点"; sourceName = data?.sourceName ?? "现有基本面股债收益差";
    note = data?.note ?? "缺少该市场的股债利差历史；不从其他市场替代。";
  } else if (id === "hs300-pe" || id === "sp500-cape") {
    active = valuation;
    const key = id === "hs300-pe" ? "pe_cn" : "cape_us";
    points = valuationMonthlyPoints(fromSeries(valuation.data?.series[key], id === "sp500-cape"));
    unit = "倍"; sourceName = VALUATION_SOURCES[id].source; sourceUrl = VALUATION_SOURCES[id].url;
    note = id === "hs300-pe" ? "每月取同源最后读数；当月显示截至所示日期的最新读数。"
      : "用过去十年经通胀调整的盈利均值计算。月份表示资料所属期，实际发布日期可能更晚。";
  } else if (id === "vix") {
    active = rates;
    points = fromSeries(rates.data?.series.vix);
    unit = "指数点"; sourceName = "Yahoo / Cboe VIX"; sourceUrl = "https://www.cboe.com/tradable-products/vix/";
  } else if (id === "pmi-cn") {
    active = macro; points = fromSeries(macro.data?.series.pmi);
    unit = "指数点"; sourceName = "中国制造业PMI（国家统计局口径，经东财）";
    note = "月度PMI历史按所属期作图；首次公开时间未核，不能拿月初当可知日。";
  } else if (id === "hy-oas" || id === "wei") {
    active = usMacro; const key = id === "wei" ? "wei" : "hy_oas";
    points = fromSeries(usMacro.data?.series[key]); unit = "%";
    sourceName = id === "wei" ? "纽约联储WEI / FRED" : "ICE BofA美国高收益债OAS / FRED";
    sourceUrl = id === "wei" ? "https://fred.stlouisfed.org/series/WEI" : "https://fred.stlouisfed.org/series/BAMLH0A0HYM2";
  } else if (id === "aaii" || id === "naaim") {
    active = survey; points = fromSurveyHistory(survey.data, surveySeries);
    unit = "%"; sourceName = id === "aaii" ? "AAII投资者调查" : "NAAIM管理人调查";
    note = "横轴为调查周，不等于该值首次公布日；仅作事后历史对照。";
  }
  return {
    points, unit, sourceName, sourceUrl, note, status, coverage, bands, frequency, referencePrice, valuationFull: valuation.data?.valuation_full === true,
    isPending: active?.isPending ?? false,
    error: active?.error ?? (active ? null : new Error("未登记的投影资料")),
    retry: () => { if (active) void active.refetch(); },
  };
}
