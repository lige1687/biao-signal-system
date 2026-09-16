"""factor_evidence 一次分析编排与产物落盘（manifest 最后原子定稿）。

流程（先验证后计算，失败不留 completed=true）：
1. 输出目录已存在 → 拒绝覆盖（计算前）；
2. ``validate_protocol`` 绑定冻结协议（身份错误→退出3）；
3. ``load_b1_observations`` 六项哈希+日历+观察表核验（资料不足→退出2）；
4. 固定方法一次完成：全期/逐年/留一年、区间重叠审计、L63/L126 成对
   循环区块重抽（同一命令内，不先偷看结果选方法）；
5. 产物落盘：全部输出写完后**最后**写 manifest（tmp → os.replace 原子
   定稿），文件集合与哈希双向一致；任何失败不产生 completed=true 的
   manifest。标准 JSON（allow_nan=False），合法缺失=null+原因。

``run_analysis`` 是显式传入观察表的合成入口（测试/复算用，不经过真实
输入身份检查）；真实入口只有 ``main``（协议→身份→装载→计算）。
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from lei_signal.research.factor_evidence.contract import (
    FIXED_INPUT_IDENTITY,
    FactorEvidenceIncompleteError,
    validate_protocol,
)
from lei_signal.research.factor_evidence.observations import (
    load_b1_observations,
)
from lei_signal.research.factor_evidence.resampling import paired_block_deltas
from lei_signal.research.factor_evidence.stability import (
    overlap_audit,
    state_summary,
    year_stability,
)


def _jdump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1,
                               allow_nan=False) + "\n", encoding="utf-8")


def _cell(v) -> str:
    """CSV 单元格：None → 空串（null+原因列另存），float → repr 精度。"""
    if v is None:
        return ""
    if isinstance(v, float):
        return repr(v)
    return str(v)


def _write_yearly_csv(path: Path, years: dict) -> None:
    cols = ["year", "true_n", "true_mean", "true_median", "true_up",
            "true_down", "true_zero", "true_up_ratio", "true_aux_n",
            "true_aux_mean", "true_aux_worst", "false_n", "false_mean",
            "false_median", "false_up", "false_down", "false_zero",
            "false_up_ratio", "false_aux_n", "false_aux_mean",
            "false_aux_worst", "delta", "null_reason"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for y in sorted(years):
            e = years[y]
            row = [y]
            for g in ("true", "false"):
                row += [e[g]["n"], e[g]["mean"], e[g]["median"], e[g]["up"],
                        e[g]["down"], e[g]["zero"], e[g]["up_ratio"],
                        e[g]["aux_n"], e[g]["aux_mean"], e[g]["aux_worst"]]
            row += [e["delta"], e["null_reason"]]
            w.writerow([_cell(v) for v in row])


def _write_loo_csv(path: Path, loo: dict) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["year", "n", "true_n", "false_n", "delta", "null_reason"])
        for y in sorted(loo):
            e = loo[y]
            w.writerow([_cell(v) for v in
                        [y, e["n"], e["true_n"], e["false_n"], e["delta"],
                         e["null_reason"]]])


def _write_replicates_csv(path: Path, replicates: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rep", "delta", "true_n", "false_n", "reason"])
        for r in replicates:
            w.writerow([_cell(v) for v in
                        [r["rep"], r["delta"], r["true_n"], r["false_n"],
                         r["reason"]]])


def _pp(x) -> str:
    """百分点展示：None → null（缺失），否则 ×100 保留4位带符号。"""
    return "null" if x is None else f"{x * 100:+.4f}个百分点"


def _report_md(full: dict, years: dict, loo: dict, eq: dict, sign: dict,
               overlap: dict, res: dict, params: dict) -> str:
    t, fl = full["true"], full["false"]
    win = params["evaluation_window"]
    yearly_lines = "\n".join(
        f"| {y} | {e['true']['n']} | {e['false']['n']} | "
        f"{'null' if e['delta'] is None else format(e['delta'] * 100, '+.4f')} |"
        f" {e['null_reason'] or ''} |"
        for y, e in sorted(years.items()))
    loo_vals = [e["delta"] for e in loo.values() if e["delta"] is not None]
    loo_lo = _pp(min(loo_vals)) if loo_vals else "null（有留一年缺组）"
    loo_hi = _pp(max(loo_vals)) if loo_vals else ""
    res_rows = "\n".join(
        f"| {L} | {r['valid_reps']}/{r['reps']} | {_pp(r['point_estimate'])}"
        f" | {_pp(r['quantile_lower'])} | {_pp(r['quantile_upper'])} |"
        for L, r in sorted(res.items()))
    ov, sp = overlap, overlap["sparse"]
    return f"""# 因子证据可靠性 v1：固定方法补充分析报告（机器生成初稿）

对象：candidate:lei.dual_ma.bull_state@draft-1（510300 双均线道路状态，候选卡未入登记表）。
数据：B1 已封存观察表 {full['n_legal']} 条合法观察（{win['start']} 至 {win['end']}）。
本报告是**事后补充的历史敏感性描述**：结果对年份与连续行情假设有多敏感；
不是因子有效性证明。

