# 主控复核四类漏放：修复与重新交付-2026-09-11

> **⚠️ 后续纠正（2026-09-11 第二轮）**：主控另行复现出同范围**三处遗漏**，
> 见 [`research-controller-fixes-2026-09-11-02.md`](research-controller-fixes-2026-09-11-02.md)：
> ① 非法停牌记录（错交易所、账户事件混入、冲突重复、非法区间）先被消费、
> 缺口照样被解释、排序获放行；② `listing_evidence` 只判非空；
> ③ 日历按条数判完整、非法日期键可补足数量。
> 均已修复并固化反例测试。本文保留为历史，其结论在该补充报告的基础上成立。

规范版本：`experiment-backtest-principles.md` v1.1；`definition-standard.md` 1.1.0；
`ai-execution-contract.md` 1.0.0；`experiment-report-template.md` 1.1.0

冻结协议：`docs/experiments/raw/research-controller-fixes-2026-09-11/baseline.json`
（含本轮开始前四个库文件与总报告的 SHA-256）

网络请求：**0 次**。未运行收益回测。未写 OKR。未执行变异检测工具。
未改生产规则、生产符号解析、UI、冻结输入与旧结果；未改定义登记表、
因子公式、参数、产品池或账户路径；0 个登记对象变更。

定义清晰程度 / 数据资格 / 实现核验 / 有效性证据 / 生产授权：

| 项 | 状态 |
|---|---|
| 定义清晰程度 | 不适用——未新增或修改任何登记对象 |
| 数据资格 | **有条件（按修复后的真实测量，见 §2）** |
| 实现核验 | **215 项测试全过**（实跑计数，不沿用旧数字）；ruff 干净；受保护文件零改动 |
| 有效性证据 | 不适用——未检验任何因子、未运行任何账户 |
| 生产授权 | **无** |

研究状态：探索（数据基础修复交付）；**不自行宣布验收通过，交回主控复核。**

---

## 一句话结论（大白话）

**主控挑出了我四处"拦不住"，我逐个复现、修好、并用反例固化成测试。**

我之前在总报告里说"排序和对照的数据缺陷已清零"——**这句话撤回**。
它是建立在四个漏洞上的：

1. **数据被篡改了也能正常用。** 快照的哈希核验明明失败了，系统却照样给"可用"。
   修复后：核验失败的数据一律进不了正常研究用途，两种曾经能绕过的开关都堵死了。
2. **日历说"这个月有"，系统就当"这个月每天都有"。** 其实那个月漏了一天，
   数据里那一天的报价还照常被当成正常的。修复后：月份被请求过不等于每天都有记录，
   漏记的日子上的报价必须被单独拦出来。
3. **一只股票少了一天，被整个池子盖住了。** 只要其他股票那天有数据，
   它缺的那一天就没人发现。修复后：逐个产品查自己的缺口，
   而且"缺"不自动等于"错"或"停牌"，没证据就标"原因未确认"。
4. **公司行动的身份和时间只验了表面。** 写错交易所、符号为空、日期是乱码
   都能混过去。修复后全部实质校验，而且合法行动照样通过，不误伤。

**修正后的真实状态**：描述和诊断可以用；排序和对照各还有 1 项没解决的问题
（11 只产品的"晚上市"缺上市资格证据，**原因保留未知**，不接受开关放行）；
研究信号和归因仍然不能用。**资料不足且被准确拒绝，本身就是正确结果。**

本轮没有测任何因子，没有收益结论。

---

## 1. 问题 → 反例 → 修复 → 测试 → 残余限制

### 必修一：哈希核验失败仍被放行

| 环节 | 内容 |
|---|---|
| 反例（复现成功） | 复制快照 → 把 `510300.SS.csv` 里 `3.904` 改成 `3.905` 且不更新哈希 → `load_snapshot` 得 `verified=False`、`hash_mismatches` 非空 → `check_snapshot` 仍判 `ranking=conditional`，`require_use` 用 `allow_conditional` 或 `accept_structural` **均放行** |
| 失败原因 | `check_snapshot` 从头到尾**不看** `loaded.verified` |
| 修复 | `check_snapshot` 前置完整性闸门：`verified=False` 时追加 BLOCK 级 `snapshot_integrity_failed`（影响全部用途、非结构属性），两种开关都绕不过 |
| 测试 | `test_tampered_snapshot_cannot_be_relabelled_as_usable`（断言篡改真实发生）＋ `test_untampered_snapshot_still_works`（防"一律拒绝"假修复；并保留"查看坏数据排查"路径）＋ 跨模块 `test_failed_load_cannot_pass_anywhere`（六个用途全拒） |
| 残余限制 | 绕过 `check_snapshot` 直接调 `check_prices` 的低层路径不感知完整性——它本来就是测试专用入口 |

