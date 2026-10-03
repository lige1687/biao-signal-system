# 经典因子与研究方法：当前协作记录

- task-id：classic-factor-research；负责人：本聊天经典研究主控，MacBook-Air-126.local。会话内部ID未取得，不猜测。原负责人持续负责，不接管、不转移。
- 状态：active（本轮协作接入及成果维护；固定科学问题completed/archived，不代表实验运行）。更新时间2026-10-03T14:07:20.645836+08:00，Asia/Shanghai。
- 唯一映射：阶段历史docs/ops/work-progress/classic-factor-research.md；成果详情docs/progress/classic-factor.md。跨任务当前摘要只有本文件，旧文件不是锁。
- 规则读取commit：b172008890b39e912c8f1d0cfb9125d1e414a97f，COORDINATION.md1.0；初读0b758e7e10f720c44cbd898d511ff392f2857535，新版规则内容相同。
- 工作分支task/classic-factor-progress；发布基础d7da6cb0f9c127606b6faa572fabc9ee93f104f7；最近已推送成果560e4eef8a5571fff4543886ede4acafe7805f2d，远端完整SHA与进展文件已读回。
- 共享研究区HEAD18e64fa632dba5dbad0e5fcae09b4ccc75f119a9、codex/factor-unit-research-20260915有多任务未提交内容，不整批上传，不用它代表成果。

## 目标、验收与规范

经典因子作为简单研究对照，学习分类、研究思路和实验过程；只推进能证明改善研究流程或因子效果的工作，国内宽基ETF优先。相同对象/日期/成熟条件比较简单参照、已有信息、新增信息；交性能与增量、反例、量级、不确定性和来源；按原规范冻结和归档。工程或同期解释通过不当未来预测或线上收益。
研究标准沿用current-standards指向mission1.1.0、question_method1.2.0、increment1.1.0、principles1.2、execution1.1.0、definition1.2.0、template1.2.1，旧冻结保留绑定。协作验收为规则读回、唯一任务记录远端可读、工作分支AGENTS追加入口及推送完整commit核对，不改变原策略/权限。

## 已完成与准确成果

以下位于 https://github.com/lige1687/biao-signal-system/tree/560e4eef8a5571fff4543886ede4acafe7805f2d ：

- docs/experiments/classic-factor-increment-2026-10-02.md及review：13定义28来源。旧涨幅/波动联合无稳定预测增量；CH3同期解释误差25.8478→20.3653（21.21%），约85.24%改善来自588000，只解释历史同期，不是未来预测或账户收益。
- docs/experiments/classic-method-adoption-audit-2026-10-02.md：已有三层比较流程足够，不重建平台。学习卡docs/literature-learning/classic-factor-usage-2026-10-02.md及seed新增一篇两卡。
- docs/experiments/classic-risk-target-fit-2026-10-02.md及numeric：四ETF1268共同观察/317日期，一次4真实拟合。加入20日波动，MSE0.35212004→0.33601140（少4.57%），但改善/恶化范围仍含负数；逐ETF较早成熟结果平均0.28800814更好，四ETF和两时期均如此。当前不新增交易规则，线上收益未测量。
- 代码：src/lei_signal/research/factor_lab/classic_attribution.py及测试、CLI归因入口；classic_volatility_risk_information.py及测试、四共享工作流文件risk专属分支。风险代码公开分支仍WIP，不能假定独立完整运行。
- 小证据：各研究raw目录、风险saved-result-checks.json、stage-execution-checks.json、receipt/state；docs/progress/classic-factor-sync-checks.json。完整逐观察行情/预测未上传。

## 正在做、下一步和范围

当前只接入现有协作规则、追加本工作分支AGENTS简短入口，不改研究代码、不计算新标签或拟合。下一步工作分支文档推送后更新准确commit；后续每轮实质工作前fetch最新协调记录，阶段/范围/阻塞/暂停/结束变化时推本文件。
固定候选已达停止条件，当前没有新科学预算，不追加参数/期限/市场。只有新合格资料、明确不同用途或用户要求重开，才先登记新问题、预算及能改变判断的验收。

## 重叠核对与避让

已读远端bootstrap与technical-factor-sequence：前者机制初始化，后者抵扣路径形状资格准备及封存C01/Q01；研究问题不同，technical明确不改共享工作流。本地external-quant和technical-mainline仅作非实时线索，分别维护外部工具/tsfresh和EMA/SMA等待/2B定义，保留原负责人。
存在共享文件层面交集：workflow.py、workflow_inputs.py、workflow_evaluation.py、question_contract.py、registry/learning-seed与行情输入；本轮只自己的文档，未发现当前执行冲突。未登记任务状态未知，不能宣称全局无冲突。
其他AI可复用结论，请避免同时改本任务classic两模块/测试、三研究raw原输出、自己的报告/卡片和任务记录。共享工作流仅classic_volatility_risk_information/forward_volatility专属分支涉及本题，不独占整个文件或ETF领域。未来修改共享代码先明确实现者和独立验证者；记录不是锁，冲突或同步失败先停冲突部分，不抢占旧记录。

