# Agent消息可靠性与买前信息首批实施计划

> 执行者使用 executing-plans 技能，按本计划检查项执行；不另派子代理。用户已选择 Ark Agent，不再询问执行方式。过程文件按项目约束落本目录。

**Goal:** 用户买前能在现有Agent入口看懂消息是否更新、事件是预期还是正式结果、原文来源和下一步技术观察条件；交付可复核、可定向采用的修复。

**Architecture:** 复用newsfeed采集/存储和Agent上下文；新增小型健康状态与事件来源纯函数，不修改技术规则。先在隔离副本实现数据和测试，主控复核后接现有依据卡、操作清单并准备运行恢复包。运行采用由主控与现有采用任务协调，不由执行者写运行库或重启服务。

**Tech Stack:** Python、SQLite既有表、FastAPI、React/TypeScript、pytest、Vite。复用已安装依赖，零新增付费服务。

## 0. 身份、授权与策略位置

- 用户授权原话：2026-09-17“可以的啊，写好计划然后delegate给 ark-agent 去做”。仅上一轮首批：消息可靠更新、正式事件来源/阶段、现有Agent买前展示。不是授权全部方向。
- 服务 `docs/trading-spec-v1.md` §2/9/10/13/14 的解释层与独立消息叙事层。阶段、触发、失效位、盈亏比只读规则输出；基本面和消息不改变技术判定、排序算法或硬过滤。
- 运行根 `R=/Users/yongbiaoli/Desktop/lei-signal-lab`；执行根 `W=/Users/yongbiaoli/Desktop/lei-signal-lab/scripts/agents/news-agent-20260917`。下文仓库相对路径均以W为根，R只读。
- 分支 `codex/agent-news-reliability-20260917`，基线 `29b150f58b3f6d8c6e558a748c12dac3384af173`。这是运行仓HEAD快照，未覆盖其未提交改动，不能视为其他Agent最新采用分支。
- 必读：W内 `AGENTS.md`、`CLAUDE.md`、`docs/trading-spec-v1.md`、`configs/rules.v1.yaml`、`.claude/skills/macd-reading/SKILL.md`、`docs/plan-sector-trend-page.md`、`docs/plan-agent-superentry-v1.md`；研究派发约定采用 `docs/research/ai-execution-contract.md` v1.0.1。权威文件指纹见R内 `docs/experiments/raw/agent-news-ark-2026-09-17/baseline.json`。
- 背景限读R内 `docs/experiments/agent-news-priorities-2026-09-17.md` 和对应 `raw/agent-news-priorities-2026-09-17/read-only-check.json`，不重复阅读大量旧实验。
- 当前任务是工程与产品信息改进，没有收益实验对象，不创建因子定义、不跑历史收益、不换模型配置。实际执行器为用户指定Ark设置，主控为Codex；没有Spark/Sol回退。

## 1. 全局约束和资源

1. Ark仅修改W。R源码、真实`~/.lei_signal_lab/`、运行数据库、.env、用户launchd配置、其他工作区均保护。不得执行git add/commit/reset/merge/push、生产DDL、launchctl load/bootstrap/bootout/kickstart、外部通知或报单。
2. 禁止改 `src/lei_signal/ui/`、技术规则目录、`configs/rules*.yaml`、因子研究代码、交易金额逻辑及`src/lei_signal/storage/sqlite_store.py`。利用既有news_runs.stats_json和现有新闻字段；本批无新增DDL。确实需要DDL时暂停对应支线交主控，不伪造字段已经保存。
3. 只读生产核查限已有状态接口/日志和launchctl print。不能用NewsStore直接打开真实库（构造器可能自动迁移）。日志仅摘取不含凭据的相关错误，不读取或复制.env。
4. Python解释器 `/Users/yongbiaoli/.workbuddy/binaries/python/envs/default/bin/python3`；测试全部临时库。允许W/web/node_modules软链至R/web/node_modules以复用依赖，但不写依赖目录；不安装/升级。
5. 联网仅公开新闻源与 `federalreserve.gov`：全job最多12次显式HTTP尝试（含重试/重定向），每次超时20秒，记录请求计数；禁运行会失控扇出的全源默认抓取。S1可定向验证官方feed和正式公告，在新临时库进行一次受控采集、一次相同材料重放核幂等；如网络失败，保留失败并用夹具继续工程，不能宣称真实抓取恢复。
6. 真实模型调用0次；执行器本身的Ark调用不属于产品模型调用。模拟评分正常/失败/缺失，禁止触发已有评分、简报和推送真实API。S2页面采用假模型与临时数据。不得购买/重置额度。
7. 阶段数2；同一个Ark会话，后续只resume；全job最多3次已派发返修，不按阶段重置。任何越界需求停对应项，完成其余独立项。测试正常迭代不冒充正式返修。
8. 新脚本仅放本任务raw或tests标准子目录；生产入口复用 `scripts/precompute_newsfeed.py`。旧报告和raw不覆盖不改名。
9. 工程采用后先恢复原有20:30周期；增加08:30（Asia/Shanghai）的仅采集任务候选，让国内开盘前有机会取得凌晨公告。运行时区不符则候选必须显式设置或说明，不默默按另一时区运行；本批执行者只交plist候选和验证命令，不加载。新晨间任务不能再次全量调用模型或发送消息。
10. 变更前记录计划文件/规范指纹，变更后交逐文件base/after哈希、补丁、新文件列表。运行目录有并行修改，采用时必须三方比较，不能把W整体覆盖R。

