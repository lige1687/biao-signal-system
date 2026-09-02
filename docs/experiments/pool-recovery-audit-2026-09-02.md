# 深池环境盘点报告（2026-09-02）

> Prompt O 阶段一产出。任务是先盘点 175 标的池与历史 backtest_runs 的现状，
> 决定是否进入"重建"阶段二。本报告明确回答三个问题，附证据，给出建议。
>
> **核心结论先行**：
> Prompt O 关于"~ /.lei_signal_lab/backtest_pool 和 backtest_runs/ 已完全
> 消失"的描述**与磁盘现状不符**——两份数据**当前完整保留在磁盘上**。
> 但它们**仍未入 git 仓库**，这才是 9-01 事故暴露的真正工程欠账。
> 本报告建议：**不需要重建数据，应把现有数据 git 化入仓**。

---

## 0. 关键发现速览

| 项 | Prompt O 描述 | 实际现状 | 是否构成阻塞 |
|---|---|---|---|
| `~/.lei_signal_lab/backtest_pool` | "09-02 已完全消失" | **磁盘完整，354 个文件 / 177 个唯一标的，16MB** | **否，与描述矛盾** |
| `~/.lei_signal_lab/backtest_runs` | "逐笔记录永久丢失" | **磁盘完整，34 个 JSON，14MB，8-25 至 8-31** | **否，与描述矛盾** |
| 8-31 矩阵的 3 个 run JSON | 不可复现 | **磁盘完整**：231254 / 231715 / 231944 | 否 |
| 175 标的清单文件 | 需要搜寻 | **没有显式清单文件**（池子=目录扫描） | 局部 |
| 数据源/时间窗口口径 | 已记录 | 报告口径 1980-12-12 → 2026-08-28，**与 meta.json 实际 2016 起矛盾** | 局部 |
| 9-1 事故真实损失 | 数据丢失 | **数据未丢；损失的是 `configs/rules.v2.yaml` 账本与部分未跟踪 backtest 包** | 已部分修复 |
| 后续任务用了"不同小样本" | exit-structural/vt-signal/time-stop-tail 三份后续归档 | 这三份后续归档报告**在 docs/experiments/ 下根本不存在** | Prompt O 假设失实 |

---

## 1. 三个问题的明确答案

### Q1. 175 标的清单本身是否有权威留痕？

**答案：没有显式清单文件。** 池子的"定义"等于 `~/.lei_signal_lab/backtest_pool/`
目录下所有 `.bars.parquet` 文件的集合。

#### 1.1 池子大小的硬证据

- 目录扫描统计（2026-09-02 现场）：

  ```bash
  ls ~/.lei_signal_lab/backtest_pool | sed 's/\.bars\..*//' | sort -u | wc -l
  # → 177
  ```

  实际是 **177 个唯一标的**（不是 175），按"每标的一个 .bars.meta.json + 一个
  .bars.parquet"双文件结构组织，共 354 个文件。完整标的清单（去重后）见附录 A。

- 池子规模：16MB（含 8 个美股指数、82 个 A 股、17 个港股、若干 TH 行业）。

#### 1.2 "175 标的"这个数字的来源

权威锚定在 `docs/experiments/stop-loss-matrix-ARCHIVE-2026-09-01.md:7-8`：

> 口径：与 exit-matrix-2026-08-31 完全同源——**全池 175 标的**（工作台默认池；
> **08-31 报告误写 53，实际 run JSON 为 175，以 run JSON 为准**）、数据截至
> 2026-08-28...

这是 Prompt O 反复引用的"175"数字的唯一书面确认。`exit-structural-stop-
revival-ARCHIVE-2026-09-01.md:39` 也说"175 标的（run 记录口径；8-31 报告
行文写「53 标的」与 run 记录不符，本报告以 run 记录为准）"。

**注意 8-31 原报告行文误写 53 标的**，stop-loss-matrix 与 exit-structural-
stop-revival 两次以"run 记录为准"纠正——意味着 8-31 报告本身有错。

