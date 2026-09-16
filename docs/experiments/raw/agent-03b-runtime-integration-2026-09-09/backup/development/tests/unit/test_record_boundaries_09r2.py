"""09R2 记录与查询边界（e1—e5）交叉场景测试（2026-09-08）。

固定验收：修后原 e1—e5 场景通过、原九探针继续通过（另跑），本文件补
能从**用户出口**（record 返回值、current_claim_ids、summarize、
recent_observations、真实 HTTP /api/copilot/observations、情绪脚本输出）
发现交叉问题的测试。临时库 + 零网络；脚本走进程内真实模块。
"""
from __future__ import annotations

import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lei_signal.copilot import observation as ob
from lei_signal.storage.sqlite_store import connect

REPO = Path(__file__).resolve().parents[2]


def _rec(conn, *, version="v1", config=None, shown=True, revision=None,
         scope="", strategy="", direction=None, rule_refs=(), frozen=None,
         observed_at="2026-08-03", symbol="A", symbols=None, flags=None,
         cls=""):
    syms = symbols if symbols is not None else (symbol,)
    return ob.record_observations(
        conn, source_type="recommendation", source_record_id="2026-08-03",
        observed_at=observed_at, evaluation_kind=ob.KIND_TECHNICAL_FORWARD,
        evaluation_version=version, shown=shown, revision_key=revision,
        items=[ob.ObservationItem(
            instrument_id=s, payload={"close": 100}, claim="watch",
            horizons=(1,), scope=scope, strategy=strategy, direction=direction,
            rule_refs=list(rule_refs), eval_config=config or {},
            rule_refs_frozen=list(frozen or []),
            shown=(flags or {}).get(s, True), claim_class=cls) for s in syms],
    )


def _claims(conn):
    return [dict(x) for x in conn.execute(
        "SELECT observation_id, evaluation_version, eval_config_hash, scope, "
        "strategy, direction, rule_refs FROM agent_observations "
        "WHERE record_type='claim'")]


# ================= e1：业务重试不吞评价方法变化 =================

@pytest.mark.parametrize("field_kw", [
    {"version": "v2"},
    {"config": {"exit": "different"}},
    {"scope": "other_scope"},
    {"strategy": "other_strategy"},
    {"direction": "up"},
    {"rule_refs": ("docs/other.md",)},
    {"observed_at": "2026-08-04"},
])
def test_e1_method_changes_are_new_business(tmp_path, field_kw):  # noqa: ANN001
    """逐项改评价版本/config/scope/策略/方向/规则选择/观察时点：均不静默吞掉。"""
    conn = connect(tmp_path / "x.db")
    _rec(conn)
    _rec(conn, **field_kw)
    rows = _claims(conn)
    assert len(rows) == 2, f"{field_kw} 被静默去重"
    cur = ob.current_claim_ids(conn, source_type="recommendation")
    assert cur == {rows[1]["observation_id"]}  # 当前集合 = 新业务批次的成员
    conn.close()


def test_e1_frozen_refs_alone_are_not_business_change(tmp_path):  # noqa: ANN001
    """材料文件单独更新（冻结引用变化）+ 同业务重试：复用当前批次，
    不新建主张；材料哈希不混入业务身份（Q2 不倒退）。"""
    conn = connect(tmp_path / "x.db")
    frozen_a = [{"rule_id": "r1", "version": "v1", "config_hash": "aaa"}]
    frozen_b = [{"rule_id": "r1", "version": "v9", "config_hash": "zzz"}]
    _rec(conn, frozen=frozen_a)
    _rec(conn, frozen=frozen_b)  # 仅动态冻结依据变化
    assert len(_claims(conn)) == 1  # 复用，不新建
    saved = json.loads(conn.execute(
        "SELECT rule_refs_frozen FROM agent_observations "
        "WHERE record_type='claim'").fetchone()[0])
    assert saved == frozen_a  # 首次冻结依据不被换掉
    conn.close()


def test_e1_keyed_same_key_different_method_conflicts(tmp_path):  # noqa: ANN001
    """相同 revision_key 换评价版本 = 业务含义不同：显式冲突，调用方可见。"""
    conn = connect(tmp_path / "x.db")
    _rec(conn, revision="k1", version="v1", config={"exit": "a"})
    st = _rec(conn, revision="k1", version="v2", config={"exit": "a"})
    assert st["revision_conflict"] == 1
    conn.close()


def test_e1_keyed_same_key_retry_keeps_first_refs(tmp_path):  # noqa: ANN001
    """同键同业务重试（引用适配器换了输出）：复用首份依据，批次/主张不增。"""
    conn = connect(tmp_path / "x.db")
    frozen_a = [{"rule_id": "r1", "version": "v1", "config_hash": "aaa"}]
    frozen_b = [{"rule_id": "r1", "version": "v9", "config_hash": "zzz"}]
    _rec(conn, revision="k1", frozen=frozen_a)
    st = _rec(conn, revision="k1", frozen=frozen_b)
    assert st["batch_reused"] == 1
    assert st.get("revision_conflict", 0) == 0
    assert len(_claims(conn)) == 1
    saved = json.loads(conn.execute(
        "SELECT rule_refs_frozen FROM agent_observations "
        "WHERE record_type='claim'").fetchone()[0])
    assert saved == frozen_a
    conn.close()


# ================= e2/e3：草稿展示同一套事务 =================

def _rows_status(conn):
    return [dict(x) for x in conn.execute(
        "SELECT record_type, observation_id, display_status, first_shown_at, "
        "superseded_by FROM agent_observations")]


def test_promotion_keyed_empty_db(tmp_path):  # noqa: ANN001
    """e2：空库首草稿（带键）转正——成员展示、首次展示时刻、评价占位齐全。"""
    conn = connect(tmp_path / "x.db")
    _rec(conn, shown=False, revision="r1")
    st = _rec(conn, shown=True, revision="r1")
    assert st["batch_promoted"] == 1
    rows = _rows_status(conn)
    assert all(r["display_status"] == "shown" for r in rows)
    batch = next(r for r in rows if r["record_type"] == "display_batch")
    member = next(r for r in rows if r["record_type"] == "claim")
    assert batch["first_shown_at"] and member["first_shown_at"]
    n = conn.execute("SELECT COUNT(*) FROM agent_observation_outcomes").fetchone()[0]
    assert n > 0  # 按版本/期限的评价占位已建
    assert ob.current_claim_ids(conn, "recommendation") == {member["observation_id"]}
    conn.close()


def test_promotion_supersedes_old_current_no_self_reference(tmp_path):  # noqa: ANN001
    """e3：有旧当前 A 时草稿 B 转正——A 被指向 B，绝不自指；当前集合=B 成员。"""
    conn = connect(tmp_path / "x.db")
    _rec(conn, symbol="A")                     # A 当前（shown）
    _rec(conn, symbol="B", shown=False)        # 草稿 B
    a_id = conn.execute("SELECT observation_id FROM agent_observations "
                        "WHERE instrument_id='A' AND record_type='claim'"
                        ).fetchone()[0]
    assert a_id in ob.current_claim_ids(conn, "recommendation")  # A 仍是当前
    _rec(conn, symbol="B", shown=True)         # B 实际展示 → 转正
    rows = _rows_status(conn)
    for r in rows:
        assert r["superseded_by"] != r["observation_id"]  # 禁止自指
    a_batch = conn.execute(
        "SELECT superseded_by FROM agent_observations WHERE observation_id=?",
        (a_id,)).fetchone()
    # A 的让位记录在「承载 A 的批次」上：当前集合应只剩 B 成员
    cur = ob.current_claim_ids(conn, "recommendation")
    b_id = conn.execute("SELECT observation_id FROM agent_observations "
                        "WHERE instrument_id='B' AND record_type='claim'"
                        ).fetchone()[0]
    assert cur == {b_id}
    assert a_batch is not None
    conn.close()


