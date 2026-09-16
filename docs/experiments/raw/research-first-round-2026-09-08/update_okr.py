from pathlib import Path
import json,urllib.request,urllib.parse
P=Path(__file__).resolve().parent;BASE='http://localhost:8000/api/upgrades';log=[]
def req(method,path='',body=None):
 r=urllib.request.Request(BASE+path,data=None if body is None else json.dumps(body,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'},method=method)
 with urllib.request.urlopen(r) as f:return json.load(f)
def get(k):return next(x for x in req('GET')['items'] if x['id']==k)
def patch(k,**fields):
 x=get(k);y=req('PATCH','/'+k,{'version':x['version'],**fields});log.append({'id':k,'operation':'patch','version':y['version']});return y
def note(k,s):
 x=get(k);y=req('POST','/'+k+'/actions',{'version':x['version'],'action':'note','note':s});log.append({'id':k,'operation':'note','version':y['version']});return y
def link(name,label):return {'label':label,'url':'/library?report='+urllib.parse.quote('docs/experiments/'+name,safe='')}
report=link('research-first-round-ARCHIVE-2026-09-08.md','三路研究首轮报告与独立复核');protocol=link('research-first-experiment-protocol-2026-09-08.md','E01完整冻结方案（尚未执行）')
new_specs=[dict(kind='concrete',parent_id='D-increment',title='E01：复核旧定投目标退出的成交时间与完整资金',purpose='在已有闲钱情景下，先对原146个目标退出机会核对时间，再用单份预算重放完整路径。保留旧实现对账，不寻找新阈值。与既有定投总目标关联，范围见冻结方案。',priority='high',owner='研究负责人＋独立复核',next_action='待按E01具体范围授权执行；先核验冻结资料、日历及报价限制，保留全部失败与未执行机会。',evidence='首轮已完成21笔时间诊断与第18两条资金账。全对象修正及完整资金版本尚未运行。',milestones=[{'id':'e1','title':'固定输入与完整事件身份，原146个机会对账或逐项解释差异','done':False},{'id':'e2','title':'按冻结方案完成时间修正与单份预算路径，现金和持仓全部对账','done':False},{'id':'e3','title':'报告全部对象、失败与边界，独立复核并交可引用证据','done':False}],links=[protocol,report,{'label':'关联定投总目标','url':'/upgrades?goal=okr-b9a424674e29'}]),dict(kind='concrete',parent_id='D-evidence',title='核对退出基准的费用、价格版本与重复计数',purpose='为后续ATR及退出增量比较建立可信起点：区分市场费用、统一结构位与成交价版本、复核旧普通时间退出的重复计数。先做隔离研究，不修改生产规则。',priority='high',owner='研究负责人＋总控独立复核',next_action='待界定并授权具体重放范围；用归档175对象清单，先核对默认基准，暂不搜索新参数。',evidence='首轮16机会与独立循环全一致、旧记录13一致；3笔价格版本差异。低价ETF收费下限适用性和真实机会重复计数已留最小反例。',milestones=[{'id':'x1','title':'冻结真实运行版本和价格来源，结构位与成交价同口径','done':False},{'id':'x2','title':'区分历史复现费用与产品适用成本，逐机会核对差异','done':False},{'id':'x3','title':'在隔离副本修核重复计数并交独立复核与引用影响清单','done':False}],links=[report,{'label':'关联风险贡献目标','url':'/upgrades?goal=K-risk-attribution'}])]
ids={}
for spec in new_specs:
 existing=next((x for x in req('GET')['items'] if x['title']==spec['title']),None)
 y=existing or req('POST','',spec);ids[spec['title']]=y['id']
 if not existing:
  req('POST','/'+y['id']+'/actions',{'version':y['version'],'action':'request_approval','note':'首轮研究形成的后续具体任务；本次仅登记完整范围，尚未执行后续全量实验。'})
root='okr-9236b2cd4622';x=get(root);m=[{**a,'done':True} for a in x['milestones']]
y=patch(root,owner='研究负责人（主agent＋三位子agent）',next_action='首轮五项成果已交，待用户验收。后续优先E01，再核对退出基准；具体范围和依赖已登记。',evidence='2026-09-08：九环节地图、3优先方向、E01冻结方案完成。退出3标的16机会与独立循环一致13笔复现旧记录；第13轮730行摘要及21笔原结果对账，10笔修正退出日；第18两条完整终值一致，资金风险经另一agent独立复核。6篇文献＋笔记加入Zotero，共18篇18笔记。研究结论mixed，未改生产、未证明新规则有效。',milestones=m,links=x['links']+[report,protocol]+[{'label':title,'url':'/upgrades?goal='+k} for title,k in ids.items()])
req('POST','/'+root+'/actions',{'version':y['version'],'action':'submit_review','note':'五项首轮成果已完成并归档。提交待验收，不自行代表用户验收或认定策略有效。'})
updates={
'K-recent':'首轮范围内新增6篇近期/高度相关方法研究及中文笔记，Zotero现18篇18笔记。包括2026趋势和ATR退出；全文不足、预印本、机构研究、版本差异均标注。此为阶段成果，尚非全面近期文献筛选结案。',
'okr-b9a424674e29':'首轮三类资金用途已分开，原定投13/18轮有时间与资金计量问题，真实最小例经独立交叉复核。E01已登记为后续具体工作；该总目标和全部19轮研究并未完成。',
'okr-6b16fa610e41':'首轮已整理可直接解释、固定方法补测、新研究三类出口，给出兼容既有引用类型的研究卡。旧胜率按对象日期去重会丢模块；缺价及日期复例通过。真实观察链仍待工程固定版本后复验。',
'K-risk-attribution':'先区分账户余额下跌与排除入金的投资价值下跌；第18 W5两者为9.67%/23.38%，不是用户实际本金亏损声明。ATR缓冲已存在且默认关闭，后续需同金额与同计划风险分别比较。',
'K-data-boundary':'175对象旧池已归档，不再沿用数据丢失结论。池含指数/板块/跨市场对象；本轮3笔价格与旧记录不一致，低价ETF收费下限适用性待核。第18纳指综合不等于纳指100。',
'K-trial-ledger':'首轮已冻结各路输入及结果指纹；普通时间退出旧参照重复计数有真实反例。已看过历史不能重新称未见验证，E01冻结说明已写明。',
'K-newmodules':'超出ABCD的长期方向保留：简单趋势对照、独立风险权重、资金用途与取款安排。当前仅方法提案，没有足以直接启用的新模块证据，先修比较基础。',
'K-baseline':'原有模块与简单趋势/普通突破的严格同资金对照仍属缺口。首轮仅16个已知机会的退出复现，未重生成入场，不冒称完整基准比较已完成。'
}
for k,s in updates.items():
 x=get(k);links=x['links'];
 if not any(a['url']==report['url'] for a in links):patch(k,links=links+[report])
 note(k,s+' 依据：首轮报告 research-first-round-ARCHIVE-2026-09-08.md。')
(P/'okr-updates.json').write_text(json.dumps({'new_goals':ids,'operations':log},ensure_ascii=False,indent=2));export=req('GET','/export');(P/'okr-after.json').write_text(json.dumps(export,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'new_goals':ids,'root':get(root)['status'],'milestones':get(root)['progress']},ensure_ascii=False))
