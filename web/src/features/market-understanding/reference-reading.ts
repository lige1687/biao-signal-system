/** Narrative meanings for existing reference values; these never produce a technical signal. */
export type ReferenceTone = 'opportunity' | 'watch' | 'risk' | 'context';
export const referenceColors: Record<ReferenceTone,string> = {
  opportunity:'#128267',watch:'#b56a11',risk:'#c44545',context:'#4778b0',
};
export interface ReferenceReading { tone: ReferenceTone; label: string; explanation: string }
export function referenceReading(key: string, index: number, y: number): ReferenceReading {
  const value=y.toLocaleString('zh-CN');
  const read=(tone:ReferenceTone,label:string,explanation:string):ReferenceReading=>({tone,label,explanation});
  if(key==='pe_cn'||key==='cape_us') {
    return index===0 ? read('opportunity',`机会观察 ≤${value}`,'低于此历史位置：估值偏低，可观察长期机会；先核盈利是否恶化，不等于价格见底。')
      : index===2 ? read('risk',`估值风险 ≥${value}`,'高于此历史位置：估值偏贵，长期回报可能受压；结合利率、盈利，不能据此判短期顶部。')
      : read('context',`历史中位 ${value}`,'这是固定历史中间位置。用于比较贵便宜，不是买卖分界。');
  }
  if(key==='erp_cn'||key==='erp_us') {
    return index===2 ? read('opportunity',`机会观察 ≥${value}`,'股债收益差较高：股票相对债券的盈利收益补偿较大；先核盈利质量和利率变化。')
      : index===0 ? read('risk',`补偿偏低 ≤${value}`,'低于此线：股票相对债券的粗略盈利收益补偿偏低；不等于股票必跌或应立即换债。')
      : read('context',`历史中位 ${value}`,'固定历史中位参考；当前资料窗口不同，不随切换区间重新标定。');
  }
  if(key==='vix') return index===2 ? read('risk',`高波动风险 ≥${value}`,'高于此线：预期波动较高；恐慌也可能带来机会观察，但须看价格止跌、信用与宽度，不能直接抄底。')
    : index===1 ? read('watch',`波动留意 ≥${value}`,'高于此线：关注波动与持仓承受能力，结合指数趋势与信用利差。')
    : read('context',`低波动 ≤${value}`,'低于此线：波动预期较低，不等于未来安全，也不能排除过度乐观。');
  if(key==='margin_rzyezb') return index===0 ? read('context',`杠杆较低 ≤${value}`,'占比较低：融资参与程度较低，结合市场规模；不能单凭低杠杆判机会。')
    : read(index===1?'watch':'risk',`${index===1?'杠杆留意':'杠杆风险'} ≥${value}`,'高于此线：融资拥挤与下跌时的去杠杆压力值得留意；比例也受流通市值变化影响。');
  if(key==='pmi') return read('context',`${value} 扩张 / 收缩`,'高于50：扩张环境支持；低于50：收缩压力。一起看新订单、生产和价格，PMI不是GDP增长率。');
  if(key==='cn_us_spread_10y') return index===0 ? read('context',`中美等值 ${value}`,'高于零：中国10年期收益率较高；低于零：美国较高。必须结合汇率，不能当股市多空分界。')
    : read('watch',`利差观察 ${value}`,'低于此线：中债收益率相对美债更低，关注汇率和资金环境；不是必然资金流出判断。');
  if(key==='cn_10y'||key==='us_10y') return index===0 ? read('opportunity',`低利率观察 ≤${value}`,'利率较低可能减轻融资成本、支持估值；也可能反映增长走弱，机会须结合盈利和需求确认。')
    : read('watch',`利率压力 ≥${value}`,'较高利率可能增加融资成本、压低估值；若由增长改善推动，不能简单判为市场利空。');
  if(key==='hy_oas') return index===0 ? read('opportunity',`信用较松 ≤${value}`,'较窄利差有利于融资环境；同时检查是否低估风险。')
    : read(index===1?'watch':'risk',`${index===1?'信用留意':'信用风险'} ≥${value}`,'利差扩大表示市场要求更高信用补偿；结合企业盈利和违约资料，不直接推断股指走势。');
  if(key==='icwa') return index===0 ? read('opportunity',`就业较强 ≤${value}`,'初请人数较低可能表示就业较稳；结合续请和非农，留意人口与季节变化。')
    : read(index===1?'watch':'risk',`${index===1?'就业留意':'就业压力'} ≥${value}`,'人数高于经验线：关注裁员压力；持续变化比单周越线更重要，不是固定衰退标准。');
  if(key==='ccwa') return read('watch',`再就业压力 ≥${value}`,'续请人数高于经验线：关注再就业变慢；结合初请、非农与劳动人口变化。');
  if(key==='hsales') return index===0 ? read('watch',`销售偏弱 ≤${value}`,'低于经验线：新屋销售需求偏弱的观察点，结合库存和房贷利率。')
    : read('opportunity',`需求支持 ≥${value}`,'高于经验线：销售活动较强；结合库存、房价，折年率不是当月实际套数。');
  if(key==='altsa') return read('context',`消费观察 ${value}`,'高于此线可观察消费支持，低于时关注需求压力；也可能是供应、库存或促销变化。');
  if(['cpi','ppi','ppiaco_yoy','cpiaucsl_yoy'].includes(key)) return y===0 ? read('context',`涨价 / 降价 ${value}`,'低于零：价格同比下降，留意需求偏弱或成本回落；高于零：同比上涨，须分辨需求改善还是供给冲击。')
    : read('watch',`通胀观察 ${value}`,'高于旧页经验参考：留意通胀、增长和利率的组合；不是政策目标，也不是单独风险触发。');
  if(['payems_yoy','wei','cshpi_yoy','dgorder_yoy'].includes(key)) return read('context',`增长 / 下降 ${value}`,'高于零表示该指标正增长，低于零表示下降；结合基数和其他经济资料。增长是否利好股票还取决于估值与利率。');
  return read('context',`参考 ${value}`,'结合该指标定义及其他资料看，不能单独判断机会或风险。');
}
