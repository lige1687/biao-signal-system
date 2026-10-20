# Agent 消息可靠性 S1：可靠采集状态与官方事件材料（2026-09-17）

> 阶段交付报告（S1/共2阶段），执行者 Ark Agent，主控 Codex。
> 计划：`docs/archive/handoffs-plans/2026-09-17-agent-news-reliability-plan.md`
> （SHA256 7b2fa2a8…45e5）；合同与同目录 contract.json。
> **本阶段未结案**：S2（Agent 展示与恢复包）须主控书面复核后另发。
> 全部改动在隔离工作区 W（`scripts/agents/news-agent-20260917`），未提交、
> 未合并、未部署、未碰真实数据库与定时任务。

## 一句话结论（大白话）

消息系统以前只有一个笼统的「正常/不正常」，所以 9 月 5 日之后明明 12 天没
更新，界面上却看不出任何异常。这次把「最后一次什么时候检查的、检查成没
成功、AI 打分坏没坏、简报出没出」分开记录和展示：**12 天没更新会明确说
「资料过期」，再不会让人误以为「今天没有重大消息」**。另外接通了美联储
官网公告源并做了真实验证：9 月 16 日的加息声明被正确识别为「正式结果」
（发布时间自动换算成北京时间 9 月 17 日凌晨 2 点，与事实分毫不差），而
9 月 4 日那条「加息概率 50.6%」的旧报道仍然标为「预期（概率猜测）」，
两条消息分开放、不会混为一谈。这些成果目前只在隔离副本里完成并通过
验证，**还没有装回正在运行的系统**，也没有任何真实 AI 调用和消息推送。

## 1. 背景与授权

- 用户授权原话：2026-09-17「可以的啊，写好计划然后delegate给 ark-agent
  去做」。仅首批三件事：消息可靠更新、正式事件来源/阶段、现有 Agent 买前
  展示。S1 只做前两件的后端材料，不做展示层（S2）。
- 策略位置：服务 `docs/trading-spec-v1.md` 的解释层与独立消息叙事层——
  消息只解释「为什么」，**不参与技术判定、不改任何交易规则、不挡信号**。
  本次零规则改动、零 DDL（没有改数据库表结构）、零模型调用、零通知。
- 基线核对：W 的 git HEAD = `29b150f5`（与 baseline.json 一致），8 份必读
  文件指纹全部一致；基线测试复现 35 通过 / 1 旧失败（旧测试期望 7 分不推，
  与 2026-09-05 用户拍板的「7 分必推」生产口径不符，属旧测试偏差）。

## 2. 交付内容（对照冻结目标）

### G1 资料健康状态可核对（采集/评分/简报分别记录）

- 新纯函数 `build_news_health`（`src/lei_signal/newsfeed/health.py`）：
  输入最近一次任务记录 + 最近成功时间 + 最新消息时间 + 未评分数 +
  当前时间 + 过期上限（26 小时，即一天加 2 小时宽限，只作运维提醒），
  输出「新鲜 / 过期 / 从未运行 / 失败 / 部分失败 / 未知」六种状态、
  三个关键时间和采集/评分/简报各自的阶段结果。
- 管线每次运行现在把**每个阶段的结果、每个数据源的尝试时间和成败**
  写进运行记录（原来只有一个笼统状态 + 日志警告）。评分失败、没开 AI
  的正常运行（标「主动跳过」而不是「失败」或「全部正常」）、部分源失败
  都能事后核对。
- `/api/news/status` 和重大事件简报都带上了这份健康状态；健康状态本身
  算不出来时会明确返回「状态未知 + 原因」，不再悄悄省略。
- 修了一个真实隐患：原来程序**先推进「已读到哪」的书签（水位）、后写库**，
  写库一旦失败，书签已经翻页，那批新闻就永远漏掉了。现在改成先写库、
  成功后才翻书签；写库失败下次会重新抓，且不会重复入库（有去重键兜底）。

### G2 重大事件区分预期/正式结果/评论/未知且可追溯

- 新纯函数 `build_event_reference`（`event_context.py`）：给每条消息标
  「预期 / 正式结果 / 评论 / 未知」、来源、原文链接、带时区的发布时间、
  事件发生时间（确认不了就留空，绝不拿抓取时间冒充）。AI 打的「利空/
  重要度」标签单独放在模型注解里，**和事实分开放**；没评分的条目不会
  被编造一个「中性」结论。
