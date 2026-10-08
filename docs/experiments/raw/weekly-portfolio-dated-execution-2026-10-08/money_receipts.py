"""Required detailed accepted/rejected step receipts for the seven new groups.
This supplements audit detail without changing the four frozen implementation files.
"""
from copy import deepcopy
import json, unittest
from pathlib import Path
from dated_ledger import Ledger
from test_dated_ledger import Checks

BASE=Path(__file__).resolve().parent
steps=[]
original=Ledger.apply

def observed_apply(self,event):
    before=self.snapshot()
    at=before['last_at'] or before['prior_complete']['at']
    initial=self.receipt(at)
    try:
        after=original(self,event)
        steps.append({'event':deepcopy(event),'accepted':True,'before':initial,'after':after})
        return after
    except ValueError as error:
        steps.append({'event':deepcopy(event),'accepted':False,'reason':str(error),
                      'before':initial,'after':self.receipt(at),
                      'money_state_unchanged':before==self.snapshot()})
        raise

Ledger.apply=observed_apply
names=[n for n in unittest.defaultTestLoader.getTestCaseNames(Checks) if n.startswith('test_group')]
suite=unittest.TestSuite(Checks(n) for n in names)
with (BASE/'money-receipts.log').open('w') as stream:
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
Ledger.apply=original
(BASE/'event-step-money-receipts.json').write_text(json.dumps(steps,default=str,ensure_ascii=False,indent=2)+'\n')
receipt={'command':'python3 -B '+str(BASE/'money_receipts.py'),
         'reason':'supplement rejected event before/after balances missing from first audit; seven new groups only',
         'tests_run':result.testsRun,'steps':len(steps),'accepted':sum(s['accepted'] for s in steps),
         'rejected':sum(not s['accepted'] for s in steps),'exit_code':0 if result.wasSuccessful() else 1,
         'failures':[(t.id(),s) for t,s in result.failures+result.errors]}
(BASE/'money-receipts.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
raise SystemExit(receipt['exit_code'])
