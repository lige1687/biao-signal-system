# 基本面趋势图：小图 sparkline → 点开大图 + 机会/风险分界线

## 背景调研结论：基建已远比预期完整

后端历史序列、前端图表库、阈值框架、分界线定义**都已存在**，真正的缺口是"小图预览 + 点开看大图"这一层 UX 没接上。

已就绪（无需重做）：
- 后端历史管道全通：
  - `GET /api/fundamentals/rates-history` → `{cn_10y, us_10y, cn_us_spread_10y, vix, margin_rzrqye}`，各项带 `dates[]`+`values[]`（`sources.py:373/402/421`、`service.py:133 rates_history`、`routes/fundamentals.py:28`）
  - `GET /market-context/breadth-history` → 宽度 20/50/200 历史（落库于 `market_breadth_snapshot_revisions`，`get_breadth_history()` 已返回序列）
- 前端 echarts + markLine 分界线范式已有：`BreadthTrendChart.tsx`（15/50/85 三线）、`MacroSnapshotPanel.tsx` 的 `MacroTrendChart`（折线+markLine）
- 已有研究的阈值框架 + 分界线定义（`MacroSnapshotPanel` 的 `US_10Y_ZONES`/`CN_10Y_ZONES`/`MARGIN_ZONES`/`METRIC_MARKLINES`，**带机构出处**）
- 抽屉覆盖层范式已有：`IndustryFlowDrawer`（同页）
- 前端 client + 类型已就绪：`fundamentalsApi.ratesHistory`、`RatesHistoryResponse`/`RatesHistorySeries`

真正的缺口：
1. Fundamentals 页利率区只有纯表格（`RatesSection`），无图、无分界线（而 `MacroSnapshotPanel` 有全部这些但只在 Workspace 页用，没接到 Fundamentals 页）
2. **全站无"小图 sparkline 预览"**——折叠态全是纯数字
3. 宽度图是"一直大图内联"，不是"小图点开变大图"
4. PMI/CPI/PPI 无历史序列（后端易补：`_fetch_macro_report` 调大 `pageSize` 返回全部行即可）

---

## 方案

### 第 1 步：抽取共享层（消除重复，单一事实源）

新建 `web/src/components/trend/`：

- **`zones.ts`**：把 `MacroSnapshotPanel` 里的阈值框架 + `METRIC_MARKLINES` 移过来，新增 PMI/CPI/PPI 的分界线（PMI 50 荣枯线；CPI/PPI 0 通胀/通缩线），新增宽度的 15/50/85。`MacroSnapshotPanel` 改为 `import` 共享常量——纯搬迁，行为不变。
- **`Sparkline.tsx`**：可复用小图组件。echarts 折线，无坐标轴/网格，约 56px 高，带淡色区域填充，支持 `onClick`，hover 高亮。入参：`dates`/`values`/`color`/可选 `markLines`（小图上也可画一条淡分界线）。
- **`TrendChart.tsx`**：可复用大图组件，从 `MacroTrendChart` 泛化。echarts 折线 + markLine 分界线 + tooltip + 坐标轴。支持单线/多线（宽度需 20/50/200 三线）+ `markLines` 配置。
- **`TrendDrawer.tsx`**：抽屉覆盖层（复用 `IndustryFlowDrawer` 的 overlay 范式）。结构：头（指标名 + 当前值 + 所处区间标签）→ 体（`TrendChart` 大图）→ 区间图例（机会/风险各档带出处，复用 `MacroSnapshotPanel` 的 zone-block 写法）。

### 第 2 步：后端补 PMI/CPI/PPI 月度历史（小改）

- `sources.py`：新增 `fetch_macro_history(report_name, *, page_size=60)`——调大 `pageSize` 返回全部行（按 `REPORT_DATE` desc），映射成 `{date, value}` 序列。PMI 取 `MAKE_INDEX`、CPI 取 `NATIONAL_SAME`、PPI 取 `BASE_SAME`，`date` 用 `TIME`/`REPORT_DATE`。
- `service.py`：新增 `macro_history()`——三项独立取数 + 独立降级，返回 `{series: {pmi/cpi/ppi: {label, unit, dates[], values[]}}, errors[]}`，TTL 复用 `_MACRO_TTL`。
- `routes/fundamentals.py`：新增 `GET /api/fundamentals/macro-history`。
- `client.ts` + `types.ts`：新增 `fundamentalsApi.macroHistory()` + `MacroHistoryResponse`。

### 第 3 步：Fundamentals 页接线（核心 UX）

`FundamentalsPage.tsx`：

- **利率区**：`RatesSection` 每个指标卡（中10Y / 美10Y / 利差 / VIX / 两融）加 `Sparkline` 小图（数据来自 `ratesHistory`，页面加载即取、缓存 30min）。点 sparkline → `TrendDrawer` 大图 + 分界线 + 区间图例。
- **市场区（宽度）**：把 `BreadthTrendChart` 从"一直大图"改为小图卡片（`Sparkline` 显示 50 日宽度 + 当前值），点开 → `TrendDrawer` 大图（20/50/200 三线 + 15/50/85 分界线 + 区间图例）。中美两个市场各一张小图。
- **消费区**：PMI/CPI/PPI 卡片加 `Sparkline`（月度，来自 `macroHistory`），点开 → `TrendDrawer`（PMI 50 荣枯线 / CPI·PPI 0 线 + 区间说明）。
- 铜金比/油金比、11 ETF：**延后**（yfinance 限流，历史序列不可靠；当前值卡保留）。

### 第 4 步：样式

`styles.css`：sparkline 卡片样式（紧凑、可点击、hover 反馈）、drawer 内大图与区间图例样式、宽度小图卡。复用既有 `macro-card`/`breadth-trend-card`/`drawer-*` 类，新增少量。

---

## 分界线（机会/风险）一览

| 指标 | 分界线 | 含义 | 数据就绪 |
|---|---|---|---|
| 宽度 | 15 绿 / 50 灰 / 85 红 | 超卖 / 中性 / 超买 | ✅ 已落库 |
| 美10Y | 3.5 绿 / 4.5 橙 / 5.0 红 | 宽松 / 甜蜜点 / 危险 | ✅ |
| 中10Y | 1.8 绿 / 2.2 灰 / 2.5 橙 | 资产荒 / 合理 / 收紧 | ✅ |
| 中美利差 | 0 灰 / -1 红 | 多空分界 / 深度倒挂 | ✅ |
| VIX | 15 绿 / 20 灰 / 30 红 | 低波 / 正常 / 恐慌 | ✅（yfinance） |
| 两融余额 | 1.5万亿 橙 / 2.2万亿 灰 / 2.8万亿 红 | 低杠杆 / 正常 / 警戒 | ✅ |
| PMI | 50 灰 | 荣枯线 | 🆕 本方案补历史 |
| CPI/PPI | 0 灰 | 通胀 / 通缩 | 🆕 本方案补历史 |

---

## 质量门

- `ruff` + `tsc` + `vite build` 全过
- 现有 8 个 fundamentals 单测不破；为 `macro_history` 加单测（三项独立降级、序列返回）
- `MacroSnapshotPanel` 抽迁后行为不变（Workspace 页回归）
- 端到端：小图渲染 → 点开大图 → 分界线 + 区间图例显示 → 各源降级（yfinance 项 None 透传显示"暂不可用"）

## 不做（明确延后）

- 铜金比/油金比、11 ETF 的历史趋势图（yfinance 限流，不可靠）
- 信用利差 / AAII·NAAIM 情绪 / 就业·WEI（需 FRED key 或爬虫，此前已定为第二批）
