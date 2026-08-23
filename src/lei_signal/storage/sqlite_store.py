"""SQLite 存储：迁移、幂等事件写入与结构生命周期。

迁移与幂等模式参考
    licai-wt-pg-integration@2ee7fdc
    src/plan_guardian/adapters/sqlite/migrations.py
改造原因：
  1. 旧实现用 `migration_steps/NNN_*.py` 模块目录 + pkgutil 发现；
     新项目规模小，改为模块内声明的 (ordinal, name, sql) 序列，
     保留「按序号顺序应用 + schema_migrations 记账 + 幂等」的核心设计。
  2. 只定义 signal_events / structure_instances / daily_assessments /
     analysis_runs / rule_registry；不移植账本、订单、通知、账户表。
  3. signal_events 只追加：以 event_id 为主键，重复写入用
     INSERT OR IGNORE 忽略，绝不 UPDATE 已有事件。
"""
from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from lei_signal.domain.types import DailyAssessment, SignalEvent, StructureInstance

MIGRATIONS: tuple[tuple[int, str, str], ...] = (
    (
        1,
        "001_core_tables",
        """
        CREATE TABLE IF NOT EXISTS assets (
            symbol TEXT PRIMARY KEY,
            display_name TEXT,
            market TEXT,
            timezone TEXT
        );

        -- 只追加：event_id 为主键，重复运行以 INSERT OR IGNORE 幂等忽略
        CREATE TABLE IF NOT EXISTS signal_events (
            event_id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            event_date TEXT NOT NULL,
            available_date TEXT NOT NULL,
            rule_id TEXT NOT NULL,
            rule_version TEXT NOT NULL,
            direction TEXT NOT NULL,
            severity TEXT NOT NULL,
            strength INTEGER NOT NULL,
            reason_cn TEXT NOT NULL,
            provenance TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            invalidation_json TEXT NOT NULL,
            structure_id TEXT,
            run_id TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_events_symbol_available
            ON signal_events(symbol, available_date);
        CREATE INDEX IF NOT EXISTS idx_events_rule ON signal_events(rule_id);

        CREATE TABLE IF NOT EXISTS structure_instances (
            structure_id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            structure_type TEXT NOT NULL,
            side TEXT NOT NULL,
            detected_date TEXT NOT NULL,
            confirmed_date TEXT,
            c_price REAL,
            neckline REAL,
            reference_high REAL,
            status TEXT NOT NULL,
            invalidated_date TEXT,
            invalidated_reason TEXT,
            source_event_ids TEXT NOT NULL,
            source_rule_id TEXT,
            provenance TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS daily_assessments (
            symbol TEXT NOT NULL,
            as_of TEXT NOT NULL,
            stage TEXT NOT NULL,
            color TEXT NOT NULL,
            dimensions_json TEXT NOT NULL,
            stage_change_reason_cn TEXT,
            primary_structure_id TEXT,
            b1_price REAL,
            data_status TEXT NOT NULL,
            ruleset_version TEXT NOT NULL,
            PRIMARY KEY (symbol, as_of)
        );

        CREATE TABLE IF NOT EXISTS analysis_runs (
            run_id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            started_at TEXT NOT NULL,
            ruleset_version TEXT NOT NULL,
            provider TEXT,
            last_data_date TEXT,
            event_count INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rule_registry (
            rule_id TEXT NOT NULL,
            rule_version TEXT NOT NULL,
            provenance TEXT NOT NULL,
            note_cn TEXT,
            PRIMARY KEY (rule_id, rule_version)
        );
        """,
    ),
    (
        2,
        "002_structure_lifecycle_events",
        """
        -- 结构状态可以更新，但每次变化必须同步写一条生命周期事件
        CREATE TABLE IF NOT EXISTS structure_lifecycle (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            structure_id TEXT NOT NULL,
            changed_on TEXT NOT NULL,
            from_status TEXT,
            to_status TEXT NOT NULL,
            reason TEXT,
            UNIQUE (structure_id, changed_on, to_status)
        );
        CREATE INDEX IF NOT EXISTS idx_lifecycle_structure
            ON structure_lifecycle(structure_id);
        """,
    ),
    (
        3,
        "003_opportunity_risk_split",
        """
        -- Round 2 修复 4：机会阶段与风险状态分离。
        -- daily_assessments 增加 opportunity_stage / risk_state 独立字段。
        -- 旧 stage 字段保留作为兼容。
        -- 使用安全的列添加：sqlite 无 IF NOT EXISTS，包装在 try/catch 中。
        """,
    ),
    (
        4,
        "004_event_lifecycle_columns",
        """
        -- Round 2 收尾修复：事件生命周期字段持久化。
        -- valid_until / lifecycle_id / ended_event_id 使数据库可还原状态的
        -- 有效/结束时间，与内存事件、解释层、研究使用同一生命周期。
        -- sqlite 无 ALTER TABLE ADD COLUMN IF NOT EXISTS，由 apply_migrations 处理。
        """,
    ),
    (
        5,
        "005_event_lifecycle_snapshots",
        """
        -- Round 3 修复 D3：事件的生命周期字段（valid_until / lifecycle_id /
        -- ended_event_id）随后续行情变化而变化；同一 event_id 在不同 as_of 下
        -- 看到的「正确」生命周期可能不同。signal_events 保持不可变（身份字段），
        -- 本表只追加生命周期快照，PRIMARY KEY = (event_id, run_id, as_of)。
        CREATE TABLE IF NOT EXISTS event_lifecycle_snapshots (
            event_id       TEXT NOT NULL,
            run_id         TEXT NOT NULL,
            as_of          TEXT NOT NULL,
            valid_until    TEXT,
            lifecycle_id   TEXT,
            ended_event_id TEXT,
            recorded_at    TEXT NOT NULL,
            PRIMARY KEY (event_id, run_id, as_of)
        );
        CREATE INDEX IF NOT EXISTS idx_lifecycle_as_of
            ON event_lifecycle_snapshots(as_of);
        """,
    ),
    (
        6,
        "006_market_context_tables",
        """
        -- Round 4: Market context independent storage.
        -- Does NOT write to signal_events, daily_assessments, or structure_instances.

        -- Universe membership version tracking
        CREATE TABLE IF NOT EXISTS universe_membership_versions (
            market_id       TEXT NOT NULL,
            as_of           TEXT NOT NULL,
            universe_version TEXT NOT NULL,
            symbol_count    INTEGER NOT NULL,
            source          TEXT NOT NULL,
            source_version  TEXT NOT NULL,
            source_kind     TEXT NOT NULL,
            retrieved_at    TEXT NOT NULL,
            provenance      TEXT NOT NULL,
            PRIMARY KEY (market_id, as_of, universe_version)
        );
        CREATE INDEX IF NOT EXISTS idx_universe_market_asof
            ON universe_membership_versions(market_id, as_of);

        -- Market breadth snapshots
        CREATE TABLE IF NOT EXISTS market_breadth_snapshots (
            market_id         TEXT NOT NULL,
            as_of             TEXT NOT NULL,
            available_at      TEXT NOT NULL,
            universe_version  TEXT NOT NULL,
            constituent_count INTEGER NOT NULL,
            eligible_20       INTEGER NOT NULL,
            eligible_50       INTEGER NOT NULL,
            eligible_200      INTEGER NOT NULL,
            missing_20        INTEGER NOT NULL,
            missing_50        INTEGER NOT NULL,
            missing_200       INTEGER NOT NULL,
            coverage_20       REAL NOT NULL,
            coverage_50       REAL NOT NULL,
            coverage_200      REAL NOT NULL,
            breadth_20        REAL,
            breadth_50        REAL,
            breadth_200       REAL,
            percentile_20     REAL,
            percentile_50     REAL,
            percentile_200    REAL,
            source_kind       TEXT NOT NULL,
            provenance        TEXT NOT NULL,
            data_status       TEXT NOT NULL,
            run_id            TEXT NOT NULL,
            PRIMARY KEY (market_id, as_of, universe_version)
        );
        CREATE INDEX IF NOT EXISTS idx_breadth_market_asof
            ON market_breadth_snapshots(market_id, as_of);

        -- Market context events (extreme events, divergence, etc.)
        CREATE TABLE IF NOT EXISTS market_context_events (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            market_id         TEXT NOT NULL,
            as_of             TEXT NOT NULL,
            available_at      TEXT NOT NULL,
            event_type        TEXT NOT NULL,
            event_version     TEXT NOT NULL,
            threshold_origin  TEXT NOT NULL,
            evidence_json     TEXT NOT NULL,
            provenance        TEXT NOT NULL,
            source_kind       TEXT NOT NULL,
            data_status       TEXT NOT NULL,
            run_id            TEXT NOT NULL,
            UNIQUE (market_id, as_of, event_type, event_version)
        );
        CREATE INDEX IF NOT EXISTS idx_context_events_market_asof
            ON market_context_events(market_id, as_of);

        -- Sentiment observations (NAAIM, AAII)
        CREATE TABLE IF NOT EXISTS sentiment_observations (
            series_id             TEXT NOT NULL,
            survey_week           TEXT NOT NULL,
            available_at          TEXT NOT NULL,
            source                TEXT NOT NULL,
            license_status        TEXT NOT NULL,
            publication_delay_days INTEGER,
            current_eligible      INTEGER NOT NULL,
            exposure_index        REAL,
            bullish               REAL,
            neutral               REAL,
            bearish               REAL,
            bull_bear             REAL,
            percentile            REAL,
            label                 TEXT NOT NULL,
            PRIMARY KEY (series_id, survey_week, available_at)
        );
        CREATE INDEX IF NOT EXISTS idx_sentiment_available
            ON sentiment_observations(series_id, available_at);

        -- Market context assessments (summary + reasons + conflicts)
        CREATE TABLE IF NOT EXISTS market_context_assessments (
            market_id           TEXT NOT NULL,
            as_of               TEXT NOT NULL,
            available_at        TEXT NOT NULL,
            long_regime         TEXT NOT NULL,
            heat_state          TEXT NOT NULL,
            breadth_direction   TEXT NOT NULL,
            summary             TEXT NOT NULL,
            reasons_json        TEXT NOT NULL,
            conflicts_json      TEXT NOT NULL,
            drawdown_from_ath   REAL,
            naaim_label         TEXT NOT NULL,
            aaii_label          TEXT NOT NULL,
            source_kind         TEXT NOT NULL,
            provenance          TEXT NOT NULL,
            data_status         TEXT NOT NULL,
            run_id              TEXT NOT NULL,
            PRIMARY KEY (market_id, as_of, available_at)
        );
        CREATE INDEX IF NOT EXISTS idx_context_assess_market_asof
            ON market_context_assessments(market_id, available_at);
        """,
    ),
    (
        7,
        "007_watchlist",
        """
        -- 看盘系统自选股列表（Web UI 作用域，纯新增，不影响研究表）
        CREATE TABLE IF NOT EXISTS watchlist_items (
            symbol TEXT PRIMARY KEY,
            display_name TEXT,
            market TEXT NOT NULL,
            note TEXT,
            sort_order INTEGER NOT NULL DEFAULT 0,
            added_at TEXT NOT NULL
        );
        """,
    ),
    (
        8,
        "008_watchlist_groups",
        """
        -- 自选分组（如「科技」「防御」）。内置「大盘」组是 config 常量，
        -- 不入库、不可删，因此本表只存用户自建组。
        CREATE TABLE IF NOT EXISTS watchlist_groups (
            group_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL UNIQUE,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        """,
    ),
    (
        9,
        "009_market_context_append_only",
        """
        -- Round 5: market-context append-only revisions.
        -- Each write is a new row keyed by revision_no; never UPDATE prior rows,
        -- never INSERT OR REPLACE the latest reading. eligibility/missing counts
        -- are persisted (not zeroed) and stale rows are filtered at query time.

        CREATE TABLE IF NOT EXISTS market_breadth_snapshot_revisions (
            market_id         TEXT NOT NULL,
            as_of             TEXT NOT NULL,
            universe_version  TEXT NOT NULL,
            revision_no       INTEGER NOT NULL,
            available_at      TEXT NOT NULL,
            run_id            TEXT NOT NULL,
            source_kind       TEXT NOT NULL,
            provenance        TEXT NOT NULL,
            data_status       TEXT NOT NULL,
            constituent_count INTEGER NOT NULL,
            eligible_20       INTEGER NOT NULL,
            eligible_50       INTEGER NOT NULL,
            eligible_200      INTEGER NOT NULL,
            missing_20        INTEGER NOT NULL,
            missing_50        INTEGER NOT NULL,
            missing_200       INTEGER NOT NULL,
            coverage_20       REAL NOT NULL,
            coverage_50       REAL NOT NULL,
            coverage_200      REAL NOT NULL,
            breadth_20        REAL,
            breadth_50        REAL,
            breadth_200       REAL,
            percentile_20     REAL,
            percentile_50     REAL,
            percentile_200    REAL,
            PRIMARY KEY (market_id, as_of, universe_version, revision_no)
        );
        CREATE INDEX IF NOT EXISTS idx_breadth_revisions_latest
            ON market_breadth_snapshot_revisions(market_id, as_of, revision_no DESC);

        CREATE TABLE IF NOT EXISTS market_context_assessment_revisions (
            market_id           TEXT NOT NULL,
            as_of               TEXT NOT NULL,
            available_at        TEXT NOT NULL,
            revision_no         INTEGER NOT NULL,
            run_id              TEXT NOT NULL,
            long_regime         TEXT NOT NULL,
            heat_state          TEXT NOT NULL,
            breadth_direction   TEXT NOT NULL,
            summary             TEXT NOT NULL,
            reasons_json        TEXT NOT NULL,
            conflicts_json      TEXT NOT NULL,
            drawdown_from_ath   REAL,
            naaim_label         TEXT NOT NULL,
            aaii_label          TEXT NOT NULL,
            source_kind         TEXT NOT NULL,
            provenance          TEXT NOT NULL,
            data_status         TEXT NOT NULL,
            PRIMARY KEY (market_id, as_of, available_at, revision_no)
        );
        CREATE INDEX IF NOT EXISTS idx_assess_revisions_latest
            ON market_context_assessment_revisions(
                market_id, as_of, available_at DESC, revision_no DESC
            );
        """,
    ),
    (
        10,
        "010_trade_plans",
        """
        -- 计划台账主体：记录状态机 + 价位，刻意不含数量/金额/成交价/账户
        CREATE TABLE IF NOT EXISTS trade_plans (
            plan_id                  TEXT PRIMARY KEY,
            symbol                   TEXT NOT NULL,
            module                   TEXT NOT NULL,          -- A/B/C/D，对齐 MODULE_MAP
            direction                TEXT NOT NULL,          -- long/short
            entry_rule_id            TEXT,                   -- 入场理由锚点（漂移检测主对象）
            entry_lifecycle_id       TEXT,
            entry_trigger_cn         TEXT,
            entry_price_ref          REAL,                   -- 参考入场价，非成交价
            invalidation_price       REAL,                   -- revision_no=0 的值永久冻结
            target_b_price           REAL,
            target_b_source          TEXT,
            reward_risk_at_plan      REAL,                   -- 建计划时 R/R 快照；不可计算时 NULL
            valid_until              TEXT NOT NULL,          -- 逐计划自填有效期；draft 允许空串
            state                    TEXT NOT NULL,          -- 见 PLAN_STATES
            ruleset_version          TEXT NOT NULL,
            reason                   TEXT NOT NULL,          -- 制定原因必填；draft 允许空串
            -- 五项交易假设（决策 1，制定时冻结，复议对照原文；Python 不语义解析）
            thesis_cn                TEXT NOT NULL DEFAULT '',
            invalidation_criteria_cn TEXT NOT NULL DEFAULT '',
            drawdown_playbook_cn     TEXT NOT NULL DEFAULT '',
            take_profit_plan_cn      TEXT NOT NULL DEFAULT '',
            stop_plan_cn             TEXT NOT NULL DEFAULT '',
            entered_on               TEXT,
            exited_on                TEXT,
            exit_reason_rule_id      TEXT,
            superseded_by            TEXT,
            created_at               TEXT NOT NULL,
            updated_at               TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_plans_symbol_state
            ON trade_plans(symbol, state);

        -- append-only 修订史：revision_no=0 为创建快照，原始失效价与五项预案永远在此
        CREATE TABLE IF NOT EXISTS trade_plan_revisions (
            revision_id        TEXT PRIMARY KEY,
            plan_id            TEXT NOT NULL,
            revision_no        INTEGER NOT NULL,             -- 0 = 创建快照
            changed_field      TEXT NOT NULL,                -- __snapshot__ 或字段名
            old_value          TEXT,
            new_value          TEXT,
            verdict            TEXT NOT NULL,                -- 见 VERDICT_*
            verdict_reason_cn  TEXT,
            changed_at         TEXT NOT NULL,
            changed_by         TEXT NOT NULL,                -- user/system
            UNIQUE (plan_id, revision_no, changed_field)
        );
        CREATE INDEX IF NOT EXISTS idx_revisions_plan
            ON trade_plan_revisions(plan_id, revision_no);

        -- 待办（决策 4）：ENTER/EXIT/REVIEW，催办计数，推迟复活谓词
        CREATE TABLE IF NOT EXISTS plan_action_items (
            action_id              TEXT PRIMARY KEY,
            plan_id                TEXT NOT NULL,
            kind                   TEXT NOT NULL,             -- ENTER/EXIT/REVIEW
            source_alert_code      TEXT NOT NULL,
            state                  TEXT NOT NULL,             -- open/done/deferred/expired
            due_from               TEXT,                      -- = alert 的 actionable_from
            nag_count              INTEGER NOT NULL DEFAULT 0,
            last_nagged_bar_date   TEXT,
            resume_on              TEXT,                      -- 推迟复活谓词 JSON
            closed_on              TEXT,
            close_kind             TEXT,                      -- done/deferred/expired
            created_at             TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_actions_plan_state
            ON plan_action_items(plan_id, state);

        -- 原因注解（append-only，永不修改已冻结记录）：推迟/放宽/收紧/复议/事后补充
        CREATE TABLE IF NOT EXISTS plan_annotations (
            annotation_id  TEXT PRIMARY KEY,
            plan_id        TEXT NOT NULL,
            ref_kind       TEXT NOT NULL,                    -- revision/action
            ref_id         TEXT,
            kind           TEXT NOT NULL,                    -- 见 Annotation.kind
            reason_cn      TEXT NOT NULL,
            created_at     TEXT NOT NULL,
            author         TEXT NOT NULL                     -- user/system/agent
        );
        CREATE INDEX IF NOT EXISTS idx_annotations_plan
            ON plan_annotations(plan_id, created_at);
        """,
    ),
    (
        11,
        "011_feishu_webhook_nonces",
        """
        -- Webhook 回执链接 nonce：一次性消费，防止旧链接重放。
        CREATE TABLE IF NOT EXISTS feishu_webhook_nonces (
            nonce TEXT PRIMARY KEY,
            plan_id TEXT NOT NULL,
            action_id TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            consumed_at TEXT,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_feishu_nonces_expiry
            ON feishu_webhook_nonces(expires_at);
        """,
    ),
    (
        12,
        "012_holding_watch_plans",
        """
        -- 持仓盯盘（人类 2026-08-05 决定）：已在场内的标的只监督退出。
        -- plan_kind=holding_watch 时直接落 entered，不走 armed 入场判定。
        -- 仍然只记价位与状态，不记数量/金额/账户（对齐 migration 010 的边界）。
        ALTER TABLE trade_plans ADD COLUMN plan_kind TEXT NOT NULL DEFAULT 'entry';
        ALTER TABLE trade_plans ADD COLUMN take_profit_price REAL;
        ALTER TABLE trade_plans ADD COLUMN stop_price REAL;
        -- 信号型退出触发：逗号分隔 rule_id（如 lei_color 转黑、dual_ma_bull_confirmed）
        ALTER TABLE trade_plans ADD COLUMN watch_signal_rule_ids TEXT NOT NULL DEFAULT '';
        CREATE INDEX IF NOT EXISTS idx_plans_kind_state
            ON trade_plans(plan_kind, state);
        """,
    ),
    (
        13,
        "013_watch_subscriptions",
        """
        -- 提醒订阅 (决策 2, 2026-08-08): 用户从 BuyPointReview.watch_conditions
        -- 一键订阅某条"未来买点"条件, 由 14:45 checker 盯盘.
        --
        -- state 状态机:
        --   active  -> pending_confirmation (checker 命中)
        --   pending_confirmation -> promoted (Step 3 落计划后回填 promoted_plan_id)
        --   pending_confirmation -> dismissed (人放弃, 写 dismissed_reason)
        --   active  -> dismissed (人主动取消)
        --
        -- kind 区分价位型 vs 状态型, v1 只接 price (kind=state 留 TODO).
        CREATE TABLE IF NOT EXISTS watch_subscriptions (
            watch_id            TEXT PRIMARY KEY,        -- ws_<symbol>_<ts>_<hash>
            symbol              TEXT NOT NULL,
            direction           TEXT NOT NULL,           -- long/short
            module              TEXT NOT NULL,           -- A/B/C/D
            source_candidate_id TEXT,                    -- review 里的 candidate id
            source_rule_id      TEXT,                    -- 锚定 rule_id
            level               REAL,                    -- kind=price 时有值
            watch_kind          TEXT NOT NULL,           -- price | state
            watch_text_cn       TEXT NOT NULL,           -- 照抄 WatchConditionDTO.text_cn
            as_signal_rule_ids  TEXT NOT NULL DEFAULT '',
            state               TEXT NOT NULL,           -- 见状态机
            created_at          TEXT NOT NULL,
            last_checked_at     TEXT,                    -- 上次 checker 跑过的时间
            triggered_at        TEXT,                    -- 首次进入 pending_confirmation 的时间
            triggered_price     REAL,                    -- 当时 last_close
            triggered_reason_cn TEXT,                    -- checker 给的命中原因
            promoted_plan_id    TEXT,                    -- Step 3 落计划后回填
            dismissed_at        TEXT,
            dismissed_reason    TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_watch_state_created
            ON watch_subscriptions(state, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_watch_symbol_state
            ON watch_subscriptions(symbol, state);
        """,
    ),
    (
        14,
        "014_plan_source_field",
        """
        -- 计划来源 (Step 3, 决策 2, 2026-08-09): trade_plans 加 source 字段,
        -- 区分计划是用户手建 / 来自提醒 / 来自 agent (未来).
        --
        --   user           = 手动 (默认)
        --   watch_promoted = 来自提醒命中 (Step 2 watch 触发, 用户确认后落计划)
        --   agent          = 来自 agent (预留, 当前未启用)
        --
        -- 为什么要 source:
        --   1) 让用户/审计能一眼看出"这条计划是被提醒带出来的还是我自己想做的"
        --   2) Step 2 watch promoted_plan_id 反查时, 知道这条 plan 是从哪个 watch 来的
        --   3) 未来按来源筛选报告 (eg "本月看提醒命中的计划胜率如何")
        ALTER TABLE trade_plans ADD COLUMN source TEXT NOT NULL DEFAULT 'user';
        CREATE INDEX IF NOT EXISTS idx_plans_source_state
            ON trade_plans(source, state);
        """,
    ),
    (
        15,
        "015_daily_opportunity_scan",
        """
        -- 今日机会雷达 (2026-08-10): 15:00 launchd 扫全自选, 落当日 verdict 快照.
        -- dashboard 面板 + TopNav 红点读这张表, 不现场跑 scan (scan 5-10s, 轮询不可接受).
        --
        -- 一行 = 一个标的一天的 scan 结果. (scan_date, symbol) 唯一.
        -- 当日重扫 = 先 DELETE 当日再 INSERT (upsert_scan_results 整体重写).
        CREATE TABLE IF NOT EXISTS daily_opportunity_scan (
            scan_date        TEXT NOT NULL,        -- YYYY-MM-DD (UTC date)
            symbol           TEXT NOT NULL,
            display_name     TEXT NOT NULL DEFAULT '',
            verdict          TEXT NOT NULL,        -- actionable | blocked | waiting | none
            verdict_cn       TEXT NOT NULL DEFAULT '',
            best_scenario_cn TEXT,
            best_state       TEXT,
            reward_risk_ratio REAL,
            reward_risk_computable INTEGER NOT NULL DEFAULT 0,
            blocking_reasons TEXT NOT NULL DEFAULT '[]',  -- JSON array
            missing_summary_cn TEXT NOT NULL DEFAULT '',
            has_active_plan  INTEGER NOT NULL DEFAULT 0,
            error            TEXT,
            generated_at     TEXT NOT NULL,
            PRIMARY KEY (scan_date, symbol)
        );
        CREATE INDEX IF NOT EXISTS idx_daily_scan_date_verdict
            ON daily_opportunity_scan(scan_date, verdict);
        """,
    ),
    (
        16,
        "016_signal_alerts",
        """
        -- 今日自选信号卖点表 (2026-08-23): 看盘主页「今日自选信号」横幅的数据源.
        -- 卖点行来自 extract_sell_signals (纯提取, 不做新判定);
        -- 买点行继续写 daily_opportunity_scan (既有表), 读 API 合并两表.
        -- 当日重扫 = 先 DELETE 当日再 INSERT (与 daily_opportunity_scan 同语义).
        -- side='meta' 的 as_of 行记录本次扫描口径 (intraday | close), 是"今日是否扫过"的唯一判据.
        CREATE TABLE IF NOT EXISTS signal_alerts (
            scan_date      TEXT NOT NULL,        -- YYYY-MM-DD (UTC date)
            symbol         TEXT NOT NULL,
            display_name   TEXT NOT NULL DEFAULT '',
            side           TEXT NOT NULL,        -- sell | unavailable | meta
            tier           TEXT NOT NULL,        -- hard | warn | soft | meta
            kind           TEXT NOT NULL,        -- structure_invalidated | exit_proxy |
                                                  -- top_structure_confirmed | key_wave_black |
                                                  -- color_black | data_unavailable | as_of
            kind_cn        TEXT NOT NULL DEFAULT '',
            title          TEXT NOT NULL DEFAULT '',
            reason_cn      TEXT NOT NULL DEFAULT '',
            is_new         INTEGER NOT NULL DEFAULT 0,
            key_prices     TEXT NOT NULL DEFAULT '{}',  -- JSON object {name: price}
            provenance     TEXT NOT NULL DEFAULT 'system',
            available_date TEXT NOT NULL DEFAULT '',
            error          TEXT,
            generated_at   TEXT NOT NULL,
            PRIMARY KEY (scan_date, symbol, side, kind)
        );
        CREATE INDEX IF NOT EXISTS idx_signal_alerts_date_side_tier
            ON signal_alerts(scan_date, side, tier);
        """,
    ),
    (
        17,
        "017_agent_sessions",
        """
        -- agent 会话层：多轮记忆（append-only，不含数量/金额）
        CREATE TABLE IF NOT EXISTS agent_sessions (
            session_id     TEXT PRIMARY KEY,
            symbol         TEXT,                   -- NULL = 全局会话
            title_cn       TEXT NOT NULL DEFAULT '',
            created_at     TEXT NOT NULL,          -- UTC ISO
            last_active_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS agent_messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL REFERENCES agent_sessions(session_id),
            role       TEXT NOT NULL CHECK (role IN ('user','assistant')),
            content    TEXT NOT NULL,
            grounded   INTEGER NOT NULL DEFAULT 0,
            meta_json  TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL               -- UTC ISO
        );
        CREATE INDEX IF NOT EXISTS idx_agent_messages_session
            ON agent_messages(session_id, message_id);
        CREATE INDEX IF NOT EXISTS idx_agent_sessions_symbol
            ON agent_sessions(symbol, last_active_at);
        """,
    ),
)


