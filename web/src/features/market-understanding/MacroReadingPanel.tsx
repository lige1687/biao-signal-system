import {useEffect,useState} from 'react';

import {useMarketData} from './use-market-data';
import {macroAnswer} from './macro-reading';
import {shanghaiToday,type Market} from './dashboard-model';
import './dashboard.css';
export default function MacroReadingPanel({initialQuestion='当前宏观环境怎么看？',onClose}:{initialQuestion?:string;onClose?:()=>void}){
 const [market,setMarket]=useState<Market>((/美股|美国|纳斯达克|标普/.test(initialQuestion)||(!/中国|A股/.test(initialQuestion)&&new URLSearchParams(window.location.search).get('market')==='us'))?'us':'cn'),[question,setQuestion]=useState(initialQuestion),[submitted,setSubmitted]=useState(initialQuestion),[answer,setAnswer]=useState('');
 const data=useMarketData(market);
 useEffect(()=>{if(!data.pending)setAnswer(macroAnswer(market,data.series,submitted,shanghaiToday(),new Date().toLocaleString('zh-CN',{timeZone:'Asia/Shanghai'})+' 中国时间'));},[submitted,data.pending,market]);
 return <section className="md-macro-panel" aria-label="宏观解读能力"><header><div><h2>宏观解读</h2><p>用系统已有资料回答，参考线、来源和所属期都能回图核查。</p></div>{onClose&&<button onClick={onClose}>收起宏观解读</button>}</header>
 <div className="md-comparison-controls"><label>市场<select value={market} onChange={e=>{setMarket(e.target.value as Market);setAnswer('');}}><option value="cn">A股</option><option value="us">美股</option></select></label>{['当前宏观环境怎么看？','利率变化意味着什么？','通胀参考线怎么看？','两融与风险怎么看？'].map(q=><button key={q} onClick={()=>{setQuestion(q);setAnswer('');}}>{q}</button>)}</div>
 <form onSubmit={e=>{e.preventDefault();setSubmitted(question);setAnswer(macroAnswer(market,data.series,question,shanghaiToday(),new Date().toLocaleString('zh-CN',{timeZone:'Asia/Shanghai'})+' 中国时间'));}}><label htmlFor="macro-question">想了解什么？</label><div className="md-macro-question"><input id="macro-question" value={question} onChange={e=>{setQuestion(e.target.value);setAnswer('');}} placeholder="例如：美国利率和通胀该结合什么看？"/><button type="submit" disabled={data.pending||!question.trim()}>{data.pending?'读取资料中…':'解读已有资料'}</button></div></form>
 {data.failed&&<p role="status">部分资料服务失败，回答会保留缺口。<button onClick={data.retry}>重新读取</button></p>}
 {answer?<div className="md-macro-answer" aria-live="polite">{answer.split('\n').filter(Boolean).map((line,i)=>line.startsWith('### ')?<h3 key={i}>{line.slice(4)}</h3>:<p key={i}>{line.split(/(\[[^\]]+\]\([^\s)]+\))/g).map((part,j)=>{const m=part.match(/^\[([^\]]+)\]\(([^\s)]+)\)$/);return m?<a key={j} href={m[2]}>{m[1]} ↗</a>:part.replace(/\*\*/g,'');})}</p>)}</div>:<p className="md-meta">选择市场并提问后生成资料解读。这里只整理事实与核查条件，不额外调用模型；本期结果不会写入原聊天历史。</p>}
 </section>;
}
