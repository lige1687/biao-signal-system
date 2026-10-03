# 前端阅读顺序与因子研究入口改进 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task. Steps use checkbox syntax for tracking. 用户已于 2026-09-30 授权交 Sol 实施；实际完成与未实测项见验收记录。

**Goal:** 让用户进入页面后，先知道这里回答什么问题，再看现有结论、证据范围与缺口，最后按需查阅原始资料。

**Architecture:** 保留 React + Vite 现有页面、接口与业务组件，调整导航归属、首屏信息和资料展开顺序。因子页新增研究概览，复用现有精确版本与实验关联，不生成新的研究判断。样式限定在对应页面，不重做全站主题。

**Tech Stack:** React 18、TypeScript、React Router、TanStack Query、现有 ECharts、现有 Node 测试工具。

**日期：** 2026-09-30。**状态：** Sol 已按冻结合同实施展示层，等待主负责人独立复核。任务框只勾真实完成项；未勾不表示其它研究结论失效。

## 一、范围与已有事实

本次服务于策略体系的“只读解释、研究证据导航、使用流程”层。它不改变道路、路牌、触发、失效、退出、风险纪律或研究对象。

现有问题不是单纯颜色或卡片不好看，主要是以下几处信息关系没有讲清楚：

| 已核实位置 | 当前表现 | 对使用者的影响 | 对应任务 |
| --- | --- | --- | --- |
| `web/src/components/TopNav.tsx` | 因子研究在“资讯与认知”，研究资料分散 | 不知道在哪里找研究结果 | Task 1 |
| `web/src/pages/factor-research/catalog.generated.json` | 展示快照生成于 2026-09-23，含 49 个对象、51 个版本、2 项已运行实验；时间说明折叠在页尾 | 容易把本页接入范围当成全仓最新研究进度 | Task 2 |
| `FactorResearchPage.tsx` 的 `CatalogCard` | 大量“范围待补”，所有按钮都叫“看结果” | 分不清有结果、仅有定义、证据尚未接入 | Task 3 |
| `FundamentalsPage.tsx` 的 `FUND_SECTIONS`、市场区 | “消费”下实际有就业、物价、景气；市场区连续放宽度、情绪、ETF 强弱、历史叠图 | 标签与内容不完全对应，不易区分当前读数和历史解释 | Task 4 |
| `SentimentPage.tsx` | 整体状态、板块、已有提示、情绪指标和历史信号连续展开 | 容易把环境描述、提示和历史证据混着读 | Task 4 |
| `ResearchPage.tsx` | “本轮研究”使用 2026-08-27 至 28 日静态材料 | 容易误认成当前进度 | Task 5 |
| 报告库、文献学习库 | 研究结论与采用状态的说明不够靠前；维护路径占主阅读位置 | 容易把“研究成立”或“学习应用”理解为获准交易 | Task 5 |
| `StrategySystemPage.tsx` | 路径、两串完整指纹占较多首屏空间 | 正文与文档职责不够突出 | Task 5 |
| `OpsPage.tsx` | 当前顺序编号为 ①③④⑤⑥②，事件区有条件显示 | 阅读顺序不连贯 | Task 5 |

以上属于页面与资料接入现状的检查，不是对全部因子研究是否充分的评审。因子快照之外可能已有新报告；本次不得把“未接入”写成“从未研究”。

## 二、全局约束