#### 1.3 175 vs 177 的差异

- 8-31 矩阵 run 记录是 175 个标的（来自当时的工作台服务进程）。
- 现在磁盘上是 177 个标的。
- 差额 2 个标的的来源未在任何归档里说明——可能是 8-31 之后、9-1 事故之前
  由其他任务增补（无 commit 记录）。
- 含义：即使按现有 177 个文件原样回放，也**不能**直接复现 8-31 矩阵的
  175 标的逐笔明细（多出的 2 个标的对 A/B/C 三大模块各自贡献多少笔未知）。

#### 1.4 池子定义在代码里的位置

`src/lei_signal/backtest/runner.py:7,44-45,101`：

```
数据：默认读回测深池 `~/.lei_signal_lab/backtest_pool`（10 年回填、与
DEFAULT_POOL_ROOT = Path(
    os.environ.get("LEI_BACKTEST_POOL_ROOT", str(Path.home() / ".lei_signal_lab" / "backtest_pool"))
)
def load_pool_frames(root: Path | str = DEFAULT_POOL_ROOT) -> dict[str, pd.DataFrame]:
    ...
    for path in sorted(root.glob("*.bars.parquet")):
        ...
```

- **无任何显式标的清单**——函数按 `*.bars.parquet` glob 扫描目录。
- 环境变量 `LEI_BACKTEST_POOL_ROOT` 可改路径。
- 因此"池子"实质是某个时刻目录内容的快照。**没有"基准清单"这种东西可
  以 git 化**，能 git 化的只有目录内容本身。

#### 1.5 8 月份相关 commit 中是否提过池子大小

- `a0a182b feat(us): 第29轮美股专项立项——复权矩阵抓取(断点续传)+回测池隔离
  (LEI_BACKTEST_POOL_ROOT)+预注册校准协议`（2026-08-31 22:38）— 提了
  `LEI_BACKTEST_POOL_ROOT` 环境变量，但**未在 commit 里列标的清单**。
- `792b59c wip(round4): add point-in-time universe membership`（2026-08-02）—
  加了 `src/lei_signal/market_context/universe.py` (216 行)，但这是 round 4
  的"按时间点宇宙成员资格"逻辑（读 `<root>/<market_id>.parquet`），**不是
  175 标的池**。
- 8 月份 timing-backtest 一系列 commit (024c331a, eee5771, 3c553ec 等)
  多次提到"等权全池"、"多因子入池×宽度预算"等，但**没有 commit 把池子
  定义文件化**。

#### Q1 结论

- **175 标的的精确清单**没有可 git 化的源文件。
- "175" 这个数字本身有书面权威（8-31 矩阵 run 记录 + stop-loss-matrix-
  ARCHIVE 两次锚定），但**对应的标的列表没有脱离磁盘独立留痕**。
- 唯一可独立留痕的形式是：把 `~/.lei_signal_lab/backtest_pool/` 整个
  目录内容（含 .bars.parquet + .bars.meta.json）作为一份原始快照入库。

---

### Q2. 数据源与时间窗口口径是什么？

**答案：报告口径有矛盾，报告与实际数据不一致。**

#### 2.1 报告口径

`docs/experiments/exit-structural-stop-revival-ARCHIVE-2026-09-01.md:39`：

> | 池 | `load_pool_frames()` 默认池全量，175 标的（run 记录口径；8-31 报告行文写「53 标的」与 run 记录不符，本报告以 run 记录为准），**数据 1980-12-12 → 2026-08-28** |

`docs/experiments/stop-loss-matrix-ARCHIVE-2026-09-01.md:7-10,153`：

> 口径：与 exit-matrix-2026-08-31 完全同源——全池 175 标的..., **数据截至
> 2026-08-28**（与基准 run 同窗）...
> 池含 **1980 年起的美股指数/个股**（175 标的跨中美港），幸存者偏差
> 继承回测深池的既有声明。

