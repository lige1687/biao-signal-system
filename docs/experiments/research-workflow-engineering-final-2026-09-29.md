# LEI 新研究入口与防重复错误：最终工程验收（2026-09-29）

## 一句话结论（大白话）

研究检查已接进现有 Factor Lab 的新执行入口和报告登记入口。两个人工数据案例都从检查、演练、冻结走到报告登记：候选没有新增帮助，或比简单方法更差，也能诚实结束；错凭据则在计算前被挡住。218项相关测试通过。这证明本轮流程行为成立，不证明任何真实市场因子有效，也没有修改技术交易规则。

这次服务于 LEI 的研究层：把道路、回调触发及风险判断变成可重复验证的问题；不改变 Python 生产判定、前端或账户动作。依据为用户本轮执行指令和桌面的两份技术原文。原文与旧A01、A02及两轮修正的274项封存指纹均核对一致。

## 本轮最终版本与保留历史

[前置工程快照](research-workflow-engineering-2026-09-29.md)和最初两个演示原样保留。收尾时发现，计算前被拒绝的命令虽有失败与实际命令耗时证据，却未计入研究家族预算。最终版本将拒绝耗时入账，预检和演练的耗时也计入；机械失败不增加科学假设次数。新增坏凭据→有耗时但回调0→原预算耗尽即暂停的配对测试。

因此在同两个研究家族、原30秒额度下重验两种人工案例，各家族只有1个科学配置、2次正式机械执行、2次拒绝尝试。最初遗漏的拒绝成本按保存的实际命令回执补入账本，没有删除、重置或伪造时间。最终两案例约消耗0.758/0.779秒受控执行预算，评分与前置版本完全相同。最终218项测试通过；这次修订没有改变技术含义、模型或市场结果。

旧演示绑定旧代码，不能拿它们的凭据执行当前版本；最终可用演示在`demos-final/`。这正是数据/代码相关依赖变化必须重验的行为，而不是追求更漂亮的分数。原7200秒总工程预算和所有旧证据继续保留。

## 已接入口、还能说到哪里

实际入口为 `scripts/run_factor_lab.py --workflow-draft`、`--workflow-contract`，新分支的 `--register-report` 也调用发布验收。不是只有说明文档或独立检查函数。

机器能检查明确字段、实际文件、日期、标签、样本名单、基准、比重、单位与产物一致性。对象是否对应用户用途、代理是否忠实于技术原文、方法是否合理、实际关注幅度和结论能说多大，仍由主控写明理由；不把填了理由当成科学判断已证明。

当前内置两种有限评价方法及两个演示特征。SMA相对距离不等于注册的A01双均线带；按周抽取日线观察也不等于周线均线。真实A01等因子须接准确适配器，才能复用公共流程。真实可操作开盘和账户政策尚未支持；给定行动清单可重算经济价格，但尚不能证明行动历史完整或历史报价何时到达。旧独立runner没有全面迁移。

## 两种实际端到端案例

以下全为人工生成的数据：各2个对象、105个日期；用于训练的时期在前，评价的41个后续日期在后，共82条配对预测。没有真实行情取数或市场模型重新拟合。简单参照B0只用训练时期已成熟结果；B1使用已有信息；B2加入候选。二元目标另列固定50%的B50。

平方错误（MSE）表示预测与实际变化相差多少，单位是百分点的平方；二元事件的平方评分（Brier）表示概率预测离0/1结果多远。两者都是越小越好，不是账户收益。

| 人工案例 | B0 | B1 | B2 | B50 | 相对B1错误减少 | 数量与范围 | 实际结案 |
|---|---:|---:|---:|---:|---:|---|---|
| 连续变化，候选没有变化 | 13.584611 | 6.429984 | 6.429984 | 不适用 | 0.000000 百分点² | 82条、41日期、2对象 | completed；候选新增帮助未获支持 |
| 未来下跌事件，关系在评价期反转 | 0.250000 | 0.322493 | 0.341463 | **0.250000** | −0.018970 平方评分 | 82条、41日期、2对象 | completed；效果更差，保留警告 |

