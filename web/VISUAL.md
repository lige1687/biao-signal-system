# 前端视觉规范（薄版 · S1）

> 定位：可执行的约束清单，不是设计系统重构。基于 `web/src/styles.css` :root
> 现有 token 扩充，不重建。适用范围：`web/` 全部页面（S1 先落首页样片，
> S3 按签认样板推广到其余四页）。

## 1. 设计方向（用户 2026-09-07 确认，不可重开）

克制、清晰、有分量的专业研究工作台。「高级感」来自排版、比例、秩序，
不是换配色。不做暗色主题切换，不引第三方 UI 库。

## 2. 字号阶梯（正文基准 13px，盯盘密度）

| 层级 | 字号/字重 | 用途 | 现有参照 |
|---|---|---|---|
| 页面主数据（标的名/现价） | 21–30px / 600–650 | 每页只允许一组 | `.ws-symbol` 23px、`.ws-quote .price` 30px |
| 页面标题 | 15px / 650 | 页头 h1 | `.page-head h1` |
| 区块标题 | 14–15px / 600 | 面板 h3 | `.panel h3` 15px |
| 正文/表格 | 13px / 400 | 默认密度 | `body` 13px |
| 次要说明 | 11–12px / 400–500 | 标签、元信息、图例 | `.ws-entry-k` 11px |

规则：同一页面主数据字号只出现一档；层级靠字号+字重+颜色三级表达，
不靠加边框。价格与数字保持 `tabular-nums`（body 已设）。

## 3. 间距与秩序

- 节奏基准 4px：组内 gap 6–8px，组间 16–24px，分区留白 ≥ 32px。
- **减少碎框**：相关联的信息进「组」，组内用间距与细文字分隔线
  （`border-left: 1px solid #e5eaf1`），不用多个独立带边框胶囊
  （`.badge-chip` 只保留给真正需要醒目的状态，如宽度预警）。
- 减少小按钮堆叠：次级操作合并进组，主操作每区最多一个 `btn primary`。

## 4. 层级与分组（顶部入口区范式）

每个页面顶部最多三个组，从左到右主次递减：

1. **主组**（`.ws-entry-primary`）：核心身份信息（标的 + 报价 + 道路状态）。
2. **次组**（`.ws-entry-context`）：键-值元信息（阶段 / 市场环境 / 板块阶段），
   弱化为 `键 11px 浅色 + 值 12.5px 深色`，无边框。
3. **动作组**（`.ws-quote-actions`）：右对齐操作按钮。

可点击的元信息用 `button.ws-entry-link`（无边框，hover 下划线+蓝），
不用带边框的假按钮。

## 5. 黑/灰/绿策略状态（专用色，不得挪用）

- 语义固定：绿 = 多头观察，灰 = 中性，黑 = 空头规避。
  token：`--biao-green: #0b9b64`、`--biao-gray`、`--biao-black`。
- **呈现方式固定：圆点 + 中文文字**（`ColorBadge` / `.color-badge` /
  `.state-dot`），绝不只靠颜色传达语义；去色后仍可辨义。
- **固定位置**：首页在报价右侧（`.ws-entry-primary` 内、`ws-state` 按钮后），
  侧栏用 `.sb-state-key` 图例 + 行内 `.color-badge`。
- 灰色必须清晰可见、不等同禁用态：灰底 `#e4e8ed` + 边 `#a3acb8` +
  字 `#364152` + 点 `#717d8e`（见 `.color-badge.gray`），状态文字对比 ≥ 4.5:1。
- 绿色不得当普通装饰；黑灰绿与涨跌红绿（`--up/--down`）严格分开呈现，
  不在同一元素混用。
- 蓝（`--accent`）= 操作/选中，仅按钮与链接态使用。

## 6. 状态组件样式（S1 落地参照）

- `.color-badge`：圆点 9px + 文字 12px/600，三色各有实体底色（黑反白、
  灰浅底深字、绿浅底深绿字），见 `workspace-design.css` §三色。
