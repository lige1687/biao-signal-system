import json,unittest,sys
from pathlib import Path
from datetime import datetime,timezone
import test_order_planning
B=Path(__file__).resolve().parent
with (B/'tests-01.log').open('w') as stream:
    r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_order_planning))
x={'command':'python3 -B '+str(B/'run_checks.py'),'checked_at':datetime.now(timezone.utc).isoformat(),'tests_run':r.testsRun,'failures':[(t.id(),s) for t,s in r.failures+r.errors],'exit_code':0 if r.wasSuccessful() else 1,'scope':'new pure-order synthetic tests only; no old tests or ledger execution'}
(B/'tests-01.json').write_text(json.dumps(x,indent=2)+'\n')
(B/'synthetic-input-output-receipts.json').write_text(json.dumps(test_order_planning.RECEIPTS,default=str,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(x,indent=2));print((B/'tests-01.log').read_text());sys.exit(x['exit_code'])
