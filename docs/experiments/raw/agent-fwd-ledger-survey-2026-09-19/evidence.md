# evidence — agent-fwd-ledger-survey-2026-09-19

仓库：`/Users/yongbiaoli/lei-agent-runtime-adoption-20260917`，分支 `codex/agent-runtime-adoption-20260917`（HEAD c5d0fc3a）。核查日期 2026-09-19，全部只读。

## 1. 账本 A：情绪线 JSON 账本

- 存储路径定义：`scripts/sentiment_journal.py:28-29`
  ```python
  CACHE = Path(os.environ.get("LEI_CACHE_ROOT", str(DEFAULT_CACHE_DIR)))
  JOURNAL = CACHE / "sentiment_signal_journal.json"
  ```
- 写入（record，幂等按 date）：`scripts/sentiment_journal.py:50-108`；记录结构 date/cn_cold/picks/alarms/as_of/review（L71-75）；推送文案含「research_proxy·非买卖点·前向存证中」（L89）。
- 对账（review）：`scripts/sentiment_journal.py:111-172`；分桶 pick10/pick20/alarm10/alarm20（L129, L135-137）；「全部到期才写」（L146）；写回 JSON 并打印战绩（L153-171）。
- 调度链：`scripts/launchd/com.lei.sector.trend.plist`（ProgramArguments 指向 `precompute_sector_trend.py`）→ `scripts/precompute_sector_trend.py:106-118`（子进程调 `sentiment_journal.py record`）。
- review 无调度：`ls scripts/launchd/` 19 个 plist，无任何条目调 `sentiment_journal.py review`；`docs/ops/运维手册.md:146` 原文「`review` 子命令可随时看 T+10/T+20 前向战绩」。
- 注意：`com.lei.sentiment.weekly.plist` 是 **fetch_sentiment_weekly.py**（NAAIM/AAII 周数据抓取），与存证账本无关。

## 2. 账本 B：recommendation_journal SQLite 表

- schema：`src/lei_signal/storage/sqlite_store.py:828-838`
  ```sql
  CREATE TABLE IF NOT EXISTS recommendation_journal (
      journal_id TEXT PRIMARY KEY, run_date TEXT NOT NULL UNIQUE,
      payload TEXT NOT NULL, outcome TEXT, outcome_at TEXT,
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
  ```
- 写入：`src/lei_signal/copilot/journal.py:20-37`（save_recommendation，ON CONFLICT(run_date) 覆盖 payload）。
- 对账：`src/lei_signal/copilot/journal.py:133-174`（score_journal_outcomes，horizons=(1,5,20)，只补 outcome IS NULL 且 run_date < today 的行）。
- 每日跑批：`scripts/copilot_daily.py:125-137`（存证+ops+score_journal_outcomes+commit）；launchd `scripts/launchd/com.lei.copilot.daily.plist`（每日 16:10，WorkingDirectory `/Users/yongbiaoli/lei-signal-sync`）。
- API 写入：`src/lei_signal/api/routes/copilot.py:127-141`（GET /copilot/recommend save=true）、`:230-237`（chat dispatch recommend 分支）。
- 读取方：`src/lei_signal/api/routes/copilot.py:608-610`（ops_today 仅 load_recommendation 当日卡）。`load_outcome`（journal.py:89-99）在 routes/web/tests 生产路径零调用（grep 命中仅 `tests/unit/test_copilot_outcome.py`、`tests/unit/test_copilot_journal.py`、`test_discussion_backtest_03b.py` 为测试）。

## 3. 账本 C：统一观察账本 schema（零接线）

- 迁移 023：`src/lei_signal/storage/sqlite_store.py:850-941`（agent_observations + agent_observation_outcomes；注释「总任务书 §3.6 前向验证闭环统一机制」「旧 recommendation_journal / sentiment_signal_journal.json 原样保留（兼容读），历史通过 observation.backfill_* 幂等迁入」；含 layer 字段默认 'observation'、status pending/ready/missing_data/not_applicable）。
- 迁移 024：`:955-1010`（record_type/sample_key/eval_config_hash/批次链/legacy_quality/display_status/recommendation_journal_history）。
- 迁移 025：`:1011-1036`（eval_config_json + rule/evidence/data_refs_frozen + first_shown_at + 旧行 legacy_quality='unknown'）。
- 迁移 026：`:1037-1085`（agent_observation_batch_members 三层事实表）。
- 零接线证据：`grep -rn "agent_observations" src/ scripts/ tests/ web/ | grep -v sqlite_store.py | grep -v __pycache__` → 空结果（exit=1）。
- 合入来源：`git log --oneline -- src/lei_signal/storage/sqlite_store.py` 首条 `96a6bf55 feat(agent): 采用已验收Agent改动（S1清单24项，来源main@f8638b9f）`。
- 部署状态旁证：`docs/experiments/agent-runtime-adoption-final-review-2026-09-17.md`（INDEX 摘行「候选与采用工具准备通过，未部署」）。
- journal.py 现行写入未填 024 新增的 payload_hash/outcome_payload_hash 列（`journal.py:20-37` INSERT 无这些列）——024 的版本绑定契约在本运行仓尚未生效。

## 4. 检索命令留痕

```
grep -rn "ledger\|存证\|对账\|reconcil" src/lei_signal/copilot/ scripts/ -l
grep -rn "agent_observations" src/ scripts/ tests/ web/
grep -rn "load_outcome|list_journal_dates|load_recommendation" src/ scripts/ tests/
grep -rn "sentiment_signal_journal" web/src -ri
cat scripts/launchd/com.lei.{sentiment.weekly,copilot.daily,copilot.weekly,sector.trend}.plist
```