@dataclass(frozen=True, slots=True)
class WriteReport:
    """写入结果，区分新增与幂等忽略。"""

    inserted: int
    ignored: int


def connect(path: str | Path) -> sqlite3.Connection:
    """打开连接并应用迁移。

    - ``timeout=5.0``：并发写（同一进程多线程 + 跨进程）时，后到的连接会等 5 秒
      而不是立即 ``database is locked``。
    - ``PRAGMA journal_mode = WAL``：多读单写场景下读写不再互斥。看盘页一次
      会拉 11+ 个标的，每个都要打开 lab.db，串行阻塞会卡到 60s+。WAL 让
      读和写可以并发，唯一互斥的是「写 vs 写」，由 5s busy_timeout 兜底。
    - 迁移必须 **只** 第一次开连接时跑一次（pragma journal_mode 是持久化的，
      后续连接会复用），避免并发连接重复 apply 互相抢锁。
    """
    connection = sqlite3.connect(str(path), timeout=5.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    apply_migrations(connection)
    return connection


def _safe_add_column(
    connection: sqlite3.Connection,
    table: str,
    column: str,
    type_sql: str,
) -> None:
    """sqlite 不支持 ALTER TABLE ADD COLUMN IF NOT EXISTS；用 try/except 兜底。"""
    try:
        connection.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {type_sql}"
        )
    except sqlite3.OperationalError as exc:
        if "duplicate column" not in str(exc).lower():
            raise


