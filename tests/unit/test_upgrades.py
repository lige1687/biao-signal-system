"""目标管理的持久化、并发与逐项授权边界。"""
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    from lei_signal.api.routes.upgrades import router

    app = FastAPI()
    app.state.upgrades_db_path = str(tmp_path / "upgrades.db")
    app.state.upgrades_seed_path = None
    app.include_router(router)
    return TestClient(app)


def create(client, **kw):
    data = {"kind": "concrete", "title": "核对历史结论", "purpose": "查清证据",
            "milestones": [{"id": "m1", "title": "复核原文", "done": False}], **kw}
    r = client.post("/api/upgrades", json=data)
    assert r.status_code == 201, r.text
    return r.json()


def action(client, item, name, **kw):
    return client.post(f"/api/upgrades/{item['id']}/actions", json={
        "version": item["version"], "action": name, "note": "本次更新依据", **kw})


def test_persistence_and_export(client):
    goal = create(client)
    r = client.patch(f"/api/upgrades/{goal['id']}", json={
        "version": goal["version"], "next_action": "提交证据表"})
    assert r.status_code == 200
    saved = client.get("/api/upgrades").json()["items"][0]
    assert saved["next_action"] == "提交证据表"
    export = client.get("/api/upgrades/export")
    assert export.status_code == 200 and "attachment" in export.headers["content-disposition"]
    assert len(export.json()["items"][0]["history"]) == 2


def test_parent_must_be_direction_and_scope_is_individual(client):
    parent = create(client, kind="directional", milestones=[])
    a = create(client, parent_id=parent["id"])
    b = create(client, parent_id=parent["id"])
    assert client.post("/api/upgrades", json={"kind": "concrete", "title": "错误父级",
                        "parent_id": a["id"]}).status_code == 422
    assert action(client, parent, "authorize", scope="整个方向").status_code == 422
    assert action(client, a, "start").status_code == 409
    approved = action(client, a, "authorize", scope="只核对报告，不改规则").json()
    assert approved["status"] == "approved"
    assert action(client, approved, "start").status_code == 200
    assert action(client, b, "start").status_code == 409


def test_authorization_completion_and_reopen(client):
    goal = create(client)
    assert action(client, goal, "authorize", scope="").status_code == 422
    goal = action(client, goal, "authorize", scope="核对报告").json()
    goal = action(client, goal, "start").json()
    assert action(client, goal, "submit_review").status_code == 422
    r = client.patch(f"/api/upgrades/{goal['id']}", json={
        "version": goal["version"], "milestones": [{"id": "m1", "title": "复核原文", "done": True}],
        "evidence": "报告表明该方向不成立，研究已完成。"})
    goal = r.json()
    goal = action(client, goal, "submit_review").json()
    assert goal["status"] == "review"
    goal = action(client, goal, "accept").json()
    assert goal["status"] == "done"
    assert action(client, goal, "start").status_code == 409
    goal = action(client, goal, "reopen").json()
    assert not goal["authorization"]["granted"]
    assert action(client, goal, "start").status_code == 409


def test_concurrent_edits_and_invalid_links_are_rejected(client):
    goal = create(client)
    assert client.patch(f"/api/upgrades/{goal['id']}", json={
        "version": goal["version"], "title": "最新名称"}).status_code == 200
    assert client.patch(f"/api/upgrades/{goal['id']}", json={
        "version": goal["version"], "title": "旧窗口覆盖"}).status_code == 409
    assert client.post("/api/upgrades", json={"kind": "concrete", "title": "链接",
        "links": [{"label": "恶意", "url": "javascript:alert(1)"}]}).status_code == 422
    assert client.patch(f"/api/upgrades/{goal['id']}", json={
        "version": 2, "status": "done"}).status_code == 422


def test_scope_edit_revokes_permission_and_history_keeps_old_scope(client):
    goal = create(client)
    goal = action(client, goal, "authorize", scope="核对单份报告").json()
    goal = client.patch(f"/api/upgrades/{goal['id']}", json={
        "version": goal["version"], "purpose": "扩展为修改交易规则"}).json()
    assert not goal["authorization"]["granted"]
    assert goal["status"] == "awaiting_approval"
    assert any(h.get("scope") == "核对单份报告" for h in goal["history"])


def test_seed_only_once_and_no_overwrite(client, tmp_path):
    seed = tmp_path / "initial.json"
    seed.write_text(json.dumps({"items": [{"id": "seed-one", "kind": "concrete",
                                           "title": "初始目标"}]}))
    client.app.state.upgrades_seed_path = str(seed)
    goal = client.get("/api/upgrades").json()["items"][0]
    client.patch(f"/api/upgrades/{goal['id']}", json={"version": 1, "title": "已更新"})
    assert client.get("/api/upgrades").json()["items"][0]["title"] == "已更新"
    assert len(client.get("/api/upgrades").json()["items"]) == 1


def test_direction_cannot_close_with_unfinished_children(client):
    parent = create(client, kind="directional", milestones=[])
    create(client, parent_id=parent["id"])
    assert action(client, parent, "accept").status_code == 409


def test_cannot_precheck_new_goal_and_changed_standard_loses_completion(client):
    r = client.post("/api/upgrades", json={"kind": "concrete", "title": "不能预填完成",
        "milestones": [{"id": "m1", "title": "未执行", "done": True}]})
    assert r.status_code == 409
    goal = create(client)
    goal = action(client, goal, "authorize", scope="核对报告").json()
    goal = client.patch(f"/api/upgrades/{goal['id']}", json={"version": goal["version"],
        "milestones": [{"id": "m1", "title": "复核原文", "done": True}]}).json()
    goal = client.patch(f"/api/upgrades/{goal['id']}", json={"version": goal["version"],
        "milestones": [{"id": "m1", "title": "复核另一份报告", "done": True}]}).json()
    assert goal["status"] == "awaiting_approval"
    assert not goal["milestones"][0]["done"]
