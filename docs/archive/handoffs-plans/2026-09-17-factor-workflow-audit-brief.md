# 把因子研究标准流程变成可操作的导航与缺口清单

工作目录 /Users/yongbiaoli/Desktop/lei-signal-lab。用户授权并行推进因子规范与研究；本任务仅做已有实现与证据的核对、交付下一步可审提案，不启动新研究计算或开发。
开工核对 branch/HEAD/git status，不切分支、不提交、不暂存、不重置、不清理。当前参考 HEAD 29b150f58b3f6d8c6e558a748c12dac3384af173；变化时记录并检查影响，勿回滚。现有宽度研究由 ZCode 独占 src/lei_signal/research/breadth_description*.py、tests/unit/test_breadth_description.py、raw/breadth-b200-first-description-2026-09-17；不得读其未交付结果作结论、不得写入。
先读根 AGENTS/CLAUDE、目录内适用 AGENTS，docs/trading-spec-v1.md、configs/rules.v1.yaml、.claude/skills/macd-reading/SKILL.md、docs/plan-sector-trend-page.md；采用 docs/research/experiment-backtest-principles.md v1.1、ai-execution-contract.md v1.0.1、definition-standard.md v1.1.0、experiment-report-template.md v1.1.0。记录实际版本和 SHA。唯一登记表 definitions.v1.json 只读；完整卡须按 profile 合并语义解析，不新造同职责库。
所有旧结果只读：旧报告声明≠本轮核验，文件存在≠通过验收，数据取得时刻≠历史可得时刻。基本面/消息只叙事，不增加硬过滤。本任务不输出新因子有效性结论，不改规则/生产/UI/OKR/registry/INDEX。
允许 rg、读文件、git只读、对文件做哈希、CSV/JSON结构检查、检查链接；禁止导入有顶层副作用的旧脚本或执行旧main。零联网、零安装、零真实因子或目标重算、零回测、零收益统计；不接触凭据。每项事实附文件/行号或键、SHA、核验范围。最多聚焦8个关键输入文件深入核查，其余做导航；不恢复全部历史。结构核查批次最多3，目录卫生检查最多1；逐次保留命令与退出码，失败计数不重置，额度到即停，交付未完项。不以任务轮次重置预算。
独占输出目录如下；除此之外一律只读。仅写Markdown/CSV/JSON（不开发代码）。目录若已有产物，停止避免覆盖。报告标“待主控复核的提案”，不宣称结案或已采纳。交付前检查自己创建的链接/CSV/JSON，记录读取的关键输入前后hash漂移；漂移暂停受影响结论，其他人的变化不回滚。不得重复创建第二份权威正文；只引用现行规范，给精确拟合并段落。完成后回调主控，不执行自己提出的下一步。

服务研究治理层，不改交易定义。只写 docs/research/proposals/factor-workflow-audit-2026-09-17/。
任务：核对既有 factor_lab、factor_unit/B1、factor_evidence、definitions 入口与已接受的主控报告（优先最新追加节），复用 factor-library-progress-2026-09-16.md，不重新做全库能力盘点。
交付 workflow-map.md：从问题/对象类型及用途→数据资格→固定协议→手算测试→运行→独立复核→证据登记→另行生产许可，每步列权威文档、真实函数/命令入口、需填写字段、产物、未实现项。分清横截面排序IC、单标的时间关系、状态比较、收益解释；不统一强制每项回归。
交付 capability-evidence.csv：definition/data/computation/effectiveness/authorization分开，绑定主控已接受报告和实际代码；未核项不能填通过；现有宽度任务只标进行中。
交付 two-worked-mappings.md：用已封存双均线B1与纯合成横截面示例说明同一流程如何分流，不重新运行，也不把合成例写成真实价值。每例写可执行命令的存在性和参数来源，没实际执行明确标注。
交付 integration-proposal.md：只提最小合并到已有手册/模板/进度总览的位置与差异，不新建总纲。按“已经可用/缺接口/缺证据”排序最有价值的最多3项后续工作，每项给受限任务prompt、依赖和验收，未授权不执行。不编造进度百分比，不因规范写了就宣称自动校验实现。
交付 README.md 与 sources-and-checks.json（版本/hash/命令/限制）。用户可在README一分钟看懂现有成果与距离目标缺什么。

