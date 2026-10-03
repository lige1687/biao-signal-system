// Read-only boundary for market-observation@55d8aa96. Does not upgrade source qualification.
export type Market = "cn" | "us";
export type Quality = "current" | "delayed" | "stale" | "time_unverified" | "missing" | "insufficient_history";
export interface Observation {
  metric_id: string; label: string; market: Market; universe: string;
  value: number | null; unit: string; change: number | null; change_unit: string | null;
  comparison_period: string | null; observation_date: string | null;
  published_at: string | null; publication_precision: "timestamp" | "date" | "unknown";
  fetched_at: string | null; source_name: string; source_url: string | null;
  quality_status: Quality; quality_reason: string | null;
  reading: string; limitations: string[]; definition_version: string;
}
export interface ObservationResult { items: Observation[]; notices: string[]; generatedAt: string | null; }
export const expectedMetrics: Record<Market, Record<string, {label: string; unit: string}>> = {
  cn: { margin_balance: {label:"融资余额",unit:"亿元"}, margin_buy:{label:"融资买入额",unit:"亿元"}, stock_turnover:{label:"A股股票成交额",unit:"亿元"} },
  us: { vix:{label:"标普500预期波动率 VIX",unit:"指数点"}, vxn:{label:"纳斯达克100预期波动率 VXN",unit:"指数点"}, real_yield_10y:{label:"美国10年实际利率",unit:"%"}, hy_oas:{label:"美国高收益债信用利差",unit:"%"}, naaim:{label:"NAAIM 自报股票敞口",unit:"%"}, aaii:{label:"AAII 看涨减看跌",unit:"百分点"} },
};
const qualityNames: Record<Quality,string> = {current:"来源标记已核对",delayed:"按来源延迟发布",stale:"历史读数 · 已过期",time_unverified:"可用时间未核实",missing:"数据缺失",insufficient_history:"历史不足"};
const text = (value: unknown): string | null => typeof value === "string" && value.trim() ? value : null;
const numberOrNull = (value: unknown): value is number | null => value === null || (typeof value === "number" && Number.isFinite(value));
const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === "object" && !Array.isArray(value);
function changeUnitAllowed(valueUnit: string, changeUnit: string): boolean {
  return changeUnit === fallbackChangeUnit(valueUnit);
}
function fallbackChangeUnit(valueUnit: string): string { return valueUnit === "%" ? "百分点" : valueUnit; }
export function safeSourceUrl(value: string | null): string | undefined {
  if (!value) return undefined;
  try { const u = new URL(value); return ["https:","http:"].includes(u.protocol) && !u.username && !u.password ? u.href : undefined; } catch { return undefined; }
}
export function decodeObservations(raw: unknown, market: Market): ObservationResult {
  if (!record(raw) || raw.market !== market) throw new Error("返回资料的市场与所选市场不一致");
  if (!Array.isArray(raw.items) || !Array.isArray(raw.errors)) throw new Error("观察接口返回格式不符合已核契约");
  const result: ObservationResult = {items:[],notices:[],generatedAt:text(raw.generated_at)};
  if (raw.errors.length) result.notices.push("部分来源读取失败；缺失不代表市场没有变化。详情请在原观察页核对。");
  const seen = new Set<string>();
  for (const row of raw.items) {
    if (!record(row)) { result.notices.push("一项资料格式异常，未展示。"); continue; }
    const id=text(row.metric_id) ?? "";
    const spec = expectedMetrics[market][id];
    if (!spec || row.market !== market || seen.has(id) || row.unit !== spec.unit || !numberOrNull(row.value) || !numberOrNull(row.change)) {
      result.notices.push(`${spec?.label ?? "一项资料"}的市场、单位、数值或唯一性未通过检查，未展示。`); continue;
    }
    const quality = text(row.quality_status);
    if (!quality || !Object.prototype.hasOwnProperty.call(qualityNames,quality)) {result.notices.push(`${spec.label}资料状态未知，未展示。`);continue;}
    if ((row.value === null && quality !== "missing" && quality !== "insufficient_history") ||
        (row.value !== null && quality === "missing")) {
      result.notices.push(`${spec.label}的读数与缺失状态不一致，未展示。`); continue;
    }
    const declaredChangeUnit = row.change_unit == null ? null : text(row.change_unit);
    if (row.change_unit != null && (!declaredChangeUnit || !changeUnitAllowed(spec.unit, declaredChangeUnit))) {
      result.notices.push(`${spec.label}的变化单位与指标不相容，未展示。`); continue;
    }
    seen.add(id);
    result.items.push({metric_id:id,label:text(row.label) ?? spec.label,market,universe:text(row.universe) ?? "范围未记录",value:row.value,unit:spec.unit,change:row.change,change_unit:declaredChangeUnit,comparison_period:text(row.comparison_period),observation_date:text(row.observation_date),published_at:text(row.published_at),publication_precision:row.publication_precision === "timestamp" || row.publication_precision === "date" ? row.publication_precision : "unknown",fetched_at:text(row.fetched_at),source_name:text(row.source_name) ?? "来源未记录",source_url:safeSourceUrl(text(row.source_url)) ?? null,quality_status:quality as Quality,quality_reason:text(row.quality_reason),reading:text(row.reading) ?? "解释待补充",limitations:Array.isArray(row.limitations)? row.limitations.filter((x):x is string=>typeof x === "string"):[],definition_version:text(row.definition_version) ?? "版本未记录"});
  }
  return result;
}
function validPeriod(value: string | null): boolean {
  if (!value) return false;
  if (/^\d{4}-(0[1-9]|1[0-2])$/.test(value)) return true;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const d=new Date(`${value}T00:00:00Z`);
  return Number.isFinite(d.getTime()) && d.toISOString().slice(0,10) === value;
}
const readable = (value: number, unit:string) => `${new Intl.NumberFormat("zh-CN",{maximumFractionDigits:2}).format(value)}${unit}`;
export function presentObservation(item: Observation) {
  const hasValue = item.value != null && Number.isFinite(item.value) && validPeriod(item.observation_date) && item.quality_status !== "missing";
  const fixed = item.metric_id === "stock_turnover";
  const unit = item.change_unit ?? fallbackChangeUnit(item.unit);
  return {
    hasValue, value:hasValue ? readable(item.value!,item.unit) : "—",
    status:hasValue && fixed ? "固定历史资料" : !hasValue && item.quality_status !== "missing" ? "读数或日期缺失" : qualityNames[item.quality_status],
    change:hasValue && item.change != null && item.comparison_period ? `${item.comparison_period} ${item.change>0?"+":""}${readable(item.change,unit)}` : "暂无可比较的上期读数",
    period:`${["aaii","naaim"].includes(item.metric_id)?"调查所属周":"资料所属期"}：${item.observation_date ?? "未记录"}`,
    publication:item.publication_precision === "unknown" || !item.published_at ? "来源发布时间未核实" : `来源发布：${item.published_at}${item.publication_precision === "date"?"（仅日期）":"（记录到时刻；不等于首次可用已核实）"}`,
    reading:hasValue ? item.reading : item.quality_reason ?? "缺少有效日期或数值，暂不展示读数。",
    fixedNote:hasValue && fixed ? "固定历史样本；刷新不会增加新交易日。" : null,
  };
}
export interface EtfProfile { exposure: Market | "unknown"; currency:"cny"|"usd"|"unknown"; structure:"ordinary"|"leveraged"|"unknown"; }
export function etfReading(profile: EtfProfile): string[] {
  const result = [profile.exposure === "unknown" ? "标的资产范围尚未确认：先核基金跟踪指数及成分，不能从名字或上市地点推断。" : profile.exposure === "cn" ? "你选择了A股资产：先联系相同指数的趋势、上涨参与面与估值；融资数据的范围可能比这只ETF更广。" : "你选择了美国股票资产：先核具体指数。VIX对应标普500，VXN对应纳斯达克100，不能互相替代。"];
  if (profile.currency === "unknown") result.push("计价币种尚未确认：先核价格、净值和所持资产的币种，不能计算跨币种溢价。");
  else if ((profile.exposure === "us" && profile.currency === "cny") || (profile.exposure === "cn" && profile.currency === "usd")) result.push("资产与计价币种不同：另核汇率、是否有汇率对冲，以及价格和净值的时间是否一致；不能据此断言有套利机会。");
  else result.push("计价币种已选，但实际汇率暴露仍需查产品说明；同币种报价不保证没有其他货币资产。");
  result.push(profile.structure === "leveraged" ? "你选择了杠杆或反向产品：核每日重置目标和持有路径，不套用普通指数ETF的长期累计表现。" : profile.structure === "ordinary" ? "你选择了普通ETF：一起核费用、买卖价差、跟踪差异和持仓集中程度；低费用不等于总成本低。" : "产品结构尚未确认：先核是否含杠杆、反向或每日重置条款，再联系相应观察项。");
  return result;
}
