export const marketSections = [
  {id:'index-comparison',label:'指数对照与事件',note:'指数、指标变化、组合与官方事件安排'},
  {id:'overview',label:'数据总览',note:'A股与美股的当前读数、曲线和参考线'},
  {id:'fund-sec-market',label:'市场宽度与情绪',note:'参与上涨的范围、情绪与ETF强弱 · 保留原基本面市场分区'},
  {id:'fund-sec-rates',label:'利率与估值',note:'中美利率、估值、长期位置与相关性'},
  {id:'fund-sec-overlay',label:'长周期叠加',note:'利率、两融与股指放在同一段历史里观察'},
  {id:'fund-sec-macro',label:'中国宏观',note:'中国景气、物价与大宗商品对照'},
  {id:'fund-sec-usmacro',label:'美国宏观',note:'就业、房产、消费、信用与价格'},
] as const;
export type MarketSectionId = typeof marketSections[number]['id'];
export function marketSectionFromHash(hash: string, fallback: MarketSectionId='overview'): MarketSectionId {
  const id=hash.replace(/^#/,'');
  return marketSections.find(s=>s.id===id)?.id ?? fallback;
}
export function legacyFundamentalsTarget(search: string, hash: string): string {
  return `/market-understanding${search}#${marketSectionFromHash(hash,'fund-sec-market')}`;
}
