"""Artificial fixed-order checks; tmp_path is routed to the frozen external disk."""

import json
from copy import deepcopy
from decimal import Decimal

import cross_week_fixed_orders as subject
import pytest


@pytest.fixture
def frozen():
    return subject.load_frozen()


def engine(tmp_path, frozen, fixture=None):
    _, manifest, original, module = frozen
    folder = tmp_path / "engine"
    folder.mkdir()
    return subject.Engine(folder, fixture or original, manifest, module)


def run_to(instance, cursor):
    while instance.state["cursor"] < cursor:
        instance.submit(instance.next_request())
    return instance


def test_main_shared_cash_and_saved_nav(tmp_path, frozen):
    e = run_to(engine(tmp_path, frozen), 7)
    week1 = e.state["summary"]
    assert tuple(Decimal(week1[key]) for key in ("cash", "assets", "fees")) == (
        Decimal("200.10"),
        Decimal("600.10"),
        Decimal("10.40"),
    )
    assert week1["prior_complete"]["at"] == "2026-01-09T15:00:00+08:00"
    nav = week1["prior_complete"]["nav"]["$decimal"]
    assert Decimal(nav) == Decimal(week1["assets"]) / Decimal(week1["units"])
    old_units = Decimal(week1["units"])
    e = subject.Engine(e.directory, frozen[2], frozen[1], frozen[3])
    deposit = e.submit(e.next_request())
    after = deposit["summary"]
    deposit_sha = subject.sha(e.state_path)
    assert e.submit(deposit["request"]) == deposit
    assert subject.sha(e.state_path) == deposit_sha
    assert Decimal(after["cash"]) == Decimal("450.10")
    assert Decimal(after["units"]) - old_units == Decimal("250") / Decimal(nav)
    assert Decimal(after["assets"]) == Decimal("850.10")
    run_to(e, 10)
    final = e.state["summary"]
    assert (Decimal(final["cash"]), Decimal(final["assets"]), Decimal(final["fees"])) == (
        Decimal("39.70"),
        Decimal("839.70"),
        Decimal("20.80"),
    )
    assert {k: Decimal(v) for k, v in final["positions"].items()} == {"TEST_A": 200, "TEST_B": 200}
    assert Decimal(final["inflows"]) == 250
    assert Decimal(final["assets"]) + Decimal(final["fees"]) == Decimal("860.50")
    assert [x["result"]["status"] for x in e.state["history"]] == ["accepted"] * 10


def test_replay_duplicate_conflict_and_order(tmp_path, frozen):
    e = engine(tmp_path, frozen)
    first = e.next_request()
    receipt = e.submit(first)
    state_hash = subject.sha(e.state_path)
    assert e.submit(first) == receipt and subject.sha(e.state_path) == state_hash
    altered = {**first, "quantity": 200}
    with pytest.raises(ValueError, match="same identity changed request"):
        e.submit(altered)
    for index in (2, 7, 8, 9):
        with pytest.raises(ValueError, match="premature, missing, or skipped action"):
            e.submit(e.plan[index])
    assert subject.sha(e.state_path) == state_hash
    assert e.ledger.snapshot()["cash"] == Decimal("405.300")


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ("insufficient", "insufficient free cash"),
        ("overlimit", "opening above fixed limit"),
        ("not_permitted", "not permitted opening"),
        ("budget", "fixed order budget exceeded"),
    ],
)
def test_fixed_whole_order_terminal_refusal(tmp_path, frozen, change, expected):
    fixture = deepcopy(frozen[2])
    if change == "insufficient":
        fixture["initial_cash"] = "200.00"
    elif change == "overlimit":
        fixture["prices"]["TEST_A"] = "2.001"
    elif change == "not_permitted":
        fixture["fixed_orders"][0]["permitted"] = False
    elif change == "budget":
        fixture["fixed_orders"][0]["budget"] = "205.19"
    e = engine(tmp_path, frozen, fixture)
    before = e.ledger.snapshot()
    result = e.submit(e.next_request())
    assert result["result"]["status"] == "refused"
    assert expected in result["result"]["reason"]
    assert e.ledger.snapshot() == before
    assert e.state["cursor"] == 1
    assert e.state["history"][0]["request"]["quantity"] == 100
    assert subject.Engine(e.directory, fixture, frozen[1], frozen[3]).state == e.state


def test_lower_qualified_open_keeps_fixed_quantity_and_limit(tmp_path, frozen):
    fixture = deepcopy(frozen[2])
    fixture["prices"]["TEST_A"] = "1.999"
    e = engine(tmp_path, frozen, fixture)
    result = e.submit(e.next_request())
    assert result["result"]["status"] == "accepted"
    assert result["result"]["event"]["qty"] == 100
    assert result["result"]["event"]["price"] == "1.999"
    assert result["request"]["limit"] == "2.000"


