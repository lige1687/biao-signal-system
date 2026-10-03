# LEI 技术阅读页与限定等待研究：持续进展

最后更新：2026-10-03T15:27:32.339164+08:00，Asia/Shanghai。负责人：本聊天主控；本地 Air（macOS arm64）。此前明确开发委派使用 Sol6.1；本次同步由主控完成，没有新派发实验。**仍由本任务负责；本次不是接管、移交或任务结束。** 2026-10-03 的持续同步指令替代此前交接包的接管安排；旧交接记录只作历史材料。

## 原始目标与当前范围

让项目和 Web 按准确角色引用两份只读权威文档，提供技术体系与因子指南阅读入口；改善研究页面的直观程度；在已有定义、资料和预算内完成有边界、与其他负责人不重复的技术信息研究。主战场是宽基与 ETF。页面清楚可查、定义正确或离线平均改善，都不能写成线上收益，线上增量未测量。

两源的职责、固定路径和确认指纹见 `configs/strategy-documents.v1.json`。技术体系是交易语义最高来源，实现文档是计算定义依据；V1 为历史对照。源正文与指导包不进此次 Git。改变交易含义、研究范围、过滤或输入变量，必须先列明受影响因子与历史可比性并由用户确认。只改 Web，不改冻结 Streamlit、生产交易、阈值和封存结果。

## 已完成（证据与真实边界）

| 内容 | 成果位置 | 验证与限制 |
|---|---|---|
| Task 1–6 的权威索引及阅读页，后续因子指南入口 | `configs/strategy-documents.v1.json`、`configs/factor-guide-documents.v1.json`、`src/lei_signal/api/strategy_documents.py`、`src/lei_signal/api/routes/strategy_documents.py`、`web/src/pages/StrategySystemPage.tsx`、`tests/unit/test_strategy_documents.py` | 固定 ID、只读、确认状态、章节与安全渲染；原设计/计划在 `docs/superpowers/specs/2026-09-29-lei-strategy-documents-web-design.md` 与 `docs/superpowers/plans/2026-09-29-lei-strategy-documents-web.md`。本分支发布本任务历史准确代码，不覆盖共享工作区新版 |
| 前端阅读改进及均线密集区展示 | `docs/archive/handoffs-plans/2026-09-30-frontend-readability-sol-plan.md`、同日 validation、`frontend-readability-2026-09-30/` | 历史检查记录保留。后续 frontend 增量只作为 `implementation.patch`、`sol61-increment.patch`、`ma-cluster-web-increment/increment.patch` 发布，**远端运行树未应用这些补丁**；依赖其他负责人修改，标记 WIP，不宣称全站已同步 |
| EMA20 先满足、SMA20 等待路径的固定历史描述 | `docs/experiments/ema-sma-waiting-path-2026-10-02.md`、同名 raw 的 protocol/receipt/acceptance/controller，`src/lei_signal/research/ema_sma_waiting_path.py`、对应 unit test | 137 起点：88 先失效，49 确认，47 成熟配对、2 未成熟；同起终点等待后的涨幅平均少 0.989616 个百分点，报价平均贵 0.891262%。没有证明等待纪律整体无效，也没有证明新规则有效。独立 40 组 6033 项核对记录通过；线上收益未测量 |
| 每周入金的两 ETF 历史账户对照 | `docs/experiments/broad-etf-weekly-income-2026-10-02.md`、同名 raw/execution 三个计算与模拟测试文件 | 12 账户、50388 日记录、0 对账差异；全期改善不能盖过近一年半落后。来源及公司行动资格仍有条件，最后独立人员复核未完成；不新增宽度交易规则，不重跑 |
| 研究报告登记 | `docs/experiments/registry.json` | 从远端基础只增加本任务两份报告条目，不复制其他任务登记修改。详细结果材料未公开交付，链接缺口见下 |

本次隔离发布树检查：阅读接口与等待路径合计 34 项、模拟资金 14 项测试通过；前端构建（745 模块）及目录检查通过。使用本机已有依赖，未验证冷安装或其他操作系统。实际命令、退出码和结果见 `docs/archive/handoffs-plans/technical-mainline-sync-2026-10-03/validation.json`，没有用历史通过冒充本次检查。

