# 事实与缺口表：混合池因子研究的数据基础设施

本轮：研究数据获取、快照与质量校验（2026-09-10）
规范采用：`experiment-backtest-principles.md` v1.1、`definition-standard.md` 1.1.0、
`ai-execution-contract.md` 1.0.0、`experiment-report-template.md` 1.1.0
工作区 HEAD：`91c720ed46ad95237dcbc56575ac122ab606edd8`（存在大量未提交修改，HEAD 不代表实际内容）

> 本表是**盘点结果**，不是验收结论。「文件存在」「字段齐全」「历史完整」「当时可知」分别判断。
> 未查明的写「未知」，不用代码注释代替数据证据。

---

## 0. 先纠正一个定位

混合池因子研究的价格与公司行动输入**不在** `research-mixed-defense-2026-09-09` 里，
而是全部指向 `research-rotation-clean-2026-09-09/full-pool-preparation/`。

链路：rotation-clean 冻结输入 → mixed-defense 只复用（`protocol.json:source_files`）
→ `definitions.v1.json:sources` 登记为 `mixed_prices/mixed_actions/mixed_pool`
→ `src/lei_signal/research/` 运行时消费。

**登记表实测计数**（本轮独立核对，用于纠正流传的错误数字）：
容器 `1.2.0`、`schema_version 1.0.0`、`standard_version 1.0.0`、
**81 个对象**、**34 个 source**、`models` 0 个。
类型分布：`state_signal` 26、`feature` 19、`benchmark` 15、`policy/strategy` 15、
`risk_metric` 4、**`factor_return` 2**。

---

## 1. 名义价格

| 维度 | 事实 |
|---|---|
| **已有来源** | 冻结 CSV：`.../full-pool-preparation/prices.csv`。原始响应：`raw-responses/` 28 个 `sina-{sh\|sz}{code}-day-{1500\|3000}.json`。在线 provider：`data/providers.py` 8 个 |
| **获取/读取函数** | 在线：`SinaPriceProvider.fetch` `providers.py:497`；链式回退 `ChainedPriceProvider.fetch:910`；默认链 `default_provider():1503`。研究侧读取：`factor_runtime.py::_normalize_prices:61` |
| **现有缓存或文件** | 冻结 CSV 18,916 行；`ParquetCache` 落 `{symbol}.{kind}.parquet` + `.meta.json`（`cache.py:61-93`）；`~/.lei_signal_lab/cache/` 58 只 |
| **实际字段与价格口径** | CSV 列实读：`date,symbol,open,high,low,close,volume`。口径 = **名义未复权收盘**（新浪 `getKLineData`，`providers.py:515` `adjusted=False`）。14 只，`2019-09-02..2026-06-30`，非矩形（562590 仅 654 行、513870 仅 643 行） |
| **时间语义** | 观察时间 = `date` 列（隐含收盘）。供应商发布时间 **无**。生效时间 **不适用**。获取时间 **无** —— `fetch-results*.json` 也没有时间戳字段 |
| **已有校验** | `validation.py::validate_bars:40-131` 共 12 项（必需列、数值强转、去重、OHLC 关系、非正价、负量置零、`adjusted=False` 告警、最小行数）。另有 `detect_unadjusted_gaps:134-150`，**未被 validate_bars 调用** |
| **实际消费者** | `factor_runtime.py::build_mixed_batch`、`factor_account_adapter.py::replay_account`、`scripts/run_factor_library_v0.py`、冻结 `full-execution/run.py` |
| **缺口** | ①**无任何获取时间**；②**生成代码未封存**——`source_manifest.source_code_sha256` 经哈希反查指向 `scripts/repro_factor_backtest.py`，不是 raw-responses→prices.csv 的转换脚本，该步不可复现；③**口径只在文档里**，CSV 无 `adjusted`/`provider`/`source` 列；④新浪已因「不复权污染信号」被逐出默认链（`providers.py:889-890`），而冻结数据恰恰全部来自新浪；⑤`validation.py` 不检查交易日历缺口 |
| **本轮处理** | 复用 `validate_bars` + 新增研究侧校验（日历覆盖、口径混用）。**把口径写进快照元数据，不改 CSV**。②③④⑤ 记录为缺口，不在本轮修复 |

