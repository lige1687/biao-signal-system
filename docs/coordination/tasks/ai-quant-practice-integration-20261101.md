# AI量化实践接入 — active

- task-id: ai-quant-practice-integration-20261101；owner: 本轮AI量化来源研究/root；status: active；scope_released=false。
- updated_at: 2026-11-01T12:43:06.008089+08:00
- checked_coordination_sha: 47e488a1cf6c930c559bc1bd9aef1f8842385253。已读COORDINATION1.1、research-dispatch-controller、research-method-practice-20261031、external-learning-x-review、theory-workflow-system-increment、strategy-account-bridge-20261020及精确路径命中任务最新状态。相关源码/共享方法范围已明确释放；不接管历史池、账户引擎、UI或冻结实验。
- 用户本轮批准两项：新假设前读取旧结论和重开条件；信号与账户结论冲突时先复用证据、必要时仅诊断一个组件。另继续读新来源，额外建议不自动实施。
- 基线：codex/factor-unit-research-20260915@18e64fa632dba5dbad0e5fcae09b4ccc75f119a9 + 共享脏区；源码未推，远端不能据HEAD复现。元数据独立worktree，不切主区。
- 唯一写入：root持src/lei_signal/research/preparation.py窄接线、tests/unit/test_research_practice_preparation.py、.agents/skills/lei-lowfreq-research/SKILL.md窄入口、docs/research/research-workflow-usage.md窄追加；实现助手分别持新src/lei_signal/research/practice_context.py+tests/unit/test_research_practice_context.py、新src/lei_signal/research/component_diagnosis.py+tests/unit/test_component_diagnosis.py。旧attempt_review.py/既有tests不改。
- 自有归档：docs/experiments/ai-quant-practice-integration-2026-11-01.md、同名raw目录、docs/archive/handoffs-plans/ai-quant-practice-integration-20261101/、docs/ops/work-progress/ai-quant-practice-integration-20261101.md。本报告registry键及INDEX单行拟收尾重核串行后登记，当前未占写。
- 适用现行索引/研究闭环、TDD/独核；原策略SHA与批准值一致，未改。保留旧preparation定义来源url/vintage严格schema失败，不以放宽验证绕过。新增只读历史入口不依赖定义解析；缺结果不推断无效，无自动重开或运行。
- 验收：失败先行的行为测试、真实旧资料只读CLI、路径/来源/状态边界、条件诊断单组件、仓库归置、源指纹；工程通过不代表收益改进。未新增金融实验或重跑，0取行情/交易/安装/付费/仓外写。小成果预计<2MiB，fresh磁盘约19GiB；大产物0。
- 来源累计前两阶段11次；本轮新增来源阅读预算6次已由只读助手使用，结果需本地主控查重。模型Sol medium，实际费用未知。待办DB仓外保持不写。
- 下一步：登记普通推送读回后按单写实施，验证并保存报告；当前代码未改、测试未运行。