- 「正式结果」门槛很严：必须来自官方来源（首批只有美联储官网）且标题
  确实是决议声明。官网上的讲话、会议纪要**不算**新利率决议（标评论）；
  非官方媒体哪怕写「美联储宣布加息」也只标「未知」。
- 新数据源 `sources/fed.py`：美联储官方货币政策公告订阅源。已做**真实
  受控采集**（临时数据库、不开 AI、不推送）：拿到 9 月 16 日 FOMC 加息
  声明和经济预测两条，发布时间换算与已知事实一致；同一份材料再跑一遍
  不会重复入库（幂等）。网络预算留痕见下。
- 同一份官方公告重复出现时只显示一条（按公告链接识别身份）；不同会议、
  以及「概率猜测 vs 正式公告」之间**绝不合并**——第一批宁可标「关联
  未知」也不猜。
- 推送文案口径修正：原来「三天影响窗口」的说法容易让人以为系统能断言
  市场影响持续三天，改成「近期事件继续关注」（3 天只是提醒别忘的关注
  期限）。提醒天数、推送门槛、发送渠道都没动。

## 3. 计划固定反例逐条验证

计划 §4 的 8 条固定反例全部有独立测试（期望值手工推演，不用被测代码生成）：

| 反例 | 结果 | 证据（测试） |
|---|---|---|
| 9月5日最后检查，现在9月17日 | 判「过期」，且不说「今日无重大消息」 | `test_old_success_is_stale`（计划原文用例） |
| 今天所有源成功但 0 条消息 | 判「新鲜·本次无相关消息」，与停更分开 | `test_fresh_check_with_zero_items_is_fresh_not_stale` |
| 部分源正常、官方源失败 | 总体「部分失败」，失败来源名留痕 | `test_partial_run_keeps_failed_source_visible` + 管线 `test_pipeline_partial_preserves_failed_source_attempt` |
| 采集成功、评分失败(429)、简报未出 | 条目保留、评分失败可见、原文可查 | `test_score_failure_visible_alongside_fresh_collect` + `test_pipeline_score_failure_visible_items_kept` |
| 正常 no_llm（不开 AI）运行 | 评分/简报标「主动跳过」，不冒充失败或全正常 | `test_no_llm_run_marks_scoring_skipped` + `test_pipeline_no_llm_marks_score_digest_push_skipped` |
| 旧运行记录没有阶段字段 | 阶段标「未知」，不回头伪造成功 | `test_legacy_run_without_stage_fields_is_unknown_not_fabricated` + `test_health_aggregates_legacy_run_not_fabricated` |
| 新闻写库失败 | 书签不提前翻页，重试不重复插入 | `test_watermark_not_advanced_when_insert_fails` |
| 任务中断（记录卡在运行中） | 中断可见，不留「永久健康」假象 | `test_stuck_running_is_not_healthy` + `test_recent_running_is_unknown_not_failed_or_fresh` |

事件侧（G2）另有 13 条反例：9月4日预期 vs 9月17日正式公告不混同、北京
时间跨日（9-16 14:00 美东夏令 = 9-17 02:00 北京）、夏令/冬令按日期换算
（用标准时区库，不用写死的美国时差）、无时区/未来日期判未知、官网讲话/
纪要不冒充决议、非官方「宣布加息」不冒充正式结果、同一公告去重、不跨
会议合并、缺发布时间不用抓取时间冒充。见 `test_newsfeed_event_context.py`
与 `test_newsfeed_sources.py`。

## 4. 真实官方源受控采集（网络预算 4/12）

- 预算：全任务上限 12 次 HTTP，S1 实花 **4 次**，全部访问同一个网址
  （美联储官方公告订阅源，20 秒超时，留痕
  `raw/agent-news-ark-2026-09-17/network-budget.json`）。真实 AI 调用 0 次、
  对外通知 0 次。剩余 8 次留给 S2。
- 过程（失败也留痕）：第 1、2 次取到了真实数据但解析失败——官网返回的
  内容带一种「字节顺序标记」（BOM，文件开头的隐形标记），且响应头没声明
  编码，程序按错误的编码解读成了乱码。改成直接按字节以 UTF-8 解码后
  第 3 次成功，但那次的重放核对脚本写法有误（绕过正常流程直接写库）污染了
  临时库；修正后第 4 次干净通过。两次失败都已记录原因，没有粉饰。
