"""Apply only the exact three-item proposal accepted by the user's 开干好吧."""
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote

P = Path(__file__).resolve().parent
BASE = 'http://localhost:8000/api/upgrades'
def save(name, value):
    (P/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
def read():
    return json.load(urlopen(BASE))
def send(path, method, data, label):
    save(label+'-request.json', data)
    req = Request(BASE+path, data=json.dumps(data, ensure_ascii=False).encode(),
                  headers={'Content-Type':'application/json'}, method=method)
    result = json.load(urlopen(req))
    save(label+'-response.json', result)
    return result
def link(label, filename):
    return {'label':label, 'url':'/library?report='+quote('docs/experiments/'+filename, safe='')}

items = {x['id']:x for x in read()['items']}
title = '宽基ETF：宽度择时与持续持有的完整资金比较'
assert not any(x['title']==title for x in items.values()), 'Existing goal must be inspected, never duplicated.'
overview = link('宽基ETF专项计划与旧基准核查', 'broad-etf-research-plan-and-baseline-2026-09-08.md')
goal = send('', 'POST', {
    'kind':'concrete', 'title':title, 'parent_id':'D-increment', 'priority':'high',
    'owner':'研究负责人（Astra审阅，Sol执行）',
    'purpose':'以宽基ETF为主战场，同一产品、同一资金与费用，比较持续持有、既有宽度择时和简单趋势。先核旧资金计算，再从沪深300ETF与创业板ETF开始，按固定六宽基范围扩展。研究结果与未来采用分别验收。',
    'next_action':'核清旧九指数权重漂移差异；冻结510300与159915的交易时点、份额现金及行动处理，执行三方法×两费用共12账户并独立核算。',
    'evidence':'专项计划已落在 docs/superpowers/plans/2026-09-08-broad-index-etf-research.md。已完成来源盘点、12产品资格清单、原两条九指数路径复算及权重漂移最小例；这些不等于可信资金基准或首12ETF账户已完成。用户确认新增为进行中0/4。',
    'milestones':[{'id':'m'+str(i+1),'title':s,'done':False} for i,s in enumerate([
        '核清可信基准与产品资料准备', '完成首12个账户及独立资金比较',
        '完成六只宽基ETF固定范围覆盖', '交付完整结论与后续观察交接'])],
    'links':[overview]
}, 'create')
key = goal['id']
scope = '用户在确认三条OKR写入提案后回复“开干好吧”。授权本专项按已存计划开展有限本地研究；本次登记进行中0/4。先核旧资金差异、执行510300/159915首12账户，再按固定六宽基范围推进；不改生产规则、不实际交易、不收费取数、不无边界扫参。完成数或验收状态后续仍按用户要求具体确认。'
goal = send('/'+key+'/actions','POST',{'version':goal['version'],'action':'authorize','note':'记录用户对上一条具体提案的明确确认：“开干好吧”。','scope':scope},'authorize')
goal = send('/'+key+'/actions','POST',{'version':goal['version'],'action':'start','note':'按已确认提案开始；四项完成标准暂不勾选。'},'start')

g = items['K-baseline']
assert g['status']=='in_progress' and sum(m['done'] for m in g['milestones'])==3
links = list(g['links'])
for entry in [link('第十二批：A/C/D有限完整账户','acd-limited-account-comparison-2026-09-08.md'),link('第十三批：A道路退出完整比较','a-road-exit-account-comparison-2026-09-08.md'),link('第十四批：顶部有效期消费检查','a-top-lifecycle-consumer-audit-2026-09-08.md'),overview]:
    if entry['url'] not in {l['url'] for l in links}: links.append(entry)
send('/K-baseline','PATCH',{
    'version':g['version'], 'links':links,
    'evidence':g['evidence']+'\n用户确认后补记第十二至十四批：修复后A/C/D有限账户、A道路退出比较、顶部有效期消费修复已经分别归档；完整模块定义、ETF全面覆盖及生产采用仍未完成。接续宽基ETF专项阶段三，个股旧结果仅参考。本次保持进行中3/4。',
    'next_action':'以宽基ETF优先，接续专项计划阶段三：先510300/159915，六A、三C、一个D与两简单参照分别算完整资金；复用第十二至十四批修复。B箱体与A6②同日歧义只挂起对应配置。'
},'baseline')
g = items['K-newmodules']
assert g['status']=='planned' and sum(m['done'] for m in g['milestones'])==0
links = list(g['links'])
if overview['url'] not in {l['url'] for l in links}: links.append(overview)
send('/K-newmodules','PATCH',{
    'version':g['version'], 'links':links,
    'evidence':g['evidence']+'\n专项计划阶段四保留最多三候选：低频趋势与成本、退出后再次进入、同风险资金分配；核对已有失败研究与原文后，最多两项进入首轮有限实验，每项最多2产品×原新2版本×2费用。来源线索包括Moskowitz等2012、Kaminski/Lo2014、Cederburg等2020、Jeon/Masturzo2025、Sepp/Lucic2026；不把线索当新增精读或已完成模块。保持待规划0/4。',
    'next_action':'随宽基ETF基准准备，先核三候选的原文、重复研究与数据可得性，冻结两项以内的具体实验；未完成前不计新模块成果。'
},'newmodules')
after = read(); save('after.json',after)
after_items = {x['id']:x for x in after['items']}
for k,g in items.items():
    if k not in {'K-baseline','K-newmodules'}:
        assert after_items[k]['version']==g['version'], k
for k,status,done in [(key,'in_progress',0),('K-baseline','in_progress',3),('K-newmodules','planned',0)]:
    g=after_items[k]; assert g['status']==status and sum(m['done'] for m in g['milestones'])==done
save('verification.json',{'new_id':key,'only_confirmed_targets_changed':True,'progress':{k:after_items[k]['progress'] for k in [key,'K-baseline','K-newmodules']}})
print(json.dumps({'new_id':key,'verified':True},ensure_ascii=False))
