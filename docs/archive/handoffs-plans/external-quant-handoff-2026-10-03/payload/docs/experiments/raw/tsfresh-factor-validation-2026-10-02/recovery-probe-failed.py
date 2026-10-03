"""Recover one known frozen source version from disjoint later validator additions.
No shared source, contract, receipt or numerical result is rewritten.
"""
import ast,hashlib,itertools,json
from pathlib import Path
RAW=Path(__file__).resolve().parent
ROOT=RAW.parents[3]
path=Path('src/lei_signal/research/question_contract.py')
expected=json.loads((RAW/'run-joint/contract.json').read_text())['bindings']['files'][str(path)]
current=(ROOT/path).read_text()
old=(RAW/'before'/path).read_text()
# All alternatives are actual source blocks in the before/current copies.
variants=[]
for n in ast.walk(ast.parse(current)):
 if isinstance(n,ast.If) and ast.unparse(n.test)=="feature['kind'] == 'ema_only_wait_age_information'":
  variants.append((''.join(current.splitlines(True)[n.lineno-1:n.end_lineno]),''))
def feature(t):
 a=t.index('    if feature["kind"] == "ema_sma_waiting_path":\n        ref = ')
 b=t.index('    if feature["kind"] in {"slope_change_information"',a)
 return t[a:b]
variants.append((feature(current),feature(old)))
for n in ast.walk(ast.parse(current)):
 if isinstance(n,ast.If) and ("b.get('real_runs')" in ast.unparse(n.test) or
   (isinstance(n.test,ast.BoolOp) and 'waiting path freezes the two calendar phases' in ast.get_source_segment(current,n))):
  variants.append((''.join(current.splitlines(True)[n.lineno-1:n.end_lineno]),''))
variants.append(('sample["decision"] != "describe_only"','sample["decision"] != "describe"'))
variants.append(('requires decision=describe_only','requires decision=describe'))
# Individual whitelist additions may precede their full validator blocks.
parts=current.split(', "ema_only_wait_age_information"')
assert len(parts)==3
for flags in itertools.product([False,True],repeat=len(variants)+2):
 t=parts[0]+('' if flags[-2] else ', "ema_only_wait_age_information"')+parts[1]+('' if flags[-1] else ', "ema_only_wait_age_information"')+parts[2]
 for (a,b),f in zip(variants,flags):
  if f:t=t.replace(a,b)
 if hashlib.sha256(t.encode()).hexdigest()==expected:
  target=RAW/'frozen-source-copy'/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(t)
  record=dict(expected_frozen_sha256=expected,shared_source_changed=False,
   no_contract_result_or_receipt_modified=True,archive_only_variant_flags=flags,
   reason='Exact original SHA-256 recovered using actual before/current disjoint validator blocks; no outcome or receipt changes')
  (RAW/'frozen-validator-recovery.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
  print(record);break
else:raise AssertionError('No exact frozen validator recovery; publication remains blocked')
