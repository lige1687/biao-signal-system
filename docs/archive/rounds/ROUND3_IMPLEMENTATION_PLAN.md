# Round 3 语义修复 —— 实施计划

> 分支：`recovery/lei-round2`　起点：`8d2f6ec`　master 保持 `c604037` 不动
> 性质：**语义修复，不是策略优化**。不调参、不用收益证明策略、不弱化旧测试。
> 目标：让状态机、事件生命周期、UI、SQLite 对**同一条结构观察链**给出一致结果。

---

## 0. 起始现场

```
分支      recovery/lei-round2
HEAD      8d2f6ec
工作区    干净（无用户未提交修改需要保留）
```

---

## 1. 已确认的缺陷（全部用数据复现，非推测）

### D1　候选底部越级（`state/machine.py::_resolve_opportunity`）

```python
if live_bottoms and joint_now:          # ← live_bottoms 含 candidate
    opportunity = Stage.JOINT_CONFIRMED
```

`live_bottoms` 包含未确认结构，`joint_now` 是**全局**双均线状态，二者都与
「这个结构自己走到哪一档」无关。实测（`confirmed_date=None` 的纯候选结构）：

```
日期          joint_now   机会阶段
2024-01-10  False       bottom_watch
2024-01-11  True        joint_confirmed   ← 越级
2024-01-12  True        joint_confirmed   ← 越级
```

同一段代码还有两处同源问题：`EARLY_STRENGTH` 判据用 `live_bottoms` 而非
`confirmed_bottoms`；`TREND_REINFORCED` 建立在可被全局触发的 `JOINT_CONFIRMED` 之上。

### D2　early_watch 确认后状态不交接（`state/machine.py::_advance_bound_latch`）

```python
if has_bound_event and reclaim_now_global:   # ← 还要求当天重新出现 EMA20 交叉
```

EMA20 reclaim 是**一次进入**事件，结构确认日通常不会再交叉一次，于是确认档
latch 永远点不亮。加上 watch / early 两套 latch 互不交接，实测：

```
日期          新EMA交叉   机会阶段              early_watch  early_strength
2024-01-02  True      bottom_watch         True         False
2024-01-05  False     structure_confirmed  True  ←错误   False ←错误   （确认日）
2024-01-11  False     joint_confirmed      True  ←错误   False ←错误   （靠全局joint越级）
```

事件生成器**本身是对的**——它已产出共享同一 `lifecycle_id` 的完整四档链：

```
ema20_reclaim_rising:S-TIER:2024-01-02
  2024-01-02 early_watch → 01-05 structure_confirmed
  → 01-11 joint_confirmed → 01-12 long_trend_improved
```

状态机根本没消费它。这是本轮**最核心**的架构问题：状态机自己另算一套，
与事件层各说各话。

### D3　SQLite 增量运行生命周期失真（`storage/sqlite_store.py::write_events`）

`INSERT OR IGNORE` + `event_id` 主键。`valid_until` / `ended_event_id` 会随后续
行情变化，二次重跑时新值被整条忽略。实测（同序列 prefix300 → full600）：

```
第一次（300根）：714 条，inserted=714
第二次（600根）：1729 条，inserted=1015 ignored=714
共同事件 714 条，生命周期不一致 25 条

double_bottom:058d993a13b77734894e86fd
  数据库 valid_until = 2023-02-25      ← 陈旧
  内存正确 valid_until = 2024-04-20
```

数据库把仍然有效的事件错误标记为已结束。

### D4　159915 测试不是黄金回放（`tests/integration/test_chinext_replay.py`）

只断言「存在任意反包底部」+「最终阶段属于一个含 7 个成员的宽泛集合」。
该集合几乎覆盖所有非 `NO_CLUE` 状态，等于没有断言。无法验证漏信号案例。
附带缺陷：`_real_or_synthetic_data()` 类型注解写的是 `pd.DataFrame`，实际返回 tuple。

### D5　生产路径不接交易日历（`compose/pipeline.py`）

```python
weekly_trend = compute_weekly_long_trend(aggregate_weekly(bars))   # 无 calendar
```

`aggregate_weekly()` 与 `build_snapshot()` 都已支持 `calendar` 参数，但
`analyze()` / `analyze_bars()` 不透传，生产路径永远退回无节假日的周一至周五日历。
底层测试能注入、生产却注不进 —— 属于「可测但不可用」。

### D6　UI 只展示全局布尔

`_render_diagnostics` 的核对表全是全局标量（`early_strength_active`、
`joint_confirmed_now`），多结构并存时只显示主结构。observation 层缺少
结构ID / 档位 / 开启日 / 升级日 / 失效原因 / 下一步等待条件。

