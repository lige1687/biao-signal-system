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
数据库排队说成「AI 在想」。**资料准备变快了**（注意：这是不算 AI 回答时间的
系统资料准备速度）：之前每个问题都要把一份 14MB 的情绪数据重算一遍（实测
约 12 秒）——修掉后，**同一个进程里第一次提问**的准备全程从 23.3 秒降到
11.3 秒（省掉的是每次重复的情绪计算，剩下的主要是一次性的目录数据加载）；
**重复提问**的资料准备从约 12.4 秒降到约 0.4 秒。失败也更好收拾：以前准备
失败或断网后立刻重试，会被一句「回答正在生成」错误地挡 10 分钟；现在失败
会保留问题、给出明确的重试按钮，点了马上继续，不会重复记录；断网后系统
自己也会把卡住的登记收尾。数据库锁的日志现在会区分「谁在排队、谁的事务
开着、谁真的拿着写锁」，撞锁时能指认同一个库里的持锁任务。真实模型回答
本身的长度（约两分钟级）这次没有动。

**主控复验后的补修（2026-09-16，同一分支）**：断开连接时登记一定有人收尾
（含真实 HTTP 断开实测）；诊断包装不再改变数据库本身的事务行为（与原生
逐项对照）；问「科创50板块」保留指数身份，问「科创板块」得到简短澄清而
不是被静默带到指数。详见 §7。

## 1. 先找清楚哪里慢、为什么失败（分段计时证据）

给提问链路加了**六段计时**（收到→身份登记→资料准备→资料展示→模型首字→
回答保存，准备段内部再分检查点），结果随流式 done 的 `timing_ms` 下发并写
服务端单行日志（不含问题原文/密钥/SQL 参数）。第一份实测（临时库、全局问题
「市场环境怎么样」、**无模型 fallback 路径——表内全部是系统资料准备与落库
耗时，不含任何 AI 回答时间**）：

| 段 | 修前 | 修后（进程内首次） | 修后（重复提问） |
|---|---|---|---|
| 身份登记 | 2ms | 2ms | 1ms |
| 标的解析/目录 | 11.1s（每进程首次加载目录数据） | 9.7s（同左，未处理） | 9ms |
| 全局/标的消息材料 | **12.15s（每问都付）** | 1.55s（含两融首抓） | **0.40s** |
| 问题落库+模板+回答保存 | ~30ms | ~35ms | ~4ms |
| **全程（无模型）** | **23.3s** | 11.3s | **0.41s** |

两个比较分别成立，不合成一个「整体提速倍数」：进程内首次提问 23.3→11.3 秒
（省掉重复的 12 秒情绪计算，剩下的 9.7 秒是一次性目录数据加载，未处理）；
重复提问（无模型）约 12.4→0.41 秒。0.41 秒是**无模型情况下的资料准备
速度**，不是完整 AI 回答速度——真实模型回答仍需分钟级时间（本轮未动）。

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
（`TrackedConnection`，经主控复验 S2/S3 重写，见 §7.2/§7.3）——登记区分
**等待 / 事务开启 / 已取得写锁**三种状态（仅 BEGIN 未写入不算持锁者；
等锁失败的语句不登记；无法证明的标「未知」），每条带库文件路径；
`BEGIN IMMEDIATE` 等锁失败时日志只列**同库**持锁者（位置/线程/已持有毫秒），
慢等待（>1.5s）/慢持有（>3s）平时也记。日志不含 SQL 参数与隐私。
**诚实边界**：快照只是「本进程、已覆盖入口」的视图——**空列表不能证明
持锁者在其他进程**（也可能来自本层未知的路径），日志原文如此标注；
跨进程写者（如 launchd 独立脚本）不在登记内。

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
226MB）实测 2500 事件：逐行 73ms vs 批量 78ms——**没有收益**，批量改动已回退。
注意这个实验的边界（按主控复验意见如实标注）：它只能说明**这个合成场景
不值得改**（语句数不是该场景瓶颈），**不能**证明历史上的「5 秒」必然是
排队等待——也可能是当时的磁盘/检查点争用或其他因素，历史现场已不可复现。
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

