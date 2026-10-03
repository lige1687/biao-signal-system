# 当前：六项流程建议融合到现有任务，由本方验收

更新时间2026-10-04 00:08 Asia/Shanghai。classic-factor-research原负责人继续；本轮active，scope=跨任务分发/独立验收，无新因子实验。用户明确：“就你6个方向，你去核对和分发吧哈，让他们顺手把你的调研的任务做了”；前文“交给他们去做，然后你验收”。

已核最新协调66068173f96a8fcc51d5740adce963ecfadcb597及六个现有对话最近消息。原规则v1.0不改。工作分支task/classic-factor-progress，基础及最新已推385bb0c4ce1833b2162f1e5341c97adb8d85079e。新的分发文档拟写docs/archive/handoffs-plans/research-workflow-fusion-2026-10-04/及自己的两进度；不写源码、共享研究规范或他人记录。

计划分发（尚未发送，发送回执后更新）：
- D1从实际困惑选题、D2负结果解释：现有「因子挖掘+lei系统（非情绪因子」复用已交技术流程样板，补真实题目引用和结论边界。
- D3新旧错误分解：现有「宽基ETF量价与风险因子发掘验证」只用已有合格配对预测、0新增拟合，核改善/恶化贡献与原误差差额一致。
- D4互补/重复：现有「外部增量」核已有共同错误/组合工具，人工例或已验能力可复用；STUMPY候选生成不冒充金融互补。
- D5未来观察准备：并入技术对话，只交就绪/缺口卡；dot-pro-increment-review明确paused，不重启或接管，breadth input_observation_only保持，不创建自动化、不收新样本。
- D6开工材料检查：现有「整理 LEI 系统过时内容」仅核classic-baseline-adoption一个真实缺件例及恢复条件，0删除/移动/安装/重跑。
四个接收者都是既有用户对话，非新建task或模型替换；每项单一负责人，本方负责实际内容与关键数值独立验收，不靠complete标志。已完成的给精确引用，不重复写通用规约。

本轮验收看业务增量及边界，实际结果未收到前保持pending。真实研究/来源/付费预算不增加；只用既有文件/记录及必要少量人工核对，不重跑封存经典/技术/情绪实验、不改生产。工具复用/定义/前瞻资格由原owner确认。无本题新市场PID/checkpoint。只允许各对话自有路径；需要跨共享文件先登记具体块，记录不作排他锁。

后续先实际发送四条限定消息→核接收/范围→已有成果就地验收、未交付明确pending/blocked→在同一记录更新。消息发送本身不等于实施或通过；不自动保证后台唤醒。旧classic入口与报告封存保持。
---

## 前序记录（保留）

# 当前成果：经典方法已落到保存结果核查入口