- 最终证据（`raw/agent-news-ark-2026-09-17/`）：
  `controlled-collect-result.json`（采集 ok、fed 入库 2 条、阶段留痕正确、
  重放 0 新增幂等）、`fed-press-monetary-live-2026-09-17.xml`（真实原始
  响应）、`temp-db-inspect.json`（临时库内容快照：FOMC 声明 + 经济预测，
  发布时间 2026-09-17T02:00:00+08:00）。
- 临时库路径 `/tmp/agent-news-s1/newsfeed-s1.db`（显式传入，非真实库）；
  真实库的「321 条、9 月 5 日断更」状态本阶段**原样未动**。

## 5. 验证命令与退出码（在 W 内真实执行）

```bash
# S1 验收套件（计划 §4 指定 8 个测试文件）：88 passed, 0 failed, 退出码 0
python3 -m pytest tests/unit/test_newsfeed_pipeline.py tests/unit/test_newsfeed_store.py \
  tests/unit/test_newsfeed_major_events.py tests/unit/test_newsfeed_api.py \
  tests/unit/test_newsfeed_sources.py tests/unit/test_newsfeed_push.py \
  tests/unit/test_newsfeed_health.py tests/unit/test_newsfeed_event_context.py -q

# 受控采集 + 重放：退出码 0（采集 ok / 重放幂等）
python3 docs/experiments/raw/agent-news-ark-2026-09-17/controlled_collect.py

# 归置自检：退出码 1，唯一报警见 §7（worktree 结构假阳性）
python3 scripts/check_repo_hygiene.py

# 相邻消费方回归（DTO 透传/llm_context/agent 聊天/copilot 路由）：32 passed
python3 -m pytest tests/unit/test_copilot_ops.py tests/unit/test_llm_context.py \
  tests/unit/test_agent_chat.py tests/unit/test_copilot_routes.py tests/unit/test_newsfeed_llm.py -q

# 代码风格（ruff）：本次改动 0 新增告警；剩余 4 处均为基线旧有
ruff check src/lei_signal/newsfeed/ tests/unit/test_newsfeed_*.py
```

基线对照：改动前同一批旧测试 35 通过 / 1 旧失败；现在 88 通过 / 0 失败。
旧失败（7 分推送边界）按计划**只改测试不改生产阈值**：新断言 7 分推、
6 分不推、行业类不推。

逐命令日志：`raw/agent-news-ark-2026-09-17/commands.jsonl`；
改动清单（含 base/after 哈希）：`changed-files.json`（24 项）；
补丁：`implementation.patch`（57KB，仅已跟踪文件的修改）。

## 6. 改动清单（人话版）

| 改动 | 干了什么 |
|---|---|
| 新增 `newsfeed/health.py` | 算「资料还能不能信」的纯函数（六种状态+分阶段） |
| 新增 `newsfeed/event_context.py` | 标「预期/正式结果/评论/未知」+ 同一公告去重 |
| 新增 `newsfeed/sources/fed.py` | 美联储官网公告源（时区/编码兼容，归「宏观」不归类「博主」） |
| 新增 `newsfeed/timeparse.py` | 严格时间解析小工具（没时区的时间不猜） |
| `newsfeed/pipeline.py` | 每阶段/每源留痕；官方源接入；书签顺序修复 |
| `newsfeed/store.py` | 健康状态需要的三个轻量查询；未评分官方条目查询 |
| `newsfeed/service.py` | 状态接口和重大事件简报带健康状态与事件参考 |
| `newsfeed/push.py` | 「影响窗口」改「继续关注」（只改说法） |
| `configs/newsfeed.json` | 过期上限 26 小时；官方源启用（验证可达后） |
| `api/schemas.py`、`copilot/ops.py` | 事件与健康状态的可选透传字段（旧数据照样能读） |
| 测试 6 改 2 新 + 夹具 4 个 | 53 个新用例（含计划 8 条固定反例与 13 条事件反例） |

未列文件零改动；`src/lei_signal/ui/`、`configs/rules*.yaml`、规则/研究/
交易金额逻辑、`storage/sqlite_store.py` 均未触碰。

## 7. 失败记录与未解决

1. **受控采集前两次失败**（编码问题）已留痕并修复，过程见 §4；没有宣称
   一次成功。