**C. 冷启动 vs 重复读取**（A 场景同服务记录，均为无模型资料准备路径）：
冷 0.45s vs 同编号重放 0.02s（`replayed:true`）；重复新问题（§1 表）
0.41s vs 修前 ~12.4s——这是无模型资料准备速度的比较，不是完整 AI 回答
速度。

**D. 迟到内容不串入**：世代/票据守卫本轮未改动；既有验收（9/14 报告 §5D）
继续有效，前端 `test:agent-workspace`（流读取清理/滚动）通过。

**E. 不倒退**：正常完成/中途断流/刷新历史恢复——`test_agent_stream`（5）+
`test_agent_incomplete_retry`（3）+ `test_agent_ask_stability`（9，含 S1
矩阵 4 条）全过；名称/板块/ETF 专项 `test_agent_subject_names`（10）、
`test_agent_sessions`、`test_discussion_contract_r2`、
`test_llm_stream_completion`（12）、`test_llm_anthropic_stream`、
`test_agent_ux_phase1`、`test_agent_chat` 全过（合计见 §5 日志）。
**1 条既有失败**：`test_agent_name_resolve::
test_catalog_layer_resolves_index_not_in_watchlist` 在 main 上同样失败
（板块字样短路别名表，名称轮引入），与本轮无关——主控复验已给出
产品定义裁决并按定义处理（§7.4，原失败记录保留在
`raw/.../pre-existing-failures.md`）。

**F. 写锁诊断**：`test_write_tx_tracking`（15 条，含 S2/S3 矩阵）——
登记/注销、cursor 写入覆盖、等待/开启/持锁区分、按库区分快照、锁失败
日志指认同库持锁方且不含 SQL 参数、慢等待/慢持有阈值日志、with 块三
分支与原生逐项一致；存储回归 45 条全过。

**失败次数统计**：35 秒场景按设计失败 1 次（busy_timeout 30 秒耗尽），
释放后重试成功；7 秒持锁场景 0 失败（等待后正常完成）；其余场景 0 失败。

## 5. 测试与运行记录

- 后端首轮（`raw/.../tests/`）：`new-and-stream.log` 27 passed（stream/incomplete
  retry/ask-stability/write-tx/mood-perf）；`agent-regressions.log`
  （agent_chat/ux_phase1/chat_discussion/subject_names/sessions/llm_stream
  两组/discussion_contract_r2）；`name-resolve.log` 8 passed + 1 既有失败
  （主控复验已裁决处理，见 §7.4）。
- 补修轮（主控复验后，`raw/.../tests/`）：`fixround-stream-stability.log`
  38 passed（write_tx 15 / mood_perf 6 / ask_stability 9 / agent_stream 5 /
  incomplete_retry 3）；`fixround-naming-chat.log` 41 passed（name_resolve /
  subject_names / agent_chat / chat_discussion / ux_phase1）；
  copilot/resolve/sector 回归 177 passed；35 秒持锁与真实断开两个验收
  脚本重跑全过（`acceptance-lock35.json`、`acceptance-disconnect.json`）。
- 前端：`tsc --noEmit` 通过；`npm run build` 通过；agent-ux / agent-workspace /
  agent-tasks / evidence-card 四组回归通过（`tests/frontend.log`；补修轮
  未改前端文件，tsc/build 复跑通过）。
- 变更文件 ruff 增量检查干净（既有文件的存量告警未新增）。
- 全程未调用付费模型；合成模型桩只验证交互，不代表真实模型体验。
- 运行仓只读：`cn_mood`/材料块/目录加载的计时均为只读函数调用与真实缓存
  文件读取，未改任何文件、未重启服务、未写业务库；`trade_plans`/`fund_trades`
  零接触。

## 6. 未解决问题（如实）

1. **真实锁冲突的持锁者仍待运行证据**：登记与日志已就位（本进程、已覆盖
   入口的视图），需要在真实运行中撞到下一次锁时收集 `db_write_tx
   lock_failed` 日志才能指认并根治；**快照为空不能证明持锁者在其他进程**
   （也可能是本层未知的路径），跨进程写者（launchd 脚本）不在登记内——
   届时按日志实际内容单独立项，不预设结论。
2. **目录数据每进程首次加载 ~10 秒**：首问仍慢这一部分；预热到服务启动
   会拖慢重启，取舍未定，未处理（主控复验意见：不新增目录预热方案）。
