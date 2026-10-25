# 当前：焦点动量接入日常看盘与因子工作台 2026-10-25T18:13:38.072085+08:00

- task-id focus-stock-universe-20261024；owner 01a16bd6-3661-7cd3-a2ff-5cadfa181605/root；status active；scope_released false仅下述新增展示范围。
- 用户本轮明确提出把焦点动量做到平常主要看板和因子看板；采用现有研究结果作为独立市场状态观察，不改买卖/情绪灯/策略。主看盘紧凑入口，因子工作台独立市场观察视图，共用冻结数据展示包；今日值未知、固定历史300股、截至2025-12-31与美股未评价必须可见。
- checked_coordination_sha 9f1993e84776778a8e867a345dc660c4236f35be；checked_at 2026-10-25T18:13:38.072085+08:00；已读COORDINATION1.1/self/research-dispatch-controller/research-utility-review-20261012/investor-workspace-simplification-20261012/market-style-observation-20261020/sentiment-factor-research相关当前记录。market-style与investor最近范围已释放；只在WorkspacePage顶部和FactorWorkbench导航/新视图插入，不动旧判断/曲线/进度接口，未发现同块活跃写者。
- 主仓codex/factor-unit-research-20260915，base 18e64fa632dba5dbad0e5fcae09b4ccc75f119a9加既有脏区。此次结果仅本地未提交、远端不可复现；不拿基线代表工作区。
- 具体写范围：新src/lei_signal/market_context/focus_momentum.py、scripts/research/export_focus_momentum.py、tests/unit/test_focus_momentum_observation.py、web/public/research/focus-momentum/、web/src/components/focus-momentum/；主控仅web/src/pages/WorkspacePage.tsx与web/src/pages/factor-workbench/FactorWorkbench.tsx插入及同工作台必要样式。自己的docs/archive/handoffs-plans/focus-momentum-display-20261025/与原progress。现有factors/sentiment API、App、vite、交易策略、原冻结研究全部不改。
- 预计分工：子代理universe_evidence写新导出器/测试/JSON；root写新组件和上述两个页面；model_source_hunt只读UI验收。后续按此范围真正派发，不把准备视为实现。
- 验收：源CSV/summary指纹绑定、空缺/篡改/日期语义测试、TypeScript与构建、真实主看盘到市场观察链接/图/日期/报告与移动宽度，来源冻结不变。静态展示包不依赖重启8000或新常驻服务。
- 上一研究已完成：docs/experiments/focus-stock-momentum-evaluation-2026-10-25.md；1冻结核心批次/1独立审计/6文献请求，固定300股独立版本未见稳定正预测增量；原式、全市场、美股与账户效果不升格。本轮0新效果实验/调参/行情下载；复用已冻结证据。
- 依赖：当前全市场实时资料未合格，展示历史状态不伪装今日监测。内盘余量16503504896字节，小产物预计<10MiB；仓外与外盘只读，不删除、不启动自动化、不改目标数据库。

---

# 当前：焦点股动量来源与中美观察用途调研结案

- task-id/owner沿原；status completed仅本轮source_review；scope_released=true仅本题归档项。updated_at 2026-10-24T13:44:03.438620+08:00；checked_coordination_sha 01b71f2366c5e8a96a9644685ba7ea56b12a8bfe；已读COORDINATION/self及已登记六相关task、strategy-account-bridge新增范围，最后fetch无增量，无同写冲突。
- 原来源 https://www.douyin.com/video/7699879945107016969 ，量化舵，2026-10-23 23:06发布；111.27秒原片、完整本地ASR、20关键帧及作者评论已核。作者未公开参数，画面成交额/评论成交量差异保留；逐段最低日圈点属事后选择，98%是同期历史表现比较而非预测胜率。支持保留热门股降温观察，预测/美股迁移/账户改善未验证。
- 本地报告 docs/experiments/focus-stock-momentum-source-review-2026-10-24.md，SHA a808f0dde2e3ad4cec32a86cb2733286e8e0ce9fb4c5653bf4dd4e5acec227f4；同名raw/source-manifest.json列原件/指纹/失败/验收；registry只加本键且保留旧项，INDEX只加本行，progress沿原。两表分别记录原声称性能及相对已有信息未测增量，给中美范围建议和反例。
- 归置exit0，报告/registry/manifest哈希读回一致；PNG首次断言因macOS ._说明文件计入40而失败，排除说明文件后20张通过，未删除。Codex open仅queued。媒体/转录/抽帧约12.67MB在已核外盘，无下载权重/付费/生产/交易/真实收益实验，已关闭本次搜索页。
- 工作分支/base沿原；源码报告未提交/推送，成果仅本地、远端不可复现，协调分支仅本摘要。原身份阻塞已解除；原版完整复现仍需完整定义/逐日底表，自定算法须另立定义，不能冒充复现。无待运行后台，无重跑封存实验。

