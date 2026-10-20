# OKR 写入前后差异与读回核验（2026-09-16）

来源：正式本地 API `GET/PATCH /api/upgrades`。写入字段仅 next_action / evidence / links 与进展记录（note）；
未改 title / purpose / parent_id / milestones / status / authorization。

## okr-cd1a0bd5532c  建设LeiSignal自有因子与信号研究体系
- 版本：v2 → v4（PATCH 与 note 各推进）
- status：planned → planned（不变=True）
- authorization.granted：False → False（不变=True）
- milestones：0/0 → 0/0（不变=True）
- `next_action` 差异（+1 行）：
  -合成通用原型v1.2.0已限定收口；三族A阶段盘点已完成主控有限接收。下一步按B0长任务建设收盘价适配和四市场输入来源/日历合同；真实表现计算待冻结协议另行确认，不再把补齐固定14只池作为总前置。
  +B0输入链与B1首个真实描述均已主控收口；证据可靠性v1已主控复核，其R1–R4返修已交付待主控复核。返修复核后，候选（C1第二载体历史描述、宽度历史成员与序列资格盘点、情绪定义/旧证据映射提案、Alphalens-reloaded隔离适配评估）逐项待用户单独授权。首轮工具子目标okr-3fa8363be729待用户确认结案。真实交易采用远未到达，不设总完成百分比。
- `evidence` 差异（+1 行）：
  +2026-09-16进度同步（记录整理，零计算零联网）：B1首个真实历史描述（510300，1,516观察）经主控数字核验与限定收口：成立组后续21区间均值+1.0424%对未成立+0.3408%，全期差+0.7016个百分点，但逐年2正5负；敏感性检查经主控复算：等权年度差−0.66个百分点、连续片段重抽范围跨零，不足以支持稳定优势也未证明无效。方向探索提案v1.2文档收尾通过，后续草案未授权。分层现状与缺口见进度总览factor-library-progress-2026-09-16。
- `links` 差异：原 2 条 → 现 5 条，新增 3 条：
  - 因子库建设进度总览（2026-09-16） → `/library?report=docs%2Fexperiments%2Ffactor-library-progress-2026-09-16.md`
  - B1首个真实描述限定收口 → `/library?report=docs%2Fexperiments%2Fb1-closeout-controller-2026-09-16.md`
  - 证据可靠性主控复核与限定返修 → `/library?report=docs%2Fexperiments%2Ffactor-evidence-controller-review-2026-09-16.md`
- 进展记录：读回含本轮 note 1 条；history 总数 2 → 4

## okr-3fa8363be729  首轮：通用因子计算、检验与策略归因工具
- 版本：v5 → v7（PATCH 与 note 各推进）
- status：approved → approved（不变=True）
- authorization.granted：True → True（不变=True）
- milestones：5/5 → 5/5（不变=True）
- `next_action` 差异（+1 行）：
  -首轮仅供合成研究的v1.2.0原型已主控限定收口并补齐终版源码恢复包；不再待派发。五项交付按原合成范围记录；目标保持原状态，等待用户确认结案，不自动accept。后续真实研究属于独立目标okr-6d9177bc89ff。
  +首轮仅供合成研究的v1.2.0原型已主控限定收口并补齐终版源码恢复包；不再待派发。五项交付按原合成范围记录；目标保持原状态，等待用户确认结案，不自动accept。后续真实研究属于独立目标okr-6d9177bc89ff。2026-09-16补充：因子库整体分层进度与缺口见进度总览factor-library-progress-2026-09-16。
- `evidence` 差异（+1 行）：
  +2026-09-16：本目标无新增执行工作，仅为进度总览同步补充导航链接；授权范围、五项完成标准勾选与待验收状态均不变。
- `links` 差异：原 3 条 → 现 4 条，新增 1 条：
  - 因子库建设进度总览（2026-09-16） → `/library?report=docs%2Fexperiments%2Ffactor-library-progress-2026-09-16.md`
- 进展记录：读回含本轮 note 1 条；history 总数 5 → 7