- `.state-dot`：8px 圆点，用于图例与列表行。
- `.ws-entry-item`：键值元信息（非状态色，中性色系）。

## 7. 红线（继承执行简报）

前端只做展示不重算信号；不改接口语义与业务逻辑；不增删路由；
判定与 UI 输出用策略自己的语言（阶段、路牌、触发条件、失效位）。

## 8. 导航信息架构（S5，2026-09-19）

顶栏从 18 入口平铺改为「轻重分组」，只改入口组织与视觉权重，
不改路由、权限与数据。

- **一级（高频工作流，常驻可见）**：看盘 / 行业板块 / 情绪 / 今日操作 /
  我的持仓，右侧 AI 区（工作台 + AI 助手按钮）。
- **二级收纳 1「策略研究」（研究资产）**：监督待办 / 因子观测台 / 回测 /
  本轮研究 / 实验报告库 / 文献学习库 / 系统待升级。
- **二级收纳 2「资讯与认知」（信息入口类）**：基本面 / 资讯流 / 收盘简报 /
  认知心态。
- 规则：收纳组用 `details/summary` 下拉（键盘 Esc 可关、点外部自动收起、
  路由切换自动收起）；当前路由在组内时 summary 高亮（`.is-current`），
  保证用户始终能定位自己所在入口。红点/角标随入口一起进组，不丢失。
- 「更多」类收纳必须有明确分类命名与固定组员，不做无分类的垃圾桶。
- 原有全部入口必须可达；新增入口先归类再上架，不回到平铺。

## 9. 无报价行页面头范式（S6，2026-09-19）

sentiment / news / mindset / fundamentals 四个认知入口页采用的页面头结构，
后续 B 档页（research/library/factors/backtest/learning/upgrades/plans）统一页头时复用：

- **结构固定三段**：`.pg-head-title`（标题 15px/650 + 一句话定位 11.5px 浅色）→
  `.pg-head-kv`（状态键值，左边框与标题分隔）→ `.pg-head-actions`（右对齐动作组）。
- **键值样式**：沿用 §4 次组范式——键 11px 浅色 + 值 12.5px/600 深色，无边框胶囊。
- **键值数据红线**：只显示接口已有字段；缺失显示「未知 / 不可用」，
  禁止前端补计算、禁止伪造涨跌或状态。
- **定位句必须声明层级边界**（叙事标注层 / 参考层 / 环境标注层），
  与策略体系「基本面消息面只做叙事标注」的红线一致。

## 10. 研究资产页统一页头（S7，2026-09-19）

research / library / factors / backtest 四页复用 §9 `.pg-head` 范式：

- 键值只取页面既有数据（research 的会话元信息、library 的 registry 统计、
  factors 的快照/截止/留痕、backtest 的当前交易模块），缺失显示「未知」。
- 交互与数据绑定不变：library「隐藏任务书」开关、factors「刷新」按钮、
  backtest 页签与表单全部原样保留，只换页头容器。
- 数据加载/失败态同样渲染页头（键值「未知」），失败提示保留在页头下方。

## 11. 收尾页统一（S8，2026-09-19）

learning / upgrades / plans 三页页头并入 §9 `.pg-head` 范式，第二批
11 个改造页（A 档 4 + B 档 4 + 收尾 3）页头结构全部一致：

- learning 键值：文献/学习内容/学习路线/内容版本（stats 与 updated_at）。
- upgrades 键值：方向性/具体目标数与待授权/进行中/待验收（items 统计）；
  原 27px 大标题降为范式 15px，导出/登记按钮原样保留。
- plans 键值：活跃计划数（entered+armed，加载中「未知」）。

## 12. 设计 token 表（S9，2026-09-19）

styles.css `:root` 建立全站 token，页面 CSS 与内联样式只允许引用 token
（特殊用途例外须在实验/阶段报告中列出）：