## 本轮开工与此前历史

# 当前：来源已找到，归档原模型核验及中美观察范围

- task-id focus-stock-universe-20261024；owner 01a16bd6-3661-7cd3-a2ff-5cadfa181605/root；status active；scope_released false仅本轮自有条目；updated_at 2026-10-24T13:39:33.990517+08:00。
- checked_coordination_sha 4367807a021d13407dd08556ff1eddff04313097；已读 COORDINATION/self/research-dispatch-controller/market-observation/sentiment-factor-research/market-style-observation-20261020/downside-sensitivity-universe-20261023/investor-observation-map；最新strategy-account-bridge仅已有因子组合，不接管彼此。准备同步时远端引用已变，首次基线断言停止无写入；已读差异后恢复。冲突决定：root唯一写本题来源报告及登记键，不改其他任务数据/报告/生产。
- 范围：docs/experiments/focus-stock-momentum-source-review-2026-10-24.md、raw/focus-stock-momentum-source-review-2026-10-24/小清单、registry.json仅本报告键、INDEX.md仅本报告行；自身progress和输出计划。验收：准确原出处+日期、ASR/画面/评论核验、解释事后圈点、A美范围和观察增量边界、归档读回/归置。
- 原视频 https://www.douyin.com/video/7699879945107016969 ，量化舵，页面发布时间2026-10-23 23:06，111.27秒。原片/ASR/20帧已读，作者拒绝完整公式披露；评论成交量与画面成交额有歧义，不编造参数。旧blocked身份问题已解决，原公式复现和预测仍未成立。采用research-closure/lei-lowfreq-research/current-standards；没有新技术定义、收益实验、拟合、交易规则或生产改动。
- 外盘UUID DEBA1C85-6059-3865-B50A-A8EE1F80E4D9核对通过，64MiB计划、1MiB本地预算；资料在 /Volumes/win+mac通用/LeiSignal-新实验结果/focus-stock-universe-20261024/focus-stock-universe-20261024-20261024T133543-24c706c99401/result/ 。视频专用API forbidden不重试，实际页面媒体+本地已装ASR读取成功，无安装/权重下载。
- 工作分支codex/factor-unit-research-20260915，基础18e64fa632dba5dbad0e5fcae09b4ccc75f119a9；研究成果仅本地未提交/推送，只推协调元数据。两Sol只读证据助手结束，root独立核关键帧；效果运行0。下一步完成来源报告及两表，释放自有归档范围。

## 历史（以下旧阻塞已被本轮来源发现解除）

# 焦点股模型：中美股票范围与观察用途核对

- task-id：focus-stock-universe-20261024；owner：01a16bd6-3661-7cd3-a2ff-5cadfa181605 / root。
- 状态：blocked / model_identity_missing。股票范围建议可交付；原模型公式、零线与效果尚未核实，研究未结案。
- 日期：2026-10-24，Asia/Shanghai。工作分支 codex/factor-unit-research-20260915，基础 18e64fa632dba5dbad0e5fcae09b4ccc75f119a9；本记录仅本地，未提交源码。
- checked_coordination_sha：623b195bb4cd28c17a4170c365b650d3b3778875；checked_at：2026-10-24T10:59:44+08:00。
- 已读：COORDINATION、research-dispatch-controller、market-observation、sentiment-factor-research、market-style-observation-20261020、downside-sensitivity-universe-20261023、investor-observation-map 的相关现状。唯一写者 root，仅本记录与自己的协调摘要；相邻资料采集、因子工作台及旧情绪研究保持原负责人，不接管、不改冻结结果。

## 本轮问题与边界

