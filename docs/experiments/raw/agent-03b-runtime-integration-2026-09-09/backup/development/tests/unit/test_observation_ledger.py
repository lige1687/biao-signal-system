"""Agent 观察存证账本 v1.2（GLM-02R 返修，2026-09-08）。

覆盖总控 00-review-contract-v1.2 与任务书验证清单：
- 探针 C—M 修复断言（新行为，不要求旧错误探针继续通过）；
- 同 payload 改 direction/claim/评价版本仍是新主张；
- 同日删除与空列表、A→B→A、旧修订键重试不重新成为当前；
- 同事件多次措辞修订只算一次研究样本；
- 两个来源各 1 条按来源分组；legacy 结果独立可见不相加；
- 结果写入显式三键（v1 不写 v2）；
- A 成熟 B 缺价后 B 能补；缺数据长期后可恢复（无 60 天停止）；
- 可信日历下中间缺一天 → 严格口径 missing_data 不按下一行补位，
  行参考口径独立成版；base/target NaN 不产出 ready；
- 截止日（as_of/today）前后隔离；
- 情绪同日修订不吞、同步失败可见且同日可重试、旧格式不按位置猜配、
  旧记录标 legacy 不并入真实前向；损坏单条旧记录不阻断其他记录；
- 迁入 preview 只读。
"""
from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch as _patch

import numpy as np
import pandas as pd
import pytest

from lei_signal.api.schemas import RecommendCardDTO, RecommendItemDTO
from lei_signal.copilot import journal
from lei_signal.copilot import observation as ob
from lei_signal.storage.sqlite_store import connect

# 09R/Q4：评价器以首次展示时间门控前向资格。旧测试以「过去的 observed_at
# + 现在的创建时间」构造数据，会把展示前结果判为历史观察——这与测试意图
# （当时记录、随后到期）不符。统一把记录时间注入为 2026-08-03 收盘后。
_SHOWN_AT = "2026-08-03T18:00:00+00:00"


@pytest.fixture(autouse=True)
def _fixed_shown_time():
    with _patch.object(ob, "_now", return_value=_SHOWN_AT):
        yield

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "sentiment_journal.py"


class _FakeEntry(SimpleNamespace):
    pass


class _FakeService:
    def __init__(self, frames: dict[str, pd.DataFrame], missing: set[str] = frozenset()):
        self._frames = frames
        self._missing = missing

    def get(self, symbol, refresh=False):
        if symbol in self._missing:
            raise KeyError(symbol)
        return _FakeEntry(result=_FakeEntry(frame=self._frames[symbol]), error=None)


def _frame(dates, closes) -> pd.DataFrame:
    return pd.DataFrame({"close": closes}, index=pd.DatetimeIndex(dates))


def _card(run_date: str, symbols: list[str]) -> RecommendCardDTO:
    return RecommendCardDTO(
        run_date=run_date,
        items=[RecommendItemDTO(symbol=s, verdict="waiting") for s in symbols],
    )


@pytest.fixture()
def conn(tmp_path):
    c = connect(str(tmp_path / "t.db"))
    yield c
    c.close()


# ============================================================ 探针 C（身份）


def _probe_record(c, *, version="v1", direction="up", claim="first",
                  refs=("r1",), payload=None):
    return ob.record_observations(
        c, source_type="probe", source_record_id="2026-08-03",
        observed_at="2026-08-03", evaluation_kind="probe",
        evaluation_version=version,
        items=[ob.ObservationItem(instrument_id="TEST",
                                  payload=payload or {"close": 100},
                                  claim=claim, direction=direction,
                                  horizons=(1,), rule_refs=refs)])


def test_probe_C_identity_includes_semantics(conn):
    """同 payload 改方向/claim/规则/评价版本 → 各自独立主张，不被去重折叠。"""
    _probe_record(conn)
    r2 = _probe_record(conn, version="v2", direction="down",
                       claim="opposite", refs=("r2",))
    rows = conn.execute(
        "SELECT direction, evaluation_version, rule_refs FROM agent_observations "
        "WHERE record_type='claim' ORDER BY direction"
    ).fetchall()
    assert r2["claims_inserted"] == 1
    assert len(rows) == 2
    assert {r["direction"] for r in rows} == {"up", "down"}


def test_same_payload_claim_change_is_new_claim(conn):
    """只改 claim 文案（payload 相同）也留新版本主张。"""
    _probe_record(conn, claim="第一次说看涨")
    r2 = _probe_record(conn, claim="第二次改口")
    assert r2["claims_inserted"] == 1
    assert conn.execute(
        "SELECT COUNT(*) c FROM agent_observations WHERE record_type='claim'"
    ).fetchone()["c"] == 2