## 全期

- 真组 n={t['n']}，均值 {_pp(t['mean'])}，中位数 {_pp(t['median'])}，
  上涨比例 {t['up_ratio']:.4f}；
- 假组 n={fl['n']}，均值 {_pp(fl['mean'])}，中位数 {_pp(fl['median'])}，
  上涨比例 {fl['up_ratio']:.4f}；
- 全期差 delta = {_pp(full['delta'])}
  （读法：真组之后的平均区间变化减假组之后的平均区间变化）。

## 逐年（信号发生年；跨年目标归观察年）

| 年 | 真n | 假n | 年度差 | 原因 |
|---|---:|---:|---:|---|
{yearly_lines}

年度差符号计数：正 {sign['positive']} / 零 {sign['zero']} / 负 {sign['negative']}。
等权年度差均值 = {_pp(eq['mean_delta'])}
（改变权重的另一视角，与全期差方向可以不同；都不是因果校正）。
留一年全期差范围：{loo_lo} 至 {loo_hi}（逐年逐一留出，不挑有利年份）。

## 标签区间重叠（相邻交易日价格区间，不是日期点数）

- 每条标签覆盖 {ov['per_label_intervals']} 个相邻价格区间；
  全表区间引用 {ov['total_interval_refs']} 次，
  唯一区间 {ov['unique_intervals']} 个，重用比 {ov['reuse_ratio']:.4f}
  （描述，不是有效样本数）；
- 相邻观察共享 {ov['adjacent_shared_mean']:.0f}/{ov['per_label_intervals']} 个区间；
- 稀疏锚点（{sp['anchor']}，步长{sp['step']}）格点间共享区间最大
  {sp['adjacent_shared_max']}（不重叠不等于独立）。

## 连续行情敏感性（成对循环区块重抽，条件性范围）

| L | 有效重复 | 点估计 | 2.5%分位 | 97.5%分位 |
|---|---:|---:|---:|---:|
{res_rows}

范围名称：条件性95%重抽范围。它只表达"在循环区块假设下，把整段历史重新
拼接后 delta 的波动"，**不是**因子有效的概率、不是显著性通过、不是独立
样本数；两种 L 并排展示，不取有利一个。

## 不能据此判断什么

