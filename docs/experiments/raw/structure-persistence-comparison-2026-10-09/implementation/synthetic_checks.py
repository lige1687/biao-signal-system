"""Finite hand-made checks. Never opens the saved four-ETF panel."""

import hashlib
import importlib.util
import math
import sys
from datetime import date, timedelta
from pathlib import Path


MAIN = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
WORKTREE = Path(__file__).resolve().parents[5]
MODULE = WORKTREE / "src/lei_signal/research/structure_persistence_comparison.py"
DETECTOR = MAIN / "src/lei_signal/rules/strict_structure.py"
assert hashlib.sha256(DETECTOR.read_bytes()).hexdigest() == "d37e1c60a9a82d780d6d2e55815782630121dce03053b920f782e6543b187a78"
spec = importlib.util.spec_from_file_location("structure_persistence_synthetic", MODULE)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def day(index):
    return (date(2025, 1, 1) + timedelta(days=index)).isoformat()


def bar(index, high, low, close):
    return {"date": day(index), "open": close, "high": high, "low": low, "close": close}


def node(side, index, reference, final, ref_index=0):
    return module.Node(side, day(index), day(ref_index), reference, 7.0, final)


def check_states():
    bars = [bar(i, 9, 7, 8) for i in range(20)]
    bars += [bar(20, 8, 6, 7), bar(21, 7.9, 6.1, 7),
             bar(22, 7, 5, 6), bar(23, 8, 6, 7),
             bar(24, 8, 5.5, 7), bar(25, 8.5, 5.2, 7),
             bar(26, 8, 5.0, 6.5), bar(27, 11, 4, 6),
             bar(28, 9, 5, 7), bar(29, 8, 4, 6)]
    nodes = [node("top", 20, 10, 6), node("top", 24, 9, 5.5, 22),
             node("top", 26, 9.5, 5, 25), node("bottom", 27, 4, 11, 25),
             node("top", 27, 9, 4, 25), node("top", 29, 8, 4, 28)]
    ema = [None] * 19 + [8.0] * (len(bars) - 19)
    rows = module.build_segment_features(asset="510300.SS", segment=0, bars=bars,
                                         nodes=nodes, ema20=ema, warmup=21)
    assert rows[20]["root_day"] and not rows[20]["episode_day"]
    assert rows[21]["bar_value"] == 1 and rows[21]["bar_comparison_count"] == 0
    assert rows[22]["bar_value"] == 1 and rows[22]["bar_comparison_count"] == 1
    assert rows[23]["bar_value"] == 0 and rows[23]["node_state"] == "pending"
    assert rows[24]["bar_value"] == 0 and rows[24]["node_state"] == "active"
    assert rows[24]["node_progress_count"] == 1  # second lower top after a rebound
    assert rows[26]["node_state"] == "broken" and rows[26]["node_value"] == 0
    assert rows[27]["terminal"] and rows[27]["root_high_break"] and rows[27]["new_bottom"]
    assert rows[27]["bar_value"] == rows[27]["node_value"] == 0
    assert not rows[27]["root_day"]  # new top on terminal date cannot reseed
    assert rows[29]["root_day"] and rows[29]["episode_id"] != rows[20]["episode_id"]
    try:
        module.build_segment_features(asset="510300.SS", segment=0, bars=bars, nodes=nodes + [nodes[0]],
                                      ema20=ema, warmup=21)
    except ValueError as exc:
        assert "duplicate" in str(exc)
    else:
        raise AssertionError("duplicate node accepted")

    # Tail extension can turn a previously valid effective group into an equality failure.
    groups = [module.Group(10, 8, day(0), day(0))]
    assert module.append_group(groups, day(1), 9, 7)
    assert not module.append_group(groups, day(2), 10, 6.5)
    assert len(groups) == 2 and groups[-1].high == groups[-2].high
    tail_bars = [bar(i, 9, 7, 8) for i in range(20)] + [bar(20, 8, 6, 7),
        bar(21, 7, 5, 6), bar(22, 8, 4.5, 6)]
    tail_rows = module.build_segment_features(asset="510300.SS", segment=0,
        bars=tail_bars, nodes=[node("top", 20, 10, 6)],
        ema20=[None] * 19 + [8.0] * (len(tail_bars) - 19), warmup=21)
    assert tail_rows[21]["bar_value"] == 1 and tail_rows[22]["bar_value"] == 0
    assert tail_rows[22]["bar_comparison_count"] == 1  # same tail was rechecked, not recounted

    # A new segment does not inherit the prior episode or baseline state.
    fresh = module.build_segment_features(asset="510300.SS", segment=1, bars=bars[:21],
                                          nodes=[], ema20=ema[:21], warmup=21)
    assert all(r["episode_id"] is None for r in fresh)


