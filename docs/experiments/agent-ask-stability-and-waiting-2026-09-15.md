# Agent 提问稳定性与等待体验 — 2026-09-15

日期：2026-09-15。任务书：改善 Agent 提问稳定性与等待体验（先找清楚哪里慢、
为什么失败；针对证据修；把等待和失败讲明白；固定验收）。
开发位置：`/Users/yongbiaoli/lei-agent-main-consolidation-20260915`，
临时开发分支 `agent-ask-stability-20260915`（基于 main `90df76b6`）。
运行仓 `/Users/yongbiaoli/Desktop/lei-signal-lab` 全程只读（只做了只读计时
测量与函数计时，未改文件、未重启服务、未写业务库）。**未调用任何付费模型**：
全部验收用合成模型流/fallback 模板与临时库完成，合成测试不冒充真实模型体验。

## 一句话结论（大白话）

问问题现在**一提交就有回音**（0.1 秒内显示「已收到问题」）；系统被后台任务
卡住时，页面每 5 秒如实告诉你「在排队、排了多久」，不再像死机，也不会把
数据库排队说成「AI 在想」。**重复提问少等约 12 秒**：之前每个问题都要把一份
14MB 的情绪数据重算一遍（实测 12 秒），修掉后重复提问的资料准备从约 12.4 秒
降到约 0.4 秒。失败也更好收拾：以前准备失败或断网后立刻重试，会被一句
「回答正在生成」错误地挡 10 分钟；现在失败会保留问题、给出明确的重试按钮，
点了马上继续，不会重复记录。数据库锁失败现在还查不清「当时谁在持锁」——
这次给系统装上了「持锁登记」：以后再撞锁，日志会直接指出是哪个任务、
持了多久。真实模型回答本身的长度（约两分钟级）这次没有动。

## 1. 先找清楚哪里慢、为什么失败（分段计时证据）

给提问链路加了**六段计时**（收到→身份登记→资料准备→资料展示→模型首字→
回答保存，准备段内部再分检查点），结果随流式 done 的 `timing_ms` 下发并写
服务端单行日志（不含问题原文/密钥/SQL 参数）。第一份实测（临时库、全局问题
「市场环境怎么样」、无模型 fallback 路径）：

| 段 | 修前 | 修后（进程内首次） | 修后（重复提问） |
|---|---|---|---|
| 身份登记 | 2ms | 2ms | 1ms |
| 标的解析/目录 | 11.1s（每进程首次加载目录数据） | 9.7s（同左，未处理） | 9ms |
| 全局/标的消息材料 | **12.15s（每问都付）** | 1.55s（含两融首抓） | **0.40s** |
| 问题落库+模板+回答保存 | ~30ms | ~35ms | ~4ms |
| **全程** | **23.3s** | 11.3s | **0.41s** |

热点定位（真实数据、只读计时）：
- `market_mood.cn_mood()` **每次调用 12.0–12.2 秒**：其中 `_cn_small_flow20`
  对两个合计 ~14MB 的板块资金流 JSON 逐点 `pd.to_datetime` 聚合，单次 10.9 秒；
  两融成分每次翻页联网 ~1 秒。讨论准备段（标的/全局两路径）每个提问都调它——
  这是上轮「每轮准备 11.9–23.5 秒」的主要构成，也是「162 秒不能全归因于模型」
  的直接证据（其余为模型时间，本轮未动）。
- 目录数据加载 ~10 秒是**每进程一次性**（第二次调用 0.02s），解释「运行首问
  格外慢」的一部分；本轮未处理（见 §6 未解决）。
- 标的讨论路径的其余材料块实测都很便宜（买点审阅 0.09s、形态/经验/胜率 ~0s），
  不为它们设第二套缓存（任务书：只复用证据支持的重复工作）。