| 新增信息对照 | 原错误→加入后 | 错误减少及允许的改善/恶化范围 | 解释 |
|---|---|---|---|
| 连续案例：B2相对B1 | 6.429984→6.429984 | 0；−3.11×10⁻¹⁷ 至 2.33×10⁻¹⁶ 百分点² | 浮点计算量级，候选没有新增帮助 |
| 连续案例：B2相对B0 | 13.584611→6.429984 | 7.154627；6.673693 至 8.155721 百分点² | 已有信息比简单参照好，不是候选的功劳 |
| 事件案例：B2相对B1 | 0.322493→0.341463 | −0.018970；−0.083844 至 0.031060 平方评分 | 包含改善和恶化，不能说新增帮助稳定 |
| 事件案例：B2相对B0/B50 | 0.250000→0.341463 | −0.091463；−0.157047 至 −0.042974 平方评分 | 完整方法较差，也允许负结果完成 |

这些范围来自事先固定的连续日期段重复抽取，同日对象一起保留，使用32次人工工程演示抽取；不是市场规律的可靠性证明。两个案例都只覆盖人工单年。金额收益、费用、可执行买卖、完整账户回撤及真实未见资料验证：**未研究，不适用本轮工程验收**。

每种案例另用改了比重却沿用旧冻结凭据的错误合同进入同一CLI：实际退出码3，`failure.json`记录计算回调未被调用。正确案例实际退出码0，生成报告并登记现有实验库。

完整命令、结果与回执见 [actual-cli-summary.json](raw/research-workflow-engineering-2026-09-29/demos-final/actual-cli-summary.json)。两份报告：[连续案例](research-workflow-continuous-final-demo-2026-09-29.md)、[事件风险案例](research-workflow-event-risk-final-demo-2026-09-29.md)。

## 实际调用链与六阶段

| 阶段 | 实际调用 | 强制行为 / 人类判断 |
|---|---|---|
| 1. 问题、用途和边界 | 原`validate_question`加`validate_workflow_contract`；相关定义解析 | 必需对象、目标、方法、时点、比重、期限、预算必须明确；对象适配、代理忠实与方法取舍由主控判断 |
| 2. 输入及计算语义 | `actual_bindings`、原`inspect_input`、`qualify_panel`、`inspect_workflow_input`、原`PreflightRegistry` | 读实际快照、日历与行动源；保留缺口原因及覆盖链；核未来时点、特征前缀、成熟标签和反例 |
| 3. 演练及冻结 | `freeze_workflow`→`freeze_contract`→`synthetic_rehearsal` | 真正运行人工小样例；冻结相关定义、代码、输入和方法；资格阶段不导出未来结果供挑选模型 |
| 4. 有限执行 | `execute_workflow`→重新`preflight`→家族互斥锁/预算与选择史→`evaluate_observations` | 上述检查在正式拟合及统计回调之前；连续预测与事件频率分流；训练标准化只用过去成熟结果 |
| 5. 生成和验收 | `render_report`、`verify_receipt`、`check_publication`→`publish` | 核完整预测ID、训练参照、重新汇总数字/单位、自动报告、实际受控账本；只接受新路径登记 |
| 6. 诚实结案 | `state.json`与家族尝试日志 | 执行、证据、覆盖、交易许可分别记录；效果不好不算程序失败，预算中断是暂停 |

主控先审最终解释，允许同预测依赖的新合同重用已计算预测，再生成和验收新报告。程序不会凭一个`verified=true`跳过检查，也不会阻止有系统权限的人在入口以外另写脚本；本轮是应用流程约束，不能被宣传成操作系统安全沙箱。

## 错误回归验收表

“入口”指实际Python执行/发布路径；“公共层”指该路径使用的函数或既有登记表检查。每个最终演示的三条命令另进行了CLI进程级运行，不把所有单元测试说成CLI演示。每项均有错误/正确配对或警告/合法结案对照。