def check_warmup_continuity():
    """State runs before bar 252; only evaluation is withheld."""
    rows = [bar(i, 10, 8, 9) for i in range(249)]
    rows += [bar(249, 9, 7, 8), bar(250, 8, 6, 7), bar(251, 7, 5, 6)]
    root = module.Node("top", day(249), day(247), 12.0, 8.0, 7.0)
    second = module.Node("top", day(250), day(248), 11.0, 7.0, 6.0)
    result = module.build_segment_features(asset="510300.SS", segment=0, bars=rows,
        nodes=[root, second], ema20=[None] * 19 + [9.0] * 233, warmup=252)
    module.mark_calendar_maturity(result)
    assert result[249]["root_day"] and result[249]["exclusion_reason"] == "warmup"
    assert result[250]["episode_day"] and result[250]["bar_value"] == 1
    assert result[250]["node_value"] == 1 and result[250]["exclusion_reason"] == "warmup"
    assert result[251]["evaluation_eligible"] and result[251]["episode_day"]
    assert result[251]["episode_id"] == result[250]["episode_id"]
    assert result[251]["bar_value"] == result[251]["node_value"] == 1
    assert result[251]["bar_comparison_count"] == 2 and result[251]["node_progress_count"] == 1
    # Maturity can fail for the last saved day, but warmup is never selected as common support.
    assert not any(r["exclusion_reason"] is None for r in result[:251])
    # A pre-warmup break is absorbing across the evaluation boundary.
    broken_bars = [bar(i, 10, 8, 9) for i in range(248)] + [
        bar(248, 9, 7, 8), bar(249, 9.5, 7.5, 8.5),
        bar(250, 8, 6, 7), bar(251, 7, 5, 6)]
    broken_nodes = [module.Node("top", day(248), day(246), 12.0, 8.0, 7.0),
                    module.Node("top", day(250), day(249), 11.0, 7.0, 6.0)]
    broken = module.build_segment_features(asset="510300.SS", segment=0,
        bars=broken_bars, nodes=broken_nodes,
        ema20=[None] * 19 + [9.0] * 233, warmup=252)
    module.mark_calendar_maturity(broken)
    assert broken[249]["bar_state"] == "broken" and broken[249]["exclusion_reason"] == "warmup"
    assert broken[251]["episode_day"] and broken[251]["bar_value"] == 0
    assert broken[251]["node_value"] == 1 and broken[251]["node_progress_count"] == 1
    # A terminal event before bar 252 ends the root, also across that boundary.
    terminal_bars = broken_bars[:250] + [bar(250, 13, 6, 9), bar(251, 8, 5, 6)]
    terminal = module.build_segment_features(asset="510300.SS", segment=0,
        bars=terminal_bars, nodes=[broken_nodes[0], node("bottom", 250, 5, 13)],
        ema20=[None] * 19 + [9.0] * 233, warmup=252)
    assert terminal[250]["terminal"] and terminal[251]["episode_id"] is None


def check_detector_prefix():
    sys.path.insert(0, str(MAIN / "src"))
    import pandas as pd
    from lei_signal.rules.strict_structure import detect_strict_structures
    pairs = [(10, 8), (9, 7), (8, 6), (9, 7.5), (8, 6.5),
             (7, 5.5), (9.2, 6.5), (8.5, 6), (7.5, 5)]
    before = {}
    for length in range(1, len(pairs) + 1):
        frame = pd.DataFrame([{"high": high, "low": low} for high, low in pairs[:length]],
                             index=pd.date_range("2026-01-01", periods=length))
        nodes = detect_strict_structures(frame)
        frozen = {(n.side, n.confirmed_date.isoformat()): module.Node.published(n) for n in nodes}
        for key, value in before.items():
            assert frozen[key] == value  # future invalidation/tail changes cannot rewrite publication
        before = frozen
    assert len(before) == 3
    assert before[("top", "2026-01-06")].reference_price == 9


