"""推荐存证账本（recommendation_journal 表 CRUD + 观察账本接线；v1.2 返修）。

两层职责：

1. **现行账本**（recommendation_journal，兼容读）：按 run_date 幂等 upsert
   当日推荐。v1.2 §6 修复：payload 覆盖前先保全唯一旧原文与成绩进
   ``recommendation_journal_history``；``outcome`` 与 ``outcome_payload_hash``
   绑定归属的卡片版本——卡片替换后 ``load_outcome`` 明确返回 None（当前
   卡片无匹配结果），不再把旧标的成绩挂在新卡片上（探针 E）。
   T+N 对账结果合并式分档补齐（chg_1d → chg_5d → chg_20d），重跑幂等。
2. **观察账本**（agent_observations/…_outcomes，见 copilot.observation）：
   save_recommendation 落完整展示批次（含完整卡片原文；空卡也是有效展示，
   探针 D）+ 每标的一条主张；score_journal_outcomes 走 observation 的
   行参考版评价（严格日历版待 01R 日历适配器接入）。

历史无逐日扫描数据，不做伪历史回测，用前向存证替代（设计定稿 §5）。
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime

from lei_signal.api.schemas import RecommendCardDTO


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _payload_hash(payload_json: str) -> str:
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def save_recommendation(conn: sqlite3.Connection, card: RecommendCardDTO) -> str:
    """当日推荐 upsert + 展示批次/主张落观察账本。

    - 内容变化：旧 (payload, outcome) 先入 history（保全唯一旧原文与成绩），
      再更新现行视图，并清掉与新卡不匹配的 outcome 绑定；
    - 内容未变：幂等跳过（不产生新历史、不产生新批次）；
    - 空卡也落观察批次（空列表是有效展示，当前对象集合随之清空）。
    """
    from lei_signal.copilot import observation

    payload_json = card.model_dump_json()
    new_hash = _payload_hash(payload_json)
    row = conn.execute(
        "SELECT payload, payload_hash, outcome, outcome_payload_hash "
        "FROM recommendation_journal WHERE run_date = ?",
        (card.run_date,),
    ).fetchone()
    if row is not None:
        old_hash = row["payload_hash"] or _payload_hash(row["payload"])
        if old_hash != new_hash:
            # 保全唯一旧原文与成绩，再更新兼容当前视图（v1.2 §6）
            seq = conn.execute(
                "SELECT COALESCE(MAX(seq), 0) + 1 AS s "
                "FROM recommendation_journal_history WHERE run_date = ?",
                (card.run_date,),
            ).fetchone()["s"]
            conn.execute(
                "INSERT INTO recommendation_journal_history "
                "(run_date, seq, payload, outcome, payload_hash, saved_at) "
                "VALUES (?,?,?,?,?,?)",
                (card.run_date, seq, row["payload"], row["outcome"],
                 old_hash, _now()),
            )
            conn.execute(
                """
                UPDATE recommendation_journal SET payload = ?, payload_hash = ?,
                    outcome = NULL, outcome_payload_hash = NULL, updated_at = ?
                WHERE run_date = ?
                """,
                (payload_json, new_hash, _now(), card.run_date),
            )
        else:
            # 未变：只补齐缺失的 hash（024 前旧行），不动其他字段
            conn.execute(
                "UPDATE recommendation_journal SET payload_hash = ?, updated_at = ? "
                "WHERE run_date = ? AND (payload_hash IS NULL OR payload_hash != ?)",
                (new_hash, _now(), card.run_date, new_hash),
            )
    else:
        conn.execute(
            """
            INSERT INTO recommendation_journal (
                journal_id, run_date, payload, payload_hash, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (f"rj_{card.run_date}", card.run_date, payload_json, new_hash,
             _now(), _now()),
        )
    observation.record_recommendation_card(conn, card)
    return card.run_date


def load_recommendation(
    conn: sqlite3.Connection, run_date: str
) -> RecommendCardDTO | None:
    row = conn.execute(
        "SELECT payload FROM recommendation_journal WHERE run_date = ?",
        (run_date,),
    ).fetchone()
    if row is None:
        return None
    return RecommendCardDTO.model_validate_json(row["payload"])


def load_history(
    conn: sqlite3.Connection, run_date: str
) -> list[dict]:
    """同日历史版本（旧原文+当时成绩，只增不删）。"""
    return [
        {"seq": r["seq"], "payload": json.loads(r["payload"]),
         "outcome": json.loads(r["outcome"]) if r["outcome"] else None,
         "payload_hash": r["payload_hash"], "saved_at": r["saved_at"]}
        for r in conn.execute(
            "SELECT seq, payload, outcome, payload_hash, saved_at "
            "FROM recommendation_journal_history WHERE run_date = ? ORDER BY seq",
            (run_date,),
        ).fetchall()
    ]


