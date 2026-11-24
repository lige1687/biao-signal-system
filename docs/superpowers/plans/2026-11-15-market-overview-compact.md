# 中美市场紧凑总览 Implementation Plan

> **For agentic workers:** Use inline execution with focused test-first checks; this task has one writer.

**Goal:** 在首页展示可读的中美估值及宽度历史小图，保留原自选和完整市场观察入口。

**Architecture:** 复用原有 `IndicatorThumbnail` 数据来源与图表；新增独立总览视图，不改现有收藏状态。页面提供科创历史快照、已有等权观察、盈利修正未知及 COR3M 详情入口。按 Pro 的建议优先四项核心，最终列数由实际 1280×720 可读性与紧凑要求决定。

**Tech Stack:** React 18、TypeScript、React Query、现有 SVG 图表、Node 内建测试、Vite。

## Global Constraints

- 桌面首页观察用途；不新增交易信号、回测、收益结论、付费来源或生产部署。
- 中美股票池、各自观察日期、宽度分母及历史版本不能混用；空值不填零。
- 已有自选配置及顺序不重置；原三层 25 项和指标分类仍可访问。
- 科创只显示标注日期的固定名单快照；盈利修正未知，等权 ETF 比值不冒充同池收益分布。
- 代码基于共享脏区，编辑前逐文件备份；变更只在已登记范围。

## Task 1: 核心总览与自选隔离

**Files:** `web/src/components/market-observation-alerts/{index.tsx,CompactOverview.tsx,compact-overview.css,CompactOverview.test.mjs}`。

- [x] 写服务端渲染回归：首页出现 `中美总览`，且持久化的自选列表保持原始字节；先运行观察原页面断言失败。
- [x] 新增四项总览：`erp-cn`、`breadth-cn`、`erp-us`、`breadth-us` 使用现有小图；点击进入现有详情；自选和完整面板独立切换。
- [x] 增加科创50/100试算快照、等权 ETF 代理、盈利修正未知和 COR3M 可访问入口，不替代缺失历史。
- [x] 重跑回归及既有 `selection.test.mjs`；核对自选迁移保持不变。

## Task 2: 图表可读性与验收

**Files:** `web/src/components/market-observation-alerts/{IndicatorThumbnail.tsx,MiniTrend.tsx,style.css}`。

- [x] 核心图保留真实日期、末值、参考线和缺失断线；为总览增加有意义的刻度，百分宽度采用 0–100%，历史不足不画伪曲线。
- [x] 执行相关 Node 测试、`npx tsc --noEmit` 和不写 `dist` 的 Vite 构建；不得覆盖服务使用的静态版本。
- [x] 内置浏览器检查 1280×720 首屏及实际两市图、日期、纵轴、入口、键盘焦点、缺数和收藏持久性；必要时调整列数和文字，不以截图代替数据资格。
- [x] 核对变更、请 Pro 复核实际结果，记明未接通的科创连续历史、盈利预测版本、同池权重和社融结构。

## 验收边界

Pro 只按文字复核，未读取截图。连续科创宽度、盈利预期修正、严格同池等权和社融数据不属于本批已完成项；新增来源额度已请求用户决定。