- 实施前重新读取仓库 `AGENTS.md`、`web/DESIGN.md`、`web/VISUAL.md`，以及两份桌面权威文档。后者只读。
- 权威源为 `~/Desktop/lei signal doc/LEI 技术交易体系.md` 与 `~/Desktop/lei signal doc/LEI 技术实现.md`。当前核对的 SHA-256 分别为 `df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20`、`85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903`。指纹变化不自动更新确认值。
- 新增、删除或改变交易含义、因子对象或研究范围时，停止相关步骤，说明影响的策略层、研究对象与历史实验可比性，等待用户确认。
- 只修改下列任务明确列出的 `web/` 文件及本计划、验收记录。不改 Python 判定、API、规则账本、研究结果、桌面文件或冻结的 `src/lei_signal/ui/`。
- `catalog.generated.json`、各研究 JSON、定义登记表、实验报告、指南包、候选注册表，本轮均只读；不因日期较旧自动重建快照，不启动回测。
- 保留全部既有路由、查询参数深链接、原报告入口、关键错误和日期提示。没有字段就说明未记录，不造百分数、评分、排名或“已验证”标签。
- 文案以大白话为主：因子是“把一个观察写成可计算的指标”；宽度是“一批股票中有多少站在各自均线上方”。定义、计算核对、历史证据、获准交易分别展示。
- 复用当前浅色研究界面：底色 `#f3f6fa`、白色内容、正文 `#202b3b`、辅助文字 `#536175`、操作蓝 `#2458c6`。技术体系阅读器保留已确认的深色样式。黑、灰、绿道路状态与行情红绿含义不改。
- 字号以 24/16/14/13/12px 为层级参考，正文建议 14px，辅助文字不低于 12px。主要操作触控区域不小于 44px；键盘焦点可见；减少动态效果设置有效。
- 仓库存在大量原有脏改动，包括整个尚未跟踪的 `web/src/pages/factor-research/`。执行前保存本次涉及文件的基线，不能清理、整文件恢复或整批暂存。未跟踪的旧文件尤其不能当作本任务新文件整体提交；无法隔离提交时保留工作区并交付本轮差异说明。
- 在用户把计划交给 Sol 后再实施。规划任务不启动新用户任务、不更改其模型、不代用户验收。

## 三、目标阅读结构

```text
策略研究菜单
  技术体系 → 因子研究 → 实验报告库 → 文献学习库
  回测 / 前向成绩 / 历史研究回顾 / 系统待升级 保持可达

因子研究
  页头：这里能回答什么 + 已接入材料的日期和范围
  [研究概览] [因子目录] [实验与组合] [旧行情快照]
  概览：已接入实验结论（各自附范围与限制）
        按问题找因子（趋势 / 回调位置 / 相对强弱 / 风险 / 宽度）
        研究指南 / 候选注册表 / 全部报告
  目录：观察什么 | 已记录结论 | 证据范围 | 对应入口
  详情：这个指标想解决什么 → 已知结果 → 适用范围/局限 → 原表与定义
```

桌面概览以连续章节和横向信息行为主，不增加一排大数字仪表卡。窄屏按“名称/问题 → 结论 → 范围 → 操作”堆叠；筛选可折叠，当前已选条件始终可见。阅读器和长表允许各自滚动，页面整体不能横向溢出。

## Task 1：先理顺入口和页面身份

**Files**

- Modify: `web/src/components/TopNav.tsx`
- Create only if needed: `web/src/components/navigation-reading.css`
- Read only: `web/src/App.tsx`、`web/DESIGN.md`、`web/VISUAL.md`

**接口与行为：** 不增删路由；只调整导航数组中的归属、顺序与展示名称。

- [x] 记录任务文件动手前的内容、既有暂存区和未跟踪文件状态。确认本计划是本次授权范围。
- [x] 将 `{ to: "/factors", label: "因子研究" }` 从资讯组移至策略研究组，位于技术体系之后。随后放实验报告库、文献学习库，其余研究入口仍可达。
- [x] 将 `/research` 标签改为“历史研究回顾”，与 Task 5 页头一致。不改路由。
- [ ] 若需要菜单说明，仅给研究入口增加一行短说明：技术体系“查规则与实现依据”、因子研究“看问题、证据和缺口”、实验报告库“查每次研究的原始报告”、文献学习库“了解方法与采用状态”。仅应用于折叠菜单，不能让常驻导航变成两行长说明。
- [x] 保留当前页面高亮、点击外部收起、跳转后收起、Escape 收起并回到菜单标题的行为。确认因子页高亮“策略研究”。

**验收：** 桌面与 390px 窄屏能通过主导航找到因子研究和原报告；全部旧入口存在；键盘能展开、选择并退出菜单；不改情绪灯点或持仓提醒数据。

## Task 2：因子页增加“研究概览”，先说明材料范围

**Files**

- Modify: `web/src/pages/factor-research/FactorResearchPage.tsx`
- Create: `web/src/pages/factor-research/FactorResearchOverview.tsx`
- Create: `web/src/pages/factor-research/overviewModel.ts`
- Create: `web/src/pages/factor-research/overview.test.mjs`
- Create: `web/src/pages/factor-research/factor-overview.css`
- Read only: 同目录 `model.ts`、`catalog.generated.json`、`reading-guidance.json`

**接口：** `FactorResearchOverview` 接收 `snapshot: Snapshot`、`onCategory(category: string): void`、`onExperiment(id: string): void`、`onCatalog(): void`。只展示已有字段；数量复用 `catalogCounts`、分类数量复用 `categoryObjectCounts`，不把实验结果合成“有效因子数”。

