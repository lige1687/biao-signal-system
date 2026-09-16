"""按需补测：持久任务绑定 + 单任务队列（03B 总控协议 §5，2026-09-08）。

- 先持久保存请求和归属（queued），再启动后台任务；run_id 创建时预留，
  重复提交/服务重启可核对。同 (session_id, client_request_id) 幂等返回原
  任务；同键不同业务内容显式冲突。
- 单标的、一套已明确的既有方法；symbols=None/空/多标的在此入口拒绝。
  内部调用现有 backtest service（execute_run），不重做引擎、不自调 HTTP。
- 配置规范化覆盖全部实际消费参数（引擎默认显式展开）；数据截止与输入
  摘要随请求保存；结果来自实际执行（含实际数据区间），不利结果也保存。
- 状态 queued/running/completed/failed/interrupted；重启后无法证明后台
  仍在运行 → interrupted，不自动无限重跑。
- 只存任务状态与归属，不算成绩、不取代观察账本。
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import sqlite3
import threading
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lei_signal.backtest import service as bt_service
from lei_signal.domain.rules_config import ruleset_version

#: 讨论补测队列首期并发 = 1（其余排队）
_SLOT = threading.Semaphore(1)
_ACTIVE: set[str] = set()
_ACTIVE_LOCK = threading.Lock()

STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_INTERRUPTED = "interrupted"

MEMBER_IDENTITY_VERSION = "v1"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _canonical(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class BacktestRequestError(ValueError):
    """请求非法（多标的/空标的/缺参数等）——API 映射 422。"""


class BacktestRequestConflict(ValueError):
    """同 client_request_id 不同业务内容——API 映射 409。"""


def build_canonical_config(
    *, symbol: str, module: str, entry_variant: str | None, exit_variant: str,
    rr_min: float | None, fee_label: str, data_cutoff: str,
) -> tuple[dict[str, Any], "bt_service.BacktestParams"]:
    """规范化配置：覆盖**全部实际消费参数**（引擎默认显式展开，不能只存
    UI 显示的几项）。返回 (canonical_dict, BacktestParams)。"""
    params = bt_service.BacktestParams(
        symbols=(symbol,),
        module=module,
        rr_min=rr_min,
        entry_variant=entry_variant,
        exit_variant=exit_variant,
        fee_label=fee_label,
        limit_guard=True,
        overrides=(),
        volume_confirm=False,
        volume_confirm_window=5,
        profile_filter="none",
        gap_target=False,
        gap_momentum=False,
        gap_momentum_lookback=10,
        volume_filter="none",
        shrink_recent=None,
        shrink_prior=None,
        volume_filter_vr_max=None,
        bias_filter=None,
        accel_filter=None,
        accel_lookback=60,
        stop_atr_buffer=None,
        min_stop_distance=None,
    )
    params.validate()
    canon = dataclasses.asdict(params)
    canon["symbols"] = list(canon["symbols"]) if canon.get("symbols") else None
    canon["overrides"] = [list(o) for o in canon.get("overrides") or []]
    canon["ruleset_version"] = ruleset_version()
    canon["data_cutoff"] = data_cutoff
    return canon, params


def create_request(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    question_id: int,
    client_request_id: str,
    symbol: str,
    module: str | None,
    entry_variant: str | None = None,
    exit_variant: str | None,
    rr_min: float | None = 3.0,
    fee_label: str = "standard",
    data_cutoff: str | None = None,
) -> dict[str, Any]:
    """创建补测请求（幂等）。同一 (session_id, client_request_id) 且业务内容
    一致 → 返回原任务；不一致 → 冲突。只落库，不启动线程（调用方拿到
    request_id/status=queued 后调用 `start_request_worker`）。

    R2（03B-R1）：模块/退出方式必须由用户明确提供（缺省不默认 A），非法
    模块/变体/费用 → BacktestRequestError（API 422，零任务写入）。
    R4：创建时冻结输入副本（快照文件）+ 实际启用规则账本（含内容摘要），
    排队期间源变更不影响本次执行依据。
    03B-R2（r12）：业务身份 = 请求编号 × 会话 × 原问题 × 对象 × 方法 × 退出；
    同编号换问题/换会话属冲突（409），不是静默复用。"""
    symbol = (symbol or "").strip()
    if not symbol:
        raise BacktestRequestError("补测需要明确一个标的（一次只跑一个标的）")
    if any(sep in symbol for sep in (",", "，", ";", " ", "/")) or symbol.lower() in ("none", "null", "all"):
        raise BacktestRequestError(
            "补测一次只跑一个标的：symbols=None/空列表/多标的在此入口一律拒绝")
    if not module:
        raise BacktestRequestError(
            "缺少交易模块：请明确 A 回调 / B 突破 / C 2B / D 假突破（不默认 A）")
    if not exit_variant:
        raise BacktestRequestError("缺少退出方式（exit_variant 不能为空）")
    data_cutoff = data_cutoff or datetime.now(UTC).date().isoformat()
    try:
        canon, params = build_canonical_config(
            symbol=symbol, module=module, entry_variant=entry_variant,
            exit_variant=exit_variant, rr_min=rr_min, fee_label=fee_label,
            data_cutoff=data_cutoff)
    except ValueError as exc:
        raise BacktestRequestError(str(exc)) from exc  # 非法模块/变体/费用 → 422
    config_hash = hashlib.sha256(_canonical(canon).encode("utf-8")).hexdigest()[:16]

    # 03B-R2：请求编号全局核对（精确字段，非模糊查询）——跨会话/换问题/换
    # 业务内容一律显式冲突；跨日或资料变化的原样重试在这里复用首次依据返回。
    row = conn.execute(
        "SELECT * FROM agent_backtest_requests WHERE client_request_id = ?",
        (client_request_id,),
    ).fetchone()
    if row is not None:
        if row["session_id"] != session_id:
            raise BacktestRequestConflict(
                "相同请求编号已归属另一会话（任务不能改挂会话），请换编号或回到原会话")
        if int(row["question_id"]) != int(question_id):
            raise BacktestRequestConflict(
                "相同请求编号已绑定原问题 "
                f"#{row['question_id']}，换问题属冲突（409）；请为新问题换请求编号")
        if row["config_hash"] != config_hash:
            raise BacktestRequestConflict(
                "相同请求编号携带不同业务内容（配置哈希不一致），请换编号或明确新任务")
        return _row_to_status(row)
    run_id = bt_service.new_run_id()
    request_id = "btr_" + uuid.uuid4().hex[:12]
    now = _now()
    # 任务创建即准备运行输出目录（结果文件、冻结快照都落在同一工作区）
    bt_service.BACKTEST_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    refs = _freeze_input_snapshot(symbol, request_id, run_id)
    conn.execute(
        """
        INSERT INTO agent_backtest_requests (
            request_id, client_request_id, session_id, question_id, symbol,
            method, entry_variant, exit_variant, canonical_config_json,
            config_hash, ruleset_version, data_cutoff, input_refs_json,
            run_id, result_ref, status, error, backfilled, created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            request_id, client_request_id, session_id, question_id, symbol,
            module, entry_variant, exit_variant, _canonical(canon),
            config_hash, canon["ruleset_version"], data_cutoff,
            _canonical(refs),
            run_id, "", STATUS_QUEUED, None, 0, now, now,
        ),
    )
    fresh = conn.execute(
        "SELECT * FROM agent_backtest_requests WHERE request_id = ?",
        (request_id,)).fetchone()
    return _row_to_status(fresh)


