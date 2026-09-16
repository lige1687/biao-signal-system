# 主控复核剩余三处遗漏：修复补充报告-2026-09-11

> **⚠️ 后续纠正（2026-09-13，主控返修单 R1/R2/R3）**：主控复核确认本报告的
> 停牌验证与日历修复成立，但另行复现两处同类口子与一处测试错位：
> ① `listing_evidence` 的来源只验非空字符串（`dummy` 也能放行）；
> ② 直接 `check_prices` 入口仍消费未核验停牌记录；
> ③ 本文 §1.2 称"周五上市、周一首次成交属正常，不算缺口"——**该说法无证据支撑，
> 已由 [`research-controller-fixes-2026-09-13.md`](research-controller-fixes-2026-09-13.md)
> 撤回并按"资格起点未知则保留未知"收紧**。
> 本文其余内容保留为历史；当前有效结论以 2026-09-13 返修交付为准。

规范版本：`experiment-backtest-principles.md` v1.1；`definition-standard.md` 1.1.0；
`ai-execution-contract.md` 1.0.0；`experiment-report-template.md` 1.1.0

基线：`docs/experiments/raw/research-controller-fixes-2026-09-11-02/baseline.json`
（本轮开始前相关库文件与上一轮修复报告的 SHA-256）

网络请求：**0 次**。未运行收益回测、未写 OKR、未运行变异工具、
未改生产或冻结输入、0 个登记对象变更、未新增数据源/依赖/因子/参数/产品池/账户路径。

定义清晰程度 / 数据资格 / 实现核验 / 有效性证据 / 生产授权：

| 项 | 状态 |
|---|---|
| 定义清晰程度 | 不适用——未新增或修改任何登记对象 |
| 数据资格 | 有条件（与上一轮一致；本轮是**让拒绝变得更准确**，不是变绿） |
| 实现核验 | **233 项测试全过**（实跑计数，不沿用 215 这个数字）；ruff 干净；受保护文件零改动 |
| 有效性证据 | 不适用——未检验任何因子、未运行任何账户 |
| 生产授权 | **无** |

研究状态：探索（修复补充交付）；**完成三处修复及验证即交回主控，不启动新一轮扩建。**

---

## 一句话结论（大白话）

**主控又挑出三处"拦不住"，性质和上次一样：坏东西进来了，系统没拦住还照常放行。**

1. **一份假停牌证明，就能让"缺了一天"变成"已解释"。** 哪怕那份证明写错交易所、
   或者根本不是原始资料（是账户流水混进来的），系统也拿它去解释数据缺口，
   然后排序就又能用了。修复后：**行动记录先验证，只有合格的才允许当证据**；
   错交易所、混入的账户流水、自相矛盾的重复记录、日期写反的区间，全都进不来。
   能当证据的，会记下是哪一条记录（编号可追溯）。
2. **"已上市"三个字就能蒙混过关。** 之前只要给个非空的来源字符串，
   系统就承认"这股票是晚上市的，缺数据正常"。修复后：上市日期必须真实、
   必须和"什么时候开始有数据"对得上；上市日到首份数据之间如果还隔着该有数据的交易日，
   就**不算**解释清楚。本地没有合格来源，就继续拒绝，不编证明。
3. **日历拿条数当完整，乱码日期也能凑数。** 把"1月5日"换成根本不存在的"1月99日"，
   条数没变，系统照样说"这个月完整"。修复后：非法日期在加载时就被剔除并**显式列出**，
   完整性按真实日期集合核对，不再按条数。

**裁决没有变绿**——这三处修复都是让"该拒绝的拒绝得更准"，不是让任何东西变可用。
真实数据的裁决与上一轮完全一致。

---

## 1. 三处反例：修复前 → 修复后

### 一、非法停牌记录先被消费，排序仍获放行

| | 修复前 | 修复后 |
|---|---|---|
| 错交易所停牌（`510300.SZ` 解释 `510300.SS` 的缺口） | 缺口被解释 → `ranking=usable`，require_use 放行 | 行动照常报 `action_identity_conflict`，但**该记录不再参与解释**；缺口保持未确认，排序不放行 |
| 账户事件混入（带 `amount`/`account_id` 字段） | 同上被消费 | 同上被拒（`events_passed_as_actions` 报告不变） |
| 冲突重复（同 event_id 内容不同） | 第一条干净的记录照样解释缺口 | **同一 event_id 整体排除**——冲突意味着这个 ID 下没有可信记录 |
| 倒置/非法区间（start > end、乱码日期） | 照常解释 | `check_actions` 新增对 `halt.start_date/end_date/resume_date` 的验证与区间顺序检查（`action_bad_date`、`action_bad_halt_range`），非法记录被 BLOCK 后自然进不了证据集 |
| 正确产品、错误日期 | 解释失败（原已正确） | 不变 |
| **正向**：合法停牌 | 解释成功 | 解释成功，且 `explained_by` 保留 `event_id` 可追溯引用；同时注明"停牌解释只说明缺口来源，**不等于当时可交易**"，不为历史日期补造 `available_at` |

