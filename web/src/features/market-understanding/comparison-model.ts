import {validDate, type Market, type Metric, type Series, type WindowYears, windowSeries} from './dashboard-model';
export const indexChoices=[{key:'hs300',title:'沪深300',market:'cn',source:'腾讯 · 沪深300价格指数'}, {key:'sse',title:'上证指数',market:'cn',source:'腾讯 · 上证综合价格指数'}, {key:'sp500',title:'标普500',market:'us',source:'FRED · SP500价格指数'}, {key:'nasdaq',title:'纳斯达克综合',market:'us',source:'FRED · NASDAQCOM；不是纳斯达克100或QQQ'}] as const;
export function decodeIndices(raw:unknown,today:string):Record<string,Series> {
 const data=raw as {data_mode?:unknown;series?:Record<string,{data_mode?:unknown;unit?:unknown;dates?:unknown;values?:unknown}>};if(!data || typeof data.series!=='object'||!data.series)throw new Error('指数资料格式不完整');
 const result:Record<string,Series>={};
 for(const {key} of indexChoices){
  const s=data.series[key],empty={dates:[],values:[],notice:'本次未取得指数历史'};
  if(['synthetic','demo','test'].includes(String(data.data_mode))||['synthetic','demo','test'].includes(String(s?.data_mode))){result[key]={...empty,notice:'演示指数不作为真实观测'};continue;}
  if(!s||s.unit!==''||!Array.isArray(s.dates)||!Array.isArray(s.values)||s.dates.length!==s.values.length){result[key]=empty;continue;}
  const ds=s.dates as unknown[],vs=s.values as unknown[];
  if(!ds.every((d,i)=>validDate(d)&&(i===0||d>(ds[i-1] as string)))||!vs.every(v=>v===null||typeof v==='number'&&Number.isFinite(v)&&v>0)){result[key]={...empty,notice:'指数日期、单位或数值不合格'};continue;}
  const n=ds.findIndex(d=>(d as string)>today);result[key]={dates:ds.slice(0,n<0?ds.length:n) as string[],values:vs.slice(0,n<0?vs.length:n) as (number|null)[],notice:n<0?'':'未来观测已排除'};
 }return result;
}
export function bucket(date:string,freq:Metric['frequency']):string {
 if(freq==='月')return date.slice(0,7);
 if(freq==='日')return date;
 const d=new Date(date+'T00:00:00Z'),day=(d.getUTCDay()+6)%7;d.setUTCDate(d.getUTCDate()-day);return d.toISOString().slice(0,10);
}
function finished(key:string,freq:Metric['frequency'],today:string){return freq==='月'?key<today.slice(0,7):freq==='周'?new Date(Date.parse(key+'T00:00:00Z')+6*86400000).toISOString().slice(0,10)<today:key<=today;}
export interface Pair {date:string;metric:number|null;index:number|null;metricDate:string;indexDate:string}
export function alignComparison(s:Series,index:Series,freq:Metric['frequency'],years:WindowYears,today:string):Pair[] {
 const a=new Map<string,{v:number|null;d:string}>(),c=new Map<string,{v:number|null;d:string}>();
 for(const [input,map] of [[windowSeries(s,years),a],[index,c]] as const)input.dates.forEach((d,i)=>{const k=bucket(d,freq);if(d<=today&&finished(k,freq,today))map.set(k,{v:input.values[i],d});});
 return [...a].map(([date,x])=>({date,metric:x.v,index:c.get(date)?.v??null,metricDate:x.d,indexDate:c.get(date)?.d??''}));
}
function consecutive(a:string,b:string,freq:Metric['frequency']) {
 if(freq==='月'){const [y,m]=a.split('-').map(Number),[z,n]=b.split('-').map(Number);return(z-y)*12+n-m===1;}
 const days=(Date.parse(b)-Date.parse(a))/86400000;return freq==='周'?days===7:days>0&&days<=4;
}
export interface Change {date:string;from:string;metricChange:number;indexReturn:number}
export function changes(pairs:Pair[],freq:Metric['frequency']):Change[] {
 return pairs.slice(1).flatMap((p,i)=>{const a=pairs[i];return a.metric===null||p.metric===null||a.index===null||p.index===null||a.index<=0||!consecutive(a.date,p.date,freq)?[]:[{date:p.date,from:a.date,metricChange:p.metric-a.metric,indexReturn:(p.index/a.index-1)*100}];});
}
export function correlation(points:Change[]):number|null {
 if(points.length<12)return null;const n=points.length,mx=points.reduce((a,p)=>a+p.metricChange,0)/n,my=points.reduce((a,p)=>a+p.indexReturn,0)/n;
 let xy=0,xx=0,yy=0;for(const p of points){const x=p.metricChange-mx,y=p.indexReturn-my;xy+=x*y;xx+=x*x;yy+=y*y;}return xx===0||yy===0?null:xy/Math.sqrt(xx*yy);
}
export function divergence(points:Change[],key:string):string|null {
 const p=points[points.length-1];if(!p)return null;
 if(['vix','hy_oas','margin_rzyezb'].includes(key)&&p.metricChange>0&&p.indexReturn>0)return `需一起核查：${p.from}—${p.date}，指数上涨${p.indexReturn.toFixed(2)}%，该指标同时增加${p.metricChange.toFixed(2)}。价格走强与这项压力读数上升并存；不等于后续必跌。`;
 return null;
}
export function choicesFor(market:Market){return indexChoices.filter(i=>i.market===market);}