**四项分别判断**：文件存在 ✅｜字段齐全 ✅（就其自身 schema）｜历史完整 ⚠️ 非矩形，且无上市日期佐证｜当时可知 ❌ **无获取时间，不可判定**

---

## 2. 公司行动（分红 / 拆分）

| 维度 | 事实 |
|---|---|
| **已有来源** | `action-sources/normalized-actions.json`。原始响应 18 个 `.html` + 33 个 `-table*.csv` + `index.json` + 3 份官方 PDF |
| **获取/读取函数** | 抓取 `action-sources/fetch.py`（天天基金 `fundf10.eastmoney.com/fhsp_{code}.html`）；规范化 `action-sources/normalize.py`（`:21-22` 三条官方拆分**硬编码**、`:23` 停牌硬编码）。研究侧：`factor_runtime.py::_normalized_actions:161-182` |
| **现有缓存或文件** | 顶层 4 键：`schema_version`(1)、`events`(21)、`excluded`(15)、`official_sources`(3)、`limitations`(4) |
| **实际字段** | 实测出现次数：`symbol/type/effective_date/source_url/source_path/source_sha256/event_id` 各 21；`record_date` 20；`ex_date`/`pay_date`/`cash_per_unit` 各 17；`announcement_date` 3；`split_ratio` 3；`halt` 1。类型：`cash_dividend` 17、`split` 3、`trading_halt` 1。**唯一 ID 有**（`event_id` = `{symbol}-{type}-{effective_date}`，21/21） |
| **时间语义** | **5 种日期**：`announcement_date`(3)、`record_date`(20)、`ex_date`(17)、`effective_date`(21，唯一全覆盖)、`pay_date`(17)。**`available_at`：0/21** —— `run_factor_library_v0.py:147-152` 自报 |
| **已有校验** | `normalize.py:19` 窗口过滤；`factor_runtime.py:169-179` split ratio 有限且>0、dividend cash 有限且≥0 否则 raise；`:216-218` 重复 event_id → raise；`controller/full-input-checks.json` 有 3 条拆分的除权前后收益核对 |
| **实际消费者** | `factor_runtime.py:161`、`factor_account_adapter.py:133`、冻结 `full-execution/run.py:29`（并在 `:206` 入 run-lock、`:222` 跑完复核哈希） |
| **缺口** | ①**21/21 缺 `available_at`** → 运行时被迫强制打 `historical_reconstruction_only`（`factor_runtime.py:258-262`）；②`limitations` 自认**无连续官方「无其他行动」证明** —— 没有行动记录 ≠ 已证明无行动；③**官方核查结果未回流**：`515300-official-qualification/` 核实 6/7 次分红（2025-12-12 那次仅二手表），但明确「本目录不修改上游 normalized-actions.json」，registry 里 `mixed_actions` 哈希仍是二手表版本；④`trading_halt` 被 `factor_runtime.py:164` **静默丢弃**；⑤`source_path` 是绝对路径 `/Users/yongbiaoli/…`，不可移植 |
| **本轮处理** | ①保持未知，**不补造**；②③④ 写入校验输出的显式缺口清单（④ 从静默丢弃改为**计数并报告**，不改丢弃行为）；⑤ 快照记录相对路径 + 原绝对路径并存 |

**四项分别判断**：文件存在 ✅｜字段齐全 ⚠️ 5 种日期不齐（`ex_date`/`pay_date` 各缺 4 条）｜历史完整 ❌ 无「无其他行动」证明｜当时可知 ❌ **0/21 有 `available_at`**

---

