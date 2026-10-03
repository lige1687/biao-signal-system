# 市场理解基础、指数对照与超级Agent宏观解读

日期：2026-10-04 Asia/Shanghai。任务investor-observation-map。软件阶段completed；资料资格缺口blocked，原任务责任继续。本轮不是收益研究，不提交因子性能表冒充有效性。

## 一句话结论（大白话）

现在可以直接看中美指标图、知道参考线从哪里来、与四个指数比较同段变化，再让超级入口按同一资料解读并回图核查；这条使用流程已测试。缺失数据仍留空，历史位置不能当成买点，尚未测量是否提高投资收益或真实用户理解。

## 原目标、业务增量和证据入口

准确摘录与权限见[original-goals](raw/market-foundation-agent-2026-10-04/original-goals.md)。沿用已获认可的[设计](../superpowers/specs/2026-10-03-market-foundation-agent-design.md)和[计划](../superpowers/plans/2026-10-03-market-foundation-agent.md)。与基线11662774379c07466935386fa7ef25ceac63bb24比较，新版从“统一图页与经验固定线”增加可复算历史位置、可核定义、四指数同日期比较、变化散点、两指标组合、事实不一致提示、选定官方事件与Agent回图。

这里的“更好”仅指可操作和信息可核查，未测用户理解效果、预测效果、完整资金收益或线上收益。没有市场拟合/回测/新数据采购，不能拿软件测试通过代替投资结论。

## 本轮已完成

- 数据总览：保留24个指标模型及A9/美16范围（中美利差共享），窗口内重算P20/P50/P80并写日期/有效数量/公式；缺数不填零。官方PMI50与算术零线保留，其余未经证明的固定经验线撤下。绿色机会观察、红色压力观察都有前提，不是交易指令。
- 四指数：沪深300、上证、标普500、纳斯达克综合NASDAQCOM，明确不是纳斯达克100/QQQ。同频同期间配对，日频不补日期，月/周未结束期间排除；只比较同区间变化，不以同期相关证明领先或收益。
- 有界发散：最多两指标的独立单位组合；指数上涨同时压力指标增加的事实提示，不预言必跌。首批BLS就业/CPI/PPI安排区分所属月和发布时间，保留夏令时差；仅日频同窗图允许事件线，月/散点不会错误显示为已标记。
- 超级入口：主输入中宏观问句与快捷入口打开同数据面板，当前状态/变化/交叉核查/逐项依据/缺口/看图链接完整。确定性整理，不额外调用模型，不写旧聊天历史；并非后端通用LLM工具注册。买卖问句仍只解释背景，不改技术规则。
- 原基本面利率/宏观显示：窄范围纠正CPI2、VIX15/30、信用6、融资3.5的无依据风险解释。共享zones.ts、原策略、Streamlit、后端和情绪研究不改。旧仓位带/相关性组件不在本轮完全科学核验范围。

源码位于web/src/features/market-understanding/{reference-evidence,comparison-model,events,use-market-data,IndexComparison,macro-reading,MacroReadingPanel}及已有图卡模型；页面范围仅MarketUnderstandingPage、FundamentalsPage显示、AgentWorkspacePage宏观入口。

## 权威来源与参考值边界

[来源账](raw/market-foundation-agent-2026-10-04/source-ledger.json)记录本轮6/6请求及访问等级，旧累计不清零。PMI与VIX仅获得官方搜索正文，不声称完整PDF已精读；联储FAQ和BLS日历实际读正文。未复制全文和第三方行情逐行数据。联储2%目标使用PCE，CPI图不借用该线。

P20意为当前历史约20%观测不高于它，不是权威机构制定的机会线；P80压力较高只是相对自身窗口的位置。窗口、采样频率或上游修订变化会改变数字。至少12个有效点是显示条件，不代表统计可靠。输入沿原API，逐期发布时间、修订版本和数值真实性未完整核验；官方定义可定位并不使第三方数据自动合格。

## 实际验证与限制

[validation.json](raw/market-foundation-agent-2026-10-04/validation.json)：12基础+14图表+4整合+33资料，共63组检查通过，最终TypeScript/Vite758模块通过。390px三页面和实际数据使用链已查；旧VIX/CPI大图可开关。归置器exit1，既存.git和docs/progress白名单问题保留，不能称全绿。构建已有大包警告。

[独立目录恢复](raw/market-foundation-agent-2026-10-04/restore-validation.json)：复制8个必要文件，逐字相同，复用本机node_modules，12组模型检查exit0。仅证明源关系与最低模型条件，不等于洁净安装、完整服务恢复、跨OS或数据许可通过。

## 尚未完成与停止条件

A股PE/ERP仍缺合格观测；FINRA月度融资、CFTC分类头寸、盈利预期与修订、完整中国事件日历未接。BLS仅选定2026快照，覆盖到10月，之后显示过期并要求核官方，不编后续日期。FOMC页面取得但未逐日期核查，未植入推测会议。宏观历史发布时间/修订资格由既有远端任务负责。

这些缺口不能只靠增加前端完成。本阶段来源预算6/6到界，不继续无上限查源。新资格成果出现、已有负责人交付合格输入，或用户明确新范围/预算后再开相应部分；不重跑QQQ/VXN、宏观18/18、AAII/NAAIM效果或黑绿实验。情绪负责人新NAAIM131周价格背景比较已登记，本线只引用其正式证据，不启动同题。

## 运行、版本与接续

工作分支task/investor-observation-map-progress，原负责人继续，基线如上；设计提交087e3bb5b0f221cab941800bea27dc8fc3b5646a。本文件所在Git提交是本阶段代码版本，准确发布SHA由协调记录引用，避免自指。规则核至66068173f96a8fcc51d5740adce963ecfadcb597；规则v1.0 SHA6871aa85da956453ca8e4d077e9bd9d9bf229df42c8447ffb94f97ba7f2461e0未变，无同文件/实验登记冲突。

中断后原预览退出，确认5185无人监听后只恢复自身预览PID26760/session46007，绑定127.0.0.1；原API1753/8000不动。无金融实验、训练或checkpoint。复制文件不迁移进程。其他AI避免同时写本轮具体显示块，独立研究可继续，记录不是锁。

最低命令，从仓库根运行：

```sh
cd web
npm ci
npm run test:market-foundation
npm run test:market-dashboard
npm run test:market-integration
npm run test:market-understanding
npm run build
LEI_API_PROXY=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1 --port 5185 --strictPort
```

npm ci仅恢复命令，未在本轮洁净环境执行。锁文件沿仓库web/package-lock.json，Node22.22.1/npm10.9.4实际使用。无需新增密钥；LEI_API_PROXY/LEI_WEB_PORT是可选非密钥变量。后端服务及数据许可须由已有项目方式具备，本报告不承诺远端8000存在。不修改全局环境，不同步登录态。

接续先读最新COORDINATION.md和自己记录，核完整Git版本及raw/SHA256SUMS，再跑最低模型检查；核新版是否已修旧问题。自己的进度文件与协调记录继续使用原任务ID，不建重复任务。独立恢复目录和截图仅本地，权重/数据库/索引新增不适用。源码和小证据入Git，大行情、私人策略原件与个人资料未交付。

## ARCHIVE：本阶段已封存

2026-10-04软件检查结论封存；仅新改动、失败或输入/适用范围变化时重查对应部分。保留首次失败与限制，不追加金融实验追求正结果。下一步优先核对用户实际阅图反馈，以及已登记来源负责人能交的单项合格输入；在无此输入时不宣称全系统数据补齐。
