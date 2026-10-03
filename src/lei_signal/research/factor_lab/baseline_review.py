"""Read-only supplementary baseline arithmetic, separate from research acceptance."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence
import json
import math

import numpy as np

from lei_signal.research import workflow_evaluation as evaluation

_MODELS = ("B0", "B1", "B2", "asset_training_mean")
_TARGETS = {"forward_return", "mae", "max_drawdown", "forward_volatility"}


def build_baseline_review(contract: Mapping[str, Any], observations: Sequence[Mapping[str, Any]],
                          predictions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Compare saved values on complete common rows; never fit or verify provenance."""
    if contract.get("target", {}).get("kind") not in _TARGETS:
        raise ValueError("baseline review supports continuous technical targets only")
    _, policy = evaluation._config(contract)
    obs = evaluation._observations(observations, False)
    axis = evaluation._axis(contract, obs)
    folds = evaluation._folds(contract)
    frame = evaluation._paired_predictions(predictions, False, folds, axis)
    eligible = obs[obs.eligible] if len(obs) else obs
    expected, training_means = set(), []
    means_by_fold = {}
    for fold in folds:
        train = eligible[eligible.date <= fold["train_end"]] if len(eligible) else eligible
        immature = train.label_end >= fold["eval_start"] if len(train) else np.array([], bool)
        if np.any(immature) and contract["split"]["label_policy"] == "require_mature":
            raise ValueError("training labels must be strictly mature before evaluation")
        train = train.loc[~immature] if len(train) else train
        ev = eligible[(eligible.date >= fold["eval_start"]) & (eligible.date <= fold["eval_end"])] if len(eligible) else eligible
        if contract["split"].get("evaluation_label_policy") == "contained" and len(ev):
            ev = ev[ev.label_end <= fold["eval_end"]]
        means = {}
        if len(train):
            for asset, group in train.groupby("asset", sort=True):
                # Divide first to avoid overflowing a sum of finite values.
                mean = math.fsum(float(y) / len(group) for y in group.y)
                if not math.isfinite(mean):
                    raise ValueError("nonfinite asset training mean")
                means[asset] = mean
                training_means.append({"fold": fold["name"], "asset": asset,
                                       "mean": mean, "rows": len(group)})
        means_by_fold[fold["name"]] = means
        if len(train) >= contract.get("evaluator", {}).get("minimum_training_rows", 1):
            expected.update(ev.id.tolist())
    actual = set(frame.id) if len(frame) else set()
    if actual != expected:
        raise ValueError("prediction coverage mismatch: require all actually evaluable rows")
    if len(frame):
        by_id = {r["id"]: r for r in obs.to_dict("records")}
        for p in frame.to_dict("records"):
            row = by_id.get(p["id"])
            if row is None or not row["eligible"] or any(p[k] != row[k] for k in ("asset", "date", "y", "label_end")):
                raise ValueError("prediction identity/target does not match eligible observation")
            if p["asset"] not in means_by_fold[p["fold"]]:
                raise ValueError(f"no mature training rows for evaluation asset {p['asset']} in fold {p['fold']}")
        frame["asset_training_mean"] = [means_by_fold[p["fold"]][p["asset"]] for p in frame.to_dict("records")]
    result = {"schema_version": "baseline-review/1.0", "diagnostic_only": True,
              "source_verification": "numeric_inputs_only", "status": "completed" if len(frame) else "insufficient_data",
              "target": dict(contract["target"]), "weighting": policy,
              "training_mean_definition": "equal rows within each asset; date <= train_end and label_end < eval_start",
              "rows": len(frame), "assets": int(frame.asset.nunique()) if len(frame) else 0,
              "dates": int(frame.date.nunique()) if len(frame) else 0,
              "training_means": training_means, "performance": [], "increments": [],
              "execution": {"fits": 0, "mode": "saved_prediction_arithmetic"},
              "limitations": ["Point estimates only; no stability, causality or trading adoption claim.",
                               "Asset training means use equal rows within each ETF, not a universal optimal baseline."]}
    if not len(frame):
        result["limitations"].append("No complete paired evaluation predictions; errors not estimated.")
        return result
    weights = evaluation._weights(frame, policy)
    errors = {}
    with np.errstate(over="ignore", invalid="ignore"):
        for model in _MODELS:
            mse = float(weights @ np.square(frame[model].to_numpy(float) - frame.y.to_numpy(float)))
            if not math.isfinite(mse):
                raise ValueError("nonfinite squared prediction error")
            errors[model] = mse
            result["performance"].append({"model": model, "mse": mse, "rmse": math.sqrt(mse),
                                          "mse_unit": "percentage_point_squared", "rmse_unit": "percentage_point"})
    for opponent in ("B0", "B1", "asset_training_mean"):
        improvement = errors[opponent] - errors["B2"]
        result["increments"].append({"new_model": "B2", "old_model": opponent,
            "old_value": errors[opponent], "new_value": errors["B2"],
            "absolute_error_improvement": improvement,
            "relative_percent": improvement / errors[opponent] * 100 if errors[opponent] else None,
            "unit": "percentage_point_squared", "interpretation": "positive means lower error, not investment return"})
    return result


