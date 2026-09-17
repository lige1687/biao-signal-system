# ZCode限定执行：因子证据工具S1–S3收尾

用户于2026-09-17授权主控通过zcode-delegate派发下一步。本任务只落实已有主控裁决，不扩研究方向。

工作区 /Users/yongbiaoli/Desktop/lei-signal-lab；分支 chore/repo-governance-2026-09-16；HEAD 01c21226279baf9743311bb601b54eae07c0c3b8。不得切分支、建工作树、暂存、提交、reset或清理他人改动。身份变更或可写文件出现并行修改立即停。读取AGENTS.md、CLAUDE.md及其必读规范；本次服务交易规格§4/5道路状态的研究证据，不改变双均线、MACD、交易或生产规则。

权威任务：docs/experiments/factor-evidence-controller-review-2026-09-16.md §9.2–9.5。完整读取。旧R1–R4历史保留。独立反例：docs/experiments/raw/factor-evidence-controller-review-2026-09-16/review-repair.py（只读，可读源码，不运行含历史核验的整脚本）。进度总览与OKR不是执行权限替代物。

G1/S1：公开run_analysis直接调用只支持显式合成输入，real模式即使symbol=510300且自填base_dir/sha也必须在写盘前拒绝。真实main仍先完整校验协议及固定输入，再调用私有落盘函数。不引入可自填verified/token/approval旁路。不要删除真实main或降低其校验。用合成测试核路径；禁止真实正向重跑。

G2/S2：报告“单个年份不使差值反号”、卡片“逐年方向不一致”、稀疏note“不重叠”等改为中性、指向实际数值的解释，不新增阈值/统计。合成两年反例：2020真/假0.1/0，2021真/假−0.2/0，全期−0.05，去2021后+0.1；不得继续给不反号结论。合法两组、单组不可估计仍能输出；原真实文件不改。

G3/S3：repair-log原红批因缺新增常量导致收集失败，不能证明未运行的行为测试逐一复现。追加准确纠正，不回退代码重造红日志。旧原文和不可恢复日志限制保留。修后字节及哈希另存本任务目录，旧repair快照不覆盖；报告说明历史run-01仍绑定旧代码。

可写仅：src/lei_signal/research/factor_evidence/runner.py；stability.py只改上述note；tests/integration/test_factor_evidence_cli.py（必要时该包原有测试仅修受接口更名影响调用，不加新能力）；docs/research/factor-evidence-reliability-usage.md；执行报告docs/experiments/factor-evidence-reliability-v1-2026-09-16.md追加带日期纠正；旧repair-log.md追加S3纠正；本任务raw目录新增文件。共享registry/INDEX/OKR、主控报告交主控统一更新，不动。

先记录可写文件哈希与现有diff，保护run-01、protocol-v1.0.0、freeze/1.0.0、supplement、旧repair快照，以及factor_lab/factor_unit/生产/规则/登记表。若发现已有另一执行者S收尾已启动或完成，停止并报告，不重复。

预算沿用§9.5，跨本任务累计，不因新job重置：定向pytest≤3（含失败）、相关回归1、ruff1、测试内合成输出1批、快照核验1次，另目录归置检查1次。先核对已有S执行账，已消耗扣除；未消耗才使用。不要把测试内多次输出藏成零运行。达到上限即停。禁止真实分析/状态/目标重跑、联网数据请求、新依赖、参数/观察窗/产品变更。

相关回归命令沿用主控报告§2九文件命令；ruff只检查本轮改动文件；python3 scripts/check_repo_hygiene.py必须执行，范围外报警只报告不顺手清理。每次命令保留stdout/stderr/退出码，不批量大范围替换文件。

交付本目录delivery.md：G1–G3证据、改动清单、实际命令和次数、旧结果保护核验、失败及未完成项，修后源码原字节和清单。所有JSON说明均如实，不将合成通过称真实结果复跑。交付以“执行agent声明，待主控复核，不代表用户意见或新增授权”开头。完成即停，返回skill规定完成标记触发回调。
