"""Release checks and append-only local attempt claims, not scientific review."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TASK = "leisignal-risk-run-20261009"
PATH_IDS = ["A_ALL-base", "A_ALL-stress", "A_SMA-base", "A_SMA-stress"]
B_OWNER = "01a1208c-d559-72f0-ba6e-980a4337fa2c"
C_TASK = "leisignal-risk-review-20261009"
C_OWNER = "01a1208d-49ba-7972-9fa1-b47d7d5749b7"


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_file(item):
    path = Path(item["path"])
    require(path.is_file(), f"bound file missing: {path}")
    require(path.stat().st_size == item["bytes"] and sha256(path) == item["sha256"],
            f"bound source bytes/hash drift: {path}")
    return path


def validate_release(contract, contract_hash, authorization, review, code_hashes,
                     input_manifest_hash, attempted_ids, batch_already_started):
    """No invocation may reinterpret a prior two-path permission or C preflight."""
    require(contract["task_id"] == TASK and contract["owner_session"] == B_OWNER, "wrong task/owner")
    require(contract.get("status") == "frozen_for_C_review", "contract not frozen")
    scope = contract["scope"]
    expected = {"symbol": "510300.SS", "start": "2026-01-01", "end": "2026-06-30",
                "reference_accounts": ["A_ALL", "A_SMA"],
                "fees": {"base": "0.001", "stress": "0.002"},
                "path_ids": PATH_IDS, "rolling_trading_days": 63,
                "stdev_ddof": 1, "risk_tolerance": ["0.90", "1.10"],
                "history_status": "already_observed_exploration"}
    require(scope == expected, "fixed scope/parameters changed")
    require(contract["budget"]["proposed_paths"] == 4, "exact four-path budget required")
    for key in ("original_A_replays", "new_signals_or_labels", "downloads", "predictive_fits", "parameter_scans"):
        require(contract["budget"][key] == 0, f"forbidden budget: {key}")
    require(contract["inputs"]["sha256"] == input_manifest_hash, "A manifest binding drift")
    require(authorization.get("status") == "approved" and authorization.get("task_id") == TASK,
            "explicit user four-path authorization missing")
    require(authorization.get("authorized_path_ids") == PATH_IDS, "permission not for exact four paths")
    require(authorization.get("contract_sha256") == contract_hash, "authorization contract mismatch")
    require(all(authorization.get(k) for k in ("user_quote", "source_thread", "authorized_at")),
            "human authorization provenance missing")
    require(review.get("decision") == "accepted" and review.get("task_id") == C_TASK
            and review.get("reviewer_session") == C_OWNER and C_OWNER != B_OWNER,
            "independent C code acceptance missing")
    require(review.get("contract_sha256") == contract_hash, "C contract binding mismatch")
    require(review.get("input_manifest_sha256") == input_manifest_hash, "C A input binding mismatch")
    require(review.get("code_sha256") == code_hashes, "C code binding mismatch")
    require(review.get("synthetic_evidence_sha256") == contract["synthetic_evidence"]["sha256"],
            "C synthetic evidence mismatch")
    require(not attempted_ids and not batch_already_started, "one-time batch already consumed; no rerun")
    return {"authorized_path_ids": PATH_IDS, "maximum_attempts_per_path": 1,
            "contract_sha256": contract_hash, "input_manifest_sha256": input_manifest_hash}


def now():
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()


def append_record(directory, filename, value):
    """Small scientific attempt records stay local; O_EXCL is the race check."""
    directory = Path(directory)
    require(not directory.is_symlink(), "attempt directory symlink refused")
    directory.mkdir(exist_ok=True)
    fd = os.open(directory/filename, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def claim_batch(directory, release, run_id):
    append_record(directory, "batch-started.json", {"task_id": TASK, "created_at": now(),
                  "status": "consumed_no_automatic_rerun", "run_id": run_id, **release})


def claim_path(directory, path_id, release, run_id):
    require(path_id in PATH_IDS, "unknown path id")
    append_record(directory, path_id+"-started.json", {"path_id": path_id, "attempt_number": 1,
                  "started_at": now(), "run_id": run_id, **release})


def actual_attempts(directory):
    directory = Path(directory)
    started = []
    for path_id in PATH_IDS:
        if (directory/(path_id+"-started.json")).is_file():
            started.append(path_id)
    return started, (directory/"batch-started.json").exists()
