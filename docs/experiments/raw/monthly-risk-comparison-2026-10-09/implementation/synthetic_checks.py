"""Independent hand expectations on ARTIFICIAL data only. No real-input IO.

Engineering checks are B's preparation evidence, never C's acceptance.
"""
from __future__ import annotations

import json
import math
import traceback
import copy
import uuid
from datetime import date, timedelta, datetime
from decimal import Decimal as D
from pathlib import Path
from zoneinfo import ZoneInfo

from monthly_account import (adjustment, dates, monthly_targets, simulate_monthly,
                             sample_stdev, metrics, opportunity_description)
from execution_guard import (TASK, PATH_IDS, B_OWNER, C_TASK, C_OWNER, validate_release,
                             claim_batch, claim_path, actual_attempts)


def must_fail(fn, phrase):
    try:
        fn()
    except ValueError as exc:
        assert phrase in str(exc), (phrase, str(exc))
        return str(exc)
    raise AssertionError("invalid input was accepted")


def artificial_accounts(flat_a=False, flat_b=False):
    natural = dates("2025-08-01", "2026-06-30")
    trading = {day for day in natural if date.fromisoformat(day).weekday() < 5}
    wealth = {"A_ALL": D(100), "A_SMA": D(100), "B0": D(100)}
    output = {key: [] for key in wealth}
    index = 0
    for day in natural:
        sign = D(1) if index % 2 == 0 else D(-1)
        if day in trading:
            index += 1
        for key in output:
            rate = D(0) if day not in trading else sign*{
                "A_ALL": D(0) if flat_a else D("0.002"),
                "A_SMA": D(0) if flat_a else D("0.001"),
                "B0": D(0) if flat_b else D("0.004")}[key]
            wealth[key] *= 1+rate
            output[key].append({"date": day, "wealth": str(wealth[key]),
                                "is_trading_day": day in trading})
    return output, trading


def target(month, weight):
    first = date.fromisoformat(month+"-01")
    return {"month": month, "cutoff": (first-timedelta(days=1)).isoformat(), "weight": str(weight)}


def quote(day, op="10", close="10", **other):
    return {"date": day, "open": op, "close": close, **other}


def sim(targets, quotes, **kwargs):
    return simulate_monthly(cash=D(10000), fee=D("0.001"), targets=targets,
                            quotes=quotes, trading_days={r["date"] for r in quotes},
                            restrictions=kwargs.pop("restrictions", {}),
                            actions=kwargs.pop("actions", []),
                            start=kwargs.pop("start", "2026-01-01"),
                            end=kwargs.pop("end", "2026-01-31"), **kwargs)


def sixty_three_and_prefix():
    a, trading = artificial_accounts()
    schedule = monthly_targets(a, trading)
    assert list(schedule) == ["A_ALL", "A_SMA"]
    for name, ratio in (("A_ALL", .5), ("A_SMA", .25)):
        assert len(schedule[name]) == 6
        for row in schedule[name]:
            assert row["observations"] == 63
            assert len(row["window_dates"]) == 63
            assert abs(float(row["weight"])-ratio) < 1e-12
            assert all(day <= row["cutoff"] < row["active_from"] for day in row["window_dates"])
    prefix = {key: [r for r in rows if r["date"] <= "2025-12-31"] for key, rows in a.items()}
    alone = monthly_targets(prefix, {d for d in trading if d <= "2025-12-31"}, end="2026-01-31")
    assert alone["A_ALL"][0] == schedule["A_ALL"][0]
    assert alone["A_SMA"][0] == schedule["A_SMA"][0]
    # Future wealth can even be unreadable; January calculation never reads it.
    future = {key: [{**r, "wealth": "unreadable"} if r["date"] >= "2026-01-01" else dict(r)
                    for r in rows] for key, rows in a.items()}
    jan = monthly_targets(future, trading, end="2026-01-31")
    assert jan == alone
    # An extreme return strictly before the 63-day denominator cannot change it.
    earliest = schedule["A_ALL"][0]["returns_a"][0]["prior_natural_date"]
    past = {key: [{**r, "wealth": "99999999"} if r["date"] < earliest else dict(r)
                  for r in rows] for key, rows in a.items()}
    assert monthly_targets(past, trading, end="2026-01-31") == alone
    return {"first_cutoff": schedule["A_ALL"][0]["cutoff"],
            "first_window": schedule["A_ALL"][0]["window_dates"], "expected_weights": [.5, .25]}


