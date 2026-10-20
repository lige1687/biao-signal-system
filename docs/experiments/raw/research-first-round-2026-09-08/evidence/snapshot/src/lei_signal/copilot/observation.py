"""Agent 观察存证账本（总控 00-review-contract-v1.2 §3–§7 返修版）。

本模块只做记录与到期检查，不改判定、排序、权重；红线（实现层强制）：

- **展示批次与可评价主张分开**（§3）：批次（record_type=display_batch）保存
  完整展示卡片与成员主张ID，无评价期限、不进任何分母；空列表也是一份有效
  展示。当前对象集合从当前批次的成员读取，A→B→A 保留三次展示顺序，
  删除/清空不靠新对象 insert 驱动。
- **主张身份=完整 SHA256**（§3/§4）：规范输入含来源记录/对象/用途、claim、
  direction、payload、input_hash、规则/证据引用、评价 kind/version/config
  与期限——同 payload 改方向/claim/规则/评价版本仍是新主张，不被去重折叠。
- **展示次数与研究样本数分开**（§4）：sample_key 由来源/策略/标的/观察日/
  主张类别方向/规则/评价配置共同决定；纯措辞或展示修订不多算样本。
- **结果读写显式三键** (observation_id, evaluation_version, horizon)（§4）：
  不给另一评价版本填结果；改方法=新版本，不借旧成绩。
- **到期与缺日**（§5）：pending=尚未到期；missing_data=到期数据缺失、可重试
  （无 60 天永久停止）；not_applicable=主张不可按此方法评价。严格交易日评价
  需要可信日历（可注入适配器，归 01R），日历不明不产生 ready；按行情行数
  偏移的结果保留为旧版本参考（available_rows），不改标签冒充严格结果。
  评价受 as_of 截止约束；ready 必须有有限有效数值与日期。
- **汇总分桶**（§4）：按来源/策略/评价方法/版本/方向/期限/来源质量分组；
  n_observations（展示记录数）与 n_samples（去重样本数）分列；conflict 可见
  并排除比例；旧版结果按版本单列不与重算版相加；独立恐慌事件数无冻结定义
  时返回 null（未知）。禁止跨桶总胜率。

写入原子性：调用方单事务 commit；本模块不自 commit。
"""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

SCHEMA_VERSION = 3  # 025：引用冻结/评价配置全文/first_shown_at 落库

# ---- 固定评价 kind（v1.2 §7；现有 kind 通过兼容映射读取，版本不混用） ----
KIND_TECHNICAL_FORWARD = "technical_forward_change"      # 推荐价格观察
KIND_SENTIMENT_DIRECTION = "sentiment_direction_change"  # 情绪方向观察
KIND_DISCUSSION_CLAIM = "discussion_claim"               # 03 标的讨论主张
KIND_PLAN_RULE_FOLLOWUP = "plan_rule_followup"           # 04 计划原逻辑检查
KIND_NON_EVALUABLE = "non_evaluable_explanation"         # 解释/假设，无胜率

#: 旧 kind → 新 kind 兼容映射（读取展示用；分组仍按存储值，不混算）
KIND_COMPAT = {
    "fwd_close_change": KIND_TECHNICAL_FORWARD,
    "sentiment_fwd_change": KIND_SENTIMENT_DIRECTION,
}

# ---- 评价版本（改方法必升版本；各版本独立成桶，不相加） ----
#: 推荐：严格 N 交易日收盘观察（需可信日历）
RECOMMENDATION_EVAL_VERSION = "technical_close_close_tdays_v2"
#: 推荐：按可用行情行偏移的旧口径，保留为参考（available_rows）
RECOMMENDATION_ROWS_VERSION = "fwd_close_change_v1"
#: 情绪：严格 N 交易日（需可信日历）
SENTIMENT_EVAL_VERSION = "sentiment_close_close_tdays_v2"
#: 情绪：按行参考旧口径
SENTIMENT_ROWS_VERSION = "sentiment_fwd_close_v1"
#: 历史迁入专用（不可考字段不伪造）
LEGACY_EVAL_VERSION = "legacy_close_close_v0"

#: 参考口径版本集合（汇总里单列，不进严格口径的普通统计标签）
REFERENCE_VERSIONS = {RECOMMENDATION_ROWS_VERSION, SENTIMENT_ROWS_VERSION,
                      LEGACY_EVAL_VERSION}