2. **归置自检唯一报警**：`.git` 在隔离工作区 W 里是一个 84 字节的指针
   文件（worktree 结构固有），被自检脚本当成「根层多出文件」。运行仓 R
   里 `.git` 是目录、在白名单内，采用后该项为绿。脚本不在本阶段可改范围，
   如实上报主控裁定。
3. **旧运行记录**（如生产的第 11 次运行）没有阶段字段：健康状态里阶段
   会显示「未知」、「最近成功时间」为空——这是刻意的诚实口径（不回头
   伪造成功），采用后首次新格式运行起即恢复完整显示。
4. **S2 待办**（本阶段未做，不越界）：Agent 各入口展示健康状态与事件、
   无模型/历史恢复路径核对、08:30 仅采集候选与 `--no-push`、页面验证、
   恢复步骤文档。晨间候选若要「只抓官方源」，现有脚本还需要一个只启用
   部分源的入口（S2 计划内）。
5. 美联储「经济预测」类官方条目目前标「未知」（它不是利率决议，也不是
   评论），如需更细的官方材料分类，属后续增强，不影响本阶段口径。

## 8. 上线限制（必须随交付一起读）

- 本阶段**生产未部署、真实数据库未改、定时任务未加载、推送未发送**；
  消息断更状态没有因本次工作改变。
- 采用必须由主控三方合并（运行仓有并行改动，禁止整体覆盖）；补丁与
  逐文件哈希在 raw 目录备齐。
- 采用后原 20:30 任务恢复时会开始抓取美联储官网（已在配置中启用，
  属计划内行为）；评分/简报/推送的真实恢复需另行核准。
- 本报告不代表主控复核通过；S1 的独立复核（重算时间反例、制造评分
  失败/无消息/部分源失败、核官方结果依据）由 Codex 执行。

---

## 修订记录（repair-1，2026-09-17，execution 2）

> 主控首次独立复核（`raw/agent-news-ark-2026-09-17/controller-s1-initial/`
> 内复核报告与探针）判定 S1 未通过，交回 5 组问题（R1–R5）。本节是返修
> 记录；上文初版内容保持原样（其中 §2/§3/§5 描述的初版行为以本节为准）。
> 初版证据由主控快照保全，未回写伪装一致。返修后：**主控独立探针
> 18/18 通过**（`repair-1/probe-rerun.json`），S1 验收套件 **105 passed /
> 0 failed**，真实材料重放验证通过（0 新增 HTTP）。

### R1 健康状态必须依据采集记录，不能只信旧的总状态 —— 已修

- 旧记录（无阶段字段）近期也**不再冒充「采集正常」**：保留「未知」，
  过期仍显示过期；
- 总状态与采集阶段矛盾的记录不被洗白：采集记失败即报失败（并注明矛盾），
  其余矛盾报未知并说明，不能声称成功；
- 辅助时间字段（最近成功/最新消息时间）**有值而非法**（无时区/坏串/未来）
  即整体「未知」，原始值留在新增 `anomalies` 字段供排查；阶段时间非法只
  降级该阶段时间；
- 未来时间**严格判定**（取消 5 分钟硬编码容差，不再出现负年龄）；过期
  阈值改用未舍入时长比较（26 小时 1 分钟 = 过期），舍入只用于文字。
- 新反例测试 7 个（`test_newsfeed_health.py`，22 passed）。

### R2 正式决议的可见性和身份不能取决于模型评分或含糊关键词 —— 已修

- 同一 FOMC 声明**模拟评分 6、0 或类别误判后仍在重大事件列表**（官方
  通道按「确定正式公告」纳入，与模型分数无关；仍有日期窗口与 5 条上限、
  按公告身份去重；普通新闻的 7 分筛选、推送和技术阈值均未动）；
- 分类顺序改为**先识别讲话/纪要再确认决议**，且决议模式去掉「FOMC
  statement」裸词：「Speech by Powell on the FOMC statement」「Minutes of
  the FOMC statement discussion」均判评论，不再误判决议、不再赋事件时间；
- 事件身份键改用**完整规范化 host+path**：不同路径的同名公告不合并。
- 新反例测试见 `test_newsfeed_event_context.py`（14 passed）与
  `test_newsfeed_major_events.py`（含主控探针同例：评分 6 仍可见）。

### R3 尊重原始时区，并比较真实时刻 —— 已修

