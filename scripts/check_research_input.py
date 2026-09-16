#!/usr/bin/env python3
"""研究输入离线检查命令入口（research-input-preflight-2026-09-13）。

运行一次，回答：是哪批数据、能用于什么、缺什么、哪些旧程序尚未接入。

**完全离线**，无 acquire 分支、无参数优化、无数据修复、无账户路径。

退出码：
- 0：请求的检查满足（仅表示本次已实现的输入检查满足，
  不等于公式实现、历史可得时点、因子有效或交易授权）；
- 2：检查完成但请求被拒——**这是有价值的检查结果，不是崩溃**；
- 3：输入 / 参数 / 解析或运行失败（不留下成功 manifest）。

输出目录**必须不存在**：已存在即拒绝并说明，不覆盖、不偷偷换目录；
调用者显式选择新的 attempt-NN。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.dont_write_bytecode = True

from lei_signal.research.input_preflight import USES, inspect_input  # noqa: E402

EXIT_OK = 0
EXIT_REJECTED = 2
EXIT_FAILED = 3


class _Parser(argparse.ArgumentParser):
    """参数错误属输入错误（退出 3），不与"正常检查被拒"(2) 混淆。"""

    def error(self, message):  # noqa: D102
        self.print_usage(sys.stderr)
        print(f"{self.prog}: error: {message}", file=sys.stderr)
        raise SystemExit(EXIT_FAILED)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: Path, obj) -> None:
    path.write_text(
        json.dumps(obj, indent=1, ensure_ascii=False, default=str), encoding="utf-8"
    )


def _render_markdown(report: dict) -> str:
    """只从同一个 dict 生成，不重新猜测，也不手抄成更乐观的结论。"""
    r = report
    lines = [
        "# 研究输入检查结果",
        "",
        f"- 快照：`{r['request']['snapshot_dir']}`",
        f"- 用途请求：**{r['request']['use']}**；refs：{r['request']['refs'] or '（无）'}",
        f"- 评价期：{r['request']['evaluation_start']} ~ {r['request']['evaluation_end']}",
        f"- **request_satisfied = {r['request_satisfied']}**",
        f"- calculation_run = {r['calculation_run']}；"
        f"production_authorized = {r['production_authorized']}",
        "",
        "## 完整性",
        "",
        f"- verified：{r['integrity']['verified']}"
        + (
            f"（不一致：{r['integrity']['hash_mismatches']}）"
            if r["integrity"]["hash_mismatches"]
            else ""
        ),
        f"- 标的：{len(r['integrity']['instruments'])} 只；"
        f"行数：{r['integrity']['rows']}；"
        f"日期：{r['integrity']['first_date']} ~ {r['integrity']['last_date']}",
        "",
        "## 六种用途",
        "",
        "| 用途 | 质量裁决 | 产物声明 | 默认接受 | 原因 |",
        "|---|---|---|---|---|",
    ]
    for u in USES:
        du = r["data_uses"][u]
        lines.append(
            f"| {u} | {du['verdict']} | {du['declared']} | "
            f"{'✅' if du['default_accepted'] else '❌'} | {du['reason']} |"
        )
    # 缺口的具体产品与日期在 findings 里；表格只给定位指引，不重复铺长列表
    gap_findings = [
        f for f in r.get("findings", [])
        if f["code"] in ("product_internal_gap", "starts_after_window",
                         "events_passed_as_actions", "quote_on_closed_day",
                         "quote_on_unknown_calendar_day")
    ]
    if gap_findings:
        lines += ["", "## 缺口定位（逐项见 preflight.json 的 findings）", "",
                  "| 检查项 | 产品 | 说明 |", "|---|---|---|"]
        for f in gap_findings[:12]:
            lines.append(
                f"| {f['code']} | {f.get('instrument') or '—'} | {f['message'][:80]} |"
            )
        if len(gap_findings) > 12:
            lines.append(f"| … | | 另有 {len(gap_findings) - 12} 条，"
                         "见 preflight.json |")
    if r["objects"]:
        lines += ["", "## 对象检查", "",
                  "| 对象 | 已解析 | 允许该用途 | 直接可满足 | 缺字段/原因 |",
                  "|---|---|---|---|---|"]
        for ref, obj in r["objects"].items():
            reason = (
                obj.get("error")
                or obj.get("purpose_error")
                or (
                    f"blocked_by={obj['blocked_by']}"
                    if obj.get("blocked_by")
                    else obj.get("missing_fields")
                )
            )
            lines.append(
                f"| `{ref}` | {obj.get('resolved')} | {obj.get('purpose_allowed')} | "
                f"{obj.get('directly_satisfiable')} | {reason} |"
            )
        lines.append(
            "> 完整解析卡与递归依赖见 manifest.json 的 "
            "`objects.<ref>.resolved_cards_closure`。"
        )
    if r["errors"]:
        lines += ["", "## 失败", ""]
        lines += [f"- `{e['stage']}`：{e['error']}" for e in r["errors"]]
    if r["limitations"]:
        lines += ["", "## 限制与未覆盖", ""]
        lines += [f"- {x}" for x in r["limitations"]]
    lines += [
        "",
        "> request_satisfied=true 仅表示本次已实现的输入检查满足；"
        "不等于公式实现、历史可得时点、因子有效或交易授权。",
    ]
    return "\n".join(lines) + "\n"


def _code_hashes() -> dict:
    files = {
        "input_preflight": ROOT / "src/lei_signal/research/input_preflight.py",
        "check_research_input": ROOT / "scripts/check_research_input.py",
        "data_quality": ROOT / "src/lei_signal/research/data_quality.py",
        "data_snapshot": ROOT / "src/lei_signal/research/data_snapshot.py",
        "trading_calendar": ROOT / "src/lei_signal/research/trading_calendar.py",
        "definitions": ROOT / "src/lei_signal/research/definitions.py",
        "factor_runtime": ROOT / "src/lei_signal/research/factor_runtime.py",
    }
    return {k: _sha256_file(v) for k, v in files.items() if v.exists()}


def _input_hashes(request: dict) -> dict:
    out = {}
    snap = Path(request["snapshot_dir"]) / "snapshot.json"
    for key, p in {
        "snapshot_json": snap,
        "calendar": request["calendar_path"],
        "publication": request["publication_path"],
        "actions": request["actions_path"],
        "registry": request["registry_path"],
    }.items():
        if p and Path(p).exists():
            out[key] = _sha256_file(Path(p))
    return out


def main(argv=None) -> int:
    parser = _Parser(description=__doc__)
    parser.add_argument("--snapshot", required=True, help="快照目录（含 snapshot.json）")
    parser.add_argument("--calendar", default=None)
    parser.add_argument("--publication", default=None)
    parser.add_argument("--actions", default=None)
    parser.add_argument("--registry", default=None)
    parser.add_argument("--start", required=True, dest="start")
    parser.add_argument("--end", required=True, dest="end")
    parser.add_argument("--use", required=True, choices=list(USES))
    parser.add_argument("--refs", nargs="*", default=[],
                        help="精确 id@version，零到多个")
    parser.add_argument("--out", required=True, help="输出目录（必须不存在）")
    parser.add_argument("--protocol", default=None,
                        help="本任务冻结协议/基线路径（可选，绑定进 manifest）")
    args = parser.parse_args(argv)

    out = Path(args.out)
    if out.exists():
        print(
            f"输出目录已存在，拒绝覆盖：{out}\n请显式选择新目录（如 attempt-NN+1）。",
            file=sys.stderr,
        )
        return EXIT_FAILED

    report = inspect_input(
        snapshot_dir=args.snapshot,
        calendar_path=args.calendar,
        publication_path=args.publication,
        actions_path=args.actions,
        registry_path=args.registry,
        refs=tuple(args.refs),
        use=args.use,
        evaluation_start=args.start,
        evaluation_end=args.end,
    )

    try:
        out.mkdir(parents=True)
    except OSError as exc:
        print(f"输出目录不可写：{exc}", file=sys.stderr)
        return EXIT_FAILED
    try:
        _write_json(out / "preflight.json", report)
        (out / "preflight.md").write_text(
            _render_markdown(report), encoding="utf-8"
        )
    except OSError as exc:
        # 能安全记录时保留失败标记；不得留下 request_satisfied 的完整假象
        import contextlib

        with contextlib.suppress(OSError):
            (out / "FAILED.txt").write_text(
                f"输出阶段失败：{type(exc).__name__}: {exc}\n"
                "preflight.json/manifest.json 均不构成本次完成证明。\n",
                encoding="utf-8",
            )
        print(f"输出阶段失败：{type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_FAILED

    if report["errors"]:
        # 输入/解析失败：保留能安全保存的原因，但不留下成功 manifest
        print(
            f"检查未完整运行（{len(report['errors'])} 个失败阶段）；"
            "原因已写入 preflight.json，未生成 manifest。",
            file=sys.stderr,
        )
        return EXIT_FAILED

    spec_files = {
        "principles": ("docs/research/experiment-backtest-principles.md", "v1.1"),
        "definition_standard": ("docs/research/definition-standard.md", "1.1.0"),
        "execution_contract": ("docs/research/ai-execution-contract.md", "1.0.1"),
        "report_template": ("docs/research/experiment-report-template.md", "1.1.0"),
    }
    protocol_binding = None
    if args.protocol:
        pp = Path(args.protocol)
        protocol_error = None
        if not pp.is_file():
            protocol_error = f"协议文件不存在：{pp}"
        else:
            try:
                json.loads(pp.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                protocol_error = f"协议文件不可读或不是合法 JSON：{exc}"
        if protocol_error:
            print(protocol_error, file=sys.stderr)
            return EXIT_FAILED
        protocol_binding = {
            "path": str(pp),
            "sha256": _sha256_file(pp),
        }

    try:
        # 规范/输入/输出哈希读取、manifest 构造与最终写入同处一个失败出口：
        # 任一环 I/O 失败都不得留下"已完成"的假象（部分 manifest 不可被消费方当完成）。
        specs = {}
        for key, (path, version) in spec_files.items():
            p = ROOT / path
            specs[key] = {
                "path": path,
                "version": version,
                "sha256": _sha256_file(p) if p.exists() else None,
            }
        manifest = {
            "schema_version": "research-input-preflight-manifest/1.0",
            "generated_at": datetime.now(UTC).isoformat(),
            "generated_at_note": "这是本次运行时刻，不得当作数据的对外可用时刻",
            "specs": specs,
            "protocol": protocol_binding,
            "code_hashes": _code_hashes(),
            "input_hashes": _input_hashes(report["request"]),
            "input_times": report.get("input_times"),
            "registry": report["registry"],
            "objects": {
                ref: {
                    "contract_digest": obj.get("contract_digest"),
                    "resolved": obj.get("resolved"),
                    "purpose_allowed": obj.get("purpose_allowed"),
                    "directly_satisfiable": obj.get("directly_satisfiable"),
                    "missing_fields": obj.get("missing_fields"),
                    "blocked_by": obj.get("blocked_by"),
                    "binding_reasons": (obj.get("binding") or {}).get("reasons"),
                    "resolved_cards_closure": obj.get("resolved_cards"),
                }
                for ref, obj in report["objects"].items()
            },
            "evaluation": {
                "start": report["request"]["evaluation_start"],
                "end": report["request"]["evaluation_end"],
            },
            "outputs": {
                "preflight_json": _sha256_file(out / "preflight.json"),
                "preflight_md": _sha256_file(out / "preflight.md"),
            },
            "request_satisfied": report["request_satisfied"],
            "calculation_run": False,
            "production_authorized": False,
        }
        _write_json(out / "manifest.json", manifest)
    except OSError as exc:
        import contextlib

        with contextlib.suppress(OSError):
            (out / "FAILED.txt").write_text(
                f"输出阶段失败：{type(exc).__name__}: {exc}\n"
                "preflight.json 与部分 manifest 均不构成本次完成证明。\n",
                encoding="utf-8",
            )
        print(f"输出阶段失败：{type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_FAILED

    print(f"preflight: {out/'preflight.json'}")
    print(f"request_satisfied: {report['request_satisfied']}")
    for u in USES:
        du = report["data_uses"][u]
        mark = "✅" if du["default_accepted"] else "❌"
        print(f"  {u:16s} {mark}  {du['verdict']}")
    if report["objects"]:
        for ref, obj in report["objects"].items():
            print(
                f"  obj {ref}: resolved={obj.get('resolved')} "
                f"purpose={obj.get('purpose_allowed')} "
                f"satisfiable={obj.get('directly_satisfiable')} "
                f"missing={obj.get('missing_fields')}"
            )
    return EXIT_OK if report["request_satisfied"] else EXIT_REJECTED


if __name__ == "__main__":
    raise SystemExit(main())
