"""Recompute P0/P5/P6 with this engine and compare all five sealed tables."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import gzip
import json

import pandas as pd

HERE = Path(__file__).resolve().parent
EIGHTH = HERE.parent.parent / "research-eighth-2026-09-08"


def read(path):
    return json.loads(path.read_text())


settings = read(EIGHTH / "product-qualification/execution-parameters.json")
prices = {}
for symbol in settings["symbols"]:
    rows = pd.read_csv(Path(settings["prices_directory"]) / f"{symbol}-nominal.csv").to_dict("records")
    prices[symbol] = {
        row["date"]: {key: row[key] for key in ("open", "high", "low", "close", "volume")}
        for row in rows
    }

actions = []
for source in read(Path(settings["actions_file"])):
    action = dict(source, ex_date=source["effective_date"])
    if source["type"] == "cash_dividend":
        action["cash_per_share"] = float(source["cash"])
    else:
        action["ratio"] = float(source["ratio"])
    actions.append(action)

with gzip.open(EIGHTH / "candidate-study/candidates.json.gz", "rt") as stream:
    candidates = json.load(stream)
with gzip.open(EIGHTH / "candidate-study/exit-observations.json.gz", "rt") as stream:
    observations = json.load(stream)

spec = spec_from_file_location("twelfth_cash_engine", HERE / "engine.py")
engine = module_from_spec(spec)
spec.loader.exec_module(engine)

checks = []
for config_id in ("P0", "P5", "P6"):
    selected = [row for row in candidates if row["config_id"] == config_id]
    actual = engine.simulate(
        prices, actions, selected, observations,
        start="2015-01-01", end="2026-06-30", weekly_per_symbol=250,
        fee=0.001, config_id=config_id, limits=settings["limits"],
        limit_changes=settings["limit_changes"], blocked_dates=settings["blocked_dates"],
    )
    for table in ("daily", "trades", "orders", "events", "roundtrips"):
        if table in ("daily", "trades"):
            observed = pd.DataFrame(actual[table]).to_csv(index=False)
            expected = (EIGHTH / "account-results" / config_id / f"{table}.csv").read_text()
        else:
            observed = actual[table]
            expected = read(EIGHTH / "account-results" / config_id / f"{table}.json")
        matched = observed == expected
        checks.append((config_id, table, matched))
        print(config_id, table, "exact" if matched else "DIFFERENT")

if not all(matched for _, _, matched in checks):
    raise SystemExit(1)
