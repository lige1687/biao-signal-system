# Round 3 语义修复交付报告

分支：`recovery/lei-round2`
起点：`8d2f6ec fix(round2): semantic closeout + EMA20 tiered structure binding`
（实际工作起点为其后一个提交 `f3e4f9e wip(round3): plan + failing repro tests for D1/D2`，
该提交由本轮开始前已存在于分支上）
终点：`05af7cd test(round3): 补齐任务书第十节的三个独立最小复现`
master：`c604037`（**未修改、未合并**）

本轮性质：**语义修复**。没有调整任何均线参数、结构参数或信号强度阈值；
没有用收益数据论证策略有效性；没有删除或弱化任何既有测试。

---

## 一、每个缺陷的根因分析

### D1 候选底部越级

**症状**：未确认的底部结构（`confirmed_date is None`）在全局双均线共同向上时
被抬到 `JOINT_CONFIRMED`。

**根因**：`state/machine.py::_resolve_opportunity()` 的判断条件是

```python
if live_bottoms and joint_now:
    return Stage.JOINT_CONFIRMED
```

`live_bottoms` 只表示「有存活底部」，不含任何确认信息；`joint_now` 是**全局**
双均线状态，与结构无关。两个都不带结构确认语义的量相乘，得出了一个
断言「这个结构已被共同确认」的结论。

**这不是条件写错，是信息来源错了**：状态机在自己重新推断阶段，
而事件层（`rules/ema_reclaim_tiers.py`）早已算出了逐结构的档位链。

### D2 early_watch 确认后不交接

**症状**：结构确认当天，`early_watch_by_structure[sid]` 不熄，
`early_strength_by_structure[sid]` 不亮，界面继续说「尚未确认」。

**根因**：`_advance_bound_latch()` 要求「升级当天重新出现一次 EMA20 交叉」
（参数 `reclaim_now_global`）。但 EMA20 收复是一次**进入事件**——
站上去之后不会每天重复发生。于是升级日永远等不到那个交叉。

**D1 与 D2 是同一个根因的两面**：状态机不消费事件层已绑定的档位链，
而是用全局标量（`joint_now` / `reclaim_now_global`）自己重推。
修复方式是架构性的——把状态机改成**事件档位的投影器**，
删除 `_advance_bound_latch()` 与 `reclaim_now_global` 整条路径。

### D3 SQLite 增量运行生命周期失真

**根因**：`signal_events` 以 `event_id` 为主键、`INSERT OR IGNORE` 写入。
`valid_until` / `lifecycle_id` / `ended_event_id` 这三个字段**不是事件身份**，
而是随观测窗口变化的推断结论。第一次写入把它们锁死后，
更长窗口下重跑算出的正确窗口无法落库。

### D4 159915 回放断言过弱

**根因**：`test_chinext_replay.py` 只断言「存在任意反转底部」加一个
7 元素的宽泛阶段集合。把整段档位判断删掉，测试照样绿。

### D5 交易日历无法从生产路径注入

**根因**：`aggregate_weekly()` 支持 `calendar` 参数，但
`analyze()` / `analyze_bars()` 都不透传。结果是**底层测试能注入、
生产路径永远注入不了**——测试覆盖的是一条真实运行中不存在的代码路径。

### D6 UI 只有全局布尔

**根因**：界面展示的是 `early_watch_by_structure` 这类全局聚合，
多结构并存时非主结构的观察链被完全隐藏；且确认后的结构仍出现在
观察档区块里，文案说「尚未确认」。

---

## 二、修复方案与关键取舍

### D1 + D2：状态机改为事件档位的投影器

新增 `StructureObservation`（frozen dataclass）：

```python
@dataclass(frozen=True, slots=True)
class StructureObservation:
    structure_id: str
    lifecycle_id: str
    tier: str | None
    opened_on: date
    last_upgraded_on: date
```

`DayState` 增加 `observations: dict[str, StructureObservation]`。
**失效/未激活的结构从 dict 中删除，而不是存 `None`** —— 让
`observations.get(sid) is None` 成为「当前无观察实例」的唯一判据。

