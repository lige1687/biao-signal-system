#!/usr/bin/env python3
"""研究数据获取/导入 → 快照 → 校验 → 离线复用 的单一命令入口。

本轮：`research-data-provenance-2026-09-10`。

子命令
------
``import``   从已有合法本地文件离线导入（不联网）
``acquire``  按声明预算联网获取（有界；默认关闭，需显式 ``--yes-network``）
``verify``   完全离线读回快照并重新校验
``diff``     比较两次快照，区分历史修订与仅追加
``bind``     把本批数据绑定到精确 ``id@version`` 并如实判断能否直接满足

输出目录必须全新；已存在则顺延 ``-NN``，绝不覆盖。
本脚本只读取冻结输入，不写生产缓存、不运行账户、不做收益回测。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.dont_write_bytecode = True

from lei_signal.research import data_quality as q  # noqa: E402
from lei_signal.research.data_snapshot import (  # noqa: E402
    FetchBudget,
    RequestSpec,
    acquire_prices,
    bind_definitions,
    diff_snapshots,
    import_prices,
    load_snapshot,
)

STUDY = "research-data-provenance-2026-09-10"
DEFAULT_OUT = ROOT / "docs/experiments/raw" / STUDY

#: 本轮协议声明的联网预算（见 protocol.json:network_budget）。
NETWORK_BUDGET = FetchBudget(
    max_instruments=2,
    max_trading_days=60,
    max_requests=10,
    timeout_seconds=15.0,
    max_retries=2,
)


def _dump(path: Path, obj) -> None:
    path.write_text(
        json.dumps(obj, indent=1, ensure_ascii=False, default=str), encoding="utf-8"
    )


def _run_quality(frames, snapshot, *, warmup_rows, actions_path):
    basis = snapshot["semantics"]["price_basis"]
    calendar_authority = snapshot["semantics"]["trading_calendar"]["authority"]
    requested = {
        i["instrument_id"]: i["requested_trading_days"]
        for i in snapshot["instruments"]
        if i["requested_trading_days"]
    }
    price_report = q.check_prices(
        frames,
        declared_basis=basis,
        calendar_authority=calendar_authority,
        requested_days=requested or None,
        warmup_rows=warmup_rows,
    )
    reports = [price_report]
    if actions_path:
        payload = json.loads(Path(actions_path).read_text(encoding="utf-8"))
        actions = payload.get("events", payload) if isinstance(payload, dict) else payload
        reports.append(
            q.check_actions(actions, declared_symbols=list(frames))
        )
    return q.merge_reports(*reports) if len(reports) > 1 else price_report


def cmd_import(args) -> int:
    result = import_prices(
        args.csv,
        source_id=args.source_id,
        out_dir=Path(args.out),
        instrument_ids=args.symbols or None,
    )
    report = _run_quality(
        result.frames,
        result.snapshot,
        warmup_rows=args.warmup_rows,
        actions_path=args.actions,
    )
    _dump(result.directory / "quality-report.json", report.to_dict())
    print(f"snapshot: {result.directory}")
    print(f"instruments: {result.instruments}")
    for v in report.verdicts:
        print(f"  {v.use:16s} {v.verdict}")
    return 0


def cmd_acquire(args) -> int:
    if not args.yes_network:
        print(
            "联网分支默认关闭。确认预算后加 --yes-network："
            f"最多 {NETWORK_BUDGET.max_instruments} 只、"
            f"{NETWORK_BUDGET.max_trading_days} 个交易日、"
            f"{NETWORK_BUDGET.max_requests} 次请求",
            file=sys.stderr,
        )
        return 2
    specs = [
        RequestSpec(
            source_id="sina_getKLineData", instrument_id=s, trading_days=args.days
        )
        for s in args.symbols
    ]
    result = acquire_prices(specs, budget=NETWORK_BUDGET, out_dir=Path(args.out))
    report = _run_quality(
        result.frames,
        result.snapshot,
        warmup_rows=args.warmup_rows,
        actions_path=args.actions,
    )
    _dump(result.directory / "quality-report.json", report.to_dict())
    print(f"snapshot: {result.directory}")
    print(f"requests used: {result.snapshot['request']['requests_used']}")
    for v in report.verdicts:
        print(f"  {v.use:16s} {v.verdict}")
    return 0


def cmd_verify(args) -> int:
    loaded = load_snapshot(args.snapshot)
    print(f"verified: {loaded.verified}")
    if not loaded.verified:
        print(f"hash mismatches: {loaded.hash_mismatches}", file=sys.stderr)
        return 1
    report = _run_quality(
        loaded.frames,
        loaded.snapshot,
        warmup_rows=args.warmup_rows,
        actions_path=args.actions,
    )
    for v in report.verdicts:
        print(f"  {v.use:16s} {v.verdict}")
    return 0


def cmd_diff(args) -> int:
    result = diff_snapshots(args.old, args.new)
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return 0


def cmd_bind(args) -> int:
    from lei_signal.research import definitions as d

    registry = d.load_registry()
    result = bind_definitions(
        registry=registry, refs=args.refs, purpose=args.purpose or None
    )
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    common_quality = {
        "--warmup-rows": dict(
            type=int, default=None, dest="warmup_rows",
            help="预热所需的自身有效报价条数（混合池月选资格为 273）",
        ),
        "--actions": dict(default=None, help="normalized-actions.json 路径（可选）"),
    }

    imp = sub.add_parser("import", help="从已有本地文件离线导入")
    imp.add_argument("--csv", required=True)
    imp.add_argument("--out", default=str(DEFAULT_OUT / "import"))
    imp.add_argument("--symbols", nargs="*", default=None)
    imp.add_argument("--source-id", default="frozen_mixed_prices", dest="source_id")
    for flag, kw in common_quality.items():
        imp.add_argument(flag, **kw)
    imp.set_defaults(func=cmd_import)

    acq = sub.add_parser("acquire", help="按预算联网获取（需显式确认）")
    acq.add_argument("--symbols", nargs="+", required=True)
    acq.add_argument("--days", type=int, default=60)
    acq.add_argument("--out", default=str(DEFAULT_OUT / "acquire"))
    acq.add_argument("--yes-network", action="store_true", dest="yes_network")
    for flag, kw in common_quality.items():
        acq.add_argument(flag, **kw)
    acq.set_defaults(func=cmd_acquire)

    ver = sub.add_parser("verify", help="离线读回并重新校验")
    ver.add_argument("--snapshot", required=True)
    for flag, kw in common_quality.items():
        ver.add_argument(flag, **kw)
    ver.set_defaults(func=cmd_verify)

    dif = sub.add_parser("diff", help="比较两次快照")
    dif.add_argument("--old", required=True)
    dif.add_argument("--new", required=True)
    dif.set_defaults(func=cmd_diff)

    bnd = sub.add_parser("bind", help="绑定到精确 id@version")
    bnd.add_argument("--refs", nargs="+", required=True)
    bnd.add_argument("--purpose", default=None)
    bnd.set_defaults(func=cmd_bind)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
