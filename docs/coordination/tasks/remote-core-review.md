# 远端核心交付验收与转黑趋势比较

- task-id：remote-core-review（稳定唯一；旧入口 docs/progress/remote-core-review.md、docs/ops/work-progress/remote-core-review.md 一对一映射）。
- 负责人：本远端核心验收会话的主负责人 /root，MacBook-Air-126.local；继续负责，未移交。其他同名 /root 会话不表示同一任务。
- 更新时间：2026-10-03T14:07:08.806905+08:00，Asia/Shanghai。
- 状态：active（有界资格准备）；独立验收 completed；正式效果 blocked、尚未启动；返修差异验收等待交付。
- 仓库：https://github.com/lige1687/biao-signal-system ；工作分支 codex/remote-core-acceptance-20261002。
- 基础完整 commit：639ad8dbd3d2aa72f824b626b86149c466c132a4；原远端 Opus 5.5 交付4155b4db7ccd14674eff2e29dfaf102d2ac3e5f9。
- 最近已推送成果完整 commit：b149a02db84522937281a09df72001b046e7a03e（已核 ls-remote 一致）；实质研究前检查0e4f3f4213ecb60a2d27d5147e8b440237946311。
- 实际读取规则：coordination/lei@b172008890b39e912c8f1d0cfb9125d1e414a97f 的 COORDINATION.md 1.0；本轮推前 fetch 未变化。适用本工作分支 AGENTS.md、docs/research/current-standards.json 和原冻结版本；不移植旧实验到新合同。

## 原始目标、最新要求和验收

独立核实基于639ad8d的远端核心T2—T10＋模块A机会母体审计，给接受程度和返修，不替用户猜策略含义、不重做全部、不改生产/规则账本/定义登记/旧封存。用户后来明确：回调条件、转黑是否结束趋势、横盘失效及小时资料的价值由量化数据判断，不让用户凭感觉选赢家；正式规则采用、付费资料和数据外传仍须对应授权。

验收问题已回答，整体有条件接受；下一阶段仅把“转黑是否重置同一趋势”变成只改变一个条件、相同当时可知机会的比较。实际业务增量定义为动作/日期/风险依据与费用后表现相对原基准及已有简单信息是否改善。新效果、费用后账户收益和线上收益均未测量；脚本通过不代表策略有效。2026-10-03最新要求是同步和统一协作，原负责人继续，不是接管或结束。

## 已完成、准确成果入口与证据

以下路径均在最近成果提交中，链接使用准确提交；不依赖本机在线。