`run_state_machine` 每日的处理顺序：

1. 颜色转黑 → 删除**全部**观察实例（结构本身仍存活）
2. 用当日事件推进/开启实例：
   - `lifecycle_id` 不同 → 开新实例
   - `lifecycle_id` 相同且 `TIER_RANK` 更高 → 升级，刷新 `last_upgraded_on`
   - **不检查当天是否有新交叉**（D2 的核心）
3. 清理不再 live 的结构
4. 由 `observations` 推导阶段

`_max_active_tier_for_stage()` 对**未确认结构**的 `early_watch` 返回
`(Stage.NO_CLUE, 0)` —— 不抬阶段、也不短路后续的 `STRUCTURE_CONFIRMED` 兜底。
这一点是 D1 的直接封堵：观察档只写理由，不产生阶段抬升。

删除的代码：`_advance_bound_latch()` 全函数、`reclaim_now_global` 参数、
`_resolve_opportunity()` 的 `joint_now` / `long_supportive` 入参。

### D3：选择 Plan A（事件不可变 + 生命周期快照表）

**取舍说明（任务书要求）**：

| | Plan A 快照表 | Plan B 严格 UPSERT |
|---|---|---|
| 存储 | 每次运行 × 每个事件一行，线性增长 | 每个事件恒定一行 |
| 查询 | 需按 `as_of` 降序取最新，多一层索引 | 直接读 |
| 审计 | 可回答「300 根那天系统认为的窗口是什么」 | 历史结论被覆盖，无法回答 |
| 语义 | 承认「不同 as_of 下的不同结论都对」 | 断言「后写的对、先写的错」 |

**选 Plan A 的理由**：生命周期是**随观测窗口变化的推断结论**，不是事实的修正。
300 根下 `valid_until=2023-02-25`（窗口内尚未结束）与 600 根下
`valid_until=2024-04-20`，在各自的 `as_of` 下**都是正确的**。
UPSERT 会把前者当成错误抹掉，破坏 point-in-time 审计链——
而 point-in-time 纪律正是这个系统的核心约束。
代价是存储线性增长，本报告接受这个代价。

迁移 005：

```sql
CREATE TABLE IF NOT EXISTS event_lifecycle_snapshots (
    event_id       TEXT NOT NULL,
    run_id         TEXT NOT NULL,
    as_of          TEXT NOT NULL,
    valid_until    TEXT,
    lifecycle_id   TEXT,
    ended_event_id TEXT,
    recorded_at    TEXT NOT NULL,
    PRIMARY KEY (event_id, run_id, as_of)
);
CREATE INDEX IF NOT EXISTS idx_lifecycle_as_of ON event_lifecycle_snapshots(as_of);
```

`signal_events` 保持 `INSERT OR IGNORE`，但写入前用 `_assert_event_identity()`
校验身份字段未被改写，冲突抛 `EventIdentityConflictError`。

**身份字段刻意不含 `evidence_json`**：`evidence` 里存的是 close / ema20 / sma20
这类观测快照，两次重算之间合法地不同（浮点精度、窗口长度），
把它算进身份会产生假冲突。这一点在实现过程中由
`test_local_parquet_upload_drives_analysis` 真实触发过。

### D5：全链路透传日历

`analyze()` / `analyze_bars()` 新增 `calendar: TradingCalendar | None = None`，
`analyze()` 透传给 `analyze_bars()`，后者传给 `aggregate_weekly()`。
UI 三个调用点全部传入 `_TRADING_CALENDAR`。

**默认日历的保守方向已在 UI 侧注明**：`WeekdayCalendar` 默认不带节假日表，
因此遇到未知节假日的短周只会**判定该周尚未结束**（偏保守，不会提前完成一周），
不会产生前视。侧栏有 caption 说明这一点。

### D6：逐结构展示

新增 `_render_per_structure_observations(state, structures)`，输出一张表，
每行一个**存活结构**（包括**没有观察实例的结构**，避免隐藏非主链），列为：

结构ID / 档位 / 生命周期ID / 开启日 / 最近升级日 / 当前是否有效 / 失效原因 / 下一步等待条件