def _pool_root() -> Path:
    """回测池根目录（与 runner.load_pool_frames 同一来源，含环境变量注入）。"""
    import os

    return Path(os.environ.get(
        "LEI_BACKTEST_POOL_ROOT",
        str(Path.home() / ".lei_signal_lab" / "backtest_pool")))


#: 测试专用输入注入（03B-R3 S1）：**仅隔离验证环境**通过
#: ``set_test_source_frames`` 显式设置；生产入口绝不写入、也不能由任何用户
#: 请求参数开启。冻结记录会标明 ``test_injection: true``，不伪造真实来源名。
_TEST_SOURCE_FRAMES: dict[str, Any] | None = None


def set_test_source_frames(frames: dict[str, Any] | None) -> None:
    """显式测试注入接口：只允许隔离验证夹具调用（合成行情注入）。"""
    global _TEST_SOURCE_FRAMES
    _TEST_SOURCE_FRAMES = frames


def _freeze_input_snapshot(symbol: str, request_id: str, run_id: str) -> list[dict[str, Any]]:
    """R4：创建时冻结输入副本 + 内容摘要；03B-R2 契约2 + 03B-R3 S1：
    - 来源信任**复用生产 ParquetCache 的实际拒读语义**：缺 meta、损坏 meta、
      provider unknown/空/synthetic/fixture 等一律 ``read()=None`` → 冻结拒绝
      （「本地池直存」不是已获准例外，缺来源不能产出可信完成结果）；
    - 显式测试注入（仅隔离验证设置）走独立分支，冻结记录标 ``test_injection``；
    - 同时冻结**实际启用**的规则账本（完整 RuleRef：路径+版本+内容摘要+文件
      副本），执行时沿同一规则输入，规则变化即明确拒绝。"""
    import shutil

    from lei_signal.data.cache import ParquetCache

    out = [_ruleset_freeze_ref(request_id)]
    pool_root = _pool_root()
    cache = ParquetCache(pool_root)
    ref: dict[str, Any] = {"kind": "backtest_pool_parquet", "symbol": symbol,
                           "source_path": str(pool_root / f"{symbol}.bars.parquet")}
    # ① 显式测试注入（隔离验证专用；不伪造真实来源名）
    if _TEST_SOURCE_FRAMES is not None and symbol in _TEST_SOURCE_FRAMES:
        import pandas as _pd

        frozen_dir = (bt_service.BACKTEST_RUNS_DIR.parent / "input_snapshots" / request_id)
        frozen_dir.mkdir(parents=True, exist_ok=True)
        frozen = frozen_dir / f"{symbol}.parquet"
        _pd.DataFrame(_TEST_SOURCE_FRAMES[symbol]).to_parquet(frozen)
        ref.update({
            "frozen_path": str(frozen),
            "content_sha256": hashlib.sha256(frozen.read_bytes()).hexdigest(),
            "size_bytes": frozen.stat().st_size, "available": True,
            "provider": None, "test_injection": True,
            "source": "isolated_test_injection",
            "provider_note": "测试专用注入（仅隔离验证环境设置），非生产行情来源",
        })
        out.append(ref)
        return out
    # ② 生产路径：与 load_pool_frames 完全相同的信任口径（read() 内含
    #    缺 meta→None、不可信 provider→None、损坏→None 三重拒读）
    frame = cache.read(symbol, kind="bars")
    meta = cache.read_meta(symbol, kind="bars")
    provider = str((meta or {}).get("provider", "")).strip().lower()
    if frame is None:
        if meta is None:
            reason = ("数据来源标记缺失（无 meta 或已损坏）——正常补测入口"
                      "拒绝执行：缺来源不能产出可信结果（ParquetCache 拒读语义）")
        else:
            reason = (f"数据来源标记不可信（{provider or '未知'}，属 "
                      "synthetic/fixture 类非行情源）——正常补测入口拒绝执行，"
                      "不以削弱来源校验的方式放行")
        ref.update({"available": False, "provider": provider or None,
                    "reason": reason})
        out.append(ref)
        return out
    frozen_dir = (bt_service.BACKTEST_RUNS_DIR.parent / "input_snapshots" / request_id)
    frozen_dir.mkdir(parents=True, exist_ok=True)
    frozen = frozen_dir / f"{symbol}.parquet"
    shutil.copyfile(pool_root / f"{symbol}.bars.parquet", frozen)
    ref.update({
        "frozen_path": str(frozen),
        "content_sha256": hashlib.sha256(frozen.read_bytes()).hexdigest(),
        "size_bytes": frozen.stat().st_size, "available": True,
        "provider": provider, "test_injection": False,
    })
    out.append(ref)
    return out