### 必修二：日历月份覆盖冒充逐日完整

| 环节 | 内容 |
|---|---|
| 反例（复现成功） | 合成日历 `months_requested` 含 2026-01 但 `days` 缺 2026-01-05 → `status` 返回 unknown（这点原本对），但 `coverage.complete` 为 `True`；含该日报价的输入 `ranking=usable` |
| 失败原因 | `coverage()` 只按"月份是否请求"判覆盖，**不查月内每天都有没有记录**；`_check_against_calendar` 对"日历说不出是什么日子"的日期上的报价**完全不管** |
| 修复 | ① `CoverageReport` 新增 `day_incomplete_months`，`complete` 要求月份全覆盖**且**逐日完整；② 新增 `calendar_days_incomplete`（WARN）与 `quote_on_unknown_calendar_day`（BLOCK，只针对**已覆盖月份内**漏记的日——未覆盖的月份仍由 `calendar_coverage_partial` 处理，不重复报） |
| 测试 | 月内漏日、整月缺失、自报 `exchange_official` 也降级、含未知日报价的输入被拒（`test_controller_fixes.py` 三条）＋跨模块 `test_incomplete_calendar_not_masked_by_complete_snapshot` |
| 残余限制 | 日历来源资格与覆盖完整性分开判断，但来源资格本身仍是自报标签，**只能降级不能升级**；真日历经新规则复核为完整（82 个月、逐日无缺） |

### 必修三：单产品缺报价被全池日期并集掩盖

| 环节 | 内容 |
|---|---|
| 反例（复现成功） | 内存中删 510300 的 2023-02-02 报价，其他产品该日照常 → **findings 前后完全相同** |
| 失败原因 | `_check_against_calendar` 只有全池并集检查，**没有逐产品检查** |
| 修复 | ① 新增 `product_internal_gap`：每只产品在自身首末报价之间的缺失交易日，必须定位到具体产品与日期；缺口标 `cause=unconfirmed`，**不自动等于错误也不自动等于停牌**；② 停牌解释改为**逐日逐产品匹配**（`(裸码, 日期)` 索引），错产品的停牌记录不得用来解释；已匹配的缺口降为 INFO 不计阻断；③ **撤回"晚上市自动算固有属性"**：`starts_after_window` 只有在拿到该产品的上市资格证据（`listing_evidence`）时才标为结构属性，否则保留未知，`accept_structural` 不再放行 |
| 测试 | 单产品中间漏日定位到日期、全池漏日仍报、错产品停牌解释被拒、无上市证据时 `structural=False` 且拒绝放行、有上市证据时才允许（`test_controller_fixes.py` 三条＋更新 `test_research_data_quality.py` 中三个旧测试并新增一条正向测试） |
| 残余限制 | 首次报价之前、最后报价之后的资格不在本检查范围（与上市证据相关，单列）；本地**没有**上市资格证据来源，故当前 `starts_after_window` 一律为未确认 |

### 必修四：公司行动身份和时间只做了表面检查

| 环节 | 内容 |
|---|---|
| 反例（复现成功，四条全中） | 声明池只有 `510300.SS` 时分别传入：`symbol="510300.SZ"`（交易所冲突）、`symbol=None`、`effective_date="garbage"`、`available_at="garbage"`——**attribution 全部仍 usable**，且 `require_available_at=True` 也挡不住乱码 |
| 失败原因 | 行动的 symbol 只比前六位裸码集合（自己上一轮修过声明侧、却漏了行动侧）；日期字段只查"存不存在"，不查"是不是真日期"；`available_at` 完全不验格式 |
| 修复 | ① 行动两侧都走完整身份解析：带后缀形式查交易所冲突（`action_identity_conflict`）；裸六位码**仅当在登记表中唯一映射**才接受，不猜交易所；`None`/空 → `action_missing_identity`；② 全部日期字段（必需＋可选）校验为真实有效日期（`action_bad_date`）；③ `available_at` 必须是**带时区**的合法时刻（`action_available_at_bad_format`），缺失/非法/时点三种情形分开；④ 生效后取得合法（`action_acquired_after_effective`，INFO），不强制早于生效日，但注明"不证明生效日之前已可知" |
| 测试 | 主控四条反例各自固化 + 无时区时刻按非法处理 + 生效后取得合法 + **合法行动正向测试**（不被误伤）＋ 跨模块 `test_bad_action_identity_not_masked_by_good_prices` |
| 残余限制 | "有 `available_at` ≠ 已满足某次历史决策"——决策时点须绑定相应合同，本轮不做该判断；未修订冻结 actions 迁就新校验器：现有 21 条**全部通过**新校验（全部为裸码且有唯一映射、日期格式均合法） |