**根因**：`check_snapshot` 把原始 actions 直接交给价格覆盖检查，`check_actions`
在**之后**才运行；且 `_halt_index` 用前六位截断匹配。
**修法**：行动先核验，未被 BLOCK 的才进入 `valid_halts`；
`_halt_index` 改用完整身份解析（带后缀走 `parse_identity`，裸六位码要求
登记表唯一映射），日期必须真实且区间不倒置。

### 二、`listing_evidence` 仍只是非空开关

| | 修复前 | 修复后 |
|---|---|---|
| `{"source": "dummy"}` | `structural=True`，随后放行 | 拒绝：缺 `listing_date`；**source 字符串非空本身不构成来源合格** |
| `{"listing_date": "2000-01-01"}` | 同上 | 拒绝：**评价期前已上市，解释不了评价期后才有报价** |
| 上市日期晚于首报价 | 同上 | 拒绝：自相矛盾 |
| 上市至首报价之间有应有报价日 | 同上 | 拒绝：残余缺口不得整体免除（残余 = 上市日与首报价**严格夹着**的交易日；周五上市、周一首次成交不算缺口） |
| 缺日期 / 非法日期 | 同上 | 拒绝 |
| **正向**：合成证据自洽（上市日=首个交易日，明确标记"仅算法测试"） | — | 允许 `structural=True`；合成来源**不是**真实市场资格证明 |

**修法**：新增 `_validate_listing_evidence`——最小证据结构
（合法 `listing_date` + 非空 `source` 引用）+ 三个自洽条件
（≥ 评价期起点、≤ 首报价、残余为零）。无日历可核残余时一律不标结构属性（安全侧）。
**本地没有合格来源，真实池继续拒绝**，与上一轮一致。

### 三、日历按条数判断完整，非法日期能补足数量

| | 修复前 | 修复后 |
|---|---|---|
| `2026-01-05` 换成 `2026-01-99`（条数不变） | `coverage.complete=True` | 非法日期键加载时剔除并列入 `invalid_records`；完整性按真实日期集合核对，`complete=False` 且报告非法记录 |
| 部分月份区间查询 | — | 区间完整性只看「查询区间 ∩ 该月」；整月完整性单列 `month_incomplete_months`，**不混为一谈** |
| 闰日 2024-02-29 | — | 合法，不误判（正向测试） |
| 下游质量判断 | 同样被骗 | `test_downstream_quality_also_catches_invalid_calendar`：非法日历下 `ranking` 不得可用 |

**修法**：加载时校验每个日期键为真实日期（非法剔除并显式列出，不悄悄消失）；
覆盖核对用真实日期集合而非字符串前缀计数；未知日期不作休市。

## 2. 合法输入正向路径（防"一律拒绝"假修复）

- 未篡改快照照常工作（沿用上轮测试）；
- 合法停牌解释成功且可追溯（`test_legal_halt_explains_with_traceable_reference`）；
- 自洽合成上市证据被接受（`test_coherent_synthetic_listing_evidence_is_structural`）；
- 完整日历、闰日、部分区间查询的完整性判定正确；
- **真实冻结数据**：21 条行动全部通过新校验（无一条被误 BLOCK）；
  512890 的停牌解释仍可追溯：`[{'date': '2021-10-22', 'event_id': '512890-halt-2021-10-22'}]`；
  真日历 `complete=True`、`invalid_records=0`。

## 3. 实际命令与结果

