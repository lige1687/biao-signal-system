"""Task0：提取前旧 describe_states 的合成行为基线（1批，不用真实数据）。

用途：提取 description_core 后逐字段深度相等对照（行为一致性证据；
与算术正确性是两种证据——算术期望另在测试里手算，不从本输出反推）。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from lei_signal.research.factor_unit.state_description import describe_states  # noqa: E402

OUT = Path(__file__).resolve().parent / "old-behavior-baseline.json"


def sched(n, start="2020-01-01", tz="Asia/Shanghai"):
    days = pd.date_range(start, periods=n, freq="D")
    return pd.DataFrame({"session": days,
                         "close_at": days.tz_localize(tz) + pd.Timedelta(hours=15)})


def contract(window, anchors, cutoff="2030-01-01T15:00:00+08:00"):
    return {"data_mode": "synthetic",
            "object_ref": "candidate:lei.dual_ma.bull_state@draft-1",
            "lookback": 20, "e_offset": 1, "x_offset": 22,
            "evaluation_window": {"start": window[0], "end": window[1]},
            "research_cutoff": cutoff,
            "sparse_anchor_session": anchors, "sparse_step": 23}


def values(symbol, sessions, states, levels):
    return pd.DataFrame({"symbol": symbol, "session": sessions,
                         "state": states, "I": levels})


def run(name, v, s, c):
    try:
        out = describe_states(v, s, c)
        return {"ok": out}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}


def main():
    cases = {}
    # 1) 50日平价：state全真，I恒100（目标全0）
    s50 = sched(50)
    sess = pd.to_datetime(s50["session"])
    cases["flat_50d"] = run("flat_50d",
                            values("SYN", sess, [True] * 50, [100.0] * 50), s50,
                            contract(("2020-01-01", "2020-02-19"), {"SYN": "2020-01-01"}))
    # 2) 100日上涨+缩短评价窗：I=100..199，窗只取前40日
    s100 = sched(100)
    sess100 = pd.to_datetime(s100["session"])
    cases["up_100d_short_window"] = run(
        "up_100d_short_window",
        values("SYN", sess100, [True] * 100, [float(100 + i) for i in range(100)]),
        s100, contract(("2020-01-01", "2020-02-09"), {"SYN": "2020-01-01"}))
    # 3) 真假未知混合且缺辅助路径（D：false@0..9，I(10)=NaN 使路径缺）
    sessions30 = pd.to_datetime(sched(30)["session"])
    d_I = [100.0] * 30
    d_I[10] = np.nan
    cases["mixed_unknown_aux_missing"] = run(
        "mixed_unknown_aux_missing",
        values("D", sessions30,
               [False] * 10 + [None] * 5 + [True] * 15, d_I),
        sched(30), contract(("2020-01-01", "2020-01-30"), {"D": "2020-01-01"}))
    # 4) 全部窗外 + 空输入
    v_out = values("SYN", sess, [True] * 50, [100.0] * 50).copy()
    v_out["session"] = v_out["session"] + pd.DateOffset(years=5)
    cases["all_outside_window"] = run("all_outside_window", v_out, s50,
                                      contract(("2020-01-01", "2020-02-19"),
                                               {"SYN": "2020-01-01"}))
    empty = pd.DataFrame({"symbol": [], "session": [], "state": [], "I": []})
    cases["empty_input"] = run("empty_input", empty, s50,
                               contract(("2020-01-01", "2020-02-19"),
                                        {"SYN": "2020-01-01"}))
    # 5) 跨年：2019-12-15起40日，评价窗跨年
    s40 = sched(40, start="2019-12-15")
    sess40 = pd.to_datetime(s40["session"])
    cases["cross_year"] = run("cross_year",
                              values("SYN", sess40, [True] * 40,
                                     [float(100 + i) for i in range(40)]),
                              s40, contract(("2019-12-15", "2020-01-23"),
                                            {"SYN": "2019-12-15"}))
    # 旧 real 拒绝负例（保持）
    c_real = contract(("2020-01-01", "2020-02-19"), {"SYN": "2020-01-01"})
    c_real["data_mode"] = "real"
    cases["real_mode_rejected"] = run("real_mode_rejected",
                                      values("SYN", sess, [True] * 50, [100.0] * 50),
                                      s50, c_real)
    OUT.write_text(json.dumps(cases, ensure_ascii=False, indent=1,
                              allow_nan=False, default=str) + "\n")
    print(f"baseline written: {OUT}")
    for k, v in cases.items():
        print(f"  {k}: {'ok' if 'ok' in v else v['error'][:60]}")


if __name__ == "__main__":
    main()
