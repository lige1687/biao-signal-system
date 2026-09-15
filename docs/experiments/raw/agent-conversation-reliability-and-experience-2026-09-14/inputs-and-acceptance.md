# 固定输入与验收表（实施前冻结）

任务书：给执行 Agent——真实问答可用性与回答体验（因子接入前的一期），v1.0，2026-09-14。
关联 OKR：`okr-8f4f1a5f026f`。

## 固定输入

- 真实模型案例标的：**510300**（沪深300ETF）。
- 行情：本机已有缓存 `~/.lei_signal_lab/cache/510300.SS.bars.parquet`
  （sha256 见 environment.json；末日 2026-09-04）。禁止联网补行情。
- 模型：运行仓 `.env` 保存的应用配置（ANTHROPIC_*，ark `/api/plan` 网关，
  model `ark-code-latest`，timeout 180s，max_tokens 16000）。不换供应商、不买额度。
- 临时业务库：每次隔离服务一个全新 temp SQLite，不迁入用户历史。
- 真实模型请求预算：4 轮 + 1 次失败重试 = 最多 5 次。

## 固定四问（验收 C，逐轮保留原文与耗时）

1. 510300 最近怎么看？先说判断，再讲机会和风险，现有依据够不够？
2. 这个判断哪些有历史依据，哪些只是当前观察？现在能不能给胜率？
3. 我先不买，只观察。接下来具体看哪些变化，什么情况再来讨论？
4. 假如后来满足入场条件，进入、失效和退出该怎样讨论？现在还缺哪些信息？先别替我保存计划。

## 基线现象（改前）

### 基线一：运行版首问 `database is locked`

- 事实来源：`docs/experiments/agent-real-conversation-case-2026-09-14.md`（运行版
  localhost:5173+8000，浏览器真实首问，最终显示「准备阶段失败：database is locked」）。
- 本次只读补充诊断（2026-09-14）：
  - 运行后端 PID 1790，2026-09-11 10:21:57 启动于运行仓目录；聊天路径核心文件
    （agent.py 9/9、sqlite_store.py 9/8、sessions.py 9/8、llm.py 9/10）mtime 均早于
    启动时刻 → 运行进程 = 当前磁盘代码，代码漂移排除（research/ 下 7 个因子线文件
    晚于启动，但不在聊天路径）。
  - 当天 18:49:20–18:55:21 运行后端跑了 360.5s 的 overseas 预热；首问发出于 18:59。
  - err 日志 9/14 当天 0 条 locked 堆栈：`_work()` 线程把准备段异常吞进 SSE 事件、
    不打日志（`agent.py` chat/stream `_work` except 分支）——可观测性缺陷。
  - err 日志历史有同类锁证据：watchlist delete、newsfeed bilibili/gnews 写库失败
    （「newsfeed … 失败: database is locked」）；当前仅运行后端自身打开 lab.db
    （WAL，-wal 88MB）。
  - 聊天路径自身写为 `BEGIN IMMEDIATE` 短事务（chat_identity.py 258/278）；
    connect() 已有 timeout=30 + WAL。→ 触发条件=存在持续持写锁 >30s 的写者
    （后台预热/分析持久化/newsfeed 均为候选；当天 18:59 的具体语句因无日志不可指认）。

### 基线二：隔离版真实模型 180s 超时

- 事实来源：上轮 raw `server-app-config.log`：
  `ark 调用异常：ReadTimeout … read timeout=180.0（model=ark-code-latest）`；
  conversation.json 显示问题与备用回答相隔 180s，grounded=false。
- 代码归因（dev b30ee97e）：`chat_discussion_stream` → `_request_completion_stream`
  对非 OpenAI 风格（含本配置的 `/api/plan` Anthropic 风格）**直接退化为
  `_request_completion` 一次性非流式请求**（llm.py 906-919）；思考型模型长输入
  thinking 期间无字节 → 180s 读超时。同文件 `_post_user_content` 注释已记录
  「非流式长输入会读超时；流式实测可用」（为买点路径所建 `_post_streaming_anthropic`，
  讨论路径未复用）。

## 验收表（任务书 §6 固定，完成情况见报告 A–E 节）

| 编号 | 必须验证 | 状态（实施前） |
|---|---|---|
| A | 两类首问失败分别有证据、明确归属；产品缺陷与脚手架问题分开 | 待验证 |
| B | 可控模型延迟/超时下，真实前端先显示已准备事实，失败后保留；三段时间记录 | 待验证 |
| C | 同一真实模型四轮案例，逐轮问题/回答原文/依据身份/耗时/人工评价 | 待验证 |
| D | 两入口分阶段展示；切会话迟到响应不串入；刷新恢复原问题最终状态；不重复记录 | 待验证 |
| E | 同样事实改前/改后表达对照 | 待验证 |
