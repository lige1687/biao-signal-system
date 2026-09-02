# backtest_pool 原始快照（2026-08-25 / 抓取时间窗 8-24 ~ 8-31）

> 9-01 工作区回退事故的"事后补牢"快照。这份数据从 2026-09-02 之前
> 一直位于 `~/.lei_signal_lab/backtest_pool/`，**未入 git 仓库**。
> 9-01 事故本身**没有破坏这些数据**（数据是磁盘独立目录，与服务
> 进程内存解耦），但暴露了"数据不进仓"这个工程欠账。
>
> 本目录是 2026-09-02 的全量复刻，**只新增，不覆盖任何现有 raw 目录内容**。

## 1. 标的基础统计

| 项 | 数值 |
|---|---|
| 文件总数 | 354（177 标的 × 每标 1 个 `.bars.meta.json` + 1 个 `.bars.parquet`） |
| 唯一标的数 | 177 |
| 总体积 | 16 MB |
| 数据源 provider 分布 | tencent 133, ths_board 20, eastmoney 9, yfinance 7, parquet_cache+tencent_rt 3, yahoo_v8 3, parquet_cache+sina_rt 1, tencent_global 1 |
| 抓取时间（fetched_at） | 2026-08-24 (52) / 2026-08-25 (39) / 2026-08-26 (79) / 2026-08-31 (7) |
| 数据起（first_date min） | **1980-12-12**（仅 AAPL） |
| 数据止（first_date max 之外） | 多数 first_date 在 2016-08 月（最常见 2016-08-25 = 77 个标的） |
| 末交易日（last_date 多数） | 2026-08-24 / 2026-08-25 / 2026-08-31 视标的而定 |

## 2. 与归档报告口径的对照

### 2.1 "175 标的"

权威留痕：

- `docs/experiments/stop-loss-matrix-ARCHIVE-2026-09-01.md:7-8` —
  "全池 175 标的（工作台默认池；08-31 报告误写 53，实际 run JSON 为 175，以 run JSON 为准）"
- `docs/experiments/exit-structural-stop-revival-ARCHIVE-2026-09-01.md:39` —
  "175 标的（run 记录口径；8-31 报告行文写「53 标的」与 run 记录不符，本报告以 run 记录为准）"

现状：**磁盘 177 标的**（8-31 之后可能新增 2 个，与 8-31 run 记录 175 标的差 2）。

8-31 矩阵 12 个 run 实际有信号的标的 union = **165**。8-31 矩阵"175 标的"
这个数字当时是工作台检测器**扫过的标的总数**（含被扫但无信号标的），
不是 union 有信号标的。

### 2.2 "数据 1980-12-12 → 2026-08-28"

- `exit-structural-stop-revival-ARCHIVE-2026-09-01.md:39` 报告口径
- `stop-loss-matrix-ARCHIVE-2026-09-01.md:153` 报告口径
- `src/lei_signal/backtest/runner.py:7` docstring 说"10 年回填"

**实际数据 first_date 分布**：

- **AAPL 是唯一 first_date=1980-12-12** 的标的（美股，yfinance）
- 77 个标的 first_date=2016-08-25（最常见）
- 31 个标的 first_date=2016-08-24
- 4 个标的 first_date=2020-01-02
- 其余散落在 2016-09 至 2018-11 区间

**报告口径的 1980-12-12 起点是名义声明**——实际是 AAPL 单标的的起点。
**实际 8-31 矩阵工作的是 165 标的 × 约 10 年**（多数 first_date 2016 年 8 月）。

末交易日 2026-08-24 至 2026-08-31 与报告的 2026-08-28 一致。

### 2.3 "1980 vs 2016" 不构成口径失实

经 §2.2 复核，报告口径与实际数据**不矛盾**——1980-12-12 是 AAPL 的
真实 first_date，10 年回填是 165 标的的众数起点。引用 stop-loss-matrix-
ARCHIVE:153 的"1980 年起的美股指数/个股（175 标的跨中美港）"时，**应
理解为"AAPL 一只 + 多数 2016 年起"**，不是 175 标的全部从 1980 起。

阶段一盘点（`pool-recovery-audit-2026-09-02.md` §2.2）当时抽样只看了
000568.SZ/002326.SZ/000001.SS 三个，**抽样偏差导致阶段一误判报告口径
与实际数据"严重不符"**。本 README 是修正。

## 3. 8-31 矩阵 12 个 run 的逐笔锚定

### 3.1 8-31 run 与 pool 标的的差异（2026-09-02 二次复核：来源已解决）

8-31 矩阵 12 个 run（`backtest-runs-snapshot-2026-08-31/20260831-*.json`）
的有信号标的 union = **165**。**每个 run JSON 的 `per_symbol` 字段嵌有当时
扫描的完整 175 标的清单**（`{symbol, bars, trades}` × 175，12 个 run 完全
一致；`data_range.symbols_count=175` 佐证）——175 精确清单已随 runs 快照
入仓，不再是"目录扫描黑盒"。

pool 177 与 run 175 的差集，以及 12 个"池中有但 run 无信号"标的的构成：

- **159165.SZ（127 根）/ 560390.SS（119 根）**：2026-08-24 已抓取入库
  （meta 的 fetched_at 为证），但被 `load_pool_frames()` 的
  `len(bars) < 300` 过滤规则排除（`src/lei_signal/backtest/runner.py`），
  **不是 8-31 之后新加的标的**。
- 其余 10 个（^HSTECH, 000831.SZ, 300308.SZ, 300661.SZ, 512690.SS,
  513870.SS, 515880.SS, 516010.SS, 600111.SS, 601600.SS）：被扫描但
  **零信号**（A run 的 42 个零信号标的的子集）。

