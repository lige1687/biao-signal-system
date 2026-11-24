"""宽度开跑前独立核验：隔离合成反例（2026-09-18，ZCode GLM-5.3-Flash）。

独立性约定：
- 全部期望值由合同（docs/archive/handoffs-plans/2026-09-17-breadth-first-description-execution.md
  §唯一评价合同/§固定统计）与手算固定，注释给出推导；不从被测实现输出抄数。
- 只用合成夹具；不读任何真实输入文件；不运行完整 CLI；不联网。
- 被审对象仅 src/lei_signal/research/breadth_description.py（经
  momentum_prototype.rank_diagnostic 传递导入）。
- 期望常量（cutoff、偏移、优先级、min_pairs 语义）在本文件内手写，不 import
  breadth_description_contract，避免以实现自证实现。
"""
from __future__ import annotations

import ast
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# 路径护栏：本文件位于 <repo>/docs/research/proposals/<目录>/checks/ 下，
# 仓库根是 parents[5]。先断言再 import，防止层级错位静默导入另一份源码。
REPO = Path(__file__).resolve().parents[5]
_SRC = REPO / "src"
if not (_SRC / "lei_signal" / "research" / "breadth_description.py").is_file():
    raise RuntimeError(f"repo path guard failed: computed REPO={REPO}")
sys.path.insert(0, str(_SRC))

from lei_signal.research.breadth_description import (  # noqa: E402
    EXCLUSION_PRIORITY,
    audit_overlap,
    build_pairs,
    summarize_pairs,
)

CUTOFF = "2026-09-17T00:00:00+08:00"  # 合同冻结截止（手写，不 import）

# 合同§唯一评价合同：主排除原因先宽度后目标、互斥。
EXPECTED_PRIORITY = [
    "breadth_row_missing", "breadth_invalid", "breadth_value_missing",
    "target_row_missing", "label_not_mature", "target_missing",
]


# ---------------------------------------------------------------- 夹具

