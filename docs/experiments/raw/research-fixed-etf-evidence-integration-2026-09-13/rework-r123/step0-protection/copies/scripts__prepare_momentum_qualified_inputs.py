#!/usr/bin/env python3
"""派生研究输入快照：为冻结名义价补上真实计算列 economic_index
（fixed-etf-evidence-integration-2026-09-13 Task 4）。

做四件事，全部离线：

1. 核验原动量协议（代码指纹/身份绑定/冻结输入哈希）与证据包
   （qualification_bundle.validate_evidence_bundle；拒绝任何 rejected 记录）；
2. 对固定池每只产品，用冻结名义收盘价 + 冻结行动（经 adapt_company_events）
   重建 economic_index，原 CSV 行与名义列逐字节保留、仅追加新列；
3. 写独立派生 snapshot（克隆原快照的来源/用途/时间语义，附加 derivation
   溯源段；economic_index 明确为事后重建列，available_at 仍为 null，
   historical_reconstruction_only=true 不因补列被清除）；
4. 完全离线读回派生快照（现有加载器逐文件核哈希），bind_definitions 检查
   两个对象字段，并把动量 772 个正式键与 run-04 逐一比对（独立既有基准）。

退出码：0 完成；2 质量限制（证据包被拒/完整性失败）；3 参数/输入/运行失败。
manifest 最后写出；写盘失败保留 FAILED.txt。
"""
from __future__ import annotations

import contextlib
import csv
import hashlib
import io
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.dont_write_bytecode = True

from run_momentum_research_prototype import (  # noqa: E402
    EXIT_FAILED,
    EXIT_OK,
    EXIT_REJECTED,
    _identity_map,
    _load_protocol,
    _OfflineGuard,
    _Parser,
    _verify_protocol_codes,
    _verify_protocol_identity,
    _verify_protocol_inputs,
)

from lei_signal.research import momentum_prototype as mp  # noqa: E402
from lei_signal.research.data_snapshot import (  # noqa: E402
    bind_definitions,
    load_snapshot,
)
from lei_signal.research.qualification_bundle import (  # noqa: E402
    validate_evidence_bundle,
)


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class QualityReject(RuntimeError):
    """质量限制导致拒绝（退出 2）。"""


def _fail_marker(out: Path, stage: str, exc: Exception) -> int:
    with contextlib.suppress(OSError):
        out.mkdir(parents=True, exist_ok=True)
        (out / "FAILED.txt").write_text(
            f"输出阶段失败（{stage}）：{type(exc).__name__}: {exc}\n"
            "部分产物与缺失的 manifest.json 均不构成本次完成证明。\n",
            encoding="utf-8",
        )
    print(f"输出阶段失败（{stage}）：{type(exc).__name__}: {exc}", file=sys.stderr)
    return EXIT_FAILED


def _append_column(csv_text: str, column: str, values: list[str]) -> str:
    """在原 CSV 文本上追加一列；原行原列逐字节保留（仅换行内追加）。"""
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    rows[0].append(column)
    assert len(rows) - 1 == len(values), (
        f"行数不一致：CSV {len(rows)-1} 行 vs 计算列 {len(values)} 行")
    for row, v in zip(rows[1:], values, strict=True):
        row.append(v)
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerows(rows)
    return buf.getvalue()