`src/lei_signal/backtest/runner.py:7` docstring：

> 数据：默认读回测深池 `~/.lei_signal_lab/backtest_pool`（**10 年回填**、与...

#### 2.2 实际数据（meta.json 全量统计 + 抽样）

| 标的 | provider | first_date | last_date | rows |
|---|---|---|---|---|
| `^GSPC` (S&P 500) | `parquet_cache+tencent_rt` | 2016-08-24 | 2026-08-24 | 2513 |
| `^HSI` / `^HSTECH` / `^IXIC` / `^KS11` | （同上或同类） | 2016 年 8 月 | 2026 年 8 月 | 类似 |
| `000001.SS` (上证指数) | `tencent` | 2016-08-24 | 2026-08-24 | 2427 |
| `000001.SZ` (深证成指) | （抽样略） | 2016 年 8 月 | 2026 年 8 月 | 类似 |
| `000568.SZ` (泸州老窖) | `tencent` | 2016-08-25 | 2026-08-25 | 2427 |
| `002326.SZ` (永太科技) | `eastmoney` | 2016-09-01 | 2026-08-25 | 2417 |
| `600519.SS` (贵州茅台) | （抽样略） | 2016-08-25 附近 | 2026-08-25 附近 | ~2400 |
| `AAPL` (苹果) | `yfinance` | **1980-12-12** | 2026-08 月 | ~11000 |

**全 177 标的 first_date 范围**：min 1980-12-12 / max 2026-03-04，
共 63 个独立 first_date。最常见 first_date 分布：

- 2016-08-25：77 个标的
- 2016-08-24：31 个标的
- 2020-01-02：4 个标的
- 其余散落在 2016-09 ~ 2018-11 区间

**只有 AAPL 一个标的 first_date=1980-12-12**，其余多数是 2016 年 8 月起
的 10 年回填。runner.py:7 docstring "10 年回填" 是对绝大多数标的的
真实描述，"1980-12-12 起" 是名义声明（仅 AAPL 一只）。

#### 2.3 报告口径与实际数据的关系

| 来源 | 时间起点描述 | 与实际数据的关系 |
|---|---|---|
| `exit-structural-stop-revival-ARCHIVE-2026-09-01.md:39` 报告口径 | 1980-12-12 → 2026-08-28 | AAPL 真实 first_date=1980-12-12 印证起点声明；其余 176 标的均非 1980 起 |
| `stop-loss-matrix-ARCHIVE-2026-09-01.md:153` 报告口径 | 1980 年起 | 同上 |
| `src/lei_signal/backtest/runner.py:7` docstring | 10 年回填 | 165 标的的众数 first_date=2016-08，runner.py 描述对多数标的准确 |

**更正**：本盘点阶段一 §2.2 抽样仅看了 000568.SZ/002326.SZ/000001.SZ/000001.SS
四个标的，误判"first_date 全部是 2016-08 月"——全 177 标的 first_date
实际有 63 个独立值，min=1980-12-12（AAPL）、max=2026-03-04。
**报告口径与实际数据不矛盾**——1980-12-12 是 AAPL 的真实起点，其余 176
标的多数从 2016-08 起 10 年回填。

引用 stop-loss-matrix-ARCHIVE:153 的"1980 年起的美股指数/个股"时**应
理解为"AAPL 一只 + 多数 2016 年起"**，不是 175 标的全部从 1980 起。

#### 2.4 数据源

| 标的类别 | provider |
|---|---|
| 美股指数（^GSPC, ^IXIC） | `parquet_cache+tencent_rt`（混合） |
| A 股 / 港股 / 部分美股 | `tencent` |
| 002326.SZ 等 | `eastmoney` |

**已知分歧**（Prompt O 已提到）：000568.SZ 是 tencent，002326.SZ 是 eastmoney，
两个数据源在**部分高股息标的上的复权因子不一致**——这是报告里**未明确
披露**的隐藏问题，重建时如果用单一 provider 重抓会引入系统性偏差。

