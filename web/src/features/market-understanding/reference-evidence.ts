import type {Reference} from './dashboard-model';
import {referenceColors} from './reference-reading';
export const officialSources = {
 pmi: {title:'国家统计局 · PMI定义',url:'https://zjzd.stats.gov.cn/gjtjjtzdcd/dczs/tjbw/art/2024/art_b136331cbe474e8c86d51c01effd651b.html',verified:'2026-10-03',meaning:'50以上表示调查活动相对上月扩张，以下表示收缩；不是经济同比增速或买卖点。'},
 vix: {title:'Cboe · VIX方法',url:'https://cdn.cboe.com/api/global/us_indices/governance/Volatility_Index_Methodology_Cboe_Volatility_Index.pdf',verified:'2026-10-03',meaning:'来自标普500期权的未来30天预期波动，采用年化表达；不能推断上涨或下跌。'},
 inflation: {title:'美联储 · 通胀目标口径',url:'https://www.federalreserve.gov/faqs/economy_14419.htm',verified:'2026-10-03',meaning:'长期2%目标针对PCE价格指数，不能把CPI的2%写成政策目标。'},
};
export function evidenceFor(key:string) {return key==='pmi'?officialSources.pmi:key==='vix'?officialSources.vix:key==='cpiaucsl_yoy'?officialSources.inflation:null;}
export function quantile(values:number[],p:number):number {
 const sorted=[...values].sort((a,b)=>a-b),pos=(sorted.length-1)*p,lo=Math.floor(pos);
 return sorted[lo]+(sorted[Math.ceil(pos)]-sorted[lo])*(pos-lo);
}
export function historicalReferences(key:string,s?:{dates:string[];values:(number|null)[]}):Reference[] {
 if(!s || ['margin_rzrqye','margin_rzye','margin_rqye','margin_buy'].includes(key))return [];
 const valid=s.values.flatMap((v,i)=>v===null?[]:[{v,d:s.dates[i]}]);
 if(valid.length<12)return []; // display minimum, not a scientific significance threshold
 const values=valid.map(x=>x.v);if(Math.min(...values)===Math.max(...values))return [];
 const basis=`当前取得历史 ${valid[0].d}—${valid[valid.length-1].d}，${values.length}个有效观测；排序后在(n−1)×p位置线性插值；随窗口重算。数据链尚缺逐期首次发布/修订，不能称官方风险标准。`;
 const valuation=['pe_cn','cape_us'].includes(key),compensation=['erp_cn','erp_us','earnings_yield_cn','earnings_yield_us'].includes(key),pressure=['vix','hy_oas','margin_rzyezb'].includes(key);
 return [.2,.5,.8].map((p,i)=>{
 const y=quantile(values,p),tone=valuation?(i===0?'opportunity':i===2?'watch':'context'):compensation?(i===2?'opportunity':'context'):pressure&&i===2?'risk':'context';
 const meaning=valuation?(i===0?'估值较低，机会观察须核盈利':i===2?'估值较高，留意盈利与利率':'估值中位'):compensation?(i===2?'历史盈利相对价格 / 股债差较高，机会观察须核盈利口径':'历史盈利收益率 / 股债差位置'):pressure?(i===2?'风险观察：该项压力读数较高':'历史位置，不能推断安全'):'历史位置，结合增长与政策判断';
 return {y,tone,color:referenceColors[tone],label:`P${p*100} ${y.toLocaleString('zh-CN',{maximumFractionDigits:2})} · ${meaning}`,explanation:`${Math.round(p*100)}%的历史观测不高于这一位置（插值口径）。${meaning}；不是已验证的买卖阈值。`,kind:'历史分位参考',basis};
 });
}
export function definedReferences(key:string):Reference[] {
 if(key==='pmi')return [{y:50,label:'50 · 扩张 / 收缩分界',tone:'context',color:referenceColors.context,explanation:officialSources.pmi.meaning,kind:'定义线',basis:`${officialSources.pmi.title}；核查2026-10-03`,sourceUrl:officialSources.pmi.url}];
 if(['cpi','ppi','cpiaucsl_yoy','ppiaco_yoy','payems_yoy','cshpi_yoy','dgorder_yoy','wei','cn_us_spread_10y','cn_10_2_spread','us_10_2_spread','erp_us','erp_cn'].includes(key))return [{y:0,label:'0 · 数值正负分界',tone:'context',color:referenceColors.context,explanation:['cn_10_2_spread','us_10_2_spread'].includes(key)?'10年收益率减2年收益率为零；正值长端较高，负值本口径倒挂，不代表自动衰退或买卖。':key==='cn_us_spread_10y'?'中国10年收益率减美国10年收益率为零；不代表多空或资金流分界。':key==='erp_us'||key==='erp_cn'?'市盈率倒数与国债收益率的差为零；不是股票与债券未来回报相等。':'该数值为零的算术基线；不等于官方衰退或市场多空判断。',kind:'定义线',basis:'按本指标计算定义；不附加未经核验的投资阈值'}];
 return [];
}
