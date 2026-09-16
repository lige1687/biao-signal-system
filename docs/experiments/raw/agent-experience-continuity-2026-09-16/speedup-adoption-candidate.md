# 提速采用候选（主控定向采用用，2026-09-16）

> 来源：只读对照分析（本任务子任务，未改任何文件）。执行者不自行重启运行服务、
> 不修改真实业务库。采用动作由主控执行。
> ⚠️ 快照时刻 2026-09-16 17:54；分析期间运行目录两个前端文件正被另一进程活跃编辑
> （AgentWorkspacePage.tsx 变了 3 次），采用前必须重新取指纹核对。

## 关键结构事实

- 开发仓库与运行仓库是**同一 git 仓库的两个 linked worktree**（共享对象库）：
  提速包 6c4f233b 在运行仓库可直接 `git show 6c4f233b:<path>` 取件，无需跨仓拷贝。
- 提交链：运行 HEAD 8ba16576 → cb71cad6 → 90df76b6 → 6c4f233b（提速包）→ 8dd78174（任务书）。
- 运行目录源码 ≈ 90df76b6 全量未提交镜像 + 并行因子工作（全部 untracked 新文件）
  + 本地 UI 工作（约 29 个 web 组件小改 + AgentWorkspacePage「买点①定位」功能，编辑中）。
- **提速包内容在运行目录为 0%**：14 个提速文件中 9 个与提速前基线逐字节相同、5 个不存在。
- 因子文件与提速 14 文件**零重叠**，采用时不需排除性特殊处理，只要不整体目录拷贝。

## 权威文件清单（90df76b6..6c4f233b，剔除 docs 后 14 个代码文件）

新文件 5：api/ask_timing.py、storage/write_tx.py、tests/unit/test_agent_ask_stability.py、
tests/unit/test_market_mood_perf.py、tests/unit/test_write_tx_tracking.py
修改 9：api/routes/agent.py(±778)、api/routes/copilot.py(±45)、copilot/chat_identity.py(±51)、
fundamentals/sources.py(±25 两融 900s TTL 缓存)、market_context/market_mood.py(±27 向量化)、
storage/sqlite_store.py(±7 connect 换 TrackedConnection，无 DDL)、
tests/unit/test_agent_name_resolve.py(±80)、web/src/components/AgentConsole.tsx(±33)、
web/src/pages/AgentWorkspacePage.tsx(±26)

## 采用候选（分三批）

**第一批·纯新增（5，零风险）**：ask_timing.py、write_tx.py、三个新测试文件。

**第二批·干净覆盖（7，运行现状逐字节 == 90df76b6）**：routes/agent.py、routes/copilot.py、
copilot/chat_identity.py、fundamentals/sources.py、market_context/market_mood.py、
storage/sqlite_store.py、tests/unit/test_agent_name_resolve.py。

**第三批·需人工定向处理（2）**：
- AgentConsole.tsx：仅 1 行本地注释差异，但正被编辑，覆盖前重新 hash-object 核对；
- AgentWorkspacePage.tsx：**唯一真冲突**——本地「买点①定位」功能（+55/-10，编辑中）
  与提速 failedRetryable 改动同文件。建议三方合并
  `git merge-file <运行副本> <(git show 90df76b6:…)> <(git show 6c4f233b:…>)`，
  保留本地 BpFocus/useBuyPointCoord 块、合入提速 failedRetryable 块；
  必须等编辑进程停手冻结后再合，合后过 tsc/build。

## 迁移/备份/回退/验证

- 迁移：**无**（无 migrations 目录；schema 为 sqlite_store.py 内联 CREATE TABLE IF NOT EXISTS，
  提速仅改 connect() 工厂，零 DDL）。
- 备份（采用前）：`sqlite3 ~/.lei_signal_lab/lab.db ".backup '~/lab.db.bak-20260916'"`；
  `tar czf ~/speedup-adopt-rollback-20260916.tgz <第二批7个+第三批2个文件的当前副本>`。
- 回退：恢复 tar 副本 + 删除第一批 5 个新文件；DB 不动。
- 隔离验证：`cp ~/.lei_signal_lab/lab.db /tmp/lei-verify/lab.db`，验证环境指向副本，不碰真实库。
- 回归命令：
  `pytest tests/unit/test_agent_ask_stability.py tests/unit/test_write_tx_tracking.py tests/unit/test_market_mood_perf.py tests/unit/test_agent_name_resolve.py tests/unit/test_agent_stream.py tests/unit/test_copilot_ops.py -q`
  `pytest tests/integration/test_agent_chat_e2e.py -q`、`ruff check src/lei_signal`、
  `cd web && npm run build`（AgentWorkspacePage 人工合并后必过 tsc）。

## 指纹（git blob SHA-1；采用后对第一+二批 12 个文件逐一 hash-object 应等于左列）

| 文件 | 6c4f233b 目标 | 运行快照（采用前） |
|---|---|---|
| api/ask_timing.py | 858a0401c79d3c4fd37304de98ca0fd40fd3a489 | ABSENT |
| api/routes/agent.py | 18961814799d238154ca380b4fff0ec012a17689 | ==90df76b6 |
| api/routes/copilot.py | 2abda8550fe91c4753e5991d185673583fbd02e4 | ==90df76b6 |
| copilot/chat_identity.py | d520cff915416f51ace7bf52925fe194786d308a | ==90df76b6 |
| fundamentals/sources.py | 211a08940e21fc471ce013612007bc739e84a517 | ==90df76b6 |
| market_context/market_mood.py | 6d8bd8503da50b9c45fc62f5d9b05d9c26979571 | ==90df76b6 |
| storage/sqlite_store.py | 6535ec9da293e368e4c655ffab687ef1a41a13cf | ==90df76b6 |
| storage/write_tx.py | f85f7efb4cb4075dcb59c3617892176f28be69ba | ABSENT |
| tests/unit/test_agent_ask_stability.py | 0b81caf38d582ba529db235cac6ec3b7329358ae | ABSENT |
| tests/unit/test_agent_name_resolve.py | ab18d6c3b919f3ff001229b1e00adc5bc32316d4 | ==90df76b6 |
| tests/unit/test_market_mood_perf.py | 032d3066dfa05f5b505ae0c26d77ac345066fd36 | ABSENT |
| tests/unit/test_write_tx_tracking.py | 629c8d5be33a6edf28901e76e6ebb0332ce1e36d | ABSENT |
| web/…/AgentConsole.tsx | 0d8c6520839719a379fb0761f43af22b155d4027 | 90df76b6+1行注释（编辑中） |
| web/…/AgentWorkspacePage.tsx | acc4f1a914fded6732cdf6f20eeeb8852c2086b2 | 90df76b6+买点定位（编辑中，勿覆盖） |
