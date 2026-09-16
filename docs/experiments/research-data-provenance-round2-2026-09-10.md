# 数据基础第二轮：独立复核、交易日历与研究身份映射-2026-09-10

规范版本：`experiment-backtest-principles.md` v1.1；`definition-standard.md` 1.1.0；
`ai-execution-contract.md` 1.0.0；`experiment-report-template.md` 1.1.0

冻结协议：`docs/experiments/raw/research-data-provenance-round2-2026-09-10/`（本轮独立目录，未覆盖上一轮）

登记表：`definitions.v1.json` 容器 1.2.0，81 对象 / 34 source（本轮**不新增、不修改任何对象**）

工作区：Git HEAD `91c720ed46ad95237dcbc56575ac122ab606edd8`；运行前 `git status --short` 已存
61 项修改 + 195 项未跟踪（**属于其他任务，本轮未覆盖、未清理**），快照见
`raw/.../workspace-status-before.txt`

对象引用：只读解析 `mixed.price.economic@1.0.0`、`mixed.momentum.raw@1.0.0`、
`trend.sma200@1.0.0` 用于绑定判定。所有既有消费者仍为 `legacy`。

定义清晰程度 / 数据资格 / 实现核验 / 有效性证据 / 生产授权：

| 项 | 状态 |
|---|---|
| 定义清晰程度 | 不适用——未新增定义对象 |
| 数据资格 | **有条件（较上一轮有实质改善但未解除）**：日历从「完全没有」变为「22/82 个月有官方来源」；身份写法冲突已可显式对齐；公司行动可得时间仍为 0/21 |
| 实现核验 | **通过**——本轮 31 项新测试 + 上一轮 66 项 + 既有 63 项全过；库代码 ruff 干净；896 个受保护文件核对，上一轮 855 项零改动 |
| 有效性证据 | 不适用——未检验任何因子、未运行任何账户 |
| 生产授权 | **无** |

研究状态：探索（数据基础工程 + 独立复核）

生产与真实交易授权：无。

---

## 一句话结论（大白话）

**上一轮说的话，我用不一样的方法重新查了一遍，大体都对，但发现了一个我自己上一轮留下的坑。**

三件实事：

1. **拿到了真的交易日历。** 从深交所官方接口取了 22 个月，共 664 天，每天都标明是不是交易日。
   拿它跟我们冻结的价格数据一对，**一处冲突都没有**——官方说休市的日子我们确实没有行情，
   官方说开市的日子我们也确实有。这同时验证了两边。
   还确认了一件容易搞错的事：**周末调休上班的日子，股市照样不开门**（样本里 0 个例外）。

2. **`.SH` / `.SS` 那个坑堵上了。** 现在有一张显式的对照表，明确说 `510300.SH` 和 `510300.SS`
   是同一只产品，映射前后产品数、行数、日期范围都对得上账。**但不猜**：六位裸码不给后缀就直接报错，
   写错交易所（比如把深交所的 159652 写成 `.SH`）也直接报错。

3. **发现我上一轮的一个真缺陷。** 上一轮我用 855 个文件的聚合哈希证明"冻结文件没被改"，
   数字是对的——但我**只记了结果，没记算法里的排序规则**。这台机器默认中文 locale，
   用命令行工具照着算会得到**完全不同的哈希**，一个独立复核的人可能因此误判成文件被篡改。
   本轮已补上完整算法说明。

**仍然不能做的事没有变**：公司行动 21 条**全部**没有"当时几点能知道"，所以归因用途依然不放行；
日历只覆盖 82 个月里的 22 个，剩下 60 个月一律是"未知"，**绝不因为它是周二就当交易日**。

**本轮没有测任何因子，没有跑任何账户，没有任何收益结论。**

---

## 1. 独立复核表

**方法纪律**：期望值不来自被测代码。文件哈希用系统 `shasum`，行数用 `awk`/标准库 `csv`，
聚合哈希用 shell 重新实现，离线性用 socket 拦截证明。

