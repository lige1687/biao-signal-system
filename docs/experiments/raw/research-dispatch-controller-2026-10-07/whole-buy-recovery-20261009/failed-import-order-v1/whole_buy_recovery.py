"""Committed-boundary recovery for one frozen, synthetic P0 whole-buy batch."""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import hashlib
import json
import os
import plistlib
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
RAW = HERE.parent
ADAPTER = RAW / "weekly-portfolio-order-ledger-adapter-2026-10-08"
sys.path.insert(0, str(ADAPTER))
from order_ledger_adapter_v2 import SyntheticAccount, attempt_open, planner  # noqa: E402

SOURCE_PATHS = {
    "spec": RAW / "weekly-portfolio-dated-execution-2026-10-08/source-baseline/shared-account-spec.md",
    "ledger": RAW / "weekly-portfolio-dated-execution-2026-10-08/dated_ledger.py",
    "planner_v2": RAW / "weekly-portfolio-order-planning-2026-10-08/order_planning_v2.py",
    "planner_v1": RAW / "weekly-portfolio-order-planning-2026-10-08/order_planning.py",
    "adapter_v2": ADAPTER / "order_ledger_adapter_v2.py",
}
SOURCE_HASHES = {
    "spec": "695ce8a18e34d3520c53f793b1f347a05e146fea345474b5d72224ba93c30a5a",
    "ledger": "20f6547deea6d19c6416daa6048ee18a7111ff6bf4c7b21bbae90a7b379e62d3",
    "planner_v2": "a9ab958fa737fc53e7a08905da9ffd82b40687354f2b8be2d508db121a13b958",
    "planner_v1": "645cac7faa6fc25bd95e0c25b63621d4e233b501a6d0b946895ff685b584a75a",
    "adapter_v2": "3bfb632f40a234e76813937a2e900377eec148d8c520acf06eb6b8601bb1e8ba",
}
FIXTURE_SHA = "bffa2c3217fd07cbbbff4f3ec42d5cfd0c54ffc63084e9e455da3bbb6fd84ab8"
MOUNT = Path("/Volumes/win+mac通用")
VOLUME_UUID = "DEBA1C85-6059-3865-B50A-A8EE1F80E4D9"


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def encode(value):
    if isinstance(value, Decimal):
        return {"$decimal": str(value)}
    if isinstance(value, datetime):
        return {"$datetime": value.isoformat()}
    if is_dataclass(value):
        return encode(asdict(value))
    if isinstance(value, tuple):
        return {"$tuple": [encode(x) for x in value]}
    if isinstance(value, set):
        items = [encode(x) for x in value]
        return {"$set": sorted(items, key=canonical)}
    if isinstance(value, list):
        return [encode(x) for x in value]
    if isinstance(value, dict):
        if not all(isinstance(k, str) for k in value):
            raise ValueError("non-string dictionary key unsupported")
        return {k: encode(v) for k, v in value.items()}
    if value is None or type(value) in (str, int, float, bool):
        return value
    raise ValueError("unsupported state type")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def _verify_inputs():
    if {k: sha(p) for k, p in SOURCE_PATHS.items()} != SOURCE_HASHES:
        raise ValueError("frozen source SHA mismatch")
    if sha(HERE / "frozen-fixtures.json") != FIXTURE_SHA:
        raise ValueError("frozen fixture SHA mismatch")
    return json.loads((HERE / "frozen-fixtures.json").read_text())


def _external_guard(plan, destination):
    output = Path(plan["output"])
    destination = Path(destination)
    if plan["external_uuid"] != VOLUME_UUID or plan["external_mount"] != str(MOUNT):
        raise ValueError("plan identity mismatch")
    if output != Path(plan["run_directory"]) / "result" or output.parent.parent.name != plan["task_id"]:
        raise ValueError("plan route mismatch")
    if not destination.is_relative_to(output) or any(p.is_symlink() for p in (destination, *destination.parents)):
        raise ValueError("state path outside plain external result")
    info = plistlib.loads(subprocess.check_output(["/usr/sbin/diskutil", "info", "-plist", str(MOUNT)], timeout=10))
    if (not os.path.ismount(MOUNT) or info.get("VolumeUUID") != VOLUME_UUID
            or info.get("MountPoint") != str(MOUNT) or info.get("Internal") is not False
            or info.get("Writable") is not True or os.stat(MOUNT).st_dev != plan["external_device"]):
        raise ValueError("external storage identity changed")
    existing = next((p for p in (destination, *destination.parents) if p.exists()), None)
    if existing is None or existing.stat().st_dev != plan["external_device"]:
        raise ValueError("external destination device mismatch")


