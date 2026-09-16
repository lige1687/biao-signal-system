from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[5];P=Path(__file__).resolve().parent
r=json.loads((P/'results.json').read_text());annual=json.loads((P/'annual.json').read_text())
profiles=r['profiles'];names={'sh510300':'沪深300ETF','sz159915':'创业板ETF'}
def method(m):return 'H1 全进全出＋缓冲' if m.startswith('H1') else 'H2 保留趋势参与'
def p(v):return f'{v*100:.2f}%'
lines=['# 宽基ETF增量回测：减少操作，还是减少错过上涨','日期：2026-09-08。区间2015-01-01—2026-06-30；两只国内宽基ETF；本批8个新增完整账户，另引用已核12个参照。','## 一句话结论（大白话）','这批测试能否在现有宽度方法上增加实际价值。把三档改为带缓冲的全进全出，交易次数从98次减到49次，最后赚的钱基本相近，是值得继续核的操作简化候选；让ETF趋势较强时继续投入，创业板多赚了，但账户最深跌幅从37.34%加大到53.48%，沪深300还少赚了。两项都没有在两产品、两费用下同时做到“赚得不少、跌得不深”，当前依据支持保留原方法、继续验证简化候选，不支持统一替换正式规则。','## 这次回答哪些实际决定','**决定一：要不要把原三档换成全进全出？** H1是已有待采用候选的周度适配，价值首先在少操作。它没有解决错过上涨的问题，2025年两只账户都是全年现金、收益为零。\n\n**决定二：原宽度叫人少投，但ETF还在涨，要不要继续参与？** H2确实在2025年参与了更多上涨，但历史大跌和长期落后也更明显。多赚的创业板账户曾从最高值跌掉超过一半，不能把这叫免费增量。','## 两种增量是什么','“宽度”指一组A股中，收盘站在200日均线上方的股票占多少。原三档在宽度低于43.3%时投满、43.3%至56.7%以下投一半、56.7%及以上持现金，每个完整周结束后在下一周可成交开盘调整。\n\n**H1 全进全出＋缓冲：** 宽度降到约43.333333%或以下才投满，回升到约45.333333%以上才全退，中间保持原状态。精确计算采用乘3与130/136比较，不截断成43.33/45.33。它取消中档，也改变状态保持方式，是完整安排的比较；不能把差额全部归给缓冲。旧原版每日观察，本批按周观察，且不重新挑参数，不能继承旧每日或定期重选版本的成绩。\n\n**H2 保留趋势参与：** ETF收盘突破此前60个有效日线最高收盘后，趋势状态变为参与；跌破此前60个最低收盘才结束。每个完整周以“原宽度比例”和“趋势参与比例”取较大的投入比例，仍不超过100%。它属于独立资金安排扩展，不改LEI的道路、路牌或A/B/C/D，不将市场环境用作技术信号硬过滤。','## 同样10万元，最后留下多少、最深跌过多少','每账户初始10万元，不追加，不借款，闲钱无利息；主费用为买卖单边各0.1%，按100份整数和名义开盘成交，分红与不能成交均计入。**最深跌幅指账户从此前最高值到后来最低值的下降，不是相对最初10万元的亏损。**期末仍持有按收盘估值，没有虚构一次卖出。','| 产品 | 方法 | 期末总财富 | 比原三档多/少 | 最深跌幅 | 买卖总次数 | 累计费用 |','|---|---|---:|---:|---:|---:|---:|']
old=ROOT/'docs/experiments/raw/research-broad-etf-cash-2026-09-08/first12/account-results'
for sym in names:
 for met in ['hold','breadth_three_tier']:
  s=json.loads((old/f'{sym}-{met}-fee0.001/summary.json').read_text())
  label='持续持有参照' if met=='hold' else '原周度三档'
  lines.append(f"| {names[sym]} | {label} | {s['final_equity']:,.2f}元 | — | {p(s['max_drawdown'])} | {s['buys']+s['sells']} | {s['fees']:,.2f}元 |")
 for s in profiles:
  if s['symbol']==sym and s['fee_per_side']==.001:
   lines.append(f"| {names[sym]} | {method(s['method'])} | {s['final_equity']:,.2f}元 | {s['extra_wealth']:+,.2f}元 | {p(s['max_drawdown'])} | {s['buys']+s['sells']} | {s['fees']:,.2f}元 |")
lines += ['H1在沪深300只多94.85元、创业板少1,367.54元，全期金额差异很小，不能称作收益显著提升。交易次数虽然减半，费用并没有减半，因为每次交易金额与账户财富也影响费用。H2在创业板多52,821.60元，同时最深下跌加深16.15个百分点；沪深300少7,394.05元且最深下跌加深6.22个百分点。','## 把费用加倍，结论是否翻转','| 产品 | 增量 | 单边0.2%期末财富 | 比同费率原三档多/少 | 最深跌幅 |','|---|---|---:|---:|---:|']
for s in profiles:
 if s['fee_per_side']==.002:lines.append(f"| {names[s['symbol']]} | {method(s['method'])} | {s['final_equity']:,.2f}元 | {s['extra_wealth']:+,.2f}元 | {p(s['max_drawdown'])} |")