def main(argv=None) -> int:
    parser = _Parser(description=__doc__)
    parser.add_argument("--protocol", required=True,
                        help="原动量研究协议 JSON（v1.0.5）")
    parser.add_argument("--evidence-bundle", required=True,
                        help="Task 2 证据包 JSON")
    parser.add_argument("--run04-values", required=True,
                        help="run-04 values.csv（独立既有算术基准，只读）")
    parser.add_argument("--out", required=True, help="输出目录（必须不存在）")
    args = parser.parse_args(argv)

    out = Path(args.out)
    if out.exists():
        print(f"输出目录已存在，拒绝覆盖：{out}", file=sys.stderr)
        return EXIT_FAILED

    guard = _OfflineGuard()
    try:
        guard.install()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_FAILED

    try:
        protocol, protocol_sha = _load_protocol(Path(args.protocol))
        _verify_protocol_codes(protocol)
        _verify_protocol_identity(protocol)
        input_paths = _verify_protocol_inputs(protocol)

        # ---- 证据包校验（真实包，禁止 rejected 记录） ----
        bundle_path = Path(args.evidence_bundle)
        if not bundle_path.is_file():
            raise FileNotFoundError(f"证据包不存在：{bundle_path}")
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        if bundle.get("synthetic") is not False:
            raise QualityReject("证据包必须为真实包（synthetic=false）")
        universe = set()

        for sym in protocol["inputs"].get("pool_symbols", []) or []:
            universe.add(sym)
        if not universe:
            # 固定池来自原快照清单
            snapshot_meta = json.loads(
                (Path(input_paths["snapshot_dir"]["path"]) / "snapshot.json")
                .read_text(encoding="utf-8"))
            universe = {item["instrument_id"]
                        for item in snapshot_meta["instruments"]}
        bundle_result = validate_evidence_bundle(
            bundle, root=ROOT, universe=universe)
        if bundle_result["rejected"]:
            raise QualityReject(
                "证据包存在被拒记录，不得进入派生："
                + "; ".join(
                    f"{r['record_id']}: {r['reasons'][0]}"
                    for r in bundle_result["rejected"][:10]))

        # ---- 原快照与行动 ----
        loaded = load_snapshot(input_paths["snapshot_dir"]["path"])
        if not loaded.verified:
            raise QualityReject("原快照完整性核验失败")
        actions = json.loads(
            Path(input_paths["actions"]["path"]).read_text(encoding="utf-8")
        )["events"]
        canon, identity_errors = _identity_map(loaded.frames.keys(), actions)
        fatal_identity = [e for e in identity_errors if e.get("scope") == "action"]
        if fatal_identity:
            raise QualityReject(
                "行动身份无法解析：" + "; ".join(
                    f"{e.get('symbol')}: {e['error']}" for e in fatal_identity))
        by_symbol: dict[str, list[dict]] = {s: [] for s in loaded.frames}
        for ev in actions:
            target = canon.get(ev.get("symbol"))
            if target in by_symbol:
                by_symbol[target].append(ev)

        # ---- 逐产品派生 CSV ----
        derived_dir = out / "snapshot"
        (derived_dir / "normalized").mkdir(parents=True)
        original_meta = json.loads(
            (Path(input_paths["snapshot_dir"]["path"]) / "snapshot.json")
            .read_text(encoding="utf-8"))
        items = []
        econ_stats: dict[str, dict] = {}
        run04_values: dict[tuple[str, str], float] = {}
        with open(args.run04_values) as f:
            for row in csv.DictReader(f):
                run04_values[(row["symbol"], row["date"])] = float(row["momentum"])

        momentum_key_mismatch = 0
        momentum_keys_checked = 0

        for meta in original_meta["instruments"]:
            symbol = meta["instrument_id"]
            frame = loaded.frames[symbol]
            close = frame["close"].astype(float)
            close = close[close > 0].dropna()
            adapted = mp.adapt_company_events(by_symbol[symbol])
            econ, unknown = mp.reconstruct_symbol_economic_index(close, adapted)
            # 原始 CSV 文本按原快照引用读回，逐字节保留原列
            orig_csv_rel = meta["normalized"]["path"]
            orig_csv_path = (
                Path(input_paths["snapshot_dir"]["path"]) / orig_csv_rel)
            csv_text = orig_csv_path.read_text(encoding="utf-8")
            lines = csv_text.splitlines()
            header = lines[0].split(",")
            date_i = header.index("date")
            econ_by_date = {
                pd.Timestamp(d).strftime("%Y-%m-%d"): repr(float(v))
                for d, v in econ.items()
            }
            new_lines = [",".join(lines[0].split(",") + ["economic_index"])]
            missing_here = 0
            for line in lines[1:]:
                d = line.split(",")[date_i]
                val = econ_by_date.get(d)
                if val is None:
                    missing_here += 1
                    val = ""
                new_lines.append(line + "," + val)
            derived_rel = f"normalized/{symbol}.csv"
            derived_csv = derived_dir / derived_rel
            derived_csv.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            items.append({**meta, "normalized": {
                "path": derived_rel, "sha256": _sha(derived_csv)}})
            econ_stats[symbol] = {
                "rows": len(lines) - 1,
                "economic_index_filled": len(lines) - 1 - missing_here,
                "economic_index_blank": missing_here,
                "unknown_available_at_events": list(unknown),
            }

            # ---- 算术核验：动量正式键 vs run-04 ----
            momentum = mp.compute_momentum(econ)
            for (sym, date_str), expected in run04_values.items():
                if sym != symbol:
                    continue
                key = pd.Timestamp(date_str)
                if key not in momentum.index:
                    continue
                got = float(momentum.loc[key])
                momentum_keys_checked += 1
                if abs(got - expected) > 1e-12 * max(1.0, abs(expected)):
                    momentum_key_mismatch += 1

        # ---- 派生 snapshot.json ----
        derived_snapshot = {
            "schema_version": original_meta["schema_version"],
            "transform_version": original_meta["transform_version"],
            "mode": original_meta["mode"],
            "protocol_id": original_meta.get("protocol_id"),
            "derived_from": {
                "original_snapshot": input_paths["snapshot_dir"]["path"],
                "original_snapshot_json_sha256":
                    input_paths["snapshot_dir"]["sha256"],
                "actions_sha256": input_paths["actions"]["sha256"],
                "evidence_bundle": {
                    "path": str(bundle_path), "sha256": _sha(bundle_path)},
                "momentum_protocol": {"path": args.protocol,
                                      "sha256": protocol_sha},
                "transform": ("economic_index = reconstructed_economic_index("
                              "名义close, adapt_company_events(冻结行动))；"
                              "基准为原首次有效报价 I=1；名义 OHLCV 与日期行"
                              "逐字节保留，缺失保持缺失"),
                "derived_at": datetime.now(UTC).isoformat(),
                "derived_at_note": "本次派生时刻，不是数据的对外可用时刻",
            },
            "timing": {**original_meta.get("timing", {}),
                       "derived_at": datetime.now(UTC).isoformat()},
            "instruments": items,
            "market_data_refs": original_meta.get("market_data_refs", {}),
            "semantics": {
                **original_meta["semantics"],
                "fields": {
                    **original_meta["semantics"]["fields"],
                    "economic_index": (
                        "事后重建经济指数（名义价+已生效分红/拆分连接，首值 I=1）；"
                        "historical_reconstruction_only=true，不得当作历史可知输入"),
                },
                "historical_reconstruction_only": True,
                "available_at_note": "未知 available_at 保持 null，不因补列被清除",
            },
            "code_identity": original_meta.get("code_identity", {}),
            "known_gaps": original_meta.get("known_gaps", []),
            "uses": original_meta.get("uses", []),
            "uses_basis": original_meta.get("uses_basis", {}),
            "not_for": original_meta.get("not_for", []),
            "authorization": original_meta.get("authorization", {}),
        }
        (derived_dir / "snapshot.json").write_text(
            json.dumps(derived_snapshot, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")

        # ---- 离线读回 + 字段绑定 + 算术结论 ----
        reloaded = load_snapshot(derived_dir)
        if not reloaded.verified:
            raise QualityReject(
                "派生快照读回核验失败：" + ", ".join(reloaded.hash_mismatches[:5]))
        registry_path = input_paths["registry"]["path"]
        from lei_signal.research import definitions as d

        registry = d.load_registry(registry_path)
        bindings = bind_definitions(
            registry=registry,
            refs=[protocol["objects"]["primary"], protocol["objects"]["dependency"]],
            snapshot=reloaded.snapshot, purpose=None,
        )["bindings"]
        binding_summary = {
            ref: {"directly_satisfiable": bindings[ref].get("directly_satisfiable"),
                  "missing_fields": bindings[ref].get("missing_fields")}
            for ref in bindings
        }

        result = {
            "evidence_bundle": {
                "validated": len(bundle_result["validated"]),
                "unresolved": len(bundle_result["unresolved"]),
                "conflicts": len(bundle_result["conflicts"]),
            },
            "econ_stats": econ_stats,
            "binding": binding_summary,
            "momentum_key_check": {
                "checked": momentum_keys_checked,
                "mismatch": momentum_key_mismatch,
                "run04_unique_keys": len(run04_values),
                "tolerance": "atol=rtol=1e-12",
            },
            "observation_cutoff_assumption": (
                "观察/决策截点 15:00 为按收盘设置的保守测试假设，"
                "不是已证实的数据到达时间或实盘决策时刻"),
        }
        if momentum_key_mismatch:
            raise QualityReject(
                f"动量正式键与 run-04 不一致 {momentum_key_mismatch} 处，拒绝交付")

        files = [("result.json", json.dumps(result, indent=1,
                                            ensure_ascii=False) + "\n")]
        snapshot_files = {
            str(p.relative_to(out)): _sha(p)
            for p in sorted(derived_dir.rglob("*")) if p.is_file()
        }
        manifest_payload = {
            "schema_version": "fixed-etf-derived-snapshot-manifest/1.0",
            "generated_at": datetime.now(UTC).isoformat(),
            "protocol": {"path": args.protocol, "sha256": protocol_sha,
                         "protocol_id": protocol["protocol_id"]},
            "offline_guard": guard.self_check,
            "result": result,
            "outputs": {
                **{name: hashlib.sha256(t.encode("utf-8")).hexdigest()
                   for name, t in files},
                **snapshot_files,
            },
        }
        manifest_text = json.dumps(manifest_payload, indent=1,
                                   ensure_ascii=False) + "\n"
        out.mkdir(parents=True, exist_ok=True)
        for name, text in files:
            (out / name).write_text(text, encoding="utf-8")
        (out / "manifest.json").write_text(manifest_text, encoding="utf-8")
        print(f"derived snapshot: {derived_dir}")
        print(f"binding: {json.dumps(binding_summary, ensure_ascii=False)}")
        print(f"momentum keys: checked={momentum_keys_checked} "
              f"mismatch={momentum_key_mismatch}")
        return EXIT_OK
    except QualityReject as exc:
        print(f"质量限制拒绝：{exc}", file=sys.stderr)
        return EXIT_REJECTED
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        print(f"输入/运行失败：{type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_FAILED
    except OSError as exc:
        return _fail_marker(out, "write", exc)
    except Exception as exc:  # noqa: BLE001
        print(f"运行失败：{type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_FAILED


if __name__ == "__main__":
    raise SystemExit(main())
