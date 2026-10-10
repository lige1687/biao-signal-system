"""One synthetic account across two frozen, manually ordered weekly batches.

The order list is test input, not a portfolio allocation or trading policy.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CONTRACT = HERE / "executor-contract.json"
FIXTURE = HERE / "frozen-fixtures.json"
SOURCE_MANIFEST = HERE / "source-manifest.json"
LEDGER_PATH = (
    ROOT / "docs/experiments/raw/weekly-portfolio-dated-execution-2026-10-08/dated_ledger.py"
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical(value):
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )


def encode(value):
    if isinstance(value, Decimal):
        return {"$decimal": str(value)}
    if isinstance(value, set):
        return {"$set": sorted((encode(x) for x in value), key=canonical)}
    if isinstance(value, list):
        return [encode(x) for x in value]
    if isinstance(value, tuple):
        return [encode(x) for x in value]
    if isinstance(value, dict):
        require(all(isinstance(key, str) for key in value), "non-string state key")
        return {key: encode(item) for key, item in value.items()}
    if value is None or type(value) in (str, int, float, bool):
        return value
    raise ValueError("unsupported state value")


def verify_original_sources(manifest):
    for relative, expected in manifest["originals"].items():
        require(sha(ROOT / relative) == expected, f"frozen source SHA mismatch: {relative}")
    require(sha(FIXTURE) == manifest["fixture_sha256"], "frozen fixture SHA mismatch")


def load_frozen():
    """Check every selected original before executing the old ledger module."""
    contract = json.loads(CONTRACT.read_text())
    manifest = json.loads(SOURCE_MANIFEST.read_text())
    require(contract["schema"] == "cross-week-fixed-orders-contract/1", "contract schema drift")
    require(contract["source_sha256"] == manifest["originals"], "source manifest drift")
    require(contract["fixture_sha256"] == manifest["fixture_sha256"], "fixture manifest drift")
    verify_original_sources(manifest)
    fixture = json.loads(FIXTURE.read_text())
    require(fixture["schema"] == "cross-week-fixed-orders-fixture/1", "fixture schema drift")
    spec = importlib.util.spec_from_file_location("cross_week_frozen_dated_ledger", LEDGER_PATH)
    require(spec is not None and spec.loader is not None, "dated ledger import unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return contract, manifest, fixture, module


def clock(day, hhmm):
    return f"{day}T{hhmm}:00+08:00"


def steps(fixture):
    orders = fixture["fixed_orders"]
    require(
        len(orders) == 4
        and [o["id"] for o in orders] == ["w1:TEST_A", "w1:TEST_B", "w2:TEST_A", "w2:TEST_B"],
        "frozen order sequence drift",
    )
    result = [{"kind": "order", **order} for order in orders[:2]]
    result += [
        {"kind": "close", "id": f"close:{day}", "day": day} for day in fixture["daily_close_days"]
    ]
    result += [{"kind": "deposit", **fixture["second_week_deposit"]}]
    result += [{"kind": "order", **order} for order in orders[2:]]
    require(len(result) == 10 and len({x["id"] for x in result}) == 10, "step identity drift")
    return result


def calendar(fixture):
    day1 = fixture["first_week_day"]
    day2 = fixture["second_week_day"]
    closes = {clock(day, "15:00"): fixture["prices"] for day in fixture["daily_close_days"]}
    clocks = {at: [4] for at in closes}
    opens = {}
    for day in (day1, day2):
        at = clock(day, "09:30")
        release_day = "2026-01-06" if day == day1 else "2026-01-13"
        release_at = clock(release_day, "09:30")
        clocks.setdefault(at, []).append(3)
        clocks.setdefault(release_at, []).append(3)
        opens[at] = {}
        for symbol in fixture["prices"]:
            selected = next(
                o
                for o in fixture["fixed_orders"]
                if o["asset"] == symbol and o["allowed_open"] == at
            )
            opens[at][symbol] = {
                "buy": selected["permitted"],
                "price": fixture["prices"][symbol],
                "observed_at": clock("2026-01-02" if day == day1 else "2026-01-09", "15:00"),
                "decision_at": selected["decision_at"],
                "release_at": release_at,
            }
    clocks[fixture["second_week_deposit"]["at"]] = [0]
    return {
        "name": "fixed-two-week-artificial-calendar",
        "timezone": "Asia/Shanghai",
        "clocks": clocks,
        "opens": opens,
        "closes": closes,
    }


def event_for(request, fixture, ledger):
    if request["kind"] == "close":
        return {"id": request["id"], "kind": "close", "at": clock(request["day"], "15:00")}
    if request["kind"] == "deposit":
        prior = ledger.snapshot()["prior_complete"]
        require(
            prior is not None and prior["at"] == clock(request["previous_complete_day"], "15:00"),
            "saved Jan9 complete NAV required",
        )
        return {
            "id": request["id"],
            "kind": "deposit",
            "at": request["at"],
            "amount": request["amount"],
        }
    require(request["kind"] == "order", "unknown step kind")
    require(request["quantity"] == fixture["lot"], "order quantity drift")
    return {
        "id": request["id"],
        "kind": "buy",
        "at": request["allowed_open"],
        "symbol": request["asset"],
        "qty": request["quantity"],
        "price": calendar(fixture)["opens"][request["allowed_open"]][request["asset"]]["price"],
        "commission_rate": fixture["costs"]["commission_rate"],
        "minimum_commission": fixture["costs"]["minimum_commission"],
        "slippage_rate": fixture["costs"]["slippage_cost_rate"],
    }


def perform(ledger, request, fixture, module):
    before = ledger.snapshot()
    if request["kind"] == "order":
        binding = calendar(fixture)["opens"][request["allowed_open"]][request["asset"]]
        if not binding["buy"]:
            return {"status": "refused", "reason": "not permitted opening", "event": None}
        if module.number(binding["price"]) > module.number(request["limit"]):
            return {"status": "refused", "reason": "opening above fixed limit", "event": None}
        full_cost = module.number(request["quantity"]) * module.number(binding["price"])
        full_cost += module.fee(
            full_cost,
            fixture["costs"]["commission_rate"],
            fixture["costs"]["minimum_commission"],
            fixture["costs"]["slippage_cost_rate"],
        )
        if full_cost > module.number(request["budget"]):
            return {"status": "refused", "reason": "fixed order budget exceeded", "event": None}
    event = event_for(request, fixture, ledger)
    try:
        receipt = ledger.apply(event)
    except ValueError as error:
        if request["kind"] != "order":
            raise
        require(ledger.snapshot() == before, "rejected order changed money state")
        return {"status": "refused", "reason": str(error), "event": None}
    return {"status": "accepted", "receipt": encode(receipt), "event": event}


def make_ledger(fixture, module):
    return module.Ledger(
        calendar(fixture),
        cash=fixture["initial_cash"],
        units=fixture["initial_account_units"],
        marks=fixture["prices"],
    )


def summary(ledger, fixture):
    state = ledger.snapshot()
    value = ledger.equity(fixture["prices"])
    initial = Decimal(fixture["initial_cash"])
    require(state["cash"] >= 0, "negative cash")
    require(
        value + state["fees"] == initial + state["inflows"], "shared money conservation failure"
    )
    return {
        "cash": str(state["cash"]),
        "assets": str(value),
        "fees": str(state["fees"]),
        "units": str(state["units"]),
        "inflows": str(state["inflows"]),
        "positions": {symbol: str(ledger.shares(symbol)) for symbol in fixture["prices"]},
        "prior_complete": encode(state["prior_complete"]),
        "ledger_state": encode(state),
        "ledger_audit": encode(ledger.audit),
    }


class Engine:
    def __init__(self, directory, fixture, manifest, module, *, strict_fixture_sha=None):
        self.directory = Path(directory)
        self.state_path = self.directory / "state.json"
        self.fixture = deepcopy(fixture)
        self.manifest = deepcopy(manifest)
        self.module = module
        self.executor_sha = sha(__file__)
        self.plan = steps(fixture)
        self.fixture_sha = (
            strict_fixture_sha or hashlib.sha256(canonical(fixture).encode()).hexdigest()
        )
        require(self.directory.is_dir(), "engine directory missing")
        verify_original_sources(self.manifest)
        if self.state_path.exists():
            self.state = json.loads(self.state_path.read_text())
            require(
                self.state["schema"] == "cross-week-fixed-orders-state/1", "bad checkpoint schema"
            )
            require(
                self.state["fixture"] == self.fixture
                and self.state["fixture_sha256"] == self.fixture_sha,
                "foreign or drifted fixture checkpoint",
            )
            require(
                self.state["source_manifest"] == self.manifest, "source version checkpoint drift"
            )
            require(
                self.state.get("executor_sha256") == self.executor_sha,
                "executor version checkpoint drift",
            )
            require(self.state["plan"] == self.plan, "frozen plan checkpoint drift")
        else:
            require(
                not any(self.directory.iterdir()), "missing checkpoint in nonempty engine directory"
            )
            self.state = {
                "schema": "cross-week-fixed-orders-state/1",
                "fixture": self.fixture,
                "fixture_sha256": self.fixture_sha,
                "source_manifest": self.manifest,
                "executor_sha256": self.executor_sha,
                "plan": self.plan,
                "history": [],
                "cursor": 0,
                "summary": None,
            }
            self._write(self.state, exclusive=True)
        self.ledger = self._reconstruct()

    def _verify_binding(self):
        verify_original_sources(self.manifest)
        require(
            sha(__file__) == self.state.get("executor_sha256"), "executor version checkpoint drift"
        )

    def _write(self, state, *, exclusive=False, fault=None):
        temp = self.directory / f"state.next.{os.getpid()}"
        require(not temp.exists(), "prior temporary checkpoint needs inspection")
        with temp.open("x") as handle:
            json.dump(state, handle, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if fault == "pre_replace":
            raise RuntimeError("injected failure before checkpoint replace")
        if exclusive:
            require(not self.state_path.exists(), "checkpoint already exists")
        os.replace(temp, self.state_path)
        directory_fd = os.open(self.directory, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        if fault == "post_replace":
            raise RuntimeError("injected response loss after checkpoint replace")

    def _reconstruct(self):
        state = self.state
        self._verify_binding()
        require(
            type(state["cursor"]) is int
            and state["cursor"] == len(state["history"])
            and 0 <= state["cursor"] <= len(self.plan),
            "bad or skipped cursor",
        )
        ledger = make_ledger(self.fixture, self.module)
        for index, entry in enumerate(state["history"]):
            self._verify_binding()
            expected = self.plan[index]
            require(entry["request"] == expected, "saved request identity drift")
            result = perform(ledger, expected, self.fixture, self.module)
            require(entry["result"] == encode(result), "checkpoint event reconstruction mismatch")
            require(
                entry["summary"] == summary(ledger, self.fixture),
                "checkpoint ledger reconstruction mismatch",
            )
        expected_summary = summary(ledger, self.fixture) if state["history"] else None
        require(state["summary"] == expected_summary, "checkpoint final state mismatch")
        return ledger

    def next_request(self):
        if self.state["cursor"] == len(self.plan):
            return None
        return deepcopy(self.plan[self.state["cursor"]])

    def submit(self, request, *, fault=None):
        self._verify_binding()
        require(
            isinstance(request, dict) and isinstance(request.get("id"), str),
            "request identity missing",
        )
        known = next((i for i, item in enumerate(self.plan) if item["id"] == request["id"]), None)
        require(known is not None, "foreign request")
        require(request == self.plan[known], "same identity changed request")
        if known < self.state["cursor"]:
            return deepcopy(self.state["history"][known])
        require(known == self.state["cursor"], "premature, missing, or skipped action")
        before = self.ledger.snapshot()
        before_nav = None
        if request["kind"] == "deposit":
            prior = before["prior_complete"]
            require(prior is not None, "prior complete NAV missing")
            before_nav = self.ledger.equity(self.fixture["prices"]) / before["units"]
            require(prior["nav"] == before_nav, "saved prior NAV differs from actual ledger")
        result = perform(self.ledger, request, self.fixture, self.module)
        after = summary(self.ledger, self.fixture)
        if result["status"] == "refused":
            require(self.ledger.snapshot() == before, "refused order changed ledger")
        if before_nav is not None:
            after_nav = self.ledger.equity(self.fixture["prices"]) / self.ledger.snapshot()["units"]
            require(abs(after_nav - before_nav) <= Decimal("1e-24"), "deposit changed unit NAV")
        entry = {"step": known, "request": request, "result": encode(result), "summary": after}
        new_state = deepcopy(self.state)
        new_state["history"].append(entry)
        new_state["cursor"] += 1
        new_state["summary"] = after
        try:
            self._write(new_state, fault=fault)
        except Exception:
            # Keep this in-memory instance unusable after uncertain persistence.
            self.state = {"invalid_after_write_failure": True}
            raise
        self.state = new_state
        return deepcopy(entry)


def compact(state):
    value = state["summary"] or {}
    return {
        "pid": os.getpid(),
        "cursor": state["cursor"],
        "cash": value.get("cash"),
        "assets": value.get("assets"),
        "fees": value.get("fees"),
        "state_sha256": None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot", required=True, choices=("continuous", "split"))
    parser.add_argument("--stage", required=True, choices=("all", "week1", "week2", "inspect"))
    parser.add_argument("--version", required=True, choices=("v2",))
    parser.add_argument("--directory", required=True, type=Path)
    args = parser.parse_args()
    contract, manifest, fixture, module = load_frozen()
    output = Path(contract["output_plan"]["output"])
    require(
        args.directory == output / args.version / args.slot and args.directory.is_dir(),
        "state outside fixed output",
    )
    require(
        args.directory.stat().st_dev == contract["output_plan"]["external_device"],
        "state device drift",
    )
    engine = Engine(
        args.directory, fixture, manifest, module, strict_fixture_sha=contract["fixture_sha256"]
    )
    targets = {"all": 10, "week1": 7, "week2": 10, "inspect": engine.state["cursor"]}
    require(
        args.stage != "week2" or engine.state["cursor"] == 7,
        "second week requires saved complete first week",
    )
    while engine.state["cursor"] < targets[args.stage]:
        engine.submit(engine.next_request())
    receipt = compact(engine.state)
    receipt["state_sha256"] = sha(engine.state_path)
    print(canonical(receipt))


if __name__ == "__main__":
    main()
