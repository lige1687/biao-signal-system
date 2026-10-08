"""Run only independent-review minimal counterexamples against exact v1 copy."""
import sys,json
from pathlib import Path
from decimal import Decimal as D
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'v1-source'))
from synthetic_fixtures import *
from dated_ledger import Ledger

observations=[]
# Known required action omitted: old support incorrectly accepts direct sale.
c=calendar(price=1); split(c)
l=ledger(lots=[lot()],c=c,marks={'A':D(2)})
r=l.apply(trade('sell','skip-split'))
assert r['equity']=='100' and l.shares('A')==0
observations.append({'finding':'R1','v1_wrongly_accepted':True,'receipt':r,
                     'correct_equity':'200','missing_required_action':'08:00 split2x'})
# Known Jan2 complete close omitted: old deposit uses Jan1 NAV .2.
c=calendar(); c['closes'][CLOSE]['A']=D(3)
l=ledger(lots=[lot()],c=c,nav='.2',marks={'A':D(3)})
r=l.apply(event('deposit','stale-nav',t(3,'00:00:00'),amount=100))
assert l.snapshot()['units']==1500
observations.append({'finding':'R2','v1_wrongly_accepted':True,'receipt':r,
                     'valuation_at_bound_close':'3','wrong_units':'1500',
                     'correct_units':str(D(1000)+D(100)/D('.3'))})
# A same-date 15:00 release is accepted in v1 without permitted exception.
c=calendar(release=CLOSE)
c['clocks'][CLOSE]=[3,4]; c['opens'][CLOSE]=dict(c['opens'][O])
l=ledger(cash=200,c=c); l.apply(trade('buy','same-day-buy'))
r=l.apply(trade('sell','same-day-sell',CLOSE))
assert l.shares('A')==0
observations.append({'finding':'R3','v1_wrongly_accepted':True,'receipt':r,
                     'release_at':CLOSE,'correct_behavior':'reject buy with same-local-date release'})
result={'command':'python3 -B '+str(BASE/'prove_v1_failures.py'),'exit_code':0,
        'scope':'3 targeted v1 counterexamples; old sealed16 and new23 not rerun',
        'expected_old_defects_reproduced':3,'observations':observations}
(BASE/'v1-independent-failure-reproductions.json').write_text(json.dumps(result,default=str,indent=2)+'\n')
print(json.dumps(result,default=str,indent=2))
