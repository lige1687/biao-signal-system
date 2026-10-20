# 策略完整性建议吸收与账户评价补缺

- task-id: strategy-account-bridge-20261020；owner: 01a1585f-53de-7883-a5cb-d9c5be52902c/root；status: active；scope_released: false；updated_at: 2026-10-20T16:19:26.538496+08:00。
- checked_coordination_sha: f0aabbadf28e30261cf34cbb0274d5578ac7876f；checked_at: 2026-10-20T16:19:26.538496+08:00；已读 COORDINATION1.1、research-dispatch-controller、research-utility-review-20261012、personal-lowfreq-system-audit-20261018、lowfreq-strategy-discovery-20261019、gemini-strategy-review-20261020、dot-pro-strategy-definition、theory-workflow-system-increment、classic-factor-research、pro-advice-process-review-20261020相关最新范围。
- 用户授权：“看看我们策略方面的缺口，这个是一个ai给的建议”；“能吸收的就去做，搜索推特或者优秀研究的实践资料，看整合到我们系统里边合适的位置”。本题只完成建议与现状核对、原始来源研究、方法/学习入口接入和已存账户路径的描述诊断；0新策略收益实验/行情下载/寻优。不改变原文/规则/生产/交易、不接管原A与账户owner。
- 基线18e64fa632dba5dbad0e5fcae09b4ccc75f119a9，成果树.codex/worktrees/strategy-account-bridge-20261020、分支codex/strategy-account-bridge-20261020；主工作树旧脏改保留。成果暂仅本地不自动提交或推送；协调元数据独立普通push。
- 本轮问题：哪些建议是已有能力、哪些是实际缺口；能否把完整规则、资金比较和回本/相对落后持续时间接入既有研究，不重建账户引擎。研究层/学习层，不是技术信号层。
- 唯一新增写入：docs/experiments/strategy-account-bridge-2026-10-20.md、同名raw/、docs/literature-learning/strategy-account-method-card-2026-10-20.md、docs/ops/work-progress/strategy-account-bridge-20261020.md、src/lei_signal/research/account_path_diagnostics.py、tests/unit/test_account_path_diagnostics.py。源码先在独立树实现、验后镜像同名主树（若已存在则停止）。
- 最小现有入口写入：docs/research/methods/factor-validation-guide.md仅增加本方法卡指针；docs/literature-learning/learning-seed.json只增本地方法笔记paper/两entry并加入classic-process；README与READING仅加本入口。registry/INDEX只追加本报告键/行，写前重新读并核其他内容不变。系统待升级仅K-baseline现有目标note，不改owner/授权/状态/里程碑/next_action，若API落点在仓外则先不写。
- 冲突决定：原A/日小时/排序/股票财务/新ETF策略及旧资金引擎保持原owner；旧报告、raw与源日账只读。新持续时间诊断是通用纯计算后处理，无信号/数量/成交/行情IO，无共享workflow改动。theory方法文档入口此前有限范围已释放；本次只添链接，不更改其规则。不同报告registry只写自身键并在写前核最新。
- 分工：Sol medium strategy_gap_audit只读已有覆盖已完成；Luna low拟唯一实现新纯诊断模块和手算反例测试，root定义接口/校验关键数值与说明。费用未知，不人为调用新模型打分。
- 采用research-closure资料研究与保存结果描述、lei-lowfreq-research及current-standards实际版本。两原文SHA与确认值一致。方法来源2检索（含X未得可引用原帖）与4原始页面；后续仅读已返回页面的定位，0新增来源、0付费。
- 验收：逐项建议去重/证据/暂缓原因；规则卡填现状而非空模板；同一已存日期及调整入金影响后的净值核回本段、期末未恢复和从起点持续落后（不同于距历史相对峰值）；严格拒绝缺失/错位输入，局部价格差不冒充资金归因；文献与报告API/浏览器可见、链接/旧内容保护和归置检查。
- 存储：固定盘身份已核；本题只新小代码/报告/诊断摘要预计250KiB、测试小临时输出，不创建大结果，不读媒体、不迁移冻结输入。已有四基金日历日账仅只读，未来规则/效益尚未评价。
- 下一步：推送读回本范围后实现小诊断与方法卡/学习条目，保存对旧结果的新增描述，检验系统可读并归档。条件不足的完整策略定义保留原任务，不把本工程交付算完整策略有效。
