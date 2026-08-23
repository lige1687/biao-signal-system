# 今日自选信号：统一买/卖点提醒面板 — 设计文档

- 日期：2026-08-23
- 状态：已与用户确认设计方向（方案 A）
- 上游约束：`AGENTS.md`、`docs/trading-spec-v1.md`（最高溯源依据）、`configs/rules.v1.yaml`

## 1. 背景与目标

现状：买点扫描已覆盖全自选（`run_opportunity_scan`，每日 15:00 落库 `daily_opportunity_scan`），但入口在 `/grid` 卡片墙；看盘主页（`/` WorkspacePage）只有顶栏红点数字。**卖点侧完全没有全自选扫描**——只有已建计划（armed/entered）的标的有退出判定（监督页 12 alert）。

用户需求：在看盘主页有一个统一位置，提醒**自选全部标的**的买点与卖点信号，并能点开看分析；盘中（上午收盘后、下午 14:45）就能看到当天信号，来得及操作。

### 目标

1. 看盘主页中栏顶部新增「今日自选信号」横幅，统一展示全自选买/卖信号（分级），点击行跳转标的并打开分析。
2. 卖点侧新增全自选提醒式扫描（四档口径，见 §2），**不绑交易计划**。
3. 扫描频率：11:35（上午收盘后）、14:45（盘中）、15:05（收盘最终版）。
4. 顶栏红点计数升级为买/卖合计。

### 非目标

- 不做主动推送（macOS 通知 / 飞书）——维持既有「只面板+红点」决策。
- 不改动计划监督链路：armed/entered 计划的退出判定与 12 alert 继续留在监督页，职责分开。
- 不发明新判定规则：卖点提取只汇总既有确定性输出（与 `build_review` 同一模式）。
- 不动 Streamlit（UI 冻结），一切前端改动只在 `web/`。
- 不改 `/grid` 页现有的今日机会雷达与 `daily_opportunity_scan` 表。

## 2. 卖出信号四档（全自选、提醒式、不绑计划）

| 档位 | 口径 | 策略溯源 | 展示颜色 |
|---|---|---|---|
| 卖·硬 / 结构失效 | 当日任一活跃结构 status → `invalidated`，或收盘跌破结构失效位（invalidation price） | 规格 §2.3「什么逻辑进场就什么逻辑退出」、§7 顶底构造失效 | 红 |
| 卖·硬 / 退出代理 | `exit_ema20_costbasis` 上升沿：收盘同时跌破 EMA20 与 20 日抵扣价 | 规格 §9 模块 A A6.1，`provenance: research_proxy` | 红 |
| 卖·预警 / 顶部路牌 | 顶部构造确认 或 反向关键性波动（当日事件） | 规格 §2.2、§7.4「预警不必然反向」 | 橙，文案必须带「预警」 |
| 卖·提醒 / 颜色转黑 | 三色状态 绿/灰 → 黑（当日转换事件） | 生命周期状态机（Round 3） | 灰 |

买点侧沿用现有 verdict 分级：`actionable`（买·行动）/ `waiting`（买·等待）/ `blocked`（买·受阻，可交易性门禁）。横幅分组含买·受阻，但**默认折叠**（它只说明"为什么现在不能动手"，优先级低于行动/等待）。

## 3. 后端设计

### 3.1 卖点提取（纯函数）

新模块 `src/lei_signal/api/sell_signals.py`：

- `extract_sell_signals(analysis_result) -> list[SellSignal]`
- 输入是 analyze 的确定性产物（结构状态集合、`exit_ema20_costbasis` 上升沿、当日事件流、三色状态转换），**不做任何新判定**。
- 每条 `SellSignal`：`symbol / tier / title / 一句话依据 / 关键价位（EMA20、抵扣价、invalidation）/ provenance / available_date`。
- 退出代理必须标 `research_proxy`；顶部路牌必须带「预警，不必然反向」限定语（UI 与 DTO 双侧保证）。

### 3.2 统一扫描

- `run_signal_scan(symbols, as_of)`（放 `src/lei_signal/api/signal_scan.py`）：
  - 逐自选跑 analyze（复用现有行情缓存与 provider 链）。
  - 买点行：来自现有 `build_review` 的 verdict + 摘要。
  - 卖点行：来自 `extract_sell_signals`。
  - 写新表 `signal_alerts`（新 migration）：`date / symbol / side / tier / title / detail(json) / as_of / created_at`；同日同 `as_of` 整体重写，幂等。
- `daily_opportunity_scan` 表与 `/grid` 页原样保留。

### 3.3 API

- `GET /api/signals/today`：按 买·行动 / 买·等待 / 卖·硬 / 卖·预警 / 卖·提醒 分组返回 + 计数 + 每行跳转载荷（symbol + 打开哪个分析面板）+ `as_of` 与扫描时间戳；附「数据不可用」清单。
- `POST /api/signals/today/refresh`：手动重扫（带 `as_of` 参数）。
- 数据获取失败的标的显式进 `DATA_UNAVAILABLE` 区，不得静默处理为「无信号」（README 既有原则）。

### 3.4 盘中口径（`as_of` 语义）

- LEI 规则为收盘口径（规格 §3.2：第 t 根收盘后生成信号，t+1 开盘执行）。
- 11:35 / 14:45 扫描：用腾讯最新价拼当日临时 K 线，跑同一套规则，结果标 `as_of=intraday`，前端显示「盘中临时」徽标——只做当天操作的前瞻预告，不冒充收盘结论。
- 15:05 扫描：`as_of=close`，为当日最终版，覆盖当日展示。
- 复用 `watch_subscriptions` 盘中取价的既有模式（腾讯实时价）。