文案规则的实现：
- `early_watch` 区块用 `st.info`（中性信息），**从不用 `st.success`**
- 该区块明确写「不构成买入信号」
- 「尚未确认」只出现在 candidate 结构上
- 已确认结构不进入 early_watch 区块
- 高档位（joint / trend）用 caption 点名绑定的是哪个结构

---

## 三、逐结构状态机真值表

`_max_active_tier_for_stage()` 的完整映射（结构确认状态 × 档位 → 阶段）：

| # | 结构确认 | 当前档位 | 结果阶段 | 说明 |
|---|---|---|---|---|
| 1 | 任意 | 无实例 | `BOTTOM_WATCH`（有确认底部时 `STRUCTURE_CONFIRMED`） | 兜底 |
| 2 | candidate | `early_watch` | `BOTTOM_WATCH` | **不抬阶段**，只写理由 |
| 3 | candidate | 任意 + 全局 joint | `BOTTOM_WATCH` | D1 封堵 |
| 4 | candidate | 任意 + joint + 长周期改善 | `BOTTOM_WATCH` | D1 封堵 |
| 5 | confirmed | `early_watch` | `BOTTOM_WATCH` | 确认结构不应停在观察档 |
| 6 | confirmed | `structure_confirmed` | `EARLY_STRENGTH` | |
| 7 | confirmed | `joint_confirmed` | `JOINT_CONFIRMED` | |
| 8 | confirmed | `long_trend_improved` | `TREND_REINFORCED` | |
| 9 | 任意 | 转黑当日 | 实例全删 → 回落 | 结构本身仍存活 |
| 10 | invalidated（触C） | 任意 | 实例永久删除 | 不可复活 |

分层推进只能是：candidate → early_watch → structure_confirmed →
joint_confirmed → long_trend_improved，**不得跨级**。

---

## 四、测试清单与断言强度说明

本轮新增/重写的测试文件：

| 文件 | 测试数 | 锁定内容 |
|---|---|---|
| `tests/integration/test_round3_state_ladder.py` | 12 | 第三节真值表，写死确切日期+阶段+档位+lifecycle_id |
| `tests/integration/test_round3_incremental_sqlite.py` | 5 | 300→600 增量、幂等、as_of 降序取最新、身份冲突 |
| `tests/integration/test_round3_calendar_pipeline.py` | 6 | 日历透传、默认保守方向、追加未来 bar 不改过去结论 |
| `tests/unit/test_round3_ui_per_structure.py` | 10 | **端到端状态对象 → 渲染结果**（非源码字符串检查） |
| `tests/integration/test_round3_counterexamples.py` | 8 | 第九节的 7 个错误实现反例 + 1 个附加 |
| `tests/integration/test_chinext_replay.py` | 5 | 逐日精确时间线（重写，原为宽泛断言） |

**断言强度的具体做法**（针对上一轮「测试太弱」的批评）：

1. **不用存在性断言**。禁止 `assert bottoms`、`assert stages & {...}` 这类
   写法——`test_counter_chinext_must_assert_specific_timeline` 会扫描源码
   禁止 `assert bottoms, ` 重新出现。
2. **写死确切值**。日期、阶段、档位名、`lifecycle_id` 全部字面量比对。
3. **每条测试先校验前提**。例如 D1 的测试先断言
   `joint.loc['2024-01-11'] is True`，确保不是「因为条件没触发所以通过」。
4. **UI 测试捕获渲染调用而非读源码**。`RecordingStreamlit` 记录方法名+参数，
   断言打到**捕获到的 DataFrame 与文案**上。且其 `__getattr__` 对未实现的
   方法**抛 AttributeError**——实现改用新渲染方法而测试没跟上会立刻暴露，
   不会静默漏断言。

---

## 五、七个错误实现反例（第九节）

`tests/integration/test_round3_counterexamples.py`，8 条全部自动化：