- [x] 先在 `overviewModel.ts` 定义并测试以下 URL 兼容函数。优先保留已有对象/实验深链接；普通 `/factors` 才进入概览。

```ts
export type FactorView = "overview" | "catalog" | "experiments" | "legacy";
export function factorView(params: URLSearchParams): FactorView {
  if (params.get("factor")) return "catalog";
  if (params.get("experiment") || params.get("project")) return "experiments";
  const tab = params.get("tab");
  if (tab === "overview" || tab === "catalog" || tab === "experiments" || tab === "legacy") return tab;
  return ["q", "asset", "category", "stage", "result", "page", "sort", "view"]
    .some(key => Boolean(params.get(key))) ? "catalog" : "overview";
}
```

测试文件沿用现有 Node + esbuild 的内存编译方式；可用以下完整入口测试，不向临时目录写编译产物：

```js
import assert from "node:assert/strict";
import { test } from "node:test";
import { build } from "esbuild";
const built = await build({ entryPoints: [new URL("./overviewModel.ts", import.meta.url).pathname], bundle: true, write: false, platform: "node", format: "esm" });
const model = await import(`data:text/javascript;base64,${Buffer.from(built.outputFiles[0].contents).toString("base64")}`);
test("overview preserves existing deep links and filters", () => {
  for (const [query, expected] of [
    ["", "overview"], ["tab=overview", "overview"], ["tab=legacy", "legacy"],
    ["factor=a%401.0.0", "catalog"], ["experiment=e1", "experiments"],
    ["project=p1", "experiments"], ["category=宽度", "catalog"],
    ["q=均线", "catalog"], ["tab=unknown", "overview"],
  ]) assert.equal(model.factorView(new URLSearchParams(query)), expected, query);
});
```

- [x] 页签增加“研究概览”，原 `catalog` 仅改中文为“因子目录”；已有参数值不更名。页签切换仍清除对象/实验详情参数，保留已有筛选的返回体验。
- [x] 页头加入“本页材料整理于〔generated_at〕，只覆盖已接入材料；未接入不等于未研究”。把对象、定义版本、实验数量改为一行辅助信息。生成日期、实验观察期、数据截止日分别显示，不能互相替代。
- [x] 将当前“进行中的研究”标题改为“材料快照中的研究项目”，保留原项目状态、摘要和证据日期；避免把旧快照的项目描述当成实时进度。
- [x] 概览首段解释“因子”后，逐项呈现已接入实验的原结论、类型、研究产品、观察期、复核状态、首项限制和“查看实验详情”。不把负面或限定结论藏起来；原文太长可展开，但首项限制不能截掉关键否定词。
- [x] 分类入口使用现有分类名称，只解释用户问题：趋势“价格处在怎样的趋势中”、回调位置“价格离已有参照位置有多远”、相对强弱“哪些产品相对更强”、风险“波动和下跌风险怎样”、宽度“走强是普遍现象还是少数股票”。这些是目录说明，具体定义仍以精确版本为准。未来未知类别显示原名称与“查看定义范围”。
- [x] 分类点击写入 `tab=catalog&category=分类`，清除会冲突的搜索、资产、阶段、结果、页码和详情参数；不能点完得到用户无法理解的空集。
- [x] 增加只读资料入口：研究指南 `/strategy?collection=factor-guide&doc=research-guide`、候选注册表 `/strategy?collection=factor-guide&doc=candidate-registry`、报告库 `/library`。候选登记不纳入正式对象数量。情绪、机构情绪等入口沿用技术体系页既有研究扩展区，不在因子目录编造未登记对象。
- [ ] 快照缺失、格式不兼容、实验为空时显示实际空态；不显示演示结论，不回退成旧行情评级。

**验收：** 打开 `/factors`，无需展开页尾即可说出材料日期和范围；两项现有实验仍保留各自限定结论；旧精确版本 URL、实验 URL、筛选 URL 刷新后有效；数量来自实际材料，不写死 49/51/2。

## Task 3：因子目录和详情把“结论、证据、缺口”放在一起

**Files**

- Modify: `web/src/pages/factor-research/FactorResearchPage.tsx`
- Modify: `web/src/pages/factor-research/factor-research.css`
- Modify: `web/src/pages/factor-research/overviewModel.ts`、`overview.test.mjs`
- Read only: `model.ts`、`model.test.mjs`、所有研究 JSON