锁失败的持锁者：给 `sqlite_store.connect` 统一接入**写事务登记**
（`TrackedConnection`）——显式 `BEGIN IMMEDIATE` 与隐式写事务都登记位置
（模块:行号 函数）、线程、开启时刻；`BEGIN IMMEDIATE` 等锁失败时日志带出
**当时进程内活跃写者快照**（位置/已持有毫秒），慢等待（>1.5s）/慢持有（>3s）
平时也记。日志不含 SQL 参数与隐私。单测锁定：持锁方开着写事务时，等待方
失败日志能指认持锁方位置（`test_write_tx_tracking.py` 8 条）。
**边界**：跨进程写者（如 launchd 独立脚本）不在进程内注册表——审计过
newsfeed 管线与补测 worker，它们的写都短促（网络/重计算不在事务内），
进程内登记已覆盖后台预热/分析持久化/聊天这些同进程写者。

## 2. 针对证据的修复

| 修复 | 证据 | 效果（实测） |
|---|---|---|
| `_cn_small_flow20` 向量化（合并语义逐项保留：同一 (date,code) 两文件重复先出现者为准） | 每问 10.9s | 10.9s→0.2s；真实文件 A/B 差 ≤1e-11 浮点序噪声，下游取整完全一致；旧算法内联对照单测锁定 |
| `fetch_margin_history` 进程内 TTL 记忆化（900s，日频叙事层指标，返回字典自带真实日期键，失败不缓存） | 每问翻页联网 ~1s×（cn_mood+融资环境两处） | `cn_mood` 12.1s→首次 1.2s→后续 0.3s；情绪判定结果不变（冷）；`margin_regime_cn` 0.95s→0.30s→0.00s |
| 失败/断连释放生成权（`release_generation`，claim_state_at CAS 防误伤租约新主）：准备失败/问题落库失败/回答保存失败/客户端断连 | 修前 claim 卡 `generating`，同身份重试被「回答正在生成或重试中」挡满 600 秒租约 | 同 cid 重试立即恢复（resume/proceed），不重复建问题（单测：模型调用 2 次、user 消息 1 条） |
| 模型流意外异常按未完成收场（`generation_error`），不再逃出流卡死 claim | 代码走查（异常路径无处理） | 部分正文保留 + 未完成标记，走既有重试 |
| 普通入口（/agent/chat）准备/落库/保存失败同样释放生成权 | 与流式同一缺陷 | 补测建档路径不再留 600 秒卡死窗口 |

**遵守任务书的两个「不」**：没有预先重写数据库层（WAL/30s busy_timeout 经
实测判断不动——见下）；没有靠加长超时掩盖问题（30s 不变，失败如实呈现+可重试）。

**做过但回退的「修复」（负面结果，防止后人重复劳动）**：历史注释称 analyze
持久化 `event_lifecycle_snapshots` 的写事务「可超 5 秒」。把逐行写改成
「IN 批量身份核对 + executemany」后，在合成生产量级库（60 万事件/100 万快照，
226MB）实测 2500 事件：逐行 73ms vs 批量 78ms——**没有收益**。该写事务不是
语句数瓶颈；历史「5 秒」更可能是写锁**排队等待**而非持锁计算。批量改动已回退；
锁等待改由 slow_wait/lock_failed 日志直接在运行中指认。
（`raw/agent-ask-stability-2026-09-15/prepare-before-after.json` 存完整数据。）

复用纪律（任务书§二）：两融记忆化复用的是**同一 lookback 的同一日频指标**
（对象/口径/配置一致），返回字典以真实日期为键原样返回，不把旧数据说成当前
数据；`cn_mood` 各成分自带 as_of。未做整包讨论材料缓存——实测标的路径其余
块都很便宜，不满足「已证明的重复」门槛。

## 3. 等待和失败讲明白（两入口一致）

- **提交即回执**：流式协议第一个事件就是 `stage received`（「已收到问题，
  正在登记请求」）；首事件到达前的占位文案从「正在读取资料…」改为
  「已提交，等待系统确认…」（工作台与标的控制台一致）。
- **真实阶段心跳**：排队期间服务端每 5 秒发 `stage waiting`——登记阶段说
  「等待系统处理：正在登记请求（数据库繁忙时需排队，已等待 N 秒）」，准备阶段
  说「仍在读取系统资料（已等待 N 秒）」。不虚构进度条/倒计时，**数据库等待
  不描述成 AI 思考**（单测断言心跳文案无「AI」字样）；前端同键心跳只保留最新
  一条，过程列表不刷屏。
