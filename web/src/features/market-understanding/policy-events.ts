import type {Market} from './dashboard-model';
import {localEventTime,upcomingEvents} from './events';
export const nbsCalendar='https://www.stats.gov.cn/xw/tjxw/tzgg/202512/t20251224_1962137.html';
export const fedCalendar='https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm';
export interface PolicyEvent {id:string;market:Market;name:string;date:string;endDate?:string;at?:string;zone:string;source:string;verified:string;reading:string}
// Selected official schedule facts. No forecast, outcome or inferred announcement time.
export const policyEvents:PolicyEvent[]=[
 ...([['10','14','19','31'],['11','09','16','30'],['12','09','15','31']] as const).flatMap(([month,cpi,economy,pmi])=>[
  {name:'中国CPI / PPI月报',day:cpi,time:'09:30',reading:'价格涨幅与需求、基数一起看；缺预期值时不计算超预期。'},
  {name:'中国经济运行发布',day:economy,time:'10:00',reading:'结合生产、消费、投资；不能只用一项数据判断全部经济。'},
  {name:'中国PMI月报',day:pmi,time:'09:30',reading:'PMI 50是扩张收缩分界；还要看订单、价格与连续变化。'},
 ].map(e=>({id:`cn-${month}-${e.day}`,market:'cn' as const,name:e.name,date:`2026-${month}-${e.day}`,at:`2026-${month}-${e.day}T${e.time}:00+08:00`,zone:'Asia/Shanghai',source:nbsCalendar,verified:'2026-10-04',reading:e.reading}))),
 ...([['10-27','10-28'],['12-08','12-09']] as const).map(([start,end])=>({id:`fomc-${start}`,market:'us' as const,name:'美联储FOMC会议',date:`2026-${start}`,endDate:`2026-${end}`,zone:'America/New_York',source:fedCalendar,verified:'2026-10-04',reading:'观察政策决定、声明与经济预测；日历只核到会议日期，不推断公布时刻或降息。'})),
];
export function upcomingPolicyEvents(market:Market,today:string){return policyEvents.filter(e=>e.market===market&&(e.endDate??e.date)>=today);}
export function policyEventText(e:PolicyEvent){return e.at?`${e.name} · 中国${localEventTime(e.at,'Asia/Shanghai')}`:`${e.name} · 美东日期${e.date}—${e.endDate}（未核公布时刻）`;}
export function eventAnswer(market:Market,today:string){const next=upcomingPolicyEvents(market,today);const bls=market==='us'?upcomingEvents(`${today}T00:00:00Z`):[];return ['### 近期已核安排（选定快照）',...next.map(e=>`${policyEventText(e)}。[官方日历](${e.source})；核查${e.verified}。${e.reading}`),...bls.map(e=>`${e.name} · 美东${localEventTime(e.at,'America/New_York')} / 中国${localEventTime(e.at,'Asia/Shanghai')}。[BLS安排](${e.source})。`),!next.length&&!bls.length?'快照中无剩余安排，不代表没有事件；先核官方更新。':'安排可能改期；会议日期和指标所属期不是同一件事。','尚无一致口径的预期值、实际值和首次公布版本，不能判断超预期或事件后的收益。'].join('\n\n');}