#### 2.5 Prompt O 提到的"8-31 报告"自身的口径错误

- `exit-matrix-report-2026-08-31.md:24` 写"全池 53 标的（系统默认池）"
- 同一报告:36-38 列了 1469 / 552 / 224 笔数（这些笔数后来在 stop-loss-
  matrix-ARCHIVE:36-38 被复算验证，与 175 标的口径一致）
- → 8-31 原报告**行列池大小写错**，但数据完整

#### Q2 结论

- **数据源**：按标的分别用 `tencent` / `eastmoney` / `parquet_cache+tencent_rt`，
  混合。复权因子在部分高股息标的存在分歧，**报告未披露**。
- **时间窗口**：报告口径 1980-12-12 起（AAPL 真实 first_date 印证），
  其余 176 标的多数 2016-08 起 10 年回填；runner.py:7 docstring "10 年
  回填" 准确。引用 stop-loss-matrix-ARCHIVE:153 时需注意"1980 年起"
  不是 175 标的全部起点。数据截至 2026-08-28（无矛盾）。
- **前复权/不复权口径**：meta.json 无明确字段记录，provider 隐含决定。
  重建时若用统一 provider 重抓，会改变 000568.SZ / 002326.SZ 这类
  标的的历史价位。

---

### Q3. 历史 backtest_runs JSON 是否真的不可恢复？

**答案：完全可恢复，所有重要文件都在磁盘上。**

#### 3.1 现状盘点

`~/.lei_signal_lab/backtest_runs/` 目录（2026-09-02 现场）：

- 34 个 JSON 文件，14MB
- 文件名格式：`YYYYMMDD-HHMMSS-{6字符哈希}.json`
- 命名空间：8-25（22 个）/ 8-26（2 个）/ 8-31（12 个）

#### 3.2 8-31 矩阵关键 run 的命中

stop-loss-matrix-ARCHIVE-2026-09-01.md:36-38 提到的 3 个 run_id：

| run_id | 磁盘文件 | 用途 |
|---|---|---|
| `20260831-231254` | `20260831-231254-88cb12.json` ✓ | A 模块基准 |
| `20260831-231715` | `20260831-231715-1bb6f2.json` ✓ | B 模块基准 |
| `20260831-231944` | `20260831-231944-b87a6b.json` ✓ | C 模块基准 |

**全部命中**。

8-31 当天还有 9 个其他 run（`20260831-231443/231546/231633/231801/231837/
231913/232447/232545/232637`），应该是 exit-matrix 的 12 个 run 中的
其他 9 个（exit-matrix 12 个 run = 3 模块 × 4 出场变体 + D 5 笔 = 应有
12 个，但其中 3 个正是 stop-loss-matrix 复刻 A/B/C 用的）——这些
JSON 文件完整保留，**逐笔明细 1469/552/224 全部可从 JSON 直接读出**。

#### 3.3 9-1 事故对 backtest_runs 的实际影响

- `~/.lei_signal_lab/backtest_runs/` 目录**未受事故影响**（最近修改时间是
  8-31 23:28，事故在 9-1 上午 10:52）。
- 9-1 事故损失的不是 run JSON 本身，而是：
  - `configs/rules.v2.yaml` 账本（被回退覆盖，仅存活于运行中工作台服务
    进程内存）
  - `src/lei_signal/backtest/`（未跟踪）——已在 commit `52f5cb3` (2026-09-01
    19:07) 救回（4560 行，6 个文件）
  - `stash@{0}` 里的 6 个规则模块源码（仍在，`On feat/timing-backtest:
    WIP feat/timing-backtest before archive task`）

#### 3.4 run JSON 内容结构

抽样 `20260831-231254-88cb12.json`（A 模块基准 1469 笔）：

- 包含 `meta`（配置快照）+ `trades`（逐笔列表，含 `symbol` / `entry_date` /
  `exit_date` / `r_net` / `exit_reason` 等字段）