| 已知问题 | 主要用例 | 经过哪一层 | 实际验收结果 |
|---|---|---|---|
| 未定义对象、6偷偷变4 | `test_missing_core_definition_or_scope_before_callback`；`test_universe_6_to_4_undisclosed_blocks_declared_partial_completes` | 执行入口 | 错误合同挡住回调；允许且披露的局部结果完成 |
| 待测条件先被筛成全true | `test_event_counterexamples_and_two_evaluator_end_to_end` | 执行入口 | 无反例拒绝增量比较；保留反例的事件研究完成 |
| 未来、未完成周、前缀变化、训练未成熟 | `test_future_and_unfinished_week_rejected_by_actual_entry`；前缀与成熟边界测试 | 执行入口+公共层 | 错时点在演练/正式计算前挡住；允许剔除的未成熟训练标签披露数量；周期完成须符合来源日历 |
| 停牌、漏报、未知行动与恢复 | `test_unknown_gap_vs_confirmed_halt_and_recovery`；`test_real_panel_binds_calendar_prices_actions_and_open_separately` | 输入公共层+实际资格函数 | 不补假报价；停牌需来源；未知漏报重置语义；预热明确；真实报价不能伪缺失 |
| 端点、路径、最低价、可操作开盘不同 | `test_endpoint_path_open_and_action_distinct`；`test_intraday_low_mae_and_unknown_high_low_sequence`；真实资格测试 | 公共标签层+资格函数 | 对应字段不足仅影响用途；收盘入场不算已发生的当日最低价；真实开盘明确拒绝 |
| 基准遗漏及较差效果 | `test_baseline_or_unit_omission_blocks_publication_not_bad_effect`；预测集合/错误B0测试 | 实际发布路径 | 缺基准或错误训练参照不能发布；完整方法比简单方法差仍完成 |
| 固定50%的二元评分 | `test_b50_exact_and_bad_probability_labels_baselines`；实际事件案例 | 公共层+CLI演示 | 0/1标签、合法比重下B50严格0.25；不要求B2胜出 |
| 自然组构成与共同权重混用 | `test_common_asset_year_weights_and_valid_mixture_outside_group_range` | 公共统计层 | 各自描述与共同对象/年份相同比重比较分开；合法组内不同构成不误判算术错误 |
| 单位或投资收益混写 | 单位/标签测试；`test_policy_account_use_is_explicitly_blocked` | schema、统计层、发布路径 | 百分点及平方分开；篡改单位拒绝发布；本入口不发布账户政策效果 |
| 旧数据、代码、比重凭据；无关卡变化 | `test_stale_check_blocks_actual_entry`；无关定义卡与纯重汇总测试 | 执行入口+缓存/验收 | 实际依赖变化拒绝；无关卡不整体失效；仅文字或汇总比重可零拟合重用预测 |
| 活动登记表与固定旧快照 | 既有`test_research_definitions.py`；相关闭包解析测试 | 既有登记层+入口 | 活动库校唯一ID/版本/依赖；旧固定快照保留原断言；未新增第二因子表 |
| 改名或改目标伪称未见 | 家族改名测试；`test_reformatted_prices_and_changed_target_do_not_become_unseen` | 执行入口与现有尝试日志 | 同资料、更换AI/家族/排版/阈值均不能称新验证；如实探索才能继续 |
| 完成与效果分离 | 连续无增量、事件更差两个案例；年份反向及日期少警告测试 | 入口、公共层、CLI演示 | completed与不支持并存；负结果、宽范围和年份反向不会触发自动调参 |
| 实际回调顺序、绕过产物、少交预测 | 坏资料/错时点回调Mock；绕过产物；少一预测测试 | 执行与发布入口 | 错输入回调次数0；无真实回执/少对象或日期不能完整发布；不能覆盖封存 |

另外覆盖同家族并发互斥、发布失败不重复扣计算时间、训练比重与汇总比重分开、情绪/越权定义与付费/生产用途拒绝。不是凭循环断言数量宣称完成。

## 独立复核与真实测试记录

Sol中等思考分别负责公共计算、输入标签；另一轮只读复核发现六类工程漏口，最终复核又指出两项窄漏洞。根补修后重新跑相关套件，并直接从两个人工价格文件复算164条未来标签、训练参照及所有主评分，差异在浮点允许范围内。B50产物严格0.25，每条固定50%评分也严格0.25。没有用子代理的“通过”替代根验收。

| 实际运行 | 结果 | 证据 |
|---|---|---|
| 相关最终套件（10个测试文件） | **218 passed，12.14秒** | `verification/attempt-final-suite-05.log/json` |
| 两类CLI：演练冻结→运行登记 | 4条正确命令退出0；两案例completed | `demos-final/*/01-freeze-command.json`、`02-run-publish-command.json` |
| 两类CLI：旧比重凭据 | 2条错误命令退出3；正式回调未执行 | `demos-final/*/03-blocked-command.json`及`invalid-run/failure.json` |
| 根独立价格/评分复算 | 两案例各82标签、3/4种参照一致；未拟合 | `verification/controller-independent-arithmetic-final.json` |
| 旧封存及原文 | 274项封存指纹、4份原manifest、2份原文全部一致 | `verification/protected-evidence-check.json` |
| 目录归置自检 | 全绿 | `verification/final-hygiene.json` |

完整相关测试命令保存在套件JSON，摘要命令为：

