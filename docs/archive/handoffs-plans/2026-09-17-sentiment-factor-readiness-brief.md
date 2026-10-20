# 核清已有情绪对象并提交首个情绪单位实验候选

工作目录 /Users/yongbiaoli/Desktop/lei-signal-lab。用户授权并行推进因子规范与研究；本任务仅做已有实现与证据的核对、交付下一步可审提案，不启动新研究计算或开发。
开工核对 branch/HEAD/git status，不切分支、不提交、不暂存、不重置、不清理。当前参考 HEAD 29b150f58b3f6d8c6e558a748c12dac3384af173；变化时记录并检查影响，勿回滚。现有宽度研究由 ZCode 独占 src/lei_signal/research/breadth_description*.py、tests/unit/test_breadth_description.py、raw/breadth-b200-first-description-2026-09-17；不得读其未交付结果作结论、不得写入。
先读根 AGENTS/CLAUDE、目录内适用 AGENTS，docs/trading-spec-v1.md、configs/rules.v1.yaml、.claude/skills/macd-reading/SKILL.md、docs/plan-sector-trend-page.md；采用 docs/research/experiment-backtest-principles.md v1.1、ai-execution-contract.md v1.0.1、definition-standard.md v1.1.0、experiment-report-template.md v1.1.0。记录实际版本和 SHA。唯一登记表 definitions.v1.json 只读；完整卡须按 profile 合并语义解析，不新造同职责库。
所有旧结果只读：旧报告声明≠本轮核验，文件存在≠通过验收，数据取得时刻≠历史可得时刻。基本面/消息只叙事，不增加硬过滤。本任务不输出新因子有效性结论，不改规则/生产/UI/OKR/registry/INDEX。
允许 rg、读文件、git只读、对文件做哈希、CSV/JSON结构检查、检查链接；禁止导入有顶层副作用的旧脚本或执行旧main。零联网、零安装、零真实因子或目标重算、零回测、零收益统计；不接触凭据。每项事实附文件/行号或键、SHA、核验范围。最多聚焦8个关键输入文件深入核查，其余做导航；不恢复全部历史。结构核查批次最多3，目录卫生检查最多1；逐次保留命令与退出码，失败计数不重置，额度到即停，交付未完项。不以任务轮次重置预算。
独占输出目录如下；除此之外一律只读。仅写Markdown/CSV/JSON（不开发代码）。目录若已有产物，停止避免覆盖。报告标“待主控复核的提案”，不宣称结案或已采纳。交付前检查自己创建的链接/CSV/JSON，记录读取的关键输入前后hash漂移；漂移暂停受影响结论，其他人的变化不回滚。不得重复创建第二份权威正文；只引用现行规范，给精确拟合并段落。完成后回调主控，不执行自己提出的下一步。

服务独立环境研究层，情绪不进入生产硬过滤。只写 docs/research/proposals/sentiment-factor-readiness-2026-09-17/。
先读已有 docs/experiments/raw/factor-unit-readiness-2026-09-15/sentiment-dossier.md、docs/experiments/sentiment-four-input-audit-2026-09-08.md、sentiment-combination-feasibility-review-2026-09-08.md、vix-sentiment-ARCHIVE-2026-09-01.md，以及方向提案 v1.1（factor-library-direction-exploration-2026-09-16），避免重复旧泛泛盘点。只追溯这些文件直接引用的代码/数据，优先 market_context/sentiment_signals、market_mood、retail_heat 等实际现存路径。
交付 object-evidence.csv：最多4个已有数值/状态对象，列公式/单位/频率/适用市场/实际来源/历史区间/三个时刻/修订或回填/已登记准确ID或未登记/历史使用情况/代码位置/数据hash/证据限制。叙事仪表盘与可计算序列分开；AAII/NAAIM/VIX/散户热度不视为同一种测量。不要把旧政策实验成功或失败等同于单因子价值证明。
交付 candidate-review.md：只按定义清晰、数据可追溯、适配问题选择最多1个推荐候选，不按旧收益排名选择。列其不适合用途、已看过历史的选择偏差；全部资料不足可推荐暂停并具体指出最小缺口。无需为了选出赢家而新增因子。
交付 experiment-proposal.md：写一个待批准的最小单因子研究方案，区分指数状态研究/跨资产排序，明确候选对象、载体选择理由、目标口径、时间对齐、频率、缺失、重复观察/重叠、主要指标与能不能解释什么。不自动沿用510300或21天，不跨市场错配；方法/载体需主控裁定的列备选理由，不自行授权运行。附可交执行者的下一轮prompt，任何真实统计/联网/新源均需后续许可。
交付 README.md 与 sources-and-checks.json，旧报告结论逐条注明本轮复核深度。不得宣布“冰点机会已确认/中间区间已证伪”等未复验泛化结论。