预测能力、交易利润、因果、其他标的/时期外推、含分红财富口径、当时可得性；
范围过零与否不构成采纳或否决的机械判决。
"""


def run_analysis(frame: pd.DataFrame, schedule: pd.DataFrame,
                 fixed_params: dict, *, out_dir, source_meta: dict) -> dict:
    """对（已验证的）观察表执行固定方法分析并落盘。合成入口，不查身份。"""
    out = Path(out_dir)
    if out.exists():
        raise ValueError(f"输出目录已存在，拒绝覆盖：{out}")
    out.mkdir(parents=True)
    res_cfg = fixed_params["resampling"]
    ov_cfg = fixed_params["overlap"]

    full = state_summary(frame)
    yearly = year_stability(frame)
    overlap = overlap_audit(frame, schedule, ov_cfg["sparse_anchor_session"],
                            ov_cfg["sparse_step"])
    res: dict[int, dict] = {}
    for L in res_cfg["block_lengths"]:
        res[L] = paired_block_deltas(
            frame, block_length=L, reps=res_cfg["reps"],
            seed=res_cfg["seed"],
            min_valid_reps=res_cfg["min_valid_reps"])

    (out / "protocol.source.json").write_bytes(
        Path(source_meta["protocol_path"]).read_bytes())
    _jdump(out / "stability.json", {
        "full_period": full,
        "year_stability": {k: v for k, v in yearly.items() if k != "years"},
    })
    _write_yearly_csv(out / "yearly.csv", yearly["years"])
    _write_loo_csv(out / "leave-one-year-out.csv",
                   yearly["leave_one_year_out"])
    _jdump(out / "overlap.json", overlap)
    for L in res:
        np.save(out / f"resampling-L{L}-starts.npy", res[L]["starts"])
        _write_replicates_csv(out / f"resampling-L{L}-replicates.csv",
                              res[L]["replicates"])
    _jdump(out / "uncertainty.json", {
        "note": "两种L并排完整展示，不取有利一个；范围为条件性95%重抽范围",
        "resampling": {f"L{L}": {k: v for k, v in res[L].items()
                                 if k not in ("starts", "replicates",
                                              "valid_deltas")}
                       for L in sorted(res)},
    })
    card = {
        "object_ref": fixed_params.get("object_ref",
                                       "candidate:lei.dual_ma.bull_state@draft-1"),
        "use": "post_hoc_historical_sensitivity_diagnostic",
        "symbol": fixed_params["symbol"],
        "target": fixed_params["target_main"],
        "window": fixed_params["evaluation_window"],
        "input": {"base_dir": FIXED_INPUT_IDENTITY["base_dir"],
                  "observations_csv_sha256":
                      FIXED_INPUT_IDENTITY["observations_csv_sha256"]},
        "protocol": {"identity": "factor-evidence-reliability@1.0.0",
                     "sha256": source_meta.get("protocol_sha256")},
        "observed_before": True,
        "observed_before_note": ("输入观察表已用于 B1 历史描述；本研究是事后"
                                 "补充，不是未见数据验证"),
        "method": {"stability": "全期+逐年+留一年+等权年度差",
                   "overlap": "相邻交易日区间级重叠审计",
                   "resampling": "circular_block_bootstrap L63/L126 各2000次"
                                 " PCG64 seed 20260916 成对同索引"},
        "results": {"stability": "stability.json", "yearly": "yearly.csv",
                    "leave_one_year_out": "leave-one-year-out.csv",
                    "overlap": "overlap.json",
                    "uncertainty": "uncertainty.json"},
        "limitations": [
            "事后描述；快照2026-09-08取得，历史可得性未知",
            "标签重叠非独立；重用比不是有效样本数",
            "条件性范围不是有效概率/显著性/独立样本数",
            "未接入：IC/排序、factor_return、风险模型归因、真实时点验证",
        ],
        "qualifications": {
            "definition_clarity": "二元状态定义来自候选卡（draft）",
            "data_qualification": "B1共同合法集合；供应商调整价未核含分红财富",
            "implementation": "本包独立实现+测试；与 arch 未做逐值兼容核验",
            "effectiveness": "无预测有效性证据；逐年方向不一致",
            "production": "无生产授权",
        },
        "next_step": "最多一个最能改变判断的实验：由主控/用户决定（见正式报告）",
        "valid": None,
    }
    _jdump(out / "evidence-card.json", card)
    (out / "report.md").write_text(
        _report_md(full, yearly["years"], yearly["leave_one_year_out"],
                   yearly["equal_weight_year_delta"], yearly["sign_counts"],
                   overlap, res, fixed_params), encoding="utf-8")

    # manifest 最后原子定稿：全部输出（只排除顶层 manifest 本身）双向一致
    files = {}
    for f in sorted(out.rglob("*")):
        if f.is_file() and f != out / "manifest.json":
            files[str(f.relative_to(out))] = {
                "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
                "bytes": f.stat().st_size,
            }
    actual = set(files)
    expected = {"protocol.source.json", "stability.json", "yearly.csv",
                "leave-one-year-out.csv", "overlap.json", "uncertainty.json",
                "evidence-card.json", "report.md"}
    expected |= {f"resampling-L{L}-{kind}" for L in res
                 for kind in ("starts.npy", "replicates.csv")}
    if actual != expected:
        raise ValueError(f"输出文件集合与必需清单不一致："
                         f"缺 {sorted(expected - actual)[:5]}，"
                         f"多 {sorted(actual - expected)[:5]}")
    manifest = {
        "identity": "factor-evidence-reliability@1.0.0",
        "completed": True,
        "exit_code": 0,
        "object_ref": card["object_ref"],
        "use": card["use"],
        "files": files,
        "file_count": len(files),
        "metadata": {
            "unit": "main/aux/delta 为小数变化率，×100 读作百分点",
            "object": card["object_ref"],
            "target": fixed_params["target_main"],
            "legal_set": fixed_params["legal_set"],
            "data_use_limits": card["limitations"],
            "inputs_verified": source_meta.get("hashes_verified"),
            "numpy_version": res[sorted(res)[0]]["numpy_version"],
            "starts_saved": [f"resampling-L{L}-starts.npy"
                             for L in sorted(res)],
        },
        "manifest_note": ("manifest 最后写入；completed=true 只代表工程完成，"
                          "不代表结论有效"),
    }
    tmp = out / "manifest.json.tmp"
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=1,
                              allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, out / "manifest.json")
    return {"full_delta": full["delta"], "valid": {L: res[L]["valid_reps"]
                                                   for L in res}}


def main(protocol_path, out_dir, repo_root) -> int:
    """真实入口：协议→输入身份→装载→一次固定分析。返回进程退出码。"""
    try:
        out = Path(out_dir)
        if out.exists():
            raise ValueError(f"输出目录已存在，拒绝覆盖：{out}")
        contract = validate_protocol(protocol_path, repo_root)
        frame, schedule, audit = load_b1_observations(repo_root, contract)
        summary = run_analysis(
            frame, schedule, contract["fixed_params"], out_dir=out,
            source_meta={
                "protocol_path": contract["protocol_path"],
                "protocol_sha256": contract["protocol_sha256"],
                "hashes_verified": audit["hashes_verified"],
            })
        print(json.dumps({"completed": True, "full_delta": summary["full_delta"],
                          "valid_reps": summary["valid"]}, ensure_ascii=False))
        return 0
    except FactorEvidenceIncompleteError as exc:
        print(f"[exit 2] 资料不足：{exc}")
        return 2
    except ValueError as exc:
        print(f"[exit 3] 身份/合同错误：{exc}")
        return 3
