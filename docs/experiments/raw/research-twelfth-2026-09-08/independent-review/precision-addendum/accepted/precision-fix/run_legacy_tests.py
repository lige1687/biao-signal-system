"""Run the frozen ninth-batch suites against the precision-fix engine."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
NINTH = HERE.parent.parent / "research-ninth-2026-09-08" / "reference-engine"

spec = spec_from_file_location("engine", HERE / "engine.py")
engine = module_from_spec(spec)
spec.loader.exec_module(engine)
sys.modules["engine"] = engine

suite = unittest.TestSuite()
for filename in ("test_baseline.py", "test_diagnostic.py", "test_parent_review.py"):
    path = NINTH / filename
    spec = spec_from_file_location("precision_" + path.stem, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))

result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
