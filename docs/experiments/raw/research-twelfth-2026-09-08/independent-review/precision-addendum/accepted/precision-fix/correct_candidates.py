"""Correct decimal >=3 qualification without changing any source or price field."""
from pathlib import Path
from decimal import Decimal
from datetime import datetime,timezone
import json,gzip,hashlib,copy,math
P=Path(__file__).resolve().parent; BASE=P.parent
D=lambda x:Decimal(str(x))
def save(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def qualify(ref,stop,target):
 if stop is None or not math.isfinite(stop) or stop>=ref or stop<=0:return None,False,'invalid_structure_risk'
 if target is None or not math.isfinite(target) or target<=ref:return None,False,'target_unavailable'
 reward=D(target)-D(ref);risk=D(ref)-D(stop)
 ok=reward>=3*risk
 return float(reward/risk),ok,None if ok else 'signal_reward_risk_below_3'
def main():
 assert not (P/'candidates.json.gz').exists()
 fs=[Path(__file__),P/'protocol.md',BASE/'adapter/candidates.json.gz',BASE/'adapter/completion.json']
 lock={str(f.resolve()):sha(f) for f in fs};save(P/'candidate-lock.json',dict(started_at_utc=datetime.now(timezone.utc).isoformat(),files=lock))
 with gzip.open(BASE/'adapter/candidates.json.gz','rt') as f:old=json.load(f)
 rows=copy.deepcopy(old);checks=[];diff=[]
 for before,c in zip(old,rows):
  rr,ok,reason=qualify(c['signal_ref'],c['stop'],c['target'])
  ref=c['config_id'].startswith('REF_')
  if ref:assert (ok,reason)==(c['signal_accepted'],c['signal_reject_reason']),c['candidate_id']
  else:c.update(signal_rr=rr,signal_accepted=ok,signal_reject_reason=reason)
  changed={k:{'before':before[k],'after':c[k]} for k in c if c[k]!=before[k]}
  assert set(changed)<={'signal_rr','signal_accepted','signal_reject_reason'}
  if changed:diff.append(dict(candidate_id=c['candidate_id'],changes=changed))
  checks.append(dict(candidate_id=c['candidate_id'],decimal_rr=rr,decision_unchanged=ok==before['signal_accepted'],reference_preserved=ref))
 changed_decisions=[c for c in checks if not c['decision_unchanged']]
 assert {c['candidate_id'] for c in changed_decisions}=={'A20E:first_ma_pullback:64e8c7322fdea81bccfdf858','A20J:first_ma_pullback:5dfc14dc6e284f6f8b6b9c36'}
 with gzip.open(P/'candidates.json.gz','wt') as f:json.dump(rows,f,ensure_ascii=False,allow_nan=False)
 save(P/'candidate-checks.json',checks);save(P/'candidate-differences.json',diff)
 assert all(sha(Path(f))==h for f,h in lock.items())
 save(P/'candidate-completion.json',dict(total=len(rows),source_acd=891,references_unchanged=1742,changed_decisions=changed_decisions,numeric_display_rows_changed=sum('signal_rr' in d['changes'] for d in diff),accepted_before=sum(c['signal_accepted'] for c in old),accepted_after=sum(c['signal_accepted'] for c in rows),all_source_price_and_metadata_unchanged=True,all_input_hashes_unchanged=True,candidates_sha256=sha(P/'candidates.json.gz')))
 print((P/'candidate-completion.json').read_text())
if __name__=='__main__':main()
