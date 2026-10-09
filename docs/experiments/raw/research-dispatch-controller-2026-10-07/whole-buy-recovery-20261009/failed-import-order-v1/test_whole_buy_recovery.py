"""Only the eight bounded synthetic verification groups for this recovery shell."""
from copy import deepcopy
from pathlib import Path
import json
import os

import whole_buy_recovery as w


def _slot(base):
    return base + os.environ.get("RECOVERY_ATTEMPT_SUFFIX", "")


def _must_reject(call):
    try:
        call()
    except (ValueError, OSError):
        return
    raise AssertionError("expected rejection")


def _cash(result, expected):
    assert result["cash"] == expected, (result["cash"], expected)


def _state_bytes(recovery):
    return recovery.path.read_bytes()


def normal_path(plan):
    r = w.Recovery(plan, "normal", _slot("normal_path"))
    r.create()
    first = r.submit(r.request(0))
    assert first["receipt"]["status"] == "filled" and first["new_order_apply_count"] == 1
    _cash(r.inspect(), "205.30")
    second = r.submit(r.request(1))
    assert second["receipt"]["status"] == "filled" and second["new_order_apply_count"] == 1
    end = r.inspect()
    _cash(end, "0.10")
    assert end["fees"] == "10.40" and end["next_index"] == 2
    return {"cash": end["cash"], "fees": end["fees"], "state_sha256": end["state_sha256"]}


def refusal_path(plan):
    r = w.Recovery(plan, "first_rejected", _slot("refusal_path"))
    r.create()
    first = r.submit(r.request(0))
    assert first["receipt"]["status"] == "refused" and first["new_order_apply_count"] == 0
    _cash(r.inspect(), "410.50")
    second = r.submit(r.request(1))
    assert second["receipt"]["status"] == "filled" and second["new_order_apply_count"] == 1
    end = r.inspect()
    _cash(end, "205.30")
    return {"first_reason": first["receipt"]["reason"], "cash": end["cash"], "fees": end["fees"]}


def duplicate(plan):
    r = w.Recovery(plan, "normal", _slot("duplicate"))
    r.create()
    requests = [r.request(i) for i in range(2)]
    r.submit(requests[0]); r.submit(requests[1])
    before = _state_bytes(r)
    for q in requests:
        got = w.Recovery(plan, "normal", _slot("duplicate")).submit(q)
        assert got["replay_ignored"] is True and got["new_order_apply_count"] == 0
    assert _state_bytes(r) == before
    return {"state_bytes_unchanged": True, "cash": r.inspect()["cash"]}


def before_fault(plan):
    r = w.Recovery(plan, "normal", _slot("before_fault"))
    r.create(); q = r.request(0); before = _state_bytes(r)
    _must_reject(lambda: r.submit(q, fail_at="before_replace"))
    assert _state_bytes(r) == before
    assert list(r.path.parent.glob("state.tmp.*")), "fault snapshot missing"
    result = w.Recovery(plan, "normal", _slot("before_fault")).submit(q)
    assert result["new_order_apply_count"] == 1
    _cash(r.inspect(), "205.30")
    return {"old_bytes_unchanged": True, "recovered_cash": r.inspect()["cash"]}


def after_fault(plan):
    r = w.Recovery(plan, "normal", _slot("after_fault"))
    r.create(); q = r.request(0)
    _must_reject(lambda: r.submit(q, fail_at="after_replace"))
    before = _state_bytes(r)
    got = w.Recovery(plan, "normal", _slot("after_fault")).submit(q)
    assert got["replay_ignored"] and got["new_order_apply_count"] == 0
    assert _state_bytes(r) == before
    _cash(r.inspect(), "205.30")
    return {"committed_response_lost_detected": True, "cash": r.inspect()["cash"]}


def request_identity(plan):
    for profile, slot in (("normal", "request_identity"), ("first_rejected", "unsupported")):
        r = w.Recovery(plan, profile, _slot(slot))
        r.create(); q = r.request(0); r.submit(q); before = _state_bytes(r)
        for key, value in (("at", "2026-01-03T09:30:00+08:00"),
                           ("price", {"$decimal": "1"}), ("symbol", "renamed")):
            altered = deepcopy(q)
            altered["content"]["opening"][key] = value
            _must_reject(lambda altered=altered: r.submit(altered))
        altered = deepcopy(q)
        altered["content"]["order"]["quantity"] = {"$decimal": "50"}
        _must_reject(lambda: r.submit(altered))
        altered = deepcopy(q)
        altered["request_id"] = "different-id"
        _must_reject(lambda: r.submit(altered))
        assert _state_bytes(r) == before
    return {"filled_and_refused_replay_mutations_rejected": True}


def corruption(plan):
    r = w.Recovery(plan, "normal", _slot("corruption"))
    r.create(); r.submit(r.request(0))
    original = json.loads(r.path.read_text())
    changes = [
        ("truncated", None),
        ("cursor", lambda s: s.__setitem__("next_index", 2)),
        ("receipt", lambda s: s["history"][0]["receipt"].__setitem__("status", "refused")),
        ("ledger", lambda s: s["runtime"]["ledger_snapshot"].__setitem__("cash", {"$decimal": "410.50"})),
        ("contradiction", lambda s: s["runtime"].__setitem__("batch_stopped", True)),
    ]
    for name, mutate in changes:
        if mutate is None:
            payload = b'{"schema":"whole-buy-recovery/1"'
        else:
            bad = deepcopy(original); mutate(bad); bad = w._sealed(bad)
            payload = (w.canonical(bad) + "\n").encode()
        w._external_guard(plan, r.path)
        (r.path.parent / ("state.bad." + name + ".json")).write_bytes(payload)
        w._external_guard(plan, r.path)
        r.path.write_bytes(payload)
        _must_reject(r.inspect)
    w._external_guard(plan, r.path)
    r.path.write_text(w.canonical(original) + "\n")
    assert r.inspect()["next_index"] == 1
    prior_fixture = w.FIXTURE_SHA
    try:
        w.FIXTURE_SHA = "0" * 64
        _must_reject(r.inspect)
    finally:
        w.FIXTURE_SHA = prior_fixture
    prior_sources = dict(w.SOURCE_HASHES)
    try:
        w.SOURCE_HASHES["ledger"] = "0" * 64
        _must_reject(r.inspect)
    finally:
        w.SOURCE_HASHES.clear(); w.SOURCE_HASHES.update(prior_sources)
    return {"bad_state_versions_retained": len(changes), "source_and_fixture_drift_rejected": True}


def unsupported(plan):
    r = w.Recovery(plan, "normal", _slot("single"))
    r.create(); q = r.request(0); before = _state_bytes(r)
    for name, change in (
        ("P1", ("content", "plan_hash", "p1")),
        ("await_sale", ("content", "order", "side", "sell")),
        ("partial", ("content", "order", "quantity", {"$decimal": "50"})),
        ("cancel", ("content", "operation", "cancel")),
        ("new_decision", ("content", "decision_hash", "new")),
        ("unknown_action", ("content", "opening", "buy", None)),
    ):
        bad = deepcopy(q); target = bad
        for k in change[:-2]: target = target[k]
        target[change[-2]] = change[-1]
        _must_reject(lambda bad=bad: r.submit(bad))
    _must_reject(lambda: r.submit(r.request(1)))
    assert _state_bytes(r) == before
    return {"unsupported_variants_rejected_before_ledger": True}


GROUPS = (normal_path, refusal_path, duplicate, before_fault, after_fault,
          request_identity, corruption, unsupported)


def run_groups(plan):
    return {fn.__name__: fn(plan) for fn in GROUPS}