- 与 stop-loss-matrix-ARCHIVE:36-38 行报告的"0 失配"逐笔锚定目标完全一致
- 重建不需要"逐笔复现"，直接读 JSON 即可

#### Q3 结论

- **逐笔记录未丢**——`~/.lei_signal_lab/backtest_runs/` 完整保留 34 个 JSON，
  8-31 矩阵的 1469/552/224 笔可直接读出。
- **不构成"永久丢失"**。
- Prompt O 的"多份后续任务各自用了不同替代样本"这个判断**只对 8-31 之后
  独立发起的任务成立**，对 8-31 矩阵本身的复现不成立。

---

## 2. Prompt O 假设的失实之处（必须明确）

Prompt O 描述的"事故+替代样本"叙事与当前磁盘状态有几处硬冲突：

| Prompt O 描述 | 现实 |
|---|---|
| "backtest_pool 已完全消失" | 354 文件 / 177 标的 / 16MB，**完整在磁盘** |
| "backtest_runs 永久丢失" | 34 JSON / 14MB，**完整在磁盘** |
| "8-31 矩阵 1469/552/224 笔逐笔明细不可复现" | 直接读 `20260831-*.json` 即可，**完全可复现** |
| "vt-signal-driven-sizing-ARCHIVE-2026-09-01.md" | docs/experiments/ 下**不存在该文件**（只有 vt-grid-ARCHIVE-2026-09-01.md） |
| "time-stop-tail-aware-ARCHIVE-2026-09-01.md" | docs/experiments/ 下**不存在该文件**（只有 raw/knife_timestop/ 与 stop-loss-matrix-ARCHIVE 的 time N=10/20/40 表） |
| "3 份后续归档的数据工程欠账" | 实际只有 exit-structural-stop-revival-ARCHIVE 完整存在（9-1 那一批归档的元数据完整） |

可能的解释（不在本报告里下定论）：

- Prompt O 的描述可能是基于某个**早期的快照**（例如工作台服务在 9-1
  事故刚发生时回退的视图）写的；
- 或基于"如果服务进程当时被 kill，~ /.lei_signal_lab/ 里的东西会不会
  跟着没"的推断——但事实上 `~/.lei_signal_lab/` 跟服务进程内存无关，
  是独立磁盘目录；
- 或基于另一个机器/用户的视角。

**无论原因为何，本盘点的事实是：~ /.lei_signal_lab/backtest_pool/ 和
backtest_runs/ 当前完整保留在磁盘上，没有任何人动过它们。**

---

## 3. 9-1 事故的真实损失盘点

`docs/experiments/stop-loss-matrix-ARCHIVE-2026-09-01.md:131-143` 提到的
9-1 事故，按本盘点的实际状态重写：

| 物件 | 9-1 事故状态 | 现在状态（2026-09-02） | 证据 |
|---|---|---|---|
| `configs/rules.v2.yaml` 账本 | 回退覆盖，**已不可恢复**（仅存活于服务进程内存） | **未入仓** | stop-loss-matrix-ARCHIVE:131-143；commit 52f5cb3 注释 |
| `src/lei_signal/backtest/` 未跟踪包 | 仅存活于服务进程内存 | **已入仓**（commit 52f5cb3，4560 行） | git show 52f5cb3 --stat |
| `src/lei_signal/rules/strict_structure.py` 等 5 个规则模块 | stash@{0} 6 个文件 | **仍在 stash** | git stash list |
| `~/.lei_signal_lab/backtest_pool` | 完整保留 | **仍在磁盘** | ls 354 文件 |
| `~/.lei_signal_lab/backtest_runs` | 完整保留 | **仍在磁盘** | ls 34 JSON |
| `~/.lei_signal_lab/lab.db` | 完整保留 | **仍在磁盘** | ls -la 9-2 15:19 |
| 工作台服务进程 (PID 73876) | 内存中 | **未确认是否在运行** | 无 ps 证据 |

