import {lastReading,type Metric,type Series} from './dashboard-model';
// This describes the delivered observations, never the official publication frequency.
export function observedFrequency(m:Pick<Metric,'frequency'>,s?:Series):Metric['frequency']{
 if(m.frequency!=='日'||!s||s.dates.length<6)return m.frequency;
 const dates=s.dates.filter((_,i)=>s.values[i]!==null);
 if(dates.length<6)return m.frequency;
 const gaps=dates.slice(1).map((d,i)=>(Date.parse(d)-Date.parse(dates[i]))/86400000).sort((a,b)=>a-b);
 const median=gaps[Math.floor(gaps.length/2)];
 if(median>=20&&median<=40&&new Set(dates.map(d=>d.slice(0,7))).size===dates.length)return '月';
 if(median>=6&&median<=8&&gaps.every(x=>x>=6&&x<=8))return '周';
 return m.frequency;
}
export function ageNotice(date:string,frequency:Metric['frequency'],today:string){
 const age=(Date.parse(today)-Date.parse(date))/86400000,limit=frequency==='日'?14:frequency==='周'?28:100;
 return age>limit?`数据所属期距今${Math.floor(age)}天；先核更新状态（提醒标准${limit}天，不是投资阈值）。`:'';
}
export const cnValuationAudit={period:'2026-08-31',pe:14.65,verified:'2026-10-04',url:'https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/000300factsheet.pdf'};
export function qualityNote(m:Pick<Metric,'frequency'>&{key?:string},s:Series|undefined,today:string){
 const frequency=observedFrequency(m,s),latest=lastReading(s);
 const i=s?.dates.indexOf(cnValuationAudit.period)??-1,value=i<0?null:s?.values[i];
 const audit=m.key==='pe_cn'&&value!==null&&value!==undefined&&Math.abs(value-cnValuationAudit.pe)>.02?`${cnValuationAudit.period}的接口市盈率${value}与官方月报${cnValuationAudit.pe}不一致，市盈率口径待核；不代表今天官方估值。`:m.key==='erp_cn'?'该股债差继承市盈率口径限制，不能作为经官方核验的估值结论。':'';
 return [audit,s?.notice,frequency!==m.frequency?`实际观测间隔按${frequency}度展示，间隔识别不等于官方发布频率核实。`:'',latest?ageNotice(latest.date,frequency,today):'尚无有效观测',latest?.trailingMissing?'末期缺值，保留最近有效观测。':'',s?.receivedAt?`客户端读取：${s.receivedAt}（不是首次公布时间）。`:'', '逐期来源、首次发布与修订版本未核实。'].filter(Boolean).join(' ');
}
