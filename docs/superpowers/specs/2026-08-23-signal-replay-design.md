# 今日自选信号 · 历史回放 — 设计文档

- 日期：2026-08-23
- 状态：已与用户确认设计方向
- 上游约束：`AGENTS.md`、`docs/trading-spec-v1.md` §3.2（无未来数据泄漏）、`docs/superpowers/specs/2026-08-23-unified-signal-panel-design.md`（本功能是其面板的回放扩展）

## 1. 背景与目标

背景：今日自选信号面板/买点分析在非交易日显示的就是上一交易日的数据（分析基于最后一根完整 K 线）；用户想看**任意过去交易日**的自选买卖信号，并确认了两个边界：**只回放信号面板**（单标的买点分析不做 as-of），**快照优先 + 回放补算**。

目标：

1. 横幅加日期选择器：选过去交易日 D → 展示截至 D 的全自选买卖信号（与今日面板同构）。
2. 有当日快照（2026-08-23 起自动积累）秒开；无快照则一键回放补算（~30-60 秒）并落库，下次秒开。
3. 回放严格无前视：行情截断到 ≤D 重跑既有规则，判定代码零改动。

非目标：

- 单标的买点分析/K线/detail 页不做 as-of（点行仍打开当前分析）。
- 顶栏红点不参与回放（永远 = 今天）。
- 不回放历史自选成分（用当前自选回溯，UI 常驻口径声明）。

## 2. 后端

### 2.1 回放计算（无前视的关键）

**实现发现（写计划时确认）**：`compose/pipeline.analyze()` 自带 `as_of: date` 参数并已实现行情截断（`pipeline.py:217-218`，Round 3 历史快照语义）——无需自造 TruncateAsOfProvider。

新模块 `src/lei_signal/api/signal_replay.py`：

- `run_signal_replay(db_path, day, *, symbols=None, max_workers=4) -> dict`：逐当前自选标的调 `analyze(symbol, as_of=day, cache_root=config.cache_root(), sqlite_path=db_path)`（**绕过 AnalysisService 的 TTL 缓存**——缓存 key 不含日期）。首个标的串行预热（V8 mini_racer 并发初始化崩溃规避，同 daily_scan 模式），其余走线程池。
- 买点行 `build_review(result, symbol=..., display_name=..., active_plan_ids=())`（回放不显示"已有计划"chip——计划是当下事实，回放日不存在）；卖点行 `extract_sell_signals`（3 根 recency 窗口相对截断后最后一根计算，`is_new` 正确）。
- 写 `signal_alerts` + `daily_opportunity_scan` 两表 `scan_date=day.isoformat()`、`as_of="close"`，当日整体重写、幂等（复用既有 upsert）。
- 单标的失败 → unavailable 行（DATA_UNAVAILABLE 显式，不静默），不影响其余。

### 2.2 API

- `GET /api/signals/day/{date}`：参数化 `scan_date` 复用 `_build_response`；无快照（无 meta 行）→ `{"available": false, ...空结构}`。非交易日或早于该标的缓存起点之外的日期 → 422，detail 给出 ≤date 的最近交易日建议。
- `POST /api/signals/day/{date}/replay`：同步执行 `run_signal_replay`（全自选 ~30-60 秒），完成后返回该日聚合结果。幂等：重复调用整体重写。
- 今日日期（UTC today）→ 422 提示用既有 `/api/signals/today` + refresh（避免两套"今天"口径）。

## 3. 前端（只动 `TodaySignalBanner`）

- 头部加 `<input type="date">`（max=昨天）。默认空 = 今天（现状不变）。
- 选了过去日期：标题「自选信号 · M月D日」+「回放」徽标；`GET /api/signals/day/{date}`：有快照直接展示；无快照显示「该日无快照 [回放计算]」，点击后 pending 态「回放计算中…（约 1 分钟）」，完成自动展示。
- 回放模式：隐藏「刷新」，显示「回到今天」；计数行照常但**不**触发红点。
- 常驻口径声明（回放模式展开时一行小字）：「回放口径：当前自选 × 行情截至所选交易日重算，含成分前视，仅形态参考，不构成买卖建议」。
- 422（非交易日等）→ 显示后端给出的建议日期提示，不清空已选内容。

## 4. 错误处理

- 回放中数据源失败：该标的进「数据不可用」区；全部失败 → 返回结构仍 200 但 unavailable 全量（横幅如实展示，不显示空「无信号」）。
- 日期早于行情缓存起点：正常回放，标的逐个进不可用区（由现有 DATA_UNAVAILABLE 链路自然表达，不做日期前置校验白名单）。
- 并发：回放与当日扫描写不同 scan_date 行，无冲突；同日重复回放幂等重写。

## 5. 测试

- `TruncateAsOfProvider`：截断正确性 + 无未来数据泄漏（照 `tests/no_lookahead/` 模式：追加未来行情不改变 ≤D 的信号输出）。
- `run_signal_replay`：快照落库幂等、is_new 相对 D、买/卖/不可用三路组装。
- 路由：快照命中 / available:false / replay 落库后可读 / 今日 422 / 非交易日 422。
- 前端：日期选择、回放 pending/结果、回到今天、口径声明（照现有组件模式，构建门禁）。

## 6. 验收标准

1. 横幅选 2026-08-21（周五）：无快照 → 回放计算 → 展示当天信号；再选回今天数据无损。
2. 同一历史日期二次进入秒开（读库）。
3. 红点在回放过程中/之后保持「今天」口径。
4. 全量测试通过、新文件 ruff/tsc 清洁、Streamlit 目录零改动。

## 7. 明确不做

- 单标的 detail/K线/买点抽屉的 as-of（若以后要，另立 spec，依赖 detail API 参数化）。
- 回放结果的 diff 视图（"今天 vs 那天信号变化"）。
- 历史自选成分复原。

## 验收记录（2026-08-23）

**代码门禁：** 新增 10 个单测（回放 4 + 路由 6），全量 1067 passed / 1 skipped；ruff 新文件全清；tsc + vite 零错误；Streamlit 零改动；no_lookahead 套件 25 passed（截断机制有直接覆盖）。

**真实回放（2026-08-21）：** 首次 POST 3:36 完成落库（11 标的，行情全量抓取）；二次 GET 0.003 秒秒开；回放结果与今日面板一致（同为周五收盘口径，交叉验证正确性）；非交易日 422（08-22/08-23 均正确建议 08-21）。

**浏览器验收：** 选 2026-08-21 → 标题「自选信号 · 2026-08-21」+「回放」徽标 + 收盘徽标 + 口径声明 + 完整分组列表；「回到今天」还原今日模式且红点保持 8 不变；周六日期错误提示完整透出后端建议文案。首次耗时文案已对齐实测（2-4 分钟）。

**实施备注：** 计划发现 `analyze()` 自带 as_of 截断，spec §2.1 已修订（无需自造 TruncateAsOfProvider）；终审 1 项 Important（前端丢弃 422 建议文案）已修复并浏览器复验。遗留 backlog：回放加载瞬态标题、mutation 失效竞态（边缘）、回放重写研究库历史评估行（设计知情选择）。