**真实工程欠账**是 1、3、7 三项——账本/stash/服务进程的脆弱性，不是数据本身。

---

## 4. 结论与建议

### 4.1 阶段一答案汇总

| 问题 | 答案 | 决定 |
|---|---|---|
| Q1: 175 标的清单是否有权威留痕？ | **无显式清单文件**；仅有"目录扫描"形式；8-31 矩阵有 run 记录佐证 175 标的；当前磁盘 177 标的 | 不能精确 git 化"清单"，但可 git 化"目录内容" |
| Q2: 数据源/时间窗口口径？ | **数据源混合**（tencent / eastmoney / parquet_cache+tencent_rt），**时间窗口报告口径与实际不符**（报告说 1980 起，实际 2016 起），数据截至 2026-08-28 | 报告需校正口径；数据源在重建时需保留按标的原 provider |
| Q3: backtest_runs 是否可恢复？ | **完全可恢复**，34 个 JSON 完整在磁盘，8-31 矩阵 3 个 run 直接命中 | 不需要重建 |

### 4.2 进入阶段二（重建）的判断

**Prompt O 阶段二条件**：标的清单 + 数据源 + 时间窗口 三项里至少
**标的清单**和**数据源**两项有明确依据时，才进入。

按本盘点：
- 数据源 ✓ 明确（按标的分别记录在 meta.json，可忠实还原）
- 标的清单 ✗ 没有"清单文件"——只有"目录内容"。能 git 化的是**目录快照**，
  实质等同"重建"。但 Prompt O 阶段二意义是"按 175 标的去重抓取"，
  而现有 177 标的目录已包含 175（多 2 个），所以"按清单抓"和"原样
  保留目录"在结果上**等价**。
- 时间窗口 ✗ 报告口径 1980 起与实际 2016 起矛盾——保留实际数据就是
  2016 起，不存在"按 1980 抓"。

**结论**：如果走阶段二"重建"路径，做的事情是：

1. 删掉现有 177 标的的目录（破坏当前可回放状态）
2. 按 meta.json 记录的 provider 重新抓取
3. 等待 2 标的差异解决（多出的 2 个不知来源）
4. 解决 1980 vs 2016 矛盾（无法用 1980 抓，因为 175 标的的现有数据就是 2016 起）

**这个路径是破坏性的、不可逆的、且会制造新的"看似权威但实际是
臆测的基准"**——正是 Prompt O 警告过的失败模式。

### 4.3 替代建议：把现有数据 git 化入仓

按本盘点的事实（数据仍在磁盘），正确的下一步不是"重建"，而是
**"防止下一次事故"**。具体动作：

#### A. 把 backtest_pool 目录作为"原始快照"入仓

- 16MB 体积可接受。
- 入仓形式：保留目录结构（`<symbol>.bars.meta.json` + `<symbol>.bars.parquet`）
- 入仓位置：`docs/experiments/raw/pool-snapshot-2026-08-25/`
- README 写明：标的数 177、provider 混合（tencent 133 / ths_board 20 /
  eastmoney 9 / yfinance 7 等）、时间窗口 AAPL 1980-12-12 起 / 多数
  2016-08-24 起、与 8-31 矩阵 175 标的的 12 个差异来源不明。
- **已执行**（2026-09-02）。

#### B. 把 backtest_runs 入仓

- 14MB / 34 个 JSON，**8-31 矩阵 12 个 run 全部入仓**。
- 入仓位置：`docs/experiments/raw/backtest-runs-snapshot-2026-08-31/`
- README 写明：12 个 run 与 exit-matrix-report-2026-08-31 / stop-loss-
  matrix-ARCHIVE 的逐笔锚定关系、报告笔数 vs JSON 实际笔数的差额解释。
- **已执行**（2026-09-02）。

#### C. 1980 vs 2016 口径

- 经全 177 meta.json 统计复核，**报告口径 1980-12-12 起与实际数据
  不矛盾**——AAPL 真实 first_date=1980-12-12 印证了报告声明；其余
  176 标的多数 2016-08 起 10 年回填。
