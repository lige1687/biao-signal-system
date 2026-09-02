# backtest_runs 原始快照（2026-08-31 截止）

> 9-01 工作区回退事故的"事后补牢"快照。这份数据从 2026-09-02 之前
> 一直位于 `~/.lei_signal_lab/backtest_runs/`，**未入 git 仓库**。
> 9-01 事故本身**没有破坏这些数据**（数据是磁盘独立目录，与服务
> 进程内存解耦），但暴露了"工作台逐笔明细不进仓"这个工程欠账。
>
> 本目录是 2026-09-02 的全量复刻，**只新增，不覆盖任何现有 raw 目录内容**。

## 1. 基础统计

| 项 | 数值 |
|---|---|
| JSON 文件总数 | 34 |
| 总体积 | 14 MB |
| 时间分布 | 2026-08-25 (22) / 2026-08-26 (2) / 2026-08-31 (12) |
| 命名格式 | `YYYYMMDD-HHMMSS-{6字符哈希}.json` |
| 最后修改 | 2026-08-31 23:28:00（exit-matrix 12 个 run 的最后一个） |

## 2. 8-31 矩阵 12 个 run（核心归档对象）

### 2.1 run 一览（按 exit_variant 与 entry_variant 分组）

| run_id | entry_variant | exit_variant | trades | 标的数 |
|---|---|---|---|---|
| `20260831-231254-88cb12` | early | a6_1_costbasis | 1521 | 133 |
| `20260831-231443-bd4d21` | early | a6_2_top_plus_keywave | 1521 | 133 |
| `20260831-231546-bfb886` | early | a6_3_structure_stop | 1521 | 133 |
| `20260831-231633-a1b3de` | early | b3_dual | 1521 | 133 |
| `20260831-231715-1bb6f2` | breakout | a6_1_costbasis | 563 | 125 |
| `20260831-231801-ecb0fd` | breakout | a6_2_top_plus_keywave | 563 | 125 |
| `20260831-231837-d70a1b` | breakout | a6_3_structure_stop | 563 | 125 |
| `20260831-231913-8a2a3a` | breakout | b3_dual | 563 | 125 |
| `20260831-231944-b87a6b` | v3 | a6_1_costbasis | 225 | 59 |
| `20260831-232447-42df5e` | v3 | a6_2_top_plus_keywave | 225 | 59 |
| `20260831-232545-db8b36` | v3 | a6_3_structure_stop | 225 | 59 |
| `20260831-232637-c88603` | v3 | b3_dual | 225 | 59 |

总：12 run = 3 entry 模块 × 4 exit 变体。

### 2.2 报告口径 vs JSON 实际笔数

报告口径在 `docs/experiments/exit-matrix-report-2026-08-31.md:36-38` 与
`docs/experiments/stop-loss-matrix-ARCHIVE-2026-09-01.md:36-38`：

| 模块 | 报告笔数 | JSON 实际 | 差额 | 解释 |
|---|---|---|---|---|
| A | 1469 | 1521 | -52 | stop-loss-matrix 复刻 simulate_trade(a6_1) 时只算 ma_period=20 主信号（ma_period 分布 20=947, 60=432, 120=142） |
| B | 552 | 563 | -11 | 同上，stop-loss-matrix 复刻子集 |
| C | 224 | 225 | -1 | 同上 |

**8-31 矩阵 12 个 run 全部完整保留，逐笔明细可从 JSON 直接读出**，
无需重跑。报告里 1469/552/224 是 stop-loss-matrix 后续复刻口径。

### 2.3 trades 字段结构

每条 trade 至少含：

```json
{
  "symbol": "000568.SZ",
  "entry_variant": "v3",
  "exit_variant": "a6_1_costbasis",
  "is_first_touch": false,
  "ma_period": 0,
  "signal_date": "2018-09-21",
  "entry_date": "2018-09-25",
  "entry_price": 21.562,
  "stop_price": 14.212,
  "target_price": 24.932,
  "reward_risk": 0.3868,
  "exit_date": "2018-10-11",
  "exit_price": 14.862,
  "exit_reason": "exit_a6_1_costbasis",
  "holding_bars": 7,
  "r_gross": -0.9115,
  "r_net": -0.9145,
  "benchmark_clock_type": 4,
  "trend_stage": 2,
  "entry_reason": "2B/破底翻确认（收回 L1 且 EMA20 与 SMA20 共同向上）..."
}
```

