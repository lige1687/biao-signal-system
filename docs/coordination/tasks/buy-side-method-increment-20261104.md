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
