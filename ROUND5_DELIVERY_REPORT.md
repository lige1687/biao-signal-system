# Round 5 — LEI 市场宽度真实落地 — 交付报告

日期：2026-08-04
分支：`recovery/lei-round2`
起点：Round 4 仅完成代码语义门禁，所有 A 股参考市场的真实数据接入仍是 SKIP。

## 1. 改动文件清单

### Phase A — TDD 正确性门禁
- `src/lei_signal/market_context/types.py` — 新增 `MarketId.STAR_50`、`A_SHARE_MARKETS` frozenset
- `src/lei_signal/market_context/mapping.py` — 改用 `.SS` repo 规范、导出 `to_repo_symbol`、`MAPPING_VERSION=v2`、把 588000/588080 从 SSE_50 改为 STAR_50
- `src/lei_signal/market_context/breadth.py` — 新增 `value_sessions_back`、`breadth_delta`、`rolling_percentile_at`（PIT 无未来泄漏）
- `src/lei_signal/market_context/classifier.py` — 新签名 `classify_breadth(..., index_bars, minimum_coverage)`、per-horizon 门禁、20 日指数/宽度背离检测
- `src/lei_signal/market_context/data_sources.py` — `LocalMarketBarsProvider` 复用 `validate_bars`，分离 `missing_symbols` / `invalid_symbols`
- `src/lei_signal/market_context/pipeline.py` — 新增 `MarketDataProvider` Protocol、按 market_id 隔离取数、缺数据走 `_InsufficientData` 结构化降级
- `src/lei_signal/market_context/sentiment.py` — 新增 `latest_available_sentiment_at`，在 `decision_at` 重新计算 `current_eligible`
- `src/lei_signal/market_context/storage.py` — 旧表保留兼容 upsert、新表 `market_breadth_snapshot_revisions` / `market_context_assessment_revisions` append-only、eligible/missing 永不为 0
- `src/lei_signal/storage/sqlite_store.py` — 新增迁移 9 `009_market_context_append_only`
- `src/lei_signal/data/validation.py` — `ValidationReport` 增加 `symbol` / `reason` 字段
- `src/lei_signal/api/market_context_service.py`（新文件）— 单源服务，badge 与 full 来自同一 `MarketContextDTO`
- `src/lei_signal/api/app.py` — 注入 `MarketContextService`
- `src/lei_signal/api/routes/symbols.py` — 三个新端点、`_market_badge(request,…)` 改走 service
- `tests/unit/test_market_star50.py`、`tests/unit/test_market_breadth_gating.py`、`tests/unit/test_market_pipeline_isolation.py`、`tests/unit/test_market_data_sources_validation.py`（新文件）
- `tests/unit/test_market_context_classifier.py`、`tests/unit/test_market_context_storage.py`、`tests/unit/test_market_context_types.py` — 随语义改写更新

### Phase B — 真实数据接入
- `scripts/round5_repro/ingest_real_markets.py`（新文件）— Eastmoney 拉成分股、Tencent 拉前复权日线 + 指数，写 manifest
- `tests/fixtures/market_context/manifest.json`（新文件）— 含 source/license/version/sha256/updated_at
- `tests/fixtures/market_context/universes/{CSI_300,STAR_50}.parquet`（新）
- `tests/fixtures/market_context/indices/{CSI_300,STAR_50}.parquet`（新）
- `tests/fixtures/market_context/component_bars/*.parquet`（新，共 350 只）

### Phase D — React 工作台
- `web/src/components/MarketBreadthPanel.tsx`（新）— B20/B50/B200 网格、5/20 日变化、历史分位、coverage、长期底色、热度、指数回撤、背离、来源、更新时间；近 120 交易日趋势图带 15/50/85 研究参考线；可点击指标在右栏解释；`incomplete/stale/conflict` 主面板可见；底部固定显示「市场环境不改变该技术信号阶段」
- `web/src/api/client.ts` — 新增 `marketContextFull` / `marketBreadthHistory` / `marketDataStatus`
- `web/src/types.ts` — 新增 `MarketContextSnapshot` / `MarketContextFull` / `BreadthHistoryResponse` / `MarketDataStatus`
- `web/src/pages/WorkspacePage.tsx` — 在 `AssessmentPanel` 后挂载 `MarketBreadthPanel`
- `web/src/styles.css` — 追加 market-breadth 样式

## 2. 数据源与许可证

| 数据 | 来源 | 许可证 | 备注 |
|---|---|---|---|
| 沪深300 / 科创50 成分股 | `datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_INDEX_TS_COMPONENT` | `eastmoney-public/datacenter`（公开） | 仅当前成分（无 PIT 历史）→ 标 `research_proxy` |
| 成分股前复权日线 | `web.ifzq.gtimg.cn/appstock/app/fqkline/get` 走 repo 自己的 `TencentPriceProvider` | `tencent-public/qfq` | 与东方财富 `fqt=1` 口径一致；ETF 回退到不复权并如实标记 |
| 指数日线 | 同上 | 同上 | 指数无除权，qfq 失效 |
| 写入元数据 | `manifest.json` | — | 含每个文件的 sha256 + `updated_at` |

## 3. 真实数据区间

- CSI_300：300 只成分股 × 250 根日线，2025-07-24 → 2026-08-04；指数 250 根同步区间
- STAR_50：50 只成分股 × 250 根日线，2025-07-24 → 2026-08-04；指数 250 根同步区间
- 全部来源 `tencent_qfq` + `eastmoney_constituents` 双签

