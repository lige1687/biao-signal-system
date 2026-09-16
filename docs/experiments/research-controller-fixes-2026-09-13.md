# 主控返修单 R1/R2/R3：修复交付-2026-09-13

> **⚠️ 后续纠正（2026-09-13 第二轮，主控复核 v1.1.0）**：主控确认 R2/R3 成立，
> 但 R1 仍有一层未堵住——**哈希一致只证明字节一致，不证明内容为真**：
> 调用方自写的 JSON（哪怕明确标注合成、或省略资格字段）经两个入口仍可放行。
> 本文 §R1 所称"假的进不来"范围过宽，已由
> [`research-controller-fixes-2026-09-13-02.md`](research-controller-fixes-2026-09-13-02.md)
> 纠正：「日期算法自洽」与「可用于真实研究的证据资格」已彻底分开，
> 当前未建立真实资料准入标准，**任何自述/合成记录都不产生结构属性**。
> 本文其余内容保留为历史。

规范版本：`experiment-backtest-principles.md` v1.1；`definition-standard.md` 1.1.0；
`ai-execution-contract.md` **1.0.1**（主控本轮已更新）；`experiment-report-template.md` 1.1.0

依据：主控书面复核报告（返修单，2026-09-13）§3–§6。
基线：`docs/experiments/raw/research-controller-fixes-2026-09-13/baseline.json`——
执行前已核对与主控报告 §1 记录的被审指纹**一致**（`data_quality.py` `fbd3429d…`、
`trading_calendar.py` `4651fa7d…`、round2 测试 `b9a70e77…`、-02 报告 `990004ba…`）。

网络：**0 次**。未运行收益回测、未写 OKR、未运行变异工具、未改生产或冻结输入、
0 个登记对象变更、未新增数据源/依赖/因子/参数/产品池/账户路径。
`trading_calendar.py` 本轮**未改**（其修复已被主控确认）。

定义清晰程度 / 数据资格 / 实现核验 / 有效性证据 / 生产授权：

| 项 | 状态 |
|---|---|
| 定义清晰程度 | 不适用——未新增或修改任何登记对象 |
| 数据资格 | 有条件（与前两轮一致；本轮让"凭假证据放行"的口子被堵上，**真实数据裁决不变**） |
| 实现核验 | **245 项测试全过**（实跑计数）；ruff 干净；受保护文件零改动 |
| 有效性证据 | 不适用——未检验任何因子、未运行任何账户 |
| 生产授权 | **无** |

研究状态：探索（返修交付）；**完成 R1/R2/R3 即交回主控，不启动新一轮扩建。**

---

## 一句话结论（大白话）

**上一轮的修复被主控确认了两项，但还发现两个口子：假的"上市证明"和绕过验证的旁门。这次都堵上了。**

1. **假上市证明能放行。** 之前只要写"这股票哪天上市的"再随便配个来源字符串
   （比如就写个 `dummy`），日期逻辑一通，系统就承认"晚上市属实"，排序就放行。
   修复后：来源必须是一份**能回查的文件**（路径 + 哈希），文件里必须写明
   **同一只股票、同一个上市日期**；文件内容被改过（哈希对不上）立刻失效。
   本地没有这种合格材料，**继续拒绝**——不下载、不编造。
2. **旁门绕过了验证。** 上一轮把"先验证再当证据"做到了主入口里，
   但还有个直接检查价格的入口没接上——从这儿塞一条混了账户流水的"停牌记录"，
   照样能把缺数据解释掉。修复后：两个入口共用同一套验证，非法记录从哪个门都进不来，
   而且混进来这件事**必须被看见**，不能悄悄丢掉。
3. **一个测试一直在错的分支上"通过"。** 我上一轮写"上市日期太早所以拒绝"，
   其实那条用例根本没走到"残余缺口"分支；现在把三种情形分开测：
   上市太早、上市在窗口内但中间缺了该有数据的日子、上市和首份数据同一天，
   各自断言各自的原因。另外纠正我一处错误说法：**"周五上市、周一才有数据算正常"
   这个说法没有证据，已撤回**——上市当天该不该有数据是未知数，按未知处理。