lines += ['加倍费用后，H1仍是沪深300略多、创业板略少；H2仍是沪深300少赚且跌更深、创业板多赚但跌更深。不存在靠忽略另一档费用才成立的统一胜出。研究费用包含简化成本情景，不代表已经核实用户实际渠道的收费与滑点。','## 全部年份：2025的改善不能盖过其他年份','主费用0.1%。2026仅上半年；各行按实际连续账户计算，并非每年重新投入10万元。','| 年份 | 沪深300 原三档 | 沪深300 H1 | 沪深300 H2 | 创业板 原三档 | 创业板 H1 | 创业板 H2 |','|---|---:|---:|---:|---:|---:|---:|']
for y in sorted({v['year'] for v in annual}):
 vals=[]
 for sym in names:
  h1=next(v for v in annual if v['year']==y and v['account_id']==f'{sym}-H1_weekly_binary_hysteresis-fee0.001')
  h2=next(v for v in annual if v['year']==y and v['account_id']==f'{sym}-H2_weekly_breadth_trend_participation-fee0.001')
  vals += [p(h1['baseline_return']),p(h1['new_return']),p(h2['new_return'])]
 lines.append('| '+('2026上半年' if y=='2026' else y)+' | '+' | '.join(vals)+' |')
lines += ['2025年创业板原三档只涨2.11%，H2涨44.77%，确实补上部分错过的上涨；但2022年H2跌14.82%，原三档跌7.70%。H1在2025年两产品都没有参与，不能把简化操作等同于减少踏空。完整持有与加倍费用各年见机器表。','## 多赚是否只是因为投得更多','| 产品 | 原三档平均投入 | H1平均投入 | H2平均投入 | H2提高目标的完整周数 |','|---|---:|---:|---:|---:|']
for sym,count in [('sh510300',195),('sz159915',196)]:
 a=next(s for s in profiles if s['symbol']==sym and s['method'].startswith('H1') and s['fee_per_side']==.001)
 b=next(s for s in profiles if s['symbol']==sym and s['method'].startswith('H2') and s['fee_per_side']==.001)
 lines.append(f"| {names[sym]} | {p(a['baseline_mean_invested_fraction'])} | {p(a['mean_invested_fraction'])} | {p(b['mean_invested_fraction'])} | {count}/588 |")
lines += ['平均投入按每日历日的ETF市值占总财富比例取平均。H2从约59%提高到约87%—88%，多赚可能与承担更多市场涨跌直接有关。这里没有同时固定风险的实验，所以不能宣称趋势信号更准或同样风险下多赚。\n\n创业板H2最深下跌从2015-06-03的账户高点延续到2018-10-18低点，直到2020-07-07才重新达到原高点，等了1,861天。沪深300H2在2021年高点后经历最深37.16%的下降，到2026-06-30仍未回到那个高点。这些等待与下跌才是实际使用者要承受的代价。','## 换一段持有时间，优势能否保留','把已运行的连续账户按每月开始的36个月窗口标准化比较，共103个窗口。窗口大量重叠，未重新买入，也不是103次独立试验；领先占比不能叫未来胜率。','| 产品 | 方法 | 领先原三档的窗口 | 落后窗口 | 最差窗口收益差 | 最差窗口 |','|---|---|---:|---:|---:|---|']
for v in r['rolling_summary']:
 if not v['account_id'].endswith('0.001'):continue
 s=next(s for s in profiles if s['account_id']==v['account_id']);w=v['worst']
 lines.append(f"| {names[s['symbol']]} | {method(s['method'])} | {v['windows_ahead']}/103 | {v['windows_behind']}/103 | {w['difference_pp']:+.2f}个百分点 | {w['start']}—{w['end']} |")