## 2. 冻结交付目标

- **G1 资料状态可信：** 分开采集、评分、简报结果；有成功检查但零条目不算失败；旧任务ok不能证明今天消息正常；空结果、过期、失败、未评分互不混淆。
- **G2 事件可核对：** 原始来源与绝对时间保留；预期/正式结果/评论/未知明确；官方声明无需模型打分也能作为参考事实展示；仅确定同一事件才关联更新，不能跨期错合并。
- **G3 买前入口可读：** 单标的和全局讨论、依据卡、操作清单都能看到资料状态与相关事件；模型缺席仍显示确定性资料；技术判断不变。
- **G4 恢复包可采用：** 交独立测试、真实公开来源探测结果、候选计划及回退步骤，准确区分开发完成/未运行采用；生产恢复由主控承接。

## 3. 文件职责和允许写范围

| 路径（相对W） | 责任 |
|---|---|
| `src/lei_signal/newsfeed/health.py`（新） | 独立计算各阶段状态、最近检查/成功/消息时间及运维过期标识 |
| `src/lei_signal/newsfeed/event_context.py`（新） | 根据可信来源与明确文本，归一化事件阶段、时间、关联；未知原样保留 |
| `src/lei_signal/newsfeed/sources/fed.py`（新，如RSS通用层无法无损承载） | 仅美联储官方货币政策feed/公告来源适配；保留原文链接及正文/摘要事实 |
| `src/lei_signal/newsfeed/{pipeline,store,service,models,config_loader,push}.py` | 阶段记录、既有字段透传、查询与文案；不改推送渠道和阈值 |
| `src/lei_signal/newsfeed/sources/rss.py`、`configs/newsfeed.json` | 无损官方来源配置与解析；不得将官方公告一律分到blogger |
| `scripts/precompute_newsfeed.py`、`scripts/launchd/com.lei.newsfeed.plist` | 可禁推送的受控入口、现有计划候选 |
| `scripts/launchd/com.lei.newsfeed.morning.plist`（新） | 08:30仅定向采集候选，未加载 |
| `src/lei_signal/plans/llm_context.py`、`src/lei_signal/api/routes/agent.py` | 仅消息子树和确定性依据卡适配，不重构意图/会话/本人事实逻辑 |
| `src/lei_signal/api/{schemas.py,routes/news.py,routes/copilot.py}`、`src/lei_signal/copilot/ops.py` | 消息DTO和状态向既有入口透传；不碰报单逻辑 |
| `web/src/types.ts`、`web/src/components/EvidenceCardView.tsx`、`web/src/components/NewsContextCard.tsx`（新） | 同一小组件展示状态、来源、事件阶段；类型保持可选兼容 |
| `web/src/pages/{NewsPage,OpsPage}.tsx`、`web/src/components/copilot/CopilotCards.tsx` | 仅消息区块接入；不改成交和推荐行为 |
| `web/src/components/news-context.css`（新） | 局部样式，不大改全站布局 |
| `tests/unit/test_newsfeed*.py`、`tests/unit/test_agent_news_context.py`（新）、`tests/integration/test_agent_news_flow.py`（新）、`tests/fixtures/newsfeed/agent-news/`（新） | 反例、流程和来源夹具 |
| `web/run-news-context-regression.mjs`（新） | 渲染/兼容性回归工具，不硬写生产接口 |
| `docs/ops/agent-news-recovery-2026-09-17.md`（新） | 逐项恢复和回退步骤 |
| `docs/experiments/agent-news-{s1,s2}-2026-09-17.md`、`docs/experiments/raw/agent-news-ark-2026-09-17/` | 阶段报告与证据 |
| `docs/experiments/{registry.json,INDEX.md}` | 仅W内新增本任务报告条目；主控定向同步R |