def list_journal_dates(conn: sqlite3.Connection, limit: int = 60) -> list[str]:
    rows = conn.execute(
        "SELECT run_date FROM recommendation_journal ORDER BY run_date DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [r["run_date"] for r in rows]


def save_outcome(conn: sqlite3.Connection, run_date: str, outcome: dict) -> None:
    """T+N 对账结果 upsert，绑定当前卡片版本（payload_hash）。

    只对已有 journal 行使用（编排方保证先存证后对账）。独立调用时 INSERT
    的 payload 为占位 JSON，load_recommendation 校验失败抛错——有意防御。
    """
    row = conn.execute(
        "SELECT payload_hash FROM recommendation_journal WHERE run_date = ?",
        (run_date,),
    ).fetchone()
    bound_hash = row["payload_hash"] if row is not None else None
    if row is None:
        bound_hash = _payload_hash(json.dumps({"placeholder": True}))
    conn.execute(
        """
        INSERT INTO recommendation_journal (journal_id, run_date, payload,
                                            payload_hash, outcome,
                                            outcome_payload_hash,
                                            created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_date) DO UPDATE SET
            outcome = excluded.outcome,
            outcome_payload_hash = excluded.outcome_payload_hash,
            updated_at = excluded.updated_at
        """,
        (
            f"rj_{run_date}",
            run_date,
            json.dumps({"placeholder": True}, ensure_ascii=False),
            bound_hash,
            json.dumps(outcome, ensure_ascii=False),
            bound_hash,
            _now(),
            _now(),
        ),
    )


def load_outcome(conn: sqlite3.Connection, run_date: str) -> dict | None:
    """当前卡片的成绩：outcome 与当前 payload 版本匹配才返回，否则 None。

    修复（探针 E）：卡片替换后不再返回旧标的成绩。旧原文与旧成绩经
    load_history 可查；观察账本按主张各归各版本。
    """
    row = conn.execute(
        "SELECT outcome, payload_hash, outcome_payload_hash "
        "FROM recommendation_journal WHERE run_date = ?",
        (run_date,),
    ).fetchone()
    if row is None or not row["outcome"]:
        return None
    # 024 前的旧行无 hash：该行未被替换过，成绩与存储 payload 的对应关系
    # 成立（score 只按存储 payload 打分），按旧语义返回。
    if row["outcome_payload_hash"] is None and row["payload_hash"] is None:
        pass
    elif row["outcome_payload_hash"] != row["payload_hash"]:
        return None
    try:
        return json.loads(row["outcome"])
    except (TypeError, ValueError):
        return None


def _outcome_changes(
    frame, run_date: str, horizons: tuple[int, ...], *, today: str | None = None
) -> dict[str, float]:
    """run_date 收盘为基准的 T+N 收盘涨跌幅（百分点，按行情行偏移=兼容旧口径）。

    P6（联合收尾）：与观察账本同一条已验证投影——复用 observation 的
    _frame_pairs（坏值保留原日期位、值校验），并受 today 截止（晚于 today
    的行情行不可用）；基价/评价价必须有限正值，否则该档不写。不再单独
    用未裁剪、未验值的计算器。
    """
    from lei_signal.copilot import observation as _ob

    pairs = _ob._frame_pairs(frame)
    if not pairs:
        return {}
    import bisect

    keys = [d for d, _ in pairs]
    base_i = bisect.bisect_right(keys, run_date) - 1
    if base_i < 0:
        return {}
    base = _ob._to_finite_positive(pairs[base_i][1])
    if base is None:
        return {}
    out: dict[str, float] = {}
    for h in horizons:
        j = base_i + h
        if j >= len(pairs):
            continue
        eval_date, eval_price = pairs[j]
        if today is not None and eval_date > today:
            continue  # 截止后行情不可用（P6）
        price = _ob._to_finite_positive(eval_price)
        if price is None:
            continue
        out[f"chg_{h}d"] = round((price / base - 1.0) * 100.0, 2)
    return out


def score_journal_outcomes(
    conn: sqlite3.Connection,
    service,
    *,
    horizons: tuple[int, ...] = (1, 5, 20),
    today: str | None = None,
    calendar=None,
) -> int:
    """给推荐账本日补 T+N 对账（合并式分档补齐，幂等）+ 观察账本评价。

    - 现行 outcome 列按合并式补齐（chg_1d→chg_5d→chg_20d，绑定当前卡片）；
    - 观察账本走 observation.evaluate_recommendation_outcomes：行参考版
      立即可评（受 today 裁剪、缺数据可恢复）；严格日历版需传入 calendar
      适配器（01R 交付后接入），日历不明不产生 ready。
    """
    from datetime import UTC as _UTC
    from datetime import datetime as _dt

    from lei_signal.copilot import observation

    today = today or _dt.now(_UTC).date().isoformat()
    rows = conn.execute(
        "SELECT run_date FROM recommendation_journal "
        "WHERE run_date < ? ORDER BY run_date",
        (today,),
    ).fetchall()
    written = 0
    for row in rows:
        run_date = row["run_date"]
        card = load_recommendation(conn, run_date)
        if card is None or not card.items:
            continue
        existing = load_outcome(conn, run_date) or {}
        merged: dict[str, dict[str, float]] = {
            sym: dict(chgs) for sym, chgs in existing.items()
        }
        changed = False
        for item in card.items:
            try:
                entry = service.get(item.symbol)
            except Exception:  # noqa: BLE001  单标的失败不影响其余
                continue
            if getattr(entry, "result", None) is None:
                continue
            changes = _outcome_changes(entry.result.frame, run_date, horizons,
                                       today=today)
            if not changes:
                continue
            old = merged.setdefault(item.symbol, {})
            for key, val in changes.items():
                if old.get(key) != val:
                    old[key] = val
                    changed = True
        if changed and merged:
            save_outcome(conn, run_date, merged)
            written += 1
    observation.evaluate_recommendation_outcomes(
        conn, service, horizons=horizons, today=today, calendar=calendar
    )
    return written
