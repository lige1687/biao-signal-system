"""独立的研究目标台账：持久化、版本冲突、授权范围及追加历史。"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from lei_signal.api.upgrade_models import GoalCreate

SEED_PATH = Path(__file__).resolve().parents[3] / "docs/okr/initial.json"
STATUSES = {"planned", "awaiting_approval", "approved", "in_progress", "review",
            "done", "paused", "dropped"}


class GoalError(Exception):
    def __init__(self, message, status=422):
        super().__init__(message)
        self.status = status


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _event(item, action, note, **extra):
    item["history"].append({"at": _now(), "action": action, "note": note, **extra})


def _new(data, key=None):
    now = _now()
    return {**data, "id": key or f"okr-{uuid4().hex[:12]}", "version": 1,
            "status": "planned", "created_at": now, "updated_at": now,
            "authorization": {"granted": False, "scope": "", "at": None}, "history": []}


def _save(conn, item):
    conn.execute("INSERT OR REPLACE INTO upgrade_goals(id, body) VALUES (?, ?)",
                 (item["id"], json.dumps(item, ensure_ascii=False)))


def _all(conn):
    return [json.loads(row[0]) for row in conn.execute("SELECT body FROM upgrade_goals")]


@contextmanager
def _db(path, seed_path=SEED_PATH):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    try:
        with conn:
            conn.execute("CREATE TABLE IF NOT EXISTS upgrade_goals (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
            conn.execute("CREATE TABLE IF NOT EXISTS upgrade_meta (id TEXT PRIMARY KEY)")
            conn.execute("BEGIN IMMEDIATE")
            if not conn.execute("SELECT 1 FROM upgrade_meta WHERE id='seed-v1'").fetchone():
                if seed_path is not None:
                    seeds = json.loads(Path(seed_path).read_text(encoding="utf-8"))["items"]
                    for seed in seeds:
                        content = {k: v for k, v in seed.items() if k in GoalCreate.model_fields}
                        item = _new(GoalCreate.model_validate(content).model_dump(mode="json"), seed["id"])
                        item["status"] = seed.get("status", "planned")
                        if item["status"] not in STATUSES:
                            raise ValueError("初始目标状态无效")
                        if seed.get("authorization_scope"):
                            item["authorization"] = {"granted": True,
                                "scope": seed["authorization_scope"], "at": seed.get("recorded_at")}
                        _event(item, "seed", seed.get("initial_note", "根据用户讨论登记，尚未启动执行。"),
                               recorded_at=seed.get("recorded_at"), scope=seed.get("authorization_scope", ""))
                        conn.execute("INSERT OR IGNORE INTO upgrade_goals VALUES (?, ?)",
                                     (item["id"], json.dumps(item, ensure_ascii=False)))
                conn.execute("INSERT INTO upgrade_meta VALUES ('seed-v1')")
        yield conn
    finally:
        conn.close()


def _get(conn, key):
    row = conn.execute("SELECT body FROM upgrade_goals WHERE id=?", (key,)).fetchone()
    if not row:
        raise GoalError("找不到这个目标", 404)
    return json.loads(row[0])


def _version(item, expected):
    if item["version"] != expected:
        raise GoalError("目标已被另一处更新，请刷新后再保存；本次内容尚未写入。", 409)


def _parent(conn, item):
    parent_id = item.get("parent_id")
    if item["kind"] == "directional" and parent_id:
        raise GoalError("方向性目标不能再挂到另一个目标下")
    if parent_id:
        parent = _get(conn, parent_id)
        if parent["kind"] != "directional" or parent["id"] == item["id"]:
            raise GoalError("具体目标只能关联方向性目标")
        if parent["status"] in {"done", "dropped"}:
            raise GoalError("请先重新打开该方向，再添加具体目标")


def list_goals(path, seed_path=SEED_PATH):
    with _db(path, seed_path) as conn:
        items = _all(conn)
    for item in items:
        children = [x for x in items if x.get("parent_id") == item["id"]]
        checks = children if item["kind"] == "directional" else item["milestones"]
        done = sum(x["status"] == "done" for x in checks) if item["kind"] == "directional" else sum(x["done"] for x in checks)
        item["progress"] = {"done": done, "total": len(checks)}
    items.sort(key=lambda x: ({"high": 0, "medium": 1, "low": 2}[x["priority"]], x["created_at"], x["id"]))
    return {"items": items, "generated_at": _now()}


def create_goal(path, data, seed_path=SEED_PATH):
    with _db(path, seed_path) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        item = _new(data)
        if item["kind"] == "concrete" and any(m["done"] for m in item["milestones"]):
            raise GoalError("新目标先登记并授权，再记录完成结果", 409)
        _parent(conn, item)
        _event(item, "created", "目标已登记，登记不会启动执行。")
        _save(conn, item)
        return item


def patch_goal(path, key, data, seed_path=SEED_PATH):
    with _db(path, seed_path) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        item = _get(conn, key)
        _version(item, data.pop("version"))
        if item["status"] in {"done", "dropped"}:
            raise GoalError("请先重新打开目标，再修改内容", 409)
        before = {k: item.get(k) for k in data}
        content = {k: item[k] for k in GoalCreate.model_fields}
        content.update(data)
        validated = GoalCreate.model_validate(content).model_dump(mode="json")
        # 改完成标准的文字或范围需重新授权；仅勾选既有标准属于进展更新。
        old_checks = [(m["id"], m["title"]) for m in item["milestones"]]
        new_checks = [(m["id"], m["title"]) for m in validated["milestones"]]
        scope_changed = any(validated[k] != item[k] for k in ("title", "purpose", "parent_id")) or old_checks != new_checks
        if any(m["done"] for m in validated["milestones"]) and validated["milestones"] != item["milestones"]:
            if not item["authorization"]["granted"] and item["kind"] == "concrete":
                raise GoalError("请先取得该具体目标的授权，再记录完成结果", 409)
        # 新增或改写的标准不能继承旧标准的完成勾选。
        previous_checks = set(old_checks)
        for milestone in validated["milestones"]:
            if (milestone["id"], milestone["title"]) not in previous_checks:
                milestone["done"] = False
        item.update(validated)
        _parent(conn, item)
        if scope_changed and item["authorization"]["granted"]:
            item["authorization"]["granted"] = False
            item["status"] = "awaiting_approval"
        elif item["status"] == "review":
            item["status"] = "in_progress" if item["kind"] == "concrete" else "planned"
        _event(item, "edited", "目标内容已更新；范围或完成标准改变时需重新授权。" if scope_changed else "进展已更新。",
               before=before, after={k: item.get(k) for k in data})
        item["version"] += 1
        item["updated_at"] = _now()
        _save(conn, item)
        return item


def act_on_goal(path, key, data, seed_path=SEED_PATH):
    with _db(path, seed_path) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        item = _get(conn, key)
        _version(item, data["version"])
        action, note = data["action"], data["note"]
        status = item["status"]
        auth = item["authorization"]
        concrete = item["kind"] == "concrete"
        if status in {"done", "dropped"} and action not in {"reopen", "note"}:
            raise GoalError("目标已结案；如有新工作，请先重新打开", 409)
        if action in {"authorize", "start", "revoke", "request_approval"} and not concrete:
            raise GoalError("请对方向下的具体目标逐项授权和推进")
        if action == "authorize":
            if not data["scope"].strip():
                raise GoalError("请写清此次授权推进的范围")
            item["authorization"] = {"granted": True, "scope": data["scope"], "at": _now()}
            item["status"] = "approved"
        elif action in {"revoke", "request_approval", "reopen"}:
            auth["granted"] = False
            item["status"] = "awaiting_approval" if concrete else "planned"
        elif action == "start":
            if not auth["granted"] or status not in {"approved", "paused"}:
                raise GoalError("需先授权该具体目标，且从已授权或已搁置状态开始", 409)
            item["status"] = "in_progress"
        elif action == "pause":
            item["status"] = "paused"
        elif action == "drop":
            auth["granted"] = False
            item["status"] = "dropped"
        elif action in {"submit_review", "accept"}:
            if concrete and (not auth["granted"] or status not in {"in_progress", "review"}):
                raise GoalError("先按授权推进，再提交验收", 409)
            if action == "accept" and status != "review":
                raise GoalError("先提交待验收，再确认完成", 409)
            if not item["evidence"].strip():
                raise GoalError("请补充实际结果或证据，再提交验收")
            if concrete and (not item["milestones"] or not all(m["done"] for m in item["milestones"])):
                raise GoalError("请先完成每一项完成标准")
            children = [x for x in _all(conn) if x.get("parent_id") == key]
            if not concrete and (not children or any(x["status"] not in {"done", "dropped"} for x in children)):
                raise GoalError("方向下还有未结案的具体目标", 409)
            item["status"] = "review" if action == "submit_review" else "done"
        _event(item, action, note, from_status=status, to_status=item["status"], scope=data.get("scope", ""))
        item["version"] += 1
        item["updated_at"] = _now()
        _save(conn, item)
        return item
