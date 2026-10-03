import {observedFrequency,qualityNote,cnValuationAudit} from './data-quality';
import {observationSnapshot,observationText} from './observation-model';
export {ageNotice} from './data-quality';
import {ageNotice} from './data-quality';
import {metrics,lastReading,formatValue,periodLabel,referencesFor,windowSeries,type Market,type Series} from './dashboard-model';
import {evidenceFor} from './reference-evidence';
export function isMacroQuestion(q:string){return /宏观|通胀|国债|利率|就业|非农|PMI|CPI|PPI|VIX|WEI|信用利差|两融|融资余额|股债|CAPE|估值|增长|资金流/i.test(q)&&! /买了|卖了|成交了|报单|申购|赎回/.test(q);}
export function questionKeys(q:string):string[]{
 const rules:[RegExp,string[]][]=[[/PMI|景气/i,['pmi','wei','dgorder_yoy']],[/通胀|CPI|PPI/i,['cpi','ppi','cpiaucsl_yoy','ppiaco_yoy']],[/利率|国债/,['cn_10y','us_10y','cn_us_spread_10y','hy_oas']],[/波动|VIX|信用|风险/i,['vix','hy_oas','margin_rzyezb','icwa']],[/两融|融资|杠杆/,['margin_rzrqye','margin_rzyezb']],[/估值|CAPE|股债/i,['pe_cn','cape_us','erp_cn','erp_us']],[/增长|经济/,['pmi','wei','payems_yoy','dgorder_yoy']],[/就业/,['icwa','ccwa','payems_yoy']]];
 return [...new Set(rules.filter(([re])=>re.test(q)).flatMap(([,keys])=>keys))];
}
export function isMacroFollowup(q:string){
 if(/买了|卖了|成交了|报单|申购|赎回|持仓|账户|机会|回测|股票|\d{4,}/.test(q))return false;
 return /^(那)?(A股|美股|中国|美国).*呢[？?]?$/.test(q.trim())||/^(这条线|这个阈值|为什么[？?]?$|最近怎么变|最近变化)/.test(q.trim())||(/^(跟|结合|还有)/.test(q.trim())&&isMacroQuestion(q));
}

