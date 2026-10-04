import {relationsFor} from './etf-relations';
import {upcomingPolicyEvents,policyEventText} from './policy-events';
import {allMetrics as metrics} from './metric-catalog';
import {observedFrequency,qualityNote} from './data-quality';
import {useEffect,useRef,useState} from 'react';
import * as echarts from 'echarts';
import {useSearchParams} from 'react-router-dom';
import {referencesFor,shanghaiToday,type Market,type Metric,type WindowYears,type Series} from './dashboard-model';
import {alignComparison,changes,correlation,divergence,choicesFor,type Pair} from './comparison-model';
import {indexOverlayOption,overlayNumber} from './index-overlay-model';
import {useMarketData} from './use-market-data';
import {marketEvents,eventDate,localEventTime,upcomingEvents,calendarSource,calendarVerified,calendarExpired} from './events';
import {evidenceFor} from './reference-evidence';
import './dashboard.css';
function ComparisonPlot({pairs,metric,indexTitle,mode,showEvents,market,refs}:{pairs:Pair[];metric:Metric;indexTitle:string;mode:'time'|'scatter';showEvents:boolean;market:Market;refs:ReturnType<typeof referencesFor>}){
 const ref=useRef<HTMLDivElement>(null);
 useEffect(()=>{
  if(!ref.current)return;const chart=echarts.init(ref.current),points=changes(pairs,metric.frequency),dates=pairs.map(p=>p.date);
  const lines=showEvents&&market==='us'?marketEvents.filter(e=>dates.includes(eventDate(e.at))).map(e=>({xAxis:eventDate(e.at),name:e.name,label:{show:false},tooltip:{formatter:`${e.name} · 所属${e.period} · 美东${localEventTime(e.at,'America/New_York')} / 中国${localEventTime(e.at,'Asia/Shanghai')}`},lineStyle:{color:'#98734a',type:'dotted'}})):[];
  const option:echarts.EChartsOption=mode==='scatter'?{
   tooltip:{trigger:'item',formatter:(p:unknown)=>{const d=(p as {data:number[]}).data,i=d[2];return `${points[i].from} → ${points[i].date}<br/>指标变化 ${d[0].toFixed(2)} ${metric.unit}<br/>指数涨跌 ${d[1].toFixed(2)}%`; }},
   grid:{left:68,right:25,top:38,bottom:62},xAxis:{type:'value',name:`指标变化（${metric.unit}）`,nameLocation:'middle',nameGap:35,scale:true},yAxis:{type:'value',name:'指数涨跌（%）',scale:true},dataZoom:[{type:'inside',xAxisIndex:0},{type:'inside',yAxisIndex:0}],series:[{type:'scatter',symbolSize:7,itemStyle:{color:'#4778b0',opacity:.6},data:points.map((p,i)=>[p.metricChange,p.indexReturn,i])}],
  }:indexOverlayOption(pairs,metric,indexTitle,refs.map(r=>({yAxis:r.y,name:r.label,lineStyle:{color:r.color,type:'dashed'},label:{formatter:r.label.split(' · ')[0],fontSize:9,position:'insideEndBottom'}})),lines);
  chart.setOption(option);const ro=new ResizeObserver(()=>chart.resize());ro.observe(ref.current);return()=>{ro.disconnect();chart.dispose();};
 },[pairs,metric,indexTitle,mode,showEvents,market,refs]);
 return <div ref={ref} style={{height:380,width:'100%'}} role="img" aria-label={`${indexTitle}价格与${metric.title}${mode==='scatter'?'变化散点':'走势叠加图：蓝线价格看左轴，橙线指标看右轴'}`}/>;
}
function PairCard({metric,s,index,indexTitle,years,today,mode,showEvents,market}:{metric:Metric;s?:Series;index?:Series;indexTitle:string;years:WindowYears;today:string;mode:'time'|'scatter';showEvents:boolean;market:Market}){
 const inputQuality=qualityNote(metric,s,today);
 metric={...metric,frequency:observedFrequency(metric,s)};
 const pairs=s&&index?alignComparison(s,index,metric.frequency,years,today):[],valid=pairs.filter(p=>p.metric!==null&&p.index!==null),points=changes(pairs,metric.frequency),r=correlation(points),note=divergence(points,metric.key);
 const refs=referencesFor(metric.key,{dates:pairs.map(p=>p.date.length===7?p.date+'-01':p.date),values:pairs.map(p=>p.metric),notice:''}),ev=evidenceFor(metric.key);
 const last=valid[valid.length-1];
 return <article className="md-card md-pair-card"><header><h2>{indexTitle}价格与{metric.title}</h2><span>{metric.frequency}频 · 同期走势</span></header>
 {mode==='time'&&<><div className="md-overlay-key"><span className="md-overlay-index">蓝线 · {indexTitle}价格 · 左轴{last&&<strong>{overlayNumber(last.index)} 点</strong>}</span><span className="md-overlay-metric">橙线 · {metric.title} · 右轴{last&&<strong>{overlayNumber(last.metric)} {metric.unit}</strong>}</span></div><p className="md-meta">{last?`共同期末 ${last.date}；下方悬停可看每期原值。`:'两条线使用同一日期轴。'}两侧各按自己的单位缩放，线的交点不表示买卖点。</p></>}
 {valid.length>=2?<ComparisonPlot pairs={pairs} metric={metric} indexTitle={indexTitle} mode={mode} showEvents={showEvents} market={market} refs={refs}/>:<p className="md-empty" role="status">尚无足够共同观测，暂不能作图。{s?.notice} {index?.notice}</p>}
 <p className="md-meta">{valid.length?`${valid[0].date}—${valid[valid.length-1].date} · ${valid.length}个共同观测`:'无共同日期'}。看同一段时间，蓝线涨跌时橙线是升、降，还是没有明显变化；不根据曲线贴合程度判断关系。</p>
 <p className="md-overlay-reading"><strong>橙线怎么看：</strong>{metric.reading}</p>
 {note&&<p className="md-warning">{note}</p>}

 <details><summary>参考线、来源与进阶统计</summary><p>{inputQuality}</p><p>{points.length}个完整相邻变化区间。{r===null?'变化相关系数暂不可算':`变化相关系数 ${r.toFixed(2)}`}（−1至1，表示同期变化的同向程度，不证明因果或领先）。</p><p>{metric.frequency==='日'?'仅同一天配对；散点跨超过4自然日的断档不计算。':'按同所属期间最后观测配对，当前未结束期间排除。'}月度标签是所属月，不是公布日；历史可能已修订，只能回看同步变化。散点横轴是指标绝对变化，纵轴是同区间指数涨跌，不含未来收益。</p>{ev&&<p><a href={ev.url} target="_blank" rel="noreferrer">{ev.title} ↗</a> · {ev.meaning}</p>}<p>指标来源：{metric.source}。指数沿现有overlay-history链；指数身份见上方。单位和日期格式已检查，上游数值真实性与逐期发布资格未完整核实。</p>{refs.map(x=><p key={x.label}><strong style={{color:x.color}}>{x.label}</strong>：{x.explanation} {x.basis}</p>)}</details>
 </article>;
}
export default function IndexComparison(){
 const [params]=useSearchParams(),[market,setMarket]=useState<Market>(params.get('market')==='us'?'us':'cn'),[indexKey,setIndexKey]=useState(params.get('market')==='us'?'sp500':'hs300'),[key,setKey]=useState(params.get('metric')??(params.get('market')==='us'?'vix':'margin_rzyezb')),[second,setSecond]=useState(''),[years,setYears]=useState<WindowYears>(3),[mode,setMode]=useState<'time'|'scatter'>('time'),[showEvents,setShowEvents]=useState(false);
 const data=useMarketData(market,true),options=metrics.filter(m=>m.market.includes(market)),index=choicesFor(market).find(i=>i.key===indexKey)!,selected=options.find(m=>m.key===key)??options[0],extra=options.find(m=>m.key===second),today=shanghaiToday(),expired=calendarExpired(today);
 return <main className="md-dashboard"><header className="md-heading"><div><h2>指数价格与指标走势叠加</h2><p>同一张图、同一段时间：蓝线看指数价格，橙线看指标升降。</p></div><a href={`/agent?macro=1&market=${market}`}>让Agent解读 ↗</a></header>
 <div className="md-comparison-controls"><label>市场<select value={market} onChange={e=>{const m=e.target.value as Market;setMarket(m);setIndexKey(m==='cn'?'hs300':'sp500');setKey(m==='cn'?'margin_rzyezb':'vix');setSecond('');}}><option value="cn">A股</option><option value="us">美股</option></select></label><label>指数<select value={indexKey} onChange={e=>setIndexKey(e.target.value)}>{choicesFor(market).map(i=><option key={i.key} value={i.key}>{i.title}</option>)}</select></label><label>指标<select value={selected.key} onChange={e=>setKey(e.target.value)}>{options.map(m=><option key={m.key} value={m.key}>{m.title}</option>)}</select></label><label>配套指标<select value={second} onChange={e=>setSecond(e.target.value)}><option value="">不叠加</option>{options.filter(m=>m.key!==selected.key).map(m=><option key={m.key} value={m.key}>{m.title}</option>)}</select></label><label>区间<select value={years} onChange={e=>setYears(e.target.value==='all'?'all':Number(e.target.value) as 1|3)}><option value={1}>近1年</option><option value={3}>近3年</option><option value="all">已取得全部</option></select></label></div>
 <div className="md-comparison-controls"><button onClick={()=>{setKey(market==='us'?'vix':'margin_rzyezb');setSecond(market==='us'?'hy_oas':'cn_10y');}}>风险与融资组合</button><button onClick={()=>{setKey(market==='us'?'cape_us':'pe_cn');setSecond(market==='us'?'us_10y':'cn_10y');}}>估值与利率组合</button></div>
 <details className="md-overlay-advanced"><summary>更多看法：变化散点与事件标记</summary><div className="md-comparison-controls"><button aria-pressed={mode==='time'} onClick={()=>setMode('time')}>走势叠加</button><button aria-pressed={mode==='scatter'} onClick={()=>setMode('scatter')}>变化散点（进阶）</button>{market==='us'&&<label><input type="checkbox" checked={showEvents&&mode==='time'&&observedFrequency(selected,data.series[selected.key])==='日'} disabled={mode!=='time'||observedFrequency(selected,data.series[selected.key])!=='日'} onChange={e=>setShowEvents(e.target.checked)}/>事件标记（仅日频；悬停虚线看详情）</label>}</div></details>
 {mode==='scatter'&&<p className="md-meta">当前为变化散点。<button onClick={()=>setMode('time')}>返回价格与指标叠加</button></p>}
 <p className="md-meta">{index.source} · {data.pending?'读取资料中…':'已读取现有资料'} · 只展示有共同观测的部分；不填补缺失，不画预测线。</p>{data.failed&&<p className="md-warning" role="status">部分接口失败，现有曲线仍保留。<button onClick={data.retry}>重新读取</button></p>}

 <section className="md-pair-grid">{[selected,...(extra&&extra.key!==selected.key?[extra]:[])].map(m=><PairCard key={m.key} metric={m} s={data.series[m.key]} index={data.indices[indexKey]} indexTitle={index.title} years={years} today={today} mode={mode} showEvents={showEvents} market={market}/>)}</section>
 <details className="md-card md-overlay-supplement"><summary>{index.title}相关ETF资料（补充）</summary>{relationsFor(indexKey).map(x=><p key={x.code}><strong>{x.code} {x.name}</strong> · {x.currency}。{x.expense&&`${x.expense}。`}{x.limitation} <a href={x.source} target="_blank" rel="noreferrer">原始披露 ↗</a><small> {x.version}；核查{x.verified}</small></p>)}<p className="md-meta">这里只核对应关系；费用仅标已核披露，分红、流动性和跟踪差异尚未接齐，指数曲线不能替代ETF实际回报。</p><p>{market==='cn'?<a href="/sectors">看已有行业板块 ↗</a>:<a href="/market-understanding#fund-sec-market">看已有美国行业ETF相对强弱 ↗</a>} · 行业权重尚缺；相对强弱与订单分类资金不等于ETF净申赎。</p></details>
 <details className="md-event-panel"><summary>发布日历与资料缺口（补充）</summary>{upcomingPolicyEvents(market,today).map(e=><p key={e.id}>{policyEventText(e)} · {e.reading} <a href={e.source} target="_blank" rel="noreferrer">官方安排 ↗</a></p>)}<p>新补选定中国发布 / FOMC快照核查2026-10-04，安排可能改期，不包含一致预期与实际值。</p>{market==='us'?<><p>首批为BLS选定的2026就业/CPI/PPI安排，非完整日历。核查{calendarVerified}，覆盖至2026-10；{expired?'快照已过期，请核官方新日历':'临近发布仍需核官方是否改期'}。不提供无来源的市场预期或实际值。</p><a href={calendarSource} target="_blank" rel="noreferrer">官方发布日历 ↗</a><ul>{upcomingEvents(new Date().toISOString()).map(e=><li key={e.at}>{e.name} · 数据所属{e.period} · 美东 {localEventTime(e.at,'America/New_York')} / 中国 {localEventTime(e.at,'Asia/Shanghai')}</li>)}</ul>{upcomingEvents(new Date().toISOString()).length===0&&<p>本快照没有尚未到期的安排，不能据此判断近期无事件。</p>}</>:<p>中国选定发布安排见上方；尚非完整日历，PMI/CPI所属月份与计划发布日期分开。</p>}<p>下一批缺口：盈利预期与修订、FINRA融资、CFTC分类头寸、完整收益率曲线/实际利率、净资金流与完整ETF成本。候选尚未接入或验证；宏观资格/情绪研究依远端原负责人，不重复启动。</p></details>
 </main>;
}
