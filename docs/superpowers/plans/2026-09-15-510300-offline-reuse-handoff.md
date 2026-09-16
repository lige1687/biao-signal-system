# 510300 离线输入复用与 B1 规格交接 Implementation Plan

> **For agentic workers:** 使用 executing-plans 按任务执行。用户禁止暂存/提交/切分支，优先于技能通用建议。不派生新工作树，不并行写共享文件。

**Goal:** 不再抓同一份行情，将已核原件做成可恢复输入包，并给出首轮双均线真实历史描述的完整待批规格。

**Architecture:** 只做原始行情的确定性拼接和证据封装；不新增因子算法，不修改既有真实资料拒绝行为。B1运行规格只写文档，不执行真实状态或目标计算。

**Tech Stack:** 现有 Python、标准库 CSV/JSON/SHA-256、既有 TradingCalendar；零安装、零联网。

## Global Constraints

- 地点 `/Users/yongbiaoli/Desktop/lei-signal-lab`；原分支 `codex/factor-unit-research-20260915`；HEAD `8ba16576b75e605aa1b0d0902568c760c4b99095`。身份不同暂停，不自行切换。
- 本任务回应用户“继续推进这两个的剩余工作”；不包含新真实因子统计、账户/生产、OKR、网络或新依赖。执行者交付声明不代表用户或主控认可。
- 先读 AGENTS、研究原则v1.1、定义标准v1.1.0、执行合同v1.0.1、模板v1.1.0、交易规格以及主控 `docs/experiments/factor-unit-four-fixes-controller-2026-09-15.md`。
- 对象仅 `candidate:lei.dual_ma.bull_state@draft-1`，卡在 `docs/experiments/raw/factor-research-workbench-v1-2026-09-14/candidate-card-dual-ma-bull-state-draft-1.md`；不是新建正式对象。列出卡与规范实际版本/完整哈希。
- 仅510300。目标拟为 vendor_adjusted_price_change，明确它与旧 total_return_wealth 不同，不沿用旧目标名。无生产授权、无历史可得性认证。
- 保护close_state、factor_lab、生产函数/规则、所有既有raw与协议、definitions.v1.json、旧缓存；禁止改study_contract/state_description/旧CLI以提前放行。
- 只新增 `docs/experiments/raw/510300-offline-reuse-2026-09-15/` 和 `docs/experiments/510300-offline-reuse-2026-09-15.md`；原四项交付报告仅追加流程说明。registry/INDEX由主控统一登记，本执行者不写。

## Task 0：身份、封存与文案收尾

- [ ] 记录branch/HEAD/git status，冻结本任务读取的代码/原件/规范哈希；不可把HEAD当作脏工作区源码身份。
- [ ] 原四项报告追加：首次成功合成包曾删除重建；旧原件可恢复与否；纠错额度不授予删除成功证据权限。不重跑补历史。
- [ ] 新建任务协议v1.0.0，排他写入。任何成功/失败/临时完整CLI运行编号均留痕，绝不删除再用同一编号。

## Task 1：独立可测的离线拼接

**Files:** 在新raw目录新增 `assemble.py`、`test_assemble.py`，不得改src或旧脚本。

**Interface:** `assemble(entries, base_dir, sessions) -> (rows, audit)`。entries来自第三轮fetch-manifest中symbol=sh510300的七条记录；rows按日期排序，输出日期及原始开/收/高/低/量字符串，禁止舍入或修改价格；audit保存重复/冲突/缺日/非交易日与输入身份。

- [ ] 先写合成单测：两个窗口同一天同值可去重；同日不同收盘拒绝；文件篡改拒绝；缺qfqday拒绝且不回退day；非正/NaN收盘拒绝；缺交易日拒绝；多出日隔离并拒绝完整资格。独立期望直接写固定行，不引用函数输出。
- [ ] 最小实现只用CSV/JSON/哈希；禁止计算任何真实收益或因子。输入原件路径与哈希以主控 `raw/factor-unit-four-fixes-controller-2026-09-15/verification.json` 的 reuse.source_files 为固定清单；与原fetch-manifest逐条一致才继续。
- [ ] 运行 `python3 -m pytest docs/experiments/raw/510300-offline-reuse-2026-09-15/test_assemble.py -q`；记录修前/后结果，不要求人为制造格式任务的失败。