def apply_migrations(connection: sqlite3.Connection) -> tuple[str, ...]:
    """按序号顺序应用未执行的迁移。已应用的跳过（幂等）。"""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            ordinal INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.commit()

    applied = {
        row["name"] for row in connection.execute("SELECT name FROM schema_migrations")
    }
    executed: list[str] = []
    for ordinal, name, sql in sorted(MIGRATIONS):
        if name in applied:
            continue
        # 003 包含 ALTER TABLE ADD COLUMN：sqlite 无 IF NOT EXISTS，
        # 用 _safe_add_column 处理
        if name == "003_opportunity_risk_split":
            _safe_add_column(connection, "daily_assessments", "opportunity_stage", "TEXT")
            _safe_add_column(connection, "daily_assessments", "risk_state", "TEXT")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_assessments_opp "
                "ON daily_assessments(symbol, as_of, opportunity_stage)"
            )
        elif name == "004_event_lifecycle_columns":
            _safe_add_column(connection, "signal_events", "valid_until", "TEXT")
            _safe_add_column(connection, "signal_events", "lifecycle_id", "TEXT")
            _safe_add_column(connection, "signal_events", "ended_event_id", "TEXT")
        elif name == "008_watchlist_groups":
            # 建分组表 + 给已有 watchlist_items 补 group_id 列。
            # group_id 可空：NULL = 未分组（左栏归入「未分组」）。
            # 不加外键约束：删组时把成员置 NULL 而非级联删除标的。
            connection.executescript(sql)
            _safe_add_column(connection, "watchlist_items", "group_id", "INTEGER")
        else:
            # executescript 会隐式提交，因此记账单独提交
            connection.executescript(sql)
        connection.execute(
            "INSERT INTO schema_migrations (ordinal, name) VALUES (?, ?)",
            (ordinal, name),
        )
        connection.commit()
        executed.append(name)
    return tuple(executed)