- task-id：classic-factor-research；原负责人本聊天主控继续负责，非接管或整体任务结束。状态：本有界实现completed，持续责任active；当前没有运行中的本题市场实验、模型任务或助手。更新时间2026-10-03 13:06:15 UTC（Asia/Shanghai 21:06:15）。
- 最新用户原话：“那你现在继续做啊，学习页先不用吧，主要是落实到项目里边”。当前目标是把合理简单对照变成项目可复用能力；学习页与路线修补均不推进。业务增量定义为识别“新模型赢旧模型却输更简单办法”的研究误判；因子效果、资金与线上收益未测量。
- 工作分支task/classic-factor-progress；本轮基础cf8d630954257fff441d55a974f8a0fe95eca443；**最新已推并核实完整成果385bb0c4ce1833b2162f1e5341c97adb8d85079e**。普通push成功，git ls-remote完整SHA等于本地；准确commit的源码与报告逐字相等，manifest blob5950d4263f821a38690d3c4f1e2e581dbcdb373c与本地Git对象相同。
- [报告](https://github.com/lige1687/biao-signal-system/blob/385bb0c4ce1833b2162f1e5341c97adb8d85079e/docs/experiments/classic-baseline-adoption-2026-10-03.md)；[进展](https://github.com/lige1687/biao-signal-system/blob/385bb0c4ce1833b2162f1e5341c97adb8d85079e/docs/progress/classic-factor.md)；[证据与最小复核入口](https://github.com/lige1687/biao-signal-system/blob/385bb0c4ce1833b2162f1e5341c97adb8d85079e/docs/experiments/raw/classic-baseline-adoption-2026-10-03/README.md)。
- 规则v1.0已读，SHA6871aa85da956453ca8e4d077e9bd9d9bf229df42c8447ffb94f97ba7f2461e0未变。启动范围85a5a28aafcfa0b25f51efedf9590cca47c51766已推读回；后续任务增量读至f9bf9e4eda2c742b4283e075dc4d4c9f513a1265。新技术两风险研究、情绪动态、市场图表和外部AlphaGen复用均不同代码块/问题，无已登记当前冲突；未登记活动未知，记录不是锁。

## 已完成、证据与用途限制

29个准确文件：新src/lei_signal/research/factor_lab/baseline_review.py；scripts/run_factor_lab.py仅新增--review-baselines/专属参数；两项新单元/集成测试；用法、工程报告/小型证据、自己的两进度；registry/INDEX只增加本报告项。四个代码/测试SHA与执行者测试版本一致；27个清单文件SHA和大小全部核对。AGENTS原有协调入口保留，未覆盖原指令。

已有受控workflow的B0/B1/B2比较不重建。新入口先通过原check_publication，再按每折评价开始前已成熟训练记录计算各ETF平均；用同一完整ETF/日期/原权重比较，独立新目录输出。原合同/预测/报告/账本不变，新增拟合0；不倒填原主检验，不自动升级结论。连续目标可用；概率/账户/状态描述不支持。缺来源/成熟训练/完整配对、源码不同或覆盖原目录会拒绝。

最终36 passed / 2 deselected，实际真实CLI通过。主控独立不等数量的三条人工评价：每ETF同分量误差20.25/12.5/4.5/0，每日期同分量20.25/10.75/5.75/0（B0/B1/B2/每ETF平均）；准确识别赢B1但输简单办法。原来源检查、保存CLI成绩重算和追加一次主控真实CLIexit0，原九件材料SHA不变。当前共享归置器针对隔离树exit0、diff检查通过。全库旧依赖/干净安装/Linux/Windows/生产未验证。

失败保留：首红测缺模块exit2；第2批36通过30失败，其中28项缺正式定义的历史依据、2项缺A01/A02原件；第3批用独立synthetic.test.sma_distance@1.0.0人工定义做完整工程流程，不伪造真实资格、不改正式定义。旧两项未运行不能称通过。提交前命令记录末尾多空行被diff-check拒绝，修空白后提交，无模型重跑。

## 预算、资料与运行

一个Sol6.1 medium实现者已结束；主控负责设计、独立核数和同步。3批工程检查、1次独立CLI；人工模型调用新演练2+保存2，核心数值回归第3批记录14、第二批另14由相同未改用例重建（非当时实时记录），共32。辅助审查0、市场0、行情请求0、付费任务0。旧风险4真实拟合、来源2/2等封存预算保持；不重新开始经典涨幅、同期解释、方法审计或波动风险问题。

约25MB合成临时目录、复制源码、完整280741字节失败日志仅本地，不入Git；相关原件清单与SHA见local-only-artifacts.json。公开旧研究的行情、策略原文、历史资格附件缺口保持，新入口不会使其自动具备复现资格；无模型权重/tokenizer/数据库需交。升级台账okr-4f4157e2957e已追加阶段证据，v52/in_progress读回一致，不宣告方向整体完成；本地台账回执未公开，不上传数据库。

曾发生本地errno28，两个最初写入失败；未删任何文件。可用空间随后从108MiB恢复1.1GiB，原因未确认，追加小写入和独立CLI成功。GitHub tree/ref备用方案未执行，最终正常本地提交并普通push；故障记录保留。共享主工作区未切换、清理、回滚或整批收走，本地未交临时物保留。没有本题PID/checkpoint需要迁移，不承诺后台自动继续。

## 当前责任与下一步

本有界实现/必要验收已完成。当前维护范围仅新baseline_review模块、CLI的review模式和对应两测试、自己的使用说明与研究证据；共享workflow/总定义/技术风险/情绪/宽度/市场页面/外部工具不接管，不圈整个CLI或ETF研究为独有。其他AI可复用入口；要修改同块先协调，不同时写此工作分支或旧封存输出。

下一步planned：在后续具备完整来源的新连续研究里，事先约定需要哪些简单对照再使用本入口。旧报告已经回答的直接引用；不为“接入演示”重拟合。没有剩余学习页任务、没有待启动的大实验，不把计划写成已运行。源码尚未合main或部署到现有服务；本次只授权独立分支同步，未强推、改权限、触发生产或付费。工作树无跟踪GitHub workflow配置；不能由此推断所有外部集成都已审计。

以下全部为历史记录；其中“拟派发”“等待教学方式确认”“不改研究代码”等旧状态已被本段替代。本协调提交自身SHA由路径历史定位，另做远端读回核实。

---

# 经典因子与研究方法：当前协作记录

- task-id：classic-factor-research；负责人：本聊天经典研究主控，MacBook-Air-126.local。会话内部ID未取得，不猜测。原负责人持续负责，不接管、不转移。
- 状态：active（落实研究方法到项目工具；用户明确暂不做学习页）。更新时间2026-10-03T12:26:28.000Z，UTC；用户时区Asia/Shanghai。
- 唯一映射：阶段历史docs/ops/work-progress/classic-factor-research.md；成果详情docs/progress/classic-factor.md。跨任务当前摘要只有本文件，旧文件不是锁。
- 规则读取commit：b172008890b39e912c8f1d0cfb9125d1e414a97f，COORDINATION.md1.0；初读0b758e7e10f720c44cbd898d511ff392f2857535，新版规则内容相同。
- 工作分支task/classic-factor-progress；发布基础d7da6cb0f9c127606b6faa572fabc9ee93f104f7；最近已推送成果cf8d630954257fff441d55a974f8a0fe95eca443（新增教学设计及阶段文档；代码/报告同560e4eef8a5571fff4543886ede4acafe7805f2d），远端完整SHA与设计文件blob已核对。
- 共享研究区HEAD18e64fa632dba5dbad0e5fcae09b4ccc75f119a9、codex/factor-unit-research-20260915有多任务未提交内容，不整批上传，不用它代表成果。

## 当前执行：强简单对照的可复用核查入口

用户最新要求：“那你现在继续做啊，学习页先不用吧，主要是落实到项目里边”。据此不再等待教学方式审批，页面与路线修补全部暂不实施；把经典研究中“复杂方法须挑战合理简单办法”的已接受结论落实到已有研究命令。
具体缺口：现有workflow自动比较B0共同训练均值/B1已有/B2新增，已能识别输给B0；但每只ETF自己的成熟历史平均只存在本任务风险raw核查，未成为可复用入口。旧方法采用审计不重跑；10-03风险报告是新增的具体适用证据，不声称旧通用流程有同一漏洞。
设计：新增src/lei_signal/research/factor_lab/baseline_review.py，读取已保存且由原check_publication验收的运行，逐折只用较早已成熟目标计算各ETF平均，与原B0/B1/B2在原来同一批观察及原权重上比较。输出到全新辅助目录，原合同/报告/预测/账本字节不变，无拟合/新行情；数值辅助不自动升级原结论或交易授权。缺某ETF成熟训练记录、配对不齐、旧依赖不匹配或收据失败则停，不删样本、不拿总体均值补齐。
精确写范围：新baseline_review.py、新tests/unit/test_classic_baseline_review.py、新tests/integration/test_classic_baseline_review_entry.py；scripts/run_factor_lab.py仅新增--review-baselines及本分支参数；研究用法只追加本入口段，本任务新计划/验收与自身两进度。公开工作树仍task/classic-factor-progress@cf8d630954257fff441d55a974f8a0fe95eca443。不改workflow.py/workflow_inputs.py/workflow_evaluation.py/question_contract.py或总定义，避开technical-factor-sequence的两风险适配器及共享块。现有benchmark-protocol不改变。
规则/任务核对e70f0f3a665d086ee36cb6b5958b6ec3543eb918，规则1.0。当前已登记写范围没有同CLI新增分支或新模块实现者；记录不是锁，后续出现重叠停冲突部分。实现拟由用户早先指定的Sol6.1/medium一个助手单写代码及测试；主控写设计/使用说明/证据并独立手算。
验收：固定人工异质两ETF案例暴露“胜原模型却输各ETF均值”；正常受控保存结果经过真实CLI产生可读报告；伪造/缺行/缺成熟数据/覆盖旧目录/不支持目标/与登记参数混用被拒绝；核源字节不变和审查期间0拟合；旧相关入口回归。无新市场实验/取数/付费，无全量回测。工程预算最多3批必要测试与1次独立CLI验收，失败计入，不为凑批次重复绿测。旧科学预算全部保留。

## 历史范围：C教学设计（已被最新要求收敛）

用户本轮明确C优先，并要求核对B是否已有其他任务负责。本聊天C指“帮助用户及后续AI学习研究思路与实验过程”，B指“日常ETF决策辅助”，与其他任务A/B/C字母命名无关。沿用唯一task-id，原负责人继续。
已完成本轮设计交付：B归属核对、现有课程核查、一份完整波动研究教学草稿和验收设计；入口docs/archive/handoffs-plans/classic-learning-design-2026-10-03/README.md，案例case-volatility.md、核对ownership-audit.md、检查validation.json。Luna low只读助手1名已返回，无后台教学/市场任务。
正在做：与用户确认具体教学方式。方向C已确定；已提出“先判断、再揭示证据、最后练写研究问题卡”，等待答复，不冒称页面实施/用户学习验收完成。
基线：现有路线已能阅读方法、案例、应用步骤和折叠答案；拟增量是先作研究判断、再揭示证据和停止理由，最后能写一份可交给AI的有界问题。学习效果与因子/交易效果分别验收，目前学习效果未测量。
已读取规则与任务快照3593b9b5393d8081acb5bbd17fd2a0a4b3ae65de，规则仍1.0。本轮仅写本任务设计目录与两份阶段文档，6文件已发布；learning-seed.json/classic-process相关条目及LearningLibraryPage.tsx属于后续拟议实现范围，尚未开写，不独占共享页面。
下一步：用户确认具体教学方案后，先补发布路线遗漏的两个既有条目引用，再按确认方案推进单个案例C；不新建因子平台、账户决策页或实验引擎。不会因教学重新跑已封存研究。

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

协作接入阶段已完成。当前工作已转入上方C教学设计与B归属核对；不改研究代码、不计算新标签或拟合。后续每轮实质工作前fetch最新协调记录，阶段/范围/阻塞/暂停/结束变化时推本文件。
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

协作接入阶段完成：工作分支0961a2cec0a31b0ad3ddbaf8e82863afc5aa0364已核远端一致，仅AGENTS追加入口和两份旧进度映射共3路径；原AGENTS字节前缀完整保留，diff检查通过，未改研究代码/运行实验。首次协调9780820345511d37acfad09fd367b39305d3532c已逐字读回，提交仅本记录；失败本地分支不发布。当前无后台科学任务，原负责人继续维护成果和协作边界，固定问题封存不扩项。
最新规则与任务核对210cc70b96e0db6ca119158971027a6119cd1b55，规则SHA2566871aa85da956453ca8e4d077e9bd9d9bf229df42c8447ffb94f97ba7f2461e0。追加读取external-quant-resources和remote-core-review：前者共享主线整合写入暂停、仅依赖/工具核查，后者黑色阶段重置资格准备且共享工具只读；不与本轮文档维护或已封存未来波动问题冲突。共享工作流正式整合尚需明确实现者/独立验证者，本任务不擅自继续此部分。未登记任务仍未知。

本版新增（2026-10-03T19:31:06+08:00）：记录用户C优先选择及B核对范围、当前只读助手与设计草稿，不改变旧实验预算或封存状态。具体学习设计尚未获确认；无新增市场/付费计算，设计文件尚未发布。

## C设计阶段交付（2026-10-03）

成果提交cf8d630954257fff441d55a974f8a0fe95eca443已推送task/classic-factor-progress，远端完整commit等于本地；设计README远端blob c0cd6655fcdca1e089034eae12e0570a8a2c812f已与本地提交比较。入口：https://github.com/lige1687/biao-signal-system/blob/cf8d630954257fff441d55a974f8a0fe95eca443/docs/archive/handoffs-plans/classic-learning-design-2026-10-03/README.md 。
B核对：技术完整策略/小时确认、市场观察、投资观察地图、情绪用途均已有原负责人；未找到完整日常ETF动作产品的明确负责人，不等于无人在做。C不接管B、不改全局导航/策略阅读/市场页。本轮只文档，未发现已登记任务同范围写入冲突；后续学习页面开写前再核。
新增真实缺口：本机classic-process有9条路线引用，已发布基线只有7条；classic-use-baseline与classic-use-attribution两条内容存在但未接路线。当前尚未修正，不能继续称九条前端入口远端已完整。
实际检查：5文档指纹/UTF-8、相对链接、9个数值与原报告、diff及敏感特征核对通过；共享现行归置检查器只读指向发布目录后通过。旧发布树检查器报docs/progress目录未列白名单，保留失败及两检查器差异，不夹带其他任务检查器修改。首次add因稀疏范围退出1，已停止依赖步骤，核暂存后按精确路径--sparse继续，仅6指定文件提交。无研究/训练/付费批次，无页面测试，学习成效未测量。
设计内容已在远端；共享本机只读委派合同仍仅本地，但不影响查看完整设计和归属证据。历史受限数据、完整风险复现和未应用CSS补丁缺口均保留，未因教学同步解决。当前等待用户对具体教学方式答复，未启动实现，不转移任务。

本版变化（2026-10-03T12:26:28.000Z）：用户收回学习页方向，执行有界项目工具接入；取消教学审批等待，旧设计作为历史草稿保留。尚无实现已启动或新测试通过声明。