每条 run JSON 顶层 keys：

- `run_id`, `created_at`, `status`, `disclaimer`
- `params`（实验参数快照）
- `data_range`（数据时间窗）
- `funnel`（漏斗统计）
- `groups`, `per_symbol`（按标的小计）
- `trades`（逐笔列表）

## 3. 8-25 / 8-26 早期 run（共 24 个）

这些是 8-31 矩阵之前的工作台历史 run（exit-matrix 之前），命名空间
8-25 (22) / 8-26 (2)。具体用途需逐个查 run_id 与 params 字段确认，
不在本目录范围内（8-31 矩阵是本快照的主归档对象）。

## 4. 9-01 事故的真实影响

按 `docs/experiments/stop-loss-matrix-ARCHIVE-2026-09-01.md:131-143` 与
commit `52f5cb3` (2026-09-01 19:07) 的实际状态：

- **`~/.lei_signal_lab/backtest_runs/` 完整保留**（最近修改 8-31 23:28）
- **事故损失的不是 run JSON 本身**，而是：
  - `configs/rules.v2.yaml` 账本（仅存活于服务进程内存，未入仓）
  - `src/lei_signal/backtest/` 未跟踪包（已通过 commit 52f5cb3 救回）
  - `stash@{0}` 6 个规则模块源码（仍在 `On feat/timing-backtest: WIP`）

**8-31 矩阵 12 个 run 逐笔明细可复现性：100%**。引用
stop-loss-matrix-ARCHIVE:36-38 行的 "A 1469 笔 / B 552 笔 / C 224 笔"
时，可从本目录 + simulate_trade(a6_1) 复刻脚本完全恢复。

## 5. 复现 8-31 矩阵的步骤

```bash
cd /Users/yongbiaoli/Desktop/lei-signal-lab
# 1. 确认数据池入仓（与本目录配套）
ls docs/experiments/raw/pool-snapshot-2026-08-25/ | grep -c '.bars.parquet'
# → 177

# 2. 读 8-31 矩阵任意 run
python3 -c "
import json
d = json.load(open('docs/experiments/raw/backtest-runs-snapshot-2026-08-31/20260831-231254-88cb12.json'))
print('trades:', len(d['trades']))
print('symbols:', len(set(t['symbol'] for t in d['trades'])))
print('first:', d['trades'][0]['symbol'], d['trades'][0]['signal_date'])
"

# 3. 复刻 stop-loss-matrix 报告的"无附加止损"子集（ma_period=20）
python3 -c "
import json
d = json.load(open('docs/experiments/raw/backtest-runs-snapshot-2026-08-31/20260831-231254-88cb12.json'))
a_subset = [t for t in d['trades'] if t['entry_variant']=='early' and t['ma_period']==20]
print(f'A ma_period=20: {len(a_subset)} trades')
# 应输出 947
"
```

## 6. 与 8-31 报告"53 标的"误写的对账

`docs/experiments/exit-matrix-report-2026-08-31.md:24` 写"全池 53 标的
（系统默认池）"——这是行文笔误。同一份报告:36-38 列了 A 1469 笔 / B 552
笔 / C 224 笔，这些笔数与本目录 12 个 run 的 JSON 一致（A 1521 笔 → 复刻
子集 1469 笔，差额已在 §2.2 解释）。

正确口径：8-31 矩阵 12 个 run 涉及 165 个有信号标的，**工作台扫过的
总池是 175 标的**（pool 当时大小；停-loss-matrix-ARCHIVE:7-8 与
exit-structural-stop-revival-ARCHIVE:39 两次以 run 记录为准纠正）。

## 7. 元数据

- 抓取快照时间：8-25 ~ 8-31（依 run 而定）
- git 入仓时间：2026-09-02
- 复刻来源：`~/.lei_signal_lab/backtest_runs/`（保留原始 mtime）
- 入仓方式：`cp -p` 保留 mtime
- 8-31 矩阵对应归档：
  - `docs/experiments/exit-matrix-report-2026-08-31.md`
  - `docs/experiments/stop-loss-matrix-ARCHIVE-2026-09-01.md`