3. **真实模型整段耗时（分钟级）未优化**：162 秒中非准备部分是模型时间，
   本轮范围外；`timing_ms` 已让每段可测，后续按数据决定。
4. **盘中/收盘日期措辞**（上轮遗留）与回答偏长偏术语：沿上轮意见在实际
   试用中观察，未在本轮处理。
5. 两融记忆化最长滞后 900 秒（日频叙事层指标，成分自带 as_of）；如需更紧
   可调 `LEI_MARGIN_HISTORY_TTL_SECONDS`。
6. 白酒行业在「板块专名」与「目录扫描」两条路径的身份写法不一致
   （TH881273.SECTOR vs TH881273，环境相关、名称轮之前即存在）——本轮只
   锁定产品身份，未统一写法（§7.4 附记）。
7. 主控探针（未修改）S1 段复测在其自身同步点报错（新行为下工作者不再
   为无消费者的请求做准备工作，探针的 `finished` 闸门按设计不触发）——
   详见 §7.1 与 `probe-rerun-note.md`；探针是否调整由主控决定。

## 7. 主控复验补修轮（2026-09-16）

主控独立复验结论：暂不整包合并；指出三个固定缺口与一项名称语义裁决，
在同一分支补修。主控探针 `raw/controller-ask-stability-review-2026-09-15/`
（未修改）；复测证据在 `raw/agent-ask-stability-2026-09-15/`（
`probe-counterexample-recheck.json`、`probe-rerun-note.md`、
`acceptance-disconnect.json`、`fingerprints.md`、`tests/fixround-*.log`）。

### 7.1 S1：断开时生成权必须有人负责收尾（高优先级）

- **修前**（主控探针实测）：回执后、领号前关闭路由生成器，随后允许后台
  真实登记完成——`answer_state=generating` 无人收尾，同一请求马上重试
  返回 `kind=incomplete` 而不是恢复生成。根因：首条 yield 在 try/finally
  之前，且生成权只在消费者读到 entered 事件后落到局部变量；消费者提前
  退出时，后台线程仍可晚领号而无人释放。执行方另实测：**真实 HTTP 断开**
  时 uvicorn 不及时取消流任务，生成器长期悬挂，claim 同样无人收尾——
  手动 close Python 生成器不能当作真实断开的验证。
- **修后**：后台工作者与流消费者共用 `_StreamState`
  （cancelled/outcome/terminal）——消费者 finally 无条件标记取消；
  工作者领号后先登记，发现已取消立即收尾、不开始准备/生成；清理只放
  自己的领取（claim_state_at CAS，无 state_at 一律不动），不触碰重试者
  的新领取。真实断开检测：`_http_disconnect_poll` 以近零超时读 ASGI
  receive 通道（生产=anyio 工作线程内经 `from_thread.run` 回事件循环；
  测试主线程无 token 按未断开处理，由 close/finally 收尾），心跳与逐
  token 检查，发现断开即停止生成并收尾。
- **验收矩阵**（`test_agent_ask_stability.py` 新增 4 条 +
  `acceptance_disconnect.py`，零付费模型）：

  | # | 场景 | 修前 | 修后 |
  |---|---|---|---|
  | 1 | 回执后领号前断开，再放行登记 | generating 卡死，重试 incomplete | pending，重试 proceed ✓ |
  | 2 | 领号成功但消费者未读 entered 断开 | 同上 | 同样收尾 ✓ |
  | 3 | 准备期间/首段正文后断开 | 见既有断连处理 | 不重复问题、迟到隔离保持 ✓ |
  | 4 | 旧工作者迟到完成撞上重试 | 可能误放重试者生成权 | 重试者终态不被触碰、不重复问题 ✓ |
  | 5 | 隔离 uvicorn 真实客户端断开+重试 | claim 不释放（≥15s） | claim→pending；重试 answered；生成调用=2；user 消息=1 ✓ |

- **探针复测说明**：未修改的探针副本复测时，S2/S3 段全部通过（见 §7.2/7.3），
  S1 段在探针自身的同步点（`finished.wait(5)`，位于按新设计不再执行的
  `fake_prepare` 内）报错——探针真正要验收的终态（pending/proceed）由
  矩阵 1 同场景覆盖；详情 `probe-rerun-note.md`。未修改为探针通过而
  调整探针。

