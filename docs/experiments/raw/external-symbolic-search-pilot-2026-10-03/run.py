"""Frozen, synthetic symbolic-search comparison. No market input or model API."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib.metadata
import json
import math
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
PROTOCOL = HERE / "protocol.json"
EXPECTED_PROTOCOL_SHA = "8e4088da68500f765d0a95b277630c2109f1033dd8ab0a727f097f337d1f50ff"
SPLITS = ("train", "validation", "test", "outside_range")
TASKS = ("additive", "rational", "noise")
ARMS = ("external", "random_control", "direct_baseline")
INVALID_SCORE = 1e30


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def array_hash(a: np.ndarray) -> str:
    a = np.asarray(a, dtype="<f8", order="C")
    return digest_bytes(a.tobytes())


def read_protocol() -> dict:
    raw = PROTOCOL.read_bytes()
    if digest_bytes(raw) != EXPECTED_PROTOCOL_SHA:
        raise ValueError("frozen protocol SHA256 differs")
    return json.loads(raw)


def protected_divide(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    with np.errstate(all="ignore"):
        return np.where(np.abs(b) > 1e-6, np.divide(a, b), 1.0)


def formula_predict(expression: str, x: np.ndarray) -> np.ndarray:
    """Independent, restricted AST interpreter; never eval an exported formula."""
    functions = {
        "add": np.add,
        "sub": np.subtract,
        "mul": np.multiply,
        "protected_divide": protected_divide,
    }

    def visit(node: ast.AST) -> np.ndarray | float:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in functions:
                raise ValueError("forbidden function")
            if node.keywords or len(node.args) != 2:
                raise ValueError("invalid function arguments")
            with np.errstate(all="ignore"):
                return functions[node.func.id](visit(node.args[0]), visit(node.args[1]))
        if isinstance(node, ast.Name) and node.id in {f"x{i}" for i in range(4)}:
            return x[:, int(node.id[1])]
        if isinstance(node, ast.Constant) and type(node.value) is float and node.value == 1.0:
            return 1.0
        raise ValueError("forbidden AST node")

    result = np.asarray(visit(ast.parse(expression, mode="eval")), dtype=np.float64)
    if result.ndim == 0:
        result = np.full(len(x), float(result))
    if result.shape != (len(x),):
        raise ValueError("prediction shape mismatch")
    return result


def valid_prediction(yhat: np.ndarray) -> bool:
    return bool(np.all(np.isfinite(yhat)) and np.all(np.abs(yhat) <= 1e6))


def mse(y: np.ndarray, yhat: np.ndarray) -> float:
    if not valid_prediction(yhat):
        return INVALID_SCORE
    return float(np.mean(np.square(y - yhat)))


def make_inputs(p: dict) -> dict[str, dict[str, np.ndarray]]:
    d = p["data"]
    result = {}
    for split in SPLITS:
        rng = np.random.default_rng(d["seeds"][split])
        n = d["rows"][split]
        if split == "outside_range":
            chunks = []
            count = 0
            while count < n:
                draw = rng.uniform(*d["outside_range"], size=(n, d["features"]))
                draw = draw[np.any(np.abs(draw) > d["normal_range"][1], axis=1)]
                chunks.append(draw)
                count += len(draw)
            x = np.concatenate(chunks)[:n]
        else:
            x = rng.uniform(*d["normal_range"], size=(n, d["features"]))
        result[split] = {}
        for task_index, task in enumerate(TASKS):
            noise_seed = d["seeds"][split] + d["target_seed_offset"] + task_index * 10000
            noise = np.random.default_rng(noise_seed)
            if task == "additive":
                y = x[:, 0] + 2 * x[:, 1] - x[:, 2] + noise.normal(0, 0.05, n)
            elif task == "rational":
                y = x[:, 0] / (1 + x[:, 1] ** 2) + x[:, 2] + noise.normal(0, 0.05, n)
            else:
                y = noise.normal(0, 1, n)
            result[split][task] = {"x": x, "y": y}
    return result


def feature_specs() -> list[dict]:
    specs = []
    for total in range(1, 4):
        for a in range(total + 1):
            for b in range(total - a + 1):
                for c in range(total - a - b + 1):
                    exponents = (a, b, c, total - a - b - c)
                    specs.append({"kind": "monomial", "powers": exponents})
    for i in range(4):
        for j in range(4):
            specs.append({"kind": "rational", "i": i, "j": j})
    return specs


def feature_matrix(x: np.ndarray, specs: list[dict]) -> np.ndarray:
    cols = []
    for spec in specs:
        if spec["kind"] == "monomial":
            cols.append(np.prod(x ** np.asarray(spec["powers"]), axis=1))
        elif spec["kind"] == "rational":
            cols.append(x[:, spec["i"]] / (1 + x[:, spec["j"]] ** 2))
        else:
            raise ValueError("invalid direct feature")
    return np.column_stack(cols) if cols else np.empty((len(x), 0))


def fit_columns(y: np.ndarray, matrix: np.ndarray, indexes: list[int]) -> np.ndarray:
    design = np.column_stack([np.ones(len(y)), matrix[:, indexes]])
    return np.linalg.lstsq(design, y, rcond=None)[0]


def direct_predict(x: np.ndarray, model: dict) -> np.ndarray:
    matrix = feature_matrix(x, model["specs"])
    return np.column_stack([np.ones(len(x)), matrix]) @ np.asarray(model["coefficients"])


def direct_baseline(train: dict, validation: dict) -> tuple[dict, dict]:
    """Fixed strong direct comparator; all fits and choices use train/validation only."""
    x, y = train["x"], train["y"]
    all_specs = feature_specs()
    all_matrix = feature_matrix(x, all_specs)
    val_matrix = feature_matrix(validation["x"], all_specs)
    variants = []
    fit_count = 0

    def add_variant(label: str, indexes: list[int], coefficients: np.ndarray) -> None:
        model = {"label": label, "specs": [all_specs[i] for i in indexes],
                 "coefficients": coefficients.tolist()}
        yhat = np.column_stack([np.ones(len(validation["y"])), val_matrix[:, indexes]]) @ coefficients
        variants.append((mse(validation["y"], yhat), model))

    add_variant("training_mean", [], np.array([float(np.mean(y))]))
    degree1 = [i for i, s in enumerate(all_specs) if s["kind"] == "monomial" and sum(s["powers"]) == 1]
    degree3 = [i for i, s in enumerate(all_specs) if s["kind"] == "monomial"]
    for label, indexes in (("linear", degree1), ("polynomial_degree3", degree3)):
        add_variant(label, indexes, fit_columns(y, all_matrix, indexes))
        fit_count += 1
    selected = []
    remaining = set(range(len(all_specs)))
    centered = all_matrix - np.mean(all_matrix, axis=0)
    norms = np.linalg.norm(centered, axis=0)
    residual = y - np.mean(y)
    for size in range(1, 5):
        eligible = [i for i in sorted(remaining) if norms[i] > 0]
        if not eligible:
            break
        # OMP chooses the feature with highest residual correlation after
        # centering and unit-norm scaling, then refits all selected columns.
        index = min(eligible, key=lambda i: (-abs(float(centered[:, i] @ residual / norms[i])), i))
        selected.append(index)
        remaining.remove(index)
        coeffs = fit_columns(y, all_matrix, selected)
        fit_count += 1
        residual = y - np.column_stack([np.ones(len(y)), all_matrix[:, selected]]) @ coeffs
        add_variant(f"omp_{size}", selected[:], coeffs)
    # Validation selects the model family and OMP size; ties use fixed insertion order.
    validation_mse, chosen = min(variants, key=lambda item: item[0])
    return chosen, {"fit_count": fit_count, "mean_estimate_count": 1,
                    "variants_validation_mse":
                    {model["label"]: score for score, model in variants},
                    "selected_validation_mse": validation_mse}


def make_pset(gp):
    pset = gp.PrimitiveSet("MAIN", 4)
    pset.renameArguments(ARG0="x0", ARG1="x1", ARG2="x2", ARG3="x3")
    for name, function in (("add", np.add), ("sub", np.subtract),
                           ("mul", np.multiply), ("protected_divide", protected_divide)):
        pset.addPrimitive(function, 2, name=name)
    pset.addTerminal(1.0)
    return pset


def search_arm(base, gp, tools, creator, pset, train: dict, seed: int, p: dict,
               arm: str, deadline: float, accounting: dict) -> dict:
    s = p["search"]
    random.seed(seed)
    toolbox = base.Toolbox()
    toolbox.register("tree", gp.genHalfAndHalf, pset=pset,
                     min_=s["initial_depth"][0], max_=s["initial_depth"][1])
    toolbox.register("individual", tools.initIterate, creator.PilotIndividual, toolbox.tree)
    toolbox.register("select", tools.selTournament, tournsize=s["tournament_size"])
    toolbox.register("mate", gp.cxOnePoint)
    toolbox.register("expr_mut", gp.genHalfAndHalf, min_=s["mutation_depth"][0],
                     max_=s["mutation_depth"][1])
    toolbox.register("mutate", gp.mutUniform, expr=toolbox.expr_mut, pset=pset)
    population = [toolbox.individual() for _ in range(s["population"])]
    invalid_count = rejected_count = 0
    evaluations = 0
    best = None

    def evaluate_population(current: list) -> None:
        nonlocal invalid_count, evaluations, best
        for individual in current:
            if time.monotonic() > deadline:
                raise TimeoutError("frozen 600-second search wall cap reached")
            expression = str(individual)
            try:
                compiled = gp.compile(individual, pset)
                raw_prediction = compiled(*(train["x"][:, i] for i in range(4)))
                prediction = np.asarray(raw_prediction, dtype=np.float64)
                if prediction.ndim == 0:
                    prediction = np.full(len(train["y"]), float(prediction))
                if prediction.shape != train["y"].shape:
                    raise ValueError("prediction shape mismatch")
                invalid = not valid_prediction(prediction)
                score = mse(train["y"], prediction)
            except (ValueError, OverflowError, FloatingPointError):
                invalid, score = True, INVALID_SCORE
            if invalid:
                invalid_count += 1
            fitness = score + s["penalty_per_node"] * len(individual)
            individual.fitness.values = (fitness,)
            evaluations += 1
            accounting["used_search_evaluations"] += 1
            if best is None or fitness < best[0]:
                best = (fitness, expression, len(individual), individual.height)

    evaluate_population(population)
    if arm == "external":
        for _ in range(s["generations"]):
            elite = toolbox.clone(tools.selBest(population, 1)[0])
            children = [toolbox.clone(i) for i in toolbox.select(population, s["population"] - 1)]
            for i in range(0, len(children) - 1, 2):
                if random.random() < s["crossover_probability"]:
                    before = (toolbox.clone(children[i]), toolbox.clone(children[i + 1]))
                    a, b = toolbox.mate(children[i], children[i + 1])
                    children[i] = a if len(a) <= p["grammar"]["max_nodes"] and a.height <= p["grammar"]["max_height"] else before[0]
                    children[i + 1] = b if len(b) <= p["grammar"]["max_nodes"] and b.height <= p["grammar"]["max_height"] else before[1]
                    rejected_count += int(children[i] is before[0]) + int(children[i + 1] is before[1])
            for i, child in enumerate(children):
                if random.random() < s["mutation_probability"]:
                    before = toolbox.clone(child)
                    candidate, = toolbox.mutate(child)
                    if len(candidate) <= p["grammar"]["max_nodes"] and candidate.height <= p["grammar"]["max_height"]:
                        children[i] = candidate
                    else:
                        children[i] = before
                        rejected_count += 1
            population = [elite] + children
            evaluate_population(population)
    else:
        # Shared DEAP tree representation, but independent draws and no evolution.
        for _ in range(s["generations"]):
            population = [toolbox.individual() for _ in range(s["population"])]
            evaluate_population(population)
    if evaluations != s["evaluation_cap_per_arm_task_seed"]:
        raise AssertionError("incorrect candidate evaluation count")
    assert best is not None
    return {"expression": best[1], "train_fitness": best[0], "nodes": best[2],
            "height": best[3], "evaluation_count": evaluations,
            "invalid_count": invalid_count, "rejected_proposal_count": rejected_count}


def json_write(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def output_data(p: dict) -> tuple[dict, dict]:
    inputs = make_inputs(p)
    fingerprints = {split: {task: {"x_sha256": array_hash(record["x"]),
                                    "y_sha256": array_hash(record["y"]),
                                    "rows": len(record["y"])}
                            for task, record in inputs[split].items()} for split in SPLITS}
    return inputs, fingerprints


def local_time() -> str:
    return datetime.now().astimezone().isoformat()


def run(output: Path) -> None:
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("output directory must be empty")
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    started_at = local_time()
    json_write(output / "command-receipts.json", {"status": "running", "pid": os.getpid(),
               "started_at": started_at, "model_calls": "unmetered/unknown"})
    try:
        _run_comparison(output, started, started_at)
    except Exception as exc:
        receipt = json.loads((output / "command-receipts.json").read_text())
        if receipt["status"] != "failed":
            json_write(output / "command-receipts.json", {"status": "failed",
                       "pid": os.getpid(), "started_at": started_at, "ended_at": local_time(),
                       "error_type": type(exc).__name__, "error": str(exc),
                       "completed_runs": 0, "used_search_evaluations": 0,
                       "direct_fit_count": 0, "wall_seconds": time.monotonic() - started,
                       "model_calls": "unmetered/unknown"})
        raise


def _run_comparison(output: Path, started: float, started_at: str) -> None:
    p = read_protocol()
    deadline = started + p["budget"]["wall_seconds_search_hard_cap"]
    inputs, fingerprints = output_data(p)
    json_write(output / "input-fingerprints.json", fingerprints)
    from deap import base, creator, gp, tools  # optional dependency only on search path
    import deap

    deap_version = importlib.metadata.version("deap")
    if deap_version != p["external"]["version"]:
        raise RuntimeError(f"DEAP version differs: {deap_version}")
    creator.create("PilotFitnessMin", base.Fitness, weights=(-1.0,))
    creator.create("PilotIndividual", gp.PrimitiveTree, fitness=creator.PilotFitnessMin)
    pset = make_pset(gp)
    results = {"protocol_sha256": EXPECTED_PROTOCOL_SHA, "pid": os.getpid(),
               "started_at": started_at,
               "runtime": {"python": sys.version.split()[0], "numpy": np.__version__,
                           "deap": deap_version}, "runs": []}
    predictions = {"protocol_sha256": EXPECTED_PROTOCOL_SHA, "runs": []}
    accounting = {"used_search_evaluations": 0, "direct_fit_count": 0,
                  "mean_estimate_count": 0}
    direct_cache = {}
    try:
        for task in TASKS:
            for seed in p["search"]["seeds"]:
                train, validation = inputs["train"][task], inputs["validation"][task]
                for arm in ARMS:
                    arm_start = time.monotonic()
                    if arm == "direct_baseline":
                        if task not in direct_cache:
                            model, extra = direct_baseline(train, validation)
                            direct_cache[task] = (copy.deepcopy(model), copy.deepcopy(extra), seed)
                            accounting["direct_fit_count"] += extra["fit_count"]
                            accounting["mean_estimate_count"] += extra["mean_estimate_count"]
                        else:
                            model, cached_extra, original_seed = direct_cache[task]
                            extra = copy.deepcopy(cached_extra)
                            extra["fit_count"] = 0
                            extra["mean_estimate_count"] = 0
                            extra["reused_from"] = {"task": task, "seed": original_seed}
                        details = {"model": model, **extra, "evaluation_count": 0,
                                   "invalid_count": 0, "rejected_proposal_count": 0}
                        predict = lambda x, m=model: direct_predict(x, m)
                    else:
                        details = search_arm(base, gp, tools, creator, pset, train, seed,
                                             p, arm, deadline, accounting)
                        verified_train_fitness = (
                            mse(train["y"], formula_predict(details["expression"], train["x"]))
                            + p["search"]["penalty_per_node"] * details["nodes"]
                        )
                        if not math.isclose(verified_train_fitness, details["train_fitness"],
                                            rel_tol=1e-10, abs_tol=1e-10):
                            raise ValueError("DEAP training and independent AST fitness disagree")
                        predict = lambda x, e=details["expression"]: formula_predict(e, x)
                    details.update({"task": task, "seed": seed, "arm": arm,
                                    "wall_seconds": time.monotonic() - arm_start})
                    outputs = {}
                    metrics = {}
                    for split in SPLITS:
                        yhat = predict(inputs[split][task]["x"])
                        # JSON has no NaN/Infinity; preserve invalidity as explicit null predictions.
                        outputs[split] = [float(z) if math.isfinite(float(z)) else None for z in yhat]
                        metrics[split] = mse(inputs[split][task]["y"], yhat)
                    details["mse"] = metrics
                    results["runs"].append(details)
                    predictions["runs"].append({"task": task, "seed": seed, "arm": arm,
                                                  "outputs": outputs,
                                                  "sha256": {s: array_hash(np.asarray(outputs[s], dtype=float))
                                                             for s in SPLITS}})
        total = sum(r["evaluation_count"] for r in results["runs"])
        if total != p["budget"]["synthetic_search_evaluations_max"]:
            raise AssertionError("total search candidate count differs")
        results["total_search_evaluations"] = total
        results["total_direct_fits"] = sum(r.get("fit_count", 0) for r in results["runs"])
        results["total_mean_estimates"] = sum(r.get("mean_estimate_count", 0) for r in results["runs"])
        # Noise has no population relationship with X. Any favorable accidental
        # score is explicitly compared with the training-mean counterexample.
        noise_cases = []
        for seed in p["search"]["seeds"]:
            mean = float(np.mean(inputs["train"]["noise"]["y"]))
            baseline = {split: mse(inputs[split]["noise"]["y"],
                                   np.full(len(inputs[split]["noise"]["y"]), mean))
                        for split in ("test", "outside_range")}
            arms = {r["arm"]: {split: r["mse"][split] for split in baseline}
                    for r in results["runs"] if r["task"] == "noise" and r["seed"] == seed}
            noise_cases.append({"seed": seed, "training_mean_test_ood_mse": baseline,
                                "arms_test_ood_mse": arms,
                                "interpretation": "no known population relationship; accidental gain is not promotion"})
        results["noise_counterexamples"] = noise_cases
        results["status"] = "complete"
        results["ended_at"] = local_time()
        json_write(output / "results.json", results)
        json_write(output / "predictions.json", predictions)
        json_write(output / "command-receipts.json", {"status": "complete", "pid": os.getpid(),
                    "started_at": started_at, "ended_at": local_time(),
                    "wall_seconds": time.monotonic() - started,
                    "used_search_evaluations": total,
                    "direct_fit_count": results["total_direct_fits"],
                    "mean_estimate_count": results["total_mean_estimates"],
                    "model_calls": "unmetered/unknown", "paid_service_calls": 0,
                    "market_fits": 0})
    except Exception as exc:
        # Partial artifacts retain completed arms; no search is resumed or
        # mistaken for a complete result by check_existing.
        results["status"] = "failed_partial"
        results["ended_at"] = local_time()
        results["used_search_evaluations"] = accounting["used_search_evaluations"]
        json_write(output / "results.json", results)
        json_write(output / "predictions.json", predictions)
        json_write(output / "command-receipts.json", {"status": "failed", "pid": os.getpid(),
                    "started_at": started_at, "ended_at": local_time(),
                    "error_type": type(exc).__name__, "error": str(exc),
                    "completed_runs": len(results["runs"]),
                    "used_search_evaluations": accounting["used_search_evaluations"],
                    "direct_fit_count": accounting["direct_fit_count"],
                    "mean_estimate_count": accounting["mean_estimate_count"],
                    "wall_seconds": time.monotonic() - started})
        raise


def check_existing(output: Path) -> dict:
    """Independently reconstruct saved inputs, predictions and scores; no DEAP import/search."""
    p = read_protocol()
    fingerprints = json.loads((output / "input-fingerprints.json").read_text())
    results = json.loads((output / "results.json").read_text())
    predictions = json.loads((output / "predictions.json").read_text())
    if (results["protocol_sha256"] != EXPECTED_PROTOCOL_SHA
            or predictions["protocol_sha256"] != EXPECTED_PROTOCOL_SHA
            or results.get("status") != "complete"):
        raise ValueError("archive protocol mismatch")
    inputs, expected_fingerprints = output_data(p)
    if fingerprints != expected_fingerprints:
        raise ValueError("archived input hashes mismatch")
    result_map = {(r["task"], r["seed"], r["arm"]): r for r in results["runs"]}
    prediction_map = {(r["task"], r["seed"], r["arm"]): r for r in predictions["runs"]}
    expected_keys = {(t, seed, a) for t in TASKS for seed in p["search"]["seeds"] for a in ARMS}
    if set(result_map) != expected_keys or set(prediction_map) != expected_keys:
        raise ValueError("missing/duplicate result identity")
    if len(results["runs"]) != len(expected_keys) or len(predictions["runs"]) != len(expected_keys):
        raise ValueError("duplicate result")
    total = 0
    direct_fits = 0
    mean_estimates = 0
    for key in sorted(expected_keys):
        task, _, arm = key
        record, archived = result_map[key], prediction_map[key]
        total += record["evaluation_count"]
        if arm == "direct_baseline":
            reused = "reused_from" in record
            if record["evaluation_count"] != 0 or record["fit_count"] != (0 if reused else 6):
                raise ValueError("direct fit accounting mismatch")
            if reused and record["reused_from"] != {"task": task, "seed": p["search"]["seeds"][0]}:
                raise ValueError("direct reuse identity mismatch")
            direct_fits += record["fit_count"]
            mean_estimates += record["mean_estimate_count"]
        elif record["evaluation_count"] != p["search"]["evaluation_cap_per_arm_task_seed"]:
            raise ValueError("search candidate count mismatch")
        if record["invalid_count"] < 0 or record["rejected_proposal_count"] < 0:
            raise ValueError("negative accounting")
        for split in SPLITS:
            x, y = inputs[split][task]["x"], inputs[split][task]["y"]
            stored = np.asarray(archived["outputs"][split], dtype=float)
            if len(stored) != len(y) or array_hash(stored) != archived["sha256"][split]:
                raise ValueError("prediction length/hash mismatch")
            if arm == "direct_baseline":
                recomputed = direct_predict(x, record["model"])
            else:
                recomputed = formula_predict(record["expression"], x)
            if not np.allclose(stored, recomputed, rtol=1e-12, atol=1e-12, equal_nan=True):
                raise ValueError("saved formula predictions mismatch")
            expected_mse = mse(y, recomputed)
            if not math.isclose(expected_mse, record["mse"][split], rel_tol=1e-10, abs_tol=1e-10):
                raise ValueError("saved metric mismatch")
    if total != p["budget"]["synthetic_search_evaluations_max"] or total != results["total_search_evaluations"]:
        raise ValueError("total candidate count mismatch")
    if direct_fits != 18 or direct_fits != results["total_direct_fits"] or mean_estimates != 3:
        raise ValueError("direct baseline total accounting mismatch")
    return {"status": "verified", "runs": len(expected_keys), "search_evaluations": total,
            "input_splits": len(SPLITS) * len(TASKS)}


def main() -> None:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--output", type=Path)
    action.add_argument("--check-existing", type=Path)
    args = parser.parse_args()
    if args.output is not None:
        run(args.output)
    else:
        print(json.dumps(check_existing(args.check_existing), ensure_ascii=False))


if __name__ == "__main__":
    main()