| # | 上一轮主张 | 独立证据 | 结果 |
|---|---|---|---|
| 1 | 冻结输入 14 只、18,916 行，哈希 `de467734…` | `shasum -a 256` 得 `de467734be6c2ccb…b850`，与 `source-manifest.json:prices_sha256` **逐字符相同**；`awk` 计得 18,916 行、14 只，逐只行数（1652/1652/1651/1648/1640/1626/1489/1470/1362/1321/1286/822/654/643）全部吻合；日期 2019-09-02 → 2026-06-30 | ✅ **确认** |
| 2 | 快照可完全离线读回 | 写 `no_network_guard.py` 替换 `socket.socket`/`create_connection`/`getaddrinfo`/`gethostbyname`，**先自证守卫有效**（守卫下建 socket 抛 `NetworkBlocked`），再在守卫下运行 `verify` → `verified: True`，六个用途裁决与联网时逐项一致 | ✅ **确认** |
| 3 | `fetched_at` 与 `available_at` 明确区分 | 遍历 4 个快照共 20 条 `MarketDataRef`：`available_at` 非空 **0 条**；acquire 模式 `fetched_at` 有值 4 条；import 模式 `fetched_at` 有值 **0 条**（导入不冒充「本次取得」） | ✅ **确认** |
| 4 | 行动缺时间、日历缺口如何影响用途 | 见 §4 的用途裁决表；本轮进一步把「有条件」变成**必须显式承担**（`require_use` 默认拒绝 conditional） | ✅ **确认并强化** |
| 5 | 错版本 / 不存在对象 / 不允许用途确实拒绝 | 独立调用：`@1.0.1`、`@9.9.9`、`nosuch.object@1.0.0` 均 `unknown exact definition version`；`purpose=attribution` 对 `mixed.momentum.raw@1.0.0` → `attribution not allowed`；非精确版本 `mixed.momentum.raw` → `BindingRejected` | ✅ **确认** |
| 6 | 受保护文件哈希清单与聚合算法可复算 | 用 `shasum` + `sort` 重算 855 项：默认 locale（`zh_CN.UTF-8`）得 `8da2bfc9…`，**与记录不符**；改用 `LC_ALL=C sort` 得 `8f79d84b…`，**与记录完全一致** | ⚠️ **数字正确，但算法说明不完整——见下** |

### 复核发现 #1（本轮唯一缺陷，已修）

**问题**：上一轮 `protected-baseline.json` 只记录了聚合值，**未记录排序规则**。
聚合依赖按路径的 Unicode 码点排序；在非 C locale 下用 shell 复算会得到不同结果，
独立复核者可能因此误判文件被篡改。

**性质**：研究专用产物的**文档缺陷**，不涉及生产或冻结内容，属可修复范围。
数字本身没有错，冻结文件确实未被改动。

**修复**：本轮 `protected-baseline.json` 增加 `aggregate_algorithm` 段，
逐项写明 per_file、line_format、ordering（明确等价 `LC_ALL=C sort`）、join、aggregate。
保留上一轮原文件不改，作为失败证据。

### 四项新增独立期望值检查

| 要求 | 实现 | 结果 |
|---|---|---|
| 一次确实改变内容的篡改 | `test_byte_level_tamper_is_detected`：复制快照后把 `3.904` 改成 `3.905`，并 `assert tampered != original` 自检确有改动 | ✅ 检出，`verified=False` |
| 一个错误代码映射 | `test_conflicting_exchange_is_rejected`：159652 登记于深交所，写成 `.SH` | ✅ 抛 `IdentityError`（冲突） |
| 一个假工作日 / 真实休市日 | 2024 春节 6 个工作日休市、2025 国庆 6 个工作日休市；样本内周末被标为交易日的 **0 天** | ✅ 全部识别 |
| 资料不足却试图升级用途 | `require_use(report, "attribution")` | ✅ 抛 `UseNotPermitted`，理由含 `available_at`；且 `conditional` 默认不放行 |

---

## 2. 交易日历：来源、覆盖、冲突与资格

### 2.1 来源比较