def write_events(
    connection: sqlite3.Connection,
    events: Iterable[SignalEvent],
    *,
    run_id: str | None = None,
) -> WriteReport:
    """只追加写入事件。同 event_id 幂等忽略，绝不覆盖已有行。

    Round 2 收尾修复：写入 valid_until / lifecycle_id / ended_event_id，
    使数据库可还原状态的「有效/结束时间」，与内存事件、解释层、研究同一生命周期。
    """
    inserted = 0
    attempted = 0
    for event in events:
        attempted += 1
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO signal_events (
                event_id, symbol, timeframe, event_date, available_date,
                rule_id, rule_version, direction, severity, strength,
                reason_cn, provenance, evidence_json, invalidation_json,
                structure_id, run_id, valid_until, lifecycle_id, ended_event_id
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                event.event_id,
                event.symbol,
                event.timeframe,
                event.event_date.isoformat(),
                event.available_date.isoformat(),
                event.rule_id,
                event.rule_version,
                event.direction.value,
                event.severity.value,
                event.strength,
                event.reason_cn,
                event.provenance.value,
                json.dumps(event.evidence, ensure_ascii=False, sort_keys=True, default=str),
                json.dumps(event.invalidation, ensure_ascii=False, sort_keys=True, default=str),
                event.structure_id,
                run_id or event.run_id,
                event.valid_until.isoformat() if event.valid_until is not None else None,
                event.lifecycle_id,
                event.ended_event_id,
            ),
        )
        inserted += cursor.rowcount if cursor.rowcount > 0 else 0
    connection.commit()
    return WriteReport(inserted=inserted, ignored=attempted - inserted)


