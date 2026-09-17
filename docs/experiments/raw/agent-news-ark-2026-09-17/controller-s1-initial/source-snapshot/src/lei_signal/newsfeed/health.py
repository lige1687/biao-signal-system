"""消息资料健康状态（纯函数，2026-09-17 S1）。

把「采集是否新鲜 / 各阶段是否成功」从原来一个 ``ok`` 里拆出来，回答用户
买前最关心的问题：现在看到的消息资料还能不能信。

口径（计划 §4 Task 2 冻结）：
- ``last_checked_at`` 来自任务实际尝试/完成时间，不取新闻发布时间；
- ``last_success_at`` 来自明确的采集成功记录，不直接取综合 ok；旧记录
  没有阶段字段时保留 None（不追溯伪造成功）；
- ``availability`` 只表达采集侧状态；评分/简报成败在 ``stages`` 里同时
  表达（单一字段不能承担所有状态）；
- 时间缺失、未来时间、无时区分别 unknown；不从条目数推断成功；
- fresh 仅代表近期做过检查，不保证检查时点之后没有新公告。
"""
from __future__ import annotations

from typing import Any

from lei_signal.newsfeed.timeparse import is_future, parse_iso_ts

_UNKNOWN_STAGE = {"status": "unknown", "finished_at": None, "errors": []}


def _norm_stage(raw: Any) -> dict:
    """把 stats.stages 里的单阶段记录归一成 {status, finished_at, errors}。"""
    if not isinstance(raw, dict):
        return dict(_UNKNOWN_STAGE)
    errors = raw.get("errors")
    return {
        "status": str(raw.get("status") or "unknown"),
        "finished_at": raw.get("finished_at"),
        "errors": list(errors) if isinstance(errors, list) else [],
    }


def _stages_from_run(latest_run: dict[str, Any] | None) -> dict[str, dict]:
    """阶段状态：新记录直读；旧记录（无 stages 字段）全部 unknown。"""
    stages: dict[str, dict] = {}
    stats = (latest_run or {}).get("stats")
    recorded = stats.get("stages") if isinstance(stats, dict) else None
    for name in ("collect", "score", "digest", "push"):
        raw = recorded.get(name) if isinstance(recorded, dict) else None
        stage = _norm_stage(raw)
        if isinstance(raw, dict) and raw.get("reason"):
            stage["reason"] = raw["reason"]
        stages[name] = stage
    return stages


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
    stages = _stages_from_run(latest_run)
    out: dict[str, Any] = {
        "availability": "unknown",
        "last_checked_at": None,
        "last_success_at": latest_success_at,
        "latest_item_at": latest_item_at,
        "age_hours": None,
        "note_cn": "",
        "stages": stages,
        "unscored_count": int(unscored_count or 0),
        "max_age_hours": int(max_age_hours),
    }

    now_dt = parse_iso_ts(now)
    if now_dt is None:
        out["note_cn"] = "健康状态时间基准缺失或不合法，无法判断资料是否新鲜"
        return out

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
        out["note_cn"] = "最近一次任务时间在未来（记录异常），状态未知"
        return out

    out["last_checked_at"] = checked_raw
    age_hours = round((now_dt - checked_dt).total_seconds() / 3600, 1)
    out["age_hours"] = age_hours
    status = str(latest_run.get("status") or "")
    max_age = int(max_age_hours)

    def _failed_sources() -> str:
        errs = latest_run.get("errors")
        if isinstance(errs, list) and errs:
            names = [str(e.get("source")) for e in errs if isinstance(e, dict) and e.get("source")]
            if names:
                return "、".join(names)
        return "未知来源"

    if status == "running":
        if age_hours > max_age:
            out["availability"] = "stale"
            out["note_cn"] = (
                f"上次任务未完成（可能中断），且距今约 {age_hours} 小时，资料过期；"
                "不能据此认为“今日无重大消息”"
            )
        else:
            out["availability"] = "unknown"
            out["note_cn"] = "最近一次任务尚未完成（可能仍在运行或已中断），状态未知"
        return out

    if status == "failed" and age_hours <= max_age:
        out["availability"] = "failed"
        out["note_cn"] = (
            f"最近一次采集失败（约 {age_hours} 小时前）：{_failed_sources()}；"
            "条目与历史记录保留"
        )
        return out

    if age_hours > max_age:
        out["availability"] = "stale"
        out["note_cn"] = (
            f"资料过期：上次检查在约 {age_hours} 小时前，已超过 {max_age} 小时"
            "运维上限；不能据此认为“今日无重大消息”"
        )
        return out

    if status == "partial":
        out["availability"] = "partial"
        out["note_cn"] = (
            f"最近一次采集部分来源失败（约 {age_hours} 小时前）：{_failed_sources()}；"
            "其余来源正常"
        )
    elif status == "ok":
        out["availability"] = "fresh"
        if latest_item_at:
            out["note_cn"] = (
                f"采集正常，最近检查在约 {age_hours} 小时前；"
                f"最新相关消息发布于 {latest_item_at}"
            )
        else:
            out["note_cn"] = (
                f"采集正常，最近检查在约 {age_hours} 小时前；"
                "本次检查无相关消息（与停更不同）"
            )
    else:
        out["note_cn"] = f"最近一次任务状态记录无法识别（{status or '缺失'}），状态未知"
        return out

    # 阶段失败与总体状态同时表达（采集新鲜但评分失败等）。
    if stages["score"]["status"] == "failed":
        out["note_cn"] += "；AI 评分失败，相关条目保留为未评分"
    if stages["digest"]["status"] == "failed":
        out["note_cn"] += "；当日简报未生成"
    return out


__all__ = ["build_news_health"]