| | 来源 A | 来源 B | 尝试但失败 |
|---|---|---|---|
| 类别 | **交易所官方** | 可追溯的本地数据组件 | 交易所官方 / 工具上游 |
| 发布方 | 深圳证券交易所（SZSE） | 本地冻结价格日期并集 | 上海证券交易所；新浪（akshare 上游） |
| 原始链接 | `http://www.szse.cn/api/report/exchange/onepersistenthour/monthList?month=YYYY-MM` | `data_provenance.py:218 reference_calendar`（`authority="price_dates_reference"`） | `query.sse.com.cn/commonQuery.do`（2 个 sqlId）；`finance.sina.com.cn/realstock/company/klc_td_sh.txt` |
| 发布时间 | **未知**——接口只给结果，不给该安排的公布时刻 | 不适用 | — |
| 获取时间 | 逐次记录于 `calendar.json:calls[].requested_at/returned_at` | 不适用 | 同左 |
| 覆盖区间 | 抽样 22 个月 / 664 天 / 389 个落在冻结区间的交易日 | 冻结区间全部 | 无 |
| 修订说明 | 接口未提供修订历史 | 无 | — |
| 许可 | 交易所公开接口，未见明示研究使用条款——**未核**，采用前需另查 | 本地自有 | — |
| 失败原因 | — | — | SSE 两个 sqlId 均返回 `result: null` / `SOA service is null`；新浪返回**混淆编码**的日期串（akshare 用私有算法解码），逆向超出本轮范围且脆弱 |

**字段语义**：`jyrq` = 日期，`jybz` = 交易标志（`1` 交易日 / `0` 非交易日，含周末与法定休市）。

**请求预算**：上限 30，**实际用 27**（探源 3 + 定向抓取 22 + SSE 重试 2）。逐次记录 URL、
请求与返回时刻、HTTP 状态、响应体 SHA-256 与原文。

### 2.2 两个必须分开的问题

| 问题 | 本轮能否回答 |
|---|---|
| **事后确认某日是否开市** | ✅ 能（在已覆盖的 22 个月内）。历史日期对齐用这个 |
| **当时是否已经知道后续开休市安排** | ❌ **不能**。来源只给结果，不给该安排的发布时刻。`TradingCalendar.schedule_known_at()` **一律返回 unknown 并说明原因** |

**推论**：任何规则若要提前利用未来的开休市安排（例如"长假前减仓"），
**不得**以本轮日历为依据，必须另行取得公告发布时间。

### 2.3 验收结果

| 验收项 | 结果 |
|---|---|
| 春节 | 2024-02：`02-09`（除夕，周五）、`02-12`~`02-16` 共 **6 个工作日休市**；`02-19` 恢复交易 |
| 国庆 | 2025-10：`10-01`~`10-03`、`10-06`~`10-08` 共 **6 个工作日休市**；`10-09` 恢复 |
| 周末调休 ≠ 开市 | 664 天样本中，**被标为交易日的周末 = 0 天** |
| 区间边界 | `2019-09-02`（冻结起点）与 `2026-06-30`（终点）均为交易日；起点当日冻结数据只有 3 只有报价（其余未上市） |
| 区间外查询 | `2018-05-15`（周二）返回 `unknown` + "不回退为工作日"；`2027-03-01` 同 |
| 来源冲突 | 与冻结价格对照：官方称交易日却整池零报价 **0 天**；官方称休市却有报价 **0 天** |
| 休市 vs 单产品缺报价 | 已覆盖月份内 389 个交易日中，**248 天属"部分产品无报价"**（未上市/停牌），正确归类为产品原因而非休市 |

### 2.4 覆盖缺口（不伪称全覆盖）

冻结区间共 **82 个月**，本轮覆盖 **22 个**，缺 **60 个**。
未覆盖月份的每一天都返回 `unknown`，**不回退为普通工作日**。
校验器对此输出 `calendar_coverage_partial` 警告并降级相关用途。

**日历补齐不自动解除其他限制**：公司行动可得时间仍未知，归因用途仍不放行。

