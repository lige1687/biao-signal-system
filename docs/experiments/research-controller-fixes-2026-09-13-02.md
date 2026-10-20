# R1 剩余问题：日期自洽与证据资格分离-2026-09-13

规范版本：`experiment-backtest-principles.md` v1.1；`definition-standard.md` 1.1.0；
`ai-execution-contract.md` 1.0.1；`experiment-report-template.md` 1.1.0

依据：主控书面复核报告 v1.1.0 §10（R2/R3 已确认，仅 R1 的证据可信边界继续返修）。
基线：`docs/experiments/raw/research-controller-fixes-2026-09-13-02/baseline.json`——
执行前已核对与主控报告 §10.1 实测指纹一致
（`data_quality.py` `d8f34018…`、9-13 报告 `f9a3b7dd…`、两份反例文件）。

网络：**0 次**。未运行收益回测、未写 OKR、未运行变异工具、未改生产或冻结输入、
0 个登记对象变更、未新增数据源/依赖/因子/参数/产品池/账户路径。
`trading_calendar.py` **未改**（已确认部分不重做）。
主控的两份固定反例文件**只读使用，未修改未删除**。

定义清晰程度 / 数据资格 / 实现核验 / 有效性证据 / 生产授权：

| 项 | 状态 |
|---|---|
| 定义清晰程度 | 不适用——未新增或修改任何登记对象 |
| 数据资格 | 有条件（与此前一致；本轮堵上"自述文件取得资格"，**真实数据裁决不变**） |
| 实现核验 | **253 项测试全过**（实跑计数）；ruff 干净；受保护文件与两份反例零改动 |
| 有效性证据 | 不适用——未检验任何因子、未运行任何账户 |
| 生产授权 | **无** |

研究状态：探索（返修交付）；**完成 R1 剩余问题即交回主控书面复核。**

---

## 一句话结论（大白话）

**上一轮我以为堵上了"假上市证明"，主控指出还差一层：证明是我自己写的，哈希算得再对也没用。**

道理很直白：之前系统检查的是"你给我的文件，和你说的哈希对不对得上"。
但如果**写文件的人、算哈希的人、填日期的人是同一个人**，
这三件事都对得上，也证明不了文件里写的是真的。

修复的办法不是再发明一套"怎么认出假文件"的规则——
那只会变成一个新的、能被同样绕过的开关。
而是**彻底换了个分法**：

- **"日期算得对不对"**和**"这份证明能不能当真的用"**，从今往后是两件完全分开的事。
- 日期那部分继续能算（上市和首份数据同一天？中间缺了该有数据的日子？都算得出来）。
- 但"能当真的用"这一层，**目前没有任何途径能通过**——
  因为"什么样的来源才算真的可信"这个标准根本还没建立。
  所以不管是明确标注"我是合成的"，还是什么都不写，
  还是自称 `official`，**一律不算数**。

主控的两份固定反例（一份明确标注合成、一份省略资格字段），
经过两个入口、两个用途，**修复前 8 个判断全部放行，修复后 8 个全部拒绝**。
日期诊断照常工作；真实数据的裁决照旧没变绿。

---

## 1. 主控剩余反例 → 根因 → 修复

| 项 | 内容 |
|---|---|
| 反例（复现成功，与主控 §10.4 逐行一致） | 两份主控构造的文件（`listing-explicit-synthetic.json`、`listing-qualification-omitted.json`），调用方为它们算正确哈希并传入 `check_prices` 与 `check_snapshot`：**8 个用途判断（2 文件 × 2 入口 × ranking/comparison）全部 ALLOWED** |
| 根因 | ① 上一轮把"哈希一致 + 字段匹配"当成了来源核验——但哈希只证明**字节一致**，不证明**内容为真**；调用方自写文件、自算哈希、自填日期时三者一致也不构成独立可信来源。② `synthetic` 标记只认一个固定字符串，省略或换成 `official` 就得到 `synthetic=False`，被当成"已核验的真实来源" |
| 修复 | `_validate_listing_evidence` 拆成两个独立结果：<br>・`dates`：日期诊断（coherent / earlier_than_window / residual / …），**只用于算法**；<br>・`source`：来源可回查性与资格状态。`qualified` **恒为 False**——当前未建立真实资料准入标准，自述/合成记录最高只能标记 `synthetic` 或 `unverified`。<br>`structural=True` 只有"来源取得真实资格 + 日期自洽"才成立，因此**当前任何输入都不会产生**；`starts_after_window` 一律保持 `cause=unconfirmed` |
| 不是新增什么 | 没有可信标签、没有白名单、没有 `trusted=True`、没有新认证平台。汇合点（资格×日期）在代码里显式可见，但没有调用方可填的开关 |
| 未做的事 | 真实上市资料的准入标准**另行授权**，不是本轮收口条件；不因为缺资料就继续允许自述文件取得资格 |

## 2. 主控 §10.3 六项要求逐条对应

