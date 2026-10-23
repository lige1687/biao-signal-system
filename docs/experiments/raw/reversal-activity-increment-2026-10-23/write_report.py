"""Render reviewed numbers and boundaries, not a new experiment."""
from pathlib import Path
import json, shutil, hashlib
import pandas as pd
D=Path(__file__).resolve().parent
W=D.parents[3]
O=Path(json.loads((D/'storage-plan-v2.json').read_text())['output'])
S=pd.read_csv(O/'account-summary.csv.gz')
X=json.loads((D/'supplement-summary.json').read_text())
C=json.loads((O/'monthly-comparisons.json').read_text())
PERIODS={'full':'2015—2025','early':'2015—2018','middle':'2019—2021','late':'2022—2025'}
NAMES={'G1':'G1 前月最强','G2':'G2','G3':'G3','G4':'G4','G5':'G5 前月最弱','pool':'同档全体','lowvol':'同数量低波动','rev_volbalanced':'波动分层后反转'}
def pct(v):return f'{v*100:.2f}%'
def pp(v):return f'{v*100:+.2f}'
def row(s,p,period='full',fee=25):return S[(S.account==f's{s}__{p}__fee{fee}')&(S.period==period)].iloc[0]
def tab(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'---|'*len(headers)]+['| '+' | '.join(map(str,r))+' |' for r in rows])
def inc(s,a,b):return next(r for r in C if r['stratum']==s and r['candidate']==a and r['baseline']==b and r['fee_bps']==25 and r['period']=='full')
main=[]
for s in (1,2,3):
 a,b,c=row(s,'G5'),row(s,'pool'),row(s,'lowvol')
 main.append([['低','中','高'][s-1],pp(a.cumulative_return-b.cumulative_return),pct(a.annualized_return),pct(b.annualized_return),pct(c.annualized_return),pp(a.annualized_return-c.annualized_return),pct(-a.max_daily_drawdown),pct(-b.max_daily_drawdown)])
main_table=tab(['形成前成交金额档','反转比同档全体累计多赚/少赚（百分点）','反转年均','同档全体年均','低波动年均','反转比低波动年均差（百分点）','反转最大跌幅','同档全体最大跌幅'],main)
increment=[]
for s in (1,2,3):
 for a,b in [('G5','pool'),('G5','lowvol'),('rev_volbalanced','pool')]:
  c=inc(s,a,b);u=c['hac3'];increment.append([s,NAMES[a]+' 对 '+NAMES[b],pp(u['mean']),f"[{pp(u['ci_low'])}, {pp(u['ci_high'])}]",pp(c['up_months']['mean_difference']),pp(c['down_months']['mean_difference'])])
increment_table=tab(['档','候选与对手','每月平均差（百分点）','考虑相邻月份相关的95%范围','同档上涨月份差','同档下跌月份差'],increment)
selection=[]
for r in X['selection']:
 u=r['rankic'];selection.append([r['stratum'],f"{u['mean']:.4f}",f"[{u['ci_low']:.4f}, {u['ci_high']:.4f}]",r['rankic_known_pairs'],r['five_groups_shared_months']]+[pct(r['five_groups_mean'][f'G{i}']) for i in range(1,6)])
selection_table=tab(['档','排名关联均值','95%范围','已知股票月','五组共同完整月','G1','G2','G3','G4','G5'],selection)
risk=[];cost=[];period=[];allgroups=[]
for s in (1,2,3):
 for p in ('G5','lowvol','pool','rev_volbalanced'):
  r=row(s,p);e=next(v for v in X['account_extra'] if v['account']==r.account)
  risk.append([s,NAMES[p],pct(r.average_unknown_fraction),pct(e['unknown_max']),pct(e['unknown_end']),pct(r.average_cash_fraction),f"{e['traded_value_per_year_over_daily_nav']:.1f}倍",int(r.trades),f"{r.fees:,.0f}"])
  cost.append([s,NAMES[p],pct(row(s,p,fee=0).annualized_return),pct(r.annualized_return)])
  period.append([s,NAMES[p]]+[pct(row(s,p,z).annualized_return) for z in ('early','middle','late')])
 for p in [f'G{i}' for i in range(1,6)]+['pool','lowvol','rev_volbalanced']:
  r=row(s,p);b=row(s,'pool');allgroups.append([s,NAMES[p],pct(r.cumulative_return),pp(r.cumulative_return-b.cumulative_return),pct(r.annualized_return),pct(-r.max_daily_drawdown)])