| # | 错误实现 | 反例测试 | 捕获方式 |
|---|---|---|---|
| M1 | `live_bottoms and joint_now` 直接抬到 JOINT | `test_counter_candidate_joint_now_should_not_lift_to_joint_confirmed` | 候选结构 + 真实 joint 触发，断言仍 BOTTOM_WATCH |
| M2 | 升级日要求重新出现 EMA20 交叉 | `test_counter_upgrade_must_not_require_fresh_reclaim` | 确认日/共同确认日/改善日均无新交叉，断言档位仍升 |
| M3 | 确认后 early_watch 不熄 | `test_counter_early_watch_must_close_on_confirmation` | 确认日断言 `early_watch is False and early_strength is True` |
| M4 | 结构之间互借信号 | `test_counter_structures_must_not_borrow_each_others_signals` | 两结构并存，各自档位互不影响 |
| M5 | SQLite 保留旧 valid_until | `test_counter_sqlite_must_not_silently_keep_old_valid_until` | 二次写入后读最新快照必须是新窗口 |
| M6 | 回放测试用宽泛断言 | `test_counter_chinext_must_assert_specific_timeline` | 源码扫描 + 要求具体档位名出现 |
| M7 | `analyze()` 忽略 calendar | `test_counter_analyze_must_not_ignore_calendar` | 注入含节假日的日历，周线结果必须不同 |
| M+ | 全局 joint 抬升未确认结构 | `test_counter_joint_confirmed_must_come_from_observation_tier` | 阶段必须来自 observation.tier |

**手工变异验证记录**：每条反例都通过手工把实现改回错误版本、
确认测试变红、再改回来的方式验证过区分力。其中一次变异暴露了
测试本身的问题，见第七节。

---

## 六、三个独立最小复现（第十节）

脚本位于 `scripts/round3_repro/`，可独立运行。以下是**修复后的真实输出**。

### 复现 1：candidate 不得越级

```
$ PYTHONPATH=src /opt/homebrew/bin/python3.11 scripts/round3_repro/repro1_candidate_no_level_jump.py
== 前提条件（证明触发条件确实出现了）==
结构 S-CAND: status=candidate confirmed_date=None
全局 joint_now @01-11 = True
全局 joint_now @01-12 = True
长周期改善     @01-12 = True
事件层产出档位 = ['early_watch']

== 逐日阶段（修复后）==
2024-01-01  stage=bottom_watch         joint_now=False long_sup=False tier=None
2024-01-02  stage=bottom_watch         joint_now=False long_sup=False tier=early_watch
2024-01-03  stage=bottom_watch         joint_now=False long_sup=False tier=early_watch
2024-01-04  stage=bottom_watch         joint_now=False long_sup=False tier=early_watch
2024-01-05  stage=bottom_watch         joint_now=False long_sup=False tier=early_watch
2024-01-08  stage=bottom_watch         joint_now=False long_sup=False tier=early_watch
2024-01-09  stage=bottom_watch         joint_now=False long_sup=False tier=early_watch
2024-01-10  stage=bottom_watch         joint_now=False long_sup=False tier=early_watch
2024-01-11  stage=bottom_watch         joint_now=True  long_sup=False tier=early_watch
2024-01-12  stage=bottom_watch         joint_now=True  long_sup=True  tier=early_watch

PASS: 全部 10 个交易日均停在 bottom_watch，候选结构未越级。
exit=0
```

注意 01-11 / 01-12 两行：`joint_now=True`、`long_sup=True` 都真实触发了，
阶段仍是 `bottom_watch`。这排除了「因为条件没出现所以通过」。

### 复现 2：early_watch 确认后正确交接

