"""四个合成手算例的算术核验（纯标准库，内置常数）。

边界：不 import 任何项目模块，不读真实数据，不联网。
所有数字是教学用合成常数，期望值独立手算后硬编码，不从任何项目输出复制。
普通小数绝对容差 1e-12（仅本脚本验算用，不构成生产容差合同）。
"""
import statistics

TOL = 1e-12
results = []


def check(name, actual, expected):
    ok = abs(actual - expected) <= TOL
    results.append((name, actual, expected, ok))
    return ok


# ---- 例1：真假组都随市场上涨 --------------------------------------------
t1 = [0.02, 0.04]
f1 = [0.01, 0.03]
m_t1 = statistics.mean(t1)
m_f1 = statistics.mean(f1)
check("ex1.true_mean", m_t1, 0.03)
check("ex1.false_mean", m_f1, 0.02)
check("ex1.diff", m_t1 - m_f1, 0.01)          # 1 个百分点
check("ex1.true_up_ratio", sum(x > 0 for x in t1) / len(t1), 1.0)
check("ex1.false_up_ratio", sum(x > 0 for x in f1) / len(f1), 1.0)

# ---- 例2：少数赢家 -------------------------------------------------------
t2 = [-0.01, -0.01, -0.01, 0.15]
check("ex2.mean", statistics.mean(t2), 0.03)
check("ex2.median", statistics.median(t2), -0.01)
check("ex2.up_ratio", sum(x > 0 for x in t2) / len(t2), 0.25)
# 赢家贡献拆解：总和 0.12 中赢家贡献 0.15，其余三个合计 -0.03
check("ex2.winner_share_of_sum", 0.15 / sum(t2), 0.15 / 0.12)

# ---- 例3：目标窗口重叠 ----------------------------------------------------
# 价格格点与相邻涨跌区间分开数（v1 曾把 21 个共同点误当 21 个共同区间）。
w0 = set(range(1, 23))    # t=0 的目标价格格点 t+1..t+22 = 1..22
w1 = set(range(2, 24))    # t=1 的格点 2..23
w23 = set(range(24, 46))  # t=23 的格点 24..45
i0 = {(i, i + 1) for i in range(1, 22)}   # t=0 的涨跌区间 (1,2)..(21,22)
i1 = {(i, i + 1) for i in range(2, 23)}   # t=1 的涨跌区间 (2,3)..(22,23)
i23 = {(i, i + 1) for i in range(24, 45)} # t=23 的涨跌区间 (24,25)..(44,45)
check("ex3.grid_points_per_window", len(w0), 22)
check("ex3.intervals_per_window", len(i0), 21)
check("ex3.shared_points_t0_t1", len(w0 & w1), 21)
check("ex3.shared_points_t0_t23", len(w0 & w23), 0)
# 相邻信号 t=0 与 t=1：共同价格点 21 个，但共同涨跌区间只有 (2,3)..(21,22)
check("ex3.shared_intervals_t0_t1", len(i0 & i1), 20)
check("ex3.interval_overlap_ratio_t0_t1", len(i0 & i1) / len(i0), 20 / 21)
check("ex3.shared_intervals_t0_t23", len(i0 & i23), 0)

# ---- 例4：分母不一致 ------------------------------------------------------
true_main = [0.02, 0.04]
true_aux = [-0.03, None]      # 第二个观察路径缺价，aux 缺失
false_main = [0.01]
unknown_main = [0.50]         # 未知状态，只进背景不进主比较

comp = true_main + false_main
background = comp + unknown_main
check("ex4.comparison_n", len(comp), 3)
check("ex4.true_n", len(true_main), 2)
check("ex4.false_n", len(false_main), 1)
check("ex4.background_n", len(background), 4)
check("ex4.comparison_mean", statistics.mean(comp), 0.07 / 3)
check("ex4.background_mean", statistics.mean(background), 0.57 / 4)
valid_aux = [x for x in true_aux if x is not None]
check("ex4.true_aux_n", len(valid_aux), 1)
check("ex4.true_aux_mean", statistics.mean(valid_aux), -0.03)
# 错误做法对照 1：把缺失 aux 填 0，平均下行被稀释一半
check("ex4.wrong_aux_filled0", statistics.mean([-0.03, 0.0]), -0.015)
# 错误做法对照 2：把未知状态的 0.50 混进主比较均值
check("ex4.wrong_mixed_mean", statistics.mean(background), 0.1425)
# 正确主比较均值约 0.0233，混入后 0.1425；放大倍数独立期望写分数 171/28
check("ex4.inflation_factor", (0.57 / 4) / (0.07 / 3), 171 / 28)

failed = [r for r in results if not r[3]]
for name, actual, expected, ok in results:
    print(f"{'PASS' if ok else 'FAIL'}  {name}: actual={actual!r} expected={expected!r}")
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed (tol={TOL})")
raise SystemExit(1 if failed else 0)
