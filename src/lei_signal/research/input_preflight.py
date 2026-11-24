"""研究输入离线检查（research-input-preflight-2026-09-13）。

让后续因子任务运行一次检查就知道：是哪批数据、能用于什么、缺什么、
哪些旧程序尚未接入——不再凭一份通过报告或几个标签开工。

**薄编排，不实现新规则**：复用 ``load_snapshot`` 的完整性核验、
``TradingCalendar``、``check_snapshot`` 的质量与用途裁决、
``require_use`` 的闸门、``definitions`` 的登记表与 ``bind_definitions``
的机械字段绑定。本模块不实现新价格公式、来源资格、因子计算或回测。

四个独立结果必须分开，不得合并成一个"通过"：

1. 快照是否完整（``integrity``）；
2. 该批数据是否满足所请求用途的质量与声明检查（``data_uses``）；
3. 对象是否允许该用途且实际输入满足其字段检查（``objects``）；
4. 是否已计算 / 是否有效 / 是否获准交易——本入口对三者一律给出否定
   （``calculation_run=False``、``production_authorized=False``，
   有效性不是本入口能判定的）。

调用方提供的 ``verified=True``、字段列表、币种、自填上市证明一律不信：
一律从路径重读并核实。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lei_signal.research import data_quality as q
from lei_signal.research.data_snapshot import load_snapshot
from lei_signal.research.trading_calendar import TradingCalendar

USES: tuple[str, ...] = q.USES


def combine_checks(
    *, integrity_ok: bool, data_use_ok: bool, object_checks: tuple[bool, ...]
) -> bool:
    """本次请求各检查项的合取。

    这只是当前这一次请求的合并逻辑，**不是**新的质量规则或可信标签入口。
    命令行不接受调用方传入这些布尔值——它们只能来自本模块自己的检查。
    """
    return integrity_ok and data_use_ok and all(object_checks)


def _error(stage: str, exc: BaseException | str) -> dict:
    return {
        "stage": stage,
        "error": f"{type(exc).__name__}: {exc}" if isinstance(exc, BaseException) else str(exc),
    }


def _read_json(path: Path, stage: str) -> tuple[Any, dict | None]:
    """读 JSON 并做最小类型检查；失败返回 (None, error)。不吞异常。"""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, _error(stage, f"文件不存在：{path}")
    except json.JSONDecodeError as exc:
        return None, _error(stage, f"不是合法 JSON：{exc}")
    except OSError as exc:
        return None, _error(stage, exc)
    if not isinstance(payload, dict):
        return None, _error(stage, f"JSON 顶层必须是对象，实际 {type(payload).__name__}")
    return payload, None


def inspect_input(
    *,
    snapshot_dir,
    calendar_path,
    publication_path,
    actions_path,
    registry_path,
    refs: tuple[str, ...],
    use: str,
    evaluation_start: str,
    evaluation_end: str,
) -> dict:
    """只读检查一批研究输入，返回可 JSON 序列化的报告。

    不运行因子、账户或收益计算；不修复数据；不启用
    ``allow_conditional`` / ``accept_structural``。
    """
    if use not in USES:
        raise ValueError(f"未知用途 {use!r}；合法值：{USES}")
    errors: list[dict] = []
    limitations: list[str] = []

    # 日期合法性/起止关系由本入口自行校验，不依赖可选日历触发。
    from datetime import date as _date

    evaluation_ok = True
    try:
        _s = _date.fromisoformat(str(evaluation_start)[:10])
        _e = _date.fromisoformat(str(evaluation_end)[:10])
        if len(str(evaluation_start)) != 10 or len(str(evaluation_end)) != 10:
            raise ValueError("日期必须是 YYYY-MM-DD")
        if _s > _e:
            evaluation_ok = False
            errors.append(
                _error("evaluation",
                       f"起止倒置：evaluation_start={evaluation_start} 晚于 "
                       f"evaluation_end={evaluation_end}；属输入错误，"
                       "不是正常的数据拒绝")
            )
    except ValueError as exc:
        evaluation_ok = False
        errors.append(_error("evaluation", f"非法评价期日期：{exc}"))

    request = {
        "snapshot_dir": str(snapshot_dir),
        "calendar_path": str(calendar_path) if calendar_path else None,
        "publication_path": str(publication_path) if publication_path else None,
        "actions_path": str(actions_path) if actions_path else None,
        "registry_path": str(registry_path) if registry_path else None,
        "refs": list(refs),
        "use": use,
        "evaluation_start": evaluation_start,
        "evaluation_end": evaluation_end,
    }

    # ---- 1. 快照与完整性（重读，不信调用方的 verified=True） ----
    integrity = {
        "verified": False,
        "hash_mismatches": [],
        "instruments": [],
        "rows": 0,
        "first_date": None,
        "last_date": None,
        "per_instrument_fields": {},
        "date_index_note": None,
    }
    loaded = None
    try:
        loaded = load_snapshot(snapshot_dir)
        integrity["verified"] = bool(loaded.verified)
        integrity["hash_mismatches"] = list(loaded.hash_mismatches)
        integrity["instruments"] = sorted(loaded.frames)
        integrity["rows"] = int(sum(len(f) for f in loaded.frames.values()))
        all_dates = sorted({str(d)[:10] for f in loaded.frames.values() for d in f.index})
        integrity["first_date"] = all_dates[0] if all_dates else None
        integrity["last_date"] = all_dates[-1] if all_dates else None
        declared_fields = set(loaded.snapshot["semantics"]["fields"])
        per_fields = {}
        for symbol, frame in sorted(loaded.frames.items()):
            have = set(frame.columns) | {"date"}
            missing = sorted(declared_fields - have)
            per_fields[symbol] = {
                "missing_declared_fields": missing,
                "rows": int(len(frame)),
            }
        integrity["per_instrument_fields"] = per_fields
        sample = next(iter(loaded.frames.values()), None)
        integrity["date_index_note"] = (
            "日期以 datetime64 索引承载，与快照声明的 date 字段一一对应；"
            f"索引类型 {sample.index.dtype if sample is not None else 'n/a'}"
        )
        if not loaded.verified:
            limitations.append("快照完整性核验失败：哈希不一致或字段结构不符")
        integrity["empty_instruments"] = not integrity["instruments"]
        if integrity["empty_instruments"]:
            limitations.append(
                "快照不含任何标的：空输入不得被当作「满足」放行"
            )
    except Exception as exc:  # noqa: BLE001 - 记录并跳过依赖阶段，不吞
        errors.append(_error("snapshot", exc))

    # ---- 2. 日历 ----
    calendar = None
    calendar_info: dict = {"loaded": False}
    if calendar_path:
        if publication_path:
            _, perr = _read_json(Path(publication_path), "publication")
            if perr:
                errors.append(perr)
        try:
            calendar = TradingCalendar.from_file(calendar_path, publication_path)
            cov = calendar.coverage(evaluation_start, evaluation_end)
            calendar_info = {
                "loaded": True,
                "authority": calendar.authority,
                "publisher": calendar.publisher,
                "coverage_complete": cov.complete,
                "missing_months": list(cov.missing_months),
                "day_incomplete_months": list(cov.day_incomplete_months),
                "invalid_records": len(cov.to_dict()["invalid_records"]),
            }
            if not cov.complete:
                limitations.append(
                    "日历覆盖不完整：未覆盖区间一律未知，不回退为普通工作日"
                )
            limitations.append(
                "日历路径与哈希不等于发布时点已获证明；"
                "跨所与年度覆盖限制照旧保留"
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(_error("calendar", exc))
    else:
        limitations.append("未提供日历：所有依赖日历的检查按无合格日历降级")

    # ---- 3. 公司行动（只读 events 容器，内容仍交核验） ----
    actions: list[dict] | None = None
    if actions_path:
        payload, aerr = _read_json(Path(actions_path), "actions")
        if aerr:
            errors.append(aerr)
        else:
            raw = payload.get("events")
            if not isinstance(raw, list):
                errors.append(_error("actions", "缺少 events 列表容器"))
            else:
                actions = raw

    # ---- 4. 质量与用途裁决 ----
    report: q.QualityReport | None = None
    if loaded is not None and evaluation_ok:
        try:
            report = q.check_snapshot(
                loaded,
                calendar=calendar,
                actions=actions,
                evaluation_start=evaluation_start,
                evaluation_end=evaluation_end,
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(_error("quality", exc))

    data_uses: dict[str, dict] = {}
    for u in USES:
        entry: dict[str, Any] = {
            "verdict": None,
            "declared": None,
            "default_accepted": False,
            "reason": "",
            "blockers": {"fixable": [], "structural": []},
        }
        if report is not None:
            entry["verdict"] = report.verdict_for(u)
            entry["blockers"] = report.blockers_for(u)
        if loaded is not None:
            entry["declared"] = u in loaded.declared_uses
            if not entry["declared"]:
                entry["reason"] = f"not_declared: 产物自身声明的用途不含 {u}"
        if report is not None and loaded is not None:
            try:
                q.require_use(report, u, declared_uses=loaded.declared_uses)
                entry["default_accepted"] = True
            except q.UseNotPermitted as e:
                entry["default_accepted"] = False
                if not entry["reason"]:
                    entry["reason"] = "; ".join(e.reasons) if e.reasons else e.verdict
        data_uses[u] = entry

    # ---- 5. 登记表与对象绑定 ----
    registry_info: dict = {"loaded": False}
    objects: dict[str, dict] = {}
    sources_ok = True
    if registry_path:
        try:
            from lei_signal.research import definitions as d

            registry = d.load_registry(registry_path)
            registry_info = {
                "loaded": True,
                "container_version": registry.get("version"),
                "objects": len(registry["objects"]),
                "sources": len(registry["sources"]),
            }
            try:
                d.verify_sources(registry)
                registry_info["sources_verified"] = True
            except Exception as exc:  # noqa: BLE001
                registry_info["sources_verified"] = False
                registry_info["sources_error"] = f"{type(exc).__name__}: {exc}"
                sources_ok = False
                if refs:
                    limitations.append(
                        "登记表来源哈希核验未通过：对请求对象所需的来源完整性"
                        "已失败，所有对象请求被保守拒绝（blocked_by=sources_unverified）；"
                        "详见 registry.sources_error"
                    )
                else:
                    registry_info["objects_stage"] = "skipped_no_refs"
                    limitations.append(
                        "登记表来源哈希核验未通过，但本次无对象请求："
                        "对象阶段未使用，独立数据结论保留；"
                        "此规则不得用于绕过有对象请求的来源失败"
                    )
            limitations.append(
                "既有机器绑定限制：validate_registry 仍要求 standard_version==1.0.0，"
                "而正文标准已为 1.1.0；如实保留，不改版本字符串冒充迁移"
            )
            for ref in refs:
                obj: dict[str, Any] = {"ref": ref}
                if "@" not in ref:
                    obj["resolved"] = False
                    obj["error"] = "必须使用精确 id@version"
                    objects[ref] = obj
                    continue
                purpose_allowed = None
                try:
                    card = d.resolve(registry, ref, use)
                    purpose_allowed = True
                except Exception as exc:  # noqa: BLE001
                    purpose_allowed = False
                    obj["purpose_error"] = f"{type(exc).__name__}: {exc}"
                    try:
                        card = d.resolve(registry, ref)
                    except Exception as exc2:  # noqa: BLE001
                        obj["resolved"] = False
                        obj["error"] = f"{type(exc2).__name__}: {exc2}"
                        objects[ref] = obj
                        continue
                obj["resolved"] = True
                obj["purpose_allowed"] = purpose_allowed
                obj["card_uses"] = card.get("uses", [])
                try:
                    from lei_signal.research.factor_runtime import contract_digest

                    obj["contract_digest"] = contract_digest(card)
                except Exception:  # noqa: BLE001
                    obj["contract_digest"] = None
                if not sources_ok:
                    obj["blocked_by"] = "sources_unverified"
                if loaded is not None:
                    from lei_signal.research.data_snapshot import bind_definitions

                    binding = bind_definitions(
                        registry=registry, refs=[ref],
                        snapshot=loaded.snapshot, purpose=None,
                    )["bindings"][ref]
                    # 保留 binding 原结果（含 reasons），不只抽两个字段
                    obj["binding"] = binding
                    obj["missing_fields"] = binding.get("missing_fields")
                    obj["directly_satisfiable"] = binding.get("directly_satisfiable")
                else:
                    obj["missing_fields"] = None
                    obj["directly_satisfiable"] = None
                # 导出完整解析卡与递归依赖（生成物，不手改）
                obj["resolved_cards"] = _resolve_closure(d, registry, ref)
                objects[ref] = obj
        except Exception as exc:  # noqa: BLE001
            errors.append(_error("registry", exc))
    elif refs:
        errors.append(_error("registry", "提供了 refs 但未提供登记表路径"))

    # ---- 6. 合并 ----
    integrity_ok = integrity["verified"] and not integrity.get(
        "empty_instruments", False
    )
    data_use_ok = bool(
        report is not None and data_uses[use]["default_accepted"]
    )
    object_checks = tuple(
        bool(
            obj.get("resolved")
            and obj.get("purpose_allowed")
            and obj.get("directly_satisfiable")
            and sources_ok
        )
        for obj in objects.values()
    )
    request_satisfied = (
        combine_checks(
            integrity_ok=integrity_ok,
            data_use_ok=data_use_ok,
            object_checks=object_checks,
        )
        and not errors
    )

    if loaded is not None and refs:
        unsatisfied = [r for r, o in objects.items()
                       if not (o.get("resolved") and o.get("purpose_allowed")
                               and o.get("directly_satisfiable"))]
        if unsatisfied:
            limitations.append(
                f"以下对象未满足字段/用途检查：{unsatisfied}；"
                "这是已实现的机械字段检查的结论，不是完整公式语义证明"
            )
    limitations.append(
        "request_satisfied=true 仅表示本次已实现的输入检查满足，"
        "不等于公式实现、历史可得时点、因子有效或交易授权"
    )

    input_times: dict = {"available_at": None}
    if loaded is not None:
        sem = loaded.snapshot.get("semantics", {})
        input_times = {
            "snapshot_timing": loaded.snapshot.get("timing"),
            "time_semantics": sem.get("time_semantics"),
            "per_instrument": {
                item["instrument_id"]: {
                    "fetched_at": item.get("fetched_at"),
                    "first_date": item.get("first_date"),
                    "last_date": item.get("last_date"),
                }
                for item in loaded.snapshot.get("instruments", [])
            },
            "available_at": None,
            "available_at_note": "历史到达时间未知；保持 null，不用本次生成时刻顶替",
        }

    return {
        "schema_version": "research-input-preflight/1.0",
        "request": request,
        "input_times": input_times,
        "integrity": integrity,
        "calendar": calendar_info,
        "data_uses": data_uses,
        "registry": registry_info,
        "objects": objects,
        "findings": (
            [f.to_dict() for f in report.findings] if report is not None else []
        ),
        "request_satisfied": request_satisfied,
        "errors": errors,
        "limitations": limitations,
        "calculation_run": False,
        "production_authorized": False,
    }


def _resolve_closure(d, registry: dict, ref: str, _seen: dict | None = None) -> dict:
    """解析 ref 及其递归依赖的完整定义卡（生成物，不手改）。

    解析失败的依赖记为 ``{"resolve_error": ...}``；环由 `_seen` 防护。
    """
    seen = {} if _seen is None else _seen
    if ref in seen:
        return seen
    try:
        card = d.resolve(registry, ref)
    except Exception as exc:  # noqa: BLE001
        seen[ref] = {"resolve_error": f"{type(exc).__name__}: {exc}"}
        return seen
    seen[ref] = card
    for dep in card.get("dependencies", []):
        _resolve_closure(d, registry, dep, seen)
    return seen


__all__ = ["USES", "combine_checks", "inspect_input"]


def inspect_workflow_input(payload: dict, contract: dict) -> dict:
    """Shared workflow adapter; source identity qualification stays with root.

    Legal missing rows remain observations with reasons. Invalid temporal input
    raises ValueError from the causal builder before downstream evaluation.
    """
    from lei_signal.research.workflow_inputs import prepare_observations

    return prepare_observations(payload, contract)
