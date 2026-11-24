import copy
import pytest
from lei_signal.research.etf_hourly_recovery import qualify_sina_hours
from lei_signal.research.etf_hourly_recovery import evaluate_etf_observations


def fixture():
    day = "2025-06-02"
    bar = dict(open="10", high="11", low="9", close="10.1", volume="1")
    hours = [{**bar, "day": f"{day} {s}:00"} for s in ("10:30", "11:30", "14:00", "15:00")]
    daily = [{**bar, "day": day, "close": "10.2", "volume": "5"}]
    saved = [{"date": day, "qualified": True, **{"adjusted_"+k: float(daily[0][k])*2 for k in ("open", "high", "low", "close")}}]
    factors = [{"dividOperateDate": "2025-01-01", "backAdjustFactor": "2"}]
    return hours, daily, factors, saved


def test_official_close_can_differ_volume_separate():
    r = qualify_sina_hours(*fixture())
    assert r["daily_audit"][0]["qualified"]
    assert r["daily_audit"][0]["volume_mismatch"]
    assert r["hours"][-1]["adjusted_close"] == 20.2


@pytest.mark.parametrize("change,reason", [
    ("missing", "missing_or_misordered_hour_slots"),
    ("open", "hour_vs_daily_OHL_mismatch"),
    ("geometry", "invalid_or_missing_source_price"),
    ("adjusted", "same_date_adjusted_daily_mismatch"),
    ("future_factor", "factor_effective_date_unknown"),
    ("range", "official_close_outside_last_hour_range"),
])
def test_rejects_without_repair(change, reason):
    h,d,f,s = fixture()
    if change == "missing": h.pop()
    if change == "open": h[0]["open"] = "10.001"
    if change == "geometry": h[0]["high"] = "8"
    if change == "adjusted": s[0]["adjusted_close"] += .01
    if change == "future_factor": f[0]["dividOperateDate"] = "2025-06-03"
    if change == "range": h[-1].update(high="10.15", close="10.1")
    before = copy.deepcopy((h,d,f,s))
    r = qualify_sina_hours(h,d,f,s)
    assert r["daily_audit"][0]["reason"] == reason
    assert all(x["adjusted_close"] is None for x in r["hours"])
    assert before == (h,d,f,s)


def test_missing_day_explicit_and_future_factor_unused():
    h,d,f,s = fixture()
    f.append({"dividOperateDate": "2025-06-03", "backAdjustFactor": "999"})
    s.append({"date": "2025-06-03", "qualified": True})
    r = qualify_sina_hours(h,d,f,s)
    assert r["hours"][0]["adjusted_close"] == 20.2
    assert r["qualification"]["longest_qualified_days"] == 1
    assert len(r["hours"]) == 8
    assert not r["hours"][-1]["hour_qualified"]


def test_duplicate_source_rejected():
    h,d,f,s = fixture()
    h.append(h[-1])
    with pytest.raises(ValueError, match="duplicate"):
        qualify_sina_hours(h,d,f,s)


def observation_fixture(confirm_day):
    days = [f"2025-06-{i:02d}" for i in range(2, 9)]
    daily = [{"date": d, "qualified": True, "adjusted_close": 10., "adjusted_low": 9.} for d in days]
    waits = [{"identity_key": "a", "first_seen": days[0], "anchor_adjusted_low": 8.,
              "status": "confirmed", "confirmation_date": days[confirm_day],
              "confirmation_time": "15:00", "confirmation_adjusted_close": 11.,
              "terminal_date": days[confirm_day], "wait_observed_hours": confirm_day*4}]
    return {"asset": {"code": "test", "name": "test", "group": "etf"}, "daily": daily, "waits": waits}


def test_simultaneous_endpoint_unknown():
    r = evaluate_etf_observations(observation_fixture(5), horizons=(5,))
    assert r["event_rows"][0]["reason"] == "confirmation_at_endpoint_no_later_observation"
    assert r["event_rows"][0]["delta_pp"] is None
    assert r["qualification_counts"]["5"]["paired"] == 0


def test_same_time_official_close_not_later_risk():
    data = observation_fixture(2)
    data["daily"][2]["adjusted_close"] = 8.
    r = evaluate_etf_observations(data, horizons=(5,))["event_rows"][0]
    assert r["qualification"] == "paired"
    assert r["candidate_risk_pct"] == pytest.approx(100*(1-10/11))