- **资料就绪即展示**：沿用上一轮 prepared 事件（本轮未改语义），两入口保留。
- **失败保留问题+明确重试**：失败 done 用 `answer_state:"failed"` +
  `retryable` + 如实文案（数据库被占用就说数据库被占用，含
  `database is locked` 原文）；两入口渲染「重试这个问题（沿用原请求，
  不重复记录）」按钮，走补修二的同 cid 通道；网络错误/连接提前结束同样给
  重试入口（服务端幂等，重试安全）。
- **保持既有能力**：「回答未完成」标记、同身份重试、迟到响应世代隔离、
  历史恢复、计划确认与中断重试——全部回归通过（§4），未改语义。

## 4. 固定验收（临时库 + 合成行情/模型桩）

**A. 持锁 35 秒**（真实 uvicorn + httpx 流，不用会缓冲的 TestClient；
`raw/.../acceptance_lock35.py` → `acceptance-lock35.json`，11 项检查全过）：

| 时刻 | 事件 |
|---|---|
| 0.06s | 「已收到问题，正在登记请求」 |
| 5–30s | 每 5 秒一条「等待系统处理（已等待 N 秒）」心跳 |
| 31.9s | 失败 done：`answer_state=failed`、`retryable=true`、文案含 database is locked 与重试说明 |
| 释放后 | 同 cid 重试成功（claim 终态 answered，user 消息恰好 1 条） |

**B. 断线重试**（单测矩阵）：客户端断连→claim 释放回 pending→同 cid 重试
立即再生成（模型调用 2 次）、不重复建问题（user 消息 1 条）；中断半场
（StreamInterrupt）沿用补修二矩阵（incomplete→重试再生成→完成后只回放）。

**C. 冷启动 vs 重复读取**（A 场景同服务记录）：冷 0.45s vs 同编号重放 0.02s
（`replayed:true`）；重复新问题（§1 表）0.41s vs 修前 ~12.4s。

**D. 迟到内容不串入**：世代/票据守卫本轮未改动；既有验收（9/14 报告 §5D）
继续有效，前端 `test:agent-workspace`（流读取清理/滚动）通过。

**E. 不倒退**：正常完成/中途断流/刷新历史恢复——`test_agent_stream`（5）+
`test_agent_incomplete_retry`（3）+ `test_agent_ask_stability`（5）全过；
名称/板块/ETF 专项 `test_agent_subject_names`（10）、`test_agent_sessions`、
`test_discussion_contract_r2`、`test_llm_stream_completion`（12）、
`test_llm_anthropic_stream`、`test_agent_ux_phase1`、`test_agent_chat` 全过
（合计见 §5 日志）。**1 条既有失败**：`test_agent_name_resolve::
test_catalog_layer_resolves_index_not_in_watchlist` 在 main 上同样失败
（板块字样短路别名表，名称轮引入），与本轮无关，记录待主控裁决
（`raw/.../pre-existing-failures.md`）。

**F. 写锁诊断**：`test_write_tx_tracking`（8 条）——登记/注销、锁失败日志
指认持锁方且不含 SQL 参数、慢等待/慢持有阈值日志、与原生连接行为一致；
存储回归 45 条全过。

**失败次数统计**：35 秒场景按设计失败 1 次（busy_timeout 30 秒耗尽），
释放后重试成功；7 秒持锁场景 0 失败（等待后正常完成）；其余场景 0 失败。

## 5. 测试与运行记录

- 后端（`raw/.../tests/`）：`new-and-stream.log` 27 passed（stream/incomplete
  retry/ask-stability/write-tx/mood-perf）；`agent-regressions.log`
  （agent_chat/ux_phase1/chat_discussion/subject_names/sessions/llm_stream
  两组/discussion_contract_r2）；`name-resolve.log` 8 passed + 1 既有失败。
- 前端：`tsc --noEmit` 通过；`npm run build` 通过；agent-ux / agent-workspace /
  agent-tasks / evidence-card 四组回归通过（`tests/frontend.log`）。
- 变更文件 ruff 增量检查干净（既有文件的存量告警未新增）。
- 全程未调用付费模型；合成模型桩只验证交互，不代表真实模型体验。
- 运行仓只读：`cn_mood`/材料块/目录加载的计时均为只读函数调用与真实缓存
  文件读取，未改任何文件、未重启服务、未写业务库；`trade_plans`/`fund_trades`
  零接触。

