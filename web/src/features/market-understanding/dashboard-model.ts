import { MARKLINES, type MarkLine } from '../../components/trend/zones';
import { referenceColors, referenceReading, type ReferenceReading } from './reference-reading';

export type Market = 'cn' | 'us';
export type Endpoint = 'rates' | 'macro' | 'usMacro';
export type WindowYears = 1 | 3 | 'all';
export const groups = { all: '全部指标', rates: '利率与信用', valuation: '估值', leverage: '资金与波动', growth: '经济与就业', inflation: '价格与通胀' } as const;
export interface Metric {
  key: string; title: string; market: Market[]; group: Exclude<keyof typeof groups, 'all'>;
  endpoint: Endpoint; apiUnit: string; unit: string; frequency: '日' | '周' | '月';
  reading: string; source: string;
}
const metric = (key: string, title: string, market: Market[], group: Metric['group'], endpoint: Endpoint, apiUnit: string, unit: string, frequency: Metric['frequency'], reading: string, source: string): Metric => ({key,title,market,group,endpoint,apiUnit,unit,frequency,reading,source});
const both: Market[] = ['cn','us'];
export const metrics: Metric[] = [
  metric('cn_10y','中国10年期国债收益率',['cn'],'rates','rates','%','%','日','上行意味着长期无风险利率提高；结合通胀、经济增长和信用利差看。下行也可能来自增长预期转弱。','原基本面利率数据链'),
  metric('us_10y','美国10年期国债收益率',['us'],'rates','rates','%','%','日','上行可能反映增长、通胀或期限补偿提高；结合通胀与信用利差，不单独推断股市方向。','原基本面利率数据链'),
  metric('margin_rzyezb','融资余额 / 流通市值',['cn'],'leverage','rates','%','%','日','比例提高，说明融资在流通市值中的占比增加。结合两融余额、成交与市值变化；市值下跌也会推高比例。','东方财富 · 沪深融资'),
  metric('pmi','制造业 PMI',['cn'],'growth','macro','','点','月','50以上表示调查相对上月扩张，以下表示收缩。结合新订单、生产与价格；不是经济同比增速。','东方财富转引月度宏观资料'),
  metric('vix','VIX 波动率指数',['us'],'leverage','rates','','点','日','上升表示期权隐含的近期波动预期提高；结合股价、信用利差。低位不保证未来安全。','Yahoo · Cboe VIX 指数'),
  metric('hy_oas','美国高收益债信用利差',['us'],'rates','usMacro','%','%','日','扩大意味着市场要求更高的信用风险补偿；结合利率和盈利。收窄也可能伴随风险定价偏低。','FRED · BAMLH0A0HYM2'),
  metric('cn_us_spread_10y','中美10年期国债利差',both,'rates','rates','%','百分点','日','中国收益率减美国收益率。零线表示两者相等，负值表示美国更高；结合汇率和各自经济环境。','原基本面中美国债同日差额'),
  metric('margin_rzrqye','沪深两融余额',['cn'],'leverage','rates','亿','亿元','日','融资与融券余额合计，不能当作融资余额或全市场杠杆。结合融资占流通市值比例；绝对额受市场规模影响，不画风险阈值。','东方财富 · 沪深合计'),
  metric('erp_cn','沪深300股债收益差',['cn'],'valuation','rates','%','百分点','日','用市盈率倒数减国债收益率作粗略比较；上升可能来自股价下跌或利率下降。结合盈利变化，不等于严格的预期股权风险溢价。','原基本面估值与国债历史组合'),
  metric('pe_cn','沪深300市盈率 TTM',['cn'],'valuation','rates','倍','倍','日','上升可能来自价格上涨或过去一年盈利下降；结合盈利、行业结构和历史位置，不能单靠低市盈率判断便宜。','乐咕乐股 · 原基本面历史接口'),
  metric('erp_us','标普500股债收益差',['us'],'valuation','rates','%','百分点','日','市盈率倒数减10年期美债收益率，是粗略比较。结合盈利预期与利率，负值不是股票必跌或应买债的指令。','原基本面估值与美债历史组合'),
  metric('cape_us','标普500 CAPE',['us'],'valuation','rates','倍','倍','月','用平滑后的实际盈利比较估值。高位说明价格相对长期盈利高，但不能给出短期拐点；结合利率和盈利结构。','multpl · 月度 CAPE'),
  metric('cpi','中国 CPI 同比',['cn'],'inflation','macro','%','%','月','上升说明居民消费价格同比涨幅扩大；结合核心价格、PPI与需求。零线表示与去年同月持平。','东方财富转引月度宏观资料'),
  metric('ppi','中国 PPI 同比',['cn'],'inflation','macro','%','%','月','上升说明工业生产者价格同比改善；结合原料成本、销售价格和利润，涨价不一定令所有行业受益。','东方财富转引月度宏观资料'),
  metric('cpiaucsl_yoy','美国 CPI 同比',['us'],'inflation','usMacro','%','%','月','结合就业、增长和利率判断通胀压力。2%沿用旧页经验参考，不能称为美联储的PCE通胀目标。','FRED · CPIAUCSL'),
  metric('ppiaco_yoy','美国最终需求 PPI 同比',['us'],'inflation','usMacro','%','%','月','观察生产者价格变化，结合CPI和利润。成本传导存在时差，不能机械预测消费通胀。','FRED · PPIFIS（保留旧接口键）'),
  metric('icwa','美国初请失业金 · 4周均值',['us'],'growth','usMacro','人','人','周','上升可能表示裁员压力增加；结合续请、非农和季节性，单周变化不代表就业趋势逆转。','FRED · ICSA，系统计算4周均值'),
  metric('ccwa','美国续请失业金人数',['us'],'growth','usMacro','人','人','周','上升可能表示再就业变慢；结合初请、非农和人口规模。旧页人数线不是固定衰退标准。','FRED · CCSA'),
  metric('payems_yoy','美国非农就业同比',['us'],'growth','usMacro','%','%','月','上升表示就业同比增长加快；结合初请、工资与失业率，留意基数和后续修订。','FRED · PAYEMS'),
  metric('wei','美国周度经济指数 WEI',['us'],'growth','usMacro','%','%','周','综合高频经济活动的增长代理；结合月度经济数据。零线是代理读数的零点，不是官方衰退判定。','FRED · WEI'),
  metric('hsales','美国新屋销售 · 折年率',['us'],'growth','usMacro','千套','千套','月','上升说明新屋销售活动增强；结合房贷利率、库存与房价。折年率不等于当月实际售出套数。','FRED · HSN1F'),
  metric('cshpi_yoy','美国房价同比',['us'],'growth','usMacro','%','%','月','观察住宅价格同比变化；结合成交、库存与利率，资料通常滞后，不能当作今天的成交价。','FRED · CSUSHPINSA'),
  metric('altsa','美国汽车销量 · 折年率',['us'],'growth','usMacro','百万辆','百万辆','月','上升可能来自消费改善或供应恢复；结合库存、信贷与促销。折年率不是当月销量。','FRED · TOTALSA'),
  metric('dgorder_yoy','美国耐用品新订单同比',['us'],'growth','usMacro','%','%','月','观察订单需求；结合出货与细项，大额飞机订单或基数会造成波动。','FRED · DGORDER'),
];
export interface Reference extends MarkLine, ReferenceReading { kind: '定义线' | '原页面参考' | '历史分位参考'; basis: string }
const historical: Record<string, {window: string; labels: string[]}> = {
  erp_cn:{window:'2005年起固定标定',labels:['P20','P50','P80']},
  erp_us:{window:'2006年起固定标定',labels:['零线','P50','P80']},
  cape_us:{window:'1950年起固定标定',labels:['P20','P50','P80']},
  pe_cn:{window:'2010年起固定标定',labels:['P20','P50','P80']},
};
const zeroKeys = new Set(['cpi','ppi','cpiaucsl_yoy','ppiaco_yoy','payems_yoy','cshpi_yoy','dgorder_yoy','wei','cn_us_spread_10y','erp_us']);
export function referencesFor(key: string): Reference[] {
  if(key==='margin_rzrqye') return [];
  return (MARKLINES[key] ?? []).map((line,i)=>{
    const definition = key==='pmi' || (line.y===0 && zeroKeys.has(key));
    const h = historical[key];
    const kind: Reference['kind'] = definition ? '定义线' : h ? '历史分位参考' : '原页面参考';
    const reading = referenceReading(key,i,line.y);
    const basis = definition ? (key==='pmi'?'PMI定义分界；不是交易阈值':'数值零点；不等于市场多空分界') : h ? `${h.window}；P20/P50/P80为当时历史的20/50/80百分位，未随当前窗口重算` : '沿用原基本面经验线；不是官方或LEI买卖阈值';
    return {y:line.y,...reading,color:referenceColors[reading.tone],kind,basis:h && !definition?`${h.labels[i]}；${basis}`:basis};
  });
}
export interface Series { dates: string[]; values: (number|null)[]; notice: string }
export interface Decoded { series: Record<string, Series>; errors: number }
function record(x: unknown): x is Record<string, unknown> { return !!x && typeof x==='object' && !Array.isArray(x); }
function validDate(x: unknown): x is string { return typeof x==='string' && /^\d{4}-\d{2}-\d{2}$/.test(x) && Number.isFinite(Date.parse(x+'T00:00:00Z')) && new Date(x+'T00:00:00Z').toISOString().slice(0,10)===x; }
export function decodeHistory(raw: unknown, endpoint: Endpoint, today: string): Decoded {
  if(!record(raw) || !record(raw.series) || !Array.isArray(raw.errors)) throw new Error('数据格式不完整');
  const result: Decoded = {series:{},errors:raw.errors.length};
  for(const m of metrics.filter(m=>m.endpoint===endpoint)) {
    const s=raw.series[m.key];
    const missing = (notice: string) => {result.series[m.key]={dates:[],values:[],notice};};
    if(!record(s) || !Array.isArray(s.dates) || !Array.isArray(s.values)) { missing('本次未返回该序列'); continue; }
    if(s.unit!==m.apiUnit || s.dates.length!==s.values.length) {missing('单位或日期与数值不匹配，暂不展示');continue;}
    if(!s.dates.every((d,i)=>validDate(d) && (i===0 || d > (s.dates as string[])[i-1])) || !s.values.every(v=>v===null || (typeof v==='number' && Number.isFinite(v)))) {missing('日期顺序或数值格式异常，暂不展示');continue;}
    const end=s.dates.findIndex(d=>d>today);
    const n=end<0?s.dates.length:end;
    result.series[m.key]={dates:s.dates.slice(0,n) as string[],values:s.values.slice(0,n) as (number|null)[],notice:end<0?'':'未来所属期已排除'};
  }
  return result;
}
export function lastReading(s: Series | undefined) {
  if(!s) return null;
  const indices=s.values.flatMap((v,i)=>v===null?[]:[i]);
  const i=indices[indices.length-1]; if(i===undefined) return null;
  const j=indices[indices.length-2];
  return {value:s.values[i]!, date:s.dates[i], change:j===undefined?null:s.values[i]!-s.values[j]!, previousDate:j===undefined?null:s.dates[j], trailingMissing:i<s.values.length-1};
}
export function windowSeries(s: Series, years: WindowYears): Series {
  if(years==='all' || !s.dates.length) return s;
  const end=s.dates[s.dates.length-1];
  // Natural calendar years, including month-end/leap-day clamping; never assume trading days for monthly series.
  const [y,m,d]=end.split('-').map(Number);
  const cutoff=new Date(Date.UTC(y-years,m-1,Math.min(d,new Date(Date.UTC(y-years,m,0)).getUTCDate()))).toISOString().slice(0,10);
  const i=s.dates.findIndex(d=>d>=cutoff);
  return {...s,dates:s.dates.slice(i),values:s.values.slice(i)};
}
export function yRangeFor(s: Series, marks: MarkLine[]): [number,number] | undefined {
  const values=[...s.values.filter((v):v is number=>v!==null),...marks.map(m=>m.y)];
  if(!values.length) return undefined;
  const lo=Math.min(...values),hi=Math.max(...values),pad=Math.max((hi-lo)*.08,Math.abs(hi)*.005,.01);
  const step=10**(Math.floor(Math.log10(hi-lo || Math.abs(hi) || 1))-1);
  return [Number((Math.floor((lo-pad)/step)*step).toPrecision(10)),Number((Math.ceil((hi+pad)/step)*step).toPrecision(10))];
}
export function formatValue(value: number, unit: string) { return value.toLocaleString('zh-CN',{maximumFractionDigits:unit==='人'?0:2}) + (unit==='%'?'%':` ${unit}`); }
export function periodLabel(date: string, frequency: Metric['frequency']) { return frequency==='月' ? `${date.slice(0,7)} 所属月` : frequency==='周' ? `${date} 所属周` : `${date} 观测日`; }
export function shanghaiToday() { return new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date()); }
export const endpoints: Record<Endpoint,string> = {rates:'/api/fundamentals/rates-history?lookback_days=1095',macro:'/api/fundamentals/macro-history?page_size=60',usMacro:'/api/fundamentals/us-macro'};
export async function loadHistory(endpoint: Endpoint, signal: AbortSignal): Promise<Decoded> {
  const response=await fetch(endpoints[endpoint],{signal});
  if(!response.ok) throw new Error(`资料服务暂不可用（${response.status}）`);
  return decodeHistory(await response.json(),endpoint,shanghaiToday());
}