def natural_denominator_and_missing():
    a, trading = artificial_accounts()
    schedule = monthly_targets(a, trading, end="2026-01-31")
    monday = next(d for d in schedule["A_ALL"][0]["window_dates"]
                  if date.fromisoformat(d).weekday() == 0)
    sunday = (date.fromisoformat(monday)-timedelta(days=1)).isoformat()
    changed = {key: [dict(r) for r in rows] for key, rows in a.items()}
    for row in changed["A_ALL"]:
        if row["date"] == sunday:
            row["wealth"] = str(D(row["wealth"])*D("1.1"))
    found = next(r for r in monthly_targets(changed, trading, end="2026-01-31")["A_ALL"][0]["returns_a"]
                 if r["date"] == monday)
    source = {r["date"]: r for r in changed["A_ALL"]}
    assert D(found["return"]) == D(source[monday]["wealth"])/D(source[sunday]["wealth"])-1
    missing = {key: [r for r in rows if not (key == "A_ALL" and r["date"] == sunday)]
               for key, rows in a.items()}
    must_fail(lambda: monthly_targets(missing, trading, end="2026-01-31"), "prior natural day")
    must_fail(lambda: monthly_targets(a, sorted(trading)[-40:], end="2026-01-31"), "fewer than 63")
    return {"monday": monday, "actual_denominator_date": sunday,
            "expected_return": found["return"], "missing_denominator_rejected": True}


def zero_and_cap():
    a, trading = artificial_accounts(flat_a=True)
    assert all(D(r["weight"]) == 0 for r in monthly_targets(a, trading)["A_ALL"])
    a, trading = artificial_accounts(flat_b=True)
    must_fail(lambda: monthly_targets(a, trading), "zero B0")
    a, trading = artificial_accounts()
    a["A_ALL"], a["B0"] = a["B0"], a["A_ALL"]
    assert all(D(r["weight"]) == 1 for r in monthly_targets(a, trading)["A_ALL"])
    assert abs(sample_stdev([D(1), D(2), D(3)])-1) < 1e-15
    return {"A_zero": 0, "cap": 1, "sample_ddof_1_hand_result": 1}


def hand_adjustments():
    buy = adjustment(10000, 0, 0, 10, ".5", ".001")
    assert D(buy["target_units"]) == 500
    assert D(buy["units_delta"]) == 500
    assert D(buy["cash_after"]) == 4995  # 5 fee; target before fees.
    claim = adjustment(100, 5000, 0, 10, 1, ".001")
    assert D(claim["opening_wealth"]) == 5100 and D(claim["target_units"]) == 500
    assert D(claim["units_delta"]) == 0 and D(claim["cash_after"]) == 100
    sell = adjustment(0, 0, 1000, 10, ".5", ".001")
    assert D(sell["units_delta"]) == -500 and D(sell["cash_after"]) == 4995
    zero = adjustment(0, 0, 1000, 10, 0, ".002")
    assert D(zero["units_delta"]) == -1000 and D(zero["cash_after"]) == 9980
    full = adjustment(10000, 0, 0, 10, 1, ".002")
    assert D(full["target_units"]) == 1000 and D(full["units_delta"]) == 900
    assert D(full["cash_after"]) == 982
    must_fail(lambda: adjustment(0, 0, 1, 10, ".5", ".001"), "non-lot")
    return {"buy_500_cash_after": "4995", "sell_500_cash_after": "4995",
            "receivable_5000_cash_100_bought": 0, "full_target_1000_affordable_900_cash": "982"}