| 类别 | token | 值 | 用途 |
|---|---|---|---|
| 字阶 | `--fs-xs` | 12px | 辅助弱信息（受控） |
| | `--fs-body` | 13px | 正文基准 |
| | `--fs-md` | 14px | 主要信息 |
| | `--fs-title` | `16px` | 模块标题 |
| | `--fs-page` | 20px | 页面标题 |
| | `--fs-display` / `--fs-display-lg` | 24px / 30px | 特大展示 |
| 文字灰 | `--text-primary` | #1f2937 | 主文字 |
| | `--text-secondary` | #5b6473 | 次级说明 |
| | `--text-muted` | #7b8494 | 弱化辅助 |
| | `--text-disabled` | #9aa3b2 | 禁用/占位 |
| 圆角 | `--radius-sm` / `-md` / `-lg` | 4 / 8 / 12px | 小控件 / 卡片面板 / 大容器 |
| 边框 | `--border` / `--border-subtle` | #dfe5ee / #e8edf4 | 普通 2 档；`--border-strong` 仅限既有强调用途，不新增 |
| 旧别名 | `--text`/`--text-dim`/`--text-faint` | 同 primary/secondary/muted | 存量引用兼容，不新增使用 |

映射规则（本次收敛所用，后续新增同此归档）：

- 字号：≤12.9→xs；13.x→body；14.x→md；15–18→title；20→page；
  21–27→display；30→display-lg。10px 及以下全部并入 12px（无图标/代码豁免项）。
- 灰字：#1f2937/#222/#333 系→primary；#5x–6x 系→secondary；
  #7x–8x/#98a2b3 系→muted；#9ca3af–#b3bdcc 系→disabled。
  黑/灰/绿策略三色（--biao-*）不计入、不映射。
- 圆角：≤7px→sm；8–10→md；≥12→lg；0/50%/999px 原样保留（不得新增 50%/999 用途）。
- 边框：中间灰蓝系→--border；更浅的 #e5–#e9 系→--border-subtle；
  红/绿/蓝/琥珀等状态边框不映射。

已知例外：workspace-design.css 原 `.top-nav/.workspace` 覆盖的
--text/--text-dim/--text-faint（#202b3b/#536175/#637084）已删除，
首页文字灰并入全站 4 档；Agent 工作台（保护文件）不参与本轮收敛。

### §12.1 表单控件字号（S9 返修，2026-09-19）

全局基础规则 `button, input, select, textarea { font-size: inherit; }`：
表单控件不吃浏览器默认 13.3333px，未显式设字号的按钮/输入框一律跟随所在
上下文字号（通常 13px 正文）。不用 `font: inherit`——那会把行高从浏览器默认
约 1.2 连带改成 1.45，全站按钮高度漂移；逐类补丁则防不住新增控件。
元素选择器特异性最低，已有显式字号的控件不受影响。新增按钮/输入框无需再
单独写 font-size，除非刻意脱离上下文。

## 13. 五类组件规格（S10，2026-09-19）

S9 token 之上的组件层规格。同类规格差为 0；布局/密度不动。

### Button
- **常规**：`padding: 4px 12px`；`min-height: 28px`；字号 `--fs-xs`；
  圆角 `--radius-sm`；边框 1px `--border`（primary = accent 实心白字）。
  适用 `.btn`、`.seg-btn`、`.fund-nav-btn`；`.bt-tab` 为胶囊形态（999px 例外）。
- **小型**：`padding: 3px 10px`；`min-height: 24px`；`--fs-xs`。
  适用 `.btn.small`、`.btn.mini`。
- **状态强调胶囊**（`.nf-focus-btn` / `.nf-filter-chip`）：5px 12px + 999px
  半透明状态边——独立小类（状态色胶囊），不计入常规同类。
- 表单输入控件沿用 §12.1 `font-size: inherit`。

### Card
- 卡片/面板容器：`--bg-panel`/`--bg-card` + 1px `--border` + `--radius-md`
  + `--shadow`；内边距基线 `10px 12px`（卡片列表底距 8px 允许，
  页面级 section 容器 14px 16px 允许）。`.card`/`.panel`/`.bt-section`/
  `.dialog` 已合规。

