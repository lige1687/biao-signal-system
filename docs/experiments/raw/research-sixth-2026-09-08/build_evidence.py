from pathlib import Path
import ast,json,hashlib
from dataclasses import dataclass,field
P=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
contract=P.parent/'research-fourth-2026-09-08/inputs/src/lei_signal/data_provenance.py'
nodes=[n for n in ast.parse(contract.read_text()).body if isinstance(n,ast.ClassDef) and n.name in ['EvidenceRef','MarketDataRef','RuleRef']]
ns=dict(dataclass=dataclass,field=field,COMPAT_UNKNOWN='unknown',SCHEMA_VERSION='provenance/1.2')
exec(compile(ast.Module(body=nodes,type_ignores=[]),'existing_frozen_contract','exec'),ns)
E,M,R=ns['EvidenceRef'],ns['MarketDataRef'],ns['RuleRef']
cfg=P/'inputs/configs/rules.v2.yaml'
rule=R('__ruleset__','2.1.0',str(cfg),sha(cfg),definition_ref='策略规格§2.3/§3/§9/§10；旧执行配置复现与固定机会研究，不修改生产').to_dict()
limits=['旧机会有历史选择偏差，未重生成入场','复权及指数代理不等于真实可买现金账户','真实产品成本及所有历史交易限制未核验','各标的资料尾期不同，MSFT末尾空价不能当有效观察','研究交付不等于生产采用或用户验收']
items=[('exit-baseline-2309','旧退出基准能否算对？','2245笔已结束交易全部独立复现；2309条中仍有一条MSFT尾部缺价观察限制。',['full-baseline-review/summary.json','full-baseline-review/all-2309-rows.csv','full-baseline-review/input-manifest.json','full-baseline-review/review-2026-09-08.md'],'legacy_reproduction',2309),('time-exit-899','旧普通时间退出真的拖累那么多吗？','两方案分别多算6条和2条，修正后变化接近零；不构成采用证据。',['protocol.md','protocol-addendum-01.md','time-exit-audit.json','time-exit-paired-ledger.csv','time-exit-review/README.md'],'legacy_duplicate_count_audit',899),('atr-half-buffer','结构位下方多留半个通常波动幅度是否有帮助？','同资金A平均结果略好但期间损失更深，B略差、C退出不变；同计划风险减少投入与损失，也降低平均收益。',['atr-protocol.md','atr-protocol-lock.json','atr-results.json','atr-paired-summary.json','atr-opportunity-ledger.csv','atr-review/README.md','atr-review/independent-results.json'],'fixed_opportunity_mechanism_comparison',2309)]
cards=[]
for key,q,c,paths,kind,n in items:
    files=[P/x for x in paths]
    ref=E(key,[str(f) for f in files],[sha(f) for f in files],'research-sixth/2026-09-08','mixed','逐标的历史范围，见价格质量表；不是当前信号',kind,compatibility='unknown',limitations='；'.join(limits)).to_dict()
    market=M('frozen_legacy_pool',instrument_id='A_B_C_historical_universe',market='mixed',health='unknown',reason='多市场代理、历史收盘/开盘；available_at没有逐条独立核实',extra={'input_manifest_path':str(P/'full-baseline-review/input-manifest.json'),'input_manifest_sha256':sha(P/'full-baseline-review/input-manifest.json')}).to_dict()
    cards.append({'user_question':q,'conclusion':c,'evidence_ref':ref,'market_data_refs':[market],'rule_refs':[rule],'research':{'run_id':'research-sixth-2026-09-08','opportunities':n,'independent_market_episodes':None,'independent_event_count_reason':'同一次市场变化会影响多笔持仓，交易行数不是独立行情次数。','independently_reviewed':True,'review_scope':'见各卡来源的独立复核报告；原输入与未来有效性不等同','production_adopted':False,'limitations':limits}})
(P/'evidence-cards.json').write_text(json.dumps(cards,ensure_ascii=False,indent=2)+'\n')
print('3 cards using existing provenance/1.2 contract')
