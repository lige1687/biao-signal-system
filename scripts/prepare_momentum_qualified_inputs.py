#!/usr/bin/env python3
"""派生研究输入快照：为冻结名义价补上真实计算列 economic_index
（fixed-etf-evidence-integration-2026-09-13 Task 4；R1–R4 返修版）。

做五件事，全部离线：

1. 核验原动量协议（**版本文件**，current 指针拒绝；代码指纹含本派生
   CLI 与 qualification_bundle 两个实际执行文件，删键不能免核；身份绑定/
   冻结输入哈希）；协议必须声明 ``research_evidence``（证据包）与
   ``derived_reference``（参考值文件）的身份，实际传入文件哈希不一致
   即输入错误；证据包经 qualification_bundle 校验（事实绑定/指纹/引用
   原件），任何 rejected 记录即拒绝派生；
2. 对固定池每只产品，用冻结名义收盘价 + 冻结行动（经 adapt_company_events）
   重建 economic_index；非正/缺失收盘价按冻结显式缺失规则排除并**逐产品
   计数留痕**，不静默过滤；原 CSV 行与名义列逐字节保留、仅追加新列；
3. 写独立派生 snapshot（克隆原快照的来源/用途/时间语义，附加 derivation
   溯源段；economic_index 明确为事后重建列，available_at 仍为 null，
   historical_reconstruction_only=true 不因补列被清除）；
4. 完全离线读回派生快照（现有加载器逐文件核哈希），bind_definitions 检查
   两个对象字段；**正式键双向核对（返修 S2）**：从冻结的观察规则/产品/
   合法窗口独立推导"应比对键集合"（不硬编码数量、不拿参考表当基准），
   参考缺键（派生有值而参考无）、越界键、派生无值键、重复键、非有限值
   与值差分别可见，全部为零才算"完整一致"，否则按质量限制拒绝；
5. 协议以**排他创建**冻结进输出目录并读回核哈希；manifest 最后写出；
   写盘失败保留 FAILED.txt。

退出码：0 完成；2 质量限制（证据包被拒/完整性失败/参考值不完整一致）；
3 参数/输入/运行失败。
"""
from __future__ import annotations

import contextlib
import csv
import hashlib
import io
import json
import math
import os
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

# 本入口实际执行的两个任务文件：协议 codes 必须声明并匹配当前哈希，
# 删键不能免核（返修 R4）。
PREPARE_REQUIRED_CODES = frozenset({
    "qualification_bundle", "prepare_momentum_qualified_inputs",
})

PROTOCOL_TEXT = ""  # 冻结副本用：排他写入输出目录（见 _freeze_protocol_copy）


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _finite(value) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        f = float(value)
        return f if math.isfinite(f) else None
    if isinstance(value, str) and value.strip():
        try:
            f = float(value.strip())
        except ValueError:
            return None
        return f if math.isfinite(f) else None
    return None


class QualityReject(RuntimeError):
    """质量限制导致拒绝（退出 2）。"""


class InputIdentityError(RuntimeError):
    """协议声明的输入身份与实际文件不一致（退出 3）。"""


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


def _freeze_protocol_copy(out: Path, protocol_sha: str) -> dict:
    """协议排他冻结进输出目录并读回核哈希；目标已存在即失败（不覆盖）。"""
    target = out / "protocol-frozen.json"
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except FileExistsError as exc:
        raise InputIdentityError(
            f"协议冻结副本已存在，拒绝覆盖：{target}") from exc
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(PROTOCOL_TEXT)
    read_back = _sha(target)
    if read_back != protocol_sha:
        raise InputIdentityError(
            f"协议冻结副本读回哈希不一致：{read_back[:12]}… != "
            f"{protocol_sha[:12]}…")
    return {"path": str(target), "sha256": read_back}


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


def _load_reference_values(path: Path) -> tuple[dict, list, list]:
    """严格解析参考值 CSV：重复键、非有限值分别留痕，不静默覆盖。"""
    seen: dict[tuple[str, str], float | None] = {}
    duplicates: list[dict] = []
    invalid: list[dict] = []
    with open(path) as f:
        for row in csv.DictReader(f):
            key = (row.get("symbol") or "", row.get("date") or "")
            value = _finite(row.get("momentum"))
            if value is None:
                invalid.append({"symbol": key[0], "date": key[1],
                                "raw": row.get("momentum")})
            if key in seen:
                duplicates.append({
                    "symbol": key[0], "date": key[1],
                    "first_value": (repr(seen[key])
                                    if seen[key] is not None else None),
                    "duplicate_raw": row.get("momentum"),
                })
                continue
            seen[key] = value
    values = {k: v for k, v in seen.items() if v is not None}
    return values, duplicates, invalid


