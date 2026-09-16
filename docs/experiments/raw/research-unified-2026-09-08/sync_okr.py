from pathlib import Path
import json,sys,datetime
P=Path(__file__).resolve().parent;ROOT=P.parents[3];sys.path.insert(0,str(ROOT/'src'))
from lei_signal.api import upgrades_store as s
from lei_signal.api.upgrade_models import GoalCreate,GoalPatch,GoalAction
DB='/Users/yongbiaoli/.lei_signal_lab/system_upgrades.db'
SCOPE=json.loads((P/'scope.json').read_text())['scope']
def save(n,x):(P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def get(k):return next(x for x in s.list_goals(DB)['items'] if x['id']==k)
def act(k,a,n,scope=''):
 x=get(k);return s.act_on_goal(DB,k,GoalAction(version=x['version'],action=a,note=n,scope=scope).model_dump(mode='json'))
def patch(k,**kw):
 x=get(k);return s.patch_goal(DB,k,GoalPatch(version=x['version'],**kw).model_dump(mode='json',exclude_unset=True))
def authorize(k,scope):
 if not get(k)['authorization']['granted']:act(k,'authorize','登记用户最新版任务书已给出的有限研究授权；不是新增请求批准。',scope)
def start(k):
 if get(k)['status']=='approved':act(k,'start','按已授权范围推进；仅记录实际完成部分。')
def link(name,label):return {'label':label,'url':'/library?report=docs%2Fexperiments%2F'+name}
L05=link('ambush-complete-menu-review-2026-09-08.md','05：旧退出复核与固定菜单结果')
L06=link('dca-instrument-measurement-review-2026-09-08.md','06：产品与资金计量审计')
L07=link('sentiment-combination-feasibility-review-2026-09-08.md','07：情绪组合可行性')
L08=link('ai-defense-evidence-audit-2026-09-08.md','08：AI缓存动作审计')
LU=link('research-unified-progress-2026-09-08.md','新版任务统一研究总览与后续清单')
if not (P/'okr-store-before-sync.json').exists():save('okr-store-before-sync.json',s.list_goals(DB))
ids={}
def create(key,title,parent,purpose,milestones,links,evidence,next_action,finished=False):
 matches=[x for x in s.list_goals(DB)['items'] if x['title']==title]
 if matches:x=matches[0]
 else:
  data=GoalCreate(kind='concrete',title=title,parent_id=parent,purpose=purpose,priority='high' if key in ['e02','unified','06a','08a'] else 'medium',owner='研究负责人',milestones=[{'id':'m'+str(i+1),'title':v} for i,v in enumerate(milestones)],links=links,next_action=next_action).model_dump(mode='json');x=s.create_goal(DB,data)
 k=x['id'];ids[key]=k;authorize(k,SCOPE+' 本项仅限：'+purpose)
 if finished:
  start(k);x=get(k);patch(k,milestones=[dict(m,done=True) for m in x['milestones']],evidence=evidence,next_action=next_action);act(k,'submit_review','已交本项有限研究成果和限制，交研究验收；不代表策略有效或生产通过。')
 else:patch(k,evidence=evidence,next_action=next_action)
 return k
k='okr-a2eff5db5b52';authorize(k,SCOPE);start(k);x=get(k);patch(k,owner='研究负责人＋独立研究复核',milestones=[dict(m,done=True) for m in x['milestones']],evidence='146原机会全部复现，58日期修正；64完整资金路径已逐笔核账。E01缺开盘两反例已修复，73份实际结果保持一致；全部缺数情形未声称完成。',next_action='研究成果已交，待验收；后续菜单结果见E02，不能自动采用生产规则。',links=[L05,LU]+[l for l in x['links'] if not l['label'].startswith('E01完整')]);act(k,'submit_review','E01有限范围完成，独立研究复核和公共证据卡已交；不代替用户验收。');ids['e01']=k
create('e02','E02：比较30%与成长50%退出的完整资金结果','D-increment','按E02跑前固定的三方案、8对象、4进入方法和两费用有限比较；不改产品分类，不扩黄金美股或参数。',['固定三方案、同预算与数据版本','交876单机会和192连续路径及收益风险取舍','完成指定独立核查、所有修正留痕与证据卡'],[L05,LU], '12条受改动连续路径9条财富增加、3条不变；各单机会组中位差0；64基准、40非改动对照、1笔50%动作及标签更正经独立核查。','待研究验收；保留历史有限支持，不自动采用50%。',True)
create('06a','06A：核对定投产品、资金流与跨市场时点','D-evidence','完成第18轮阶段A来源与计量审计；复用首轮两条资金核账，未知元数据明确保留。',['核对研究序列与可买产品、数据缺口','区分旧资金复现与风险计量更正','列出跨市场时点问题及允许引用范围'],[L06,LU], '已交产品映射、两旧路径计量对照和数据缺口；^IXIC不等于513100，隔离文件未启用；不将复用计新增实验。','阶段A待验收；实际产品与长历史研究尚未运行。',True)
create('06b','06B：补齐可比数据后验证定投组合长历史','D-increment','先查同产品、币种、分红、复权和可交易时间；通过才冻结原三对照有限研究。缺数据时只交缺口，不拼接成原组合。',['核实可用产品数据和缺失原因','固定最长可比窗口、共同资金及成交时间','资料合格后运行固定三对照或明确无法运行原因'],[L06,LU],'当前缺每份文件元数据、513100有效数据和统一跨市场时点，尚无合格新收益实验。','已获有限研究授权，等待资料条件满足；先查来源记录，不能恢复隔离数据或付费购买。')
create('07a','07A：核对情绪旧研究与组合可行性','D-evidence','核对完整四条件与旧简化研究差异，只做固定窗口状态描述并复用已有不足结果。',['说明旧研究覆盖哪些条件','保存64行日期状态描述及局限','给出一个有条件候选问题和停止条件'],[L07,LU],'旧脚本两条件不等于完整四条件；64行不计算收益；完整事件交集仍未知。','阶段A待验收；未来候选先补当时四条件资料。',True)
create('07b','07B：核实完整冰点是否增加不同的历史机会','D-increment','仅保留完整四条件在既有深超跌/底部进入中的新增信息问题；先数据可行性与事件重叠，不据日期数量认定收益有效。',['取得或明确缺少四条件逐日历史与发布时间','分开成立、不成立、未知及重叠机会','足够可比信息时固定一次完整资金方案，否则记录停止原因'],[L07,LU],'完整四条件逐日记录未齐；未开新收益研究，旧美股隔夜不足结果保留。','已获有限研究授权；先查完整条件记录，不做硬过滤、不重扫阈值。')
create('08a','08A：审计AI退出证据并重放缓存动作','D-evidence','核对缓存/报告/提示词版本与时点，运行五对象四项固定对照，不调用模型。',['完成130条缓存与旧报告对账','完成固定动作重放、现金核算与风险区别','区分可复现动作与不可复现模型能力'],[L08,LU],'130=123保持+7减半；20项重放、15条每日资金账；半导体少赚且最深下跌不改善，恒科机械与AI投入52/67不等。','阶段A待验收；不能宣传事前AI退出优势，后续先完善两类验证协议。',True)
create('08b','08B：分别设计AI解释价值与退出价值的未来验证','D-forward','仅设计两份协议：解释正确/遗漏/越权/成本，以及同资金新行情退出观察。当前不创建自动任务、不调用收费模型。',['分别定义两类主张、对照与完整输入版本','规定所有建议、失败和不行动的记录及事件归组','写清最低值得改善、观察量依据和启动条件'],[L08,LU],'阶段A报告已有两类设计框架；尚无执行版通过标准、所需观察量或未来记录。','在既有本地研究授权内完善协议；模型费用与生产记录接入另按边界处理。')
create('unified','交付新版任务的首批统一研究与后续清单','D-tracking','统一承接05—08及ATR/完整技术交易；本项完成首批研究交付与队列，不声称所有后续研究结束。',['交05完整菜单有限研究','交06/07/08审计与各自数据边界','统一ATR、完整交易及四线依赖和最多三个优先方向','归档报告、引用证据卡和OKR进展'],[LU,L05,L06,L07,L08],'E01/E02和AI固定动作重放完成；06长历史、07完整交集、08未来观察、ATR完整技术交易仍有明确后续项目。','待验收本轮研究交付；下一优先为退出基准费用/价格/重复计数，再决定ATR具体用途。',True)
# Preserve broader objectives; add status/evidence without claiming their old full criteria are met.
updates={
 'okr-2e99d9d04832':('按最新授权排在下一顺位：先冻结真实费用与价格来源，在隔离副本核对重复计数，再固定ATR单一用途比较。','首轮已有16机会核对与3笔价格差，费用适用与普通时间退出重复计数仍待系统复验。'),
 'K-baseline':('按最新授权先补可信退出基准，再固定同机会、同预算的完整技术方案；不无边界扫参。','首轮证据地图保留；本轮05完整资金方法不等于A/B/C/D完整对照已完成。'),
 'K-risk-attribution':('ATR四用途分开：初始距离、结构缓冲、盈利后跟随、仓位。先基准，后同金额/同计划风险有限比较。','本轮菜单与AI均同时报告财富、最深下跌和等待代价；ATR缓冲已存在且默认关，非本轮新发明。'),
 'K-data-boundary':('复用06产品和07完整条件缺口；先核当时来源与可交易时点，不擅自补值或启用隔离数据。','本轮06A/07A已交；不能把全部市场数据审计标完成。'),
 'K-trial-ledger':('复用本轮全部尝试及版本记录，再补其他旧研究，不将重复路径当独立试验。','E01两实现版本、E02三方案两标签版本、AI四项固定对照均已留档；无新参数搜索。'),
 'K-forward-protocol':('与08B合并设计工作，记录版本和新行情起点；本轮不启动自动观察。','08报告把解释价值与退出价值分开，尚未形成全部可执行通过标准。'),
 'okr-b9a424674e29':('复用05完整研究及06产品审计；长历史依赖数据，持续收入、闲钱和技术分批仍分别研究。','E01/E02已交，06A已交；未完成全部19轮、取款、阶梯加码或所有产品研究。')}
for key,(n,e) in updates.items():
 authorize(key,SCOPE+' 本具体目标仅限本地审计、固定有限方案与依赖准备，禁止大规模搜索、生产修改、收费调用。');x=get(key);links=x['links']+[LU] if LU not in x['links'] else x['links'];patch(key,next_action=n,evidence=e,owner='研究负责人',links=links);act(key,'note','最新版任务书覆盖旧逐步等待授权文字；各目标当前完成度仍按实际证据，不因授权记完成。')
for key in ['D-increment','D-evidence','D-forward','D-tracking','D-literature']:
 act(key,'note','研究负责人统一承接05—08及ATR/完整交易；本轮成果与后续项见“交付新版任务的首批统一研究与后续清单”。旧首轮保持待验收；Zotero沿用18篇与18份笔记，本轮未新增论文。')
save('okr-ids.json',ids);save('okr-after.json',s.list_goals(DB));save('okr-sync-method.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reason':'localhost:8000连接拒绝，使用同一现有upgrades_store保存逻辑，保留版本/授权/历史检查','store_path':DB,'other_databases_modified':False,'accept_action_used':False})
print(json.dumps(ids,ensure_ascii=False))