```
$ PYTHONPATH=src /opt/homebrew/bin/python3.11 scripts/round3_repro/repro2_early_watch_handover.py
== 前提条件 ==
结构确认日 = 2024-01-05
EMA20 收复交叉发生在哪些日子（True = 当天新交叉）：
  2024-01-02  <<< 唯一一次进入交叉
→ 01-05 / 01-11 / 01-12 当天都没有新交叉，若实现仍要求「重新交叉」，这三档全部点不亮。

== 事件层档位链（共享 lifecycle_id）==
  2024-01-02  tier=early_watch            strength=35  lifecycle=ema20_reclaim_rising:S-HANDOVER:2024-01-02
  2024-01-05  tier=structure_confirmed    strength=60  lifecycle=ema20_reclaim_rising:S-HANDOVER:2024-01-02
  2024-01-11  tier=joint_confirmed        strength=75  lifecycle=ema20_reclaim_rising:S-HANDOVER:2024-01-02
  2024-01-12  tier=long_trend_improved    strength=85  lifecycle=ema20_reclaim_rising:S-HANDOVER:2024-01-02

== 逐日状态机投影（修复后）==
date        stage               early_watch  early_strength  tier                  new_cross  lifecycle
2024-01-01  bottom_watch        False        False           None                  False      -
2024-01-02  bottom_watch        True         False           early_watch           True       ema20_reclaim_rising:S-HANDOVER:2024-01-02
2024-01-03  bottom_watch        True         False           early_watch           False      ema20_reclaim_rising:S-HANDOVER:2024-01-02
2024-01-04  bottom_watch        True         False           early_watch           False      ema20_reclaim_rising:S-HANDOVER:2024-01-02
2024-01-05  early_strength      False        True            structure_confirmed   False      ema20_reclaim_rising:S-HANDOVER:2024-01-02
2024-01-08  early_strength      False        True            structure_confirmed   False      ema20_reclaim_rising:S-HANDOVER:2024-01-02
2024-01-09  early_strength      False        True            structure_confirmed   False      ema20_reclaim_rising:S-HANDOVER:2024-01-02
2024-01-10  early_strength      False        True            structure_confirmed   False      ema20_reclaim_rising:S-HANDOVER:2024-01-02
2024-01-11  joint_confirmed     False        True            joint_confirmed       False      ema20_reclaim_rising:S-HANDOVER:2024-01-02
2024-01-12  trend_reinforced    False        True            long_trend_improved   False      ema20_reclaim_rising:S-HANDOVER:2024-01-02

PASS: 01-05 观察档熄灭 + 确认档点亮；01-05/01-11/01-12 三次升级
      当天均无新 EMA20 交叉；四档共享同一 lifecycle_id ema20_reclaim_rising:S-HANDOVER:2024-01-02。
exit=0
```

`new_cross` 列只有 01-02 一天为 True，而档位在 01-05 / 01-11 / 01-12
连升三级——D2 的「升级不得要求再次交叉」得到直接证明。

### 复现 3：SQLite 300 根 → 600 根增量生命周期一致

```
$ PYTHONPATH=src /opt/homebrew/bin/python3.11 scripts/round3_repro/repro3_sqlite_incremental_lifecycle.py
== 两次运行 ==
run-300  bars=300  as_of=2023-02-24  events=624
run-600  bars=600  as_of=2024-04-19  events=1942
共同 event_id = 624

== 区分力证明（这条复现不是恒真的）==
300 根 与 600 根 下 valid_until 不同的共同事件：15 条
  例：double_bottom:0cd6a4961185600e5981e3ef
      300 根算出 valid_until = 2023-02-25
      600 根算出 valid_until = 2024-04-20
  → 旧的 INSERT OR IGNORE 会把 300 根那个值锁死，库里永远读到过期窗口。

== 修复后：每个共同 event_id 的最新快照 vs 内存最新结果 ==
  bottom_c_lifecycle:344049be7873413c79a35e7a
      最新快照 as_of=2024-04-19 run_id=run-600 valid_until=2022-07-29 lifecycle=None
  bottom_c_lifecycle:5d31062370b630680efd32e7
      最新快照 as_of=2024-04-19 run_id=run-600 valid_until=2022-07-29 lifecycle=None
  bottom_c_lifecycle:738b0056fd8e0c317b2f71f9
      最新快照 as_of=2024-04-19 run_id=run-600 valid_until=2022-11-18 lifecycle=None
  ...（共 624 条全部逐字段比对）

== 审计留痕（Plan A 的代价与收益）==
run-300 的历史快照仍在库中：624 行 —— 可回答「300 根那天系统认为的有效窗口是什么」。

PASS: 624 个共同事件的最新生命周期快照与 600 根内存结果逐字段一致（valid_until / lifecycle_id / ended_event_id / run_id）。
exit=0
```

