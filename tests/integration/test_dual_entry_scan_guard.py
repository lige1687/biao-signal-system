"""双入口薄护栏：CLI 日扫入口 vs API 扫描入口在冻结样本上判定字段一致（J1/S2）。

契约：docs/archive/handoffs-plans/2026-09-19-arch-j1-contract.json G2。
样本与冻结预期：tests/golden/scan_entry_samples.py（复用 S1 golden 构造函数）。

两条入口各自走**真实编排路径**（非同一纯函数调两遍充数）：
- CLI：子进程 runpy 执行 scripts/daily_scan.py 的 main()——argparse、
  自选解析（_resolve_symbols 读 watchlist 表）、AnalysisService(max_workers=8)
  构造 + 串行预热、run_opportunity_scan(refresh=True, only_with_candidates=True)、
  upsert_scan_results 落库、count_opportunities、verdict 计数打印、os._exit。
- API：FastAPI TestClient 走真实 HTTP 路由——GET /api/opportunities/scan
  （routes/opportunities.scan_opportunities -> run_opportunity_scan）与
  POST /api/opportunities/today/refresh（扫描 + 落库 + _group_today 分组）。

比较口径（契约 G2：共同判定字段一致；差异三分类处置）：
- 判定字段（必须一致，不一致即停止交主控）：symbol / verdict /
  best_scenario_cn（扫描表达层承载「哪个模块的什么场景」；ScanItemDTO 与
  daily_opportunity_scan 表均无独立 module 列，此映射为既有编排事实，记录不阻塞）/
  best_state / reward_risk_ratio / reward_risk_computable / blocking_reasons /
  has_active_plan / error / missing_summary_cn（blocking-missing 语义载体）。
- 展示层差异（记录即可，不阻塞）：generated_at 每次生成、scan_date 取当日、
  verdict_cn 由同一映射派生、API 分组响应把 none 过滤为「缺席」。
- unavailable 语义：两入口同为「verdict=none + error 显式携带」，错误文案
  均来自 analyze_bars 的 MIN_BARS 生产门槛经 _classify_error 透传。
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from lei_signal.api.app import create_app
from lei_signal.api.opportunity_scan import (
    count_opportunities,
    list_scan,
    today_date,
)
from lei_signal.api.services import AnalysisService
from lei_signal.api.watchlist import upsert_watchlist
from lei_signal.storage.sqlite_store import connect
from tests.golden.scan_entry_samples import (
    ALL_SYMBOLS,
    EXPECTED_CANDIDATE,
    SYMBOL_CANDIDATE,
    SYMBOL_NO_SIGNAL,
    SYMBOL_SHORT_HISTORY,
    SYMBOL_UNAVAILABLE,
    render_cli_runner_script,
    stub_analyze,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]

#: 判定字段冻结锚点：unavailable 行（错误文案来自生产门槛，冻结关键词而非全文）
EXPECTED_UNAVAILABLE_ERROR_KEYWORDS = ("只有 10 根日K线", "21 根")


def _get(row, key: str):  # noqa: ANN001 — 兼容 ScanItemDTO / DailyScanRow / API JSON dict
    return row[key] if isinstance(row, dict) else getattr(row, key)


def _judgment_fields(row) -> dict:  # noqa: ANN001
    """两入口共同判定字段（比较用；来源字段名在 DTO / DB 行 / JSON dict 上同形）。"""
    return {
        "symbol": _get(row, "symbol"),
        "verdict": _get(row, "verdict"),
        "best_scenario_cn": _get(row, "best_scenario_cn"),
        "best_state": _get(row, "best_state"),
        "reward_risk_ratio": _get(row, "reward_risk_ratio"),
        "reward_risk_computable": bool(_get(row, "reward_risk_computable")),
        "blocking_reasons": list(_get(row, "blocking_reasons")),
        "missing_summary_cn": _get(row, "missing_summary_cn"),
        "has_active_plan": bool(_get(row, "has_active_plan")),
        "error": _get(row, "error"),
    }


def _seed_watchlist(db_path: str) -> None:
    with closing(connect(db_path)) as conn:
        for symbol in ALL_SYMBOLS:
            upsert_watchlist(conn, symbol=symbol, display_name=symbol, market="A")


def _rows_by_symbol(rows) -> dict:  # noqa: ANN001
    return {_get(r, "symbol"): r for r in rows}


# ---------------------------------------------------------------------------
# 两侧真实编排（模块级只跑一次：CLI 子进程 + API TestClient）
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def dual_entry(tmp_path_factory) -> dict:  # noqa: ANN001
    cli_dir = tmp_path_factory.mktemp("cli")
    api_dir = tmp_path_factory.mktemp("api")

    # ---- CLI 侧：真实 main() 子进程 ----
    cli_db = str(cli_dir / "lab.db")
    _seed_watchlist(cli_db)
    runner = cli_dir / "_run_daily_scan.py"
    runner.write_text(
        render_cli_runner_script(
            str(_REPO_ROOT),
            str(_REPO_ROOT / "scripts" / "daily_scan.py"),
            ["--db", cli_db],
        ),
        encoding="utf-8",
    )
    env = {
        **os.environ,
        # 配置默认路径全部重定向到 tmp，杜绝触碰 ~/.lei_signal_lab
        "LEI_SQLITE_PATH": str(cli_dir / "subproc_default.db"),
        "LEI_CACHE_ROOT": str(cli_dir / "cache"),
    }
    proc = subprocess.run(
        [sys.executable, str(runner)],
        capture_output=True,
        text=True,
        timeout=600,
        env=env,
        cwd=str(_REPO_ROOT),
        check=False,
    )
    assert proc.returncode == 0, (
        f"CLI 子进程失败 rc={proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}"
    )
    match = re.search(
        r"完成: scanned=(\d+) actionable=(\d+) waiting=(\d+) "
        r"blocked=(\d+) none=(\d+) scan_date=(\S+)",
        proc.stdout,
    )
    assert match, f"CLI 汇总行缺失：{proc.stdout!r}"
    cli_counts = {
        "scanned": int(match.group(1)),
        "actionable": int(match.group(2)),
        "waiting": int(match.group(3)),
        "blocked": int(match.group(4)),
        "none": int(match.group(5)),
    }

    # ---- API 侧：真实 HTTP 路由 ----
    api_db = str(api_dir / "lab.db")
    _seed_watchlist(api_db)
    service = AnalysisService(
        analyze_fn=stub_analyze, sqlite_path=api_db, ttl_seconds=900
    )
    app = create_app(analysis_service=service)
    app.state.plans_db_path = api_db
    app.state.watchlist_db_path = api_db
    app.state.quote_provider = None
    app.state.friendly_name_provider = False
    client = TestClient(app)
    scan_response = client.get("/api/opportunities/scan", params={"refresh": "true"})
    assert scan_response.status_code == 200, scan_response.text
    refresh_response = client.post("/api/opportunities/today/refresh")
    assert refresh_response.status_code == 200, refresh_response.text

    with closing(connect(cli_db)) as conn:
        cli_rows = _rows_by_symbol(list_scan(conn, today_date()))
        cli_opp_count = count_opportunities(conn, today_date())
    with closing(connect(api_db)) as conn:
        api_rows = _rows_by_symbol(list_scan(conn, today_date()))
        api_opp_count = count_opportunities(conn, today_date())

    return {
        "cli_counts": cli_counts,
        "cli_rows": cli_rows,
        "cli_opp_count": cli_opp_count,
        "api_items": _rows_by_symbol(scan_response.json()["items"]),
        "api_groups": refresh_response.json(),
        "api_rows": api_rows,
        "api_opp_count": api_opp_count,
    }


# ---------------------------------------------------------------------------
# G2 护栏断言
# ---------------------------------------------------------------------------


def test_cli_stdout_counts_frozen(dual_entry) -> None:  # noqa: ANN001
    """CLI 真实编排的汇总计数：4 标的中 1 waiting 候选 + 1 unavailable，其余被过滤。"""
    assert dual_entry["cli_counts"] == {
        "scanned": 4, "actionable": 0, "waiting": 1, "blocked": 0, "none": 1,
    }
    assert dual_entry["cli_opp_count"] == 1  # 今日机会 = actionable + waiting


def test_both_entries_absent_symbols_and_presence(dual_entry) -> None:  # noqa: ANN001
    """过滤语义一致：无候选两样本缺席（none+only_with_candidates），其余两样本在场。"""
    for rows in (dual_entry["cli_rows"], dual_entry["api_rows"]):
        assert SYMBOL_NO_SIGNAL not in rows
        assert SYMBOL_SHORT_HISTORY not in rows
        assert set(rows) == {SYMBOL_CANDIDATE, SYMBOL_UNAVAILABLE}
    api_items = dual_entry["api_items"]
    assert set(api_items) == {SYMBOL_CANDIDATE, SYMBOL_UNAVAILABLE}


def test_candidate_row_judgment_fields_frozen(dual_entry) -> None:  # noqa: ANN001
    """waiting 候选行的共同判定字段与冻结值一致（两入口各自落库/返回后核对）。"""
    for tag, row in (
        ("CLI", dual_entry["cli_rows"][SYMBOL_CANDIDATE]),
        ("API-scan", dual_entry["api_items"][SYMBOL_CANDIDATE]),
        ("API-refresh", dual_entry["api_rows"][SYMBOL_CANDIDATE]),
    ):
        fields = _judgment_fields(row)
        frozen = {k: fields[k] for k in EXPECTED_CANDIDATE}
        assert frozen == EXPECTED_CANDIDATE, f"{tag} 判定字段漂移: {fields}"
        # 判定依据（tests/golden/scan_entry_samples.py 样本 docstring）：
        # D 空头镜像 watch @最后一根 -> waiting；tradability 无阻断 -> blocking 空。


def test_unavailable_semantics_identical_across_entries(dual_entry) -> None:  # noqa: ANN001
    """unavailable 语义一致：verdict=none + error 显式携带生产门槛原文。"""
    for tag, row in (
        ("CLI", dual_entry["cli_rows"][SYMBOL_UNAVAILABLE]),
        ("API-scan", dual_entry["api_items"][SYMBOL_UNAVAILABLE]),
        ("API-refresh", dual_entry["api_rows"][SYMBOL_UNAVAILABLE]),
    ):
        fields = _judgment_fields(row)
        assert fields["verdict"] == "none"
        assert fields["error"], f"{tag} unavailable 行缺 error"
        for keyword in EXPECTED_UNAVAILABLE_ERROR_KEYWORDS:
            assert keyword in fields["error"], f"{tag} error 文案漂移: {fields['error']}"
        assert fields["best_scenario_cn"] is None and fields["best_state"] is None
    # 错误文案三处完全一致（同一生产门槛原文，不经文案改写）
    cli_err = _get(dual_entry["cli_rows"][SYMBOL_UNAVAILABLE], "error")
    assert _get(dual_entry["api_items"][SYMBOL_UNAVAILABLE], "error") == cli_err
    assert _get(dual_entry["api_rows"][SYMBOL_UNAVAILABLE], "error") == cli_err


def test_cross_entry_judgment_fields_equal(dual_entry) -> None:  # noqa: ANN001
    """核心护栏：CLI 落库行 vs API 扫描项 vs API 落库行，判定字段逐项相等。

    判定字段差异 -> 停止不修，交最小复现给主控（契约 G2 / 差异三分类第 3 类）。
    """
    cli_rows, api_items, api_rows = (
        dual_entry["cli_rows"], dual_entry["api_items"], dual_entry["api_rows"],
    )
    assert set(cli_rows) == set(api_items) == set(api_rows)
    for symbol in cli_rows:
        base = _judgment_fields(cli_rows[symbol])
        assert _judgment_fields(api_items[symbol]) == base, f"{symbol}: API 扫描项与 CLI 不一致"
        assert _judgment_fields(api_rows[symbol]) == base, f"{symbol}: API 落库行与 CLI 不一致"


def test_api_grouping_matches_cli_write(dual_entry) -> None:  # noqa: ANN001
    """API 分组响应（/today/refresh）与 CLI 落库行同象：waiting 组=候选标的。

    展示层差异（记录，不阻塞）：_group_today 只分组 actionable/waiting/blocked，
    unavailable 行（verdict=none）不进任何组也不进 scanned——今日面板分组视图
    看不到 unavailable，需经 /scan 或读表获取；CLI 的落库行与 stdout 计数
    （none=1）则可见。两入口判定字段本身一致（见 test_unavailable_semantics_*）。
    """
    groups = dual_entry["api_groups"]
    assert groups["scanned"] == 1  # 只数 actionable+waiting+blocked；none 不入库不入组
    assert [i["symbol"] for i in groups["waiting"]] == [SYMBOL_CANDIDATE]
    assert groups["actionable"] == [] and groups["blocked"] == []
    assert dual_entry["api_opp_count"] == 1
