"""Task6 独立重汇总（恢复核验1次）：只核字节与从已有 observations 重汇总。

不调用 description_core 的汇总函数，不重新计算状态/目标，不增加真实运行。
规则固定：主比较 = in_comparison=true 的行；真假组按 state 分；n/mean/median/
strict_up_ratio(>0)/aux_n/aux_mean/aux_worst 与 summary.json 对比，
浮点误差 ≤1e-12，计数/键/null 严格一致。
"""
import csv
import json
import math
import sys
from pathlib import Path

RAW = Path(__file__).resolve().parent
RUN = RAW / (sys.argv[1] if len(sys.argv) > 1 else "run-02")
TOL = 1e-12


def stat(mains, auxs):
    if not mains:
        return {"n": 0, "mean": None, "median": None, "up_ratio": None,
                "aux_n": 0, "aux_mean": None, "aux_worst": None}
    s = sorted(mains)
    n = len(s)
    median = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
    return {"n": n, "mean": sum(mains) / n, "median": median,
            "up_ratio": sum(1 for m in mains if m > 0) / n,
            "aux_n": len(auxs),
            "aux_mean": sum(auxs) / len(auxs) if auxs else None,
            "aux_worst": min(auxs) if auxs else None}


def close(a, b):
    if a is None or b is None:
        return a is None and b is None
    return math.isclose(a, b, abs_tol=TOL)


def main() -> int:
    errors = []
    summary = json.loads((RUN / "summary.json").read_text())
    quality = json.loads((RUN / "quality.json").read_text())
    sym = summary["symbols"]["510300"]

    with (RUN / "observations.csv").open(newline="") as f:
        obs = list(csv.DictReader(f))

    comp = [r for r in obs if r["in_comparison"] == "True"]
    groups = {}
    for want, key in (("true", "true_group"), ("false", "false_group")):
        g = [r for r in comp if r["state"] == want]
        mains = [float(r["main"]) for r in g]
        auxs = [float(r["aux"]) for r in g if r["aux"] != ""]
        groups[key] = stat(mains, auxs)

    for key, mine in groups.items():
        ref = sym[key]
        for field in ("n", "aux_n"):
            if mine[field] != ref[field]:
                errors.append(f"{key}.{field}: {mine[field]} != {ref[field]}")
        for field in ("mean", "median", "up_ratio", "aux_mean", "aux_worst"):
            if not close(mine[field], ref[field]):
                errors.append(f"{key}.{field}: {mine[field]!r} != {ref[field]!r}")

    rec = quality["reconciliation"]
    if rec["comparison_n"] != len(comp):
        errors.append(f"comparison_n: {rec['comparison_n']} != {len(comp)}")
    t = sum(1 for r in comp if r["state"] == "true")
    fl = sum(1 for r in comp if r["state"] == "false")
    if (rec["comparison_true"], rec["comparison_false"]) != (t, fl):
        errors.append("comparison true/false 对账不符")
    # 稀疏格点独立重数（从 observations 直接按锚点+步长定位，不用 summary slots）
    with (RUN / "states.csv").open(newline="") as f:
        states_rows = list(csv.DictReader(f))
    anchor_pos = next(i for i, r in enumerate(states_rows)
                      if r["date"] == "2019-10-08")
    slot_sessions = {states_rows[p]["date"]
                     for p in range(anchor_pos, len(states_rows), 23)}
    in_eval = [r for r in obs if r["session"] in slot_sessions]
    for want, label in (("true", "true"), ("false", "false")):
        valid = [r for r in in_eval if r["state"] == want
                 and r["in_comparison"] == "True"]
        up = sum(1 for r in valid if float(r["main"]) > 0)
        down = sum(1 for r in valid if float(r["main"]) < 0)
        zero = sum(1 for r in valid if float(r["main"]) == 0)
        ref = sym["sparse_view"]["groups"][label]
        if (ref["n"], ref["up"], ref["down"], ref["zero"]) != \
                (len(valid), up, down, zero):
            errors.append(f"sparse {label}: 独立({len(valid)},{up},{down},{zero}) "
                          f"!= {ref}")

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print(f"独立重汇总一致（容差1e-12）：主比较 n={len(comp)} "
          f"(真{t}/假{fl})；稀疏两组计数一致；未重算状态/目标")
    print(f"真组 mean={groups['true_group']['mean']:.6f} "
          f"median={groups['true_group']['median']:.6f} "
          f"up={groups['true_group']['up_ratio']:.4f}")
    print(f"假组 mean={groups['false_group']['mean']:.6f} "
          f"median={groups['false_group']['median']:.6f} "
          f"up={groups['false_group']['up_ratio']:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
