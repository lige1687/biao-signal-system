# 可复用的项目经理—执行者交接流程

2026-11-02；任务 `ai-quant-practice-integration-20261101`，沿原任务第三阶段。

**已把前次选中的两项思路接入现有技能和LeiSignal：带来源的研究上下文交接、沿原任务的回调与恢复。通用脚本及本地回放已验证；真实冷上下文AI接收演练因执行模型额度中断，尚未完成。** 当前可复用本地工具和工作要求，不能据此宣称代理已经普遍遵守、节省了费用，或提高了策略收益。

本阶段只回答交接结构与本地恢复问题，未重新搜索旧来源、运行金融实验或安装DeepSeek框架。真实AI接收验证保留恢复点；不存在后台继续。

## 对系统的具体改变

主控保留问题、权限、预算和验收；执行者收到目标与材料入口，实际读取后工作。主控向用户交付结果和需要决定的事项；完整上下文、过程记录和证据按需查看。

| 已有方式／基准 | 本次增量 | 实际证据与范围 | 结论 |
|---|---|---|---|
| 合同预检已有，历史主要靠主控在提示中转述 | 原准备入口可生成交接上下文；保留历史、未知、负结论和原合同，并核来源字节 | 原已保存的人工研究记录可生成有效packet；原人工预算3/4、剩余1和“资料已观察”声明保留，当前金融实验授权仍为0 | 结构可用；旧余额不是本次授权 |
| 来源有效不代表彼此属于同一任务 | packet与上下文内合同须同一路径、版本、选择位置和内容；显式合同身份须匹配 | 独审发现旧合同B上下文可配新合同A；3个失败反例复现后修正 | 阻断该错配，不能证明合同内容真实 |
| 回调和恢复主要靠文字约定 | 稳定任务/阶段/尝试身份、绑定状态路径、实际接收回执、结果引用、独立复核 | 本地独立进程回放完成预留→派发记录→CLI接收→回调→复核→下一阶段预留 | 记录链可重放；派发记录本身不是平台执行证明 |
| 重复消息需人工辨认 | 同附件内重复事件、回调、下一阶段预留不增加记录；换状态路径拒绝 | 重复回调和下一阶段事件返回duplicate且状态字节未变；另一附件路径拒绝 | 仅绑定附件内去重，不保证跨新packet或外部工具只执行一次 |
| 上下文过长时可能只看摘要 | 必需来源指针与截断状态显式保留，无法复原关键来源则阻塞 | 既有2026-10-24研究的review已截断，适配器保留原内容并阻塞；未重跑、未删减历史凑通过 | 缺件不能当成无问题；大上下文仍需有界组织 |
| “收到材料”与“理解限制”容易混淆 | 结构接收和研究判断分开 | 227项项目回归＋50项通用检查通过；真实新AI接收没有派发成功记录 | 本地验证通过；AI行为验收暂停 |

非量化的人工parser任务也完成同一通用脚本回放，说明核心没有LeiSignal导入依赖。这只验证接口可复用，不代表其他项目已采用。

## 共用入口