## Task 2：一份可恢复输入包

- [ ] 正式拼装最多1次；允许修正后使用新编号再1次。超出需交回，不论失败还是/tmp正式重放都计数。单测内纯合成不计真实拼装。
- [ ] 输入覆盖固定2019-09-02至2026-02-03，日历SHA `aa43736b67bbcee04fc21eedf8d510b184b764adf138456c8bce93a3155eb6c1`；检查期望1558行只是主控交叉证据，完整性须从日历逐日推导，不靠行数放行。
- [ ] 输出 `run-01/prices.csv`、quality.json、manifest.json、原始响应七份、fetch-manifest原字节、日历原字节、协议原字节、assemble.py原字节。manifest最后写，包内文件集合/哈希双向一致。
- [ ] 声明 vendor_qfq、原始提取字段qfqday、人民币报价、retrieved_at继承原件清单、assembled_at为当前；历史available_at=null；精确复权anchor unknown；`data_mode=real`、`historical_reconstruction_only=true`，不能称total_return或PIT verified。
- [ ] 新输入不升级旧缓存。来源裁定另作本次包内 `source-decision.csv`，标记“原件可追溯、仅供待批供应商调整价历史描述”，不自行填price_basis_verified求放行。
- [ ] 临时目录恢复一次，只读验证原字节和完整依赖；不调用真实研究入口。

## Task 3：完整 B1 草案，不提前实现或运行

新增包目录中的 `b1-spec.md` 与 `b1-contract-draft.json`，JSON是待实现/待冻结规格，不声称已有消费者。

- [ ] 对象和公式完全沿用卡/close_state，lookback20、种子20日、EMA系数2/21，预热20个交易日；第一评价日2019-10-08、末日2025-12-31。输入从2019-09-02开始，不额外用2013历史改变EMA初始条件。
- [ ] 主目标 `P_vendor(t+22)/P_vendor(t+1)-1`；辅助目标 `min(0,min(P_vendor(s)/P_vendor(t+1)-1))`，s为t+1..t+22所有交易日。声明仅收盘路径，不是盘中最大损失或账户回撤。
- [ ] sparse_anchor_session=2019-10-08、step=23；禁止看结果后挪锚点。标签截止按CN逐日15:00+08，研究截断建议固定2026-02-03T15:00:00+08:00，但与2026-09-08才取回快照的知识时点不同：这是事后历史描述，绝不声称在2月已经拥有此快照。
- [ ] 真假状态主比较使用共同合法集合；未知状态单列；辅助目标有效数量另列；逐年只是固定分组，不能挑最好年份；不同日期未来区间重叠，不当成独立成功次数。
- [ ] 输出拟包含状态覆盖、真假状态后目标均值/中位数/上涨比例、辅助下行、固定稀疏视角及缺失对账；不输出策略年化、显著性结论、IC、alpha或生产建议。
- [ ] 列清当前阻断：旧describe_states只支持synthetic且结果硬标synthetic、study_contract真实目标全拒绝。提出独立研究适配的最小文件范围和反例要求，不能伪造synthetic绕过。实际开发/真实正式运行由主控另行裁决。

## Task 4：交付与停止

- [ ] 仅本任务测试与ruff，相关回归最多1次；不跑全仓库或真实统计。输出完整命令、退出码、实际次数及日志。
- [ ] 报告大白话回答：有多少输入、来自哪里、能研究什么/不能证明什么、下一步还缺哪个消费者。保护哈希逐项复算。
- [ ] 执行报告需有“执行者声明 / 主控待核 / 待用户决定”三栏。报告登记建议随交接提交，不修改共享导航。
- [ ] 完成即停：无联网、无真实因子/目标计算、无提交。交回给主控审输入包和B1草案后，再决定一次真实历史描述的开发与运行，不因输入完整自动获批。