def _construct(fixture, profile):
    if profile not in fixture["profiles"]:
        raise ValueError("unknown fixed fixture profile")
    op = fixture["opening_at"]
    release = fixture["release_at"]
    calendar = {
        "name": fixture["calendar_name"], "timezone": "Asia/Shanghai",
        "clocks": {op: [3], release: [3]}, "actions": {}, "closes": {},
        "opens": {op: {s: {"price": Decimal(price), "buy": True, "sell": False,
                            "release_at": release, "observed_at": fixture["known_at"],
                            "decision_at": fixture["decision_at"]}
                       for s, price in fixture["profiles"][profile].items()}},
    }
    account = SyntheticAccount(fixture["name"], calendar, initial_at=fixture["known_at"],
                               cash=Decimal(fixture["cash"]), units=Decimal(fixture["units"]),
                               prior_complete={"at": fixture["known_at"], "nav": Decimal(1)},
                               marks={s: Decimal(v) for s, v in fixture["references"].items()})
    c = fixture["costs"]
    costs = planner.Costs(c["commission"], c["minimum"], c["slippage"], c["name"])
    decision, cash = account.decision(name=fixture["decision_name"],
                                      decision_at=fixture["decision_at"],
                                      reference_known_at=fixture["known_at"],
                                      references=fixture["references"], costs=costs)
    context = planner.ActionContext(fixture["action_coverage_name"], fixture["action_source"],
                                    fixture["known_at"], fixture["known_at"], op, ())
    plan = planner.plan_p0(decision, current_cash=cash, action_context=context,
                           frozen_at=fixture["frozen_at"], opening_at=op)
    if (plan.status != "ready" or plan.funding_receipt is not None or len(plan.orders) != 2
            or any(o.side != "buy" or o.quantity != Decimal("100") for o in plan.orders)):
        raise ValueError("P0 fixed whole-buy plan differs")
    batch = account.begin(decision, plan)
    return account, decision, plan, batch


def _runtime(account, decision, plan, batch):
    if account._sale_results or account.calendar_events:
        raise ValueError("outside pure-buy account state")
    return encode({
        "decision": decision, "plan": plan, "ledger_snapshot": account.ledger.snapshot(),
        "ledger_audit": account.ledger.audit, "calendar": account._calendar,
        "calendar_hash": account.calendar_hash,
        "original_decision_hash": account._original_decision_hash,
        "attempted_keys": account._attempted_keys,
        "batch_expected": batch.expected, "batch_receipts": batch.receipts,
        "batch_stopped": batch.stopped, "cash_sources": account._cash_sources,
        "decisions": account._decisions, "sale_results": account._sale_results,
    })


def _request(run_id, decision, plan, account, index):
    order = plan.orders[index]
    opening = account.opening(order.symbol, order.opening_at.isoformat())
    content = encode({"run_id": run_id, "decision_hash": decision.input_hash,
                      "plan_hash": plan.plan_hash, "order": order, "opening": opening})
    return {"request_id": digest((run_id, decision.input_hash, plan.plan_hash, order.order_id, encode(opening))),
            "content": content, "content_sha256": digest(content)}


def _sealed(state):
    content = {k: v for k, v in state.items() if k != "state_sha256"}
    return {**content, "state_sha256": digest(content)}


