"""Integrate only root-owned adapter blocks on an existing published baseline."""
from pathlib import Path
import re,json,shutil
R=Path(__file__).resolve().parents[4];D=R/'.codex/worktrees/price-volume-risk-delivery'
kinds=['risk_shape_information','session_composition_information','volume_direction_information']
assert 'volume_direction_information' not in (D/'src/lei_signal/research/workflow_inputs.py').read_text(), 'requires untouched inherited baseline; do not duplicate partial writes'
kset='{"risk_shape_information", "session_composition_information", "volume_direction_information"}'
def blocks(text,needle):
 out=[]
 for m in re.finditer(re.escape(needle),text):
  a=m.start();tail=text[a+len(needle):];end=re.search(r'^    (?:if |[A-Za-z_][A-Za-z_0-9]* ?=|return |def )',tail,re.M);z=a+len(needle)+end.start() if end else len(text);out.append(text[a:z])
 return out
for rel in ['src/lei_signal/research/workflow_inputs.py','src/lei_signal/research/question_contract.py','src/lei_signal/research/workflow.py']:
 src=(R/rel).read_text();p=D/rel;t=p.read_text()
 if rel.endswith('workflow_inputs.py'):
  add=''.join(blocks(src,f"    if contract['feature']['kind'] == '{k}':")[0] for k in kinds);pos=t.index("    if contract['feature']['kind'] == 'ema_only_wait_age_information':");t=t[:pos]+add+t[pos:]
 elif rel.endswith('question_contract.py'):
  line=next(line for line in t.splitlines(True) if 'if feature["kind"] not in {' in line);new=line.replace('}:',', '+', '.join('"'+k+'"' for k in kinds)+'}:');t=t.replace(line,new,1)
  add=''.join(blocks(src,f'    if feature["kind"] == "{k}":')[0] for k in kinds);pos=t.index('    if feature["kind"] == "tsfresh_price_information":');t=t[:pos]+add+t[pos:]
 else:
  add_bind=[];add_cache=[];add_guard=[];add_rehearsal=[]
  for k in kinds:
   for b in blocks(src,f'    if contract["feature"]["kind"] == "{k}":'):
    if 'related_code.extend' in b:add_bind.append(b)
    elif 'adapter = bindings' in b:add_cache.append(b)
   add_guard.extend(blocks(src,f'    if contract["feature"]["kind"] == "{k}" and not ('))
   for b in blocks(src,f'    if c["feature"]["kind"] == "{k}":'):
    if 'from lei_signal.research.' in b:add_rehearsal.append(b)
  pos=t.index('    if contract["feature"]["kind"] == "tsfresh_price_information":');t=t[:pos]+''.join(add_bind)+t[pos:]
  pos=t.index('    if contract["feature"]["kind"] == "ema_sma_waiting_path":',t.index('def cache_keys'));t=t[:pos]+''.join(add_cache)+t[pos:]
  pos=t.index('    bindings = actual_bindings(contract, root)',t.index('def preflight'));t=t[:pos]+''.join(add_guard)+t[pos:]
  old='    missing = sorted(set(contract["universe"]["assets"]) - set(evaluation_assets))';pos=t.index(old,t.index('    eval_rows ='))
  repl='    prediction_assets = set(contract["universe"]["assets"])\n    if contract["feature"]["kind"] in '+kset+':\n        prediction_assets.discard(contract["feature"]["anchor_asset"])\n    missing = sorted(prediction_assets - set(evaluation_assets))';t=t[:pos]+t[pos:].replace(old,repl,1)
  pos=t.index('    if count > 2000:');t=t[:pos]+'    if c["feature"]["kind"] in '+kset+':\n        count = 600  # fixed engineering fixture for root-owned new adapters\n'+t[pos:]
  lines=t.splitlines(True)
  for j,line in enumerate(lines):
   if 'elif c["feature"]["kind"] in (' in line and '"tsfresh_price_information"' in line:lines[j]=line.replace('):',', '+', '.join('"'+k+'"' for k in kinds)+'):')
  t=''.join(lines)
  add_session=next(b for b in blocks(src,'    if c["feature"]["kind"] == "session_composition_information":') if 'row["open"]' in b)
  pos=t.index('    payload = {"data_mode": "synthetic"');t=t[:pos]+add_session+t[pos:]
  pos=t.index('    c["question"].update(sampling="daily"',t.index('def run_rehearsal'));t=t[:pos]+'    if c["feature"]["kind"] in '+kset+':\n        c["feature"]["anchor_asset"] = assets[0]\n'+t[pos:]
  pos=t.index('    c["calendar"] = dates',t.index('def run_rehearsal'));t=t[:pos]+'    if c["feature"]["kind"] in '+kset+':\n        c["split"]["evaluation_label_policy"] = "contained"\n'+t[pos:]
  pos=t.index('    if c["feature"]["kind"] == "green_black_state60_information":',t.index('    result = evaluate_observations',t.index('def run_rehearsal')));t=t[:pos]+''.join(add_rehearsal)+t[pos:]
 p.write_text(t)
for f in ['src/lei_signal/research/'+k+'.py' for k in kinds]+['tests/unit/test_'+k+'.py' for k in kinds]:
 (D/f).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/f,D/f)
rel='docs/research/definitions.v1.json';a=json.loads((R/rel).read_text());b=json.loads((D/rel).read_text());own=[o for o in a['objects'] if o['id'] in ['research.risk.vol_instability20','research.risk.beta_asymmetry60','research.risk.negative_cluster60','research.price.overnight_minus_intraday20','research.volume.direction_excess20']];assert len(own)==5
ids={o['id'] for o in b['objects']};assert not ids & {o['id'] for o in own};b['objects'].extend(own)
for o in own:
 for key in o['sources']:
  val=a['sources'][key]
  if key in b['sources']:assert b['sources'][key]==val
  else:b['sources'][key]=val
b['changelog'].append({'date':'2026-10-04','change':'Append root-owned3 risk cards and session/volume research cards; preserve inherited definitions'});(D/rel).write_text(json.dumps(b,ensure_ascii=False,indent=2)+'\n')
print('Own adapters/hooks/cards integrated; no market experiments')
