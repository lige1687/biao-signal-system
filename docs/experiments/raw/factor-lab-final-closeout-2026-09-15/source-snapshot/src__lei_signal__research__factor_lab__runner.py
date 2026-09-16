"""统一协议运行器：先核对冻结合同，再计算；运行后记录可追溯证据。

退出码合同：0=合成检查完成（常驻 synthetic）；2=合法资料不足（原因完整落盘）；
3=身份/格式失败（必需代码键缺失/哈希不符/卡变化/目标参数不符/输入篡改等，
全部在计算前拒绝）；1=期望核对失败或意外错误。运行前核对，不靠运行后记录
替代冻结确认；不提供跳过核验或强制通过开关。
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import sys
import traceback
from pathlib import Path

import pandas as pd

from lei_signal.research import definitions
from lei_signal.research.factor_lab.adapters import CANDIDATE_CARDS, calculate_batch
from lei_signal.research.factor_lab.attribution import (
    explain_strategy,
    validate_comparison_contract,
)
from lei_signal.research.factor_lab.contracts import (
    EXIT_IDENTITY_FORMAT,
    IdentityFormatError,
    InsufficientDataError,
    protocol_sha256,
)
from lei_signal.research.factor_lab.diagnostics import evaluate_predictive
from lei_signal.research.factor_lab.validation import TRIAL_REQUIRED, audit_validation
from lei_signal.research.momentum_prototype import build_targets

SPEC_BINDINGS = {
    "experiment_backtest_principles": "docs/research/experiment-backtest-principles.md@v1.1",
    "definition_standard": "docs/research/definition-standard.md@1.1.0",
    "ai_execution_contract": "docs/research/ai-execution-contract.md@1.0.1",
    "experiment_report_template": "docs/research/experiment-report-template.md@1.1.0",
    "plan": "docs/superpowers/plans/2026-09-14-factor-research-workbench-v1.md@1.0.0",
    "repair_plan": (
        "docs/superpowers/plans/2026-09-14-factor-lab-concentrated-repair.md@1.0.0"
    ),
}

#: 不可由协议删减的必需代码键：六模块 + CLI + 实际复用依赖（含规则配置加载器）。
REQUIRED_CODE_KEYS: frozenset[str] = frozenset({
    "src/lei_signal/research/factor_lab/__init__.py",
    "src/lei_signal/research/factor_lab/contracts.py",
    "src/lei_signal/research/factor_lab/adapters.py",
    "src/lei_signal/research/factor_lab/diagnostics.py",
    "src/lei_signal/research/factor_lab/validation.py",
    "src/lei_signal/research/factor_lab/attribution.py",
    "src/lei_signal/research/factor_lab/runner.py",
    "scripts/run_factor_lab.py",
    "src/lei_signal/research/definitions.py",
    "src/lei_signal/research/momentum_prototype.py",
    "src/lei_signal/research/factor_diagnostics.py",
    "src/lei_signal/rules/dual_ma.py",
    "src/lei_signal/rules/lei_color.py",
    "src/lei_signal/features/indicators.py",
    "src/lei_signal/domain/rules_config.py",
})

#: 期望容差的固定允许值；不允许无穷或任意容差放行。
ALLOWED_TOLERANCES: tuple[float, ...] = (0.0, 1e-9, 1e-6, 0.01)

SUPPORTED_TARGET_OFFSETS = {"entry_offset": 1, "exit_offset": 22}

REQUIRED_DECLARATIONS = ("price_scale", "calendar", "timezone", "currency")

SYNTHETIC_TITLE = "合成算法验证，非真实收益/有效性证据"


class _Logger:
    def __init__(self, lines: list[str]):
        self.lines = lines

    def log(self, message: str) -> None:
        self.lines.append(message)

    def flush(self) -> None:  # 由 run_protocol 统一落盘
        pass


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(data) -> str:
    return hashlib.sha256(
        json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        .encode("utf-8")).hexdigest()


def _dump_json(data) -> str:
    """JSON 落盘统一出口：拒绝 NaN/Infinity（缺失写 null），写前递归清洗。"""
    warnings: list[str] = []

    def sanitize(obj, path="$"):
        if isinstance(obj, float):
            if obj != obj or obj in (float("inf"), float("-inf")):
                warnings.append(f"{path}: non-finite replaced with null")
                return None
            return obj
        if isinstance(obj, dict):
            return {key: sanitize(value, f"{path}.{key}") for key, value in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [sanitize(value, f"{path}[{i}]") for i, value in enumerate(obj)]
        return obj

    cleaned = sanitize(data)
    text = json.dumps(cleaned, ensure_ascii=False, indent=2, allow_nan=False,
                      default=str)
    if warnings:
        text += "\n// non-finite sanitization: " + json.dumps(warnings) + "\n"
    return text


def _load_protocol(protocol_path: Path) -> dict:
    if protocol_path.suffix != ".json":
        raise IdentityFormatError("protocol must be a .json file")
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if not isinstance(protocol, dict):
        raise IdentityFormatError("protocol must be a JSON object")
    for key in ("protocol_id", "version", "kind", "data_mode", "case", "inputs"):
        if not protocol.get(key):
            raise IdentityFormatError(f"protocol missing key: {key}")
    if "current" in protocol:
        # current 指针会静默漂移到最新版本；本轮只接受排他冻结的精确版本。
        raise IdentityFormatError(
            "protocol contains a 'current' pointer; exclusive frozen versions only"
        )
    return protocol


def _verify_inputs(protocol: dict, base_dir: Path) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for name, spec in protocol["inputs"].items():
        path = (base_dir / spec["path"]).resolve()
        if not path.is_file():
            raise IdentityFormatError(f"input file missing: {spec['path']}")
        digest = _sha256_file(path)
        if digest != spec["sha256"]:
            raise IdentityFormatError(
                f"input hash mismatch for {name}: file={digest} "
                f"protocol={spec['sha256']}"
            )
        paths[name] = path
    return paths


def _required_references(protocol: dict) -> list[str]:
    refs: list[str] = list(protocol.get("extra_card_references", []))
    for calc in protocol.get("calculations", []):
        refs.append(calc["reference"])
    if "state_candidate" in protocol:
        refs.append(protocol["state_candidate"]["reference"])
    if "breadth" in protocol:
        refs.extend(protocol["breadth"]["references"].values())
    return list(dict.fromkeys(refs))


def verify_frozen_contract(protocol: dict, repo_root: Path,
                           protocol_dir: Path) -> dict:
    """计算前核对冻结合同；任何不符在计算开始前以格式错误拒绝。"""
    code_identity = protocol.get("code_identity")
    if not isinstance(code_identity, dict):
        raise IdentityFormatError("protocol.code_identity (path->sha256) required")
    missing_keys = sorted(REQUIRED_CODE_KEYS - set(code_identity))
    if missing_keys:
        raise IdentityFormatError(
            f"protocol.code_identity missing required code keys: {missing_keys}; "
            "必需代码键不可由协议删减")
    for rel in sorted(REQUIRED_CODE_KEYS):
        path = repo_root / rel
        declared = code_identity[rel]
        if not path.is_file() or _sha256_file(path) != declared:
            actual = _sha256_file(path) if path.is_file() else "MISSING"
            raise IdentityFormatError(
                f"frozen code hash mismatch for {rel}: file={actual} "
                f"protocol={declared}")

    registry = definitions.load_registry()
    declared_registry = protocol.get("registry")
    if not isinstance(declared_registry, dict):
        raise IdentityFormatError(
            "protocol.registry (version+canonical_sha256) required")
    if declared_registry.get("version") != registry["version"]:
        raise IdentityFormatError(
            f"registry version mismatch: file={registry['version']} "
            f"protocol={declared_registry.get('version')}")
    if declared_registry.get("canonical_sha256") != _canonical_sha256(registry):
        raise IdentityFormatError(
            "registry canonical sha256 mismatch: 登记表字节与协议冻结不一致")

    cards = {}
    for reference in _required_references(protocol):
        declared_sha = protocol.get("definition_cards_sha256", {}).get(reference)
        if not declared_sha:
            raise IdentityFormatError(
                f"definition_cards_sha256 missing for {reference}; "
                "卡指纹必须冻结并在计算前核对")
        if reference.startswith("candidate:"):
            card = CANDIDATE_CARDS[reference]
        else:
            try:
                card = definitions.resolve(registry, reference)
            except ValueError as exc:
                raise IdentityFormatError(
                    f"reference not resolvable: {reference}: {exc}") from exc
        if _canonical_sha256(card) != declared_sha:
            raise IdentityFormatError(
                f"definition card changed since freeze: {reference}; "
                "卡内容与协议冻结不一致")
        cards[reference] = card

    targets = protocol.get("targets")
    effective_targets = dict(SUPPORTED_TARGET_OFFSETS)
    if targets is not None:
        for key, expected in SUPPORTED_TARGET_OFFSETS.items():
            declared = targets.get(key)
            if declared is not None and declared != expected:
                raise IdentityFormatError(
                    f"targets.{key}={declared} not supported; only {expected} "
                    "（声明与执行不得分离）")
        observations = targets.get("observations")
        if observations is not None:
            if not isinstance(observations, dict) or {"start", "end"} - set(observations):
                raise IdentityFormatError("targets.observations must provide start/end")
            effective_targets["observations"] = dict(observations)
    declarations = protocol.get("data_declarations")
    if not isinstance(declarations, dict):
        raise IdentityFormatError(
            "protocol.data_declarations required（合成数据也须声明价格尺度/日历/时间/币种）")
    for key in REQUIRED_DECLARATIONS:
        if not isinstance(declarations.get(key), str) or not declarations[key].strip():
            raise IdentityFormatError(
                f"data_declarations.{key} must be a non-empty string")
    if declarations["timezone"] != protocol["timezone"]:
        raise IdentityFormatError("data_declarations.timezone must match protocol.timezone")
    required_checks = protocol.get("required_checks")
    expectations = protocol.get("expectations")
    if not isinstance(required_checks, list) or not required_checks:
        raise IdentityFormatError(
            "protocol.required_checks must be a non-empty list（空期望不能成为成功证据）")
    if not isinstance(expectations, dict) or not expectations:
        raise IdentityFormatError(
            "protocol.expectations must be a non-empty dict（空期望不能成为成功证据）")
    absent = sorted(set(required_checks) - set(expectations))
    if absent:
        raise IdentityFormatError(
            f"required checks missing from expectations: {absent}; 删检查必须拒绝")
    tolerance = protocol.get("expectation_tolerance_abs", 1e-6)
    if (not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool)
            or tolerance < 0 or tolerance not in ALLOWED_TOLERANCES):
        raise IdentityFormatError(
            f"expectation_tolerance_abs must be one of {ALLOWED_TOLERANCES}")
    source = protocol.get("expectation_source")
    if not isinstance(source, dict) or not source.get("path") or not source.get("sha256"):
        raise IdentityFormatError(
            "protocol.expectation_source (path+sha256) required；独立期望来源必须冻结")
    source_path = (protocol_dir / source["path"]).resolve()
    if not source_path.is_file() or _sha256_file(source_path) != source["sha256"]:
        raise IdentityFormatError("expectation_source file missing or hash mismatch")
    if protocol.get("comparison") is not None:
        validate_comparison_contract(protocol["comparison"])
    trials = protocol.get("trials") or []
    for index, trial in enumerate(trials):
        if not isinstance(trial, dict):
            raise IdentityFormatError(f"trials[{index}] must be a dict")
        absent_trial = TRIAL_REQUIRED - set(trial)
        if absent_trial:
            raise IdentityFormatError(
                f"trials[{index}] missing keys: {sorted(absent_trial)}")
    return {"registry": registry, "cards": cards, "effective_targets": effective_targets}


def _read_wide_prices(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, parse_dates=["date"]).set_index("date")
    if not frame.index.is_unique or not frame.index.is_monotonic_increasing:
        raise IdentityFormatError(f"prices in {path.name} need unique increasing dates")
    return frame


def _read_bars(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["date"]).set_index("date")


def _membership_from_file(path: Path) -> tuple[dict, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    membership: dict = {}
    for segment in data["segments"]:
        for day in pd.bdate_range(segment["start"], segment["end"]):
            membership[day.normalize()] = list(segment["members"])
    return membership, str(data["universe"])


def _load_input(name: str, spec: dict, path: Path):
    fmt = spec.get("format")
    if fmt == "wide_prices":
        return _read_wide_prices(path)
    if fmt == "bars":
        return _read_bars(path)
    if fmt == "membership":
        return _membership_from_file(path)
    if fmt == "actions":
        return json.loads(path.read_text(encoding="utf-8"))
    if fmt == "table":
        return pd.read_csv(path)
    raise IdentityFormatError(f"unknown input format for {name}: {fmt}")


def _build_targets_panel(panel: pd.DataFrame, *, observations=None,
                         entry_offset: int = 1, exit_offset: int = 22) -> pd.DataFrame:
    """复用 momentum_prototype.build_targets：固定 t+1→t+22 经济价格变化。"""
    if entry_offset != SUPPORTED_TARGET_OFFSETS["entry_offset"] \
            or exit_offset != SUPPORTED_TARGET_OFFSETS["exit_offset"]:
        raise IdentityFormatError("first version keeps the fixed 1/22 endpoint contract")
    sessions = list(panel.index)
    obs = list(panel.index) if observations is None else [
        day for day in panel.index
        if pd.Timestamp(observations["start"]) <= day <= pd.Timestamp(observations["end"])
    ]
    frames = []
    for entity in panel.columns:
        targets = build_targets(panel[entity], sessions, obs)
        targets = targets.rename(columns={"entry_date": "label_start",
                                          "exit_date": "label_end"})
        targets["entity_id"] = str(entity)
        targets["label_available_at"] = [
            pd.Timestamp(day).tz_localize("Asia/Shanghai") + pd.Timedelta(hours=15)
            if day is not None and pd.notna(day) else None
            for day in targets["label_end"]
        ]
        frames.append(targets)
    combined = pd.concat(frames, ignore_index=True)
    return combined[["observation_date", "entity_id", "label_start", "label_end",
                     "label_available_at", "target", "reason"]]


def _checkpoint(frame: pd.DataFrame, date, entity_id: str) -> float | None:
    row = frame[(frame["observation_date"] == pd.Timestamp(date))
                & (frame["entity_id"] == entity_id)]
    if row.empty:
        return None
    value = row.iloc[0]["value"]
    return None if value is None or pd.isna(value) else float(value)


def _sub_protocol(protocol: dict, diagnostics: dict) -> dict:
    view = dict(protocol)
    view["diagnostics"] = diagnostics
    return view


def _pairs_for_audit(values: pd.DataFrame, targets: pd.DataFrame) -> pd.DataFrame:
    values = values.copy()
    values["observation_date"] = pd.to_datetime(values["observation_date"])
    targets = targets.copy()
    for col in ("observation_date", "label_start", "label_end"):
        targets[col] = pd.to_datetime(targets[col])
    return values.merge(targets, on=["observation_date", "entity_id"], how="inner")


def run_numerical(protocol: dict, paths: dict, loaded: dict, logger: _Logger) -> dict:
    checkpoints: dict = {}
    artifacts: dict[str, pd.DataFrame] = {}
    artifact_meta: dict[str, dict] = {}
    diagnostics_results: dict[str, dict] = {}
    targets_cache: dict[str, pd.DataFrame] = {}

    def targets_for(input_name: str) -> pd.DataFrame:
        if input_name not in targets_cache:
            targets_cache[input_name] = _build_targets_panel(
                loaded[input_name],
                observations=protocol["targets"].get("observations"))
        return targets_cache[input_name]

    for calc in protocol["calculations"]:
        reference, input_name = calc["reference"], calc["input"]
        if input_name not in loaded:
            raise IdentityFormatError(f"calculation input missing: {input_name}")
        batch = calculate_batch(reference, {"prices": loaded[input_name]},
                                protocol=protocol)
        artifacts[calc["id"]] = batch.values
        artifact_meta[calc["id"]] = {"metadata": batch.metadata,
                                     "findings": batch.findings}
        logger.log(f"calculated {calc['id']} ({reference}) rows={len(batch.values)}")
        if calc.get("evaluate_with_targets"):
            panel_targets = targets_for(input_name)
            if int(panel_targets["target"].notna().sum()) == 0:
                raise InsufficientDataError(
                    f"no computable targets for {input_name}: 全部观察日的 "
                    f"{SUPPORTED_TARGET_OFFSETS['exit_offset']} 日后结果缺失"
                    "（合法资料不足，非格式错误）")
            result = evaluate_predictive(
                batch, panel_targets,
                protocol=_sub_protocol(protocol, protocol["diagnostics"]))
            diagnostics_results[calc["id"]] = result

    probe = protocol["expectations_probe"]
    row252 = pd.Timestamp(probe["row252_date"])
    for key, spec_p in probe["value_probes"].items():
        values = artifacts[spec_p["calculation"]]
        row = values[(values["entity_id"] == spec_p["entity"])
                     & (pd.to_datetime(values["observation_date"]) == row252)]
        checkpoints[key] = (None if row.empty or pd.isna(row.iloc[0]["value"])
                            else float(row.iloc[0]["value"]))

    primary_result = diagnostics_results[probe["primary_id"]]
    checkpoints["ic_mean_3"] = primary_result["mean_ic"]
    checkpoints["n_periods_3"] = primary_result["n_periods"]
    checkpoints["n_periods_with_value_3"] = primary_result["n_periods_with_value"]
    checkpoints["min_n_3"] = min(p["n"] for p in primary_result["periods"])
    checkpoints["min_n_with_value_3"] = min(
        (p["n"] for p in primary_result["periods"] if p["ic"] is not None), default=0)
    secondary_id = probe.get("secondary_id")
    if secondary_id:
        secondary = diagnostics_results[secondary_id]
        checkpoints["ic_mean_5"] = secondary["mean_ic"]
        checkpoints["n_periods_with_value_5"] = secondary["n_periods_with_value"]
        checkpoints["min_n_5"] = min(p["n"] for p in secondary["periods"])
        checkpoints["min_n_with_value_5"] = min(
            (p["n"] for p in secondary["periods"] if p["ic"] is not None), default=0)
        checkpoints["max_n_5"] = max(p["n"] for p in secondary["periods"])

    mom_values = artifacts[probe["first_valid_probe"]["calculation"]]
    entity = probe["first_valid_probe"]["entity"]
    entity_rows = mom_values[mom_values["entity_id"] == entity]
    first_valid_date = pd.to_datetime(
        entity_rows[entity_rows["value"].notna()]["observation_date"].min())
    panel = loaded[probe["first_valid_probe"]["input"]]
    checkpoints["momentum_first_valid_row"] = int(panel.index.get_loc(first_valid_date) + 1)

    checks = protocol.get("checks", {})
    if "price_scale_invariance" in checks:
        spec_c = checks["price_scale_invariance"]
        base = calculate_batch(spec_c["reference"], {"prices": loaded[spec_c["input"]]},
                               protocol=protocol)
        scaled = calculate_batch(spec_c["reference"],
                                 {"prices": loaded[spec_c["input"]] * spec_c["factor"]},
                                 protocol=protocol)
        merged = base.values.merge(scaled.values, on=["observation_date", "entity_id"],
                                   suffixes=("_b", "_s"))
        both = merged[merged["value_b"].notna() & merged["value_s"].notna()]
        checkpoints["scale_invariance_max_diff"] = float(
            (both["value_b"] - both["value_s"]).abs().max())
    if "append_future_invariance" in checks:
        spec_a = checks["append_future_invariance"]
        panel = loaded[spec_a["input"]]
        full = calculate_batch(spec_a["reference"], {"prices": panel}, protocol=protocol)
        part = calculate_batch(spec_a["reference"],
                               {"prices": panel.iloc[:spec_a["keep_rows"]]},
                               protocol=protocol)
        merged = part.values.merge(full.values, on=["observation_date", "entity_id"],
                                   suffixes=("_p", "_f"))
        both = merged[merged["value_p"].notna() & merged["value_f"].notna()]
        checkpoints["append_invariance_max_diff"] = float(
            (both["value_p"] - both["value_f"]).abs().max())

    pairs = _pairs_for_audit(artifacts[probe["audit_pairs_from"]],
                             targets_for(probe["audit_targets_of"]))
    audit = audit_validation(pairs, protocol.get("trials"), protocol=protocol)
    for segment in ("dev", "validation", "holdout"):
        counts = audit["sample_counts"][segment]
        checkpoints[f"{segment}_n_usable_clean"] = counts["n_usable_clean"]
        if segment != "holdout":
            checkpoints[f"{segment}_label_crossing_n"] = (
                counts["n_label_crossing_into_next_segment"])
    checkpoints["trial_history_status"] = audit["trial_history_status"]

    return {
        "checkpoints": checkpoints,
        "artifacts": artifacts,
        "artifact_meta": artifact_meta,
        "targets": targets_cache,
        "diagnostics": diagnostics_results,
        "validation": audit,
    }


def run_state(protocol: dict, paths: dict, loaded: dict, logger: _Logger) -> dict:
    checkpoints: dict = {}
    artifacts: dict[str, pd.DataFrame] = {}
    artifact_meta: dict[str, dict] = {}
    diagnostics_results: dict[str, dict] = {}

    bars = {name.removeprefix("bars_"): loaded[name]
            for name, spec in protocol["inputs"].items() if spec.get("format") == "bars"}
    dm_batch = calculate_batch(protocol["state_candidate"]["reference"], {"bars": bars},
                               protocol=protocol)
    artifacts["dm"] = dm_batch.values
    artifact_meta["dm"] = {"metadata": dm_batch.metadata, "findings": dm_batch.findings}
    for finding in dm_batch.findings:
        if finding.get("code") == "entity_readiness":
            entity = finding["entity_id"]
            checkpoints[f"{entity}_not_ready_rows"] = finding["not_ready_rows"]
            checkpoints[f"{entity}_state_true_rows"] = finding["state_true_rows"]
            checkpoints[f"{entity}_state_false_rows"] = finding["state_false_rows"]

    readiness_probe = protocol["expectations_probe"]
    for entity, probes in readiness_probe["state_rows"].items():
        for probe_key, (date, expect_ready) in probes.items():
            row = dm_batch.values[(dm_batch.values["entity_id"] == entity)
                                  & (dm_batch.values["observation_date"]
                                     == pd.Timestamp(date))]
            if expect_ready:
                checkpoints[probe_key] = int(row.iloc[0]["value"])
            else:
                checkpoints[probe_key] = ("not_ready" if pd.isna(row.iloc[0]["value"])
                                          else "ready")

    membership, universe = _membership_from_file(paths[protocol["breadth"]["membership"]])
    close = loaded[protocol["breadth"]["close"]]
    breadth_results: dict[str, object] = {}
    probe_b = readiness_probe["breadth"]
    change_day = pd.Timestamp(probe_b["change_date"])
    day_before_date = pd.Timestamp(probe_b["day_before_date"])
    for ref_id, reference in protocol["breadth"]["references"].items():
        b_batch = calculate_batch(reference, {"prices": close,
                                              "membership_by_date": membership,
                                              "universe_id": universe},
                                  protocol=protocol)
        artifacts[ref_id] = b_batch.values
        artifact_meta[ref_id] = {"metadata": b_batch.metadata,
                                 "findings": b_batch.findings}
        values = b_batch.values
        valid = values[values["value"].notna()]
        missing = values[values["value"].isna()]
        # 检查点以对象ID命名：B50/B200 互不覆盖。
        checkpoints[f"{ref_id}_first_valid_date"] = str(
            pd.Timestamp(valid["observation_date"].min()).date())
        checkpoints[f"{ref_id}_valid_days"] = int(len(valid))
        checkpoints[f"{ref_id}_coverage_missing_days"] = int(
            (missing["missing_reason"] == "coverage_below_minimum").sum())
        first = valid.sort_values("observation_date").iloc[0]
        checkpoints[f"{ref_id}_at_first_valid"] = float(first["value"])
        at_change = valid[pd.to_datetime(valid["observation_date"]) == change_day]
        checkpoints[f"{ref_id}_at_change"] = float(at_change.iloc[0]["value"])
        day_before = valid[pd.to_datetime(valid["observation_date"]) == day_before_date]
        checkpoints[f"{ref_id}_day_before_change"] = (
            float(day_before.iloc[0]["value"]) if len(day_before) else None)
        breadth_results[ref_id] = b_batch

    ic_request = protocol["diagnostic_requests"]["constant_breadth_ic"]
    ic_result = evaluate_predictive(
        breadth_results[ic_request["batch"]],
        pd.DataFrame(columns=["observation_date", "entity_id", "label_start",
                              "label_end", "label_available_at", "target"]),
        protocol=_sub_protocol(protocol, ic_request["diagnostics"]))
    diagnostics_results["constant_breadth_ic"] = ic_result
    checkpoints["constant_breadth_ic_status"] = ic_result["status"]

    so_request = protocol["diagnostic_requests"]["state_outcomes"]
    bars_panel = pd.concat(
        [frame.assign(entity_id=name)["close"].rename(name)
         for name, frame in bars.items()], axis=1)
    so_targets = _build_targets_panel(bars_panel)
    so_result = evaluate_predictive(
        dm_batch, so_targets,
        protocol=_sub_protocol(protocol, so_request["diagnostics"]))
    diagnostics_results["state_outcomes"] = so_result
    for entry in so_result["entities"]:
        entity = entry["entity_id"].replace("-", "_")
        checkpoints[f"so_{entity}_true_n"] = entry["groups"]["state_true"]["n"]
        checkpoints[f"so_{entity}_false_n"] = entry["groups"]["state_false"]["n"]

    ts_request = protocol["diagnostic_requests"]["time_series_state"]
    ts_targets = _build_targets_panel(close)
    ts_result = evaluate_predictive(
        breadth_results[ts_request["batch"]], ts_targets,
        protocol=_sub_protocol(protocol, ts_request["diagnostics"]))
    diagnostics_results["time_series_state"] = ts_result
    for entry in ts_result["entities"]:
        checkpoints[f"ts_{entry['target_entity']}_status"] = entry["status"]
        checkpoints[f"ts_{entry['target_entity']}_n"] = entry["n"]

    return {
        "checkpoints": checkpoints,
        "artifacts": artifacts,
        "artifact_meta": artifact_meta,
        "targets": {"state_outcomes": so_targets, "time_series": ts_targets},
        "diagnostics": diagnostics_results,
        "validation": None,
    }


def run_attribution(protocol: dict, inputs: dict, loaded: dict, logger: _Logger) -> dict:
    accounts = {"accounts": {}}

    def as_str(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
        out = frame.copy()
        for column in columns:
            if column in out:
                out[column] = out[column].astype(str)
        return out

    for name, spec in protocol["accounts"].items():
        accounts["accounts"][name] = {
            "initial": float(spec["initial"]),
            "equity": loaded[spec["equity"]],
            "trades": as_str(loaded[spec["trades"]], ["symbol", "side"]),
            "events": as_str(loaded[spec["events"]], ["event_id", "event"]),
            "actions": loaded[spec["actions"]],
            "prices": as_str(loaded[spec["prices"]], ["symbol"]),
        }
    model_card = protocol.get("model_card")
    result = explain_strategy(accounts, model_card=model_card, protocol=protocol)
    checkpoints: dict = {}
    layer1 = result["layer1_capital"]
    for name in protocol["accounts"]:
        entry = layer1[name]
        key = name.replace("-", "_")
        checkpoints[f"{key}_status"] = entry["status"]
        if entry["contributions"]:
            checkpoints[f"{key}_net_contribution"] = float(
                entry["contributions"][0]["net_contribution"])
        checkpoints[f"{key}_reconcile_error"] = float(
            entry["reconciliation"]["max_abs_error"])
    layer2 = result["layer2_decision_increment"]
    checkpoints["l2_status"] = layer2["status"]
    if "differences" in layer2:
        checkpoints["l2_net_pnl_diff"] = float(layer2["differences"]["net_pnl"])
    layer3 = result["layer3_risk_model"]
    checkpoints["l3_status"] = layer3["status"]
    checkpoints["l3_reason"] = layer3.get("reason")
    return {"checkpoints": checkpoints, "attribution": result,
            "diagnostics": {}, "validation": None, "artifacts": {},
            "artifact_meta": {}}


CASE_RUNNERS = {"numerical": run_numerical, "state": run_state,
                "attribution": run_attribution}


def _compare_expectations(protocol: dict, checkpoints: dict) -> dict:
    expectations = protocol.get("expectations", {})
    tolerance = protocol.get("expectation_tolerance_abs", 1e-6)
    results = []
    for check_id in protocol.get("required_checks", sorted(expectations)):
        expected = expectations.get(check_id, "<<missing>>")
        actual = checkpoints.get(check_id, "<<missing>>")
        if (isinstance(expected, (int, float)) and isinstance(actual, (int, float))
                and not isinstance(expected, bool) and not isinstance(actual, bool)):
            passed = abs(float(actual) - float(expected)) <= tolerance
        else:
            passed = actual == expected
        results.append({"check": check_id, "expected": expected,
                        "actual": actual, "passed": bool(passed)})
    return {"tolerance_abs": tolerance, "checks": results,
            "all_passed": bool(results) and all(r["passed"] for r in results)}


def _build_manifest(protocol: dict, protocol_path: Path, case_result: dict,
                    effective_targets: dict) -> dict:
    source_bytes = protocol_path.read_bytes()
    return {
        "task": "factor-research-workbench-v1 / concentrated-repair",
        "synthetic": True,
        "title": SYNTHETIC_TITLE,
        "production_authorization": "not_authorized",
        "effectiveness_claim": "none；本运行不证明任何因子有效",
        "spec_bindings": SPEC_BINDINGS,
        "registry": {"version": protocol["registry"]["version"],
                     "canonical_sha256": protocol["registry"]["canonical_sha256"]},
        "definition_cards_sha256": protocol.get("definition_cards_sha256", {}),
        "code_identity": protocol["code_identity"],
        "protocol": {
            "path": protocol_path.name,
            "version": protocol["version"],
            "file_sha256": hashlib.sha256(source_bytes).hexdigest(),
            "canonical_sha256": protocol_sha256(protocol),
        },
        "data_declarations": protocol.get("data_declarations", {}),
        "inputs": {name: {"path": spec["path"], "sha256": spec["sha256"]}
                   for name, spec in protocol["inputs"].items()},
        "targets_effective": effective_targets,
        "split_protocol": protocol.get("validation", {}).get("split"),
        "segment_cutoffs": protocol.get("validation", {}).get("segment_cutoffs"),
        "attempt_history": protocol.get("attempt_history", []),
        "executor_model": protocol.get(
            "executor_model", "not_declared_in_protocol（实际模型见执行报告）"),
        "outputs": {},  # 写manifest时现算（见 _write_manifest），保证覆盖全部落盘产物
        "artifact_metadata": {
            artifact_id: {"reference": meta["metadata"]["reference"],
                          "unit": meta["metadata"]["unit"],
                          "entity_axis": meta["metadata"]["entity_axis"],
                          "synthetic": meta["metadata"]["synthetic"]}
            for artifact_id, meta in case_result.get("artifact_meta", {}).items()
        },
    }


def _write_manifest(output_dir: Path, manifest: dict) -> None:
    # 写manifest时对已落盘产物现算哈希（manifest自身除外），逐项可追溯。
    outputs = {}
    for path in sorted(output_dir.iterdir()):
        if path.is_file() and path.name != "manifest.json":
            outputs[path.name] = _sha256_file(path)
    manifest["outputs"] = outputs
    (output_dir / "manifest.json").write_text(_dump_json(manifest), encoding="utf-8")


def _write_outputs(output_dir: Path, protocol: dict, protocol_path: Path,
                   case_result: dict, quality: dict, manifest: dict,
                   logger: _Logger) -> None:
    # 写盘顺序：协议字节副本 → 值/旁置元数据 → 诊断/审计/归因 → quality
    # → summary → run.log → manifest 最后。任何写盘失败都不得留下"已完成"的manifest。
    output_dir.mkdir(parents=True, exist_ok=False)
    try:
        (output_dir / "protocol.source.json").write_bytes(protocol_path.read_bytes())
        declared_inputs = {name: {"path": spec["path"], "sha256": spec["sha256"]}
                           for name, spec in protocol["inputs"].items()}
        for artifact_id, frame in case_result.get("artifacts", {}).items():
            frame.to_csv(output_dir / f"values_{artifact_id}.csv", index=False)
            meta = case_result.get("artifact_meta", {}).get(artifact_id, {})
            sidecar = {
                "artifact_id": artifact_id,
                "metadata": meta.get("metadata", {}),
                "findings": meta.get("findings", []),
                "declared_inputs": declared_inputs,
                "rows": int(len(frame)),
                "missing_reason_counts": {
                    str(k): int(v) for k, v in
                    frame["missing_reason"].value_counts(dropna=False).items()
                } if "missing_reason" in frame else {},
                "quality": "synthetic_only；生产授权无",
            }
            (output_dir / f"values_{artifact_id}.meta.json").write_text(
                _dump_json(sidecar), encoding="utf-8")
        targets = case_result.get("targets")
        if isinstance(targets, pd.DataFrame):
            targets.to_csv(output_dir / "targets.csv", index=False)
        elif isinstance(targets, dict):
            for name, frame in targets.items():
                frame.to_csv(output_dir / f"targets_{name}.csv", index=False)
        for name, payload in case_result.get("diagnostics", {}).items():
            (output_dir / f"diagnostics_{name}.json").write_text(
                _dump_json(payload), encoding="utf-8")
        if case_result.get("validation") is not None:
            (output_dir / "validation.json").write_text(
                _dump_json(case_result["validation"]), encoding="utf-8")
        if case_result.get("attribution") is not None:
            (output_dir / "attribution.json").write_text(
                _dump_json(case_result["attribution"]), encoding="utf-8")
        (output_dir / "quality.json").write_text(_dump_json(quality), encoding="utf-8")

        failed = [c for c in quality["checks"] if not c["passed"]]
        summary = [
            f"# {protocol['protocol_id']} v{protocol['version']} — {SYNTHETIC_TITLE}",
            "",
            f"- 协议：`{protocol_path.name}`（文件SHA前12位 "
            f"{manifest['protocol']['file_sha256'][:12]}），kind={protocol['kind']}，"
            "资料模式=synthetic（合成）",
            f"- 期望核对：{len(quality['checks'])} 项，全部通过={quality['all_passed']}",
            "- 生产授权：无；有效性声明：无（本运行不证明任何因子有效）",
            "",
            "## 期望核对明细",
            "",
        ]
        for check in quality["checks"]:
            mark = "通过" if check["passed"] else "**失败**"
            summary.append(
                f"- {mark} {check['check']}：期望 {check['expected']}，"
                f"实际 {check['actual']}"
            )
        if failed:
            summary += ["", "## 失败项说明", "",
                        "以下核对未通过，说明实现与手算期望不一致，"
                        "本运行不可作为完成证据："]
            summary += [f"- {check['check']}" for check in failed]
        (output_dir / "summary.md").write_text("\n".join(summary) + "\n",
                                               encoding="utf-8")
        (output_dir / "run.log").write_text("\n".join(logger.lines) + "\n",
                                            encoding="utf-8")
        # manifest 最后写：前面任何失败都不会留下"已完成"的 manifest。
        _write_manifest(output_dir, manifest)
    except Exception:
        with contextlib.suppress(OSError):
            (output_dir / "manifest.json").unlink(missing_ok=True)
        raise


def run_protocol(protocol_path, output_dir) -> int:
    """CLI 唯一入口：返回退出码（0/1/2/3），产出完整证据目录。"""
    protocol_path = Path(protocol_path)
    output_dir = Path(output_dir)
    raw_dir = protocol_path.parent
    repo_root = Path(__file__).resolve().parents[4]
    log_lines: list[str] = []

    def log(message: str) -> None:
        log_lines.append(message)

    def flush_log() -> None:
        with contextlib.suppress(OSError):
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "run.log").write_text("\n".join(log_lines) + "\n",
                                                encoding="utf-8")

    if output_dir.exists():
        print(f"refusing to overwrite existing output dir: {output_dir}",
              file=sys.stderr)
        return EXIT_IDENTITY_FORMAT
    try:
        protocol = _load_protocol(protocol_path)
        log(f"protocol loaded: {protocol_path.name} v{protocol['version']} "
            f"case={protocol['case']}")
        paths = _verify_inputs(protocol, raw_dir)
        log(f"inputs verified: {len(paths)}")
        frozen = verify_frozen_contract(protocol, repo_root, raw_dir)
        log("frozen contract verified: code keys, registry, cards, targets, "
            "declarations, required checks, expectation source")
        loaded = {name: _load_input(name, spec, paths[name])
                  for name, spec in protocol["inputs"].items()}
        runner = CASE_RUNNERS[protocol["case"]]
        case_result = runner(protocol, paths, loaded, _Logger(log_lines))
        log("case runner finished")
        quality = _compare_expectations(protocol, case_result["checkpoints"])
        log(f"expectations: {len(quality['checks'])} checks, "
            f"all_passed={quality['all_passed']}")
        manifest = _build_manifest(protocol, protocol_path, case_result,
                                   frozen["effective_targets"])
        _write_outputs(output_dir, protocol, protocol_path, case_result, quality,
                       manifest, _Logger(log_lines))
        if not quality["all_passed"]:
            print("expectation checks failed; see quality.json", file=sys.stderr)
            return 1
        return 0
    except InsufficientDataError as exc:
        log(f"INSUFFICIENT_DATA: {exc}")
        with contextlib.suppress(Exception):
            output_dir.mkdir(parents=True, exist_ok=False)
            (output_dir / "quality.json").write_text(
                _dump_json({"status": "insufficient", "reasons": [str(exc)],
                            "all_passed": False, "checks": []}), encoding="utf-8")
            flush_log()
        print(f"legal data insufficiency: {exc}", file=sys.stderr)
        return 2
    except IdentityFormatError as exc:
        log(f"IDENTITY_FORMAT_ERROR: {exc}")
        with contextlib.suppress(Exception):
            flush_log()
        print(f"identity/format failure: {exc}", file=sys.stderr)
        return EXIT_IDENTITY_FORMAT
    except Exception as exc:  # 未预期错误：完整日志不丢失，不留"已完成"manifest
        log("UNEXPECTED_ERROR:\n" + traceback.format_exc())
        log("WRITE_FAILURE: output incomplete; manifest withheld")
        with contextlib.suppress(OSError):
            (output_dir / "manifest.json").unlink(missing_ok=True)
            flush_log()
        print(f"unexpected error: {exc}", file=sys.stderr)
        return 1