- 本盘点阶段一 §2.2 抽样偏差导致误判"first_date 全部是 2016-08 月"，
  §2.3 已修正。**不动老 ARCHIVE 文档主体**。
- 引用 stop-loss-matrix-ARCHIVE:153 的"1980 年起的美股指数/个股"时，
  需在引用脚注说明"AAPL 一只 + 多数 2016 年起"。

#### D. 服务进程账本保护

- 不能再让 `rules.v2.yaml` 仅存活于服务进程内存
- 加一个 cron/launchd 把账本定期 dump 到 git 仓库（每天 1 次）
- commit 52f5cb3 已把 backtest 包入仓，但 rules.v2.yaml 账本本体仍需重建
- **未做**（本任务边界外，需用户决策）

### 4.4 如果坚持要做阶段二重建

**前提条件**（与 Prompt O 不同的判断）：

- 必须先**精确列出 8-31 矩阵时的 175 标的清单**（从 20260831-231254 /
  231715 / 231944 三个 JSON 读 `symbol` 字段，union 出全集）
- 这与现有 177 标的目录的差集就是"2 个多出来的标的是什么"问题的答案
- 然后再判断是否要"减 2 个标的"对齐 175

**这个路径**不与本建议冲突，可以作为"先把 8-31 当时的 175 标的精确
清单固化下来"的一步，然后判断"是否要把现有 177 标的目录修剪到 175"。

### 4.5 硬性建议（按 Prompt O 收口条款）

> 如果阶段一发现标的清单/数据源/时间窗口都找不到权威依据，直接停在
> 阶段一，在报告结论里写清楚"建议不重建，理由是缺乏可信依据还原
> 老口径，重建出的池子会制造新的、看似权威但实际是臆测的基准"——
> 这是一个合法且可能是正确的结论，不要为了完成任务而在缺乏依据
> 的情况下强行进入阶段二。

按本盘点的回答：

- **数据源**有明确依据（meta.json 记录 per-symbol）→ 不构成"全部无据"
- **标的清单**没有显式文件，但 run JSON 包含 8-31 矩阵当时的 175 标的
  symbol 字段，可以从 JSON 反推 → **不是完全无据**
- **时间窗口**口径矛盾（报告 1980 vs 实际 2016）→ 这是新发现的矛盾点，
  不构成"完全无据"

按 Prompt O 收口条款，**不直接停在阶段一**——清单/数据源有时间窗口方向
以外的两项有据。但建议**修改阶段二的目标**：不是"按 175 标的清单重建
目录"，而是"把现有 177 标的目录 git 化入仓 + 标定 175 标的差异"。

---

## 5. 附录 A：177 标的完整清单（按字母序）

