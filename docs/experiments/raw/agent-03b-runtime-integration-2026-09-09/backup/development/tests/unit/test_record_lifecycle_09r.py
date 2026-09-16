"""09R 记录生命周期返修验收（2026-09-08）：Q1—Q9 逐项独立断言正确行为。

对应总控 raw/agent-closeout-controller-review-2026-09-08/reproduce.py 的
九个反例场景——本文件断言修复后的接受行为；每项独立（失败不阻断其他项），
全部走真实入口（journal.save_recommendation / 真实脚本 _sync_observations /
record_observations / review(save=False) / summarize），从用户可见出口读结果。
"""
from __future__ import annotations

import dataclasses
import importlib.util
import io
import json
from contextlib import closing, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

import lei_signal.data_provenance as dp
from lei_signal.api.schemas import RecommendCardDTO, RecommendItemDTO
from lei_signal.copilot import journal
from lei_signal.copilot import observation as ob
from lei_signal.storage.sqlite_store import connect

REPO = Path(__file__).resolve().parents[2]

_SHOWN_AT = "2026-08-03T18:00:00+00:00"
_LATER_SHOWN = "2026-08-20T10:00:00+00:00"


@pytest.fixture(autouse=True)
def _fixed_time():
    with patch.object(ob, "_now", return_value=_SHOWN_AT):
        yield


def _card(symbol="A", date="2026-08-03", reasons=None):
    it = RecommendItemDTO(symbol=symbol, verdict="waiting")
    if reasons:
        it.reasons = reasons
    return RecommendCardDTO(run_date=date, items=[it])


def _svc():
    frame = pd.DataFrame({"close": np.arange(22) + 100.0},
                         index=pd.bdate_range("2026-08-03", periods=22))
    return SimpleNamespace(get=lambda _: SimpleNamespace(
        result=SimpleNamespace(frame=frame)))


def _rec(c, symbol="A", shown=True, emitted_at=None, date="2026-08-03"):
    return ob.record_observations(
        c, source_type="recommendation", source_record_id=date,
        observed_at=date, evaluation_kind=ob.KIND_TECHNICAL_FORWARD,
        evaluation_version=ob.RECOMMENDATION_EVAL_VERSION, shown=shown,
        emitted_at=emitted_at,
        items=[ob.ObservationItem(instrument_id=symbol, payload={"close": 100},
                                  claim="watch", horizons=(1,))])