lines += ['创业板H2全期多赚，但在103个三年窗口里有89个落后；较近阶段的强上涨不能代表任意开始日期都适合它。H1也可能连续多年落后，不能承诺“交易更少而表现总一样”。预先固定的2015—2019与2020—2026上半年两段、全部费用及完整窗口见 `decision-analysis/results.json` 和 `rolling-36-months.json`，没有只保留有利窗口。','## 目前可以据此做什么决定','1. **原三档继续作为研究和实际讨论的基准。** 本批没有证据支持统一换成某个新方案。\n2. **H1保留为“减少操作”的候选。** 两只ETF的交易次数都减半、全期财富接近，值得扩大合格产品验证；但2025完全空仓、长期落后阶段和旧参数筛选的局限都要保留。\n3. **H2这一版暂不作为通用升级。** 它在创业板体现了多赚与多承受下跌的交换，在沪深300则没有改善；不能仅因补上2025就默认采用。它的失败不等于所有再次参与方法都无效。\n4. **下一批先补产品资料，再继续已安排的比较。** 510050、510500仍缺合格名义价格与公司行动解释；其中510500还有两处旧价格断裂未闭合。六宽基、四行业、持续收入、LEI技术账户和共享资金组合仍在总计划中，不能把本批说成已全测完。','## 论文里具体借了什么','本轮定向核对两项近期原文：Jeon与Masturzo 2025机构研究把退出、再次进入和成本放在同一套安排中；本地据此比较完整现金去向与风险收益取舍。[机构原文](https://media.researchaffiliates.com/1099_stop_the_losses_e389db6127.pdf)\n\nSepp与Lucic 2026预印本用于提醒我们区分方向、资金参与和成本；本轮不复现作者合约组合、做空或风险缩放。[预印本](https://arxiv.org/abs/2607.19497)\n\n具体宽度界线、60日、周度执行和取较大目标都是本地来源或研究设计，论文没有替这些数值背书。H1已在旧历史中筛选过，H2又针对已知2025短板提出，这段历史属于回顾性筛查，不能重新命名为未知行情验证。沿用Sullivan/Cederburg的完整比较思想，保留所有试法、费用和失败时期，没有宣称复现其全部统计检验。\n\n三条可学习的方法按既有文献编号放在[学习补充](../literature-learning/broad-etf-increment-lessons-2026-09-08.md)及同名JSON，供页面增量接入；未重复创建Zotero文献，未增加“全文精读”记录。','## 实现、复核与证据边界','独立复核已完成：从原始宽度、名义行情、行动和限制重新生成信号及资金，没有导入执行器或价格辅助函数来证明自己。8个账户共33,592条日账、402笔成交、1,104个月度记录、96个年度记录及390段从新高下跌到恢复/未恢复的过程均核对；每账户588个完整周信号一致。根负责人另从日账复核费用、期末财富、最深下跌、所有年份和103个三年窗口。静态代码审阅通过，7个边界测试与三条旧代表账户回归通过。\n\n复核保留两项记录差异：H1把signal_date用于宽度来源日，周末决策日需由下周一资格日前一天推导；H2直接分列两日期。四个创业板账户的2021-02-08停牌被原拒绝记录写为缺行情；该日均没有成交，资金完全一致。逐行资格说明及文件指纹见 execution/record-qualification.json，原主跑结果保留不改，不称原字段逐字全部相同。\n\n收益前修过一处起始周文字歧义及浮点测试例；初稿、正式v1/v1.1和准备证据保留。独立复核也保留了首次引用旧锁文件名、第二次发现拒绝原因分类差异的失败尝试，没有改交易规则去追求数字一致。主运行只跑固定8账户，16项输入指纹结束时不变。月末60日备选未计算收益。','资料为有条件研究资格：只应用已记录公司行动，未证明全历史公告连续无遗漏；宽度历史股票池/版本没有完整绑定；日线不能精确表示所有涨跌停、盘中可成交性和实际成本。两只ETF共用同一A股宽度，不是两次完全独立成功。当前结论没有升级为正式规则或真实交易指令。','## 复现入口与交付范围','- 冻结协议：`raw/research-broad-etf-multimethod-2026-09-08/protocol.md`（v1.1）。\n- 运行结果：同目录 `execution/account-results/summary.json`；每账户有日账、逐笔、信号、未成交、年月、跌幅恢复及期末持仓。\n- 独立复核：同目录 `independent-review/`；静态代码审阅：`code-review/`。\n- 根负责人对照分析：同目录 `decision-analysis/results.json`、`annual.json`、`rolling-36-months.json`。\n- 方法与下一对ETF资料盘点：同目录 `method-inventory/`；论文筛选：`literature-screen/`。\n- [首12参照报告](broad-etf-first12-account-comparison-2026-09-08.md)、[后续总计划](../superpowers/plans/2026-09-08-broad-index-etf-research.md)。\n\nOKR已按用户明确确认，仅将“宽基ETF：宽度择时与持续持有的完整资金比较”更新为进行中2/4；本批不自动增加完成数，其他目标保持原值。','## ARCHIVE','本批历史实验与解释完成后封存为mixed（有条件或证据不足）。结论是操作简化有继续验证价值，趋势参与此版本没有通用升级证据；不是所有宽基研究或未来观察均完成。最终文件指纹见批次 `final-manifest.json`；主计划、registry、INDEX和活跃OKR是后续可变导航，另存快照后不纳入旧封存文件修改。']
(ROOT/'docs/experiments/broad-etf-increment-decision-comparison-2026-09-08.md').write_text(''.join(('\n' if i and line.startswith('|') and lines[i-1].startswith('|') else '\n\n' if i else '')+line for i,line in enumerate(lines))+'\n')