- 命名时区**按其定义偏移**（EST 恒 -05:00、EDT 恒 -04:00），删除「假定
  源站写错季节」的无来源纠错：9 月 16 日 14:00 EST = 19:00 UTC，不再被
  挪成 18:00 UTC；已核事实（14:00 EDT = 北京次日 02:00）保持正确；
- 书签（since）比较**统一真实时刻**（带时区 datetime）：feed 条目 18:00
  GMT vs 书签 19:00 UTC 不再误收为新条目；非法书签显式报错；
- 未来日期/无时区条目**不推进书签**并记 warning；整份 feed 时间全部不可
  解析时抛源错误，不再装成一次成功的空采集；
- 修正注释：真实材料是 **GMT**（另有 BOM/CDATA），EST/EDT 仅见于合成
  夹具，注释与夹具 README 已分开表述。
- 测试 `test_newsfeed_sources.py`（16 passed，含主控探针同例）。

### R4 评分或简报抛异常时，已完成的采集和失败阶段仍要落库 —— 已修

- 评分阶段抛异常：捕获后阶段记 failed（含异常类型）、**简报/推送明确记
  skipped(upstream_failed) 不假装跑过也不触发外发**，运行记录正常收尾
  （不再永远停在 running）、已采集条目保留；
- 简报阶段抛异常：同样落库记 failed；推送与简报相互独立，仍按自身
  try/except 留痕。
- 新异常路径测试 2 个（`test_newsfeed_pipeline.py`，14 passed）；真实
  材料上的端到端表现见 `repair-1/replay-verify-result.json`。

### R5 修正文件清单对自己的无效哈希 —— 已修

- 新 `changed-files.json` **不对自身声称最终哈希**（自身条目
  `after_sha256` 置 null 并注明），最终一致性由主控外置校验；
- 初版声称值与主控复核实测值的不一致记录保存在
  `repair-1/hash-note.json`；初版未回写。主控 45 次哈希核对中其余 44 个
  一致，未发现其他偏差。

### 返修后验证命令与退出码（W 内真实执行）

```bash
# S1 验收套件（8 文件）：105 passed / 0 failed，退出码 0
python3 -m pytest tests/unit/test_newsfeed_pipeline.py tests/unit/test_newsfeed_store.py \
  tests/unit/test_newsfeed_major_events.py tests/unit/test_newsfeed_api.py \
  tests/unit/test_newsfeed_sources.py tests/unit/test_newsfeed_push.py \
  tests/unit/test_newsfeed_health.py tests/unit/test_newsfeed_event_context.py -q

# 主控独立探针离线复跑：18/18 通过，退出码 0（临时库，0 HTTP/0 模型/0 推送）
python3 <R>/docs/experiments/raw/agent-news-ark-2026-09-17/controller-s1-initial/probe.py

# repair-1 真实材料重放验证：退出码 0（0 新增 HTTP）
python3 docs/experiments/raw/agent-news-ark-2026-09-17/repair-1/replay-verify.py
```

- 网络预算：repair-1 全程使用已保存真实响应与合成夹具，**0 新增 HTTP**；
  全 job 计数保持 4/12（execution 1 记录不变）。
- 仍有效限制：§7/§8 全部成立（生产未部署、真实库未改、定时任务未加载、
  推送未发送、W 归置 .git 假阳性由主控裁定）；本返修不代表主控复核通过，
  S1 再复核由 Codex 执行。

---

## 修订记录（repair-2，2026-09-17，execution 3）

> 主控第二次复核判定：首轮 18 反例与 105 测试全部通过，但发现唯一功能
> 问题组 **R6：来源异常不能变成「采集正常」**（原 G1「空消息与失败不能
> 混淆」与 R3 的未闭合部分）。本节是第二次返修记录；上文与 repair-1
> 记录保持原样。返修后：**主控首轮探针 18/18、R6 附加探针 7/7**、S1
> 验收套件 **110 passed / 0 failed**、真实材料离线重放通过（0 新增 HTTP）。
> 本轮证据全部在 `raw/agent-news-ark-2026-09-17/repair-2/`。

### R6 来源异常不能变成「采集正常」——已修

大白话：官网有时会返回「服务不可用」错误页，或者公告里有几条缺日期/
缺链接。之前系统把这些情况当成「检查了、没消息」，买前的人就会以为
官方真没发公告。现在：

