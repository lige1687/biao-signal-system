# 研究数据获取、快照与质量校验-2026-09-10

规范版本：`experiment-backtest-principles.md` v1.1（SHA-256 `ac5a676c0635441b…`）

策略规格版本：不适用——本轮不产生任何交易判定，未触及 `docs/trading-spec-v1.md` 的道路/路牌/A-D 触发。

规则账本版本：不适用——未读取也未修改 `configs/rules.v1.yaml`。

冻结协议：`docs/experiments/raw/research-data-provenance-2026-09-10/protocol.json`（SHA-256 `6501779e959e93f3…`）

定义规范与登记表：`definition-standard.md` v1.1.0（`3406feaea2bbb8d2…`）；
`definitions.v1.json` 容器 1.2.0（`c008efb991c40f06…`），实测 **81 个对象 / 34 个 source / models 0**。

执行合同：`ai-execution-contract.md` v1.0.0（`2de83d71ec4ea6e6…`）；模板 1.1.0（`cae2853f81841de6…`）

对象引用：本轮**不新增、不修改任何登记对象**。仅以只读方式解析
`mixed.price.economic@1.0.0`、`mixed.momentum.raw@1.0.0`、`breadth.csi300.b200.common@1.0.0`
用于绑定判定（结论见 §5）。所有既有实现仍为 `legacy`，本轮不改其状态。

实验 manifest：每个输出目录内的 `snapshot.json`（含对象/代码哈希、输入快照与指纹、
数据截止、四类时间、质量状态、允许与禁止用途、生产未授权标记）。
**历史到达时间未知处一律写未知。**

定义清晰程度 / 数据资格 / 实现核验 / 有效性证据 / 生产授权：

| 项 | 本轮状态 |
|---|---|
| 定义清晰程度 | **不适用**——未新增定义对象；只对既有对象做只读绑定判定 |
| 数据资格 | **有条件**——冻结混合池价格与行动可用于描述与诊断；`attribution` 受限（21/21 缺 `available_at`）；无合格交易日历 |
| 实现核验 | **通过**——66 项新测试全过（手算期望），63 项既有回归全过，ruff 干净；855 个受保护文件聚合哈希前后一致 |
| 有效性证据 | **不适用**——本轮不检验任何因子、不产生收益结论 |
| 生产授权 | **无** |

研究状态：探索（数据基础工程交付）

生产与真实交易授权：无。

---

## 一句话结论（大白话）

我们现在能说清楚每一份研究数据**是从哪儿来的、什么时候取的、完不完整、当时能不能拿到**，
而且这些话有文件和哈希可查，不是凭印象。

**补上的**：一套「取数/导入 → 存快照 → 查质量 → 完全离线重跑」的闭环。
它会把来源地址、请求参数、请求和返回的精确时刻、原始响应原文、每个文件的指纹全部存下来，
重复运行绝不覆盖旧证据，数据变了会留下新旧两份和差异说明。

**仍然缺的**（本轮明确不补，不是忘了）：
21 条公司行动**全部没有"当时几点能知道"这个时间**，所以我们只能说这是历史重建，
不能说当时就拿得到；整个仓库**没有一份真正的交易所日历**，所以"某天该不该有行情"这类判断
一律降级处理，绝不拿"周一到周五"糊弄过去。

**顺带查出一个真问题**：冻结数据里的代码写成 `510300.SH`，而仓库自己的代码认的是 `510300.SS`——
两套写法各自都能跑，但**一旦按代码把两边数据拼起来，会得到空的结果而且不报错**。已加入校验拦截。

**这一轮没有测任何因子，没有任何收益结论，也不构成"数据已经合格"或"可以真实交易"。**

---

## 1. 决策问题与停止条件

- 资金用途：不适用。本轮不安排任何资金。
- 持有周期：不适用。
- 本轮回答的问题（开工前写死在 `protocol.json`）：
  数据从哪里来？取得了哪个版本？是否完整？当时是否可知？
  同一输入能否重复使用？资料异常能否明确失败，而不悄悄污染研究？
- **通过条件**：上述六问对至少一条真实链路有可查证的答案，且失败路径确实失败。
- **停止条件**：接口不支持有界请求、许可不明或需扩大范围 → 停联网分支，完成离线适配并列明缺口。
- **明确不作为完成标准**：新增因子、提高收益、取得更多数据。

