# docs/experiments 总索引

- 2026-10-04：[组合观察、日期透明与连续宏观追问](market-observation-flow-2026-10-04.md)：80项工程检查通过，官方PE口径差异与来源资格未解决。
- 2026-10-04：[市场理解基础、指数对照与宏观解读](market-foundation-agent-2026-10-04.md)：63组软件检查通过，来源资格缺口与未测效果保留。

- 2026-10-03：[A股与美股专业投资观察地图](investor-observation-map-2026-10-02.md)：50组指标、事件、覆盖与去重缺口；接入与收益未测。

- 2026-10-03：[市场理解内容与入口方案](market-understanding-expansion-2026-10-03.md)：50组原目录、12项内容差额与12张说明卡；页面未实现，效果未测。

- 2026-09-23：[开发任务路由改为GPT-6系列](jev-gpt6-skill-routing-2026-09-23.md)：项目级路由与编排Skill改用GPT-6 Luna、Sol、Astra；32项离线检查通过，真实任务效果继续观察。

- 2026-09-22：[Jev开发任务路由Skill首版接入](jev-task-router-skill-adoption-2026-09-22.md)：项目级Skill的26项离线检查和一次真实调用通过，明确任务零Jev调用、边界任务最多问一次；20个真实任务观察完成前不自动派发。

- 2026-09-17：[外部因子方法复用主控复核](factor-method-reuse-controller-review-2026-09-17.md)：R1–R4限定返修，未验收或批准安装。

- 2026-09-17：[因子流程导航主控复核](factor-workflow-audit-controller-review-2026-09-17.md)：§6限定收口，入口与状态已纠正，导航可参考，不新增运行授权。

- 2026-09-17：[情绪对象提案主控复核](sentiment-factor-readiness-controller-review-2026-09-17.md)：§6限定收口，候选资料和待批方案接受；时点/许可/日历仍未核，不启动真实研究。

- 2026-09-17：[宽度首次描述执行](breadth-b200-first-description-2026-09-17.md) / [主控阻断复核](breadth-b200-first-description-controller-review-2026-09-17.md)：路径错误未出数，补救待授权；保留合成调用超支记录。

> 2026-09-03 整理建索引。**没有移动、改名、删除任何现有文件**——所有归档、
> 任务书、raw 数据都在原位，本文件是新增的导航层。大白话说：这里的每份
> 文件都是一次独立实验或任务的"结案报告"，之前散着放找不到，现在按
> "任务编号 → 归档"和"主题 → 归档"两条路都能查。
>
> 维护约定：新增归档或新发任务书时，顺手在 §1 字母账和 §2 对应主题组各
> 补一行，保持索引不过期。

---

## 0. 新会话入口（按顺序读）

1. 仓库根 `AGENTS.md` — 项目级约束（先读策略文档、说人话、红线词汇）
2. `../next-steps-master-plan-2026-09-02.md` — **下一步方向总纲**（九个新组合
   语义 + 五项遗留债务 + 优先级建议，当前选题的唯一入口）
3. `coverage-sync-2026-09-02.md` — 跨机器任务覆盖对账（A–W 哪些做过、
   何处存疑；注意其 §3/§4 写于 23ca826 补齐归档之前，部分"零归档"结论
   已过时，以本索引 §1 为准）
4. `CROSS-GROUP-SYNTHESIS-2026-09-01.md` — 跨组统一视图与开放冲突清单
5. `../system-architecture-and-decisions-2026-09-04.md` — **系统四轨架构
   原型 + 决策台账（D1~D4 待拍板事项）+ 研究队列**（2026-09-04 起维护，
   拍板与立项状态以它为准）
6. 本索引（机器可读版：`registry.json`，分类/判定状态供「实验报告库」
   页面使用，新归档须同步登记，见 AGENTS.md 归档规约）
7. `session-handoff-manifest-2026-09-04.md` — 9-03~04 四批 25 项交接总表

## 1. 任务编号总账（任务书 → 执行归档）

- 2026-09-17：[Agent消息 S1 通过复核](agent-news-s1-repair2-controller-review-2026-09-17.md)：110项测试、58项独立检查通过；允许继续S2，线上未恢复。

- 2026-09-17：[Agent消息 S1 首次返修主控复核](agent-news-s1-repair1-controller-review-2026-09-17.md)：18个旧反例通过，来源异常识别尚有遗漏，限定第二次返修。

- 2026-09-17：[Agent消息 S1 主控复核](agent-news-s1-controller-review-2026-09-17.md)：88项测试通过，独立反例需返修；未进入S2、未上线。

- 2026-09-17：[Agent超级入口与消息面优先级](agent-news-priorities-2026-09-17.md)：核实断更和已有接线，纠正概率报道、影响期限及停更归因；先资料可靠，再买前准备，尚未开发。

- 2026-09-17：[宽度研究准备主控复核](factor-breadth-readiness-controller-review-2026-09-17.md)：§9限定收口，保留流程偏差与来源未知，未启动真实统计。

- 2026-09-17：[因子证据S1–S3派发受阻复核](factor-evidence-zcode-dispatch-review-2026-09-17.md)：权限客户端受阻且环境身份变化，未落地修复，待确认执行方式。

- 2026-09-17：[因子库进度与OKR接入主控复核](factor-library-progress-controller-review-2026-09-16.md)：v1.1记录整理限定收口，四条OKR读回一致，未改变授权或完成勾选。

- 2026-09-16：[仓库目录治理](repo-governance-2026-09-16.md)：四层目录白名单化+169项旧产物归档+plist回填，全量测试零新增失败；AGENTS.md 立文件归置规约 + scripts/check_repo_hygiene.py 结案自检防再乱。

- 2026-09-16：[因子库建设进度总览](factor-library-progress-2026-09-16.md)：能力分层现状快照+四条OKR同步（只读整理，零计算零联网零安装）；首个真实结果与全部缺口、下一步授权状态一页可查，不是验收。

- 2026-09-16：[因子证据可靠性v1](factor-evidence-reliability-v1-2026-09-16.md) → [主控复核§10](factor-evidence-controller-review-2026-09-16.md)：09-17 S1–S3限定收口，118项回归通过；历史数字保留、零真实重跑，保留快照核验超预算违规。

- 2026-09-16：[外部候选接入设计（第三轮）](external-schools-integration-design-2026-09-16.md)：五候选（筹码剖面/波动收缩箱体/52周高/剩余动量/宽度推力）各交付规格挂点+数据代码现实+定义草案+差异表+对照设计五件套；数据全就绪、C3最便宜（2024-09-30硬检验）、D1/D2复用封存账户引擎；推荐首批C3事件清点+C1描述；零回测待授权。

- 2026-09-16：[外部流派融合深度调研（第二轮）](external-schools-deep-dive-2026-09-16.md)：最重要发现是把自家规格未实现章节用成熟工具补上（成交量剖面→§11筹码、波动收缩/箱体→§4.6+B模块，零边界成本）；C1/C2/C3精确口径与A股证据补齐；缠论/Wyckoff同构只吸收概念，Ichimoku/三重滤网/波浪类不引入；仍零回测待授权。

- 2026-09-16：[因子库方向探索主控复核](factor-library-direction-controller-review-2026-09-16.md)：v1.2限定文档收尾通过，无必需返修；方向部分采用，未授权后续实验。

- 2026-09-16：[买前判断与信息取舍：系统扩展方向讨论](practical-pretrade-direction-2026-09-16.md)：先串起关注清单、买前卡与条件变化，再补ETF产品资料；方向建议，尚未开发或验证收益。

- 2026-09-16：[外部技术流派融合候选盘点](external-schools-fusion-candidates-2026-09-16.md)：零回测调研；首批候选 52周新高距离/剩余动量/宽度推力（均结合因子线），次批 RSI-2 简单对照、双动量绝对腿、ATR 通道；已覆盖者不重复，全部待逐项授权。

- 2026-09-16：[B1首次真实描述](b1-dual-ma-first-real-description-2026-09-16.md) → [主控复核](b1-controller-review-2026-09-16.md) → [限定收口](b1-closeout-controller-2026-09-16.md)：数字及补件接受，流程偏差保留；不重跑真实统计，不代表因子有效。

- 2026-09-16：[首轮结果解释R1–R4收口](factor-unit-interpretation-closeout-2026-09-16.md)：27项教学核验通过；本并行线收口，不重开研究引擎返修。

- 2026-09-15：[首轮结果解释主控复核](factor-unit-interpretation-controller-2026-09-15.md)：部分采用；教学区间计数与过强表述限定修订，不修改研究引擎。

- 2026-09-15：[510300离线复用交付](510300-offline-reuse-2026-09-15.md) → [主控复核](510300-offline-reuse-controller-2026-09-15.md)：固定输入包接受；有限文案收尾，真实统计未启动。

- 2026-09-15：[双均线四项修复与510300数据方案主控复核](factor-unit-four-fixes-controller-2026-09-15.md) — 限定收口；1558交易日可离线复用，真实统计未启动。

- [B0剩余四项限定修复任务书](../superpowers/plans/2026-09-15-factor-unit-four-fixes-glm.md) — 用户明确授权恢复四项修复；交接区分执行者声明与用户授权，零联网、B1仍暂停。