def test_same_request_retry_deduped(conn):
    """完全相同语义重试只一份（主张+批次+outcome 档位都不重复）。"""
    _probe_record(conn)
    stats = _probe_record(conn)
    assert stats["claims_deduped"] == 1 and stats["batch_reused"] == 1
    assert conn.execute(
        "SELECT COUNT(*) c FROM agent_observations WHERE record_type='claim'"
    ).fetchone()["c"] == 1


# ============================================================ 探针 D（批次）


def test_probe_D_removal_and_empty_list(conn):
    """A+B→A、A→空：删除不靠新对象 insert 驱动，当前集合来自当前批次成员。"""
    journal.save_recommendation(conn, _card("2026-08-03", ["A", "B"]))
    journal.save_recommendation(conn, _card("2026-08-03", ["A"]))
    cur = ob.current_claim_ids(conn, "recommendation")
    assert len(cur) == 1  # 只剩 A 当前；B 留档但不在当前集合
    journal.save_recommendation(conn, _card("2026-08-03", []))
    assert ob.current_claim_ids(conn, "recommendation") == set()  # 空列表=有效展示
    n_batches = conn.execute(
        "SELECT COUNT(*) c FROM agent_observations WHERE record_type='display_batch'"
    ).fetchone()["c"]
    assert n_batches == 3  # 三次展示顺序完整保留


def test_probe_D_removed_claim_still_evaluated(conn):
    """被删掉的 B 说过的话仍按期对账（留档不算消失）。"""
    dates = pd.bdate_range("2026-08-03", periods=30)
    closes = [100.0 + i for i in range(30)]
    svc = _FakeService({
        "A": _frame(dates, closes),
        "B": _frame(dates, [50.0] * 30),
    })
    journal.save_recommendation(conn, _card("2026-08-03", ["A", "B"]))
    journal.save_recommendation(conn, _card("2026-08-03", ["A"]))
    journal.score_journal_outcomes(conn, svc, today="2026-09-15")
    b_ready = conn.execute(
        """
        SELECT COUNT(*) c FROM agent_observation_outcomes oc
        JOIN agent_observations o ON o.observation_id = oc.observation_id
        WHERE o.instrument_id='B' AND oc.status='ready'
          AND oc.evaluation_version = ?
        """,
        (ob.RECOMMENDATION_ROWS_VERSION,),
    ).fetchone()["c"]
    assert b_ready > 0


def test_ABA_preserves_three_batches_and_current(conn):
    """A→B→A：三个批次保序，当前=最后一次 A；紧跟同内容重试复用当前。"""
    journal.save_recommendation(conn, _card("2026-08-03", ["A"]))
    journal.save_recommendation(conn, _card("2026-08-03", ["B"]))
    journal.save_recommendation(conn, _card("2026-08-03", ["A"]))
    journal.save_recommendation(conn, _card("2026-08-03", ["A"]))  # 重试
    batches = conn.execute(
        "SELECT COUNT(*) c FROM agent_observations WHERE record_type='display_batch'"
    ).fetchone()["c"]
    assert batches == 3
    cur = ob.current_claim_ids(conn, "recommendation")
    assert len(cur) == 1


def test_stale_revision_key_retry_not_current(conn):
    """带明确旧修订键的重试：主张留档，但不重新成为当前批次。"""
    def rec(key, tag):
        return ob.record_observations(
            conn, source_type="keyed", source_record_id="2026-08-03",
            observed_at="2026-08-03", revision_key=key,
            evaluation_kind="probe", evaluation_version="v1",
            items=[ob.ObservationItem(instrument_id=tag, payload={"tag": tag},
                                      claim=f"claim {tag}", direction="up",
                                      horizons=(1,))])
    rec("rev1", "A")
    rec("rev2", "B")
    stats = rec("rev1", "A")  # 旧键重试
    assert stats["stale_revision_ignored"] == 1
    cur = ob.current_claim_ids(conn, "keyed")
    assert len(cur) == 1  # 当前仍是 B


# ============================================================ 探针 E（旧接口）


def test_probe_E_outcome_bound_to_card_version(conn):
    """卡片替换后 load_outcome 明确无匹配；旧原文+成绩先入 history 保全。"""
    journal.save_recommendation(conn, _card("2026-08-03", ["OLD"]))
    journal.save_outcome(conn, "2026-08-03", {"OLD": {"chg_1d": 9.0}})
    journal.save_recommendation(conn, _card("2026-08-03", ["NEW"]))
    assert journal.load_outcome(conn, "2026-08-03") is None  # 不再串卡
    hist = journal.load_history(conn, "2026-08-03")
    assert len(hist) == 1 and "OLD" in hist[0]["outcome"]
    # 同卡重存成绩仍可读
    journal.save_recommendation(conn, _card("2026-08-03", ["NEW"]))
    journal.save_outcome(conn, "2026-08-03", {"NEW": {"chg_1d": 1.0}})
    assert journal.load_outcome(conn, "2026-08-03") == {"NEW": {"chg_1d": 1.0}}