### 跨模块测试组（§8 要求，全部真实链路）

| 命题 | 测试 | 结果 |
|---|---|---|
| 失败加载结果不能正常放行 | `test_failed_load_cannot_pass_anywhere`：篡改快照 → check_snapshot → 六个用途 require_use 全拒（两种开关同试） | ✅ |
| 不完整日历不能被完整快照掩盖 | `test_incomplete_calendar_not_masked_by_complete_snapshot` | ✅ |
| 错身份行动不能被正确价格身份掩盖 | `test_bad_action_identity_not_masked_by_good_prices`（真实冻结行动 + 一条 `.SZ` 注入） | ✅ |
| 基础检查通过不能冒充动量定义绑定成功 | `test_passing_basic_checks_does_not_satisfy_momentum_definition`：description 放行，但 `mixed.momentum.raw@1.0.0` 仍报缺 `economic_index` | ✅ |

## 2. 修复后的真实状态（重新测量，`final-measurement.json`）

对象不变：规范标签快照 v2（14 只 / 18,916 行）＋ 82 个月日历 ＋ 21 条行动。

| 用途 | 裁决 | 可修缺陷 | 固有属性 | 接受固有属性后 |
|---|---|---|---|---|
| description | 可用 | — | — | 放行 |
| diagnostic | 可用 | — | — | 放行 |
| ranking | 有条件 | **`starts_after_window`（原因未确认）** | — | **拒绝** |
| comparison | 有条件 | **`starts_after_window`（原因未确认）** | — | **拒绝** |
| research_signal | 有条件 | `action_available_at_unknown`、`zero_volume_days` | — | 拒绝 |
| attribution | 有条件 | `action_available_at_unknown`、`zero_volume_days` | — | 拒绝 |

**与修复前结论的差异**：
- 修复前我说排序/对照"可修缺陷清零、只剩固有属性、接受后可放行"——**撤回**。
  实际情况：`starts_after_window` 没有上市资格证据支撑，**不是已确认的固有属性**，
  是原因未确认的问题，不能靠开关放行。
- 512890 在 2021-10-22 的缺口现在被其停牌记录**逐日匹配**，判为已确认事件
  （INFO，不计阻断）；其余产品逐日完整。

**三个层次分开，不得跳层引用**：
① 基础格式/完整性检查——通过（快照哈希、字段结构、OHLC、日历逐日完整）；
② 具体定义所需输入——`mixed.momentum.raw@1.0.0` **仍缺 `economic_index`**，
名义价快照不因①通过而满足该定义；
③ 研究用途证据——见上表逐项裁决。

## 3. 实际命令、退出结果、失败史

```sh
python3 -m pytest tests/unit/test_controller_fixes.py \
  tests/integration/test_controller_fixes_cross_module.py -q
# 修复前：13 个主控反例测试全部失败（预期）；修复后：19 passed（退出码 0）

python3 -m pytest <本轮 2 个测试文件 + 全部既有研究/定义/因子/报告测试> -q
# → 215 passed（退出码 0；实跑计数）

python3 -m ruff check <4 个库文件 + 2 个新测试文件>   # All checks passed!
```

**失败史**（本轮自己的错误，如实记录）：
1. 替换 `check_actions` 循环体时边界设错，**一度把 `check_snapshot` 整个函数删掉**
   （ruff F822 暴露）；它是未提交的新代码，git 无法恢复，按原设计重写。
2. 另一处替换把 event_id/重复/类型/金额检查圈进了删除区间，补丁脚本自身
   `ValueError` 中止且文件未写入——**没有造成半写状态**，改为整段重写。
3. `listing_evidence` 参数双重查找（调用处取一次、内层又取一次），导致证据
   永远落空；修复后旧测试才按新行为通过。
4. `quote_on_unknown_calendar_day` 初版误伤"日历从未覆盖的月份"
   （与 `calendar_coverage_partial` 重复且过度阻断）；收窄为只报"已覆盖月份内
   漏记的日"。
5. 全解释缺口的级别语义：已匹配停牌的缺口起初仍按 WARN 计入阻断项；
   改为 INFO（已确认事件），未解释的才保留 WARN。