| 要求 | 落实 |
|---|---|
| 1. 分开两种结果 | `dates` / `source` 两个独立子结构；合成/未核验来源在正常入口保持 `cause=unconfirmed` |
| 2. 未知不能默认真实 | qualification 省略 → `unverified`；自述 `official_verified_real` → 同样 `unverified`（有专门测试 `test_self_declared_official_qualification_gains_nothing`）；无 `trusted=True` 类开关 |
| 3. 两入口最终用途验证 | 两份固定反例 × `check_prices`/`check_snapshot` × ranking/comparison，测试断言到 `require_use` 层全部 REJECTED（`test_fixed_counterexamples_rejected_everywhere`），不停在 synthetic 标签 |
| 4. 保留算法正向例 | 同日上市（coherent）、早于评价期、残余缺口（点名残余日 `2026-05-29`）、周五上市（residual）各分支照常诊断；**未为保住旧的 `structural=True` 断言而保留错误放行**——三个旧测试改为按新语义断言，机制测试（accept_structural 本身）改用手工构造的 structural finding 覆盖 |
| 5. 不改 `allow_conditional` 语义 | 未改；`starts_after_window` 保持 WARN（conditional），未升级为 BLOCK |
| 6. 收窄报告结论、填完整哈希 | 本报告结论限定到实测通过的检查；修复后完整哈希见 §4；失败史见 §5 |

## 3. 修复前后对照

| 输入 | 修复前 | 修复后 |
|---|---|---|
| 显式合成文件 × check_prices | structural=True，ranking/comparison **ALLOWED** | structural=False（synthetic 标记保留），两者 **REJECTED** |
| 显式合成文件 × check_snapshot | 同上 ALLOWED | 同上 REJECTED |
| 省略 qualification 文件 × 两入口 | structural=True（synthetic=False 被当成已核验），ALLOWED | structural=False（unverified），REJECTED |
| `dummy` 字符串来源 | 已拒（上轮） | 仍拒，诊断同时给出"日期算法自洽"与"来源未核验"两层 |
| 自述 `official_verified_real` | （上轮会被当成已核验） | `unverified`，REJECTED |
| 同日上市/首报价（合成记录） | structural=True | structural=False，但 `dates.outcome=coherent` 照常给出 |
| 真实冻结数据 | 四项受限 | **完全不变**：描述/诊断可用，ranking/comparison 因 `starts_after_window`（未确认）拒绝，research_signal/attribution 因行动到达时间与停牌数据源拒绝 |

## 4. 实际命令、计数与完整哈希

```sh
python3 -m pytest tests/unit/test_controller_fixes_round4.py -q
# 修复前：§10.4 反例 8 判断全部 ALLOWED（复现成功）；修复后：8 passed（退出码 0）

python3 -m pytest \
  tests/unit/test_controller_fixes.py \
  tests/unit/test_controller_fixes_round2.py \
  tests/unit/test_controller_fixes_round3.py \
  tests/unit/test_controller_fixes_round4.py \
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
# → 253 passed（退出码 0）

python3 -m ruff check src/lei_signal/research/data_quality.py \
  src/lei_signal/research/trading_calendar.py \
  tests/unit/test_controller_fixes_round4.py \
  tests/unit/test_controller_fixes_round3.py \
  tests/unit/test_controller_fixes_round2.py \
  tests/unit/test_research_data_quality.py
# → All checks passed!
```

| 文件 | 修复前（主控 §10.1 实测） | 修复后（完整值） |
|---|---|---|
| `src/lei_signal/research/data_quality.py` | `d8f34018a0101fdabccb0d02bffa0e1e608cc642402298813699939228156bb6` | `ddad2ecfd676e0c1c9dbc3787afcc29024c53581f3eb664a97167f2e9fc8f783` |
| `src/lei_signal/research/trading_calendar.py` | `4651fa7d0e1e20ae…` | **未变** |
| `tests/unit/test_controller_fixes_round3.py` | `3d1d8def…` | 已变化（断言改到新语义、补 pytest 导入） |
| `tests/unit/test_controller_fixes_round2.py` | `f3182260…` | 已变化（正向例改到新语义） |
| `tests/unit/test_research_data_quality.py` | `11ba81e2…` | 已变化（三个旧测试按新语义重写、补 WARN 导入） |
| 两份固定反例文件 | `bdd93488…` / `3b6520db…` | **未修改未删除** |
| 受保护文件（896 项） | — | **零改动** |

## 5. 失败史（本轮自己的错误）

1. 新测试文件两处 evidence 字典少写右括号，首次收集即 `SyntaxError`；修括号后发现
   同一模式有两处，`replace_all` 一并处理。
2. 早前 ruff `--fix` 删掉了 round3 文件中"当时未使用"的 pytest 导入，
   本轮给该文件加 `pytest.raises` 断言时 `NameError`；已补回。
   （这再次说明机械清理导入要小心测试文件的未来使用。）
3. 三个依赖旧语义的测试（structural=True via 合成证据）按主控 §10.3-4 的要求
   全部改写为新语义断言，**没有为保通过而保留错误放行**；
   `accept_structural` 机制本身的正负路径改用手工构造 finding 覆盖。

## 6. 待确认项（交主控）

1. **真实资料准入标准**——这是目前唯一能让 `starts_after_window` 转为
   已确认固有属性的路径，但它需要主控定义"什么算真实合格来源"
   （交易所官方上市公告？产品招募书？），属另行授权事项。在此标准建立前，
   `starts_after_window` 一律保持未确认，ranking/comparison 继续拒绝——
   这是本轮认可的安全结果，不是待修的缺陷。
2. `_check_listing_dates` / `_verify_listing_source` 已拆成独立函数。
   若主控认为日期诊断部分可供其他研究复用（例如验证任何"起始日 vs 首报价"场景），
   可另列提取；本轮未做通用化。
3. 上一轮报告（-13）的"假的进不来"表述过宽，已在其顶部加纠正指针；
   更早的 -02 报告的同类表述已有指针。建议主控在导航层以本报告为当前有效版本。

**完成 R1 剩余问题即交回主控书面复核。
不宣布策略有效、因子有效、OKR 完成或获准交易。**