- [B0剩余四项限定修复执行交付](factor-unit-four-fixes-2026-09-15.md) — 执行者声明四反例反转（待主控独立核验）：自填证据不再升级含分红资格、稀疏同一合法集合、pd.NA可接入、证据随包+旧包补件；真实目标仍blocked、B1未启动、零联网。

- [B0集中修复主控限定裁决](factor-unit-b0-fix-controller-review-2026-09-15.md) — 87测试通过，多项旧反例关闭；真实资格与统计尚有限制，保留可信部分、暂停B1，无自动新返修。

- [B0主控复核](factor-unit-b0-controller-review-2026-09-15.md) — 收盘价适配保留，资格/统计集中修复；[原GLM下一轮任务书](../superpowers/plans/2026-09-15-factor-unit-b0-concentrated-fix-glm.md)。

- [因子A阶段主控复核与B0方向](factor-unit-readiness-controller-review-2026-09-15.md) — 盘点有限接收；[B0长任务prompt](../superpowers/plans/2026-09-15-factor-unit-close-adapter-glm.md)：收盘价适配、四市场来源裁定，真实统计另行确认。

- AGENT-NAMES-MAIN：[名称、板块识别与主分支收口](agent-subject-names-and-main-2026-09-15.md) — 名称加代码，板块不替换成ETF；已采用Agent改动集中至本地main。

- [新GLM因子独立研究A阶段执行prompt](../superpowers/plans/2026-09-15-factor-unit-readiness-glm.md)：原目录/专用分支已准备，三族定义与美A数据资格盘点，真实研究不自动运行。

- [因子A阶段盘点交付：三族档案与美A数据资格](factor-unit-readiness-2026-09-15.md)：三族定义档案+旧证据边界建齐；四载体长日频价格已确认，复权/volume/美股市历三阻断未解；双均线协议建议 proposal_not_executable，本轮零真实统计。

- [双均线B0：收盘价适配与真实输入冻结](factor-unit-close-adapter-2026-09-15.md)：close-only适配建好测通（R1–R6全落地，44新测试）；四输入来源三档全为producer_candidate_only，主目标四票blocked；冻结候选包+b1-run-request交主控，B1未开算。

- [双均线B0集中修复：R1–R4反例关闭](factor-unit-b0-concentrated-fix-2026-09-15.md)：资格"填上就算"路径全堵（证据/日历/必需键闭合）、统计消费完整合同（截止/共同集合）、冻结包含合同原件；撤回除息日推断并作废159915错位比对；真实资格仍退出2，新申请仅510300。

- AGENT-RUNTIME-DEPLOY：[运行版更新与真实使用验收](agent-runtime-deployment-2026-09-15.md) — 已应用，第二次问答与历史恢复通过；数据库锁和日期表述待处理。

- [自有因子独立研究首批方案](factor-unit-research-proposal-2026-09-15.md)：三类定义/资料盘点，建议双均线先做美A研究；设计待确认，未启动真实运行。

- [Agent运行版合入准备](agent-runtime-integration-preparation-2026-09-15.md)：33文件无冲突，候选验证通过，备份/回退方案就绪，实际更新待确认。

- [Agent问答补修收口与试用条件](agent-conversation-controller-closeout-2026-09-15.md)：两处遗漏通过，不再返修；待定向合入和运行检查后试用。

- [因子工具首轮限定收口与能力说明](factor-lab-final-controller-decision-2026-09-15.md)：S1–S4指定反例通过，保留合成原型；终版源码归档待补，无真实有效性或生产授权。

- [因子工具集中返修主控复核](factor-lab-repair-controller-review-2026-09-15.md)：S1–S4最后一轮限定收尾，内含完整返还执行agent的任务与终版运行条件。

- [Agent中断补修二轮复验](agent-conversation-controller-recheck-2026-09-15.md)：主路径通过；流内错误与历史重试按钮两处遗漏，固定范围收口。

- [Agent真实讨论一期主控复核](agent-conversation-controller-review-2026-09-15.md)：实际回答有进步；固定补修中断识别与历史重试，锁根因保留未知。

- [通用因子工具主控初审](factor-lab-controller-review-2026-09-14.md)：94项新测试复跑通过，独立反例仍需R1–R4集中返修；[执行任务书](../superpowers/plans/2026-09-14-factor-lab-concentrated-repair.md)。

- [因子研究工具复用短名单](research-tool-reuse-shortlist-2026-09-14.md)：Alphalens和统计组件优先按需复用，ETF供数独立比较，回测框架后置；未安装或扩当前任务。

- [FactorHub API与MCP复用实测](factorhub-api-reuse-review-2026-09-14.md)：13次只读请求，区分可复用供数与仍需自建的研究判断；限流后停止，未安装或接入生产。

- [Agent下一阶段与因子库分工](agent-conversation-next-stage-2026-09-14.md)：先做好真实问答，首批因子实际交付后再评接入；附固定范围执行任务书。

- [Agent真实首问效果初测](agent-real-conversation-case-2026-09-14.md)：运行版数据库锁、隔离模型180秒超时；评价备用回答，未冒称多轮通过。

- [自有因子研究体系：目标、OKR与首轮任务](factor-research-workbench-mandate-2026-09-14.md)：通用计算/检验/过拟合风险/归因工具优先，固定ETF补证后置；未验收、无生产权限。
- [Factor Lab最后一轮收尾执行报告](factor-lab-final-closeout-2026-09-15.md)：S1–S4反例先行失败后修复转通过；必查集合由独立期望产物权威化；终版3案例62项期望全过、145测试、371回归；v1.1.0不可复放已纠正表述；待主控复核。
- [Factor Lab集中返修执行报告](factor-lab-concentrated-repair-2026-09-14.md)：R1–R4反例先行失败后修复并全部转为通过测试；3个正式案例62项期望全过、132测试、358回归；仍仅合成验证，无有效性/授权声明，待主控回调复核。
- [通用因子研究能力首轮执行报告](factor-research-workbench-v1-2026-09-14.md)：factor_lab六模块+CLI+3类合成端到端+94测试+316回归；仅合成算法验证，不证明因子有效；待主控回调复核，OKR由主控更新。

- [计划流程C1—C3主控复核](agent-plan-flow-controller-recheck-2026-09-14.md)：固定功能项通过，合入前留单行文案补丁和归档清理，不再重做整轮。

- [计划流程主控复核](agent-plan-flow-controller-review-2026-09-13.md)：主流程保留，固定C1—C3版本分支/重试/错误指引补修；未合入。

- [Agent体验一期主控收口](agent-user-experience-controller-closeout-2026-09-13.md)：R1通过，R2调查接受但完整计划未通过；既有计划流程问题转独立[任务书](../prompts/agent-plan-review-and-confirmation-2026-09-13.md)，不再重做已通过体验交互。

- [2026-09-13 Qlib Alpha158 主控审核与收口意见](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/qlib-alpha158-controller-review-2026-09-13.md)：§8确认[执行报告v1.1.1](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/qlib-alpha158-definition-review-2026-09-12.md)六项纠正及三处文案收尾完成；定义审阅已收口，无剩余必修项，初审返修历史保留。整体暂不引入，不代表Qlib已接入、因子有效或获准交易。

- [2026-09-10规范包合并](governance-pack-merge-2026-09-10.md)：权威路径、版本、冲突与模板映射；旧v0只映射不改规则，接口未接入项单列。

- [因子库后续：外部资源适配与分批接入](factor-library-external-backlog-2026-09-09.md)：四类待办已关联系统待升级台账；不扩大 v0，按具体问题逐项授权，执行时同步 OKR。

- [宽度候选收口与输入观察启动](breadth-freeze-start-2026-09-09.md)：固定两项候选；10项补证先查两区间40日，输入观察已启动，正式信号尚未就绪。

### 9-10 规范包合并与数据基础

