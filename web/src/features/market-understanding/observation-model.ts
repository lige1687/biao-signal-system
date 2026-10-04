import {allMetrics as metrics} from './metric-catalog';
import {lastReading,formatValue,periodLabel,type Market,type Series,type Metric} from './dashboard-model';
import {observedFrequency,qualityNote} from './data-quality';
import {indexChoices,alignComparison,changes as pairChanges,divergence} from './comparison-model';
type Reading=ReturnType<typeof lastReading>;
export function observationLink(market:Market,key:string){return `/market-understanding?market=${market}&metric=${encodeURIComponent(key)}#overview`;}
export interface ObservationRow{key:string;title:string;unit:string;frequency:Metric['frequency'];reading:Reading;series?:Series;metric?:Metric;quality:string}
export interface ObservationGroup{id:string;title:string;purpose:string;reading:string;counterexample:string;rows:ObservationRow[]}
const definitions=[
 {id:'growth',title:'增长 · 物价 · 利率',purpose:'经济需求与资金价格是否相互支持',cn:['pmi','cpi','cn_2y','cn_10y','cn_10_2_spread'],us:['wei','cpiaucsl_yoy','us_2y','us_10y','us_10_2_spread'],reading:'增长改善而物价压力平稳，可观察需求支持；增长和物价一起上升时，还要留意利率提高带来的压力。',counterexample:'利率下降也可能因为增长转弱；物价同比上升可能只是去年基数偏低。'},
 {id:'valuation',title:'估值 · 盈利 · 利率',purpose:'价格相对盈利和无风险利率是否偏高',cn:['pe_cn','earnings_yield_cn','erp_cn','cn_10y','earnings_forward'],us:['cape_us','earnings_yield_us','erp_us','us_10y','earnings_forward'],reading:'估值下降可观察价格压力减轻，股债收益差上升可观察相对吸引力；两者都需要核盈利是否恶化。',counterexample:'市盈率下降不保证便宜；盈利预期下调可能使原有盈利数字失去参考意义。CAPE与TTM市盈率口径不同。'},
 {id:'leverage',title:'融资 · 资金 · 指数',purpose:'价格变化是否伴随融资和真实资金流支持',cn:['margin_rzrqye','margin_rzye','margin_rqye','margin_buy','margin_rzyezb','hs300','etf_flow'],us:['sp500','finra_margin','etf_flow'],reading:'融资扩大且指数走强，说明杠杆参与增加，也需留意拥挤风险；融资回落可能是主动降风险或被动平仓。',counterexample:'融资占比上升也可能因为市值下跌；ETF成交额不等于净流入，美国月度FINRA与A股两融不能直接互比。'},
 {id:'credit',title:'信用 · 波动 · 指数',purpose:'价格走强时，风险补偿与波动预期是否同步',cn:['hs300','cn_10y','cn_credit','cn_volatility'],us:['hy_oas','vix','sp500'],reading:'信用利差扩大或波动预期升高时，应观察风险压力；若指数同期走强，先核这种不一致是否持续。',counterexample:'低VIX不保证未来安全；中国国债收益率不能替代信用利差，缺少中国信用/波动输入时不能照搬美国结论。'},
];
const gaps:Record<string,string>={earnings_forward:'指数盈利预期与修订',etf_flow:'ETF净资金流',finra_margin:'美国FINRA月度融资',cn_credit:'中国信用利差',cn_volatility:'中国波动预期'};
function available(s:Series|undefined,today:string){if(!s)return undefined;const n=s.dates.findIndex(d=>d>today);return n<0?s:{...s,dates:s.dates.slice(0,n),values:s.values.slice(0,n)};}
export function observationSnapshot(market:Market,series:Record<string,Series>,indices:Record<string,Series>,today:string){
 const row=(key:string):ObservationRow=>{const m=metrics.find(x=>x.key===key),index=indexChoices.find(x=>x.key===key),s=available(m?series[key]:indices[key],today),frequency=m?observedFrequency(m,s):'日';return {key,title:m?.title??index?.title??gaps[key]??key,unit:m?.unit??(index?'点':''),frequency,reading:lastReading(s),series:s,metric:m,quality:m?qualityNote(m,s,today):index?'价格指数；逐期来源与发布时间未核实。':'尚无合格连续输入，暂不判断。'};};
 const groups:ObservationGroup[]=definitions.map(d=>({...d,rows:d[market].map(row)}));
 const all=metrics.filter(m=>m.market.includes(market)).map(m=>row(m.key));
 const changes=all.filter((x):x is ObservationRow&{reading:NonNullable<Reading>}=>x.reading!==null&&x.reading.change!==null).sort((a,b)=>b.reading.date.localeCompare(a.reading.date)||a.key.localeCompare(b.key));
 const index=available(indices[market==='cn'?'hs300':'sp500'],today);
 const conflicts=(market==='cn'?['margin_rzyezb']:['vix','hy_oas']).flatMap(key=>{const x=row(key);if(!x.metric||!x.series||!index)return [];const note=divergence(pairChanges(alignComparison(x.series,index,x.frequency,3,today),x.frequency),key);return note?[`${x.title}：${note}`]:[];});
 return {heading:'最近观测变化',conflicts,groups,changes,available:all.filter(x=>x.reading).length,total:all.length,missing:all.filter(x=>!x.reading)};
}
export function observationText(row:ObservationRow){const x=row.reading;if(!x)return `${row.title}：暂无合格观测`;return `${row.title} ${formatValue(x.value,row.unit)} · ${periodLabel(x.date,row.frequency)}；${x.change===null?'变化不可比':`较${x.previousDate} ${x.change>0?'上升':x.change<0?'下降':'持平'}${formatValue(Math.abs(x.change),row.unit==='%'?'百分点':row.unit)}`}`;}