def main(argv=None) -> int:
    global PROTOCOL_TEXT
    parser = _Parser(description=__doc__)
    parser.add_argument("--protocol", required=True,
                        help="原动量研究协议版本文件（如 protocol-v1.0.8.json；"
                             "current 指针拒绝）")
    parser.add_argument("--evidence-bundle", required=True,
                        help="任务证据包 JSON（须与协议 research_evidence 声明一致）")
    parser.add_argument("--run04-values", required=True,
                        help="参考值 CSV（须与协议 derived_reference 声明一致）")
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
        protocol_path = Path(args.protocol)
        protocol, protocol_sha = _load_protocol(protocol_path)
        PROTOCOL_TEXT = protocol_path.read_text(encoding="utf-8")
        _verify_protocol_codes(protocol, extra_required=PREPARE_REQUIRED_CODES)
        _verify_protocol_identity(protocol)
        input_paths = _verify_protocol_inputs(protocol)

        # ---- 协议必须声明证据包与参考值身份；实际文件须一致（返修 R4） ----
        ev_declared = protocol.get("research_evidence")
        ref_declared = protocol.get("derived_reference")
        if not (isinstance(ev_declared, dict) and ev_declared.get("sha256")):
            raise InputIdentityError(
                "协议缺少 research_evidence 声明（证据包 path/sha256）")
        if not (isinstance(ref_declared, dict) and ref_declared.get("sha256")):
            raise InputIdentityError(
                "协议缺少 derived_reference 声明（参考值 path/sha256）")
        bundle_path = Path(args.evidence_bundle)
        values_path = Path(args.run04_values)
        for label, declared, actual in (
                ("research_evidence", ev_declared, bundle_path),
                ("derived_reference", ref_declared, values_path)):
            if not actual.is_file():
                raise FileNotFoundError(f"{label} 文件不存在：{actual}")
            actual_sha = _sha(actual)
            if actual_sha != declared.get("sha256"):
                raise InputIdentityError(
                    f"{label} 与协议声明不一致：实际 {actual_sha[:12]}… vs 声明 "
                    f"{str(declared.get('sha256'))[:12]}…；拒绝使用被改动的输入")

        # ---- 排他冻结协议副本（返修 R4）：先于一切派生写盘 ----
        out.mkdir(parents=True)
        frozen = _freeze_protocol_copy(out, protocol_sha)

        # ---- 证据包校验（真实包，禁止 rejected 记录） ----
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

        # ---- 参考值严格解析（返修 R2）：重复/非有限留痕，不静默覆盖 ----
        run04_values, ref_duplicates, ref_invalid = _load_reference_values(
            values_path)

        # ---- 逐产品派生 CSV（先算动量，键核对统一在观察全集上做） ----
        derived_dir = out / "snapshot"
        (derived_dir / "normalized").mkdir(parents=True)
        original_meta = json.loads(
            (Path(input_paths["snapshot_dir"]["path"]) / "snapshot.json")
            .read_text(encoding="utf-8"))
        items = []
        econ_stats: dict[str, dict] = {}
        momentum_by_symbol: dict[str, pd.Series] = {}

        for meta in original_meta["instruments"]:
            symbol = meta["instrument_id"]
            frame = loaded.frames[symbol]
            raw_close = frame["close"].astype(float)
            n_raw = len(raw_close)
            close = raw_close[raw_close > 0].dropna()
            n_dropped = n_raw - len(close)
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
                # 冻结显式缺失规则：非正/缺失收盘价不进入重建，逐产品留痕
                "close_dropped_nonpositive_or_nan": n_dropped,
                "unknown_available_at_events": list(unknown),
            }
            momentum_by_symbol[symbol] = mp.compute_momentum(econ)

        # ---- 正式观察键全集（返修 S2）：从冻结的观察规则/产品/合法窗口
        # 独立推导"应比对键集合"，不硬编码数量、不拿参考表当基准。 ----
        from lei_signal.research.trading_calendar import TradingCalendar

        calendar = TradingCalendar.from_file(
            input_paths["calendar"]["path"], input_paths["publication"]["path"])
        start = protocol["inputs"]["evaluation_start"]
        end = protocol["inputs"]["evaluation_end"]
        observations = [str(d) for d in
                        mp.complete_month_last_trading_days(calendar, start, end)]
        symbols = list(loaded.frames.keys())
        expected_all = {(s, o) for s in symbols for o in observations}
        derivable: dict[tuple[str, str], float] = {}
        for sym, obs in expected_all:
            m = momentum_by_symbol.get(sym)
            if m is None:
                continue
            key = pd.Timestamp(obs)
            if key in m.index:
                v = float(m.loc[key])
                if math.isfinite(v):
                    derivable[(sym, obs)] = v

        ref_keys = set(run04_values)
        reference_missing = sorted(derivable.keys() - ref_keys)
        out_of_scope = sorted(ref_keys - expected_all)
        no_derived_value = sorted(
            k for k in (ref_keys & expected_all) if k not in derivable)
        momentum_key_mismatch = 0
        momentum_keys_checked = 0
        for sym, obs in sorted(derivable.keys() & ref_keys):
            momentum_keys_checked += 1
            got = derivable[(sym, obs)]
            expected = run04_values[(sym, obs)]
            # 阈值 = 1e-12 * max(1.0, |expected|)；比常用
            # atol + rtol*|expected| 更严格（拒绝更多），非更宽松。
            if abs(got - expected) > 1e-12 * max(1.0, abs(expected)):
                momentum_key_mismatch += 1

        complete_consistent = bool(
            run04_values
            and not ref_duplicates and not ref_invalid
            and not reference_missing and not out_of_scope
            and not no_derived_value
            and momentum_key_mismatch == 0
            and momentum_keys_checked == len(derivable)
        )
        momentum_key_check = {
            "expected_observation_combinations": len(expected_all),
            "derivable_keys": len(derivable),
            "unique_reference_keys": len(run04_values),
            "checked": momentum_keys_checked,
            "mismatch": momentum_key_mismatch,
            "duplicate_reference_rows": ref_duplicates,
            "invalid_reference_values": ref_invalid,
            "reference_missing_expected_key": [
                {"symbol": s, "date": d} for s, d in reference_missing],
            "reference_out_of_scope": [
                {"symbol": s, "date": d} for s, d in out_of_scope],
            "reference_without_derived_value": [
                {"symbol": s, "date": d} for s, d in no_derived_value],
            "tolerance": (
                "阈值 = 1e-12 * max(1.0, |expected|)（比常用 "
                "atol + rtol*|expected| 更严格）；双方均为有限值后才比较"),
            "complete_consistent": complete_consistent,
        }

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
                    "path": str(bundle_path),
                    "sha256": ev_declared["sha256"]},
                "momentum_protocol": {"path": args.protocol,
                                      "sha256": protocol_sha},
                "reference_values": {"path": str(values_path),
                                     "sha256": ref_declared["sha256"]},
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
                "schema_version": bundle.get("schema_version"),
                "validated": len(bundle_result["validated"]),
                "unresolved": len(bundle_result["unresolved"]),
                "conflicts": len(bundle_result["conflicts"]),
            },
            "econ_stats": econ_stats,
            "binding": binding_summary,
            "momentum_key_check": momentum_key_check,
            "observation_cutoff_assumption": (
                "观察/决策截点 15:00 为按收盘设置的保守测试假设，"
                "不是已证实的数据到达时间或实盘决策时刻"),
        }
        if not complete_consistent:
            raise QualityReject(
                "正式键双向核对不完整一致，拒绝交付："
                f"expected_all={len(expected_all)} derivable={len(derivable)} "
                f"unique_reference={len(run04_values)} "
                f"checked={momentum_keys_checked} "
                f"mismatch={momentum_key_mismatch} "
                f"duplicates={len(ref_duplicates)} "
                f"invalid={len(ref_invalid)} "
                f"reference_missing={len(reference_missing)} "
                f"out_of_scope={len(out_of_scope)} "
                f"without_derived_value={len(no_derived_value)}")

        files = [("result.json", json.dumps(result, indent=1,
                                            ensure_ascii=False) + "\n")]
        snapshot_files = {
            str(p.relative_to(out)): _sha(p)
            for p in sorted(derived_dir.rglob("*")) if p.is_file()
        }
        manifest_payload = {
            "schema_version": "fixed-etf-derived-snapshot-manifest/1.1",
            "generated_at": datetime.now(UTC).isoformat(),
            # 不可变身份：输入版本文件 + 输出目录内排他冻结副本（双锚点）
            "protocol": {"input_path": args.protocol, "sha256": protocol_sha,
                         "protocol_id": protocol["protocol_id"],
                         "frozen_copy": frozen},
            "declared_inputs": {
                "evidence_bundle": {"path": str(bundle_path),
                                    "sha256": ev_declared["sha256"]},
                "reference_values": {"path": str(values_path),
                                     "sha256": ref_declared["sha256"]},
            },
            "offline_guard": guard.self_check,
            "result": result,
            "outputs": {
                **{name: hashlib.sha256(t.encode("utf-8")).hexdigest()
                   for name, t in files},
                "protocol-frozen.json": frozen["sha256"],
                **snapshot_files,
            },
        }
        manifest_text = json.dumps(manifest_payload, indent=1,
                                   ensure_ascii=False) + "\n"
        for name, text in files:
            (out / name).write_text(text, encoding="utf-8")
        (out / "manifest.json").write_text(manifest_text, encoding="utf-8")
        print(f"derived snapshot: {derived_dir}")
        print(f"binding: {json.dumps(binding_summary, ensure_ascii=False)}")
        print(f"momentum keys: unique={len(run04_values)} "
              f"checked={momentum_keys_checked} mismatch={momentum_key_mismatch} "
              f"complete_consistent={complete_consistent}")
        return EXIT_OK
    except QualityReject as exc:
        print(f"质量限制拒绝：{exc}", file=sys.stderr)
        return EXIT_REJECTED
    except InputIdentityError as exc:
        print(f"输入身份失败：{exc}", file=sys.stderr)
        return EXIT_FAILED
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