def review_saved_run(run_dir, output_dir, *, root=None) -> dict[str, Any]:
    """Require the existing controlled receipt; write only a new auxiliary directory."""
    from lei_signal.research import workflow

    source, out = Path(run_dir).resolve(), Path(output_dir).resolve()
    root = Path(root).resolve() if root is not None else workflow.ROOT
    if out.exists():
        raise ValueError("refuse to overwrite existing review output")
    if out == source or source in out.parents or out in source.parents:
        raise ValueError("review output must be separate from saved run directory")
    for name in ("contract.json", "preflight.json", "result.json", "receipt.json", "report.md"):
        if not (source / name).is_file():
            raise ValueError(f"missing saved artifact: {name}")
    contract = workflow.read_json(source / "contract.json")
    if contract.get("target", {}).get("kind") not in _TARGETS:
        raise ValueError("baseline review supports continuous technical targets only")
    ledger = workflow.family_ledger(root, contract["history"]["family"])
    if not ledger.is_file():
        raise ValueError("missing controlled execution journal; read-only review cannot create it")
    catalog = workflow.read_json(root / workflow.CATALOG)
    registry = root / catalog["report_registry"]
    if not registry.is_file():
        raise ValueError("missing original report registry")
    input_path = workflow.resolve_path(root, contract["data"]["path"])
    watched = [source / name for name in ("contract.json", "preflight.json", "result.json", "receipt.json", "report.md")]
    watched += [ledger, registry, input_path]
    before = {str(path): workflow.file_hash(path) for path in watched}
    # A receipt's copied source hashes must describe the code actually imported
    # in this process, rather than an older implementation left under --root.
    for relative in workflow.CODE_PATHS:
        current = workflow.ROOT / relative
        supplied = root / relative
        if not supplied.is_file() or workflow.file_hash(supplied) != workflow.file_hash(current):
            raise ValueError(f"review source code differs from active implementation: {relative}")
    watched += [root / relative for relative in workflow.CODE_PATHS]
    before = {str(path): workflow.file_hash(path) for path in watched}
    original_state = workflow.check_publication(source, root)
    proof = workflow.read_json(source / "preflight.json")
    saved_result = workflow.read_json(source / "result.json")
    receipt = workflow.read_json(source / "receipt.json")
    review = build_baseline_review(contract, proof["observations"], saved_result["predictions"])
    review.update(source_verification="workflow.check_publication", original_run_id=receipt["run_id"],
                  original_conclusion=original_state["evidence"], original_state=original_state,
                  data_mode=contract["data"]["mode"], saved_run=str(source),
                  source_sha256={name: workflow.file_hash(source / name) for name in
                                 ("contract.json", "preflight.json", "result.json", "receipt.json", "report.md")},
                  review_code_sha256={"baseline_review.py": workflow.file_hash(Path(__file__)),
                                     "scripts/run_factor_lab.py": workflow.file_hash(Path(__file__).resolve().parents[4] / "scripts/run_factor_lab.py")},
                  original_source_bindings=contract.get("bindings", {}),
                  input_sha256=workflow.file_hash(workflow.resolve_path(root, contract["data"]["path"])))
    after = {str(path): workflow.file_hash(path) for path in watched}
    if before != after:
        raise ValueError("original material changed during baseline review; refuse verified output")
    review["original_material_sha256"] = before
    report = _render_report(review)
    encoded = json.dumps(review, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    out.mkdir(parents=True, exist_ok=False)
    (out / "review.json").write_text(encoded, encoding="utf-8")
    (out / "report.md").write_text(report, encoding="utf-8")
    return review


def _render_report(review: Mapping[str, Any]) -> str:
    errors = {row["model"]: row["mse"] for row in review["performance"]}
    def compare(opponent, label):
        delta = errors["B2"] - errors[opponent]
        relation = "小" if delta < 0 else "大" if delta > 0 else "相同"
        return f"候选模型的误差比{label}{relation}" if delta else f"候选模型的误差与{label}相同"
    summary = (compare("B1", "原已有信息模型") + "；" + compare("asset_training_mean", "各ETF自己的历史平均") + "。") if errors else "资料不足，没有可完整配对的评价记录。"
    lines = ["# 保存结果的简单对手补充核查", "", "## 一句话结论（大白话）", "",
             summary, "",
             "在原来相同ETF和日期上，把已保存模型与各ETF自己较早、已能知道结果的历史平均比较。"
             "这里只核算误差，不重新训练模型；局部误差更小不能证明长期有效，也不改变原研究结论。", "",
             "B0 是共同训练平均，B1 是原已有信息模型，B2 是原增加候选信息的模型；"
             "asset_training_mean 是每只ETF自己的成熟历史平均，每只ETF内部各条训练记录同等分量。", "",
             f"评价记录 {review['rows']} 条，ETF {review['assets']} 只，日期 {review['dates']} 个。"
             + ("每只ETF总分量相同。" if review['weighting'] == 'equal_asset' else "每个日期总分量相同。"), "",
             "误差先平方再按上述分量平均（MSE）；开平方后回到原目标的百分点单位（RMSE）。", "",
             "| 方法 | 平均平方误差 | 开方误差 |", "|---|---:|---:|"]
    lines += [f"| {r['model']} | {r['mse']:.12g} | {r['rmse']:.12g} |" for r in review["performance"]]
    if not review["performance"]:
        lines.append("资料不足，没有可完整配对的评价记录，不计算误差。")
    lines += ["", "| B2的比较对手 | 对手误差减B2误差（正数较好） | 相对减少 |", "|---|---:|---:|"]
    for row in review["increments"]:
        percent = "无法计算（对手误差为零）" if row["relative_percent"] is None else f"{row['relative_percent']:.6g}%"
        lines.append(f"| {row['old_model']} | {row['absolute_error_improvement']:.12g} | {percent} |")
    lines += ["", "只报告当前资料中的数值，不提供稳定性或因果证据，不授权交易采用。", "",
              f"原运行：{review['original_run_id']}；原结论：{review['original_conclusion']}；资料类型：{review['data_mode']}；新增拟合：0。",
              "原结果通过既有 workflow.check_publication 核查；本文件为辅助诊断，未登记研究报告。", "",
              "## 来源指纹", "", "```json", json.dumps({k: review[k] for k in ("source_sha256", "review_code_sha256", "input_sha256")}, ensure_ascii=False, indent=2), "```", ""]
    return "\n".join(lines)