「15 条会漂移」这一行是关键——它证明这条复现有区分力，
而不是在一个 `valid_until` 恰好相同的数据集上恒真。

---

## 七、发现的测试自身缺陷（自查）

**D5 的日历测试最初没有区分力**，这是本轮最重要的一次自查。

`test_analyze_passes_calendar_through_to_weekly` 的第一版：把 `analyze_bars`
中的 `calendar` 参数改成忽略（人工变异），测试**仍然是绿的**。
根因是构造 fixture 时用了 `pd.bdate_range`，bar 落在了节假日当天，
于是 `available_date = max(calendar_last, last_observed)` 在两种日历下
算出同一个值——日历的差别被数据本身抵消了。

这正是上一轮被复核批评的那类问题：测试覆盖了代码，却没有覆盖语义。

**修复方式**：
1. 重建索引，**排除**节假日日期，让两种日历必然给出不同的周划分
2. 加一条显式的区分力守卫：`assert len(direct) != len(default_weekly)`

**重新变异验证**：把 `analyze_bars` 的 calendar 改回忽略 → **2 条测试变红**；
把 `analyze()` 的透传去掉 → **1 条测试变红**。区分力确认。

---

## 八、UI 展示规则的落地位置

| 规则 | 实现位置 | 对应测试 |
|---|---|---|
| 逐结构表（7 个必需字段） | `_collect_structure_observations()` | `test_render_shows_all_seven_required_columns` |
| 开启日/升级日取实例真实日期 | `StructureObservation.opened_on / last_upgraded_on` | `test_render_shows_exact_lifecycle_dates` |
| 「尚未确认」只给 candidate | `_TIER_DESC_CN` + 分支 | 文案断言测试 |
| 已确认结构不进 early_watch 区块 | `_render_per_structure_observations()` 过滤 | 渲染捕获断言 |
| 观察档用 `st.info` 不用 `st.success` | 同上 | 断言 `"success" not in recorder.methods()` |
| 明写「不构成买入信号」 | 同上的 info 文案 | 文案断言 |
| 高档位点名绑定结构 | 结尾 caption | 断言 caption 含结构 ID |
| 多结构不隐藏非主链 | 收集函数包含**无观察实例**的存活结构 | `test_multiple_structures_are_all_rendered` |
| 失效原因可读 | `_describe_inactive_reason()` | 断言含「转黑」+「仍存活」 |

---

## 九、四项验收门禁（真实输出）

```
$ /opt/homebrew/bin/python3.11 -m pytest -q -rs
....................s................................................... [ 20%]
........................................................................ [ 40%]
........................................................................ [ 60%]
........................................................................ [ 80%]
.......................................................................  [100%]
=========================== short test summary info ============================
SKIPPED [1] tests/integration/test_chinext_replay.py:68: 未找到真实 159915 数据快照：tests/fixtures/159915_real.parquet。
本测试只针对真实数据；合成数据请看下面的合成黄金回放测试。
358 passed, 1 skipped in 46.24s

$ /opt/homebrew/bin/python3.11 -m ruff check src tests
All checks passed!

$ /opt/homebrew/bin/python3.11 -m mypy src
Success: no issues found in 44 source files

$ git diff --check
（无输出，exit=0）
```

唯一的 skip 是缺失真实 159915 快照，属任务书明确要求保留的显式跳过。

---

## 十、159915 回放的真实数据状态

**`tests/fixtures/159915_real.parquet` 不存在。没有伪造。**

处理方式（按任务书第七节）：
- `test_real_snapshot_timeline_if_available` 保留**显式 skip**，
  skip 原因写明缺哪个文件