---

## 3. 研究身份映射

**问题性质判定**：这是**代码形式（后缀写法）**问题，不是交易所识别错误，也不是产品身份错误。
`510300.SH` 与 `510300.SS` 指同一只上交所产品，只是后缀约定不同。

**实现**：`src/lei_signal/research/symbol_identity.py`（研究专用，**未改生产 `resolve_symbol`，未改冻结输入**）

- 显式登记本轮 14 只产品（13 只 SSE + 1 只 SZSE），不做全局字符串替换
- 三层身份并存：`raw`（逐字保留）/ `bare_code` / `canonical`（仓库规范写法）
- 拒绝而非猜测：缺后缀、未知后缀、未登记产品、交易所冲突、重复身份、重复代码 → 全部 `IdentityError`

**账目核对**（`audit_mapping`）：映射前后产品数 14→14、行数 18,916→18,916、
日期范围 2019-09-02 ~ 2026-06-30 一致，`balanced=True`；映射后 14 只**全部**可被生产
`resolve_symbol` 认成 A 股。

**空交集检测**：对侧给 `["510300.SS","515300.SS"]` 时，映射后报"共有产品 2 个"；
对侧给不同产品时报"空交集——按代码合并将得到空结果，必须先统一写法"。

> **身份匹配成功 ≠ 价格口径、公司行动或历史可得时间合格。** 这三项各自独立，未因映射而改善。

---

## 4. 小型离线闭环

产物：`raw/research-data-provenance-round2-2026-09-10/offline-loop/loop-result.json`
（`accounts_run: 0`——**未运行任何收益账户路径**）

| 步骤 | 结果 |
|---|---|
| 1 快照 + 指纹 | `verified: True`，14 只 / 18,916 行 |
| 2 身份映射 | `balanced: True`，与 `.SS` 侧共有产品 2 个 |
| 3 日历 | 覆盖 22 月 / 缺 60 月；与价格零冲突 |
| 4 质量 + 行动 | 见下表 |
| 5 定义绑定 | 三个对象**全部 `directly_satisfiable: false`**，缺 `economic_index` |
| 6 用途请求 | description ✅ / diagnostic ✅ / ranking ❌ / research_signal ❌ / attribution ❌ / comparison ❌ |

**一个能走通的合法检查**：`require_use(report, "description")` → 放行。

**一个因资料不足被正确拒绝的请求**：`require_use(report, "attribution")` →
`UseNotPermitted`，理由 `action_available_at_unknown: 21/21 条行动缺少 available_at…`。

**绑定继续被拒**：名义价缺 `economic_index`，三个对象全部不满足。
**没有为了展示成功而改卡片要求、补造字段或偷换价格口径。**

**价格与每份现金分红同步缩放**（`test_price_and_per_unit_dividend_scale_together`）：
名义价 ×10 且每份分红 ×10 时，经济指数逐值不变；
**反例**——只缩价格不缩分红时，末值确实不同（经济含义已变，不得要求不变）。

**events 与 actions 来源**：`actions` 来自
`full-pool-preparation/action-sources/normalized-actions.json` 的 `events` 列表（原始公司行动公告）。
已实测该文件**不含**任何 `account_id`/`event`/`amount` 字段；
伪造一条账户事件混入后校验器立即报 `events_passed_as_actions`。
**本轮不运行账户，因此不存在真正的账户 events，也未从账户事件倒推原始行动。**

---

## 5. 其他缺口有界盘点（只核本地证据）