```sh
python3 -m pytest tests/unit/test_controller_fixes_round2.py -q
# 修复前：12 个反例/正向测试失败（预期）；修复后：18 passed（退出码 0）

python3 -m pytest \
  tests/unit/test_controller_fixes.py \
  tests/unit/test_controller_fixes_round2.py \
  tests/integration/test_controller_fixes_cross_module.py \
  tests/unit/test_research_data_quality.py \
  tests/unit/test_research_data_snapshot.py \
  tests/unit/test_research_calendar_and_identity.py \
  tests/integration/test_research_offline_loop_round2.py \
  tests/integration/test_research_data_snapshot_cli.py \
  tests/unit/test_research_definitions.py \
  tests/unit/test_factor_runtime.py \
  tests/unit/test_factor_diagnostics.py \
  tests/unit/test_factor_account_adapter.py \
  tests/unit/test_experiment_reports.py -q
# → 233 passed（退出码 0；实跑计数，不把 215 当固定目标）

python3 -m ruff check \
  src/lei_signal/research/data_quality.py \
  src/lei_signal/research/trading_calendar.py \
  src/lei_signal/research/data_snapshot.py \
  src/lei_signal/research/symbol_identity.py \
  tests/unit/test_controller_fixes_round2.py
# → All checks passed!
```

## 4. 失败史（本轮自己的错误）

1. **我把一个测试断言写错了**：用 `allow_conditional=True` 断言拒绝——
   但那个开关本来就是"调用方显式接受有条件"，设计就该放行。
   真正要堵的是 `accept_structural`。已改正，并在修复前先把这条从失败列表里澄清，
   没有把它当成"发现的缺陷"。
2. **冲突重复的第一条记录是干净的、照样解释了缺口**——初版修复只排除了
   被抓到的那条；意识到同一个 event_id 出现冲突内容时**该 ID 下全部记录都不可信**，
   改为按 event_id 整体排除。
3. **残余缺口的口径初版过严**：把上市日当天也算进残余（周五上市、周一首次成交
   会被误判为有缺口）。改为严格夹着的交易日，并补了正向例。

## 5. 修改清单与指纹

| 文件 | 类型 | 内容 |
|---|---|---|
| `src/lei_signal/research/data_quality.py` | 修改 | `check_snapshot`：行动先核验、仅合格记录进证据集、event_id 冲突整体排除；`_halt_index`：完整身份解析 + 日期与区间验证 + 可追溯引用；`check_actions`：停牌区间与嵌套日期验证（`action_bad_halt_range`）；`_validate_listing_evidence`：实质证据核验；`_check_one_price_frame` 增加 calendar 参数 |
| `src/lei_signal/research/trading_calendar.py` | 修改 | 加载时剔除非法日期键并列入 `invalid_records`（附 `_invalid_keys` 集合）；覆盖按真实日期集合核对；区间完整性与整月完整性分开（`month_incomplete_months`）；非法日期查询如实返回未知 |
| `src/lei_signal/research/data_snapshot.py` / `symbol_identity.py` | 未改 | （复用，未修改） |
| `tests/unit/test_controller_fixes_round2.py` | 新增 | 18 项：三处反例 + 正向保护 |
| `docs/experiments/research-controller-fixes-2026-09-11.md` | **顶部加纠正指针** | 保留历史 |
| `docs/experiments/raw/research-controller-fixes-2026-09-11-02/` | 新增 | 基线指纹 |
| `docs/experiments/registry.json` / `INDEX.md` | 追加一条 | — |

**受保护文件**：896 项基线逐文件复核 **零改动**。
**代码指纹变化**（相对本轮基线）：`data_quality.py`、`trading_calendar.py`、
上一轮修复报告（加指针）CHANGED；`data_snapshot.py`、`symbol_identity.py` 未变。

## 6. 当前受限用途与未接入项

**与上一轮一致**（本轮修复不改变真实数据裁决）：

| 状态 | 项 |
|---|---|
| 可用 | description、diagnostic |
| 受限（准确拒绝中） | ranking、comparison（`starts_after_window` 原因未确认）；research_signal、attribution（行动到达时间 + 停牌数据源） |
| 未接入 | 全部既有消费者仍为 legacy；`mixed.momentum.raw@1.0.0` 仍缺 `economic_index`，未伪造绑定成功 |

## 7. 范围外发现（登记，不扩项）

1. `_validate_listing_evidence` 的最小证据结构只覆盖"晚上市"这一类；
   其他固有属性（若有）没有对应的证据核验，届时需各自定义，**不能复用这个开关**。
2. `check_actions` 现在会 BLOCK 非法停牌区间；若历史输入中存在这类记录，
   该产品的缺口解释会相应减少——这是预期行为，但若某份历史研究曾依赖
   "被错误解释的缺口"，其结论需要按新口径重看（当前真实数据只有 1 条合法停牌，无影响）。
3. 本轮只修了主控复现的三处；**同类型的其他输入路径**（如未来新增的证据类参数）
   应按同样标准设计，而不是继续"先消费后验证"。

**完成三处修复及验证即交回主控复核。
不宣布策略有效、因子有效、OKR 完成或获准交易。**