- **同一条状态链在合成 fixture 上完整跑通**，4 条测试**始终执行、不跳过**：
  - `test_synthetic_golden_full_timeline_assertions` —— 逐日精确时间线
  - `test_synthetic_golden_rejects_pretend_skip` —— 守卫上一条不被删/不被 skip
  - `test_synthetic_golden_observation_tier_chain` —— structure_confirmed →
    joint_confirmed → long_trend_improved，单调不降，共享一个 lifecycle_id
  - `test_synthetic_golden_no_new_ema20_cross_on_subsequent_upgrades` ——
    同一 lifecycle 内的后续升级当天不得有新交叉

合成路径用的是既有的 `golden_delayed_upgrade()`（架构文档第 15 节的漏信号案例），
它天然产出 2022-08-23 结构确认 / 2022-08-26 共同确认 / 2022-09-09 长周期改善。

**关于第四条测试的命名修正**：最初写成「所有升级日都不得有新交叉」，
在 2022-08-23（第一档）失败——那天的 reclaim 是**开启 lifecycle 的进入事件**，
本来就需要交叉。D2 要治的是「升级要求再次交叉」，不是「进入不许有交叉」。
因此改名为 `..._on_subsequent_upgrades` 并跳过第一条事件。
这是断言范围的修正，不是为了让测试变绿而放宽——升级日的约束一条没减。

---

## 十一、已知限制

1. **真实 159915 行情快照缺失**。当前所有回放结论建立在合成 fixture 上。
   合成数据能验证状态机语义，**不能**验证真实行情下的形态识别质量。
2. **Plan A 的存储线性增长**。`event_lifecycle_snapshots` 随
   运行次数 × 事件数增长，长期需要归档策略（本轮未实现）。
3. **默认交易日历不含节假日表**。方向是保守的（不会提前完成一周），
   但周线聚合的精度依赖调用方注入真实日历。UI 侧已注明。
4. **`_render_per_structure_observations` 的渲染替身是白名单式的**。
   若实现新增渲染方法而未同步 `RecordingStreamlit`，测试会抛
   AttributeError 而非静默通过——这是刻意设计，但需要维护者知晓。
5. **本轮未做任何策略有效性验证**。没有回测、没有收益统计，
   本报告不含任何关于「策略是否赚钱」的结论。
6. **真实快照路径当前只有骨架断言，不是逐日精确时间线**。
   `test_real_snapshot_timeline_if_available` 的断言强度目前是
   「状态链必须出现 / 不得跳跃 / 最终阶段须含 TREND_REINFORCED」，
   因为任务书给出的 2025-06-24、2025-11-14 等日期与真实数据可能有偏差，
   确切日期需要在真实数据到位后**人工核对固化**。
   逐日精确断言目前**只在合成路径上成立**。
   因此不能说「只差一个 parquet 文件就完备了」——补上数据之后，
   真实路径的精确时间线仍是一项待完成工作。

---

## 十二、结论

代码语义门禁通过：

- `pytest -q -rs`：358 passed, 1 skipped
- `ruff check src tests`：All checks passed
- `mypy src`：Success, no issues in 44 source files
- `git diff --check`：clean
- 三个独立最小复现全部 PASS，且各自附带前提条件/区分力证明

**真实行情集成验收仍待完成**——`tests/fixtures/159915_real.parquet`
尚未提供，真实数据路径的回放断言处于显式跳过状态。
且如第十一节第 6 条所述，**即便快照到位，真实路径当前也只有骨架断言**，
逐日精确时间线仍需人工核对固化，不是「只差数据」。

**不得据此宣称策略有效或可直接实盘。**

---

### 提交记录（`recovery/lei-round2`，未合并 master）

```
05af7cd test(round3): 补齐任务书第十节的三个独立最小复现
aa0375b chore(round3): 清理 ruff/mypy 门禁
132b245 test(round3): 7 条错误实现反例自动化
0b38282 wip(round3): 159915 golden replay (D4)
25cb08d wip(round3): UI per-structure observation chain (D6)
c484ed2 wip(round3): production path wires trading calendar (D5)
af7e898 wip(round3): sqlite lifecycle snapshots (D3)
3a5571c wip(round3): state machine consumes tier events (D1 + D2)
f3e4f9e wip(round3): plan + failing repro tests for D1/D2   ← 本轮起点
```
