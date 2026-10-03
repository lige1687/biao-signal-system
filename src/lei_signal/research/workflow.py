"""Controlled new-research branch of Factor Lab. Historical runners stay frozen.

Gates run BEFORE statistical callbacks, and are rerun before publication. Receipt
verification is application-level audit, not an OS sandbox or cryptographic proof
against a user who can rewrite the code, artifacts and journal together.
"""
from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import math
import signal
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from lei_signal.research import definitions
from lei_signal.research.candidate_preflight import PreflightRegistry
from lei_signal.research.input_preflight import inspect_input
from lei_signal.research.question_contract import validate_workflow_contract

ROOT = Path(__file__).resolve().parents[3]
CATALOG = "docs/research/current-standards.json"
CODE_PATHS = (
    "src/lei_signal/research/workflow.py",
    "src/lei_signal/research/workflow_inputs.py",
    "src/lei_signal/research/workflow_evaluation.py",
    "src/lei_signal/research/question_contract.py",
    "src/lei_signal/research/input_preflight.py",
    "src/lei_signal/research/candidate_preflight.py",
    "src/lei_signal/research/definitions.py",
    "scripts/run_factor_lab.py",
)
COST_EVENTS = {"finish", "rehearsal", "acceptance", "gate_attempt"}


class WorkflowBlocked(ValueError):
    """Invalid execution/publication, never evidence that a factor is ineffective."""


class WorkflowPaused(WorkflowBlocked):
    """Budget interruption; never a scientific verdict."""


