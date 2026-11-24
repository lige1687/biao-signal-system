import {useEffect,useMemo,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import {useQuery} from '@tanstack/react-query';
import MarketTrendChart,{type LineSeries} from '../market-style/MarketTrendChart';
import MiniTrend from './MiniTrend';
import ChartLegend from './ChartLegend';
import {concentrationDisplay} from './concentrationDisplay';
import {MemberDispersionDetail,MemberDispersionSummary} from './MemberDispersion';
import {isMemberDispersion,useMemberDispersion} from './memberDispersionData';
import {parseMicrostructure,reading,formatMicro,todayShanghai,selectedMicro,type MicroCard,type MicroPacket} from './microstructureData';
import './microstructure.css';
const BRANCHES=['funding','equity','derivatives'];
const SERIES_COLORS=['#28629e','#c0563b','#327c72','#80678a'];
function series(c:MicroCard,percentile=false):LineSeries[]{const points=percentile?c.percentiles??[]:c.points;const tail=c.id.startsWith('cn-industry-turnover-')?[{label:'95%历史位置',value:95},{label:'98%历史位置',value:98}]:[];const merged=c.lines?.length?c.lines.map((l,i)=>({name:l.label,color:SERIES_COLORS[i%SERIES_COLORS.length],values:l.values})):[{name:percentile?'历史分位':c.title,color:'#28629e',values:points.map(p=>p.value)}];return [...merged,...(percentile?tail:c.references??[]).map(r=>({name:r.label,color:'#9b7953',dashed:true,values:points.map(()=>r.value)}))];}
type ConcentrationContext = ReturnType<typeof concentrationDisplay>;
function ReferenceNote({context}:{context:ConcentrationContext}){
 return context&&<p className="micro-scope">{context.note}{context.dailySource&&<> <a href={context.dailySource} target="_blank" rel="noreferrer">中金研报 ↗</a></>}</p>;
}
function Detail({card,onClose}:{card:MicroCard;onClose:()=>void}){
 const ref=useRef<HTMLDialogElement>(null);const [window,setWindow]=useState(252);const [ready,setReady]=useState(false);
 const dispersion=useMemberDispersion(isMemberDispersion(card.id)?card.id:undefined);
 useEffect(()=>{const trigger=document.activeElement as HTMLElement|null;ref.current?.showModal();setReady(true);return()=>{ref.current?.close();trigger?.focus();};},[]);
 const context=concentrationDisplay(card);
 const points=window?card.points.slice(-window):card.points;const lines=[...series(card),...(context?.overlays??[])].map(s=>({...s,values:window?s.values.slice(-window):s.values}));
 const hasPercentile=card.percentiles?.some(p=>p.value!==null);
 return createPortal(<dialog ref={ref} className="micro-dialog" aria-label={card.title} onCancel={e=>{e.preventDefault();onClose();}} onClick={e=>{if(e.target===e.currentTarget)onClose();}}><header><h2>{card.title}</h2><button onClick={onClose}>关闭 ×</button></header>
 {dispersion ? (ready&&<MemberDispersionDetail card={dispersion}/>) : <>
 <p>{card.scope} · {card.frequency==='daily'?'日频':'月频'} · {points[0]?.date} 至 {points[points.length-1]?.date}</p>
 <div className="micro-period">{[120,252,756,0].map(n=><button key={n} aria-pressed={n===window} onClick={()=>setWindow(n)}>{n?`近${n}期`:'全部'}</button>)}</div>
 {context?.reading&&<p><strong>{context.reading}</strong></p>}
 <ReferenceNote context={context}/>
 {ready&&<MarketTrendChart dates={points.map(p=>p.date)} series={lines} unit={card.unit} precision={card.unit==='相关系数'?3:2} height={hasPercentile?250:330}/>}
 {context?.comparison&&<p>{context.comparison}</p>}
 {card.id==='cn-monthly-amount-top5'&&<p>集中度回落时，对照同月市场宽度和日均成交额。参与面扩大可支持成交扩散的读法；参与面也走弱时，留意主线是否在降温。</p>}
 {hasPercentile&&<><h3>相对此前{card.percentileWindow}期的历史位置</h3><MarketTrendChart dates={points.map(p=>p.date)} series={series(card,true).map(s=>({...s,values:window?s.values.slice(-window):s.values}))} unit="%" height={180} valueBounds={[0,100]}/></>}
 <p>{card.meaning}</p>{card.latestDetails?.map(x=><p key={x.label}>{x.label}：{x.value}</p>)}
 {card.limitations.map(s=><p key={s} className="micro-limit">{s}</p>)}<p><a href={card.sourceUrl} target="_blank" rel="noreferrer">{card.sourceName}</a> · 历史快照，未自动按日更新</p></>}</dialog>,document.body);
}
function Selected({card,showTitle=false}:{card:MicroCard;showTitle?:boolean}){
 const [open,setOpen]=useState(false);const r=reading(card);const context=concentrationDisplay(card);const lines=[...series(card),...(context?.overlays??[])];const recent=card.points.slice(-120);const old=(Date.parse(todayShanghai())-Date.parse(r.date))/86400000>7;
 const isDispersion=isMemberDispersion(card.id);
 const dispersion=useMemberDispersion(isDispersion?card.id:undefined);
 const lastKnown=r.value===null?card.points.slice().reverse().find(p=>p.value!==null):undefined;
 return <article className="micro-reading" data-micro-card={card.id} aria-label={card.title}>
 {showTitle&&<h3>{card.title}</h3>}
 {dispersion ? <MemberDispersionSummary card={dispersion}/> : <>
 <div className="micro-current"><strong>{formatMicro(r.value,card.unit)}</strong><span>{r.date}{old?' · 历史资料':''}</span></div>
 <p>{r.change===null?'相邻期资料不足':`较${r.previousDate} ${r.change>0?'+':''}${r.change.toFixed(3)}${card.unit==='%'?'个百分点':card.unit==='相关系数'?'':card.unit}`}{r.percentile!==null&&` · 此前${card.percentileWindow}期分位 ${r.percentile.toFixed(1)}%`}</p>
 {lastKnown&&<p className="micro-scope">最近合格读数 {formatMicro(lastKnown.value,card.unit)} · {lastKnown.date}；不代表当前值</p>}
 {context?.reading&&<p><strong>{context.reading}</strong></p>}
 <ChartLegend items={lines.map(l=>({label:l.name,color:l.color,dashed:l.dashed}))}/>
 <ReferenceNote context={context}/>
 <MiniTrend dates={recent.map(p=>p.date)} lines={lines.filter(l=>!l.dashed).map(s=>({...s,values:s.values.slice(-120)}))} references={lines.filter(l=>l.dashed).map(s=>({...s,values:s.values.slice(-120)}))} label={`${card.title}，单位${card.unit}`}/>
 <p>{isDispersion?'宽度与离散度的联合诊断暂不可读。':card.meaning}</p><p className="micro-scope">{card.scope}</p>
 <p className="micro-limit">{card.limitations[0]}</p></>}
 <footer className={isDispersion?'md-card-footer':undefined}><a href={card.sourceUrl} target="_blank" rel="noreferrer">{isDispersion?(card.market==='cn'?'BaoStock':'Yahoo Finance'):card.sourceName}</a><button type="button" onClick={()=>setOpen(true)}>{isDispersion?'展开图表与口径':'看历史与口径 ↗'}</button></footer>
 {open&&<Detail card={card} onClose={()=>setOpen(false)}/>}
 </article>;
}
export default function MicrostructureObservations({market,selectedIds}:{market:'cn'|'us';selectedIds?:readonly string[]}){
 const q=useQuery({queryKey:['microstructureObservationPacketsV1'],queryFn:async({signal})=>Promise.all(BRANCHES.map(async branch=>{try{const r=await fetch(`/research/microstructure-observations-20261108/${branch}.json`,{signal,cache:'no-cache'});if(!r.ok)throw Error('load');return {branch,data:parseMicrostructure(await r.json()),failed:false};}catch{return {branch,data:null as MicroPacket|null,failed:true};}})),staleTime:60000,refetchInterval:60000,refetchOnWindowFocus:true});
 const cards=useMemo(()=>selectedMicro(q.data?.flatMap(p=>p.data?.cards??[])??[],market,selectedIds),[q.data,market,selectedIds]);
 const missing=selectedMicro(q.data?.flatMap(p=>p.data?.unavailable??[])??[],market,selectedIds);
 const [selected,setSelected]=useState('');const card=cards.find(c=>c.id===selected)??cards[0];
 const storageKey=`ws.microstructure.${market}.collapsed`;const [collapsed,setCollapsed]=useState(()=>{try{return localStorage.getItem(storageKey)==='true';}catch{return false;}});
 const toggle=()=>setCollapsed(v=>{try{localStorage.setItem(storageKey,String(!v));}catch{}return !v;});
 if(selectedIds?.length===0)return null;
 if(selectedIds?.length===1){
  if(card)return <Selected key={card.id} card={card} showTitle/>;
  if(missing[0])return <article className="micro-reading"><h3>{missing[0].title}</h3><p>{missing[0].reason}</p><p className="micro-limit">{missing[0].nextRequirement}</p></article>;
  return <p role="status">{q.isPending?'正在读取观察资料…':'该项观察资料暂时不可读。'}{!q.isPending&&<button onClick={()=>void q.refetch()}>重试</button>}</p>;
 }
 return <section className="micro-section" aria-label={`${market==='cn'?'A股':'美股'}交易结构与衍生品`}><header><div><h3>交易结构与衍生品</h3><span>{cards.length}项可读 · {missing.length}项资料待齐</span></div><button onClick={toggle} aria-expanded={!collapsed}>{collapsed?'展开':'收起'}</button></header>
 {!collapsed&&<>{q.isPending&&<p>正在读取观察资料…</p>}{q.data?.some(p=>p.failed)&&<p role="status">部分观察资料暂时不可读。<button onClick={()=>void q.refetch()}>重试</button></p>}
 {card&&<><label className="micro-select">查看指标<select value={card.id} onChange={e=>setSelected(e.target.value)}>{cards.map(c=><option value={c.id} key={c.id}>{c.title}</option>)}</select></label><Selected key={card.id} card={card}/></>}
 {missing.length>0&&<details className="micro-missing"><summary>待补资料 · {missing.length}项</summary>{missing.map(m=><div key={m.id}><b>{m.title}</b><p>{m.reason}</p><p>{m.nextRequirement}</p></div>)}</details>}<p className="micro-scope">按各项资料日期阅读 · 历史快照，未自动按日更新</p></>}
 </section>;
}
