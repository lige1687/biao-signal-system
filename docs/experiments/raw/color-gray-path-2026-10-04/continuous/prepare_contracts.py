from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from lei_signal.research.color_continuous_workflow import BASELINE_FEATURES,ADDED_FEATURES,DEFINITION_REF,build_qualification
from lei_signal.research.lightgbm_information import PARAMETERS,NUM_BOOST_ROUND,PACKAGE_VERSION,runtime_fingerprint
from lei_signal.research.question_contract import validate_workflow_contract
ROOT=Path(__file__).resolve().parents[5]; HERE=Path(__file__).resolve().parent
panel=json.loads((ROOT/'docs/experiments/raw/volume-information-2026-09-30/execution/panel.json').read_text())
prior=json.loads((ROOT/'docs/experiments/raw/color-event-universe-2026-10-04/core/green-return20/freeze-01/contract.json').read_text())
def put(p,x):
 p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
ledger={'maximum_real_fits':16,'actual_real_fits':0,'branches':[],'history':'Continuous question16 fits additional to gray16 and prior color-event16; no grid.'}
for method in ['prediction_ridge','prediction_lightgbm']:
 for target in ['forward_return','mae']:
  name=method.removeprefix('prediction_')+'-'+target;c=deepcopy(prior)
  for k in ['bindings','freeze','rehearsal','calendar']:c.pop(k,None)
  c['feature']={'kind':'color_continuous_workflow','lookback':20,'bar_frequency':'daily_quote','warmup':252,'missing_policy':'segmented','definition_ref':DEFINITION_REF}
  c['target']['kind']=target
  q=c['question'];q.pop('event_definition',None)
  q.update(question_id='color-continuous-'+name+'-2026-10-04',hypothesis_family='color-continuous-'+name+'-2026-10-04',factor_refs=[DEFINITION_REF],sampling='daily',joint_structure='同日ETF共同波动、连续灰色和20间隔结果重叠',baseline='成熟每ETF均值；20/60当前颜色、ret20/ret60/vol20、多头排列、旧EMA上行比例和ETF身份',added_information='20日严格绿色占比、19对颜色变动频率、有符号EMA20距离',added_information_reason='历史路径表达，是否补充指定基线须检验；不预设黑必跌',decision_use='检验连续颜色表达的同日排序及额外预测帮助，非账户收益',method={'name':method,'reason':'固定线性lambda1与40轮depth2浅树；不调参'},trial_history='两目标两方法两折两模型16拟合；全部行情已见；连续表达另批16不混算',auxiliary_metrics=['同日Spearman排名关联；平均并列名次高低两组rank大于/小于0.5，中间相等保留中组；同时期池均值/ret20趋势/旧EMA占比参照','逐期逐ETF、去一ETF、日期同步20/60日块1000次','按原值方向描述，不按评价翻转；排名原值与变换恒等检查'],dependence='完整评价交易日历同步20/60日块，灰日/ETF行不独立')
  q['target'].update(kind=target,price_basis='close_to_close' if target=='forward_return' else 'close_to_close_path')
  e={'kind':method,'version':'1.0.0','baseline_features':list(BASELINE_FEATURES),'added_features':list(ADDED_FEATURES),'minimum_training_rows':40}
  if method=='prediction_ridge':e['lambda']=1.0
  else:e.update(parameters=PARAMETERS,num_boost_round=NUM_BOOST_ROUND,package_version=PACKAGE_VERSION,runtime=runtime_fingerprint())
  c['evaluator']=e;c['history']={'family':q['hypothesis_family'],'changed_after_results_reason':'New fixed continuous bundle question; no outcomes read before freeze; historical exploration','ledger_path':'docs/experiments/raw/research-workflow-ledgers-2026-09-29/'+sha256(q['hypothesis_family'].encode()).hexdigest()[:24]+'/attempts.jsonl'}
  c['publication']={'report_path':'docs/experiments/color-continuous-'+name+'-2026-10-04.md','category':'模块与信号','claimed_scope':'partial','conclusion':'not_supported'}
  for k,reason in {'universe_fit':'四ETF有限回顾资料；真实到达/行动完整性未知','proxy_fidelity':'全日三色保留；绿色占比不等于旧EMA占比，价格距离复用旧公式；排名不新增信息','method_fit':'两折成熟训练，共同ETF日期权重，固定线性与浅树；来源组小须披露','conclusion_scope':'历史信息比较，不是独立未来验证或净资金收益'}.items():c['controller_review'][k]={'reason':reason,'source_refs':['docs/experiments/raw/color-gray-path-2026-10-04/brief.json']}
  d=c['research_design'];d['claim_mapping'].update(original_statement='颜色序列与价格连续表达是否有同日区分和相对既有背景的额外帮助',source_section='技术体系§2.7；实现§3.2',proxy_definition=q['added_information'],preserved_conditions=['严格原20判色','原多头排列作控制','未知非灰','原始值方向不看评价结果翻转'],omitted_conditions=['完整见黑等绿重置/到期','持仓动作','小时与日周共振'],decision_use=q['decision_use'],observation_time='t完整收盘后',tested_scope='四ETF共同连续合格日期')
  qual=build_qualification(panel,c,ROOT);p=HERE/name/'qualification.json';put(p,qual)
  d['sample_fit'].update(qualification_artifact=str(p.relative_to(ROOT)),qualification_sha256=sha256(p.read_bytes()).hexdigest(),unit='ETF×全部合格连续日',model_feature_count=len(BASELINE_FEATURES)+len(ADDED_FEATURES),paired_support=json.dumps(qual['scientific_support'],ensure_ascii=False),dependence=q['dependence'],rationale='四ETF同日分辨率低，日期和颜色段不独立',**qual['counts'])
  validate_workflow_contract(c);put(HERE/name/'draft.json',c);ledger['branches'].append({'name':name,'planned_fits':4,'qualification':str(p.relative_to(ROOT))})
put(HERE/'ledger.json',ledger);print(json.dumps(ledger,ensure_ascii=False))
