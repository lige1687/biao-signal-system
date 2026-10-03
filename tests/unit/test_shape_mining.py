"""Native component and causal-boundary tests; no financial fits."""
from datetime import date, timedelta
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from lei_signal.research.shape_mining import discover, apply_library


def fixture_series():
    # Deterministic synthetic sequence: several independently placed repetitions.
    rng = np.random.default_rng(420)
    shape = np.array([0, .1, .4, .2, -.1, -.4, -.2, .3, .5, .1,
                      -.3, -.5, -.2, .2, .7, .4, .1, -.2, .1, .6])
    logs = 4.0 + rng.normal(0, .01, 240)
    for start in [5, 60, 110, 170, 215]:
        logs[start:start+20] = 4.0 + .02*shape
    return {"asset":"synthetic", "dates":[(date(2020,1,1)+timedelta(days=i)).isoformat() for i in range(240)],
            "close":np.exp(logs).tolist()}


@pytest.fixture(scope="module")
def fixed():
    data=fixture_series()
    return data,discover(data,data["dates"][159])


def test_native_discovery_not_empty_and_only_training(fixed):
    data,bank=fixed
    assert 1 <= len(bank["candidates"]) <= 3
    all_starts=[]
    for candidate in bank["candidates"]:
        assert len(candidate["template"])==20
        assert max(candidate["template_dates"])<=bank["discovery_end"]
        starts=[o["start"] for o in candidate["occurrences"]]
        assert len(starts)>=2
        all_starts+=starts
    assert all(abs(a-b)>=20 for i,a in enumerate(all_starts) for b in all_starts[i+1:])


def test_future_tail_does_not_change_discovery(fixed):
    data,bank=fixed
    changed=copy.deepcopy(data)
    changed["close"][160:]=[1e200 if i%2 else 1e-200 for i in range(80)]
    assert discover(changed,bank["discovery_end"])==bank


def test_future_tail_does_not_change_past_application(fixed):
    data,bank=fixed
    result=apply_library(data,bank)
    changed=copy.deepcopy(data)
    changed["close"][210:]=[1e200]*30
    later=apply_library(changed,bank)
    assert result["rows"][:210]==later["rows"][:210]
    assert all(all(v is None for v in row["distances"].values()) for row in result["rows"][:160])


def test_native_distance_matches_independent_hand_formula(fixed):
    data,bank=fixed
    result=apply_library(data,bank)
    for end in [179,198,229]:
        x=np.log(data["close"][end-19:end+1]);z=(x-x.mean())/x.std()
        for candidate in bank["candidates"]:
            q=np.array(candidate["template"]);q=(q-q.mean())/q.std()
            expected=float(np.linalg.norm(z-q))
            actual=result["rows"][end]["distances"][candidate["candidate_id"]]
            assert actual==pytest.approx(expected,abs=1e-6)


def test_missing_is_not_compressed(fixed):
    data,bank=fixed
    changed=copy.deepcopy(data);changed["close"][180]=None
    rows=apply_library(changed,bank)["rows"]
    assert len(rows)==len(data["dates"])
    assert all(all(v is None for v in rows[i]["distances"].values()) for i in range(180,200))
    assert all(v is not None for v in rows[200]["distances"].values())


def test_price_scale_invariance(fixed):
    data,bank=fixed
    sliced={"asset":data["asset"],"dates":data["dates"][160:],"close":data["close"][160:]}
    scaled={**sliced,"close":[v*7 for v in sliced["close"]]}
    a,b=apply_library(sliced,bank),apply_library(scaled,bank)
    for ra,rb in zip(a["rows"],b["rows"]):
        for key,value in ra["distances"].items():
            if value is None:assert rb["distances"][key] is None
            else:assert rb["distances"][key]==pytest.approx(value,abs=1e-6)


def test_constant_windows_have_no_interpretable_distance(fixed):
    data,bank=fixed
    sliced={"asset":data["asset"],"dates":data["dates"][160:],"close":[100.]*80}
    assert all(all(v is None for v in r["distances"].values()) for r in apply_library(sliced,bank)["rows"])
    assert discover({"asset":"constant","dates":data["dates"][:60],"close":[100.]*60},data["dates"][59])["candidates"]==[]


@pytest.mark.parametrize("change",["negative","infinite","duplicate","label","bool"])
def test_bad_inputs_rejected(fixed,change):
    data,bank=fixed;bad=copy.deepcopy(data)
    if change=="negative":bad["close"][1]=-1
    elif change=="infinite":bad["close"][1]=float("inf")
    elif change=="bool":bad["close"][1]=True
    elif change=="duplicate":bad["dates"][1]=bad["dates"][0]
    else:bad["future_return"]=[0]*240
    with pytest.raises(ValueError):apply_library(bad,bank)


def test_wrong_asset_revision_and_corrupted_library(fixed):
    data,bank=fixed
    with pytest.raises(ValueError):apply_library({**data,"asset":"another"},bank)
    revised=copy.deepcopy(data);revised["close"][0]*=2
    with pytest.raises(ValueError):apply_library(revised,bank)
    altered=copy.deepcopy(bank);altered["candidates"][0]["template"][0]+=.1
    with pytest.raises(ValueError):apply_library(data,altered)


def test_cli_apply_recovers_from_json_and_refuses_overwrite(fixed,tmp_path):
    data,bank=fixed
    (tmp_path/"input.json").write_text(json.dumps(data));(tmp_path/"library.json").write_text(json.dumps(bank))
    cmd=[sys.executable,"-m","lei_signal.research.shape_mining","apply","--input",str(tmp_path/"input.json"),
         "--library",str(tmp_path/"library.json"),"--output",str(tmp_path/"fresh")]
    success=subprocess.run(cmd,capture_output=True,text=True)
    assert success.returncode==0,success.stderr
    restored=json.loads((tmp_path/"fresh"/"observations.json").read_text())
    assert restored==apply_library(data,bank)
    before=hashlib.sha256((tmp_path/"fresh"/"observations.json").read_bytes()).hexdigest()
    assert subprocess.run(cmd,capture_output=True,text=True).returncode!=0
    assert hashlib.sha256((tmp_path/"fresh"/"observations.json").read_bytes()).hexdigest()==before


def test_noise_without_native_matches_returns_empty_library():
    data=fixture_series()
    data["close"]=np.exp(4+np.random.default_rng(421).normal(0,.01,240)).tolist()
    bank=discover(data,data["dates"][159])
    assert bank["candidates"]==[]
    assert bank["coverage"]["native_groups"]==0