def delayed_and_one_open():
    quotes = [quote("2026-01-02", tradable="False"), quote("2026-01-05", op=None),
              quote("2026-01-06"), quote("2026-01-07", "1", "1")]
    result = sim([target("2026-01", ".5")], quotes)
    assert [r["date"] for r in result["fills"]] == ["2026-01-06"]
    assert [r["reason"] for r in result["rejections"]] == ["explicit_restriction", "missing_open"]
    assert D(result["daily"][-1]["units"]) == 500
    assert result["orders"][0]["executed_at"] == "2026-01-06 open"
    no_lot = simulate_monthly(cash=1000, fee=".002", targets=[target("2026-01", 1)],
                             quotes=[quote("2026-01-02"), quote("2026-01-05", ".1", ".1")],
                             trading_days={"2026-01-02", "2026-01-05"}, restrictions={}, actions=[],
                             start="2026-01-01", end="2026-01-31")
    assert no_lot["fills"] == [] and D(no_lot["daily"][-1]["units"]) == 0
    assert no_lot["orders"][0]["status"] == "no_executable_lot_or_target_met"
    return {"allowed_open": "2026-01-06", "fills": 1, "no_lot_not_retried": True}


def cross_month_supersession_and_sell():
    quotes = [quote("2026-01-02"), quote("2026-01-30"), quote("2026-02-02")]
    result = sim([target("2026-01", ".8"), target("2026-02", ".2")], quotes,
                 end="2026-02-28", restrictions={"2026-01-02": "halt", "2026-01-30": "blocked"})
    assert result["orders"][0]["status"] == "superseded"
    assert result["orders"][0]["superseded_at"] == "2026-02-01"
    assert len(result["fills"]) == 1 and D(result["fills"][0]["units_delta"]) == 200
    second = sim([target("2026-01", ".8"), target("2026-02", ".2")], quotes, end="2026-02-28")
    assert [D(f["units_delta"]) for f in second["fills"]] == [800, -700]
    # Fee shrinks February wealth: 9992*.2/10=199.84 shares -> 100 whole-lot target.
    assert D(second["orders"][1]["adjustment"]["opening_wealth"]) == 9992
    assert D(second["daily"][-1]["cash"]) == 8985
    return {"expired_target": ".8", "replacement_target": ".2", "replacement_buy": 200,
            "executed_case_feb_sell": 700, "ending_cash": "8985"}


def dividends_and_pay_phase():
    actions = [{"type": "dividend", "event_id": "ARTIFICIAL", "record_date": "2026-01-30",
                "ex_date": "2026-02-02", "pay_date": "2026-02-02",
                "cash_per_unit": "5", "unit_basis": "old"}]
    quotes = [quote("2026-01-02"), quote("2026-01-30"), quote("2026-02-02", "5", "5"),
              quote("2026-02-03", "5", "5")]
    result = simulate_monthly(cash=10000, fee=0, targets=[target("2026-01", 1), target("2026-02", 1)],
                              quotes=quotes, trading_days={r["date"] for r in quotes},
                              restrictions={}, actions=actions, start="2026-01-01", end="2026-02-28")
    assert len(result["fills"]) == 1 and D(result["fills"][0]["units_delta"]) == 1000
    feb = result["orders"][1]["adjustment"]
    assert D(feb["opening_wealth"]) == 10000 and D(feb["receivable_before"]) == 5000
    assert D(feb["target_units"]) == 2000 and D(feb["cash_before"]) == 0
    assert D(feb["units_delta"]) == 0  # today's payment is only spendable after close.
    assert D(result["daily"][-1]["cash"]) == 5000
    assert D(result["daily"][-1]["units"]) == 1000
    assert D(result["daily"][-1]["wealth"]) == 10000
    for row in result["daily"]:
        assert all(D(row["reconciliation"][k]) == 0 for k in (
            "cash_residual_cny", "receivable_residual_cny", "unit_residual", "wealth_residual_cny"))
    bad = [{**actions[0], "pay_date": "2026-03-02"}]
    must_fail(lambda: sim([target("2026-01", 1), target("2026-02", 1)], quotes,
                          end="2026-02-28", actions=bad), "cross-boundary")
    return {"ex_and_pay_same_day_open_cash": 0, "receivable_in_wealth": 5000,
            "not_reinvested_next_day": True, "final_wealth": "10000", "all_bridges": "0"}