### 7.2 S2：诊断包装不能改变数据库原行为（高优先级）

- **修前**（主控实测）：`TrackedConnection.__exit__` 自行调用 commit，
  延迟外键提交失败时漏掉原生回滚——`in_transaction=true`、未提交行数 1
  （原生为 false/0），事务可能继续占锁。
- **修后**：`__exit__`/`commit`/`rollback`/`executescript` 全部委托原生
  实现，登记只在边界后按 `in_transaction` **真实状态**同步——提交失败
  （延迟外键）时与原生逐项一致（异常类型 IntegrityError、
  in_transaction=false、未提交行数 0）；SQL 级 COMMIT/ROLLBACK、
  executescript 留未结束事务、close 均按真实状态同步，不残留、不提前消失。
- **复测**：`probe-counterexample-recheck.json`（与探针同操作序列）——
  `commit_failure == commit_failure_native == (false, 0)`；
  `test_write_tx_tracking.py` 15 条全过。

### 7.3 S3：诊断必须区分等待、事务开启与已取得写锁（中优先级）

| 主控反例 | 修前 | 修后（复测 `probe-counterexample-recheck.json`） |
|---|---|---|
| `conn.cursor().execute(INSERT)` 开了写事务但快照为空 | tracked=[] | tracked 含 write_lock、库路径正确（TrackedCursor 接入） |
| 仅 BEGIN 未写入被登记成持锁者 | explicit 持锁者 | `tx_open_no_write`，不是持锁者 |
| 等锁失败的 INSERT 等待方出现在活跃写者 | 在册 | 不登记（tracked=[]） |

另按固定要求：BEGIN IMMEDIATE 成功才起算持锁（等待不计入）；快照带库
路径、锁失败日志只列同库持锁者；无法证明的状态标 `unknown_open`；报告与
日志均删除「进程内快照为空就证明是其他进程持锁」的推论（空列表也可能
来自未覆盖入口）。

### 7.4 名称/板块语义裁决（独立小提交 `1d4ad8f8`）

按主控产品定义实现：明确说「科创50」（即使句中另有「板块」二字）保留
指数身份（目录层与 resolve API 都把明确别名/目录全名置于板块关键词之
前）；「科创」「科创板」移出口语别名表，板块泛指不再静默映射到指数；
「科创板块/科创板整体」由 resolve 接口给简短澄清——科创50 仅作可选
观察参考并明确「50 只成分股的指数，不代表整个板块」；通信板块/版块与
通信ETF 行为不变，未恢复板块→ETF 顶替。旧测试按定义更新（原失败记录
与定义调整保留在 `pre-existing-failures.md`）。
**复测**：`test_agent_name_resolve.py`（10，含更新后的原失败用例与新增
resolve 澄清用例）+ `test_agent_subject_names.py`（10）全过；
copilot/resolve/sector 回归 177 过。附记：白酒行业在两条查找路径的
身份写法不一致（.SECTOR 后缀有无）为名称轮之前即存在的环境相关现象，
只锁定产品身份，未统一写法（§6.6）。

### 7.5 补修轮回归与指纹

- `tests/fixround-stream-stability.log`：write_tx 15 + mood_perf 6 +
  ask_stability 9 + agent_stream 5 + incomplete_retry 3 = **38 passed**；
- `tests/fixround-naming-chat.log`：name_resolve 10 + subject_names 10 +
  agent_chat/chat_discussion/ux_phase1 等 = **41 passed**；
- 35 秒持锁验收重跑（S1 改动后）：11 项检查全过（`acceptance-lock35.json` 已更新）；
- 前端：本轮未改前端文件；`tsc --noEmit` 与 `npm run build` 复跑通过；
- 源指纹（main→分支逐文件 SHA256 前缀）：`fingerprints.md`；
- 未重跑付费模型案例（按主控指示零付费模型）。

## 8. 合并清单（合回 main 用）

分支 `agent-ask-stability-20260915`（基于 main `90df76b6`），提交按序：