def digest(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Never turn NaN into 0 or erase a failed output.
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def resolve_path(root, name):
    return (Path(root) / name).expanduser().resolve()


def _verify_research_design_qualification(contract, rows, root):
    """Bind 1.1 design declarations to a hashed qualification artifact and rows."""
    if contract.get("schema_version") != "research-workflow/1.1":
        return
    sample = contract["research_design"]["sample_fit"]
    path = resolve_path(root, sample["qualification_artifact"])
    if file_hash(path) != sample["qualification_sha256"]:
        raise WorkflowBlocked("research-design qualification artifact hash differs from the declared SHA-256")
    try:
        artifact = read_json(path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WorkflowBlocked(f"research-design qualification artifact is unreadable JSON: {exc}") from exc
    if not isinstance(artifact, dict):
        raise WorkflowBlocked("research-design qualification artifact must be a JSON object")
    if artifact.get("data_sha256") != contract["data"].get("sha256"):
        raise WorkflowBlocked("research-design qualification artifact data_sha256 differs from workflow data SHA-256")
    if artifact.get("outcome_values_used_for_design") is not False:
        raise WorkflowBlocked("research-design qualification artifact must state outcome_values_used_for_design=false")
    counts = artifact.get("counts")
    if not isinstance(counts, dict):
        raise WorkflowBlocked("research-design qualification artifact must contain counts object")
    if not {"assets", "observations", "dates", "episodes"} <= counts.keys():
        raise WorkflowBlocked("research-design qualification artifact counts must include assets, observations, dates, and episodes")
    actual = {
        "assets": len({row["asset"] for row in rows}),
        "observations": len(rows),
        "dates": len({row["date"] for row in rows}),
    }
    declared = {key: sample[key] for key in ("assets", "observations", "dates")}
    if declared != actual:
        raise WorkflowBlocked(f"research-design sample_fit counts differ from scheduled observations: declared={declared}, actual={actual}")
    for key, value in actual.items():
        if type(counts.get(key)) is not int or counts[key] != value:
            raise WorkflowBlocked(f"research-design qualification artifact counts.{key} differs from period observations")
    episodes = sample["episodes"]
    if episodes is not None:
        if any("episode_id" not in row for row in rows):
            raise WorkflowBlocked("episode count was declared but observations have no episode_id field")
        actual_episodes = len({(row["asset"], row["episode_id"]) for row in rows
                               if row["episode_id"] is not None and str(row["episode_id"]).strip()})
        if episodes != actual_episodes or type(counts.get("episodes")) is not int or counts["episodes"] != actual_episodes:
            raise WorkflowBlocked("research-design qualification artifact or sample_fit episode count differs from observations")
    elif counts.get("episodes") is not None:
        raise WorkflowBlocked("research-design qualification artifact counts.episodes must be null when sample_fit episodes is null")


def family_ledger(root, family):
    # Task name, output name, caller-selected ledger name cannot reset this budget.
    return Path(root) / "docs/experiments/raw/research-workflow-ledgers-2026-09-29" / digest(family)[:24] / "attempts.jsonl"


@contextmanager
def locked_journal(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        stream.seek(0)
        records = [json.loads(line) for line in stream if line.strip()]
        yield stream, records
        stream.flush()
        fcntl.flock(stream, fcntl.LOCK_UN)


@contextmanager
def family_execution_lock(root, contract):
    path = family_ledger(root, contract["history"]["family"]).with_name("execution.lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise WorkflowBlocked("one family already running: concurrent jobs cannot share the same remaining budget") from exc
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def _append(stream, value):
    stream.seek(0, 2)
    stream.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n")
    stream.flush()


def _closure(registry, refs):
    selected = {}
    def visit(ref):
        if ref in selected:
            return
        card = definitions.resolve(registry, ref)
        if not set(card["uses"]) & {"description", "research_signal", "comparison", "diagnostic"}:
            raise WorkflowBlocked(f"definition has no allowed research use: {ref}")
        status_text = json.dumps(card, ensure_ascii=False)
        if "OUT_OF_SCOPE" in status_text or card.get("research_owner") == "sentiment_agent":
            raise WorkflowBlocked(f"out_of_scope: {ref}")
        selected[ref] = card
        for dep in card.get("dependencies", []):
            visit(dep)
    for ref in refs:
        visit(ref)
    return selected


def actual_bindings(contract, root=ROOT):
    """Dependency-specific fingerprints, not a hash of the whole active registry."""
    root = Path(root)
    catalog = read_json(root / CATALOG)
    registry = definitions.load_registry(root / catalog["definition_registry"])
    cards = _closure(registry, contract["question"]["factor_refs"])
    files = {CATALOG: file_hash(root / CATALOG)}
    versions = {}
    for key, item in catalog["standards"].items():
        if item["version"] not in (root / item["path"]).read_text(encoding="utf-8"):
            raise WorkflowBlocked(f"central standard version not present in actual document: {key}")
        files[item["path"]] = file_hash(root / item["path"])
        versions[key] = item["version"]
    related_code = list(CODE_PATHS)
    if contract["feature"]["kind"] == "ema_only_wait_age_information":
        related_code.extend(("src/lei_signal/research/ema_only_wait_age_information.py",
                             "src/lei_signal/research/deduction_box_information.py",
                             "src/lei_signal/research/top_structure_information.py",
                             "src/lei_signal/research/volume_information.py"))
    if contract["feature"]["kind"] == "ema_sma_waiting_path":
        related_code.extend(("src/lei_signal/research/ema_sma_waiting_path.py",
                             "src/lei_signal/research/top_structure_information.py",
                             "src/lei_signal/research/volume_information.py"))
    if contract["feature"]["kind"] == "prior_top_dual_break_information":
        related_code.extend(("src/lei_signal/research/prior_top_dual_break_information.py",
                             "src/lei_signal/research/key_fluctuation_information.py",
                             "src/lei_signal/research/top_invalidation_information.py",
                             "src/lei_signal/research/top_structure_information.py",
                             "src/lei_signal/research/volume_information.py",
                             "src/lei_signal/features/indicators.py",
                             "src/lei_signal/rules/clock_classifier.py",
                             "src/lei_signal/domain/rules_config.py", "configs/rules.v2.yaml"))
    if contract["feature"]["kind"] == "pullback_layer_change_information":
        related_code.extend(("src/lei_signal/research/pullback_layer_change_information.py",
                             "src/lei_signal/research/a03_pullback_order.py",
                             "src/lei_signal/research/top_structure_information.py",
                             "src/lei_signal/research/volume_information.py",
                             "src/lei_signal/features/pivots.py",
                             "src/lei_signal/features/indicators.py",
                             "src/lei_signal/rules/clock_classifier.py",
                             "src/lei_signal/domain/rules_config.py",
                             "configs/rules.v2.yaml"))
    if contract["feature"]["kind"] in {"slope_change_information", "simple_top_invalidation_information"}:
        semantic_adapter = ("trend_slope_change_information" if
                            contract["feature"]["kind"] == "slope_change_information" else
                            "top_invalidation_information")
        related_code.extend((f"src/lei_signal/research/{semantic_adapter}.py",
                             "src/lei_signal/research/top_structure_information.py",
                             "src/lei_signal/research/volume_information.py",
                             "src/lei_signal/features/indicators.py",
                             "src/lei_signal/domain/rules_config.py",
                             "configs/rules.v2.yaml"))
        if contract["feature"]["kind"] == "slope_change_information":
            related_code.append("src/lei_signal/rules/clock_classifier.py")
    if contract["feature"]["kind"] == "tsfresh_price_information":
        related_code.extend(("src/lei_signal/research/tsfresh_price_information.py",
                             "src/lei_signal/research/trend_slope_change_information.py",
                             "src/lei_signal/research/top_structure_information.py",
                             "src/lei_signal/research/volume_information.py",
                             "src/lei_signal/features/indicators.py",
                             "src/lei_signal/rules/clock_classifier.py",
                             "src/lei_signal/domain/rules_config.py",
                             "configs/rules.v2.yaml",
                             ".agents/skills/lei-quant-tools/scripts/tsfresh_calculators.py",
                             ".agents/skills/lei-quant-tools/scripts/tsfresh-LICENSE.txt"))
    if contract["feature"]["kind"] == "double_ma_order_information":
        related_code.extend(("src/lei_signal/research/double_ma_order_information.py", "src/lei_signal/features/indicators.py"))
    if contract["feature"]["kind"] == "a01_signed_band":
        related_code.append("src/lei_signal/research/a01_index_features.py")
    if contract["feature"]["kind"] == "ma_cluster_information":
        related_code.extend(("src/lei_signal/research/a01_index_features.py",
                             "src/lei_signal/research/ma_cluster_information.py"))
    if contract["feature"]["kind"] == "volume_anomaly_information":
        related_code.append("src/lei_signal/research/volume_information.py")
    if contract["feature"]["kind"] == "key_fluctuation_information":
        related_code.extend(("src/lei_signal/research/key_fluctuation_information.py",
                             "src/lei_signal/research/top_structure_information.py",
                             "src/lei_signal/research/volume_information.py"))
    if contract["feature"]["kind"] == "profile_overhead_information":
        related_code.extend(("src/lei_signal/research/profile_information.py",
                             "src/lei_signal/features/volume_profile.py",
                             "src/lei_signal/research/volume_information.py",
                             "src/lei_signal/research/top_structure_information.py"))
    if contract["feature"]["kind"] == "simple_top3_information":
        related_code.extend(("src/lei_signal/research/top_structure_information.py",
                             "src/lei_signal/research/volume_information.py"))
    if contract["feature"]["kind"] == "future_deduction_box_information":
        related_code.extend(("src/lei_signal/research/deduction_box_information.py",
                             "src/lei_signal/research/volume_information.py"))
    if contract["feature"]["kind"] == "a03_pullback_order":
        related_code.extend(("src/lei_signal/research/a01_index_features.py",
                             "src/lei_signal/research/a03_pullback_order.py"))
    if contract["feature"]["kind"] == "space_prior_target":
        related_code.extend(("src/lei_signal/research/a01_index_features.py",
                             "src/lei_signal/research/space_prior_target.py",
                             "src/lei_signal/features/pivots.py",
                             "src/lei_signal/rules/resistance_b1.py"))
    if contract["data"].get("qualification", {}).get("adapter") == "tencent_index_price/1.0":
        related_code.append("src/lei_signal/research/provider_index_input.py")
    if contract.get("descriptive"):
        related_code.append("src/lei_signal/research/workflow_descriptions.py")
    for name in related_code:
        files[name] = file_hash(root / name)
    source_config = root / catalog["strategy_sources"]
    files[catalog["strategy_sources"]] = file_hash(source_config)
    strategy = read_json(source_config)
    for document in strategy["documents"]:
        p = Path(strategy["canonical_directory"]).expanduser() / document["file_name"]
        actual = file_hash(p)
        if actual != document["approved_sha256"]:
            raise WorkflowBlocked(f"strategy source changed; confirm meaning before new research: {p}")
        files[str(p)] = actual
    data_path = resolve_path(root, contract["data"]["path"])
    data_hash = file_hash(data_path)
    if data_hash != contract["data"]["sha256"]:
        raise WorkflowBlocked("stale_data: actual input differs from contract")
    for item in contract["sources"]:
        p = resolve_path(root, item["path"])
        if file_hash(p) != item["sha256"]:
            raise WorkflowBlocked(f"stale_source: {item['path']}")
        files[item["path"]] = item["sha256"]
    # Snapshot quality artifacts are also dependencies of real-data eligibility.
    qualification = contract["data"].get("qualification", {})
    for key, name in qualification.items():
        if key.endswith("_path") and key != "registry_path":
            p = resolve_path(root, name)
            files[str(p)] = file_hash(p)
        elif key == "snapshot_dir":
            for p in sorted(resolve_path(root, name).rglob("*")):
                if p.is_file():
                    files[str(p)] = file_hash(p)
            manifest = read_json(resolve_path(root, name) / "snapshot.json")
            for transform in manifest.get("semantics", {}).get("economic_transforms", {}).values():
                for source in (transform.get("nominal", {}), transform.get("actions", {})):
                    if source.get("path"):
                        p = resolve_path(resolve_path(root, name), source["path"])
                        if file_hash(p) != source.get("sha256"):
                            raise WorkflowBlocked("economic transform source changed")
                        files[str(p)] = file_hash(p)
    return {"files": files, "versions": versions, "definition_closure": cards,
            "data_sha256": data_hash}


def cache_keys(contract, bindings):
    """Report words excluded; aggregation-only changes keep prediction identity."""
    feature = digest({"data": bindings["data_sha256"], "feature": contract["feature"],
                      "definitions": bindings["definition_closure"],
                      "code": bindings["files"][CODE_PATHS[1]],
                      "feature_adapter": [bindings["files"].get(name) for name in
                          ("src/lei_signal/research/a01_index_features.py",
                           "src/lei_signal/research/ma_cluster_information.py",
                           "src/lei_signal/research/volume_information.py",
                           "src/lei_signal/research/key_fluctuation_information.py",
                           "src/lei_signal/research/profile_information.py",
                           "src/lei_signal/research/trend_slope_change_information.py",
                           "src/lei_signal/research/tsfresh_price_information.py",
                           ".agents/skills/lei-quant-tools/scripts/tsfresh_calculators.py",
                           ".agents/skills/lei-quant-tools/scripts/tsfresh-LICENSE.txt",
                           "src/lei_signal/research/top_invalidation_information.py",
                           "src/lei_signal/features/indicators.py",
                           "src/lei_signal/rules/clock_classifier.py",
                           "src/lei_signal/domain/rules_config.py",
                           "configs/rules.v2.yaml",
                           "src/lei_signal/features/volume_profile.py",
                           "src/lei_signal/research/top_structure_information.py",
                           "src/lei_signal/research/deduction_box_information.py",
                           "src/lei_signal/research/a03_pullback_order.py",
                           "src/lei_signal/research/space_prior_target.py",
                           "src/lei_signal/features/pivots.py",
                           "src/lei_signal/rules/resistance_b1.py")],
                      "universe": contract["universe"],
                      "sampling": {k: contract["question"].get(k) for k in ("sampling", "frequency", "period", "event_definition")}})
    labels = digest({"data": bindings["data_sha256"], "target": contract["target"],
                     "code": bindings["files"][CODE_PATHS[1]]})
    if contract["feature"]["kind"] == "ema_sma_waiting_path":
        adapter = bindings["files"]["src/lei_signal/research/ema_sma_waiting_path.py"]
        feature = digest({"base": feature, "waiting_path_adapter": adapter})
        labels = digest({"base": labels, "waiting_path_adapter": adapter})
    if contract["feature"]["kind"] == "pullback_layer_change_information":
        adapter = bindings["files"]["src/lei_signal/research/pullback_layer_change_information.py"]
        feature = digest({"base": feature, "pullback_layer_adapter": adapter,
                          "pivots": bindings["files"]["src/lei_signal/features/pivots.py"]})
        labels = digest({"base": labels, "pullback_layer_adapter": adapter})
    if contract["feature"]["kind"] in {"slope_change_information", "simple_top_invalidation_information"}:
        semantic_adapter = ("trend_slope_change_information" if
                            contract["feature"]["kind"] == "slope_change_information" else
                            "top_invalidation_information")
        labels = digest({"base": labels, "adapter": bindings["files"][f"src/lei_signal/research/{semantic_adapter}.py"]})
    if contract["feature"]["kind"] == "tsfresh_price_information":
        labels = digest({"base": labels,
                         "adapter": bindings["files"]["src/lei_signal/research/tsfresh_price_information.py"],
                         "slope_label_path": bindings["files"]["src/lei_signal/research/trend_slope_change_information.py"]})
    if contract["feature"]["kind"] == "double_ma_order_information":
        adapter = bindings["files"]["src/lei_signal/research/double_ma_order_information.py"]
        feature = digest({"base": feature, "T03_adapter": adapter, "seeded_indicators": bindings["files"]["src/lei_signal/features/indicators.py"]})
        labels = digest({"base": labels, "T03_label_adapter": adapter})
    if contract["feature"]["kind"] in {"key_fluctuation_information", "profile_overhead_information"}:
        adapter_name = ("src/lei_signal/research/key_fluctuation_information.py" if
                        contract["feature"]["kind"] == "key_fluctuation_information" else
                        "src/lei_signal/research/profile_information.py")
        labels = digest({"base": labels, "adapter_label_path": bindings["files"][adapter_name]})
    if contract["feature"]["kind"] == "prior_top_dual_break_information":
        feature = digest({"base": feature, "combination_adapter": bindings["files"]["src/lei_signal/research/prior_top_dual_break_information.py"]})
        labels = digest({"base": labels, "combination_adapter": bindings["files"]["src/lei_signal/research/prior_top_dual_break_information.py"],
                         "key_adapter": bindings["files"]["src/lei_signal/research/key_fluctuation_information.py"]})
    prediction = digest({"features": feature, "labels": labels, "split": contract["split"],
                         "evaluator": contract["evaluator"],
                         "training_weights": contract.get("training_weights", "equal_asset"),
                         "code": bindings["files"][CODE_PATHS[2]]})
    aggregate = digest({"prediction": prediction, "weights": contract["weights"], "descriptive": contract.get("descriptive"),
                        "dependence": contract["dependence"], "code": bindings["files"][CODE_PATHS[2]]})
    return {"features": feature, "labels": labels, "prediction": prediction, "aggregate": aggregate}


def _warning(code, message):
    return {"code": code, "message": message}


def qualify_panel(payload, contract, qualification, snapshot):
    """Bind the actual panel to existing source/calendar facts, not caller flags.

    Unknown corporate-action coverage does not become known through an empty
    action list. Current snapshot import does not establish actionable opens;
    that use is deliberately blocked until an opening-session adapter exists.
    """
    from lei_signal.research.trading_calendar import TradingCalendar
    from lei_signal.research.data_quality import _validated_halts, _halt_index
    from lei_signal.research.symbol_identity import parse_identity
    import pandas as pd
    q = qualification
    calendar = TradingCalendar.from_file(q["calendar_path"], q["publication_path"])
    dates = payload["calendar"]
    if [q["evaluation_start"], q["evaluation_end"]] != [dates[0], dates[-1]]:
        raise WorkflowBlocked("qualification period must cover actual warmup/observation/label calendar")
    if q["use"] not in {"research_signal", "comparison", "diagnostic"}:
        raise WorkflowBlocked("description-only qualification cannot authorize prediction evaluation")
    expected = [d for d in sorted(calendar._days) if dates[0] <= d <= dates[-1] and calendar.is_trading_day(d)]
    if dates != expected or not calendar.coverage(dates[0], dates[-1]).complete:
        raise WorkflowBlocked("panel calendar differs from the qualified full trading calendar")
    if contract["question"]["sampling"] == "periodic":
        from datetime import date, timedelta
        frequency = contract["question"]["frequency"]
        for explicit_end in payload.get("completed_period_ends", []):
            end = date.fromisoformat(explicit_end)
            later = end + timedelta(days=1)
            while (later.isocalendar()[:2] == end.isocalendar()[:2] if frequency == "weekly" else later.month == end.month):
                if (frequency == "monthly" or later.weekday() < 5) and calendar.status(later).status != "closed":
                    raise WorkflowBlocked("unfinished period: source calendar does not prove declared period end")
                later += timedelta(days=1)
    actions = read_json(q["actions_path"])
    events = actions.get("events", [])
    valid_halts, _ = _validated_halts(events, list(snapshot.frames))
    halt_index = _halt_index(valid_halts)
    rows = {(b["asset"], b["date"]): b for b in payload["bars"]}
    transforms = snapshot.snapshot["semantics"].get("economic_transforms", {})
    computed_scales = {}
    for asset, transform in transforms.items():
        if transform.get("operator") != "definitions.economic_index/1.0":
            raise WorkflowBlocked("unimplemented economic price transform")
        sources = {}
        for key in ("nominal", "actions"):
            source = transform[key]
            p = resolve_path(q["snapshot_dir"], source["path"])
            if file_hash(p) != source["sha256"]:
                raise WorkflowBlocked("economic transform source differs from declared bytes")
            sources[key] = p
        raw = pd.read_csv(sources["nominal"], parse_dates=["date"]).set_index("date")
        action_events = read_json(sources["actions"]).get("events", [])
        economic = definitions.economic_index(raw.close, [a for a in action_events if a.get("symbol") == asset and a.get("type") in {"cash_dividend", "split"}])
        computed_scales[asset] = (raw, economic)
    if contract["target"]["entry_field"] == "open":
        raise WorkflowBlocked("real actionable opening-session evidence adapter is not implemented; open_actionable=true is not proof")
    for asset in contract["universe"]["assets"]:
        frame = snapshot.frames.get(asset)
        if frame is None:
            continue  # partial universe gate handles absent assets
        identity = parse_identity(asset, require_registered=False)
        for d in dates:
            b = rows.get((asset, d))
            when = pd.Timestamp(d)
            quoted = when in frame.index and pd.notna(frame.loc[when, "close"])
            if quoted:
                if b is None or b["status"] != "quoted":
                    raise WorkflowBlocked("panel hides a real snapshot quote as a gap/halt")
                for field in ("close", "open", "high", "low"):
                    v = b.get(field)
                    source_value = frame.loc[when, field] if field in frame.columns else None
                    if pd.notna(source_value) and v is None:
                        raise WorkflowBlocked("panel hides an actual snapshot price field as missing")
                    if v is not None and (pd.isna(source_value) or not math.isclose(float(v), float(source_value), rel_tol=1e-10)):
                        raise WorkflowBlocked("panel price differs from qualified snapshot")
                if b.get("action_known") is True and asset not in computed_scales:
                    raise WorkflowBlocked("corporate-action scale is unproven; caller action_known=true cannot qualify labels")
                if asset in computed_scales:
                    raw, economic = computed_scales[asset]
                    if when not in raw.index or not math.isfinite(float(economic.loc[when])):
                        raise WorkflowBlocked("economic transform has no qualified quote at this date")
                    scale = economic.loc[when] / raw.loc[when, "close"]
                    for field in ("open", "high", "low", "close"):
                        if b.get(field) is not None and not math.isclose(float(b[field]), float(raw.loc[when, field] * scale), rel_tol=1e-10):
                            raise WorkflowBlocked("economic price differs from actual recomputed nominal/actions transform")
            elif b is not None and b["status"] == "quoted":
                raise WorkflowBlocked("panel fabricates a quote absent from the snapshot")
            elif b is not None and b["status"] == "halt":
                if (identity.bare_code, d) not in halt_index:
                    raise WorkflowBlocked("halt status has no validated source event")
    # These facts are a restricted reconstruction, not arrival-time certification.
    return {"calendar_bound": True, "prices_bound": True, "action_scale_bound": bool(computed_scales),
            "action_history_completeness": "not_proved_by_empty_event_list",
            "opening_actionability": "unsupported", "historical_arrival": "not_certified"}


def preflight(contract, root=ROOT, *, require_frozen=True):
    """Actual input-derived evidence. This function does not fit or do final statistics."""
    from lei_signal.research.input_preflight import inspect_workflow_input
    validate_workflow_contract(contract)
    if contract["feature"]["kind"] == "prior_top_dual_break_information" and not (
            contract.get("permissions", {}).get("real_labels") is True and
            contract.get("permissions", {}).get("effect_authorized") is True and
            contract.get("permissions", {}).get("real_fits") == 4):
        raise WorkflowBlocked("prior-top combination requires explicit effect permission and four-fit ceiling")
    if contract["feature"]["kind"] == "pullback_layer_change_information" and not (
            contract.get("permissions", {}).get("real_labels") is True and
            contract.get("permissions", {}).get("effect_authorized") is True and
            contract.get("permissions", {}).get("real_fits") == 4):
        raise WorkflowBlocked("pullback-layer study requires explicit label/effect permission and four-fit ceiling")
    if contract["feature"]["kind"] in {"slope_change_information", "simple_top_invalidation_information"} and not (
            contract.get("permissions", {}).get("real_labels") is True and
            contract.get("permissions", {}).get("effect_authorized") is True and
            contract.get("permissions", {}).get("real_fits") == 4):
        raise WorkflowBlocked("semantic studies require explicit label/effect permission and four-fit ceiling")
    if contract["feature"]["kind"] == "tsfresh_price_information" and not (
            contract.get("permissions", {}).get("real_labels") is True and
            contract.get("permissions", {}).get("effect_authorized") is True and
            type(contract.get("permissions", {}).get("real_fits")) is int and
            contract["permissions"]["real_fits"] == 4):
        raise WorkflowBlocked("tsfresh price study requires explicit label/effect permission and four-fit ceiling")
    if contract["feature"]["kind"] == "key_fluctuation_information" and not (contract.get("permissions", {}).get("real_labels") is True and contract.get("permissions", {}).get("effect_authorized") is True and contract.get("permissions", {}).get("real_fits") == 4):
        raise WorkflowBlocked("K01 preparation has no real-label/effect authorization; use no-label qualification only")
    if contract["feature"]["kind"] == "profile_overhead_information" and not (contract.get("permissions", {}).get("real_labels") is True and contract.get("permissions", {}).get("effect_authorized") is True and contract.get("permissions", {}).get("real_fits") == 4):
        raise WorkflowBlocked("P01 preparation has no real-label/effect authorization; use no-label qualification only")
    if contract["feature"]["kind"] == "double_ma_order_information" and not (contract.get("permissions", {}).get("real_labels") is True and contract.get("permissions", {}).get("effect_authorized") is True and contract.get("permissions", {}).get("real_fits") == 4):
        raise WorkflowBlocked("T03 preparation has no real-label/effect authorization; use schema/qualification binding checks only")
    if contract["feature"]["kind"] == "ema_only_wait_age_information" and not (
            contract.get("permissions", {}).get("real_labels") is True and
            contract.get("permissions", {}).get("effect_authorized") is True and
            contract.get("permissions", {}).get("real_fits") == 4):
        raise WorkflowBlocked("current-age study requires explicit real label/effect permission and four-fit ceiling")
    bindings = actual_bindings(contract, root)
    if require_frozen and contract.get("bindings") != bindings:
        raise WorkflowBlocked("stale_proof: freeze does not match this input/definition/code")
    if contract.get("permissions", {}).get("paid_requests", 0) or contract.get("permissions", {}).get("production", False):
        raise WorkflowBlocked("paid/production work is outside this technical research entry")
    ledger = family_ledger(root, contract["history"]["family"])
    if resolve_path(root, contract["history"]["ledger_path"]) != ledger.resolve():
        raise WorkflowBlocked("ledger must use the stable research-family path")
    payload = read_json(resolve_path(root, contract["data"]["path"]))
    if require_frozen and contract.get("calendar") != payload.get("calendar"):
        raise WorkflowBlocked("stale_calendar: frozen calendar differs from actual input")
    if len(payload.get("bars", [])) > contract["budget"]["max_rows"]:
        raise WorkflowBlocked("input row budget exceeded")
    if payload.get("data_mode", contract["data"]["mode"]) != contract["data"]["mode"]:
        raise WorkflowBlocked("payload data mode differs from the contract")
    warnings = []
    provider_index = contract["data"].get("qualification", {}).get("adapter") == "tencent_index_price/1.0"
    volume_etf = contract["data"].get("qualification", {}).get("adapter") == "volume_etf_economic/1.0"
    key_etf = contract["data"].get("qualification", {}).get("adapter") == "key_etf_economic/1.0"
    profile_etf = contract["data"].get("qualification", {}).get("adapter") == "profile_etf_economic/1.0"
    top_etf = contract["data"].get("qualification", {}).get("adapter") == "top_etf_economic/1.0"
    deduction_etf = contract["data"].get("qualification", {}).get("adapter") == "deduction_etf_economic/1.0"
    double_order_etf = contract["data"].get("qualification", {}).get("adapter") == "double_order_etf_economic/1.0"
    if contract["data"]["mode"] != "synthetic" and double_order_etf:
        from lei_signal.research.double_ma_order_information import qualify_double_order_panel
        try:
            quality = qualify_double_order_panel(payload, contract, root)
        except (ValueError, KeyError, TypeError) as exc:
            raise WorkflowBlocked(f"T03 economic close/source qualification failed: {exc}") from exc
        warnings.extend(_warning("t03_retrospective", str(w)) for w in quality["warnings"])
    elif contract["data"]["mode"] != "synthetic" and deduction_etf:
        from lei_signal.research.deduction_box_information import qualify_deduction_panel
        try:
            quality = qualify_deduction_panel(payload, contract, root)
        except (ValueError, KeyError, TypeError) as exc:
            raise WorkflowBlocked(f"D01 economic OHLC/source qualification failed: {exc}") from exc
        for item in quality.get("warnings", []):
            warnings.append(item if isinstance(item, dict) else _warning("deduction_price_scope", item))
    elif contract["data"]["mode"] != "synthetic" and profile_etf:
        from lei_signal.research.profile_information import qualify_profile_panel
        try:
            quality = qualify_profile_panel(payload, contract, root)
        except (ValueError, KeyError, TypeError) as exc:
            raise WorkflowBlocked(f"P01 economic OHLCV/source qualification failed: {exc}") from exc
        for item in quality.get("warnings", []):
            warnings.append(item if isinstance(item, dict) else _warning("profile_price_scope", item))
    elif contract["data"]["mode"] != "synthetic" and key_etf:
        from lei_signal.research.key_fluctuation_information import qualify_key_panel
        try:
            quality = qualify_key_panel(payload, contract, root)
        except (ValueError, KeyError, TypeError) as exc:
            raise WorkflowBlocked(f"K01 economic OHLC/source qualification failed: {exc}") from exc
        for item in quality.get("warnings", []):
            warnings.append(item if isinstance(item, dict) else _warning("key_price_scope", item))
    elif contract["data"]["mode"] != "synthetic" and top_etf:
        from lei_signal.research.top_structure_information import qualify_top_panel
        try:
            quality = qualify_top_panel(payload, contract, root)
        except (ValueError, KeyError, TypeError) as exc:
            raise WorkflowBlocked(f"T01 economic OHLC/source qualification failed: {exc}") from exc
        for item in quality.get("warnings", []):
            warnings.append(item if isinstance(item, dict) else _warning("top_price_scope", item))
    elif contract["data"]["mode"] != "synthetic" and volume_etf:
        from lei_signal.research.volume_information import qualify_volume_panel
        try:
            quality = qualify_volume_panel(payload, contract, root)
        except (ValueError, KeyError, TypeError) as exc:
            raise WorkflowBlocked(f"V01 economic price/volume source qualification failed: {exc}") from exc
        for item in quality.get("warnings", []):
            warnings.append(item if isinstance(item, dict) else _warning("volume_price_scope", item))
    elif contract["data"]["mode"] != "synthetic" and provider_index:
        from lei_signal.research.provider_index_input import qualify_provider_index_panel
        try:
            quality = qualify_provider_index_panel(payload, contract, root)
        except (ValueError, KeyError, TypeError) as exc:
            raise WorkflowBlocked(f"provider index price qualification failed: {exc}") from exc
        for item in quality.get("warnings", []):
            warnings.append(item if isinstance(item, dict) else _warning("provider_price_scope", item))
    elif contract["data"]["mode"] != "synthetic":
        q = copy.deepcopy(contract["data"].get("qualification", {}))
        mandatory = {"snapshot_dir", "calendar_path", "publication_path", "actions_path", "registry_path", "use", "evaluation_start", "evaluation_end"}
        if not mandatory <= q.keys():
            raise WorkflowBlocked("real input needs existing input_preflight snapshot/use qualification")
        for key in mandatory:
            if key.endswith("_path") or key == "snapshot_dir":
                q[key] = resolve_path(root, q[key])
        requested_registry = q["registry_path"]
        if requested_registry != (Path(root) / "docs/research/definitions.v1.json").resolve():
            raise WorkflowBlocked("new research uses selected closure from the active definition registry")
        # Use this existing entry for snapshot/data-use quality. Exact selected
        # definition closure is already checked separately; do not hash/verify
        # every unrelated registered object as an input dependency.
        q["refs"] = ()
        q["registry_path"] = None
        quality = inspect_input(**q)
        if not quality["request_satisfied"]:
            raise WorkflowBlocked("real data-use qualification failed: " + json.dumps(quality["errors"]))
        from lei_signal.research.data_snapshot import load_snapshot
        snapshot = load_snapshot(q["snapshot_dir"])
        semantics = qualify_panel(payload, contract, q, snapshot)
        if semantics["action_history_completeness"] != "proved":
            warnings.append(_warning("action_coverage", "仅核对给定名义报价和已记录行动生成的经济价格；未证明行动历史完整，不能声称覆盖所有分红、拆并及退出事件。"))
            if contract["publication"]["conclusion"] == "supported":
                raise WorkflowBlocked("unproven action-history coverage limits this real input to inconclusive/unsupported reconstruction")
        warnings.append(_warning("historical_arrival", "历史到达时间和资产身份适用范围仍按快照限制；回溯结果不自动成为未见资料。"))
    result = inspect_workflow_input(payload, contract)
    start, end = contract["question"]["period"]
    rows = [r for r in result["observations"] if start <= r["date"] <= end]
    _verify_research_design_qualification(contract, rows, root)
    for fold in contract["split"]["folds"]:
        if not start <= fold["train_end"] < fold["eval_start"] <= fold["eval_end"] <= end:
            raise WorkflowBlocked("split is outside declared research period")
    actual_assets = sorted({b["asset"] for b in payload["bars"] if b["status"] == "quoted" and b["asset"] in contract["universe"]["assets"]})
    quote_missing = sorted(set(contract["universe"]["assets"]) - set(actual_assets))
    # Actual-builder prefix check; do not compare labels (they necessarily mature later).
    dates = sorted({r["date"] for r in rows})
    prefix_checks = []
    # The real waiting adapter binds the complete panel bytes. Truncating those
    # bytes without a newly bound source is invalid, so its all-date independent
    # recurrence check below replaces these generic two-cutoff probes.
    cutoffs = ([] if contract["feature"]["kind"] == "ema_sma_waiting_path" else
               dates[len(dates)//2:len(dates)//2+1] + dates[-2:-1])
    for cutoff in cutoffs:
        prefix_payload = {**payload, "bars": [b for b in payload["bars"] if b["date"] <= cutoff]}
        prior = inspect_workflow_input(prefix_payload, contract)["observations"]
        expected = {r["id"]: (r["features"], r["tested_condition"]) for r in rows if r["date"] <= cutoff}
        found = {r["id"]: (r["features"], r["tested_condition"]) for r in prior if start <= r["date"] <= cutoff}
        if found != expected:
            raise WorkflowBlocked("future_leakage: adding future bars changed past features")
        prefix_checks.append({"cutoff": cutoff, "rows": len(found)})
    if contract["feature"]["kind"] == "ema_sma_waiting_path":
        # This gate observes only each day's available state. Later confirmation,
        # prices and terminal outcomes are accessed solely after reservation.
        from lei_signal.research.ema_sma_waiting_path import inspect_waiting_prefix_invariance
        invariant = inspect_waiting_prefix_invariance(payload, contract, root=root)
        if not invariant["ok"]:
            raise WorkflowBlocked("future_leakage: full waiting-path prefix check failed")
        evaluation = [r for r in rows if r.get("feature_reason") is None]
        evaluation_assets = sorted({r["asset"] for r in evaluation})
        missing = sorted(set(contract["universe"]["assets"]) - set(evaluation_assets))
        partial = bool(missing)
        if partial and (not contract["universe"]["allow_partial"] or contract["publication"]["claimed_scope"] != "partial"):
            raise WorkflowBlocked("waiting path missing assets requires disclosed partial coverage")
        warnings.extend(value if isinstance(value, dict) else _warning("input_limitation", str(value))
                        for value in result.get("warnings", []))
        coverage = {**result["coverage"], "planned_assets": contract["universe"]["assets"],
                    "input_assets": actual_assets, "input_missing_assets": quote_missing,
                    "actual_assets": evaluation_assets, "missing_assets": missing, "partial": partial,
                    "evaluation_rows": len(evaluation), "evaluation_dates": len({r["date"] for r in evaluation}),
                    "evaluation_kind": "current_state_qualification_only", "outcome_values_used": False}
        proof = {"bindings": bindings, "cache_keys": cache_keys(contract, bindings),
                 "observations": rows, "coverage": coverage, "warnings": warnings,
                 "prefix_checks": prefix_checks, "full_prefix_invariance": invariant,
                 "candidate_preflight": None, "calculation_run": False, "production_authorized": False}
        if require_frozen and contract.get("freeze", {}).get("preflight_digest") != digest({k: v for k, v in proof.items() if k != "observations"}):
            raise WorkflowBlocked("stale_proof: waiting-path qualification changed after freeze")
        return proof
    eval_rows = [r for r in rows if r["eligible"] and any(f["eval_start"] <= r["date"] <= f["eval_end"] for f in contract["split"]["folds"])]
    if contract["split"].get("evaluation_label_policy") == "contained":
        eval_rows = [r for r in eval_rows if any(f["eval_start"] <= r["date"] <= f["eval_end"] and r["label_end"] <= f["eval_end"] for f in contract["split"]["folds"])]
    if not eval_rows:
        raise WorkflowBlocked("no_evaluable_rows: requested question has no qualified evaluation labels")
    evaluation_assets = sorted({r["asset"] for r in eval_rows})
    missing = sorted(set(contract["universe"]["assets"]) - set(evaluation_assets))
    partial = bool(missing)
    if partial and not contract["universe"]["allow_partial"]:
        raise WorkflowBlocked(f"universe_missing: no qualified evaluation rows for {missing}")
    if partial and contract["publication"]["claimed_scope"] != "partial":
        raise WorkflowBlocked("partial coverage cannot be published as full universe validation")
    if partial:
        warnings.append(_warning("partial_universe", f"计划池中{missing}没有合格评价观察，仅限实际进入比较的对象。"))
    for fold in contract["split"]["folds"]:
        possible = [r for r in rows if r["eligible"] and r["date"] <= fold["train_end"]]
        crossing = [r for r in possible if r["label_end"] >= fold["eval_start"]]
        mature = [r for r in possible if r["label_end"] < fold["eval_start"]]
        if crossing and contract["split"]["label_policy"] == "require_mature":
            raise WorkflowBlocked("training_label_leakage: labels cross prediction time")
        if not mature:
            raise WorkflowBlocked("no mature training labels before evaluation")
        fields = contract["evaluator"]["baseline_features"] + contract["evaluator"]["added_features"]
        for row in mature + [r for r in eval_rows if fold["eval_start"] <= r["date"] <= fold["eval_end"]]:
            for field in fields:
                v = row["features"].get(field)
                if v is None or not isinstance(v, (float, int, bool)) or not math.isfinite(float(v)):
                    raise WorkflowBlocked(f"missing/nonfinite feature {field} before statistical callback")
    candidate = None
    if contract["feature"]["kind"] in {"decline_event", "a03_pullback_order", "volume_anomaly_information"}:
        conditions = {r["tested_condition"] for r in eval_rows}
        if conditions != {True, False}:
            raise WorkflowBlocked("condition_prefiltered: comparison needs event and counterexamples; this is a sample problem, not a factor verdict")
    if contract["feature"]["kind"] == "decline_event":
        identity = {k: digest(v) for k, v in {
            "data": bindings["data_sha256"], "contract": contract["question"],
            "target": contract["target"], "baseline": contract["evaluator"]["baseline_features"],
            "horizon": contract["target"]["end_offset"], "evaluator": contract["evaluator"],
            "thresholds": contract.get("comparison_min_each", 1), "features": contract["feature"],
        }.items()}
        structural = [{"id": r["id"], "question": "event", "symbol": r["asset"], "date": r["date"],
                       "stratum": r["stratum"], "x": r["tested_condition"], "eligible": True,
                       "features": {"state": r["features"]["existing_state"] > 0}} for r in eval_rows]
        registry = PreflightRegistry(identity, {"event": {"state": [True, False]}},
                                     {"event": contract.get("comparison_min_each", 1)}, structural)
        candidate = registry.inspect({"candidate_id": "predeclared", "question": "event",
                                      "context": {"logic": "and", "terms": [{"field": "state", "value": True}]}})
        if not candidate["common_layers"]:
            warnings.append(_warning("limited_support", "部分背景内没有足够的事件与反例，相关比较只能明确限定或记为证据不足。"))
    for value in result.get("warnings", []):
        warnings.append(value if isinstance(value, dict) else _warning("input_limitation", str(value)))
    coverage = {**result["coverage"], "planned_assets": contract["universe"]["assets"],
                "input_assets": actual_assets, "input_missing_assets": quote_missing,
                "actual_assets": evaluation_assets, "missing_assets": missing, "partial": partial,
                "evaluation_rows": len(eval_rows), "evaluation_dates": len({r['date'] for r in eval_rows})}
    proof = {"bindings": bindings, "cache_keys": cache_keys(contract, bindings),
            "observations": rows, "coverage": coverage, "warnings": warnings,
            "prefix_checks": prefix_checks, "candidate_preflight": candidate,
            "calculation_run": False, "production_authorized": False}
    if require_frozen and contract.get("freeze", {}).get("preflight_digest") != digest({k: v for k, v in proof.items() if k != "observations"}):
        raise WorkflowBlocked("stale_proof: weights, target, sample or checks changed after freeze")
    return proof


def _record_gate_failure(contract, root, started, error):
    """Persist actual rejected-attempt cost without counting a new hypothesis."""
    if not isinstance(contract, dict) or not isinstance(contract.get("history"), dict) or not isinstance(contract.get("question"), dict):
        return
    family = contract["history"].get("family")
    if not isinstance(family, str) or not family or family != contract["question"].get("hypothesis_family"):
        return  # Unattributable malformed contracts remain in CLI failure artifacts.
    with locked_journal(family_ledger(root, family)) as (stream, _):
        _append(stream, {"event": "gate_attempt", "classification": "mechanical_rejection",
                         "seconds": time.monotonic() - started, "results_seen": False,
                         "callback_executed": False, "error": f"{type(error).__name__}: {error}"})


def freeze_contract(contract, root=ROOT):
    started = time.monotonic()
    accounting = {"charged": False}
    try:
        return _freeze_contract(contract, root, started, accounting)
    except Exception as error:
        if not accounting["charged"]:
            _record_gate_failure(contract, root, started, error)
        raise


def _freeze_contract(contract, root, started, accounting):
    """Freeze after checks. A frozen contract is not a scientific approval."""
    frozen = copy.deepcopy(contract)
    frozen["history"]["ledger_path"] = str(family_ledger(root, frozen["history"]["family"]).relative_to(root))
    frozen["calendar"] = read_json(resolve_path(root, frozen["data"]["path"]))["calendar"]
    checked = preflight(frozen, root, require_frozen=False)
    frozen["bindings"] = checked["bindings"]
    frozen["freeze"] = {"preflight_digest": digest({k: v for k, v in checked.items() if k != "observations"}),
                        "observations_digest": digest(checked["observations"])}
    with family_execution_lock(root, frozen):
        ledger = family_ledger(root, frozen["history"]["family"])
        with locked_journal(ledger) as (stream, records):
            headers = [r for r in records if r["event"] == "family"]
            budget = frozen["budget"]
            if headers and any(budget[k] > headers[0]["budget"][k] for k in budget):
                raise WorkflowBlocked("family budget cannot be raised on freeze/retry")
            if not headers:
                _append(stream, {"event": "family", "family": frozen["history"]["family"], "budget": budget})
            spent = sum(r.get("seconds", 0) for r in records if r["event"] in COST_EVENTS)
            if spent + time.monotonic() - started >= budget["execution_seconds"]:
                raise WorkflowPaused("family execution budget exhausted before rehearsal")
        try:
            frozen["rehearsal"] = run_rehearsal(frozen)
        finally:
            with locked_journal(ledger) as (stream, _):
                _append(stream, {"event": "rehearsal", "phase": "synthetic_before_freeze",
                    "seconds": time.monotonic() - started, "market_fits": 0,
                    "purpose": "engineering_error_check_only"})
                accounting["charged"] = True
        if spent + time.monotonic() - started > budget["execution_seconds"]:
            raise WorkflowPaused("family budget interrupted during rehearsal; not an effect verdict")
    return frozen


def run_rehearsal(contract):
    """Actual small synthetic pipeline; never read holdout outcomes for selection."""
    from datetime import date, timedelta
    from lei_signal.research.workflow_inputs import prepare_observations
    from lei_signal.research.workflow_evaluation import evaluate_observations
    c = copy.deepcopy(contract)
    if c["feature"]["kind"] == "ema_sma_waiting_path":
        return _waiting_rehearsal(c)
    if c["feature"]["kind"] == "double_ma_order_information":
        # This deep copy only is synthetic; the real contract remains unchanged.
        c["data"]["mode"] = "synthetic"
        c.setdefault("permissions", {})["real_labels"] = True
    n = max(c["feature"]["lookback"] + 1, c["feature"]["warmup"])
    if c["feature"]["kind"] in ("space_prior_target", "ma_cluster_information"):
        n = max(n, 600)  # enough weekly training rows; space also needs 730 natural days
    count = n + c["target"]["end_offset"] * 2 + 72
    if c["feature"]["kind"] == "prior_top_dual_break_information":
        count = 600  # four causal component states in a fixed engineering fixture
    if c["feature"]["kind"] == "pullback_layer_change_information":
        count = 1000  # two completed pullbacks need more history than daily states
    if c["feature"]["kind"] == "double_ma_order_information":
        count = 900  # fixed engineering correction; no real design change
    if c["feature"]["kind"] in {"slope_change_information", "simple_top_invalidation_information", "tsfresh_price_information"}:
        count = 600  # engineering fixture, never a market parameter selection
    if count > 2000:
        raise WorkflowBlocked("synthetic rehearsal size exceeds finite engineering adapter limit")
    dates, d = [], date(2020, 1, 2)
    while len(dates) < count:
        if d.weekday() < 5:
            dates.append(d.isoformat())
        d += timedelta(days=1)
    assets = ["synthetic-A", "synthetic-B"]
    bars = []
    for j, asset in enumerate(assets):
        price = 100.0 + j
        for i, d in enumerate(dates):
            if c["feature"]["kind"] == "pullback_layer_change_information":
                price = 100.0 + j + 0.2 * i + (4.0 + 2.0 * math.sin(i / 60)) * math.sin(i / 5)
                low = price - 0.6
            elif c["feature"]["kind"] in ("slope_change_information", "simple_top_invalidation_information", "tsfresh_price_information"):
                price = 100.0 + j + 0.10 * i + 4.0 * math.sin(i / 7)
                low = price - 0.8
            elif c["feature"]["kind"] in ("space_prior_target", "ma_cluster_information"):
                price = 100.0 + j + 0.10 * i + 5.0 * math.sin(i / 15)
                low = price * 0.99
            elif c["feature"]["kind"] == "a03_pullback_order":
                # A rising synthetic road with separately constructed pullbacks.
                # This exercises first/later event identity and real fitting;
                # artificial lows are not a market calibration of touch depth.
                price = 100.0 + j + 0.2 * i
                low = price - (7.0 if i >= 254 and i % 8 == 6 else 1.0)
            elif c["feature"]["kind"] in {"key_fluctuation_information", "prior_top_dual_break_information"}:
                price = 100.0 + j + 0.10 * i + 3.0 * math.sin(i / 7)
                low = price - 0.8
            elif c["feature"]["kind"] == "profile_overhead_information":
                price = 100.0 + j + 0.14 * i + 3.0 * math.sin(i / 8)
                low = price - 1.2
            elif c["feature"]["kind"] == "simple_top3_information":
                # Rising road with repeated strict 3-bar descents; both true
                # and false observations must reach an actual fitted fold.
                price = 100.0 + j + 0.12 * i + 2.0 * math.sin(i / 4)
                low = price - 0.8
            elif c["feature"]["kind"] == "double_ma_order_information":
                # Exact rising seed -> low plateau -> rising road. This fixes
                # both states before any run; no synthetic optimization/search.
                price = (100.0 + j + i if i < 280 else
                         100.0 + j if i < 480 else
                         100.0 + j + (i - 480) if i < 600 else
                         100.0 + j if i < 680 else
                         100.0 + j + (i - 680))
                low = price * 0.99
            elif c["feature"]["kind"] == "future_deduction_box_information":
                price = 100.0 + j + 0.03 * i + 3.0 * math.sin(i / 7)
                low = price - 0.8
            else:
                decline = -0.007 if c["feature"]["kind"] == "a01_signed_band" else -0.014
                price *= 1 + (0.008 if i % 5 < 3 else decline) + j * 0.0001
                low = price * 0.99
            bars.append({"asset": asset, "date": d, "status": "quoted", "close": price,
                         "open": price, "high": price * 1.01, "low": low,
                         "action_known": True, "open_actionable": True,
                         "volume": 400.0 if (i + 3*j) % 11 == 0 else 100.0,
                         "volume_source_known": True, "volume_break": False})
    payload = {"data_mode": "synthetic", "calendar": dates, "bars": bars}
    c["universe"]["assets"] = assets
    c["question"].update(sampling="daily", universe=assets, period=[dates[0], dates[-1]])
    cutoff = n + c["target"]["end_offset"] + 32
    if c["feature"]["kind"] == "pullback_layer_change_information":
        cutoff = 700
    if c["feature"]["kind"] == "double_ma_order_information":
        cutoff = 550  # training includes rising restart EMA120 lag vs SMA60_up5
    c["split"] = {"label_policy": "purge", "folds": [{"train_end": dates[cutoff],
        "eval_start": dates[cutoff + 1], "eval_end": dates[-1 - c["target"]["end_offset"]]}]}
    if c["feature"]["kind"] in {"double_ma_order_information", "profile_overhead_information"}:
        c["split"]["evaluation_label_policy"] = "contained"
    c["calendar"] = dates
    c["dependence"] = {"block_length": 5, "draws": 16, "seed": 7}
    inputs = prepare_observations(payload, c)
    result = evaluate_observations(inputs["observations"], c)
    if c["feature"]["kind"] == "prior_top_dual_break_information":
        ready = [r for r in inputs["observations"] if r["eligible"]]
        states = {(r["features"]["prior_top_active"], r["features"]["dual_break"]) for r in ready}
        if result["execution"]["fits"] != 2 or len(states) != 4 or not any(r["y"] > 0 for r in ready):
            raise WorkflowBlocked("combination rehearsal requires four states, nonzero risk and two fits")
    if c["feature"]["kind"] == "pullback_layer_change_information":
        available = [r for r in inputs["observations"] if r["eligible"]]
        if (not result["performance"] or result["execution"]["fits"] != 2 or
                len({r["features"]["added"] for r in available}) < 2):
            raise WorkflowBlocked("pullback-layer rehearsal requires distinct layer changes and both fitted comparisons")
    if c["feature"]["kind"] == "space_prior_target" and not result["performance"]:
        raise WorkflowBlocked("space synthetic rehearsal must exercise available upper targets and real predictions")
    if c["feature"]["kind"] == "ma_cluster_information" and not result["performance"]:
        raise WorkflowBlocked("width synthetic rehearsal must exercise trend-qualified predictions")
    if c["feature"]["kind"] == "a01_signed_band" and not result["performance"]:
        raise WorkflowBlocked("A01 synthetic rehearsal must exercise eligible trend-state predictions, not an empty pipeline")
    if c["feature"]["kind"] == "a03_pullback_order" and (not result["performance"] or
            inputs["coverage"]["first_touches"] < 1 or inputs["coverage"]["later_touches"] < 1):
        raise WorkflowBlocked("A03 synthetic rehearsal must exercise first/later touches and real predictions")
    if c["feature"]["kind"] == "simple_top3_information" and (not result["performance"] or
            result["execution"]["fits"] < 2 or inputs["coverage"]["top_in_uptrend"] < 1 or
            inputs["coverage"]["eligible"] <= inputs["coverage"]["top_in_uptrend"]):
        raise WorkflowBlocked("T01 synthetic rehearsal requires true/false observations and real predictions")
    if c["feature"]["kind"] == "future_deduction_box_information" and (not result["performance"] or
            result["execution"]["fits"] != 2 or inputs["coverage"]["context"] < 1):
        raise WorkflowBlocked("D01 synthetic rehearsal requires context rows and both OLS comparisons")
    if c["feature"]["kind"] == "profile_overhead_information":
        eligible = [r for r in inputs["observations"] if r["eligible"]]
        if (len({r["asset"] for r in eligible}) != 2 or
            len({round(r["features"]["added"], 8) for r in eligible}) < 2 or
            not any(abs(r["features"]["added"] - r["features"]["price_only_overhead_ratio"]) > 1e-8 for r in eligible) or
            not result["performance"] or result["execution"]["fits"] != 2):
            raise WorkflowBlocked("P01 synthetic rehearsal requires two assets, quantity-versus-geometry variation and both OLS fits")
    if c["feature"]["kind"] == "double_ma_order_information":
        fold = c["split"]["folds"][0]
        train = [r for r in inputs["observations"] if r["eligible"] and
                 r["date"] <= fold["train_end"] and r["label_end"] < fold["eval_start"]]
        evaluation = [r for r in inputs["observations"] if r["eligible"] and
                      fold["eval_start"] <= r["date"] <= fold["eval_end"] and
                      r["label_end"] <= fold["eval_end"]]
        if (not result["performance"] or not result["predictions"] or
            result["execution"]["fits"] != 2 or
            {r["tested_condition"] for r in train} != {False, True} or
            not any(r["features"]["added"] != r["features"]["sma60_up5"] for r in train) or
            {r["tested_condition"] for r in evaluation} != {False, True} or
            any(r["ready_252"] for r in inputs["observations"] if r["date"] < dates[251]) or
            any(not r["ready_252"] for r in inputs["observations"] if r["date"] == dates[251]) or
            c["target"]["start_offset"] != 1 or c["target"]["end_offset"] != 21):
            raise WorkflowBlocked("T03 synthetic rehearsal requires segmented252, nonduplicate added/up5 training support, both states in paired train/eval,21-close MAE and exactly two OLS fits")
    if c["feature"]["kind"] == "tsfresh_price_information":
        ready = [r for r in inputs["observations"] if r["eligible"]]
        if (not result["performance"] or result["execution"]["fits"] != 2 or
                len({r["asset"] for r in ready}) != 2 or
                not all(all(math.isfinite(r["features"][name]) for name in
                            ("mean_abs_log_change20", "return_autocorrelation20_lag1")) for r in ready) or
                any(r["ready_252"] for r in inputs["observations"] if r["date"] < dates[251])):
            raise WorkflowBlocked("tsfresh rehearsal requires common finite candidates, segmented252 and two synthetic fits")
    return {"schema_version": "workflow-rehearsal/1.0", "data_mode": "synthetic",
            "input_sha256": digest(payload), "definition_and_method": digest({"feature": c["feature"], "target": c["target"], "evaluator": c["evaluator"]}),
            "coverage": inputs["coverage"], "performance": result["performance"],
            "fits": result["execution"]["fits"], "purpose": "engineering_error_check_only",
            "selection_used": False}


def _waiting_rehearsal(contract):
    """Finite predetermined counterexamples; never read the market panel."""
    from datetime import date, timedelta
    from lei_signal.research.ema_sma_waiting_path import prepare_waiting_observations, evaluate_waiting_paths
    paths = {
        "synthetic-confirm": [100] * 252 + [110] * 20 + [90] * 10 + [100] * 40,
        "synthetic-failed": [100] * 252 + [110] * 20 + [90] * 10 + [100] * 2 + [80] * 38,
        # The end is deliberately incomplete, preserving an unconfirmed start.
        "synthetic-unconfirmed": [100] * 252 + [110] * 20 + [90] * 10 + [100] * 3,
    }
    dates = [(date(2020, 1, 1) + timedelta(days=i)).isoformat() for i in range(max(map(len, paths.values())))]
    bars = [{"asset": asset, "date": dates[i], "status": "quoted", "action_known": True,
             "open": price, "high": price, "low": price, "close": price, "exact_nominal_close": str(price)}
            for asset, prices in paths.items() for i, price in enumerate(prices)]
    payload = {"data_mode": "synthetic", "calendar": dates, "bars": bars}
    c = copy.deepcopy(contract)
    c["data"]["mode"] = "synthetic"
    c["universe"]["assets"] = list(paths)
    c["question"].update(universe=list(paths), period=[dates[0], dates[-1]])
    inputs = prepare_waiting_observations(payload, c)
    result = evaluate_waiting_paths(payload, c, inputs["observations"])
    statuses = {r["status"] for r in result["event_ledger"]}
    if "confirmed" not in statuses or "ema_failed" not in statuses or not statuses.intersection({"missing", "immature", "no_confirmation"}):
        raise WorkflowBlocked("waiting rehearsal must preserve confirmation, failure and unconfirmed counterexamples")
    if result["execution"]["fits"] != 0 or result["predictions"]:
        raise WorkflowBlocked("waiting rehearsal cannot fit or predict")
    return {"schema_version": "workflow-rehearsal/1.0", "data_mode": "synthetic",
            "input_sha256": digest(payload), "definition_and_method": digest({"feature": c["feature"], "target": c["target"], "evaluator": c["evaluator"]}),
            "coverage": inputs["coverage"], "performance": result["performance"],
            "status_counts": result["coverage"]["status_counts"], "fits": 0,
            "purpose": "engineering_error_check_only", "selection_used": False}


def freeze_workflow(draft_path, output_dir, root=ROOT):
    out = Path(output_dir)
    if out.exists():
        raise WorkflowBlocked("freeze outputs must be new, old snapshots remain immutable")
    frozen = freeze_contract(read_json(draft_path), root)
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / "contract.json", frozen)
    write_json(out / "rehearsal.json", frozen["rehearsal"])
    proof = preflight(frozen, root)
    redacted = {**proof, "observations": [{**r, "y": "redacted_before_freeze_publication"} for r in proof["observations"]],
                "label_value_access": "internally_for_qualification_only; not exported for model choice"}
    write_json(out / "preflight.json", redacted)
    return out / "contract.json"


def _scientific_key(contract, proof):
    return digest({"prediction": proof["cache_keys"]["prediction"],
                   "aggregation": proof["cache_keys"]["aggregate"],
                   "family": contract["history"]["family"]})


def _evaluation_quote_keys(contract, proof, root):
    """Recorded observation material remains seen after reformatting or changing targets.

    This is actual quoted observation content, independent of labels and chosen
    thresholds. Source identity aliases and unintegrated historical contact still
    require the controller's honest source/contact review.
    """
    evaluated = {(r["asset"], r["date"]) for r in proof["observations"] if r["eligible"] and
                 any(f["eval_start"] <= r["date"] <= f["eval_end"] for f in contract["split"]["folds"])}
    payload = read_json(resolve_path(root, contract["data"]["path"]))
    return {digest({"asset": b["asset"], "date": b["date"], "close": float(b["close"])})
            for b in payload["bars"] if (b["asset"], b["date"]) in evaluated and b["status"] == "quoted"}


def _reserve(contract, proof, out, root, *, reuse=False):
    if contract["feature"]["kind"] == "ema_sma_waiting_path" and contract["data"]["mode"] != "synthetic":
        permissions = contract.get("permissions", {})
        if (permissions.get("real_labels") is not True or permissions.get("effect_authorized") is not True or
                type(permissions.get("real_fits")) is not int or permissions["real_fits"] != 0 or
                type(contract["budget"].get("real_runs")) is not int or contract["budget"]["real_runs"] < 1):
            raise WorkflowBlocked("waiting-path real effects require explicit permission, zero fits and a positive real-run budget")
    path = family_ledger(root, contract["history"]["family"])
    key = _scientific_key(contract, proof)
    with locked_journal(path) as (stream, records):
        headers = [r for r in records if r["event"] == "family"]
        budget = contract["budget"]
        if headers:
            cap = headers[0]["budget"]
            if any(budget[k] > cap[k] for k in cap):
                raise WorkflowBlocked("family budget cannot be raised by another task/contract")
        else:
            _append(stream, {"event": "family", "family": contract["history"]["family"], "budget": budget})
        starts = [r for r in records if r["event"] == "start"]
        finished = {r.get("run_id") for r in records if r["event"] == "finish"}
        unsettled = [r["run_id"] for r in starts if r["run_id"] not in finished]
        if unsettled:
            raise WorkflowPaused("unsettled execution starts require explicit reconciliation before retry: "
                                 + ", ".join(unsettled))
        variants = {r["scientific_key"] for r in starts}
        if contract["feature"]["kind"] == "ema_sma_waiting_path" and contract["data"]["mode"] != "synthetic":
            actual_runs = [r for r in starts if r.get("real_effect_run")]
            if not reuse and len(actual_runs) >= budget["real_runs"]:
                raise WorkflowPaused("waiting-path real-run budget exhausted")
        if key not in variants and len(variants) >= budget["scientific_variants"]:
            raise WorkflowPaused("scientific variant budget exhausted; a retry cannot reset it")
        seconds = sum(r.get("seconds", 0) for r in records if r["event"] in COST_EVENTS)
        if seconds >= budget["execution_seconds"]:
            raise WorkflowPaused("family execution budget exhausted")
        label_keys = {digest({"asset": r["asset"], "date": r["date"], "target": contract["target"], "y": r["y"]})
                      for r in proof["observations"] if r["eligible"] and any(f["eval_start"] <= r["date"] <= f["eval_end"] for f in contract["split"]["folds"])}
        quote_keys = _evaluation_quote_keys(contract, proof, root)
        # Existing experiment journals, not a second factor registry. Inspect
        # known controlled runs across families so changing AI/name/family cannot
        # turn the same evaluated labels into new evidence.
        global_seen = []
        for journal in path.parent.parent.glob("*/attempts.jsonl"):
            for line in journal.read_text(encoding="utf-8").splitlines():
                r = json.loads(line)
                if r.get("results_seen") and (r.get("data_sha256") == proof["bindings"]["data_sha256"] or label_keys.intersection(r.get("evaluation_labels", [])) or quote_keys.intersection(r.get("evaluation_quotes", []))):
                    global_seen.append(r)
        previously_seen = [r for r in records if r.get("results_seen") and r.get("data_sha256") == proof["bindings"]["data_sha256"]]
        if global_seen and contract["question"]["validation"]["stage"] == "unseen":
            raise WorkflowBlocked("seen_evidence: known evaluated material cannot be unseen in another family/AI")
        if previously_seen and contract["question"]["validation"]["stage"] == "unseen":
            raise WorkflowBlocked("seen_evidence: renaming data/task/AI cannot make results unseen")
        if previously_seen and key not in variants and not contract["history"].get("changed_after_results_reason"):
            raise WorkflowBlocked("changed_after_results: record the exploratory change before execution")
        if global_seen and key not in variants and contract["question"]["validation"]["stage"] != "exploration":
            raise WorkflowBlocked("changed_after_results: changed research on seen material must be exploration")
        run_id = uuid.uuid4().hex
        _append(stream, {"event": "start", "run_id": run_id, "scientific_key": key,
                         "real_effect_run": contract["data"]["mode"] != "synthetic" and not reuse,
                         "classification": "mechanical_retry" if key in variants else "scientific_variant",
                         "data_sha256": proof["bindings"]["data_sha256"], "out": str(out),
                         "time": datetime.now(timezone.utc).isoformat(),
                         "change_reason": contract["history"].get("changed_after_results_reason"),
                         "input_access": "qualification_only_before_fitting"})
    return run_id


def _finish(contract, root, run_id, proof, seconds, status, receipt=None):
    with locked_journal(family_ledger(root, contract["history"]["family"])) as (stream, _):
        _append(stream, {"event": "finish", "run_id": run_id, "seconds": seconds, "status": status,
                         "data_sha256": proof["bindings"]["data_sha256"],
                         "results_seen": status in {"computed", "failed_after_callback"}, "receipt_sha256": receipt,
                         "evaluation_quotes": sorted(_evaluation_quote_keys(contract, proof, root)),
                         "evaluation_labels": [digest({"asset": r["asset"], "date": r["date"],
                             "target": contract["target"], "y": r["y"]}) for r in proof["observations"]
                             if r["eligible"] and any(f["eval_start"] <= r["date"] <= f["eval_end"] for f in contract["split"]["folds"])]})


def verify_receipt(output_dir, root=ROOT):
    """No hand-written 'verified=true' shortcut; require journal and exact artifacts."""
    out = Path(output_dir)
    contract = read_json(out / "contract.json")
    receipt = read_json(out / "receipt.json")
    if receipt.get("contract_sha256") != file_hash(out / "contract.json"):
        raise WorkflowBlocked("receipt contract mismatch")
    proof = preflight(contract, root)
    if read_json(out / "preflight.json") != proof:
        raise WorkflowBlocked("stale input/weight proof; rerun affected checks")
    for name, expected in receipt["outputs"].items():
        if file_hash(out / name) != expected:
            raise WorkflowBlocked(f"artifact changed after execution: {name}")
    with locked_journal(family_ledger(root, contract["history"]["family"])) as (_, records):
        matching = [r for r in records if r["event"] == "finish" and r.get("run_id") == receipt["run_id"]
                    and r.get("receipt_sha256") == file_hash(out / "receipt.json") and r["status"] == "computed"]
    if not matching:
        raise WorkflowBlocked("bypassed_entry: no matching controlled execution journal receipt")
    return contract, proof, receipt


def _same_numeric(left, right):
    if type(left) is not type(right) and not isinstance(left, (float, int)):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_same_numeric(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_same_numeric(a, b) for a, b in zip(left, right))
    if isinstance(left, (float, int)) and not isinstance(left, bool):
        return isinstance(right, (float, int)) and math.isclose(left, right, rel_tol=1e-10, abs_tol=1e-12)
    return left == right


def _require_rehearsal(contract):
    rehearsal = contract.get("rehearsal", {})
    if not isinstance(rehearsal, dict) or rehearsal.get("schema_version") != "workflow-rehearsal/1.0" or rehearsal.get("data_mode") != "synthetic" or rehearsal.get("purpose") != "engineering_error_check_only":
        raise WorkflowBlocked("missing actual frozen rehearsal evidence")


def check_publication(output_dir, root=ROOT):
    from lei_signal.research.workflow_evaluation import summarize_predictions
    contract, proof, receipt = verify_receipt(output_dir, root)
    result = read_json(Path(output_dir) / "result.json")
    if contract["feature"]["kind"] == "ema_sma_waiting_path":
        _require_rehearsal(contract)
        from lei_signal.research.ema_sma_waiting_path import evaluate_waiting_paths
        actual = evaluate_waiting_paths(read_json(resolve_path(root, contract["data"]["path"])),
                                        contract, proof["observations"], root=root)
        # Recompute prices, every start and all failure/unknown reasons. There
        # are no prediction signatures or fitted baseline scores for this kind.
        for key in ("evaluator", "definition_ref", "performance", "increments", "descriptions", "coverage",
                    "event_ledger", "period_comparisons", "uncertainty", "limitations", "fits"):
            if not _same_numeric(result.get(key), actual.get(key)):
                raise WorkflowBlocked(f"waiting-path publication numeric/unit/ledger mismatch: {key}")
        if result.get("execution", {}).get("fits") != 0 or result.get("predictions") != []:
            raise WorkflowBlocked("waiting-path publication cannot contain fits or predictions")
        if (Path(output_dir) / "report.md").read_text(encoding="utf-8") != render_report(contract, proof, result):
            raise WorkflowBlocked("waiting-path core report was altered")
        return {"execution": "completed", "evidence": contract["publication"]["conclusion"],
                "coverage": "partial" if proof["coverage"]["partial"] else "declared_scope",
                "production_authorized": False, "receipt": receipt["run_id"]}
    expected_ids = set()
    for index, fold in enumerate(contract["split"]["folds"]):
        train = [r for r in proof["observations"] if r["eligible"] and
                 r["date"] <= fold["train_end"] and r["label_end"] < fold["eval_start"]]
        ev = [r for r in proof["observations"] if r["eligible"] and
              fold["eval_start"] <= r["date"] <= fold["eval_end"] and
              (contract["split"].get("evaluation_label_policy") != "contained" or
               r["label_end"] <= fold["eval_end"])]
        if len(train) < contract["evaluator"].get("minimum_training_rows", 1):
            # A predeclared minimum can make a sparse period unestimable. It
            # must be reported, never silently treated as a prediction miss.
            marker = f"fold {index}: no mature training/evaluation rows; not estimated"
            if ev and marker not in result.get("warnings", []):
                raise WorkflowBlocked("unestimated fold was not disclosed")
            continue
        expected_ids.update(r["id"] for r in ev)
    if {p["id"] for p in result["predictions"]} != expected_ids:
        raise WorkflowBlocked("prediction coverage mismatch: cannot quietly omit assets/dates/opportunities")
    _require_rehearsal(contract)
    # Recompute simple baselines from actual training labels, not test labels or self-declared scores.
    import numpy as np
    for i, fold in enumerate(contract["split"]["folds"]):
        tr = [r for r in proof["observations"] if r["eligible"] and r["date"] <= fold["train_end"] and r["label_end"] < fold["eval_start"]]
        policy = contract.get("training_weights", "equal_asset")
        from collections import Counter
        key = "asset" if policy == "equal_asset" else "date"
        counts = Counter(r[key] for r in tr)
        raw_w = np.array([1 / counts[r[key]] for r in tr])
        mean = float((raw_w / raw_w.sum()) @ np.array([r["y"] for r in tr]))
        for p in result["predictions"]:
            if str(p["fold"]) == str(i) and not math.isclose(p["B0"], mean, rel_tol=1e-10, abs_tol=1e-12):
                raise WorkflowBlocked("B0 was not computed from strictly mature training labels")
    actual = summarize_predictions(result["predictions"], contract, proof["observations"])
    if contract["feature"]["kind"] == "double_ma_order_information":
        from lei_signal.research.double_ma_order_information import attach_primary_rmse
        attach_primary_rmse(actual, contract, proof["observations"])
        for key in ("primary_rmse", "primary_rmse_block60"):
            if not _same_numeric(result.get(key), actual.get(key)):
                raise WorkflowBlocked("T03 paired RMSE primary aggregation mismatch")
    for key in ("performance", "increments", "descriptions", "period_comparisons"):
        if not _same_numeric(result[key], actual[key]):
            raise WorkflowBlocked(f"publication numeric/unit/comparison mismatch: {key}")
    if contract.get("descriptive"):
        from lei_signal.research.workflow_descriptions import summarize_price_groups
        described = summarize_price_groups(proof["observations"], read_json(resolve_path(root, contract["data"]["path"])), contract)
        if not _same_numeric(result.get("factor_descriptions"), described):
            raise WorkflowBlocked("publication state-group/return/risk/common-background mismatch")
    models = {p["model"] for p in result["performance"]}
    required = {"B0", "B1", "B2"} | ({"B50"} if contract["target"]["kind"] in {"up", "downside_event"} else set())
    if not required <= models:
        raise WorkflowBlocked("required baseline absent from publication")
    report = render_report(contract, proof, result)
    # The core table is generated here. The published file must match the generated table.
    if (Path(output_dir) / "report.md").read_text(encoding="utf-8") != report:
        raise WorkflowBlocked("core report was altered or omitted required baselines")
    return {"execution": "completed", "evidence": contract["publication"]["conclusion"],
            "coverage": "partial" if proof["coverage"]["partial"] else "declared_scope",
            "production_authorized": False, "receipt": receipt["run_id"]}


def human_warning(warning):
    if isinstance(warning, dict):
        return warning.get("message", str(warning))
    s = str(warning)
    if "underperforms" in s:
        return "加入候选后的方法在这一对照下更差；合法负结果可以结束，不为过关调参。详情：" + s.split(":")[0]
    if "zero variance" in s:
        return "部分字段在训练时期没有变化，无法提供可学习的差别。"
    if "common support absent" in s:
        return "某些背景没有足够事件和反例，不能从这一组描述确认新增帮助。"
    if "date-block draws" in s:
        return "部分整段日期的重复抽取缺少固定对象，已剔除并报告次数，没有改换对象比重。"
    if "year sign reversal" in s:
        return "不同年份的改善方向相反，不能视作跨年份稳定帮助。"
    if "few date blocks" in s:
        return "评价日期只容纳不足三个预定长度的日期段，允许的改善和恶化范围证据有限。"
    if "Demonstration proxy" in s:
        return "这是演示计算代理；真实身份、权威日历和经济价口径需要单独资格，不等价于注册A01公式。"
    if "Known halts" in s:
        return "正常停牌没有填补报价；特征使用真实报价数量，目标期限仍使用交易日历；收盘风险只用实际收盘。"
    if "no quoted input" in s:
        return "某对象没有报价，但保留在计划池及覆盖损失中。"
    return s


def render_report(contract, proof, result):
    """Core numbers always derived from evaluator artifacts, never copied by an AI."""
    if contract["feature"]["kind"] == "ema_sma_waiting_path":
        return _render_waiting_report(contract, proof, result)
    synthetic = contract["data"]["mode"] == "synthetic"
    evidence = {"not_supported": "本次方法下未得到新增帮助的支持", "insufficient": "证据不足", "supported": "本次范围内获得支持"}[contract["publication"]["conclusion"]]
    lines = [f"# {contract['question']['question_id']}（{'合成流程演示' if synthetic else '限定范围研究'}）", "",
             "## 一句话结论（大白话）", "",
             f"{evidence}。{'这里使用人工生成的数据，只证明流程行为，不说明市场规律。' if synthetic else '结论只涉及本合同的对象、时期和方法。'}计算与检查完成不等于允许交易。", "",
             f"问题：{contract['question'].get('decision_use', contract['question']['added_information'])}",
             f"计划对象：{', '.join(contract['universe']['assets'])}；实际有报价：{', '.join(proof['coverage']['actual_assets'])}。",
             f"时期：{contract['question']['period']}；评价对象数量：{proof['coverage']['evaluation_rows']}条、{proof['coverage']['evaluation_dates']}个日期。",
             "简单参照B0只使用训练期已成熟结果；B1是已有信息；B2加入候选信息。二元目标另列固定50%的B50。", "",
             "## 预测表现（与投资收益分开）", "",
             "错误越小表示预测更接近实际结果；平均平方错误（MSE）的单位是目标单位的平方，开方错误（RMSE）与目标同单位。方向或下跌事件用平方评分（Brier）。这里没有账户买卖收益。", "",
             "例如实际变化5%、预测3%，相差2个百分点，平方错误为4；方向或下跌事件评分在0到1之间，越小越好，固定50%的评分是0.25。", "",
             "| 方法 | 错误指标 | 数值 | 单位 | 观察数 | 日期数 | 对象数 |",
             "|---|---|---:|---|---:|---:|---:|"]
    for p in result["performance"]:
        unit = {"percentage_point": "百分点", "percentage_point_squared": "百分点²", "probability_squared": "0到1的平方评分"}.get(p["unit"], p["unit"])
        lines.append(f"| {p['model']} | {p['metric']} | {p['value']:.8g} | {unit} | {p['rows']} | {p['dates']} | {p['assets']} |")
    lines += ["", "## 相对已有信息的增量", "",
              "同一观察、同一比重比较。正数表示错误减少，负数表示更差；范围保留连续日期与同日对象一起重抽，是此方法允许的改善及恶化范围。", "",
              "| 对照 | 原错误 | 加入后错误 | 错误减少 | 相对变化 | 改善及恶化范围 | 单位 |",
              "|---|---:|---:|---:|---:|---|---|"]
    for p in result["increments"]:
        relative = "未估计" if p["relative_percent"] is None else f"{p['relative_percent']:.4g}%"
        interval = "无法可靠估计" if p["lo"] is None else f"{p['lo']:.6g} 至 {p['hi']:.6g}"
        lines.append(f"| {p['new_model']} 相对 {p['old_model']} | {p['old_value']:.8g} | {p['new_value']:.8g} | {p['absolute_error_improvement']:.8g} | {relative} | {interval} | {p['unit']} |")
    lines += ["",
              "## 机会数量、风险与覆盖", "",
              "固定窗口价格变化与途中风险是目标描述，不是已兑现收益。自然组内描述使用各自构成；只有共同对象与年份按相同比重的比较可以直接计算组间差。", "",
              "描述关系覆盖全部可评价历史机会，包含训练时期；预测表只覆盖合同中预留的后续评价时期，两者不合称独立验证。未设定的辅助目标记为未计算，不填0。", "",
              "```json", json.dumps({"coverage": proof["coverage"], "descriptions": result["descriptions"]}, ensure_ascii=False, indent=2), "```", "",
              "## 反例和结论边界", "",
              "评价期资料没有参与训练或标准化；已有资料是否曾用于挑选方法仍以研究家族记录为准，换名字不成为新验证。预测改善不直接代表投资收益。", ""]
    for warning in proof["warnings"] + result.get("warnings", []):
        lines.append(f"- {human_warning(warning)}")
    lines += ["", "## 主控判断（程序不能替代）", "", "```json",
              json.dumps(contract["controller_review"], ensure_ascii=False, indent=2), "```", "",
              "## ARCHIVE / 最小决策卡", "",
              f"执行：completed；证据：{contract['publication']['conclusion']}；覆盖：{'partial' if proof['coverage']['partial'] else '本合同已声明范围'}；交易许可：无。",
              "本轮有界问题已交付；不因负结果自动增加市场、参数或模型。复现见同目录contract.json、preflight.json、result.json、receipt.json及研究家族日志。", ""]
    if contract["feature"]["kind"] == "double_ma_order_information":
        lines += ["", "## T03 主指标RMSE（百分点；MSE区间仅辅助）", "", "0.10pp attention只对应B1 RMSE减B2 RMSE，不是sqrt(deltaMSE)或交易增量。", "```json", json.dumps({k: result.get(k) for k in ("primary_rmse", "primary_rmse_block60")}, ensure_ascii=False, indent=2), "```"]
    return "\n".join(lines)


def _render_waiting_report(contract, proof, result):
    """Keep descriptive prices distinct from forecasts and account outcomes."""
    lines = [f"# {contract['question']['question_id']}（等待过程的限定描述）", "",
             "## 一句话结论（大白话）", "",
             "本次记录EMA刚向上、SMA尚未向上之后，等待SMA跟上时的成功、失败和价格变化。"
             "早看与等确认都用同一个结束日期比较；只有实际确认且价格齐全的起点才能相减，"
             "这部分结果不能代表全部等待，更不能代表完整账户收益或已获准交易。",
             "人工数据只检查程序行为，不构成市场证据。" if contract['data']['mode'] == 'synthetic' else
             "资料是已见历史的回顾性重建，不能宣称来自全新验证。", "",
             "## 性能表（固定终点价格描述）", "",
             "early_path是全部能计算的早期观察；early_paired_path和waiting_path只用双方价格齐全的共同起点。"
             "早期观察从起点后一天收盘开始，等待观察从确认后一天收盘开始，均结束于起点后21个交易日。"
             "这些百分比是价格变化，未计算费用、现金或复利账户。", "",
             "```json", json.dumps(result['performance'], ensure_ascii=False, indent=2), "```", "",
             "## 相对已有信息的增量", "",
             "全部早期观察与成功配对的早期观察之间，差的是事后进入比较的机会组成，不能叫新增信息的帮助。"
             "同一成功配对起点的等待价格变化减早期价格变化，只描述等待价差；没有拟合或预测增量。"
             "缺确认、失败、中断、太晚及未成熟全部留账，缺少的等待价差记为空，不填0。"
             "未确认指截至固定终点仍未确认，不表示以后永远不会确认。", "",
             "```json", json.dumps(result['increments'], ensure_ascii=False, indent=2), "```", "",
             "## 机会数量、反例和范围", "",
             "相邻起点的观察窗口会重叠，四只ETF也受到共同市场影响，因此记录数不是独立验证次数。"
             "本轮未估计结果可能由巧合造成的范围，也不把某组均值解释成因果效果。", "",
             "```json", json.dumps({'qualification': proof['coverage'], 'outcomes': result['coverage'],
                                      'periods': result['period_comparisons']}, ensure_ascii=False, indent=2), "```", "",
             "## 主控判断（程序不能替代）", "", "```json",
             json.dumps(contract['controller_review'], ensure_ascii=False, indent=2), "```", "",
             "## ARCHIVE / 最小决策卡", "",
             f"执行：completed；证据：{contract['publication']['conclusion']}；仅描述当前合同范围；拟合：0；交易许可：无。",
             "全部起点记录见result.json的event_ledger；未覆盖条件和来源限制继续保留，不能以本轮描述替代完整入场规则。", ""]
    return "\n".join(lines)


def publish(output_dir, root=ROOT):
    """The only new-workflow report registration path, guarded by actual acceptance."""
    state = check_publication(output_dir, root)
    out = Path(output_dir)
    contract = read_json(out / "contract.json")
    relative = Path(contract["publication"]["report_path"])
    if relative.is_absolute() or relative.parent != Path("docs/experiments") or relative.suffix != ".md":
        raise WorkflowBlocked("report must be a new dated docs/experiments markdown file")
    try:
        from datetime import date
        date.fromisoformat(relative.stem[-10:])
    except ValueError:
        raise WorkflowBlocked("report filename must carry its date")
    registry_path = Path(root) / "docs/experiments/registry.json"
    with registry_path.open("r+", encoding="utf-8") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        registry = json.load(stream)
        category = contract["publication"]["category"]
        if category not in registry["categories"]:
            raise WorkflowBlocked("unknown report category")
        target = Path(root) / relative
        if target.exists() or str(relative) in registry["entries"]:
            raise WorkflowBlocked("refusing to overwrite an existing report/registration")
        target.write_text((out / "report.md").read_text(encoding="utf-8"), encoding="utf-8")
        registry["entries"][str(relative)] = {
            "category": category, "verdict": "mixed" if state["evidence"] != "supported" else "passed",
            "oneLiner": "合成流程案例，仅验证研究检查与诚实结案，不构成市场效果证据。" if contract["data"]["mode"] == "synthetic" else None,
            "workflow_receipt": str(out / "receipt.json"),
        }
        stream.seek(0)
        stream.write(json.dumps(registry, ensure_ascii=False, indent=2) + "\n")
        stream.truncate()
        fcntl.flock(stream, fcntl.LOCK_UN)
    return state


def execute_workflow(contract_path, output_dir, *, root=ROOT, executor=None, register_report=False, reuse_predictions=None):
    started = time.monotonic()
    contract = read_json(contract_path)
    accounting = {"charged": False}
    try:
        preflight(contract, root)  # Rejections log cost, never invoke statistics.
        with family_execution_lock(root, contract):
            return _execute_workflow(contract_path, output_dir, root=root, executor=executor,
                                     register_report=register_report, reuse_predictions=reuse_predictions,
                                     started_at=started, accounting=accounting)
    except BaseException as error:
        if not accounting["charged"]:
            _record_gate_failure(contract, root, started, error)
        raise


def _execute_workflow(contract_path, output_dir, *, root=ROOT, executor=None, register_report=False, reuse_predictions=None, started_at=None, accounting=None):
    """Precheck -> reserve -> evaluator -> receipt -> publication acceptance.

    A callback is injected only for integration tests or explicitly frozen adapters.
    The CLI uses the built-in finite evaluator menu. It cannot import arbitrary raw scripts.
    """
    from lei_signal.research.workflow_evaluation import evaluate_observations, summarize_predictions
    out = Path(output_dir)
    if out.exists():
        raise WorkflowBlocked("refusing to overwrite sealed/existing outputs")
    contract = read_json(contract_path)
    started = started_at if started_at is not None else time.monotonic()
    run_id = None
    proof = None
    cost_recorded = False
    callback_started = False
    # No directory/ledger side effect, let alone statistical callback, before the gate.
    proof = preflight(contract, root)
    _require_rehearsal(contract)
    if digest(proof["observations"]) != contract.get("freeze", {}).get("observations_digest"):
        raise WorkflowBlocked("stale_freeze: features/label qualification changed")
    run_id = _reserve(contract, proof, out, root, reuse=bool(reuse_predictions))
    out.mkdir(parents=True, exist_ok=False)
    try:
        write_json(out / "contract.json", contract)
        write_json(out / "preflight.json", proof)
        if reuse_predictions:
            _, previous_proof, _ = verify_receipt(reuse_predictions, root)
            if previous_proof["cache_keys"]["prediction"] != proof["cache_keys"]["prediction"]:
                raise WorkflowBlocked("cache_invalid: feature/label/data/split/evaluator changed")
            if contract["feature"]["kind"] == "ema_sma_waiting_path" and previous_proof["cache_keys"]["aggregate"] != proof["cache_keys"]["aggregate"]:
                raise WorkflowBlocked("cache_invalid: waiting-path reuse requires the same scientific aggregation")
            previous = read_json(Path(reuse_predictions) / "result.json")
            if contract["feature"]["kind"] == "ema_sma_waiting_path":
                result = copy.deepcopy(previous)
            else:
                result = summarize_predictions(previous["predictions"], contract, proof["observations"])
            result["execution"] = {**result.get("execution", {}), "fits": 0,
                                   "reused_from": str(reuse_predictions)}
        else:
            # Enforce the remaining elapsed budget in the CLI/main thread. The
            # checker is not a sandbox for callbacks launching their own processes.
            remaining = contract["budget"]["execution_seconds"]
            with locked_journal(family_ledger(root, contract["history"]["family"])) as (_, records):
                remaining -= sum(r.get("seconds", 0) for r in records if r["event"] in COST_EVENTS)
            old_handler = signal.getsignal(signal.SIGALRM)
            old_timer = signal.getitimer(signal.ITIMER_REAL)
            def timed_out(*_):
                raise WorkflowPaused("execution time budget interrupted")
            signal.signal(signal.SIGALRM, timed_out)
            signal.setitimer(signal.ITIMER_REAL, max(0.001, remaining))
            try:
                callback_started = True
                if contract["feature"]["kind"] == "ema_sma_waiting_path" and executor is None:
                    from lei_signal.research.ema_sma_waiting_path import evaluate_waiting_paths
                    result = evaluate_waiting_paths(read_json(resolve_path(root, contract["data"]["path"])),
                                                    contract, proof["observations"], root=root)
                else:
                    result = (executor or evaluate_observations)(proof["observations"], contract)
            finally:
                signal.setitimer(signal.ITIMER_REAL, *old_timer)
                signal.signal(signal.SIGALRM, old_handler)
        if contract.get("descriptive"):
            from lei_signal.research.workflow_descriptions import summarize_price_groups
            result["factor_descriptions"] = summarize_price_groups(proof["observations"], read_json(resolve_path(root, contract["data"]["path"])), contract)
        if contract["feature"]["kind"] != "ema_sma_waiting_path":
            for item in result["increments"]:
                if item.get("lo") is not None and item["lo"] <= 0 <= item["hi"]:
                    result["warnings"].append(_warning("uncertain_increment", f"{item['new_model']}相对{item['old_model']}的范围仍包含改善及恶化，当前不能确认稳定帮助。"))
            years = {p["date"][:4] for p in result["predictions"]}
            if len(years) < 2:
                result["warnings"].append(_warning("single_year", "预测评价只覆盖一个年份，不能据此确认跨年份重复。"))
        elapsed = time.monotonic() - started
        if elapsed > contract["budget"]["execution_seconds"]:
            raise WorkflowPaused("budget interrupted: retain outputs, do not mark ineffective/completed")
        if contract["feature"]["kind"] == "double_ma_order_information":
            from lei_signal.research.double_ma_order_information import attach_primary_rmse
            attach_primary_rmse(result, contract, proof["observations"])
            if time.monotonic() - started > contract["budget"]["execution_seconds"]:
                raise WorkflowPaused("budget interrupted including T03 paired RMSE aggregation")
        write_json(out / "result.json", result)
        (out / "report.md").write_text(render_report(contract, proof, result), encoding="utf-8")
        receipt = {"schema_version": "workflow-receipt/1.0", "run_id": run_id,
                   "entry": "scripts/run_factor_lab.py --workflow-contract",
                   "contract_sha256": file_hash(out / "contract.json"),
                   "cache_keys": proof["cache_keys"], "callback_executed": True,
                   "outputs": {p.name: file_hash(p) for p in (out / "preflight.json", out / "result.json", out / "report.md")}}
        write_json(out / "receipt.json", receipt)
        _finish(contract, root, run_id, proof, elapsed, "computed", file_hash(out / "receipt.json"))
        if accounting is not None:
            accounting["charged"] = True
        callback_seconds = elapsed
        cost_recorded = True
        state = check_publication(out, root)
        write_json(out / "state.json", state)
        if register_report:
            publish(out, root)
        with locked_journal(family_ledger(root, contract["history"]["family"])) as (stream, _):
            _append(stream, {"event": "acceptance", "run_id": run_id,
                "seconds": max(0, time.monotonic() - started - elapsed), "state": state})
        return state
    except BaseException as exc:
        elapsed = time.monotonic() - started
        _finish(contract, root, run_id, proof, 0 if cost_recorded else elapsed,
                "publication_failed" if cost_recorded else "failed_after_callback")
        if accounting is not None:
            accounting["charged"] = True
        if cost_recorded:
            with locked_journal(family_ledger(root, contract["history"]["family"])) as (stream, _):
                _append(stream, {"event": "acceptance", "run_id": run_id,
                    "seconds": max(0, elapsed - callback_seconds), "state": "publication_failed"})
        if not (out / "failure.json").exists():
            write_json(out / "failure.json", {"execution": "paused" if isinstance(exc, (WorkflowPaused, KeyboardInterrupt, SystemExit)) else "blocked", "evidence": "not_evaluated",
                                             "error": f"{type(exc).__name__}: {exc}", "seconds": elapsed,
                                             "run_id": run_id, "callback_executed": callback_started})
        raise


def run_workflow(contract_path, output_dir, *, register_report=False, reuse_predictions=None):
    import sys
    started = time.monotonic()
    try:
        execute_workflow(contract_path, output_dir, register_report=register_report,
                         reuse_predictions=reuse_predictions)
        return 0
    except (ValueError, OSError, KeyError) as exc:
        out = Path(output_dir)
        if not out.exists():
            out.mkdir(parents=True, exist_ok=False)
            write_json(out / "failure.json", {"execution": "paused" if isinstance(exc, WorkflowPaused) else "blocked", "evidence": "not_evaluated",
                "stage": "pre_execution", "callback_executed": False,
                "seconds": time.monotonic() - started,
                "error": f"{type(exc).__name__}: {exc}", "requested_contract": str(contract_path)})
        print(f"workflow blocked before full acceptance: {exc}", file=sys.stderr)
        return 2 if isinstance(exc, WorkflowPaused) else 3
