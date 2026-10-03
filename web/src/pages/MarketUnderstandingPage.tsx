import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { cards, catalogue, contentVersion, methods, reportUrl, roles, sources, topics, type Market, type Method, type TopicId } from "../features/market-understanding/content";
import { decodeObservations, etfReading, expectedMetrics, presentObservation, safeSourceUrl, type EtfProfile, type Observation } from "../features/market-understanding/observation";
import "../features/market-understanding/market-understanding.css";

function Fact({ item }: { item: Observation }) {
  const display = presentObservation(item);
  return <article className="mu-fact">
    <div className="mu-card-head"><h3>{item.label}</h3><span className="mu-state">{display.status}</span></div>
    <strong className="mu-value">{display.value}</strong>
    <p className="mu-change">{display.change}</p>
    {display.fixedNote && <p className="mu-warning">{display.fixedNote}</p>}
    <p>{display.reading}</p><p className="mu-caption">{display.period}</p>
    <details><summary>对象、日期与来源</summary><div className="mu-details-body">
      <p>{item.universe}</p><p>{display.publication}</p><p>系统取得：{item.fetched_at ?? "未记录"}；不能代替来源发布时点。</p>
      {item.quality_reason && <p>{item.quality_reason}</p>}
      <ul>{item.limitations.map((s,i)=><li key={i}>{s}</li>)}</ul>
      <p>{safeSourceUrl(item.source_url) ? <a href={safeSourceUrl(item.source_url)} target="_blank" rel="noreferrer">{item.source_name} ↗</a> : item.source_name} · 定义版本：{item.definition_version}</p>
    </div></details>
  </article>;
}