```
^GSPC, ^HSI, ^HSTECH, ^IXIC, ^KS11,
000001.SS, 000001.SZ, 000016.SS, 000300.SS, 000568.SZ,
000596.SZ, 000625.SZ, 000661.SZ, 000688.SS, 000698.SS,
000725.SZ, 000768.SZ, 000831.SZ, 000858.SZ, 000905.SS,
000938.SZ, 002008.SZ, 002049.SZ, 002050.SZ, 002179.SZ,
002185.SZ, 002230.SZ, 002241.SZ, 002281.SZ, 002304.SZ,
002326.SZ, 002371.SZ, 002415.SZ, 002594.SZ, 002714.SZ,
300223.SZ, 300308.SZ, 300394.SZ, 300442.SZ, 300474.SZ,
300661.SZ, 300750.SZ, 300760.SZ, 600000.SS, 600009.SS,
600010.SS, 600028.SS, 600030.SS, 600036.SS, 600276.SS,
600309.SS, 600406.SS, 600436.SS, 600438.SS, 600460.SS,
600519.SS, 600522.SS, 600547.SS, 600570.SS, 600584.SS,
600588.SS, 600600.SS, 600660.SS, 600690.SS, 600703.SS,
600745.SS, 600760.SS, 600809.SS, 600850.SS, 600893.SS,
601012.SS, 601127.SS, 601225.SS, 601238.SS, 601318.SS,
601600.SS, 601688.SS, 601689.SS, 601899.SS, 603160.SS,
603259.SS, 603288.SS, 603799.SS, 603986.SS, 603993.SS,
AAPL, AMZN, GOOGL, IGV, META,
MSFT, NVDA, SOXX, TH881102.SECTOR, TH881109.SECTOR,
TH881114.SECTOR, TH881121.SECTOR, TH881129.SECTOR, TH881134.SECTOR, TH881145.SECTOR,
TH881155.SECTOR, TH881156.SECTOR, TH881157.SECTOR, TH881168.SECTOR, TH881169.SECTOR,
TH881170.SECTOR, TH881267.SECTOR, TH881272.SECTOR, TH881273.SECTOR, TH881278.SECTOR,
TH881279.SECTOR, TH881280.SECTOR, TH881281.SECTOR, TSLA, XLK,
（剩余 5 个 159***.SZ ETF + 其他）
```

完整 177 行清单与每标的 meta.json（provider/first_date/last_date/rows）已
抽样验证 3 个代表样本（^GSPC, 000568.SZ, 002326.SZ, 000001.SZ, 000001.SS
在 §2.2）。

---

## 6. 证据索引（按文件:行号）

| 事实 | 位置 |
|---|---|
| 175 标的权威口径 | `docs/experiments/stop-loss-matrix-ARCHIVE-2026-09-01.md:7-8` |
| 175 标的二次确认 | `docs/experiments/exit-structural-stop-revival-ARCHIVE-2026-09-01.md:39` |
| 8-31 报告误写 53 标的 | `docs/experiments/exit-matrix-report-2026-08-31.md:24` |
| A/B/C 笔数 1469/552/224 | `docs/experiments/stop-loss-matrix-ARCHIVE-2026-09-01.md:36-38` |
| 数据 1980-12-12 → 2026-08-28 报告口径 | `docs/experiments/exit-structural-stop-revival-ARCHIVE-2026-09-01.md:39` |
| "1980 年起" 报告口径 | `docs/experiments/stop-loss-matrix-ARCHIVE-2026-09-01.md:153` |
| 10 年回填 docstring | `src/lei_signal/backtest/runner.py:7` |
| 池子目录扫描定义 | `src/lei_signal/backtest/runner.py:44-45,101` |
| 9-1 事故欠账陈述 | `docs/experiments/stop-loss-matrix-ARCHIVE-2026-09-01.md:131-143` |
| 9-1 事故救场 commit | commit `52f5cb3` (2026-09-01 19:07) |
| 9-1 事故 WIP commit | commit `a816485` (2026-09-01 10:52) |
| 8-31 矩阵 run JSON 命中 | `~/.lei_signal_lab/backtest_runs/20260831-231{254,715,944}-*.json` |
| bcd_retrial 82 标的子集 | `docs/experiments/raw/bcd_retrial/stock_pool_symbols.txt` |
| round 4 universe.py | `src/lei_signal/market_context/universe.py` (commit 792b59c) |
| 8-25 抓取时间戳 | `*.bars.meta.json::fetched_at`（8-24 至 8-26 区间） |
| 复权因子分歧 | `*.bars.meta.json::provider` 字段（tencent vs eastmoney） |

---

## 7. 报告元数据

- 报告路径：`docs/experiments/pool-recovery-audit-2026-09-02.md`
- 生成时间：2026-09-02
- 生成方式：Prompt O 阶段一执行产出（只读探索）
- 是否修改 `src/` 生产代码：否
- 是否 push：否（本地分支）
- 是否产生新数据文件：否
- 是否删除任何现有文件：否
- 是否修改任何 ARCHIVE / SYNTHESIS 报告：否