| 编号 | 任务 | 执行归档 | 状态 |
|---|---|---|---|
| AGENT-UX-recheck-20260913 | Agent体验第一期二轮复核 | [剩余两项](agent-user-experience-controller-recheck-2026-09-13.md) | mixed；主要交互已收口，仅文案小修和计划确认验证 |
| AGENT-UX-controller-20260913 | Agent体验第一期主控复核 | [固定返修单](agent-user-experience-controller-review-2026-09-13.md) | mixed；保留改进，修U1—U4与原页面验证，未合入 |
| 固定ETF证据接入 | 数据与质量 | [固定ETF池证据与研究输入贯通执行报告](fixed-etf-evidence-integration-2026-09-13.md) | mixed；主控§13（2026-09-14）确认S1–S3工程收尾通过，必修项无；420项回归与772键独立核算通过。数据资格未解除，预算偏差保留，无预测有效性或生产授权。 |
| 动量研究样板主控复核 | 方法论与验证 | [书面复核与集中返修单](momentum-prototype-controller-review-2026-09-13.md) | mixed；最新§13（2026-09-14）确认S1–S3工程收尾通过，停止返修，必修项无。420项回归与独立772键核算通过；资料限制仍保留，后续真实运行须另授权。 |
| 因子研究工作台v1（执行者交付） | 方法论与验证 | [通用因子研究能力首轮执行报告](factor-research-workbench-v1-2026-09-14.md) | mixed；待主控回调复核。factor_lab六模块+CLI落地：6对象+双均线候选同一API、IC/状态/宽度诊断分流、试验史/时间切分/标签跨段检查、三层归因入口；3类合成端到端50项手算期望全过，94项测试、316项相关回归。仅合成验证，不证明因子有效，无生产授权；OKR由主控更新。 |
| 因子研究工作台v1集中返修 | 方法论与验证 | [R1–R4集中返修执行报告](factor-lab-concentrated-repair-2026-09-14.md) | mixed；待主控回调复核。时间资格实际消费统计、运行前冻结合同核对、比较合同固定必查（未知降级）、空期望拒绝；正式运行3案例62项期望全过、132测试、358回归；无有效性/授权声明。 |
| 因子研究工作台v1最后一轮收尾 | 方法论与验证 | [S1–S4收尾执行报告](factor-lab-final-closeout-2026-09-15.md) | mixed；待主控复核。分侧输入身份不得自比、必查集合独立权威化、审计/诊断共享合法集合、JSON严格可解析；终版批次62项期望全过、145测试、371回归；无有效性/授权声明。 |
| 动量研究样板 | 方法论与验证 | [已有动量指标研究样板执行报告](momentum-research-prototype-2026-09-13.md) | mixed；主控§10部分确认R1/R2，仍有全标签排除、期内晚取得标注和历史版本说明待收尾；368项回归，run-09绑定v1.0.4，772真实值仍按原v1.0.2封存。真实预测仍受限，不证明指标有效，无生产授权。 |
| 研究输入入口主控复核 | 数据与质量 | [书面复核与集中收尾单](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/research-input-preflight-controller-review-2026-09-13.md) | mixed；最新§10确认来源拒绝修复、295项回归和真实0/2/2；manifest输出失败已由动量样板轮 Task 1 收尾（四类写盘失败+--protocol校验测试固化）。 |
| 研究输入验收入口 | 数据与质量 | [因子开工前离线验收](research-input-preflight-2026-09-13.md) | mixed；主控部分确认，暂不整体验收。真实0/2/2复现，另发现来源哈希失败仍放行；见主控集中收尾单。 |
| 验收入口集中收尾 | 数据与质量 | [F1-F4 修复交付](research-input-preflight-fix-2026-09-13.md) | mixed；主控确认来源拒绝修复、295项回归和真实0/2/2；manifest写盘失败仍有遗漏，见主控§10，不能声称所有出口已补齐。 |
| **★ 数据地基总报告（历史总账）** | 方法论与验证 | [总报告与待审事项](research-data-foundation-summary-2026-09-10.md) | 六轮总账及失败史；“排序/对照缺陷清零”已撤回。最新结论见9-13主控§11：有限修复收口，真实数据仍只有描述/诊断可用。 |
| 主控复核四类漏放修复 | 数据与质量 | [修复与重新交付](research-controller-fixes-2026-09-11.md) | mixed；四类反例全部复现并固化测试；**撤回「数据缺陷已清零」**，当前真实状态：描述/诊断可用，排序/对照各余1项未确认问题，研究信号/归因仍不可用；总报告已加纠正说明。 |
| 主控复核三处遗漏修复 | 数据与质量 | [修复补充报告](research-controller-fixes-2026-09-11-02.md) | mixed；2026-09-13主控部分确认、仍需返修；上市来源及直接价格入口仍可漏放，测试分支需纠正。执行者原主张保留在正文，当前判断见下行。 |
| 主控返修单 R1-R3 修复 | 数据与质量 | [修复交付](research-controller-fixes-2026-09-13.md) | mixed；当轮R2/R3确认、R1返修的历史证据；后续-02已由主控§11确认有限收口，不再把旧返修当当前任务。 |
| R1 剩余问题：资格与日期分离 | 数据与质量 | [日期自洽与证据资格分离](research-controller-fixes-2026-09-13-02.md) | mixed；主控§11确认有限修复：8判断全拒、253项回归通过，日期诊断保留，真实数据仍受限；无新增代码必修项。 |
| 数据基础主控复核（9-13） | 数据与质量 | [书面复核与执行要求](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/research-data-foundation-controller-review-2026-09-13.md) | §11的R1/R2/R3限定收口保持。后续[离线输入验收长任务](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/superpowers/plans/2026-09-13-research-input-preflight.md)已另交实现、待新主控单集中收尾；不因此重开旧修复或新增授权。 |
| 数据基础第二轮 | 数据与质量 | [独立复核·交易日历·身份映射](research-data-provenance-round2-2026-09-10.md) | mixed；6项主张5项确认、1项纠正（聚合哈希未记排序规则已补）；深交所官方日历22个月与冻结价格零冲突；.SH/.SS 显式映射账目平衡。日历仍缺60个月、无法回答「当时是否已知休市安排」，行动21/21缺可得时间，归因不放行。 |
| 日历补齐与发布时间 | 数据与质量 | [交易日历补齐·发布时间证据](research-calendar-completion-2026-09-10.md) | mixed；日历补到82/82月，全区间1652天零冲突，唯一缺口由512890拆分加停牌完整解释；2026年休市安排2025-12-22已公布，2026-02两所一致。但纠正上一轮：四个受限用途裁决一个都没变，另三项阻断仍在。 |
| 身份映射接入与阻断分类 | 数据与质量 | [身份接入·用途阻断分类](research-identity-wiring-2026-09-10.md) | mixed；规范标签快照使13条代码错配清零且数值逐值不变；查清前三轮裁决不变的根因——固有属性与可修缺陷混筐，已分开：排序/对照可修缺陷清零，研究信号/归因仍余2项且接受固有属性不放行。行动时点细化为3条有下界18条全未知。 |
| **数据基础统一交接（历史）** | 方法论与验证 | [五轮自查与统一交接](research-data-foundation-audit-and-handoff-2026-09-10.md) | 保留五轮自查证据；旧“排序/对照可修缺陷清零”不再作为当前结论。最新受限状态和有限修复收口见9-13主控§11。 |
| 研究数据获取与快照 | 数据与质量 | [获取/导入→快照→校验→离线复用](research-data-provenance-2026-09-10.md) | mixed；闭环跑通并留全部来源指纹与请求时刻，855个受保护文件未变；查出 .SH/.SS 代码约定冲突已拦截。仍缺公司行动到达时间与真实交易所日历，资料判为有条件可用；未测因子、无收益结论、未接入既有消费者。 |

### 9-09 总控评审后的有限迭代

| 编号 | 任务 | 执行归档 | 状态 |
|---|---|---|---|
| 宽度固定50日对手 | [两只宽基：宽度是否值得保留](breadth-price50-decision-2026-09-09.md) | 2026-09-09 | 四条新账户、日期资格与18对持仓差额；保留有限候选，不自动扩参数 |
| 小型研究因子库v0计划 | 统一计算、固定波动过滤对照、完整资金解释与独立验收 | [执行任务书](factor-library-v0-task-2026-09-09.md) | 计划已执行，交付见下一行。 |
| 小型研究因子库v0交付 | 批量计算库、E11逐行兼容、8路径0.01元核账、E11−E10条件依赖 | [交付报告](factor-library-v0-delivery-2026-09-09.md) | mixed；过滤在选强路径整段增收但回撤更深、分段方向相反；工程交付待主控独立验收，未授权生产。 |
| 因子、信号与基准定义规范化 | 76个对象定义卡、来源映射、研究隔离复算与流程入口 | [定义登记与复算](definition-normalization-ARCHIVE-2026-09-09.md) | mixed；32项单元/报告回归通过，两条小例逐值一致；旧消费者未迁移，未证明策略有效，不改生产或OKR。 |
| ETF宽度来源与转强确认 | 510300/159915，全A与历史成分来源、W0—W3、三种简单参照、双费用 | [完整回测](etf-breadth-source-and-confirmation-backtest-2026-09-09.md) | mixed；18/22主路径完成，暂缓本轮固定宽度转强过滤但不淘汰宽度；宽度加价格确认与沪深300自身宽度保留验证，创业板历史成分链C级暂停。 |
| 混合池四方案完整评价 | 固定11只四方案分期、恢复曲线、自身48次回补与历史资格来源 | [完整结果](mixed-four-way-evaluation-2026-09-09.md) | mixed；前段防守改善、后段近满额波动且收益较低；无新策略或修复后收益。 |
| 混合池集中度与回补核账 | 原回补49次核账、时期及方向贡献、11只固定代表池双费用 | [完整结果](mixed-pool-concentration-audit-2026-09-09.md) | mixed；11只保留近满额收益及较浅回撤，后期与方向集中仍待更广历史池核验 |
| 混合池防守方式两对照 | 原月度回补、快速回补与75%简单投入；同池全期双费用 | [完整结果](mixed-pool-defense-comparison-2026-09-09.md) | mixed；快速回补23.01%/23.27%，高费20.85%/25.70%；75%削弱原退出收益理由，快回补回撤优势不稳固。 |
| ETF轮动四组重建 | 14只可交易ETF与7只行业、动态入池、逐年贡献和月度回补 | [完整结果](rotation-reconstructed-four-way-2026-09-09.md) | mixed；14只选强加退出17.31%/21.60%，7只行业未胜简单平均；旧34.38%未复现，12主路径已独立核对。 |
| 34.38%旧轮动优先复核 | 原运行恢复、上游实际函数反例与17代码数据版本审计 | [复核结论](rotation-3438-reproducibility-audit-2026-09-09.md) | mixed；原成绩不可复现，上游隐含每日调整已证实但未绑定原E3，无新增历史收益，OKR未改。 |
| 两项收益范围审核 | 旧轮动34.38%与四ETF定投14.46%的年限、代码及实际运行材料 | [审核补充](two-strategy-scope-review-2026-09-09.md) | mixed；四ETF可定位，旧轮动实际名单与准确日期未恢复，不更新OKR。 |
| 按标的研究总方向 | 汇总宽基、红利、行业、黄金与海外的特性、已有收益证据和后续优先级 | [总方向表](etf-research-direction-map-2026-09-09.md) | mixed；只汇总与安排，行业新批保留准备资料，未新增收益或更新OKR。 |
| 语义组合首批 | 同C1收复日位置/方向四组与三种退出，48完整流程、126固定路径 | [组合与退出报告](etf-semantic-combinations-2026-09-09.md) / [方法学习](../literature-learning/semantic-comparison-methods-2026-09-09.md) | mixed；仅18个不同可执行机会，E2为事后追加诊断，OKR未改。 |
| R1单退出贡献 | 只取消道路退出，4新完整路径＋330固定原买入双版本 | [技术退出报告](r1-road-exit-contribution-2026-09-09.md) / [论文方法学习](../literature-learning/r1-exit-contribution-lessons-2026-09-09.md) | mixed；核心金额/退出/新投入曲线独立核对，不支持统一升级，OKR未改。 |
| 分红公平参照 | 2ETF×2费用，到账后分红再买 | [分红再投入比较](etf-dividend-reinvestment-reference-2026-09-09.md) | mixed；4新路径独立核对通过，宽度优势仍有来源限制，OKR未改。 |
| 宽度来源审计 | 追查股票范围、原价格和生成版本 | [来源审计](breadth-source-provenance-audit-2026-09-09.md) | mixed；来源缺口明确，旧收益限有条件研究，不改OKR。 |
| AGENT-03B-runtime-integration | 讨论、补测与计划链定向合入 | [运行目录交付](agent-03b-runtime-integration-2026-09-09.md) | passed；已合入实际lab，保留新工作台；双入口与落地核查通过 |

