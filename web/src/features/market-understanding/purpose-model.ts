import type {Metric} from './dashboard-model';
export const purposes={all:'全部观察',trend:'趋势交易',dca:'长期定投',value:'价值观察'} as const;
export type Purpose=keyof typeof purposes;
const priorities:Record<Purpose,string[]>={all:[],trend:['leverage','rates','growth','inflation','valuation'],dca:['valuation','rates','growth','inflation','leverage'],value:['valuation','growth','rates','inflation','leverage']};
export const purposeReading:Record<Purpose,string>={all:'同一份数据，按观察目的调整图表顺序。',trend:'先看波动、信用与融资压力，再与原技术阶段结合；背景资料不改变技术触发。',dca:'先看估值与利率，再核盈利和自身现金安排；历史低位不等于应该加大投入。',value:'先核估值口径，再看历史盈利收益率与经济；指数盈利预期、经营现金流和成分权重仍需补齐。'};
export function orderMetrics(items:Metric[],purpose:Purpose){return [...items].sort((a,b)=>{const rank=(group:string)=>{const i=priorities[purpose].indexOf(group);return i<0?99:i;};return rank(a.group)-rank(b.group);});}