## 正在做

独立分支第一阶段成果已推送，远端核对 SHA 为 `67d850cb7ff3d00e85f470a6ff6600b8e6b14de2`。本轮接续条件整理已完成，见 `docs/archive/handoffs-plans/technical-mainline-sync-2026-10-03/next-question-readiness.md`。仍由本聊天负责证据与下一问题启动前的核对，目前没有可独立启动的新效果问题；需要明确原义/合格资料或范围分配变化。没有后台研究、模型拟合或市场数据请求；不是把计划写成运行中。原共享源码、分支、暂存区保留，使用独立索引提交。

本任务持续负责：阅读页既有成果与故障复核、限定 EMA/SMA 等待问题的证据维护、自己的进度文件，以及下一问题启动前的定义与归属检查。已结案问题不因仍有负责人就重跑。

## 计划做 / 暂停 / 未完成

- 接续准备已完成：复用 Pro 第二轮与已核的原技术负责人最新成果，整理下一问题启动条件与停止条件。计划做：仅在出现唯一原义/新合格资料/明确不重复范围后，绑定下一有边界问题；不反复重做去重或凭空另起方向。
- 暂停：2B 盘中跌破但收盘收回，还是收盘跌破后另日收回，尚未取得唯一明确原义；正式定义与适配器归原技术因子任务负责人，本聊天不抢做。第三轮 Pro 尚未送审或收到回复，不宣称运行中。
- 未完成：完整作者 EMA 稳定条件、完整底部/模块 A 的效果验证；这些并未被窄等待研究回答，也没有被本次同步自动授权或独占。
- 未验证：远端干净依赖安装、Linux/Windows、全站数据与部署、完整全站页面所有交互。历史页面检查没有覆盖真实 200% 缩放/所有失败场景。远端阅读页缺两原文时应明确报缺失；不得回退旧 V1 正文。
- WIP：共享工作流四个文件的当前版本已偏离冻结指纹，其整文件不属于本任务，未推送。等待工作流集成测试源仅在 `wip-owned-workflow-tests/` 保留，不列为本分支可运行集成入口。旧合同不能直接执行。

## 并行任务应避开与可继续范围

请暂时避开本任务的 `ema_sma_waiting_path.py`、对应 unit test、上述两个已封存问题和本进度文件；修改已有 `/strategy` 的索引/接口/阅读页前先与本任务协调。不要把所有技术因子或未来页面都划成本任务独占。

本任务避开原技术因子负责人 K01/P01/C01/Q01 与 2B 正式定义适配；避开“push git+oneapi+任务验证验收”的四项规则比较、小时资料与同日路径；避开“外部增量”的多候选偶然挑中赢家检验工具。情绪、宽度、宏观、经典因子、账户政策和其他页面共同改动均保留各自归属。另一 AI 可从自己独立分支推进其明确负责问题，不接管或并发写本任务输出。

## 已封存结论 / 不要重复

EMA/SMA 固定等待描述与每周入金旧研究各已运行一次核心计算。等待研究 1 科学变体、0 拟合、0 网络取数；工作流记录 12.079047333994822 秒 / 原 3600 秒预算，资格检查不冒充效果运行。历史工程检查有覆盖重叠，不将 23/134/58 相加为独立研究次数。冻结证明旧版失败与第二版通过均保留，不改锁、不删失败，不换参数追求正结果。只在新证据、前提变化、明确冲突或用户要求下重开，并说明原因。

## 基础版本、资料与上传边界

目标已核：`git@github.com:lige1687/biao-signal-system.git`。独立持续分支：`task/lei-technical-reader-research-progress`（本次用户指定 task/ 命名）。发布基础：`91a93ad2b881fbeed1ee15ae03d4fc3bbff08342`；共享工作区 HEAD：`18e64fa632dba5dbad0e5fcae09b4ccc75f119a9`。从 `597f0f67de9c00e5a4e048b0db3c1251df286a06` 至共享 HEAD 提取本任务阅读页提交差异，排除前五个无关 Jev 提交；附加明确归属的本地成果。不是共享全站快照。