### 9-09 给总控的全任务交接

| 编号 | 任务 | 执行归档 | 状态 |
|---|---|---|---|
| 总控评审落实 | 宽度来源、分红再投入公平参照、技术单环节及旧宽度定义补充 | [落实与接续安排](research-controller-review-response-2026-09-09.md) | watch；事实核对和计划修订完成，4条新参照尚未运行，OKR未改。 |
| 研究全任务总交接 | 截至9月8日的全部增量与非增量、收益、证据限制与三条接续优先线 | [完整交接稿](research-controller-handoff-all-results-2026-09-09.md) | 汇总已核，mixed；研究未全部完成，无新增回测，OKR未改。 |
| 研究总交接独立评审 | 关键金额另算、宽度来源与公平比较、下一批方向裁决 | [总控评审](research-handoff-controller-review-2026-09-09.md) | mixed；方向有条件采纳，尚非完整体系或生产采用验证；OKR未改。 |

### 9-08 宽基与ETF主战场专项

| 编号 | 任务 | 执行归档 | 状态 |
|---|---|---|---|
| 宽基ETF专项·投入资金更正 | 剔除未交易现金的分母影响，核原数量与缩量单位表现，明确研究欠账 | [指标与进度更正](invested-capital-performance-correction-2026-09-08.md) | 指标独立核对通过；缩量没有交易增益，完整研究未完成，OKR未改。 |
| 宽基ETF专项·组合设计追问 | 解释缩量收益代价，明确基础投资与技术交易的资金分工 | [解释与设计](broad-etf-combination-design-2026-09-08.md) | watch；只复核已有交易，组合比例及完整资金协议待固定，无新增收益，OKR未改。 |
| 宽基ETF专项第五批·数量增量 | R1候选和退出不变，仅1%计划风险缩量；4新账户＋4旧参照 | [资金缩量报告](broad-etf-risk-sizing-increment-2026-09-08.md) / [学习条目](../literature-learning/broad-etf-risk-sizing-lessons-2026-09-08.md) | 独立资金及订单核对完成；mixed；明显少跌但收益代价大，未证实通用升级；OKR不变。 |
| 宽基ETF专项第四批·技术48账户 | 两只ETF十个A/C/D版本与两个简单参照×两费用 | [技术资金比较](broad-etf-technical-capital-comparison-2026-09-08.md) / [学习条目](../literature-learning/broad-etf-technical-lessons-2026-09-08.md) | 独立资金与订单核对完成；mixed；机会少、投入及退出不同，简单道路有产品差异；OKR保持确认值。 |
| 宽基ETF专项第三批·增量决策 | 二元缓冲周度适配与趋势再参与，8新增账户/两费用 | [增量决策报告](broad-etf-increment-decision-comparison-2026-09-08.md) / [学习条目](../literature-learning/broad-etf-increment-lessons-2026-09-08.md) | 独立资金核对完成；mixed；交易可减半但无统一收益风险改善，两个记录口径差异另有说明；OKR仅按确认更新至2/4。 |
| 宽基ETF专项第二批·首12账户 | 沪深300/创业板ETF持有、宽度、简单突破×两费用 | [完整账户报告](broad-etf-first12-account-comparison-2026-09-08.md) / [学习条目](../literature-learning/broad-etf-account-lessons-2026-09-08.md) | 独立资金/成交核算完成；mixed；宽度全期领先但2025明显踏空；六宽基及技术模块扩测尚未完成，OKR保持已确认值。 |
| 宽基ETF专项第二批·旧基准 | 旧九指数份额现金重建与真正持有对照 | [资金核查](broad-breadth-cash-reconciliation-2026-09-08.md) | 已独立核对；mixed；宽度旧优势保留，ETF首12另行比较。 |
| 宽基ETF专项第一批 | 六宽基四行业总计划、覆盖清单、旧宽度A/B基准复现 | [启动报告](broad-etf-research-plan-and-baseline-2026-09-08.md) / [工作计划](../superpowers/plans/2026-09-08-broad-index-etf-research.md) | 计划与本批起点检查已交；mixed；OKR已确认登记进行中0/4，首12ETF账户另批执行。 |

### 9-08 第十四批顶部退出有效期

| 编号 | 任务 | 执行归档 | 状态 |
|---|---|---|---|
| 研究第十四批 | 顶部失效消费方反例、隔离修复及真实识别器链路检查 | [核查报告](a-top-lifecycle-consumer-audit-2026-09-08.md) | 已归档；mixed；10项检查通过，完整收益未运行，同日口径待答复，OKR未更新。 |

### 9-08 研究成果盘点

| 编号 | 任务 | 执行归档 | 状态 |
|---|---|---|---|
| 研究盘点 | 定投、闲钱投入、结构缓冲和A退出的积极结果与证据边界 | [成就与限制](research-promising-directions-review-2026-09-08.md) | 已归档；mixed；候选不等于升级，不更新OKR程度。 |

### 9-08 第十三批A道路退出与重新参与

| 编号 | 任务 | 执行归档 | 状态 |
|---|---|---|---|
| 研究第十三批 | 六A×两退出完整账户、固定17买入与原文方法核读 | [退出报告](a-road-exit-account-comparison-2026-09-08.md) / [学习补充](../literature-learning/exit-and-reentry-lessons-2026-09-08.md) | 已归档；mixed；A20少跌但少赚，其余四组无差异；OKR证据待具体确认。 |

### 9-08 第十二批修复后有限账户比较

| 编号 | 任务 | 执行归档 | 状态 |
|---|---|---|---|
| 研究第十二批 | A/C/D与简单参照12配置、全账户及独立核查 | [账户报告](acd-limited-account-comparison-2026-09-08.md) / [学习补充](../literature-learning/account-comparison-lessons-2026-09-08.md) | 已归档；mixed；收益集中与零成交完整保留，完整策略仍未完成；本批OKR证据待确认。 |

### 9-08 第十一批隔离修复与历史复测

| 编号 | 任务 | 执行归档 | 状态 |
|---|---|---|---|
| 研究第十一批 | A/C/D已证实问题修复、原日期与连续日期复测 | [修复报告](acd-repair-validation-2026-09-08.md) | 已归档；mixed；366+168次历史检查通过；完整收益对照仍待续。 |

### 9-08 第十批信息时点与定义核查

| 编号 | 任务 | 执行归档 | 状态 |
|---|---|---|---|
| 研究第十批 | A/C/D原始事件、历史一致性与修复验收 | [诊断报告](acd-information-qualification-2026-09-08.md) | 已归档；mixed；366次检查，A两个真实日期差异；修复与完整账户待续，OKR未更新。 |

### 9-08 第九批诊断与研究交接

| 编号 | 任务 | 执行归档 | 状态 |
|---|---|---|---|
| 研究第九批 | 两组入场纪律诊断、B六事件区间溯源 | [诊断报告](entry-discipline-and-b-zone-diagnosis-2026-09-08.md) | 已归档；mixed；全部资金和成交核对；不改变正式纪律。 |
| 研究交接 | 05—08、ATR、论文、完整模块的已交与未完成清单 | [统一交接](research-local-phase-closeout-2026-09-08.md) / [学习内容补充交接](../literature-learning/research-followups-handoff-2026-09-08.md) | 有限研究已交，完整系统和未来验证仍未完成；K-baseline已按确认更新3/4。 |

### 9-08 第八批有限技术账户

