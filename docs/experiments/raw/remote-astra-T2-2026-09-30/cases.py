"""T2 八个（另加一个补充）人工案例的输入。标准答案写在 expected.json，由人工按原文判断。"""
from __future__ import annotations

INIT = dict(sma20=104.0, sma60=100.0, sma120=96.0, ema20=104.6, ema60=100.4, ema120=96.4)


def D(c, l, h=None, lag20=98.0, lag60=97.0, lag120=93.0, **kw):
    return dict(c=c, l=l, h=h if h is not None else c + 0.4, lag20=lag20, lag60=lag60,
                lag120=lag120, **kw)


UP = [D(105.2, 104.8), D(105.4, 105.0), D(105.6, 105.2)]            # 离开 60 组触碰带
DIP60 = [D(103.0, 102.6), D(101.6, 101.2), D(100.9, 100.3)]           # 回撤到 60 组
BLACK_DIP60 = [D(103.0, 102.6, lag20=104.0), D(101.4, 101.0, lag20=104.5),
               D(100.8, 100.1, lag20=104.8)]                          # 同样回撤但 20 组转黑
RECOVER = [D(101.8, 100.9), D(104.9, 101.9), D(105.6, 105.1), D(106.0, 105.6)]

CASES = {
    "C1_valid_first": dict(focus=60, days=UP + DIP60 + RECOVER),
    "C2_later_after_black": dict(
        focus=60, days=UP + DIP60 + RECOVER + [D(106.3, 106.0)] + BLACK_DIP60
        + [D(101.6, 100.9, lag20=100.0), D(104.9, 101.8, lag20=100.0), D(105.6, 105.1)]),
    "C3_direction_changed": dict(
        focus=60, days=UP + [D(103.0, 102.6), D(101.6, 101.2), D(100.9, 100.3, lag60=97.0),
                             D(100.6, 100.2, lag60=101.2), D(101.8, 100.9, lag60=97.0),
                             D(104.9, 101.9), D(105.6, 105.1)]),
    "C4_structure_not_confirmed": dict(focus=60, days=UP + DIP60 + RECOVER, a3_compare=True,
                                       structures=[]),
    "C5_confirm_after_touch": dict(
        focus=60, days=UP + DIP60 + [D(100.7, 100.2), D(101.1, 100.5), D(101.3, 100.8),
                                     D(104.9, 101.2), D(105.6, 105.1)],
        a3_compare=True,
        structures=[dict(id="S_c5", confirmed_date="2024-03-15", ref_low=100.2,
                         invalidated_date=None)]),
    "C6_target_missing": dict(focus=60, days=UP + DIP60 + RECOVER, target_check=True),
    "C7_old_structure_invalid_new_structure": dict(
        focus=20, a3_mode="structure_required",
        days=[D(107.0, 106.5), D(107.5, 107.0), D(108.0, 107.6),
              D(106.4, 105.0), D(106.2, 105.3, clock=3), D(106.3, 105.4, clock=3),
              D(106.5, 104.4, clock=3), D(106.7, 105.6, clock=3), D(107.0, 106.1),
              D(107.4, 106.6), D(107.8, 107.1)],
        # S1: M1=03-07 低点105.0，03-08 抬高低点，03-11 创更高高点确认；03-12 最低104.4<105.0 失效。
        # S2: M1=03-12 低点104.4，03-15 确认。时钟 03-08..03-13 为三类，阻断入场。
        structures=[dict(id="S1", confirmed_date="2024-03-11", ref_low=105.0,
                         invalidated_date="2024-03-12"),
                    dict(id="S2", confirmed_date="2024-03-15", ref_low=104.4,
                         invalidated_date=None)]),
    "C8_data_gap": dict(
        focus=60, days=UP + [D(103.0, 102.6), D(101.6, 101.2), {"missing": True},
                             D(100.9, 100.3), D(101.8, 100.9), D(104.9, 101.9), D(105.6, 105.1)]),
    "C9_supplement_touch_without_departure": dict(
        focus=20, days=[D(104.9, 104.5), D(105.1, 104.7), D(105.3, 104.9), D(105.6, 105.2),
                        D(106.2, 105.9), D(106.8, 106.5)]),
}