用户询问“冰点焦点股东然模型”，认为可能选择成交集中的龙头，想了解 A 股、美股股票范围与观察用途。任务先确认身份，再评价适配及额外信息；不修改交易规则、生产界面或原策略。不把候选解释当作原模型。

采用 research-closure、lei-lowfreq-research；本轮为定义与已有证据核对，真实市场效果实验 0、拟合 0。已发准确名称/页面链接澄清，尚未收到回复。公开发现请求 6 次（3 次工具调用，分别 2/3/1 个查询），未定位可靠原始公式；失败搜索保留为本轮成本，不据此声称模型不存在。用户需提供的核心资料是原模型准确名称或来源，而非替 AI 设计方法。

## 已确认与建议

1. 仓库检索未找到对应“焦点股”模型；`src/lei_signal/market_context/market_mood.py` 的 cn_mood 是融资变化与板块价格代理，明确不合成为冰点，与待查模型不能混同。旧冰点简化复现也不能借用为本题效果证据。
2. 条件性建议：若原定义确为成交额前列股票的动量，A 股主观察范围用沪深普通 A 股、北交所单列；美股主观察范围用美国主要交易所的本土普通股，境外发行人/ADR 单列，排除基金、杠杆产品、优先股和权证。成交额排序比直接按成交股数更适合衡量交易资金集中；确切窗口、选取数量与汇总公式待原定义确认。
3. 全市场焦点与大盘焦点分开。沪深300/中证1000、标普500/罗素2000可作预设分层对照；纳指100是独立适用范围。不能用少数大股解释全部市场，也不能用今天名单回填历史。
4. 观察至少分清：焦点股价格变化、其相对整个股票范围的强弱、其成交额占全范围的比例。低于零若是涨跌幅只说明下跌，若是相对涨跌只说明落后，若是标准化分数只说明低于基准水平；任何一种都不能仅凭负值判为极端低迷或未来反弹。
5. 拟评价用途是为宽基/ETF低频复盘区分少数热门股支撑、普遍转弱及修复是否扩散。独立增量须与指数自身涨跌、全范围涨跌和上涨家数比例比较，市场方向/反弹概率/提前时间/少亏少赚目前均未评价。

## 现有资料核对与更新

- `docs/experiments/common-universe-acquisition-2026-10-24.md`、raw/coverage-manifest.json 为早间13池来源目录，不能当完整历史回测资格。
- 已另外核新 `docs/experiments/raw/universe-history-completion-2026-10-24/controller-membership-admission.json`（10:44+08）：中证1000已有2022-12至2025-11的36个月成员获原负责人接受，中证2000已有2023-08至10三个月；不能沿用早间报告声称完全没有历史成员。该文件仍明确完整价格/退出/分红资料未合格、完整历史股票池未完成、效果运行0。
- 未读取外盘大原件、未重新取数。storage于10:59+08核内盘余量20,176,203,776字节，外盘身份正常；本轮仅新增小记录，无大结果。

## 委派、核验与恢复

Sol medium助手 universe_evidence 仅只读早间13池报告及小清单，write_paths=[]、network_allowed=false、max_agents=1。root独立核原代码及新增历史成员准入，纠正助手仅依据早间快照的覆盖限制；未将资料核查当科学性能结论。实际模型费用未知。

恢复唯一必要输入：准确模型名、页面链接或原公式。取得后先绑定原公式、股票筛选、价格口径、输出单位与可用时点，再决定是否已有同题效果证据或需有界检验。当前未建立新实验合同、不登记已结案报告、不修改系统目标数据库或规则、不创建后台任务。归置检查与协调推送读回由本轮工具回执确认。


## 交付前协调增量

2026-10-24T11:03:00+08:00：共享远端引用在准备同步时已从623b195变为c7f0ace93ffbeba4dfd5110d5a503600dd3ff0de，首次基线断言及时停止，未创建提交或修改索引。已读唯一变化downside-sensitivity-universe-20261023：本批资料补采已结案，成员36/3月结论不变，完整历史仍未完成。实际checked_coordination_sha更新为c7f0ace93ffbeba4dfd5110d5a503600dd3ff0de；范围不冲突。

协调摘要引用本地进度 docs/ops/work-progress/focus-stock-universe-20261024.md；scope_released=true，无活跃代码写入范围。归置检查本轮退出0。此协调副本已包含现有结论和阻塞；未提交源码或归档实验。
