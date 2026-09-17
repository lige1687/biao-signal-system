# ZCode 限定重派：因子证据工具 S1–S3 收尾

用户于 2026-09-17 明确要求解决旧任务及派发权限问题。本任务只落实已有主控裁决，不扩研究方向。旧 job `5c5e753f-d7e4-4458-a6d7-ab79fca81e63` 因派发器错误使用 `build` 模式而没有写入任何文件、没有运行测试；旧 job 保留失败记录，不复用其会话或轮次。本次为修好派发器后的新任务。

工作区 `/Users/yongbiaoli/Desktop/lei-signal-lab`；分支 `codex/factor-unit-research-20260915`；起始 HEAD `2b05787f746991a90ec33a06736b61cfdeca6119`。不得切分支、建工作树、暂存、提交、reset 或清理他人改动。起始时六个可写既有文件均无工作区差异；身份变化或这些文件出现非本任务并行修改立即停。

先完整读取根 `AGENTS.md`、`CLAUDE.md` 及其要求的策略/研究规范。本次服务于交易规格道路状态相关研究工具的证据可靠性，只做入口、解释和记录纠错；不改变双均线、MACD、策略定义、规则参数、真实研究结果或生产行为。研究原则采用 `docs/research/experiment-backtest-principles.md` v1.1，执行合同采用 `docs/research/ai-execution-contract.md` v1.0.1，定义标准采用 `docs/research/definition-standard.md` v1.1.0。

权威任务：完整读取 `docs/experiments/factor-evidence-controller-review-2026-09-16.md` §9.2–9.5。旧 R1–R4 历史保留。独立反例：`docs/experiments/raw/factor-evidence-controller-review-2026-09-16/review-repair.py`（只读，可读源码，不运行含历史核验的整脚本）。进度总览与 OKR 不是执行权限替代物。

G1/S1：公开 `run_analysis` 直接调用只支持显式合成输入，`real` 模式即使 `symbol=510300` 且自填 `base_dir/sha` 也必须在写盘前拒绝。真实 `main` 仍先完整校验协议及固定输入，再调用私有落盘函数。不引入可自填 `verified/token/approval` 旁路。不要删除真实 `main` 或降低其校验。用合成测试核路径；禁止真实正向重跑。

G2/S2：报告“单个年份不使差值反号”、卡片“逐年方向不一致”、稀疏 note“不重叠”等改为中性、指向实际数值的解释，不新增阈值或统计。合成两年反例：2020 真/假 0.1/0，2021 真/假 −0.2/0，全期 −0.05，去 2021 后 +0.1；不得继续给不反号结论。合法两组、单组不可估计仍能输出；原真实文件不改。

G3/S3：`repair-log` 原红批因缺新增常量导致收集失败，不能证明未运行的行为测试逐一复现。追加准确纠正，不回退代码重造红日志。旧原文和不可恢复日志限制保留。修后字节及哈希另存本任务目录，旧 repair 快照不覆盖；报告说明历史 `run-01` 仍绑定旧代码。

可写仅：

- `src/lei_signal/research/factor_evidence/runner.py`
- `src/lei_signal/research/factor_evidence/stability.py`，仅改上述 note
- `tests/integration/test_factor_evidence_cli.py`，必要时该包原有测试仅修接口更名影响，不加新能力
- `docs/research/factor-evidence-reliability-usage.md`
- `docs/experiments/factor-evidence-reliability-v1-2026-09-16.md`，只追加带日期纠正
- `docs/experiments/raw/factor-evidence-reliability-v1-2026-09-16/repair-r1-r4/repair-log.md`，只追加 S3 纠正
- 本目录新增交付、日志、修后原字节和清单

共享 `registry/INDEX/OKR`、主控报告交主控统一更新，不动。保护 `run-01`、`protocol-v1.0.0.json`、`freeze/1.0.0`、`supplement`、旧 repair 快照，以及 `factor_lab/factor_unit`、生产、规则账本和定义登记表。

预算沿用 §9.5，跨旧失败 job 累计：旧 job 的 pytest/ruff/hygiene/合成输出/快照核验均为 0 次，因此本次可用定向 pytest ≤3 次（含失败）、相关回归 1 次、ruff 1 次、测试内合成输出 1 批、快照核验 1 次、目录归置检查 1 次。不要把测试内多次输出藏成零运行。达到上限即停。禁止真实分析、状态或目标重跑，禁止联网数据、新依赖、参数/观察窗/产品变更。

相关回归命令沿用主控报告 §2 九文件命令；ruff 只检查本轮改动文件；`python3 scripts/check_repo_hygiene.py` 必须执行，范围外报警只报告，不顺手清理。每次命令保留 stdout/stderr/退出码，不批量大范围替换文件。

交付本目录 `delivery.md`：G1–G3 证据、改动清单、实际命令和次数、旧结果保护核验、失败及未完成项，修后源码原字节和清单。开头必须写“执行 agent 声明，待主控复核，不代表用户意见或新增授权”。所有 JSON 说明如实，不将合成通过称真实结果复跑。完成即停，返回 Skill 规定完成标记触发回调。
