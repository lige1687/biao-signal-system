"""联合收尾（2026-09-08）真实调用链验收：P1—P10 逐项断言正确行为。

与总控 raw/agent-repair-controller-review-2026-09-08/reproduce.py 的残余错误
探针相对——那些断言在修复后应当失败；本文件断言修复后的正确行为，且全部
走真实封装/真实脚本函数（record/review → _sync_observations → record_observations；
journal.save_recommendation/score_journal_outcomes → observation 评价器；
record_recommendation_card / record_sentiment_day 落库后从 DB 读回引用）。
"""
from __future__ import annotations

import importlib.util
import io
import json
from contextlib import closing, redirect_stdout
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch as _patch

import numpy as np
import pandas as pd
import pytest

import lei_signal.data_provenance as dp
from lei_signal.api.app import create_app
from lei_signal.api.schemas import RecommendCardDTO, RecommendItemDTO
from lei_signal.copilot import journal
from lei_signal.copilot import observation as ob
from lei_signal.dca.state import compute_state
from lei_signal.storage.sqlite_store import MIGRATIONS, connect


# 09R/Q4：评价器以首次展示时间门控前向资格；旧测试以过去 observed_at + 现在
# 创建时间构造数据会误触门控。统一注入「当时展示」时间（与观察日同日晚间）。
@pytest.fixture(autouse=True)
def _fixed_shown_time():
    with _patch.object(ob, "_now", return_value="2026-08-03T18:00:00+00:00"):
        yield


REPO = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------- helpers ----

def _card(symbols, date="2026-08-03"):
    return RecommendCardDTO(
        run_date=date,
        items=[RecommendItemDTO(symbol=s, verdict="waiting") for s in symbols])


def _svc(end="2026-08-31"):
    frame = pd.DataFrame(
        {"close": np.arange(22) + 100.0},
        index=pd.bdate_range("2026-08-03", periods=22))
    return SimpleNamespace(
        get=lambda _: SimpleNamespace(result=SimpleNamespace(frame=frame)))


def _record(c, *, shown=True, rules=("rule_v1",), config=None,
            claim="look", symbol="TEST", source="recommendation", frozen=None,
            day="2026-08-03"):
    return ob.record_observations(
        c, source_type=source, source_record_id=day,
        observed_at=day,
        evaluation_kind=ob.KIND_TECHNICAL_FORWARD,
        evaluation_version=ob.RECOMMENDATION_EVAL_VERSION,
        items=[ob.ObservationItem(
            instrument_id=symbol, payload={"close": 100}, claim=claim,
            rule_refs=list(rules), eval_config=config or {}, horizons=(1,),
            rule_refs_frozen=frozen or [])],
        shown=shown)


def _db(tmp_path, name):
    c = connect(tmp_path / f"{name}.db")
    return c


# ---------------------------------------------------------------- P1 / P2 ----

def test_p1_interior_gap_keeps_window_positions():
    """中间缺值不压缩窗口：年线不可判（null+原因），无缺口数据不变。"""
    dates = pd.bdate_range(end="2026-09-07", periods=300)
    values = np.r_[np.full(200, 100.0), np.linspace(100.0, 70.0, 100)]
    bars = pd.DataFrame({"close": values}, index=dates)
    bars.iloc[-50, 0] = np.nan  # 200 窗口内缺 1 个
    st = compute_state("TEST", "TEST", bars, 26.0)
    assert st.ma200_gap is None and st.deep20 is None
    assert "200日窗口缺 1 个收盘" in st.window_note
    assert st.state_status == "degraded"
    clean = compute_state("TEST", "TEST",
                          pd.DataFrame({"close": values}, index=dates), 26.0)
    assert clean.state_status == "ok" and clean.deep20 is True
    assert clean.ma200_gap == pytest.approx(-0.2432, abs=1e-3)


