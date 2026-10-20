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

``run_analysis`` 是显式传入观察表的合成入口（测试/复算用）；直接调用
**只支持合成**——real 模式写盘前拒绝，自填 base_dir/sha 不能自证真实
身份（主控 S1 收窄）。真实入口只有 ``main``（协议→身份→装载→计算），
其内部经完整校验后调用私有落盘函数 ``_run_analysis_write``。
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
    FIXED_USE,
    IDENTITY,
    OBJECT_REF,
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
    """组间差展示：None → null（缺失），否则 ×100 记作百分点。"""
    return "null" if x is None else f"{x * 100:+.4f}个百分点"


def _pct(x) -> str:
    """组内水平展示：None → null，否则 ×100 记作百分比。"""
    return "null" if x is None else f"{x * 100:+.4f}%"


def _f4(x) -> str:
    """比例展示（无单位）：None → null。"""
    return "null" if x is None else f"{x:.4f}"


def _sv(x) -> str:
    """整数/杂项展示：None → null。"""
    return "null" if x is None else str(x)


def _report_md(full: dict, years: dict, loo: dict, eq: dict, sign: dict,
               overlap: dict, res: dict, params: dict, ident: dict) -> str:
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
    run_kind = ("合成运行（不含真实市场资料，数字无市场含义）"
                if ident["synthetic"] else "真实运行")
    not_est = ("\n**本例全期不可估计（not_estimable）："
               + (full["null_reason"] or "")
               + "；以下组内/区间数字为空或仅结构保留。**"
               if full["delta"] is None else "")
    return f"""# 因子证据可靠性 v1：固定方法补充分析报告（机器生成初稿）

运行性质：{run_kind}。对象：{ident['object_ref']}；标的：{ident['symbol']}。
数据：{full['n_legal']} 条合法观察（{win['start']} 至 {win['end']}）。
目标口径：{params['target_main']}。
本报告是**事后补充的历史敏感性描述**：结果对年份与连续行情假设有多敏感；
不是因子有效性证明。{not_est}

## 全期

- 真组 n={t['n']}，均值 {_pct(t['mean'])}，中位数 {_pct(t['median'])}，
  上涨比例 {_f4(t['up_ratio'])}；
- 假组 n={fl['n']}，均值 {_pct(fl['mean'])}，中位数 {_pct(fl['median'])}，
  上涨比例 {_f4(fl['up_ratio'])}；
- 全期差 delta = {_pp(full['delta'])}
  （读法：真组之后的平均区间变化减假组之后的平均区间变化；
  组内水平用百分比，组间差用百分点）。

## 逐年（信号发生年；跨年目标归观察年）

| 年 | 真n | 假n | 年度差 | 原因 |
|---|---:|---:|---:|---|
{yearly_lines}

年度差符号计数：正 {sign['positive']} / 零 {sign['zero']} / 负 {sign['negative']}。
等权年度差均值 = {_pp(eq['mean_delta'])}
（把每年当一票的平均，与全期把两组各自观察直接平均问的问题不同；
两个都是描述视角，都不是因果校正，反转不意味着计算错误）。
留一年全期差范围：{loo_lo} 至 {loo_hi}
（删除任一单个年份后的全期差；逐项查看各年份删除后的差值及缺失原因，
差值是否随之反号以实际数值为准，不能由此排除单个年份的集中影响，
也不据此称不依赖连续行情）。

## 标签区间重叠（主结果=共同合法集合；单位是相邻交易日价格区间）

- 主结果审计 {_sv(ov['rows_audited'])} 条合法观察；
  排除非法行 {_sv(ov['illegal_rows_excluded'])} 条、
  合法但缺端点 {_sv(ov['legal_missing_endpoints'])} 条（均保留原轴位置）；
- 每条标签覆盖 {_sv(ov['per_label_intervals'])} 个相邻价格区间
  （以本实例协议端点为准，不是对所有输入的通用承诺）；
  全表区间引用 {_sv(ov['total_interval_refs'])} 次，
  唯一区间 {_sv(ov['unique_intervals'])} 个，
  重用比 {_f4(ov['reuse_ratio'])}（描述，不是有效样本数）；
- 相邻观察共享区间均值 {_f4(ov['adjacent_shared_mean'])}/
  {_sv(ov['per_label_intervals'])}；
- 稀疏锚点（{sp['anchor']}，步长{sp['step']}）应有格点
  {_sv(sp['expected_points'])}、可审计 {_sv(sp['auditable_points'])}、
  缺失原因 {sp['reasons']}；可审计格点间共享区间最大
  {_sv(sp['adjacent_shared_max'])}（该计数即使为 0 也不证明独立）。

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


def _resolve_identity(frame: pd.DataFrame, fixed_params: dict,
                      source_meta: dict) -> dict:
    """解析运行身份（主控R1）：真实/合成分开，合成不得冒用真实身份。

    内部辅助函数，不是入口：真实分支的 input_identity 必须来自 ``main``
    已完成的协议校验与固定装载（``validate_protocol`` +
    ``load_b1_observations``），本函数不独立验证来源。

    - real：必须提供已验证合同的 input_identity；数据标的必须与协议一致，
      冲突在写盘前拒绝；对象/用途取合同常量。
    - synthetic：必须显式提供 symbol 与 object_ref，且与数据一致；
      任何 B1/真实输入常量不得进入合成产物。
    """
    mode = source_meta.get("mode")
    symbols = sorted({str(s) for s in frame["symbol"].tolist()})
    if mode == "real":
        identity = source_meta.get("input_identity")
        if not isinstance(identity, dict) or not identity.get("base_dir"):
            raise ValueError("真实模式必须提供已验证合同的 input_identity"
                             "（正式身份由已验证合同导出，不能从常量借用）")
        want = fixed_params.get("symbol")
        if symbols != [want]:
            raise ValueError(f"真实模式身份冲突：协议标的 {want!r} ≠ "
                             f"数据标的 {symbols}（写盘前拒绝）")
        return {
            "mode": "real", "synthetic": False, "symbol": want,
            "object_ref": OBJECT_REF, "use": FIXED_USE,
            "input": {"mode": "real", "base_dir": identity["base_dir"],
                      "observations_csv_sha256":
                          identity.get("observations_csv_sha256")},
        }
    if mode == "synthetic":
        sym = source_meta.get("symbol")
        obj = source_meta.get("object_ref")
        if not isinstance(sym, str) or not sym:
            raise ValueError("合成模式必须显式提供 symbol（合成来源不得"
                             "冒用真实身份）")
        if symbols != [sym]:
            raise ValueError(f"合成元数据 symbol {sym!r} 与数据标的 "
                             f"{symbols} 不一致（矛盾拒绝）")
        if not isinstance(obj, str) or not obj:
            raise ValueError("合成模式必须显式提供 object_ref")
        return {
            "mode": "synthetic", "synthetic": True, "symbol": sym,
            "object_ref": obj, "use": FIXED_USE,
            "input": {"mode": "synthetic",
                      "note": "合成数据；不含真实市场资料，不冒用 B1 身份"},
        }
    raise ValueError("source_meta.mode 必须为 'real' 或 'synthetic'"
                     "（合成输出不得冒用真实资料身份）")


def run_analysis(frame: pd.DataFrame, schedule: pd.DataFrame,
                 fixed_params: dict, *, out_dir, source_meta: dict) -> dict:
    """对观察表执行固定方法分析并落盘（直接调用**仅限显式合成输入**）。

    主控 S1 收窄：公开直接调用不再接受 real 模式——自填
    ``input_identity``（base_dir/sha）不是已验证合同，不能自证真实身份，
    写盘前拒绝；真实运行只能经 ``main`` 的已校验入口（协议校验→固定输入
    装载→私有落盘函数），不引入可自填的 verified/token/approval 旁路。
    """
    mode = source_meta.get("mode")
    if mode == "real":
        raise ValueError("real 模式不允许直接调用 run_analysis：真实身份"
                         "不能自填（base_dir/sha 不是已验证合同，写盘前"
                         "拒绝）；真实运行只能经 main 的已校验入口")
    if mode != "synthetic":
        raise ValueError("source_meta.mode 必须为 'synthetic'（直接调用仅"
                         "支持显式合成输入；真实入口只有 main）")
    return _run_analysis_write(frame, schedule, fixed_params,
                               out_dir=out_dir, source_meta=source_meta)


def _run_analysis_write(frame: pd.DataFrame, schedule: pd.DataFrame,
                        fixed_params: dict, *, out_dir,
                        source_meta: dict) -> dict:
    """分析并落盘（私有：真实路径仅由 ``main`` 完成校验后调用）。

    身份（真实/合成）由 ``source_meta`` 显式声明并经 ``_resolve_identity``
    逐项核对；本函数不承诺独立验证来源，对外不是已校验真实入口。
    缺组/空集/不足资料不崩溃，写成结构化 not_estimable 输出（真实 CLI
    入口的资料不足出口为退出 2，见 ``main``）。
    """
    out = Path(out_dir)
    if out.exists():
        raise ValueError(f"输出目录已存在，拒绝覆盖：{out}")
    ident = _resolve_identity(frame, fixed_params, source_meta)
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

    if ident["mode"] == "real":
        (out / "protocol.source.json").write_bytes(
            Path(source_meta["protocol_path"]).read_bytes())
    else:
        _jdump(out / "protocol.source.json", {
            "mode": "synthetic",
            "note": ("合成运行无正式冻结协议；本文件是占位说明，"
                     "不是协议副本，不给合成计算背书"),
        })
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
        "object_ref": ident["object_ref"],
        "use": ident["use"],
        "synthetic": ident["synthetic"],
        "symbol": ident["symbol"],
        "target": fixed_params["target_main"],
        "window": fixed_params["evaluation_window"],
        "input": ident["input"],
        "protocol": (None if ident["synthetic"] else {
            "identity": IDENTITY,
            "sha256": source_meta.get("protocol_sha256")}),
        "observed_before": not ident["synthetic"],
        "observed_before_note": ("合成数据，不涉及已见/未见真实资料" if
                                 ident["synthetic"] else
                                 "输入观察表已用于 B1 历史描述；本研究是事后"
                                 "补充，不是未见数据验证"),
        "method": {"stability": "全期+逐年+留一年+等权年度差",
                   "overlap": "相邻交易日区间级重叠审计（主结果=共同合法集合）"},
        "resampling": {
            "name": "circular_block_bootstrap 成对同索引",
            "block_lengths": res_cfg["block_lengths"],
            "reps": res_cfg["reps"], "seed": res_cfg["seed"],
            "min_valid_reps": res_cfg["min_valid_reps"]},
        "results": {"stability": "stability.json", "yearly": "yearly.csv",
                    "leave_one_year_out": "leave-one-year-out.csv",
                    "overlap": "overlap.json",
                    "uncertainty": "uncertainty.json"},
        "limitations": [
            "事后描述；快照2026-09-08取得，历史可得性未知" if not
            ident["synthetic"] else "合成数据，无真实市场含义",
            "标签重叠非独立；重用比不是有效样本数",
            "条件性范围不是有效概率/显著性/独立样本数",
            "未接入：IC/排序、factor_return、风险模型归因、真实时点验证",
        ],
        "qualifications": {
            "definition_clarity": "二元状态定义来自候选卡（draft）",
            "data_qualification": ("B1共同合法集合；供应商调整价未核含分红财富"
                                   if not ident["synthetic"] else
                                   "合成输入，无数据资格声明"),
            "implementation": "本包独立实现+测试；与 arch 未做逐值兼容核验",
            "effectiveness": "无预测有效性证明；年度结果见实际输出",
            "production": "无生产授权",
        },
        "next_step": "最多一个最能改变判断的实验：由主控/用户决定（见正式报告）",
        "valid": None,
    }
    _jdump(out / "evidence-card.json", card)
    (out / "report.md").write_text(
        _report_md(full, yearly["years"], yearly["leave_one_year_out"],
                   yearly["equal_weight_year_delta"], yearly["sign_counts"],
                   overlap, res, fixed_params, ident), encoding="utf-8")

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
            "mode": ident["mode"],
            "synthetic": ident["synthetic"],
            "symbol": ident["symbol"],
            "unit": ("组内均值/中位数为百分比；组间差（delta）为小数变化率，"
                     "×100 读作百分点"),
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
                                                   for L in res},
            "not_estimable": full["delta"] is None}


def main(protocol_path, out_dir, repo_root) -> int:
    """真实入口：协议→输入身份→装载→一次固定分析。返回进程退出码。

    资料不足（全期缺组/轴短于最大L）按原合同返回 2，不创建输出目录；
    身份/合同错误返回 3。
    """
    try:
        out = Path(out_dir)
        if out.exists():
            raise ValueError(f"输出目录已存在，拒绝覆盖：{out}")
        contract = validate_protocol(protocol_path, repo_root)
        frame, schedule, audit = load_b1_observations(repo_root, contract)
        params = contract["fixed_params"]
        pre = state_summary(frame)
        max_L = max(params["resampling"]["block_lengths"])
        if pre["delta"] is None or len(frame) < max_L:
            print(f"[exit 2] 资料不足（not_estimable）："
                  f"{pre['null_reason']}；n={len(frame)}，max_L={max_L}")
            return 2
        # 真实路径只经私有落盘函数：上方 validate_protocol + 装载已完成
        # 完整校验，公开 run_analysis 已收窄为仅合成直接调用（主控S1）
        summary = _run_analysis_write(
            frame, schedule, params, out_dir=out,
            source_meta={
                "mode": "real",
                "input_identity": contract["input_identity"],
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