---

## 2. 核心设计决策

### 2.1 状态机改为「消费事件档位」，不再自己另算

D1 与 D2 是同一个根因的两面：状态机用全局标量推断阶段。修复方式不是补丁式地
加条件，而是让状态机**逐结构投影事件层已经算好的档位链**。

引入 `StructureObservation`（状态机侧的逐日投影）：

| 字段 | 含义 |
|---|---|
| `structure_id` | 绑定结构 |
| `lifecycle_id` | 当前观察实例；转黑后重开则换新 id |
| `tier` | 当前档位（四档之一，`None`=无活跃观察） |
| `opened_on` | 本实例开启日 |
| `last_upgraded_on` | 最近一次升级日 |

逐日推进规则：

1. 当日有绑定到该结构的事件 → 按事件的 `lifecycle_id` / `tier` 更新；
   `lifecycle_id` 与当前不同即视为**新实例**（`opened_on` = 当日）。
2. 当日无事件 → **保持上一日状态**（转强是持续状态，不是脉冲）。
   —— 这一条直接消灭「升级日要求重新 EMA20 交叉」。
3. 颜色转黑 → 关闭观察实例（`tier=None`），结构本身存活；重新转强由事件层
   分配新 `lifecycle_id`。
4. 结构触及 C 失效 → 移出 `live_bottoms`，observation 一并丢弃，不复活。

**`reclaim_now_global` 这个参数被彻底删除**。事件本身即判据；再叠加一个全局
条件，正是 D2 的病灶。

### 2.2 档位 → 机会阶段映射（唯一映射点）

| 结构状态 | 观察档位 | 机会阶段 | 理由 |
|---|---|---|---|
| 无 live 结构 | — | `NO_CLUE` | |
| candidate | 无观察 | `BOTTOM_WATCH` | |
| candidate | `early_watch` | **`BOTTOM_WATCH`** | 观察档不抬阶段 |
| confirmed | 无观察 | `STRUCTURE_CONFIRMED` | |
| confirmed | `structure_confirmed` | `EARLY_STRENGTH` | 已确认 + 转强活跃 |
| confirmed | `joint_confirmed` | `JOINT_CONFIRMED` | |
| confirmed | `long_trend_improved` | `TREND_REINFORCED` | |

两条硬约束：

* **只有结构自身已确认，其观察档才能抬阶段。** `early_watch` 按 `tier_on` 的定义
  只可能出现在未确认结构上；此处再做一次显式排除，双保险。
* **阶段取各结构独立推进后的最大值**，不允许跨结构拼装条件
  （A 的确认 + B 的转强 ≠ 任何升级）。

`joint_confirmed_now` 保留在 `DayState` 中，仅作为「全局双均线当前状态」的
**描述性信息**供界面展示与维度标签使用，**不再驱动任何阶段升级**。

### 2.3 SQLite 选型：方案 A（不可变事件 + 生命周期快照表）

选 A 不选 B，理由是 B 会**丢失演变过程**。

事件的身份（发生日、规则版本、证据、结构ID）是历史事实，永不改变；
而生命周期是**随观测窗口变化的推断结论**——同一事件在 300 根和 600 根行情下
`valid_until` 本就不同，二者都是各自 as_of 下的正确答案。用 UPSERT 直接覆盖
等于宣称「后面的才对、前面的是错的」，抹掉了「系统当时是怎么认为的」这个
审计线索。研究系统需要能回答「上周五我们以为它什么时候结束」。

新增表：

```sql
CREATE TABLE event_lifecycle_snapshots (
    event_id       TEXT NOT NULL,
    run_id         TEXT NOT NULL,   -- 无 run_id 时用 as_of 兜底
    as_of          TEXT NOT NULL,   -- 该次分析的最后数据日
    valid_until    TEXT,
    lifecycle_id   TEXT,
    ended_event_id TEXT,
    recorded_at    TEXT NOT NULL,
    PRIMARY KEY (event_id, run_id, as_of)
);
```

`signal_events` 保持 `INSERT OR IGNORE` 不变（身份不可变）。
提供 `read_latest_lifecycle(conn, event_id=...)`：按 `as_of` 降序取最新快照，
`as_of` 相同则取 `recorded_at` 较晚者。

身份字段冲突检测同样保留：同 `event_id` 但身份字段不同 → **报错**，不静默忽略。

### 2.4 交易日历透传