| 缺口 | 本地证据 | 下一步（未执行） |
|---|---|---|
| 公司行动原始可得时间 | 21 条 events，`available_at` **0 条**；`announcement_date` 仅 3 条（均为拆分）。文件自带 4 条 limitations，含"无连续官方无其他行动证明"、"515300 分红金额/日期来自二手汇编，采用前需官方验证" | 需带发布时间的来源；或永久接受"只能历史重建"。**本轮未采购、未追溯** |
| 官方核查结果如何回流 | `515300-official-qualification/qualification.md` 明写"本目录不修改上游 `normalized-actions.json`"；登记表 `mixed_actions` 哈希 `097043b2c622a308…` 与当前文件实际哈希**完全一致** → **确认未回流** | 回流属改动冻结输入，需单独授权 |
| `prices.csv` 生成代码是否已封存 | `source_manifest.source_code_sha256 = 3dcb1696…`，全仓反查命中 `scripts/repro_factor_backtest.py`，该文件**不含 `prices.csv` 引用** → **确认不是转换脚本，生成链未封存** | 需原作者提供或重新封存。**不得凭现有 CSV 倒推生成过程** |

Alphalens 与 Alpha158 保留既有待办（`factor-library-external-backlog-2026-09-09.md` v1.1.0），
**本轮未安装、未运行、未增加能力**。

---

## 6. 测试命令与实际结果

```sh
python3 -m pytest tests/unit/test_research_calendar_and_identity.py \
  tests/integration/test_research_offline_loop_round2.py -q      # 31 passed
python3 -m pytest tests/unit/test_research_data_snapshot.py \
  tests/unit/test_research_data_quality.py \
  tests/integration/test_research_data_snapshot_cli.py -q        # 66 passed（上一轮回归）
python3 -m pytest tests/unit/test_research_definitions.py tests/unit/test_factor_runtime.py \
  tests/unit/test_factor_diagnostics.py tests/unit/test_factor_account_adapter.py \
  tests/unit/test_experiment_reports.py -q                       # 63 passed（既有回归）
python3 -m ruff check <本轮 3 个库文件 + 2 个测试文件>            # All checks passed!
```

**失败修复史**：
1. `audit_mapping` 中 `raw` 变量未使用 → ruff `B007`，已改为遍历 `.values()`，复跑通过。
2. `raw/` 目录下两个一次性核验脚本有 7 条 ruff 提示（E501 行长、E402 导入位置）。
   **未修**——它们是已产出证据的脚本，改动会使其哈希与所产出结果对不上。如实记录，不假称干净。

**未执行**：Alphalens / Qlib 未安装未运行；未跑账户、收益回测、参数搜索。

---

## 7. 保护文件核对与修改清单

`raw/research-data-provenance-round2-2026-09-10/protected-baseline.json`：**896 个文件**
（上一轮 855 项 + 上一轮全部交付产物 41 项）。

- **上一轮 855 项中被改动的：无**
- 本轮聚合 `fbfae8e3bbe735a363c16622737026f721805467fbca87b3eaa909bd8c3a4846`
- **算法已完整写明**（per_file / line_format / ordering=码点序，等价 `LC_ALL=C sort` / join / aggregate）

**本轮修改清单**：

| 文件 | 类型 |
|---|---|
| `src/lei_signal/research/symbol_identity.py` | 新增 |
| `src/lei_signal/research/trading_calendar.py` | 新增 |
| `src/lei_signal/research/data_quality.py` | **修改**（新增 `require_use`/`UseNotPermitted`/`_check_against_calendar`，`check_prices` 增 `calendar` 参数；原有 35 项测试全过，行为向后兼容） |
| `tests/unit/test_research_calendar_and_identity.py` | 新增 |
| `tests/integration/test_research_offline_loop_round2.py` | 新增 |
| `docs/experiments/raw/research-data-provenance-round2-2026-09-10/**` | 新增（独立目录，未覆盖上一轮） |
| `docs/experiments/research-data-provenance-round2-2026-09-10.md` | 新增 |
| `docs/experiments/registry.json` / `INDEX.md` | 追加一条 |

**未接入**：所有既有消费者（`factor_runtime`、`factor_account_adapter`、`factor_diagnostics`、
`run_factor_library_v0.py`、生产宽度与全 A 计算、冻结实验脚本）仍为 `legacy`，
**本轮未改任何一个去使用新日历或新映射。**

---

## 8. 提交主控的五个结论