- [验收报告](https://github.com/lige1687/biao-signal-system/blob/b149a02db84522937281a09df72001b046e7a03e/docs/experiments/remote-astra-core-acceptance-2026-10-02.md)：16项必须脚本完成；T2合成9/9、生产读法239/239与188/188；逐日按原算法504/504、364条未先离开触碰带、11笔中9笔属于该类。报告登记为方法论与验证，原验收提交30dca305eeca7172359b427d51c9c0a3008812d0。
- [验收原证据及返修提示词](https://github.com/lige1687/biao-signal-system/tree/b149a02db84522937281a09df72001b046e7a03e/docs/experiments/raw/remote-astra-core-acceptance-2026-10-02)：T5两反例、T6机械问题成立；T9重算后可绕过、T10关键资料缺失仍准入；R1—R8返修尚未确认派发或新提交。
- [历史完整材料包](https://github.com/lige1687/biao-signal-system/tree/73592f5bc0d6d2e0d15b96809364600f44a8b8b2/docs/archive/handoffs-plans/remote-core-handoff-2026-10-03)：原件、权威来源、指纹、环境、预算、失败、恢复命令和缺口均已交。只在固定73592f5b核原清单；原包“交接后停止”的历史计划已被最新人类要求撤销，不改旧锁。
- 最低恢复：独立目录和新Python环境读取3273行真实输入、180行特征正常、1项合成规则检查与2项单元测试通过；仅macOS arm64。两次恢复失败保留；完整研究资格检查 blocked，不能当完整云端恢复。见包内 VALIDATION.md / validation-results.json。
- [新版本检查和单开关草案](https://github.com/lige1687/biao-signal-system/tree/0e4f3f4213ecb60a2d27d5147e8b440237946311/docs/experiments/raw/remote-core-rule-next-2026-10-03)：core-sync@d7da6cb0f9c127606b6faa572fabc9ee93f104f7的7个相关文件与旧交付逐字节相同，56条定义证据仍缺失。两边仅episode_reset_on_black不同；共同机会、未知/未触发、当时构造、旧实现缺陷和停止条件均写入草案，不是正式执行合同。
- [阶段历史和本分支协作说明](https://github.com/lige1687/biao-signal-system/blob/b149a02db84522937281a09df72001b046e7a03e/docs/ops/work-progress/remote-core-review.md)：本阶段仅追加AGENTS协作入口、两份旧进度入口映射；原AGENTS原文完整保留。

## 正在做、下一步及限定文件范围

正在做：black-reset单问题研究资格与合同准备；只读 lifecycle_ref.py 的 episode_reset_on_black、first_ma_pullback.py 结束/取消行为和现行研究定义/输入要求。无正式适配器、无新效果计算；R1—R8差异核验责任保留，当前没有可验的新返修提交。

预计仅触及本任务 docs/experiments/raw/remote-core-rule-next-2026-10-03/、本工作分支自己的两份进度、此任务记录。登记表/共享workflow/生产代码只读，不自行修复或整目录占用。

下一步：先读取最新协调；只读核准确对象与研究工具绑定、当前两ETF日线是否能支持该窄问题。原始证据负责人提供正确版本引用、正式对象/工具负责人交付准确绑定后，才冻结预算与必要比较。不要把一个旧登记中的无关缺项自动泛化成所有独立工作必须停止，也不能绕过正式工具的资格检查。完整A3/小时、横盘效果和生产修复未启动、不认领全部未来方向。

## 冲突核对与避让

本轮读 b1720088 下全部已登记任务：lei-coordination-bootstrap completed，technical-factor-sequence active（抵扣路径形状、只读输入资格；C01/Q01已封存）。与本任务黑色阶段重置/返修验收没有已登记同题冲突。共享研究工具均只读；将来需修改先明确实现者与核验者。未登记任务状态未知，不能凭缺记录抢占。

其他AI暂避同时改写本任务记录、两份旧进度、新black-reset草案/输出；避免重做T2—T10独立验收及504逐日审计。任何重叠先协商，实现与独立核验可分工；此记录不是排他锁。F1完成度、F2事件记录、T1历史目标的旧负责线不被本任务接管；其当前身份仍以最新登记为准。

## 阻塞、运行中工作与预算

- 正式效果 blocked：现行Git登记56条引用缺失、black-reset准确注册对象版本及正式工具绑定未交付。不能删除旧引用或从共享脏代码偷取绑定。解除：负责方提供/修正有版本证据，确认研究专用定义与共同基线，不改变策略原文。
- 完整小时问题缺小时数据及六ETF现行完整资格包；仅阻塞依赖步骤，不推断所有地方都无小时数据。第二篇指定PDF完整指纹/页码、远端返修任务ID、新分支和累计预算未确认。
- 本地无本任务后台效果计算、无活跃checkpoint或输出锁；未新起进程、未杀任何进程。历史母体worker77981—77984已结束；远端任务状态未知，不能依据复制文件推断进程迁移。
- 累计：16脚本记录529.246秒；旧逐日中断2326.799秒，后续并行墙钟728.693秒/worker累计2771.911秒（不重复相加）。远端原24小时/费用实际已用与余额未知；不因500元历史口述或换设备重置。
- 新效果0次、模型拟合0次、付费采购0、封存实验重跑0；此前新版本检查1批。新效果预算尚未登记，本轮仅协作文档/Git，不产生付费计算。
- 本机磁盘曾导致完整恢复失败；不清理或删除资料。此协调目录最小检出，不依赖本机持续在线。

## 数据、指纹与仅本地材料

权威原件Git只读快照 docs/research/strategy-source-snapshots/2026-09-30/；体系SHA256 df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20，实现85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903，2026-10-03实测未变化。历史原输入/版本/大小/SHA/字段/恢复详见固定handoff manifest.json、ARTIFACTS.md、data-fields.json。逐日完整摘要SHA f3c53471fa97d88fc8470837f141449ed44a7ddb062690eeeaf966a1b42ba4a8。

本任务安全成果均在上述工作提交；本次提交后隔离任务工作区无未提交任务成果。共享源分支codex/factor-unit-research-20260915@18e64fa632dba5dbad0e5fcae09b4ccc75f119a9的其他任务脏改动仍仅本地、远端不可复现，不认作本任务、不清理、不顺带推送。没有交付新大包、活跃数据库、密钥、登录态或私人账户。模型权重/tokenizer不适用（没有训练）；缺少完整当时构造列表不能拿旧摘要代替。

## 本轮实际检查与封存限制

通过：remote目标一致；规则及两份任务读回；工作分支准确SHA已核；AGENTS旧文完整保留；仅3份本任务文档准确暂存；敏感形态扫描未命中；diff --check及工作分支目录卫生全绿。两分支均无 .github/workflows，工作目录无活动Git hooks；未发现受版本管理的生产/付费触发器，外部平台集成未知，本轮不调用部署/计算。未运行：任何大实验、训练、完整回测、生产、Linux/Windows复现（文档同步不要求重跑）。

不要重复16验收/504母体、A01/A02/A03、旧绿色黑色研究、旧48账户、技术顺序线C01/Q01和已结案同用途问题。T7 30/13仅资格计数，不是逐日收益；T6少8.5%—11%仍是假设估算；T9/T10演练不代表真实准入；T2整组研究生命周期开关未批准为正式默认。只有新证据、适用前提变化、明确纠错或人类要求才重开，并记录理由。

## 下次恢复与本版变化

下次先fetch coordination/lei，读此文件和新增相关任务；核准确成果commit、输入SHA与当前绑定，再继续单问题资格步骤。历史handoff按73592f5b核锁，最新所有权以此记录及最新用户指令为准。权限不会随旧包自动继承。

本版首次接入统一协作，保持稳定remote-core-review身份、完整版本/证据、窄范围/未登记风险及失败预算；没有接管、关闭原任务或启动重复计算。本任务记录自身完整commit用git log -1 --format=%H -- docs/coordination/tasks/remote-core-review.md定位，不无限补交自指SHA。推后须读回核验后才称已同步。
