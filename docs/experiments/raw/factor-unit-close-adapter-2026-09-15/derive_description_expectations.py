"""独立期望推导：state_description 合成夹具（test_factor_unit_state_description）。

本脚本**禁止 import 被测模块**（lei_signal.* 亦不 import）；期望由独立算术推导，
输出 JSON 供复核对照。夹具构造与 tests/unit/test_factor_unit_state_description.py
的 build_fixture 一致（常数重复是独立性的代价，特意为之）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

N = 47  # 42格2020 + 5格2021
SPECIAL_A = {24: 101.0, 6: 110.0, 27: 121.0, 9: 105.0, 30: 115.5,
             20: 115.0, 34: 99.0, 33: 97.0, 37: 102.0, 41: 103.0}
TRUE_A = (2, 5, 8, 30)
FALSE_A = (12, 15)
EVAL_MAX = 24  # x = t+22 <= 46


def sessions() -> pd.DatetimeIndex:
    s1 = pd.date_range("2020-01-01", periods=42, freq="D")
    s2 = pd.date_range("2021-01-01", periods=5, freq="D")
    return s1.append(s2)


def vector(special: dict[int, float], nan_at: int | None = None) -> np.ndarray:
    v = np.full(N, 100.0)
    for k, val in special.items():
        v[k] = val
    if nan_at is not None:
        v[nan_at] = np.nan
    return v


def main_target(I: np.ndarray, t: int) -> tuple[str, float | None]:
    if t + 22 >= N:
        return "tail_immature", None
    e, x = I[t + 1], I[t + 22]
    if np.isnan(e):
        return "e_missing", None
    if np.isnan(x):
        return "x_missing", None
    return "ok", x / e - 1.0


def aux_target(I: np.ndarray, t: int) -> float | None:
    if t + 22 >= N:
        return None
    path = I[t + 1 : t + 23]
    if np.isnan(path).any():
        return None
    return min(0.0, float(np.min(path / I[t + 1] - 1.0)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    out_path = Path(args.out) if (args := ap.parse_args()) else None
    if out_path.exists():
        print(f"REFUSE to overwrite {out_path}")
        sys.exit(3)

    sess = sessions()
    I_a = vector(SPECIAL_A)
    mains_a = {t: main_target(I_a, t) for t in range(N)}
    true_mains = [m for t in TRUE_A if (m := mains_a[t][1]) is not None]
    false_mains = [mains_a[t][1] for t in FALSE_A if mains_a[t][1] is not None]
    true_aux = [a for t in TRUE_A if mains_a[t][1] is not None and (a := aux_target(I_a, t)) is not None]
    false_aux = [aux_target(I_a, t) for t in FALSE_A if mains_a[t][1] is not None]
    false_aux = [a for a in false_aux if a is not None]
    all_mains = [m[1] for m in mains_a.values() if m[1] is not None]

    I_d = vector({}, nan_at=10)
    d_reasons: dict[str, int] = {}
    d_false_mains = []
    for t in range(10):  # false@0..9
        reason, m = main_target(I_d, t)
        d_reasons[reason] = d_reasons.get(reason, 0) + 1
        if m is not None:
            d_false_mains.append(m)

    payload = {
        "fixture": "test_factor_unit_state_description.build_fixture",
        "expectation_source": "independent arithmetic (no import of module under test)",
        "A": {
            "state_true": len(TRUE_A), "state_false": len(FALSE_A),
            "state_unknown": N - len(TRUE_A) - len(FALSE_A),
            "true_group": {"n": len(true_mains), "mean": float(np.mean(true_mains)),
                           "median": float(np.median(true_mains)),
                           "up_ratio": float(np.mean([m > 0 for m in true_mains])),
                           "aux_mean": float(np.mean(true_aux)) if true_aux else None,
                           "aux_worst": float(np.min(true_aux)) if true_aux else None},
            "false_group": {"n": len(false_mains), "mean": float(np.mean(false_mains)),
                            "median": float(np.median(false_mains)),
                            "up_ratio": float(np.mean([m > 0 for m in false_mains])),
                            "aux_mean": float(np.mean(false_aux)) if false_aux else None,
                            "aux_worst": float(np.min(false_aux)) if false_aux else None},
            "unconditional": {"n": len(all_mains), "mean": float(np.mean(all_mains)),
                              "median": float(np.median(all_mains)),
                              "up_ratio": float(np.mean([m > 0 for m in all_mains]))},
            "tail_immature": sum(1 for t in range(N) if mains_a[t][0] == "tail_immature"),
            "true_segments": len(TRUE_A),  # 各true互不相邻（unknown隔开）
            "false_segments": len(FALSE_A),
            "sparse_slots": [
                {"session": str(sess[t].date()), "main": mains_a[t][1]}
                for t in range(2, N, 23) if mains_a[t][1] is not None
            ],
        },
        "D": {"false_evaluable": len(d_false_mains), "target_reasons": d_reasons,
              "false_mean": float(np.mean(d_false_mains)) if d_false_mains else None},
        "notes": [
            "E夹具：单true@2、全上涨路径 → aux_mean=aux_worst=0",
            "G夹具：删窗口中间行(index10)后t=5主目标仍=110/100-1=0.10（日历定位）",
        ],
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
    print(f"written {out_path}")


if __name__ == "__main__":
    main()