def _expected_structure_transitions(
    structure: StructureInstance,
) -> list[tuple[str | None, str, date]]:
    """根据结构日期字段推断完整状态链（按时间顺序）。

    每个元素 ``(from_status, to_status, changed_on)``：
      * ``None -> candidate``                  @ detected_date
      * ``candidate -> confirmed``             @ confirmed_date     （已确认时）
      * ``confirmed/candidate -> invalidated``  @ invalidated_date  （已失效时）

    旧实现只比较「数据库已有状态」与「当前快照状态」，对一次性传入的最终结构
    只会记录一次跳变，并因 ``confirmed_date or invalidated_date`` 的 or 链把
    **确认日**误当作**失效日**，漏掉 candidate→confirmed 与 confirmed→invalidated。
    这里改为从日期字段重建完整链路，每次运行都补全缺失转换（INSERT OR IGNORE 幂等）。
    """
    transitions: list[tuple[str | None, str, date]] = [
        (None, "candidate", structure.detected_date),
    ]
    confirmed_date = structure.confirmed_date
    is_confirmed = confirmed_date is not None and structure.status.value in (
        "confirmed",
        "active",
        "invalidated",
    )
    if is_confirmed and confirmed_date is not None:
        transitions.append(("candidate", "confirmed", confirmed_date))
    if structure.invalidated_date is not None and structure.status.value == "invalidated":
        prev = "confirmed" if is_confirmed else "candidate"
        transitions.append((prev, "invalidated", structure.invalidated_date))
    return transitions