def test_p2_weekend_preopen_holiday_never_fresh():
    ref = dp.reference_calendar("cn", pd.bdate_range("2026-08-01", "2026-08-03"))
    pol = dp.SourcePolicy("cn", verified=True, basis="synthetic verified fixture")
    weekend = dp.assess_freshness("2026-08-03", "cn", now=datetime(2026, 9, 12, 18),
                                  calendar=ref, policy=pol)
    preopen = dp.assess_freshness("2026-08-03", "cn", now=datetime(2026, 9, 14, 9),
                                  calendar=ref, policy=pol)
    # 节假日（工作日但休市，无交易所日历不可知）→ 保守 unknown
    holiday = dp.assess_freshness(
        "2026-09-03", "cn", now=datetime(2026, 9, 7, 18),
        calendar=dp.reference_calendar("cn", pd.bdate_range("2026-08-01", "2026-09-04")),
        policy=pol)
    for a in (weekend, preopen, holiday):
        assert a.health == "unknown", a.reason
    assert "未覆盖" in weekend.reason
    # 覆盖足够时仍可判 fresh / stale（无新增宽限天数）
    good = dp.reference_calendar("cn", pd.bdate_range("2026-08-01", "2026-09-07"))
    assert dp.assess_freshness("2026-09-07", "cn", now=datetime(2026, 9, 7, 22),
                               calendar=good, policy=pol).health == "fresh"
    assert dp.assess_freshness("2026-09-02", "cn", now=datetime(2026, 9, 7, 22),
                               calendar=good, policy=pol).health == "stale"


# ---------------------------------------------------------------- P3 ----

def test_p3_not_shown_excluded_until_actually_shown(tmp_path):
    c = _db(tmp_path, "shown")
    _record(c, shown=False)
    c.commit()
    ob.evaluate_recommendation_outcomes(c, _svc(), today="2026-08-04")
    before = ob.summarize(c)
    assert before["buckets"] == []  # 未展示阶段 0 个正式样本
    assert before["not_shown_observations"] == {"recommendation": 1}
    # 同内容真正展示：升级为 shown、记首次展示时间、不被旧 not_shown 去重吞掉
    _record(c, shown=True)
    c.commit()
    row = c.execute(
        "SELECT display_status, first_shown_at FROM agent_observations "
        "WHERE record_type='claim'").fetchone()
    assert row["display_status"] == "shown" and row["first_shown_at"]
    ob.evaluate_recommendation_outcomes(c, _svc(), today="2026-08-04")
    after = ob.summarize(c)
    rb = next(b for b in after["buckets"]
              if b["evaluation_version"] == ob.RECOMMENDATION_ROWS_VERSION)
    assert rb["n_observations"] == 1  # 展示后才进入评价
    # 旧生成正文（claim）未被改写
    assert c.execute("SELECT claim FROM agent_observations "
                     "WHERE record_type='claim'").fetchone()["claim"] == "look"
    c.close()


# ---------------------------------------------------------------- P4 ----

def _frozen(rid, ver):
    return [{"rule_id": rid, "version": ver, "config_path": "configs/rules.v2.yaml",
             "config_hash": f"hash_{ver}", "definition_ref": "", "fallback_note": ""}]


def test_p4_rules_and_config_split_into_groups(tmp_path):
    """Q1：真实规则身份（冻结 rule_id@version:hash）参与分组与样本键。"""
    c = _db(tmp_path, "grouping")
    _record(c, rules=("rule_v1",), config={"exit": "a"},
            frozen=_frozen("module_a", "1.0.0"), day="2026-08-03")
    _record(c, rules=("rule_v2",), config={"exit": "b"},
            frozen=_frozen("module_a", "2.0.0"), day="2026-08-04")
    c.commit()
    strict = [b for b in ob.summarize(c)["buckets"]
              if b["evaluation_version"] == ob.RECOMMENDATION_EVAL_VERSION]
    assert len(strict) == 2  # 冻结规则版本不同 → 两个组，不合并
    assert {b["rule_identity"] for b in strict} == {
        "module_a@1.0.0:hash_1.0", "module_a@2.0.0:hash_2.0"}  # hash 取前8位
    assert {b["eval_config_hash"] for b in strict}.__len__() == 2
    # 无冻结引用的旧记录单独成组（未知，不与任何版本混算）
    _record(c, rules=("rule_v1",), day="2026-08-05")
    c.commit()
    strict2 = [b for b in ob.summarize(c)["buckets"]
               if b["evaluation_version"] == ob.RECOMMENDATION_EVAL_VERSION]
    assert len(strict2) == 3
    unknown = [b for b in strict2 if not b["rule_identity_known"]]
    assert len(unknown) == 1
    # eval_config 全文持久化（可恢复「怎么算」）
    body = c.execute(
        "SELECT eval_config_json FROM agent_observations WHERE record_type='claim'"
    ).fetchall()
    assert any('"exit"' in r["eval_config_json"] for r in body)
    # 同规则仅改措辞（claim 文本变化、claim_class 不变）→ 仍 1 个样本
    c2 = _db(tmp_path, "wording")
    _record(c2, claim="first wording")
    _record(c2, claim="second wording")
    c2.commit()
    b = [x for x in ob.summarize(c2)["buckets"]
         if x["evaluation_version"] == ob.RECOMMENDATION_EVAL_VERSION]
    assert len(b) == 1 and b[0]["n_observations"] == 2 and b[0]["n_samples"] == 1
    c.close()
    c2.close()


