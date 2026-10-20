#!/usr/bin/env python3
"""B200×510300 受限历史描述：只读一次性 CLI（synthetic_test / restricted_historical）。

用法：
    python3 run_breadth.py --protocol <freeze/v1.0.0/protocol-v1.0.0.json> \
        --output <新目录> [--mode synthetic_test --input-dir <合成夹具目录>]

- 真实分支（restricted_historical）只消费协议白名单内的四份冻结输入，
  不支持任意目录或多标的；--input-dir 在真实分支被拒绝。
- 协议身份常量与实际算法逐项核对 + 实际 import 闭包哈希核对，缺一拒绝（退出 3）。
- 资料结构/内容不满足合同 → 退出 2，不做统计；异常失败非 0。
- 输出包 manifest 最后写；写盘失败不得留下成功 manifest。
- 数据质量固定 restricted：available_at=null、历史可得性未核验、价格逐列来源
  未核验；不因任何通过检查而升级为“合格”。
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve()
REPO_ROOT = _HERE.parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from lei_signal.research import breadth_description as bd  # noqa: E402
from lei_signal.research import breadth_description_contract as contract  # noqa: E402
from lei_signal.research.trading_calendar import TradingCalendar  # noqa: E402

AGENT_MODEL = "GLM-5.3-Flash"
AGENT_NAME = "ZCode"
DELEGATED_JOB_ID = "da7dabfc-ab2c-4cc1-9686-0c7c0a538a9b"


def _write_file(target: Path, data: str) -> None:
    """单一写盘入口（测试在此注入写盘失败）。"""
    target.write_text(data, encoding="utf-8")


def _strict_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1, allow_nan=False)


def _reject(out: Path, payload: dict) -> None:
    with contextlib.suppress(OSError):
        _write_file(out / "rejection.json", _strict_json(payload))


def _load_breadth(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    if "date" not in df.columns:
        df = df.reset_index()
    if "date" not in df.columns:
        raise contract.DataError(f"breadth parquet has no date column: {path}")
    df["date"] = [pd.Timestamp(v).strftime("%Y-%m-%d") for v in df["date"]]
    return df


def _load_prices(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"date": str}, keep_default_na=False)
    df["close"] = pd.to_numeric(df["close"], errors="raise")
    return df


def _load_observations(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df["main"] = pd.to_numeric(df["main"].replace("", np.nan), errors="raise")
    return df


def _load_inputs(mode: str, input_dir: str | None):
    if mode == "restricted_historical":
        loaded = {}
        for name, required in contract.REQUIRED_INPUTS.items():
            path = REPO_ROOT / required["path"]
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != required["sha256"]:
                raise contract.IdentityError(f"frozen input hash mismatch on disk: {name}")
            loaded[name] = path
        breadth = _load_breadth(loaded["breadth_csi300.parquet"])
        prices = _load_prices(loaded["prices.csv"])
        observations = _load_observations(loaded["observations.csv"])
        calendar_payload = json.loads(loaded["calendar.json"].read_text(encoding="utf-8"))
        return breadth, prices, observations, calendar_payload
    if not input_dir:
        raise contract.IdentityError("synthetic_test requires --input-dir")
    base = Path(input_dir)
    breadth = _load_breadth(base / "breadth_csi300.parquet")
    prices = _load_prices(base / "prices.csv")
    observations = _load_observations(base / "observations.csv")
    calendar_payload = json.loads((base / "calendar.json").read_text(encoding="utf-8"))
    return breadth, prices, observations, calendar_payload


def _git_head() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _report_md(summary: dict, overlap: dict, meta: dict) -> str:
    full = summary["full"]
    rank = full["rank"]
    rho = rank["time_series_spearman"]
    rho_text = "无法计算（样本不足或常数列）" if rho is None else f"{rho:+.6f}"
    lines = [
        "# B200 × 510300 首轮受限历史描述（自动生成）",
        "",
        f"- 用途：{contract.USE}（受限事后描述；不是预测，不是收益结论）。",
        f"- 观察轴：{contract.EVALUATION_START} → {contract.EVALUATION_END}，"
        f"全部交易日 {full['n_all']} 天；纳入统计 {full['n_included']} 天。",
        "- 主指标：时间序列名次相关（两列各自按并列平均名次排名后再算相关性）。",
        f"- 全期名次相关：{rho_text}（n={rank['n']}，原因={rank['reason']}）。",
        "- 大白话：正值表示本快照里宽度较高日期的随后涨幅也倾向较高，负值方向相反；"
        "这不等于涨幅增加了多少，也不是交易收益。",
        "",
        "| 年份 | 全部天数 | 纳入 | 名次相关 | 原因 |",
        "|---|---|---|---|---|",
    ]
    for year in contract.STATISTICS["years"]:
        row = summary["years"][str(year)]
        r = row["rank"]
        value = "—" if r["time_series_spearman"] is None else f"{r['time_series_spearman']:+.6f}"
        lines.append(
            f"| {year} | {row['n_all']} | {row['n_included']} | {value} | {r['reason']} |"
        )
    lines += [
        "",
        f"重叠对账：{overlap['included_pairs']} 条合法配对共引用 "
        f"{overlap['total_interval_references']} 段相邻价格区间，唯一区间 "
        f"{overlap['unique_intervals']} 段；相邻观察共享段数直方图 "
        f"{overlap['consecutive_shared_histogram']}。",
        "",
        "限制：目标区间互相重叠，不构成多次独立证据；本轮不算显著性、不排除过拟合；"
        "源数据已被旧研究观察，不是全新未知验证资料。数据质量固定 restricted。",
        "",
        f"输入快照：{meta['snapshot_note']}",
    ]
    return "\n".join(lines) + "\n"


def _package_files(pairs, summary, overlap, protocol, protocol_bytes: bytes, mode: str,
                   pairs_meta: dict) -> dict[str, str]:
    quality = {
        **contract.QUALITY,
        "notes": [
            "qualification 固定 restricted，不因检查通过而升级。",
            "宽度序列与价格快照的历史到达时间未知，不补造 available_at。",
            "价格逐列来源未核验（unverified_per_column）。",
        ],
    }
    environment = {
        "python": sys.version.split()[0],
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "platform": platform.platform(),
        "agent": AGENT_NAME,
        "model": AGENT_MODEL,
        "delegated_job_id": DELEGATED_JOB_ID,
        "git_head": _git_head(),
        "mode": mode,
        "run_finished_at": datetime.now(UTC).isoformat(),
    }
    files = {
        "pairs.csv": pairs.to_csv(index=False, na_rep=""),
        "pairs.meta.json": _strict_json(pairs_meta),
        "summary.json": _strict_json(summary),
        "overlap.json": _strict_json(overlap),
        "quality.json": _strict_json(quality),
        "report.md": _report_md(summary, overlap, pairs_meta),
        "protocol.source.json": protocol_bytes.decode("utf-8"),
        "environment.json": _strict_json(environment),
    }
    return files


def _check_pending(files: dict[str, str]) -> None:
    missing = [name for name in contract.PACKAGE_FILES if name != "manifest.json"
               and name not in files]
    if missing:
        raise contract.DataError(f"package files missing before manifest: {missing}")
    for name in ("pairs.meta.json", "summary.json", "overlap.json", "quality.json",
                 "environment.json"):
        json.loads(files[name], parse_constant=_reject_constant)


def _reject_constant(token: str):
    raise ValueError(f"non-strict JSON constant {token!r}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", choices=list(contract.MODES), default=None)
    parser.add_argument("--input-dir", default=None)
    args = parser.parse_args(argv)

    try:
        out = contract.ensure_fresh_output_dir(args.output)
    except contract.IdentityError as exc:
        print(f"identity error: {exc}", file=sys.stderr)
        return 3
    out.mkdir(parents=True)

    protocol_path = Path(args.protocol)
    try:
        protocol_bytes = protocol_path.read_bytes()
        protocol = json.loads(protocol_bytes)
    except (OSError, json.JSONDecodeError) as exc:
        _reject(out, {"stage": "protocol_load", "errors": [str(exc)]})
        return 3

    mode = args.mode or protocol.get("mode")
    errors = contract.validate_protocol(protocol, mode=mode, protocol_path=protocol_path)
    if args.input_dir and mode == "restricted_historical":
        errors.append("--input-dir is not allowed in restricted_historical mode")
    if errors:
        _reject(out, {"stage": "protocol_validate", "errors": errors})
        return 3

    closure = contract.compute_import_closure(_HERE)
    code_errors = contract.verify_code_manifest(closure, protocol["code"])
    if code_errors:
        _reject(out, {"stage": "code_manifest", "errors": code_errors})
        return 3

    try:
        breadth, prices, observations, calendar_payload = _load_inputs(mode, args.input_dir)
    except (contract.IdentityError, contract.DataError, OSError,
            json.JSONDecodeError, ValueError, TypeError) as exc:
        _reject(out, {"stage": "input_load", "errors": [str(exc)]})
        print(f"input load failed: {exc}", file=sys.stderr)
        return 3 if isinstance(exc, contract.IdentityError) else 2

    try:
        calendar = TradingCalendar(calendar_payload)
        coverage = calendar.coverage(
            contract.CALENDAR_VERIFY_START, contract.CALENDAR_VERIFY_END)
        if not coverage.complete:
            raise contract.DataError(
                "calendar coverage incomplete over verify window: "
                f"missing={coverage.missing_months}, "
                f"day_incomplete={coverage.day_incomplete_months}"
            )
        sessions = calendar.trading_days(
            contract.CALENDAR_VERIFY_START, contract.CALENDAR_VERIFY_END)
        pairs = bd.build_pairs(
            breadth, observations, prices, sessions,
            evaluation_start=contract.EVALUATION_START,
            evaluation_end=contract.EVALUATION_END,
            cutoff=contract.CUTOFF,
        )
    except (contract.DataError, ValueError) as exc:
        _reject(out, {"stage": "pairing", "errors": [str(exc)]})
        print(f"pairing rejected: {exc}", file=sys.stderr)
        return 2

    summary = bd.summarize_pairs(pairs, contract.STATISTICS["years"])
    overlap = bd.audit_overlap(pairs, sessions)
    pairs_meta = {
        "family": contract.FAMILY,
        "use": contract.USE,
        "data_mode": mode,
        "object": contract.OBJECT,
        "symbol": contract.SYMBOL,
        "date_window": contract.DATE_WINDOW,
        "target": contract.TARGET,
        "cutoff": contract.CUTOFF,
        "axis_rows": int(len(pairs)),
        "included_rows": int(pairs["included"].sum()),
        "data_cutoff": contract.CUTOFF,
        "observed_at": None,
        "snapshot_fetched_at": None,
        "snapshot_note": (
            "observed_at/snapshot_fetched_at/available_at 均未知，分列且不用文件"
            "时间补造；B1 报告记载价格快照取回于 2026-09-08，本任务未独立验证时刻。"
        ),
        "common_calculate_called": False,
        "consumed_legacy_sequence": True,
        "unit_conversion": contract.UNIT_CONVERSION,
    }
    files = _package_files(pairs, summary, overlap, protocol, protocol_bytes, mode, pairs_meta)
    try:
        _check_pending(files)
        for name, content in files.items():
            _write_file(out / name, content)
        manifest = {
            "schema": contract.SCHEMA,
            "protocol_id": contract.PROTOCOL_ID,
            "protocol_version": contract.PROTOCOL_VERSION,
            "data_mode": mode,
            "package_completed": True,
            "manifest_written_last": True,
            "files": {
                name: {"sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                       "bytes": len(content.encode("utf-8"))}
                for name, content in files.items()
            },
        }
        _write_file(out / "manifest.json", _strict_json(manifest))
    except OSError as exc:
        _reject(out, {"stage": "package_write", "errors": [f"write failure: {exc}"],
                      "package_completed": False})
        print(f"package write failed: {exc}", file=sys.stderr)
        return 2
    print(f"package completed: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