def _ruleset_freeze_ref(request_id: str) -> dict[str, Any]:
    """冻结实际启用的规则账本：完整 RuleRef（含内容摘要）+ 文件副本。"""
    import shutil

    from lei_signal.domain import rules_config

    path = rules_config._default_config_path()
    ref: dict[str, Any] = {"kind": "ruleset_yaml", "config_path": str(path),
                           "rule_id": "__ruleset__"}
    try:
        ref["ruleset_version"] = rules_config.ruleset_version()
    except Exception:  # noqa: BLE001
        ref["ruleset_version"] = "unavailable"
    if not path.exists():
        ref.update({"available": False, "content_sha256": None,
                    "reason": "规则账本文件缺失"})
        return ref
    frozen_dir = (bt_service.BACKTEST_RUNS_DIR.parent / "input_snapshots" / request_id)
    frozen_dir.mkdir(parents=True, exist_ok=True)
    frozen = frozen_dir / Path(path).name
    shutil.copyfile(path, frozen)
    ref.update({"frozen_path": str(frozen),
                "content_sha256": hashlib.sha256(frozen.read_bytes()).hexdigest(),
                "available": True})
    return ref


def _frozen_ruleset_ref(refs: list[dict[str, Any]]) -> dict[str, Any] | None:
    for r in refs or []:
        if isinstance(r, dict) and r.get("kind") == "ruleset_yaml":
            return r
    return None


def _frozen_data_ref(refs: list[dict[str, Any]]) -> dict[str, Any] | None:
    for r in refs or []:
        if isinstance(r, dict) and r.get("kind") == "backtest_pool_parquet":
            return r
    return None


def _row_to_status(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "request_id": row["request_id"],
        "client_request_id": row["client_request_id"],
        "session_id": row["session_id"],
        "question_id": row["question_id"],
        "symbol": row["symbol"],
        "method": row["method"],
        "entry_variant": row["entry_variant"],
        "exit_variant": row["exit_variant"],
        "status": row["status"],
        "run_id": row["run_id"],
        "error": row["error"],
        "result_ref": row["result_ref"] or None,
        "backfilled": bool(row["backfilled"]),
        "config": json.loads(row["canonical_config_json"] or "{}"),
        "config_hash": row["config_hash"],
        "data_cutoff": row["data_cutoff"],
        "input_refs": json.loads(row["input_refs_json"] or "[]"),
        "run_manifest": (json.loads(row["run_manifest_json"])
                         if row["run_manifest_json"] else None),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_request(conn: sqlite3.Connection, request_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM agent_backtest_requests WHERE request_id = ?",
        (request_id,)).fetchone()
    if row is None:
        return None
    _mark_interrupted_if_stale(conn, row)
    # 03B-R2 契约4（r10）：输出文件已写完但状态停在 running/interrupted
    # （进程在 completed 更新前退出）→ 按预留 run_id 校验产物并恢复，
    # 不只覆盖「已 completed 未回填」。
    _recover_output_if_crashed(conn, request_id)
    # R5 崩溃恢复：completed 且未回填 → 从结果文件重建完成卡（最多一条）
    _recover_backfill_if_needed(conn, request_id)
    # 核查后重新读取——首次 GET 就返回核查后的状态
    fresh = conn.execute(
        "SELECT * FROM agent_backtest_requests WHERE request_id = ?",
        (request_id,)).fetchone()
    return _row_to_status(fresh)


def list_requests(conn: sqlite3.Connection, session_id: str,
                  limit: int = 20) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM agent_backtest_requests WHERE session_id = ? "
        "ORDER BY created_at DESC LIMIT ?", (session_id, limit)).fetchall()
    out = []
    for row in rows:
        _mark_interrupted_if_stale(conn, row)
    # R5：标记后再统一读取（孤儿 queued/running 均不留在列表里）
    for row in conn.execute(
        "SELECT * FROM agent_backtest_requests WHERE session_id = ? "
        "ORDER BY created_at DESC LIMIT ?", (session_id, limit)).fetchall():
        out.append(_row_to_status(row))
    return out


def list_requests_any(conn: sqlite3.Connection, limit: int = 50) -> list[dict[str, Any]]:
    """跨会话最近任务（03B-R2 契约4：页面恢复以服务端列表为权威）。"""
    rows = conn.execute(
        "SELECT * FROM agent_backtest_requests "
        "ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    for row in rows:
        _mark_interrupted_if_stale(conn, row)
    rows = conn.execute(
        "SELECT * FROM agent_backtest_requests "
        "ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [_row_to_status(row) for row in rows]


def _mark_interrupted_if_stale(conn: sqlite3.Connection, row: sqlite3.Row) -> None:
    """R5：进程内无活跃工作者（重启/线程死亡）→ running 与 queued 孤儿均标
    interrupted（可恢复语义：有完整输出则可读，无则明示中断），不无限假排队。"""
    if row["status"] in (STATUS_RUNNING, STATUS_QUEUED) \
            and row["request_id"] not in _ACTIVE:
        conn.execute(
            "UPDATE agent_backtest_requests SET status = ?, "
            "error = COALESCE(error, '服务重启后无法确认后台任务状态'), updated_at = ? "
            "WHERE request_id = ? AND status IN (?, ?)",
            (STATUS_INTERRUPTED, _now(), row["request_id"],
             STATUS_RUNNING, STATUS_QUEUED))
        conn.commit()


def _claim_queued(db_path: str, request_id: str) -> bool:
    """R5：数据库**原子领取**→running——只有成功领取者运行；同一请求重试/
    并发提交/已完成均不重复执行。03B-R2：兼容从 interrupted 领回——POST 提交
    与进程内存活登记之间，并发状态查询可能先把新任务标成 interrupted
    （查询与领取窗口不得互相破坏）；本函数只被本进程存活 worker 调用。"""
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            "UPDATE agent_backtest_requests SET status = ?, updated_at = ? "
            "WHERE request_id = ? AND status IN (?, ?)",
            (STATUS_RUNNING, _now(), request_id, STATUS_QUEUED, STATUS_INTERRUPTED))
        conn.commit()
        return cur.rowcount == 1
    finally:
        conn.close()


def start_request_worker(db_path: str, request_id: str) -> bool:
    """登记存活并启动后台 worker；queued→running 的原子领取移到**槽内**执行
    （03B-R2 契约4：只有真正开始计算才算 running，排队中保持 queued；
    _ACTIVE 覆盖「排队等待+执行中」全程，查询不会把本进程活任务误标中断）。"""
    with _ACTIVE_LOCK:
        if request_id in _ACTIVE:
            return False
        _ACTIVE.add(request_id)
    t = threading.Thread(target=_worker, args=(db_path, request_id), daemon=True)
    t.start()
    return True


def _set_status(db_path: str, request_id: str, status: str, *,
                error: str | None = None, result_ref: str | None = None) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "UPDATE agent_backtest_requests SET status = ?, "
            "error = ?, result_ref = CASE WHEN ? <> '' THEN ? ELSE result_ref END, "
            "updated_at = ? WHERE request_id = ?",
            (status, error, result_ref or "", result_ref or "", _now(), request_id),
        )
        conn.commit()
    finally:
        conn.close()