class Recovery:
    def __init__(self, plan, case, slot="single"):
        if case not in ("normal", "first_rejected"):
            raise ValueError("fixed case required")
        bases = ("single", "normal_path", "refusal_path", "duplicate", "before_fault",
                 "after_fault", "request_identity", "corruption", "unsupported",
                 "process_success", "process_refusal")
        if not any(re.fullmatch(re.escape(base) + r"(?:_v[1-9][0-9]*)?", slot) for base in bases):
            raise ValueError("fixed verification slot required")
        self.plan = plan
        self.case = case
        self.slot = slot
        self.run_key = plan["run_id"] + ":" + slot
        self.path = Path(plan["output"]) / slot / case / "state.json"

    def _read(self):
        _external_guard(self.plan, self.path)
        fixture = _verify_inputs()
        if not self.path.is_file():
            raise ValueError("state absent; explicit creation required")
        state = json.loads(self.path.read_text())
        if state != _sealed(state):
            raise ValueError("state digest differs")
        if (state.get("schema") != "whole-buy-recovery/1" or state.get("profile") != self.case
                or state.get("run_id") != self.run_key
                or state.get("fixture_sha256") != FIXTURE_SHA
                or state.get("source_sha256") != SOURCE_HASHES
                or state.get("wrapper_sha256") != sha(__file__)):
            raise ValueError("state frozen identity differs")
        account, decision, plan, batch = _construct(fixture, self.case)
        if state.get("decision_hash") != decision.input_hash or state.get("plan_hash") != plan.plan_hash:
            raise ValueError("state decision or plan differs")
        history = state.get("history")
        if not isinstance(history, list) or len(history) > len(plan.orders):
            raise ValueError("invalid history")
        apply_count = 0
        for i, record in enumerate(history):
            expected = _request(self.run_key, decision, plan, account, i)
            if record.get("request") != expected:
                raise ValueError("saved request identity differs")
            order = plan.orders[i]
            receipt = attempt_open(decision, plan, order, account.opening(order.symbol, order.opening_at.isoformat()), account.ledger, batch)
            apply_count += receipt.ledger_apply_count
            if record.get("receipt") != encode(receipt):
                raise ValueError("saved receipt differs from original replay")
        if state.get("next_index") != len(history) or state.get("runtime") != _runtime(account, decision, plan, batch):
            raise ValueError("saved complete state differs from original replay")
        return state, account, decision, plan, batch, apply_count

    def create(self):
        _external_guard(self.plan, self.path)
        fixture = _verify_inputs()
        if self.path.exists():
            raise ValueError("existing state cannot be initialized again")
        account, decision, plan, batch = _construct(fixture, self.case)
        state = _sealed({"schema": "whole-buy-recovery/1", "run_id": self.run_key,
                         "profile": self.case, "source_sha256": SOURCE_HASHES,
                         "fixture_sha256": FIXTURE_SHA, "wrapper_sha256": sha(__file__),
                         "decision_hash": decision.input_hash, "plan_hash": plan.plan_hash,
                         "next_index": 0, "history": [],
                         "runtime": _runtime(account, decision, plan, batch)})
        self._commit(state, exclusive=True)
        return self.inspect()

    def inspect(self):
        state, account, decision, plan, batch, replay_apply = self._read()
        return {"state_sha256": state["state_sha256"], "next_index": state["next_index"],
                "cash": format(account.ledger.snapshot()["cash"], ".2f"),
                "fees": format(account.ledger.snapshot()["fees"], ".2f"),
                "receipts": [r["receipt"] for r in state["history"]],
                "runtime": state["runtime"], "recovery_replay_apply_count": replay_apply,
                "new_order_apply_count": 0}

    def request(self, index):
        _, account, decision, plan, _, _ = self._read()
        if type(index) is not int or not 0 <= index < len(plan.orders):
            raise ValueError("fixed order index required")
        return _request(self.run_key, decision, plan, account, index)

    def submit(self, request, fail_at=None):
        state, account, decision, plan, batch, replay_apply = self._read()
        matches = [i for i in range(len(plan.orders))
                   if isinstance(request, dict) and request.get("request_id") ==
                   _request(self.run_key, decision, plan, account, i)["request_id"]]
        if len(matches) != 1:
            raise ValueError("unknown fixed request identity")
        index = matches[0]
        expected = _request(self.run_key, decision, plan, account, index)
        if request != expected:
            raise ValueError("complete request content differs")
        if index < state["next_index"]:
            return {"receipt": state["history"][index]["receipt"],
                    "replay_ignored": True, "recovery_replay_apply_count": replay_apply,
                    "new_order_apply_count": 0, "state_sha256": state["state_sha256"]}
        if index != state["next_index"]:
            raise ValueError("fixed serial order differs")
        order = plan.orders[index]
        receipt = attempt_open(decision, plan, order, account.opening(order.symbol, order.opening_at.isoformat()), account.ledger, batch)
        next_state = _sealed({**{k: v for k, v in state.items() if k != "state_sha256"},
                              "next_index": index + 1,
                              "history": state["history"] + [{"request": expected, "receipt": encode(receipt)}],
                              "runtime": _runtime(account, decision, plan, batch)})
        self._commit(next_state, fail_at=fail_at)
        return {"receipt": encode(receipt), "replay_ignored": False,
                "recovery_replay_apply_count": replay_apply,
                "new_order_apply_count": receipt.ledger_apply_count,
                "state_sha256": next_state["state_sha256"]}

    def _commit(self, state, exclusive=False, fail_at=None):
        _external_guard(self.plan, self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        _external_guard(self.plan, self.path)
        if exclusive and self.path.exists():
            raise ValueError("state already exists")
        temp = self.path.with_name("state.tmp." + os.urandom(8).hex())
        payload = (canonical(state) + "\n").encode()
        with temp.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if fail_at == "before_replace":
            raise OSError("injected failure before replace; prior state authoritative")
        _external_guard(self.plan, self.path)
        os.replace(temp, self.path)
        directory_fd = os.open(self.path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        if fail_at == "after_replace":
            raise OSError("injected lost response after committed replace")
