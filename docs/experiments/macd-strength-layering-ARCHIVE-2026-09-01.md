# MACD 强度状态 × 入场模块信号质量分层 · 归档摘要（2026-09-01）

> Prompt E（五路拆分第五任务）。任务定位：MACD 强度状态（`rules/macd_strength.py`
> 八状态，研究代理）能否给**已经能产生买卖点的 A/B/C/D 入场模块**的历史信号做
> 质量分层——即"同一模块触发的信号，MACD 扩散期 vs 收敛期，后续收益/胜率是否有
> 统计上可信的差异"。**不产生任何交易事件，不下买卖结论**。
>
> 脚本（预注册协议写死于 docstring）：`docs/experiments/raw/macd-strength-layering/run_macd_layering.py`
> 逐笔标注记录：`raw/macd-strength-layering/records_macd_layering.json`（1,066 笔有效信号）
> 分析输出：`raw/macd-strength-layering/analysis_macd_layering.json`
> 双跑哈希（PYTHONHASHSEED=0 / 42，一致）：records `76beb306…ddb7cb`、analysis `fd1b8744…04cb0e`

## 一句话结论

**42 个分析格 0 个通过预注册线（N≥20 双侧且置换 p<0.05），且真实成立格数 0
低于标签打乱基线的 95 分位（2 格）——"MACD 扩散/收敛状态可给 A/B/C/D 信号做
质量分层"整体判负，不高于随机噪音。A 模块两市场方向同号（cn +0.59R / us +1.31R）
但均不显著（p=0.42 / 0.35）、胜率无差、20 日前瞻收益方向相反——尾部驱动的假象。
按 Prompt E 的唯一合法用途回答用户问题：不建议把 MACD 强度状态接进 A/B/C/D
确认层作参考权重。**

## 信号本体与口径（重要：为什么不是重跑引擎）

当前分支 `recovery/lei-round2` 的 `backtest` 包处于**半重构状态**：
`engine.py:33` 仍 `from first_ma_pullback import ENTRY_CONFIRMED, ENTRY_EARLY`，
但该检测器已不再导出这两个名字（import 即 ImportError），且 A/B/C 检测器的
evidence 已不含引擎要求的 `stop_price`/`variant` 契约字段——**A/B/C 无法在本分支
重跑**。2026-08-27/28 实验所用的完整契约代码只存在于当时的工作树（未提交、已丢失）。

因此信号本体取自已入 git 的 `execute_run` 全量逐笔归档（standard 费用 +
limit_guard，2016-08→2026-08）：

| 池 | 模块 | 归档 | N | 配置 |
|---|---|---|---:|---|
| cn | A | `raw/breadth_overlay/wf_a_noshrink.json` | 655 | early / a6_1_costbasis / cm0.5 / 无量能过滤，44 只 ETF |
| cn | B | `raw/lifecycle_combo/T1_Bp_a61.json` | 101 | breakout / a6_1 / cb30+cl3%，83 只个股（含 000300.SS） |
| cn | C | `raw/lifecycle_combo/T2_C_stocks_v3_b15.json` | 177 | v3 / a6_1 / bias −15% 过滤 |
| cn | D | `raw/lifecycle_combo/T2_D_stocks_default.json` | 2 | 默认（十年 2 笔） |
| us | A | `raw/stage_b200/A_us.json` | 96 | early / a6_1 / cm0.5 / shrink，XLK+IGV+SOXX |
| us | B | `raw/stage_b200/B_us.json` | 37 | breakout / a6_1 / cb20+cl10% |

标注层为本脚本新算，全部只用信号日 T 及以前数据：MACD 状态 =
`compute_features`（账本 12/26/9）+ 生产读数器 `read_macd_strength(row[T], row[T-1])`；
牛熊 = 逐笔自带 `benchmark_clock_type`（cn=000300.SS、us=^GSPC 时钟，映射沿用
`run_regime_gate.py`：1,2=牛 / 3=横 / 4,5=熊）；宽度 = `cache/timing` 的
b200/b50 于 T 日值三分区（低≤30 / 中 / 高≥70，对齐冠军三档边界）。
主结果变量 r_net（引擎原模拟净 R）；次级 fwd20（入场后第 20 根收盘/入场价−1）。

## 一、通过清单

**空。** 无任何模块×维度组合通过预注册线（判定标准见脚本 docstring，跑前写死）。
方法学质控全部执行：双跑哈希一致、阴性对照 200 次标签打乱、42 格全量落盘
（含不成立格），无跑后调参。

## 二、证伪清单

| 实验 | 假设 | 结果 | 验证强度 |
|---|---|---|---|
| ★MACD 扩散/收敛 × A 模块质量分层 | 扩散期信号优于收敛期 | cn +0.59R (N=316/218, p=0.42)、us +1.31R (N=59/27, p=0.35)：两市场同号但无一显著；胜率无差（cn 23.1% vs 22.0%；**us 扩散 32.2% < 收敛 33.3%**，均值差全靠尾部）；fwd20 方向相反（cn −0.98pp / us −1.87pp）；牛熊×宽度×b50 共 9 个样本充分格 0 成立 | 42 格全量 + 双市场 + fwd20 交叉 + 双退出（B） |
| MACD 分层 × B 模块 | 同上 | N=36/32（cn）；a6_1 退出 diff +0.24 vs b3_dual 退出 diff −0.56——**换退出方向即翻转**；us N=13/17 diff −0.72 | 双退出对照 + 双市场（样本不足标注） |
| MACD 分层 × C 模块 | 同上 | **结构性不可检验**：177 笔中 170 笔（熊市 127 笔中 121 笔）触发时已是"空头收敛"，空头扩散为 0——bias−15% 过滤与"深度负乖离+乖离收敛"天然共线，二元分层无方差 | 状态分布审计（非检验） |
| MACD 分层 × D 模块 | 同上 | 十年 2 笔（cn 个股池默认参数） | 样本不足，仅记录 |