def _worker(db_path: str, request_id: str) -> None:
    try:
        with _SLOT:  # 首期同时运行 1 个任务，其余排队（排队中保持 queued）
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row  # worker 内按列名取值
            row = conn.execute(
                "SELECT * FROM agent_backtest_requests WHERE request_id = ?",
                (request_id,)).fetchone()
            if row is None:
                conn.close()
                return
            # 03B-R2：领取在槽内——queued→running 原子领取，只有实际执行
            # 才显示 running；领取失败（已被处理）不运行。
            if not _claim_queued(db_path, request_id):
                conn.close()
                return
            config = json.loads(row["canonical_config_json"])
            canon_symbols = config.get("symbols") or []
            params = bt_service.BacktestParams(
                symbols=tuple(canon_symbols) if canon_symbols else None,
                module=config.get("module", "A"),
                rr_min=config.get("rr_min", 3.0),
                entry_variant=config.get("entry_variant"),
                exit_variant=config.get("exit_variant", "a6_1_costbasis"),
                fee_label=config.get("fee_label", "standard"),
                limit_guard=config.get("limit_guard", True),
                volume_confirm=config.get("volume_confirm", False),
                volume_confirm_window=config.get("volume_confirm_window", 5),
                profile_filter=config.get("profile_filter", "none"),
                volume_filter=config.get("volume_filter", "none"),
                gap_target=config.get("gap_target", False),
                gap_momentum=config.get("gap_momentum", False),
                gap_momentum_lookback=config.get("gap_momentum_lookback", 10),
                accel_filter=config.get("accel_filter"),
                accel_lookback=config.get("accel_lookback", 60),
                stop_atr_buffer=config.get("stop_atr_buffer"),
                min_stop_distance=config.get("min_stop_distance"),
                bias_filter=config.get("bias_filter"),
            )
            run_id = row["run_id"]
            # R4：从**冻结副本**读入（排队期间源变更不冒充原输入），截止先
            # 作用到原始行情，再用与生产加载器相同的函数链计算特征。
            # 03B-R2 契约2：副本完整性核对（损坏/不符明确失败）；规则账本
            # 内容核对（创建后被改动 → 拒绝本次执行，不沿用未声明的规则）。
            refs = json.loads(row["input_refs_json"] or "[]")
            data_ref = _frozen_data_ref(refs)
            rules_ref = _frozen_ruleset_ref(refs)
            frozen_path = (data_ref or {}).get("frozen_path")
            data_cutoff = row["data_cutoff"]
            symbol = row["symbol"]
            import pandas as pd

            from lei_signal.backtest import runner as bt_runner

            def _fail(reason: str) -> None:
                conn.execute(
                    "UPDATE agent_backtest_requests SET status = ?, error = ?, "
                    "updated_at = ? WHERE request_id = ?",
                    (STATUS_FAILED, reason, _now(), request_id))
                conn.commit()
                conn.close()

            if rules_ref is not None and rules_ref.get("available"):
                from lei_signal.domain.rules_config import _default_config_path

                active_hash = None
                try:
                    active_hash = hashlib.sha256(
                        _default_config_path().read_bytes()).hexdigest()
                except OSError:
                    active_hash = None
                if active_hash != rules_ref.get("content_sha256"):
                    _fail(
                        "规则账本内容在任务创建后发生了变化（冻结依据 "
                        f"{str(rules_ref.get('content_sha256'))[:12]}…，当前 "
                        f"{str(active_hash)[:12]}…）——本次执行拒绝，"
                        "请以当前规则重新发起补测（不沿用未声明的规则）")
                    return
            if not frozen_path or not Path(frozen_path).exists():
                _fail((data_ref or {}).get("reason")
                      or "缺所需历史资料（无冻结输入副本）")
                return
            copy_hash = hashlib.sha256(Path(frozen_path).read_bytes()).hexdigest()
            if copy_hash != (data_ref or {}).get("content_sha256"):
                _fail(
                    "冻结输入副本损坏或与创建时不符（内容摘要不一致）——"
                    "不冒充原输入执行，请重新发起补测")
                return
            raw = pd.read_parquet(frozen_path)
            raw.index = pd.to_datetime(raw.index)
            raw = raw.loc[raw.index <= pd.Timestamp(data_cutoff)]  # 截止裁剪原始行情
            if raw.empty:
                conn.execute(
                    "UPDATE agent_backtest_requests SET status = ?, error = ?, "
                    "updated_at = ? WHERE request_id = ?",
                    (STATUS_FAILED,
                     "数据截止早于全部行情：无可用输入（不伪造 K 线）",
                     _now(), request_id))
                conn.commit()
                conn.close()
                return
            if not {"open", "high", "low", "close", "volume"} <= {
                    c.lower() for c in raw.columns}:
                conn.execute(
                    "UPDATE agent_backtest_requests SET status = ?, error = ?, "
                    "updated_at = ? WHERE request_id = ?",
                    (STATUS_FAILED,
                     "缺完整开高低收/成交量：无法按引擎要求计算（不伪造）",
                     _now(), request_id))
                conn.commit()
                conn.close()
                return
            # 与生产加载器同一特征计算链（真实路径，非替身）
            frame = bt_runner.classify_colors(bt_runner.compute_features(raw))
            frames = {symbol: frame}
            # 03B-R3 S3：可核对的**运行清单**——请求/运行/对象集合/完整配置
            # 摘要/冻结原始输入摘要（Parquet 字节）/截止后引擎实际输入摘要
            # （特征表，与原始摘要分开不算混比）/规则摘要。
            engine_digest = bt_service._frame_content_digest(frame)
            manifest = {
                "request_id": request_id,
                "run_id": run_id,
                "symbols": [symbol],
                "config_sha256": row["config_hash"],
                "raw_input_sha256": (data_ref or {}).get("content_sha256"),
                "engine_input_sha256": engine_digest,
                "data_fingerprint": hashlib.sha256(
                    f"{symbol}:{engine_digest}".encode("utf-8")).hexdigest()[:16],
                "ruleset_sha256": (rules_ref or {}).get("content_sha256"),
                "data_cutoff": data_cutoff,
            }
            try:
                result = bt_service.execute_run(params, frames=frames)
                result["run_id"] = run_id
                # 引擎返回的数据指纹必须与本清单一致（同一输入的自证）
                if str(result.get("params", {}).get("data_fingerprint", "")) \
                        != manifest["data_fingerprint"]:
                    raise ValueError(
                        "引擎数据指纹与运行清单不一致（输入核对失败，不冒充完成）")
                result["run_manifest"] = manifest
                run_dir = bt_service.BACKTEST_RUNS_DIR
                run_dir.mkdir(parents=True, exist_ok=True)
                result_path = run_dir / f"{run_id}.json"
                # 03B-R2 契约4：临时文件 + 原子替换；写后回读核验（对象/运行
                # 一致）才标 completed——损坏/不完整结果不冒充完成。
                tmp_path = run_dir / f".{run_id}.tmp"
                tmp_path.write_text(
                    json.dumps(result, ensure_ascii=False, allow_nan=False),
                    encoding="utf-8")
                os.replace(tmp_path, result_path)
                reread = json.loads(result_path.read_text(encoding="utf-8"))
                if reread.get("run_id") != run_id or reread.get("status") != "done":
                    raise ValueError("结果文件回读核验失败（运行标识/状态不符）")
                # 03B-R3 T2：正常完成路径也消费同一完整核验——产物与请求依据
                # 不符（如受控的异常费用/区间）不得标 completed（保持失败可重试，
                # 不冒充完成）；与异常恢复、后续证据读取共用一个验证结论。
                refs = json.loads(row["input_refs_json"] or "[]")
                _reject = _validate_output_for_request(row, result, refs)
                if _reject is not None:
                    raise ValueError(f"运行输出与请求依据不符，未采纳：{_reject}")
                conn.execute(
                    "UPDATE agent_backtest_requests SET status = ?, result_ref = ?, "
                    "run_manifest_json = ?, updated_at = ? WHERE request_id = ?",
                    (STATUS_COMPLETED, str(result_path),
                     json.dumps(manifest, ensure_ascii=False), _now(), request_id))
                conn.commit()
                _backfill(db_path, conn, row, result)
            except Exception as exc:  # noqa: BLE001 后台失败可见、可重试
                conn.execute(
                    "UPDATE agent_backtest_requests SET status = ?, error = ?, "
                    "updated_at = ? WHERE request_id = ?",
                    (STATUS_FAILED, str(exc), _now(), request_id))
                conn.commit()
            finally:
                conn.close()
    finally:
        with _ACTIVE_LOCK:
            _ACTIVE.discard(request_id)


