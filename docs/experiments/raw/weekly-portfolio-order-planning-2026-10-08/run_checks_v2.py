import json, unittest, sys, shutil
from pathlib import Path
from datetime import datetime, timezone
import test_order_planning_v2

B = Path(__file__).resolve().parent

def save(name, data):
    free = shutil.disk_usage(B).free
    if free < len(data.encode()) + 1000000:
        raise OSError('insufficient space for small receipt: ' + name)
    p = B / name
    p.write_text(data)
    assert p.read_text() == data


# Buffer tests in memory. No implicit shell or tempfile writes.
from io import StringIO
out = StringIO()
r = unittest.TextTestRunner(stream=out, verbosity=2).run(
    unittest.defaultTestLoader.loadTestsFromModule(test_order_planning_v2))
x = {'command': 'python3 -B ' + str(B / 'run_checks_v2.py'),
     'checked_at': datetime.now(timezone.utc).isoformat(), 'tests_run': r.testsRun,
     'failures': [(t.id(), s) for t, s in r.failures + r.errors],
     'exit_code': 0 if r.wasSuccessful() else 1,
     'scope': 'three repair counterexamples and legal counterparts plus related pure checks only; no old test reruns'}
save('tests-v2-01.log', out.getvalue())
save('tests-v2-01.json', json.dumps(x, indent=2) + '\n')
save('synthetic-receipts-v2.json', json.dumps(test_order_planning_v2.RECEIPTS,
                                          default=str, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(x, indent=2)); print(out.getvalue()); sys.exit(x['exit_code'])