## okr-6d9177bc89ff  因子独立研究：双均线、宽度与情绪（美A）
- 版本：v3 → v5（PATCH 与 note 各推进）
- status：planned → planned（不变=True）
- authorization.granted：False → False（不变=True）
- milestones：0/4 → 0/4（不变=True）
- `next_action` 差异（+1 行）：
  -交GLM执行docs/superpowers/plans/2026-09-15-factor-unit-close-adapter-glm.md v1.0.0；原目录/分支codex/factor-unit-research-20260915。先处理主控R1–R6、做close-only隔离适配和输入来源裁定；本轮尚未派发，未授权真实运行/联网。
  +B0已按四项修复主控收口；B1首个真实描述已交付并主控限定收口；证据可靠性v1已主控复核，其R1–R4返修已交付待主控复核。下一步：返修复核后，是否推进C1第二载体历史描述、宽度历史成员与序列资格盘点、情绪定义/旧证据映射提案，由用户单独授权；四项完成标准维持未勾选（勾选需先登记执行授权），不自动验收。
- `evidence` 差异（+1 行）：
  +2026-09-16纠正过时状态：本条此前停留在'B0待派发'。实际进展：B0三轮修复后限定收口（factor-unit-four-fixes-controller-2026-09-15：T1–T4关闭，510300离线输入1,558交易日核验完整）；B1首个真实描述（1,516有效观察：成立590/未成立926；成立组均值+1.0424%对未成立+0.3408%，全期差+0.7016个百分点；逐年2正5负）经主控独立重汇总一致并限定收口（b1-closeout-controller-2026-09-16）；敏感性检查（等权年度差−0.66个百分点、63/126天连续片段重抽范围跨零、1,516观察约折合1,536段不重复区间）经主控复算一致，结论为不足以支持稳定优势、未证明无效（factor-evidence-controller-review-2026-09-16）；其R1–R4返修为执行者交付、待主控复核。宽度/情绪仅有A阶段定义与旧证据映射，旧结论转引未复验；无第二载体正式结果。
- `links` 差异：原 3 条 → 现 6 条，新增 3 条：
  - 因子库建设进度总览（2026-09-16） → `/library?report=docs%2Fexperiments%2Ffactor-library-progress-2026-09-16.md`
  - B1首个真实描述限定收口 → `/library?report=docs%2Fexperiments%2Fb1-closeout-controller-2026-09-16.md`
  - 证据可靠性主控复核与限定返修 → `/library?report=docs%2Fexperiments%2Ffactor-evidence-controller-review-2026-09-16.md`
- 进展记录：读回含本轮 note 1 条；history 总数 3 → 5

## okr-4f4157e2957e  因子库后续：外部资源适配与分批接入
- 版本：v7 → v9（PATCH 与 note 各推进）
- status：planned → planned（不变=True）
- authorization.granted：False → False（不变=True）
- milestones：0/4 → 0/4（不变=True）
- `next_action` 差异（+1 行）：
  -按已明确用途选择外部复用：定义参考、计算/诊断工具、基础数据、基准收益、归因模型输入分别核验。双均线B0不强制Alphalens/IC、不安装Qlib、不增加新因子；下一候选与外部采用留待资料资格和研究问题明确后单独授权。
  +按已明确用途选择外部复用：定义参考、计算/诊断工具、基础数据、基准收益、归因模型输入分别核验。方向探索v1.2收尾后维持'暂不整包安装、先定位具体复用需求'：Alphalens-reloaded隔离适配为优先评估候选（未授权）；双均线B0不强制Alphalens/IC、不安装Qlib、不增加新因子；下一候选与外部采用留待资料资格和研究问题明确后单独授权。
- `evidence` 差异（+1 行）：
  +2026-09-16：因子库方向探索提案经主控三轮复核（v1.0→v1.2）文档收尾通过：外部工具证据按工具分项列示（Qlib数学/依赖行为核对、FactorHub历史只读接口调用，均不宣称已接入本地消费者），两份后续接入草案仍是未授权草案；外围另有外部流派融合三轮设计文档（registry登记watch、零回测）作并行候选，与本目标的外部资源适配分属不同线、不混计。四项完成标准不变。
- `links` 差异：原 7 条 → 现 9 条，新增 2 条：
  - 因子库方向探索主控复核（v1.2收尾） → `/library?report=docs%2Fexperiments%2Ffactor-library-direction-controller-review-2026-09-16.md`
  - 因子库建设进度总览（2026-09-16） → `/library?report=docs%2Fexperiments%2Ffactor-library-progress-2026-09-16.md`
- 进展记录：读回含本轮 note 1 条；history 总数 7 → 9

## 核验结论
- 状态/授权/完成标准全部不变：通过
- 每条写入均以写入前 GET 的 version 做冲突检查，未发生覆盖。