def _result_summary(result: dict[str, Any]) -> str:
    """确定性完成卡文案（零 LLM）：零交易=没有可统计交易、胜率未知。"""
    overview = {}
    try:
        overview = result["groups"]["True"]["总览"][0]
    except (KeyError, TypeError, IndexError, ValueError):
        overview = {}
    trade_count = overview.get("trade_count")
    if not trade_count:
        return "没有可统计交易（零交易）：胜率为未知，不是 0% 或 100%。"
    return f"交易笔数 {trade_count}；各分组与逐笔明细见回测详情。"


def _completion_card(row, result: dict[str, Any]) -> tuple[str, dict]:
    """确定性完成卡文案 + meta（崩溃恢复与正常回填共用同一内容）。"""
    data_range = result.get("data_range") or {}
    text = (
        f"【补测完成】{row['symbol']} · 模块{row['method']}"
        f" · 退出方式 {row['exit_variant']}\n"
        f"请求 {row['request_id']} · 运行 {row['run_id']}"
        f" · 数据截止 {row['data_cutoff']}"
        f" · 实际数据区间 {data_range.get('start')} ~ {data_range.get('end')}\n"
        f"{_result_summary(result)}\n"
        f"（该结果只回答当初那一次提问；换方法/换退出请另起补测）")
    meta = {
        "kind": "backtest_result",
        "request_id": row["request_id"],
        "run_id": row["run_id"],
        "question_id": row["question_id"],
        "symbol": row["symbol"],
        "system_generated": True,
        "actual_data_range": data_range,
        "result_ref": row["result_ref"] or "",
    }
    return text, meta


