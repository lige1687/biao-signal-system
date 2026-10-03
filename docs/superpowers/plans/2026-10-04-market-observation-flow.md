# Market observation flow Implementation Plan

> **For agentic workers:** 使用executing-plans在当前独立worktree依次执行；用户已授权实施，不另派任务。

**Goal:** 在既有市场图表上完成日期透明、四组观察、共同摘要及连续宏观解读。
**Architecture:** data-quality纯函数识别观测间隔，observation-model生成四组合及变化事实；ObservationPanel展示同模型，MacroReadingPanel维护仅面板内上下文并用当前查询输入重算。复用历史API和已有图表，不新增数据供应商或改技术层。
**Tech Stack:** React18、TypeScript、ECharts、TanStack Query5、esbuild现有运行环境。

## Global Constraints
只叙事层；web UI不动Streamlit；不改交易/策略/共享工作区；既有封存报告/预算不重置；代码只本任务分支，协调只本条；不可用输入不填零；无部署/main/付费。

### Task 1: 日期与输入资格
Files: web/src/features/market-understanding/data-quality.ts、dashboard-model.ts、MarketDashboard.tsx、IndexComparison.tsx；Test: web/run-market-observation-regression.mjs。
- [x] 写回归：月末PE实际月频；空/疏采不认证；未来不纳入；演示不当现值；读取时间不称发布时间。运行`cd web && node run-market-observation-regression.mjs`先核缺模块失败。
- [x] 实现`observedFrequency(metric, series)`与`qualityNote(metric, series, today)`，保留原单位/数据。loadHistory附客户端读取时间；卡片和对照使用保守频率。
- [x] 运行相同检查exit0，相关旧测试exit0。

### Task 2: 四组合与摘要
Files: observation-model.ts、ObservationPanel.tsx、MarketDashboard.tsx、dashboard.css；Test同上。
- [x] 检查`observationSnapshot(market,series,indices,today)`四组角色/缺项，变动排序、不同日期不混为同日、空指数不补。预先写断言。
- [x] 图中每行独立单位，当前值/变化/日期/参考/来源透明；摘要列最近有效观测及缺项。组合详细读法含升降条件和反例。
- [x] 测真实接口输入和390px布局，允许部分缺数，不能断言真实供应商资格全部通过。

### Task 3: 连续宏观追问
Files: macro-reading.ts、MacroReadingPanel.tsx、AgentWorkspacePage.tsx；Test同上。
- [x] 检查`resolveMacroQuestion(question, previous)`的A/美切换、利率追问、买卖边界及无上下文；补足关键词估值/增长，保留原成交排除。
- [x] 在既有入口接续最近问题而非按问题key重挂载；使用当前series依赖重算，选题按钮直接解读，显示前题和清空上下文。
- [x] 实际浏览器连续追问→切市场→回图，原Agent必要内存回归，不改旧聊天流。

### Task 4: 来源核查、证据和同步
Files: dated docs/experiments/market-observation-flow-2026-10-04.md及raw、registry/INDEX自己的条目、两进度。
- [x] 核官方PE定义/FINRA月度/CFTC周度/盈利修订可取得性与许可缺口；记录请求/失败、指纹，0金融实验。
- [x] `cd web && npm run build`与相关测试；独立仓内临时目录恢复最低纯函数检查；归置器记录实际结果。
- [x] 精确清单/敏感扫描/diff，普通提交push任务分支，fetch读回文件和完整SHA；更新并核协调本条。新规则/冲突出现先停冲突块。

验收不以计划勾选代替实际回执；归档包含输入和原策略指纹、失败、剩余数据资格与未测量业务效果。

实际回执见本轮报告与raw/validation.json。工程步骤完成；来源只取得有限定义/反例，真实资料资格未完成，按请求项超限后停止。原计划“6次”含糊批次记账保留错误，不把勾选等同来源完成。台账写入等待明确确认。