未列文件确有必要时先在当前阶段报告说明，不能自行扩路径。包内新纯函数可使用私有辅助文件，但必须在newsfeed目录内、列入变更清单，不生成新技术信号。

## 4. S1：可靠采集状态与官方事件材料

**交付：** G1、G2；后端模块、临时库反例、S1报告。结束后停止，等待主控复核。

### Task 1：核对基线与最小反例

- [ ] 读必读文件，复核baseline.json的HEAD和策略文件指纹；当前机器launchd仅print。历史卸载原因查不到就标未知。
- [ ] 复用主控已运行的六组新闻基线测试记录；修复前针对本任务反例写测试并保留失败。
- 基线实际结果：35 passed、1 failed。`test_newsfeed_push.py::test_push_only_macro_risk_and_importance`仍期待m7不展示，而现有`PUSH_IMPORTANCE=7`及2026-09-05注释明确7分。允许核对后把测试改成7分包含、6分排除，保留行业不推的断言；禁止把生产阈值改回8。此为已知旧测试偏差，不阻止隔离工程，不计新功能通过。
- [ ] 本任务raw建立`commands.jsonl`、`network-budget.json`、`source-manifest.json`；只记录必要信息，不抄密钥/全部日志。

固定反例：

| 输入 | 独立预期 |
|---|---|
| 9月5日最后检查，当前9月17日 | 资料过期；不能输出“今日无重大消息” |
| 今天所有启用源成功返回0条 | 采集正常，无相关消息；与停更不同 |
| 部分源正常、官方源失败 | 总体部分失败且保留该来源失败；不能用其他源成功掩盖 |
| 原文采集成功、评分429、简报未生成 | 条目保留、评分失败可见；官方原文仍可查看 |
| 正常no_llm运行 | 评分/简报明确skipped，不误写failed或全部ok |
| 旧news_runs没有阶段字段 | unknown兼容，不追溯伪造成功 |
| 新闻写库失败 | 不提前推进水位导致漏新闻；回滚/重试后不重复插入 |
| 请求运行异常或异常退出记录 | 失败/中断可见，不遗留永久健康的running解释 |

### Task 2：实现health纯函数与分阶段记录

接口冻结为可JSON序列化dict，旧DTO字段保留，新增字段可选：

函数名`build_news_health`，仅关键字参数：`latest_run: dict | None`、`latest_success_at: str | None`、`latest_item_at: str | None`、`unscored_count: int`、`now: str`、`max_age_hours: int`，返回dict。

返回字段：`availability`取fresh/stale/never/failed/partial/unknown；`last_checked_at`、`last_success_at`、`latest_item_at`、`age_hours`、`note_cn`；`stages`含collect/score/digest各自的status/finished_at/errors。無资料保留unknown。last_checked_at来自任务实际尝试/完成时间，不取新闻发布时间；last_success_at来自明确采集成功记录，不直接取综合ok。

`max_age_hours=26`放`configs/newsfeed.json`的`health`配置，是对既有每日运行的运维过期提醒（24小时+2小时宽限），不参与技术策略。时间缺失、未来时间和时区不合法分别unknown，不从条目数推断成功。fresh仅代表近期检查，不能保证时点之后无新公告。单一字段不能承担所有状态：采集新而评分失败需同时表达。