| 编号 | 任务 | 执行归档 | 状态 |
|---|---|---|---|
| 研究第八批 | 修正B研究差异、固定8配置、全现金核算与独立重建 | [第八批报告](technical-account-limited-comparison-2026-09-08.md) / [学习补充](../literature-learning/technical-comparison-lessons-2026-09-08.md) | 已归档；mixed；交易极少，未证明升级有效；OKR拟更新待确认。 |

### 9-08 第七批论文方法落实

| 编号 | 任务 | 执行归档 | 状态 |
|---|---|---|---|
| 研究第七批 | 论文原文方法、实际年月盈亏、B规则与价格转换前提核验 | [第七批报告](paper-methods-applied-checks-2026-09-08.md) / [学习补充](../literature-learning/paper-method-followup-2026-09-08.md) | 已归档；mixed；独立重算一致，完整技术账户仍有规则和数据定义前提。 |

### 9-08 文献对照

| 编号 | 任务 | 执行归档 | 状态 |
|---|---|---|---|
| 文献对照 | 系统与专业金融论文的关联、区别及可借鉴方法 | [对照报告](lei-academic-literature-ARCHIVE-2026-09-08.md) | 已归档；12篇论文及中文笔记已存 Zotero；非新回测 |
| 研究负责人任务审阅 | 逐环节效果、完整交易与论文方法的研究安排 | [审阅与补充建议](research-lead-task-review-2026-09-08.md) | 已审阅；研究待授权 |
| 文献学习库 | 18篇文献、20条学习内容与独立页面开发交接 | [交接稿](literature-learning-library-handoff-2026-09-08.md) | 内容已备；页面未开发 |

### 9-08 研究负责人首轮

| 编号 | 任务 | 执行归档 | 状态 |
|---|---|---|---|
| 研究首轮 | 九环节证据、近期论文、真实小范围复现与独立复核 | [首轮报告](research-first-round-ARCHIVE-2026-09-08.md) | 五项成果已交，待验收；部分旧证据需收窄 |
| E01 | 旧定投目标退出的成交时间与完整资金复验 | [冻结方案](research-first-experiment-protocol-2026-09-08.md) / [执行结果](ambush-complete-menu-review-2026-09-08.md) | 原146机会与64路径已复核，研究待验收 |

### 9-08 新版统一研究首批

| 编号 | 任务 | 执行归档 | 状态 |
|---|---|---|---|
| 新版研究 | 出场与止损 | [ambush-complete-menu-review-2026-09-08.md](ambush-complete-menu-review-2026-09-08.md) | 已交有限研究；mixed，后续范围见总览 |
| 新版研究 | 方法论与验证 | [dca-instrument-measurement-review-2026-09-08.md](dca-instrument-measurement-review-2026-09-08.md) | 已交有限研究；mixed，后续范围见总览 |
| 新版研究 | 宏观与情绪 | [sentiment-combination-feasibility-review-2026-09-08.md](sentiment-combination-feasibility-review-2026-09-08.md) | 已交有限研究；mixed，后续范围见总览 |
| 新版研究 | 方法论与验证 | [ai-defense-evidence-audit-2026-09-08.md](ai-defense-evidence-audit-2026-09-08.md) | 已交有限研究；mixed，后续范围见总览 |
| 新版研究 | 研究总纲 | [research-unified-progress-2026-09-08.md](research-unified-progress-2026-09-08.md) | 已交有限研究；mixed，后续范围见总览 |

### 9-08 05—08第二批推进

| 编号 | 任务 | 执行归档 | 状态 |
|---|---|---|---|
| 05—08第二批 | 出场与止损 | [ambush-pending-boundaries-2026-09-08.md](ambush-pending-boundaries-2026-09-08.md) | 补齐未成交及取消记录，8类检查通过、64账户原结果不变；没有新的策略收益。 |
| 05—08第二批 | 数据与质量 | [dca-split-data-audit-2026-09-08.md](dca-split-data-audit-2026-09-08.md) | 纳指基金约80%跳降与1拆5对应；近期价格有了明确来源，长历史三对照仍未运行。 |
| 05—08第二批 | 语义组合 | [sentiment-four-input-audit-2026-09-08.md](sentiment-four-input-audit-2026-09-08.md) | 半导体无完整可算日，有色96日无四条件同时触发；资料不足以验证新增机会收益。 |
| 05—08第二批 | 方法论与验证 | [ai-future-validation-protocol-2026-09-08.md](ai-future-validation-protocol-2026-09-08.md) | 解释与退出两份未来方案及记录模板已备；偏好、最小改善幅度和观察量尚待冻结。 |
| 05—08第二批 | 研究总纲 | [research-05-08-progress-2026-09-08.md](research-05-08-progress-2026-09-08.md) | 05记录补齐、06拆分核查、07完整条件资料及08未来方案已交；后两项仍有未完成标准。 |

### 9-08 05—08第三批推进

| 编号 | 任务 | 执行归档 | 状态 |
|---|---|---|---|
| 第三批研究 | 数据与质量 | [dca-long-data-cash-boundary-2026-09-08.md](dca-long-data-cash-boundary-2026-09-08.md) | 四基金长历史价格已取回；单次分红对账确认前复权比值不同于保留现金的持有财富，长历史三对照仍未运行。 |
| 第三批研究 | 语义组合 | [icepoint-legacy-replay-2026-09-08.md](icepoint-legacy-replay-2026-09-08.md) | 旧四区间252条价格观察全部复现，但实际只测两条件，不能证明完整冰点四条件有效。 |
| 第三批研究 | 方法论与验证 | [ai-explanation-exercise-pack-2026-09-08.md](ai-explanation-exercise-pack-2026-09-08.md) | 8份解释练习、答案依据和来源已备，尚未运行模型或评价用户理解。 |
| 第三批研究 | 研究总纲 | [research-third-progress-2026-09-08.md](research-third-progress-2026-09-08.md) | 长价格取得、分红计量、旧252条观察复现及8份解释练习已交；完整组合收益与AI效果尚未验证。 |

### 9-08 05—08第四批推进

| 批次 | 类别 | 报告 | 状态 |
|---|---|---|---|
| 第四批研究 | 组合与仓位 | [实际基金现金三对照](dca-actual-fund-cash-comparison-2026-09-08.md) | 三年同资金对照已交：季度调整多赚但没有减少最大跌幅；长期仍待资料 |
| 第四批研究 | 研究总纲 | [第四批全貌](research-fourth-progress-2026-09-08.md) | 12固定情景与基础账户独立核查完成；更早历史与其他未决事项保持记录 |

### 9-08 第五批与06研究交付

| 批次 | 类别 | 报告 | 状态 |
|---|---|---|---|
| 第五批 | 组合与仓位 | [近13年实际资金比较](dca-long-cash-study-closeout-2026-09-08.md) | 21次固定比较完成；长期季度方案有条件支持，2020—2022仍亏损，提交待验收 |
| 交付总览 | 研究总纲 | [05—08总交接](research-05-08-delivery-handoff-2026-09-08.md) | 已交证据、未定偏好、缺失资料与未来观察分开；附三个按文献索引的本地学习例子 |

### 9-01 轮（A–M，任务书合订本：`prompts-2026-09-01.md`）

| 编号 | 任务 | 执行归档 | 状态 |
|---|---|---|---|
| A | 美债10Y/收益率曲线做美股触发 | us-treasury-ARCHIVE + us-treasury-CROSSCHECK | ✅ |
| B | VIX期限结构/PUT-CALL情绪触发 | vix-sentiment-ARCHIVE | ✅ |
| C | A股宏观变量触发层 | ashare-macro-ARCHIVE | ✅ |
| D | 新信号×现有两腿正交检查 | orthogonality-check | ✅ |
| E | MACD强度信号分层验证 | macd-strength-layering-ARCHIVE | ✅ |
| F | 宽度/利率分位仓位映射复活 | position-mapping-revival-ARCHIVE | ✅ |
| G | 纯结构止损复活（补止盈） | exit-structural-stop-revival-ARCHIVE | ✅ |
| H | vt目标波动缩放网格 | vt-grid-ARCHIVE | ✅ |
| I | 止损方式跨模块统一矩阵 | stop-loss-matrix-ARCHIVE | ✅ |
| J | a6_1三部件拆解（三件套） | exit-three-piece-ARCHIVE | ✅ 证伪（0/27 全灭） |
| K | vt接入信号驱动单标的仓位层 | vt-signal-driven-sizing-ARCHIVE | ✅ |
| L | 板块级RS加权 | sector-rs-ARCHIVE | ✅ |
| M | 时间止损接受右尾（反向设计） | time-stop-tail-aware-ARCHIVE | ✅ |

### 9-02 单发（N–X，任务书各自单独成文件）