## 2. 事实与缺口表

完整表见 [`raw/research-data-provenance-2026-09-10/facts-and-gaps.md`](raw/research-data-provenance-2026-09-10/facts-and-gaps.md)，
覆盖四类对象（名义价格 / 公司行动 / 产品身份资格与交易日期 / 输入快照与定义协议绑定），
每类按 8 个维度逐项列出，并对「文件存在 / 字段齐全 / 历史完整 / 当时可知」**分别判断**。

四类的「当时可知」一栏结论：

| 对象 | 文件存在 | 字段齐全 | 历史完整 | **当时可知** |
|---|---|---|---|---|
| 名义价格 | ✅ | ✅ | ⚠️ 非矩形 | ❌ 无获取时间 |
| 公司行动 | ✅ | ⚠️ 日期不齐 | ❌ 无「无其他行动」证明 | ❌ **0/21 有 available_at** |
| 产品身份与资格 | ✅ | ✅ | ❌ 无上市/退市/日历 | ⚠️ 缺日历佐证 |
| 快照与绑定 | ✅ | ⚠️ 缺规范/转换版本 | ⚠️ 原始响应未进绑定链 | ❌ 无获取时间 |

## 3. 修改文件与真实调用链

**全部为新增文件，未修改任何既有文件**（`git status --short` 全为 `??`）：

| 文件 | SHA-256 | 职责 |
|---|---|---|
| `src/lei_signal/research/data_snapshot.py` | `1bd91ede1d97be8d…` | 获取/导入、快照、离线复用、差异、定义绑定 |
| `src/lei_signal/research/data_quality.py` | `905ac3474dc2288f…` | 质量校验与按用途裁决 |
| `scripts/run_research_data_snapshot.py` | `05eacef64356d570…` | 单一命令入口 |
| `tests/unit/test_research_data_snapshot.py` | — | 24 项 |
| `tests/unit/test_research_data_quality.py` | — | 35 项 |
| `tests/integration/test_research_data_snapshot_cli.py` | — | 7 项 |

**实际复用了什么**（不是重写）：

| 复用组件 | 用法 |
|---|---|
| `data_provenance.py::MarketDataRef` / `file_source_hash` / `SourcePolicy` | 四类时间语义与来源指纹。**该模块此前只被 `dca/` 使用，因子链路一行未接**——本轮是它第一次进入研究数据链路 |
| `data/providers.py::SinaPriceProvider` | 抓取。通过其 `opener` 注入点包一层记录器，拿到 URL/时刻/原始响应，**未改动 provider 一行** |
| `data/validation.py::validate_bars` | K 线基础校验（12 项），不重复实现 |
| `data/symbols.py::resolve_symbol` / `is_a_share` | 产品代码规范性检查 |
| `research/definitions.py::load_registry` / `resolve` | 定义解析。**不建第二份登记表** |
| `research/factor_runtime.py::contract_digest` | 契约摘要，不另写一份 |

**自行实现了什么，以及为什么**：

- 抓取快照写出器与离线复用读回器——仓库确实没有（`raw-responses/` 是一次性产物，连抓取时间都没记）。
- 研究级质量校验与用途裁决——`validate_bars` 只做单文件 K 线检查，不做日历覆盖、口径混用、行动一致性，也不输出按用途的裁决。
- `fresh_dir`——与 `scripts/run_factor_library_v0.py:62-79` 语义一致。该脚本有顶层
  `sys.path.insert` 与 `sys.dont_write_bytecode` 副作用，按 v0 计划「导入旧脚本前检查顶层副作用」
  的告诫不宜作为库导入，故重实现。**如实登记为必要重复**，非缺口。

## 4. 输入/输出快照、版本与来源指纹

四个输出目录，全部新建、无覆盖：

| 目录 | 模式 | 内容 |
|---|---|---|
| `example-fullpool/` | 导入 | 冻结全池 14 只 × 18,916 行 |
| `example-import/` | 导入 | 2 只子集（演示池外行动被阻断） |
| `example-acquire/` | **联网** | 510300.SS / 515300.SS 各 60 行 |
| `example-acquire-01/` | **联网** | 同上重复运行（演示防覆盖 + 差异检测） |

