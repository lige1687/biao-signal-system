"""R2 返修补件：独立核验器 verify_result.py 的合成验证（S1 execution=2）。

按主控复核 R2：用合成输入直接调用核验函数（不经 CLI、不读真实数据），
验证它能抓住 删行、额外行、NaN、单位错、目标错 五种破坏，并先有清洁控制组
证明一致产物可通过。合成 run 与期望全部由本文件**手造算术**生成：
不 import breadth_description / summarize / build_pairs，不拿被审实现输出当
真值；手算期望（rho=-1、重叠 168/28/20 段、8 干净行+22 缺目标行）在注释中
给推导。若核验器漏抓破坏，记录实质问题而不修改被审实现。

被调对象：docs/experiments/raw/breadth-b200-first-description-2026-09-17/
verify_result.py（只读加载，其模块顶层仅常量与函数定义）。
"""
from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[5]
_SRC = REPO / "src"
if not (_SRC / "lei_signal" / "research" / "breadth_description_contract.py").is_file():
    raise RuntimeError(f"repo path guard failed: computed REPO={REPO}")

RAW = (REPO / "docs/experiments/raw/breadth-b200-first-description-2026-09-17")
VERIFY = RAW / "verify_result.py"

# ---- 手造合成数据（30 个自然日当交易日轴；价格 100+i；前 8 天宽度递增） ----
SESSIONS = [(pd.Timestamp("2020-01-01") + pd.Timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(30)]
CLOSES = [100.0 + i for i in range(30)]
# 宽度：t=0..7 依次 10..80（严格递增），其余日 50（行存在，但目标缺失被排除）
B200 = [10.0 * (i + 1) if i < 8 else 50.0 for i in range(30)]
COVERAGE = 290 / 300
# 目标：t=i → close(x)/close(e)-1，e=i+1、x=i+22（合同公式，手算代入）。
# f(i)=(122+i)/(101+i)-1 严格递减（分子分母同加常数，商向 1 收敛），故
# 宽度名次升、目标名次降、无并列 → 手算 rho = -1（期望固定值，不算出来的）。
MAIN = {i: CLOSES[i + 22] / CLOSES[i + 1] - 1.0 for i in range(8)}
REASONS = ["breadth_row_missing", "breadth_invalid", "breadth_value_missing",
           "target_row_missing", "label_not_mature", "target_missing"]
PAIR_COLUMNS = ["session", "e_date", "x_date", "label_mature", "included",
                "primary_exclusion", "exclusion_reasons", "b200_percent",
                "b200_fraction", "target", "target_recomputed", "coverage",
                "pool_total", "eligible"]
FROZEN_EVAL_START, FROZEN_EVAL_END = "2019-10-08", "2025-12-31"


def _load_verify_module():
    spec = importlib.util.spec_from_file_location("verify_result_repair", VERIFY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def verify_mod():
    return _load_verify_module()


def _pairs_row(i: int) -> dict:
    """第 i 个轴日的 pairs.csv 行（字符串值；空串表示 None）。

    端点与核验器同规则手写：e 存在当且仅当 i+1<30；x 存在当且仅当 i+22<30。
    """
    if i < 8:
        e, x = SESSIONS[i + 1], SESSIONS[i + 22]
        included, mature, primary, reasons = "True", "True", "", ""
        target = target_rc = repr(MAIN[i])
    else:
        e = SESSIONS[i + 1] if i + 1 < 30 else ""
        x = ""
        included, mature, primary, reasons = "False", "False", "target_row_missing", \
            "target_row_missing"
        target = target_rc = ""
    return {"session": SESSIONS[i], "e_date": e, "x_date": x, "label_mature": mature,
            "included": included, "primary_exclusion": primary,
            "exclusion_reasons": reasons, "b200_percent": repr(B200[i]),
            "b200_fraction": repr(B200[i] / 100.0), "target": target,
            "target_recomputed": target_rc, "coverage": repr(COVERAGE),
            "pool_total": "300", "eligible": "290"}


def _describe(vals):
    # 与合同同义的手写统计：均值/中位数（偶数取中间两数平均）/最小/最大。
    if not vals:
        return {"mean": None, "median": None, "min": None, "max": None}
    s = sorted(vals)
    n = len(s)
    return {"mean": sum(vals) / n,
            "median": s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2,
            "min": s[0], "max": s[-1]}


def _summary_table():
    # 全期 = 2020 表（轴全部落在 2020）：8 干净行 + 22 个 target_row_missing。
    fracs = [B200[i] / 100.0 for i in range(8)]
    targets = [MAIN[i] for i in range(8)]
    exclusions = {r: 0 for r in REASONS}
    exclusions["target_row_missing"] = 22
    return {
        "n_all": 30, "n_included": 8, "exclusions": exclusions,
        "breadth_percent": _describe([B200[i] for i in range(8)]),
        "breadth_fraction": _describe(fracs),
        "target": _describe(targets),
        # 手算：8 个目标全为正（x 晚于 e 且价格全正）→ 上涨比例 1.0
        "target_up_fraction": 1.0,
        # 手算：宽度 0.1→0.8 严格升、目标严格降、无并列 → rho = -1
        "rank": {"n": 8, "time_series_spearman": -1.0, "reason": None},
    }


def _empty_year_table():
    return {"n_all": 0, "n_included": 0, "exclusions": {r: 0 for r in REASONS},
            "breadth_percent": _describe([]), "breadth_fraction": _describe([]),
            "target": _describe([]), "target_up_fraction": None,
            "rank": {"n": 0, "time_series_spearman": None,
                     "reason": "fewer_than_three_pairs"}}


def _build_synthetic_run(base: Path) -> Path:
    """手造一份与核验器键集自洽的 inputs + run（全部合成，临时目录）。"""
    inputs = base / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"date": SESSIONS, "pool_total": 300, "quoted": 300,
                  "eligible": 290, "coverage": COVERAGE, "valid": True,
                  "b200": B200}).to_parquet(inputs / "breadth_csi300.parquet",
                                            index=False)
    pd.DataFrame({"date": SESSIONS, "close": CLOSES}).to_csv(
        inputs / "prices.csv", index=False)
    pd.DataFrame([{"session": SESSIONS[i], "e_date": SESSIONS[i + 1],
                   "x_date": SESSIONS[i + 22], "main": repr(MAIN[i])}
                  for i in range(8)]).to_csv(inputs / "observations.csv", index=False)
    (inputs / "calendar.json").write_text(json.dumps(
        {"days": {d: {"is_trading_day": True} for d in SESSIONS}}), encoding="utf-8")

    run = base / "run"
    run.mkdir()
    pd.DataFrame([_pairs_row(i) for i in range(30)],
                 columns=PAIR_COLUMNS).to_csv(run / "pairs.csv", index=False)
    full = _summary_table()
    (run / "summary.json").write_text(json.dumps(
        {"full": full,
         "years": {str(y): (full if y == 2020 else _empty_year_table())
                   for y in range(2019, 2026)}}), encoding="utf-8")
    # 手算重叠：8 条合法行，每条 21 段（{i+1..i+21}）→ 引用 168；并集 {1..28}=28；
    # 相邻共享 {i+2..i+21}=20 段 ×7 次。
    (run / "overlap.json").write_text(json.dumps(
        {"included_pairs": 8, "segments_per_pair": 21,
         "total_interval_references": 168, "unique_intervals": 28,
         "consecutive_shared_histogram": {"20": 7}}), encoding="utf-8")
    (run / "pairs.meta.json").write_text(json.dumps(
        {"evaluation_start": FROZEN_EVAL_START, "evaluation_end": FROZEN_EVAL_END,
         "target": {"offsets": [1, 22]},
         "unit_conversion": {"from": "percent", "to": "fraction", "scale": 100},
         "common_calculate_called": False}), encoding="utf-8")
    return run