| 提交 | 内容 | 文件 |
|---|---|---|
| `7f0d83cb` | 写事务登记与锁诊断 | `src/lei_signal/storage/write_tx.py`（新）、`src/lei_signal/storage/sqlite_store.py`（connect 工厂）、`tests/unit/test_write_tx_tracking.py`（新） |
| `ea598eb1` | 分段计时、失败释放生成权、回执与心跳 | `src/lei_signal/api/ask_timing.py`（新）、`src/lei_signal/api/routes/agent.py`、`src/lei_signal/copilot/chat_identity.py`、`tests/unit/test_agent_ask_stability.py`（新） |
| `0f83b4a6` | 情绪材料去重计算 | `src/lei_signal/market_context/market_mood.py`、`src/lei_signal/fundamentals/sources.py`、`tests/unit/test_market_mood_perf.py`（新） |
| `38f85fcf` | 前端两入口失败重试/心跳去重/如实提示 | `web/src/pages/AgentWorkspacePage.tsx`、`web/src/components/AgentConsole.tsx` |
| `d1112719` | 普通入口保存失败释放 + ruff 清理 | `src/lei_signal/api/routes/agent.py`、三个测试文件 |
| `72f704b1` | S2/S3：诊断不改事务语义、区分等待/开启/持锁、覆盖 cursor | `src/lei_signal/storage/write_tx.py`、`tests/unit/test_write_tx_tracking.py`（重写） |
| `d4933049` | S1：断开时生成权收尾（共享状态+真实断开检测） | `src/lei_signal/api/routes/agent.py`、`tests/unit/test_agent_ask_stability.py`、`raw/.../acceptance_disconnect.py`+`.json` |
| `1d4ad8f8` | 名称/板块语义按主控裁决（独立小提交） | `src/lei_signal/api/routes/agent.py`（别名表+目录层顺序）、`src/lei_signal/api/routes/copilot.py`（resolve 澄清）、`tests/unit/test_agent_name_resolve.py`、`raw/.../pre-existing-failures.md` |
| `e91ab70a`、`e5ed4d53` | 报告与登记（首轮） | 报告、raw、registry、INDEX |
| （本报告更新提交） | 主控复验补修轮报告与证据 | 报告 §1/§2/§4C/§6/§7/§8 修订、`raw/.../probe-counterexample-recheck.*`、`probe-rerun-note.md`、`acceptance-disconnect.json`、`fingerprints.md`、`tests/fixround-*.log` |

合入注意：① 前端改动需重新 build 后同步 `web/dist`；② 无数据库迁移
（无 schema 变更）；③ `connect` 工厂换成 TrackedConnection 是行为等价
包装（事务语义委托原生，登记按真实事务状态同步），全仓经
`sqlite_store.connect` 的连接自动获得登记；④ 阈值可用
`LEI_DB_SLOW_WAIT_MS`/`LEI_DB_SLOW_HOLD_MS` 调整；⑤ 合入后按上轮流程在运行
入口复验真实首问——「等待方+持锁方」日志已备好。

## ARCHIVE

- 分类：数据与质量；verdict：passed（仅指本报告所列固定改动、固定验收与
  所列检查，含主控复验补修轮 S1/S2/S3 与名称语义用例；真实运行锁冲突的
  根治与真实模型体验不在通过范围）。
- 原始材料：`docs/experiments/raw/agent-ask-stability-2026-09-15/`——
  `acceptance_lock35.py`、`acceptance-lock35.json`（35 秒持锁全事件时间线，
  S1 改动后重跑）、`acceptance_disconnect.py`、`acceptance-disconnect.json`
  （真实 HTTP 断开+重试）、`prepare-before-after.json`（分段修前修后）、
  `probe-counterexample-recheck.py`/`.json`（主控反例复测）、
  `probe-rerun.py`（未修改的主控探针原样副本）、`probe-rerun-note.md`、
  `pre-existing-failures.md`、`fingerprints.md`、
  `tests/`（含 fixround-stream-stability.log、fixround-naming-chat.log）。
- 生命周期快照批量化的负面结果已记录在 `prepare-before-after.json`，
  改动回退未交付。未声称收益、未声称真实模型质量、未声称锁已根治；
  「进程内快照为空=其他进程持锁」的推论已按主控复验意见删除。