| 编号 | 任务书 | 执行归档 | 状态 |
|---|---|---|---|
| N | prompt-N-module-conflict-resonance | module-conflict-resonance-ARCHIVE | ✅ |
| O | prompt-O-pool-recovery | pool-recovery-audit | ✅ |
| P | prompt-PQ（P：标普替代纳指） | spx-vs-ndx-ARCHIVE-2026-09-03 | ✅ 已执行 09-03（标普版年化-1.9pp、回撤略浅） |
| Q | prompt-PQ（Q：纯宽基vs行业篮子） | 无独立归档 | 〰️ 被 X 阶段三间接回答 |
| R | prompt-R-full-pool-revalidation | full-pool-revalidation-ARCHIVE | ✅ |
| S | prompt-S-b-module-reverse-vt | b-module-reverse-vt-ARCHIVE | ✅ |
| T | prompt-T-valuation-overlay | valuation-overlay-ARCHIVE | ✅ A股主判定证伪→催生U |
| U | prompt-U-us-erp-overlay | us-erp-overlay-ARCHIVE | ✅ |
| V | prompt-V-current-holdings-check | 无独立归档 | 〰️ 内容被 W 吸收（W 第三步） |
| W | prompt-W-holdings-correlation | holdings-correlation-study | ✅ |
| X | prompt-X-broad-index-comprehensive | coverage-sync + broad-index 三份 | ✅ 四份产出齐全 |

### 9-03 本轮拆分（任务书已入库；已全部执行，见下方 9-03~04 会话四批节）

| 编号 | 任务书 | 内容 | 梯队 |
|---|---|---|---|
| Y | prompt-Y-pollution-recheck-2026-09-03 | 债务一+三复核：模块B仍成立；510500证据不足 | 一 · ✅已执行 |
| AE | prompt-AE-staged-entry-precheck-2026-09-03 | 语义九前置：分批执行叠加现有信号 | 一 |
| Z | prompt-Z-antifragile-precheck-2026-09-03 | 语义三前置：反脆弱补偿效应事件研究 | 一 |
| AA | prompt-AA-master-slave-precheck-2026-09-03 | 语义一前置：主从关系依赖性验证 | 二 |
| AB | prompt-AB-multi-confirm-frequency-2026-09-03 | 语义四前置：多重确认共触发频率 | 二 |
| AC | prompt-AC-timescale-layering-precheck-2026-09-03 | 语义五前置：长短期信号分层 | 二 |
| AD | prompt-AD-overnight-us-cn-precheck-2026-09-03 | 语义七前置：美股隔夜×次日A股关联 | 二 |

### 9-04 轮（AU–AW，会话内自研自跑，预注册+双跑哈希同前例）

| 编号 | 任务 | 执行归档 | 状态 |
|---|---|---|---|
| AU | 二元+滞回 vs 现役三档（决策级，AJ/AP 搁置的决策） | binary-hysteresis-vs-t3-decision-2026-09-04 | ✅ 判「换」（宽基域，待用户拍板） |
| AV | 极端底部价格阶梯执行（R1 主臂+R2 追涨兜底） | price-ladder-execution-2026-09-04 | ✅ 交换结构（+6.1pp中位 vs V型左尾） |
| AW | 宽度择时个股边界（12美股大盘股+SPY/QQQ） | us-stocks-timing-boundary-2026-09-04 | ✅ 判「无优势」（有效域=跟随宽度的宽基） |
| AX | 换档决策走样本前向验证 + 相对痛苦度量 | switch-walkforward-and-pain-2026-09-04 | ✅ 判「保持」（6/11 压线；重选协议是 edge 一半） |
| AY | A股个股面板×四引擎 + 跟随度分层（81只） | astock-panel-timing-2026-09-04 | ✅ 混合；机制线支持边界判据（跟随度连续谱） |

不发（等条件）：语义二/六（总纲判高风险暂缓）、语义八（等 Z 结果）、
债务二（等用户拍板立项）、债务五 P 部分（等用户表态是否有兴趣）。

### 9-05 单发（用户直发任务）

| 编号 | 任务 | 执行归档 | 状态 |
|---|---|---|---|
| BD | 因子观测台价值验证（第三次独立重建信号×因子对账，8561 条） | factor-panel-value-2026-09-05 | 〰️ 路由提示复现增强(t=4.4)；「高波打折/彩票股」警示对已确认信号反向 |
| BE | A股跌破200日线分步清单自测（文主任增量 #4） | ma200-breakdown-checklist-astock-2026-09-05 | 〰️ 多数虚惊成立(60%/5天收回)；急速vs缓慢形态分组在A股反向、不落地 |
| BF | 横截面动量标的池研究（文主任增量 #5，研究先行） | cross-sectional-momentum-pool-2026-09-05 | 〰️ 池内胜率略高但分年不稳定（牛市年占优/弱势年反向）、盈亏比无差——不落地留观察 |
| BG | 因子实验台扩展：组合回测+L1-L6+估值分位（文主任增量 #6） | factor-lab-extension-2026-09-05 | 👁 低波前30%年化20%超基准5.6pp/动量反向；L1-L6高档后波动单调更大；全部只观察 |

### 9-06 单发（用户直发任务）

| 编号 | 任务 | 执行归档 | 状态 |
|---|---|---|---|
| BH | 定投方式对比：频率×要不要浮动×按什么浮动（13 标的九臂） | dca-methods-comparison-2026-09-06 | 〰️ 频率无关选省事的；行业基金宽度浮动 10/10 胜、宽基 0/10 败；美股平投碾压浮动（热暂停版腰斩） |
| BI | 定投×情绪信号择时（冰点/散户热宽度成分，八臂） | dca-sentiment-timing-2026-09-06 | 〰️ 纯冰点加倍=空心的（26格与平投一分不差，加码没弹药）；配热减半后行业微弱正(+0.3~0.9%)仍远弱于宽度版；宽基/美股平投三次复证 |
| BK | 定投×时间跨度稳健性（31年/22年/四个十年，12指数） | dca-longwindow-robustness-2026-09-06 | ✅ 三条结论全维持：宽基平投(16窗宽度版仅赢2)、美股平投16/16、频率无关20/20；1995-2005十年定投A股是亏的；科创50五年是物理上限 |
| BL | 行业指数×定投择时长窗口（10指数+5ETF对照） | dca-industry-longwindow-2026-09-07 | ❌ 推翻第一轮「行业宽度浮动有效」：只剩军工/证券/白酒赢(6/20)，ETF短样本甜头来自2021-2024熊市段；四轮终局=定投择时整体证伪，平投最优 |
| BM | 系统买点后的执行方式：一次性 vs 分批 vs 定投窗口（A 4368笔+B 552笔） | dca-entry-execution-2026-09-07 | ❌ 8/8臂负增量、8/8更贵：买点后行情平均上行晚买更贵+批次被出场作废三至六成；亏钱单少亏1~2pp不敌赢钱单少赚2~9pp；语义九第三次判负，一次性买入最优 |
| BN | 估值分段定投×情绪定投（乐咕PE/PB 21年+NAAIM/AAII/VIX/融资/换手） | dca-sentiment-valuation-2026-09-07 | 〰️ 估值分段方向8/8正但幅度+0~0.9%趋零（不亏不值当）；情绪五族20/20全输（融资-7~-10%/NAAIM-7~-8%/VIX-5~-6%/AAII-2%）且分半窗全负——定投系列收官：平投+一次性执行即最优 |
| BO | 定投标的横评×篮子再平衡（28标的两窗+两篮三臂） | dca-basket-targets-2026-09-07 | ✅ 标的：中证1000/科创50/黄金/纳指两窗靠前、沪深300中游、2021顶起投的白酒消费医药全亏；篮子定投月度/年度再平衡各4/4有增量（九篮子+5.9%回撤浅3.1pp、费仅1~26bp）——低买高卖的正确形态是成分间再平衡 |
| BP | 组合矩阵×定投总开关（六组合三档再平衡+七标的两开关） | dca-combos-exit-2026-09-07 | 〰️ 跨资产四件套(300+创业板+黄金+纳指)月度再平衡年化15.8%回撤-9.8%性价比全场最佳，再平衡增量随腿间差异递增；定投总开关双双判负(年线0/14宽度2/14连A股也负)——现金流本身就是风控，定投侧三类择时形态全部封箱 |
| BQ | 科创腿×再平衡方式×纳指核心长持（四组合两窗+五方式+三方案） | dca-kc-rebal-core-2026-09-07 | 〰️ 换科创50年化+1.3pp回撤+3pp(换比加好)；季度再平衡4/4胜月度省2/3交易、阈值版判负年度不稳；纳指长持多赚0.5~2.1pp但回撤-12.6%→-22%(配置旋钮非免费午餐) |
| BR | 埋伏进场滚动检验（316段12个月campaign×四臂） | dca-ambush-entry-2026-09-07 | 👁 一次性赢中位左尾深、平投左尾保护大成本低1.1pp、平投+阶梯(-8/16/24%加档)成本再低1pp几乎免费、纯阶梯踏空别用；贴年线深回调仅5样本结局分裂——底部感觉无统计背书 |
| BS | 买点时机状态表（8指数31年6400周观测×5状态维度×4期限） | dca-entry-timing-table-2026-09-07 | 👁 距年线≤-20%深超跌6个月胜率95%中位+12.8%左尾消失=最强时机行；底部区域12个月+4.6%/61%当前创业板在区；热档中位+9.6%但P10-27.9%(等惨=尾部管理非收益最大化)；浅超跌-10~0%是最差磨底坑 |
| BT | 定投触发门控（四触发×三形态×8指数16格） | dca-trigger-gating-2026-09-07 | ❌ 等触发才投全灭：深超跌门控2/16(连95%胜率的行也输)、底部区域10/16混合、惨档偏零——常开平投本来就在好周自动买入，门控只新增现金闲置；触发状态管预期不停钱，埋伏=额外闲钱阶梯加码 |
| BU | 条件定投完整交易闭环（四入场×五出场×600余笔平仓） | dca-complete-trades-2026-09-07 | ✅ 出场比入场重要：+30%目标止盈让任意入场中位+25~27%；深乖离+30%出场次优(底部入场+22.6%/69%)；宽度热出场砍牛腿最差；时间离场=随机入场中位-5.2%；埋伏模板=底部/惨档触发→12月定投→止盈或深乖离出场→24月兜底 |
| BV | 标的适配止盈止损（六出场臂含波动/分位适配与止损侧） | dca-adaptive-exits-2026-09-08 | 〰️ 波动适配止盈8/32不敌统一30%(A股波动挤在20~30%带)；止损首测=买尾部卖中位(bottom入场-20%止损中位27%→3%，deep20入场无损)；菜单：要中位不带止损/要稳带30%-20%/折中波动止损 |
| BW | 分标的出场规则（跨资产11标的×止盈类vs不止盈类） | dca-per-target-exits-2026-09-08 | 〰️ 分裂轴=蓝筹vs成长：沪深300/深证/红利该止盈(30%档差+12~21pp)，创业板/1000/科创深底入场别设低止盈(不止盈+63%vs止盈+55%，用50%档或等过热)；标普框架内止盈占优纳指平(24月兜底截断，美股不止盈以九轮40年口径为准)；分腿出场菜单落地 |
| BX | 分腿止盈组合级联合模拟（两篮×四政策，收官） | dca-joint-policy-2026-09-08 | ❌ 三种止盈政策0/12全判负：季度再平衡本来就是更聪明的止盈器(只卖偏离永不停摆)；止盈清仓停摆期错过后续(科创腿32%现金滞留)、部分止盈26次砍领涨腿回撤反深；唯一例外=年线回场0.4%代价买5pp回撤改善——定投终局形态：平投+跨资产篮子+季度再平衡 |
| BY | 状态表事件级复验（外部评审R2：事件归并+抽签重抽） | dca-deep20-episodes-2026-09-08 | 〰️ 深超跌行扛住最严口径(11次独立深跌10次6月为正、重抽胜率下限89%、剔90年代不变)账本改报区间；底部区域行降级(16事件仅62.5%的12月为正，+4.6%/61%被重叠样本抬高)——底部区域触发仍可用但预期按弱参照讲 |
| BZ | 终局形态整装验证（外部评审R1：13年长窗+96起点网格+参数邻域） | dca-final-form-assembly-2026-09-08 | ✅ 篮子对纯沪深300优势96/96起点为正(中位+10.8pp)、再平衡增量96/96为正但仅+0.62pp；13年整装12.14%/-23.8%——15.88%/-9.7%被5.8年窗抬高(终点±3月晃4pp)，账本主数字改报中位13.86%[12.23%,15.70%]；季度≈月度("完胜"改判等价+省费)；往300倾斜差3pp=权重敏感 |
| — | 核心八 ETF 两年闭环 | etf-eight-twoyear-2026-09-06 | 〰️ 钱全靠趋势回调赚，破底翻在 ETF 上净亏（补登，见 registry） |
| — | AI 参与决策三档实验 | ai-three-tier-decision-2026-09-06 | ❌ 否决权完败，AI 留信息层（补登，见 registry） |