阴性对照：真实成立格 0 ≤ 打乱 200 次分布 95 分位 2（均值 0.53、最大 4）——
与 9 个样本充分格 × 5% 假阳性率的期望 ~0.45 格吻合，基线自洽。

## 三、观察中

- **cn.A × b50 低区**：扩散 +1.52R（胜率 24.6%）vs 收敛 −1.49R（胜率 14.6%），
  N=69/48，p=0.093——最接近线但未过；对应 b200 低区格 +1.70R p=0.50 不跟随，
  且属 42 格中的事后最亮点（多重比较暴露），按纪律**仅记录不跟踪**（继承
  heiti-ARCHIVE 对小样本发现的谨慎措辞）。
- **cn.C 牛熊主效应**（忽略 MACD）：熊市格 +0.31R (N=127) vs 牛市格 −0.39R
  (N=19)，牛−熊 = −0.70R，**p=0.035 全实验唯一过线的主效应**。与 C 模块
  "破底翻=深跌后反转"的机制自洽；但注意 kuandu-quanzhan"接刀格补丁"三变体
  证伪已证明 2018/2024 阴跌事前不可区分，此主效应**不可反推为可用的熊市加仓规则**。
- **B 模块触发的 MACD 状态分布**：34 多头扩散 + 31 空头收敛（占 96%）——
  "均线密集突破"的入场前提（六线密集）在 MACD 语言里就是"乖离收敛"，两者
  结构共线（见冲突发现 3）。

## 四、下一步方向（≤3）

1. **不把 MACD 状态接入 A/B/C/D 确认层**（用户问题的直接答案）：本实验判负 +
   与形态定义共线，接入即重复计数。
2. C 模块牛熊分层的样本外观察可挂进打分卡记账（成本≈0），与"接刀格补丁"
   证伪边界一起看；不新开回测。
3. 若要恢复模块回测能力，需先修复 backtest 包事件契约（engine 期望的
   stop_price/variant 已从检测器消失）——**代码工程欠账**，是否修由用户拍板，
   本任务未动 `src/`。

## 五、冲突发现

1. **与 trd-gate-report（regime/宏观门三连败）**：机制不同（本任务是
   "宏观状态→信号质量标注"，trd-gate 是"宏观状态→仓位门"），但结论同向——
   信息在 regime 层真实存在（cn.C 牛熊主效应 p=0.035），而 **MACD 层零增量**。
   如实承认：这次也一样，"第四门"在 MACD 上不存在；同时 trd-gate 的教训
   （宏观信息做门→判负）依然成立，cn.C 主效应只能当标注不能当闸。
2. **与 kuandu-quanzhan（宽度结论）**：未重现"宽度低位信号更好"——cn.A
   b200 低−高 = −0.61R (p=0.61)、cn.B −2.29R (p=0.30) 均不显著。不冲突但
   划界：宽度组的通过结论在**三档引擎层/双极值事件层**（宽度决定买不买），
   模块信号层（A/B/C/D 已触发后的质量）宽度与 MACD 均无增量——两层不可互推。
3. **同义反复风险（SKILL 红线的定量印证）**：`macd-reading` 口径明确
   "MACD=乖离率=强度，与价格趋势高度共线"。本实验给出定量证据：C 模块
   触发时 96% 已是"空头收敛"（bias 过滤≈乖离收敛），B 模块前提"均线密集"
   ≈ MACD 收敛——把 MACD 接进 B/C 确认层等于对同一信息重复计数（与
   kuandu-quanzhan"双指标仓位叠加=重复计数"证伪同机制）。
4. **组内数据欠账披露**（不新增结论，只声明缺口）：① cn.A 归档运行的 44 只
   ETF 池未带基准标的 → 655 笔全部无牛熊标注（牛熊维度对 cn.A 不可用）；
   ② us 侧逐笔仅 XLK/IGV/SOXX（科技类），SPY/QQQ 本体无归档，且 us 十年
   91/2/3 的牛/熊/横分布使 us 牛熊维度几乎无方差；③ C 模块唯一逐笔归档带
   bias−15% 过滤层。

## 附：诚实条款自查

- [x] 判定标准先写死于脚本 docstring 再跑，跑完未改（含格级/模块级/阴性对照/
      冲突检查四层规则与 42 格全量落盘）
- [x] 双跑复现：PYTHONHASHSEED=0/42 两 JSON sha256 一致（HASH_MANIFEST.txt）
- [x] 阴性对照：200 次组内标签打乱，真实 0 格 ≤ 打乱 95 分位 2 格，如实判负
- [x] 样本不足格（N<20 双侧）全部显式标注，不进判定；D 模块 N=2 如实记录
- [x] 信号本体非本分支重跑（引擎半重构无法重跑），取自已归档逐笔并全文披露
      选择规则与配置；标注层只用 T 日及以前数据，无未来函数
- [x] 不产生买卖点、不改 `src/`、不改 `macd_strength.py`、不接仓位系数、
      不在 `reportsIndex.ts` 登记

## 复现

```bash
cd /Users/yongbiaoli/Desktop/lei-signal-lab
PYTHONHASHSEED=0  python3 docs/experiments/raw/macd-strength-layering/run_macd_layering.py
PYTHONHASHSEED=42 python3 docs/experiments/raw/macd-strength-layering/run_macd_layering.py
# 两次运行后 HASH_MANIFEST.txt 两行 sha256 应一致（约 2-3 分钟/次）
```