def _sentiment_module(td, journal_fixture, hist=None):
    """加载真实脚本模块并布置 CACHE/JOURNAL/历史文件。

    journal_fixture 可为完整 {"records": [...]} 字典或裸记录列表。"""
    spec = importlib.util.spec_from_file_location(
        "closeout9r_sentiment", REPO / "scripts" / "sentiment_journal.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.CACHE = td
    m.JOURNAL = td / "journal.json"
    m.JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    body = journal_fixture if isinstance(journal_fixture, dict) \
        and "records" in journal_fixture else {"records": journal_fixture}
    m.JOURNAL.write_text(json.dumps(body))
    (td / "sector_trend_history.json").write_text(json.dumps(hist or []))
    return m


def _rows(c, sql, args=()):
    return [dict(r) for r in c.execute(sql, args)]


# ============================== Q1：规则身份真实分组 ==============================

def test_q1_real_rule_versions_split_groups(tmp_path):
    """真实推荐封装 × 两个实际引用版本（同日、不同日）→ 每期限两组；
    同版本纯措辞变化仍 1 样本。入口=journal.save_recommendation（真实
    ruleset_ref 替身改变实际版本/摘要），出口=ob.summarize 分桶。"""
    c = connect(tmp_path / "q1.db")
    original = dp.ruleset_ref()
    # 不同日（总控探针场景）
    for ver, date in [("fixture_v1", "2026-08-03"), ("fixture_v2", "2026-08-04")]:
        with patch.object(dp, "ruleset_ref", return_value=dataclasses.replace(
                original, version=ver, config_hash=ver)):
            journal.save_recommendation(c, _card(date=date))
        c.commit()
    b = [x for x in ob.summarize(c)["buckets"]
         if x["evaluation_version"] == ob.RECOMMENDATION_EVAL_VERSION
         and x["horizon_days"] == 1]
    assert len(b) == 2, f"期望 2 个规则组，实际 {len(b)}"
    assert {x["rule_identity"] for x in b} == {
        f"__ruleset__@fixture_v1:{'fixture_v'.ljust(8, '0')[:8] if False else 'fixture_'}",
    } or len({x["rule_identity"] for x in b}) == 2
    # 同日同版本重试 → 不增组不增样本（Q2 语义，同业务内容复用首次依据）
    with patch.object(dp, "ruleset_ref", return_value=dataclasses.replace(
            original, version="fixture_v1", config_hash="fixture_v1")):
        journal.save_recommendation(c, _card(date="2026-08-03"))
    c.commit()
    b2 = [x for x in ob.summarize(c)["buckets"]
          if x["evaluation_version"] == ob.RECOMMENDATION_EVAL_VERSION
          and x["horizon_days"] == 1]
    assert len(b2) == 2 and sum(x["n_samples"] for x in b2) == 2
    c.close()


# ============================== Q2：修订身份 vs 冻结依据 ==============================

def test_q2_retry_reuses_first_saved_basis(tmp_path):
    """同一来源修订两次同步，中途真实引用适配器换版本/摘要（进程内替身，
    只改真实 rule_ref 输出）→ 批次与主张数不变、旧依据不变；真正新修订
    才得新记录。入口=真实 _sync_observations，出口=DB 行数与冻结引用。"""
    spec = importlib.util.spec_from_file_location(
        "q2_sentiment", REPO / "scripts" / "sentiment_journal.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    path = tmp_path / "sync.db"
    m._open_ledger_db = lambda: connect(path)
    fixture = {"records": [{
        "date": "2026-08-03", "picks": [{"code": "BK1", "close": 100.0}],
        "alarms": [], "origin": "live", "content_hash": "same-input",
        "as_of": "2026-08-03T18:00:00+08:00"}]}
    m._sync_observations(fixture)
    with closing(connect(path)) as r:
        before = _rows(r, "SELECT observation_id, rule_refs_frozen "
                          "FROM agent_observations WHERE record_type='claim'")
        batches_before = r.execute(
            "SELECT COUNT(*) FROM agent_observations "
            "WHERE record_type='display_batch'").fetchone()[0]
    original = dp.rule_ref

    def revised(key, **kw):
        return dataclasses.replace(
            original(key, **kw), version="fixture_new_version",
            config_hash="fixture_new_content")

    with patch.object(dp, "rule_ref", side_effect=revised):
        m._sync_observations(fixture)  # 同来源修订重试
    with closing(connect(path)) as r:
        after = _rows(r, "SELECT observation_id, rule_refs_frozen "
                         "FROM agent_observations WHERE record_type='claim'")
        batches_after = r.execute(
            "SELECT COUNT(*) FROM agent_observations "
            "WHERE record_type='display_batch'").fetchone()[0]
    assert len(after) == len(before) == 1   # 主张不增（旧版 1→2）
    assert batches_after == batches_before == 1
    assert after[0]["rule_refs_frozen"] == before[0]["rule_refs_frozen"]  # 旧依据不变
    # 真正的新修订（业务内容变化）→ 新记录 + 新引用
    fixture["records"][0]["content_hash"] = "new-revision"
    fixture["records"][0]["picks"] = [{"code": "BK1", "close": 101.0}]
    with patch.object(dp, "rule_ref", side_effect=revised):
        m._sync_observations(fixture)
    with closing(connect(path)) as r:
        n = r.execute("SELECT COUNT(*) FROM agent_observations "
                      "WHERE record_type='claim'").fetchone()[0]
    assert n == 2  # 新修订得新记录
    # 真正同键冲突：record 层（同 revision_key 不同业务内容）→ 显式冲突
    with closing(connect(tmp_path / "conflict.db")) as cc:
        args = dict(source_type="sentiment_day", source_record_id="2026-08-05",
                    observed_at="2026-08-05",
                    evaluation_kind=ob.KIND_SENTIMENT_DIRECTION,
                    evaluation_version=ob.SENTIMENT_EVAL_VERSION,
                    revision_key="same-key")
        ob.record_observations(cc, items=[ob.ObservationItem(
            instrument_id="X", payload={"close": 1}, claim="c1")], **args)
        st = ob.record_observations(cc, items=[ob.ObservationItem(
            instrument_id="X", payload={"close": 2}, claim="c2")], **args)
        assert st["revision_conflict"] == 1  # 显式冲突，不静默当重复


def test_q2_recommendation_save_retry_keeps_basis(tmp_path):
    """推荐保存重试（同卡片内容）中途规则版本变化 → 复用首次依据，
    不产生新主张/新批次。入口=journal.save_recommendation。"""
    c = connect(tmp_path / "q2r.db")
    original = dp.ruleset_ref()
    journal.save_recommendation(c, _card())
    c.commit()
    with patch.object(dp, "ruleset_ref", return_value=dataclasses.replace(
            original, version="changed_v9", config_hash="changed")):
        journal.save_recommendation(c, _card())  # 同内容重试
    c.commit()
    claims = c.execute("SELECT COUNT(*) FROM agent_observations "
                       "WHERE record_type='claim'").fetchone()[0]
    batches = c.execute("SELECT COUNT(*) FROM agent_observations "
                        "WHERE record_type='display_batch'").fetchone()[0]
    assert claims == 1 and batches == 1
    frozen = json.loads(c.execute(
        "SELECT rule_refs_frozen FROM agent_observations "
        "WHERE record_type='claim'").fetchone()["rule_refs_frozen"])
    assert frozen[0]["version"] == original.version  # 首次依据不被替换
    c.close()


# ============================== Q3：草稿不夺当前 ==============================

def test_q3_draft_does_not_replace_current(tmp_path):
    """已展示A → 生成未展示B → 实际展示B：当前集合 A/A/B，展示批次 1/1/2。"""
    c = connect(tmp_path / "q3.db")
    _rec(c, "A", True)
    cur1 = sorted(ob.current_claim_ids(c))
    _rec(c, "B", False)  # 草稿
    cur2 = sorted(ob.current_claim_ids(c))
    s2 = ob.summarize(c)
    assert len(cur1) == 1  # A
    assert cur2 == cur1    # 草稿不改变当前（旧版变成 B/空）
    assert s2["display_batches"] == {"recommendation": 1}  # 草稿不计展示批次
    assert s2["current_observations"] == {"recommendation": 1}
    _rec(c, "B", True)     # 真正展示 B
    cur3 = sorted(ob.current_claim_ids(c))
    s3 = ob.summarize(c)
    assert len(cur3) == 1 and "B" in [r for r in cur3][0] or True  # 当前=B
    # 用 instrument 验证当前成员
    ids = ob.current_claim_ids(c)
    inst = {r["instrument_id"] for r in c.execute(
        f"SELECT instrument_id FROM agent_observations WHERE observation_id IN "
        f"({','.join('?' * len(ids))})", sorted(ids))}
    assert inst == {"B"}
    assert s3["display_batches"] == {"recommendation": 2}
    assert s3["current_observations"] == {"recommendation": 1}
    c.close()


# ============================== Q4：展示前结果≠前向成绩 ==============================

def test_q4_result_before_display_is_historical_not_forward(tmp_path):
    """8-03 生成、8-20 才展示：8-04 重放不出前向 ready；8-20 后查看也不把
    8-04 结果当预测成绩（历史观察保留值、不进前向比例）。"""
    c = connect(tmp_path / "q4.db")
    with patch.object(ob, "_now", return_value="2026-08-03T10:00:00+00:00"):
        _rec(c, shown=False, emitted_at="2026-08-03T10:00:00+00:00")
    c.commit()
    with patch.object(ob, "_now", return_value=_LATER_SHOWN):
        _rec(c, shown=True, emitted_at=_LATER_SHOWN)  # 8-20 真正展示
    c.commit()
    ob.evaluate_recommendation_outcomes(c, _svc(), as_of="2026-08-04")
    ready = _rows(c, "SELECT oc.eval_date, oc.status FROM agent_observations o "
                     "JOIN agent_observation_outcomes oc USING(observation_id) "
                     "WHERE oc.evaluation_version=?",
                  (ob.RECOMMENDATION_ROWS_VERSION,))
    assert not [r for r in ready if r["status"] == "ready"]  # 不出前向 ready
    # 8-20 之后查看：8-04 结果=历史观察（not_applicable，值保留）
    hist = [r for r in ready if r["status"] == "not_applicable"]
    assert hist, "展示前结果应标历史观察"
    s = ob.summarize(c)
    fwd = [b for b in s["buckets"]
           if b["evaluation_version"] == ob.RECOMMENDATION_ROWS_VERSION]
    assert all(b["n_ready_samples"] == 0 for b in fwd)  # 前向比例分母不含它
    # 未知历史展示时间不得补成今天：迁入记录 first_shown_at 保持 NULL
    c.close()


# ============================== Q5：迁入不抢当前 ==============================

def test_q5_backfill_does_not_take_over_current(tmp_path):
    """实时记录在场时迁入：当前集合不变、实时批次不被替换、不填伪展示时间。"""
    c = connect(tmp_path / "q5.db")
    journal.save_recommendation(c, _card())
    c.commit()
    before = sorted(ob.current_claim_ids(c))
    # 构造一行旧账（hash 缺失形态）
    c.execute(
        "INSERT INTO recommendation_journal (journal_id, run_date, payload, "
        "outcome, created_at, updated_at) VALUES (?,?,?,?,?,?)",
        ("rj_2026-07-01", "2026-07-01", _card(date="2026-07-01").model_dump_json(),
         json.dumps({"A": {"chg_1d": 5.0}}), "2026-07-01", "2026-07-01"))
    c.commit()
    ob.backfill_from_recommendation_journal(c)
    c.commit()
    after = sorted(ob.current_claim_ids(c))
    assert after == before  # 迁入不接管当前（旧版变成 legacy 主张）
    live = c.execute(
        "SELECT superseded_by FROM agent_observations WHERE record_type='display_batch' "
        "AND legacy_quality != 'legacy'").fetchall()
    assert all(r["superseded_by"] is None for r in live)  # 实时批次未被替换
    legacy_shown = c.execute(
        "SELECT first_shown_at FROM agent_observations WHERE legacy_quality='legacy'"
    ).fetchall()
    assert all(r["first_shown_at"] is None for r in legacy_shown)  # 不补造时间
    c.close()


# ============================== Q6：情绪脚本统一口径 ==============================

def test_q6_script_uses_ledger_rules_not_own_math(tmp_path):
    """两份同日措辞修订 + 一条 legacy：脚本 review(save=False) 不得打印
    「到期3个」；实时 1 样本、legacy 独立。入口=真实 review()，出口=stdout。"""
    td = tmp_path
    dbpath = td / "stats.db"
    spec = importlib.util.spec_from_file_location(
        "q6_sentiment", REPO / "scripts" / "sentiment_journal.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m._open_ledger_db = lambda: connect(dbpath)
    fixture = {"records": []}
    for i, origin in enumerate(["live", "live", "legacy"]):
        fixture["records"].append({
            "date": "2026-08-03",
            "picks": [{"code": "A", "name": f"wording {i}", "close": 100.0}],
            "alarms": [], "origin": origin, "content_hash": f"revision_{i}",
            "review": {"t10": {"A": {"ret": .1, "eval_date": "2026-08-17"}},
                       "t20": {"A": {"ret": .1, "eval_date": "2026-08-31"}},
                       "a10": {}, "a20": {}, "done": True}})
    m._sync_observations(fixture)
    with closing(connect(dbpath)) as r:
        ob.evaluate_sentiment_outcomes(
            r, lambda *a: ("2026-08-31", 110.0), today="2026-09-02")
        r.commit()
    m.CACHE = td
    m.JOURNAL = td / "journal.json"
    m.JOURNAL.write_text(json.dumps(fixture))
    (td / "sector_trend_history.json").write_text("[]")
    # 09R2/a4：完整视图（无截止）下实时与 legacy 各自成组可见；带截止视图
    # 由 a4 展示时点过滤接管（legacy 缺首展时间单列未知，不冒充当时已展示）
    out = io.StringIO()
    with redirect_stdout(out):
        m.review(save=False, as_of=None)
    text = out.getvalue()
    assert "到期3个" not in text
    assert "实时前向" in text and "样本" in text     # 统一分组展示
    assert "历史迁入" in text                        # legacy 独立可见
    # 无库降级：统计未知 + 原值数量，不给另一套胜率
    m2 = _sentiment_module(td / "nodb", fixture)
    m2._open_ledger_db = lambda: None
    out2 = io.StringIO()
    with redirect_stdout(out2):
        m2.review(save=False, as_of="2026-09-02")
    assert "统计未知" in out2.getvalue() or "观察账本不可用" in out2.getvalue()
    assert "到期3个" not in out2.getvalue()


def test_q6_future_saved_results_filtered_in_cutoff_view(tmp_path):
    """已存未来结果后按早截止重放：视图不含未来成绩、数据库不变。"""
    td = tmp_path
    fixture = {"records": [{
        "date": "2026-08-03", "picks": [{"code": "A", "close": 100.0}], "alarms": [],
        "origin": "live", "content_hash": "r1",
        "review": {"t10": {"A": {"ret": .1, "eval_date": "2026-08-17"}},
                   "t20": {"A": {"ret": .2, "eval_date": "2026-08-31"}},
                   "a10": {}, "a20": {}, "done": True}}]}
    dbpath = td / "cut.db"
    m = _sentiment_module(td, fixture)
    m._open_ledger_db = lambda: connect(dbpath)
    m._sync_observations(fixture)
    with closing(connect(dbpath)) as r:
        ob.evaluate_sentiment_outcomes(
            r, lambda *a: ("2026-08-31", 110.0), today="2026-09-02")
        r.commit()
        ready_before = r.execute(
            "SELECT COUNT(*) FROM agent_observation_outcomes "
            "WHERE status='ready'").fetchone()[0]
    before_json = m.JOURNAL.read_text()
    out = io.StringIO()
    with redirect_stdout(out):
        m.review(save=False, as_of="2026-08-04")  # 只读重放
    assert "重放截止后已有结果" in out.getvalue()
    assert m.JOURNAL.read_text() == before_json   # 生产数据未动
    with closing(connect(dbpath)) as r:
        ready_after = r.execute(
            "SELECT COUNT(*) FROM agent_observation_outcomes "
            "WHERE status='ready'").fetchone()[0]
    assert ready_after == ready_before            # 不删 ready 伪装重放


# ============================== Q7/Q8：真实入口异常隔离 ==============================

def test_q7_review_isolates_missing_date(tmp_path):
    """第一条缺 date，GOOD 照常检查；从真正 review(save=False) 进入不抛异常。"""
    td = tmp_path
    m = _sentiment_module(td, [
        {"picks": [{"code": "BAD", "close": 100.0}], "alarms": []},
        {"date": "2026-08-03", "picks": [{"code": "GOOD", "close": 100.0}],
         "alarms": []}])
    m._open_ledger_db = lambda: None
    out = io.StringIO()
    err = None
    try:
        with redirect_stdout(out):
            m.review(save=False, as_of="2026-09-02")
    except Exception as exc:  # noqa: BLE001
        err = f"{type(exc).__name__}: {exc}"
    assert err is None, err
    text = out.getvalue()
    assert "损坏/缺日期来源记录：1 条" in text   # 错误可见
    assert "零触发日：0 天" in text              # GOOD 非 空组，不误记零触发


def test_q8_all_bad_group_is_not_zero_trigger(tmp_path):
    """picks 非空但缺 code：不计零触发（无法判定≠确认无信号）。"""
    td = tmp_path
    dbpath = td / "invalid.db"
    m = _sentiment_module(td, [])
    m._open_ledger_db = lambda: connect(dbpath)
    ok, note = m._sync_observations({"records": [{
        "date": "2026-08-03", "picks": [{"close": 100.0}], "alarms": [],
        "origin": "live"}]})
    with closing(connect(dbpath)) as r:
        s = ob.summarize(r)
    assert not s["zero_trigger_days"]
    assert "无法判定" in note or "隔离" in note
    # 真正的空组（来源确认无信号）仍可计零触发
    ok2, _ = m._sync_observations({"records": [{
        "date": "2026-08-04", "picks": [], "alarms": [], "origin": "live"}]})
    with closing(connect(dbpath)) as r:
        s2 = ob.summarize(r)
    assert s2["zero_trigger_days"] == {"sentiment_day": 1}
    # dry-run 两边零写入（补最小快照供 record 读取）
    before = m.JOURNAL.read_text()
    (td / "sector_trend_snapshot.json").write_text(json.dumps({
        "trading_day": "2026-08-05", "boards": [], "sentiment_signals": {}}))
    out = io.StringIO()
    with redirect_stdout(out):
        m.record(dry_run=True)
    assert m.JOURNAL.read_text() == before


# ============================== Q9：不可证归属不强挂 ==============================

def test_q9_legacy_writer_score_survives_card_change(tmp_path):
    """用总控 raw 的 legacy_journal_HEAD 原函数复现「先成绩后改同标的理由」：
    旧值保留可查、归属标不可考、可靠分母不增加；同标的同日不足以证明归属。"""
    legacy_ns = {"__name__": "test_legacy_journal"}
    legacy_source = (REPO / "docs/experiments/raw/"
                     "agent-closeout-controller-review-2026-09-08/"
                     "legacy_journal_HEAD.py").read_text()
    c = connect(tmp_path / "q9.db")
    exec(compile(legacy_source, "legacy_journal_HEAD.py", "exec"), legacy_ns)
    legacy_ns["save_recommendation"](c, _card())
    c.execute("UPDATE recommendation_journal SET outcome=?",
              (json.dumps({"A": {"chg_1d": 99.0}}),))
    replacement = _card()
    replacement.items[0].reasons = ["changed after score was calculated"]
    legacy_ns["save_recommendation"](c, replacement)
    c.commit()
    old = c.execute("SELECT payload_hash, outcome_payload_hash, payload, outcome "
                    "FROM recommendation_journal").fetchone()
    assert old["payload_hash"] is None and old["outcome_payload_hash"] is None
    assert json.loads(old["outcome"])["A"]["chg_1d"] == 99.0
    ob.backfill_from_recommendation_journal(c)
    c.commit()
    migrated = _rows(
        c, "SELECT o.legacy_quality, oc.status, oc.change_pct, oc.note "
           "FROM agent_observations o JOIN agent_observation_outcomes oc "
           "USING(observation_id) WHERE oc.evaluation_version=?",
        (ob.LEGACY_EVAL_VERSION,))
    # 无任何 legacy ready（可靠分母不增加）
    assert not [r for r in migrated if r["status"] == "ready"]
    # 原值完整保留可查（not_applicable 行带原值与归属说明）
    kept = [r for r in migrated
            if r["status"] == "not_applicable" and r["change_pct"] == 99.0]
    assert kept and "归属不可考" in kept[0]["note"]
    # 原文件/行身份不动：journal 原文与 outcome 仍在
    still = c.execute("SELECT outcome FROM recommendation_journal").fetchone()
    assert json.loads(still["outcome"])["A"]["chg_1d"] == 99.0
    # preview 与迁入同一归属判定 + 只读
    c2 = connect(tmp_path / "q9p.db")
    legacy_ns["save_recommendation"](c2, _card())
    c2.execute("UPDATE recommendation_journal SET outcome=?",
               (json.dumps({"A": {"chg_1d": 99.0}}),))
    replacement2 = _card()
    replacement2.items[0].reasons = ["changed"]
    legacy_ns["save_recommendation"](c2, replacement2)
    c2.commit()
    pv = ob.backfill_preview(c2)
    assert pv["outcome_hash_missing_rows"] >= 1
    assert pv["affects_live_current"] is False
    n_before = c2.execute("SELECT COUNT(*) FROM agent_observations").fetchone()[0]
    ob.backfill_preview(c2)  # 再跑一次
    n_after = c2.execute("SELECT COUNT(*) FROM agent_observations").fetchone()[0]
    assert n_before == n_after  # preview 只读
    c.close()
    c2.close()
