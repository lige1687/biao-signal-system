# 市场理解第一版实施计划

> For agentic workers: use subagent-driven-development for the bounded content task, controller integration and a focused final review.

**Goal:** 用户在显眼入口按市场和投资目的阅读50组观察主题、12项详细解释、现有接口读数及ETF范围联系。
**Architecture:** 新React页及独立feature目录；只读消费另一负责人已发布observations契约；无后端时说明未接通。归档素材晋升为应用内容，不在运行时导入raw。
**Tech Stack:** React18、React Query5、TypeScript、Vite；现有Node内置assert回归方式。

## Global Constraints

- 只写本计划精确范围，不改原观察卡/CPI/情绪/技术规则/后端/Streamlit。App仅import/route、TopNav仅一个入口。
- CN/US严格隔离；知识说明不冒充最新数值。空值不填0，接口错误不变“市场平静”，固定历史资料不称今天。
- 日期所属期、来源公布、系统取得分开；未知不升级资格。高低与升降分开，无通用买卖阈值；事件无可比预期不说超预期。
- ETF关系来自用户显式选择的资产范围/币种/结构，不从名字猜，不读取账户金额，不产生交易操作。
- 来源研究12/12封存，本轮0新来源/拟合/市场实验/付费；只做软件功能检查。
- 一文件一写入者，隔离工作区；不切换共享脏分支。安全成果仅本任务分支，协调仅自己的记录；不合并部署。

## Task 1 — Promote reviewed content (Sol)

Read docs/experiments/raw/market-understanding-expansion-2026-10-03/{indicator-cards,density-audit,source-ledger}.json and report §2 roles. Write only web/src/features/market-understanding/content.ts and content-data.json. Export contract specified in task-1-brief.md. Preserve 50 stable IDs/exact source cells, 12 explanations and source evidence. Add readable 8 topic metadata, method reading order and roles derived from existing report. Do not create live numeric values or broaden financial claims. Verify IDs, relationships and static types; report to task-1-report.md. No git commit by helper; parent owns index.

## Task 2 — Read-only adapter + regression (controller)

Create observation.ts matching published55d8aa9 API, runtime reject wrong-market, malformed/duplicate/unknown IDs, nonfinite numeric values, invalid units and inconsistent missing statuses. Optional endpoint failure has distinct state. Preserve server qualification, expose unavailable date. Normalize to small display model with fixed historical turnover fact, correct survey-week label and no invented publication dates. Test both markets, nulls, source errors, wrong units/market, zero, date precision and fixed sample using web/run-market-understanding-regression.mjs and own package script. Tests use synthetic data only.

## Task 3 — Usable page and connection (controller)

Create MarketUnderstandingPage.tsx and features/market-understanding/market-understanding.css. Desktop/phone layout, accessible labels/details/buttons, readable first screen. Market/method selector, evidence-backed facts and missing events, topic search/filter + full catalogue with provenance; 12 detailed cards; investor purposes; explicit ETF exposure/currency/structure selections with unknown state. Existing APIs and original pages linked, not copied/rebuilt. Add App route and TopNav near 看盘. Update approved spec current status without rewriting historical research.

## Task 4 — Verification and publication

Install lockfile dependencies in isolated worktree; baseline build. After changes regression/type/build, repo hygiene. Browser check synthetic API current/delayed/missing/stale/fixed/error and market switching, expansion/keyboard, narrow screen. No external data fetch. Read-only real local API smoke only if existing service available; otherwise mark unavailable. One focused reviewer for newpage/adapter/content risks; do not repeat old experiments. Review staged exact paths/size/secrets/CI, push work branch, compare remote full SHA, update/readback own coordination record. Record commands, exits and limitations; no online benefit claim.

## State

Coordination scope registered/read back c4ec1ccdc9a861a60c1aa8deecb63201e9a691f8 after rule8778bd3f417834f49885047afddc22c8d72bf2b8. Work base d58a0740502207ca6dfeb9c9f18b1c135aa54632. Source strategy hashes unchanged: system df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20; implementation85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903. This feature serves explanatory/reference layer only.