def test_promotion_repeat_idempotent(tmp_path):  # noqa: ANN001
    """重复转正：不新增时间、占位或展示事件。"""
    conn = connect(tmp_path / "x.db")
    _rec(conn, shown=False, revision="r1")
    _rec(conn, shown=True, revision="r1")
    snap1 = _rows_status(conn)
    n_out1 = conn.execute(
        "SELECT COUNT(*) FROM agent_observation_outcomes").fetchone()[0]
    st = _rec(conn, shown=True, revision="r1")
    assert st["batch_promoted"] == 0  # 未再升级
    snap2 = _rows_status(conn)
    n_out2 = conn.execute(
        "SELECT COUNT(*) FROM agent_observation_outcomes").fetchone()[0]
    assert snap1 == snap2 and n_out1 == n_out2
    conn.close()


def test_promotion_a_b_a_chain(tmp_path):  # noqa: ANN001
    """A→B→A：三次展示顺序保留，当前集合=最后一次展示批次成员。"""
    conn = connect(tmp_path / "x.db")
    _rec(conn, symbol="A")
    _rec(conn, symbol="B")
    _rec(conn, symbol="A")
    batches = conn.execute(
        "SELECT observation_id, previous_batch_id, superseded_by FROM agent_observations "
        "WHERE record_type='display_batch' ORDER BY created_at, rowid").fetchall()
    assert len(batches) == 3
    assert batches[1]["previous_batch_id"] == batches[0]["observation_id"]
    assert batches[2]["previous_batch_id"] == batches[1]["observation_id"]
    cur = ob.current_claim_ids(conn, "recommendation")
    first_members = set(json.loads(batches[0]["observation_id"] == ""
                                    and "[]" or "[]")) if False else None
    members_last = set(json.loads(conn.execute(
        "SELECT batch_members FROM agent_observations WHERE observation_id=?",
        (batches[2]["observation_id"],)).fetchone()[0]))
    assert cur == members_last
    conn.close()


def test_promotion_empty_member_set(tmp_path):  # noqa: ANN001
    """空展示集合：批次可建可转正，成员同步为空操作，不崩。"""
    conn = connect(tmp_path / "x.db")
    ob.record_observations(
        conn, source_type="s", source_record_id="d", observed_at="2026-08-03",
        evaluation_kind=ob.KIND_TECHNICAL_FORWARD, evaluation_version="v1",
        items=[], shown=False)
    st = ob.record_observations(
        conn, source_type="s", source_record_id="d", observed_at="2026-08-03",
        evaluation_kind=ob.KIND_TECHNICAL_FORWARD, evaluation_version="v1",
        items=[], shown=True)
    assert st["batch_promoted"] == 1
    assert ob.current_claim_ids(conn, "s") == set()
    conn.close()


def test_promotion_partial_members_already_shown(tmp_path):  # noqa: ANN001
    """部分成员此前已单独展示：转正只升级仍未展示成员，已展示的首次时间不动。"""
    conn = connect(tmp_path / "x.db")
    # 成员1 先单独展示（同主张，item shown）
    ob.record_observations(
        conn, source_type="s", source_record_id="d", observed_at="2026-08-03",
        evaluation_kind=ob.KIND_TECHNICAL_FORWARD, evaluation_version="v1",
        items=[ob.ObservationItem(instrument_id="A", payload={"close": 1},
                                  claim="c", horizons=(1,))], shown=True)
    m1 = next(iter(ob.current_claim_ids(conn, "s")))
    first1 = conn.execute(
        "SELECT first_shown_at FROM agent_observations WHERE observation_id=?",
        (m1,)).fetchone()[0]
    # 草稿批次含成员1+2（同业务内容 → 去重成员1 + 新成员2，批次 not_shown）
    class _It:
        pass
    it2 = ob.ObservationItem(instrument_id="B", payload={"close": 2},
                             claim="c2", horizons=(1,))
    ob.record_observations(
        conn, source_type="s", source_record_id="d", observed_at="2026-08-03",
        evaluation_kind=ob.KIND_TECHNICAL_FORWARD, evaluation_version="v1",
        items=[ob.ObservationItem(instrument_id="A", payload={"close": 1},
                                  claim="c", horizons=(1,)), it2],
        shown=False)
    # 草稿转正
    ob.record_observations(
        conn, source_type="s", source_record_id="d", observed_at="2026-08-03",
        evaluation_kind=ob.KIND_TECHNICAL_FORWARD, evaluation_version="v1",
        items=[ob.ObservationItem(instrument_id="A", payload={"close": 1},
                                  claim="c", horizons=(1,)), it2],
        shown=True)
    first1_after = conn.execute(
        "SELECT first_shown_at FROM agent_observations WHERE observation_id=?",
        (m1,)).fetchone()[0]
    assert first1_after == first1  # 已展示成员首次时间不被覆盖
    n = conn.execute("SELECT COUNT(*) FROM agent_observations WHERE "
                     "record_type='claim' AND display_status='not_shown'").fetchone()[0]
    assert n == 0  # 未展示成员已全部随批转正
    conn.close()


# ================= e4：脚本复用账本共享投影 =================

