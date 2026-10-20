import importlib.util
import json
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent


def load_runner():
    spec = importlib.util.spec_from_file_location("phase13_runner", HERE / "run_accounts.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_exit_rule_strict_and_missing_values():
    m = load_runner()
    assert m.structure_only({}, {}, 9) is None
    assert m.ema_cost_exit({}, {"ema20": 10, "cost20": 11}, 9) == "ema_cost_exit"
    assert m.ema_cost_exit({}, {"ema20": 9, "cost20": 11}, 9) is None
    assert m.ema_cost_exit({}, {"ema20": 10, "cost20": 9}, 9) is None
    import pytest
    with pytest.raises(ValueError, match="Missing exit observation"):
        m.ema_cost_exit({}, {"ema20": None, "cost20": 11}, 9)


def test_engine_structure_priority_and_next_open():
    m = load_runner()
    engine = m.module("phase13_test_engine", m.ENGINE)
    prices = {"x": {
        "2014-12-31": {"open": 10, "high": 10, "low": 10, "close": 10},
        "2015-01-05": {"open": 10, "high": 10, "low": 10, "close": 10},
        "2015-01-06": {"open": 10, "high": 10, "low": 8, "close": 8},
        "2015-01-07": {"open": 7, "high": 8, "low": 7, "close": 7.5},
    }}
    candidate = {"config_id": "X", "candidate_id": "c", "symbol": "x",
                 "signal_date": "2015-01-05", "signal_accepted": True,
                 "signal_reject_reason": None, "signal_ref": 10, "stop": 9,
                 "target": 14, "variant": "A"}
    obs = {"x": {"2015-01-06": {"ema20": 9, "cost20": 9}}}
    result = engine.simulate(prices, [], [candidate], obs, start="2015-01-05",
        end="2015-01-07", weekly_per_symbol=10000, fee=.001, config_id="X",
        limits={"x": .5}, exit_rule=m.ema_cost_exit, explicit_config_set={"X"})
    sells = [t for t in result["trades"] if t["side"] == "sell"]
    assert sells[0]["date"] == "2015-01-07"
    assert sells[0]["price"] == 7
    assert sells[0]["reason"] == "structure_stop"


def test_engine_buy_day_close_can_signal_but_not_sell_same_day():
    m = load_runner()
    engine = m.module("phase13_test_engine_buyday", m.ENGINE)
    prices = {"x": {
        "2014-12-31": {"open": 10, "high": 10, "low": 10, "close": 10},
        "2015-01-05": {"open": 10, "high": 10, "low": 10, "close": 10},
        "2015-01-06": {"open": 10, "high": 10, "low": 9, "close": 9},
        "2015-01-07": {"open": 8, "high": 9, "low": 8, "close": 8.5},
    }}
    candidate = {"config_id": "X", "candidate_id": "c", "symbol": "x",
                 "signal_date": "2015-01-05", "signal_accepted": True,
                 "signal_reject_reason": None, "signal_ref": 10, "stop": 9,
                 "target": 14, "variant": "A"}
    obs = {"x": {"2015-01-06": {"ema20": 10, "cost20": 10}}}
    result = engine.simulate(prices, [], [candidate], obs, start="2015-01-05",
        end="2015-01-07", weekly_per_symbol=10000, fee=.001, config_id="X",
        limits={"x": .5}, exit_rule=m.ema_cost_exit, explicit_config_set={"X"})
    assert [(t["side"], t["date"]) for t in result["trades"]] == [("buy", "2015-01-06"), ("sell", "2015-01-07")]


def fixed_fixture(m, tmp_path, entry="2015-01-05", stop=1):
    cfg=tmp_path/"A20E";cfg.mkdir()
    base={"config_id":"A20E","position_id":"p","candidate_id":"c","symbol":"x","entry_date":entry,"initial_stop":stop,"net_pnl":0}
    (cfg/"roundtrips.json").write_text(json.dumps([base]))
    pd.DataFrame([{"date":entry,"position_id":"p","side":"buy","shares":100,"price":10,"notional":1000,"fee":1}]).to_csv(cfg/"trades.csv",index=False)
    m.BASE=tmp_path
    settings={"blocked_dates":{"x":[]},"limits":{"x":.5},"limit_changes":{"x":[]}}
    return base,settings


def test_fixed_path_split_on_no_quote_day(tmp_path):
    m=load_runner();base,settings=fixed_fixture(m,tmp_path)
    prices={"x":{"2015-01-04":{"open":10,"close":10},"2015-01-05":{"open":10,"close":10},"2015-01-07":{"open":5,"close":5}}}
    actions=[{"symbol":"x","event_id":"split","type":"split","ex_date":"2015-01-06","ratio":2}]
    r=m.fixed_position_path(base,prices,actions,{"x":{}},settings,"S")
    assert r["final_shares"]==200 and r["final_stop"]==.5


def test_fixed_path_record_then_sell_still_receives_payment(tmp_path):
    m=load_runner();base,settings=fixed_fixture(m,tmp_path,stop=9)
    prices={"x":{d:{"open":p,"close":p} for d,p in [("2015-01-04",10),("2015-01-05",10),("2015-01-06",10),("2015-01-07",8),("2015-01-08",8)]}}
    actions=[{"symbol":"x","event_id":"div","type":"cash_dividend","record_date":"2015-01-06","ex_date":"2015-01-07","pay_date":"2015-01-08","cash_per_share":1}]
    r=m.fixed_position_path(base,prices,actions,{"x":{}},settings,"S")
    assert r["exit_date"]=="2015-01-08" and r["dividends"]==100
    assert any(e["kind"]=="dividend_paid" and e["amount"]==100 for e in r["events"])


def test_fixed_path_new_buy_on_ex_date_has_no_old_entitlement(tmp_path):
    m=load_runner();base,settings=fixed_fixture(m,tmp_path,entry="2015-01-07")
    prices={"x":{d:{"open":p,"close":p} for d,p in [("2015-01-06",10),("2015-01-07",9),("2015-01-08",9)]}}
    actions=[{"symbol":"x","event_id":"div","type":"cash_dividend","record_date":"2015-01-06","ex_date":"2015-01-07","pay_date":"2015-01-08","cash_per_share":1}]
    r=m.fixed_position_path(base,prices,actions,{"x":{}},settings,"S")
    assert r["dividends"]==0