def check_target_and_support():
    rows = [{"date": day(i), "segment": 0, "close": 100 - i} for i in range(22)]
    phases = {row["date"]: "eval_2025" for row in rows}
    answer = module.target_downside20(rows, 0, phases)
    assert answer["matured_at"] == day(21) and math.isclose(answer["downside_pct"], 100 * (1 - 79 / 99))
    phases[day(21)] = "eval_2026H1"
    assert module.target_downside20(rows, 0, phases) is None
    phases[day(21)] = "eval_2025"
    rows[21]["segment"] = 1
    assert module.target_downside20(rows, 0, phases) is None
    rows[21]["segment"] = 0
    rows[21]["close"] = math.nan
    assert module.target_downside20(rows, 0, phases) is None

    base = {"asset": "510300.SS", "phase": "eval_2025", "sma20_rising": True,
            "ema20_rising": False, "exclusion_reason": None, "episode_id": "e1"}
    sample = [dict(base, date=day(i), bar_value=bar, node_value=node)
              for i, (bar, node) in enumerate(((0, 0), (1, 0), (0, 1), (1, 1)))]
    sample.append(dict(base, date=day(4), sma20_rising=False, bar_value=1, node_value=1))
    support = module.freeze_common_support(sample)
    assert sum(cell["retained"] for cell in support["cells"]) == 1
    assert not support["full_panel_eligible"]  # one asset-phase is not the full 4-by-2 panel
    assert any(not cell["retained"] for cell in support["cells"])

    complete = []
    for asset in ("510300.SS", "510050.SS", "510500.SS", "588000.SS"):
        for phase_name, start in (("eval_2025", "2025-01-01"), ("eval_2026H1", "2026-01-01")):
            for i, (bar_state, node_state, y) in enumerate(((0, 0, 0), (1, 0, 4), (0, 1, 2), (1, 1, 6))):
                today = (date.fromisoformat(start) + timedelta(days=i)).isoformat()
                complete.append({"asset": asset, "phase": phase_name, "date": today,
                                 "sma20_rising": True, "ema20_rising": False,
                                 "exclusion_reason": None, "episode_id": asset + phase_name,
                                 "bar_value": bar_state, "node_value": node_state,
                                 "bar_state": "active" if bar_state else "broken",
                                 "node_state": "active" if node_state else "pending",
                                 "episode_age_bars": i + 1, "node_progress_count": node_state,
                                 "target": {"downside_pct": float(y), "terminal_return_pct": float(-y)}})
    frozen = module.freeze_common_support(complete)
    assert frozen["full_panel_eligible"] and len(frozen["retained_keys"]) == 8
    effects = module.effect_table(complete, frozen)
    assert effects["primary"]["status"] == "supported"
    assert effects["primary"]["bar_delta"] == 4 and effects["primary"]["node_delta"] == 2
    calendar = sorted({r["date"] for r in complete})
    intervals = module.moving_block_intervals(complete, frozen, calendar, draws=5, lengths=(2,))
    assert intervals["2"]["status"] == "interval_insufficient" and 0 <= intervals["2"]["valid_draws"] <= 5


def check_effect_release_guard():
    import guarded_runner
    class NoTarget:
        calls = 0
        def attach_matured_targets(self, rows):
            self.calls += 1
            raise AssertionError("target must not run for invalid release")
    fake = NoTarget()
    for release in ({"qualification_path": "/unused"},
                    {"mode": "unknown", "qualification_path": "/unused"},
                    {"mode": "estimate", "panel_path": "/wrong", "qualification_path": "/unused"}):
        try:
            guarded_runner.build_effect(release, fake)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid effect release accepted")
    assert fake.calls == 0


if __name__ == "__main__":
    check_states()
    check_warmup_continuity()
    check_detector_prefix()
    check_target_and_support()
    check_effect_release_guard()
    print("synthetic structure checks passed: frozen prefix, containment, dual termination, warmup crossing and absorbing states, v2 second node, maturity, fixed common support, paired effect and invalid release before Y")