def _sentiment_env(tmp_path, rows_changes, *, code="BK1"):
    """构造情绪脚本环境：同一样本多行 ready 结果（rows_changes 按库内顺序）。
    记录时刻固定为 2026-08-03（a4 语义：展示时点晚于查询截止的记录不进视图）。"""
    spec = importlib.util.spec_from_file_location(
        "s09r2_sentiment", REPO / "scripts" / "sentiment_journal.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    db = connect(tmp_path / "probe.db")
    from unittest.mock import patch

    with patch.object(ob, "_now", return_value="2026-08-03T10:00:00+00:00"):
        ob.record_sentiment_day(
            db, date="2026-08-03", picks=[{"code": code, "close": 100.0, "name": "w"}],
            alarms=[])
        rows = [dict(r) for r in db.execute(
            "SELECT oc.observation_id, oc.horizon FROM agent_observation_outcomes oc "
            "JOIN agent_observations o ON o.observation_id=oc.observation_id "
            "WHERE o.record_type='claim' AND oc.evaluation_version=? AND oc.horizon=10",
            (ob.SENTIMENT_ROWS_VERSION,))]
        assert rows, "占位应已建"
        # 同一样本额外措辞修订（不同主张、同 sample_key）再各建一行
        for i in range(len(rows_changes) - 1):
            ob.record_sentiment_day(
                db, date="2026-08-03",
                picks=[{"code": code, "close": 100.0, "name": f"w{i}"}], alarms=[])
    all_ids = [dict(r)["observation_id"] for r in db.execute(
        "SELECT observation_id FROM agent_observations WHERE record_type='claim'")]
    for oid_i, chg in zip(all_ids, rows_changes, strict=False):
        db.execute(
            "UPDATE agent_observation_outcomes SET status='ready', hit=1, "
            "change_pct=?, eval_date='2026-08-17' WHERE observation_id=? AND horizon=10",
            (chg, oid_i))
    db.commit()
    m.CACHE = tmp_path
    m.JOURNAL = tmp_path / "source.json"
    m.JOURNAL.write_text('{"records":[]}')
    (tmp_path / "sector_trend_history.json").write_text("[]")
    m._open_ledger_db = lambda: connect(tmp_path / "probe.db")
    return m, db


@pytest.mark.parametrize("changes", [[10.0, 20.0, 20.0], [20.0, 10.0, 20.0],
                                     [20.0, 20.0, 10.0]])
def test_e4_conflict_locks_regardless_of_order(tmp_path, changes, capsys):  # noqa: ANN001
    """冲突一旦成立，不因下一条与最后值相同而恢复——任意插入顺序均一致。"""
    m, db = _sentiment_env(tmp_path, changes)
    with TemporaryDirectory():
        pass
    m.review(save=False, as_of="2026-08-31")
    text = capsys.readouterr().out
    assert "到期1样本" not in text
    assert "全部样本冲突排除" in text
    pack = ob.forward_stats(db, source_type="sentiment_day",
                            evaluation_version=ob.SENTIMENT_ROWS_VERSION)
    b = [x for x in pack["buckets"] if x["horizon_days"] == 10][0]
    assert b["n_conflict_samples"] == 1 and b["n_ready_samples"] == 0
    db.close()


def test_e4_script_matches_ledger_field_by_field(tmp_path):  # noqa: ANN001
    """脚本统计与账本共享投影逐字段一致（不同规则/配置/legacy/未展示分组）。"""
    m, db = _sentiment_env(tmp_path, [15.0])
    # 不同规则身份（带冻结引用）与 legacy 组、未展示组（均固定展示时点在截止前）
    from unittest.mock import patch

    with patch.object(ob, "_now", return_value="2026-08-04T10:00:00+00:00"):
        ob.record_observations(
            db, source_type="sentiment_day", source_record_id="2026-08-04",
            observed_at="2026-08-04", evaluation_kind=ob.KIND_SENTIMENT_DIRECTION,
            evaluation_version=ob.SENTIMENT_ROWS_VERSION,
            items=[ob.ObservationItem(
                instrument_id="BK2", payload={"close": 50.0}, claim="冰点",
                direction="up", horizons=(10,), scope="cn_sector",
                strategy="情绪观察", claim_class="icepoint_pick",
                rule_refs_frozen=[{"rule_id": "icepoint_pick", "version": "2",
                                   "config_hash": "ff"}])])
        ob.record_sentiment_day(db, date="2026-08-05", legacy=True,
                                picks=[{"code": "BK3", "close": 30.0, "name": "l"}],
                                alarms=[])
        ob.record_sentiment_day(db, date="2026-08-06",
                                picks=[{"code": "BK4", "close": 40.0, "name": "h"}],
                                alarms=[])
    db.execute("UPDATE agent_observation_outcomes SET status='ready', change_pct=5.0, "
               "eval_date='2026-08-20' WHERE evaluation_version=? AND horizon=10 "
               "AND observation_id IN (SELECT observation_id FROM agent_observations "
               "WHERE instrument_id='BK2')", (ob.SENTIMENT_ROWS_VERSION,))
    db.execute("UPDATE agent_observation_outcomes SET status='ready', change_pct=-2.0, "
               "eval_date='2026-08-20' WHERE evaluation_version=? AND horizon=10 "
               "AND observation_id IN (SELECT observation_id FROM agent_observations "
               "WHERE instrument_id='BK3')", (ob.SENTIMENT_ROWS_VERSION,))
    # BK4 保持未展示 → 不进任何统计（display not_shown 不进分母）
    db.commit()
    stats, _ = m.ledger_stats(db, as_of=None)
    pack = ob.forward_stats(db, source_type="sentiment_day",
                            evaluation_version=ob.SENTIMENT_ROWS_VERSION)
    api = {(b["direction"], b["horizon_days"], b["legacy_quality"],
            b["rule_identity"]): b for b in pack["buckets"]}
    for st in stats:
        key = (st["direction"], st["horizon"], st["quality"], st["rule_identity"])
        b = api[key]
        assert st["n_samples"] == b["n_ready_samples"], (st, b)
        assert st["n_conflict"] == b["n_conflict_samples"]
        assert st["changes"] == b["ready_changes"]
    # 未展示不进分母：BK4 不出现在任何桶
    assert all("BK4" not in str(b) for b in pack["buckets"])
    db.close()


# ================= e5：截止日贯通公开查询 =================

def _api(tmp_path):
    from lei_signal.api.routes import copilot

    app = FastAPI()
    app.state.plans_db_path = str(tmp_path / "probe.db")
    app.include_router(copilot.router)
    return TestClient(app)


def test_e5_api_cutoff_filters_summary_recent_and_echoes(tmp_path):  # noqa: ANN001
    from unittest.mock import patch

    conn = connect(tmp_path / "probe.db")
    with patch.object(ob, "_now", return_value="2026-08-03T10:00:00+00:00"):
        _rec(conn)
    conn.execute("UPDATE agent_observation_outcomes SET status='ready', change_pct=10, "
                 "eval_date='2026-08-17' WHERE evaluation_version=?",
                 (ob.RECOMMENDATION_ROWS_VERSION,))
    conn.commit()
    client = _api(tmp_path)
    r = client.get("/api/copilot/observations", params={"as_of": "2026-08-04"})
    assert r.status_code == 200
    body = r.json()
    assert body["as_of"] == "2026-08-04"
    assert body["cutoff"]["excluded_future_results"] >= 1
    assert body["cutoff"]["note"]
    future = [o for item in body["recent"] for o in item.get("outcomes", [])
              if o.get("eval_date", "") and o["eval_date"] > "2026-08-04"]
    assert not future
    ready_buckets = [b for b in body["summary"]["buckets"] if b["n_ready_samples"]]
    assert not ready_buckets  # 当时视图无可计入成绩
    # 未传 as_of：完整视图可见；原值保留在库
    r2 = client.get("/api/copilot/observations")
    full = [o for item in r2.json()["recent"] for o in item.get("outcomes", [])
            if o.get("eval_date") == "2026-08-17"]
    assert full
    row = conn.execute(
        "SELECT change_pct, eval_date, status FROM agent_observation_outcomes "
        "WHERE eval_date='2026-08-17'").fetchone()
    assert (row["change_pct"], row["eval_date"], row["status"]) == (10.0, "2026-08-17", "ready")
    conn.close()


def test_e5_api_invalid_as_of_rejected(tmp_path):  # noqa: ANN001
    connect(tmp_path / "probe.db").close()
    client = _api(tmp_path)
    r = client.get("/api/copilot/observations", params={"as_of": "08/40/2026"})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "INVALID_AS_OF"


def test_e5_current_reconstructed_by_cutoff(tmp_path):  # noqa: ANN001
    """晚于截止才展示的批次不冒充当时看到的内容：as-of 当前=此前批次成员。
    契约生效后成员可见性由关系首展决定——测试同时固定批次与关系时点。"""
    conn = connect(tmp_path / "x.db")
    _rec(conn, symbol="A")                  # 展示时刻下面按批次/关系手工固定
    _rec(conn, symbol="B")
    batches = [r["observation_id"] for r in conn.execute(
        "SELECT observation_id FROM agent_observations "
        "WHERE record_type='display_batch' ORDER BY rowid")]
    for bid, fs in ((batches[0], "2026-08-03T09:00:00+00:00"),
                    (batches[1], "2026-08-10T09:00:00+00:00")):
        conn.execute("UPDATE agent_observations SET first_shown_at=? "
                     "WHERE observation_id=?", (fs, bid))
        conn.execute("UPDATE agent_observation_batch_members SET first_shown_at=? "
                     "WHERE batch_id=?", (fs, bid))
    conn.commit()
    ids_early, unk = ob.current_claim_ids_as_of(conn, "2026-08-05",
                                                source_type="recommendation")
    ids_late, _ = ob.current_claim_ids_as_of(conn, "2026-08-11",
                                             source_type="recommendation")
    a_id = conn.execute("SELECT observation_id FROM agent_observations "
                        "WHERE instrument_id='A'").fetchone()[0]
    b_id = conn.execute("SELECT observation_id FROM agent_observations "
                        "WHERE instrument_id='B'").fetchone()[0]
    assert ids_early == {a_id} and not unk
    assert ids_late == {b_id}
    # 展示时间未知（整链无可定位批次与关系）→ 来源标 unknown，不用今天的 current 顶替
    conn.execute("UPDATE agent_observations SET first_shown_at=NULL "
                 "WHERE record_type='display_batch'")
    conn.execute("UPDATE agent_observation_batch_members SET first_shown_at=NULL")
    conn.commit()
    _, unk2 = ob.current_claim_ids_as_of(conn, "2026-08-05",
                                         source_type="recommendation")
    assert unk2 == ["recommendation:2026-08-03"]
    conn.close()


def test_e5_boundary_eval_date_equal_as_of_included(tmp_path):  # noqa: ANN001
    from unittest.mock import patch

    conn = connect(tmp_path / "probe.db")
    with patch.object(ob, "_now", return_value="2026-08-03T10:00:00+00:00"):
        _rec(conn)
    conn.execute("UPDATE agent_observation_outcomes SET status='ready', change_pct=3, "
                 "eval_date='2026-08-04' WHERE evaluation_version=?",
                 (ob.RECOMMENDATION_ROWS_VERSION,))
    conn.commit()
    s = ob.summarize(conn, as_of="2026-08-04")
    ready = [b for b in s["buckets"] if b["n_ready_samples"]]
    assert ready and s["cutoff"]["excluded_future_results"] == 0
    conn.close()


def test_e5_bad_value_rows_excluded_counted(tmp_path):  # noqa: ANN001
    """坏值（非有限 ready 涨跌）不进统计且可识别计数（e4 坏值项）。"""
    conn = connect(tmp_path / "probe.db")
    _rec(conn)
    conn.execute("UPDATE agent_observation_outcomes SET status='ready', change_pct=1e999 "
                 "WHERE evaluation_version=?", (ob.RECOMMENDATION_ROWS_VERSION,))
    conn.commit()
    pack = ob.forward_stats(conn, source_type="recommendation")
    assert all(b["n_ready_samples"] == 0 for b in pack["buckets"])
    assert pack["cutoff"]["excluded_bad_value_rows"] >= 1
    conn.close()


# ================= 09R2 补修（a1—a8）交叉测试 =================

def _statuses(conn):
    return {r["observation_id"]: dict(r) for r in conn.execute(
        "SELECT observation_id, record_type, instrument_id, display_status, "
        "first_shown_at FROM agent_observations")}


def test_a2_keyed_unshown_retry_stays_draft(tmp_path):  # noqa: ANN001
    """a2：同键连续 shown=False——批次/成员保持草稿，无首展时间、零占位。
    带键/无键两路都从数据库核对，不信返回值。"""
    for keyed in (True, False):
        conn = connect(tmp_path / f"k{keyed}.db")
        kw = {"revision": "d1"} if keyed else {}
        _rec(conn, shown=False, **kw)
        st = _rec(conn, shown=False, **kw)
        assert st.get("batch_promoted", 0) == 0
        rows = _statuses(conn)
        assert all(r["display_status"] == "not_shown" for r in rows.values()), keyed
        n = conn.execute("SELECT COUNT(*) FROM agent_observation_outcomes"
                         ).fetchone()[0]
        assert n == 0, keyed
        # 用户出口：当前集合为空（草稿不是当前）
        assert ob.current_claim_ids(conn, "recommendation") == set()
        conn.close()


def test_a2_shown_then_unshown_retry_keeps_shown(tmp_path):  # noqa: ANN001
    """a2 另一路：先展示、后同键 shown=False 重试——展示状态与首展时间不变。"""
    conn = connect(tmp_path / "x.db")
    _rec(conn, shown=False, revision="d1")
    _rec(conn, shown=True, revision="d1")
    before = _statuses(conn)
    st = _rec(conn, shown=False, revision="d1")
    assert st.get("batch_promoted", 0) == 0
    assert _statuses(conn) == before
    conn.close()


def test_a3_explicitly_hidden_member_not_promoted(tmp_path):  # noqa: ANN001
    """a3：A 授权、B 明确 shown=False——只升 A；B 不进成绩；带键/无键一致；
    从数据库与用户出口（summarize 桶）双核对。"""
    for keyed in (True, False):
        conn = connect(tmp_path / f"k{keyed}.db")
        kw = {"revision": "m1"} if keyed else {}
        _rec(conn, shown=False, symbols=("A", "B"), flags={"B": False}, **kw)
        _rec(conn, shown=True, symbols=("A", "B"), flags={"B": False}, **kw)
        rows = _statuses(conn)
        claims = {r["instrument_id"]: r for r in rows.values()
                  if r["record_type"] == "claim"}
        assert claims["A"]["display_status"] == "shown", keyed
        assert claims["B"]["display_status"] == "not_shown", keyed
        nb = conn.execute(
            "SELECT COUNT(*) FROM agent_observation_outcomes WHERE observation_id=?",
            (claims["B"]["observation_id"],)).fetchone()[0]
        assert nb == 0, keyed
        s = ob.summarize(conn)
        assert all(b["n_observations"] <= 1 for b in s["buckets"])  # B 不进桶
        # 已展示成员之后才首次展示：补成员事件与占位
        _rec(conn, shown=True, symbols=("A", "B"), flags={"B": True}, **kw)
        rows2 = _statuses(conn)
        claims2 = {r["instrument_id"]: r for r in rows2.values()
                   if r["record_type"] == "claim"}
        nb2 = conn.execute(
            "SELECT COUNT(*) FROM agent_observation_outcomes WHERE observation_id=?",
            (claims2["B"]["observation_id"],)).fetchone()[0]
        assert nb2 > 0, keyed  # B 本次授权 → 补占位
        conn.close()


def test_a3_material_update_still_matches_member(tmp_path):  # noqa: ANN001
    """a3：冻结引用（材料）更新后重试——稳定成员键不受材料变化影响，
    首次保存的成员仍被正确匹配授权，不产生对不上的新 ID。"""
    conn = connect(tmp_path / "x.db")
    frozen_a = [{"rule_id": "r", "version": "1", "config_hash": "a"}]
    frozen_b = [{"rule_id": "r", "version": "9", "config_hash": "z"}]
    _rec(conn, shown=False, symbols=("A",), frozen=frozen_a)
    _rec(conn, shown=True, symbols=("A",), frozen=frozen_b)
    rows = _statuses(conn)
    member = next(r for r in rows.values() if r["record_type"] == "claim")
    assert member["display_status"] == "shown"
    saved = json.loads(conn.execute(
        "SELECT rule_refs_frozen FROM agent_observations WHERE observation_id=?",
        (member["observation_id"],)).fetchone()[0])
    assert saved == frozen_a  # 首次引用不变（Q2 不倒退）
    conn.close()


def test_a1_http_filter_combinations(tmp_path):  # noqa: ANN001
    """a1：来源/标的/截止组合与空来源均可查，不再 500。"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from lei_signal.api.routes import copilot

    conn = connect(tmp_path / "probe.db")
    _rec(conn)
    conn.close()
    app = FastAPI()
    app.state.plans_db_path = str(tmp_path / "probe.db")
    app.include_router(copilot.router)
    client = TestClient(app, raise_server_exceptions=False)
    for params in ({}, {"source_type": "recommendation"},
                   {"source_type": "sentiment_day"},
                   {"instrument": "A"}, {"instrument": "NOPE"},
                   {"source_type": "recommendation", "instrument": "A"},
                   {"as_of": "2026-09-01"},
                   {"source_type": "recommendation", "as_of": "2026-09-01"},
                   {"source_type": "recommendation", "instrument": "A",
                    "as_of": "2026-09-01"}):
        r = client.get("/api/copilot/observations", params=params)
        assert r.status_code == 200, (params, r.text[:200])
        body = r.json()
        assert "summary" in body and "recent" in body
        if params.get("source_type") == "sentiment_day":
            assert body["summary"]["buckets"] == []  # 空来源组可查


def test_a5_cutoff_filter_before_limit(tmp_path):  # noqa: ANN001
    """a5：超过 limit 的未来记录不把历史记录挤出当时窗口；superseded 按当时链。"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from unittest.mock import patch
    from lei_signal.api.routes import copilot

    conn = connect(tmp_path / "probe.db")
    with patch.object(ob, "_now", return_value="2026-08-03T10:00:00+00:00"):
        _rec(conn, symbol="A")
        _rec(conn, symbol="A2")
        _rec(conn, symbol="A3")
    with patch.object(ob, "_now", return_value="2026-08-20T10:00:00+00:00"):
        for sym in ("B1", "B2", "B3"):
            _rec(conn, symbol=sym)
    conn.commit()
    app = FastAPI()
    app.state.plans_db_path = str(tmp_path / "probe.db")
    app.include_router(copilot.router)
    client = TestClient(app)
    r = client.get("/api/copilot/observations",
                   params={"as_of": "2026-08-04", "limit": 2})
    assert r.status_code == 200
    items = r.json()["recent"]
    assert items, "历史记录不得被未来记录挤出"
    assert all((x["first_shown_at"] or x["created_at"])[:10] <= "2026-08-04"
               for x in items)
    # superseded 按当时展示链：A 系在截止时未被替代（B 系 08-20 才展示）
    a_items = [x for x in items if x["instrument_id"] in ("A", "A2", "A3")]
    assert all(not x["superseded"] for x in a_items)
    conn.close()


def test_a6_strict_as_of_formats(tmp_path):  # noqa: ANN001
    """a6：非标准格式 422（含 2026-8-4/带时间/空串/非法日/闰日错年），
    标准合法日期放行；非法格式不得原样比较泄漏未来结果。"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from lei_signal.api.routes import copilot

    conn = connect(tmp_path / "probe.db")
    _rec(conn)
    conn.execute("UPDATE agent_observation_outcomes SET status='ready', "
                 "change_pct=10, eval_date='2026-08-17' WHERE evaluation_version=?",
                 (ob.RECOMMENDATION_ROWS_VERSION,))
    conn.commit()
    conn.close()
    app = FastAPI()
    app.state.plans_db_path = str(tmp_path / "probe.db")
    app.include_router(copilot.router)
    client = TestClient(app, raise_server_exceptions=False)
    for bad in ("2026-8-4", "2026-08-4", "26-08-04", "2026-08-04T10:00",
                "", "2026-02-30", "2023-02-29", "20260804", "abc"):
        r = client.get("/api/copilot/observations", params={"as_of": bad})
        assert r.status_code == 422, (bad, r.status_code)
        assert r.json()["detail"]["code"] == "INVALID_AS_OF"
        leaked = [x for item in (r.json().get("recent") or [])
                  for x in item.get("outcomes", [])
                  if x.get("eval_date") == "2026-08-17"]
        assert not leaked, bad  # 非法格式不返回任何视图
    ok = client.get("/api/copilot/observations", params={"as_of": "2024-02-29"})
    assert ok.status_code == 200  # 合法闰日放行
    with pytest.raises(ValueError):
        ob.normalize_as_of("2026-8-4")
    assert ob.normalize_as_of("2026-08-04") == "2026-08-04"


def test_a7_claim_class_change_new_claim_and_sample(tmp_path):  # noqa: ANN001
    """a7：业务字段在三层身份中的使用——只换 claim_class：新批次 + 新主张 +
    新样本键（不得只建批次复用旧主张）。"""
    conn = connect(tmp_path / "x.db")
    _rec(conn, cls="class_one")
    _rec(conn, cls="class_two")
    claims = _claims(conn)
    assert len(claims) == 2
    sks = {r["sample_key"] for r in conn.execute(
        "SELECT sample_key FROM agent_observations WHERE record_type='claim'")}
    assert len(sks) == 2
    nb = conn.execute("SELECT COUNT(*) FROM agent_observations "
                      "WHERE record_type='display_batch'").fetchone()[0]
    assert nb == 2
    conn.close()


def test_a8_single_review_call_output_matches_final_db(tmp_path, capsys):  # noqa: ANN001
    """a8：一次 review(save=True) 内先同步/评价再输出——本次补出的成绩
    出现在同一次输出中，且与调用结束后的数据库一致。"""
    spec = importlib.util.spec_from_file_location(
        "a8_sentiment", REPO / "scripts" / "sentiment_journal.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    from unittest.mock import patch

    m.CACHE = tmp_path
    m.JOURNAL = tmp_path / "sentiment.json"
    m._open_ledger_db = lambda: connect(tmp_path / "probe.db")
    import pandas as pd

    dates = [x.strftime("%Y-%m-%d") for x in pd.bdate_range("2026-08-03", periods=22)]
    (tmp_path / "sector_trend_history.json").write_text(json.dumps(
        [{"date": d, "boards": {"A": {"close": 100 + i}}}
         for i, d in enumerate(dates)]))
    source = {"records": [{"date": "2026-08-03", "origin": "live",
                           "picks": [{"code": "A", "close": 100, "name": "A"}],
                           "alarms": []}]}
    m.JOURNAL.write_text(json.dumps(source))
    with patch.object(ob, "_now", return_value="2026-08-03T10:00:00+00:00"):
        ok2, note2 = m._sync_observations(source)
    assert ok2, note2
    log = io.StringIO()
    with redirect_stdout(log):
        m.review(save=True, as_of=dates[-1])
    text = log.getvalue()
    db = connect(tmp_path / "probe.db")
    pack = ob.forward_stats(db, source_type="sentiment_day",
                            evaluation_version=ob.SENTIMENT_ROWS_VERSION,
                            as_of=dates[-1])
    db.close()
    db_samples = sum(b["n_ready_samples"] for b in pack["buckets"])
    assert db_samples == 2  # 10/20 日两档已成熟
    assert "到期1样本" in text  # 10日档：100→110 = +10% 命中
    assert "到期" in text and "样本" in text
    # 输出与最终数据库一致：10日、20日两行都打印
    assert "10日" in text and "20日" in text


def test_a8_review_dry_run_zero_write_and_readonly_note(tmp_path, capsys):  # noqa: ANN001
    """a8：dry-run（save=False）零写入，并明确只读已有记录。"""
    spec = importlib.util.spec_from_file_location(
        "a8d_sentiment", REPO / "scripts" / "sentiment_journal.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.CACHE = tmp_path
    m.JOURNAL = tmp_path / "sentiment.json"
    m.JOURNAL.write_text(json.dumps({"records": []}))
    (tmp_path / "sector_trend_history.json").write_text("[]")
    from unittest.mock import patch

    calls = {"sync": 0}
    orig = m._sync_observations

    def counted(j):
        calls["sync"] += 1
        return orig(j)

    m._sync_observations = counted
    with patch.object(ob, "_now", return_value="2026-08-03T10:00:00+00:00"):
        m.review(save=False, as_of="2026-08-31")
    text = capsys.readouterr().out
    assert calls["sync"] == 0  # dry-run 不触发任何同步/评价写入
    assert "只读" in text
    # dry-run 未新建观察账本（无任何连接建立）
    probe_db = tmp_path / "probe.db"
    assert not probe_db.exists()


def test_journal_load_outcome_as_of_explicit_unsupported(tmp_path):  # noqa: ANN001
    """旧成绩读取入口：带 as_of 时显式不支持（不静默返回无截止结果冒充当时）。"""
    from lei_signal.copilot import journal

    conn = connect(tmp_path / "x.db")
    card = {"run_date": "2026-08-03", "items": [{"symbol": "A"}]}
    from lei_signal.copilot.journal import _payload_hash

    digest = _payload_hash(json.dumps(card, ensure_ascii=False, sort_keys=True))
    conn.execute(
        "INSERT INTO recommendation_journal (journal_id, run_date, payload, "
        "payload_hash, outcome, outcome_payload_hash, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        ("rj_x", "2026-08-03", json.dumps(card), digest,
         json.dumps({"A": {"chg_1d": 1.0}}), digest,
         "2026-08-03", "2026-08-03"))
    conn.commit()
    # 无截止：完整结果（既有语义不变）
    full = journal.load_outcome(conn, "2026-08-03")
    assert full == {"A": {"chg_1d": 1.0}}
    # 带截止：显式不支持 + 原值保留，不冒充当时视图
    hist = journal.load_outcome(conn, "2026-08-03", as_of="2026-08-04")
    assert hist["supported"] is False
    assert hist["as_of"] == "2026-08-04"
    assert hist["outcome_untimed"] == {"A": {"chg_1d": 1.0}}
    conn.close()


# ================= 09R2 成员契约（b1—b4）交叉测试 =================

def _relations(conn, batch_id=None):
    sql = ("SELECT batch_id, observation_id, member_key, member_identity_version, "
           "first_shown_at, visibility_quality FROM agent_observation_batch_members")
    args: list = []
    if batch_id:
        sql += " WHERE batch_id = ?"
        args.append(batch_id)
    return [dict(x) for x in conn.execute(sql, args)]


def test_contract_relations_written_for_every_member(tmp_path):  # noqa: ANN001
    """契约 §1/§3.1：新批次每个成员都有关系行（known；含非空 member_key 与
    身份版本）；授权成员有首展、未授权成员为空。"""
    conn = connect(tmp_path / "x.db")
    _rec(conn, shown=False, symbols=("A", "B"), flags={"B": False})
    _rec(conn, shown=True, symbols=("A", "B"), flags={"B": False})
    rels = _relations(conn)
    assert len(rels) == 2  # 草稿批 + 展示批，各 2 成员
    assert all(r["member_key"] and r["member_identity_version"] == "v1"
               and r["visibility_quality"] == "known" for r in rels)
    shown_rels = [r for r in rels if r["first_shown_at"]]
    assert len(shown_rels) == 1  # 只有 A 授权
    a_obs = conn.execute("SELECT observation_id FROM agent_observations "
                         "WHERE instrument_id='A'").fetchone()[0]
    assert shown_rels[0]["observation_id"] == a_obs
    conn.close()


def test_contract_b1_hidden_category_separate_authorization(tmp_path):  # noqa: ANN001
    """b1：同标的同类原文不同类别 = 不同 member_key；隐藏类别不进成绩；
    稍后单独授权时补该类别的成员事件与占位（其他类别不重复记时）。"""
    conn = connect(tmp_path / "x.db")
    items = lambda f: [  # noqa: E731
        ob.ObservationItem(instrument_id="A", claim="watch",
                           payload={"close": 100}, claim_class="one",
                           horizons=(1,), shown=True),
        ob.ObservationItem(instrument_id="A", claim="watch",
                           payload={"close": 100}, claim_class="two",
                           horizons=(1,), shown=f),
    ]
    ob.record_observations(
        conn, source_type="recommendation", source_record_id="2026-08-03",
        observed_at="2026-08-03", evaluation_kind=ob.KIND_TECHNICAL_FORWARD,
        evaluation_version=ob.RECOMMENDATION_EVAL_VERSION,
        items=items(False), revision_key="two_cats", shown=True)
    two_claims = [dict(x) for x in conn.execute(
        "SELECT observation_id, display_status, first_shown_at FROM agent_observations "
        "WHERE record_type='claim'")]
    assert len(two_claims) == 2
    shown_n = sum(1 for x in two_claims if x["display_status"] == "shown")
    assert shown_n == 1
    # 稍后授权第二类别
    ob.record_observations(
        conn, source_type="recommendation", source_record_id="2026-08-03",
        observed_at="2026-08-03", evaluation_kind=ob.KIND_TECHNICAL_FORWARD,
        evaluation_version=ob.RECOMMENDATION_EVAL_VERSION,
        items=items(True), revision_key="two_cats", shown=True)
    two = [x for x in conn.execute(
        "SELECT display_status, first_shown_at FROM agent_observations "
        "WHERE record_type='claim'")]
    assert all(x["display_status"] == "shown" for x in two)
    n_out = conn.execute("SELECT COUNT(*) FROM agent_observation_outcomes"
                         ).fetchone()[0]
    assert n_out == 4  # 2 主张 × (严格+行参考) 各 1 期限
    conn.close()


def test_contract_member_conflict_contradictory_flags(tmp_path):  # noqa: ANN001
    """契约 §2：同一批相同业务成员矛盾 shown 标志 → 显式冲突，零写入。"""
    conn = connect(tmp_path / "x.db")
    st = ob.record_observations(
        conn, source_type="recommendation", source_record_id="2026-08-03",
        observed_at="2026-08-03", evaluation_kind=ob.KIND_TECHNICAL_FORWARD,
        evaluation_version=ob.RECOMMENDATION_EVAL_VERSION,
        items=[ob.ObservationItem(instrument_id="A", claim="watch",
                                  payload={"close": 100}, claim_class="one",
                                  horizons=(1,), shown=True),
               ob.ObservationItem(instrument_id="A", claim="watch",
                                  payload={"close": 100}, claim_class="one",
                                  horizons=(1,), shown=False)],
        shown=True)
    assert st["member_conflict"] == 1
    n = conn.execute("SELECT COUNT(*) FROM agent_observations").fetchone()[0]
    assert n == 0
    conn.close()


def test_contract_rollback_no_partial_upgrade(tmp_path):  # noqa: ANN001
    """契约 §3.5：批次/关系/主张同事务——调用方回滚后无半升级残留。"""
    from unittest.mock import patch

    conn = connect(tmp_path / "x.db")
    conn.execute("BEGIN IMMEDIATE")
    with patch.object(ob, "_outcome_placeholders_for",
                      side_effect=RuntimeError("boom")):
        try:
            ob.record_observations(
                conn, source_type="recommendation", source_record_id="2026-08-03",
                observed_at="2026-08-03", evaluation_kind=ob.KIND_TECHNICAL_FORWARD,
                evaluation_version=ob.RECOMMENDATION_EVAL_VERSION,
                items=[ob.ObservationItem(instrument_id="A", claim="watch",
                                          payload={"close": 100},
                                          horizons=(1,))],
                shown=True)
        except RuntimeError:
            conn.rollback()
    for table in ("agent_observations", "agent_observation_batch_members",
                  "agent_observation_outcomes"):
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert n == 0, table  # 无只升级了一半的残留
    conn.close()


def test_contract_same_sample_multi_display_single_sample(tmp_path):  # noqa: ANN001
    """不同批复用同一主张（新批追加新成员）：当前可见集合正确、累计样本仍 1
    （不因新增批次关系重复计样本）。"""
    conn = connect(tmp_path / "x.db")
    _rec(conn, symbol="A")              # 批次1：A
    _rec(conn, symbols=("A", "C"))      # 批次2：A 复用 + C 新（业务变化→新批）
    cur = ob.current_claim_ids(conn, "recommendation")
    assert len(cur) == 2  # A（复用授权）+ C
    a_id = conn.execute("SELECT observation_id FROM agent_observations "
                        "WHERE instrument_id='A'").fetchone()[0]
    rels_a = _relations(conn)
    assert sum(1 for r in rels_a if r["observation_id"] == a_id) == 2  # A 在两批各有关系
    s = ob.summarize(conn)
    # A、C 各一条主张 → 每桶 n_samples = 不同主张数（2）；关系翻倍不翻样本
    assert all(b["n_samples"] == 2 for b in s["buckets"])  # 样本不重复计
    conn.close()


def test_contract_legacy_as_of_untimed_and_full_view(tmp_path):  # noqa: ANN001
    """b3（HTTP 级）：legacy 主张截止视图 ready 移入 outcomes_untimed；
    完整视图原值独立可查；summary 与 recent 同一判断。"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from unittest.mock import patch
    from lei_signal.api.routes import copilot

    conn = connect(tmp_path / "probe.db")
    with patch.object(ob, "_now", return_value="2026-08-20T10:00:00+00:00"):
        ob.record_sentiment_day(conn, date="2026-08-03",
                                picks=[{"code": "A", "close": 100, "name": "A"}],
                                alarms=[], legacy=True)
        ob.evaluate_sentiment_outcomes(
            conn, lambda code, d, h: ("2026-08-17" if h == 10 else "2026-08-31", 110),
            as_of="2026-08-20")
    conn.commit()
    # 关系为 unknown（legacy 无法证明逐批展示）
    rels = _relations(conn)
    assert rels and all(r["visibility_quality"] == "unknown"
                        and r["first_shown_at"] is None for r in rels)
    app = FastAPI()
    app.state.plans_db_path = str(tmp_path / "probe.db")
    app.include_router(copilot.router)
    client = TestClient(app)
    cut = client.get("/api/copilot/observations", params={"as_of": "2026-08-18"}).json()
    ready_now = [o for r in cut["recent"] for o in r.get("outcomes", [])
                 if o["status"] == "ready"]
    assert not ready_now
    untimed = [o for r in cut["recent"] for o in r.get("outcomes_untimed", [])]
    assert untimed and all(o["supported_for_as_of"] is False for o in untimed)
    assert sum(b["n_ready_samples"] for b in cut["summary"]["buckets"]) == 0
    full = client.get("/api/copilot/observations").json()
    ready_full = [o for r in full["recent"] for o in r.get("outcomes", [])
                  if o["status"] == "ready"]
    assert ready_full  # 完整视图原值可查
    conn.close()


def test_contract_pre_migration_batch_degrades_honestly(tmp_path):  # noqa: ANN001
    """§6：旧批次（关系被清空=迁移前状态）不参与成员级可见集合；
    完整视图原值照常可查——降级诚实而非丢失。"""
    conn = connect(tmp_path / "x.db")
    _rec(conn, symbol="A")
    conn.execute("DELETE FROM agent_observation_batch_members")  # 模拟迁移前旧批
    conn.commit()
    assert ob.current_claim_ids(conn, "recommendation") == set()  # 诚实：无法证明
    rows = conn.execute("SELECT COUNT(*) FROM agent_observations").fetchone()[0]
    assert rows == 2  # 原文/主张保留（原值可查）
    recents = ob.recent_observations(conn)
    assert any(r["record_type"] == "display_batch" for r in recents)
    conn.close()


def test_contract_api_current_matches_relations(tmp_path):  # noqa: ANN001
    """契约 §4：API current/summary 与存储关系一致（真实 HTTP 出口）。"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from lei_signal.api.routes import copilot

    conn = connect(tmp_path / "probe.db")
    _rec(conn, shown=False, symbols=("A", "B"), flags={"B": False})
    _rec(conn, shown=True, symbols=("A", "B"), flags={"B": False})
    conn.commit()
    app = FastAPI()
    app.state.plans_db_path = str(tmp_path / "probe.db")
    app.include_router(copilot.router)
    body = TestClient(app).get("/api/copilot/observations").json()
    n_api = body["summary"]["current_observations"].get("recommendation", 0)
    n_db = len(ob.current_claim_ids(conn, "recommendation"))
    assert n_api == n_db == 1  # 只数真正可见成员（B 明确未展示）
    conn.close()


# ================= 09R2 旧库升级保护（c1/c2）交叉测试 =================

def _real_migrate(conn):
    """真实 025→026 升级：删 026 新表与迁移标记，重跑 apply_migrations
    （总控同一夹具方式）——非 DELETE 关系行模拟；二次执行幂等。"""
    from lei_signal.storage import sqlite_store as st

    conn.execute("DROP TABLE agent_observation_batch_members")
    conn.execute("DELETE FROM schema_migrations WHERE ordinal=26")
    conn.commit()
    first = st.apply_migrations(conn)
    second = st.apply_migrations(conn)
    assert first == ("026_agent_observation_batch_members",) and second == ()
    rels = [dict(r) for r in conn.execute(
        "SELECT visibility_quality, first_shown_at, member_key "
        "FROM agent_observation_batch_members")]
    assert rels and all(r == {"visibility_quality": "unknown",
                              "first_shown_at": None, "member_key": ""}
                        for r in rels)
    return rels


def test_c1_unified_as_of_judgment_after_real_upgrade(tmp_path):  # noqa: ANN001
    """c1：真实升级后，旧主张（全局首展早于截止、关系 unknown）在汇总与
    明细得到同一结论：均不进当时分母；unknown 成员计数可见；原值保留。"""
    import pandas as pd
    from types import SimpleNamespace
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from unittest.mock import patch
    from lei_signal.api.routes import copilot

    conn = connect(tmp_path / "probe.db")
    with patch.object(ob, "_now", return_value="2026-08-03T10:00:00+00:00"):
        _rec(conn)
    frame = pd.DataFrame({"close": [100, 110]},
                         index=pd.to_datetime(["2026-08-03", "2026-08-04"]))
    svc = SimpleNamespace(get=lambda _: SimpleNamespace(
        result=SimpleNamespace(frame=frame)))
    ob.evaluate_recommendation_outcomes(conn, svc, as_of="2026-08-05")
    conn.commit()
    before = [dict(r) for r in conn.execute("SELECT * FROM agent_observation_outcomes")]
    _real_migrate(conn)
    after = [dict(r) for r in conn.execute("SELECT * FROM agent_observation_outcomes")]
    assert before == after  # 升级不改任何成绩
    app = FastAPI()
    app.state.plans_db_path = str(tmp_path / "probe.db")
    app.include_router(copilot.router)
    body = TestClient(app).get(
        "/api/copilot/observations", params={"as_of": "2026-08-05"}).json()
    assert sum(b["n_ready_samples"] for b in body["summary"]["buckets"]) == 0
    ready = [o for r in body["recent"] for o in r.get("outcomes", [])
             if o["status"] == "ready"]
    untimed = [o for r in body["recent"] for o in r.get("outcomes_untimed", [])]
    assert not ready and untimed  # 两出口同一结论
    assert untimed[0]["supported_for_as_of"] is False
    assert untimed[0]["change_pct"] == 10.0  # 原值保留
    assert body["summary"]["cutoff"]["excluded_unknown_first_shown"] >= 1
    assert body["summary"]["current_observations_unknown_members"] >= 1
    conn.close()


def test_c2_old_draft_retry_rejected_before_mutation(tmp_path):  # noqa: ANN001
    """c2：旧草稿（unknown 关系）带键重试——先校验后变更：结构化拒绝、
    零写入，正常 B 当前保持，旧 A 仍是草稿（首展/占位不动）。"""
    from unittest.mock import patch

    conn = connect(tmp_path / "probe.db")
    with patch.object(ob, "_now", return_value="2026-08-03T10:00:00+00:00"):
        _rec(conn, shown=False, revision="old")     # 旧 A 草稿（带键 'old'）
    a_batch = dict(conn.execute(
        "SELECT observation_id, display_status, first_shown_at, superseded_by "
        "FROM agent_observations WHERE record_type='display_batch'").fetchone())
    _real_migrate(conn)
    with patch.object(ob, "_now", return_value="2026-08-03T11:00:00+00:00"):
        _rec(conn, symbol="B")  # 正常新 B（无键）
    before = ob.current_claim_ids(conn, "recommendation")
    with patch.object(ob, "_now", return_value="2026-08-03T12:00:00+00:00"):
        result = _rec(conn, revision="old", shown=True)
    assert result.get("member_match_unknown") == 1
    assert result["batch_promoted"] == 0 and result["batch_reused"] == 0
    assert "无法匹配" in result["reason"]
    assert ob.current_claim_ids(conn, "recommendation") == before  # 当前不动
    a_after = conn.execute(
        "SELECT display_status, first_shown_at, superseded_by "
        "FROM agent_observations WHERE observation_id=?",
        (a_batch["observation_id"],)).fetchone()
    assert a_after["display_status"] == "not_shown"   # 旧 A 仍是草稿
    assert a_after["first_shown_at"] is None
    assert a_after["superseded_by"] is None           # 未抢当前
    a_claim = conn.execute(
        "SELECT observation_id FROM agent_observations "
        "WHERE instrument_id='A' AND record_type='claim'").fetchone()[0]
    n_a = conn.execute("SELECT COUNT(*) FROM agent_observation_outcomes "
                       "WHERE observation_id=?", (a_claim,)).fetchone()[0]
    assert n_a == 0  # 旧 A 零占位（B 的合法占位不计）
    conn.close()


def test_c2_empty_display_set_still_legitimate(tmp_path):  # noqa: ANN001
    """契约：真正空展示集合（items=[]）与「非空成员匹配失败」不混淆——
    前者仍可正常记批并转正。"""
    conn = connect(tmp_path / "probe.db")
    ob.record_observations(
        conn, source_type="s", source_record_id="d", observed_at="2026-08-03",
        evaluation_kind=ob.KIND_TECHNICAL_FORWARD, evaluation_version="v1",
        items=[], shown=False, revision_key="empty1")
    st = ob.record_observations(
        conn, source_type="s", source_record_id="d", observed_at="2026-08-03",
        evaluation_kind=ob.KIND_TECHNICAL_FORWARD, evaluation_version="v1",
        items=[], shown=True, revision_key="empty1")
    assert st.get("member_match_unknown") is None
    assert st["batch_promoted"] == 1
    assert ob.current_claim_ids(conn, "s") == set()  # 空集合就是空
    conn.close()


def test_c2_sync_surfaces_rejection_not_success(tmp_path):  # noqa: ANN001
    """封装不得吞掉拒绝：_sync_observations 遇 member_match_unknown 按失败
    计数并带原因，不打印同步成功。"""
    import importlib.util
    from unittest.mock import patch

    spec = importlib.util.spec_from_file_location(
        "c2_sentiment", REPO / "scripts" / "sentiment_journal.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    conn = connect(tmp_path / "probe.db")
    # 旧情绪草稿：修订键与业务成员语义与 _sync_observations 将产生的完全一致
    with patch.object(ob, "_now", return_value="2026-08-03T10:00:00+00:00"):
        ob.record_observations(
            conn, source_type="sentiment_day", source_record_id="2026-08-03",
            observed_at="2026-08-03", evaluation_kind=ob.KIND_SENTIMENT_DIRECTION,
            evaluation_version=ob.SENTIMENT_EVAL_VERSION,
            revision_key="2026-08-03#v1:same-input", shown=False,
            input_hash="same-input",
            batch_payload={"picks": [{"code": "A", "close": 100.0}],
                           "alarms": [], "date": "2026-08-03"},
            items=[ob.ObservationItem(
                instrument_id="A", payload={"code": "A", "close": 100.0},
                claim="冰点机会（看涨观察）：A", direction="up",
                horizons=(10, 20), scope="cn_sector", strategy="情绪观察",
                claim_class="icepoint_pick",
                rule_refs=["docs/experiments/retail-sentiment-ts-2026-09-05.md"],
                evidence_refs=["configs/sentiment_evidence.json"])])
    _real_migrate(conn)
    m._open_ledger_db = lambda: connect(tmp_path / "probe.db")
    fixture = {"records": [{
        "date": "2026-08-03", "picks": [{"code": "A", "close": 100.0}],
        "alarms": [], "origin": "live", "content_hash": "same-input",
        "as_of": "2026-08-03T18:00:00+08:00"}]}
    ok, note = m._sync_observations(fixture)
    assert not ok, "拒绝不得包装成同步成功"
    assert "无法匹配" in note or "unknown" in note.lower()
    conn.close()


def test_c1_unproven_rows_summary_recent_consistent(tmp_path):  # noqa: ANN001
    """c1：unknown 关系主张在 as_of 下——summary 桶零 ready、cutoff 计数
    与 recent outcomes_untimed 一致；完整视图照常。"""
    from unittest.mock import patch

    conn = connect(tmp_path / "probe.db")
    with patch.object(ob, "_now", return_value="2026-08-03T10:00:00+00:00"):
        _rec(conn)
    conn.execute("UPDATE agent_observation_outcomes SET status='ready', "
                 "change_pct=7, eval_date='2026-08-04' WHERE evaluation_version=?",
                 (ob.RECOMMENDATION_ROWS_VERSION,))
    conn.commit()
    _real_migrate(conn)
    s = ob.summarize(conn, as_of="2026-08-05")
    assert sum(b["n_ready_samples"] for b in s["buckets"]) == 0
    assert s["cutoff"]["excluded_unknown_first_shown"] >= 1
    rec = ob.recent_observations(conn, as_of="2026-08-05")
    assert not [o for r in rec for o in r.get("outcomes", []) if o["status"] == "ready"]
    assert [o for r in rec for o in r.get("outcomes_untimed", [])]
    # 完整视图原值可查
    full = ob.recent_observations(conn)
    assert [o for r in full for o in r.get("outcomes", [])
            if o["status"] == "ready" and o["change_pct"] == 7]
    conn.close()
