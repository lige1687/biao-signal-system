import data from './content-data.json'

export type Market = 'cn' | 'us'
export type Method = 'trend' | 'dca' | 'value'
export type TopicId = 'trend' | 'position' | 'leverage' | 'volatility' | 'economy' | 'valuation' | 'etf' | 'method'

export const contentVersion = 'market-understanding-content/2026-10-03'
const pinned = 'https://github.com/lige1687/biao-signal-system/blob/d58a0740502207ca6dfeb9c9f18b1c135aa54632/'
export const reportUrl = `${pinned}docs/experiments/market-understanding-expansion-2026-10-03.md`
export const draftUrl = `${pinned}docs/superpowers/specs/2026-10-03-market-understanding-design.md`

export const topics: { id: TopicId; title: string; question: string; href: string }[] = [
  { id: 'trend', title: '趋势与市场参与', question: '上涨或下跌是否广泛、持续？', href: '/sectors' },
  { id: 'position', title: '调查、仓位与预期', question: '谁说乐观、谁实际持有什么、资料有多旧？', href: '/sentiment' },
  { id: 'leverage', title: '杠杆与交易集中', question: '借款和合约头寸怎样变化？', href: '/fundamentals' },
  { id: 'volatility', title: '波动与保护成本', question: '市场为多大的波动或保护付多少钱？', href: '/fundamentals' },
  { id: 'economy', title: '经济与融资环境', question: '需求、物价、资金价格和信用如何联动？', href: '/fundamentals' },
  { id: 'valuation', title: '估值与经营', question: '价格背后的盈利和现金是否支持假设？', href: '/fundamentals' },
  { id: 'etf', title: 'ETF产品本身', question: '持有这只产品要付什么成本、承担什么额外风险？', href: '/fundamentals' },
  { id: 'method', title: '个人计划与组合', question: '这些信息与我的投入、期限和风险有什么关系？', href: '/portfolio' },
]

export const methods: { id: Method; title: string; goal: string; order: TopicId[] }[] = [
  { id: 'trend', title: '趋势交易', goal: '先看技术阶段、触发和失效，再用市场参与、波动与成本理解背景。', order: ['trend', 'volatility', 'leverage', 'etf', 'position', 'economy', 'valuation', 'method'] },
  { id: 'dca', title: '定投与长期配置', goal: '先核投入计划和产品成本，再看持有资产、估值与经济背景。', order: ['method', 'etf', 'valuation', 'economy', 'trend', 'position', 'leverage', 'volatility'] },
  { id: 'value', title: '价值投资', goal: '先理解经营和估值假设，再看经济背景、持有载体与风险。', order: ['valuation', 'economy', 'etf', 'method', 'trend', 'position', 'leverage', 'volatility'] },
]

// These ten purposes come from the reviewed report. Institutions and teams do not all use the same checklist.
export const roles: { title: string; goal: string; reads: string }[] = data.roles

function market(value: string): Market {
  if (value === 'cn' || value === 'us') return value
  throw new Error(`Unknown market in content: ${value}`)
}

function topic(value: string): TopicId {
  switch (value) {
    case 'trend': case 'position': case 'leverage': case 'volatility':
    case 'economy': case 'valuation': case 'etf': case 'method': return value
    default: throw new Error(`Unknown topic in content: ${value}`)
  }
}

export const catalogue: {
  id: string; title: string; markets: Market[]; topic: TopicId; frequency: string;
  reading: string; coverage: string; sourceUrl: string
}[] = data.catalogue.map(({ id, title, markets, topic: topicId, frequency, reading, coverage, sourceUrl }) => ({
  id, title, markets: markets.map(market), topic: topic(topicId), frequency, reading, coverage, sourceUrl,
}))

export const cards: {
  id: string; title: string; markets: Market[]; topic: TopicId; question: string;
  definition: string; frequency: string; rising: string; falling: string; level: string;
  combine: string[]; counterexample: string; threshold: string; coverage: string;
  limitation: string; sourceIds: string[]
}[] = data.cards.map(({ id, title, markets, topic: topicId, question, definition, frequency,
  rising, falling, level, combine, counterexample, threshold, coverage, limitation, sourceIds }) => ({
  id, title, markets: markets.map(market), topic: topic(topicId), question, definition, frequency,
  rising, falling, level, combine, counterexample, threshold, coverage, limitation, sourceIds,
}))

export const sources: { id: string; title: string; url: string; limitation: string }[] =
  data.sources.map(({ id, title, url, limitation }) => ({ id, title, url, limitation }))
