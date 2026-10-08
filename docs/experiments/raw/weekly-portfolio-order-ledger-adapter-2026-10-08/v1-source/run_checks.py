from pathlib import Path
from io import StringIO
from datetime import datetime, timezone
import unittest, json, shutil, sys
import test_adapter

B = Path(__file__).resolve().parent

def save(name, data):
    if shutil.disk_usage(B).free < len(data.encode()) + 1000000:
        raise OSError('insufficient space for small adapter receipt: ' + name)
    p = B / name; p.write_text(data); assert p.read_text() == data

out = StringIO()
r = unittest.TextTestRunner(stream=out, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(test_adapter))
x = {'command': 'python3 -B ' + str(B / 'run_checks.py'), 'checked_at': datetime.now(timezone.utc).isoformat(),
     'tests_run': r.testsRun, 'failures': [(t.id(), s) for t, s in r.failures+r.errors],
     'exit_code': 0 if r.wasSuccessful() else 1,
     'scope': 'new named synthetic account adapter checks only; no old tests or market workflow'}
save('tests-04.log', out.getvalue()); save('tests-04.json', json.dumps(x, indent=2)+'\n')
save('attempt-and-calendar-receipts-04.json', json.dumps(test_adapter.RECEIPTS, default=str, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(x, indent=2)); print(out.getvalue()); sys.exit(x['exit_code'])
