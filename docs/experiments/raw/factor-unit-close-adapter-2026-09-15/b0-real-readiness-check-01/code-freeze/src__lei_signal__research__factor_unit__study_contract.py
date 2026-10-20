"""研究坐标与时间/目标合同校验（factor_unit，B0）。

只做合同的结构、身份、参数校验与资料资格裁定；不计算任何真实因子表现。
结构/身份/参数非法抛 ValueError；资料不足返回受限/阻断状态并给出原因，
不伪造可执行资格。本轮固定 theme=trend、type=state_signal、
use=historical_description、lookback=20、e_offset=1、x_offset=22、regime=none。

R2 边界：session_close（当地交易所收盘）≠ fetched_at（抓取时刻）≠
available_at（资料实际可得时刻）。available_at 未知时保持 null 且
``point_in_time_verified=false``；历史描述资格不要求假造当时毫秒，
也不授予预测资格。

R4 边界：``price_basis_verified`` 必须来自独立来源证据，自填无效。
价格尺度不清的市场不产生有投资含义的目标资格。
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

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
        "exchange_note": "上交所510300/深交所159915",
    },
    "US": {
        "session_close": "16:00",
        "timezone": "America/New_York",
        "exchange_note": "NYSE挂牌SPY/Nasdaq挂牌QQQ；两者日历通常一致但不得假定永远一致",
    },
}
CARRIER_MARKET = {"510300": "CN", "159915": "CN", "SPY": "US", "QQQ": "US"}
_UTC_OFFSET_IN_TIME = re.compile(r"[+-]\d{2}:?\d{2}$")


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def validate_study_contract(contract: dict) -> dict:
    """校验研究合同；非法抛 ValueError，资料不足返回受限状态。

    返回 dict：status（ok/restricted）、reasons（阻断）、notes（信息）、
    allowed_uses、markets（逐载体 price_basis/calendar/target 三项资格）。
    不计算任何真实表现。
    """
    _require(isinstance(contract, dict), "contract 必须是 dict")

    # ── 身份 ──
    _require(
        contract.get("object_ref") == OBJECT_REF,
        f"object_ref 必须精确为 {OBJECT_REF}（候选未入登记表，不得伪造已登记引用）",
    )
    card = contract.get("candidate_card") or {}
    _require(card.get("path") == CARD_PATH, f"candidate_card.path 必须是 {CARD_PATH}")
    card_file = Path(contract.get("_repo_root", ".")) / CARD_PATH
    if card_file.is_file():
        actual = _sha256(card_file)
        _require(card.get("sha256") == actual, "candidate_card.sha256 与实际卡文件不符")

    # ── 固定研究坐标 ──
    for key, want in FIXED.items():
        got = contract.get(key)
        _require(got == want, f"{key} 本轮固定为 {want!r}，收到 {got!r}（参数不得擅改）")

    use = contract["use"]
    _require(
        use in {"historical_description"},
        "use 仅允许 historical_description（预测用途另获授权）",
    )
    universe = contract.get("universe") or {}
    members = universe.get("members")
    _require(
        isinstance(members, list) and members
        and all(m in CARRIER_MARKET for m in members),
        "universe.members 只能为四载体 510300/159915/SPY/QQQ 的子集（不得增删换标的）",
    )
    labels = universe.get("attribute_labels") or {}
    _require(
        isinstance(labels, dict),
        "attribute_labels 必须是 dict（成长/宽基等标签允许重叠，不组成可加总归因账）",
    )

    standards = contract.get("standards") or []
    _require(isinstance(standards, list) and standards, "standards 必须列出实际采用的规范")
    for s in standards:
        _require(isinstance(s, str) and "@" in s, f"standards 项必须形如 path@version：{s!r}")
    cutoff = contract.get("research_cutoff")
    _require(
        isinstance(cutoff, str) and "T" in cutoff and cutoff.endswith("+08:00"),
        "research_cutoff 必须是带 +08:00 时区的 ISO 时刻",
    )
    code_identity = contract.get("code_identity")
    _require(
        isinstance(code_identity, dict) and code_identity,
        "code_identity 必须是非空 dict（空源码键集合拒绝）",
    )

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

    for symbol in members:
        market = CARRIER_MARKET[symbol]
        entry = data_identity.get(symbol) or {}
        _require(
            entry.get("path") and entry.get("sha256"),
            f"{symbol}: data_identity 缺 path/sha256",
        )
        p = Path(entry["path"])
        if not p.is_file():
            reasons.append(f"{symbol}: 输入文件不存在")
            markets_report[symbol] = {
                "price_basis": "missing",
                "calendar": "unverified",
                "target": "blocked",
            }
            continue
        actual = _sha256(p)
        if entry["sha256"] != actual:
            reasons.append(f"{symbol}: 文件哈希与合同不符（先验哈希后消费；被改输入=资料不足）")
        _require(
            "fetched_at" in entry,
            f"{symbol}: data_identity 必须分列 fetched_at（未知也须显式）",
        )

        # available_at / point_in_time（R2）
        available_at = entry.get("available_at")
        pit = entry.get("point_in_time_verified")
        if available_at is not None:
            _require("T" in str(available_at), f"{symbol}: available_at 必须是 ISO 时刻或 null")
            _require(
                entry.get("available_at_source"),
                f"{symbol}: available_at 非空时必须给出来源；不得用 session_close 冒充可得时间",
            )
            session_alias = f"session_close:{MARKETS[market]['timezone']}"
            _require(
                str(entry["available_at_source"]) != session_alias,
                f"{symbol}: 收盘时刻不得冒充资料可得时间（R2）",
            )
        if pit is True:
            _require(
                available_at is not None and entry.get("available_at_source"),
                f"{symbol}: point_in_time_verified=true 需要非空 available_at 及来源；"
                "自填可信标记拒绝",
            )
        else:
            notes.append(
                f"{symbol}: available_at 未知（point_in_time_verified=false）"
                "→ 仅事后描述资格，不授予预测资格"
            )

        # 价格口径（R4）
        pb = entry.get("price_basis_status")
        _require(
            pb in {"producer_candidate_only", "snapshot_provenance_bound", "price_basis_verified"},
            f"{symbol}: price_basis_status 必须是三档之一（自填 verified 之外的身份不受理）",
        )
        _require(
            not (pb == "price_basis_verified" and not entry.get("price_basis_evidence")),
            f"{symbol}: price_basis_verified 必须附 price_basis_evidence（来源证据），自填无效",
        )

        # 日历（R2/合同要求）：时钟声明先于文件存在性校验
        cal = calendar_identity.get(market) or {}
        _require(bool(cal), f"{market}: calendar_identity 缺失")
        _check_clock(
            {
                "time": cal.get("session_close", MARKETS[market]["session_close"]),
                "timezone": cal.get("timezone", MARKETS[market]["timezone"]),
            },
            market,
            "session_close",
        )
        hd = cal.get("half_day_close")
        if hd is not None:
            _check_clock(hd, market, "half_day_close")
        cal_ok = False
        if cal.get("source"):
            cal_path = Path(contract.get("_repo_root", ".")) / str(cal["source"])
            if cal_path.is_file() and (not cal.get("sha256") or cal["sha256"] == _sha256(cal_path)):
                cov = cal.get("coverage") or [None, None]
                _require(
                    isinstance(cov, list) and len(cov) == 2,
                    f"{market}: 日历 coverage 必须是 [start, end]",
                )
                cal_ok = True
            elif not cal_path.is_file():
                reasons.append(f"{market}: 日历来源文件不存在：{cal['source']}")
            else:
                reasons.append(f"{market}: 日历来源哈希不符")
        else:
            reasons.append(
                f"{market}: 无本地可核日历来源 → 交易日目标保持 blocked"
                "（不从报价日期或周一至周五反推日历）"
            )
        if cal_ok and entry.get("date_range"):
            cov = cal.get("coverage") or [None, None]
            dr = entry["date_range"]
            if (cov[0] and dr[0] < cov[0]) or (cov[1] and dr[1] > cov[1]):
                reasons.append(
                    f"{symbol}: 数据区间 {dr} 超出日历覆盖 {cov}（日期冲突；缺日即缺格，不补造）"
                )

        # 目标资格
        if target_basis == "total_return_wealth" and pb != "price_basis_verified":
            tgt = "blocked"
            reasons.append(
                f"{symbol}: 主目标 total_return_wealth 需要 price_basis_verified；"
                f"当前 {pb} → 目标阻断，不得开算"
            )
        elif target_basis == "vendor_adjusted_price_change" and pb != "snapshot_provenance_bound":
            tgt = "blocked"
            reasons.append(
                f"{symbol}: 替代目标 vendor_adjusted_price_change 至少需要 "
                f"snapshot_provenance_bound；当前 {pb}"
            )
        else:
            tgt = "pending_controller_freeze"
        markets_report[symbol] = {
            "price_basis": pb,
            "calendar": "declared_local" if cal_ok else "unverified",
            "target": tgt,
        }

    allowed = []
    blocked = [s for s, v in markets_report.items() if v["target"] == "blocked"]
    pending = [s for s, v in markets_report.items() if v["target"] == "pending_controller_freeze"]
    status = "restricted" if reasons else "ok"
    if pending:
        notes.append(
            "存在 pending_controller_freeze 目标（" + ", ".join(pending)
            + "）：资料齐备待主控冻结协议；不自动启动执行"
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
            "若仅能证明供应商调整价格，可记录替代目标提案 vendor_adjusted_price_change "
            "等待主控确认；与 total_return_wealth 不可混榜"
            if target_basis == "total_return_wealth"
            else ""
        ),
    }