**导入侧身份核对**：`example-fullpool` 记录的源文件 SHA-256 为 `de467734…`，
与冻结 `source-manifest.json:prices_sha256` **完全一致**；行数 18,916 与其 `rows` 字段一致。
源文件按只读处理，运行前后字节不变。

**联网侧实际记录**（节选 `example-acquire/snapshot.json`）：

```
url: …CN_MarketData.getKLineData?symbol=sh510300&scale=240&ma=no&datalen=60
requested_at: 2026-09-10T16:07:12.103942+00:00
returned_at:  2026-09-10T16:07:12.250372+00:00
observed_at   = 2026-09-10
available_at  = None
generated_at  = 2026-09-10T16:07:12.257980+00:00
fetched_at    = 2026-09-10T16:07:12.250372+00:00
health        = unknown
reason        = 来源发布节奏未核实（SOURCE_POLICIES 为空）；对外可用时刻未知，不用抓取时刻顶替
```

**这是本轮最关键的一条纪律**：`fetched_at` 精确到毫秒，`available_at` 仍然是 `None`。
知道什么时候取到，不等于知道当时能不能取到。

## 5. 定义与调用绑定：诚实结果是「还不够」

`bind_definitions` 用**机械可判**的方式（对象 `input.fields` ⊆ 本批提供字段）判断能否直接满足，
不解释卡里的散文。实测（`purpose="description"`）：

| 对象 | 直接可满足 | 原因 |
|---|---|---|
| `mixed.price.economic@1.0.0` | ❌ | 缺 `economic_index` |
| `mixed.momentum.raw@1.0.0` | ❌ | 缺 `economic_index` |
| `breadth.csi300.b200.common@1.0.0` | ❌ | 缺 `P_signal`、`membership_by_date`；且单位无量纲，不接受价格行 |
| `mixed.momentum.raw@9.9.9` | ❌ | 拒绝：unknown exact definition version |
| `nonexistent.object@1.0.0` | ❌ | 拒绝：unknown exact definition version |

**结论：名义价快照直接满足不了混合池中任何一个对象**——它们都要 `economic_index`，
必须先把名义价与公司行动连接起来。这是如实报告，不是失败；
**本轮不把任何消费者标为「已接入」。**

用途闸门同样生效：以 `purpose="diagnostic"` 解析这些卡会被 `resolve` 拒绝
（`diagnostic` 不在其 `uses` 内）。

**actions 与 events 严格分开**：校验器对带 `account_id`/`event`/`amount` 字段的记录直接阻断
（`events_passed_as_actions`）。本轮**不运行账户**，也不从账户事件倒推原始行动。

## 6. 质量校验实际输出

对冻结全池 14 只 + 21 条行动的裁决：

| 用途 | 裁决 |
|---|---|
| description | 可用 |
| diagnostic | 可用 |
| ranking | **有条件** |
| research_signal | **有条件** |
| attribution | **有条件** |
| comparison | **有条件** |

阻断产品：**无**。发现 16 warn + 1 info：

| 代码 | 次数 | 含义 |
|---|---|---|
| `symbol_convention_mismatch` | 13 | `.SH` 写法不被仓库 `resolve_symbol` 判为 A 股（第 14 只 `159652.SZ` 正常） |
| `no_qualified_calendar` | 1 | 无合格交易日历，不推断缺失交易日 |
| `action_available_at_unknown` | 1 | 21/21 缺到达时间，只能历史重建 |
| `zero_volume_days` | 1 | 零成交量日，无停牌数据源可区分 |
| `coverage_unproven` | 1 | **没有行动记录不等于已证明没有行动** |

**只阻断受影响部分**已验证：一只标的有非正价时，同批另一只干净标的不受牵连（单元测试
`test_bad_instrument_does_not_block_the_good_one`）。

## 7. 实际测试命令、通过/失败/未执行

```sh
python3 -m pytest tests/unit/test_research_data_snapshot.py \
  tests/unit/test_research_data_quality.py \
  tests/integration/test_research_data_snapshot_cli.py -q
# → 66 passed（退出码 0）

python3 -m pytest tests/unit/test_research_definitions.py tests/unit/test_factor_runtime.py \
  tests/unit/test_factor_diagnostics.py tests/unit/test_factor_account_adapter.py \
  tests/unit/test_experiment_reports.py -q
# → 63 passed（退出码 0）

python3 -m ruff check <本轮 6 个文件>
# → All checks passed!
```

