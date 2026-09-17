"""消息资料健康状态（纯函数，2026-09-17 S1；repair-1 按主控复核 R1 返修）。

把「采集是否新鲜 / 各阶段是否成功」从原来一个 ``ok`` 里拆出来，回答用户
买前最关心的问题：现在看到的消息资料还能不能信。

口径（计划 §4 Task 2 + 主控复核 R1 冻结）：
- ``last_checked_at`` 来自任务实际尝试/完成时间，不取新闻发布时间；
- ``last_success_at`` 来自明确的采集成功记录，不直接取综合 ok；
- **可用性以明确的采集阶段记录为准**：新格式看 stages.collect.status；
  旧记录没有阶段字段时保留未知（recent=unknown，过期=stale），不冒充正常；
  总状态与采集阶段矛盾时不能洗成正常——采集记失败即失败，其余矛盾报未知
  并说明；
- 辅助时间字段（latest_success_at / latest_item_at / 各阶段时间）缺失可以，
  **有值而非法（无时区/坏串/未来）不得拿来证明正常**：前两者非法即整体
  unknown 并留 anomalies 原始值供排查；阶段时间非法只降级该阶段时间；
- 未来时间严格判定（无容差）；过期阈值用未舍入时长比较，舍入只用于文字；
- fresh 仅代表近期做过检查，不保证检查时点之后没有新公告；「从未采集」与
  「检查正常但无消息」是两回事。
"""
from __future__ import annotations

from typing import Any

from lei_signal.newsfeed.timeparse import is_future, parse_iso_ts

_UNKNOWN_STAGE = {"status": "unknown", "finished_at": None, "errors": []}


def _norm_stage(raw: Any, name: str, anomalies: list[str], now_dt) -> dict:
    """把 stats.stages 里的单阶段记录归一成 {status, finished_at, errors}。

    阶段时间有值而非法（无时区/坏串/未来）时：时间降级为 None 并留异常，
    阶段状态本身不受影响（主控复核 R1：保留原始异常供排查）。
    """
    if not isinstance(raw, dict):
        return dict(_UNKNOWN_STAGE)
    errors = raw.get("errors")
    finished = raw.get("finished_at")
    if finished is not None:
        dt = parse_iso_ts(finished)
        if dt is None:
            anomalies.append(f"阶段 {name}.finished_at 无时区或语法非法：{finished!r}")
            finished = None
        elif is_future(dt, now_dt):
            anomalies.append(f"阶段 {name}.finished_at 在未来：{finished!r}")
            finished = None
    return {
        "status": str(raw.get("status") or "unknown"),
        "finished_at": finished,
        "errors": list(errors) if isinstance(errors, list) else [],
    }


def _stages_from_run(
    latest_run: dict[str, Any] | None, anomalies: list[str], now_dt
) -> dict[str, dict]:
    """阶段状态：新记录直读；旧记录（无 stages 字段）全部 unknown。"""
    stages: dict[str, dict] = {}
    stats = (latest_run or {}).get("stats")
    recorded = stats.get("stages") if isinstance(stats, dict) else None
    for name in ("collect", "score", "digest", "push"):
        raw = recorded.get(name) if isinstance(recorded, dict) else None
        stage = _norm_stage(raw, name, anomalies, now_dt)
        if isinstance(raw, dict) and raw.get("reason"):
            stage["reason"] = raw["reason"]
        stages[name] = stage
    return stages


def _collect_stage_status(latest_run: dict[str, Any]) -> str | None:
    """明确的采集阶段状态；旧记录无此字段返回 None（不追溯伪造）。"""
    stats = latest_run.get("stats")
    stages = stats.get("stages") if isinstance(stats, dict) else None
    if not isinstance(stages, dict):
        return None
    collect = stages.get("collect")
    if not isinstance(collect, dict) or not collect.get("status"):
        return None
    return str(collect["status"])


