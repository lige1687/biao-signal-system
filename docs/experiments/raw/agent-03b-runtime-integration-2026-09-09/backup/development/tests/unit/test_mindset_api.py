"""认知与心态页接口测试：种子导入 → 评价 → 复习抽取 → 新增/删除 全流程。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from lei_signal.api.app import create_app


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    seed = tmp_path / "seed.json"
    seed.write_text(
        json.dumps(
            {
                "items": [
                    {"category": "认知", "text": "测试观点一", "source": "测试来源A"},
                    {"category": "纪律", "text": "测试观点二", "quote": "原话二", "source": "测试来源A"},
                    {"category": "心态", "text": "测试观点三", "source": "测试来源B"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    app = create_app()
    app.state.mindset_db_path = str(tmp_path / "mindset_test.db")
    app.state.mindset_seed_path = seed
    return TestClient(app)


def test_seed_import_and_list(client: TestClient):
    r = client.get("/api/mindset/items")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 3
    assert body["summary"]["total"] == 3
    assert body["summary"]["unevaluated"] == 3
    # 再次列出：种子幂等，不重复插入
    r2 = client.get("/api/mindset/items")
    assert len(r2.json()["items"]) == 3


def test_filter_and_bad_params(client: TestClient):
    r = client.get("/api/mindset/items", params={"category": "纪律"})
    assert [i["text"] for i in r.json()["items"]] == ["测试观点二"]
    assert client.get("/api/mindset/items", params={"status": "bogus"}).status_code == 400
    assert client.get("/api/mindset/items", params={"category": "不存在"}).status_code == 400


def test_status_update_and_review(client: TestClient):
    items = client.get("/api/mindset/items", params={"status": "unevaluated"}).json()["items"]
    target = next(i for i in items if i["text"] == "测试观点一")
    r = client.patch(f"/api/mindset/items/{target['id']}/status", json={"status": "agree"})
    assert r.status_code == 200
    assert r.json()["status"] == "agree"

    # 复习抽取：篮子里只有认可项/自建项，当前仅"测试观点一"
    rev = client.get("/api/mindset/review/next")
    assert rev.status_code == 200
    assert rev.json()["text"] == "测试观点一"
    assert rev.json()["review_count"] == 1

    # 改回未评价后篮子为空 → next 返回 null
    client.patch(f"/api/mindset/items/{target['id']}/status", json={"status": "unevaluated"})
    assert client.get("/api/mindset/review/next").json() is None

    # 404：不存在的 id
    assert client.patch("/api/mindset/items/nope/status", json={"status": "agree"}).status_code == 404


def test_create_and_delete_user_item(client: TestClient):
    r = client.post(
        "/api/mindset/items",
        json={"category": "复盘", "text": "今天追高了，违反纪律", "source": "自己记录"},
    )
    assert r.status_code == 201
    item = r.json()
    assert item["origin"] == "user"
    assert item["status"] == "unevaluated"

    # 校验：text 过短 422
    assert client.post("/api/mindset/items", json={"category": "复盘", "text": "短"}).status_code == 422

    # 删除自建 OK；删除种子条目 409
    assert client.delete(f"/api/mindset/items/{item['id']}").status_code == 204
    seed_item = client.get("/api/mindset/items").json()["items"][0]
    assert client.delete(f"/api/mindset/items/{seed_item['id']}").status_code == 409


def test_real_seed_file_wellformed():
    """仓库真实种子文件可解析、条目字段齐全（防止手改 JSON 写坏）。"""
    path = Path(__file__).resolve().parents[2] / "configs" / "mindset_seed.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data["items"]
    assert len(items) >= 20
    for row in items:
        assert row["category"] in ("认知", "心态", "纪律", "复盘")
        assert len(row["text"]) >= 10