def strict_invalid_cases():
    must_fail(lambda: sim([target("2026-01", ".5")], [quote("2026-01-02")],
                          restrictions={"2026-01-02": "limit_up"}), "unknown restriction")
    must_fail(lambda: sim([{**target("2026-01", ".5"), "cutoff": "2026-01-02"}],
                          [quote("2026-01-02")]), "future/same-month")
    must_fail(lambda: sim([target("2026-01", ".5")], [quote("2026-01-02", "NaN")]), "nonfinite")
    must_fail(lambda: sim([target("2026-01", ".5")], [quote("2026-01-02", close=None)]), "no valuation")
    must_fail(lambda: sim([target("2026-01", ".5")], [quote("2026-01-02"), quote("2026-01-02")]), "duplicate")
    return {"unknown_restriction": "rejected", "future_target": "rejected", "nan": "rejected",
            "held_without_mark": "rejected", "duplicate": "rejected"}


def metrics_and_opportunity():
    ledger = [{"date": "2026-01-01", "wealth": "90", "invested_pct": "100", "is_trading_day": True},
              {"date": "2026-01-02", "wealth": "110", "invested_pct": "100", "is_trading_day": True},
              {"date": "2026-01-03", "wealth": "99", "invested_pct": "100", "is_trading_day": False}]
    m = metrics(ledger, D(100), {"2026-01-01", "2026-01-02"}, "2026-01-01", "2026-01-03")
    assert D(m["max_drawdown"]) == D("-.1") and m["longest_underwater_calendar_days"] == 2
    assert m["unrecovered_at_end"] is True
    expected = abs(-.1-2/9)/math.sqrt(2)
    assert abs(m["trading_day_volatility"]-expected) < 1e-15
    flat = [{**r, "wealth": "100"} for r in ledger]
    desc = opportunity_description(flat, 100, ledger, 100, "2026-01-01", "2026-01-03")
    assert abs(float(desc["b0_up_days_gap_cny"])-100*2/9) < 1e-12
    assert D(desc["b0_down_days_avoided_cny"]) == 20
    assert desc["additional_simulated_paths"] == 0
    return {"max_drawdown": "-.1", "expected_sample_sigma": expected,
            "b0_up_gap": desc["b0_up_days_gap_cny"], "no_additional_account": True}