# ---------------------------------------------------------------- P5 ----

def _load_script():
    spec = importlib.util.spec_from_file_location(
        "closeout_sentiment", REPO / "scripts" / "sentiment_journal.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_p5_real_script_sync_stable_revision_keys(tmp_path):
    """真实脚本 _sync_observations：同日 A→B；连续两次同步批次数不变，
    当前仍是 B，旧批次不夺当前。"""
    mod = _load_script()
    syncdb = tmp_path / "sync.db"
    mod._open_ledger_db = lambda: connect(syncdb)
    fixture = {"records": [
        {"date": "2026-08-03", "picks": [{"code": "A", "close": 100.0}],
         "alarms": [], "origin": "live", "content_hash": "ha", "superseded": True},
        {"date": "2026-08-03", "picks": [{"code": "B", "close": 100.0}],
         "alarms": [], "origin": "live", "content_hash": "hb"},
    ]}
    ok, note = mod._sync_observations(fixture)
    assert ok, note
    c = connect(syncdb)
    n1 = c.execute("SELECT COUNT(*) FROM agent_observations "
                   "WHERE record_type='display_batch'").fetchone()[0]
    ok2, _ = mod._sync_observations(fixture)  # 同数据重跑
    n2 = c.execute("SELECT COUNT(*) FROM agent_observations "
                   "WHERE record_type='display_batch'").fetchone()[0]
    cur = c.execute(
        "SELECT payload FROM agent_observations WHERE record_type='display_batch' "
        "AND superseded_by IS NULL").fetchone()["payload"]
    assert n1 == n2 == 2            # 重跑不增加批次（旧版为 2→4）
    assert '"B"' in cur or "B" in cur  # 当前仍是 B
    superseded = c.execute(
        "SELECT COUNT(*) FROM agent_observations "
        "WHERE record_type='display_batch' AND superseded_by IS NOT NULL"
    ).fetchone()[0]
    assert superseded == 1          # 旧版 A 被链住，不冒充新展示
    c.close()


def test_p5_sync_isolates_missing_date_and_code(tmp_path):
    """dict 缺 date / 对象缺 code：单条隔离，其他记录照常同步（不整单回滚）。"""
    mod = _load_script()
    syncdb = tmp_path / "syncbad.db"
    mod._open_ledger_db = lambda: connect(syncdb)
    fixture = {"records": [
        {"date": "2026-08-03", "picks": [{"close": 100.0}], "alarms": []},   # 缺 code
        {"picks": [{"code": "X", "close": 100.0}], "alarms": []},            # 缺 date
        {"date": "2026-08-04", "picks": [{"code": "GOOD", "close": 100.0}],
         "alarms": [], "origin": "live", "content_hash": "hg"},
    ]}
    ok, note = mod._sync_observations(fixture)
    assert ok and "已同步 1 条记录" in note and "隔离跳过" in note
    c = connect(syncdb)
    n = c.execute("SELECT COUNT(*) FROM agent_observations "
                  "WHERE record_type='claim' AND instrument_id='GOOD'").fetchone()[0]
    assert n == 1                   # GOOD 照常入库（旧行为：整单回滚→0）
    bad = c.execute("SELECT COUNT(*) AS n FROM agent_observations "
                    "WHERE record_type='claim' AND instrument_id='X'").fetchone()[0]
    assert bad == 0                 # 缺 code 对象不入库冒充
    c.close()


# ---------------------------------------------------------------- P6 ----

def test_p6_legacy_reader_respects_cutoff(tmp_path):
    c = _db(tmp_path, "legacy")
    journal.save_recommendation(c, _card(["A"]))
    c.commit()
    journal.score_journal_outcomes(c, _svc(), today="2026-08-04")
    old = journal.load_outcome(c, "2026-08-03")
    assert set(old["A"]) == {"chg_1d"}           # 截止后档位不写（旧含 chg_20d）
    pend = dict(c.execute(
        "SELECT horizon, status FROM agent_observation_outcomes "
        "WHERE evaluation_version=?", (ob.RECOMMENDATION_ROWS_VERSION,)).fetchall())
    assert pend[1] == "ready" and pend[5] == "pending" and pend[20] == "pending"
    # 换卡不串成绩（既有行为回归）
    journal.save_recommendation(c, _card(["NEW"]))
    c.commit()
    assert journal.load_outcome(c, "2026-08-03") is None or \
        "NEW" not in (journal.load_outcome(c, "2026-08-03") or {})
    c.close()


def test_p6_replay_with_existing_future_results_consistent(tmp_path):
    """已有未来结果后按更早 today 重放：不新增未来档；两读路径口径一致。"""
    c = _db(tmp_path, "replay")
    journal.save_recommendation(c, _card(["A"]))
    c.commit()
    journal.score_journal_outcomes(c, _svc(), today="2026-08-31")  # 全部到期
    full = journal.load_outcome(c, "2026-08-03")
    assert set(full["A"]) == {"chg_1d", "chg_5d", "chg_20d"}
    journal.score_journal_outcomes(c, _svc(), today="2026-08-04")  # 重放更早截止
    again = journal.load_outcome(c, "2026-08-03")
    assert again == full  # 已存结果不被重放抹掉；读者口径一致
    c.close()


# ---------------------------------------------------------------- P7 ----

def test_p7_real_wrappers_freeze_references_in_db(tmp_path):
    c = _db(tmp_path, "refs")
    journal.save_recommendation(c, _card(["A"]))
    c.commit()
    row = c.execute(
        "SELECT input_hash, available_at, rule_refs_frozen, evidence_refs_frozen, "
        "       data_refs_frozen FROM agent_observations WHERE record_type='claim'"
    ).fetchone()
    assert row["input_hash"] != "unknown"        # 真实输入摘要
    assert row["available_at"] == "unknown"      # 来源可用时点未核实（不伪造）
    rule_frozen = json.loads(row["rule_refs_frozen"])
    assert rule_frozen and rule_frozen[0]["version"]          # ruleset 版本
    assert rule_frozen[0]["config_hash"]                      # 账本内容哈希
    ev = json.loads(row["evidence_refs_frozen"])
    assert ev[0]["id"] == "module_winrate:A"
    assert ev[0]["source_hash"] and ev[0]["compatibility"] == "unknown"
    dr = json.loads(row["data_refs_frozen"])
    assert dr[0]["instrument_id"] == "A" and dr[0]["last_valid_at"] is None
    # 情绪封装：规则条目 + 证据条目（含材料哈希）冻结
    ob.record_sentiment_day(c, date="2026-08-03",
                            picks=[{"code": "BK1", "close": 100.0}], alarms=[])
    c.commit()
    srow = c.execute(
        "SELECT rule_refs_frozen, evidence_refs_frozen, input_hash "
        "FROM agent_observations WHERE record_type='claim' "
        "AND source_type='sentiment_day'").fetchone()
    srule = json.loads(srow["rule_refs_frozen"])
    assert srule[0]["rule_id"] == "icepoint_pick" and srule[0]["version"]
    sev = json.loads(srow["evidence_refs_frozen"])
    assert sev[0]["id"] == "icepoint_pick" and sev[0]["source_hash"]
    assert srow["input_hash"] == "unknown"  # 未传 content_hash 时如实 unknown
    c.close()


def test_p7_material_update_creates_new_record_old_frozen_unchanged(tmp_path):
    """证据材料更新 → 新记录带新哈希；旧冻结引用不被回写。"""
    mod = _load_script()
    syncdb = tmp_path / "mat.db"
    mod._open_ledger_db = lambda: connect(syncdb)
    fixture = {"records": [{"date": "2026-08-03",
                            "picks": [{"code": "BK1", "close": 100.0}],
                            "alarms": [], "origin": "live",
                            "content_hash": "h1"}]}
    mod._sync_observations(fixture)
    c = connect(syncdb)
    old_row = c.execute(
        "SELECT observation_id, evidence_refs_frozen FROM agent_observations "
        "WHERE record_type='claim'").fetchone()
    old_frozen = old_row["evidence_refs_frozen"]
    old_id = old_row["observation_id"]
    c.close()
    # 材料更新（content_hash 变化 → input_hash 变化 → 新主张身份）
    fixture["records"][0]["content_hash"] = "h2"
    mod._sync_observations(fixture)
    c = connect(syncdb)
    rows = c.execute(
        "SELECT observation_id, evidence_refs_frozen FROM agent_observations "
        "WHERE record_type='claim' ORDER BY created_at").fetchall()
    assert len(rows) == 2                       # 新记录生成
    kept = next(r for r in rows if r["observation_id"] == old_id)
    assert kept["evidence_refs_frozen"] == old_frozen  # 旧引用不变
    c.close()


# ---------------------------------------------------------------- P8 ----

def test_p8_batch_counts_grouped_by_source(tmp_path):
    c = _db(tmp_path, "counts")
    journal.save_recommendation(c, _card(["A"]))
    c.commit()
    ob.record_sentiment_day(c, date="2026-08-03",
                            picks=[{"code": "B", "close": 100.0}], alarms=[])
    c.commit()
    bc = ob.summarize(c)["display_batches"]
    assert bc == {"recommendation": 1, "sentiment_day": 1}  # 真正按来源分组
    c.close()


# ---------------------------------------------------------------- P9 ----

def test_p9_bad_symbol_isolated_good_evaluates(tmp_path):
    c = _db(tmp_path, "iso")
    ob.record_sentiment_day(c, date="2026-08-03",
                            picks=[{"code": "BAD", "close": 100.0},
                                   {"code": "GOOD", "close": 100.0}], alarms=[])
    c.commit()

    def lookup(code, d, h):
        if code == "BAD":
            raise ValueError("synthetic corrupt one symbol")
        return ("2026-09-01", 110.0)

    stats = ob.evaluate_sentiment_outcomes(c, lookup, today="2026-09-02")
    assert stats["ready_rows_reference"] >= 1    # 不再整单中断
    good = c.execute(
        "SELECT COUNT(*) AS n FROM agent_observation_outcomes oc "
        "JOIN agent_observations o USING(observation_id) "
        "WHERE o.instrument_id='GOOD' AND oc.status='ready'").fetchone()["n"]
    assert good >= 1
    bad_note = c.execute(
        "SELECT note FROM agent_observation_outcomes oc "
        "JOIN agent_observations o USING(observation_id) "
        "WHERE o.instrument_id='BAD' AND oc.status='missing_data'").fetchone()
    assert bad_note and "异常" in bad_note["note"]
    c.close()


def test_p9_numeric_strings_convert_invalid_never_ready(tmp_path):
    """数字字符串按明确规则转 float；NaN/Inf/非正统一无效不 ready。"""
    assert ob._to_finite_positive("100.5") == 100.5
    assert ob._to_finite_positive("abc") is None
    assert ob._to_finite_positive(True) is None
    assert ob._to_finite_positive(float("nan")) is None
    assert ob._to_finite_positive(float("inf")) is None
    assert ob._to_finite_positive(0) is None and ob._to_finite_positive(-5) is None
    c = _db(tmp_path, "numstr")
    ob.record_sentiment_day(c, date="2026-08-03",
                            picks=[{"code": "STR", "close": "100.0"},
                                   {"code": "ZERO", "close": 0}], alarms=[])
    c.commit()

    def lookup(code, d, h):
        return ("2026-09-01", 110.0)

    ob.evaluate_sentiment_outcomes(c, lookup, today="2026-09-02")
    rows = {r["instrument_id"]: r["status"] for r in c.execute(
        "SELECT o.instrument_id, oc.status FROM agent_observation_outcomes oc "
        "JOIN agent_observations o USING(observation_id) "
        "WHERE o.source_type='sentiment_day'")}
    assert rows["STR"] == "ready"               # 字符串基价先转 float 再算
    assert rows["ZERO"] == "missing_data"       # 非正 → 无效，不 ready
    c.close()


# ---------------------------------------------------------------- P10 ----

def test_p10_replay_filters_saved_future_results(tmp_path):
    mod = _load_script()
    cache = tmp_path / "review"
    cache.mkdir()
    mod.CACHE = cache
    mod.JOURNAL = cache / "sentiment_signal_journal.json"
    mod._open_ledger_db = lambda: None
    saved = {"records": [{
        "date": "2026-08-03", "picks": [{"code": "A", "close": 100.0}], "alarms": [],
        "review": {"t10": {"A": {"ret": .1, "eval_date": "2026-08-17"}},
                   "t20": {"A": {"ret": .2, "eval_date": "2026-08-31"}},
                   "a10": {}, "a20": {}, "done": True}}]}
    mod.JOURNAL.write_text(json.dumps(saved))
    (cache / "sector_trend_history.json").write_text("[]")
    buf = io.StringIO()
    with redirect_stdout(buf):
        mod.review(save=False, as_of="2026-08-04")
    out = buf.getvalue()
    assert "到期1个" not in out                 # 未来成绩不进重放视图（旧版打印）
    assert "重放截止后已有结果：2 项" in out     # 如实告知被过滤数量
    assert json.loads(mod.JOURNAL.read_text()) == saved  # 只读重放不抹历史


# ------------------------------------------- 迁移链路（023 旧行 → 024 → 025） ----

def _migrate_up_to(conn, max_ordinal):
    """手动按序执行 ≤max_ordinal 的迁移（模拟历史版本库逐步升级）。"""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "ordinal INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, "
        "applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    for ordinal, name, sql in sorted(MIGRATIONS):
        if ordinal > max_ordinal:
            continue
        done = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE name = ?", (name,)).fetchone()
        if done:
            continue
        conn.executescript(sql)
        conn.execute("INSERT INTO schema_migrations (ordinal, name) VALUES (?, ?)",
                     (ordinal, name))
    conn.commit()


def test_migration_023_rows_upgrade_to_025(tmp_path):
    """带 023 旧数据的库升级到 024/025：旧缺键记录标 unknown、按对象隔离，
    不混算、不导致查询失败（不只测空库建表）。"""
    import sqlite3 as sq

    path = tmp_path / "legacy.db"
    raw = sq.connect(path)
    raw.row_factory = sq.Row
    _migrate_up_to(raw, 23)
    # 023 时代的旧行（无 sample_key/eval_config_hash/legacy_quality 列）
    now = "2026-01-01T00:00:00"
    for sym, ver in (("A", "fwd_close_change_v1"), ("B", "fwd_close_change_v1")):
        oid = f"obs_old_{sym}"
        raw.execute(
            "INSERT INTO agent_observations (observation_id, schema_version, "
            "source_type, source_record_id, scope, strategy, instrument_id, "
            "event_group_id, observed_at, available_at, emitted_at, input_hash, "
            "payload_hash, payload, claim, horizons, direction, layer, "
            "evaluation_kind, evaluation_version, rule_refs, evidence_refs, "
            "legacy, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?"
            ",?,?,?,?,?,?,?,?,?,?)",
            (oid, 1, "recommendation", "2026-01-01", "", "", sym,
             "2026-01-01", "2026-01-01", None, now, "unknown", "x",
             '{"close":1}', "old", "[]", None, "observation",
             "fwd_close_change", ver, "[]", "[]", 1, now, now))
        raw.execute(
            "INSERT INTO agent_observation_outcomes (observation_id, "
            "evaluation_version, horizon, status, change_pct, evaluated_at) "
            "VALUES (?,?,5,'ready',1.5,?)", (oid, ver, now))
    raw.commit()
    # 升级 024 → 025（connect 会应用全部；此处手动分步验证）
    _migrate_up_to(raw, 25)
    qual = {r["instrument_id"]: r["legacy_quality"] for r in raw.execute(
        "SELECT instrument_id, legacy_quality FROM agent_observations "
        "WHERE observation_id LIKE 'obs_old_%'")}
    assert qual == {"A": "unknown", "B": "unknown"}  # 025 数据修复生效
    raw.close()
    # 用常规 connect 打开（全部迁移幂等）并查询：旧记录按对象隔离成 2 样本
    c = connect(path)
    buckets = [b for b in ob.summarize(c)["buckets"]
               if b["legacy_quality"] == "unknown"]
    assert sum(b["n_samples"] for b in buckets) == 2   # 不按版本压成 1 个
    recent = ob.recent_observations(c, instrument="A")
    assert all(r["instrument_id"] == "A" for r in recent)
    c.close()


def test_backfill_preview_hash_categories(tmp_path):
    """preview 分列 hash 归属；不符不迁挂；缺失（024 前旧行）按旧语义迁挂 legacy。"""
    c = _db(tmp_path, "prev")
    journal.save_recommendation(c, _card(["A"]))
    c.commit()
    journal.score_journal_outcomes(c, _svc(), today="2026-08-31")
    c.commit()
    # 制造一行 hash 不符：成绩挂在旧卡上
    journal.save_recommendation(c, _card(["A2"]))  # 换卡→outcome 清空
    c.commit()
    journal.score_journal_outcomes(c, _svc(), today="2026-08-31")
    c.commit()
    journal.save_outcome(c, "2026-08-03", {"A": {"chg_1d": 9.0}})
    c.commit()
    c.execute(
        "UPDATE recommendation_journal SET outcome_payload_hash = 'stale' "
        "WHERE run_date = '2026-08-03'")
    c.commit()
    # 另一行模拟 024 前旧行：hash 缺失（未被替换过 → 对应成立）
    journal.save_recommendation(c, _card(["OLD"], date="2026-07-01"))
    c.commit()
    # 模拟方式：直接把该行改成 024 前形态（hash 双缺失）+ 旧式成绩
    c.execute(
        "UPDATE recommendation_journal SET payload_hash = NULL, "
        "outcome_payload_hash = NULL WHERE run_date = '2026-07-01'")
    c.commit()
    journal.save_outcome(c, "2026-07-01", {"OLD": {"chg_1d": 3.0}})
    c.commit()
    c.execute(
        "UPDATE recommendation_journal SET outcome_payload_hash = NULL "
        "WHERE run_date = '2026-07-01'")
    c.commit()
    pv = ob.backfill_preview(c)
    assert pv["outcome_hash_mismatch_rows"] >= 1
    assert pv["outcome_hash_missing_rows"] >= 1
    ob.backfill_from_recommendation_journal(c)
    c.commit()
    # hash 不符 → 不迁挂；缺失（旧行）→ 迁挂为 legacy
    legacy = c.execute(
        "SELECT o.instrument_id FROM agent_observation_outcomes oc "
        "JOIN agent_observations o USING(observation_id) "
        "WHERE oc.evaluation_version = ?", (ob.LEGACY_EVAL_VERSION,)).fetchall()
    syms = {r["instrument_id"] for r in legacy}
    assert "OLD" in syms and "A" not in syms
    c.close()


# ------------------------------------------------ API instrument 过滤端到端 ----

def test_api_instrument_filter_end_to_end(tmp_path):
    """完整 API 按 instrument 查询：summary/recent/当前数量都不串其他标的。"""
    from fastapi.testclient import TestClient

    app = create_app()
    app.state.plans_db_path = str(tmp_path / "api.db")
    client = TestClient(app)
    with closing(connect(tmp_path / "api.db")) as conn:
        journal.save_recommendation(conn, _card(["AAA", "BBB"]))
        conn.commit()
    r = client.get("/api/copilot/observations", params={"instrument": "AAA"})
    assert r.status_code == 200
    body = r.json()
    recents = [x for x in body["recent"] if x["record_type"] == "claim"]
    assert recents and all(x["instrument_id"] == "AAA" for x in recents)
    cur = body["summary"]["current_observations"]
    assert cur.get("recommendation") == 1  # 只数 AAA，不是 2
    # recent 已结构化分版本 outcomes（无 outcome_line 原始拼串）
    assert "outcome_line" not in recents[0]
    assert recents[0]["outcomes"] and recents[0]["outcomes"][0]["status_cn"]