测试必须通过直接输入时间与独立常识预期，不用待测函数生成expected：

```python
def test_old_success_is_stale():
    health = build_news_health(
        latest_run={"finished_at": "2026-09-05T22:08:32+08:00", "status": "ok"},
        latest_success_at="2026-09-05T22:08:32+08:00",
        latest_item_at="2026-09-04T20:41:25+08:00", unscored_count=0,
        now="2026-09-17T09:00:00+08:00", max_age_hours=26)
    assert health["availability"] == "stale"
    assert health["latest_item_at"] == "2026-09-04T20:41:25+08:00"
```

- [ ] `news_runs.stats_json`新增阶段结果及每源尝试时间；失败要可追溯，不只日志warning。无数据与失败分开，原有计数字段兼容。
- [ ] Store增加只读聚合查最近成功/最新条目/未评分数，避免在API查询时全表载入正文。
- [ ] API和major_events_brief均带health，空items仍保留状态；服务异常用明确失败材料替代None静默省略。
- [ ] 修复仅与本次可靠性直接相关的水位提交顺序，不另做通用数据库重构。

### Task 3：事件来源和阶段，正式公告不依赖AI评分

函数名`build_event_reference(item: dict) -> dict`。返回字段：`event_stage`取expectation/official_result/commentary/unknown；`source`、`source_name`、`source_url`、`published_at`、`event_at`、`ingested_at`；`event_key`、`related_to`、`relevance_cn`无确定依据时null。direction和importance放入model_annotation，未知不填为“中性事实”。

- [ ] 官方来源仅核`https://www.federalreserve.gov/feeds/press_monetary.xml`及其官方公告；验证实际可达再接。沿用RSS解析，不将官方声明分进博主。来源失败显式记录，不换成无来源模型回答。
- [ ] 保留标题、摘要、链接、带时区发布时间、实际取得时间。缺发布时间不能以抓取时间冒充；无法确认事件时间就null。
- [ ] 正式结果必须由可信官方来源且内容确实为决议支持；官方域名的讲话、日历、会议纪要不自动算新的利率决议。关键词和模型只能作为待核标签。
- [ ] 旧概率报道保持expectation，不能因后来正式加息而回写成已确认事实。文章时间与会议时间分开，缺少对应会议日期时不得自动合并；首批宁可关联未知。
- [ ] 同一官方公告URL/确定事件身份去重，优先显示已确认同一事件的正式结果，保留旧条目及来源。不得把相邻两次会议合并。
- [ ] 允许未评分官方事件进入参考列表，不凭空赋重要度/利空分数；其他未评分信息显示“尚未评分”，不会变成新买点或影响技术排序。
- [ ] 改push展示文案“三天影响未消化”为“近期事件继续关注”；不改现有天数、阈值或发送渠道。

时间测试至少覆盖北京时间跨日、夏令/冬令时间（用zoneinfo而非固定美国时差）、无时区/未来日期未知。固定已核事实夹具：2026-09-16 14:00 EDT对应2026-09-17 02:00+08；新闻阶段是已核官方结果，不是本地早已采集。

### S1验收命令

```bash
/Users/yongbiaoli/.workbuddy/binaries/python/envs/default/bin/python3 -m pytest tests/unit/test_newsfeed_pipeline.py tests/unit/test_newsfeed_store.py tests/unit/test_newsfeed_major_events.py tests/unit/test_newsfeed_api.py tests/unit/test_newsfeed_sources.py tests/unit/test_newsfeed_push.py tests/unit/test_newsfeed_health.py tests/unit/test_newsfeed_event_context.py -q
python3 scripts/check_repo_hygiene.py
```

新增最后两个测试文件在允许的test_newsfeed*.py范围内。预期本任务全部通过；旧失败单列最小复现，不扩大修复。交S1报告（含大白话结论）及W内registry/INDEX登记，主控复核后才进入S2。

## 5. S2：现有Agent展示、端到端核对与运行恢复包

**交付：** G3、G4。不改聊天连续性、持仓/资金提取、报单去重或其他正在进行的工作。

### Task 4：数据先显示，模型只解释