## 3. 产品身份、资格与交易日期

| 维度 | 事实 |
|---|---|
| **已有来源** | `candidate-pool.json`（9 顶层键，14 candidates × 20 字段全齐） |
| **资格逻辑** | 权威常量 `MINIMUM_QUOTES = 273`（`factor_runtime.py:98`），绑定校验 `:55-58`，判定 `:400-408`（当日有报价 AND `valid_count>=273` AND `isfinite(momentum)`）。另有独立实现 `definitions.py::select_mixed:327-336`、冻结 `full-execution/run.py:66`、复核 `full-review/verify_full.py:41` —— **共 4 处实现同一阈值** |
| **273 vs 253** | 已知且登记：`candidate-pool.json:threshold_reconciliation`（上游代码 253、E3 报告文字 273、采用 273）。上游 253 见 `scripts/repro_factor_backtest.py:284,329` |
| **`valid_count` 语义** | **该产品自身的有效报价条数**，不是交易日数 |
| **交易日历** | ❌ **全项目无真实交易所日历**。`calendar.py:66-106 WeekdayCalendar` 是周一至周五近似且**节假日表为空**（`:74`），`DEFAULT_TRADING_CALENDAR` 即它（`:115`）。混合池实际用「14 只产品报价日期的并集」（`run_factor_library_v0.py:120-143`，`calendar_limitation` 字段自认「无法区分整池缺席日与非交易日」）。另有 `data_provenance.py:218 reference_calendar`，`authority="price_dates_reference"`，自认「不能证明未列出的日期不是交易日」 |
| **上市/退市日期** | ❌ 无。`grep -il "delist\|退市\|listing_date\|上市日期\|trading_calendar"` 在 `full-pool-preparation/*.json\|*.md` **零命中**。只有 `first_nominal_date`（首个实际报价日，**不是上市日**） |
| **缺口** | ①身份自认 `original_e3_membership = "not_proven"`；②池是「当前存续的 14 只」→ **存活偏差**（registry profile `mixed.universe.eligibility` 已自认）；③`local_qfq_path` 指向 `~/.lei_signal_lab/cache/*.bars.parquet`，**机器本地、不在仓库、可被 `ParquetCache.clear()` 删除** |
| **本轮处理** | 校验器中**明确禁止把工作日当交易日**：无合格日历时输出 `calendar_authority="none"` 并把相关用途降级，不静默近似。①②③ 记录不修复 |

**四项分别判断**：文件存在 ✅｜字段齐全 ✅｜历史完整 ❌ 无上市/退市/交易日历｜当时可知 ⚠️ 资格可按当时报价数重算，但缺日历佐证

---

## 4. 输入快照与定义/协议绑定