**接口：** 复用 `factorOutcome(item)`、`linkedExperiments(item, experiments)`、`groupCatalog`、`displayFactorName`、`dossierFacts`。关联必须同时满足实验 ID 和精确 `reference`，不把旧版证据挪到新版。

- [x] 在 `overviewModel.ts` 添加下述按钮文案函数，测试“准确关联”“同对象不同版本”“计算核对”“研究进行中”“未接入”五种情况；它只决定入口文字，不改变研究状态。

```ts
import { linkedExperiments, type FactorItem, type Experiment } from "./model";
export function catalogAction(item: FactorItem, experiments: Experiment[]): string {
  if (linkedExperiments(item, experiments).some(e => e.run_status === "completed")) return "查看证据";
  return item.research.stage === "in_progress" ? "查看进展" : "查看定义";
}
```

- [x] 列表增加可见列说明“观察什么 / 已记录结论 / 证据范围 / 详情”；移动端每行保留字段标签。将笼统“范围待补”改为“本页未接入该版本实验”，不能说该对象从未研究。
- [x] 多版本对象显示当前选中版本，仍可进入全部版本；旧版有实验、新版没有时，新版不显示旧版结论。多项实验的范围不能拼成虚构的大样本。
- [x] 详情首段按“观察什么 → 当前结论 → 本次在哪些产品和日期检查 → 主要局限”组织，复用现有说明和实验字段。原公式、时间可用性、详细指标和八方面核对保留在下层页签/展开区。
- [x] 保留各类缺口的原区分：只核对计算、证据未接入、已研究但证据不足、本次没有帮助。不能用同一个灰色“待完善”替代，也不能添加总分。
- [x] 搜索结果为空给“清除筛选”；加载失败给实际原因。单项资料缺失不能让整个因子目录消失。
- [x] 检查原实验中的数值、单位、日期、基准、成本和限制逐项未变化；不把价格变化当账户收益，不把每年正负数量直接叫稳定性。

**验收用例：** 普通动量仍显示本次未发现帮助；完整排名仍是计算核对；未接入版本不出现“看结果”；同对象切换旧/新版不串证据；返回目录、浏览器后退、刷新后筛选与页码符合原 URL；长名称和长限制在窄屏可读。

## Task 4：基本面和情绪页先讲清分区，不增加判断

**Files**

- Modify: `web/src/pages/FundamentalsPage.tsx`
- Modify: `web/src/pages/SentimentPage.tsx`
- Modify: `web/src/components/SentimentSectorBlock.tsx`，仅添加已有列表空态与分组说明
- Create: `web/src/pages/reference-reading.css`，由上述页面导入，选择器限定新页面根类
- Read only: `api/client.ts`、趋势组件、阈值配置、类型定义

**接口：** 所有接口参数、请求频率、图表数据、投票、筛选规则与判定沿用现状。分组组件只包现有 JSX，不重新计算状态。

- [x] 基本面页签保留原 hash ID：`fund-sec-market` 显示“市场环境”，`fund-sec-macro` 显示“经济与物价”；其余“利率 / 长周期叠加 / 美国宏观”保持。将“最有用”等笼统提示换成该分区实际包含的信息。
- [x] 市场区加入两个清楚分组：MarketSection 前为“当前市场：宽度与情绪”；EtfStrengthSection、SentimentViews 前为“进一步查看：产品强弱与历史变化”。说明历史叠图用于观察同期变化，不能据此认定原因或交易效果。保留原组件顺序和抽屉。
- [x] 基本面页头的“数据源”状态须诚实反映所检查接口的范围：不能仅因 `overview/rates` 无错误就宣称所有分区全部可用。不新增数据探测；显示为“概览数据源：本次未报告错误/部分不可用”，各分区保留自己的加载与缺失提示。
- [x] 情绪页给现有区块加层级标题或短锚点目录：整体状态、板块情况、系统现有提示、指标说明、历史信号。保持原有提示及行动卡的位置和条件，本轮不增强其交易号召，也不改 `VerdictBar` 推断、`plan_cn`、`win_rate_cn` 等含义。
- [x] 全 A 情绪卡将已有投票说明紧邻投票结果，三个现有指标按当前映射稳定排列；缺失项显示“未取得数据”及实际日期，不将空值当零。沿用现有方向和投票规则，不增删指标。
- [x] 板块观察、持仓、推荐等已有列表为空时给具体空态，例如“暂无持仓相关板块”，但有加载/不可用状态时优先显示该状态，不冒称“没有”。原全板块排行保留，不在本轮新增推荐筛选算法。
- [x] 对“约 9 月底恢复”等写死的未来日期，改为由现有 `available` 状态决定的“数据暂不可用，恢复后显示”；不承诺后台修复时间，不触发重建。