## 检查、失败、进程和预算

旧成果：归因20单元检查通过；风险3代表观察过去/未来波动独立公式差小于1e-12，身份、成熟边界、训练均值、主性能核数通过。资格/冻结/真实/保存检查/零拟合登记5入口退出0；16相关检查分批覆盖，不相加为独立证据。归置检查绿色。
本轮remote/规则/相关任务已读，成果目录tracked修改为空，研究进程核对为空，无run_factor_lab/prepare-study/check-saved-results运行，无checkpoint需迁移；不推断所有远端进程为空，不杀其他进程。未运行本轮功能/新训练/大回测，文档同步不重跑研究。Linux、干净安装、公开分支完整风险流程与生产未验证。
本轮失败：首隔离目录no-checkout未初始化index，任务文件写入失败，后续错误提交7a41b793b8f072009ad4cc3296309bd06a0b6cd2仅本地；普通push因远端前进拒绝，未同步。保留在codex/classic-coordination-sync，不合并/推送。已改从最新远端创建独立目录、初始化index并按原树读入三协调文件；提交前硬核暂存清单只等于本任务记录，依赖步骤失败即停。没有回滚/清理原研究区或改封存数据。
风险总批次仍4：由2市场+2工程改1市场+3工程；已用市场1/1（4真实拟合）、工程3/3、来源2/2、助手2/2、付费0；最后冻结2人工演练拟合，保存检查/登记0真实拟合。先前18通过2失败、58通过和交接4检查尝试/6人工拟合单列保留，不清零。旧经典18线性拟合+6均值、2系数核数；方法采用3报告/8检查均结案。
两分支未发现跟踪的.github/workflows，自定义hooks未配置；外部仓库级自动化未全面核实，只普通文档push并skip ci，不运行部署/付费。

## 依赖、仅本地材料与阻塞

协作接入无权限阻塞；完整远端复现缺canonical共享top_structure_information.py、原行情及完整结构合同，共享本机源码与任务专属公开版不同，不能写恢复通过。
面板docs/experiments/raw/volume-information-2026-09-30/execution/panel.json，1,582,974字节、5348报价/1337日期，SHA256382d82ff21cb43758bca8e596026284ba2821038a79e1b4c331135119524679b；仅本地，远端不可复现。完整冻结/运行/逐观察结果、策略原件和材料包亦仅本地，分发许可未确认。每项路径/大小/SHA见工作分支docs/progress/classic-factor-artifact-locations.json和风险raw/runtime-artifact-fingerprints.json。
历史到达及行动完整性未知。恢复需用户指定获准材料位置并核指纹、与共享依赖负责人协调，不因仓库公开/私有假定许可。页面两行CSS变更只发布补丁未应用，共享CSS由原负责人维护。权重/tokenizer不适用，无密钥/登录态/账户数据库上传。

## 封存、最小接续及本版变化

封存旧涨幅联合、CH3同期解释、方法采用、当前未来波动目标和预定反例；没有新证据/不同用途/明确用户要求，不改名或调参重跑。旧结果和预算不改。
下轮fetch coordination/lei→读规则、本文件与相关任务→核成果commit和输入/源码SHA→只补实际环境缺口，复用旧结论→具备新授权范围才推进。同步不授权生产、账户、删除、强推、跨项目取数、外传材料。
首次新增唯一ID、旧入口映射、强简单对照负结果、准确成果、仅本地缺口、预算和窄避让，保留原失败和历史。文件自身commit用git log --路径定位，不无限补自指。

阶段核对：追加读取3fab17d5bd7225eb447bb2358aa9ca1ec1f97e13上的market-observation及technical-factor-sequence更新；规则内容未变。market仅CPI说明/观察卡叙事，不改经典模块或workflow，与当前文档范围无执行冲突。共享registry按条目维护，尚未登记者仍未知。

最新核对：读取9c994de31b2c325ee49080df50009e3369a52f55的新增lei-technical-reader-research和investor-observation-map；它们分别保留阅读/等待研究与观察地图范围，明确避开经典问题。无当前执行冲突，共享workflow/registry未来修改仍需协调。规则内容仍1.0。第二次普通push因并行登记被拒，未强推；改用GitHub单文件创建接口，不上传本地失败分支或合并树。