### 9-03~04 会话四批（Y–BC，交接总表：`session-handoff-manifest-2026-09-04.md`）

> 调度会话四批 25 项，全部预注册+双跑哈希。**注意：本批代号与上方 9-04
> AU–AY 节存在字母复用（两组会话各编各的），引用一律以文件名为准。**
> 机器可读判定/分类见 `registry.json`，判定状态已登记。

| 代号 | 报告 | 判定（大白话） |
|---|---|---|
| Y | pollution-recheck-moduleB-csi500-2026-09-03 | ✅ 模块B仍成立；中证500 证据不足不入池 |
| Z | antifragile-event-study-2026-09-03 | ❌ 反脆弱补偿不成立 |
| AA | master-slave-precheck-2026-09-03 | ❌ 主从依赖不成立（两信号 100% 同步） |
| AB | multi-confirm-frequency-2026-09-03 | 〰️ 仅 P1 对过线但独立性存疑 |
| AC | timescale-layering-precheck-2026-09-03 | ❌ 长短期分层不值得设计 |
| AD | overnight-us-cn-precheck-2026-09-03 | 〰️ 关联存在但主通道是开盘跳空 |
| AE | staged-entry-precheck-2026-09-03 | ❌ 分批买入证据不足 |
| AF | p1-increment-test-2026-09-03 | ❌ 语义四实质关闭 |
| AG | overnight-gate2-increment-2026-09-03 | ❌ 语义七关闭 |
| AH | csi500-fee-sensitivity-2026-09-03 | 〰️ 费率敏感带内打平，不入池不变 |
| AI | module-b-robustness-2026-09-03 | ✅ 稳健但压线（前三笔占 69%） |
| AJ | binary-vs-tiered-vs-dca-2026-09-03 | 〰️ A股二元赢；美股 40 年定投碾压 |
| AK | extreme-bottom-event-study-2026-09-03 | ✅ A股底部是过程非事件 |
| AL | tsy10y-high-orthogonality-2026-09-03 | ❌ 不独立（重叠 94%），2027-03 复查 |
| AM | extreme-bottom-staged-entry-validation-2026-09-03 | ❌ 语义九买入侧关闭 |
| AN | top-structure-event-study-2026-09-03 | 〰️ 卖出警报偏磨顶、几乎非顶 |
| AO | module-b-regime-diagnosis-2026-09-03 | 👁 栖息地仅登记（弱证据） |
| AP | binary-hysteresis-sensitivity-2026-09-03 | ✅ 滞回带修复阈值脆弱性 |
| AQ | module-b-stock-pool-boundary-2026-09-03 | ✅ 个股复现同型（15 只 +0.726） |
| AR | system-fragility-xray-2026-09-03 | ✅ 系统体检：阴跌是唯一死穴 |
| AV | module-b-filter-h1h2-validation-2026-09-04 | ❌ H1/H2 都不启用 |
| AW | hysteresis-binary-promotion-2026-09-04 | ✅ 滞回二元候选成立，等拍板 |
| AX | staged-exit-validation-2026-09-04 | ❌ 语义九卖出侧关闭 |
| AY | breadth-input-comparison-2026-09-04 | ❌ 查重关闭（playbook 已测） |
| BC | module-b-us-etf-boundary-2026-09-04 | ❌ 模块B不出海（剔 1995 后≈零） |

### 9-08 第六批退出基准与ATR

| 编号 | 任务 | 执行归档 | 状态 |
|---|---|---|---|
| 第六批基准 | 2309条旧记录、价格与时间退出重复计数 | [完整核验](exit-baseline-full-audit-2026-09-08.md) | 研究已交；真实成本仍缺，OKR待用户确认 |
| 第六批ATR | 0.5ATR固定机会、相同资金与计划风险 | [有限比较](atr-buffer-opportunity-study-2026-09-08.md) | 55416行及独立复核已交；mixed，未接生产 |
| 第六批交接 | 已完成证据、学习实例与剩余依赖 | [统一交接](research-sixth-handoff-2026-09-08.md) | 整体仍有未完成项；OKR待确认 |


## 2. 归档按主题（每份文件只归一组，标题即内容摘要）

### 元与跨组

- `../system-architecture-and-decisions-2026-09-04.md` — 系统四轨架构原型 +
  决策台账 + 研究队列（docs 根，2026-09-04 起的决策状态权威文件）
- `CROSS-GROUP-SYNTHESIS-2026-09-01.md` — 跨组统一视图（五路归档汇总）
- `coverage-sync-2026-09-02.md` — 跨机器任务覆盖对账 + stash 26份报告恢复
- `FINAL-VERDICT-walkforward-2026-08-27.md` — walk-forward 时序终审（第十三轮）
- `todo-new-composition-semantics-2026-09-02.md` — 新组合语义待办（已并入总纲）

### 宽度择时主线（大盘冷热信号）

- `kuandu-quanzhan-ARCHIVE-2026-09-01.md` — 31轮总决算（冠军三档、两只版、8指数篮子）
- `breadth-overlay-report-2026-08-27.md` — 宽度极值叠加（用户口径两档制）
- `stage-b200-report-2026-08-27.md` — stage路由 + B200 牛熊口径纠正
- `midzone-breadth-timing-2026-09-07.md` — 中间地带宽度择时证伪（16组缓冲带21年全跑输持有；极端位仅配价格确认有效）

### 入场模块与标的池（8-25～8-28 早期探索 + 后续板块/判别器）

- `etf-expansion-log/report-2026-08-25.md` ×2 — 扩池实验（A稳健档被推翻）
- `experiment-log / final-report-2026-08-25.md` — 8-25 四轮总日志与终报
- `filters-round4-log/report-2026-08-25.md` ×2 — 第四轮过滤器（量能/筹码/状态机）
- `shrink-filter-report-2026-08-25.md` — 缩量回调过滤器
- `bcd-retrial-report-2026-08-26.md` — B/C/D 公平重测
- `b-adaptation-report-2026-08-26.md` — B 模块全谱参数×标的类型
- `bform-*-report-2026-08-28.md` ×3 — B 形态探索/动态/终审
- `portfolio-params-pool-report-2026-08-28.md` — B 形态参数真高原、9只最优池
- `regime-gate-report-2026-08-27.md` — 宽基"仅横"门禁（干净发现）
- `rs26-detector / siphon-detector-report-2026-08-27.md` — RS虹吸灯方法论源头
- `sector-layer-report-2026-08-27.md` — 板块第四层筛选器
- `sector-rs-ARCHIVE-2026-09-02.md` — 板块级RS加权（任务L）
- `module-conflict-resonance-ARCHIVE-2026-09-02.md` — 四模块同标的同日互斥（任务N）

