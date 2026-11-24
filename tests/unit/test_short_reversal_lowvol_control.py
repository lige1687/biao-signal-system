import pytest

from lei_signal.research.short_reversal_lowvol_control import lowvol_weights


def test_unbalanced_groups_keep_original_capital_and_ignore_outcomes():
    groups = {str(i): min(i // 7 + 1, 5) for i in range(33)}
    rows = [{"code": str(i), "eligible": True, "vol60": i % 7 / 100,
             "future": 100 if i % 7 > 3 else -100} for i in range(33)]
    w = lowvol_weights(rows, groups)
    assert sum(w.values()) == pytest.approx(1)
    for g in range(1, 6):
        n = sum(v == g for v in groups.values())
        assert sum(x for c, x in w.items() if groups[c] == g) == pytest.approx(n / 33)
        assert sum(groups[c] == g for c in w) == n // 2
    for row in rows:
        row["future"] = -row["future"]
    assert lowvol_weights(rows, groups) == w


def test_missing_member_and_nan_do_not_silently_refill():
    groups = {str(i): i // 6 + 1 for i in range(30)}
    rows = [{"code": str(i), "eligible": True, "vol60": .1} for i in range(30)]
    with pytest.raises(ValueError):
        lowvol_weights(rows[:-1], groups)
    rows[0]["vol60"] = float("nan")
    with pytest.raises(ValueError):
        lowvol_weights(rows, groups)