- **错误页面不再冒充订阅内容**（反例 A）：HTTP 200 返回
  `<html>Service unavailable</html>` 这类页面时先验结构，不是支持的
  RSS 就报来源失败；**合法的空订阅（没有新公告）仍然是正常结果**——
  用结构验证区分，不是「没条目就报错」。
- **全部条目缺必需字段 = 来源失败**（反例 B）：标题/链接/发布时间统一
  计数，存在条目却全部不可用时明确报错，不再冒充「本次无相关消息」。
- **混合响应：好的留、坏的记、状态说真话**（反例 C）：一条合法声明加
  一条坏日期公告时——合法公告照常入库；无效条目的**数量和原因写进
  运行记录**（`news_runs` 的 errors/sources，可经状态接口与健康状态
  查到，不再只有终端日志）；该源记部分失败，健康状态显示「部分失败」
  而不是「采集正常」。
- **书签保守策略**：本次读取不完整时**不推进该源书签**——下次重试时
  修正后的漏项还能补进来（已有条目靠去重键不会重复），不会悄悄越过
  漏项。主控明确允许这种保守做法，未新建补数框架。
- 保持 `collect_fed_press` 既有调用兼容（主控探针按原样运行）；仅 Fed
  适配增加结构化诊断（可选输出字典），复用现有 stats/sources/errors
  记录，未扩大重构其他来源；新闻重要度、推送阈值、技术信号均未动。

### 必须覆盖的独立预期——逐条验证

| 预期 | 结果 | 证据 |
|---|---|---|
| 合法空 RSS：源成功、0 新增，与失败区分 | 通过 | `test_fed_valid_empty_rss_is_success_not_failure` |
| 错误 HTML/XML 结构：源失败可见 | 通过 | `test_fed_rejects_error_page_despite_http_200` + 主控附加探针 `html_200` |
| 全部字段不完整/全部日期不可解析：源失败可见 | 通过 | `test_fed_all_items_missing_required_fields_fails` + 主控附加探针 `missing_fields`/`invalid_times` |
| 混合响应：合法保留、部分缺失可查、不说全正常、书签不造成不可恢复遗漏 | 通过 | `test_fed_mixed_valid_and_invalid_reports_diagnostics` + `test_pipeline_mixed_fed_marks_partial_and_keeps_watermark` + 主控附加探针 `partial_feed_health_not_fresh` |
| 修正材料重试：补进漏项、已有项不重复 | 通过 | 同上管线测试后半段（x.htm 去重、y.htm 补进、书签随后正常推进） |
| 既有 18 反例 / 105 测试 / 真实 XML 离线复放 | 通过 | `repair-2/probe-initial-rerun.json`（18/18）、验收套件 110/110、`repair-2/replay-verify-rerun.json` |

### 返修后验证命令与退出码（W 内真实执行）

```bash
# S1 验收套件（8 文件）：110 passed / 0 failed，退出码 0
python3 -m pytest tests/unit/test_newsfeed_pipeline.py tests/unit/test_newsfeed_store.py \
  tests/unit/test_newsfeed_major_events.py tests/unit/test_newsfeed_api.py \
  tests/unit/test_newsfeed_sources.py tests/unit/test_newsfeed_push.py \
  tests/unit/test_newsfeed_health.py tests/unit/test_newsfeed_event_context.py -q

# 主控首轮探针复跑：18/18，退出码 0
python3 <R>/docs/experiments/raw/agent-news-ark-2026-09-17/controller-s1-initial/probe.py

# 主控 R6 附加探针复跑：7/7，退出码 0
python3 <R>/docs/experiments/raw/agent-news-ark-2026-09-17/controller-s1-repair1/additional-probe.py
```

- 网络预算：本轮全程已保存材料与合成夹具，**0 新增 HTTP**；全 job 计数
  保持 4/12。真实模型 0、通知 0。
- 证据归置：本轮新证据/清单/补丁全部在 `repair-2/`；repair-1 与初始 raw
  未覆盖（例外：repair-1 的重放脚本被作为回归复核再跑，其结果文件写回
  原路径，内容副本已存 `repair-2/replay-verify-rerun.json`）。
- 采用依据更新：`repair-2/changed-files.json`（47 项，自哈希置 null）+
  `repair-2/implementation.patch` 取代 repair-1 时点清单。
- 仍有效限制：生产未部署、真实库未改、定时任务未加载、推送未发送、
  W 归置 `.git` 假阳性沿主控裁定；本返修不代表主控复核通过，S1 再复核
  由 Codex 执行。