#: kind → 行参考版本（记录时同时建参考版占位，由行参考评价器填充）
_KIND_ROWS_VERSION = {
    KIND_TECHNICAL_FORWARD: RECOMMENDATION_ROWS_VERSION,
    KIND_SENTIMENT_DIRECTION: SENTIMENT_ROWS_VERSION,
    # 兼容旧调用直接传旧 kind 字符串
    "fwd_close_change": RECOMMENDATION_ROWS_VERSION,
    "sentiment_fwd_change": SENTIMENT_ROWS_VERSION,
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(canon: str) -> str:
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _canonical(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _finite_positive(v: Any) -> bool:
    return _to_finite_positive(v) is not None


def _to_finite_positive(v: Any) -> float | None:
    """显式数值转换（P9）：bool 不算数；int/float/数字字符串 → float；
    NaN/Inf/非正/不可转 → None（统一判无效，后续除法只用转换后的 float）。"""
    if isinstance(v, bool):
        return None
    if not isinstance(v, (int, float, str)):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if (math.isfinite(f) and f > 0) else None


# ---------------------------------------------------------------------------
# 日历适配器（§2/§5；真实适配器归 01R，此处只定义注入接口）
# ---------------------------------------------------------------------------

#: 严格交易日评价的日历适配器：market, base_date, n → 目标交易日 ISO 日期，
#: 日历不可信/未知返回 None（此时不产生 ready）。禁止修改全局默认日历。
CalendarAdapter = Callable[[str, str, int], "str | None"]


def dict_calendar(dates: Sequence[str]) -> CalendarAdapter:
    """测试用替身：给定可信交易日序列，返回第 n 个交易日的适配器。

    仅用于隔离测试与迁入预演；生产日历由 01R 提供（v1.2 §2）。
    """
    ordered = sorted(set(dates))

    def _lookup(market: str, base_date: str, n: int) -> str | None:
        import bisect

        i = bisect.bisect_right(ordered, base_date) - 1
        if i < 0:
            return None
        j = i + n
        return ordered[j] if j < len(ordered) else None

    return _lookup


# ---------------------------------------------------------------------------
# 1) 记录：展示批次（不可变链） + 单对象主张（完整身份）
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ObservationItem:
    """一条可检验的单对象主张。

    身份=完整 SHA256（claim/direction/payload/input_hash/规则/证据/评价
    kind+version+config/期限全部参与），同 payload 改语义仍是新主张。
    claim_class 是研究样本类别（措辞修订不改变它，避免多算样本）。
    shown=False 表示仅生成过程、未实际展示（不进前向统计）。
    """

    instrument_id: str | None
    payload: dict[str, Any]
    claim: str = ""
    direction: str | None = None  # 'up' | 'down' | None=无方向主张
    horizons: Sequence[int] = ()
    baseline: str | None = None
    scope: str = ""
    strategy: str = ""
    available_at: str | None = None
    rule_refs: Sequence[str] = field(default_factory=list)
    evidence_refs: Sequence[str] = field(default_factory=list)
    claim_class: str = ""          # 主张类别（sample_key 成分；空=来源+方向）
    eval_config: dict[str, Any] = field(default_factory=dict)
    # 冻结引用（P7，v1.2 §1）：写入时快照，材料更新不回写旧记录
    rule_refs_frozen: Sequence[dict] = field(default_factory=list)     # RuleRef
    evidence_refs_frozen: Sequence[dict] = field(default_factory=list)  # EvidenceRef
    data_refs_frozen: Sequence[dict] = field(default_factory=list)      # MarketDataRef
    shown: bool = True


def _claim_identity(
    source_type: str,
    source_record_id: str,
    it: ObservationItem,
    evaluation_kind: str,
    evaluation_version: str,
    eval_config_hash: str,
    input_hash: str,
) -> str:
    """主张 observation_id：完整 SHA256（v1.2 §3，不缩短防碰撞）。"""
    canon = _canonical({
        "source_type": source_type,
        "source_record_id": source_record_id,
        "instrument_id": it.instrument_id,
        "claim": it.claim,
        "direction": it.direction,
        "payload": it.payload,
        "input_hash": input_hash,
        "available_at": it.available_at,
        "rule_refs": list(it.rule_refs),
        "evidence_refs": list(it.evidence_refs),
        "rule_refs_frozen": list(it.rule_refs_frozen),
        "evidence_refs_frozen": list(it.evidence_refs_frozen),
        "data_refs_frozen": list(it.data_refs_frozen),
        "evaluation_kind": evaluation_kind,
        "evaluation_version": evaluation_version,
        "eval_config_hash": eval_config_hash,
        "horizons": list(it.horizons),
        "scope": it.scope,
        "strategy": it.strategy,
        "baseline": it.baseline,
    })
    return "obs_" + _sha256(canon)


def _sample_key(
    source_type: str,
    observed_at: str,
    it: ObservationItem,
    evaluation_kind: str,
    evaluation_version: str,
    eval_config_hash: str,
) -> str:
    """研究样本键（v1.2 §4）：措辞/展示修订不改变，不多算样本。"""
    canon = _canonical({
        "source_type": source_type,
        "strategy": it.strategy,
        "scope": it.scope,
        "instrument_id": it.instrument_id,
        "observed_at": observed_at,
        "claim_class": it.claim_class or f"{source_type}:{it.direction}",
        "direction": it.direction,
        # Q1：样本键消费与汇总同一规则身份（冻结版本），不再用路径字符串
        "rule_identity": _rule_identity(list(it.rule_refs_frozen)),
        "evaluation_kind": evaluation_kind,
        "evaluation_version": evaluation_version,
        "eval_config_hash": eval_config_hash,
    })
    return "sk_" + _sha256(canon)


def _rule_identity(rule_refs_frozen: Any) -> str:
    """冻结 RuleRef → 稳定规则身份（Q1）：rule_id@version:config_hash 前 8 位，
    排序后连接。**不使用文件路径、引用文案或记录生成时间**。
    无冻结引用（023/024 旧记录）→ ""（历史规则版本未知，不与任何新版本混算）。
    """
    frozen = rule_refs_frozen
    if isinstance(frozen, str):
        try:
            frozen = json.loads(frozen)
        except (TypeError, ValueError):
            frozen = None
    if not frozen:
        return ""
    parts = []
    for r in frozen:
        if not isinstance(r, dict):
            continue
        rid = str(r.get("rule_id") or "?")
        ver = str(r.get("version") or "?")
        ch = str(r.get("config_hash") or "")[:8]
        parts.append(f"{rid}@{ver}:{ch}")
    return "|".join(sorted(parts))


def _current_batch(
    conn: sqlite3.Connection, source_type: str, source_record_id: str
) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM agent_observations WHERE record_type = 'display_batch' "
        "AND source_type = ? AND source_record_id = ? AND superseded_by IS NULL "
        # Q3：草稿（未展示）不是当前；Q5：历史迁入不接管实时当前
        "AND display_status != 'not_shown' "
        "AND COALESCE(legacy_quality, '') != 'legacy'",
        (source_type, source_record_id),
    ).fetchone()


def record_observations(
    conn: sqlite3.Connection,
    *,
    source_type: str,
    source_record_id: str,
    observed_at: str,
    evaluation_kind: str,
    evaluation_version: str,
    items: Iterable[ObservationItem],
    event_group_id: str | None = None,
    emitted_at: str | None = None,
    input_hash: str = "unknown",
    legacy: bool = False,
    legacy_quality: str | None = None,
    revision_key: str | None = None,
    batch_payload: dict[str, Any] | None = None,
    shown: bool = True,
) -> dict[str, int]:
    """落一批展示事实：一条展示批次 + 若干单对象主张。幂等。

    - 主张按完整身份 INSERT OR IGNORE：相同语义重试去重；claim/direction/
      规则/评价版本任一变化=新主张（不被折叠）。
    - 批次：带 revision_key 时按键定位（旧键重试不重新成为当前）；无键时
      与当前批次比较内容——未变复用，变化新建并链接前一批次（A→B→A 保留
      三次顺序；删除/清空也产生新批次，当前对象集合=当前批次成员）。
    - 返回 {claims_inserted, claims_deduped, batch_created, batch_reused,
           stale_revision_ignored}。
    """
    emitted = emitted_at or _now()
    items = list(items)
    quality = legacy_quality or ("legacy" if legacy else "ok")
    now = _now()
    inserted = deduped = shown_promoted = 0

    def _outcome_placeholders(obs_id: str, it: ObservationItem) -> None:
        """评价占位：主张自身版本（严格）；有行参考口径的 kind 加参考版。"""
        versions = {evaluation_version}
        rows_ver = _KIND_ROWS_VERSION.get(evaluation_kind)
        if rows_ver and rows_ver != evaluation_version:
            versions.add(rows_ver)
        for h in it.horizons:
            for v in versions:
                conn.execute(
                    "INSERT OR IGNORE INTO agent_observation_outcomes "
                    "(observation_id, evaluation_version, horizon, status, evaluation_kind) "
                    "VALUES (?, ?, ?, 'pending', ?)",
                    (obs_id, v, h, evaluation_kind),
                )

    # ---- Q2：来源修订身份与冻结依据分开。业务内容哈希只含业务语义
    # （payload/claim/方向/期限/对象），不含冻结引用与 input_hash——同一来源
    # 修订重试时复用首次已保存的依据，不因当前磁盘材料变化伪造新展示事件。
    business = {
        "payload": batch_payload if batch_payload is not None
        else [it.payload for it in items],
        "claims": [it.claim for it in items],
        "directions": [it.direction for it in items],
        "horizons": [list(it.horizons) for it in items],
        "instruments": [it.instrument_id for it in items],
        "revision_key": revision_key,
    }
    business_hash = _sha256(_canonical(business))

    def _promote(row) -> bool:
        """把此前仅生成的批次升级为实际展示（记首次展示时间，不覆盖）。"""
        if shown and row["display_status"] == "not_shown":
            conn.execute(
                "UPDATE agent_observations SET display_status = 'shown', "
                "first_shown_at = COALESCE(first_shown_at, ?), updated_at = ? "
                "WHERE observation_id = ?",
                (now, now, row["observation_id"]),
            )
            return True
        return False

    # ---- 重试识别（优先于生成新引用，Q2）----
    if revision_key is not None:
        keyed_id = "batch_" + _sha256(
            _canonical([source_type, source_record_id, revision_key]))
        keyed = conn.execute(
            "SELECT * FROM agent_observations WHERE observation_id = ?",
            (keyed_id,)).fetchone()
        if keyed is not None:
            if keyed["payload_hash"] != business_hash:
                # 相同稳定修订键携带不同业务内容 = 显式冲突（不静默当重复，
                # 不改写旧事件；旧依据与旧正文保持原样）
                return {"claims_inserted": 0, "claims_deduped": 0,
                        "batch_created": 0, "batch_reused": 0,
                        "stale_revision_ignored": 0, "shown_promoted": 0,
                        "revision_conflict": 1}
            _promote(keyed)
            return {"claims_inserted": 0, "claims_deduped": len(items),
                    "batch_created": 0, "batch_reused": 1,
                    "stale_revision_ignored": 0, "shown_promoted": 0}
    else:
        cur0 = _current_batch(conn, source_type, source_record_id)
        if cur0 is not None and cur0["payload_hash"] == business_hash:
            # 同业务内容重试：复用当前批次的首次依据，不重建引用（Q2）
            if _promote(cur0):
                shown_promoted += 1
            return {"claims_inserted": 0, "claims_deduped": len(items),
                    "batch_created": 0, "batch_reused": 1,
                    "stale_revision_ignored": 0,
                    "shown_promoted": shown_promoted}
        # Q3：草稿转正——同业务内容的未展示批次，本次真正展示则升级它
        if shown:
            draft = conn.execute(
                "SELECT * FROM agent_observations WHERE record_type='display_batch' "
                "AND source_type = ? AND source_record_id = ? "
                "AND display_status = 'not_shown' "
                "AND COALESCE(legacy_quality,'') != 'legacy' "
                "AND payload_hash = ? ORDER BY created_at DESC LIMIT 1",
                (source_type, source_record_id, business_hash)).fetchone()
            if draft is not None:
                _promote(draft)  # 必然升级（shown=True 且 not_shown）
                cur1 = _current_batch(conn, source_type, source_record_id)
                if cur1 is not None:
                    conn.execute(
                        "UPDATE agent_observations SET superseded_by = ?, "
                        "updated_at = ? WHERE observation_id = ? "
                        "AND superseded_by IS NULL",
                        (draft["observation_id"], now, cur1["observation_id"]))
                # 草稿主张此前未建评价占位 → 现在补建
                for member in json.loads(draft["batch_members"] or "[]"):
                    row = conn.execute(
                        "SELECT payload, horizons, evaluation_kind, "
                        "evaluation_version, claim, direction, scope, strategy, "
                        "sample_key, eval_config_hash FROM agent_observations "
                        "WHERE observation_id = ?", (member,)).fetchone()
                    if row is None:
                        continue
                    it2 = ObservationItem(
                        instrument_id=None, payload=json.loads(row["payload"]),
                        claim=row["claim"], direction=row["direction"],
                        horizons=json.loads(row["horizons"] or "[]"),
                        scope=row["scope"] or "", strategy=row["strategy"] or "")
                    _outcome_placeholders(member, it2)
                return {"claims_inserted": 0, "claims_deduped": len(items),
                        "batch_created": 0, "batch_reused": 0,
                        "stale_revision_ignored": 0, "shown_promoted": 1,
                        "batch_promoted": 1}

    claim_ids: list[str] = []
    for it in items:
        cfg_hash = _sha256(_canonical(it.eval_config or {}))[:16]
        obs_id = _claim_identity(source_type, source_record_id, it,
                                 evaluation_kind, evaluation_version, cfg_hash,
                                 input_hash)
        claim_ids.append(obs_id)
        existing = conn.execute(
            "SELECT display_status FROM agent_observations "
            "WHERE observation_id = ?", (obs_id,)
        ).fetchone()
        item_shown = bool(it.shown and shown)
        if existing is not None:
            deduped += 1
            # P3：先按未展示落档、后来真正展示 → 升级为 shown 并记首次展示
            # 时间（不被旧 not_shown 去重吞掉；不改旧生成正文）
            if item_shown and existing["display_status"] == "not_shown":
                conn.execute(
                    "UPDATE agent_observations SET display_status = 'shown', "
                    "first_shown_at = COALESCE(first_shown_at, ?), updated_at = ? "
                    "WHERE observation_id = ?",
                    (now, now, obs_id),
                )
                _outcome_placeholders(obs_id, it)  # 展示后才进前向评价
                shown_promoted += 1
            continue
        conn.execute(
            """
            INSERT INTO agent_observations (
                observation_id, schema_version, source_type, source_record_id,
                scope, strategy, instrument_id, event_group_id,
                observed_at, available_at, emitted_at,
                input_hash, payload_hash, payload, claim, horizons, baseline,
                direction, layer, evaluation_kind, evaluation_version,
                rule_refs, evidence_refs, supersedes_id, legacy,
                record_type, sample_key, eval_config_hash,
                previous_batch_id, batch_members, legacy_quality, display_status,
                eval_config_json, rule_refs_frozen, evidence_refs_frozen,
                data_refs_frozen, first_shown_at,
                created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                obs_id, SCHEMA_VERSION, source_type, source_record_id,
                it.scope, it.strategy, it.instrument_id,
                event_group_id or source_record_id,
                observed_at, it.available_at or "unknown", emitted,
                input_hash, obs_id[-16:], _canonical(it.payload), it.claim,
                json.dumps(list(it.horizons)), it.baseline,
                it.direction, "observation", evaluation_kind, evaluation_version,
                json.dumps(list(it.rule_refs)), json.dumps(list(it.evidence_refs)),
                None, 1 if legacy else 0,
                "claim",
                _sample_key(source_type, observed_at, it, evaluation_kind,
                            evaluation_version, cfg_hash),
                cfg_hash,
                None, "[]", quality,
                "shown" if item_shown else "not_shown",
                # P4/P7：评价配置全文 + 冻结引用（写入时快照）
                _canonical(it.eval_config or {}),
                _canonical(list(it.rule_refs_frozen)),
                _canonical(list(it.evidence_refs_frozen)),
                _canonical(list(it.data_refs_frozen)),
                (now if item_shown and not legacy else None),
                now, now,
            ),
        )
        inserted += 1
        if item_shown:
            # P3：未展示主张不建评价占位（生成过程不进前向统计）
            _outcome_placeholders(obs_id, it)

    # ---- 批次（Q2：ID 用业务内容/修订键，不含冻结引用）----
    content = {
        "claims": claim_ids,
        "payload": business["payload"],
        "revision_key": revision_key,
    }
    if revision_key is not None:
        batch_id = keyed_id
        content_hash = business_hash
    else:
        content_hash = business_hash
        batch_id = "batch_" + _sha256(
            _canonical([source_type, source_record_id, content_hash]))

    # 同 ID 已存在：无键模式 = A→B→A 的再次展示 → 序号后缀新建（v1.2 §3
    # 保留完整展示顺序）；带键模式已在上方重试/冲突分支返回，不会到这里。
    probe = batch_id
    seq = 1
    while conn.execute(
        "SELECT 1 FROM agent_observations WHERE observation_id = ?", (probe,)
    ).fetchone() is not None:
        seq += 1
        probe = f"{batch_id}#{seq}"
    batch_id = probe

    conn.execute(
        """
        INSERT INTO agent_observations (
            observation_id, schema_version, source_type, source_record_id,
            scope, strategy, instrument_id, event_group_id,
            observed_at, available_at, emitted_at,
            input_hash, payload_hash, payload, claim, horizons, baseline,
            direction, layer, evaluation_kind, evaluation_version,
            rule_refs, evidence_refs, supersedes_id, legacy,
            record_type, sample_key, eval_config_hash,
            previous_batch_id, batch_members, legacy_quality, display_status,
            eval_config_json, rule_refs_frozen, evidence_refs_frozen,
            data_refs_frozen, first_shown_at,
            created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            batch_id, SCHEMA_VERSION, source_type, source_record_id,
            "", "", None, event_group_id or source_record_id,
            observed_at, "unknown", emitted,
            input_hash, content_hash, _canonical(content), "", "[]", None,
            None, "display_batch", evaluation_kind, evaluation_version,
            "[]", "[]", None, 0,
            "display_batch", None, None,
            cur["observation_id"] if cur is not None else None,
            json.dumps(claim_ids), quality,
            "shown" if shown else "not_shown",
            "{}", "[]", "[]", "[]",
            now if shown else None,
            now, now,
        ),
    )
    if cur is not None:
        conn.execute(
            "UPDATE agent_observations SET superseded_by = ?, updated_at = ? "
            "WHERE observation_id = ? AND superseded_by IS NULL",
            (batch_id, now, cur["observation_id"]),
        )
    return {"claims_inserted": inserted, "claims_deduped": deduped,
            "batch_created": 1, "batch_reused": 0,
            "stale_revision_ignored": stale_ignored,
            "shown_promoted": shown_promoted}


def current_claim_ids(
    conn: sqlite3.Connection,
    source_type: str | None = None,
    source_record_id: str | None = None,
) -> set[str]:
    """当前对象集合：当前展示批次的成员（v1.2 §3；单条 superseded_by 非权威）。"""
    sql = ("SELECT batch_members FROM agent_observations "
           "WHERE record_type = 'display_batch' AND superseded_by IS NULL")
    args: list[Any] = []
    if source_type:
        sql += " AND source_type = ?"
        args.append(source_type)
    if source_record_id:
        sql += " AND source_record_id = ?"
        args.append(source_record_id)
    out: set[str] = set()
    for row in conn.execute(sql, args).fetchall():
        try:
            out.update(json.loads(row["batch_members"]))
        except (TypeError, ValueError):
            continue
    return out


# ------------------------------------------------------------------ 封装 ----


def record_recommendation_card(conn: sqlite3.Connection, card) -> dict[str, int]:
    """推荐卡 → 展示批次（完整卡片原文）+ 每标的一条主张。

    技术推荐的 1/5/20 日涨跌是观察而非方向主张（direction=None）：
    不算方向命中，不冒充原退出规则下的交易胜率。空卡也记录（有效展示）。

    P7（引用真正落库）：每条主张冻结——规则账本整体版本（ruleset_ref）、
    该标的的胜率表引用（winrate_evidence_ref，含材料哈希与 unknown 兼容性）、
    数据引用（数据日=run_date，发布节奏未核实→health=unknown）；
    input_hash=完整卡片内容摘要（不再是 "unknown"）。
    """
    from lei_signal.data_provenance import (
        MarketDataRef,
        ruleset_ref,
        winrate_evidence_ref,
    )

    payload = card.model_dump()
    payload_json = _canonical(payload)
    input_hash = _sha256(payload_json)
    ruleset = ruleset_ref().to_dict()
    items = []
    for it in payload.get("items", []):
        data_ref = MarketDataRef(
            source_id="copilot/recommend.py+scan",  # 判定层产出（当日扫描表）
            instrument_id=it["symbol"], market="cn",
            observed_at=card.run_date, available_at=card.run_date,
            generated_at=card.run_date, last_valid_at=card.run_date,
            health="unknown",  # 扫描表发布节奏未核实（01D 后登记）
            reason="当日扫描表数据日=run_date；发布节奏未核实",
        ).to_dict()
        items.append(ObservationItem(
            instrument_id=it["symbol"],
            payload={"symbol": it["symbol"], "verdict": it["verdict"],
                     "display_name": it.get("display_name", ""),
                     "score": it.get("score", 0.0),
                     "reasons": it.get("reasons", [])},
            claim=f"今日推荐观察：{it['symbol']}（{it.get('verdict_cn') or it['verdict']}）",
            direction=None,
            horizons=(1, 5, 20),
            scope="a_share_etf",
            strategy="技术观察",
            claim_class="recommendation_watch",
            rule_refs=["docs/trading-spec-v1.md"],
            evidence_refs=["docs/experiments/module_winrate.json"],
            available_at=card.run_date,   # 数据日（不猜时刻）
            rule_refs_frozen=[ruleset],
            evidence_refs_frozen=[winrate_evidence_ref(it["symbol"]).to_dict()],
            data_refs_frozen=[data_ref],
        ))
    return record_observations(
        conn,
        source_type="recommendation",
        source_record_id=card.run_date,
        observed_at=card.run_date,
        evaluation_kind=KIND_TECHNICAL_FORWARD,
        evaluation_version=RECOMMENDATION_EVAL_VERSION,
        items=items,
        batch_payload=payload,  # 完整卡片原文（含总体说明），批次留档
        input_hash=input_hash,
    )


def _sentiment_frozen_refs(claim_class: str, code: str, date: str):
    """冰点/强热主张的冻结引用（P7）：规则条目 + 证据条目（含材料哈希）+ 数据引用。

    规则与证据按 claim_class 取 icepoint_pick / heat_alarm 条目；材料哈希在
    写入时冻结（configs/sentiment_evidence.json 更新后旧记录不回写）。
    """
    from pathlib import Path

    from lei_signal.data_provenance import (
        MarketDataRef,
        evidence_ref,
        rule_ref,
    )

    key = "icepoint_pick" if "icepoint" in claim_class else (
        "heat_alarm" if "heat" in claim_class else None)
    rule_frozen = [rule_ref(key).to_dict()] if key else []
    evidence_frozen: list[dict] = []
    if key:
        ledger = Path(__file__).resolve().parents[3] / "configs" / "sentiment_evidence.json"
        try:
            entry = (json.loads(ledger.read_text(encoding="utf-8"))
                     .get("signals", {}).get(key))
        except (OSError, json.JSONDecodeError):
            entry = None
        if entry is not None:
            evidence_frozen = [evidence_ref(
                key, entry, source_paths=[str(ledger)]).to_dict()]
    data_ref = MarketDataRef(
        source_id="sector_trend_snapshot.json",
        instrument_id=code, market="cn",
        observed_at=date, available_at=None,  # 快照发布节奏未核实
        generated_at=None, last_valid_at=date,
        health="unknown", reason="快照数据日=交易日；发布节奏未核实",
    ).to_dict()
    return rule_frozen, evidence_frozen, [data_ref]


def record_sentiment_day(
    conn: sqlite3.Connection,
    *,
    date: str,
    picks: Sequence[dict],
    alarms: Sequence[dict],
    emitted_at: str | None = None,
    legacy: bool = False,
    revision_key: str | None = None,
    input_hash: str | None = None,
    available_at: str | None = None,
) -> dict[str, int]:
    """情绪日快照 → 展示批次（完整 picks/alarms）+ 主张（冰点=涨/强热=跌）。

    零触发日落组级标记（无期限、不进分母）；legacy=True 标历史迁入，
    不与上线后真实前向样本合并。P5/P7：revision_key=来源 JSON 的稳定修订键
    （旧版重试不夺当前、重跑不增批次）；input_hash/available_at 透传冻结。
    """
    items: list[ObservationItem] = []
    for p in picks:
        rf, ef, df = _sentiment_frozen_refs("icepoint_pick", p["code"], date)
        items.append(ObservationItem(
            instrument_id=p["code"], payload=p,
            claim=f"冰点机会（看涨观察）：{p.get('name', p['code'])}",
            direction="up", horizons=(10, 20),
            scope="cn_sector", strategy="情绪观察",
            claim_class="icepoint_pick",
            rule_refs=["docs/experiments/retail-sentiment-ts-2026-09-05.md"],
            evidence_refs=["configs/sentiment_evidence.json"],
            available_at=available_at,
            rule_refs_frozen=rf, evidence_refs_frozen=ef, data_refs_frozen=df,
        ))
    for a in alarms:
        rf, ef, df = _sentiment_frozen_refs("heat_alarm", a["code"], date)
        items.append(ObservationItem(
            instrument_id=a["code"], payload=a,
            claim=f"强热警报（看跌观察，条件版）：{a.get('name', a['code'])}",
            direction="down", horizons=(10, 20),
            scope="cn_sector", strategy="情绪观察",
            claim_class="heat_alarm",
            rule_refs=["docs/experiments/retail-sentiment-ts-2026-09-05.md"],
            evidence_refs=["configs/sentiment_evidence.json"],
            available_at=available_at,
            rule_refs_frozen=rf, evidence_refs_frozen=ef, data_refs_frozen=df,
        ))
    if not picks and not alarms:
        items.append(ObservationItem(
            instrument_id=None,
            payload={"date": date, "picks": 0, "alarms": 0},
            claim="当日无触发（零触发日）",
            direction=None, horizons=(),
            scope="cn_sector", strategy="情绪观察",
            claim_class="zero_trigger_day",
            available_at=available_at,
        ))
    return record_observations(
        conn,
        source_type="sentiment_day",
        source_record_id=date,
        observed_at=date,
        emitted_at=emitted_at,
        evaluation_kind=KIND_SENTIMENT_DIRECTION,
        evaluation_version=SENTIMENT_EVAL_VERSION,
        items=items,
        batch_payload={"picks": list(picks), "alarms": list(alarms), "date": date},
        legacy=legacy,
        revision_key=revision_key,
        input_hash=input_hash or "unknown",
    )


# ---------------------------------------------------------------------------
# 2) 到期检查（严格日历版 + 行参考版；显式三键；缺数据可恢复）
# ---------------------------------------------------------------------------


def _frame_pairs(frame) -> list[tuple[str, float]] | None:
    """行情帧 → 按日期排序的 (date, close)；重复日期保留后者。

    坏值（NaN/非正/非数）**保留在原日期位**：命中坏值按 missing_data 处理，
    不静默丢弃该行导致行偏移跳到下一天（R06：坏值不冒充有效数据）。
    形态异常（无 close/索引不可解析）返回 None。
    """
    import pandas as pd

    try:
        dates = pd.to_datetime(frame.index).date.tolist()
        closes = frame["close"].astype(float).tolist()
    except (KeyError, TypeError, ValueError):
        return None
    merged: dict[str, float] = {}
    for d, c in zip(dates, closes, strict=False):
        try:
            merged[d.isoformat()] = float(c)
        except (TypeError, ValueError, AttributeError):
            continue
    return sorted(merged.items())


def _price_at(pairs: list[tuple[str, float]], date: str) -> float | None:
    """精确日期的收盘价；该日无行或值无效（NaN/非正）返回 None（不跳行）。"""
    for d, c in pairs:
        if d == date:
            return c if _finite_positive(c) else None
    return None


def _base_price(pairs: list[tuple[str, float]], observed_at: str) -> float | None:
    """起算价：观察交易日当日的收盘（缺行=None，不用其他日期冒充）。"""
    return _price_at(pairs, observed_at)


def _fill_ready(
    conn: sqlite3.Connection,
    observation_id: str,
    evaluation_version: str,
    horizon: int,
    *,
    base_price: float | None,
    eval_date: str | None,
    eval_price: float | None,
    change_pct: float | None,
    hit: int | None,
    baseline_change: float | None = None,
    evaluation_kind: str = "",
) -> None:
    """ready 写入：显式三键定位，只动本版本行（v1.2 §4）。"""
    conn.execute(
        """
        UPDATE agent_observation_outcomes
        SET status = 'ready', base_price = ?, due_date = COALESCE(due_date, ?),
            eval_date = COALESCE(eval_date, ?), eval_price = ?,
            change_pct = ?, baseline_change_pct = ?,
            hit = ?, evaluated_at = ?
        WHERE observation_id = ? AND evaluation_version = ? AND horizon = ?
          AND status IN ('pending', 'missing_data')
        """,
        (base_price, eval_date, eval_date, eval_price, change_pct,
         baseline_change, hit, _now(),
         observation_id, evaluation_version, horizon),
    )


def _set_status(
    conn: sqlite3.Connection,
    observation_id: str,
    evaluation_version: str,
    horizon: int,
    status: str,
    *,
    note: str = "",
) -> None:
    conn.execute(
        """
        UPDATE agent_observation_outcomes SET status = ?, note = ?, evaluated_at = ?
        WHERE observation_id = ? AND evaluation_version = ? AND horizon = ?
          AND status IN ('pending', 'missing_data')
        """,
        (status, note, _now(), observation_id, evaluation_version, horizon),
    )


def _pending_rows(
    conn: sqlite3.Connection,
    *,
    source_type: str | None,
    evaluation_version: str,
    with_instrument: bool = True,
) -> list[sqlite3.Row]:
    """待评价行（pending + missing_data 均可重试；无 60 天停止）。"""
    sql = (
        "SELECT o.observation_id, o.instrument_id, o.observed_at, o.direction, "
        "       o.payload, o.evaluation_kind AS claim_kind, o.display_status, "
        "       oc.horizon, oc.evaluation_kind AS outcome_kind "
        "FROM agent_observations o "
        "JOIN agent_observation_outcomes oc ON oc.observation_id = o.observation_id "
        "WHERE o.record_type = 'claim' AND oc.evaluation_version = ? "
        "AND oc.status IN ('pending', 'missing_data') "
        "AND o.display_status != 'not_shown'"  # P3：未展示不进评价
    )
    args: list[Any] = [evaluation_version]
    if source_type:
        sql += " AND o.source_type = ?"
        args.append(source_type)
    if with_instrument:
        sql += " AND o.instrument_id IS NOT NULL"
    return conn.execute(sql, args).fetchall()


def _hit_of(direction: str | None, change_pct: float) -> int | None:
    if direction == "up":
        return 1 if change_pct > 0 else 0
    if direction == "down":
        return 1 if change_pct < 0 else 0
    return None


def evaluate_recommendation_outcomes(
    conn: sqlite3.Connection,
    service,
    *,
    horizons: tuple[int, ...] = (1, 5, 20),
    today: str | None = None,
    as_of: str | None = None,
    calendar: CalendarAdapter | None = None,
    market: str = "cn",
) -> dict[str, int]:
    """给推荐观察补 T+N 结果。

    两个口径分别落各自版本（不相加、不互填）：
    - 行参考版（RECOMMENDATION_ROWS_VERSION）：按可用行情行偏移，
      受 as_of/today 截止约束，坏值隔离，missing_data 可恢复；
    - 严格版（RECOMMENDATION_EVAL_VERSION）：需要可信日历适配器；
      日历不明不产生 ready（保持 pending）。
    """
    today = as_of or today or datetime.now(UTC).date().isoformat()
    strict = 0
    reference = 0
    # ---- 行参考版 ----
    frames: dict[str, list[tuple[str, float]] | None] = {}
    for r in _pending_rows(conn, source_type="recommendation",
                           evaluation_version=RECOMMENDATION_ROWS_VERSION):
        sym = r["instrument_id"]
        if sym not in frames:
            try:
                entry = service.get(sym)
                res = getattr(entry, "result", None)
                frames[sym] = _frame_pairs(res.frame) if res is not None else None
            except Exception:  # noqa: BLE001  单标的坏数据隔离，不阻断其余
                frames[sym] = None
        pairs = frames[sym]
        if pairs is None or not pairs:
            _set_status(conn, r["observation_id"], RECOMMENDATION_ROWS_VERSION,
                        r["horizon"], "missing_data", note="无有效行情行")
            continue
        base = _base_price(pairs, r["observed_at"])
        if base is None:
            _set_status(conn, r["observation_id"], RECOMMENDATION_ROWS_VERSION,
                        r["horizon"], "missing_data", note="观察日无收盘价")
            continue
        # 行偏移目标：观察日在序列中的位置 + N（as_of 之后的行不可用）
        import bisect

        keys = [d for d, _ in pairs]
        i = bisect.bisect_right(keys, r["observed_at"]) - 1
        if i < 0:
            _set_status(conn, r["observation_id"], RECOMMENDATION_ROWS_VERSION,
                        r["horizon"], "missing_data", note="观察日早于全部行情")
            continue
        j = i + r["horizon"]
        if j >= len(pairs) or pairs[j][0] > today:
            continue  # 未到期（或晚于截止）→ 保持 pending
        eval_date, eval_price = pairs[j]
        if not _finite_positive(eval_price):
            _set_status(conn, r["observation_id"], RECOMMENDATION_ROWS_VERSION,
                        r["horizon"], "missing_data", note="评价日价格无效")
            continue
        chg = round((eval_price / base - 1.0) * 100.0, 2)
        _fill_ready(conn, r["observation_id"], RECOMMENDATION_ROWS_VERSION,
                    r["horizon"], base_price=base, eval_date=eval_date,
                    eval_price=eval_price, change_pct=chg, hit=None)
        reference += 1

    # ---- 严格版（可信日历） ----
    if calendar is not None:
        for r in _pending_rows(conn, source_type="recommendation",
                               evaluation_version=RECOMMENDATION_EVAL_VERSION):
            pairs = frames.get(r["instrument_id"])
            if pairs is None and r["instrument_id"] not in frames:
                try:
                    entry = service.get(r["instrument_id"])
                    res = getattr(entry, "result", None)
                    pairs = _frame_pairs(res.frame) if res is not None else None
                except Exception:  # noqa: BLE001
                    pairs = None
                frames[r["instrument_id"]] = pairs
            if pairs is None:
                _set_status(conn, r["observation_id"], RECOMMENDATION_EVAL_VERSION,
                            r["horizon"], "missing_data", note="无有效行情行")
                continue
            base = _base_price(pairs, r["observed_at"])
            if base is None:
                _set_status(conn, r["observation_id"], RECOMMENDATION_EVAL_VERSION,
                            r["horizon"], "missing_data", note="观察日无收盘价")
                continue
            target = calendar(market, r["observed_at"], r["horizon"])
            if target is None:
                continue  # 日历不明/未到期 → pending，不伪造
            if target > today:
                continue
            price = _price_at(pairs, target)
            if price is None:
                _set_status(conn, r["observation_id"], RECOMMENDATION_EVAL_VERSION,
                            r["horizon"], "missing_data",
                            note=f"目标交易日 {target} 缺价（不按下一行补位）")
                continue
            chg = round((price / base - 1.0) * 100.0, 2)
            _fill_ready(conn, r["observation_id"], RECOMMENDATION_EVAL_VERSION,
                        r["horizon"], base_price=base, eval_date=target,
                        eval_price=price, change_pct=chg, hit=None)
            strict += 1
    return {"ready_rows_reference": reference, "ready_rows_strict": strict,
            "checked_versions": 2 if calendar else 1}


def evaluate_sentiment_outcomes(
    conn: sqlite3.Connection,
    close_lookup: Callable[[str, str, int], tuple[str, float] | None],
    *,
    today: str | None = None,
    as_of: str | None = None,
    calendar: CalendarAdapter | None = None,
    price_at: Callable[[str, str], float | None] | None = None,
    market: str = "cn",
) -> dict[str, int]:
    """给情绪观察补 T+N 结果（行参考版 + 可选严格日历版）。

    close_lookup(code, observed_at, n) 为行参考查询（板块趋势历史）；
    price_at(code, exact_date) 为严格版精确日期查询。基价用存证记录的
    信号日收盘（payload.close），不用今天的快照倒推。
    """
    today = as_of or today or datetime.now(UTC).date().isoformat()
    reference = strict = 0
    for r in _pending_rows(conn, source_type="sentiment_day",
                           evaluation_version=SENTIMENT_ROWS_VERSION):
        try:
            payload = json.loads(r["payload"])
        except (TypeError, ValueError):
            payload = {}
        base = _to_finite_positive(payload.get("close"))
        if base is None:
            _set_status(conn, r["observation_id"], SENTIMENT_ROWS_VERSION,
                        r["horizon"], "missing_data", note="存证基价无效")
            continue
        try:  # P9：单对象行情查询异常只隔离它自己，不阻断后续对象
            found = close_lookup(r["instrument_id"], r["observed_at"], r["horizon"])
        except Exception as exc:  # noqa: BLE001
            _set_status(conn, r["observation_id"], SENTIMENT_ROWS_VERSION,
                        r["horizon"], "missing_data",
                        note=f"行情查询异常：{exc}")
            continue
        if found is None:
            continue  # 未到期或该板块缺价 → pending，等数据（可恢复）
        eval_date, eval_close = found
        eval_f = _to_finite_positive(eval_close)
        if eval_date > today:
            continue
        if eval_f is None:
            _set_status(conn, r["observation_id"], SENTIMENT_ROWS_VERSION,
                        r["horizon"], "missing_data", note="评价日价格无效")
            continue
        chg = round((eval_f / base - 1.0) * 100.0, 2)
        _fill_ready(conn, r["observation_id"], SENTIMENT_ROWS_VERSION,
                    r["horizon"], base_price=base, eval_date=eval_date,
                    eval_price=eval_f, change_pct=chg,
                    hit=_hit_of(r["direction"], chg))
        reference += 1

    if calendar is not None and price_at is not None:
        for r in _pending_rows(conn, source_type="sentiment_day",
                               evaluation_version=SENTIMENT_EVAL_VERSION):
            try:
                payload = json.loads(r["payload"])
            except (TypeError, ValueError):
                payload = {}
            base = _to_finite_positive(payload.get("close"))
            if base is None:
                _set_status(conn, r["observation_id"], SENTIMENT_EVAL_VERSION,
                            r["horizon"], "missing_data", note="存证基价无效")
                continue
            target = calendar(market, r["observed_at"], r["horizon"])
            if target is None or target > today:
                continue
            try:  # P9：单对象异常隔离
                price = _to_finite_positive(price_at(r["instrument_id"], target))
            except Exception as exc:  # noqa: BLE001
                _set_status(conn, r["observation_id"], SENTIMENT_EVAL_VERSION,
                            r["horizon"], "missing_data",
                            note=f"行情查询异常：{exc}")
                continue
            if price is None:
                _set_status(conn, r["observation_id"], SENTIMENT_EVAL_VERSION,
                            r["horizon"], "missing_data",
                            note=f"目标交易日 {target} 缺价（不按下一行补位）")
                continue
            chg = round((price / base - 1.0) * 100.0, 2)
            _fill_ready(conn, r["observation_id"], SENTIMENT_EVAL_VERSION,
                        r["horizon"], base_price=base, eval_date=target,
                        eval_price=price, change_pct=chg,
                        hit=_hit_of(r["direction"], chg))
            strict += 1
    return {"ready_rows_reference": reference, "ready_rows_strict": strict,
            "checked_versions": 2 if calendar else 1}


# ---------------------------------------------------------------------------
# 3) 只读汇总（§4：分组维度齐全；展示数/样本数分列；冲突可见；无总胜率）
# ---------------------------------------------------------------------------

STATUS_CN = {
    "pending": "待到期",
    "ready": "已评价",
    "missing_data": "缺数据",
    "not_applicable": "不可评价",
}


def summarize(
    conn: sqlite3.Connection,
    *,
    source_type: str | None = None,
    instrument: str | None = None,
) -> dict:
    """分桶汇总。旧版结果按 evaluation_version 单列（不与重算版相加）。

    每桶：n_observations（展示记录数）/ n_samples（去重样本数）分列；
    同 sample_key 的 ready 结果数值冲突 → conflict 计数并从比例中排除；
    命中率只用有效 ready 样本；未评价不进分母。无跨桶总胜率、无总样本。
    independent_event_count 无冻结历史事件划分时为 None（未知）。
    """
    sql = (
        "SELECT o.source_type, o.strategy, o.direction, "
        "       o.evaluation_kind AS claim_kind, o.legacy_quality, o.sample_key, "
        "       o.rule_refs, o.eval_config_hash, o.observation_id, "
        "       oc.evaluation_version, oc.evaluation_kind AS outcome_kind, "
        "       oc.horizon, oc.status, oc.change_pct, oc.hit, oc.eval_date, "
        "       oc.baseline_change_pct "
        "FROM agent_observations o "
        "JOIN agent_observation_outcomes oc ON oc.observation_id = o.observation_id "
        "WHERE o.record_type = 'claim' AND o.display_status != 'not_shown'"
    )
    args: list[Any] = []
    if source_type:
        sql += " AND o.source_type = ?"
        args.append(source_type)
    if instrument:
        sql += " AND o.instrument_id = ?"
        args.append(instrument)
    rows = conn.execute(sql, args).fetchall()

    groups: dict[tuple, dict] = {}
    for r in rows:
        key = (
            r["source_type"], r["strategy"], r["direction"],
            r["outcome_kind"] or r["claim_kind"],
            r["evaluation_version"], r["horizon"],
            r["legacy_quality"] or "ok",
            # P4：规则与评价配置不同 = 不同组（不合并）
            r["rule_refs"] or "[]", r["eval_config_hash"] or "",
        )
        g = groups.setdefault(key, {"rows": []})
        g["rows"].append(r)

    buckets = []
    for (src, strategy, direction, kind, version, horizon, quality,
         rule_refs_json, cfg_hash), g in sorted(
        groups.items(), key=lambda kv: (kv[0][0], kv[0][4], kv[0][5] or 0)
    ):
        rows = g["rows"]
        ready = [r for r in rows if r["status"] == "ready"]
        # 样本去重：同 sample_key 只算一个样本；ready 数值冲突 → conflict 排除。
        # 023 旧记录无 sample_key → 按 observation_id 逐条隔离（标 unknown），
        # 不按 evaluation_version 压成一个样本。
        by_sample: dict[str, list] = {}
        for r in rows:
            sk = r["sample_key"] or r["observation_id"]
            by_sample.setdefault(sk, []).append(r)
        n_samples = len(by_sample)
        conflicts = 0
        valid_ready: list = []
        for _sk, rs in by_sample.items():
            ready_rs = [x for x in rs if x["status"] == "ready"]
            if not ready_rs:
                continue
            changes = {x["change_pct"] for x in ready_rs}
            if len(changes) > 1:
                conflicts += 1
                continue
            valid_ready.append(ready_rs[0])
        try:
            rule_list = json.loads(rule_refs_json) if rule_refs_json else []
        except (TypeError, ValueError):
            rule_list = []
        bucket = {
            "source_type": src,
            "strategy": strategy,
            "evaluation_kind": KIND_COMPAT.get(kind, kind),
            "evaluation_kind_stored": kind,
            "evaluation_version": version,
            "is_reference_version": version in REFERENCE_VERSIONS,
            "direction": direction,
            "horizon_days": horizon,
            "legacy_quality": quality,
            "rule_refs": rule_list,
            "eval_config_hash": cfg_hash or None,
            "n_observations": len(rows),
            "n_samples": n_samples,
            "n_ready_observations": len(ready),
            "n_ready_samples": len(valid_ready),
            "n_pending": sum(1 for r in rows if r["status"] == "pending"),
            "n_missing": sum(1 for r in rows if r["status"] == "missing_data"),
            "n_not_applicable": sum(1 for r in rows if r["status"] == "not_applicable"),
            "n_conflict_samples": conflicts,
            "avg_change_pct": (
                round(sum(r["change_pct"] for r in valid_ready) / len(valid_ready), 2)
                if valid_ready else None),
            "min_change_pct": min((r["change_pct"] for r in valid_ready), default=None),
            "max_change_pct": max((r["change_pct"] for r in valid_ready), default=None),
            "first_eval_date": min(
                (r["eval_date"] for r in valid_ready if r["eval_date"]), default=None),
            "last_eval_date": max(
                (r["eval_date"] for r in valid_ready if r["eval_date"]), default=None),
            "has_baseline": any(r["baseline_change_pct"] is not None for r in valid_ready),
        }
        if direction and valid_ready:
            hits = sum(r["hit"] or 0 for r in valid_ready if r["hit"] is not None)
            bucket["n_hit_samples"] = hits
            bucket["hit_rate_pct"] = round(100.0 * hits / len(valid_ready), 1)
        buckets.append(bucket)

    # 零触发日 / 批次数 / 当前对象数（按来源分组；P8：COUNT 真正 GROUP BY；
    # instrument 过滤在当前数量上与桶/recent 一致）
    zero_sql = ("SELECT source_type, COUNT(*) AS n FROM agent_observations "
                "WHERE record_type = 'claim' AND instrument_id IS NULL "
                "AND json_extract(payload, '$.picks') = 0 "
                "AND json_extract(payload, '$.alarms') = 0")
    batch_sql = ("SELECT source_type, COUNT(*) AS n FROM agent_observations "
                 "WHERE record_type = 'display_batch'")
    cond = ""
    z_args: list[Any] = []
    if source_type:
        cond = " AND source_type = ?"
        z_args.append(source_type)
    zero = {r["source_type"]: r["n"] for r in conn.execute(
        zero_sql + cond + " GROUP BY source_type", z_args).fetchall()}
    batch_counts = {r["source_type"]: r["n"] for r in conn.execute(
        batch_sql + cond + " GROUP BY source_type", z_args).fetchall()}
    current_ids = current_claim_ids(conn, source_type=source_type)
    current_by_source: dict[str, int] = {}
    if current_ids:
        marks = ",".join("?" * len(current_ids))
        cur_args: list[Any] = list(sorted(current_ids))
        cur_sql = (f"SELECT source_type, COUNT(*) AS n FROM agent_observations "
                   f"WHERE observation_id IN ({marks}) AND display_status != 'not_shown'")
        if instrument:
            cur_sql += " AND instrument_id = ?"
            cur_args.append(instrument)
        for r in conn.execute(cur_sql + " GROUP BY source_type", cur_args).fetchall():
            current_by_source[r["source_type"]] = r["n"]
    not_shown = {r["source_type"]: r["n"] for r in conn.execute(
        "SELECT source_type, COUNT(*) AS n FROM agent_observations "
        "WHERE display_status = 'not_shown' AND record_type = 'claim'"
        + cond + " GROUP BY source_type", z_args).fetchall()}
    return {
        "schema_version": SCHEMA_VERSION,
        "buckets": buckets,
        "display_batches": batch_counts,
        "zero_trigger_days": zero,
        "current_observations": current_by_source,
        "not_shown_observations": not_shown,
        "n_superseded_batches": conn.execute(
            "SELECT COUNT(*) AS n FROM agent_observations "
            "WHERE record_type = 'display_batch' AND superseded_by IS NOT NULL"
            + (" AND source_type = ?" if source_type else ""),
            args[:1] if source_type else [],
        ).fetchone()["n"],
        # 展示批次ID不是独立恐慌事件ID；无冻结的历史事件划分 → 未知
        "independent_event_count": None,
        "independent_event_note": "无冻结的历史事件划分依据，独立事件数未知；"
                                  "不拿板块/日期数量冒充独立事件。",
        "status_cn": STATUS_CN,
        "note_cn": "分桶统计，不同种类/版本/口径各自单独计数不合并总胜率；"
                   "展示记录数(n_observations)与研究样本数(n_samples)分列，"
                   "同一事件改措辞不多算样本；参考口径(按行情行数)与严格口径"
                   "(交易日历)分版本单列；无基准只报绝对涨跌不标超额；"
                   "未评价(待到期)与缺数据不进命中率分母。",
    }


def recent_observations(
    conn: sqlite3.Connection, *, limit: int = 50, source_type: str | None = None,
    instrument: str | None = None,
) -> list[dict]:
    """最近展示记录（批次与主张都返回，含修订链与原话），供查询卡片用。

    instrument 过滤与 summarize 口径一致（查单标的不串其他对象）。
    outcomes 为结构化分版本结果（严格/参考口径、状态与数值分列），
    不再拼无版本说明的单串。
    """
    where = "WHERE 1=1"
    args: list[Any] = []
    if source_type:
        where += " AND o.source_type = ?"
        args.append(source_type)
    if instrument:
        where += " AND o.instrument_id = ?"
        args.append(instrument)
    rows = conn.execute(
        f"""
        SELECT o.observation_id, o.source_type, o.source_record_id, o.instrument_id,
               o.claim, o.direction, o.observed_at, o.emitted_at, o.legacy,
               o.record_type, o.batch_members, o.superseded_by, o.legacy_quality,
               o.display_status, o.payload, o.first_shown_at
        FROM agent_observations o
        {where}
        ORDER BY o.created_at DESC LIMIT ?
        """,
        (*args, limit),
    ).fetchall()
    out = []
    for r in rows:
        try:
            payload = json.loads(r["payload"])
        except (TypeError, ValueError):
            payload = {}
        outcomes = [
            {
                "evaluation_version": oc["evaluation_version"],
                "is_reference_version": oc["evaluation_version"] in REFERENCE_VERSIONS,
                "horizon": oc["horizon"],
                "status": oc["status"],
                "status_cn": STATUS_CN.get(oc["status"], oc["status"]),
                "change_pct": oc["change_pct"],
                "eval_date": oc["eval_date"],
            }
            for oc in conn.execute(
                "SELECT evaluation_version, horizon, status, change_pct, eval_date "
                "FROM agent_observation_outcomes WHERE observation_id = ? "
                "ORDER BY evaluation_version, horizon",
                (r["observation_id"],),
            ).fetchall()
        ]
        out.append({
            "observation_id": r["observation_id"],
            "source_type": r["source_type"],
            "source_record_id": r["source_record_id"],
            "instrument_id": r["instrument_id"],
            "claim": r["claim"],
            "direction": r["direction"],
            "observed_at": r["observed_at"],
            "emitted_at": r["emitted_at"],
            "legacy": bool(r["legacy"]),
            "record_type": r["record_type"],
            "batch_members": json.loads(r["batch_members"]) if r["batch_members"] else [],
            "superseded": bool(r["superseded_by"]),
            "legacy_quality": r["legacy_quality"] or "ok",
            "display_status": r["display_status"],
            "first_shown_at": r["first_shown_at"],
            "payload": payload,
            "outcomes": outcomes,
        })
    return out


# ---------------------------------------------------------------------------
# 4) 旧库迁入：只读 preview（§6；正式迁入待总控批准，不自动执行）
# ---------------------------------------------------------------------------


def backfill_preview(conn: sqlite3.Connection) -> dict:
    """迁入预览（只读、不写库）：拟迁条数、同日修订、卡片/成绩不一致、
    无法考证关联、迁入后各组计数。供总控核对后再决定一次性迁入。

    联合收尾（2026-09-08）：归属核对加 hash 维度——outcome_payload_hash 与
    当前 payload_hash 不等=成绩属于旧版卡片（不迁挂）；hash 缺失=归属不可考
    （同标的同日期不足以证明成绩属于当前卡片，同样不迁挂，标 unknown）。
    """
    rows = conn.execute(
        "SELECT run_date, payload, outcome, created_at, payload_hash, "
        "outcome_payload_hash FROM recommendation_journal ORDER BY run_date"
    ).fetchall()
    to_migrate = same_day_revisions = card_outcome_mismatch = unattributable = 0
    hash_match = hash_mismatch = hash_missing = 0
    mismatch_samples: list[dict] = []
    for r in rows:
        try:
            payload = json.loads(r["payload"])
        except (TypeError, ValueError):
            unattributable += 1
            continue
        items = payload.get("items", [])
        if isinstance(items, list) and items:
            to_migrate += 1
        try:
            outcome = json.loads(r["outcome"]) if r["outcome"] else {}
        except (TypeError, ValueError):
            outcome = {}
        symbols = {it.get("symbol") for it in items if isinstance(it, dict)}
        for sym, _chgs in outcome.items():
            if sym not in symbols:
                card_outcome_mismatch += 1
                if len(mismatch_samples) < 10:
                    mismatch_samples.append({"run_date": r["run_date"], "symbol": sym})
                break
        # hash 归属核对（v1.2 §6：不能只凭同标的同日期认定）
        # 缺失=024 前旧行（未被替换过，对应成立可迁挂）；不符=旧卡成绩不迁挂
        if outcome:
            if r["outcome_payload_hash"] is not None:
                if r["outcome_payload_hash"] == r["payload_hash"]:
                    hash_match += 1
                else:
                    hash_mismatch += 1
            else:
                hash_missing += 1
    # recommendation_journal_history 里的同日旧版本
    same_day_revisions = conn.execute(
        "SELECT COUNT(*) AS n FROM recommendation_journal_history"
    ).fetchone()["n"]
    already = conn.execute(
        "SELECT COUNT(*) AS n FROM agent_observations "
        "WHERE source_type='recommendation' AND legacy_quality='legacy'"
    ).fetchone()["n"]
    return {
        "journal_rows": len(rows),
        "rows_with_items": to_migrate,
        "legacy_claims_already_migrated": already,
        "same_day_revisions_in_history": same_day_revisions,
        "card_outcome_mismatch_rows": card_outcome_mismatch,
        "unattributable_payload_rows": unattributable,
        "outcome_hash_match_rows": hash_match,
        "outcome_hash_mismatch_rows": hash_mismatch,
        "outcome_hash_missing_rows": hash_missing,
        "mismatch_samples": mismatch_samples,
        "note_cn": "只读预览，未写入任何数据。成绩符号不在卡片内、或成绩"
                   "hash 与当前卡片不符的行不迁挂（同标的同日期不足以证明"
                   "归属，标 unknown 隔离）；hash 缺失=024 前旧行未被替换过，"
                   "按旧绑定语义迁挂为 legacy；正式迁入需总控批准后带备份执行一次。",
    }


def backfill_from_recommendation_journal(conn: sqlite3.Connection) -> dict[str, int]:
    """旧推荐账本 → 观察账本（幂等）。**仅供总控批准后的一次性迁入使用**，
    日常跑批不调用；迁入前先跑 backfill_preview 核对。

    - payload 可恢复 → 批次存完整原文，主张标 legacy_quality='legacy'；
    - 旧 outcome JSON 的 chg_{h}d → LEGACY_EVAL_VERSION ready 行（只带带符号
      涨跌）；成绩符号不在该卡 items 内 → 不挂（unknown 隔离，preview 可见）；
    - 不删除/不修改 recommendation_journal 与 history 原表。
    """
    rows = conn.execute(
        "SELECT run_date, payload, outcome, created_at FROM recommendation_journal "
        "ORDER BY run_date"
    ).fetchall()
    inserted = outcomes = skipped_mismatch = 0
    for r in rows:
        try:
            payload = json.loads(r["payload"])
        except (TypeError, ValueError):
            skipped_mismatch += 1
            continue
        run_date = r["run_date"]
        items = [
            ObservationItem(
                instrument_id=it.get("symbol"),
                payload={k: it.get(k) for k in
                         ("symbol", "verdict", "display_name", "score", "reasons")},
                claim=f"今日推荐观察：{it.get('symbol', '?')}",
                direction=None,
                horizons=(1, 5, 20),
                scope="a_share_etf",
                strategy="技术观察",
                claim_class="recommendation_watch",
                rule_refs=["docs/trading-spec-v1.md"],
                evidence_refs=["docs/experiments/module_winrate.json"],
            )
            for it in payload.get("items", []) if isinstance(it, dict)
        ]
        stats = record_observations(
            conn,
            source_type="recommendation",
            source_record_id=run_date,
            observed_at=run_date,
            emitted_at=r["created_at"] or "unknown",
            evaluation_kind=KIND_TECHNICAL_FORWARD,
            evaluation_version=RECOMMENDATION_EVAL_VERSION,
            items=items,
            batch_payload=payload,
            input_hash="unknown",
            legacy=True,
        )
        inserted += stats["claims_inserted"]
        try:
            old_out = json.loads(r["outcome"]) if r["outcome"] else {}
        except (TypeError, ValueError):
            old_out = {}
        # 归属核对（联合收尾，v1.2 §6）：outcome_payload_hash 缺失=024 前旧行
        # 未被替换过——成绩按存储 payload 打分，对应关系成立，可迁挂（legacy）；
        # hash 不符=成绩属于旧版卡片，不硬挂新卡（原值经 history 表保全可查）。
        row_hashes = conn.execute(
            "SELECT payload_hash, outcome_payload_hash "
            "FROM recommendation_journal WHERE run_date = ?", (run_date,)
        ).fetchone()
        outcome_attributable = (
            row_hashes is not None
            and (row_hashes["outcome_payload_hash"] is None
                 or row_hashes["outcome_payload_hash"] == row_hashes["payload_hash"])
        )
        if old_out and not outcome_attributable:
            skipped_mismatch += 1
            old_out = {}
        symbols = {it.instrument_id for it in items}
        for sym, chgs in old_out.items():
            if sym not in symbols:
                skipped_mismatch += 1
                continue
            obs_id = conn.execute(
                "SELECT observation_id FROM agent_observations "
                "WHERE source_type='recommendation' AND source_record_id=? "
                "AND instrument_id=? AND legacy_quality='legacy' LIMIT 1",
                (run_date, sym),
            ).fetchone()
            if obs_id is None:
                continue
            for key, val in chgs.items():
                if not (key.startswith("chg_") and key.endswith("d")):
                    continue
                try:
                    h = int(key[4:-1])
                except ValueError:
                    continue
                exists = conn.execute(
                    "SELECT 1 FROM agent_observation_outcomes "
                    "WHERE observation_id=? AND evaluation_version=? AND horizon=?",
                    (obs_id["observation_id"], LEGACY_EVAL_VERSION, h),
                ).fetchone()
                if exists is None:
                    conn.execute(
                        "INSERT INTO agent_observation_outcomes "
                        "(observation_id, evaluation_version, horizon, status, "
                        " change_pct, evaluated_at) VALUES (?,?,?, 'ready', ?, ?)",
                        (obs_id["observation_id"], LEGACY_EVAL_VERSION, h,
                         float(val), _now()),
                    )
                    outcomes += 1
    return {"claims_inserted": inserted, "legacy_outcomes": outcomes,
            "skipped_unattributable": skipped_mismatch}


__all__ = [
    "SCHEMA_VERSION",
    "KIND_TECHNICAL_FORWARD", "KIND_SENTIMENT_DIRECTION", "KIND_DISCUSSION_CLAIM",
    "KIND_PLAN_RULE_FOLLOWUP", "KIND_NON_EVALUABLE", "KIND_COMPAT",
    "RECOMMENDATION_EVAL_VERSION", "RECOMMENDATION_ROWS_VERSION",
    "SENTIMENT_EVAL_VERSION", "SENTIMENT_ROWS_VERSION", "LEGACY_EVAL_VERSION",
    "REFERENCE_VERSIONS", "STATUS_CN",
    "CalendarAdapter", "dict_calendar",
    "ObservationItem",
    "record_observations", "record_recommendation_card", "record_sentiment_day",
    "current_claim_ids",
    "evaluate_recommendation_outcomes", "evaluate_sentiment_outcomes",
    "summarize", "recent_observations",
    "backfill_preview", "backfill_from_recommendation_journal",
]