def _insert_backfill(conn: sqlite3.Connection, row, text: str,
                     meta: dict) -> None:
    """03B-R2 契约4（r11）：写事务内**两重领取**——backfilled 0→1 原子更新 +
    ``agent_backtest_backfills.request_id`` 主键唯一约束（同一补测请求全生命
    周期最多一条完成卡：并发 GET/worker 恢复、甚至标志位被重置，都不会插入
    第二张卡）。不是「先无条件插消息、最后 UPDATE 加 WHERE」。"""
    now = _now()
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            "INSERT INTO agent_backtest_backfills (request_id, message_id, "
            "created_at) VALUES (?,?,?)", (row["request_id"], 0, now))
        cur = conn.execute(
            "INSERT INTO agent_messages (session_id, role, content, grounded, "
            "meta_json, created_at, question_id, message_kind, source_request_id) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (row["session_id"], "assistant", text, 1,
             json.dumps(meta, ensure_ascii=False), now,
             None, "backtest_result", row["request_id"]))
        conn.execute(
            "UPDATE agent_backtest_backfills SET message_id = ? "
            "WHERE request_id = ?", (int(cur.lastrowid or 0), row["request_id"]))
        conn.execute(
            "UPDATE agent_sessions SET last_active_at = ? WHERE session_id = ?",
            (now, row["session_id"]))
        conn.execute(
            "UPDATE agent_backtest_requests SET backfilled = 1, updated_at = ? "
            "WHERE request_id = ?", (now, row["request_id"]))
        conn.commit()
    except sqlite3.IntegrityError:
        # 已有回填登记（卡早已存在，如恢复时标志位被重置）：不重复插卡，
        # 只把标志位补齐为已回填
        conn.rollback()
        conn.execute(
            "UPDATE agent_backtest_requests SET backfilled = 1, updated_at = ? "
            "WHERE request_id = ? AND backfilled = 0", (now, row["request_id"]))
        conn.commit()
    except Exception:  # noqa: BLE001
        conn.rollback()
        raise


def _expected_manifest_from_frozen(row: sqlite3.Row) -> dict[str, Any] | None:
    """从冻结依据**重建**期望运行清单（03B-R3 S3）：只做确定性特征计算以
    生成输入摘要，不重跑回测引擎。冻结副本损坏/规则已变 → None（拒绝采纳）。"""
    import pandas as pd

    from lei_signal.backtest import runner as bt_runner

    try:
        refs = json.loads(row["input_refs_json"] or "[]")
    except ValueError:
        return None
    data_ref = _frozen_data_ref(refs)
    rules_ref = _frozen_ruleset_ref(refs)
    frozen_path = (data_ref or {}).get("frozen_path")
    if not data_ref or not data_ref.get("available") or not frozen_path \
            or not Path(frozen_path).exists():
        return None
    if hashlib.sha256(Path(frozen_path).read_bytes()).hexdigest() \
            != data_ref.get("content_sha256"):
        return None  # 冻结副本损坏：无法证明输入
    rules_sha = (rules_ref or {}).get("content_sha256")
    if rules_ref and rules_ref.get("available"):
        from lei_signal.domain.rules_config import _default_config_path

        try:
            if hashlib.sha256(
                    _default_config_path().read_bytes()).hexdigest() != rules_sha:
                return None  # 规则已在创建后变化
        except OSError:
            return None
    raw = pd.read_parquet(frozen_path)
    raw.index = pd.to_datetime(raw.index)
    cutoff = row["data_cutoff"]
    if cutoff:
        raw = raw.loc[raw.index <= pd.Timestamp(cutoff)]
    if raw.empty:
        return None
    engine_digest = bt_service._frame_content_digest(
        bt_runner.classify_colors(bt_runner.compute_features(raw)))
    return {
        "request_id": row["request_id"],
        "run_id": row["run_id"],
        "symbols": [row["symbol"]],
        "config_sha256": row["config_hash"],
        "raw_input_sha256": data_ref.get("content_sha256"),
        "engine_input_sha256": engine_digest,
        "data_fingerprint": hashlib.sha256(
            f"{row['symbol']}:{engine_digest}".encode("utf-8")).hexdigest()[:16],
        "ruleset_sha256": rules_sha,
        "data_cutoff": cutoff,
        # 03B-R3 T2：期望数据区间（冻结行情经 cutoff 截断后的首个/末个交易日，
        # 与引擎 execute_run 的 first_date/last_date 同一来源）——供结果区间核对
        "data_range": {
            "start": raw.index.min().date().isoformat() if len(raw) else None,
            "end": raw.index.max().date().isoformat() if len(raw) else None,
        },
    }


#: 明确**不属于计算配置**的字段（T2）：只描述数据口径与账本标识，单独核对，
#: 不参与「实际生效参数」的逐项比较。其余规范化配置字段一律逐项比对。
_NON_COMPUTED_CONFIG_FIELDS = frozenset({"data_cutoff", "ruleset_version"})