| 维度 | 事实 |
|---|---|
| **`source-manifest.json`** | 11 个字段实读，含 **7 个哈希**（`prices_sha256`、`candidate_pool_sha256`、`source_code_sha256`、`round6_report_sha256`、`fetch_results_3000_sha256`、`pool_contract_sha256`、`normalized_actions_sha256`）。**无 `schema_version`、无规范版本绑定字段、无 `transform_version`、无 `created_at`/`fetched_at`** |
| **冻结协议** | 三层：`full-protocol.json`（+ `.md` + `.sha256`）；`full-execution/run-lock.json`（`created_before_returns` + 7 路径→哈希，`run.py:206-210` 结果前锁、`:222` 跑完复核）；`mixed-defense/protocol.json:source_files` + `source-checks.json`。**`run.py:211` 有防覆盖**：`run-lock.json` 已存在则改名 `run-lock-attempt-02.json`（但结果 CSV 仍会覆盖） |
| **源哈希核验** | `factor_account_adapter.py`：载入前 `load_frozen_defense:41-55`（`defense_code` 不符即 raise）；调用后 `replay_account:141-145` 复算 4 项（`defense_code/defense_protocol/mixed_prices/mixed_actions`），任一变化即 raise。**无降级、无警告模式** |
| **`validate_registry`** | `definitions.py:84-` 检查：`schema_version=="1.0.0"`、`standard_version=="1.0.0"`、相对路径存在、四区块类型、每个 source **恰好只有 `{path,sha256}` 两键**且格式合法（**只校验格式，不读文件**）、每个 object 展开 profile 后含 15 个必需字段、id/version 正则、sources key 必须已登记。**内容哈希核验是另一个函数** `verify_sources:489-495` |
| **运行时指纹** | `factor_runtime.py:236-244 _input_fingerprint`（prices 7 列 + actions 全量的规范化 JSON sha256）——**内容指纹，非文件哈希**，追加未来数据会变（`test_factor_runtime.py:145` 明确测这个）。`:112-120 contract_digest`（定义卡 4 段 + deps 的 sha256） |
| **运行时质量闸门** | `build_mixed_batch:253-263`：`currency!="CNY"` raise、`price_basis!="nominal_close"` raise、`kind=="breadth_fraction"` raise、**`historical_reconstruction_only` 未置位即 raise**。输出 `metadata["quality"]:364-374` 含 `events_without_available_at`、`point_in_time_availability="not certified…"` |
| **缺口** | ①**`definitions.v1.json:sources` 34 项里没有一项指向 `raw-responses/` 或 fetch 脚本** —— 原始供应商响应不在被核验的绑定链里；②`prices.csv → economic_index` 的转换在**三处独立实现**（`full-execution/run.py:33-51`、`factor_runtime.py:184-234`、`review/*.py`），靠数值比对而非共享代码保证一致 |
| **⚠️ 规范版本绑定限制（如实保留，本轮不改）** | `validate_registry` 硬要求 `standard_version == "1.0.0"`，而 `definition-standard.md` 现为 **1.1.0**；`make_manifest` 硬编码 `principles_version=1.0.0`，而原则现为 **v1.1**。此限制已由 `governance-pack-merge-2026-09-10.md:59` 记录。**本轮不改版本字符串冒充迁移**，只在快照里单列实际采用的文档路径 + 版本 + 当次 SHA-256，并标注机器输出仍显示旧版本 |

**四项分别判断**：文件存在 ✅｜字段齐全 ⚠️ 缺规范版本与转换版本｜历史完整 ⚠️ 原始响应未进绑定链｜当时可知 ❌ 无获取时间

---

## 5. 既有能力：可复用 vs 确实缺失

### ✅ 已有，本轮直接复用（**不重建**）

| 能力 | 路径 |
|---|---|
| **完整的数据引用元信息协议** | `src/lei_signal/data_provenance.py`（646 行，`SCHEMA_VERSION="provenance/1.2"`）：`MarketDataRef` 带 `observed_at/available_at/generated_at/last_valid_at/health/reason/calendar_ref/as_of_cutoff/source_policy_ref`；`file_source_hash:82`；`SourcePolicy:113`（`verified=False` 不参与 fresh 判定）；`reference_calendar:218`；`assess_freshness:266`。设计哲学明写「**unknown 永不当作当前**」「不补造」 |
| 行情抓取与回退 | `data/providers.py`（超时/有限重试/链式回退；失败一律 raise，**不伪装空成功**） |
| 基础 K 线校验 | `data/validation.py::validate_bars`（12 项） |
| 目录防覆盖 | `run_factor_library_v0.py:62-79 fresh_dir()`（已存在则 bump `-NN`） |
| 源哈希核验 / 指纹 | `definitions.py:489 verify_sources`、`:480 fingerprint`、`:541 make_manifest`（强制 `data_cutoff<=available_at<=decision_at` 且三者带时区） |
| 漂移清单 | `run_factor_library_v0.py:86-101 source_status()` |

> **关键发现**：`data_provenance.py` 是本轮所需字段的现成实现，但**只被 `dca/service.py:230` 和 `dca/state.py:256` 使用，因子库链路一行都没接**。本轮走「加薄适配」而非新建。

