"""Create the bounded extension drafts from the archived, corrected design."""
import json,copy,hashlib
from pathlib import Path
from lei_signal.research.color_continuous_eight_etf import build_qualification,ASSETS,BASELINE_FEATURES,DEFINITION_REF
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def read(p):return json.loads(p.read_text())
def put(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
panel=read(HERE/'workflow-input.local.json');source=read(HERE/'source-manifest.json')
for method in ['ridge','lightgbm']:
 for target in ['forward_return','mae']:
  branch=method+'-'+target;out=HERE/'continuous'/branch;out.mkdir(parents=True,exist_ok=True)
  c=read(ROOT/'docs/experiments/raw/color-gray-path-2026-10-04/continuous'/branch/'accepted-draft.json')
  q=c['question'];qid='color-sector-'+branch+'-2026-10-05';q.update(question_id=qid,hypothesis_family=qid,factor_refs=[DEFINITION_REF],universe=list(ASSETS),trial_history='new fixed8ETF extension16fits; previous fourETF32fits retained, no tuning; all history seen',sources={'panel':sha(HERE/'workflow-input.local.json')})
  c['data']={'path':str((HERE/'workflow-input.local.json').relative_to(ROOT)),'sha256':sha(HERE/'workflow-input.local.json'),'mode':'historical_reconstruction','qualification':{'adapter':'color_eight_etf_economic/1.0','manifest_path':str((HERE/'source-manifest.json').relative_to(ROOT)),'manifest_sha256':sha(HERE/'source-manifest.json')}}
  c['universe'].update(assets=list(ASSETS),rationale='fixed4broad+4sector retrospectively qualified; not fullpopulation or trade',identity_basis='existing data-owner source-bound economic OHLC, missing dates reset; actual availability/completeness unknown')
  c['feature'].update(kind='color_continuous_eight_etf',definition_ref=DEFINITION_REF)
  c['evaluator']['baseline_features']=list(BASELINE_FEATURES)
  c['budget']['max_rows']=12000
  c['history']={'family':qid,'changed_after_results_reason':'User-authorized new universe extension; formulas/settings unchanged after earlier fourETF evidence; explicitly exploratory'}
  c['publication'].update(report_path='docs/experiments/'+qid+'.md')
  c['sources']=[{'path':str((HERE/'source-manifest.json').relative_to(ROOT)),'sha256':sha(HERE/'source-manifest.json')},{'path':str((HERE/'brief.json').relative_to(ROOT)),'sha256':sha(HERE/'brief.json')}]+source['files']+[source['owner_qualification']]+[s for s in c['sources'] if 'strategy-source-snapshots' in s['path']]
  for v in c['controller_review'].values():v['source_refs']=[str((HERE/'brief.json').relative_to(ROOT))]
  c['controller_review']['universe_fit']['reason']='8fixedETFs; broad/sector and gaps explicitly qualified; evidence not whole ETF population'
  cm=c['research_design']['claim_mapping'];cm.update(tested_scope='fixed eight ETF qualified daily records',application_scope='trend_road_information')
  qual=build_qualification(panel,c,ROOT);put(out/'qualification.json',qual)
  c['research_design']['sample_fit'].update(qualification_artifact=str((out/'qualification.json').relative_to(ROOT)),qualification_sha256=sha(out/'qualification.json'),assets=8,observations=qual['counts']['observations'],dates=qual['counts']['dates'],paired_support=json.dumps(qual['scientific_support'],ensure_ascii=False),model_feature_count=len(BASELINE_FEATURES)+3,rationale='fixed8 small historical pool; missing days reset; counts are not independent outcomes')
  put(out/'draft.json',c)
print('4 drafts; X-only qualification saved; no fits or labels')