def _validate_output_for_request(row: sqlite3.Row, result: dict[str, Any],
                                 refs: list[dict[str, Any]]) -> str | None:
    """03B-R2 契约4 + 03B-R3 S3：恢复前核对产物与请求依据——运行清单逐项
    一致 + 完整配置字段一致才采纳；返回 None=可采纳，否则给出拒绝原因
    （不冒充完成；不重跑引擎掩盖错配）。"""
    if not isinstance(result, dict):
        return "输出不是 JSON 对象"
    if result.get("run_id") != row["run_id"]:
        return (f"输出 run_id {result.get('run_id')!r} 与预留 "
                f"{row['run_id']!r} 不符")
    if result.get("status") != "done":
        return f"输出状态为 {result.get('status')!r}，不是完成态"
    # 冻结依据（一次计算，供清单/指纹/规则/实际区间核对共用；只读不重跑引擎）
    expected = _expected_manifest_from_frozen(row)
    if expected is None:
        return ("冻结依据不可用或已变化（副本损坏/规则更新），无法证明该输出"
                "属于本次请求")
    params = result.get("params")
    if not isinstance(params, dict):
        # 结构错误（非对象：字符串/列表/数字等）转结构化拒绝，不抛到外层导致
        # 整张证据卡消失（边界 u4）；坏记录逐条隔离，正常运行与当前事实保留。
        return ("输出参数（params）结构错误：应为对象，实际为 "
                f"{type(params).__name__}，无法核对实际参数")
    # ① 准确的**对象集合**（不是"包含"）：多跑/少跑标的都不算本次请求的产物
    # 先校验 symbols 为合法标的列表类型（d3）：非 list/tuple/set（如数值、字符串）
    # 直接结构化拒绝，不在遍历时抛异常导致整张 evidence_card 消失；坏记录逐条
    # 隔离，正常记录与当前事实保留。共享类型检查，不特判某数值。
    raw_symbols = params.get("symbols")
    if not isinstance(raw_symbols, (list, tuple, set)):
        return (f"输出对象集合（symbols）结构错误：应为标的列表，实际为 "
                f"{type(raw_symbols).__name__}，无法核对对象集合")
    got_symbols = sorted(str(s) for s in raw_symbols)
    want_symbols = sorted({str(row["symbol"])})
    if got_symbols != want_symbols:
        return (f"输出对象集合 {got_symbols} 与本次请求的对象 "
                f"{want_symbols} 不一致（不是同一次运行）")
    # 运行清单核对（S3）：结果写入的清单必须与请求依据重建的清单逐项一致
    out_manifest = result.get("run_manifest")
    if out_manifest is None:
        return "输出缺运行清单（run_manifest），无法核对实际输入与配置"
    # 结构错误（非对象：字符串/列表/数字等）转结构化拒绝，不抛到外层导致
    # 整张证据卡消失（边界 v2）；坏记录逐条隔离，正常运行与当前事实保留。
    if not isinstance(out_manifest, dict):
        return (f"输出运行清单（run_manifest）结构错误：应为对象，"
                f"实际为 {type(out_manifest).__name__}，无法核对实际输入与配置")
    # data_range 是结果实际区间（不属运行清单），单独在④核对，不进清单比对
    diffs = [k for k in expected
             if k != "data_range" and str(out_manifest.get(k)) != str(expected.get(k))]
    if diffs:
        return ("运行清单与请求依据不符（字段："
                f"{','.join(diffs)}；输出可能是另一次运行或被篡改的产物）")
    # ② 实际结果的**完整生效参数**与原完整配置逐项比（T2：不是只比三项）
    #    规范化后比对；data_cutoff/ruleset_version 属数据口径与账本标识，
    #    单独核对，不混进计算参数集合。
    canon_raw = row["canonical_config_json"] if "canonical_config_json" \
        in row.keys() else ""
    if not canon_raw:
        return "请求缺少完整配置记录（canonical_config_json），无法核对实际参数"
    try:
        canon = json.loads(canon_raw)
    except (TypeError, ValueError):
        return "请求的完整配置记录无法解析，无法核对实际参数"
    # ② 实际结果的**完整生效参数**与原完整配置逐项比（T2：先存在、再类型、
    # 再值；逐字段类型契约，不再对所有字段做 None/空容器→同一字符串的合并）。
    # 必需字段存在性优先于值比较：缺字段不能凭 dict.get/默认值补成已验证（v1）。
    # 仅 overrides 这类引擎明确等价表示允许 None↔空列表；数值可选字段
    # （stop_atr_buffer）拒绝空列表/空对象/空字符串；其余字段原值直接比对，
    # 禁止靠 str() 隐藏类型差异。
    # 类型契约（T2）：先存在（上方已查），再类型，最后值；禁止靠 str() 隐藏
    # 类型差异（z2）。字符串 "None" ≠ null、字符串 "False" ≠ 布尔 false、
    # 字符串 "3.0" ≠ 数值 3.0。仅 overrides 允许 None↔空容器等价；stop_atr_buffer
    # 为数值可选，None 合法、空容器/空串不合法。
    _NUMERIC_OPTIONAL = {"stop_atr_buffer"}
    _LIST_NONE_EQ = {"overrides"}
    param_diffs = []

    def _type_eq(a, b) -> bool:
        # 布尔：必须都是 bool **且值（True/False）完全一致**——不止比类型
        # （d1）。例：gap_momentum 从 false 翻到 true 必须判不符；字符串
        # "False" 不属于 bool 自然被拒；bool 与 int（True vs 1）也不同型被拒。
        a_is_bool = isinstance(a, bool)
        b_is_bool = isinstance(b, bool)
        if a_is_bool or b_is_bool:
            return a_is_bool and b_is_bool and a == b
        # 数值（int/float）按值比较（bool 已在上方排除）
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return float(a) == float(b)
        # 其余：同型且相等
        return type(a) is type(b) and a == b

    for k in canon:
        if k in _NON_COMPUTED_CONFIG_FIELDS:
            continue
        if k not in params:
            param_diffs.append(f"{k}(缺失)")
            continue
        v = params[k]
        cv = canon[k]
        if k in _LIST_NONE_EQ:
            # 仅 overrides：None 与空列表/元组/集合等价（引擎等价表示）
            _nv = "" if (v is None or (isinstance(v, (list, tuple, set)) and len(v) == 0)) else v
            _nc = "" if (cv is None or (isinstance(cv, (list, tuple, set)) and len(cv) == 0)) else cv
            if _nv != _nc:
                param_diffs.append(k)
            continue
        # null 处理：空值必须显式等于请求冻结值，不能凭类型伪装放行（z2）
        if v is None or cv is None:
            if v is not None or cv is not None:
                param_diffs.append(f"{k}(空值类型不符)")
            continue
        # stop_atr_buffer：数值可选，空容器/空串无效（仍按类型核对值）
        if k in _NUMERIC_OPTIONAL:
            if isinstance(v, (list, tuple, dict, set)) and len(v) == 0:
                param_diffs.append(f"{k}(空容器无效)")
                continue
            if isinstance(v, str) and v.strip() == "":
                param_diffs.append(f"{k}(空字符串无效)")
                continue
        # 类型契约：先类型、再值（禁止 str() 隐藏差异）
        if not _type_eq(v, cv):
            param_diffs.append(f"{k}(类型不符)")
            continue
    if param_diffs:
        shown = ",".join(sorted(param_diffs)[:8])
        return (f"输出的实际生效参数与本次请求的完整配置不符（字段：{shown}；"
                "不采纳为本次结果）")
    # ③ 输入指纹与规则摘要：必须与冻结依据的**实际值**一致（不只非空）
    if str(params.get("data_fingerprint") or "") != \
            str(expected.get("data_fingerprint") or ""):
        return ("输出的数据内容指纹与冻结依据不符（实际输入不是本次请求的数据）")
    if str(params.get("ruleset_sha256") or "") != \
            str(expected.get("ruleset_sha256") or ""):
        return "输出的规则内容摘要与本次请求冻结的规则账本不符"
    # ④ 结果数据区间：必须有完整有效起止，且与冻结输入及引擎定义对应的
    # 覆盖范围一致（不只检查 end<=cutoff）。合法末日=实际行情末日，不填充
    # 行情、不改成请求截止。
    expected_range = expected.get("data_range") or {}
    actual_range = result.get("data_range")
    if not isinstance(actual_range, dict):
        # 结构错误（非对象）转结构化拒绝，坏记录逐条隔离，整卡不丢（u4）
        return ("结果数据区间（data_range）结构错误：应为对象，实际为 "
                f"{type(actual_range).__name__}，无法核对实际区间")
    exp_s, exp_e = expected_range.get("start"), expected_range.get("end")
    act_s, act_e = actual_range.get("start"), actual_range.get("end")
    if not (act_s and act_e and exp_s and exp_e):
        return "结果数据区间不完整（缺起止），不采纳"
    if str(act_s) != str(exp_s) or str(act_e) != str(exp_e):
        return (f"结果数据区间 {act_s}~{act_e} 与冻结输入期望 "
                f"{exp_s}~{exp_e} 不一致（区间不符，不采纳）")
    return None


