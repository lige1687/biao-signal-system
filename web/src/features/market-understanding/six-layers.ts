import additions from './fundamentals-reading.json'
import { cards, catalogue, sources, type Market, type Method } from './content'

export type LayerId = 'macro' | 'industry' | 'business' | 'flows' | 'etf' | 'events'
export type LayerSelection = LayerId | 'all'
type MarketText = Record<Market, string>
export type Layer = {
  id: LayerId; title: string; question: string; cadence: string; focus: MarketText;
  combine: string[]; gap: string; links: { title: string; href: string; scope: string; markets: Market[] }[]
}
export const layers: Layer[] = [
  { id:'macro', title:'宏观', question:'经济、物价和资金价格，正在怎样变化？', cadence:'利率看交易日；经济数据按月或季度，先核所属期与修订。',
    focus:{cn:'A股先连着看：PMI与订单 → 物价和企业成本 → 信贷结构与资金价格。',us:'美股先连着看：就业和消费 → 核心物价 → 政策与市场利率、信用条件。'},
    combine:['增长：订单与就业、消费能否相互印证？一次回升能否持续？','物价：上涨来自需求改善还是供给、能源冲击？不同成分是否同向？','融资：利率下降时，信用风险和融资可得性有没有一起改善？'],
    gap:'已有利率和宏观图表；社融结构、修订历史及可比预期仍不完整。本页没有新增这些实时数据。',
    links:[{title:'利率与估值图表',href:'/fundamentals#fund-sec-rates',scope:'原页含中美不同系列，逐图看国家与单位。',markets:['cn','us']},{title:'经济与物价图表',href:'/fundamentals#fund-sec-macro',scope:'中国PMI/CPI/PPI及商品比值；不代表每项都为国内数据。',markets:['cn']},{title:'美国宏观专题',href:'/fundamentals#fund-sec-usmacro',scope:'美国就业、消费、住房及订单；不是A股国内读数。',markets:['us']}] },
  { id:'industry', title:'行业', question:'行业的需求、供给和利润，谁先发生变化？', cadence:'行业经营按月或季度；价格与相对强弱按各自交易日。',
    focus:{cn:'A股行业ETF：先核指数成分，再看相关订单、销量、库存与价格。',us:'美股行业ETF：先核行业与地区构成，再看终端需求、定价和成本。'},
    combine:['需求：销量与订单一起读，提价带来的收入增长不等于卖得更多。','供给：库存、产能与资本开支一起读；扩产也可能带来未来竞争。','利润与价格：经营改善是否传到利润和现金？行业股价是否已先反映？'],
    gap:'已有行业价格强弱与市场参与情况；行业订单、库存、产能和汇总利润没有在本页接通。',
    links:[{title:'行业趋势与相对强弱',href:'/sectors',scope:'A股重点与自选板块，ETF联系仅部分映射；不能代替经营数据。',markets:['cn']},{title:'美股行业ETF相对强弱',href:'/fundamentals#fund-sec-market',scope:'美国11行业ETF相对SPY的既有图表；并非全部行业。',markets:['us']},{title:'订单与经济背景',href:'/fundamentals#fund-sec-macro',scope:'中国总体经济资料；不是每个行业的专属订单。',markets:['cn']},{title:'美国订单与消费',href:'/fundamentals#fund-sec-usmacro',scope:'美国总体背景；不是每个行业的专属订单。',markets:['us']}] },
  { id:'business', title:'企业经营与估值', question:'赚的钱、收到的钱，能否支持现在的价格？', cadence:'财报随季度、半年或年度披露；估值价格与盈利日期分别标识。',
    focus:{cn:'宽基ETF先看指数整体盈利、行业权重与估值口径，再看主要成分的经营变化。',us:'美股ETF同时看指数盈利、龙头集中度、每股盈利与预期；不要拿单家龙头代替全指数。'},
    combine:['经营：收入增长来自销量、价格还是并表？利润率有没有持续改善？','现金：利润是否收到现金？投入、债务到期、分红和回购是否可持续？','价格：估值上升来自股价上涨还是盈利下降？市场期待的增长是否有依据？'],
    gap:'原基本面有部分PE/CAPE和利率对照；指数收入、利润、现金流及带历史版本的盈利预期尚未接通。读法补齐不代表数据齐全。',
    links:[{title:'已有估值与利率对照',href:'/fundamentals#fund-sec-rates',scope:'部分中美指标；不是完整企业财务分析或公允价值结论。',markets:['cn','us']}] },
  { id:'flows', title:'资金与杠杆', question:'谁在参与，借了多少，市场承受多大波动？', cadence:'成交与两融通常按交易日；调查、分类持仓按周；FINRA按月。',
    focus:{cn:'A股重点分开看两融、成交参与、期权与调查；两融不能代表全市场杠杆。',us:'美股分开看FINRA证券借款、调查仓位、期货分类持仓与波动；对象和日期不可混用。'},
    combine:['参与：指数走势与上涨家数、行业范围是否一致？少数大公司能推动指数。','杠杆：余额变化结合成交、可比市值与价格；余额高不自动意味着即将下跌。','风险：波动与保护成本一起看，调查情绪、实际仓位与期货合约分别理解。'],
    gap:'部分观察读数可用性见下方；FINRA、CFTC等真实数据尚未接通，现有调查不覆盖全部投资者。',
    links:[{title:'市场观察图表',href:'/fundamentals#fund-sec-market',scope:'原页含历史和不同市场指标，逐项核日期。',markets:['cn','us']},{title:'利率、两融与股指叠加',href:'/fundamentals#fund-sec-overlay',scope:'进入后仍需选择对应市场与图组；默认A股×利率，叠加不证明因果。',markets:['cn','us']},{title:'情绪资料与已有研究',href:'/sentiment',scope:'调查、仓位、交易行为是不同信息。',markets:['cn','us']}] },
  { id:'etf', title:'ETF产品', question:'指数判断之外，这只产品还带来什么成本和风险？', cadence:'交易成本随时段变动；持仓、费用与产品条款按文件更新。',
    focus:{cn:'先核国内资产或跨境资产、折溢价、申购限制与费用；不能只按上市地点分类。',us:'先核指数范围、行业集中、费用和跟踪，再确认币种及杠杆结构。'},
    combine:['交易：价格和净值是否同一时点？价差与可成交数量是否足够？','持有：费用、跟踪差异、分红与税费如何共同影响结果？','组合：成分重叠、币种、集中度与投入计划是否清楚？产品便宜不等于风险小。'],
    gap:'本页提供产品核对顺序和详细读法；未自动读取具体ETF文件、持仓或净值。',
    links:[{title:'在本页核对ETF范围',href:'#mu-etf',scope:'按明确选择解释，未知保持未知。',markets:['cn','us']},{title:'查看持仓与投入计划',href:'/portfolio',scope:'核对自己的记录；本页不会调整计划或金额。',markets:['cn','us']}] },
  { id:'events', title:'事件', question:'什么时候知道了什么，和原先的预期差多少？', cadence:'按官方事件时间；公告时间与生效时间分开，发布后核前值修订。',
    focus:{cn:'关注统计发布、政策与利率决定、财报、指数调整、分红及ETF产品公告。',us:'关注经济发布、FOMC、财报与指引、指数调整和ETF产品事项。'},
    combine:['事前：核官方日程、所属期、预期来源与版本，没有可比预期不判断超预期。','事后：把实际值、前值修订和指引分开，确认消息是否早已公开。','市场反应：利率、汇率、行业与价格如何响应？好消息也可能早已反映在价格里。'],
    gap:'事件读法已有；官方日历、可比预期与提醒尚未接入。本页不生成临时行情结论。',
    links:[{title:'到资讯流核对公告',href:'/news',scope:'资讯流不等于完整官方事件日历。',markets:['cn','us']}] },
]
export const layerOrder: Record<Method, LayerId[]> = {
  trend:['flows','industry','macro','etf','events','business'],
  dca:['etf','business','macro','industry','flows','events'],
  value:['business','industry','macro','etf','events','flows'],
}
export function catalogueLayers(id: string): LayerId[] {
  const n=Number(id)
  if (n===4) return ['industry','flows']
  if (n>=2 && n<=25) return ['flows']
  if (n===31 || n===35) return ['macro','industry']
  if (n>=26 && n<=35) return ['macro']
  if (n===37 || n===40) return ['business','industry']
  if (n>=36 && n<=42) return ['business']
  if (n>=43 && n<=47) return ['etf']
  return []
}
type ReadingCard = (typeof cards)[number] & { layer: LayerId }
const oldCardLayer=(id:string):LayerId=>id==='M12'?'events':Number(id.slice(1))<=4?'flows':'etf'
function checkedLayer(value:string):LayerId {
  if (layers.some(x=>x.id===value)) return value as LayerId
  throw new Error(`Unknown reading layer: ${value}`)
}
function checkedTopic(value:string):'economy'|'valuation' {
  if(value==='economy'||value==='valuation') return value
  throw new Error(`Unknown reading topic: ${value}`)
}
export const readingCards: ReadingCard[] = [
  ...cards.map(c=>({...c,layer:oldCardLayer(c.id)})),
  ...additions.cards.map(c=>({...c,markets:c.markets.map(m=>{
    if(m==='cn'||m==='us') return m
    throw new Error(`Unknown reading market: ${m}`)
  }),topic:checkedTopic(c.topic),layer:checkedLayer(c.layer)})),
]
export const readingSources = [...sources,...additions.sources]
function matchesText(query:string, values:(string|undefined)[]) {
  const q=query.trim().toLowerCase()
  const text=values.filter(Boolean).join(' ').toLowerCase()
  return text.includes(q) || (q==='两融' && /融资|融券/.test(text))
}
function catalogueRank(id:string,method:Method) {
  return Math.min(layerOrder[method].length,...catalogueLayers(id).map(x=>layerOrder[method].indexOf(x)))
}
export function filterCatalogue(market:Market, layer:LayerSelection, search:string, method:Method) {
  return catalogue.filter(c=>c.markets.includes(market) && (layer==='all'||catalogueLayers(c.id).includes(layer)) && matchesText(search,[c.title,c.reading]))
    .sort((a,b)=>catalogueRank(a.id,method)-catalogueRank(b.id,method))
}
export function filterCards(market:Market, layer:LayerSelection, search:string, method:Method) {
  return readingCards.filter(c=>c.markets.includes(market) && (layer==='all'||c.layer===layer) && matchesText(search,[c.title,c.question,c.definition,...c.sourceIds]))
    .sort((a,b)=>layerOrder[method].indexOf(a.layer)-layerOrder[method].indexOf(b.layer))
}

export function catalogueHref(id:string, market:Market):string {
  if (Number(id)>=48) return '/portfolio'
  if (id==='01') return '/'
  if (id==='13') return '/fundamentals#fund-sec-overlay'
  if (id==='04') return market==='cn'?'/sectors':'/fundamentals#fund-sec-market'
  const layer=catalogueLayers(id)[0]
  if (Number(id)>=26 && Number(id)<=30) return '/fundamentals#fund-sec-rates'
  if (layer==='macro') return market==='us'?'/fundamentals#fund-sec-usmacro':'/fundamentals#fund-sec-macro'
  if (layer==='business') return '/fundamentals#fund-sec-rates'
  if (layer==='etf') return Number(id)>=48?'/portfolio':'#mu-etf'
  return '/fundamentals#fund-sec-market'
}