- 用户级 `codex-delegate/SKILL.md`：按场景采用保存交接；简单单步任务保留原合同预检。
- 用户级 `codex-delegate/references/handoff-workflow.md`：唯一详细流程、packet/event格式、命令和恢复规则。
- 用户级 `scripts/handoff.py`：prepare / verify / receive / transition / inspect；不启动代理、不执行任意命令。
- 原 `scripts/dry_run.py`：可选 `--root` 与 `--handoff-file`；合同和packet必须对应同一实际文件字节，旧用法保持。
- LeiSignal原 `preparation`：可选 `--handoff-contract`，新增 `delegation_context`；独立模块 `lei_signal.research.delegation_context` 可检查已保存准备结果。准确用法见[研究工作流](../research/research-workflow-usage.md#可复用的任务交接与恢复2026-11-02)。项目研究和委派技能均已链接此入口。

恢复沿原packet和绑定附件，先检查真实worker及产物。如果只记录了预留而没有派发回执，不能假定从未执行并立即重派；本次冷代理案例另有明确事实记录：主控尚未调用spawn，审查助手先返回额度错误。

## 验证、代价和未验证范围

- 旧项目回归与新适配、准备入口共227项通过；通用packet/状态/预检共50项通过。局部Ruff及仓库归置结果见最终回执。测试包含来源漂移、路径、锁、事件顺序、跨合同错配、重复回调、必需来源缺失、未知保留、指针类型和非有限JSON等反例；失败产物全部保留。
- `local-replay-01`是合成本地进程演练，结果中的“派发”是fixture事件；真实工具接收通过CLI完成，**没有AI模型执行或金融计算**。
- 原研究和旧结果只读。接收回执不认证理解，SHA不认证事实，accepted不认证科学有效或预算许可。新状态附件不替代原研究账本。
- Unix `fcntl`协作锁及原子保存仅保护本地附件；不是OS沙箱，也不抵御任意恶意并发文件改动。每文件1 MiB、JSON列表256项、上下文来源100项、嵌套64层；超过限制拒绝，不静默压缩历史。
- 独立设计审查完成；独立实现审查在提出合同错配后触发provider额度上限。主控复现并修正，完成剩余代码与产物核查；不冒称第二轮独立模型审查完成。
- 本阶段研究来源请求0，沿原累计23；金融实验、模型API、行情采集、安装、付费数据和交易均0。协作代理实际token/费用未知；无固定任务效率对照，节时、费用和收益增量均未评价。小代码/说明及保留测试夹具体积见验收manifest，未删除历史资料。

## 当前决定与恢复

采用现有技能中的通用工具和流程说明，保留项目适配；不引入另一套主控平台或后台服务。工程实现及本地验证已交付，**真实冷代理行为验收暂停**，不能把这项暂停写成整套流程已经端到端验收。

恢复入口为[checkpoint](raw/reusable-agent-handoff-2026-11-02/checkpoint.json)：原provider可用时，先核packet/source/state和实际worker，再按已有合同完成一次只读接收，验证执行者能复述旧负结论、累计预算和已看历史且不启动新实验。保留同任务、同合同和原预留，不重新跑旧金融研究、不更换模型或另起重复任务。若需要更换执行模型，应按既有授权规则处理。

## 证据索引

- [原借鉴评估](superagent-quant-adoption-review-2026-11-02.md)：本轮沿用已读的[DeepSeek原型README](https://github.com/deepseek-ai/dsh-superagent-prototype/blob/main/README.md)、[理念](https://github.com/deepseek-ai/dsh-superagent-prototype/blob/main/docs/000-philosophy.md)、[执行](https://github.com/deepseek-ai/dsh-superagent-prototype/blob/main/docs/003-execution.md)与[架构](https://github.com/deepseek-ai/dsh-superagent-prototype/blob/main/docs/007-architecture.md)；研究原型不等于官方产品或全部设计已实现。
- [初始范围](raw/reusable-agent-handoff-2026-11-02/brief.json)、[接口](raw/reusable-agent-handoff-2026-11-02/interface.md)、[审查增补](raw/reusable-agent-handoff-2026-11-02/interface-addendum.md)、[审查与写者移交](raw/reusable-agent-handoff-2026-11-02/review-and-ownership.json)。
- [最终项目检查](raw/reusable-agent-handoff-2026-11-02/final-project-tests.json)、[最终通用检查](raw/reusable-agent-handoff-2026-11-02/final-global-tests.json)、[本地回放](raw/reusable-agent-handoff-2026-11-02/local-replay-01/summary.json)、[可重复回放脚本](raw/reusable-agent-handoff-2026-11-02/replay_local.py)。
- [旧研究截断反例](raw/reusable-agent-handoff-2026-11-02/real-truncation-blocked.json)、[人工旧研究交接packet](raw/reusable-agent-handoff-2026-11-02/cold-packet.json)、[实际预留](raw/reusable-agent-handoff-2026-11-02/cold-state.json)。
- [最终验收与范围](raw/reusable-agent-handoff-2026-11-02/acceptance.json)、[代码和说明指纹](raw/reusable-agent-handoff-2026-11-02/source-manifest.json)。初始备份在同目录`before/`，最终局部快照在`after/`；所有红绿测试在原任务`phase3/`与本目录，不覆盖前两阶段。

源码、技能和报告仍为本地成果；仅任务协调元数据同步到`coordination/lei`，不以旧HEAD声称远端可复现本轮代码。
