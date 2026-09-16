"""研究坐标与时间/目标合同校验（factor_unit，四项限定修复版）。

R1/R3 落地：证据结构化{path,sha256}并逐产品对照来源裁定；必需代码键与必需
规范集合为本模块常量，合同不可裁剪；日历用 TradingCalendar/逐日 schedule 做
内容级核验（声明范围不替代实际days）；数据被篡改属身份错误（ValueError）。
纯函数不声称能自动识别数据出处；真实价资格必须绑定可回查供应商材料，
本轮缺材料继续 restricted，不编造材料造正例。

四项修复（主控限定复核2026-09-15）：
- 「能追到供应商调整价生成过程」≠「已核含分红财富构造」：
  snapshot_provenance_bound / price_basis_verified 都不能满足
  total_return_wealth；本轮真实目标没有经过主控确认的资料，一律
  target=blocked 并注明 manual_target_review_required；来源检查完成只
  入 notes，不称「含分红目标资格齐备」。本轮不实现自行批准真实目标的开关。
- 被消费的 vendor_response_ref 必须结构化 {path,sha256}、文件存在、指纹
  一致，且记录绑定同产品/输入哈希/请求参数/价格语义；空字符串、假路径、
  错产品/输入、冲突重复记录全部拒绝（不只检查 vendor_traceable 布尔）。
- 证据记录与来源裁定CSV每symbol唯一（重复冲突拒绝，不选首条/末条）；
  CSV必须给完整sha256精确相等，sha256_16前缀不再接受；模式/档位/输入
  身份必须一致。文件相符只证明完整性，不证明自写事实真实。

R2 边界：session_close ≠ fetched_at ≠ available_at；日期/时刻用真实解析；
available_at 未知保持 null；本 B0 不实现逐行真实历史资格，真实身份的
``point_in_time_verified=true`` 一律拒绝。
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

import pandas as pd

OBJECT_REF = "candidate:lei.dual_ma.bull_state@draft-1"
CARD_PATH = (
    "docs/experiments/raw/factor-research-workbench-v1-2026-09-14/"
    "candidate-card-dual-ma-bull-state-draft-1.md"
)
FIXED = {
    "theme": "trend",
    "type": "state_signal",
    "use": "historical_description",
    "lookback": 20,
    "e_offset": 1,
    "x_offset": 22,
    "regime": "none",
}
MARKETS = {
    "CN": {
        "session_close": "15:00",
        "timezone": "Asia/Shanghai",
        "expected_calendar_market": "CN",
    },
    "US": {
        "session_close": "16:00",
        "timezone": "America/New_York",
        "expected_calendar_market": "US",
    },
}
CARRIER_MARKET = {"510300": "CN", "159915": "CN", "SPY": "US", "QQQ": "US"}

#: 必需代码键（R3）：合同不可裁剪；CLI 在生成任何结果前逐项核哈希。
REQUIRED_CODE_KEYS = (
    "src/lei_signal/research/factor_unit/__init__.py",
    "src/lei_signal/research/factor_unit/close_state.py",
    "src/lei_signal/research/factor_unit/study_contract.py",
    "src/lei_signal/research/factor_unit/state_description.py",
    "scripts/check_factor_unit_readiness.py",
    "src/lei_signal/features/indicators.py",
    "src/lei_signal/rules/lei_color.py",
    "src/lei_signal/rules/dual_ma.py",
    "src/lei_signal/domain/rules_config.py",
    "configs/rules.v2.yaml",
    "src/lei_signal/research/trading_calendar.py",
)

#: 必需规范（不可裁剪为一条带@的字符串）；每项含准确版本与指纹。
REQUIRED_STANDARDS = (
    ("docs/research/experiment-backtest-principles.md", "1.1"),
    ("docs/research/definition-standard.md", "1.1.0"),
    ("docs/research/ai-execution-contract.md", "1.0.1"),
    ("docs/research/experiment-report-template.md", "1.1.0"),
)

PRICE_BASIS_TIERS = {
    "producer_candidate_only",
    "snapshot_provenance_bound",
    "price_basis_verified",
}
_UTC_OFFSET_IN_TIME = re.compile(r"[+-]\d{2}:?\d{2}$")
EVIDENCE_SCHEMA = "factor-unit-price-evidence/1"


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ref_file(root: Path, ref, label: str) -> Path:
    """文件引用必须 {path, sha256} 齐备、文件存在且哈希匹配（消费前核）。"""
    _require(isinstance(ref, dict), f"{label} 必须是 {{path, sha256}} 结构化引用")
    _require(bool(ref.get("path")) and bool(ref.get("sha256")),
             f"{label} 缺 path 或 sha256（删哈希拒绝）")
    p = root / str(ref["path"])
    _require(p.is_file(), f"{label} 文件不存在：{ref['path']}")
    _require(ref["sha256"] == _sha256(p), f"{label} 哈希与实际文件不符：{ref['path']}")
    return p


def _parse_tz_timestamp(value, label: str) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    _require(ts.tzinfo is not None, f"{label} 必须带时区（收到 {value!r}）")
    return ts


def _check_clock(clock: dict, market: str, field: str) -> None:
    _require(isinstance(clock, dict), f"{market} {field} 必须是含 time/timezone 的对象")
    t = clock.get("time")
    tz = clock.get("timezone")
    bad_offset = isinstance(t, str) and _UTC_OFFSET_IN_TIME.search(t)
    _require(
        isinstance(t, str) and not bad_offset,
        f"{market} {field}.time 必须是当地墙上时间，不得带固定UTC偏移（夏令时会差一小时）",
    )
    _require(
        tz == MARKETS[market]["timezone"],
        f"{market} {field}.timezone 必须是 {MARKETS[market]['timezone']}"
        "（IANA时区名，夏令时由时区规则处理）",
    )
    if field == "session_close":
        _require(
            t == MARKETS[market]["session_close"],
            f"{market} session_close 必须是 {MARKETS[market]['session_close']} 当地墙上时间",
        )
    if field == "half_day_close":
        _require(
            t != MARKETS[market]["session_close"],
            f"{market} half_day_close 不得等于常规收盘时刻（半日市用16点是非法声明）",
        )


def _synthetic_schedule_sessions(root: Path, ref: dict, market: str):
    """合成日历必须逐日 session/close_at 且一一对应；返回 sessions 或抛错。"""
    p = _ref_file(root, ref, f"{market} 合成日历")
    sched = pd.read_parquet(p)
    _require(
        {"session", "close_at"} <= set(sched.columns),
        f"{market} 合成日历需要逐日 session/close_at（Markdown或声明不能冒充日历）",
    )
    sessions = pd.to_datetime(sched["session"]).reset_index(drop=True)
    _require(sessions.is_unique and sessions.is_monotonic_increasing,
             f"{market} 合成日历 session 必须唯一递增")
    for i, raw in enumerate(sched["close_at"].reset_index(drop=True)):
        ts = pd.Timestamp(raw)
        _require(ts.tzinfo is not None,
                 f"{market} 合成日历 close_at 必须逐日带时区")
        _require(ts.date() == sessions[i].date(),
                 f"{market} 合成日历 close_at 日期必须与 session 对应")
    return sessions


def _calendar_complete(root: Path, market: str, cal: dict, needed_start: str,
                       needed_end: str, symbol: str, reasons: list) -> bool:
    """内容级日历核验：所需区间逐日有定义。缺格写 reasons（资料不足），不抛。"""
    expected_market = MARKETS[market]["expected_calendar_market"]
    if cal.get("source"):
        p = _ref_file(root, cal["source"], f"{market} 日历来源")
        payload = json.loads(p.read_text())
        if payload.get("market") != expected_market:
            raise ValueError(
                f"{market} 日历来源的 market={payload.get('market')!r}，"
                f"与 {expected_market} 不符（错市场拒绝）"
            )
        from lei_signal.research.trading_calendar import TradingCalendar

        cal_obj = TradingCalendar.from_file(p)
        missing = []
        cursor = pd.Timestamp(needed_start)
        last = pd.Timestamp(needed_end)
        while cursor <= last:
            if cal_obj.status(cursor.strftime("%Y-%m-%d")).status == "unknown":
                missing.append(cursor.strftime("%Y-%m-%d"))
                if len(missing) >= 5:
                    break
            cursor += pd.Timedelta(days=1)
        if missing:
            reasons.append(
                f"{symbol}: {market} 日历在所需区间缺定义（先列）：{missing}——缺日即缺格"
            )
            return False
        # 目标尾部：评价end后 x_offset 个交易日必须可定位
        count, cursor = 0, pd.Timestamp(needed_end)
        while count < FIXED["x_offset"]:
            cursor += pd.Timedelta(days=1)
            st = cal_obj.status(cursor.strftime("%Y-%m-%d")).status
            if st == "unknown":
                reasons.append(f"{symbol}: {market} 日历在目标尾部缺定义（{cursor.date()}）")
                return False
            if st == "trading":
                count += 1
        return True
    if cal.get("synthetic_schedule"):
        sessions = _synthetic_schedule_sessions(root, cal["synthetic_schedule"], market)
        have = set(sessions.dt.strftime("%Y-%m-%d"))
        missing = []
        cursor = pd.Timestamp(needed_start)
        last = pd.Timestamp(needed_end)
        while cursor <= last:
            key = cursor.strftime("%Y-%m-%d")
            if key not in have:
                missing.append(key)
                if len(missing) >= 5:
                    break
            cursor += pd.Timedelta(days=1)
        if missing:
            reasons.append(f"{symbol}: {market} 合成日历在所需区间缺定义（先列）：{missing}")
            return False
        return True
    reasons.append(
        f"{symbol}: {market} 无日历材料（真实source与合成schedule均为空）→ 目标 blocked"
    )
    return False


def _needed_start(eval_start: str, lookback: int) -> str:
    return (pd.Timestamp(eval_start) - pd.Timedelta(days=lookback + 5)).strftime("%Y-%m-%d")


def _load_source_decision(root: Path, ref: dict) -> dict:
    p = _ref_file(root, ref, "source_decision")
    rows = {}
    with open(p, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sym = row.get("symbol")
            _require(
                sym not in rows,
                f"source_decision 每symbol必须唯一（重复冲突拒绝，不选首条/末条）：{sym}",
            )
            rows[sym] = row
    return rows


def _consume_vendor_response(root: Path, rec: dict, symbol: str,
                             input_sha: str) -> bool:
    """消费供应商原件。返回是否有可回查材料。

    引用缺省/空或未声明 vendor_traceable → False（走缺材料降级路径）；
    引用存在但结构非法、文件不存在、指纹不符、JSON非法、绑定错产品/错输入、
    缺请求参数或价格语义、记录重复 → ValueError（伪造/矛盾拒绝，不降级）。
    文件相符只证明完整性，不证明自写事实真实。
    """
    ref = rec.get("vendor_response_ref")
    if rec.get("vendor_traceable") is not True or ref in (None, ""):
        return False
    p = _ref_file(root, ref, f"{symbol} vendor_response_ref")
    try:
        payload = json.loads(p.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"{symbol}: 供应商原件不是合法JSON：{exc}") from exc
    vrecs = [r for r in payload.get("records", []) if r.get("symbol") == symbol]
    _require(
        len(vrecs) == 1,
        f"{symbol}: 供应商原件必须含且仅含一条该产品记录（重复冲突拒绝）",
    )
    vrec = vrecs[0]
    _require(
        vrec.get("input_sha256") == input_sha,
        f"{symbol}: 供应商原件绑定输入哈希与合同输入不符（错产品/错输入拒绝）",
    )
    _require(
        isinstance(vrec.get("request_params"), dict) and bool(vrec["request_params"]),
        f"{symbol}: 供应商原件缺请求参数绑定",
    )
    _require(
        isinstance(vrec.get("price_semantics"), str)
        and bool(vrec["price_semantics"]),
        f"{symbol}: 供应商原件缺价格语义绑定",
    )
    return True


def validate_study_contract(contract: dict) -> dict:
    """校验研究合同；身份/结构错误抛 ValueError，资料不足返回 restricted。"""
    _require(isinstance(contract, dict), "contract 必须是 dict")
    root = Path(contract.get("_repo_root", "."))

    # ── 身份 ──
    _require(
        contract.get("object_ref") == OBJECT_REF,
        f"object_ref 必须精确为 {OBJECT_REF}（候选未入登记表，不得伪造已登记引用）",
    )
    card = contract.get("candidate_card") or {}
    _require(card.get("path") == CARD_PATH, f"candidate_card.path 必须是 {CARD_PATH}")
    card_file = root / CARD_PATH
    _require(card_file.is_file(), "候选卡文件缺失（不得跳过核验）")
    _require(card.get("sha256") == _sha256(card_file), "candidate_card.sha256 与实际卡文件不符")

    data_mode = contract.get("data_mode")
    _require(data_mode in {"real", "synthetic"}, "data_mode 必须是 real 或 synthetic")

    # ── 固定研究坐标 ──
    for key, want in FIXED.items():
        got = contract.get(key)
        _require(got == want, f"{key} 本轮固定为 {want!r}，收到 {got!r}（参数不得擅改）")

    use = contract["use"]
    _require(use in {"historical_description"}, "use 仅允许 historical_description")
    universe = contract.get("universe") or {}
    members = universe.get("members")
    _require(
        isinstance(members, list) and members
        and all(m in CARRIER_MARKET for m in members),
        "universe.members 只能为四载体 510300/159915/SPY/QQQ 的子集",
    )
    labels = universe.get("attribute_labels") or {}
    _require(isinstance(labels, dict), "attribute_labels 必须是 dict")

    # ── 必需规范（准确版本+指纹，不可裁剪） ──
    standards = contract.get("standards")
    _require(isinstance(standards, list), "standards 必须是列表")
    by_path = {}
    for s in standards:
        _require(
            isinstance(s, dict) and s.get("path") and s.get("version") and s.get("sha256"),
            "standards 项必须为 {path, version, sha256}（不得裁剪为带@字符串）",
        )
        by_path[s["path"]] = s
    for path, version in REQUIRED_STANDARDS:
        s = by_path.get(path)
        _require(s is not None, f"缺少必需规范：{path}@{version}")
        _require(s["version"] == version, f"{path} 版本必须为 {version}（收到 {s['version']}）")
        fp = root / path
        _require(fp.is_file(), f"规范文件缺失：{path}")
        _require(s["sha256"] == _sha256(fp), f"{path} 指纹与实际文件不符")

    # ── 必需代码键（合同不可自行缩小集合） ──
    code_identity = contract.get("code_identity")
    _require(
        isinstance(code_identity, dict) and code_identity,
        "code_identity 必须是非空 dict（空源码键集合拒绝）",
    )
    missing_keys = [k for k in REQUIRED_CODE_KEYS if k not in code_identity]
    _require(
        not missing_keys,
        f"code_identity 缺少必需代码键（不可裁剪）：{missing_keys[:5]}…",
    )

    # ── 评价窗与截止 ──
    window = contract.get("evaluation_window") or {}
    _require(
        isinstance(window, dict) and bool(window.get("start")) and bool(window.get("end")),
        "evaluation_window 必须给出 {start, end}",
    )
    eval_start = pd.Timestamp(window["start"])
    eval_end = pd.Timestamp(window["end"])
    _require(eval_start <= eval_end, "evaluation_window start 不得晚于 end")
    cutoff = _parse_tz_timestamp(contract.get("research_cutoff"), "research_cutoff")
    del cutoff  # 合同侧只校验解析；统计侧由 describe_states 消费

    reasons: list[str] = []
    notes: list[str] = []
    markets_report: dict[str, dict] = {}
    data_identity = contract.get("data_identity") or {}
    calendar_identity = contract.get("calendar_identity") or {}
    _require(isinstance(data_identity, dict) and data_identity, "data_identity 必须是非空 dict")
    _require(isinstance(calendar_identity, dict), "calendar_identity 必须是 dict")

    target_basis = contract.get("target_basis")
    _require(
        target_basis in {"total_return_wealth", "vendor_adjusted_price_change"},
        "target_basis 只能是 total_return_wealth（主候选）或 "
        "vendor_adjusted_price_change（待主控确认的替代提案）；两者不可混榜",
    )

    sd_ref = contract.get("source_decision")
    _require(isinstance(sd_ref, dict), "source_decision 必须是 {path, sha256} 引用")
    sd_rows = _load_source_decision(root, sd_ref)

    for symbol in members:
        market = CARRIER_MARKET[symbol]
        sym_blockers = 0
        entry = data_identity.get(symbol) or {}
        _require(entry.get("path") and entry.get("sha256"),
                 f"{symbol}: data_identity 缺 path/sha256")
        p = root / str(entry["path"])
        _require(p.is_file(), f"{symbol}: 输入文件不存在（身份错误）")
        if entry["sha256"] != _sha256(p):
            raise ValueError(f"{symbol}: 文件哈希与合同不符——数据被篡改属身份错误")
        _require("fetched_at" in entry,
                 f"{symbol}: data_identity 必须分列 fetched_at（未知也须显式）")
        _require(
            isinstance(entry.get("date_range"), list) and len(entry["date_range"]) == 2,
            f"{symbol}: data_identity 必须声明 date_range=[first, last]",
        )

        # available_at / point_in_time
        available_at = entry.get("available_at")
        pit = entry.get("point_in_time_verified")
        if available_at is not None:
            _parse_tz_timestamp(available_at, f"{symbol} available_at")
            _require(
                entry.get("available_at_source"),
                f"{symbol}: available_at 非空时必须给出来源；不得用 session_close 冒充",
            )
            session_alias = f"session_close:{MARKETS[market]['timezone']}"
            _require(
                str(entry["available_at_source"]) != session_alias,
                f"{symbol}: 收盘时刻不得冒充资料可得时间（R2）",
            )
        if pit is True:
            _require(
                data_mode == "synthetic" and available_at is not None
                and entry.get("available_at_source"),
                f"{symbol}: 本B0不实现逐行真实历史资格，"
                "真实身份的 point_in_time_verified=true 一律拒绝",
            )
        if pit is not True:
            notes.append(
                f"{symbol}: available_at 未知/未证（point_in_time_verified=false）"
                "→ 仅事后描述资格，不授予预测资格"
            )

        # 价格证据（结构化+逐项对照）
        ev_path = _ref_file(root, entry.get("price_basis_evidence"),
                            f"{symbol} price_basis_evidence")
        try:
            evidence = json.loads(ev_path.read_text())
        except json.JSONDecodeError as exc:
            raise ValueError(f"{symbol}: 证据文件不是合法JSON：{exc}") from exc
        _require(evidence.get("schema") == EVIDENCE_SCHEMA,
                 f"{symbol}: 证据 schema 必须是 {EVIDENCE_SCHEMA}")
        records = [r for r in evidence.get("records", []) if r.get("symbol") == symbol]
        _require(records, f"{symbol}: 证据中没有该产品的记录")
        _require(
            len(records) == 1,
            f"{symbol}: 证据中该产品记录重复（冲突拒绝，不选首条/末条）",
        )
        rec = records[0]
        _require(rec.get("input_sha256") == entry["sha256"],
                 f"{symbol}: 证据 input_sha256 与输入不符（矛盾拒绝）")
        pb = entry.get("price_basis_status")
        _require(pb in PRICE_BASIS_TIERS, f"{symbol}: price_basis_status 必须是三档之一")
        _require(
            rec.get("price_basis_status") == pb,
            f"{symbol}: 证据 price_basis_status={rec.get('price_basis_status')!r} "
            f"与合同 {pb!r} 矛盾",
        )
        _require(
            rec.get("data_mode") == data_mode,
            f"{symbol}: 证据 data_mode={rec.get('data_mode')!r} 与合同 {data_mode!r} 矛盾"
            "（合成证据不得用于真实身份，反之亦然）",
        )
        price_ok = True
        if data_mode == "real":
            sd_row = sd_rows.get(symbol)
            _require(sd_row is not None, f"{symbol}: 来源裁定CSV缺该产品行（矛盾拒绝）")
            entry_sha = str(entry["sha256"])
            sd_sha = str(sd_row.get("sha256") or "")
            _require(
                sd_sha == entry_sha,
                f"{symbol}: 来源裁定CSV必须给出完整sha256且与输入精确相等"
                "（sha256_16前缀不再接受）",
            )
            sd_mode = str(sd_row.get("data_mode") or "")
            _require(
                sd_mode in ("", data_mode),
                f"{symbol}: 来源裁定CSV模式 {sd_mode!r} 与合同 {data_mode!r} 矛盾",
            )
            effective_pb = pb
            vendor_checked = False
            if pb == "price_basis_verified":
                if _consume_vendor_response(root, rec, symbol, entry_sha):
                    vendor_checked = True
                else:
                    # verified声明缺可回查供应商材料 → 按 producer_candidate_only
                    # 处理（降级，不拒绝也不编造），再用降级后的档位对照CSV
                    effective_pb = "producer_candidate_only"
                    reasons.append(
                        f"{symbol}: verified声明缺可回查供应商材料 → "
                        "按producer_candidate_only处理，继续restricted不编造"
                    )
                    sym_blockers += 1
            _require(
                sd_row.get("provenance_tier") == effective_pb,
                f"{symbol}: 来源裁定档位 {sd_row.get('provenance_tier')!r} "
                f"与有效价格档位 {effective_pb!r} 矛盾",
            )
            # 目标闸（四项修复）：能追到供应商调整价的生成过程 ≠ 已核含分红
            # 财富构造；本轮真实目标没有经过主控确认的资料，一律 blocked 并注明
            # manual_target_review_required，不实现自行批准真实目标的开关。
            price_ok = False
            sym_blockers += 1
            if target_basis == "total_return_wealth":
                if effective_pb == "producer_candidate_only":
                    reasons.append(
                        f"{symbol}: 真实模式 {target_basis} 需要更高价格档位"
                        f"（当前 {effective_pb}）；缺可回查材料继续 restricted，不编造"
                    )
                else:
                    reasons.append(
                        f"{symbol}: {effective_pb} 只证明供应商调整价/快照溯源的"
                        "生成过程，不证明含分红财富构造；total_return_wealth 目标"
                        "保持 blocked（manual_target_review_required）"
                    )
                    if vendor_checked:
                        notes.append(
                            f"{symbol}: 来源检查完成（供应商原件身份一致），"
                            "含分红财富构造未核 → 目标仍未批准"
                        )
            else:
                reasons.append(
                    f"{symbol}: vendor_adjusted_price_change 是主控未确认的替代"
                    "提案；真实目标保持 blocked（manual_target_review_required）"
                )
        elif pb != "price_basis_verified":
            reasons.append(f"{symbol}: 合成模式证据未达 price_basis_verified（{pb}）")
            price_ok = False
            sym_blockers += 1

        # 日历（内容级核验）
        cal = calendar_identity.get(market) or {}
        _require(bool(cal), f"{market}: calendar_identity 缺失")
        _check_clock(
            {"time": cal.get("session_close", MARKETS[market]["session_close"]),
             "timezone": cal.get("timezone", MARKETS[market]["timezone"])},
            market, "session_close",
        )
        hd = cal.get("half_day_close")
        if hd is not None:
            _check_clock(hd, market, "half_day_close")
        cal_ok = False
        if cal.get("source") or cal.get("synthetic_schedule"):
            needed_start = _needed_start(window["start"], FIXED["lookback"])
            cal_ok = _calendar_complete(
                root, market, cal, needed_start, window["end"], symbol, reasons
            )
            if not cal_ok:
                sym_blockers += 1
        else:
            reasons.append(
                f"{symbol}: {market} 无日历材料（真实source与合成schedule均为空）"
                "→ 目标 blocked"
            )
            sym_blockers += 1

        markets_report[symbol] = {
            "price_basis": pb,
            "calendar": "qualified" if cal_ok else "blocked",
            "target": ("pending_controller_freeze"
                       if price_ok and cal_ok and sym_blockers == 0 else "blocked"),
        }

    allowed = []
    blocked = [s for s, v in markets_report.items() if v["target"] == "blocked"]
    pending = [s for s, v in markets_report.items() if v["target"] == "pending_controller_freeze"]
    status = "restricted" if reasons else "ok"
    if pending:
        notes.append(
            "存在 pending_controller_freeze 目标（" + ", ".join(pending)
            + "）：资格齐备待主控冻结协议；不自动启动执行"
        )
    if blocked:
        reasons.append(
            "资料不足：声明用途（historical_description 的既定目标）当前不可执行，仅保留资格诊断"
        )
    return {
        "status": status,
        "reasons": reasons,
        "notes": notes,
        "allowed_uses": allowed,
        "markets": markets_report,
        "alternative_target_note": (
            "供应商调整价格变化与含分红财富是两个目标，不能改名互换"
            if target_basis == "total_return_wealth" else ""
        ),
    }