def write_structures(
    connection: sqlite3.Connection,
    structures: Iterable[StructureInstance],
) -> WriteReport:
    """写入结构。状态变化允许更新，但每次变化同步写生命周期事件。

    Round 2 收尾修复：生命周期依据 ``detected_date`` / ``confirmed_date`` /
    ``invalidated_date`` 重建完整转换链，每次运行幂等补全（不再漏记确认、不再把
    确认日误当失效日）。
    """
    inserted = 0
    updated = 0
    for structure in structures:
        existing = connection.execute(
            "SELECT status FROM structure_instances WHERE structure_id = ?",
            (structure.structure_id,),
        ).fetchone()
        payload = (
            structure.structure_id,
            structure.symbol,
            structure.structure_type,
            structure.side,
            structure.detected_date.isoformat(),
            structure.confirmed_date.isoformat() if structure.confirmed_date else None,
            structure.c_price,
            structure.neckline,
            structure.reference_high,
            structure.status.value,
            structure.invalidated_date.isoformat() if structure.invalidated_date else None,
            structure.invalidated_reason,
            json.dumps(list(structure.source_event_ids), ensure_ascii=False),
            structure.source_rule_id,
            structure.provenance.value,
        )
        if existing is None:
            connection.execute(
                """
                INSERT INTO structure_instances (
                    structure_id, symbol, structure_type, side, detected_date,
                    confirmed_date, c_price, neckline, reference_high, status,
                    invalidated_date, invalidated_reason, source_event_ids,
                    source_rule_id, provenance
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                payload,
            )
            inserted += 1
        elif existing["status"] != structure.status.value:
            connection.execute(
                """
                UPDATE structure_instances SET
                    confirmed_date = ?, status = ?, invalidated_date = ?,
                    invalidated_reason = ?
                WHERE structure_id = ?
                """,
                (
                    structure.confirmed_date.isoformat() if structure.confirmed_date else None,
                    structure.status.value,
                    structure.invalidated_date.isoformat()
                    if structure.invalidated_date
                    else None,
                    structure.invalidated_reason,
                    structure.structure_id,
                ),
            )
            updated += 1
        # 生命周期：依据日期字段重建完整转换链，幂等补全（INSERT OR IGNORE）。
        # 放在 if/elif 之外，保证无论结构是新建还是更新，缺失转换都会被补上。
        for from_status, to_status, changed_on in _expected_structure_transitions(
            structure
        ):
            _record_lifecycle(
                connection,
                structure_id=structure.structure_id,
                changed_on=changed_on,
                from_status=from_status,
                to_status=to_status,
                reason=structure.invalidated_reason or "status_change",
            )
    connection.commit()
    return WriteReport(inserted=inserted, ignored=updated)


def _record_lifecycle(
    connection: sqlite3.Connection,
    *,
    structure_id: str,
    changed_on: date,
    from_status: str | None,
    to_status: str,
    reason: str | None,
) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO structure_lifecycle
            (structure_id, changed_on, from_status, to_status, reason)
        VALUES (?,?,?,?,?)
        """,
        (structure_id, changed_on.isoformat(), from_status, to_status, reason),
    )


