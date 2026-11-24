import math

from lei_signal.research.observation_candidates import classify, downside20, mean_ranks_desc, str20


def row(status="1", change="-2", amount="100000000", volume="100", close="9.8", preclose="10"):
    return ["2020-01-01", "sh.600000", "10", "10", "9", close, preclose, volume, amount, "3", status, change, "0"]


def test_quote_and_suspension_classification():
    assert classify(row(), "sh.600000") == ("trade", -0.02, 100000000.0)
    assert classify(row(status="0", change="", amount="", volume=""), "sh.600000") == ("suspended", None, None)
    assert classify(row(status="1", amount=""), "sh.600000") is None
    assert classify(row(status="1", change="nan"), "sh.600000") is None


def test_downside_window_keeps_missing_and_suspensions_distinct():
    window = [classify(row(change="1"), "sh.600000")] * 18
    window += [classify(row(), "sh.600000"), classify(row(status="0", change="", amount="", volume=""), "sh.600000")]
    assert downside20(window) == 2.0
    assert downside20(window[:-1] + [None]) is None
    assert downside20([window[-1]] * 20) is None


def test_str_tie_ranks_and_weighted_difference():
    assert mean_ranks_desc([1, 2, 2, 0]) == [3, 1.5, 1.5, 4]
    returns = [0.01] * 19 + [0.1]
    market = [0.0] * 20
    value = str20(returns, market)
    assert value > 0
    assert value < 0.1
    assert math.isclose(str20([0.01] * 20, [0.01] * 20), 0.0, abs_tol=1e-15)