**① 上一轮哪些陈述得到独立确认，哪些需要纠正？**
六项主张中 **5 项完全确认**（文件身份、离线性、时间语义区分、用途影响、拒绝路径）。
**1 项需要纠正**：受保护文件聚合哈希的**数字正确但算法说明不完整**——未写排序规则，
非 C locale 下 shell 复算结果不同，可能被误判为篡改。已补齐算法说明，原文件保留为失败证据。

**② 日历解决了哪些具体问题，仍不能解决什么？**
*解决*：22 个月内可事后确认开市与否；确认周末调休不开市；能把"休市"与"单产品缺报价"分开
（389 个交易日中 248 天属后者）；与冻结价格零冲突，双向互证。
*不能解决*：① 60 个月未覆盖，一律未知；② **完全无法回答"当时是否已知后续开休市安排"**——
来源不提供发布时刻，任何提前利用未来休市安排的规则都不能以此为据；③ 只有深交所，
未取上交所，跨所差异未核；④ 接口许可条款未核。

**③ 产品身份对齐是否可靠，影响哪些研究消费者？**
在**已显式登记的 14 只**范围内可靠：账目平衡、14 只全部可被生产解析、冲突与歧义均拒绝。
超出这 14 只即拒绝，不外推。
*影响的消费者*：**目前一个都没有**——本轮未把任何既有消费者改为使用它。
它解除的是"未来把冻结数据与仓库口径数据合并时会静默空交集"这一风险，不是已发生的修复。

**④ 哪些对象现在仍不能合法使用，为什么？**
- `mixed.price.economic@1.0.0`、`mixed.momentum.raw@1.0.0`、`trend.sma200@1.0.0`：
  **缺 `economic_index`**——名义价必须先与公司行动连接，本轮不做该连接。
- `breadth.*`：缺 `P_signal`、`membership_by_date`，且单位无量纲，不接受价格行。
- 用途层面：`ranking`/`research_signal`/`comparison` 因日历覆盖不全与代码写法不一致而受限；
  `attribution` 因 **21/21 缺 `available_at`** 而受限。
- **`production_trade` 在本登记表中根本不是允许用途**，任何情况下不放行。

**⑤ 下一步最值得单独授权的一件事？**
**把交易日历补到覆盖冻结区间的全部 82 个月，并同时取得该日历的发布时间证据。**
理由：它是唯一一个**同时**解锁三个受限用途（ranking / research_signal / comparison）的缺口，
本轮已证明来源可用、格式稳定、与我方数据零冲突，剩下的只是覆盖量（约需 60 次请求）与
发布时间这一项新证据。相比之下，公司行动可得时间只影响 `attribution` 一个用途，
且很可能根本取不到。

---

## 9. 最小决策卡

| 必答项 | 本轮答案 |
|---|---|
| 决策与资金用途 | 不安排资金。消除的障碍：上一轮结论此前只有执行者自述，现有独立证据；且此前"无日历"和"代码写法冲突"两个硬缺口有了可用工具 |
| 基准与增量 | 不适用——无收益实验、无对照账户 |
| 收益解释 | 不适用——不产生任何收益数字 |
| 代价与执行 | 新增 2 个库文件 + 2 个测试文件，修改 1 个库文件（向后兼容）；零新增依赖；联网 27 次（上限 30） |
| 证据与结论 | **证据充分、范围明确**。资料资格仍为**有条件可用**，但受限原因从"完全没有日历"变为"日历覆盖 22/82 个月"——性质从缺失变为不足 |
| 下一步与边界 | 见结论 ⑤。未获准冻结观察，未获准生产采用。停止条件：若日历无法补到全覆盖，未覆盖月份永久保持未知，不用工作日近似顶替 |

---

## 限制与不可推导的结论

- 日历可用 **不等于** 数据合格；`attribution` 仍不放行。
- 身份对齐成功 **不等于** 价格口径、公司行动或历史可得时间合格。
- 零冲突 **不等于** 两个来源都正确——只说明它们互不矛盾。
- 独立复核通过 **不等于** 策略有效、因子有效或获准交易。
- 本轮**不自行宣布最终验收通过**，交回主控复核。