def build_news_health(
    *,
    latest_run: dict | None,
    latest_success_at: str | None,
    latest_item_at: str | None,
    unscored_count: int,
    now: str,
    max_age_hours: int,
) -> dict:
    """汇总消息资料健康状态。仅关键字参数；返回可 JSON 序列化 dict。"""
    anomalies: list[str] = []
    out: dict[str, Any] = {
        "availability": "unknown",
        "last_checked_at": None,
        "last_success_at": latest_success_at,
        "latest_item_at": latest_item_at,
        "age_hours": None,
        "note_cn": "",
        "stages": {},
        "unscored_count": int(unscored_count or 0),
        "max_age_hours": int(max_age_hours),
        "anomalies": anomalies,
    }

    now_dt = parse_iso_ts(now)
    if now_dt is None:
        out["note_cn"] = "健康状态时间基准缺失或不合法，无法判断资料是否新鲜"
        return out
    stages = _stages_from_run(latest_run, anomalies, now_dt)
    out["stages"] = stages

    # ---- 辅助时间字段：缺失可以；有值而非法 → 整体 unknown（R1）----
    aux_invalid = False
    for label, key in (("latest_success_at", "last_success_at"),
                       ("latest_item_at", "latest_item_at")):
        raw = out[key]
        if raw is None:
            continue
        dt = parse_iso_ts(raw)
        if dt is None:
            anomalies.append(f"{label} 无时区或语法非法：{raw!r}")
            aux_invalid = True
        elif is_future(dt, now_dt):
            anomalies.append(f"{label} 在未来：{raw!r}")
            aux_invalid = True

    if latest_run is None:
        if latest_success_at or latest_item_at:
            out["note_cn"] = "存在历史消息但没有任何采集任务记录，状态未知"
            return out
        out["availability"] = "never"
        out["note_cn"] = "尚未有任何采集记录"
        return out

    checked_raw = latest_run.get("finished_at") or latest_run.get("started_at")
    checked_dt = parse_iso_ts(checked_raw)
    if checked_dt is None:
        out["note_cn"] = "最近一次任务时间缺失或不合法（无时区/坏串），状态未知"
        return out
    if is_future(checked_dt, now_dt):
        # 严格未来判定：不设容差，也不会出现负年龄（R1）。
        out["note_cn"] = "最近一次任务时间在未来（记录异常），状态未知"
        return out

    out["last_checked_at"] = checked_raw
    exact_age_hours = (now_dt - checked_dt).total_seconds() / 3600
    out["age_hours"] = round(exact_age_hours, 1)  # 舍入仅用于文字展示
    max_age = int(max_age_hours)
    overdue = exact_age_hours > max_age  # 阈值用未舍入时长（R1）

    if aux_invalid:
        out["note_cn"] = "辅助时间字段有值而非法（见 anomalies），状态未知，不据此证明正常"
        return out

    run_status = str(latest_run.get("status") or "")

    def _failed_sources() -> str:
        errs = latest_run.get("errors")
        if isinstance(errs, list) and errs:
            names = [str(e.get("source")) for e in errs if isinstance(e, dict) and e.get("source")]
            if names:
                return "、".join(names)
        return "未知来源"

    def _stale_note(context: str = "") -> str:
        return (
            f"资料过期：上次检查在约 {out['age_hours']} 小时前，已超过 {max_age} 小时"
            "运维上限；不能据此认为“今日无重大消息”" + context
        )

    if run_status == "running":
        if overdue:
            out["availability"] = "stale"
            out["note_cn"] = _stale_note("；上次任务未完成（可能中断）")
        else:
            out["availability"] = "unknown"
            out["note_cn"] = "最近一次任务尚未完成（可能仍在运行或已中断），状态未知"
        return out

    # ---- 可用性以明确采集阶段为准（R1）----
    collect_status = _collect_stage_status(latest_run)
    conflict = (
        collect_status is not None
        and run_status in ("ok", "partial", "failed")
        and collect_status in ("ok", "partial", "failed")
        and collect_status != run_status
    )

    if overdue:
        # 过期的旧记录仍须显示过期；失败/矛盾作为上下文保留。
        out["availability"] = "stale"
        context = ""
        if collect_status == "failed":
            context = f"；最近一次采集还曾失败（{_failed_sources()}）"
        elif conflict:
            context = f"；且记录自相矛盾（总状态 {run_status}，采集阶段 {collect_status}）"
        out["note_cn"] = _stale_note(context)
        return out

    if collect_status is None:
        # 旧记录缺阶段字段：检查时间新鲜也不能冒充采集正常（R1）。
        out["availability"] = "unknown"
        out["note_cn"] = (
            f"最近一次检查在约 {out['age_hours']} 小时前，但旧记录缺少采集阶段字段，"
            "采集是否成功未知（不冒充正常）"
        )
        return out

    if conflict:
        if collect_status == "failed":
            out["availability"] = "failed"
            out["note_cn"] = (
                f"最近一次采集阶段记录为失败（总状态却记为 {run_status}，记录矛盾）："
                f"{_failed_sources()}；条目与历史记录保留"
            )
        else:
            out["availability"] = "unknown"
            out["note_cn"] = (
                f"运行记录自相矛盾（总状态 {run_status}，采集阶段 {collect_status}），"
                "状态未知，不能声称成功"
            )
        return out

    if collect_status == "failed":
        out["availability"] = "failed"
        out["note_cn"] = (
            f"最近一次采集失败（约 {out['age_hours']} 小时前）：{_failed_sources()}；"
            "条目与历史记录保留"
        )
        return out

    if collect_status == "partial":
        out["availability"] = "partial"
        out["note_cn"] = (
            f"最近一次采集部分来源失败（约 {out['age_hours']} 小时前）：{_failed_sources()}；"
            "其余来源正常"
        )
    elif collect_status == "ok":
        out["availability"] = "fresh"
        if out["latest_item_at"]:
            out["note_cn"] = (
                f"采集正常，最近检查在约 {out['age_hours']} 小时前；"
                f"最新相关消息发布于 {out['latest_item_at']}"
            )
        else:
            out["note_cn"] = (
                f"采集正常，最近检查在约 {out['age_hours']} 小时前；"
                "本次检查无相关消息（与停更不同）"
            )
    else:
        out["availability"] = "unknown"
        out["note_cn"] = f"采集阶段状态无法识别（{collect_status}），状态未知"
        return out

    # 阶段失败与总体状态同时表达（采集新鲜但评分失败等）。
    if stages["score"]["status"] == "failed":
        out["note_cn"] += "；AI 评分失败，相关条目保留为未评分"
    if stages["digest"]["status"] == "failed":
        out["note_cn"] += "；当日简报未生成"
    return out


__all__ = ["build_news_health"]
