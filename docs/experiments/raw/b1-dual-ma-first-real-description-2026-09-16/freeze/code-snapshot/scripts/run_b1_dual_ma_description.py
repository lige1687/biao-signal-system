#!/usr/bin/env python3
"""B1 双均线首次真实历史描述 CLI（先验证，后计算）。

用法：
    python3 scripts/run_b1_dual_ma_description.py --protocol PROTOCOL.json --out NEW_DIR

只接受冻结正式协议（草案拒绝）；退出码：0=完成；2=资料不完整/对账不平
（不留成功 manifest）；3=协议/身份/输入错误（不留状态/目标文件）。
验证（协议+输入包）全部通过后才加载真实计算路径；manifest 最后写，
按实际文件集合双向核哈希。结果硬标 post_hoc_historical_description，
data_mode=real，无预测资格。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from lei_signal.research.factor_unit.b1_contract import (  # noqa: E402
    REQUIRED_CODE_KEYS,
    B1IncompleteError,
    load_verified_input,
    validate_b1_protocol,
)


def sha256_of(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _env_payload() -> dict:
    import numpy
    import pandas
    import yaml
    deps = {"pandas": pandas.__version__, "numpy": numpy.__version__,
            "PyYAML": yaml.__version__}
    for mod, exe in (("pytest", ["python3", "-m", "pytest", "--version"]),
                     ("ruff", ["python3", "-m", "ruff", "--version"])):
        try:
            import subprocess
            out = subprocess.run(exe, capture_output=True, text=True).stdout.strip()
            deps[mod] = out.splitlines()[0] if out else "unknown"
        except Exception:  # noqa: BLE001
            deps[mod] = "unknown"
    return {"python": platform.python_version(), "platform": platform.platform(),
            "dependencies": deps,
            "note": "读取的是未提交工作区源码原字节（source-snapshot/），git HEAD仅参考"}


def _fmt_pct(x):
    return "null" if x is None else f"{x * 100:.3f}%"


def _fmt_ratio(x):
    return "null" if x is None else f"{x:.3f}"


def _write_report(path: Path, summary: dict, quality: dict, contract: dict) -> None:
    sym = contract["symbol"]
    s = summary["symbols"][sym]
    tg, fg = s["true_group"], s["false_group"]
    rec = quality["reconciliation"]
    sparse = s["sparse_view"]
    lines = [
        "# B1 双均线首次真实历史描述（run 内报告）",
        "",
        "结果身份：post_hoc_historical_description（事后历史描述）；data_mode=real；",
        "无预测资格、无 PIT verified、无生产建议。",
        "",
        "## 1. 测的是什么",
        "",
        f"在 {sym} 的供应商调整价历史上，把每个交易日按双均线共同确认状态分为",
        "真/假/未知，比较真/假两组之后 t+1 到 t+22 收盘的价格变化（21个变动区间）。",
        "状态只是道路路况描述，没有买卖动作；这不是交易、策略或选股考试。",
        "",
        "## 2. 资料限制（先于任何数字）",
        "",
        "- 供应商前复权快照 2026-09-08 取得；精确复权公式与锚点未知；未核验历史",
        "  各日价格与当时可见价格一致，也未核验当时可得性（available_at=null）；",
        "- 成熟截止 2026-02-03T15:00+08 是事后设定的标签成熟线，不代表 2 月已持有快照；",
        "- 供应商调整价未独立构造或验证分红再投资财富序列，与含分红财富等价性未核；",
        f"- 单一标的 {sym}、单一评价窗 {contract['evaluation_window']['start']} 至 "
        f"{contract['evaluation_window']['end']}，该段历史底色会渗进所有数字。",
        "",
        "## 3. 有多少有效观察",
        "",
        f"- 评价窗内观察：{rec['observations_in_eval_window']}（真 {rec['state_true']} /",
        f"  假 {rec['state_false']} / 未知 {rec['state_unknown']}；准备期 "
        f"{rec['warmup_sessions_before_window']} 行在窗前单列）",
        f"- 主比较 n = {rec['comparison_n']}（真 {rec['comparison_true']} + "
        f"假 {rec['comparison_false']}，对账"
        f"{'相等' if rec['true_plus_false_equals_comparison'] else '不平！'}）",
        f"- 互斥主要排除原因：{json.dumps(rec['primary_exclusion_counts'], ensure_ascii=False)}",
        "",
        "## 4. 真假状态之后的差别（历史描述差，不是因子贡献）",
        "",
        "| 组 | n | 均值 | 中位数 | 上涨比例(>0) | aux_n | 平均最差 | 最差单例 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        f"| 真 | {tg['n']} | {_fmt_pct(tg['mean'])} | {_fmt_pct(tg['median'])} | "
        f"{_fmt_ratio(tg['up_ratio'])} | {tg['aux_n']} | "
        f"{_fmt_pct(tg['aux_mean'])} | {_fmt_pct(tg['aux_worst'])} |",
        f"| 假 | {fg['n']} | {_fmt_pct(fg['mean'])} | {_fmt_pct(fg['median'])} | "
        f"{_fmt_ratio(fg['up_ratio'])} | {fg['aux_n']} | "
        f"{_fmt_pct(fg['aux_mean'])} | {_fmt_pct(fg['aux_worst'])} |",
        "",
        "措辞纪律：状态为真的观察**之后**目标平均为……；禁止“状态带来了……”。",
        "均值与中位数若不同号，只提示分布不对称、需检查集中程度，不能单凭异号",
        "断言依赖少数赢家。",
        "",
        "## 5. 逐年 / 稀疏 / 分布特征",
        "",
        "逐年（按状态观察年，目标可跨年，不称年度收益）见 summary.json by_year。",
        f"稀疏（锚点 {sparse['anchor_session']}，步长 {sparse['step']}，事先固定）：",
    ]
    for label, cn in (("true", "真"), ("false", "假")):
        g = sparse["groups"][label]
        lines.append(f"- {cn}组有效格 {g['n']}：上涨 {g['up']} / 下跌 {g['down']} / "
                     f"零变化 {g['zero']}（合计=组数）")
    lines += [
        f"- 真状态段：{s['state_segments']['true_segments']} 段，最长 "
        f"{s['state_segments']['longest_true']} 日；假状态段："
        f"{s['state_segments']['false_segments']} 段，最长 "
        f"{s['state_segments']['longest_false']} 日",
        "",
        "## 6. 仍不能证明什么",
        "",
        "本轮不能证明状态有预测能力；不能证明差别会重演；不能证明任何交易能拿到",
        "这笔钱（无仓位、费用、成交检验）；不能推广到其他标的、其他时期；差值不是",
        "因子贡献，背景上涨不是状态功劳，稀疏无重叠不是统计独立。",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--protocol", required=True)
    ap.add_argument("--out", required=True, help="新目录；已存在则拒绝")
    args = ap.parse_args()
    now = datetime.now(timezone(timedelta(hours=8)))
    out = Path(args.out)
    if out.exists():
        print(f"REFUSE: 输出目录已存在 {out}", file=sys.stderr)
        return 3

    # ── 先验证（协议→输入包），通过前不加载真实计算路径、不写任何输出 ──
    try:
        contract = validate_b1_protocol(args.protocol, REPO)
    except ValueError as exc:
        print(f"协议错误: {exc}", file=sys.stderr)
        return 3
    try:
        prices, schedule, audit = load_verified_input(
            REPO / contract["input_identity"]["package"], contract)
    except B1IncompleteError as exc:
        print(f"资料不完整: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"输入/身份错误: {exc}", file=sys.stderr)
        return 3

    # 输出目录在计算前建立：写盘故障（含只读父目录）在任何真实计算之前失败
    try:
        out.mkdir(parents=True)
    except OSError as exc:
        print(f"写盘失败（未开始计算）: {exc}", file=sys.stderr)
        return 3

    from lei_signal.research.factor_unit.b1_description import describe_b1
    result = describe_b1(prices, schedule, contract)
    rec = result["quality"]["reconciliation"]
    recon_ok = all([
        rec["states_sum_equals_window"], rec["true_plus_false_equals_comparison"],
        rec["exclusion_plus_comparison_equals_window"],
        rec["sparse_true_group_sum"], rec["sparse_false_group_sum"],
    ])

    # ── 写盘（计算已完成；失败不置 package_completed） ──
    try:
        proto_bytes = Path(args.protocol).read_bytes()
        (out / "protocol.source.json").write_bytes(proto_bytes)
        # 输入包完整只读拷贝
        shutil.copytree(REPO / contract["input_identity"]["package"],
                        out / "input-package")
        # 必需代码原字节（保留相对目录）
        snap = out / "source-snapshot"
        for rel in REQUIRED_CODE_KEYS:
            dest = snap / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((REPO / rel).read_bytes())
        (out / "environment.json").write_text(
            json.dumps(_env_payload(), ensure_ascii=False, indent=1) + "\n")
        result["states"].to_csv(out / "states.csv", index=False)
        result["observations"].to_csv(out / "observations.csv", index=False)
        (out / "summary.json").write_text(json.dumps(
            result["summary"], ensure_ascii=False, indent=1, allow_nan=False) + "\n")
        quality = dict(result["quality"])
        quality["input_audit"] = audit
        quality["analysis_executed_at"] = now.isoformat()
        (out / "quality.json").write_text(json.dumps(
            quality, ensure_ascii=False, indent=1, allow_nan=False) + "\n")
        _write_report(out / "report.md", result["summary"], quality, contract)
        manifest = {
            "schema": "b1-dual-ma-description/1.0.0",
            "family": contract["family"],
            "use": contract["use"],
            "result_identity": quality["result_identity"],
            "data_mode": "real",
            "protocol_sha256": hashlib.sha256(proto_bytes).hexdigest(),
            "input_identity": contract["input_identity"],
            "reconciliation_ok": recon_ok,
            "package_completed": False,
            "qualification": None,
            "exit_code": None,
            "no_claims": quality["no_claims"],
            "written_at": now.isoformat(),
        }
        (out / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
        actual = {str(f.relative_to(out)) for f in out.rglob("*")
                  if f.is_file() and f.name != "manifest.json"}
        manifest["file_hashes"] = {rel: sha256_of(out / rel) for rel in sorted(actual)}
        manifest["two_way_check"] = {
            "listed_missing_on_disk": sorted(set(manifest["file_hashes"]) - actual),
            "on_disk_not_listed": sorted(actual - set(manifest["file_hashes"])),
        }
        manifest["package_completed"] = bool(recon_ok)
        manifest["qualification"] = "complete" if recon_ok else "reconciliation_failed"
        manifest["exit_code"] = 0 if recon_ok else 2
        (out / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1, allow_nan=False) + "\n")
    except OSError as exc:
        print(f"写盘失败（不置 package_completed）: {exc}", file=sys.stderr)
        return 3

    if not recon_ok:
        print("EXIT 2: 合法集合对账不平（详见 quality.json reconciliation）")
        return 2
    print("EXIT 0: B1 历史描述完成（post_hoc_historical_description；不自动触发任何后续）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