`analyze(calendar=...)` → `analyze_bars(calendar=...)` → `aggregate_weekly(calendar=...)`，
一路显式传递。UI 两条路径（普通行情、CSV/Parquet 上传）使用同一常量，
默认仍为保守的 `WeekdayCalendar()`（无节假日表），并在界面明示当前口径。

---

## 3. 状态转换真值表

`S` = 结构自身状态，`T` = 该结构当前观察档位，`→` = 机会阶段。
（风险维度独立，不在此表）

| # | S | T | 全局 joint | 机会阶段 | 说明 |
|---|---|---|---|---|---|
| 1 | 无结构 | — | 任意 | `NO_CLUE` | |
| 2 | candidate | 无 | False | `BOTTOM_WATCH` | |
| 3 | candidate | 无 | **True** | **`BOTTOM_WATCH`** | **D1 反例**：全局双均线不得越级 |
| 4 | candidate | `early_watch` | False | `BOTTOM_WATCH` | 观察档不抬阶段 |
| 5 | candidate | `early_watch` | **True** | **`BOTTOM_WATCH`** | **D1 反例** |
| 6 | candidate | `early_watch` | True + long改善 | **`BOTTOM_WATCH`** | **D1 反例**：不得进 `TREND_REINFORCED` |
| 7 | confirmed | 无 | False | `STRUCTURE_CONFIRMED` | 确认但无转强 |
| 8 | confirmed | `structure_confirmed` | False | `EARLY_STRENGTH` | **确认日不要求新 EMA20 交叉** |
| 9 | confirmed | `joint_confirmed` | True | `JOINT_CONFIRMED` | 同一 lifecycle 升级 |
| 10 | confirmed | `long_trend_improved` | True | `TREND_REINFORCED` | 同一 lifecycle 升级 |
| 11 | confirmed | 任意 | 转黑当日 | 观察关闭 → 回落 `STRUCTURE_CONFIRMED` | 结构不失效 |
| 12 | 触及 C | — | 任意 | 结构移出 live | 永久失效，不复活 |
| 13 | A=confirmed, B=candidate | B 有 `early_watch` | 任意 | 按 A 独立结果 | **不得跨结构借用** |

`early_watch_by_structure[sid]` ⇔ `T == early_watch`
`early_strength_by_structure[sid]` ⇔ `T ∈ {structure_confirmed, joint_confirmed, long_trend_improved}`

特别地，结构确认日起必须同时满足：

```
early_watch_by_structure[sid]    == False
early_strength_by_structure[sid] == True
```

---

## 4. 准备修改的文件

| 文件 | 改动 |
|---|---|
| `src/lei_signal/state/machine.py` | 核心重写：`StructureObservation`、事件驱动推进、映射表、删除 `reclaim_now_global` |
| `src/lei_signal/compose/pipeline.py` | `analyze` / `analyze_bars` 增加 `calendar` 参数并全链路透传 |
| `src/lei_signal/storage/sqlite_store.py` | 迁移 005：`event_lifecycle_snapshots`；`write_event_lifecycles()`、`read_latest_lifecycle()`；身份冲突检测 |
| `src/lei_signal/ui/app.py` | 按结构展示观察链；日历口径提示；两条路径口径一致 |
| `src/lei_signal/compose/interpreter.py` | 跟随状态机新字段（如有必要） |
| `tests/integration/test_chinext_replay.py` | 改为逐日精确时间线断言框架 |
| `tests/integration/test_round3_state_ladder.py` | 新增：D1/D2 真值表逐行 + 逐日断言 |
| `tests/integration/test_round3_incremental_sqlite.py` | 新增：增量回放一致性 |
| `tests/integration/test_round3_calendar_pipeline.py` | 新增：日历透传 |
| `tests/integration/test_round3_counterexamples.py` | 新增：7 条错误实现反例自动化 |

---

## 5. 验收命令

```bash
/opt/homebrew/bin/python3.11 -m pytest -q -rs
/opt/homebrew/bin/python3.11 -m ruff check src tests
/opt/homebrew/bin/python3.11 -m mypy src
git diff --check
```

三项独立最小复现（修复后须给出真实输出）：

1. candidate 不得越级
2. early_watch 确认后正确交接
3. SQLite 300 根 → 600 根增量生命周期一致

---

## 6. 提交节奏（防上下文耗尽）

每个模块独立完成并通过相关测试后立即 WIP 提交，最终整理：

1. `wip(round3): plan + failing repro tests`
2. `wip(round3): state machine consumes tier events`
3. `wip(round3): sqlite lifecycle snapshots`
4. `wip(round3): calendar wiring`
5. `wip(round3): golden replay + UI per-structure`
6. 最终：报告 + 汇总

不回滚、不覆盖、不删除现有提交。