def _corrupted_run(base: Path, clean: Path, mutate) -> Path:
    run = base / clean.name
    shutil.copytree(clean, run)
    pairs = pd.read_csv(run / "pairs.csv", dtype=str, keep_default_na=False)
    pairs = mutate(pairs)
    pairs.to_csv(run / "pairs.csv", index=False)
    return run


# ---------------------------------------------------------------- 控制组

def test_verifier_accepts_clean_synthetic_run(tmp_path, verify_mod):
    run = _build_synthetic_run(tmp_path)
    report = verify_mod.verify_run(run, tmp_path / "inputs")
    assert report["ok"] is True, report
    # 证明确实到达键集核对且行数对上（30=30），不是空转通过。
    assert "key set: expected 30 rows, file has 30" in report["checks"], report


# ---------------------------------------------------------------- 五种破坏

def test_verifier_catches_deleted_row(tmp_path, verify_mod):
    clean = _build_synthetic_run(tmp_path / "clean")

    def mutate(pairs):
        return pairs[pairs["session"] != SESSIONS[5]].reset_index(drop=True)

    run = _corrupted_run(tmp_path / "c1", clean, mutate)
    report = verify_mod.verify_run(run, tmp_path / "clean" / "inputs")
    assert report["ok"] is False, report
    assert any(f"missing row for session {SESSIONS[5]}" in e
               for e in report["errors"]), report


