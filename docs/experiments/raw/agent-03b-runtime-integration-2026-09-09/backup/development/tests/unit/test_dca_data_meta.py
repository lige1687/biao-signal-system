"""证据读取与数据日期元信息测试（01R 返修版，契约 v1.2）。

覆盖总控验收 R01/R02/R07 的正确行为（本文件取代 round-01 版测试中按旧
语义写的断言；总控 reproduce.py 是错误行为证据，不在此复跑）：
A. 默认路径（不注入）读真实账本/种子；幂等；用户评价不被覆盖；
B. 证据缺失/损坏、种子损坏 → 可识别降级，不冒充正常空结果；
C. R01：未知日历 / 参考日历自身停更 / 未来日期 → 一律不能 current=true
   （unknown 不默认当前；无统一 N 日宽限）；
D. R02：按状态依赖分列——deep20 只依赖价格（宽度缺失不压制）；bottom_zone
   缺宽度 active=null（≠false）；价格尾行 NaN 裁剪降级且严格 JSON 合法；
   滚动窗口缺值 → 对应字段 null；
E. v1.2 引用：source_hash 冻结/变更；compatibility 默认 unknown，不同
   对象/方法不得共用 exact；胜率表引用适配；
F. 数值与信号判定不变（同一合成输入与 round-01 相同结果）。
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from lei_signal.api.app import create_app
from lei_signal.data_provenance import (
    COMPAT_UNKNOWN,
    MarketDataRef,
    SourcePolicy,
    assess_freshness,
    evidence_ref,
    file_source_hash,
    reference_calendar,
    winrate_evidence_ref,
)
from lei_signal.dca import service
from lei_signal.dca.state import compute_state, read_breadth

REPO = Path(__file__).resolve().parents[2]

NOW = datetime(2026, 9, 7, 22, 0)           # 周一收盘后
CAL_DATES = pd.bdate_range("2026-08-01", "2026-09-07")  # 覆盖到今天
POLICY_CN = SourcePolicy("cn", publish_by="16:30", tz="Asia/Shanghai",
                         verified=True, basis="test")
POLICY_US = SourcePolicy("us", publish_by="18:00", tz="America/New_York",
                         verified=True, basis="test")


def _crash_bars(end: str = "2026-09-07", tail_nan: int = 0) -> pd.DataFrame:
    """前 200 根 100 → 后 100 根跌到 70（距年线约 −30%：深超跌+底部区域形态）。"""
    n = 300
    if tail_nan:
        idx = pd.bdate_range(end=end, periods=n + tail_nan)
        close = np.concatenate([
            np.full(200, 100.0), np.linspace(100.0, 70.0, 100),
            np.full(tail_nan, np.nan)])
    else:
        idx = pd.bdate_range(end=end, periods=n)
        close = np.concatenate([np.full(200, 100.0), np.linspace(100.0, 70.0, 100)])
    open_ = np.roll(close, 1)
    open_[0] = 100.0
    return pd.DataFrame({"open": np.where(np.isnan(close), np.nan, open_),
                         "close": close}, index=idx)


def _evidence(tmp_path: Path) -> Path:
    ev = tmp_path / "evidence.json"
    ev.write_text(json.dumps({
        "version": "test-ledger-v1",
        "state_expectations": {
            "deep20": {"label": "深超跌", "horizon_stats": {"6m": "中位+12.8%"},
                       "source": "dca-entry-timing-table-2026-09-07",
                       "status": "active", "window": "test-window"},
            "bottom_zone": {"label": "底部区域",
                            "horizon_stats": {"12m": "中位+4.6%"},
                            "source": "dca-entry-timing-table-2026-09-07",
                            "status": "downgraded", "window": "test-window"},
            "tier_low": {"label": "惨档", "horizon_stats": {"12m": "中位+2.0%"},
                         "source": "dca-entry-timing-table-2026-09-07",
                         "status": "active", "window": "test-window"},
        },
        "ambush_template": {"entry": "底部区域或惨档触发",
                            "source": "dca-complete-trades-2026-09-07",
                            "status": "active", "window": "test-window"},
    }, ensure_ascii=False), encoding="utf-8")
    return ev


def _ev_dict(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _client(tmp_path: Path, *, evidence: Path | None,
            seed: Path | None = None,
            breadth_override: dict | None = None) -> TestClient:
    app = create_app()
    app.state.dca_db_path = str(tmp_path / "dca_test.db")
    app.state.mindset_db_path = str(tmp_path / "mindset_test.db")
    if evidence is not None:
        app.state.dca_evidence_path = evidence
    if seed is not None:
        app.state.mindset_seed_path = seed
    if breadth_override is not None:
        app.state.dca_breadth_override = breadth_override
    app.state.dca_data_loader = (
        lambda symbol: _crash_bars() if symbol == "000300" else None)
    return TestClient(app)


def _svc_kit() -> dict:
    """注入式服务参数：已核实发布策略 + 覆盖到今天的日历。"""
    return {"now": NOW,
            "policies": {"cn": POLICY_CN, "us": POLICY_US},
            "calendars": {"cn": CAL_DATES, "us": CAL_DATES}}


_EMPTY_EV = {"version": "", "state_expectations": {}}

# ---------------- A. 默认路径（不注入） ----------------

def test_default_evidence_path_reads_real_ledger(tmp_path: Path):
    client = _client(tmp_path, evidence=None,
                     breadth_override={"cn": 26.0, "us": 61.0})
    body = client.get("/api/dca/evidence").json()
    assert body["available"] is True
    assert body["version"] == json.loads(
        (REPO / "configs" / "dca_evidence.json").read_text(encoding="utf-8")
    )["version"]
    assert "deep20" in body["state_expectations"]
    meta = body["meta"]
    assert meta["available"] is True
    refs = {r["id"]: r for r in meta["refs"]}
    assert refs["deep20"]["status"] == "active"
    assert refs["deep20"]["source_hash"]          # v1.2：材料内容哈希
    assert refs["deep20"]["compatibility"] == COMPAT_UNKNOWN  # 不默认 exact
    rules = {r["rule_id"]: r for r in meta["rules"]}
    assert rules["dca_state_thresholds"]["version"]
    assert rules["dca_state_thresholds"]["config_hash"]


def test_default_mindset_seed_imports_on_fresh_db(tmp_path: Path):
    client = _client(tmp_path, evidence=None)
    r1 = client.get("/api/mindset/items").json()
    assert r1["seed"]["available"] is True and r1["seed"]["status"] == "ok"
    assert len(r1["items"]) >= 20
    r2 = client.get("/api/mindset/items").json()
    assert len(r2["items"]) == len(r1["items"])
    assert r2["seed"]["imported_now"] == 0
    item = r1["items"][0]
    client.patch(f"/api/mindset/items/{item['id']}/status",
                 json={"status": "disagree"})
    r3 = client.get("/api/mindset/items").json()
    assert next(i for i in r3["items"]
                if i["id"] == item["id"])["status"] == "disagree"


# ---------------- B. 可识别降级 ----------------

def test_evidence_missing_degrades_identifiably(tmp_path: Path):
    client = _client(tmp_path, evidence=tmp_path / "nope.json",
                     breadth_override={"cn": 26.0, "us": 61.0})
    body = client.get("/api/dca/evidence").json()
    assert body["available"] is False
    assert body["error_code"] == service.EVIDENCE_MISSING
    assert "读不到依据" in body["note"]
    st = client.get("/api/dca/state", params={"symbols": "000300"}).json()
    assert st["states"][0]["deep20"] is True
    assert st["states"][0]["expectation"] is None
    assert st["data_meta"]["evidence"]["error_code"] == service.EVIDENCE_MISSING


def test_evidence_corrupt_degrades_identifiably(tmp_path: Path):
    ev = tmp_path / "broken.json"
    ev.write_text("{not json", encoding="utf-8")
    client = _client(tmp_path, evidence=ev,
                     breadth_override={"cn": 26.0, "us": 61.0})
    body = client.get("/api/dca/evidence").json()
    assert body["available"] is False
    assert body["error_code"] == service.EVIDENCE_CORRUPT
    assert client.get("/api/dca/triggers").status_code == 200


def test_mindset_seed_corrupt_flagged_not_silent(tmp_path: Path):
    seed = tmp_path / "seed.json"
    seed.write_text("{oops", encoding="utf-8")
    client = _client(tmp_path, evidence=None, seed=seed)
    body = client.get("/api/mindset/items").json()
    assert body["seed"]["status"] == "corrupt"
    assert body["items"] == []


# ---------------- C. R01：未知/停更日历、未来日期 ≠ 当前 ----------------

def test_r01_unknown_calendar_never_current(tmp_path):
    """无日历：bottom_zone 触发保留为历史事实，但 current=None（未知≠当前）。"""
    ev = _evidence(tmp_path)
    board = service.triggers_board(
        lambda s: _crash_bars(end="2026-08-03") if s == "000300" else None,
        _ev_dict(ev), symbols=[("000300", "测试")], b200_cn=26.0,
        now=NOW, calendars={"cn": None, "us": None})  # 无日历，策略也未注册
    row = next(r for r in board["detail"]["bottom_zone"]
               if r["symbol"] == "000300")
    assert row["bottom_zone"] is True            # 事实保留
    assert row["current"] is None                # 未知不默认当前（旧版为 True）
    assert row["signals"]["bottom_zone"]["health"] == "unknown"


def test_r01_stale_reference_calendar_not_fresh(tmp_path):
    """值与参考日历同停 8-03：即便发布策略已核实，参考没覆盖到发布截止已过
    的今天 → unknown；无统一 5 日宽限，不再返回 ok。"""
    stale_cal = pd.bdate_range("2026-08-01", "2026-08-03")
    a = assess_freshness("2026-08-03", "cn", now=NOW, policy=POLICY_CN,
                         calendar=reference_calendar("cn", stale_cal))
    assert a.health == "unknown"
    assert "不能证明当前" in a.reason or "未覆盖" in a.reason
    # 旧签名兼容投影同样不再 ok（旧版返回 ("ok", 0)）
    import lei_signal.data_provenance as dp

    with pytest.MonkeyPatch.context() as mk:
        mk.setattr(dp, "market_trading_dates", lambda m: stale_cal)
        health, _lag = dp.classify_freshness("2026-08-03", "cn")
    assert health == "unknown"


def test_r01_future_date_never_fresh(tmp_path):
    a = assess_freshness("2027-01-01", "cn", now=NOW, policy=POLICY_CN,
                         calendar=reference_calendar("cn", CAL_DATES))
    assert a.health == "unknown"                 # 旧版返回 ("ok", 0)
    assert "未来" in a.reason


def test_r01_fresh_and_stale_discriminated_with_policy(tmp_path):
    good = reference_calendar("cn", CAL_DATES)
    assert assess_freshness("2026-09-07", "cn", now=NOW, policy=POLICY_CN,
                            calendar=good).health == "fresh"
    s = assess_freshness("2026-09-02", "cn", now=NOW, policy=POLICY_CN,
                         calendar=good)
    assert s.health == "stale" and s.reference_lag_trading_days == 3


# ---------------- D. R02：按状态依赖分列 ----------------

def test_r02_deep20_independent_of_missing_breadth(tmp_path):
    """价格完整（fresh）+ 宽度缺失：deep20 照常触发且 current=True；
    bottom_zone active=None（不可判，≠false）；不是整行 data_unavailable。"""
    ev = _evidence(tmp_path)
    missing_b = MarketDataRef(source_id="missing_breadth", market="cn_all",
                              health="missing", reason="宽度文件缺失")
    board = service.triggers_board(
        lambda s: _crash_bars() if s == "000300" else None,
        _ev_dict(ev), symbols=[("000300", "测试")], b200_cn=None,
        breadth_meta={"cn": missing_b}, **_svc_kit())
    assert board["data_unavailable"] == []
    row = next(r for r in board["detail"]["deep20"] if r["symbol"] == "000300")
    assert row["deep20"] is True
    assert row["current"] is True                # 旧版被缺失宽度压成 False
    sig = row["signals"]
    assert sig["deep20"]["active"] is True and sig["deep20"]["current"] is True
    assert sig["bottom_zone"]["active"] is None  # 宽度缺失 → 无法判定
    assert "000300" in board["unjudgeable"]["bottom_zone"]
    assert board["bottom_zone_triggered"] == []  # null 不进触发表


def test_r02_price_nan_tail_degrades_json_legal(tmp_path):
    """价格尾行 NaN：裁到最后有效收盘、state_status=degraded、严格 JSON 合法。"""
    bad = _crash_bars(tail_nan=3)
    st = compute_state("000300", "测试", bad, 26.0)
    assert st.state_status == "degraded"
    assert st.as_of == "2026-09-02"              # 最后有效收盘（跳过 9-03/04/07 三行 NaN）
    assert st.close == pytest.approx(70.0) and np.isfinite(st.close)
    json.dumps(st.to_dict(), allow_nan=False)    # 不再输出非法 JSON
    row = service.targets_state(
        lambda s: bad if s == "000300" else None, _EMPTY_EV,
        symbols=[("000300", "测试")], b200_cn=26.0, **_svc_kit())[0]
    json.dumps(row, allow_nan=False)


def test_r02_rolling_window_missing_yields_null(tmp_path):
    """有效收盘不足 220 根：insufficient_data，deep20/bottom_zone=None（≠false）。"""
    tiny = pd.DataFrame(
        {"close": np.linspace(100.0, 90.0, 199)},
        index=pd.bdate_range(end="2026-09-07", periods=199))
    st = compute_state("000300", "测试", tiny, 26.0)
    assert st.state_status == "insufficient_data"
    assert st.deep20 is None and st.bottom_zone is None
    assert json.dumps(st.to_dict(), allow_nan=False)


def test_r02_stale_price_trigger_is_historical_not_current(tmp_path):
    """今天生成、旧行情：deep20 触发保留为历史事实，current=False（确认滞后）。"""
    ev = _evidence(tmp_path)
    board = service.triggers_board(
        lambda s: _crash_bars(end="2026-08-27") if s == "000300" else None,
        _ev_dict(ev), symbols=[("000300", "测试")], b200_cn=26.0,
        now=NOW, policies={"cn": POLICY_CN},
        calendars={"cn": CAL_DATES})
    row = next(r for r in board["detail"]["deep20"] if r["symbol"] == "000300")
    assert row["deep20"] is True
    assert row["current"] is False
    assert row["as_of"] == "2026-08-27"
    assert "000300" in board["stale_data_triggers"]
    assert "不称当前机会" in board["note"]


# ---------------- 宽度读取（NaN 尾/缺文件/无策略） ----------------

def _write_breadth(cache: Path, market: str, *, tail_nan: int = 0,
                   end: str = "2026-09-07") -> None:
    idx = pd.bdate_range(end=end, periods=30)
    vals = np.full(30, 55.0)
    if tail_nan:
        vals[-tail_nan:] = np.nan
    pd.DataFrame({"b200": vals}, index=idx).to_parquet(
        cache / f"breadth_{market}.parquet")


def test_read_breadth_nan_tail_uses_last_valid(tmp_path):
    _write_breadth(tmp_path, "sp500", tail_nan=3)
    r = read_breadth("sp500", cache_dir=tmp_path)
    assert r.value == pytest.approx(55.0)
    assert r.observed_at == "2026-09-07"
    assert r.last_valid_at == "2026-09-02"
    assert r.observed_at != r.last_valid_at
    d = r.meta().to_dict()
    assert d["last_valid_at"] == "2026-09-02" and d["available_at"] is None


def test_read_breadth_long_nan_tail_incomplete(tmp_path):
    _write_breadth(tmp_path, "sp500", tail_nan=6, end="2026-09-07")
    r = read_breadth("sp500", cache_dir=tmp_path)
    assert r.health == "incomplete"              # 尾部长期缺值单列
    assert r.value == pytest.approx(55.0)


def test_read_breadth_missing_file(tmp_path):
    r = read_breadth("cn_all", cache_dir=tmp_path)
    assert r.value is None and r.health == "missing"
    assert r.meta().to_dict()["health"] == "missing"


def test_read_breadth_default_unknown_without_policy(tmp_path):
    """无已核实发布策略：即便值是今天的，health=unknown（不默认当前）。"""
    _write_breadth(tmp_path, "cn_all", end="2026-09-07")
    r = read_breadth("cn_all", cache_dir=tmp_path, now=NOW)
    assert r.last_valid_at == "2026-09-07"
    assert r.health == "unknown"
    assert "未核实" in r.reason


# ---------------- E. v1.2 引用：哈希冻结 / 兼容性 ----------------

def test_evidence_hash_changes_and_frozen_ref_stable(tmp_path):
    """修改材料后新引用哈希改变；先前冻结的引用 dict 保持不变。"""
    (tmp_path / "docs" / "experiments").mkdir(parents=True)
    src = tmp_path / "docs" / "experiments" / "src_experiment.md"
    src.write_text("v1 内容", encoding="utf-8")
    entry = {"source": "src_experiment", "status": "active", "window": "w",
             "note": "n"}
    frozen = evidence_ref("deep20", entry, ledger_version="L1",
                          repo_root=tmp_path).to_dict()
    old_hash = frozen["source_hash"][0]
    time.sleep(0.02)
    src.write_text("v2 内容——材料被修改", encoding="utf-8")
    new = evidence_ref("deep20", entry, ledger_version="L1",
                       repo_root=tmp_path).to_dict()
    assert new["source_hash"][0] != old_hash
    assert frozen["source_hash"][0] == old_hash     # 冻结引用不被追溯改写
    assert frozen["id"] == "deep20" and frozen["evidence_id"] == "deep20"


def test_compatibility_unknown_and_winrate_adapter():
    """不同标的/方法不得共用 exact：默认 unknown；胜率表引用适配附限制。"""
    ref = winrate_evidence_ref("510300", "A")
    d = ref.to_dict()
    assert d["compatibility"] == COMPAT_UNKNOWN
    assert "不得标 exact" in d["limitations"]
    ref_b = winrate_evidence_ref("510300", "B")
    assert ref_b.id != ref.id                       # 对象/方法分开
    assert file_source_hash(REPO / "docs/experiments/module_winrate.json")


# ---------------- F. 数值与信号判定不变 ----------------

def test_signal_values_unchanged_from_round01():
    """同一合成输入：deep20/bottom_zone/tier 判定与 round-01 相同。"""
    st = compute_state("000300", "测试", _crash_bars(), 26.0)
    assert st.deep20 is True
    assert st.bottom_zone is True
    assert st.tier == "low"
    assert st.state_status == "ok"
    st_flat = compute_state("000300", "测试", pd.DataFrame(
        {"close": np.full(300, 100.0)},
        index=pd.bdate_range(end="2026-09-07", periods=300)), 61.0)
    assert st_flat.deep20 is False and st_flat.tier == "high"


def test_state_board_route_shapes(tmp_path):
    """路由层：新旧字段并存（signals 结构化 + 兼容别名），JSON 严格合法。"""
    ev = _evidence(tmp_path)
    client = _client(tmp_path, evidence=ev,
                     breadth_override={"cn": 26.0, "us": 61.0})
    body = client.get("/api/dca/state", params={"symbols": "000300"}).json()
    row = body["states"][0]
    assert row["signals"]["deep20"]["active"] is True
    assert "current" in row["signals"]["deep20"]
    assert row["data_freshness"]["freshness"]          # 兼容别名仍在
    assert body["data_meta"]["breadth"]["cn"]["last_valid_at"] is None
    # 注入覆盖值无日期 → unknown，不得当当前
    assert body["data_meta"]["breadth"]["cn"]["health"] == "unknown"
    json.dumps(body, allow_nan=False)


# ---------------- #5：冰点/强热共用参数一致性（显式冲突，不静默） ----------------

def test_icepoint_heat_param_conflict_raises(monkeypatch, tmp_path):
    """两条目共用参数不一致 → 显式配置冲突（不得静默忽略强热参数）。"""
    import lei_signal.market_context.sentiment_signals as ss
    from lei_signal.domain import rules_config

    base = {
        "ruleset_version": "9.9.9-test",
        "rules": {
            "icepoint_pick": {"version": "0.1.0", "params": {
                "z_threshold": 1.5, "retail_window": 20,
                "z_base_window": 120, "r60_max": -10.0, "b50_max": 30.0}},
            "heat_alarm": {"version": "0.1.0", "params": {
                "z_threshold": 2.0, "retail_window": 20,
                "z_base_window": 120, "b50_min": 70.0, "b200_min": 70.0}},
        },
    }
    import yaml

    p = tmp_path / "rules_test.yaml"
    p.write_text(yaml.safe_dump(base, allow_unicode=True), encoding="utf-8")
    monkeypatch.setattr(rules_config, "load_ruleset",
                        lambda path=None: rules_config.load_ruleset(str(p))
                        if False else __import__("yaml").safe_load(p.read_text()))
    with pytest.raises(ValueError, match="配置冲突"):
        ss._cfg()


def test_icepoint_heat_params_consistent_in_real_ledger():
    """真实账本：两条目共用参数当前一致（不一致时 _cfg 会显式报错）。"""
    import lei_signal.market_context.sentiment_signals as ss

    cfg = ss._cfg()   # 不抛异常即一致
    assert cfg["z_threshold"] == 1.5 and cfg["retail_window"] == 20
    assert cfg["z_base_window"] == 120


# ---------------- R07：环境前提与完整信号分开（scout 文案） ----------------

def test_scout_icepoint_environment_only_no_full_stats(monkeypatch):
    """scout 只检测全市场 cold：卡上不得出现四条件统计数字，只说环境前提。"""
    import lei_signal.copilot.scout as scout_mod
    import lei_signal.market_context.market_mood as mm

    monkeypatch.setattr(
        mm, "cn_mood", lambda: {"state": "cold", "state_cn": "三票冷"})
    monkeypatch.setattr(mm, "sector_heat_boards", lambda: {"boards": []})
    out = scout_mod.scout_sentiment()
    assert out and "环境前提" in out[0]["detail_cn"]
    assert "尚未逐项核实" in out[0]["detail_cn"]
    assert "12.9" not in out[0]["detail_cn"]      # 完整统计不贴环境卡
    assert "57%" not in out[0]["detail_cn"]