覆盖到的分支：正常小例 / 乱序 / 重复 / 重复冲突 / 空响应 / 字段缺失 / 超时 / 错误响应 /
有限重试 / 请求上限（预检与运行中各一）/ 非正价 / 无穷值 / NaN / OHLC 非法 / 负成交量 /
零成交量 / 预热不足 / 评价期为空 / 起点晚于评价期 / 代码错配 / 口径混用 / 声明缺失 /
分红零值与负值与无穷 / 拆分比例边界 / 重复行动 ID / 冲突行动 ID / 缺 event_id / 缺必需日期 /
未声明字段不被当作每份分红 / 未知类型 / 池外产品 / available_at 缺失（warn 与 block 两档）/
events 混作 actions / 离线复用一致 / 快照被篡改可检出 / 目录防覆盖 / 差异分历史修订与仅追加 /
错版本与不存在对象的拒绝路径。

**失败史**：开发中出现两次真实失败，均已修复并保留在此：
1. 测试初版用 `510300.SH`，被 `resolve_symbol` 判为非 A 股导致 12 项失败——
   **这不是测试写错，而是暴露了冻结数据与仓库代码的代码约定冲突**，据此新增了 `symbol_convention_mismatch` 检查。
2. 篡改检测测试初版用 `glob("*.csv")` 取到的是 `512890.SS.csv`，其中没有待替换的字符串，
   文件实际未变、哈希自然仍匹配，测试假通过——改为指定文件并加 `assert tampered != original` 自检。

**未执行**：Alphalens / Qlib 均未安装未运行（本轮明确不引入）；
未跑任何账户、任何收益回测、任何参数搜索。

## 8. 完整示例：获取或导入 → 快照 → 校验 → 离线复用

```sh
# 1) 导入冻结全池（只读源文件）→ 自动出快照与质量报告
python3 scripts/run_research_data_snapshot.py import \
  --csv docs/experiments/raw/research-rotation-clean-2026-09-09/full-pool-preparation/prices.csv \
  --actions .../action-sources/normalized-actions.json \
  --warmup-rows 273 \
  --out docs/experiments/raw/research-data-provenance-2026-09-10/example-fullpool

# 2) 完全离线读回并重新校验（逐文件核哈希）
python3 scripts/run_research_data_snapshot.py verify \
  --snapshot docs/experiments/raw/research-data-provenance-2026-09-10/example-fullpool \
  --warmup-rows 273
# → verified: True，裁决与首次一致
```

联网闭环同样跑通（见 §4）：**2 只标的、60 个交易日、共用 4 次请求**
（首次 2 次 + 重复运行 2 次），上限 10 次；未写生产缓存、未新增凭据或供应商。
重复运行落入 `example-acquire-01/`，差异检测返回 `identical: true`。

## 9. 原冻结输入与结果未被改动的证据

运行前记录 855 个受保护文件的逐文件与聚合 SHA-256
（`raw/research-data-provenance-2026-09-10/protected-baseline.json`），
覆盖 5 个冻结 raw 目录 + 登记表 + 5 个 research 模块 + 5 个 data 模块 + 规则账本 + v0 脚本。

```
baseline aggregate: 8f79d84bdfec072f32dc3232250873f04fa545a6d08afe5b91d767d6ccd21715
current  aggregate: 8f79d84bdfec072f32dc3232250873f04fa545a6d08afe5b91d767d6ccd21715
changed: (无)
```

## 10. 已接入 / 未接入消费者与用途限制

**已接入（真实调用且被测试）**：仅本轮新增的三个文件互相调用，以及它们对
`data_provenance` / `providers` / `validation` / `symbols` / `definitions` 的只读调用。

**未接入（仍为 legacy，本轮不改其状态）**：
`factor_runtime.build_mixed_batch`、`factor_account_adapter.replay_account`、
`factor_diagnostics`、`run_factor_library_v0.py`、所有生产宽度与全 A 日常计算、
所有冻结实验脚本。**本轮没有把任何既有消费者改为使用新快照。**

**用途限制**：快照 `uses = [description, diagnostic, comparison]`，
`not_for = [production_trade, 宣称历史时点可交易, 作为复权价格使用]`。

## 11. 已知的规范版本绑定限制（如实单列，本轮不改）

