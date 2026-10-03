"""Bounded native AlphaGen component audit; no upstream implementation vendored.

Supplies already evaluated artificial arrays via the upstream abstract interface.
This does not test native formula evaluation, RL, or a market-data workflow.
"""
import argparse
import datetime as dt
import hashlib
import importlib.metadata as md
import json
import os
from pathlib import Path
import platform
import sys
import time


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    root = args.upstream.resolve()
    if args.output.exists():
        raise SystemExit("Refusing to overwrite saved evidence")
    expected = json.loads((here / "upstream-files.sha256.json").read_text())
    assert all(sha(root / name) == digest for name, digest in expected.items())
    started = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat()
    clock = time.monotonic()
    # Prevent bytecode writes into the unmodified upstream snapshot.
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(root))
    import torch
    import pandas as pd
    from alphagen.data.calculator import TensorAlphaCalculator
    from alphagen.data.expression import Feature
    from alphagen.models.linear_alpha_pool import MseAlphaPool
    from alphagen_qlib.stock_data import FeatureType, StockData

    class Arrays(TensorAlphaCalculator):
        """Only the two methods required by the native array interface."""
        def __init__(self, values, target):
            super().__init__(target)
            self.values = values

        @property
        def n_days(self):
            return self.target.shape[0]

        def evaluate_alpha(self, expr):
            return self.values[str(expr)]

    dtype = torch.float64
    x = torch.tensor([[-1, -1, 1, 1]] * 3, dtype=dtype)
    z = torch.tensor([[-1, 1, -1, 1]] * 3, dtype=dtype)
    target = (x + z) / (2 ** 0.5)
    calculator = Arrays({"$close": x, "$open": z, "$high": x, "$low": -x}, target)
    pool = MseAlphaPool(capacity=4, calculator=calculator, l1_alpha=0,
                        device=torch.device("cpu"))
    transitions = []
    for kind in [FeatureType.CLOSE, FeatureType.OPEN, FeatureType.HIGH, FeatureType.LOW]:
        expr = Feature(kind)
        value = pool.try_new_expr(expr)
        transitions.append({"candidate": str(expr), "returned_objective": value,
                            "size": pool.size, "eval_cnt": pool.eval_cnt,
                            "current_ic": pool.evaluate_ensemble(),
                            "best_ic": pool.best_ic_ret, "json": pool.to_json_dict()})
    time_vector = torch.tensor([[1], [2], [3], [4]], dtype=dtype)
    semantic = []
    for name, values in [("one_instrument", time_vector),
                         ("common_signal_four_instruments", time_vector.repeat(1, 4))]:
        calc = Arrays({"$close": values}, values)
        semantic.append({"case": name, "input": values.tolist(),
                         "target": values.tolist(),
                         "native_ic": calc.calc_single_IC_ret(Feature(FeatureType.CLOSE))})

    # Controlled constructor precondition test; do not initialize a present Qlib.
    import importlib.util
    if importlib.util.find_spec("qlib") is None:
        try:
            StockData(instrument=["synthetic"], start_time="2020-01-01", end_time="2020-01-04",
                      max_backtrack_days=0, max_future_days=0, device=torch.device("cpu"),
                      preloaded_data=(torch.zeros((4, 6, 1), dtype=dtype),
                                      pd.date_range("2020-01-01", periods=4), pd.Index(["synthetic"])))
        except ModuleNotFoundError as exc:
            constructor = {"status": "blocked", "exception": type(exc).__name__,
                           "missing_module": exc.name, "message": str(exc)}
        else:
            constructor = {"status": "unexpected_success"}
    else:
        constructor = {"status": "not_executed", "reason": "Qlib present; no service initialization authorized by this probe"}
    unchanged = all(sha(root / name) == digest for name, digest in expected.items())
    receipt = {"started_at": started,
               "finished_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),
               "elapsed_seconds": time.monotonic() - clock, "pid": os.getpid(),
               "python": platform.python_version(), "platform": platform.platform(),
               "dependencies": {name: md.version(name) for name in ["torch", "numpy", "pandas"]},
               "protocol_sha256": sha(here / "protocol.json"), "runner_sha256": sha(Path(__file__)),
               "upstream_commit": "259687e8f316994426416c530a94842a2fe6405e",
               "upstream_source_unchanged": unchanged,
               "inputs": {"x": x.tolist(), "z": z.tolist(), "target": target.tolist()},
               "pool_transitions": transitions, "semantic_cases": semantic,
               "stock_data_precondition": constructor,
               "budget": {"core_batches": 1, "try_new_expr_calls": 4,
                          "native_lstsq_calls_inferred_from_accepted_transitions": 2,
                          "market_fits": 0, "rl_training_steps": 0, "external_model_calls": 0}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    assert unchanged
    print(json.dumps({"output": str(args.output), "sizes": [v["size"] for v in transitions],
                      "ics": [v["current_ic"] for v in transitions],
                      "semantic_ics": [v["native_ic"] for v in semantic],
                      "stock_data": constructor, "elapsed_seconds": receipt["elapsed_seconds"]}))


if __name__ == "__main__":
    main()