@pytest.mark.parametrize(
    "field", ["quantity", "limit", "budget", "batch_id", "decision_at", "allowed_open", "asset"]
)
def test_fixed_request_drift_rejected_before_ledger(tmp_path, frozen, field):
    e = engine(tmp_path, frozen)
    request = e.next_request()
    request[field] = "drift" if field != "quantity" else 200
    before = subject.sha(e.state_path)
    with pytest.raises(ValueError, match="same identity changed request"):
        e.submit(request)
    assert subject.sha(e.state_path) == before and e.ledger.audit == []


def test_source_guard_before_import(monkeypatch):
    original = subject.sha
    monkeypatch.setattr(
        subject,
        "sha",
        lambda path: "bad" if str(path).endswith("dated_ledger.py") else original(path),
    )
    monkeypatch.setattr(
        subject.importlib.util,
        "spec_from_file_location",
        lambda *_: pytest.fail("old source imported"),
    )
    with pytest.raises(ValueError, match="frozen source SHA mismatch"):
        subject.load_frozen()


def test_source_drift_rejected_before_operation_and_reconstruction(tmp_path, frozen, monkeypatch):
    e = engine(tmp_path, frozen)
    state_hash = subject.sha(e.state_path)
    original = subject.sha
    monkeypatch.setattr(
        subject,
        "sha",
        lambda path: "changed" if str(path).endswith("dated_ledger.py") else original(path),
    )
    with pytest.raises(ValueError, match="frozen source SHA mismatch"):
        e.submit(e.next_request())
    assert original(e.state_path) == state_hash and e.ledger.audit == []
    with pytest.raises(ValueError, match="frozen source SHA mismatch"):
        subject.Engine(e.directory, frozen[2], frozen[1], frozen[3])


def test_wrapper_version_drift_rejected_before_operation_and_restore(tmp_path, frozen, monkeypatch):
    e = engine(tmp_path, frozen)
    state_hash = subject.sha(e.state_path)
    original = subject.sha
    monkeypatch.setattr(
        subject,
        "sha",
        lambda path: "changed" if str(path) == subject.__file__ else original(path),
    )
    with pytest.raises(ValueError, match="executor version checkpoint drift"):
        e.submit(e.next_request())
    assert original(e.state_path) == state_hash and e.ledger.audit == []
    with pytest.raises(ValueError, match="executor version checkpoint drift"):
        subject.Engine(e.directory, frozen[2], frozen[1], frozen[3])


def test_bad_foreign_and_reconstruction_state(tmp_path, frozen):
    e = run_to(engine(tmp_path, frozen), 2)
    original = json.loads(e.state_path.read_text())
    for key, changed, match in [
        ("schema", "foreign", "bad checkpoint schema"),
        ("cursor", 7, "bad or skipped cursor"),
        ("fixture_sha256", "foreign", "foreign or drifted fixture"),
        ("source_manifest", {}, "source version checkpoint drift"),
    ]:
        damaged = deepcopy(original)
        damaged[key] = changed
        e.state_path.write_text(json.dumps(damaged))
        with pytest.raises(ValueError, match=match):
            subject.Engine(e.directory, frozen[2], frozen[1], frozen[3])
    damaged = deepcopy(original)
    damaged["summary"]["cash"] = "999"
    e.state_path.write_text(json.dumps(damaged))
    with pytest.raises(ValueError, match="checkpoint final state mismatch"):
        subject.Engine(e.directory, frozen[2], frozen[1], frozen[3])
    damaged = deepcopy(original)
    damaged["history"][0]["summary"]["ledger_state"]["cash"] = {"$decimal": "999"}
    e.state_path.write_text(json.dumps(damaged))
    with pytest.raises(ValueError, match="checkpoint ledger reconstruction mismatch"):
        subject.Engine(e.directory, frozen[2], frozen[1], frozen[3])


@pytest.mark.parametrize("fault", ["pre_replace", "post_replace"])
def test_failure_boundary_recovered_on_restart(tmp_path, frozen, fault):
    e = engine(tmp_path, frozen)
    request = e.next_request()
    initial_sha = subject.sha(e.state_path)
    with pytest.raises(RuntimeError, match="injected"):
        e.submit(request, fault=fault)
    restarted = subject.Engine(e.directory, frozen[2], frozen[1], frozen[3])
    if fault == "pre_replace":
        assert subject.sha(e.state_path) == initial_sha
        assert restarted.state["cursor"] == 0
        assert list(e.directory.glob("state.next.*"))
    else:
        committed_sha = subject.sha(e.state_path)
        assert restarted.state["cursor"] == 1
        assert restarted.submit(request) == restarted.state["history"][0]
        assert subject.sha(e.state_path) == committed_sha
