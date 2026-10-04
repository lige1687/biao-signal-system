import {purposes,purposeReading,orderMetrics,type Purpose} from './purpose-model';
import {loadContext} from './context-model';
import {allMetrics as metrics} from './metric-catalog';
import ObservationPanel from './ObservationPanel';
import {observedFrequency,qualityNote,cnValuationAudit} from './data-quality';
import { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import TrendChart from '../../components/trend/TrendChart';
import { formatValue, groups, lastReading, loadHistory,  periodLabel, referencesFor, windowSeries, yRangeFor, type Market, type Metric, type Series, type WindowYears, shanghaiToday } from './dashboard-model';
import './dashboard.css';
import {evidenceFor} from './reference-evidence';

function Plot({metric,series,years,showLines,large=false}:{metric:Metric;series:Series;years:WindowYears;showLines:boolean;large?:boolean}) {
  const window=windowSeries(series,years);
  const marks=showLines?referencesFor(metric.key,window):[];
  return <div className="md-plot" role="img" aria-label={`${metric.title}历史曲线，${window.dates[0]}至${window.dates[window.dates.length-1]}；${showLines?'含参考线':'参考线已隐藏'}`}>
    <TrendChart dates={metric.frequency==='月'?window.dates.map(d=>d.slice(0,7)):window.dates} series={[{name:metric.title,values:window.values,color:'#527db8'}]} unit={metric.unit} markLines={marks.map(r=>({...r,label:r.kind==='定义线'?r.label:r.label.split(' · ')[0]}))} yRange={yRangeFor(window,marks)} height={large?420:230}/>
  </div>;
}
function Reading({metric,series}:{metric:Metric;series?:Series}) {
  const refs=referencesFor(metric.key,series); const evidence=evidenceFor(metric.key);
  return <div className="md-reading"><p>{metric.reading}</p>{refs.length>0 && <ul className="md-reading-lines">{refs.map(r=><li key={r.y}><strong className={`md-tone-text-${r.tone}`}>{r.label}</strong>：{r.explanation}<small>{r.kind} · {r.basis}</small></li>)}</ul>}{evidence && <p><a href={evidence.url} target="_blank" rel="noreferrer">{evidence.title} ↗</a> · 定义核查 {evidence.verified}。{evidence.meaning}</p>}<p>{series?.source?.source_url&&<a href={series.source.source_url} target="_blank" rel="noreferrer">核供方与系列 ↗</a>} 来源路径：{metric.source}。名称依据现有实现；逐期首次公布/修订尚缺；补充指标的供方取得时间与首次公布分开。</p></div>;
}
function Card({metric,series,years,showLines,pending,failed,onExpand,market}:{market:Market;metric:Metric;series?:Series;years:WindowYears;showLines:boolean;pending:boolean;failed:boolean;onExpand:(button:HTMLButtonElement)=>void}) {
  const inputQuality=qualityNote(metric,series,shanghaiToday());
  metric={...metric,frequency:observedFrequency(metric,series)};
  const latest=lastReading(series), refs=referencesFor(metric.key,series?windowSeries(series,years):undefined);
  return <article id={`metric-${metric.key}`} className="md-card" data-metric={metric.key}>
    <header><div><p className="md-category">{groups[metric.group]} · {metric.frequency}频</p><h2>{metric.title}</h2></div><button className="md-expand" aria-label={`放大${metric.title}`} disabled={!latest} onClick={e=>onExpand(e.currentTarget)}>放大 ↗</button></header>
    <div className="md-number">{latest?formatValue(latest.value,metric.unit):'—'}</div>
    <div className="md-period">{latest?periodLabel(latest.date,metric.frequency):'暂无有效观测'}</div>
    <div className="md-change">{latest?.change!==null && latest?.change!==undefined ? <>较上一有效观测 {latest.change>0?'+':''}{formatValue(latest.change,metric.unit==='%'?'百分点':metric.unit)} <span>（{latest.previousDate?.slice(0,metric.frequency==='月'?7:10)}）</span></> : '变化暂不可比'}</div>
    {latest && series ? <Plot metric={metric} series={series} years={years} showLines={showLines}/> : <div className="md-empty" role="status">{pending?'正在读取曲线…':failed?'资料暂不可用，可重新读取':series?.notice || '本次未取得历史数据'}</div>}
    {latest?.trailingMissing && <p className="md-warning">末期读数缺失，上方显示最近有效观测。</p>}
    {latest && series?.notice && <p className="md-warning">{series.notice}</p>}
    <div className="md-reference" aria-label="阈值与参考">{refs.length ? <><span>{!latest?'参考定义':showLines?'图中虚线':'参考线已隐藏'}：</span>{refs.map(r=><span className={`md-ref-chip md-tone-${r.tone}`} title={r.explanation} key={r.y}>{r.label}<small>{r.kind}</small></span>)}</> : <span>无经核验的固定投资阈值 · 本项不画分位或有效历史不足</span>}</div>
    <p className={/不一致|市盈率口径/.test(inputQuality)?"md-warning":"md-meta"}>{inputQuality}</p>{metric.key==='pe_cn'&&<a href={cnValuationAudit.url} target="_blank" rel="noreferrer">核查官方月报（{cnValuationAudit.period}）↗</a>}
    <a href={`/market-understanding?market=${market}&metric=${metric.key}#index-comparison`}>与指数对照 ↗</a><details><summary>怎么看 · 与什么一起看</summary><Reading metric={metric} series={series?windowSeries(series,years):undefined}/></details>
  </article>;
}
function Enlarged({metric,series,years,showLines,onClose,opener}:{metric:Metric;series:Series;years:WindowYears;showLines:boolean;onClose:()=>void;opener:HTMLButtonElement|null}) {
  const ref=useRef<HTMLDialogElement>(null);
  useEffect(()=>{const dialog=ref.current!;dialog.showModal();return ()=>{dialog.close();opener?.focus();};},[opener]);
  metric={...metric,frequency:observedFrequency(metric,series)};
  const value=lastReading(series);
  return <dialog ref={ref} className="md-dialog" onCancel={e=>{e.preventDefault();onClose();}} aria-labelledby="md-dialog-title">
    <header><div><h2 id="md-dialog-title">{metric.title}</h2><p>{value && `${formatValue(value.value,metric.unit)} · ${periodLabel(value.date,metric.frequency)}`}</p></div><button autoFocus onClick={onClose} aria-label="关闭放大图">关闭 ×</button></header>
    <Plot metric={metric} series={series} years={years} showLines={showLines} large/>
    <p className="md-meta">曲线窗口：截至本指标最新所属期。可在图内缩放；参考线不参与技术买卖判定。</p><Reading metric={metric} series={series?windowSeries(series,years):undefined}/>
  </dialog>;
}
export default function MarketDashboard({embedded=false}:{embedded?:boolean}) {
  const [market,setMarket]=useState<Market>(new URLSearchParams(window.location.search).get('market')==='us'?'us':'cn');
  const requested=new URLSearchParams(window.location.search).get('metric');
  const [group,setGroup]=useState<keyof typeof groups>(metrics.find(m=>m.key===requested)?.group??'all');
  const [purpose,setPurpose]=useState<Purpose>('all');
  const [years,setYears]=useState<WindowYears>(3);
  const [showLines,setShowLines]=useState(true);
  const [expanded,setExpanded]=useState<string|null>(null);
  const opener=useRef<HTMLButtonElement|null>(null);
  const rates=useQuery({queryKey:['market-dashboard','rates'],queryFn:({signal})=>loadHistory('rates',signal),staleTime:300_000,retry:false});
  const macro=useQuery({queryKey:['market-dashboard','macro'],queryFn:({signal})=>loadHistory('macro',signal),enabled:market==='cn',staleTime:300_000,retry:false});
  const usMacro=useQuery({queryKey:['market-dashboard','usMacro'],queryFn:({signal})=>loadHistory('usMacro',signal),enabled:market==='us',staleTime:300_000,retry:false});
  const context=useQuery({queryKey:['market-context',1],queryFn:({signal})=>loadContext(signal),staleTime:300_000,retry:false});
 const queries={rates,macro,usMacro,context};
  const selected=metrics.filter(m=>m.market.includes(market));
  const visible=orderMetrics(selected.filter(m=>group==='all'||m.group===group),purpose);
  const count=selected.filter(m=>lastReading(queries[m.endpoint].data?.series[m.key])).length;
  const relevant=[rates,market==='cn'?macro:usMacro,context];
  const isFetching=relevant.some(q=>q.isFetching);
  const failures=relevant.filter(q=>q.isError).length;
  const sourceErrors=relevant.reduce((n,q)=>n+(q.data?.errors??0),0);
  const large=visible.find(m=>m.key===expanded);
  const largeSeries=large?queries[large.endpoint].data?.series[large.key]:undefined;
  useEffect(()=>{if(requested&&!isFetching)document.getElementById(`metric-${requested}`)?.scrollIntoView({block:'center'});},[requested,isFetching]);
  return <main className={`md-dashboard${embedded?' md-dashboard-embedded':''}`}>
    <header className="md-heading"><div>{embedded?<h2>数据总览</h2>:<><h1>市场数据</h1><p>利率、估值、资金与经济变化</p></>}</div><div className="md-market" aria-label="观察市场">{([['cn','A股'],['us','美股']] as const).map(([id,label])=><button key={id} aria-pressed={market===id} onClick={()=>{setMarket(id);setGroup('all');setExpanded(null);}}>{label}</button>)}</div></header>
    <div className="md-color-legend" aria-label="参考线颜色含义"><span className="md-tone-opportunity">绿色 · 机会观察 / 环境支持</span><span className="md-tone-watch">橙色 · 需要留意</span><span className="md-tone-risk">红色 · 风险压力</span><span className="md-tone-context">蓝色 · 分界 / 结合判断</span><small>分位线描述当前窗口的历史位置；颜色提示观察方向，不代表该位置已验证收益。原固定经验线已撤下。</small></div>
    <p className="md-meta"><label>观察目的 <select value={purpose} onChange={e=>setPurpose(e.target.value as Purpose)}>{Object.entries(purposes).map(([id,label])=><option key={id} value={id}>{label}</option>)}</select></label> · {purposeReading[purpose]}</p>
    <div className="md-toolbar"><div className="md-groups" aria-label="指标分类">{Object.entries(groups).map(([id,label])=><button key={id} aria-pressed={group===id} onClick={()=>setGroup(id as keyof typeof groups)}>{label}</button>)}</div><div className="md-options"><label>区间 <select value={years} onChange={e=>setYears(e.target.value==='all'?'all':Number(e.target.value) as 1|3)}><option value={1}>近1年</option><option value={3}>近3年</option><option value="all">已取得全部</option></select></label><label><input type="checkbox" checked={showLines} onChange={e=>setShowLines(e.target.checked)}/>参考线</label><button disabled={isFetching} onClick={()=>{void context.refetch();void rates.refetch();void (market==='cn'?macro:usMacro).refetch();}}>{isFetching?'读取中…':'重新读取'}</button></div></div>
    <div className="md-status" role="status"><span>{market==='cn'?'A股':'美股'} · 已有读数 {count}/{selected.length} 项{isFetching?' · 更新中':''}</span><span>各图按自身日期显示 · 月度数据标所属月 · 参考线不代表买卖条件</span></div>
    {(failures>0 || (sourceErrors>0 && count<selected.length)) && <p className="md-warning">{failures>0?`${failures}组接口暂不可用。`:''}{sourceErrors>0?'共享资料接口有缺失提示。':''}已取得的曲线仍可查看，空缺不会填成零值。</p>}
    <ObservationPanel market={market} today={shanghaiToday()}/>
    <section className="md-grid" aria-label={`${market==='cn'?'A股':'美股'}指标图表`}>{visible.map(m=>{const q=queries[m.endpoint];return <Card key={m.key} market={market} metric={m} series={q.data?.series[m.key]} years={years} showLines={showLines} pending={q.isPending} failed={q.isError} onExpand={button=>{opener.current=button;setExpanded(m.key);}}/>;})}</section>
    <footer className="md-footer"><p>显示最近已取得的数据，未确认全部为最新发布；资料所属期不是发布时间。区间以每项最新所属期为终点，切换区间不会补取更早历史。</p><details><summary>当前覆盖与缺项</summary><p>A股：两融、利率、估值及月度经济；美股：利率、估值、波动、信用与经济。接口无有效历史时保留空卡。FINRA美国融资、CFTC持仓、盈利预期、完整事件日历等尚未接到这些图表（首批美国安排见“指数对照与事件”）；情绪研究与技术判定仍沿用各自模块。</p><p>这次增加的是已有市场资料的直接展示；没有新增交易条件，也未测量对投资收益的影响。</p></details></footer>
    {large && largeSeries && <Enlarged metric={large} series={largeSeries} years={years} showLines={showLines} onClose={()=>setExpanded(null)} opener={opener.current}/>}
  </main>;
}