def _recover_output_if_crashed(conn: sqlite3.Connection, request_id: str) -> None:
    """03B-R2 契约4（r10）：引擎输出已落盘、但状态停在 running/interrupted
    （进程在 completed 更新前退出）→ 按预留 run_id 读取并校验产物（对象/
    运行/配置/规则），通过则恢复为 completed 并回填完成卡；不重跑引擎。
    校验不过 → 保持 interrupted 并记录拒绝原因，不冒充完成。"""
    row = conn.execute(
        "SELECT * FROM agent_backtest_requests WHERE request_id = ?",
        (request_id,)).fetchone()
    if row is None or row["status"] not in (STATUS_RUNNING, STATUS_INTERRUPTED):
        return
    if row["request_id"] in _ACTIVE:
        return  # 本进程仍有工作者：查询不与领取窗口互相破坏
    if not row["run_id"]:
        return
    output = bt_service.BACKTEST_RUNS_DIR / f"{row['run_id']}.json"
    if not output.exists():
        return
    try:
        result = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return  # 损坏/不完整文件：不采纳（原子写保证正常产物完整）
    try:
        refs = json.loads(row["input_refs_json"] or "[]")
    except (ValueError, TypeError):
        refs = None
    if not isinstance(refs, list):
        refs = None
    reject = _validate_output_for_request(row, result, refs)
    if reject is not None:
        conn.execute(
            "UPDATE agent_backtest_requests SET error = COALESCE(error, ?), "
            "updated_at = ? WHERE request_id = ? AND status IN (?, ?)",
            (f"检测到运行输出但与请求依据不符，未采纳：{reject}", _now(),
             request_id, STATUS_RUNNING, STATUS_INTERRUPTED))
        conn.commit()
        return
    # T2：恢复成功时**持久保存已核实清单**——否则后续证据读取会把来源当未知
    # 或误判为完全适用（写一次，后续读取与写入完成走同一验证结果）
    cur = conn.execute(
        "UPDATE agent_backtest_requests SET status = ?, result_ref = ?, "
        "run_manifest_json = ?, updated_at = ? "
        "WHERE request_id = ? AND status IN (?, ?)",
        (STATUS_COMPLETED, str(output),
         json.dumps(result.get("run_manifest") or {}), _now(), request_id,
         STATUS_RUNNING, STATUS_INTERRUPTED))
    conn.commit()
    if cur.rowcount != 1:
        return
    _recover_backfill_if_needed(conn, request_id)


def _recover_backfill_if_needed(conn: sqlite3.Connection, request_id: str) -> None:
    """R5 崩溃恢复：引擎结果已写盘、状态 completed、但完成卡未回填
    （崩溃发生在回填前）→ 从结果文件重建完成卡（最多一条）。不重跑引擎。"""
    row = conn.execute(
        "SELECT * FROM agent_backtest_requests WHERE request_id = ?",
        (request_id,)).fetchone()
    if row is None or row["status"] != STATUS_COMPLETED or row["backfilled"]:
        return
    if not row["result_ref"] or not Path(row["result_ref"]).exists():
        return
    try:
        result = json.loads(Path(row["result_ref"]).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    text, meta = _completion_card(row, result)
    _insert_backfill(conn, row, text, meta)


def _backfill(db_path: str, conn: sqlite3.Connection, row: sqlite3.Row,
              result: dict[str, Any]) -> None:
    """完成后以 system-generated assistant 消息回填**原 question_id 和原
    标的**；重复查询只回填一次。切换标的不得拼接旧结果。"""
    if row["backfilled"]:
        return
    text, meta = _completion_card(row, result)
    _insert_backfill(conn, row, text, meta)


def _recover_backfill_if_needed(conn: sqlite3.Connection, request_id: str) -> None:
    """R5 崩溃恢复：引擎结果已写盘、状态 completed、但完成卡未回填
    （崩溃发生在回填前）→ 从结果文件重建完成卡（最多一条）。不重跑引擎。"""
    row = conn.execute(
        "SELECT * FROM agent_backtest_requests WHERE request_id = ?",
        (request_id,)).fetchone()
    if row is None or row["status"] != STATUS_COMPLETED or row["backfilled"]:
        return
    if not row["result_ref"] or not Path(row["result_ref"]).exists():
        return
    try:
        result = json.loads(Path(row["result_ref"]).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    text, meta = _completion_card(row, result)
    _insert_backfill(conn, row, text, meta)


__all__ = [
    "BacktestRequestError", "BacktestRequestConflict",
    "create_request", "get_request", "list_requests", "list_requests_any",
    "start_request_worker",
    "build_canonical_config", "STATUS_QUEUED", "STATUS_RUNNING",
    "STATUS_COMPLETED", "STATUS_FAILED", "STATUS_INTERRUPTED",
]