### ❌ 确实缺失，本轮补

| 缺的能力 | 说明 |
|---|---|
| **行情抓取快照写出器** | 没有任何通用工具把「URL + 请求参数 + 响应体 + 请求/返回时刻 + 哈希」一起落盘。`raw-responses/` + `fetch-results*.json` 是一次性产物，且**连抓取时间都没记** |
| **离线复用读回器** | 无「从已有合法快照完全离线重算」的入口 |
| **研究级质量校验与用途裁决** | `validate_bars` 只做单文件 K 线检查；没有日历覆盖、口径混用、公司行动一致性检查，也**没有「按用途给出可用/有条件可用/不可用」的输出** |
| **跨运行差异检测** | `fresh_dir` 只保证不覆盖，**不比较**。相同请求返回不同内容时无差异留存机制 |

---

## 6. OKR 只读核对（**本轮不改任何里程碑、授权或完成度**）

`~/.lei_signal_lab/system_upgrades.db` 表 `upgrade_goals`（45 条）中相关条目：

| ID | 标题 | 状态 | 与本轮的关系 |
|---|---|---|---|
| `okr-4f4157e2957e` | 因子库后续：外部资源适配与分批接入 | **planned**，`authorization.granted=false`，4 milestone 全 `done:false`，next_action「暂不执行」 | 其 `data` milestone =「明确历史成员、分红拆分或退出数据的实际缺口」——**本表正是该 milestone 要求的缺口盘点**，建议关联为证据，但**不建议改 done 状态**（本轮只盘点缺口，未形成供应商采用/不采用结论） |
| `K-data-boundary` | 核对数据代理与真实可交易条件 | **approved**，3 milestone 全 `done:false` | 授权范围限本地审计，明令「不买数据、不收费调用、不大规模搜索」——与本轮联网上限一致。建议关联 |
| `K-trial-ledger` | 补齐试过哪些规则和版本的记录 | approved | m1 含「**数据版本**」，本轮快照产出可作部分证据 |
| `D-evidence` | 让每个系统结论都有可靠依据 | planned（方向性） | 上述三条的父条目 |

**建议（不执行）**：把本轮报告作为 `okr-4f4157e2957e.data` 与 `K-data-boundary` 的证据链接；
里程碑完成度的改动需另行授权。

---

## 7. 本轮处理 / 延期一览

| 缺口 | 本轮 | 理由 |
|---|---|---|
| 无获取时间语义 | **处理** —— 新抓取记录四类时间；历史快照保持未知 | 核心目标 |
| 无抓取快照写出器 | **处理** —— 新增，复用 `MarketDataRef` | 确实缺失 |
| 无离线复用入口 | **处理** | 核心目标 |
| 无研究级质量校验与用途裁决 | **处理** | 核心目标 |
| 无跨运行差异检测 | **处理** —— 相同请求内容变化时存新快照 + diff | 核心目标 |
| `trading_halt` 静默丢弃 | **处理**（改为计数报告，不改丢弃行为） | 低风险、属校验范畴 |
| 21/21 缺 `available_at` | **保持未知** | 禁止补造 |
| prices.csv 生成代码未封存 | **延期** | 属历史资料修复，需另行授权 |
| 官方核查结果未回流 `normalized-actions.json` | **延期** | 改动冻结输入，超出本轮权限 |
| 无真实交易所日历 | **延期**（但校验器拒绝用工作日近似顶替） | 需新数据源，本轮禁止 |
| 无上市/退市日期 | **延期** | 需新数据源 |
| `validate_registry` 卡死 `standard_version=="1.0.0"` | **延期，如实单列** | 明令不得只改版本字符串冒充迁移 |
| economic_index 三处实现 | **延期** | 触及冻结代码 |
| 存活偏差 | **延期** | 数据资格问题，非本轮可解 |
