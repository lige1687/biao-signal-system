# 因子开工前：研究输入离线验收入口-2026-09-13

规范版本：`experiment-backtest-principles.md` v1.1；`definition-standard.md` 1.1.0；
`ai-execution-contract.md` 1.0.1；`experiment-report-template.md` 1.1.0

任务：`research-input-preflight-2026-09-13`（研究家族 research-data-foundation，计划 v1.0.0）
冻结协议：`docs/experiments/raw/research-input-preflight-2026-09-13/protocol.json`
基线与消费者清单：同目录 `baseline.json`、`consumer-map.md`

网络 **0 次**；新增依赖 0；账户路径 0；未运行收益回测；未写 OKR；未运行变异工具；
0 个登记对象变更；未改生产或冻结输入。

定义清晰程度 / 数据资格 / 实现核验 / 有效性证据 / 生产授权：

| 项 | 状态 |
|---|---|
| 定义清晰程度 | 不适用——未新增或修改任何登记对象 |
| 数据资格 | 有条件（与此前一致；本入口如实呈现，不改变它） |
| 实现核验 | **281 项测试全过**（15 个既有回归文件 + 2 个新文件，实跑计数）；ruff 干净；896 项保护基线零改动 |
| 有效性证据 | **不适用——本轮未计算收益**（资金贡献、政策增量、风险因子解释同此） |
| 生产授权 | **无** |

研究状态：探索（研究输入工程与检查接入）；**完成即交主控复核，不自行宣布因子第一波可以开工。**

---

## 一句话结论（大白话）

**以后开始因子研究，不用再凭一份"通过报告"或几个标签开工了。**

现在有一条命令，跑一遍就告诉你四件以前要翻半天才知道的事：

1. **这是哪批数据**——哪个文件、多少行、哪 14 只、哈希是多少，有没有被改过；
2. **能用于什么**——六种用途逐个给出结论和原因，不是一个笼统的"合格"；
3. **缺什么**——想要算动量？它告诉你缺 `economic_index`（名义价里没有它，
   也没有谁把收盘价改个名字糊弄过去）；
4. **哪些旧程序还没接上**——一张清单写明谁在用、谁没在用。

三次真实运行：**描述用途通过（退出 0）**；**加上三个对象后被拒（退出 2）**——
因为三个对象都要 `economic_index`，而这批数据没有；**请求排序也被拒（退出 2）**——
排序自身的数据条件就不满足，而且动量同样缺字段。
"被拒"在这里是有价值的检查结果，不是坏了——它阻止的是"拿着不够格的数据开工"。

**它不是什么**：不算因子、不算收益、不做预测、不给"合格"盖章。
它说"描述可用"不等于说"你能拿它做研究"——那是另一层，由对象自己的定义卡决定。

---

## 1. 交付物

| 项 | 路径 |
|---|---|
| 薄编排库 | `src/lei_signal/research/input_preflight.py`（`inspect_input` + `combine_checks`） |
| 命令入口 | `scripts/check_research_input.py`（退出码 0 满足 / 2 被拒 / 3 失败） |
| 单元测试 | `tests/unit/test_research_input_preflight.py`（7 项） |
| CLI 边界测试 | `tests/integration/test_research_input_preflight_cli.py`（21 项） |
| 协议/基线/消费者清单 | `docs/experiments/raw/research-input-preflight-2026-09-13/` |
| 三次真实检查 | 同目录 `attempt-01-03/`、`attempt-02-02/`、`attempt-03-02/`（各含 preflight.json/preflight.md/manifest.json） |

**复用而非新建**：完整性核验（`load_snapshot`）、日历（`TradingCalendar`）、
质量与用途裁决（`check_snapshot`/`require_use`）、定义登记与绑定
（`definitions`/`bind_definitions`）。没有新价格公式、新质量规则、
来源信任平台、因子库或回测引擎。`combine_checks` 只是本次请求的合取，
不是可信标签入口，命令行不接受调用方传布尔值。

## 2. 四个独立结果（不合并）

| # | 结果 | attempt-01-03 | attempt-02-02 | attempt-03-02 |
|---|---|---|---|---|
| 1 快照是否完整 | | ✅ 14 只 / 18,916 行 / verified | ✅ | ✅ |
| 2 数据是否满足所请求用途 | description ✅ | description ✅ | ranking ❌（conditional，`starts_after_window` 原因未确认） |
| 3 对象是否允许且输入满足字段 | （无 refs） | ❌ 三对象全部缺 `economic_index` | ❌ `mixed.momentum.raw` 缺 `economic_index` |
| 4 已计算 / 有效 / 获准交易 | **全否** | 全否 | 全否 |