### Badge
- **胶囊徽标**：999px（既有例外，不新增）、`padding: 3px 12px`、`--fs-xs`、
  `--border` 或状态色边。适用 `.badge-chip`、`.chip`、`.bt-tab`。
- **矩形小标签**：`--radius-sm`、fs-xs（`.card .tag` 1px 5px 行内标记、
  `.workspace .chip` 4px 7px、`.workspace .color-badge` 4px 9px）——
  行内密度场景变体，不算胶囊同类。

### Table
- 宽度 100% + border-collapse；`--fs-xs`；**th/td padding 统一 6px 8px**；
  th：fs-xs、weight 600、`--text-faint`/`--text-dim`；行线 1px
  `--border`/`--border-subtle` bottom；数字列 tabular-nums。
- 紧凑变体（声明保留，不属违规）：`.macro-table` th 3px 8px 3px 0、
  `.sx-table` tbody td 4px 8px。

### Header
- **页面头（.pg-head 范式）**：标题 `--fs-title`/650；副题 xs faint；
  键值 k=xs faint、v=xs secondary/600；左分隔 1px `--border-subtle`；
  动作组右对齐 gap 8。旧 `.page-head` 标题字重统一 650 对齐。
- **模块头**：面板内 `.panel h3` = `--fs-md`；卡片区头 h3 = `--fs-title`。

### §13.1 Button 上下文变体（补充声明）

`.btn small` 与上下文类并用的混合按钮，遵循各自上下文规格，不计入
「小型按钮」同类：
- `.top-nav .nav-agent`（btn small nav-agent）：padding 8px 12px，与
  顶导链接（9px 11px）同高，属 Header/导航族。
- `.workspace .ws-sidebar-toggle`（btn small ws-sidebar-toggle）：
  图标按钮，min-height 28px、padding 2px、正方形。
- `.btn small chip` / `.portfolio-action` 等装饰叠加不改变按钮盒规格。

## 14. 代表页精修回归（S11，2026-09-19）

五代表页（首页/详情/情绪/板块/回测）× 三宽度（1440/1280/500）computed
审计 13 组全部达标：字号 ≤6 档（24/30 合并"特大展示"档计）、字阶外 0
（10px/13.3333px 已于 S9 清零）、普通文字灰 2 档、圆角 2 档、文档级溢出 0。

本轮精修（5 处）：

1. 板块页两处内联 11px 说明文字 → 12px（字阶）。
2. 板块页 `STAGE_HEX[""]` 阶段未知灰 #9aa4b2 → #8c96a8（与 --biao-gray
   同值）：阶段未知是灰状态语义，归入 BIAO 灰状态色，不再算普通文字灰。
3. `.sx-table tbody td` 行线 #eef1f6 → `--border-subtle`（S9 映射遗漏补齐）。
4. `.btn` 显式 `line-height: 1.45`（表单控件行高不继承 body，▼ 等回退
   字形会把行盒撑到 normal 的不同高度；显式行高使同类按钮高度严格一致，
   实测小按钮 25/26 → 全 25）。
5. `.sx-header-actions .btn` nowrap：窄宽度下页头按钮不再文字换行
   （原 41px 高双行钮），动作组整体换行，表格可读性不变。

判定语义说明：情绪页 verdictColor #4b5563（中性判定）/红/绿/琥珀为状态
色族，不计普通文字灰；黑灰绿三态徽标全程未动。回测/板块 500px 的元素级
"越界"全部是表格自身滚动容器内部（S8 既有范式，文档级溢出 0，与改造前
一致，无新增）。

截图：/tmp/s11shots/{before,after}_{home,sectors,detail}_{1280,500}.png。

## 15. 首屏层级实验（S12，2026-09-19）

WorkspacePage 首屏阅读顺序重组：第一眼报价行（标的+价格+道路状态），
第二眼「今日信号组」，第三步动作区，K 线作验证层。手段全部为分组/留白/
分隔线，无字号放大缩小、无新增颜色、无判定逻辑变化。