## 4. 前端设计（只动 `web/`）

- **`TodaySignalBanner`**（新组件）：挂 WorkspacePage 中栏顶部。
  - 收起态一行：`今日自选信号　买·行动 2 · 买·等待 5 · 卖·硬 1 · 卖·预警 3 · 卖·提醒 2　[展开]` + 盘中/收盘徽标 + 扫描时间（买·受阻只在展开态出现，默认折叠）。
  - 展开态：分组列表。每行：标的 / 档位标签 / 一句话结论 / 新增·持续 / 口径徽标；行内可展开小节显示关键价位与口径依据。
  - 无信号日显示「今日暂无信号」+ 上次扫描时间（不得空白）。
- **点击行为**：买点行 → 选中该标的 + 自动打开 BuyPointDrawer；卖点行 → 选中标的 + 右侧解释面板定位到对应结构/风险段。
- **顶栏红点**：计数升级为买（actionable+waiting）+ 卖（硬+预警）合计；数据源与横幅同 API，避免两套口径。

## 5. 调度（launchd）

- 新 agent `com.lei.signal.scan`：一个 plist，`StartCalendarInterval` 数组挂 11:35 / 14:45 / 15:05 三个时刻，跑 `scripts/signal_scan.py`（镜像 `daily_scan.py` 结构，支持 `--as-of intraday|close` 与 `--symbols`）。
- 现有 `com.lei.daily_scan`（15:00，喂 `/grid`）不动。
- `运维手册.md` 补一节：三个时刻、失败排查、与既有 14:45/14:46/15:00 任务的时间关系。

## 6. 错误处理

- 单标的 analyze 失败：进「数据不可用」区，带原因；不影响其余标的（沿用板块快照 `warnings` 模式）。
- 全量失败（如数据源不可用）：横幅显示扫描失败态 + 上次成功时间；不得显示空的「无信号」误导用户。
- 盘中临时 K 线拿不到当日实时价：该标的按上一收盘数据扫描并标注「无盘中价」。

## 7. 测试计划

- `extract_sell_signals` 单测：四档各构造触发 fixture（复用现有 tests/fixtures 模式），断言档位、文案限定语、关键价位、provenance；确认不产生第五种口径。
- 盘中口径单测：临时 K 线拼接、`as_of` 标注、close 版覆盖 intraday。
- 落库幂等单测：同日同 `as_of` 重写。
- API 路由测试：分组、计数、`DATA_UNAVAILABLE`、refresh。
- 前端：横幅收起/展开、行点击跳转、红点计数（照现有组件测试模式）。

## 8. 验收标准

1. 11:35 / 14:45 / 15:05 三个时刻自动出结果，`biao status` 可见新 agent。
2. 看盘主页横幅一键展开，能看到全自选买卖信号分级列表；点买点行打开买点分析、点卖点行定位解释面板。
3. 卖点四档口径均可在真实自选上触发或明确显示为无；退出代理带 `research_proxy` 标注、顶部路牌带「预警」限定语。
4. 顶栏红点反映买卖合计数。
5. 全部测试通过；Streamlit 目录零改动。

## 9. 明确不做

- 推送通知（macOS / 飞书）——如果以后想要，另起需求，复用 `notify/` 基础设施。
- state 型 watch 订阅（`watch_subscriptions.py` 里的 TODO）——与本设计无关，不顺手实现。
- 盘中高频轮询（<1 小时）——先用三个时刻跑稳，按需再加密。

## 验收记录（2026-08-23）

**代码门禁：** 全量 1056 passed / 1 skipped（新增 26 个单测）；ruff 对本功能全部新文件 "All checks passed!"；`tsc --noEmit` + `vite build` 零错误；Streamlit 目录零改动。

**调度：** `com.lei.signal.scan` 已通过 `install_app_autostart.sh` 装载（交易日 11:35 / 14:45 / 15:05）；`biao-ctl status` 与安装脚本 echo 清单均含新 agent。

**真实数据：** 全自选 11 个标的（9 指数/ETF + 板块），在线 `POST /api/signals/today/refresh?as_of=intraday` 成功：买·行动 0 / 买·等待 1 / 买·受阻 7；卖·硬 5（4 结构失效 + 1 退出代理）/ 卖·预警 2（顶部构造确认 + 反向关键性波动）/ 卖·提醒 0；数据不可用 0。退出代理行带「研究代理」徽标，预警行带「不必然反向」限定语。

**浏览器验收：** 看盘主页中栏顶部横幅渲染正常——「盘中临时」徽标、「上次扫描 11:36 AM」、五档计数、展开分组列表、买·受阻 `<details>` 默认折叠、`aria-expanded` 正确；点击卖·硬「证券」行原地切换选中标的（`?symbol=TH881157.SECTOR`，不跳页）；顶栏「看盘」红点 = 8（买 1 + 卖 7，`today_signal_total`）。

**实施过程备注：** 计划中「run_opportunity_scan 内部落库」的假设有误，已在 Task 3 修正为统一扫描自身重写两表（commit dd3fe60）；运维手册两处用户既有未提交改动曾被误带入提交，已退回工作区未提交状态（commit b643508）。遗留 backlog：S3a 可排除同窗口内已失效的顶部构造（当前无实例）；POST refresh 成功路径补测。
