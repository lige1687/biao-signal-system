# Ark Agent执行书：跨标的名称绑定修复与合入验证

用户本轮原话：“继续下一轮，分派给arkagent吧”。主控选择Ark的原因：用户明确指定，且本任务涉及真实路由的对象优先级、已验收候选与并行运行代码的协调。策略/架构和最终采用判断由主控保留。

工作区唯一写入位置：/Users/yongbiaoli/lei-agent-runtime-adoption-20260917，分支codex/agent-runtime-adoption-20260917，产品冻结基线71070885。允许在此分支按阶段提交任务代码、测试和报告，禁止新建/切换用户分支或改main。运行目录 /Users/yongbiaoli/Desktop/lei-signal-lab 只读，采集时HEAD7f8c38c3且有并行因子文档/报告工作；来源main目录 /Users/yongbiaoli/lei-agent-main-consolidation-20260915 只读，f8638b9f。三个目录是同仓库worktree，不可整仓合并/同步。

开工先读本目录AGENTS.md/CLAUDE.md及四份必读策略文档（trading-spec-v1、rules.v1、macd-reading、plan-sector-trend-page）。本次服务于解释展示层：名称、资料、阶段、失效位须属于实际讨论对象；不改交易定义或阈值。UI只改web，冻结src/lei_signal/ui。

先读已核实缺陷（不要重复大量历史研究）：运行目录 docs/experiments/agent-symbol-binding-review-2026-09-17.md 和对应raw。它证实71070885先问通信ETF再说沪深300/上证指数时实际resolved仍515880；已有DASHBOARD_INDICES未纳入目录。controller-recheck-v2证据在 /Users/yongbiaoli/.codex/zcode-delegate/briefs/symbol-binding-recheck-2026-09-17/controller-recheck-v2/；原脚本只有核查功能，不能以exit0宣称产品正常。用当前候选真实路由重现失败后修。先看已有精确目录与解析优先级，不扩展模糊匹配。

S1目标：复用DASHBOARD_INDICES准确名称/代码补齐解析与显示名。明确新名称/代码优先于旧selected/page/session；没有新对象的“那失效位呢”继续继承。normal/stream两条chat入口都验证落库、resolved、资料卡/引用对象一致，缺新对象行情时不附旧卡。沪深300、上证指数、通信板块/通信ETF、科创50板块/科创板整体原语义保留；双标的比较仅保留既有澄清边界，本轮不发明比较引擎。前端必须用后端真实对象，不在前端猜信号。允许最小必要解析/目录/显示名修改，意图漂移需上报。

S2仅在主控S1通过后：按届时运行实态复算原24项+7依赖及S1新增影响文件，保留其他agent改动；在当前隔离候选刷新定向采用差异与 before/after 清单，旧raw失败记录不可覆盖，旧通过代码不重复重构。真实浏览器若可用，隔离端口和临时库下验证工作台/控制台切对象、名称与资料一致；若不可用，明确缺口，不假装HTTP等于浏览器。不得部署/重启/修改运行工作区，实际合入由主控在阶段验收后执行。

原采用包和验收：docs/experiments/agent-runtime-adoption-final-review-2026-09-17.md，raw/...candidate.../adoption-package；安装/回退保护已验收，必须保持，不另造部署框架。恢复时后续编辑/备份损坏拒绝、权限故障非零；14个独立工具场景原证据可复用，只在受改动时补测。

测试环境：/opt/homebrew/bin/python3.11、PYTHONPATH=src；本机Chrome/已有依赖可以用，不下载安装。脚手架必须进程级禁止外部DNS/连接，替换资料提供者并使用合成行情、模拟模型、临时数据库；不能复制.env或凭据，不能调用真实模型、行情预热或读取个人交易库。原test_s13会外呼，不裸跑全量。保留已知数值校验器xfail，不扩大修真实性算法。

报告按日期落docs/experiments并有大白话结论、ARCHIVE、registry现有类别、INDEX导航；过程文档在docs/archive/handoffs-plans，本轮raw独立目录。运行目录既有registry/INDEX脏改只读。每阶段返回：实际修改、命令与结果、证据位置、未完成与是否可合入。系统待升级台账由主控更新，不改种子或自行完成方向目标。主控复核后才下一阶段；只完成当前阶段。
