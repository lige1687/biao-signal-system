# Agent 入口一致性修复：生产采用记录（2026-09-19）

## 一句话结论（大白话）

上一轮验收发现"网页打字到不了三张新卡"的入口缺口，本次已修复上线：现在在
网页 AI 助手里直接打字问"现在能定投吗"，定投状态板卡片会完整渲染在页面上
（证据账本版本、中美宽度、11 个标的逐状态都在，并明确标注"只提示不判定"）。
改动只有前端预路由一个判断分支加一个回归脚本，后端零改动。

## 工作模式说明（按用户指示）

本轮应用户"让6pro来顶"的指示，采用**GPT 6 Pro 直接产出补丁代码、主控落地
验证**的模式（未派 GLM 执行器，磁盘足迹最小）。补丁产出与对话记录在 GPT
项目会话"补丁代码与回归测试"（c/6aade4f2）。主控对补丁做了一处增强：回归
脚本增加"源文件同步守卫"（3 项断言，防止测试副本与真文件漂移），并把脚本
路径按仓库惯例从 scripts/ 调整为根层。

## 修复内容与验证

- web/src/utils/resolveRoute.ts：discussion + topic∈{dca,sentiment,mindset}
  → dispatch；旧三类与 backtest 原样保留；两层词表口径差异与 chat_fallback
  优雅回落写入注释（6 Pro 起草、主控落地）。
- web/run-resolve-route-regression.mjs：10 断言（三类新 topic→dispatch、
  未知 topic/空 topic→chat、旧三类→dispatch、backtest、symbol 不改变路由）
  + 3 源守卫；package.json 增 test:resolve-route 脚本入口（无依赖变更）。
- 候选提交 c5d0fc3a（候选仓）；零漂移预检后应用至运行仓，装后 3/3 逐哈希
  一致；运行仓复跑 10+3 断言全过、vite build 通过。
- **线上实测（决定性）**：真实 Chrome 驱动生产前端（vite 5173），AI 助手
  抽屉打字"现在能定投吗"→定投状态板卡片页面渲染（截图
  raw/agent-entry-fix-adoption-2026-09-19/page-typed-dca-card-live.png）。
  回归三脚本（resolve-route/copilot-cards/agent-ux）在运行仓全过。

## 限制与边界

- 完成声明口径：**网页输入路径入口一致性已修复**；agent 工作台
  （/api/agent/chat）管线本就不经过这些卡，不受影响。
- 情绪/心态问句的页面打字路径同机制放行（同一分支），未逐句截图，
  机制与回归断言覆盖。
- 采用过程中磁盘多次写满（本轮累计四次），均清理可再生缓存化解；
  磁盘根本性大清理仍待用户。

## ARCHIVE

分类数据与质量，passed 指入口一致性修复按冻结流程完成且线上实测通过；
不构成策略有效性或收益结论。