# ============================================================ 探针 F（legacy 可见）


def test_probe_F_legacy_visible_and_separate(conn):
    """旧版结果独立成桶可见，不与重算版相加。"""
    conn.execute(
        "INSERT INTO recommendation_journal (journal_id,run_date,payload,outcome,"
        "created_at,updated_at) VALUES (?,?,?,?,?,?)",
        ("rj_2026-08-03", "2026-08-03", _card("2026-08-03", ["A"]).model_dump_json(),
         json.dumps({"A": {"chg_1d": 9.0}}), "2026-08-03", "2026-08-03"),
    )
    stats = ob.backfill_from_recommendation_journal(conn)
    assert stats["claims_inserted"] == 1
    s = ob.summarize(conn)
    legacy = [b for b in s["buckets"] if b["evaluation_version"] == ob.LEGACY_EVAL_VERSION]
    # 09R/Q9 总控纠偏：hash 缺失不可证明归属——旧值完整保留可查（not_applicable
    # 行带原值），归属未知清楚，不进可靠 ready 分母（不与重算版相加）
    assert legacy and legacy[0]["n_ready_observations"] == 0
    assert legacy[0]["legacy_quality"] == "legacy"
    preserved = conn.execute(
        "SELECT change_pct, status, note FROM agent_observation_outcomes oc "
        "JOIN agent_observations o USING(observation_id) "
        "WHERE o.legacy_quality='legacy' AND oc.status='not_applicable'"
    ).fetchall()
    assert preserved and any(
        abs(r["change_pct"] - 9.0) < 1e-9 and "归属不可考" in r["note"]
        for r in preserved)
    # 再算一笔新版（行参考）也不与 legacy 相加：各版本独立成桶
    dates = pd.bdate_range("2026-08-03", periods=30)
    journal.save_recommendation(conn, _card("2026-08-03", ["A"]))
    journal.score_journal_outcomes(
        conn, _FakeService({"A": _frame(dates, np.arange(30) + 100.0)}), today="2026-09-15"
    )
    s2 = ob.summarize(conn)
    versions = {b["evaluation_version"] for b in s2["buckets"]}
    assert ob.LEGACY_EVAL_VERSION in versions and ob.RECOMMENDATION_ROWS_VERSION in versions
    for b in s2["buckets"]:
        assert not (b["evaluation_version"] == ob.LEGACY_EVAL_VERSION
                    and b["n_observations"] > 1)


def test_backfill_preview_readonly(conn):
    """迁入 preview 只读：不写库、mismatch/无法考证可见。"""
    conn.execute(
        "INSERT INTO recommendation_journal (journal_id,run_date,payload,outcome,"
        "created_at,updated_at) VALUES (?,?,?,?,?,?)",
        ("rj_2026-08-03", "2026-08-03", _card("2026-08-03", ["A"]).model_dump_json(),
         json.dumps({"GHOST": {"chg_1d": 9.0}}), "2026-08-03", "2026-08-03"),
    )
    before = conn.execute(
        "SELECT COUNT(*) c FROM agent_observations"
    ).fetchone()["c"]
    pv = ob.backfill_preview(conn)
    assert pv["journal_rows"] == 1 and pv["card_outcome_mismatch_rows"] == 1
    assert pv["mismatch_samples"] and pv["mismatch_samples"][0]["symbol"] == "GHOST"
    assert conn.execute(
        "SELECT COUNT(*) c FROM agent_observations"
    ).fetchone()["c"] == before  # 零写入
    # mismatch 成绩迁入时不挂到同日卡片（unknown 隔离）
    stats = ob.backfill_from_recommendation_journal(conn)
    assert stats["skipped_unattributable"] >= 1


# ============================================================ 探针 G（三键写入）