- [ ] `major_events_brief`完整事件及health经过`llm_context._major_events_block`仍保留来源、绝对时间和状态，旧available=false不再无声消失。
- [ ] 单标的、全局、模型不可用三个路径均提供消息资料。来源状态可在既有EvidenceCard附加`news_context`字段，缺该字段的历史卡仍可读。
- [ ] 右侧/依据卡使用同一个NewsContextCard：先状态和日期，再少量相关条目；链接只接受http/https，不渲染原文HTML、不执行页面指令。
- [ ] `/ops`复用同一资料，只回答值得关注的变化；`/agent`解释技术条件/未满足/失效，再给消息背景。保留完整详情入口，最多3条为首层显示数量（展示参数，不修改推荐排序）。
- [ ] 宏观关联不确定时标“全局背景”，不能硬说影响当前ETF或由它导致价格涨跌。模型标签与官方事实分开显示。
- [ ] 禁止用新闻阻止合法技术信号、修改档位或编造“市场尚未消化”“加息必跌”。

独立端到端案例：

1. 旧资料+无items：卡片和模型材料均明确过期。
2. 正常采集+无相关消息：明确本次检查无相关消息，不声称全市场无事。
3. 未评分官方决议：原文、时点、阶段仍展示，无模型利空评分。
4. 旧概率+正式结果：不混同；对应身份未知时不伪造关联。
5. 两只ETF连续查询：来源/关联不串对象，技术review输出前后相同。
6. 无模型：确定性资料仍可读；无消息服务：技术卡仍正常。
7. 历史对话恢复：保留当时快照，不能把今日最新事件注入旧回答冒充当时已知。
8. 恶意URL或HTML标题：纯文本且无脚本链接。

### Task 5：验证与准备恢复

- [ ] 跑针对性后端回归、新集成测试、现有依据卡回归及前端build。

```bash
/Users/yongbiaoli/.workbuddy/binaries/python/envs/default/bin/python3 -m pytest tests/unit/test_agent_news_context.py tests/integration/test_agent_news_flow.py -q
cd web
npm run test:evidence-card
node run-news-context-regression.mjs
npm run build
```

- [ ] 用临时API端口18047和前端15147做桌面/窄屏检查；真实交易写端点不调用。端口被占则记录并选空闲端口，不杀其他进程。关闭仅自己启动的服务。
- [ ] 复用S1官方真实HTTP证据；零真实模型调用。开发测试不读取真实用户交易库。真实API只核/status等只读端点。
- [ ] `--no-push`参数贯通生产脚本/pipeline默认行为兼容；恢复时可先仅采集，在实际投递单独核准前禁推送。证明fixture正常运行也不会触发通知。
- [ ] 检查20:30原plist与08:30仅采集候选的解释器、绝对路径、时区、日志目录、禁推送参数，用plistlib/plutil校验但不加载。晨间候选只启用官方宏观源，不重复抓全部B站或用模型。
- [ ] 写`docs/ops/agent-news-recovery-2026-09-17.md`：主控采用前核baseline/hash→备份→逐文件三方合并→相关验证→仅采集验证→加载新闻任务→观察任务状态；后端/前端重启与既有采用任务协调。每一步写回退，不能回滚整个真实库覆盖新增数据。
- [ ] 交`changed-files.json`（base_sha256/after_sha256/用途）、`implementation.patch`及新文件、真实HTTP原始响应文件（不含凭据）、命令退出码、UI截图、失败记录。单列生产尚未恢复，不宣称已经上线。
- [ ] S2报告按归档三件套登记；最后跑hygiene并全绿。主控复核每阶段出书面报告，全部通过才接受开发交付；运行恢复另记录实际结果。

## 6. 主控复核与停止条件

主控S1重算时间反例、制造评分失败/无消息/部分源失败，核官方结果依据；S2独立验证无模型与历史恢复、技术输出不变及补丁范围。不得只复述Ark“全部通过”。

当前阶段结束即停并回调；缺权威字段不自造、网络预算达到即停联网；保护文件必须改才可继续时报告具体阻塞；全job三次返修仍不通过则交付已确认部分和剩余问题，不无限增加前置研究。

最终清理：开发及采用交接验收后，先归档补丁/新文件/测试证据，再由主控删除本任务子代理工作区；不可提前删除，也不可清理其他代理或旧raw。