```bash
python3 -m pytest tests/integration/test_research_workflow_entry.py tests/unit/test_workflow_inputs.py tests/unit/test_workflow_evaluation.py tests/unit/test_question_contract.py tests/unit/test_candidate_preflight.py tests/unit/test_research_input_preflight.py tests/unit/test_research_input_preflight_fix.py tests/unit/test_research_definitions.py tests/unit/test_factor_lab_contracts.py tests/unit/test_factor_lab_validation.py -q
PYTHONPATH=src python3 docs/experiments/raw/research-workflow-engineering-2026-09-29/run_demos.py --revision final
python3 scripts/check_repo_hygiene.py
```

演示脚本拒绝覆盖已有目录，原命令已运行；再次复现需另选新的演示路径/研究家族并如实继承已见记录，不能直接覆盖此次结果。正式runner不导入该raw脚本或旧A01/A02的临时实现。旧岭回归共同域一致性与A02存量218条评分重汇总仅在测试中读取旧归档，没有改写或重新拟合旧市场结果。

开发过程中两次早期测试期望失败，以及212/216/217/218项逐步通过的运行均保留，见`verification/engineering-attempt-history.json`与`verification/final-verification-amendment.json`。早期问题是人工夹具预期与拒绝顺序，不是尝试市场参数；不会只保留最漂亮版本。

## 修改与复用范围

新增公共模块：`workflow.py`（受控编排、冻结、验收）、`workflow_inputs.py`（特征/标签/覆盖）、`workflow_evaluation.py`（两种有限方法、参照、共同汇总）。扩展原`question_contract.py`和`input_preflight.py`，原问题检查及输入资格仍复用；`candidate_preflight.py`未改。

现有CLI增加两个互斥分支及新分支的报告验收；新增三份相关测试。新入口当前规范只导航到`docs/research/current-standards.json`，AGENTS与既有项目编排skill补实际调用说明，`factor-lab-usage.md`补导航。现有定义表没有因为本轮工程增加因子卡。

作者的下一项技术因子工作是：根据原文及唯一登记表实现准确特征/事件适配器与研究卡，并核对它与当前有限评价器是否适配；随后直接走同一个草稿→演练冻结→受控计算→主控解释→发布路径。不要再复制训练、标签、相同样本比较、重复日期处理和报告计算。新增或删除技术体系规则仍先与用户确认。

用户的一页说明在 [research-workflow-usage.md](../research/research-workflow-usage.md)。完整文件清单及指纹在本轮`delivery-manifest.json`；只列本轮改动，不把工作区大量既有改动认领为本轮成果。

## 剩余边界与停止理由

本轮工程问题已经回答：入口实际接入、已知错误有成对测试、两种合法负结果可以完整登记。必要的本轮验收无待执行项。预算补齐及新版本重验由根书面复核，见`controller-acceptance-final.md`。停止是有界问题完成，不是因负结果或预算不足停止。

尚未完成的是新问题或明确的能力边界：准确A01/其他技术适配器；真实完整行动历史及到达时点；真正可操作开盘和完整账户政策；旧独立runner全面迁移及过去资料接触史。报价接触摘要记录本入口已评价日期的实际close，不能保证所有别名、所有未来标签区间或未接入工具的资料接触都已被发现。科学独立性仍要核真实交接，不因日志无记录就自称未见。

没有自动启动下一轮技术因子、情绪/宽度/宏观研究、部署或大规模扫描。系统待升级只追加本项成果和待验收证据，不改大目标的里程碑或自动接受用户验收。

## ARCHIVE / 最小决策卡

| 项目 | 本轮决定 |
|---|---|
| 执行 | completed；六阶段工程接入与必要验收完成 |
| 证据 | 工程行为在限定范围内成立；真实因子效果未评估 |
| 覆盖 | 新workflow执行/发布分支；两种有限方法；旧入口未全面迁移 |
| 来源和合同 | 用户2026-09-29工程指令；本轮`contract.json`、`source-manifest.json`、接口补充及实际demo冻结合同 |
| 尝试与预算 | 7200秒内本地工程；2种正式人工演示；市场拟合0、网络0、付费0；失败及成本保留 |
| 资金、策略与交易 | 不适用；无生产采用或真实交易许可 |
| 下一动作 | 准确技术因子适配后复用本入口；不以本工程替代因子验证 |
| 复核 | 主控书面验收、Sol只读审查、实际测试/命令、独立算术与保护指纹 |