export interface MacroContext {market:Market;question:string;topic:string;needsContext:boolean}
export function resolveMacroQuestion(q:string,previous:MacroContext|null,fallback:Market):MacroContext{
 const market=/美国|美股|标普|纳斯达克/.test(q)?'us':/中国|A股|沪深|上证/i.test(q)?'cn':previous?.market??fallback;
 const follow=/^(那|这个|这条|它|跟|结合|为什么|怎么看|最近|还有)/.test(q.trim())||/一起看|结合看|呢[？?]?$/.test(q.trim());
 const needsContext=(!previous&&follow&&!questionKeys(q).length)||(/这条线|这个阈值/.test(q)&&!questionKeys(q).length);
 const clean=(text:string)=>text.replace(/美国|美股|标普|纳斯达克|中国|A股|沪深|上证/gi,'').slice(0,200);
 const prior=previous?.topic??clean(previous?.question??'');
 const topic=follow&&previous?(questionKeys(q).length?`${prior}；${clean(q)}`.slice(0,300):prior):clean(q);
 return {market,topic,question:follow&&previous?`${q}（前题：${prior}）`:q,needsContext};
}
export function macroAnswer(market:Market,series:Record<string,Series>,question:string,today:string,readAt:string,indices:Record<string,Series>={}):string {
 const wanted=questionKeys(question),selected=metrics.filter(m=>m.market.includes(market)&&(wanted.length?wanted.includes(m.key):['cn_10y','us_10y','pmi','cpi','cpiaucsl_yoy','hy_oas','vix','margin_rzyezb','cape_us'].includes(m.key)));
 const lines=[`### ${market==='cn'?'A股':'美股'}宏观资料解读`,`本次整理：${readAt}。这是按系统已取得数据整理的解读；各项所属期如下，整理时间不是首次公布时间。`];
 if(/买|卖|预测|收益|涨多少|抄底|必涨|必跌/.test(question))lines.push('这些背景资料不能单独确定买卖、未来涨跌或收益。需要结合原技术条件与个人计划；下方仅回答目前能核查的事实。');
 const snapshot=observationSnapshot(market,series,indices,today);
 lines.push('### 最近观测变化',...snapshot.changes.filter(x=>!wanted.length||wanted.includes(x.key)).slice(0,5).map(observationText),'按各项观测期排序，不代表刚刚发布；所属期、读取时间与首次发布时间不同。');
 const current=selected.flatMap(m=>{const x=lastReading(series[m.key]);return x?[{m,x}]:[];});
 lines.push('### 当前状态与变化');
 if(current.length)lines.push(current.map(({m,x})=>`${m.title}：${formatValue(x.value,m.unit)}（${periodLabel(x.date,observedFrequency(m,series[m.key]))}），${x.change===null?'变化不可比':x.change>0?'较前一有效观测上升':x.change<0?'较前一有效观测下降':'较前一有效观测持平'}`).join('；')+'。');else lines.push('本次没有可用数据，无法给出当前环境判断。');
 lines.push('### 证据是否相互支持');
 const prices=current.filter(({m})=>['cpi','ppi','cpiaucsl_yoy','ppiaco_yoy'].includes(m.key));
 if(prices.length===2&&prices[0].x.date===prices[1].x.date&&prices.every(({x})=>x.change!==null&&x.change>0))lines.push('同所属月的两项价格同比读数均较前次升高，支持物价涨幅扩大的观察；仍需核核心价格、需求与基数，不代表股市一定下跌。');
 else lines.push('先按下方每项所属期和变化核对，不能把不同频率或缺失资料拼成一致判断。利率、增长、信用与估值需要一起看。');
 if(snapshot.conflicts.length)lines.push('### 同段不一致观察',...snapshot.conflicts);
 const relevantGroups=snapshot.groups.filter(g=>g.rows.some(x=>wanted.includes(x.key)));
 lines.push('### 与什么一起看',...(wanted.length?relevantGroups:snapshot.groups).map(g=>`${g.title}：${g.reading} 反例：${g.counterexample} 尚缺：${g.rows.filter(x=>!x.reading).map(x=>x.title).join('、')||'本次列出的字段有读数，但发布和修订仍需核实'}。`));
 lines.push('### 逐项依据与参考线（近3年已取得历史）');
 let available=0;
 for(const m of selected){const s=series[m.key],r=lastReading(s);lines.push(`
### ${m.title}`);if(!r){lines.push('本次未取得合格观测，无法判断；不补成零。');continue;}available++;
 lines.push(`当前已取得 ${formatValue(r.value,m.unit)} · ${periodLabel(r.date,observedFrequency(m,s))}；${r.change===null?'无可比前值':`较${r.previousDate} ${r.change>0?'+':''}${formatValue(r.change,m.unit==='%'?'百分点':m.unit)}`}。`);
 const age=ageNotice(r.date,observedFrequency(m,s),today);if(age)lines.push(age);if(r.trailingMissing)lines.push('末期缺值，显示的是最近有效观测。');
 lines.push(m.reading,qualityNote(m,s,today));if(m.key==='pe_cn')lines.push(`[核查官方月报：${cnValuationAudit.period}](${cnValuationAudit.url})，核查${cnValuationAudit.verified}；这个历史单点不是今天官方估值。`);const refs=referencesFor(m.key,s?windowSeries(s,3):undefined);if(refs.length){lines.push(...refs.map(x=>`${x.label}：${x.explanation}${x.sourceUrl?` [定义来源](${x.sourceUrl})`:''}`));lines.push(...new Set(refs.map(x=>x.basis)));}else lines.push('没有经核验的固定投资阈值。');
 const ev=evidenceFor(m.key);if(ev)lines.push(`[${ev.title}](${ev.url})，定义核查${ev.verified}。${ev.meaning}`);
 lines.push(`数据路径：${m.source}。[看图核查](/market-understanding?market=${market}&metric=${m.key}#overview)`);
 }
 lines.push(`
### 还要核查什么
本次${available}/${selected.length}项有有效观测。不同频率和所属期不能混称“今天一起发生”。利率下降可能来自增长转弱；估值下降可能来自盈利变化。历史分位描述位置，不证明买点或危险线有效。逐期首次公布/修订、预期差、盈利预期、完整中国事件日历尚缺，相关判断暂不能完成。`);
 return lines.join('\n\n');
}