### 出场与止损

- `exit-matrix-report-2026-08-31.md` — A/B'/C × 四种出场矩阵
- `exit-structural-stop-revival-ARCHIVE-2026-09-01.md` — a6_3 结构止损复活（任务G）
- `exit-three-piece-ARCHIVE-2026-09-02.md` — a6_5 三件套证伪（任务J）
- `stop-loss-matrix-ARCHIVE-2026-09-01.md` — 止损跨模块统一矩阵（任务I）
- `time-stop-tail-aware-ARCHIVE-2026-09-02.md` — 时间止损接受右尾（任务M）
- `knife-timestop-report-2026-08-27.md` — 接刀格时间止损判负

### 仓位与波动机制

- `breadth-position-report-2026-08-27.md` — 宽度→仓位曲线（定投基准对比出处）
- `position-mapping-revival-ARCHIVE-2026-09-01.md` — 仓位映射复活判负（任务F）
- `vt-grid-ARCHIVE-2026-09-01.md` — vt 网格（任务H）
- `vt-signal-driven-sizing-ARCHIVE-2026-09-02.md` — vt 信号驱动单标的仓位（任务K）
- `b-module-reverse-vt-ARCHIVE-2026-09-02.md` — B 高波反向 vt（任务S）
- `huanjing-ARCHIVE-2026-09-01.md` — 环境组宽度×RV 总仓位系数

### 组合与资金层

- `portfolio-report / portfolio-split-report-2026-08-27~28.md` — 资金层与分账制
- `bform-global-report + m5-final-review-report-2026-08-28.md` — M5 跨市场宽指组合全周期
- `heiti-ARCHIVE-2026-08-31.md` — 合体组（B9+LEI 分账制 224.6万/-9.7%）
- `combined-certification-report-2026-08-31.md` — 合体认证 6/6
- `cash-leg / gold-expand-report-2026-08-31.md` — 现金腿与黄金腿增强
- `lifecycle-report / full-stack-sim-report-2026-08-27.md` — 生命周期与三层串联
- `lei-ARCHIVE + meta-scan + signal-density` — LEI 个股腿三份
- `module-e-report-2026-08-27.md` — 模块E 情绪极值择时（手册口径）

### 宏观/情绪/估值确认层（触发路线，基本全线判负）

- `us-treasury-ARCHIVE + us-treasury-CROSSCHECK-2026-09-01.md` — 美债（任务A）
- `vix-sentiment-ARCHIVE-2026-09-01.md` — VIX/PUT-CALL（任务B）
- `ashare-macro-ARCHIVE-2026-09-01.md` — A股宏观（任务C）
- `sentiment-gate-report-2026-08-28.md` — 两融分位闸 + 北向
- `trd-gate-report-2026-08-31.md` — 股债性价比门首测即证伪
- `valuation-overlay-ARCHIVE-2026-09-02.md` — 估值确认层（任务T，A股证伪）
- `us-erp-overlay-ARCHIVE-2026-09-02.md` — 美股ERP（任务U）
- `orthogonality-check-2026-09-01.md` — 新信号×两腿正交（任务D）
- `macd-strength-layering-ARCHIVE-2026-09-01.md` — MACD强度分层（任务E）
- `retail-mania-threshold-2026-09-04.md` — 板块散户热度阈值（进行中：口径/页面已上线，等数据回填出回测）

### 宽基/全池/持仓/数据质量专项（9-02）

- `broad-index-coverage-summary / gap-fill / portfolio-and-signals-2026-09-02.md` — 任务X 阶段一/二/三+四
- `full-pool-revalidation-ARCHIVE-2026-09-02.md` — 175标的全池复验（任务R复验M+K）
- `data-quality-jump-audit-2026-09-02.md` — 13处复权断裂审计（修平方法出处）
- `holdings-correlation-study-2026-09-02.md` — 用户持仓×已验证标的相关性（任务W）
- `pool-recovery-audit-2026-09-02.md` — 深池环境盘点（任务O）
- `pollution-recheck-moduleB-csi500-2026-09-03.md` — 债务一+三复核（任务Y）
- `spx-vs-ndx-ARCHIVE-2026-09-03.md` — 标普替代纳指全量对比（任务P）

## 3. raw/ 数据目录对照

按目录名与归档名对应（个别按任务编号/提交信息推断并标注）；空白 = 未对账，
使用前以归档报告内的 raw 引用为准。快照类目录（backtest-runs / pool-snapshot）
是环境保全，不隶属单一实验。

| raw 目录 | 对应归档 |
|---|---|
| ashare-macro / vix-sentiment / us-treasury-signal(+crosscheck) / A_round2 | 任务A/B/C 归档（A_round2 为任务A二轮，推断） |
| breadth_overlay / stage_b200 | breadth-overlay / stage-b200 |
| breadth_position | breadth-position |
| etf_expansion | etf-expansion 系列 |
| b_adaptation / B_breakout_matrix（推断） / bcd_retrial | b-adaptation / bcd-retrial |
| bform 系列（无独立 raw，参数在归档内） | — |
| exit_matrix / exit_revival_a64 / exit_three_piece | exit-matrix / exit-structural-stop-revival / exit-three-piece |
| stop_loss_matrix / knife_timestop / time_stop_tail_aware(+full_pool) | stop-loss-matrix / knife-timestop / time-stop-tail-aware（full_pool=任务R复验） |
| position-mapping-revival / vt-grid / vt_signal_sizing(+full_pool) / b_reverse_vt / huanjing | 仓位机制组各归档（vt full_pool=任务R复验） |
| portfolio / portfolio_split / cash_leg / gold_expand / combined_cert / heiti / lei / meta_scan / signal_density / lifecycle_combo / full_stack / module_e / ultimate（heiti终极组合，推断） | 组合与资金层组各归档 |
| regime_gate / rs26_detector / siphon_detector / sector_layer / sector_rs / module-conflict-resonance | 入场模块组各归档 |
| sentiment / trd_gate / valuation_overlay / us_erp_overlay / orthogonality-check / macd-strength-layering | 触发/确认层组各归档 |
| gap_fill / holdings_correlation | broad-index-gap-fill / holdings-correlation |
| ashare_axes / cross_check / etf_breadth / stock_breadth | —（未对账） |
| backtest-runs-snapshot-2026-08-31 / pool-snapshot-2026-08-25 | 环境保全快照（非单一实验） |
| pollution_recheck / spx_vs_ndx | pollution-recheck / spx-vs-ndx（任务Y/P，09-03） |
| agent_AU-binary-hyst-vs-t3 / agent_AV-price-ladder / agent_AW-us-stocks-timing | binary-hysteresis-vs-t3-decision / price-ladder-execution / us-stocks-timing-boundary（09-04） |
| agent_AX-walkforward-switch / agent_AY-astock-panel | switch-walkforward-and-pain / astock-panel-timing（09-04 晚） |

## 4. 悬案与未执行清单

- ~~P（标普替代纳指）~~ **已执行（09-03，spx-vs-ndx-ARCHIVE）** — 两只版换腿：
  年化 15.9%→14.0%（-1.9pp）、回撤 -25.6%→-24.0%；防守版纳指档保险性价比更高
  （13.8 vs 8.7）。附勘误：原防守版归档"纳指5档"标签与代码不符（实为3档）。
- **数据断裂正式修复未立项** — `data-quality-jump-audit` 第7节，属生产数据
  操作，等用户拍板（总纲债务二）。新增两条待立项线索：①HEAD 引擎代码断链
  （engine.py 引用已丢失模块，复现靠 git 悬空对象重建，gc 后会失效）；
  ②512690 深池 2020-02-03 单日 +25.1% 超物理限制，不在审计 13 清单内。
- **债务一/三已复核（09-03，pollution-recheck 归档）** — 模块B宽基正收益仍
  成立（三跑分解），且审计 §5"b-adaptation 7宽基受污染"系跨数据源误推
  （该实验用深池数据、深池无跳变；勘误登记于此，不改原归档）；中证500 重审
  落"证据不足"中间态（翻案三条件仅过一条，判负触发条件也未命中）。
- **总纲债务四（J–N/P–S/U–V 去向不明）已基本自解** — 23ca826 补齐了任务书
  原文和 J/K/L/M/T/U 归档，实际残留只有上面两条。
- timing-sweep 时代引用的 `vt-signal / time-stop-tail` 两份后续归档，即
  vt-signal-driven-sizing 与 time-stop-tail-aware（coverage-sync 疑点2 的答案）。

## 5. 相邻目录

- `docs/timing-sweep/` — 8-27 时代 31 轮择时实验档案（`execution_playbook_20260827.md`
  被大量引用，其余为各轮 txt/csv）
- `docs/reports/` — 说明：回测 HTML 报告已迁至 `web/public/reports/`
- `docs/` 根的 `handoff-* / plan-*` 为应用线（data-sync）历史任务书与方案，
  与本目录研究线互不隶属