6. 测试文件 9 条 lint（长行、未用变量、未用导入）；"before" 变量原本无意义，
   改为复现前置条件断言（删除前 510300 不应已有缺口）。

**未执行**：变异检测工具（本轮明令不在共享工作区运行）；OKR 写入（本轮明令不写）。

## 4. 代码与测试修改清单

| 文件 | 类型 | 内容 |
|---|---|---|
| `src/lei_signal/research/data_quality.py` | 修改 | 完整性闸门（`snapshot_integrity_failed`）；`calendar_days_incomplete` 与 `quote_on_unknown_calendar_day`；逐产品 `product_internal_gap` + 停牌逐日匹配 + 已解释降级；`starts_after_window` 改为需上市证据才标结构属性；`check_actions` 循环体重写（身份、日期、available_at、生效后取得）；`check_snapshot` 恢复并扩展 |
| `src/lei_signal/research/trading_calendar.py` | 修改 | `CoverageReport.day_incomplete_months`；`complete` 要求逐日完整；`days_in_month` 访问器 |
| `src/lei_signal/research/data_snapshot.py` | 未改 | — |
| `src/lei_signal/research/symbol_identity.py` | 未改 | （被复用，未修改） |
| `tests/unit/test_controller_fixes.py` | 新增 | 15 项：主控反例固化 + 正向保护 |
| `tests/integration/test_controller_fixes_cross_module.py` | 新增 | 4 项跨模块守卫 |
| `tests/unit/test_research_data_quality.py` | 修改 | 三个旧测试按新行为更新（提供上市证据）+ 新增一条无证据正向测试 |
| `docs/experiments/research-data-foundation-summary-2026-09-10.md` | **加纠正说明**（原文保留为历史） | 撤回"数据缺陷已清零"等 7 项 |
| `docs/experiments/raw/research-controller-fixes-2026-09-11/` | 新增 | 基线指纹、最终测量 |
| `docs/experiments/registry.json` / `INDEX.md` | 追加一条 | — |

**受保护文件**：前两轮 896 项基线逐文件复核 **零改动**；
冻结 actions、prices.csv、全部冻结实验与前几轮交付未被修改。

## 5. 当前可用 / 受限 / 未核验 / 未接入

| 状态 | 项 |
|---|---|
| **可用** | description、diagnostic（含完整性闸门通过时） |
| **受限（准确拒绝中）** | ranking、comparison（`starts_after_window` 原因未确认）；research_signal、attribution（行动到达时间 + 停牌数据源） |
| **未核验** | 上市资格证据来源（本地没有）；2019—2025 发布时间；上交所逐日数据；跨所 81 个月差异；接口许可 |
| **未接入** | 全部既有消费者（factor_runtime、factor_account_adapter、factor_diagnostics、生产宽度等）仍为 legacy；`mixed.momentum.raw@1.0.0` 仍缺 `economic_index`，**没有伪造接入成功** |

## 6. 本轮之外发现的新问题（登记影响，交主控，不扩项）

1. 主控反例已修，但同类问题可能存在于**其他消费者路径**——本轮四个模块以外的
   代码（如 `factor_runtime` 内部的价格处理）未在本轮复核范围。
2. `listing_evidence` 目前没有任何本地来源；若主控认为"晚上市"需要被正式确认，
   需要一个上市日期数据源（新授权）。
3. `CoverageReport.complete` 语义已变（更严）。若有既有消费者依赖旧的宽松语义
   （当前仓库内未发现调用方），需评估影响。

## 7. 给主控的交接

- 四类反例全部复现并固化：修复前 13 个测试失败（预期），修复后 215 项全过。
- 总报告已加有日期的纠正说明（保留原文历史），**"数据缺陷已清零"已撤回**；
  当前真实状态以本报告 §2 的重新测量为准。
- 一个我自己这轮的新错误值得你知道：替换边界设错时我一度把 `check_snapshot`
  整个函数删掉了，靠 ruff 的 F822 才暴露。这类"大范围文本替换"是我这几轮的
  主要出错方式，后续我会改用更小编辑步长。
- **没有伪造接入成功**：名义价快照仍然满足不了 `mixed.momentum.raw@1.0.0`，
  它缺的 `economic_index` 依然缺。
- 资料不足且被准确拒绝，是本轮的正确结果，不是问题。

**完成上述交付即停止，等待主控独立复核。
不宣布策略有效、因子有效、OKR 完成或获准交易。**