本文件所在提交可用 `git log -1 --format=%H -- docs/progress/lei-technical-reader-research.md` 查到；推送成功以远端完整 SHA 核对为准。本分支不合并 default/main/master、不上线、不部署、不改变权限，不上传原文、供应商原始行情、活跃 DB、密钥、登录态或大型材料包。仓内未发现此任务分支的发布/付费工作流配置；外部 webhook 未核实，不据此承诺不存在。

`withheld-materials.json` 逐项列未上传路径、大小、SHA256 和原因。等待输入 panel 指纹 `382d82ff21cb43758bca8e596026284ba2821038a79e1b4c331135119524679b`；报告指纹 `cd15f2e88d1431e4ea3583abce96c32083a22353e63b31e64fc5d65bfcfbb9e0`。来源、冻结合同与结果缺失的链接不能靠报告均值反造；查看结论不需要这些数据，但真实重演需要获准私有材料与匹配代码。无模型权重依赖，线上增量未测量。

## 另一 AI 的第一步

先核远端分支和本文件实际提交，再读两份报告与 protocol/acceptance；核 `withheld-materials.json`，区分已公开代码、未应用补丁与未交付数据。最低可运行检查：在隔离 clone 根目录以 pytest 运行 `tests/unit/test_ema_sma_waiting_path.py`；每周入金只运行 `test_synthetic.py`，不得运行真实账户入口或旧冻结合同。先核新版本是否已修复旧问题，再按自身授权推进，不继承本机登录、资料许可或交易权限。


## 统一协作接入：2026-10-03T14:01:55.025115+08:00

唯一跨任务当前记录：远端 `coordination/lei` 的 `docs/coordination/tasks/lei-technical-reader-research.md`。规则入口是该分支根 `COORDINATION.md`；本轮已读规则完整 commit `0b758e7e10f720c44cbd898d511ff392f2857535`（版本1.0）。本文件和 `docs/ops/work-progress/technical-factor-mainline.md` 留作本工作分支阶段证据，不再承担跨分支实时状态。每轮实质工作先 fetch/read 最新记录，更新自己的记录并核验同步后再开展可能冲突的修改。当前无新实验；只保留原负责人范围，未知任务不视为空闲。


## 2026-10-03T15:27:32.339164+08:00：协作刷新后完成独立阅读页验收

本轮沿用同一task-id与既有AGENTS入口，不重建任务；实际读规则与相关新任务基线 `15b3e4e0edd878c3e84ef30482d108e492563dbd`，推前审阅 `7b7b70050cb4661ca36966517ea2324da8d5db50` 增量。登记提交 `d8cb0077de83ce2b4aba398c177220b2b8360b5d` 已在远端读回，只有本任务文件变化。2B归属文字已由对方澄清为“保留问询”，不构成实施移交；原义和未来实施/独立验证分工仍缺条件。无新效果实验。

本阶段独立工作已完成：只验收已发布阅读器在桌面1440×900与窄屏390×844下的合成文件状态与导航。12组通过/0失败，包括缺失路径/恢复按钮、变更警告、完整Markdown渲染与危险HTML清理、章节URL刷新、真实Tab焦点2px、减少动态效果、实现/指南资料身份保存。119个前端源文件按输入完整commit `179a4c89447a55eac63e900b05295159e5659359` 逐字节比较通过，复用原构建不重复build；运行代码与技术规则未改。来源真实可用、真正200%缩放、其他系统、全站和线上增量未验证。

代码之外的新交付为 `docs/archive/handoffs-plans/technical-mainline-sync-2026-10-03/reader-ui-acceptance/` 的脚本、receipt、README、SHA256SUMS和10张合成截图；均不含原文、行情或账号。CUA初次读取超时一次，复用既有Chrome/Playwright的独立环境完成，不复制登录。首次协调push被并发拒绝后fetch审阅再单文件推送成功，无强推。精确失败与限制见验收README。

本任务仍负责阅读页及等待研究证据；已封存题目不重开，共享前端补丁暂停应用，技术抵扣候选/转黑/市场观察/外部工具各归原任务。当前本轮没有尚在运行的浏览器或测试服务（自有服务正常关闭），不停止其他任务。下一步仅在明确新原义/资料/分工或实际未修缺陷出现时按协调规则续接，不为持续运行重做本次12组。