def release_and_once_protection():
    # These artificial documents are passed ONLY to pure validation functions.
    # They are never written to the real authorization.json or passed to runner.
    contract = {"task_id": TASK, "owner_session": B_OWNER, "status": "frozen_for_C_review",
                "scope": {"symbol": "510300.SS", "start": "2026-01-01", "end": "2026-06-30",
                          "reference_accounts": ["A_ALL", "A_SMA"],
                          "fees": {"base": "0.001", "stress": "0.002"}, "path_ids": PATH_IDS,
                          "rolling_trading_days": 63, "stdev_ddof": 1,
                          "risk_tolerance": ["0.90", "1.10"], "history_status": "already_observed_exploration"},
                "budget": {"proposed_paths": 4, "original_A_replays": 0, "new_signals_or_labels": 0,
                           "downloads": 0, "predictive_fits": 0, "parameter_scans": 0},
                "inputs": {"sha256": "ARTIFICIAL_INPUT_HASH"},
                "synthetic_evidence": {"sha256": "ARTIFICIAL_SYNTHETIC_HASH"}}
    auth = {"task_id": TASK, "status": "approved", "authorized_path_ids": PATH_IDS,
            "contract_sha256": "ARTIFICIAL_CONTRACT_HASH", "user_quote": "ARTIFICIAL_NOT_AUTHORIZATION",
            "source_thread": "ARTIFICIAL", "authorized_at": "ARTIFICIAL"}
    code = {"monthly_account.py": "ARTIFICIAL_CODE_HASH"}
    review = {"decision": "accepted", "task_id": C_TASK, "reviewer_session": C_OWNER,
              "contract_sha256": "ARTIFICIAL_CONTRACT_HASH", "input_manifest_sha256": "ARTIFICIAL_INPUT_HASH",
              "synthetic_evidence_sha256": "ARTIFICIAL_SYNTHETIC_HASH", "code_sha256": code}
    def check(c=contract, a=auth, r=review, hashes=code, attempted=(), started=False):
        return validate_release(c, "ARTIFICIAL_CONTRACT_HASH", a, r, hashes,
                                "ARTIFICIAL_INPUT_HASH", attempted, started)
    release = {**check(), "dataset": "ARTIFICIAL_ONLY_NOT_RUN_PERMISSION"}
    must_fail(lambda: check(a={**auth, "status": "not_granted"}), "authorization missing")
    must_fail(lambda: check(a={**auth, "authorized_path_ids": PATH_IDS[:2]}), "exact four")
    must_fail(lambda: check(r={**review, "decision": "method_prepared"}), "C code acceptance")
    must_fail(lambda: check(r={**review, "reviewer_session": B_OWNER}), "C code acceptance")
    must_fail(lambda: check(hashes={"monthly_account.py": "DRIFT"}), "code binding")
    wrong = copy.deepcopy(contract)
    wrong["scope"]["rolling_trading_days"] = 20
    must_fail(lambda: check(c=wrong), "scope/parameters changed")
    must_fail(lambda: check(attempted=[PATH_IDS[0]]), "already consumed")
    must_fail(lambda: check(started=True), "already consumed")
    folder = Path(__file__).parent/"synthetic-attempts"/("ARTIFICIAL-"+uuid.uuid4().hex)
    folder.mkdir(parents=True)
    claim_batch(folder, release, "ARTIFICIAL")
    claim_path(folder, PATH_IDS[0], release, "ARTIFICIAL")
    ids, started = actual_attempts(folder)
    assert ids == PATH_IDS[:1] and started
    for fn in (lambda: claim_batch(folder, release, "ARTIFICIAL"),
               lambda: claim_path(folder, PATH_IDS[0], release, "ARTIFICIAL")):
        try:
            fn()
        except FileExistsError:
            pass
        else:
            raise AssertionError("duplicate atomic claim was accepted")
    return {"missing_permission_C_and_drift_rejected": True, "old_two_path_permission_rejected": True,
            "repeat_batch_and_path_claims_rejected": True,
            "artificial_claims_path": str(folder), "historical_paths": 0}


def main():
    tests = [sixty_three_and_prefix, natural_denominator_and_missing, zero_and_cap,
             hand_adjustments, delayed_and_one_open, cross_month_supersession_and_sell,
             dividends_and_pay_phase, strict_invalid_cases, metrics_and_opportunity,
             release_and_once_protection]
    report = {"schema": "monthly-risk-synthetic/1", "dataset": "ARTIFICIAL_ONLY",
              "acceptance_by_C": False, "historical_paths_attempted": 0,
              "generated_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(), "checks": []}
    for test in tests:
        try:
            details = test()
            report["checks"].append({"name": test.__name__, "status": "passed", "evidence": details})
        except Exception:
            report["checks"].append({"name": test.__name__, "status": "failed", "failure": traceback.format_exc()})
    report["engineering_checks_passed"] = all(r["status"] == "passed" for r in report["checks"])
    stamp = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%dT%H%M%S%f")
    output = Path(__file__).parent/("synthetic-evidence-"+stamp+".json")
    with output.open("x") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"evidence": str(output), "passed": sum(r["status"] == "passed" for r in report["checks"]),
                      "failed": [r["name"] for r in report["checks"] if r["status"] == "failed"],
                      "C_acceptance": False, "historical_paths": 0}))
    return 0 if report["engineering_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