def test_probe_G_explicit_version_write(conn):
    """v1 评价器不填 v2 的 pending 行。"""
    dates = pd.bdate_range("2026-08-03", periods=10)
    journal.save_recommendation(conn, _card("2026-08-03", ["A"]))
    oid = conn.execute(
        "SELECT observation_id FROM agent_observations WHERE record_type='claim'"
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO agent_observation_outcomes (observation_id,evaluation_version,"
        "horizon,status) VALUES (?,?,1,'pending')",
        (oid, "different_exit_v2"),
    )
    ob.evaluate_recommendation_outcomes(
        conn, _FakeService({"A": _frame(dates, np.arange(10) + 100.0)}),
        today="2026-08-31",
    )
    v2 = conn.execute(
        "SELECT status FROM agent_observation_outcomes "
        "WHERE evaluation_version='different_exit_v2'"
    ).fetchall()
    assert all(r["status"] == "pending" for r in v2)


# ============================================================ 探针 H（恢复）


def test_probe_H_missing_data_recovers_without_time_limit(conn):
    """缺数据标 missing 后行情到位可恢复；长期（>60 天）不再永久停止。"""
    dates = pd.bdate_range("2026-08-03", periods=30)
    closes = [100.0 + i for i in range(30)]
    journal.save_recommendation(conn, _card("2026-08-03", ["A"]))
    ob.evaluate_recommendation_outcomes(
        conn, _FakeService({}), today="2026-11-03")  # 无数据 → missing/pending
    st1 = {r["status"] for r in conn.execute(
        "SELECT status FROM agent_observation_outcomes").fetchall()}
    assert "ready" not in st1
    # 长期后（>60 自然日）行情到位 → 仍被检查并恢复
    ob.evaluate_recommendation_outcomes(
        conn, _FakeService({"A": _frame(dates, closes)}), today="2026-12-01")
    st2 = {r["status"] for r in conn.execute(
        "SELECT status FROM agent_observation_outcomes "
        "WHERE evaluation_version=?", (ob.RECOMMENDATION_ROWS_VERSION,)).fetchall()}
    assert "ready" in st2


# ============================================================ 探针 I（缺日/坏值/双口径）


def test_probe_I_strict_calendar_gap_is_missing_not_shifted(conn):
    """可信日历下目标交易日缺价 → 严格口径 missing_data，不按下一行补位；
    行参考口径独立成版（如实记偏移后的日期）。"""
    cal_dates = pd.bdate_range("2026-08-03", periods=10)
    cal = ob.dict_calendar(cal_dates.strftime("%Y-%m-%d").tolist())
    journal.save_recommendation(conn, _card("2026-08-03", ["A"]))
    # 行情缺 08-04（h1 的目标交易日）
    f = _frame(cal_dates.delete(1), np.arange(9) * 2.0 + 100.0)
    ob.evaluate_recommendation_outcomes(
        conn, _FakeService({"A": f}), today="2026-08-31", calendar=cal)
    strict = conn.execute(
        "SELECT status, note FROM agent_observation_outcomes "
        "WHERE evaluation_version=? AND horizon=1",
        (ob.RECOMMENDATION_EVAL_VERSION,),
    ).fetchone()
    assert strict["status"] == "missing_data"
    assert "不按下一行补位" in strict["note"]
    ref = conn.execute(
        "SELECT status, eval_date FROM agent_observation_outcomes "
        "WHERE evaluation_version=? AND horizon=1",
        (ob.RECOMMENDATION_ROWS_VERSION,),
    ).fetchone()
    assert ref["status"] == "ready" and ref["eval_date"] == "2026-08-05"  # 行偏移参考


def test_probe_I_nan_base_and_target_isolated(conn):
    """NaN 起算价/目标价不产出 ready（坏值单对象隔离）。"""
    journal.save_recommendation(conn, _card("2026-08-03", ["A", "B"]))
    f_a = _frame(pd.bdate_range("2026-08-03", periods=5), [np.nan, 110.0, 111.0, 112.0, 113.0])
    f_b = _frame(pd.bdate_range("2026-08-03", periods=5),
                 [100.0, np.nan, 102.0, 103.0, 104.0])
    ob.evaluate_recommendation_outcomes(
        conn, _FakeService({"A": f_a, "B": f_b}), today="2026-08-31")
    rows = conn.execute(
        "SELECT status FROM agent_observation_outcomes "
        "WHERE evaluation_version=? AND status='ready'",
        (ob.RECOMMENDATION_ROWS_VERSION,),
    ).fetchall()
    assert not rows  # 坏值不 ready
    # 坏值标 missing 可恢复
    f_a2 = _frame(pd.bdate_range("2026-08-03", periods=5),
                  [100.0, 110.0, 111.0, 112.0, 113.0])
    ob.evaluate_recommendation_outcomes(
        conn, _FakeService({"A": f_a2, "B": f_b}), today="2026-08-31")
    a_ready = conn.execute(
        """
        SELECT COUNT(*) c FROM agent_observation_outcomes oc
        JOIN agent_observations o ON o.observation_id=oc.observation_id
        WHERE o.instrument_id='A' AND oc.status='ready'
          AND oc.evaluation_version=?
        """,
        (ob.RECOMMENDATION_ROWS_VERSION,),
    ).fetchone()["c"]
    assert a_ready > 0


def test_duplicate_and_bad_dates_isolated(conn):
    """重复日期/无日期/错误类型的行情不炸、单对象隔离。"""
    journal.save_recommendation(conn, _card("2026-08-03", ["A", "B"]))
    dup = pd.DataFrame(
        {"close": [100.0, 101.0, 100.5, 102.0]},
        index=pd.DatetimeIndex(pd.to_datetime(
            ["2026-08-03", "2026-08-04", "2026-08-04", "2026-08-05"])),
    )  # 08-04 重复行 → 保留后者 100.5
    bad = pd.DataFrame({"close": ["x", "y"]},
                       index=pd.DatetimeIndex(pd.to_datetime(["2026-08-03", "2026-08-04"])))
    ob.evaluate_recommendation_outcomes(
        conn, _FakeService({"A": dup, "B": bad}), today="2026-08-31")
    a = conn.execute(
        """
        SELECT oc.eval_price FROM agent_observation_outcomes oc
        JOIN agent_observations o ON o.observation_id=oc.observation_id
        WHERE o.instrument_id='A' AND oc.horizon=1
          AND oc.evaluation_version=? AND oc.status='ready'
        """,
        (ob.RECOMMENDATION_ROWS_VERSION,),
    ).fetchone()
    assert a is not None and a["eval_price"] == pytest.approx(100.5)
    b = conn.execute(
        """
        SELECT oc.status FROM agent_observation_outcomes oc
        JOIN agent_observations o ON o.observation_id=oc.observation_id
        WHERE o.instrument_id='B' AND oc.evaluation_version=?
        """,
        (ob.RECOMMENDATION_ROWS_VERSION,),
    ).fetchall()
    assert b and all(r["status"] in ("missing_data", "pending") for r in b)


# ============================================================ 探针 J（样本去重）


def test_probe_J_wording_revisions_single_sample(conn):
    """同日同板块改 z 展示值两次：展示 2 条、研究样本 1 个。"""
    for z in [1.6, 1.7]:
        ob.record_sentiment_day(conn, date="2026-08-03",
                                picks=[{"code": "A", "close": 100.0, "z": z}], alarms=[])
    ob.evaluate_sentiment_outcomes(conn, lambda *a: ("2026-09-01", 110.0),
                                   today="2026-09-02")
    s = ob.summarize(conn)
    for b in s["buckets"]:
        if b["horizon_days"] == 10 and b["direction"] == "up":
            assert b["n_observations"] == 2
            assert b["n_samples"] == 1


def test_conflicting_same_sample_excluded_from_rate(conn):
    """同 sample_key 结果冲突 → conflict 可见并从比例排除，不选较好那份。"""
    ob.record_sentiment_day(conn, date="2026-08-03",
                            picks=[{"code": "A", "close": 100.0, "z": 1.6}], alarms=[])
    ob.record_sentiment_day(conn, date="2026-08-03",
                            picks=[{"code": "A", "close": 200.0, "z": 1.6}], alarms=[])
    # 基价不同 → 同方向同标的同日：sample_key 仍相同（payload 不参与）
    def lookup(code, d, h):
        return ("2026-09-01", 110.0)
    ob.evaluate_sentiment_outcomes(conn, lookup, today="2026-09-02")
    s = ob.summarize(conn)
    b = next(x for x in s["buckets"]
             if x["horizon_days"] == 10 and x["direction"] == "up"
             and x["n_ready_observations"] > 0)  # 冲突出现在有 ready 的参考口径桶
    assert b["n_conflict_samples"] == 1
    assert b.get("hit_rate_pct") is None  # 冲突样本不进比例


# ============================================================ 探针 K（来源分组）


def test_probe_K_sources_grouped(conn):
    """推荐 1 条 + 情绪 1 条：当前对象数按来源分组各计 1。"""
    journal.save_recommendation(conn, _card("2026-08-03", ["A"]))
    ob.record_sentiment_day(conn, date="2026-08-03",
                            picks=[{"code": "B", "close": 100.0}], alarms=[])
    counts = ob.summarize(conn)["current_observations"]
    assert counts == {"recommendation": 1, "sentiment_day": 1}


# ============================================================ 探针 M（截止）


def test_probe_M_cutoff_isolation(conn):
    """today 之后的数据不可用：h1（≤截止当日）可评，h5/h20 保持待到期。"""
    dates = pd.bdate_range("2026-08-03", periods=22)
    closes = np.arange(22) + 100.0
    journal.save_recommendation(conn, _card("2026-08-03", ["A"]))
    ob.evaluate_recommendation_outcomes(
        conn, _FakeService({"A": _frame(dates, closes)}), today="2026-08-04")
    rows = conn.execute(
        "SELECT horizon, status FROM agent_observation_outcomes "
        "WHERE evaluation_version=? ORDER BY horizon",
        (ob.RECOMMENDATION_ROWS_VERSION,),
    ).fetchall()
    by_h = {r["horizon"]: r["status"] for r in rows}
    assert by_h[1] == "ready"      # 目标 08-04 == 截止日，可用
    assert by_h[5] == "pending"    # 08-10 > 截止 → 不可用
    assert by_h[20] == "pending"


def test_as_of_replay_excludes_later_rows(conn):
    """as_of 历史重放：晚于截止的行情行不可用（review --as-of 同口径）。"""
    dates = pd.bdate_range("2026-08-03", periods=22)
    closes = np.arange(22) + 100.0
    journal.save_recommendation(conn, _card("2026-08-03", ["A"]))
    ob.evaluate_recommendation_outcomes(
        conn, _FakeService({"A": _frame(dates, closes)}), as_of="2026-08-06")
    rows = {r["horizon"]: r["status"] for r in conn.execute(
        "SELECT horizon, status FROM agent_observation_outcomes "
        "WHERE evaluation_version=?",
        (ob.RECOMMENDATION_ROWS_VERSION,),
    ).fetchall()}
    # 截止 08-06：h1 目标 08-04 可评；h5 目标 08-10、h20 目标 08-31 均晚于截止 → 待到期
    assert rows[1] == "ready"
    assert rows[5] == "pending"
    assert rows[20] == "pending"


# ============================================================ 汇总口径


def test_zero_days_and_independent_event_unknown(conn):
    """零触发日不进分母；独立事件数未知（None）。"""
    ob.record_sentiment_day(conn, date="2026-08-01",
                            picks=[{"code": "BK0478", "close": 100.0}], alarms=[])
    ob.record_sentiment_day(conn, date="2026-08-02", picks=[], alarms=[])
    s = ob.summarize(conn)
    assert s["zero_trigger_days"].get("sentiment_day") == 1
    assert s["independent_event_count"] is None
    marker = conn.execute(
        "SELECT COUNT(*) c FROM agent_observation_outcomes oc "
        "JOIN agent_observations o ON o.observation_id=oc.observation_id "
        "WHERE o.instrument_id IS NULL"
    ).fetchone()["c"]
    assert marker == 0


def test_reference_and_strict_versions_not_summed(conn):
    """参考口径与严格口径分版本单列、互不相加。"""
    dates = pd.bdate_range("2026-08-03", periods=30)
    closes = np.arange(30) + 100.0
    journal.save_recommendation(conn, _card("2026-08-03", ["A"]))
    ob.evaluate_recommendation_outcomes(
        conn, _FakeService({"A": _frame(dates, closes)}), today="2026-09-15",
        calendar=ob.dict_calendar(dates.strftime("%Y-%m-%d").tolist()))
    s = ob.summarize(conn)
    strict = [b for b in s["buckets"] if b["evaluation_version"] == ob.RECOMMENDATION_EVAL_VERSION]
    ref = [b for b in s["buckets"] if b["evaluation_version"] == ob.RECOMMENDATION_ROWS_VERSION]
    assert strict and ref
    for b in strict:
        assert not b["is_reference_version"]
    for b in ref:
        assert b["is_reference_version"]
    # 每桶 n_observations 都是本版本自己的行数（一个观察两版本各自 ≤1 行/期限）
    assert all(b["n_observations"] == b["n_ready_observations"] + b["n_pending"]
               + b["n_missing"] + b["n_not_applicable"] for b in s["buckets"])


def test_recommendation_bucket_no_direction_rate(conn):
    """技术推荐观察无方向主张：桶不报命中率。"""
    dates = pd.bdate_range("2026-08-03", periods=30)
    journal.save_recommendation(conn, _card("2026-08-03", ["A"]))
    journal.score_journal_outcomes(
        conn, _FakeService({"A": _frame(dates, np.arange(30) + 100.0)}), today="2026-09-15")
    for b in ob.summarize(conn)["buckets"]:
        if b["source_type"] == "recommendation":
            assert "hit_rate_pct" not in b


def test_display_batch_not_in_buckets(conn):
    """展示批次无评价期限、不进任何分母。"""
    journal.save_recommendation(conn, _card("2026-08-03", ["A"]))
    for b in ob.summarize(conn)["buckets"]:
        assert b["n_observations"] >= 0  # 批次行不产生 outcome 行
    batches = conn.execute(
        "SELECT COUNT(*) c FROM agent_observation_outcomes oc "
        "JOIN agent_observations o ON o.observation_id=oc.observation_id "
        "WHERE o.record_type='display_batch'"
    ).fetchone()["c"]
    assert batches == 0


# ============================================================ 情绪脚本（隔离）


class _NotifySpy:
    calls: list[str] = []

    def __init__(self, *args, **kwargs):
        pass

    def send(self, payload):
        type(self).calls.append(payload.title)
        return True


@pytest.fixture()
def sent_env(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    cache.mkdir()
    monkeypatch.setenv("LEI_CACHE_ROOT", str(cache))
    monkeypatch.setenv("LEI_SQLITE_PATH", str(tmp_path / "lab.db"))
    monkeypatch.delenv("FEISHU_WEBHOOK_URL", raising=False)
    import lei_signal.notify.feishu_webhook as fw
    import lei_signal.notify.macos as mac

    monkeypatch.setattr(mac, "MacNotifier", _NotifySpy)
    monkeypatch.setattr(fw, "FeishuWebhookNotifier", _NotifySpy)
    _NotifySpy.calls.clear()

    def _load():
        spec = importlib.util.spec_from_file_location(
            f"sentiment_journal_{id(tmp_path)}_{len(_NotifySpy.calls)}", SCRIPT
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    return SimpleNamespace(cache=cache, db=str(tmp_path / "lab.db"), load=_load)


def _write_sent_fixtures(env, *, boards_with_b=False, snap_date="2026-08-03"):
    dates = pd.bdate_range("2026-08-03", periods=34)
    recs = []
    for i, d in enumerate(dates):
        boards = {"BK0478": {"close": 100.0 + 0.6 * i}}
        if boards_with_b:
            boards["BK1036"] = {"close": 200.0 - 1.0 * i}
        recs.append({"date": d.strftime("%Y-%m-%d"), "boards": boards})
    (env.cache / "sector_trend_history.json").write_text(json.dumps(recs))
    snap = {"trading_day": snap_date, "as_of": f"{snap_date}T16:00:00+08:00",
            "sentiment_signals": {"cn_cold": False},
            "boards": [
                {"code": "BK0478", "name": "有色", "sig_icepoint_pick": True,
                 "sig_retail_z": 1.9, "close": 100.0, "b50": 20},
                {"code": "BK1036", "name": "半导体", "sig_heat_alarm": True,
                 "sig_retail_z": 2.3, "close": 200.0, "b50": 92},
            ]}
    (env.cache / "sector_trend_snapshot.json").write_text(json.dumps(snap))


def test_probe_L_partial_day_not_done_and_recovers(sent_env, capsys):
    """A 有价 B 缺价：整天不标 done；B 行情补齐后下次 review 恢复。"""
    _write_sent_fixtures(sent_env, boards_with_b=False)
    mod = sent_env.load()
    mod.record()
    mod.review()
    rec = json.loads(
        (sent_env.cache / "sentiment_signal_journal.json").read_text()
    )["records"][-1]
    assert rec["review"].get("done") is not True  # 缺价对象挂起整天
    assert "BK0478" in rec["review"]["t10"]
    assert "BK1036" not in rec["review"].get("a10", {})  # 缺价对象未成熟（组键可缺省）
    # 补齐 B 行情 → 恢复
    hist = json.loads((sent_env.cache / "sector_trend_history.json").read_text())
    for i, r in enumerate(hist):
        r["boards"]["BK1036"] = {"close": 200.0 - 1.0 * i}
    (sent_env.cache / "sector_trend_history.json").write_text(json.dumps(hist))
    mod.review()
    rec = json.loads(
        (sent_env.cache / "sentiment_signal_journal.json").read_text()
    )["records"][-1]
    assert rec["review"].get("done") is True
    assert "BK1036" in rec["review"]["a10"]


def test_sentiment_same_day_revision_not_swallowed(sent_env, capsys):
    """同日快照内容变化 → 修订留档（旧记录标 superseded），不吞掉。"""
    _write_sent_fixtures(sent_env)
    mod = sent_env.load()
    mod.record()
    # 同日改内容：去掉半导体警报
    snap = json.loads((sent_env.cache / "sector_trend_snapshot.json").read_text())
    snap["boards"] = [b for b in snap["boards"] if not b.get("sig_heat_alarm")]
    snap["trading_day"] = "2026-08-03"
    (sent_env.cache / "sector_trend_snapshot.json").write_text(json.dumps(snap))
    mod.record()
    out = capsys.readouterr().out
    assert "修订" in out or "第 2 版" in out
    records = json.loads(
        (sent_env.cache / "sentiment_signal_journal.json").read_text()
    )["records"]
    same_day = [r for r in records if r["date"] == "2026-08-03"]
    assert len(same_day) == 2
    assert same_day[0].get("superseded") is True  # 旧话保留
    assert same_day[1].get("superseded") is not True


def test_sentiment_sync_failure_visible_and_retryable(sent_env, capsys, monkeypatch):
    """同步失败可见；同日同内容重试会重跑同步（不因已存证而吞掉）。"""
    _write_sent_fixtures(sent_env)
    mod = sent_env.load()
    # 注入一次同步失败：_open_ledger_db 返回损坏连接
    class _BrokenConn:
        def execute(self, *a, **k):
            raise sqlite3.OperationalError("injected")

        def commit(self):
            raise sqlite3.OperationalError("injected")

        def rollback(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(mod, "_open_ledger_db", lambda: _BrokenConn())
    mod.record()
    out = capsys.readouterr().out
    assert "✗ 观察账本未同步" in out  # 失败可见
    # 同日同内容重试 → 不追加、重跑同步成功
    mod2 = sent_env.load()
    mod2.record()
    out3 = capsys.readouterr().out
    assert "跳过追加" in out3 and "✓ 观察账本同步" in out3
    records = json.loads(
        (sent_env.cache / "sentiment_signal_journal.json").read_text()
    )["records"]
    assert len([r for r in records if r["date"] == "2026-08-03"]) == 1


def test_sentiment_old_format_not_positionally_matched(sent_env, capsys):
    """旧格式纯列表结果：整体转 legacy 原样保留，不按位置猜配对象。"""
    _write_sent_fixtures(sent_env)
    mod = sent_env.load()
    mod.JOURNAL.write_text(json.dumps({"records": [{
        "date": "2026-07-20",
        "picks": [{"code": "OLD1", "close": 100.0}, {"code": "OLD2", "close": 50.0}],
        "alarms": [], "as_of": None,
        "review": {"t10": [0.05, -0.02], "t20": [0.1]},
    }]}))
    mod.review()
    rec = json.loads(mod.JOURNAL.read_text())["records"][0]
    assert "legacy_t10" in rec["review"] and "t10" not in rec["review"]
    assert rec["review"]["legacy_t10"] == [0.05, -0.02]  # 原样保留
    out = capsys.readouterr().out
    assert "旧格式遗留收益列表" in out and "不并入" in out


def test_sentiment_legacy_records_marked_legacy_in_ledger(sent_env):
    """旧情绪记录（无 origin 标记）同步进观察账本标 legacy，不并入真实前向。"""
    _write_sent_fixtures(sent_env)
    mod = sent_env.load()
    mod.JOURNAL.write_text(json.dumps({"records": [
        {"date": "2026-07-20", "picks": [{"code": "OLD1", "close": 100.0}],
         "alarms": [], "as_of": None, "review": {}},
        {"date": "2026-07-21", "picks": [], "alarms": [], "review": {}},
    ]}))
    mod.record()  # live 记录 + 同步全部
    conn = connect(sent_env.db)
    quals = {r["legacy_quality"]: r["n"] for r in conn.execute(
        "SELECT legacy_quality, COUNT(*) n FROM agent_observations "
        "WHERE source_type='sentiment_day' AND record_type='claim' "
        "GROUP BY legacy_quality")}
    conn.close()
    assert quals.get("legacy", 0) >= 1 and quals.get("ok", 0) >= 1


def test_sentiment_corrupted_record_does_not_block_others(sent_env, capsys):
    """损坏的单条旧记录（坏基价/坏结构）不阻断其他记录评价。"""
    _write_sent_fixtures(sent_env, boards_with_b=True)
    mod = sent_env.load()
    mod.JOURNAL.write_text(json.dumps({"records": [
        {"date": "2026-07-20", "picks": [{"code": "X", "close": "garbage"}],
         "alarms": [], "review": {}},          # 坏基价
        "corrupted-not-a-dict",                  # 损坏记录
        {"date": "2026-07-21", "picks": [], "alarms": [], "review": {}},
    ]}))
    mod.review()  # 不抛错
    out = capsys.readouterr().out
    assert "坏基价" in out


def test_sentiment_dry_run_zero_write_both_sides(sent_env):
    """dry-run：JSON 与 SQLite 均零写入、零通知。"""
    _write_sent_fixtures(sent_env)
    mod = sent_env.load()
    assert mod.record(dry_run=True) == 0
    assert not (sent_env.cache / "sentiment_signal_journal.json").exists()
    assert not Path(sent_env.db).exists()
    assert _NotifySpy.calls == []


def test_sentiment_as_of_cutoff(sent_env):
    """review --as-of：晚于截止的行情行不可用。"""
    _write_sent_fixtures(sent_env, boards_with_b=True)
    mod = sent_env.load()
    mod.record()
    mod.review(as_of="2026-08-10")  # 只允许 08-10 前的行情
    rec = json.loads(
        (sent_env.cache / "sentiment_signal_journal.json").read_text()
    )["records"][-1]
    # T+10 目标行 08-17 > 截止 08-10 → 不评
    assert "BK0478" not in rec["review"].get("t10", {})
    mod.review(as_of="2026-09-30")
    rec = json.loads(
        (sent_env.cache / "sentiment_signal_journal.json").read_text()
    )["records"][-1]
    assert "BK0478" in rec["review"]["t10"]