## 6. 未解决问题（如实）

1. **真实锁冲突的持锁者仍待运行证据**：登记与日志已就位（进程内视图），
   需要在真实运行中撞到下一次锁时收集 `db_write_tx lock_failed` 日志才能
   指认并根治；跨进程写者（launchd 脚本）不在登记内，如日志显示进程内无
   活跃写者仍撞锁，则持锁者在别的进程，届时单独立项。
2. **目录数据每进程首次加载 ~10 秒**：首问仍慢这一部分；预热到服务启动
   会拖慢重启，取舍未定，未处理。
3. **真实模型整段耗时（分钟级）未优化**：162 秒中非准备部分是模型时间，
   本轮范围外；`timing_ms` 已让每段可测，后续按数据决定。
4. **名称解析 1 条既有失败**（板块字样短路别名表）：待主控裁决是否名称轮
   有意行为（§4E）。
5. **盘中/收盘日期措辞**（上轮遗留）与回答偏长偏术语：沿上轮意见在实际
   试用中观察，未在本轮处理。
6. 两融记忆化最长滞后 900 秒（日频叙事层指标，成分自带 as_of）；如需更紧
   可调 `LEI_MARGIN_HISTORY_TTL_SECONDS`。

## 7. 合并清单（合回 main 用）

分支 `agent-ask-stability-20260915`（基于 main `90df76b6`），提交：

| 提交 | 内容 | 文件 |
|---|---|---|
| `7f0d83cb` | 写事务登记与锁诊断 | `src/lei_signal/storage/write_tx.py`（新）、`src/lei_signal/storage/sqlite_store.py`（connect 工厂）、`tests/unit/test_write_tx_tracking.py`（新） |
| `ea598eb1` | 分段计时、失败释放生成权、回执与心跳 | `src/lei_signal/api/ask_timing.py`（新）、`src/lei_signal/api/routes/agent.py`、`src/lei_signal/copilot/chat_identity.py`、`tests/unit/test_agent_ask_stability.py`（新） |
| `0f83b4a6` | 情绪材料去重计算 | `src/lei_signal/market_context/market_mood.py`、`src/lei_signal/fundamentals/sources.py`、`tests/unit/test_market_mood_perf.py`（新） |
| `38f85fcf` | 前端两入口失败重试/心跳去重/如实提示 | `web/src/pages/AgentWorkspacePage.tsx`、`web/src/components/AgentConsole.tsx` |
| `d1112719` | 普通入口保存失败释放 + ruff 清理 | `src/lei_signal/api/routes/agent.py`、三个测试文件 |
| （本报告提交） | 报告与验收材料 | `docs/experiments/agent-ask-stability-and-waiting-2026-09-15.md`、`docs/experiments/raw/agent-ask-stability-2026-09-15/`、`docs/experiments/registry.json`、`docs/experiments/INDEX.md` |

合入注意：① 前端改动需重新 build 后同步 `web/dist`；② 无数据库迁移
（无 schema 变更）；③ `connect` 工厂换成 TrackedConnection 是行为等价
包装，全仓经 `sqlite_store.connect` 的连接自动获得登记；④ 阈值可用
`LEI_DB_SLOW_WAIT_MS`/`LEI_DB_SLOW_HOLD_MS` 调整；⑤ 合入后按上轮流程在运行
入口复验真实首问——本次已把「等待方+持锁方」日志都备好。

## ARCHIVE

- 分类：数据与质量；verdict：passed（仅指本报告所列固定改动、固定验收与
  所列检查；真实运行锁冲突的根治与真实模型体验不在通过范围）。
- 原始材料：`docs/experiments/raw/agent-ask-stability-2026-09-15/`——
  `acceptance_lock35.py`、`acceptance-lock35.json`（35 秒持锁全事件时间线）、
  `prepare-before-after.json`（分段修前修后）、`pre-existing-failures.md`、
  `tests/`（后端 3 份日志 + 前端日志）。
- 生命周期快照批量化的负面结果已记录在 `prepare-before-after.json`，
  改动回退未交付。未声称收益、未声称真实模型质量、未声称锁已根治。
