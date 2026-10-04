from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from lei_signal.research.bull_gray_origin_information import BASELINE_FEATURES,ADDED_FEATURES,DEFINITION_REF,build_qualification
from lei_signal.research.lightgbm_information import PARAMETERS,NUM_BOOST_ROUND,PACKAGE_VERSION,runtime_fingerprint
from lei_signal.research.question_contract import validate_workflow_contract
ROOT=Path(__file__).resolve().parents[5]; HERE=Path(__file__).resolve().parent
panel=json.loads((ROOT/'docs/experiments/raw/volume-information-2026-09-30/execution/panel.json').read_text())
prior=json.loads((ROOT/'docs/experiments/raw/color-event-universe-2026-10-04/core/green-return20/freeze-01/contract.json').read_text())
def put(p,x):
 p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
ledger={'maximum_real_fits':16,'actual_real_fits':0,'branches':[],'history':'Separate gray-origin question; old color-event16 fits retained. Added continuous question has separate16; no grid.'}
for method in ['prediction_ridge','prediction_lightgbm']:
 for target in ['forward_return','mae']:
  name=method.removeprefix('prediction_')+'-'+target;c=deepcopy(prior)
  for k in ['bindings','freeze','rehearsal','calendar']:c.pop(k,None)
  c['feature']={'kind':'bull_gray_origin_information','lookback':20,'bar_frequency':'daily_quote','warmup':252,'missing_policy':'segmented','definition_ref':DEFINITION_REF}
  c['target']['kind']=target
  q=c['question'];q.pop('event_definition',None)
  q.update(question_id='bull-gray-origin-'+name+'-2026-10-04',hypothesis_family='bull-gray-origin-'+name+'-2026-10-04',factor_refs=[DEFINITION_REF],sampling='daily',joint_structure='同日ETF共同波动、连续灰色和20间隔结果重叠',baseline='成熟每ETF均值；固定价格距离/既有涨跌波动/当下灰日龄与几何/组距/ETF身份',added_information='当前多头灰色进入时的此前明确方向，黑1绿0未知排除',added_information_reason='历史路径表达，是否补充指定基线须检验；不预设黑必跌',decision_use='辅助判断多头灰色等待中未来收益和风险，非完整交易',method={'name':method,'reason':'固定线性lambda1与40轮depth2浅树；不调参'},trial_history='两目标两方法两折两模型16拟合；全部行情已见；连续表达另批16不混算',auxiliary_metrics=['每ETF及来源成熟历史均值','逐期逐ETF、去一ETF、日期同步20/60日块1000次','全3x3路径计数，未结束路径保留'],dependence='完整评价交易日历同步20/60日块，灰日/ETF行不独立')
  q['target'].update(kind=target,price_basis='close_to_close' if target=='forward_return' else 'close_to_close_path')
  e={'kind':method,'version':'1.0.0','baseline_features':list(BASELINE_FEATURES),'added_features':list(ADDED_FEATURES),'minimum_training_rows':40}
  if method=='prediction_ridge':e['lambda']=1.0
  else:e.update(parameters=PARAMETERS,num_boost_round=NUM_BOOST_ROUND,package_version=PACKAGE_VERSION,runtime=runtime_fingerprint())
  c['evaluator']=e;c['history']={'family':q['hypothesis_family'],'changed_after_results_reason':'New bounded gray-origin question; no new outcome read before freeze; historical exploration','ledger_path':'docs/experiments/raw/research-workflow-ledgers-2026-09-29/'+sha256(q['hypothesis_family'].encode()).hexdigest()[:24]+'/attempts.jsonl'}
  c['publication']={'report_path':'docs/experiments/color-gray-'+name+'-2026-10-04.md','category':'模块与信号','claimed_scope':'partial','conclusion':'not_supported'}
  for k,reason in {'universe_fit':'四ETF有限回顾资料；真实到达/行动完整性未知','proxy_fidelity':'当前多头灰，保留所有来源明确日期；此前颜色可形成于非多头组，非等待重置交易规则','method_fit':'两折成熟训练，共同ETF日期权重，固定线性与浅树；来源组小须披露','conclusion_scope':'历史信息比较，不是独立未来验证或净资金收益'}.items():c['controller_review'][k]={'reason':reason,'source_refs':['docs/experiments/raw/color-gray-path-2026-10-04/brief.json']}
  d=c['research_design'];d['claim_mapping'].update(original_statement='颜色是趋势描述，检验当前多头灰的先前方向能否相对基线有帮助',source_section='技术体系§2.7；实现§3.2',proxy_definition=q['added_information'],preserved_conditions=['严格原20判色','原多头排列','未知非灰','未结束路径保留'],omitted_conditions=['完整见黑等绿重置/到期','持仓动作','小时与日周共振'],decision_use=q['decision_use'],observation_time='t完整收盘后',tested_scope='四ETF当前多头灰日期')
  qual=build_qualification(panel,c,ROOT);p=HERE/name/'qualification.json';put(p,qual)
  d['sample_fit'].update(qualification_artifact=str(p.relative_to(ROOT)),qualification_sha256=sha256(p.read_bytes()).hexdigest(),unit='ETF×当前多头灰日',model_feature_count=len(BASELINE_FEATURES)+len(ADDED_FEATURES),paired_support=json.dumps(qual['scientific_support'],ensure_ascii=False),dependence=q['dependence'],rationale='小样本条件研究，不宣称颜色段独立',**qual['counts'])
  validate_workflow_contract(c);put(HERE/name/'draft.json',c);ledger['branches'].append({'name':name,'planned_fits':4,'qualification':str(p.relative_to(ROOT))})
put(HERE/'ledger.json',ledger);print(json.dumps(ledger,ensure_ascii=False))
