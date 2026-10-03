import {useEffect,useRef,useState} from 'react';
import {useMarketData} from './use-market-data';
import {macroAnswer,resolveMacroQuestion,type MacroContext} from './macro-reading';
import {shanghaiToday,type Market} from './dashboard-model';
import './dashboard.css';
export default function MacroReadingPanel({initialQuestion='当前宏观环境怎么看？',onClose}:{initialQuestion?:string;onClose?:()=>void}){
 const fallback:Market=new URLSearchParams(window.location.search).get('market')==='us'?'us':'cn';
 const [context,setContext]=useState<MacroContext>(()=>resolveMacroQuestion(initialQuestion,null,fallback));
 const [question,setQuestion]=useState(''),[history,setHistory]=useState<string[]>([initialQuestion]);
 const lastProp=useRef(initialQuestion),current=useRef(context);current.current=context;
 const data=useMarketData(context.market,true);
 function submit(q:string){if(!q.trim())return;setContext(resolveMacroQuestion(q.trim(),current.current,current.current.market));setHistory(h=>[...h.slice(-7),q.trim()]);setQuestion('');}
 useEffect(()=>{if(initialQuestion!==lastProp.current){lastProp.current=initialQuestion;submit(initialQuestion);}},[initialQuestion]);
 const answer=data.pending?'':context.needsContext?'请说明具体指标或参考线，例如“PMI 的50线”或“沪深300市盈率的历史分位线”，才能准确接续。':macroAnswer(context.market,data.series,context.question,shanghaiToday(),new Date().toLocaleString('zh-CN',{timeZone:'Asia/Shanghai'})+' 中国时间',data.indices);
 return <section className="md-macro-panel" aria-label="宏观解读能力"><header><div><h2>宏观解读</h2><p>与市场理解共用现有资料；可接续提问并回图核查。</p></div>{onClose&&<button onClick={onClose}>收起宏观解读</button>}</header>
 <div className="md-comparison-controls"><label>市场<select value={context.market} onChange={e=>setContext({...context,market:e.target.value as Market})}><option value="cn">A股</option><option value="us">美股</option></select></label>{['当前宏观环境怎么看？','利率变化意味着什么？','通胀参考线怎么看？','两融与风险怎么看？'].map(q=><button key={q} onClick={()=>submit(q)}>{q}</button>)}<button onClick={()=>{setContext(resolveMacroQuestion('当前宏观环境怎么看？',null,context.market));setHistory([]);setQuestion('');}}>清空追问上下文</button></div>
 <p className="md-macro-context">正在解读：{context.market==='cn'?'A股':'美股'} · {context.question}。跨市场可问“那美股呢”；指定“这条线”时需说清指标。</p>
 <form onSubmit={e=>{e.preventDefault();submit(question);}}><label htmlFor="macro-question">继续问什么？</label><div className="md-macro-question"><input id="macro-question" value={question} onChange={e=>setQuestion(e.target.value)} placeholder="例如：那A股呢？跟利率结合看呢？"/><button type="submit" disabled={data.pending||!question.trim()}>{data.pending?'读取资料中…':'解读 / 追问'}</button></div></form>
 {data.failed&&<p role="status">部分资料服务失败，回答保留缺口。<button onClick={data.retry}>重新读取</button></p>}
 {history.length>1&&<details className="md-macro-history"><summary>本次追问记录（{history.length}条，仅此面板）</summary><ol>{history.map((q,i)=><li key={i}>{q}</li>)}</ol><p>只保留最近8条问题，不写原聊天历史；回答按当前输入重新整理。</p></details>}
 {answer?<div className="md-macro-answer" aria-live="polite">{answer.split('\n').filter(Boolean).map((line,i)=>line.startsWith('### ')?<h3 key={i}>{line.slice(4)}</h3>:<p key={i}>{line.split(/(\[[^\]]+\]\([^\s)]+\))/g).map((part,j)=>{const m=part.match(/^\[([^\]]+)\]\(([^\s)]+)\)$/);return m?<a key={j} href={m[2]}>{m[1]} ↗</a>:part.replace(/\*\*/g,'');})}</p>)}</div>:<p className="md-meta">正在读取已有资料；不额外调用模型。本面板是可核查的事实整理，不能代替完整投资判断。</p>}
 </section>;
}
