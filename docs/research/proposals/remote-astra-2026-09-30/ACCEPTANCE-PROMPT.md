# 给验收总负责人的提示词（远端核心队列 2026-09-30）

你是 biao-signal-system 项目的验收主负责人。请对远端 Opus 5.5 会话交付的“核心队列 T2—T10 及模块 A 机会母体审计”做独立验收。你的职责是核实关键事实、判定能否接受、列出返修项与需要用户决定的事项，不是重做全部研究。

## 先读（按顺序）

1. 根目录 `AGENTS.md`（特别是“第零步”“交易研究与回测必读”“实验归档规约”“说人话”）。
2. 任务书：`docs/archive/handoffs-plans/remote-astra-queue-2026-09-30/` 下的 README.md、OWNERSHIP-AND-DEDUP.md、TASKS.md、RESEARCH-DECISIONS-ARCHITECTURE.md。
3. 交付总报告：`docs/experiments/remote-astra-core-review-2026-09-30.md`；补充报告：`docs/experiments/module-a-population-audit-2026-10-02.md`。
4. 状态账：`docs/research/proposals/remote-astra-2026-09-30/task-state.json`；各题提案在同目录 `T2/ T3/ T4/ T5/ T6/ T7/ T8/ T9/ T10/`；可执行核验在 `docs/experiments/raw/remote-astra-T{2,3,4,5,6,7,9,10}-2026-09-30/` 与 `docs/experiments/raw/remote-astra-T2-audit-2026-10-02/`。

分支：`codex/astra-core-review-20260930`（基于 `codex/core-sync-20260930` 的 `639ad8d`）。交付方声明：未改生产代码、规则账本、定义登记表、策略原文副本、旧报告与旧 raw；只新增本任务文件，并在 `registry.json` 与 `INDEX.md` 各加两条登记。

## 必须独立核实（不要只复述交付方的“通过”）

1. **改动边界**：`git diff 639ad8d --stat` 只应包含上述新目录、两份报告、`registry.json` 与 `INDEX.md` 的追加行；`src/ configs/ tests/` 与任何既有 `docs/experiments/raw/*` 文件零改动。运行 `python3 scripts/check_repo_hygiene.py` 应全绿。
2. **T2 关键结论**（模块 A 口径与原文不一致）：
   - 运行 `python docs/experiments/raw/remote-astra-T2-2026-09-30/run_cases.py`，应输出 9/9 一致、FAILURES none；抽查 C1、C2、C7、C9 的人工答案（`expected.json`）是否真符合策略原文 `docs/research/strategy-source-snapshots/2026-09-30/` 体系 §4.4、§7.4 与实现模块 A。
   - 打开 `src/lei_signal/rules/first_ma_pullback.py`，核对报告引用的行为：武装条件 :474-475、入场前作废 :284-314、转黑重置 :235、构造缓存 :324、回到触碰带上方即结束 :436-463。
   - 运行 `real_coverage.py`，核对“生产读法参考实现与生产代码逐事件一致 239/239、188/188”和“55/38 次入场中 42/30 次触碰前从未整天离开触碰带”。
3. **机会母体审计**：运行 `python -B docs/experiments/raw/remote-astra-T2-audit-2026-10-02/population_audit.py`（约 2 秒，全历史构造口径：457/504 复现）；有时间再加 `--asof-structures`（约 15 分钟，应 504/504 复现、364 条“未离开就算回调”、11 笔成交中 9 笔属此类）。判断“逐日只用当时历史识别构造”的做法是否合理。
4. **T6 资金核算**：重跑 `docs/experiments/raw/remote-astra-T6-2026-09-30/` 下 `ledger.py`、`probe_frozen.py`、`real_accounts.py`、`compare.py`，输出 JSON 应与提交版逐字节一致；核对冻结引擎 `research-broad-etf-technical-2026-09-08/execution/engine.py:207` 的浮点取整，与首12 `run_accounts.py:253-262` 的除息/拆分日缺价估值问题；从原始行情核对 2024-10-08 两只 ETF 开盘涨停。
5. **T5 反例**：重跑 `PYTHONPATH=src python docs/experiments/raw/remote-astra-T5-2026-09-30/check_counterexamples.py`，结果应仅 `elapsed_seconds` 不同；重点复核 F1（盘中K线写入研究库）与 F2（放量突破事件被后来的失效改写）的可运行最小输入与引用代码行（`tradability_gate.py:262-265`、`compose/pipeline.py:81,85`）。交付方自报 H01d 的缓存子检查无效、未重跑——确认这一限制已如实写明。
6. **T3/T4/T7/T9/T10 演练**：分别运行 `b_cases.py`（9/9 预测一致）、`timing_cases.py`（12/12）、`method_examples.py`（4/4）与 `qualification_count.py`、`observation_ledger.py`（5/5＋3 个负例）、`handoff_check.py`（5/5）、`existing_audit.py`。抽查 T10 的“行情 CSV 只差换行符”和“定义登记表因 56 个证据文件缺失无法加载”。
7. **公开资料**：T7 方法卡称精读 MacKinnon-Nielsen-Webb（arXiv:2205.03285）指定章节与 Montgomery-Nyhan-Torres（AJPS 2018 发表前版本）§5；T8 称上交所法律声明已现场核读、深交所声明未找到。抽查引用是否与原文一致，阅读范围是否如实。

## 判定口径

- 对每项给出：接受 / 有条件接受（列返修项）/ 不接受，并写理由。核验通过只说明计算和语义核对按约定执行，不代表任何因子或策略有效。
- 区分三类问题：机械错误（交付方可直接修）、研究代理取舍（主负责人可定）、策略语义（必须由用户确认）。不得替用户确认策略语义，不得因验收而修改生产代码、规则账本、登记表或旧封存结果；如认为需要修复，写成单独任务。
- 检查“说人话”：报告首段的一句话结论是否让非量化背景的用户能看懂测了什么、结果是什么、有什么意义。
- 检查去重：本交付是否重复了异常放量、六线聚散、A01 个股资料、情绪、市场来源或页面接入等已有负责线的工作。

## 需要合并交给用户决定的事项（核实后转交，不要自行拍板）

1. 回调结构条件：原文“底部构造＋低一级别多头”与实现“至少一种”的冲突（T2 Q1）。
2. “一波趋势”何时结束：是否 LEI 转黑也结束（T2 Q2）。
3. 横盘突破的两个失效动作是否必须同一天（T3 Q1）。
4. 是否采购或提供小时行情（T8）。

## 交付格式

写一份验收报告放 `docs/experiments/remote-astra-core-acceptance-YYYY-MM-DD.md`（含 `## 一句话结论（大白话）`、逐项判定表、实际运行的命令与结果、返修清单、转交用户的问题），并在 `registry.json` 登记（category 用“方法论与验证”）。主负责人另需决定：T2 研究生命周期开关（`lifecycle_ref.RECOMMENDED`）是否批准、生产修复建议（`T2/production-fix-notes.md`、`T5/fix-suggestions.md`、T6 README 中首12程序问题）是否立项。