对账恒等式：pool 177 − 2（<300 根被过滤）= 175 扫描 = 133（A 有信号）
+ 42（零信号）；12 个 run 的有信号 union = 165。

> **更正痕（2026-09-02 二次复核）**：本节初版写"12 个差异标的来源
> 未明，可能是 8-31 之后新加（0/12 候选）"——经 per_symbol 清单与
> runner.py 过滤规则比对，来源已完全确定（2 个被 <300 根规则过滤 +
> 10 个零信号），初版猜测作废。**177 个标的文件全部保留，不删**：
> 159165.SZ / 560390.SS 是真实抓取数据，只是未达回测门槛。

### 3.2 8-31 矩阵 4 大模块笔数

| 模块 | exit_variant | 8-31 矩阵 run 笔数 | 报告口径笔数 | 差额 |
|---|---|---|---|---|
| A·趋势回调 | a6_1_costbasis | 1521 | 1469 | -52 |
| A·趋势回调 | a6_2_top_plus_keywave | 1521 | - | - |
| A·趋势回调 | a6_3_structure_stop | 1521 | - | - |
| A·趋势回调 | b3_dual | 1521 | - | - |
| B'·密集突破 | a6_1_costbasis | 563 | 552 | -11 |
| B'·密集突破 | a6_2_top_plus_keywave | 563 | - | - |
| B'·密集突破 | a6_3_structure_stop | 563 | - | - |
| B'·密集突破 | b3_dual | 563 | - | - |
| C·2B 破底翻 | a6_1_costbasis | 225 | 224 | -1 |
| C·2B 破底翻 | a6_2_top_plus_keywave | 225 | - | - |
| C·2B 破底翻 | a6_3_structure_stop | 225 | - | - |
| C·2B 破底翻 | b3_dual | 225 | - | - |

A run ma_period 分布：20=947, 60=432, 120=142（供参考，与笔数差额无关）。

**报告 1469/552/224 = 有效平仓笔**（exit_reason ∈ {`exit_a6_1_costbasis`,
`structure_stop_C`}）：A = 899 + 570 = 1469，B = 473 + 79 = 552，
C = 222 + 2 = 224，与 stop-loss-matrix-ARCHIVE"基准出场构成"逐字一致；
差额 52/11/1 = 未成交与无效记录（invalid_nonpositive_risk /
skipped_limit_up_at_entry / open_at_end / signal_at_end_not_entered）。

> **更正痕（2026-09-02 二次复核）**：初版把差额解释为"只算
> ma_period=20 主信号"（947≠1469，数值不成立），已废弃。详见
> backtest-runs-snapshot-2026-08-31/README.md §2.2。

### 3.3 锚定校验通过项

- 8-31 矩阵 12 个 run 的 JSON 全部完整保留
- trades 字段含 symbol / entry_date / exit_date / r_net / exit_reason
  / entry_price / exit_price / stop_price / target_price / reward_risk /
  holding_bars / benchmark_clock_type / trend_stage / entry_reason
- 与 stop-loss-matrix-ARCHIVE:36-38 行的"逐笔锚定 0 失配"目标一致

**8-31 矩阵的逐笔明细 1469/552/224 完全可从本目录 + backtest-runs-snapshot
联合复现。**

## 4. 复权因子分歧（已知数据源问题）

按 `*.bars.meta.json::provider` 字段：

- **000568.SZ** (泸州老窖) — `tencent`（来自腾讯）
- **002326.SZ** (永太科技) — `eastmoney`（来自东财）

这 2 个标的是 Prompt O 与 exit-structural-stop-revival 报告都点名
"复权因子不一致"的高股息样本。**当前快照忠实保留分歧**，不修正。
引用时需特别注明。

## 5. 与现有 raw 目录的关系

- `docs/experiments/raw/lei/` — 含部分 ETF / 行业指数的 K 线与实验结果
  （与本快照有重叠，特别是指数类）
- `docs/experiments/raw/etf_expansion/` — ETF 扩展实验
- `docs/experiments/raw/bcd_retrial/stock_pool_symbols.txt` — 82 个 BCD
  重测个股子集，是本快照的子集
- `docs/experiments/raw/portfolio_split/portfolio_pool13_results.json` —
  13 标的组合子集

**本快照不替代这些 raw 目录的实验结果**，只是"工作台回测引擎依赖的
池子本身"——它是其他所有 raw 目录的数据源。

## 6. 重建方法（如未来确实需要重建）

按本快照的 provider 分布，**忠实重建**的脚本是：

```python
# 伪代码——按 meta.json 的 provider 字段逐标的抓取
import json, glob
from pathlib import Path
for meta_path in glob.glob("docs/experiments/raw/pool-snapshot-2026-08-25/*.bars.meta.json"):
    d = json.load(open(meta_path))
    symbol = d['symbol']
    provider = d['provider']
    # 调 src/lei_signal/data/ 下对应 provider
    # 注意: tencent_global 仅用于港股，yfinance/yahoo_v8 用于美股,
    #       ths_board 用于 TH 行业，parquet_cache+* 是混合源
    df = fetch_with_provider(symbol, provider, start='1980-12-12')  # 或 first_date
    df.to_parquet(f'.../{symbol}.bars.parquet')
```

**注意**：本任务不做重建（按 `pool-recovery-audit-2026-09-02.md` §4.2 结论，
当前磁盘数据完整，重建无意义）。此脚本仅作记录用途。

## 7. 元数据

- 抓取快照时间：2026-08-24 ~ 2026-08-31（依标的而定）
- git 入仓时间：2026-09-02
- 复刻来源：`~/.lei_signal_lab/backtest_pool/`（保留原始 fetched_at 时间戳）
- 入仓方式：`cp -p` 保留 mtime，硬链接 + meta 双文件结构不变