**真实数据的裁决一点没变绿**：描述和诊断可用，其余四项继续被拒。
这轮修的只是"假的进不来"，不是"真的变多了"。

---

## R1：上市日期自洽不能代替来源核验

| 项 | 内容 |
|---|---|
| 修复前反例（复现成功） | 评价期 2026-05-28~06-02，晚出现产品首报价 2026-06-01，传 `{"listing_date": "2026-06-01", "source": "dummy"}` → `structural=True`，`require_use(..., accept_structural=True)` **放行** |
| 根因 | `_validate_listing_evidence` 只验 source 是非空字符串 + 日期自洽，**把"字段合法"当成了"来源已核验"** |
| 最小改动 | `source` 改为必须是可回查引用 `{path, sha256}`：文件须存在、**哈希须一致**（内容变化即拒绝，不得沿用旧结论）、JSON 内须声明**同一产品**（与证据所属产品按完整身份比对）与**同一上市日期**。非空字符串、白名单、自填可信标记一律不算。合成资格记录（`qualification: "synthetic_algorithm_test"`）只验证算法，返回标注 `synthetic=True`，**不是真实市场资格证明** |
| 修复后 | `dummy`、不存在路径、错哈希、错产品、错日期、内容变化后沿用旧哈希，全部拒绝；诊断输出明确写出"来源未核验：<具体原因>；日期与窗口关系成立不代替来源核验" |
| 正向路径 | 合成资格记录（可回查、哈希一致、产品日期匹配）通过算法路径并标注合成；**真实池无任何合格来源，继续拒绝，未伪造"已接入"** |

## R2：直接价格入口不能消费未核验停牌记录

| 项 | 内容 |
|---|---|
| 修复前反例（复现成功） | 直接 `check_prices` 传带 `account_id`/`amount` 的停牌记录 → 缺口被解释 → `ranking=usable`，放行；同一记录走 `check_snapshot` 则正确被拒——**两个入口行为不一致** |
| 根因 | `check_prices` 把 `halts` 原样交给 `_check_against_calendar`；`_halt_index` 假定调用方已核验，但直接入口没人核验 |
| 最小改动 | 新增 `_validated_halts`：直接入口对传入停牌记录做与 `check_snapshot` **同源**的核验（复用 `check_actions`），只有合格记录参与缺口解释；非法记录（账户字段混入、错身份、缺 ID、冲突 ID 及其同 ID 全部记录、非法/倒置区间）**既不得解释缺口，其混入情况也作为 BLOCK 发现保留在报告里**。合法停牌缺少 `available_at` 不阻碍解释（历史时点未知另行声明，不补造） |
| 修复后 | 主控 §7 复跑脚本的三条路径全部表现为拒绝：`direct_no_halt`（conditional/unconfirmed）、`direct_account_event`（拒绝 + `events_passed_as_actions` 可见）、`snapshot_account_event`（拒绝） |
| 接入/未接入 | **本次接入**：`check_prices`（直接入口）、`check_snapshot`（此前已接入，行为不变）。**未接入**：全部既有消费者仍为 legacy；CLI 的 `verify` 子命令不消费 halts，未改动（不因名称相关强制重构） |

## R3：资格起点语义与残余缺口测试

| 项 | 内容 |
|---|---|
| R3.1（测试分支错位） | 我上一轮"残余缺口"用例实际命中的是"上市早于评价期"分支。**修正**：上市日期放进评价期（2026-05-28）、中间确有开市缺报价日（05-29），断言拒绝原因含"残余"且点名残余日 `2026-05-29`；对照组（上市 05-20）断言原因为"早于评价期" |
| R3.2（周五上市语义） | 我上一轮把"周五上市、周一首报价"当作正常（从残余中排除了上市日）。**撤回**：上市当天是否具备报价资格未知，合成日历明确该周五开市，**资格起点未知则保留未知**。残余口径改为"上市日（含当天，若开市）至首报价之间" |
| 受影响的旧测试 | `test_research_data_quality.py` 中三个用"2026-05-29 上市 + 字符串来源"的旧测试，其"自洽"前提已不成立（既过严又过时）；改为上市日=首报价日 + 结构化合成资格记录。round2 的正向例同样改为结构化合成文档 |
| 报告纠错 | 我此前在 -02 报告与函数文档中写"周五上市、周一首次成交属正常，不算缺口"——**该说法无证据支撑，已撤回**（-02 报告顶部已有纠正指针，此处再次记录） |

