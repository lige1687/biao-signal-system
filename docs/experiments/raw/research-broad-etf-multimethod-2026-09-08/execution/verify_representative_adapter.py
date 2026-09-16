"""Rebuild three old representative paths in memory and compare every stored row."""
import csv
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
from account_adapter import FIRST12, load_frozen_inputs


def csv_rows(path):
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def same_value(actual, expected):
    if actual is None:
        return expected in (None, "")
    if isinstance(actual, (int, float)) and not isinstance(actual, bool):
        try:
            return math.isclose(float(actual), float(expected), rel_tol=0, abs_tol=1e-9)
        except (TypeError, ValueError):
            return False
    return str(actual) == str(expected)


def compare_rows(actual, expected, label):
    assert len(actual) == len(expected), (label, len(actual), len(expected))
    for index, (left, right) in enumerate(zip(actual, expected)):
        assert set(left) == set(right), (label, index, set(left)^set(right))
        for key in left:
            assert same_value(left[key], right[key]), (label, index, key, left[key], right[key])


def main():
    runner, config, settings, actions, bars = load_frozen_inputs()
    prepared = json.loads((FIRST12/"prepared-signals.json").read_text())
    cases = [
        ("sh510300", "breadth_three_tier", "0.001", prepared["weekly_breadth"]),
        ("sz159915", "simple_60_close_breakout", "0.001", prepared["breakout"]["sz159915"]),
        ("sz159915", "hold", "0.001", []),
    ]
    checked = []
    for symbol, method, fee, signals in cases:
        account_id=f"{symbol}-{method}-fee{fee}"
        rebuilt=runner.simulate(account_id,symbol,method,runner.D(fee),bars[symbol],actions,settings,signals,*config["research_window"])
        old=FIRST12/"account-results"/account_id
        compare_rows(rebuilt["daily"],csv_rows(old/"daily.csv"),account_id+":daily")
        compare_rows(rebuilt["trades"],csv_rows(old/"trades.csv"),account_id+":trades")
        for name in ("signals","rejected","summary"):
            expected=json.loads((old/f"{name}.json").read_text())
            if isinstance(rebuilt[name],list): compare_rows(rebuilt[name],expected,account_id+":"+name)
            else: compare_rows([rebuilt[name]],[expected],account_id+":"+name)
        checked.append({"account_id":account_id,"daily":len(rebuilt["daily"]),"trades":len(rebuilt["trades"])})
    print(json.dumps({"status":"exact_values_matched","representative_accounts":checked},ensure_ascii=False))


if __name__=="__main__":main()
