import {validDate,type Metric,type Series,type SourceMeta} from './dashboard-model';

export const contextMetrics:Metric[]=[
 {key:'margin_rzye',title:'融资余额',market:['cn'],group:'leverage',endpoint:'context',apiUnit:'亿',unit:'亿元',frequency:'日',source:'东方财富 · 沪深融资',reading:'上升表示未偿还融资余额增加；结合融资买入、偿还及指数。余额变化不是当日净资金流。'},
 {key:'margin_rqye',title:'融券余额',market:['cn'],group:'leverage',endpoint:'context',apiUnit:'亿',unit:'亿元',frequency:'日',source:'东方财富 · 沪深融券',reading:'上升表示融券余额增加；受可借证券、制度和价格变化影响，不能直接等同市场做空意愿。'},
 {key:'margin_buy',title:'当日融资买入额',market:['cn'],group:'leverage',endpoint:'context',apiUnit:'亿',unit:'亿元',frequency:'日',source:'东方财富 · 沪深融资买入',reading:'反映当日融资买入规模；缺少偿还额时不能称净融资流入，结合成交额及余额。'},
 {key:'cn_2y',title:'中国2年国债收益率',market:['cn'],group:'rates',endpoint:'context',apiUnit:'%',unit:'%',frequency:'日',source:'东方财富 · 中美国债资料',reading:'观察短端市场资金价格，结合10年利率与政策；不等于央行政策利率。'},
 {key:'us_2y',title:'美国2年国债收益率',market:['us'],group:'rates',endpoint:'context',apiUnit:'%',unit:'%',frequency:'日',source:'东方财富 · 中美国债资料',reading:'反映市场对短期利率等因素的定价；结合政策、通胀与长端，不直接预测股市。'},
 {key:'cn_10_2_spread',title:'中国10年减2年期限差',market:['cn'],group:'rates',endpoint:'context',apiUnit:'百分点',unit:'百分点',frequency:'日',source:'同源国债：10年减2年',reading:'正值表示长端高于短端，负值表示本口径倒挂；曲线变陡须分清短端下降或长端上升，不是企业信用利差。'},
 {key:'us_10_2_spread',title:'美国10年减2年期限差',market:['us'],group:'rates',endpoint:'context',apiUnit:'百分点',unit:'百分点',frequency:'日',source:'同源国债：10年减2年',reading:'观察收益率曲线形状；与增长、政策和通胀一起看，倒挂不等于衰退或股市下跌已经确定。不是10年减3月。'},
 {key:'earnings_yield_cn',title:'沪深300历史盈利收益率',market:['cn'],group:'valuation',endpoint:'context',apiUnit:'%',unit:'%',frequency:'日',source:'100 / 乐咕乐股沪深300滚动PE',reading:'是过去盈利相对价格的比例；继承市盈率口径差异，不是盈利增长、盈利预期或持有回报。结合盈利质量与利率。'},
 {key:'earnings_yield_us',title:'标普500历史盈利收益率',market:['us'],group:'valuation',endpoint:'context',apiUnit:'%',unit:'%',frequency:'月',source:'Multpl · 历史盈利收益率',reading:'是过去盈利相对价格的比例；上升可能来自价格下降或盈利提高，不是分析师盈利预测或未来收益。'},
];

function record(x:unknown):x is Record<string,unknown>{return !!x&&typeof x==='object'&&!Array.isArray(x);}
export function safeSourceUrl(x:unknown):string|null{
 if(typeof x!=='string')return null;
 try{const u=new URL(x);return u.protocol==='https:'&&!u.username&&!u.password&&!/[?&](token|key|password|secret|auth|signature)=/i.test(x)?u.href:null;}catch{return null;}
}
function time(x:unknown):string|null{return typeof x==='string'&&/T.*(?:Z|[+-]\d{2}:\d{2})$/.test(x)&&Number.isFinite(Date.parse(x))?x:null;}
function sourceMeta(x:unknown):SourceMeta|null{
 if(!record(x)||typeof x.provider!=='string'||typeof x.series_identity!=='string')return null;
 return {provider:x.provider.slice(0,150),source_url:safeSourceUrl(x.source_url),series_identity:x.series_identity.slice(0,150),retrieved_at:time(x.retrieved_at),published_at:time(x.published_at),vintage:typeof x.vintage==='string'?x.vintage.slice(0,100):null,frequency:typeof x.frequency==='string'?x.frequency.slice(0,20):'未知',value_status:'provider_observed',historical_prediction_use:'unqualified',limitations:typeof x.limitations==='string'?x.limitations.slice(0,500):'来源口径待核'};
}
export interface SourceGap{status:'missing_input'|'permission_unconfirmed';reason:string;source_url:string|null}
export function decodeContext(raw:unknown,today:string):{series:Record<string,Series>;gaps:Record<string,SourceGap>;errors:number}{
 if(!record(raw)||raw.schema_version!=='market-context/1'||!record(raw.series)||!Array.isArray(raw.errors))throw new Error('补充资料格式不完整');
 const series:Record<string,Series>={};
 for(const m of contextMetrics){
  const s=raw.series[m.key],blank=(notice:string)=>{series[m.key]={dates:[],values:[],notice};};
  if(['synthetic','demo','test'].includes(String(raw.data_mode))||(record(s)&&['synthetic','demo','test'].includes(String(s.data_mode)))){blank('演示资料不作为市场读数');continue;}
  if(!record(s)||s.unit!==m.apiUnit||!Array.isArray(s.dates)||!Array.isArray(s.values)||s.dates.length!==s.values.length){blank('本次未取得匹配的补充资料');continue;}
  const meta=sourceMeta(s.source);
  if(!meta||!s.dates.every((d,i)=>validDate(d)&&(i===0||d>(s.dates as string[])[i-1]))||!s.values.every(v=>v===null||typeof v==='number'&&Number.isFinite(v))){blank('来源、日期或数值不合格');continue;}
  const end=s.dates.findIndex(d=>d>today),n=end<0?s.dates.length:end;
  series[m.key]={dates:s.dates.slice(0,n) as string[],values:s.values.slice(0,n) as (number|null)[],notice:end<0?'':'未来所属期已排除',source:meta};
 }
 const gaps:Record<string,SourceGap>={};
 if(record(raw.source_gaps))for(const key of ['finra_margin','earnings_forward','etf_flow','cn_credit','cn_volatility']){
  const g=raw.source_gaps[key];if(record(g)&&['missing_input','permission_unconfirmed'].includes(String(g.status))&&typeof g.reason==='string')gaps[key]={status:g.status as SourceGap['status'],reason:g.reason.slice(0,400),source_url:safeSourceUrl(g.source_url)};
 }
 return {series,gaps,errors:raw.errors.length};
}
export async function loadContext(signal:AbortSignal){const r=await fetch('/api/fundamentals/market-context?lookback_days=1095',{signal});if(!r.ok)throw new Error(`补充资料暂不可用（${r.status}）`);const x=decodeContext(await r.json(),new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Shanghai'}).format(new Date()));Object.values(x.series).forEach(s=>s.receivedAt=new Date().toLocaleString('zh-CN',{timeZone:'Asia/Shanghai'})+' 中国时间');return x;}
