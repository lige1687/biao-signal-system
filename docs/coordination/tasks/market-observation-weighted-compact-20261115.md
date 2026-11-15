# 市场观察本地正式版部署及建议去重（当前阶段）

- task-id: market-observation-weighted-compact-20261115
- owner: Codex当前chat 01a1de33-42bb-7ce3-b34a-241079e8452d（/root）
- status: active
- scope_released: false
- updated_at: 2026-11-15T23:01:18.787822+08:00
- checked_coordination_sha: 398be95ef16967c4e9946516c5c84b2d1818edcc
- 已读task-id: 自身、research-dispatch-controller、institutional-macro-gap-20261114、douyin-yangtuoshen-20261113、market-observation-panel-v2-20261109、cross-market-risk-context-20261102、microstructure-observations-20261108、trae-observation-integration-20261108、trae-sector-observation-20261108；已读COORDINATION、AGENTS、web/AGENTS。
- 本轮授权: 用户明确要求“改动在本地没部署，感觉你部署了我看看”，并要求查所说盈利完整历史、有可用数据先做；另贴Quant建议要求去重借鉴。本阶段授权本机现有看板正式版更新，不是公网发布或策略采用。
- 基线: codex/factor-unit-research-20260915@18e64fa632dba5dbad0e5fcae09b4ccc75f119a9，共享dirty原样保留；源代码仍未提交，只有协调元数据push。前阶段10文件after-manifest指纹重核一致；当前8000静态版为11-09旧build，5173为当前开发版。
- 当前唯一共享写范围: web/dist/**（仅root执行构建产物复制及入口切换；原部署文件完整备份，旧哈希assets保留）；不修改其他owner的源码/任务、服务脚本、API、策略/参数、数据原件或默认Git index。只读代理无共享写范围。
- 冲突决定: panel-v2与microstructure旧记录仍active，本文不占用其源文件、不宣告其完成；只读取现有快照编译，构建前后核全部输入指纹防并发漂移。其余邻接已有释放记录。本轮无第二写者、无源码覆盖、无需重启backend。
- 验收: 备份/读回旧dist清单；当前生产构建和相关检查；复制时assets与资料先就位、index最后原子替换；HTTP8000入口新hash、所引assets、两份JSON逐字一致和API健康；桌面实际页面展开加权/社融、检查既有自选入口。当前数据资格沿前阶段，不把部署当预测验证。
- 问题分工: evidence_review只读查既存盈利文件；quant_advice_review只读现有模块与必要原始方法资料；root独立复核及部署。若要新增产品再登记准确范围，现阶段不新增技术阈值/交易动作。
- 存储/代价: 22:57固定外盘identity_ok=true、available=true、约468GB free；内盘约2.5GB足够本轮预计小记录<5MiB、正式dist新增<100MiB。外盘部署备份/构建预计<250MiB，均核登记新结果目录。无删除、强推、付费、交易、新收益回测、追加行情或重置旧预算。
- 产物: /Users/yongbiaoli/Documents/ChatGPT/在做中/research-notes/leisignal-market-observation-review-2026-11-15/gemini-followup/deployment-20261115；外盘待核后记录精确部署目录。上阶段原始证据、失败和封存结论保留下文历史。

## 已封存前阶段记录（下列“未部署”等表述对应前阶段）

# 市场观察：Gemini审阅与紧凑/加权展示

- task-id: market-observation-weighted-compact-20261115
- owner: Codex当前chat 01a1de33-42bb-7ce3-b34a-241079e8452d（/root）
- status: completed
- scope_released: true
- updated_at: 2026-11-15T16:46:15.892739+08:00
- checked_coordination_sha: c7cc0202ae58abc2a5557735e9109f05e2c199c4
- 已读task-id: institutional-macro-gap-20261114、douyin-yangtuoshen-20261113；已读COORDINATION.md及AGENTS.md、web/AGENTS.md。
- 冲突决定: 原institutional-macro已明确scope_released=true；douyin最新阶段仅研究文档且已释放。不修改这些原任务记录、冻结研究及其预算。此为用户当前明确委托的本地展示后续，独立小记录在仓外，仅本地产品改动。
- 工作分支: codex/factor-unit-research-20260915；基础完整commit 18e64fa632dba5dbad0e5fcae09b4ccc75f119a9；当前大量未提交改动，逐文件备份后只修改清单路径，不reset/clean/stash。不提交产品、不部署，最近成果提交不适用（仅本地）。
- 用户目标/授权: 与Gemini 4 Argon最高思考讨论既有五方向；认可后落实紧凑入口及加权宽度并查看效果；核实盈利数据真实能力。用户另明确窗口/模式可自行调整。无新收益回测、生产、交易、付费、调参授权。
- 当前已完成: 原始东方财富142条及字段/指纹复核，50/50与92/100覆盖；股票级历史修正广度仍未知。原10-30六组权重宽度算术与现有数量快照核对一致。Gemini模型菜单4 Argon已选、思考低/中/高中高超级详尽已选，本轮问题已提交，待有效正文；不把提交当认可。
- 用途/基线: 现有数量宽度解释参与股票比例；增加同日有效权重对照解释参与者的指数权重。社融不同年度余额差额同比仅作月度宏观背景；盈利保持字段覆盖与修正未知。观察价值和收益增量分开，未测交易效果不补造。
- 拟唯一产品写范围（Gemini认可后执行；root总控，代理按单文件合同不重叠）:
  - web/src/components/market-style/StarBreadthSnapshot.tsx
  - web/src/components/market-style/StarWeightedBreadthSnapshot.tsx
  - web/src/components/market-style/star-breadth.css
  - web/public/research/star-weighted-breadth-20261030.json
  - web/src/components/market-style/SocialFinancingSnapshot.tsx
  - web/src/components/market-style/social-financing.css
  - web/public/research/social-financing-yoy-20261115.json
  - web/src/components/market-observation-alerts/CompactOverview.tsx
  - web/src/components/market-observation-alerts/compact-overview.css
  - web/src/components/market-style/observation-snapshots.test.mjs
- 验收: 原数据与新展示逐项数值/日期/分母一致；10-30权重不套11-13；单日不画连续权重图；社融缺月不补0、政府债以外不称民营信用；当前EPS覆盖不称盈利修正。相关数据资格测试、TS检查与不覆盖dist的构建；只做桌面页面实际检查，保留自选/完整观察入口。
- 已用来源/预算: 原institutional-macro public-138、早先6/6两阶段、长桥2和个股150/150保持；本chat前轮文稿核查额外6来源保持。本阶段新增金融来源0、行情0、收益实验0。Gemini原生界面操作失败与恢复留仓外stage-state.json，不引入后台任务。
- 原始证据: /Volumes/win+mac通用/LeiSignal-新实验结果/institutional-macro-gap-20261114/source-continuation-20261115-101905-a691db69（只读）。新小记录/合同/报告: /Users/yongbiaoli/Documents/ChatGPT/在做中/research-notes/leisignal-market-observation-review-2026-11-15/gemini-followup。
- 待完成: 取得Gemini完整新答并由主控复核→把本记录改active并核远端→备份准确文件并实现最小展示→相关验证与桌面查看→交付并释放范围。Gemini若有实质异议先核证，不照单执行；缺数据的项保留未知，不扩展收益研究。

## 完成与释放

- status: completed；scope_released: true。已完成用户当前授权的Gemini讨论、真实数据能力核查、最小本地展示与桌面验收；不宣称原institutional-macro其他未完成研究已完成。
- Gemini4 Argon/高（最高可选）两轮有效完整回复；第二轮明确认可收窄范围。最终三入口、盈利下钻、六组单日权重双分母与社融1—10月小图一致。
- 原始盈利142条核验、50/50及92/100覆盖；指数历史修正广度继续未知。原资料/预算/失败保持；本阶段新增金融来源0、行情0、新收益回测0。
- 产品实际改10个已列路径（8个前端文件、2个新显示JSON）；6个旧文件有字节备份。主控按前后差异与原始数据独立验收；两句口径修订后主控仅移除社融重复标题/孤立CSS，无新增范围。
- 相关Node检查、TypeScript、不覆盖dist的Vite构建、仓库归置均通过；旧SSR路由警告保留。实际桌面检查首屏、科创权重表、盈利覆盖及社融零起轴/空月。没有手机验收。
- 成果仍仅本地未提交产品、未部署；沿用codex/factor-unit-research-20260915工作区。协调提交不代表可在远端重现本地未提交UI。
- 新小记录及最终交付：/Users/yongbiaoli/Documents/ChatGPT/在做中/research-notes/leisignal-market-observation-review-2026-11-15/gemini-followup/delivery.md；同目录有Gemini意见、数据能力、合同、before/after指纹、product-diff.patch与verification.json。
- 当前无剩余必需工作。真实历史成员/连续权重、盈利修正完整版本和预测/账户增量未评价，需新的合格资料或新用途问题，不在本轮继续换参数或追加收益实验。