## 实际命令与结果（实跑计数，不追求固定数字）

```sh
python3 -m pytest tests/unit/test_controller_fixes_round3.py -q
# 修复前：6 个反例测试失败（预期）；修复后：12 passed（退出码 0）

python3 -m pytest \
  tests/unit/test_controller_fixes.py \
  tests/unit/test_controller_fixes_round2.py \
  tests/unit/test_controller_fixes_round3.py \
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
# → 245 passed（退出码 0）

python3 -m ruff check src/lei_signal/research/data_quality.py \
  src/lei_signal/research/trading_calendar.py \
  src/lei_signal/research/data_snapshot.py \
  src/lei_signal/research/symbol_identity.py \
  tests/unit/test_controller_fixes_round3.py \
  tests/unit/test_controller_fixes_round2.py \
  tests/unit/test_research_data_quality.py
# → All checks passed!（先报 1 条未使用导入，--fix 后复跑通过）

# 主控 §7 复跑脚本：逐行实际执行，输出与"返修后应拒绝"一致（见 R1/R2 节）
```

## 前后代码哈希

| 文件 | 修复前（主控被审版） | 修复后 |
|---|---|---|
| `src/lei_signal/research/data_quality.py` | `fbd3429d0bd9c159…` | 已变化（见下） |
| `src/lei_signal/research/trading_calendar.py` | `4651fa7d0e1e20ae…` | **未变**（本轮修复已被确认，未重做） |
| `tests/unit/test_controller_fixes_round2.py` | `b9a70e77f43d0933…` | 已变化（正向例换结构化来源） |

**受保护文件**：896 项基线逐文件复核 **零改动**。

## 影响的真实数据裁决

**与返修前完全一致**（本轮让假证据进不来，没让真数据变多）：

| 用途 | 裁决 | 可修缺陷 | `accept_structural=True` |
|---|---|---|---|
| description / diagnostic | 可用 | — | 放行 |
| ranking / comparison | 有条件 | `starts_after_window`（无合格上市证据） | **拒绝** |
| research_signal / attribution | 有条件 | `action_available_at_unknown`、`zero_volume_days` | 拒绝 |

512890 的停牌解释仍可追溯：`[{'date': '2021-10-22', 'event_id': '512890-halt-2021-10-22'}]`。

## 失败史（本轮自己的错误）

1. **R3 测试最初用字符串来源**，修完 R1 后反而到不了日期分支——
   立刻 4 个测试失败。这本身就是 R1 修对了的证明：不再允许绕过来源核验。
   改为结构化合成资格记录。
2. **旧测试里"周五上市周一报价正常"是我上一轮的过宽口径**，
   主控 R3.2 指出后撤回，按"资格起点未知则保留未知"收紧；
   受此影响的三条旧测试改为同日上市 + 结构化来源。
3. 一处未使用导入（ruff F401），`--fix` 处理。

## 待确认项（交主控）

1. `_validate_listing_evidence` 的引用文档格式是本轮定义的**最小合成格式**
   （`symbol` + `listing_date` + `qualification`）。若日后接入真实上市资料，
   真实文档的 schema 需要主控定义，**不能把本合成格式当作真实资格标准**。
2. "上市当天是否具备报价资格"目前一律按未知处理。若主控取得交易所对
   上市首日交易规则的正式说明，可据此细化残余口径。
3. R2 的接入范围只有 `check_prices` 与 `check_snapshot` 两个研究入口。
   其他可能消费停牌记录的路径（如有）未在本轮排查，主控若有清单可另列。

**完成 R1/R2/R3 即交回主控复核。
不宣布策略有效、因子有效、OKR 完成或获准交易。**