退出码：0 / 2 / 2，与计划预计一致。
**名义价缺 `economic_index` 是本轮的核心事实**——三个指定对象
（`mixed.price.economic@1.0.0`、`mixed.momentum.raw@1.0.0`、`trend.sma200@1.0.0`）
的字段检查全部停在这里；没有任何东西把收盘价改名补足。

## 3. 消费者接入表（沿用 Task 1 清单，交付后状态）

| 消费者 | 状态 | 说明 |
|---|---|---|
| **`scripts/check_research_input.py`（本入口）** | **已接入** | 第一个把"完整性 → 用途闸门 → 对象绑定"串起来的消费者 |
| `scripts/run_research_data_snapshot.py::_run_quality` | **legacy** | 走旧的"调用方声明口径"路径（不传日历对象、不走用途闸门）；本轮未改 |
| 同脚本 `cmd_bind` | **legacy** | 绑定基于 `NORMALIZED_FIELDS` 常量而非实际快照；本轮未改 |
| `scripts/run_factor_library_v0.py` + `factor_runtime` | **frozen legacy** | v0 冻结计算链，只映射，不迁移、不倒填合规版本 |
| 其余全部既有消费者 | **legacy** | 无任何既有消费者调用 `check_snapshot`/`require_use`（除测试） |

**未伪造接入**：本入口是新增消费者，不声称旧程序已合规；
不恢复已被否决的"合成材料等于真实资格"逻辑。

## 4. 数据缺口 → 影响哪个用途

| 缺口 | 影响的用途 | 为什么不能被绕过 |
|---|---|---|
| 缺 `economic_index`（名义价未与行动连接） | 三个指定对象的字段检查；`ranking`/`research_signal`/`attribution` 的对象层 | 连接需要把名义价与 21 条公司行动按登记规则合成——那是**计算**，本轮不做；把 close 改名是造假 |
| 公司行动到达时间（21 条 0/21 有 `available_at`） | `research_signal`、`attribution` | 需要带发布时间的来源；哈希和自填标记都不能代替 |
| 停牌数据源（本地仅 1 条记录） | `research_signal`、`attribution`（零成交量日无法区分） | 同上 |
| 上市资格证据（本地无合格来源） | `ranking`、`comparison`（`starts_after_window` 保持未确认） | 自述/合成记录不获得真实资格（主控 v1.1.0 已定论） |
| 产品池非矩形（11 只晚于评价期起点上市） | `ranking`、`comparison` 的可比性 | 结构性，补数据改不了，只能声明 |
| 日历仅深交所、发布时间仅 2026 年、跨所仅一个月 | 日历相关判断的适用范围 | 需要另一所数据与各年公告，另行授权 |

## 5. 下一阶段最小资料需求表（只做需求，不采集）

| 需求 | 现有本地证据 | 缺哪条原始事实 | 影响哪项判断 | 为何不能由哈希/自填标记代替 | 建议验收方式 |
|---|---|---|---|---|---|
| **economic_index 生成与绑定** | 名义价快照（完整）+ 21 条行动（格式合法） | 把两者按登记规则连接的**计算结果**及其验证 | 三个指定对象能否被满足；动量/趋势/经济价能否进入研究 | 它不是资料问题而是**未做的计算**；自填字段是造假 | 定义规则卡 + 手算小例（分红×拆分共存）+ 与冻结旧输出逐值比对；需单独授权（属计算任务） |
| **公司行动到达时间** | 3 条拆分有 `announcement_date`（下界） | 18 条完全无时点；全部缺带时区的真实到达时刻 | `research_signal`、`attribution` | 下界≠到达时刻；自填 available_at 是补造 | 带发布时间的公告来源 + 抽样核对 3 条已有下界 |
| **停牌数据源** | 1 条官方停牌记录（512890，已验证可解释唯一缺口） | 全市场停牌/复牌序列 | 零成交量日判定；`research_signal`、`attribution` | 单条记录证明不了"其他日子没停牌" | 交易所或数据商停牌表 + 与既有 1 条核对 |
| **上市资格证据** | 无 | 各产品上市日期与资格起点（上市当天是否可交易） | `ranking`、`comparison` 的 `starts_after_window` | 主控 v1.1.0：自述/合成不获得真实资格；哈希只证字节一致 | 主控先定义"什么算真实合格来源"，再按该标准采集 |

以上均**不自动选供应商、不建信任白名单**；每项需单独授权。

## 6. 实际命令与结果