def sessions_list(n, start="2020-01-01"):
    return [(pd.Timestamp(start) + pd.Timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(n)]


def breadth_frame(sessions, b200=25.0, valid=True, coverage=290 / 300, eligible=290):
    return pd.DataFrame({
        "date": list(sessions), "pool_total": [300] * len(sessions),
        "quoted": [300] * len(sessions), "eligible": [eligible] * len(sessions),
        "coverage": [coverage] * len(sessions), "valid": [valid] * len(sessions),
        "b200": [b200] * len(sessions),
    })


def obs_frame(rows):
    frame = pd.DataFrame(rows)
    for col in ("session", "e_date", "x_date"):
        if col not in frame.columns:
            frame[col] = None
    if "main" not in frame.columns:
        frame["main"] = None
    return frame[["session", "e_date", "x_date", "main"]]


def standard_obs(sessions, closes):
    """obs main 手算 = close(x)/close(e)-1（合同目标公式），x 越出轴则无行。"""
    rows = []
    for i in range(len(sessions) - 22):
        e_i, x_i = i + 1, i + 22
        rows.append({"session": sessions[i], "e_date": sessions[e_i],
                     "x_date": sessions[x_i],
                     "main": closes[x_i] / closes[e_i] - 1.0})
    return obs_frame(rows)


def build(breadth, obs, prices, sessions, eval_start, eval_end, cutoff=CUTOFF):
    return build_pairs(breadth, obs, prices, sessions,
                       evaluation_start=eval_start, evaluation_end=eval_end,
                       cutoff=cutoff)


def one_day_pairs(b200=25.0, eligible=290, coverage=None):
    """单日评价窗（t=0）的最小合法夹具；close(e)=100、close(x)=110 手算目标 0.1。"""
    s = sessions_list(30)
    closes = [100.0] * 30
    closes[22] = 110.0
    obs = obs_frame([{"session": s[0], "e_date": s[1], "x_date": s[22], "main": 0.1}])
    cov = (eligible / 300) if coverage is None else coverage
    pairs = build(breadth_frame(s, b200=b200, eligible=eligible, coverage=cov),
                  obs, pd.DataFrame({"date": s, "close": closes}), s, s[0], s[0])
    return pairs, s


def window_pairs(n_axis=8, total=30, drop_obs_at=(), extra_obs_rows=None):
    """前 n_axis 天为评价窗，obs 覆盖全部 x 可行日（i ≤ total-23）。"""
    s = sessions_list(total)
    closes = [100.0 + i for i in range(total)]
    obs = standard_obs(s, closes)
    keep = [r for r in obs.to_dict("records") if r["session"] not in drop_obs_at]
    if extra_obs_rows:
        keep += extra_obs_rows
    obs = obs_frame(keep)
    pairs = build(breadth_frame(s), obs,
                  pd.DataFrame({"date": s, "close": closes}), s, s[0], s[n_axis - 1])
    return pairs, s


def mini_pairs(x, y, dates):
    return pd.DataFrame({
        "session": list(dates), "b200_percent": [v * 100 for v in x],
        "b200_fraction": list(x), "target": list(y),
        "included": [True] * len(x), "primary_exclusion": [""] * len(x),
    })


# ---------------------------------------------------------------- 主统计（手算）

def test_exclusion_priority_order_matches_contract():
    assert list(EXCLUSION_PRIORITY) == EXPECTED_PRIORITY


def test_rank_ascending_rho_one():
    # 名次 [1,2,3] vs [1,2,3]，Pearson = 1（合同§固定统计：并列平均名次后名次相关）
    result = summarize_pairs(mini_pairs([0.1, 0.2, 0.3], [0.01, 0.02, 0.03],
                                        ["2020-01-01", "2020-01-02", "2020-01-03"]),
                             [2020])
    assert result["full"]["rank"]["n"] == 3
    assert result["full"]["rank"]["time_series_spearman"] == pytest.approx(1.0)
    assert result["full"]["rank"]["reason"] is None


def test_rank_descending_rho_minus_one():
    result = summarize_pairs(mini_pairs([0.1, 0.2, 0.3], [0.03, 0.02, 0.01],
                                        ["2020-01-01", "2020-01-02", "2020-01-03"]),
                             [2020])
    assert result["full"]["rank"]["time_series_spearman"] == pytest.approx(-1.0)


def test_rank_tie_sqrt3_over_2():
    # x 名次 [1.5,1.5,3]，y 名次 [1,2,3]：cov=1.5，√(var_x·var_y)=√(1.5·2)=√3
    # → rho = 1.5/√3 = √3/2（手算）
    result = summarize_pairs(mini_pairs([0.1, 0.1, 0.3], [0.01, 0.02, 0.03],
                                        ["2020-01-01", "2020-01-02", "2020-01-03"]),
                             [2020])
    assert result["full"]["rank"]["time_series_spearman"] == pytest.approx(math.sqrt(3) / 2)


def test_rank_constant_column_null():
    result = summarize_pairs(mini_pairs([0.5, 0.5, 0.5], [0.01, 0.02, 0.03],
                                        ["2020-01-01", "2020-01-02", "2020-01-03"]),
                             [2020])
    assert result["full"]["rank"]["time_series_spearman"] is None
    assert result["full"]["rank"]["reason"] == "constant_rank"


def test_rank_two_pairs_null():
    result = summarize_pairs(mini_pairs([0.1, 0.2], [0.01, 0.02],
                                        ["2020-01-01", "2020-01-02"]), [2020])
    assert result["full"]["rank"]["n"] == 2
    assert result["full"]["rank"]["time_series_spearman"] is None
    assert result["full"]["rank"]["reason"] == "fewer_than_three_pairs"


def test_yearly_rerank_by_observation_year():
    # 2020 同向 rho=1、2021 反向 rho=-1；拼接全期：rank_x=[1.5,3.5,5.5,1.5,3.5,5.5]，
    # rank_y=[1.5,3.5,5.5,5.5,3.5,1.5]，dev 积和 = 4+0+4-4+0-4 = 0 → 全期 rho=0（手算）。
    dates = ([f"2020-01-0{d}" for d in (1, 2, 3)]
             + [f"2021-01-0{d}" for d in (1, 2, 3)])
    result = summarize_pairs(mini_pairs([0.1, 0.2, 0.3, 0.1, 0.2, 0.3],
                                        [0.01, 0.02, 0.03, 0.03, 0.02, 0.01], dates),
                             [2020, 2021])
    assert result["full"]["rank"]["time_series_spearman"] == pytest.approx(0.0, abs=1e-12)
    assert result["years"]["2020"]["rank"]["time_series_spearman"] == pytest.approx(1.0)
    assert result["years"]["2021"]["rank"]["time_series_spearman"] == pytest.approx(-1.0)


# ---------------------------------------------------------------- 目标与单位

def test_target_100_to_110_and_scale_invariance():
    # 合同目标公式 close(x)/close(e)-1：e 收盘 100、x 收盘 110 → 0.1；
    # 价格整体同乘 10（1000→1100）目标不变（比例不随单位漂移）。
    s = sessions_list(30)
    for scale in (1.0, 10.0):
        closes = [100.0 * scale] * 30
        closes[22] = 110.0 * scale
        obs = obs_frame([{"session": s[0], "e_date": s[1], "x_date": s[22], "main": 0.1}])
        pairs = build(breadth_frame(s), obs,
                      pd.DataFrame({"date": s, "close": closes}), s, s[0], s[0])
        row = pairs.iloc[0]
        assert row["e_date"] == s[1] and row["x_date"] == s[22]  # t+1 / t+22 端点
        assert row["target"] == pytest.approx(0.1, abs=1e-12)
        assert row["target_recomputed"] == pytest.approx(0.1, abs=1e-12)
        assert bool(row["included"]) is True


def test_percent_to_fraction_once():
    # 合同：输入百分数 0–100，消费时 /100 只一次。25→0.25（不是 0.0025）；
    # 0 与 100 是合法边界（common 卡 quality_gate：等于 0.90 有效、宽度域 [0,100]）。
    for percent, fraction in [(25.0, 0.25), (0.0, 0.0), (100.0, 1.0)]:
        pairs, _ = one_day_pairs(b200=percent)
        row = pairs.iloc[0]
        assert row["b200_percent"] == percent
        assert row["b200_fraction"] == pytest.approx(fraction, abs=1e-15)
        assert bool(row["included"]) is True


def test_coverage_boundary_090():
    # common 卡 quality_gate：eligible/成员总数 >= 0.90，等于 0.90 有效。
    pairs, _ = one_day_pairs(eligible=270)  # 270/300 = 0.90
    assert bool(pairs.iloc[0]["included"]) is True
    pairs2, _ = one_day_pairs(eligible=269)  # 269/300 ≈ 0.8967 < 0.90
    row2 = pairs2.iloc[0]
    assert row2["primary_exclusion"] == "breadth_invalid"
    assert bool(row2["included"]) is False


def test_valid_row_nan_b200_is_excluded_not_rejected():
    # 合同：有效行 b200 缺失按日期保留为 breadth_value_missing，不整体拒绝、不填 0。
    s = sessions_list(30)
    closes = [100.0 + i for i in range(30)]
    bf = breadth_frame(s)
    bf.loc[bf["date"] == s[1], "b200"] = np.nan
    pairs = build(bf, standard_obs(s, closes),
                  pd.DataFrame({"date": s, "close": closes}), s, s[0], s[7])
    row = pairs[pairs["session"] == s[1]].iloc[0]
    assert row["primary_exclusion"] == "breadth_value_missing"
    assert np.isnan(row["b200_percent"]) and np.isnan(row["b200_fraction"])
    assert int(pairs["included"].sum()) == 7


# ---------------------------------------------------------------- 排除与优先级

def test_priority_breadth_before_target_same_day():
    # 同日既有 breadth_invalid 又有 target_row_missing：primary 取先宽度后目标的
    # breadth_invalid；全部原因保留在 exclusion_reasons。
    s = sessions_list(30)
    closes = [100.0 + i for i in range(30)]
    bf = breadth_frame(s)
    bf.loc[bf["date"] == s[3], "valid"] = False
    obs = standard_obs(s, closes)
    obs = obs[obs["session"] != s[3]]
    pairs = build(bf, obs, pd.DataFrame({"date": s, "close": closes}), s, s[0], s[7])
    row = pairs[pairs["session"] == s[3]].iloc[0]
    assert row["primary_exclusion"] == "breadth_invalid"
    assert row["exclusion_reasons"] == "breadth_invalid|target_row_missing"
    assert int(pairs["included"].sum()) == 7 and len(pairs) == 8
    assert int((~pairs["included"].astype(bool)).sum()) == 1


def test_missing_breadth_row_keeps_axis_and_dates():
    # 轴先推导后左连接：缺宽度行不压缩轴，后续 e/x 端点仍按原日历推导。
    s = sessions_list(30)
    closes = [100.0 + i for i in range(30)]
    bf = breadth_frame(s)
    bf = bf[bf["date"] != s[4]]
    pairs = build(bf, standard_obs(s, closes),
                  pd.DataFrame({"date": s, "close": closes}), s, s[0], s[7])
    assert s[4] in set(pairs["session"])
    row4 = pairs[pairs["session"] == s[4]].iloc[0]
    assert row4["primary_exclusion"] == "breadth_row_missing"
    row5 = pairs[pairs["session"] == s[5]].iloc[0]
    assert row5["e_date"] == s[6] and row5["x_date"] == s[27]
    assert bool(row5["included"]) is True


def test_missing_obs_row_and_immature_label_and_missing_target():
    s = sessions_list(30)
    closes = [100.0 + i for i in range(30)]
    obs = standard_obs(s, closes)
    # 无目标行
    pairs = build(breadth_frame(s), obs[obs["session"] != s[2]],
                  pd.DataFrame({"date": s, "close": closes}), s, s[0], s[2])
    assert pairs[pairs["session"] == s[2]].iloc[0]["primary_exclusion"] \
        == "target_row_missing"
    # 标签未成熟：x 日 15:00+08 晚于截止 → label_not_mature，且不产生目标值
    pairs2 = build(breadth_frame(s), obs,
                   pd.DataFrame({"date": s, "close": closes}), s, s[0], s[0],
                   cutoff="2020-01-05T00:00:00+08:00")
    row2 = pairs2.iloc[0]
    assert row2["primary_exclusion"] == "label_not_mature"
    assert row2["target"] is None and row2["target_recomputed"] is None
    assert row2["b200_fraction"] == pytest.approx(0.25, abs=1e-12)
    # 目标行存在但 main 缺失 → target_missing
    obs3 = obs.copy()
    obs3.loc[obs3["session"] == s[0], "main"] = np.nan
    pairs3 = build(breadth_frame(s), obs3,
                   pd.DataFrame({"date": s, "close": closes}), s, s[0], s[0])
    assert pairs3.iloc[0]["primary_exclusion"] == "target_missing"


# ---------------------------------------------------------------- B1 旧状态无关

@pytest.mark.parametrize("state,in_comp", [("true", "false"), ("false", "true"), ("", "")])
def test_b1_state_fields_irrelevant(state, in_comp):
    # 合同：过滤绝不依赖 B1 的 state/flag_*/in_comparison 等旧状态字段。
    s = sessions_list(30)
    closes = [100.0 + i for i in range(30)]
    base_obs = standard_obs(s, closes)
    key_cols = ["session", "e_date", "x_date", "label_mature", "pool_total",
                "eligible", "coverage", "b200_percent", "b200_fraction", "target",
                "target_recomputed", "included", "primary_exclusion", "exclusion_reasons"]
    base = build(breadth_frame(s), base_obs,
                 pd.DataFrame({"date": s, "close": closes}), s, s[0], s[7])[key_cols]
    for junk in ("state", "in_comparison", "primary_exclusion"):
        base_obs[junk] = state or in_comp or "true"
    variant = build(breadth_frame(s), base_obs,
                    pd.DataFrame({"date": s, "close": closes}), s, s[0], s[7])[key_cols]
    pd.testing.assert_frame_equal(base, variant)


# ---------------------------------------------------------------- 硬拒绝路径

def test_missing_required_breadth_column_rejected():
    s = sessions_list(30)
    closes = [100.0 + i for i in range(30)]
    bf = breadth_frame(s).drop(columns=["coverage"])
    with pytest.raises(ValueError, match="missing columns"):
        build(bf, standard_obs(s, closes),
              pd.DataFrame({"date": s, "close": closes}), s, s[0], s[0])


def test_duplicate_dates_rejected():
    s = sessions_list(30)
    closes = [100.0 + i for i in range(30)]
    dup = pd.concat([breadth_frame(s), breadth_frame(s).iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        build(dup, standard_obs(s, closes),
              pd.DataFrame({"date": s, "close": closes}), s, s[0], s[0])
    dup_obs = pd.concat([standard_obs(s, closes), standard_obs(s, closes).iloc[[0]]],
                        ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        build(breadth_frame(s), dup_obs,
              pd.DataFrame({"date": s, "close": closes}), s, s[0], s[0])


def test_string_boolean_rejected():
    # 合同：每行 valid 须真布尔，禁止凭非空字符串判真。
    s = sessions_list(30)
    closes = [100.0 + i for i in range(30)]
    bf = breadth_frame(s)
    bf["valid"] = ["true"] * len(s)
    with pytest.raises(ValueError, match="boolean"):
        build(bf, standard_obs(s, closes),
              pd.DataFrame({"date": s, "close": closes}), s, s[0], s[0])


def test_counts_constraint_rejected():
    s = sessions_list(30)
    closes = [100.0 + i for i in range(30)]
    bf = breadth_frame(s)
    bf.loc[0, "eligible"] = 301  # 违反 0<=eligible<=quoted<=pool_total
    with pytest.raises(ValueError, match="count"):
        build(bf, standard_obs(s, closes),
              pd.DataFrame({"date": s, "close": closes}), s, s[0], s[0])


def test_price_nonpositive_or_nonfinite_rejected():
    s = sessions_list(30)
    obs = standard_obs(s, [100.0 + i for i in range(30)])
    bad = pd.DataFrame({"date": s, "close": [100.0 + i for i in range(30)]})
    bad.loc[0, "close"] = 0.0
    with pytest.raises(ValueError, match="price"):
        build(breadth_frame(s), obs, bad, s, s[0], s[0])
    bad.loc[0, "close"] = np.inf
    with pytest.raises(ValueError, match="price"):
        build(breadth_frame(s), obs, bad, s, s[0], s[0])


def test_target_endpoint_off_by_one_rejected():
    # 合同：目标行存在时端点必须与日历推导完全相同；x 错一天 → 整体拒绝。
    s = sessions_list(30)
    closes = [100.0 + i for i in range(30)]
    obs = standard_obs(s, closes)
    obs.loc[obs["session"] == s[0], "x_date"] = s[21]
    with pytest.raises(ValueError, match="endpoint"):
        build(breadth_frame(s), obs,
              pd.DataFrame({"date": s, "close": closes}), s, s[0], s[7])


def test_target_ratio_mismatch_rejected_but_tolerance_passes():
    # 合同：与冻结价格比率差 >1e-12 绝对误差整体拒绝；容差内通过且保留原 main。
    s = sessions_list(30)
    closes = [100.0 + i for i in range(30)]
    obs = standard_obs(s, closes)
    bad = obs.copy()
    bad.loc[bad["session"] == s[0], "main"] += 1e-9
    with pytest.raises(ValueError, match="ratio"):
        build(breadth_frame(s), bad,
              pd.DataFrame({"date": s, "close": closes}), s, s[0], s[7])
    ok = obs.copy()
    ok.loc[ok["session"] == s[0], "main"] += 5e-13
    pairs = build(breadth_frame(s), ok,
                  pd.DataFrame({"date": s, "close": closes}), s, s[0], s[7])
    assert bool(pairs.iloc[0]["included"]) is True
    assert pairs.iloc[0]["target"] == pytest.approx(ok.loc[0, "main"], abs=1e-15)


def test_b200_out_of_range_rejected():
    for bad_value in (100.5, -0.1):
        s = sessions_list(30)
        closes = [100.0 + i for i in range(30)]
        with pytest.raises(ValueError, match="b200"):
            build(breadth_frame(s, b200=bad_value), standard_obs(s, closes),
                  pd.DataFrame({"date": s, "close": closes}), s, s[0], s[0])


# ---------------------------------------------------------------- 重叠对账（手算）

def test_overlap_21_segments_and_20_shared():
    # 8 条合法配对（t=0..7）：每条 21 段，总引用 8*21=168；
    # 区间并集 = {1..28} → 唯一 28；相邻两条共享 {i+2..i+21} = 20 段（手算）。
    pairs, s = window_pairs(n_axis=8)
    report = audit_overlap(pairs, s)
    assert report["included_pairs"] == 8
    assert report["segments_per_pair"] == 21
    assert report["total_interval_references"] == 168
    assert report["unique_intervals"] == 28
    assert report["consecutive_shared_histogram"] == {"20": 7}


def test_overlap_no_axis_compression_after_exclusion():
    # 剔除 t=4 后剩 7 条（t=0,1,2,3,5,6,7）：区间仍按原日历位置。
    # t=3 → {4..24}，t=5 → {6..26}，共享 {6..24} = 19 段；其余相邻共享 20 段
    # → 直方图 {"20":5,"19":1}；并集仍 {1..28}=28；引用 7*21=147（手算）。
    pairs, s = window_pairs(n_axis=8, drop_obs_at=("2020-01-05",))
    report = audit_overlap(pairs, s)
    assert report["included_pairs"] == 7
    assert report["total_interval_references"] == 147
    assert report["unique_intervals"] == 28
    assert report["consecutive_shared_histogram"] == {"20": 5, "19": 1}


# ---------------------------------------------------------------- 导入卫生

def test_reviewed_modules_have_no_top_level_side_effects():
    # 交接工作项3：import 前静态检查顶层副作用——被审两模块 + 传递导入的
    # momentum_prototype/definitions/factor_runtime 及两个空 __init__。
    rels = [
        "src/lei_signal/__init__.py",
        "src/lei_signal/research/__init__.py",
        "src/lei_signal/research/breadth_description.py",
        "src/lei_signal/research/breadth_description_contract.py",
        "src/lei_signal/research/momentum_prototype.py",
        "src/lei_signal/research/definitions.py",
        "src/lei_signal/research/factor_runtime.py",
    ]
    allowed = (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef,
               ast.ClassDef, ast.Assign, ast.AnnAssign, ast.Expr)
    for rel in rels:
        tree = ast.parse((REPO / rel).read_text(encoding="utf-8"))
        for node in tree.body:
            assert isinstance(node, allowed), f"{rel}: top-level {type(node).__name__}"
            if isinstance(node, ast.Expr):
                assert isinstance(node.value, ast.Constant), \
                    f"{rel}: non-docstring top-level expression"
        # 模块级赋值里只允许纯构造调用（Path/re.compile/frozenset 等），禁止 open/网络
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call):
                        func = sub.func
                        name = getattr(func, "id", getattr(func, "attr", ""))
                        assert name not in {"open", "read_bytes", "read_text",
                                            "write_text", "write_bytes", "mkdir",
                                            "socket", "urlopen", "request", "run"}, \
                            f"{rel}: suspicious top-level call {name!r}"