def write_assessment(
    connection: sqlite3.Connection,
    assessment: DailyAssessment,
) -> None:
    """写入每日解释快照（同一天重复运行覆盖为同值）。

    Round 2 修复 4：同时写入 opportunity_stage 与 risk_state 独立字段。
    旧 stage 字段保留作为兼容。
    """
    connection.execute(
        """
        INSERT OR REPLACE INTO daily_assessments (
            symbol, as_of, stage, color, dimensions_json,
            stage_change_reason_cn, primary_structure_id, b1_price,
            data_status, ruleset_version,
            opportunity_stage, risk_state
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            assessment.symbol,
            assessment.as_of.isoformat(),
            assessment.stage.value,
            assessment.color.value,
            json.dumps(assessment.dimensions, ensure_ascii=False, sort_keys=True),
            assessment.stage_change_reason_cn,
            assessment.primary_structure.structure_id
            if assessment.primary_structure
            else None,
            assessment.b1_price,
            assessment.data_status,
            assessment.rule_ruleset_version,
            assessment.opportunity_stage.value,
            assessment.risk_state.value,
        ),
    )
    connection.commit()


def record_run(
    connection: sqlite3.Connection,
    *,
    run_id: str,
    symbol: str,
    started_at: str,
    ruleset_version: str,
    provider: str | None,
    last_data_date: date | None,
    event_count: int,
) -> None:
    """记录运行元数据，使结果可复现追溯。"""
    connection.execute(
        """
        INSERT OR REPLACE INTO analysis_runs (
            run_id, symbol, started_at, ruleset_version,
            provider, last_data_date, event_count
        ) VALUES (?,?,?,?,?,?,?)
        """,
        (
            run_id,
            symbol,
            started_at,
            ruleset_version,
            provider,
            last_data_date.isoformat() if last_data_date else None,
            event_count,
        ),
    )
    connection.commit()


def count_events(connection: sqlite3.Connection, symbol: str | None = None) -> int:
    if symbol is None:
        row = connection.execute("SELECT COUNT(*) AS n FROM signal_events").fetchone()
    else:
        row = connection.execute(
            "SELECT COUNT(*) AS n FROM signal_events WHERE symbol = ?", (symbol,)
        ).fetchone()
    return int(row["n"])


# ========================================================================
# Round 3 修复 D3：事件生命周期快照
# -----------------------------------------------------------------------
# signal_events 保持不可变（身份字段：发生日、规则版本、证据、结构ID），
# 用 ``INSERT OR IGNORE`` 幂等忽略。新增 ``event_lifecycle_snapshots`` 表
# 记录每次分析时算出的 valid_until / lifecycle_id / ended_event_id。
# 这样后续增量重跑（更长行情下同一 event_id 的 valid_until 可能延长）
# 不会覆盖旧记录，而是新增一条快照。``read_latest_lifecycle`` 按
# as_of 降序取最新结果。
# ========================================================================


@dataclass(frozen=True, slots=True)
class LifecycleSnapshot:
    """事件在某个 as_of 下的生命周期快照。"""

    event_id: str
    run_id: str
    as_of: str
    valid_until: str | None
    lifecycle_id: str | None
    ended_event_id: str | None
    recorded_at: str


def _read_existing_event_identity(
    connection: sqlite3.Connection,
    event: SignalEvent,
) -> dict[str, object] | None:
    """读取数据库中已存在事件的**身份字段**（不可变字段）。

    身份字段是「事件是什么」的稳定语义，不包括观测时刻的原始数值（close、
    ema20 等）——后者是 evidence 的快照，随数据源 / 重算口径变化属于正常
    现象，归入 ``event_lifecycle_snapshots`` 表记录演变。
    """
    row = connection.execute(
        """
        SELECT event_date, available_date, rule_id, rule_version, structure_id,
               symbol, timeframe
        FROM signal_events WHERE event_id = ?
        """,
        (event.event_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "event_date": row["event_date"],
        "available_date": row["available_date"],
        "rule_id": row["rule_id"],
        "rule_version": row["rule_version"],
        "structure_id": row["structure_id"],
        "symbol": row["symbol"],
        "timeframe": row["timeframe"],
    }


class EventIdentityConflictError(RuntimeError):
    """同一 event_id 的身份字段不一致。

    身份字段是历史事实，不应改变。如果出现冲突说明上游规则或事件生成
    逻辑发生了非预期变更（如规则版本错误、structure_id 错误绑定），
    必须显式报错，不得静默覆盖。
    """


def _assert_event_identity(
    connection: sqlite3.Connection,
    event: SignalEvent,
) -> None:
    existing = _read_existing_event_identity(connection, event)
    if existing is None:
        return
    new_values = {
        "event_date": event.event_date.isoformat(),
        "available_date": event.available_date.isoformat(),
        "rule_id": event.rule_id,
        "rule_version": event.rule_version,
        "structure_id": event.structure_id,
        "symbol": event.symbol,
        "timeframe": event.timeframe,
    }
    for key, expected in existing.items():
        if new_values[key] != expected:
            raise EventIdentityConflictError(
                f"事件 {event.event_id} 的身份字段 {key} 不一致："
                f"已存={expected!r}，新值={new_values[key]!r}。"
                "身份字段是不可变历史事实，必须显式处理，不得静默覆盖。"
            )


def write_event_lifecycles(
    connection: sqlite3.Connection,
    events: Iterable[SignalEvent],
    *,
    run_id: str | None,
    as_of: date,
) -> tuple[int, int]:
    """写入事件生命周期快照。

    与 ``write_events`` 不同：
      * 本函数是**追加**写入：同一 ``(event_id, run_id, as_of)`` 主键下
        重复写入用 ``INSERT OR REPLACE`` 覆盖（同一次分析内重新跑覆盖为同值）。
      * **不修改 signal_events**：身份字段保持不可变。
      * 如果 signal_events 里已有该 event_id 但身份字段不同 → **报错**，
        不允许任何形式覆盖（保留审计线索）。

    返回 ``(inserted, identity_conflicts)``。
    """
    from datetime import UTC, datetime

    if run_id is None:
        raise ValueError("write_event_lifecycles 必须显式传入 run_id")

    inserted = 0
    recorded_at = datetime.now(UTC).isoformat()
    as_of_text = as_of.isoformat()

    for event in events:
        _assert_event_identity(connection, event)
        cursor = connection.execute(
            """
            INSERT OR REPLACE INTO event_lifecycle_snapshots (
                event_id, run_id, as_of, valid_until,
                lifecycle_id, ended_event_id, recorded_at
            ) VALUES (?,?,?,?,?,?,?)
            """,
            (
                event.event_id,
                run_id,
                as_of_text,
                event.valid_until.isoformat() if event.valid_until is not None else None,
                event.lifecycle_id,
                event.ended_event_id,
                recorded_at,
            ),
        )
        inserted += cursor.rowcount if cursor.rowcount > 0 else 0
    connection.commit()
    return inserted, 0


def read_latest_lifecycle(
    connection: sqlite3.Connection,
    event_id: str,
) -> LifecycleSnapshot | None:
    """读取该 event_id 的**最新**生命周期快照（as_of 降序，相同则取 recorded_at 较晚者）。

    用于增量回放场景：同一事件在多次分析中可能有不同快照，本函数返回
    「最近一次分析认为它什么时候结束」。如果该事件从未写入快照则返回 None。
    """
    row = connection.execute(
        """
        SELECT event_id, run_id, as_of, valid_until, lifecycle_id,
               ended_event_id, recorded_at
        FROM event_lifecycle_snapshots
        WHERE event_id = ?
        ORDER BY as_of DESC, recorded_at DESC
        LIMIT 1
        """,
        (event_id,),
    ).fetchone()
    if row is None:
        return None
    return LifecycleSnapshot(
        event_id=row["event_id"],
        run_id=row["run_id"],
        as_of=row["as_of"],
        valid_until=row["valid_until"],
        lifecycle_id=row["lifecycle_id"],
        ended_event_id=row["ended_event_id"],
        recorded_at=row["recorded_at"],
    )


def read_lifecycle_at_as_of(
    connection: sqlite3.Connection,
    event_id: str,
    as_of: date,
) -> LifecycleSnapshot | None:
    """读取该 event_id 在指定 as_of 时的生命周期快照。"""
    row = connection.execute(
        """
        SELECT event_id, run_id, as_of, valid_until, lifecycle_id,
               ended_event_id, recorded_at
        FROM event_lifecycle_snapshots
        WHERE event_id = ? AND as_of = ?
        ORDER BY recorded_at DESC
        LIMIT 1
        """,
        (event_id, as_of.isoformat()),
    ).fetchone()
    if row is None:
        return None
    return LifecycleSnapshot(
        event_id=row["event_id"],
        run_id=row["run_id"],
        as_of=row["as_of"],
        valid_until=row["valid_until"],
        lifecycle_id=row["lifecycle_id"],
        ended_event_id=row["ended_event_id"],
        recorded_at=row["recorded_at"],
    )


__all__ = [
    "EventIdentityConflictError",
    "LifecycleSnapshot",
    "MIGRATIONS",
    "WriteReport",
    "apply_migrations",
    "connect",
    "count_events",
    "read_latest_lifecycle",
    "read_lifecycle_at_as_of",
    "record_run",
    "write_assessment",
    "write_event_lifecycles",
    "write_events",
    "write_structures",
]