export default function MarketUnderstandingPage() {
  const [market,setMarket] = useState<Market>("cn");
  const [method,setMethod] = useState<Method>("trend");
  const [topic,setTopic] = useState<TopicId | "all">("all");
  const [search,setSearch] = useState("");
  const [profile,setProfile] = useState<EtfProfile>({exposure:"unknown",currency:"unknown",structure:"unknown"});
  const query = useQuery({queryKey:["market-understanding-observations",market],queryFn:async ({signal})=>{
    const response=await fetch(`/api/fundamentals/observations?market=${market}`,{signal});
    if (!response.ok) throw new Error(response.status === 404 ? "当前环境尚未接通观察接口" : "观察服务暂时不可用");
    return decodeObservations(await response.json(),market);
  },retry:false,staleTime:5*60_000});
  const selectedMethod = methods.find(m=>m.id===method)!;
  const orderedTopics = [...topics].sort((a,b)=>selectedMethod.order.indexOf(a.id)-selectedMethod.order.indexOf(b.id));
  const match=(x:{markets:Market[];topic:TopicId;title:string;question?:string;definition?:string;reading?:string;sourceIds?:string[]})=>{
    const queryText=search.trim().toLowerCase();
    const searchable=[x.title,x.question,x.definition,x.reading,...(x.sourceIds ?? [])].filter(Boolean).join(" ").toLowerCase();
    const textMatches=searchable.includes(queryText) || (queryText === "两融" && /融资|融券/.test(searchable));
    return x.markets.includes(market) && (topic === "all" || x.topic === topic) && textMatches;
  };
  const visibleCatalogue=catalogue.filter(match).sort((a,b)=>selectedMethod.order.indexOf(a.topic)-selectedMethod.order.indexOf(b.topic));
  const visibleCards=cards.filter(match).sort((a,b)=>selectedMethod.order.indexOf(a.topic)-selectedMethod.order.indexOf(b.topic));
  const observed = query.data?.items ?? [];
  const missing=Object.entries(expectedMetrics[market]).filter(([id])=>!observed.some(x=>x.metric_id===id));
  const counts = observed.filter(x=>presentObservation(x).hasValue).length;
  const selectedTopic=topics.find(t=>t.id===topic);
  const setProfileField = <K extends keyof EtfProfile>(key: K, value: EtfProfile[K])=>setProfile(p=>({...p,[key]:value}));
  return <main className="mu-page">
    <header className="mu-hero">
      <div><p className="mu-eyebrow">看市场，也读懂变化</p><h1>市场理解</h1><p className="mu-lead">先问这项信息在回答什么，再看变化、配套证据和另一种解释。</p></div>
      <a className="mu-evidence-link" href={reportUrl} target="_blank" rel="noreferrer">研究依据 ↗</a>
    </header>
    <nav className="mu-jump" aria-label="市场理解页内导航"><a href="#mu-now">已有读数</a><a href="#mu-map">观察地图</a><a href="#mu-reading">指标读法</a><a href="#mu-etf">联系ETF</a></nav>
    <section className="mu-controls" aria-label="阅读范围">
      <fieldset><legend>观察市场</legend><div className="mu-segments">{([['cn','A股'],['us','美股']] as const).map(([id,title])=><button key={id} type="button" aria-pressed={market===id} onClick={()=>setMarket(id)}>{title}</button>)}</div></fieldset>
      <fieldset><legend>我的阅读目的</legend><div className="mu-segments">{methods.map(m=><button key={m.id} type="button" aria-pressed={method===m.id} onClick={()=>setMethod(m.id)}>{m.title}</button>)}</div></fieldset>
      <p className="mu-method" aria-live="polite">{selectedMethod.goal}<span>切换方法只调整阅读顺序，不改变读数或交易规则。</span></p>
    </section>
    <section id="mu-now" className="mu-section" aria-labelledby="mu-now-title">
      <div className="mu-section-head"><div><p className="mu-eyebrow">01 / 先看事实</p><h2 id="mu-now-title">{market==='cn'?'A股':'美股'} · 目前能读到什么</h2></div><button className="mu-button" type="button" disabled={query.isFetching} onClick={()=>void query.refetch()}>{query.isFetching?'读取中…':'重新读取'}</button></div>
      <p className="mu-caption">读数按各自资料所属期展示；这不是“今日行情已齐全”的声明。所有内容用于理解市场。</p>
      <div aria-live="polite" aria-busy={query.isFetching}>
        {query.isPending ? <p className="mu-notice">正在读取观察资料；下方解释内容可先阅读。</p> : query.isError ? <div className="mu-notice" role="status"><strong>{query.error.message}。</strong><p>本页保留指标读法；没有数据不代表市场平静，也不会填入示例行情。</p><Link to="/fundamentals">查看原基本面页 →</Link></div> : <>
          <p className="mu-caption">可显示读数 {counts} 项；接口返回 {observed.length} 项。页面整理时间：{query.data.generatedAt ?? '未记录'}，不是数据公布时间。</p>
          {query.data.notices.map((n,i)=><p key={i} className="mu-warning">{n}</p>)}
          <div className="mu-fact-grid">{observed.map(x=><Fact item={x} key={x.metric_id}/>)}</div>
          {missing.length>0 && <p className="mu-notice">本次尚未返回：{missing.map(([,s])=>s.label).join('、')}。不推断其数值或方向。</p>}
        </>}
      </div>
      <div className="mu-event"><strong>事件观察：日历尚未接入本页</strong><p>关注数据发布、利率决定、财报、政策、指数调整与产品事项。先核官方时间、所属期、前值是否修订；没有可比预期，就不判断“超预期”。</p><Link to="/news">到资讯流核对事件 →</Link></div>
    </section>
    <section id="mu-map" className="mu-section" aria-labelledby="mu-map-title">
      <div className="mu-section-head"><div><p className="mu-eyebrow">02 / 带着问题读</p><h2 id="mu-map-title">专业投资者的观察地图</h2></div><span className="mu-caption">50组目录 · 8个主题</span></div>
      <p>机构和个人的目标不同，没有一份人人每天必看的清单。先选问题，再决定需要哪些资料。</p>
      <details className="mu-role-details"><summary>谁在看，想解决什么问题？</summary><div className="mu-role-grid">{roles.map(r=><article key={r.title}><h3>{r.title}</h3><p>{r.goal}</p><p className="mu-caption">常看：{r.reads}</p></article>)}</div></details>
      <div className="mu-topic-grid">{orderedTopics.map(t=><button type="button" key={t.id} aria-pressed={topic===t.id} onClick={()=>setTopic(topic===t.id?'all':t.id)}><strong>{t.title}</strong><span>{t.question}</span></button>)}</div>
      <div className="mu-search-row"><label>找指标<input type="search" value={search} onChange={e=>setSearch(e.target.value)} placeholder="例如：两融、估值、跟踪" /></label><button type="button" className="mu-button" onClick={()=>{setTopic('all');setSearch('');}}>全部主题</button><p className="mu-caption" aria-live="polite">{selectedTopic?.title ?? '全部主题'} · 当前市场匹配 {visibleCatalogue.length} 组</p></div>
      <p className="mu-caption">覆盖说明来自2026-10-03的研究盘点，表示系统的已知能力；不代表此刻已经取得行情。中美适用范围已分别筛选。</p>
      {visibleCatalogue.length===0 ? <p className="mu-notice">这个市场和搜索条件下没有匹配项，可清空搜索或选择全部主题。</p> : <div className="mu-catalogue">{visibleCatalogue.map(x=><details key={x.id}><summary><span className="mu-number">{x.id}</span><strong>{x.title}</strong><span className="mu-catalogue-frequency">{x.frequency}</span></summary><div className="mu-details-body"><p>{x.reading}</p><p><b>系统盘点：</b>{x.coverage}</p><div className="mu-inline-links"><Link to={topics.find(t=>t.id===x.topic)?.href ?? '/fundamentals'}>查看相关模块 →</Link><a href={x.sourceUrl} target="_blank" rel="noreferrer">原目录与限制 ↗</a></div></div></details>)}</div>}
    </section>
    <section id="mu-reading" className="mu-section" aria-labelledby="mu-reading-title">
      <div className="mu-section-head"><div><p className="mu-eyebrow">03 / 多读一层</p><h2 id="mu-reading-title">指标升降，分别意味着什么</h2></div><span className="mu-caption">首批12项详细读法</span></div>
      <p>“现在很高”与“最近在上升”是两件事。下面沿用相同市场、主题和搜索条件；卡片解释概念，未接通的指标不展示假读数。</p>
      {visibleCards.length===0 && <p className="mu-notice">此筛选下尚无详细卡；上方目录保留现有读法及原模块入口。</p>}
      <div className="mu-reading-grid">{visibleCards.map(c=><article className="mu-reading-card" key={c.id}><p className="mu-eyebrow">{topics.find(t=>t.id===c.topic)?.title} · 指标说明</p><h3>{c.title}</h3><p className="mu-card-question">{c.question}</p><p className="mu-caption">{c.id==='M01'?'已有观察接口；实际读数和日期见上方。':'本页未加载此项真实读数。'}</p><details><summary>展开读法与容易误判的地方</summary><div className="mu-details-body"><dl><dt>{c.id==='M12'?'事件与预期':'位置高低'}</dt><dd>{c.level}</dd><dt>{c.id==='M12'?'事件方向':'数值上升'}</dt><dd>{c.rising}</dd><dt>{c.id==='M12'?'相反情形':'数值下降'}</dt><dd>{c.falling}</dd><dt>一起检查</dt><dd><ul>{c.combine.map(x=><li key={x}>{x}</li>)}</ul></dd><dt>另一种解释</dt><dd>{c.counterexample}</dd><dt>阈值怎么用</dt><dd>{c.threshold}</dd></dl><details className="mu-source-details"><summary>定义、频率和证据</summary><dl><dt>定义与单位</dt><dd>{c.definition}</dd><dt>频率与可用时间</dt><dd>{c.frequency}</dd><dt>系统盘点</dt><dd>{c.coverage}</dd><dt>资料限制</dt><dd>{c.limitation}</dd></dl><ul>{c.sourceIds.map(id=>{const s=sources.find(x=>x.id===id);return <li key={id}>{s ? <><a href={s.url} target="_blank" rel="noreferrer">{s.title} ↗</a><p className="mu-caption">{s.limitation}</p></> : `来源${id}尚待定位`}</li>;})}</ul></details></div></details></article>)}</div>
    </section>
    <section id="mu-etf" className="mu-section" aria-labelledby="mu-etf-title">
      <div className="mu-section-head"><div><p className="mu-eyebrow">04 / 联系自己的产品</p><h2 id="mu-etf-title">与我关注的ETF有什么关系</h2></div></div>
      <p>先按基金文件确认下面三项。本页只按你明确选择的范围解释，不根据基金名称猜测，也不读取持仓金额；这不是具体基金的自动核验。</p>
      <div className="mu-profile">
        <label>标的资产范围<select value={profile.exposure} onChange={e=>setProfileField('exposure',e.target.value as EtfProfile['exposure'])}><option value="unknown">尚未确认 / 其他资产</option><option value="cn">A股股票</option><option value="us">美国股票</option></select></label>
        <label>交易计价币种<select value={profile.currency} onChange={e=>setProfileField('currency',e.target.value as EtfProfile['currency'])}><option value="unknown">尚未确认 / 其他币种</option><option value="cny">人民币</option><option value="usd">美元</option></select></label>
        <label>产品结构<select value={profile.structure} onChange={e=>setProfileField('structure',e.target.value as EtfProfile['structure'])}><option value="unknown">尚未确认</option><option value="ordinary">普通ETF</option><option value="leveraged">杠杆或反向ETF</option></select></label>
      </div>
      <ul className="mu-etf-reading" aria-live="polite">{etfReading(profile).map(x=><li key={x}>{x}</li>)}</ul>
      <p className="mu-caption">这三个选择独立于上方观察市场。具体指数、成分、费用版本、币种对冲和净值时点仍需核实；这里只提供检查顺序。</p><Link to="/portfolio">回到我的持仓核对产品 →</Link>
    </section>
    <footer className="mu-footer">内容版本 {contentVersion} · 解释与观察层，不参与LEI触发、失效或退出判定。使用效果和投资收益尚未测量。<a href={reportUrl} target="_blank" rel="noreferrer">来源、反例与未解决问题 ↗</a></footer>
  </main>;
}
