# 买方方法接入与低余量主动恢复已完成

- task-id: buy-side-method-increment-20261104；owner: root / chat01a1a6ef-35ef-7b02-8681-2dd40a202f89；status: completed_bounded_integration；scope_released: true（只限本轮源码/文档；冻结结果仍保护）。
- checked_coordination_sha: 1db43be46f75ac7927442bf3257315e6bdb98466；checked_at: 2026-11-05T18:49:31.910654+08:00；已读此前所列任务及gemini-factor-fit、breadth-reading-aid新增范围，均无本轮同写重叠。
- 用户11月5日要求低于5GiB先清理再继续，外盘优先，已改AGENTS/存储规范与machine-readable recovery动作；只读plan不静默删除，由当前AI核闲置/归档/复查。没有后台删除或自动通知。当前任务曾触发4.96GiB，盘点缓存后移除前恢复5.94GiB，0删除并继续，无重复确认。
- 当前组合入口portfolio-review与23项边界检查落地；采用当前JKP/Tidy口径卡和AQR/Robeco/FactorBench限定方法，复用文献库24资料/33条/4路线，旧23/31保持。
- 独立验收：31,872GP股票月值/身份映射一致，233零收益与5未知分开；9组保存比较最大差1.78e-15，5,124费用单元恒等式误差0，最终CLI输出一致。83相关测试、62整合通过；1外盘FIFO环境失败在本机重验通过；格式修正后23模块测试、Ruff/归置通过。测试集合有重叠，不把总次数当增量。
- 金融决定：0新选股/回测/寻优/行情下载；FH30对G1既有25bp净增量+0.06025pp/月，旧95%区间[-0.109,+0.228]，仍不确定；不把旧收益归因新接入。未补完整PIT/成交/母指数，未改生产交易/前向账户。
- 报告: docs/experiments/buy-side-method-increment-2026-11-05.md；SHA256:8012d4324c612662255140214db936fe3c1f4a24b8af85c994e599bd63670182。附件docs/experiments/raw/buy-side-method-increment-20261104含state、预算、inputs、verification、completion、限定diff；本机8000/5173报告及学习API读回一致，831旧报告条目保持。
- 外盘固定UUID DEBA1C85-6059-3865-B50A-A8EE1F80E4D9；结果LeiSignal-新实验结果/buy-side-method-increment-20261104/buy-side-method-increment-20261104-20261105T183446-ff6b74f3b3d6/result；<10MiB外盘和<2MiB本机新增预算通过。
- 工作分支仍codex/factor-unit-research-20260915@18e64fa632dba5dbad0e5fcae09b4ccc75f119a9；源码/报告当前仅本地未提交，远端不能据此复现；只本协调记录推送。没有操作共享索引/强推/部署。
- 范围内无待执行动作或用户决定；需要新合格证据时沿已有研究预算恢复。历史首次容量失败和所有测试/来源失败保留。

---

# Buy-side method increment 20261104

- task-id: buy-side-method-increment-20261104
- owner: Codex chat 01a1a6ef-35ef-7b02-8681-2dd40a202f89 root
- status: active; scope_released: false
- updated_at: 2026-11-04T22:40:01.844340+08:00
- checked_coordination_sha: 6963c79a2f0698e500d73199a0b5b57e60fdc697
- read_tasks: research-dispatch-controller, factor-method-standards-increment-20261103, strategy-account-bridge-20261020, ai-quant-practice-integration-20261101
- work_branch: codex/factor-unit-research-20260915; base_commit: 18e64fa632dba5dbad0e5fcae09b4ccc75f119a9
- latest_pushed_artifact_commit: none; new artifacts local only until verified.
- authorization: User asks to implement JKP/Tidy, AQR/Robeco and FactorBench priorities with quantified increments; research methods only, no production/trades or parameter search.
- question: Can current source semantics and a reusable after-cost incremental comparison improve the decision evidence versus accepted V2? Do not reattribute existing V2 improvements to this task.
- baseline: frozen cn-profitability-risk-v2-construction-2026-11-04; 132 calendar/127 gross/122 net months; fixed cohort, incomplete PIT and execution remain.
- standards: current-standards.json plus research-closure and existing factor-combination workflow; original frozen artifacts unchanged.
- conflict decision: prior account evidence review completed and explicitly released; do not modify that checker, preparation or frozen V2 files. Own new module/test/reference/report/raw only. Shared docs append exact sections; registry append one record preserving all others.
- write_paths: src/lei_signal/research/incremental_portfolio_review.py; tests/unit/test_incremental_portfolio_review.py; docs/research/buy-side-method-reference.v1.json; docs/research/factor-combination-workflow.md; docs/experiments/buy-side-method-increment-2026-11-04.md; docs/experiments/raw/buy-side-method-increment-20261104/; docs/experiments/registry.json; docs/experiments/INDEX.md; docs/ops/work-progress/buy-side-method-increment-20261104.md
- unique writers: helper owns new module and test only; root owns remaining paths. No other path ownership claimed.
- acceptance: boundary tests; saved monthly artifact reconciliation; zero missing-return imputation; common calendar masks; gross/net cost attribution; active versus total correlation; current source and formula scope bound.
- budget: one saved-data analysis, zero new holdings/backtests or parameter search; <=10MiB external outputs and <=2MiB internal code/records; source review <=6 batches; 1 helper. Engineering repair not new strategy trial.
- known overlaps: previous V2 buffer/filter account evaluation retained, prior account_evidence_review remains authoritative for its payload type. No duplicate pipeline or purported new PIT.
- passed: current coordination review and frozen result existence; pending: implementation and independent acceptance.
- blockers: none; storage plan required before output.
- source results: external cn-profitability-risk-v2-20261104/20261104T003628/fine-result, read-only with new hashes bound before comparison.
- next: implement bounded reusable review, reconcile saved evidence, archive quantitative result.

## 2026-11-05 continuation and storage policy authorization

- checked_coordination_sha: f8e4a60e5a13257f463440aa30c4a82e69583de8; checked_at: 2026-11-05T18:34:11.899743+08:00
- read_tasks: previous four plus mac-local-storage-cleanup and storage-headroom-20261015. Prior storage task completed; no active code writer declared. User now explicitly authorizes changing project policy and bounded cleanup when below5GiB. Historical frozen scripts remain untouched; source change is an explicit new output_storage version.
- added write_paths: AGENTS.md; docs/ops/research-output-storage.md; docs/ops/codex-storage-management.md; configs/research-output-policy.v1.json; src/lei_signal/research/output_storage.py; tests/unit/test_research_output_storage.py; src/lei_signal/research/factor_combinations.py; docs/literature-learning/learning-seed.json; docs/literature-learning/READING.md; docs/literature-learning/buy-side-learning-sources-2026-11-05.md. Own report filename now buy-side-method-increment-2026-11-05.md.
- unique writers: helper owns incremental_portfolio_review.py and its new test; root owns all other listed paths. No concurrent changes to helper paths by root after dispatch.
- storage behavior: below5GiB prompts agent to reclaim verified reproducible idle caches or archive verified inactive recoverable products to fixed external disk, then recheck and continue. Do not stop at capacity error or ask again within authorized cleanup scope. Preserve datasets, frozen evidence, databases, sessions, environments and uncommitted work. Plan-only remains read-only; errors expose recovery action instead of silently deleting. No daemon.
- fresh capacity: about7.9GiB internal and445GiB external; no cleanup necessary now; no claiming space freed. Prior blocked plan and read-only computation preserved. Budget remains one saved-data batch, no holdings/backtests, external10MiB/internal2MiB.