`validate_registry` 硬要求 `standard_version == "1.0.0"`，而 `definition-standard.md` 现为 **1.1.0**；
`make_manifest` 硬编码 `principles_version=1.0.0`，而原则现为 **v1.1**。
已由 `governance-pack-merge-2026-09-10.md:59` 记录。

**本轮不改这些版本字符串冒充迁移。** 处理方式：在 `snapshot.json` 与本报告头部
显式记录实际采用的文档路径、版本与当次 SHA-256，并声明机器输出仍显示旧版本。

## 12. 需要另外授权的数据、接口或下一任务

1. **取得一份可核验的 A 股交易日历**（最高优先）。来源不预设：交易所官方公告、
   akshare、baostock、Qlib 数据组件应放在一起比较资格，不因来自大厂就当权威。
   这是当前最卡的缺口——它同时限制 `ranking`、`research_signal`、`comparison` 三个用途。
2. **公司行动到达时间**：现有 21 条无 `available_at`。要么找到带发布时间的来源，
   要么永久接受「只能历史重建」。
3. **官方核查结果回流**：`515300-official-qualification/` 已核实 6/7 次分红，
   但明确不修改上游 `normalized-actions.json`。回流属于改动冻结输入，需单独授权。
4. **`prices.csv` 生成代码封存**：`source_code_sha256` 经哈希反查指向
   `scripts/repro_factor_backtest.py`，不是转换脚本；raw-responses → prices.csv 不可复现。
5. **隔离环境评估 alphalens-reloaded**（固定版本、Apache-2.0）——见待办 v1.1.0 的修正条件。
6. **代码约定统一**：`.SH` vs `.SS`。本轮只做检测拦截，未统一，因为统一会改动冻结输入。

## 13. OKR 只读核对（**本轮无任何写入**）

只读查询 `~/.lei_signal_lab/system_upgrades.db` 表 `upgrade_goals`（45 条）：

| ID | 状态 | 与本轮关系 | **建议**（未执行） |
|---|---|---|---|
| `okr-4f4157e2957e` 因子库后续：外部资源适配与分批接入 | planned，`authorization.granted=false`，4 milestone 全 `done:false` | 其 `data` milestone =「明确历史成员、分红拆分或退出数据的实际缺口」 | 关联本报告为证据。**不建议勾选完成**——本轮只盘点缺口，未形成供应商采用/不采用结论 |
| `K-data-boundary` 核对数据代理与真实可交易条件 | approved，3 milestone 全 `done:false` | 授权范围「不买数据、不收费调用、不大规模搜索」与本轮联网上限一致 | 关联为证据；完成度不改 |
| `K-trial-ledger` 补齐试过哪些规则和版本的记录 | approved | m1 含「数据版本」，本轮快照可作部分证据 | 关联；不勾选 |

**本轮未调用任何写入 API，未改 `docs/okr/initial.json`。**

## 14. 最小决策卡

| 必答项 | 本轮答案 |
|---|---|
| 决策与资金用途 | 不安排资金。消除的决策障碍是：此前无法说清研究数据的来源、版本、完整性与当时可知性，因而任何因子结论的资料资格都无法被审计 |
| 基准与增量 | 不适用——本轮无收益实验、无对照账户 |
| 收益解释 | 不适用——本轮不产生任何收益数字 |
| 代价与执行 | 新增 3 个源文件 + 3 个测试文件，零新增依赖，未改任何既有文件；联网共 4 次请求 |
| 证据与结论 | **证据充分但范围有限**：闭环可复现、失败路径确实失败、受保护文件未变。数据资格结论为**有条件可用**：描述与诊断可用，`ranking`/`research_signal`/`attribution`/`comparison` 均有条件 |
| 下一步与边界 | 最能改变判断的一件事：**取得可核验的 A 股交易日历**（它同时解锁三个受限用途）。未获准冻结观察，未获准生产采用。停止条件：若交易日历无法取得合格来源，相关用途永久保持降级，不用工作日近似顶替 |

---

## 限制与不可推导的结论

- 接口跑通 **不等于** 策略有效。
- 算术一致（哈希匹配、行数一致）**不等于** 历史时点已证实。
- 测试通过 **不等于** 获准真实交易。
- 本轮**不自行宣布全部数据已合格**，交回主控复核。
- 联网分支只证明该接口在本次可有界取得 60 日数据，**不证明**其历史数据的时点合法性，
  也不构成对该供应商的资格认证。