**验收：** 所有页签及 hash 深链接有效；有数据、缺失、错误三态可区分；图表点击和缩放保持；无额外网络调用；情绪状态、提示条件、投票与原接口逐项一致。任何发现的“已验证/机会”措辞与研究证据冲突只记入问题清单，交用户裁定其含义，不顺手改策略。

## Task 5：统一资料页身份与阅读顺序

**Files**

- Modify: `web/src/pages/ResearchPage.tsx`
- Modify: `web/src/pages/ReportsLibraryPage.tsx`
- Modify: `web/src/pages/LearningLibraryPage.tsx`
- Modify: `web/src/pages/StrategySystemPage.tsx`
- Modify: `web/src/pages/strategy-system.css`
- Modify: `web/src/pages/OpsPage.tsx`
- Create only if needed: `web/src/pages/page-reading.css`

**接口：** 只改显示顺序、标题、链接、折叠区与编号；保留所有读取、筛选、报告渲染和执行操作处理函数。

- [x] `/research` 页头改为“历史研究回顾”，原研究题目与 2026-08-27 至 28 日日期保留；增加“查看因子研究”链接 `/factors`。静态运行安排标为“当时的运行安排”；`web/public/reports` 等路径放“维护说明”展开区。
- [x] 报告库在结论筛选旁解释“成立/证伪针对报告提出的研究问题，不等于获准交易”，原分类、枚举和计数保持。缺一句话结论时显示“该报告尚未整理一句话结论，可打开正文查看”；登记文件路径和维护要求收进展开区，原警示仍可见。
- [x] 文献学习内容的 `system_relation`、`adoption_status`、`content_status` 原样移到标题下，在应用步骤之前；应用步骤加“学习用”标签。未知状态保持未知，不补造采用结论。
- [x] 技术体系页始终显示文档名称、职责、来源状态和更新时间；完整路径与当前/已确认指纹放在“查看来源路径与指纹”原生 `details` 内。未确认变化警告、读取失败、缺失路径与恢复办法保持常显，不因折叠降低可见性。
- [x] 因子指南包保留中文切换和包内选择器，增加“查看已接入研究结果”链接 `/factors`。候选注册表、正式定义和真实实验保持各自身份；模板不显示为已完成研究。
- [x] 今日操作页按当前 DOM 显示顺序只修编号：①持仓、②计划、③观察、④情绪、⑤事件、⑥推荐；事件不显示时推荐为⑤。禁止重排执行顺序或改变操作按钮行为。

**验收：** 学习内容、历史实验、当前证据三者身份一眼可辨；原文件路径/指纹仍可查；源文件变化与缺失警告不折叠；今日操作在有/无事件两种情形下编号连续，原业务内容和操作不变。

## Task 6：验收、范围复核与 Sol 交接

**Files**

- Modify: 本计划，仅勾选已验证的任务。
- Create: `docs/archive/handoffs-plans/2026-09-30-frontend-readability-validation.md`
- 其余仅运行检查，不为通过检查去清理别人的工作区。

- [x] 开始实施时检索系统待升级台账。规划时已核对 `okr-7f065ec87f69` 和 `okr-a4fed76c71c3`：两者是此前范围不同的待验收前端任务，不得覆写它们的成果或验收状态。若仍无同范围条目，登记本计划为独立具体目标；只按用户交给 Sol 的实际授权记录范围，完成后提交待验收，不自动 accept，不改 `docs/okr/initial.json`。
- [x] 执行以下相关测试与构建。前两项新旧行为测试、第三项原资料回归为必要检查；不增加只核对 CSS 字符串的测试。

```bash
cd /Users/yongbiaoli/Desktop/lei-signal-lab/web
node --test src/pages/factor-research/overview.test.mjs
node --test src/pages/factor-research/model.test.mjs
npm run test:strategy-system
npm run build
```

预期：Node 用例全通过、策略阅读回归通过、类型检查和 Vite 构建退出码为 0。若策略页面回归只因来源折叠而失败，先核对原行为仍满足，再只更新对应断言；需要修改 `web/run-strategy-system-regression.mjs` 时允许本任务的相关小块，不删除安全用例。