def test_verifier_catches_extra_row(tmp_path, verify_mod):
    clean = _build_synthetic_run(tmp_path / "clean")

    def mutate(pairs):
        extra = {c: "" for c in pairs.columns}
        extra["session"] = "2099-01-01"
        return pd.concat([pairs, pd.DataFrame([extra])], ignore_index=True)

    run = _corrupted_run(tmp_path / "c2", clean, mutate)
    report = verify_mod.verify_run(run, tmp_path / "clean" / "inputs")
    assert report["ok"] is False, report
    assert any("extra row for session 2099-01-01" in e
               for e in report["errors"]), report


def test_verifier_catches_nan_value(tmp_path, verify_mod):
    clean = _build_synthetic_run(tmp_path / "clean")

    def mutate(pairs):
        pairs.loc[pairs["session"] == SESSIONS[0], "b200_fraction"] = "nan"
        return pairs

    run = _corrupted_run(tmp_path / "c3", clean, mutate)
    report = verify_mod.verify_run(run, tmp_path / "clean" / "inputs")
    assert report["ok"] is False, report
    assert any(f"row {SESSIONS[0]}: b200_fraction mismatch" in e
               for e in report["errors"]), report


def test_verifier_catches_unit_error(tmp_path, verify_mod):
    clean = _build_synthetic_run(tmp_path / "clean")

    def mutate(pairs):
        # 比例被当成百分数（0.1 → 10）：单位核对必须抓出。
        idx = pairs.index[pairs["session"] == SESSIONS[0]][0]
        pairs.loc[idx, "b200_fraction"] = "10.0"
        return pairs

    run = _corrupted_run(tmp_path / "c4", clean, mutate)
    report = verify_mod.verify_run(run, tmp_path / "clean" / "inputs")
    assert report["ok"] is False, report
    assert any("unit broken" in e for e in report["errors"]), report


def test_verifier_catches_wrong_target(tmp_path, verify_mod):
    clean = _build_synthetic_run(tmp_path / "clean")

    def mutate(pairs):
        idx = pairs.index[pairs["session"] == SESSIONS[0]][0]
        pairs.loc[idx, "target"] = repr(MAIN[0] + 1e-6)
        return pairs

    run = _corrupted_run(tmp_path / "c5", clean, mutate)
    report = verify_mod.verify_run(run, tmp_path / "clean" / "inputs")
    assert report["ok"] is False, report
    assert any(f"row {SESSIONS[0]}: target mismatch" in e
               for e in report["errors"]), report
