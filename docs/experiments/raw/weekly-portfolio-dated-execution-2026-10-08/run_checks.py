"""Run only new dated tests; retain results, events and actual commands locally."""
import hashlib, json, subprocess, sys, unittest
from pathlib import Path
from datetime import datetime, timezone
import test_dated_ledger

BASE=Path(__file__).resolve().parent
names=[n for n in unittest.defaultTestLoader.getTestCaseNames(test_dated_ledger.Checks)
       if n.startswith(('test_group', 'test_repair'))]
suite=unittest.TestSuite(test_dated_ledger.Checks(n) for n in names)
with (BASE/'tests-v2-final.log').open('w') as out:
    result=unittest.TextTestRunner(stream=out,verbosity=2).run(suite)
receipt={'command':'python3 -B '+str(BASE/'run_checks.py'), 'executed_at':datetime.now(timezone.utc).isoformat(),
         'tests_run':result.testsRun, 'failures':len(result.failures),'errors':len(result.errors),
         'exit_code':0 if result.wasSuccessful() else 1,
         'trace_groups':len(test_dated_ledger.TRACES),
         'failed_checks':[(t.id(),s) for t,s in result.failures+result.errors],
         'scope':'only seven new dated groups plus four independent-review repair groups; old sealed16 and migrated16 not executed in final repair run'}
(BASE/'tests-v2-final.json').write_text(json.dumps(receipt,indent=2)+'\n')
(BASE/'event-receipts-v2-final.json').write_text(json.dumps(test_dated_ledger.TRACES,default=str,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(receipt,indent=2)); print((BASE/'tests-v2-final.log').read_text())
sys.exit(receipt['exit_code'])