opps=[]
for s in (1,2,3):
 for p in ('G5','lowvol','rev_volbalanced'):
  r=next(v for v in X['opportunities'] if v['stratum']==s and v['portfolio']==p)
  opps.append([s,NAMES[p],f"{r['known_winners_retained']}/{r['known_winners_available']}",pct(r['known_winner_capture']),pct(r['loss_fraction_known']),pct(r['deep_loss_fraction_known'])])
report=f'''# 成交活跃程度能否改善月度反转：固定300股、11年分层检验

## 一句话结论（大白话）

**本轮没有找到可加入个人低频策略的稳定改善。** 在固定300只历史A股、2015—2025年中，前月回报的反向排序与后续回报有正向关联，但“成交金额低就更适合反转”的猜想未获支持；扣除假定交易费用后，三档反转的年均收益都低于同数量低波动选择。中、高成交档相对同档全体有局部少亏线索，仍有时期反例、频繁换股和停牌估值限制。暂停直接把月度最弱20%作为新增买入规则，保留有条件的研究价值。

## 最关键结果：先看明确基准的超额

此处的基准是**每个月在同一成交金额档内全部合格股票平均分配资金**，与候选使用相同资金、成交规则和费用。固定300股不是沪深300或中证1000，故没有合法的“母指数超额”可直接宣称。所有收益均为**单边0.25%费用假设下的开盘报价模拟**，尚未核用户实际费表、真实成交和完整现金分红。最大跌幅由每日记录算出，但未知持仓沿用最后可信报价，不能当实盘风险上限。

{main_table}

累计收益差是两个账户的累计回报直接相减；年均为复利年均，不能相加。下表里的月均差是另一种统计口径，波动与复利会使二者方向不完全一致。

![三档相对同档全体的累计收益差](/research/reversal-activity-increment-20261023/excess-curves.svg)

图以月末绘制，虚线分开2015—2018、2019—2021、2022—2025。这些都是**已经看过的历史**，不是新的验证样本。G1是前月最强，G5是前月最弱；图上的G3较好也不能事后改成“买G3”并宣布发现策略。[查看绝对资产曲线](/research/reversal-activity-increment-20261023/absolute-curves.svg)。

## 现在知道什么，以及仍不知道什么

- **范围确实改变表现，但不能只贴“小盘股”标签。** 低成交档反转相对同档全体月均少0.490个百分点，高成交档多0.157个百分点；低档改善减高档改善为−0.647个百分点/月，95%范围[−1.220, −0.073]。它是当前报价情景的历史差异，无法证明原因。成交金额没有提供市值、自由流通股、散户占比、价差或行业身份。
- **排序有信息不等于买最弱组有效。** 三档的前月反向排序与次月涨跌的排名关联均值均为正；完整五组比较却没有稳定逐组递增，且最弱组对低波动的收益增量范围都容纳改善和恶化。
- **月度调仓仍可能很费交易。** 反转每年买卖金额合计约账户资产的19—20倍，同数量低波动约6.5—8.6倍。零费用时中、高档反转的年均收益高于低波动；加入单边0.25%假设后反转低于低波动，说明成本会改变判断。此假设没有额外叠加已实测的价差与冲击，也不是用户实际成本。
- **风险价值仍要单独看。** 中、高档相对同档全体最大跌幅较浅；但相对低波动，高档反转跌得更深，近段2022—2025三档反转年均收益全部落后低波动，不能称通用防守升级。低档对低波动全期最大跌幅略浅，伴随更差的近段表现与更高费用。
- **未知估值是实质限制。** 三档反转平均未知价值占比约6.31%、3.37%、2.47%；峰值达70.88%、71.04%、67.07%。Luna独核峰值日55条持仓原件，全部存在且来源指纹一致，三天的停牌数量14/11/13与滞后估值数量相同，未发现当日来源衔接矛盾。这支持“停牌时保留旧报价”的解释，不能把平滑曲线叫风险保护。

真实母指数含分红净超额、用户实费、集合竞价能否成交、涨跌停排队、整手约束、退市现金结算、历史数据发布与修订版本，以及未看过的新时期，均未评价或尚未取得完整资格。三档每月按当时金额重分，所以这不是三套固定股票名单。

## 按用途评价：排序、收益、风险和机会

先把股票按因子排序，再看未来涨跌的排序是否相近，这个相关程度叫RankIC；本轮使用**前月回报取负数**，因此正数代表“前月较弱、次月相对较强”的线索。不是平均总分，也没有预设应当达到0.04或0.06来调代码。

{selection_table}

五组均值是形成月之后首个交易日开盘至再下一月首个交易日开盘的保存报价变化，仅使用该档**五组全部完整的相同月份**，未扣费、不是连续账户；132个月仍保留未知位置，不用删掉缺数的月份拼成长账户。这里只剩75/73/73个完整月，缺失可能具有选择性。账户表则保留所有132个月、失败成交及滞后估值，两种结果不得混称。排名关联的已知股票月总数是{sum(r['rankic_known_pairs'] for r in X['selection']):,}，不同股票同月相关，不能将其当成同数量独立试验。

{tab(['档','选择','保留的大涨机会/同档已知大涨机会','大涨机会保留比例','所选已知结果中下跌比例','所选已知结果中跌≥20%比例'],opps)}

“大涨”事前固定为保存的次月报价涨幅≥20%。这只是已知结果的机会计数，未知没有补零，也不是已兑现收益。反转比低波动保留更多大涨机会，同时所选股票发生大跌的比例更高。各档本来只选约20%，不能把未选中的80%都当作失败。

## 相对已有简单方法到底增加了什么

{increment_table}

共同日期均为132个月。95%范围用于表达历史估计的不确定性，按相邻3个月的相关性作修正，不是“结论为真的概率”，也未证明已排除多次研究挑选的影响。上涨/下跌分组按**该月结束后**同档全体账户收益划分，只解释代价，**不是前向牛熊择时信号**。

波动分层后反转：先按过去60日波动分成两半，各半再选前月最弱20%，保留原来两半的资金占比。它让反转与同档全体的波动差异缩小，但没有完全相同：三档所选日波动均值约2.42%/2.88%/3.24%，同档全体2.39%/2.81%/3.12%；对应中期动量也仍有差异。故只能叫**粗略控制波动后的对照**，不能宣称独立于波动和动量的信息。

逐个排除某一年重新汇总既有月差额后，低档G5对同档全体仍为负（−0.671至−0.367个百分点/月）；三档G5对低波动都可因排除不同年份而正负改变。高档的波动分层反转对同档全体保留正向线索，但全部时期和低波动对手并不一致，保留观察，未达到采用依据。

## 分期、费用与资金代价

{tab(['档','方法','2015—2018年均','2019—2021年均','2022—2025年均'],period)}

以上期间在结果前固定，没有训练参数，全部已见。每段从上一段实际资产继续计算；分段跌幅从该段起点重新计峰值，不能理解为原账户此前损失已恢复。

{tab(['档','方法','零费用年均','单边0.25%年均'],cost)}

{tab(['档','方法','平均未知价值占比','峰值未知占比','期末未知占比','平均现金占比','每年买卖额/当时资产','11年成交笔数','假定费用合计（元）'],risk)}

每套账户起始10万元，无追加投入，现金零息，无结尾强制清仓；月末确定名单，下月首个交易日开盘按报价尝试成交，先卖后买。卖不掉继续持有，买不到保留现金，不把失败股票的资金重新塞给买成的股票。全部48套现金、成交费、期末持仓估值与月末资产由主控独立核数。期末每套现金、持仓、将未知持仓暂按零计的期末敏感性，以及最长未收复前高的交易日数，见supplement-summary.json；零估值只是一时点压力值，不是真实退市损失或完整最差路径。

## Universe的金融理由与实际构建

金融猜想是：短期买卖压力可能让价格偏离，压力消退后回归；但交易不活跃也可能意味着坏消息尚未消化、价差大、停牌或无法成交。因此必须在同一金额档内与简单方法比较，同时看成本和少赚。

原始材料来自BaoStock历史接口：2014-12-31快照2595只，2026-10-19取得，不能称已取得当年的发布版本。复用2026-10-20冻结抽选：从历史快照去掉原600只，按固定salt加证券代码的SHA-256排序取300只；不是按后来收益挑选，没有按后来仍上市筛选。保留后来退出对象，完整退市财富仍未齐。

原研究共有36,019个股票月，要求既有月回报、60日波动、中期动量和年内高点资料共同合格，本轮继承该范围，因此比“有反转数据即可”更窄。新增形成日前含当日60个市场交易日的原始人民币成交金额均值：显式停牌零值计入，缺失/非法值拒绝；169行金额缺失不合格后剩35,850行，每月237—292只。按当月金额分三档，每档至少30只，全部396档月合格。无新行情下载，无当前指数名单回填。

形成期2014-12至2025-11，持有期2015-01至2025-12，132个月；金额/因子只使用形成日及以前。开盘资格只读开盘、当日前收、此前原价与有效调整因子、假定已知交易状态；当日收盘/最高最低/全天量不参与开盘订单。日内收盘审计只能事后标记未知，不能撤销早晨订单。历史状态与调整信息的真实供应商到达时间未证实，故依然只是有时点隔离的回溯报价情景。

## 文献依据、广泛研究的去重安排与下一决定

| 原始方法/资料 | 实际读到的范围 | 本轮用途与边界 |
|---|---|---|
| [Nagel：Evaporating Liquidity](https://www.nber.org/papers/w17653) | 搜索返回摘要；原页403保留 | 把短期反转与提供流动性联系起来，支持竞争假说；不是A股月度效果证明 |
| [Robeco：限制换手与交易成本](https://www.robeco.com/nl-nl/visie/2017/05/factor-investing-challenges-limiting-turnover) | 作者机构说明相关段落 | 提醒反转小股票交易成本可能抵消收益；未直接移用其参数和结果 |
| [Robeco：短期剩余收益反转](https://www.robeco.com/nl-nl/visie/2011/11/short-term-residual-reversal) | 作者机构方法摘要 | 提出扣除共同市场/风格影响后的另一解释；完整原稿规格与历史行业未齐，本轮未冒称复现 |
| [2026反转测量论文入口](https://doi.org/10.1016/j.econlet.2026.113113) | 仅搜索摘要，原稿读取失败 | 留作原文待核，不据摘要引入新算法或引用数值结论 |

| 金融方向 | 已有工作与本轮取舍 |
|---|---|
| 临时买卖压力/反转 | 本轮实际完成成交金额分层及波动对照；暂停直接月度最弱20%买入，不为G3较好改规则 |
| 下跌敏感度/交易不活跃程度 | 另一负责人已完成两项ETF有限对照，原报告downside-sensitivity-universe-2026-10-23.md保留不采纳结论；本轮不重跑，也不把ETF结论代替个股 |
| 经营盈利、价值和中期动量 | 复用原逐股与公开组合结果；缺历史财务结构/共同逐股资格的部分不得用公开组合均值代替，已完成组合owner独立负责 |
| 机构资金压力 | mechanism-rebalancing-review负责人正核A股两基金跨期申赎与完整持仓，本方不另取同批资料 |
| 标准指数股票池 | research-utility负责人正在核沪深300、中证500、标普500、纳指100的历史名单/价格/退出；新增中证1000/2000和Russell范围资格归downside负责人。19:23快照仍未开放完整池，不把采集数写成合格样本 |

**下一步优先级是资料合格后检验有明确市场身份的同一反转定义，尤其先排除“小盘/散户”等未经测量的解释；不再从当前300只中挑出好看的组。** 若继续一个新的金融问题，优先核原文所说的“扣除共同市场/行业涨跌后，个股独有的短期偏离是否回归”，需要精确定义、历史行业与新验证范围；在这些前提未齐之前不宣称它已经有效。当前金额分层问题已回答，无理由再改窗口或扩大一批同源价格变形。

## 证据、失败与ARCHIVE

本轮主控按research-closure、lei-lowfreq-research及current-standards实际索引执行。独立研究工具不在原生二分类预测适配器范围内，不冒称通过原生预测流程。规范、方法、定义及两份策略原文指纹均绑定于contract-v2.json/design.json/resolved-definitions.json；原策略、LEI判定、生产和交易权限均未改。

准确对象：research.selection.short_reversal.month_return@1.0.0、research.selection.short_reversal.vol60@1.0.0（复用）；research.selection.activity.amount60@1.0.0、research.selection.activity.reversal_volbalanced@1.0.0、research.selection.activity.open_quote_policy@1.0.0（新增）。三新卡单独通过定义校验，不声称既有整个定义库全绿。

定义清楚：本地适配；数据资格：限定回溯报价、到达版本未知；实现核验：13个合成用例与独立核数通过；有效性：有排序/风险机会线索、未确认稳定可采用增量；生产授权：无。来源使用6/6，含2读取失败，行情请求0。核心尝试1次在计算前失败，必要修复1/3完成同一固定比较，实际账户效果仅一批48套；所有失败和旧家族研究保留，完整家族累计次数未知，不能把48套视作48个独立发现。

预跑发现并修复：G5排序符号反向、金额状态未核、缺报价被当永久断点、未调仓持仓没有更新可信开盘价、跨档差额符号相反；均发生于本轮真实效果前，13个小样例覆盖。定义登记前三次字段/路径检查失败留存。第一次真实启动因主控提前建日志目录触发新路径保护退出1，未读取效果；新plan/newcontract/newrunner只改合同定位，后一次退出0。外盘原失败目录未删除，未覆盖旧报告或原引擎。

独立核数：48账户、128,352日资产记录、256,854笔成交、96组配对统计、396个档月、18个原件60日金额锚点及逐月RankIC。Astra只读方法与关键修复审阅，Sol实现，Luna执行和未知峰值原件检查，root独立数值验收与结论。工程检查不证明数据完全可靠或策略有效。

复现入口：本报告同名raw目录内run-v2.py、contract-v2.json、input-refs.json、storage-plan-v2.json、dev-receipt.json、core-execution-receipt-v2.json、independent-audit.json、supplement-summary.json、unknown-peak-audit.json、audit_and_present.py。大结果位置：`{O}`。manifest绑定每个结果；此路径只有接入已登记同一资源盘才能读取，代码拉取不等于原件已移交。旧冻结文件保持原SHA，原失败与重试回执单列。

### 全部五组与对手，避免只展示赢家

{tab(['档','方法','累计收益','比同档全体累计差（百分点）','复利年均','每日最大跌幅'],allgroups)}

### 最小决策卡

- 改善了什么：确认股票范围与交易费用会改变反转表现，区分了排序信息、买入最弱组、低波动风险控制与上涨机会。
- 代价是什么：较高买卖额、更多下跌机会、停牌估值未知、跨期反例；约11年已见历史不能替代新验证。
- 保留什么：局部排序关联、更多大涨机会以及高成交档粗波动控制后的有限线索，均未授权交易。
- 暂停什么：固定月度买最弱20%作为通用增收益或防守规则；不将最低成交档当“优选universe”。
- 恢复条件：标准历史成员/退出/成本与报价处理资格补齐，或精确的新机制原文与独立验证资料能改变当前判断；复用本轮，不调参数救结果。
'''
import re
report=re.sub(r'research\.selection\.[\w.]+@1\.0\.0',lambda m:'`'+m.group(0)+'`',report)
(W/'docs/experiments/reversal-activity-increment-2026-10-23.md').write_text(report)
assets=W/'web/public/research/reversal-activity-increment-20261023';assets.mkdir(parents=True,exist_ok=True)
for name in ['excess-curves.svg','absolute-curves.svg']:shutil.copyfile(D/name,assets/name)
print('report written',len(report.encode()),'bytes; 2 static SVG assets')