```bash
cd /Users/yongbiaoli/Desktop/lei-signal-lab
python3 scripts/check_repo_hygiene.py
git diff --check
```

预期：目录检查通过、差异检查无新增错误。既有无关错误单独记录，不能清理原始材料来换取全绿。

- [x] 用真实浏览器检查 1440×900、1024×768、390×844。现有开发服务正常时直接使用，不另启冲突服务；采用可用的浏览器工具调整视口，完成后恢复。记录真实截图或检查事实，不以构建代替页面检查。
- [ ] 完成下面的交互验收表，记录通过/失败、使用的 URL、实际材料日期。缺失/错误用例优先用开发测试夹具或工具模拟响应，不移动或修改桌面权威文件。

| 检查 | 可观察结果 |
| --- | --- |
| 导航键盘操作 | 因子归策略研究；Enter 展开/进入，Escape 收起并回焦点；旧路由全部可达 |
| 因子概览 | 先见材料日期、已接入结论和各自限制；定义/候选/实验数量不混合 |
| 分类→目录→详情→返回 | 选中分类正确；未知 ID 不自动选别的版本；刷新与后退保留预期状态 |
| 实验深链接 | 两条现有实验各自的产品、日期、原结论、局限保持；不同版本不串结果 |
| 因子空态与加载失败 | 无匹配有清除筛选；无材料不展示演示数据或旧评级 |
| 基本面所有页签 | hash、图表抽屉、缩放、局部错误提示可用；标题对应实际内容 |
| 情绪有/无数据 | 原提示条件不变；缺失不呈现为零/正常；无固定恢复承诺 |
| 技术体系两文档和指南包 | 目录、深链接、复制链接、窄屏目录有效；职责/状态常显，完整指纹可展开 |
| 来源变化/缺失 | 警告及恢复路径可见；不改确认指纹，不回退旧 V1 正文 |
| 历史研究/报告/学习 | 原材料和分类未改，身份与采用状态先于方法细节 |
| 今日操作 | 事件存在与缺席时编号都连续；持仓/计划/推荐顺序和动作不变 |
| 其余页面抽查 | 看盘、行业板块、持仓、监督待办、工作台无全局样式回归；不主动提交任何业务操作 |
| 视觉与无障碍 | 390px 页面不横向溢出；长标题、表格、日期可读；200% 缩放可操作；焦点可见；减少动态效果有效 |

- [x] 差异复核：产品改动只在本计划文件白名单；研究 JSON、规则、桌面权威文档、后端和 Streamlit 没有本任务改动。对桌面两源重新计算指纹，与实施前比较。
- [x] 验收记录写清：实际改动、测试结果、页面检查、遗留资料缺口、每项任务状态；区分“展示完成”与“研究证据已补齐”。不要把本轮 UI 工作提交为实验研究结案。
- [ ] 仅提交已核对的本轮小块。已有未跟踪因子目录若无法单独提交本轮增量，保留工作区并明确交付差异，不整包纳入其他任务成果。提交不是部署，不自动推送、合并或验收目标。

## 四、明确留给后续的工作

1. **研究证据接入更新：** 快照停在 9 月 23 日是实际资料接入限制。需要另行逐项核对精确对象版本、实验来源、复核状态与新旧报告关系；本计划只让限制清楚可见并提供报告库入口，不凭文件新日期认定新结论。
2. **研究是否充分：** 需要按每个问题检查基准、适用资产、时间范围、反例与相对既有信息的帮助；页面美化不能代替这项工作，不在此运行新实验。
3. **情绪用词与规则冲突：** “机会窗口”“已验证”等已有字样如缺充分依据，应列出原字段及报告给用户判断，不以 UI 改造名义修改技术含义。
4. **未发现具体问题的页面：** 看盘、持仓、计划、工作台等本轮只做全局导航与样式回归，避免无证据地全面重排。后续基于用户实际使用问题再定具体任务。

## 五、规划交接事实

- 规划阶段使用 Sol 做研究资料页只读审阅，Luna 做基本面/情绪页只读审阅；主负责人核对因子材料日期、精确关联方式和展示边界。
- 用户改为“只做计划”时，先前已动过的四页文字与展示顺序已逐项撤回；未整文件恢复、未暂存、未提交。本计划之外没有保留本轮产品代码变更。
- 这份计划本身不表示实现测试或页面验收已经通过。Sol 执行时必须按 Task 6 重新验证。