1. **今日信号组 `.ws-firstlook-group`**：今日信号横幅（组头）+ 四段摘要条
   （组体）合并为一个白底单框容器，组内以细横线分界；覆写两组件原先
   「透明横幅 vs 各自带框卡片」的异质样式（`workspace-design.css` 追加段）。
   两组件内部逻辑、黑灰绿徽章不动。
2. **动作/工具分组**：报价行动作区改为「建立执行计划、买点分析 | 解释」，
   动作在前，工具在后，中间 1px 竖分隔线（`.ws-action-sep`）。
3. **主组留白**：`.ws-entry-primary` gap 24→28px，强化报价行与次组分隔。

审计基线说明：WorkspacePage 既有 10/11/12.5/13.3333px 字号集中在回测折叠
面板头（pb-*/cb-*）与量能图例，为 S12 之前工作树遗留，非本轮引入；本轮
改动零字号声明，三宽度直方图前后一致。截图：
/tmp/s12shots/{before,after}_{1440,1280,500}.png。

## 16. 信号组层级模式推广（S13，2026-09-19）

首页（S12 `.ws-firstlook-group`）验证的层级模式推广到 /ops 与 /daily
两个同心智页面，共用类 `.pg-firstlook-group`（组头/组体/动作区共享同一
白底容器，细横线分界，动作区右对齐、不与摘要竞争）：

- **每页最多一个一级信号组**：组头=标题+日期/阶段等上下文+主任务提示；
  组体=摘要层（只汇总既有数据，不新增信息）；动作组=主动作（进入既有
  入口/槽位切换）+次动作（查看解释/展开详情）。明细分区（表格、清单）
  留在组容器之外，作为第二层阅读。
- **/ops**：组头「今日操作+日期+推送摘要」；组体为计数摘要行（持仓/
  待办/观察+过热警示）；动作区「去监督待办处理（btn primary）+展开
  情绪面与事件详情（锚点）」。
- **/daily**：组头「收盘简报+日期/槽位/生成时刻」；组体=今日机会速览
  条+核心摘要（去各自外框合并进组容器）；动作区=槽位切换+原始文字版
  开关。原始文字版由常驻折叠改为按钮控制展开。
- 红线：只调整视觉分组，不新增信息、不改业务判断与数据绑定、不新增
  路由、不复制首页内容（只复制层级模式）。

## 17. 情绪页趋势图视觉中心（S14，2026-09-20）

/sentiment 以空间建立主次：主图 = 板块情绪区内的「整体市场冷热（宽度图）」
（既有 `MarketBreadthChart`，未新增图表），辅助层 = 底部四张情绪指标卡
（全A情绪/市场结构/美股情绪/美国调查）。样式全部在页面级
`src/pages/sentiment.css`（由 SentimentPage.tsx 独占引入），未写共享 styles.css。

- **桌面（≥1280）主图增高**：`.sent-page .sb-breadth-block > div[style*="height"]`
  以 `height: 360px !important` 覆盖组件内联 250px（echarts ResizeObserver
  随容器自适应重绘）；实测主图 360px > 最高指标卡 295px，成为页面最高的
  单一视觉元素。768/390 高度不变（250px），窄屏阅读顺序本就图先于指标卡
  （DOM 顺序既定，未调整）。
- **指标卡降权**：`.sent-page .mood-grid .mood-card` 背景由白 `--bg-panel`
  改为页面底色 `--bg`、边框改 `--border-subtle`——白卡区（主图所在）与
  扁平灰卡区形成两层阅读；内容、字号、徽章色、交互全部不变。
- 审计：三宽度（1280/768/390）水平溢出 0；字号直方图前后完全一致
  （12/13/16/24px 四档，无新增档）；图例/轴标/阈值线目检无裁切；
  主图区块 padding 10/12→14/16 并与后续内容拉开 18px 间距。
- 截图：/tmp/s14shots/{before,after}_{1280,768,390}.png（同一合成夹具，
  mock /api/sentiment/dashboard 与 /api/market-context/breadth-history，
  未起生产后端）。