```sh
python3 scripts/check_research_input.py \
  --snapshot docs/experiments/raw/research-identity-wiring-2026-09-10/canonical-snapshot-v2 \
  --calendar docs/experiments/raw/research-calendar-completion-2026-09-10/calendar-merged/calendar.json \
  --publication docs/experiments/raw/research-calendar-completion-2026-09-10/publication-evidence.json \
  --actions docs/experiments/raw/research-rotation-clean-2026-09-09/full-pool-preparation/action-sources/normalized-actions.json \
  --registry docs/research/definitions.v1.json \
  --start 2019-09-02 --end 2026-06-30 --use description \
  --out docs/experiments/raw/research-input-preflight-2026-09-13/attempt-01-03
# EXIT=0（仅描述请求满足；四项受限不隐藏）

# attempt-02-02：同上 + --refs mixed.price.economic@1.0.0 mixed.momentum.raw@1.0.0 trend.sma200@1.0.0 → EXIT=2
# attempt-03-02：--use ranking --refs mixed.momentum.raw@1.0.0 → EXIT=2

python3 -m pytest <15 个既有回归文件> tests/unit/test_research_input_preflight.py \
  tests/integration/test_research_input_preflight_cli.py -q
# → 281 passed（退出码 0；实跑计数，不追求固定数字）

python3 -m ruff check src/lei_signal/research/input_preflight.py \
  scripts/check_research_input.py tests/unit/test_research_input_preflight.py \
  tests/integration/test_research_input_preflight_cli.py
# → All checks passed!
```

**重复运行稳定性**：同一请求两次运行，integrity/data_uses/objects/findings/
request_satisfied/errors 完全一致（有测试）；仅生成时刻与输出位置等明确易变字段不同。

**断网验证**：子进程内封锁 socket（guard 先自证有效）后完成合法检查（有测试）。

## 7. 失败史（本轮自己的错误）

1. **首次真实运行即失败**：`TradingCalendar.from_file` 第二参数要的是路径，
   我传了已解析的 dict（TypeError）。修后三次运行与计划预计一致。
   ——这正好演示了入口的价值：失败阶段被明确记录，没有假装成功。
2. **首次输出里没有 findings**：污染原因与 event_id 都进不了 JSON，
   两个边界测试因此失败。补上 `findings` 段——它本来就是"缺什么"该展示的。
3. **两次 zsh 不Word-split 的坑**：`$BASE` 整串被当一个参数（CLI 报缺参）。
   与此前日历轮同样的错；已改为完整命令。
4. **测试里两处自己写的假断言**：`or True` 让它永真；`b"99.9"` 少了 `b` 前缀
   导致 TypeError 而非预期失败。都已修正并记录——先断言篡改真实发生，再看结果。
5. **一处断言选错用途**：`description` 本来就不受行动污染影响（它影响
   attribution/research_signal），退出 0 是对的；改 attribution 验证闸门。
6. 死代码（`if False else None`）与未断言的 `proc` 若干，lint 后补退出码断言。

## 8. 文件指纹（完整 SHA-256 见各文件；前 16 位）

| 文件 | 指纹 |
|---|---|
| `src/lei_signal/research/input_preflight.py` | `37200f4e45adb300…` |
| `scripts/check_research_input.py` | `b884d5c125b3e29d…` |
| `tests/unit/test_research_input_preflight.py` | `60b7fe0dceae865c…` |
| `tests/integration/test_research_input_preflight_cli.py` | `d315405f7e1f673a…` |
| attempt-01-03 / 02-02 / 03-02 的 preflight.json | `4fd98225c2d99797…` / `57bb22b547eb3344…` / `6821ca92ff0c7399…` |

**受保护文件**：896 项基线逐文件复核零改动；主控两份反例文件未动；
`data_quality.py` 等八个既有模块本轮**一行未改**（见 consumer-map.md）。

## 9. 给主控的交接

- **建成与否请独立验证**：换一个 agent，只凭 `protocol.json` 与相同本地输入，
  运行 §6 的命令，应得到同样的稳定判定字段（14 只/18,916 行、六用途裁决、
  三对象缺 `economic_index`、退出码 0/2/2）。
- **它故意不做的事**：不计算 `economic_index`、不判因子有效、不碰生产。
  三个指定对象仍缺字段、四项用途仍受限——这是允许的真实结果，不是缺陷。
- **下一道真正的门槛**是 §5 表里的第一项：`economic_index` 的生成与绑定。
  它是计算任务，不是资料任务，需要单独授权（含定义规则卡、手算小例、
  与冻结旧输出逐值比对）。在它完成前，`mixed.*` 对象层全部不可用。
- 待确认事项：**无新增**（既有七项缺口见 §5 表）。

**完成即停，交主控复核。不自行宣布因子第一波可以开工；
不宣布策略有效、因子有效、OKR 完成或获准交易。**