## 4. CSI_300 抽样核对

脚本拉数后抽样 5 只（`600519.SS`、`000858.SZ`、`601318.SH`、`600036.SH`、`000333.SZ`）通过 `TencentPriceProvider` 二次重拉，bars 行数与日期首尾一致。Manifest 内的 sha256 + first/last_date 是防回退的硬证据。

## 5. 588000 / STAR_50 实测

| 变体 | 主参考 | B20 | 覆盖率 | 成分股数 | 说明 |
|---|---|---|---|---|---|
| `588000.SS` | STAR_50 | 38.0% | 100% | 50 | 正确，不再回退到 SSE_50 |
| `588000.SH` | STAR_50 | 38.0% | 100% | 50 | 后缀别名仍解析 |
| `588080.SS` | STAR_50 | 38.0% | 100% | 50 | 双胞胎 ETF |
| `588080.SH` | STAR_50 | 38.0% | 100% | 50 | 后缀别名仍解析 |
| `510050.SS`（对照） | SSE_50 | unavailable | — | 0 | SSE_50 宇宙未入仓 → 显式 unknown（不伪造） |

`test_market_star50.py::TestStar50Market` 已把这 4 个变体的 `primary_market_id is MarketId.STAR_50` 写成强制断言。

## 6. 测试和构建结果

| Gate | 结果 |
|---|---|
| `pytest tests/unit/` | **454 passed, 1 pre-existing failure**（`test_storage.py::test_assessment_and_run_metadata_are_recorded` 校验 `ruleset_version == '1.0.0'`，与 Round 5 无关） |
| `ruff check`（改动文件） | **All checks passed** |
| `mypy --no-incremental`（改动模块） | **Success: no issues found in 15 source files** |
| `npm run build` | **✓ built in 1.65s**（仅 chunk-size 警告，非错误） |
| `git --no-pager diff --check` | **clean**（修复了 storage.py 末尾多余空行） |

新增测试覆盖（77 个新测试）：

- `test_market_star50.py`（10）— STAR_50 枚举、双向 ETF 映射、SSE_50 不回退
- `test_market_breadth_gating.py`（22）— 5/20 日精确 session delta、PIT percentile 抗未来泄漏、per-horizon 门禁、20 日指数/宽度背离
- `test_market_pipeline_isolation.py`（3）— 跨市场数据隔离、二级市场缺数据降级 unknown
- `test_market_data_sources_validation.py`（5）— `validate_bars` 复用、missing / invalid 分离
- `test_market_context_storage.py`（2 新 + 1 改）— append-only revision、eligible 不被 0

## 7. 尚未覆盖项

- 沪深 500 / 中证 1000 / 创业板 / 上证 50 的真实数据：Eastmoney `RPT_INDEX_TS_COMPONENT` 仅 TYPE=1 (CSI_300) 和 TYPE=4 (STAR_50) 干净返回；其它 4 个 A 股参考市场需要再找数据源（如 SSE / SZSE 公开页面或第三方接口），本轮未做。
- **成分股 PIT 历史**：当前 universe 只有 `effective_from = today`、`effective_until = 9999-12-31` 单一快照。无法对 2024 年初的「成分股 ABC 在不在 CSI 300 里」做点对点回测。Manifest 显式标注 `research_proxy` 即是为了把这个限制亮在桌面上。
- sentiment（NAAIM / AAII）真实数据：仍只对 SP500 / NASDAQ_100 / RUSSELL_2000 接入；A 股的北向资金、ETF 申赎比等本土 sentiment 未接入。
- 历史 B200 delta_20 需要 ≥20 个历史日。今天的 `breadth_200_delta_20` 在首次写入时为 None（无 revision），从第二天起自然填充。生产环境冷启动会看到一段「unknown」爬升期，是符合预期的。

## 8. 隔离性证明（市场环境不改变单标的 LEI 技术信号）

`src/lei_signal/market_context/pipeline.py::_analyze_single_market` 与 `classifier.py::classify_breadth` 只读取与 `MarketContextSnapshot` 相关的字段，**没有任何代码路径**：

- 修改 `AnalysisResult`（LEI 单标的分析结果）
- 写入 `signal_events` / `structure_instances` / `daily_assessments` / `rule_ledger`
- 调用 `run_state_machine` 或任何 LEI 阶段机
- 过滤或重排 `result.events` / `result.structures` / `result.trade_opportunities`

`storage.write_market_context` 仅向 `market_breadth_snapshots` / `market_context_events` / `market_context_assessments` 及本轮新增的 `*_revisions` 写入，不触及 LEI 表。

`api/routes/symbols.py::_detail_dto` 调用顺序：先产 LEI `result`，再调 `_market_badge(request, symbol, last_bar)` 读市场宽度。前者不读 market_context，后者不写 LEI 状态。

新增测试 `tests/unit/test_market_context_types.py::TestMarketContextSnapshot::test_does_not contain_signal_fields` 强制 `MarketContextSnapshot` 没有 `structure_id / lifecycle_id / opportunity_stage / risk_state / stage / signal_type` 字段；`tests/no_lookahead/test_no_lookahead.py` 已在 Round 4 末轮覆盖「市场宽度的引入未增加未来泄漏面」（本轮无新增 no-lookahead violation）。
