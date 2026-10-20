# 双均线独立研究B0：收盘价适配与真实输入冻结-2026-09-15

> **2026-09-15 纠正指针（B0集中修复轮追加，正文保留不倒改）**：主控复核
> [factor-unit-b0-controller-review-2026-09-15.md](factor-unit-b0-controller-review-2026-09-15.md)
> 判定 R1–R4：来源/日历/代码身份存在"填上就算"路径、描述统计未消费完整合同、
> 冻结包运行身份链未闭合、"8跌3无"除息日推理不成立（不复权下市场涨跌可抵消除息）
> 且 159915 的 1651 日对比实际比的是 510300 快照（作废）；本地 CN 日历实际覆盖
> 2019-09-01—2026-06-30 而非声明的 1990 起；skip 归属与 mtime 语义已纠正。
> 逐项修复见 [factor-unit-b0-concentrated-fix-2026-09-15.md](factor-unit-b0-concentrated-fix-2026-09-15.md)
> 与 [readiness-corrections 附件](raw/factor-unit-b0-concentrated-fix-2026-09-15/source-decision-v2.csv)。

规范版本：`experiment-backtest-principles.md` v1.1 / `definition-standard.md` 1.1.0 /
`ai-execution-contract.md` 1.0.1 / `experiment-report-template.md` 1.1.0。
任务书：`docs/superpowers/plans/2026-09-15-factor-unit-close-adapter-glm.md` v1.0.0；
主控依据：[factor-unit-readiness-controller-review-2026-09-15.md](factor-unit-readiness-controller-review-2026-09-15.md)
v1.0.0（R1–R6 优先于 A 阶段不可执行提案）。
执行目录 `/Users/yongbiaoli/Desktop/lei-signal-lab`；分支 `codex/factor-unit-research-20260915`；
开工 HEAD `8ba16576b75e605aa1b0d0902568c760c4b99095`（与主控核对一致，未移动、未提交）。
执行模型：GLM（`builtin:bigmodel-coding-plan/GLM-5.3-Flash`）；实际开工/结束时刻见
`raw/factor-unit-close-adapter-2026-09-15/task-contract.json`（未倒填）。

对象引用：`candidate:lei.dual_ma.bull_state@draft-1`（候选卡只读，未入登记表）。
定义清晰程度 / 数据资格 / 实现核验 / 有效性证据 / 生产授权：
explicit（公式不变，复用生产函数）/ 四输入三档全部 producer_candidate_only /
44 项新测试 + 独立期望交叉核验 / **无（本轮零真实因子—目标统计）** / **not_authorized**。
研究状态：探索（B0 离线适配与资格）；OKR 未写（归主控）。

## 一句话结论（大白话）

**"只用收盘价做双均线状态检查"的接口已经建好并测通**——不需要成交量，不改老代码，
公式和线上一模一样。四个市场的价格文件也逐个查了来历：**没有一份能证明自己的分红
复权口径**（A股那只 510300 尤其可疑：它一半除息日有分红跳变、一半没有，还和冻结名义
价逐日完全相等），美股还缺一份真正的交易所日历。所以四只都还不能开始算真实表现，
差什么、差多少、需要什么授权，都写进了给主控的运行请求里；本轮没有算任何真实收益。

## 1. 直接回答任务书三问

1. **能不能使用只有收盘价的资料？** 能——但只对"双均线共同确认状态"这一个候选成立
   （R1：状态只依赖 close/EMA20/SMA20/滞后收盘/颜色）。`compute_close_state` 已实现：
   13 项单测通过（含独立手算 EMA 种子/递推、前缀不变、同比缩放不变、内部 NaN 诚实传播、
   与旧全量调用链 80 根逐行零差异）；分红缩放例未实现，显式标 skip 不谎报覆盖（R6）。
2. **四份输入各缺什么？** 见 `source-decision.csv` 与 §3：四份都停在
   `producer_candidate_only` 档——抓取代码找到了（A股 qfq 优先/新浪不复权回退；
   美股 yfinance auto_adjust=True），但没有运行日志/sidecar 证明现存文件走了哪个分支；
   510300 的除息日行为自相矛盾（5/8 有分红跳变、3/8 无，且与冻结名义价 1652 个重叠日
   逐值相等）；159915 无分红事件无从判别；SPY/QQQ 只与同族惯例文件 1.5e-6 级一致
   （不构成独立核验）。美股另缺 NYSE/Nasdaq 日历与半日市表。
3. **给主控哪份冻结包就能批准第一批历史描述？**
   `raw/factor-unit-close-adapter-2026-09-15/b0-real-readiness-check-01/`（manifest
   completed=true，含源码原字节、依赖/解释器、卡与规范指纹、来源表、日历证据、四文件
   结构资格），加上 [b1-run-request.md](raw/factor-unit-close-adapter-2026-09-15/b1-run-request.md)
   里的 4 项最小授权清单。**当前退出码 2：价格口径与美股市历不解决，主目标不得开算。**

## 2. R1–R6 纠正逐条处理（readiness-corrections.md 摘要）

| 项 | 处理 |
|---|---|
| R1 成交量 | close-only 薄适配，只复用 seeded_ema/classify_colors/dual_ma_bull_state；不填假量、不改旧接口；范围限定于本候选 |
| R2 时间 | session_close/fetched_at/available_at 三列分列；未知保持 null；`point_in_time_verified=false` 是默认诚实态 |
| R3 公式重叠 | 保留完整生产公式；等价解释（state ⟺ 绿色 ∧ C>SMA20，非浮点临界处）写入 docstring 与专项测试 |
| R4 来源不能猜 | source-decision.csv 三档语义；边界检查落盘 boundary-checks.json；无任何 verified 自填 |
| R5 窗口与风险 | lookback=20（观察前）与 horizon=22（观察后）分列；下行目标 `min(0, min(I(s)/I(e)-1))`；尾部未成熟单列 tail_immature |
| R6 证据边界 | 撤回"分红缩放已验证"；分红例 skip 并写明理由；旧证据引用一律标"旧主张" |

## 3. 四输入来源裁定（Task 2，≤8 份追踪记录用满）

追踪记录：①backfill_timing_data.py ②timing_backtest/data.py ③breadth-freeze readiness.json
（已明确记载"timing ETF 文件实际价格分支未留 sidecar"）④data-quality-jump-audit 报告
⑤midzone-breadth-timing 报告 ⑥frozen normalized-actions.json（510300 八笔分红）
⑦canonical-snapshot-v2 冻结名义价 ⑧px_SPY/px_QQQ 同族文件。
边界检查（boundary-checks.json，只做边界吻合不做总回报外推）：

- **510300**：与冻结名义价 1652 重叠日 ratio≡1.0（std=0）→ 排除干净 qfq；
  8 个冻结除息日中 5 个相邻日跌幅≈每份分红（2019-01-16 -1.851% vs 现金 1.851%；
  2026-01-19 -2.490% vs 2.531%）、3 个无跳变 → 亦非干净不复权 → **生产分支本地不可裁定**；
- **159915**：无分红事件、无交叉锚点 → 价格口径完全不可判别；
- **SPY/QQQ**：与同族惯例文件最大相对差 1.54e-6/1.46e-6（同惯例一致≠独立核验）；
  季度除息窗观察对判别无判别力（股息率低）。

四载体哈希与 A 阶段清单逐一致（未变，未标新快照）。

## 4. 时间/目标合同与合成描述（Task 3–4）

- `validate_study_contract`：20 项单测覆盖任务书全部最少反例（收盘冒充可得时间、
  无时区、半日市用16点、固定UTC偏移夏令时差一小时、日期冲突、日历缺来源/哈希不符、
  未知价格尺度、擅改 20/1/22、伪造对象引用、空源码键集合、自填可信标记、换标的、
  预测用途），每项均有合法对照；
- `describe_states`：仅 synthetic；目标按**日历位置** t+1/t+22 定位（删中间行不改变端点，
  专项测试）；真/假/未知三分离；无条件参照=同一可评价全集；逐年含空年份 n=0；
  连续状态段（unknown 闭合段）；每 23 格稀疏视角（锚点=首个已知状态观察，缺格跳过）；
  窗口重叠固定标注；无 NaN/Infinity 可严格 JSON 序列化；
- 独立期望脚本 `derive_description_expectations.py`（禁止 import 被测模块）产出
  description-expectations.json，与模块输出交叉一致（真组 n=3/mean=0.07/aux Worst
  -0.0909；无条件 n=25；D 组 9 可评+1 e_missing）。

## 5. 资格 CLI 与正式批次（Task 5）

`scripts/check_factor_unit_readiness.py`：退出 0/2/3 语义；先验哈希后消费；旧 current
指针不作为冻结身份；源码原字节入包（非只记 git HEAD）；manifest 最后写、completed 仅
成功置 true、输出拒绝覆盖。正式批次（每批留档 raw/，含合同、日志、verdict、包）：

| 批次 | 退出码 | 结果 |
|---|---|---|
| b0-synthetic-positive-01（合成正例） | 0 | manifest completed=true；代码/规范/卡/来源表/日历全部入包 |
| b0-synthetic-negative-01（缺来源表） | 2 | 阻断原因写全 |
| b0-real-readiness-check-01（真实资格 1/1） | 2 | 四载体结构合格（行数/首末日/无重复与 A 阶段一致）；主目标四票全 blocked；美股日历缺失；**未计算任何真实状态/目标** |

纠错批次 1/1：首批在适配器文件被本轮工具事故损坏前的字节上生成（见 §7 失败史），
已留档 `*-attempt-01` 并以最终字节重冻结；无其他超预算。

## 6. 测试与回归计数（实际数，不追目标）

- 新增：close_state 13 过 1 skip；study_contract 20 过；state_description 5 过；
  CLI 集成 6 过 → **44 passed, 1 skipped**；
- 完整相关回归第 1/2 次（命令见任务书 Task 6，日志 regression-run-01.log）：
  **193 passed, 1 skipped in 15.47s**（1 skip = factor_lab 既有 skip，非本轮）；
- ruff：本轮 9 个文件 **All checks passed**（行宽 100 仓库配置）；
- 零联网、零安装、零密钥、零真实表现统计、零 OKR 写入。

## 7. 失败史（本轮自己的错误，全部留痕）

1. **红→绿流程**：close_state/study_contract/state_description 均先写测试确认失败再实现
   （t1-red.log 留档）；多轮失败源于我方测试构造错误（NaN 比较未做 NaN 感知、
   负索引回绕、把 t+22 算成 t+23、夹具 NaN 污染预期干净窗口、成员不在面板先触发
   no_eligible_quotes），逐一修正并保留过程；
2. **模块两处缺陷由测试暴露**：状态段遇 unknown 未闭合（段计数丢失）；稀疏视角锚点
   被未知状态观察占据——均已修复并加回归断言；
3. **工具事故（纠错批次根因）**：我编写的批量行宽修复脚本对含代码的长行做了破坏性
   换行，6 个文件语法损坏；全部从上下文重写为等价干净版本（44 测试 + ruff 复全过），
   首批三份正式包以 `*-attempt-01` 留档并重跑——这是唯一动用纠错额度的操作；
4. CLI 退出码语义一次返工：被改输入应为 2（资料不足）而非 3（身份错误），经反例
   test_real_tampered_input_exit2 修正。

## 8. 能力边界：已实现 / 未实现

已实现：close-only 状态适配（复用生产公式）、合同校验与资格诊断、合成状态—目标描述、
冻结候选包 CLI、来源裁定三档语义、R1–R6 全部纠正。
未实现/未授权：真实数据上任何状态/目标计算（B1 未授权）；available_at 真实来源证据；
美股交易日历与半日市表；含分红财富目标的价格基础；宽度/情绪新表现（本轮禁入）。

## 9. 逐市场下一步（与 b1-run-request.md 一致，最多一个主推）

**主推：先裁定 A 股价格口径**（允许一次带复权声明的重抓或官方结算价核对）——
510300/159915 只差这一件事；美股需先补 NYSE 日历来源（另行申请）。四只不齐步走，
任一市场条件齐备即可由主控单独冻结放行。

## 10. 复核与复现

```sh
python3 -m pytest tests/unit/test_factor_unit_close_state.py \
  tests/unit/test_factor_unit_study_contract.py \
  tests/unit/test_factor_unit_state_description.py \
  tests/integration/test_factor_unit_readiness_cli.py -q
python3 -m ruff check src/lei_signal/research/factor_unit scripts/check_factor_unit_readiness.py \
  tests/unit/test_factor_unit_close_state.py tests/unit/test_factor_unit_study_contract.py \
  tests/unit/test_factor_unit_state_description.py tests/integration/test_factor_unit_readiness_cli.py
python3 scripts/check_factor_unit_readiness.py --contract <合同> --out <新目录>   # 拒绝覆盖
```

复核性质：本轮为执行者交付，待主控复核；所有新 JSON 经标准 json.loads 读回。

## 最小决策卡

| 必答项 | 本轮答案 |
|---|---|
| 改变什么 | 从三族盘点转向双均线收盘价适配与输入来源核实；主控 R1–R6 全部落地 |
| 增加什么证据 | 四输入三档来源裁定+除息日边界检查；44 新测试；独立期望交叉核验；三份正式冻结包 |
| 钱从哪里来 | 未研究收益来源；零真实因子表现结果 |
| 代价与边界 | 四载体主目标全 blocked（价格口径+美股市历）；v1.2.0 合成原型与登记表零改动 |
| 证据与结论 | 能用收盘价做状态接口（已证）；四份输入都还不能算真实表现（已证）；交付可冻结资格包 |
| 下一步与边界 | 主控按 b1-run-request 裁定最小授权（A股价格口径优先）；B1 未获令前不开算 |

## ARCHIVE

- 结案日期：2026-09-15
- 最终结论：工程交付完成（mixed）——适配可复用、四输入资格不足如实入档；无有效性结论
- 生产采用：未授权；B1 未启动
- 原始数据与复现入口：`docs/experiments/raw/factor-unit-close-adapter-2026-09-15/`
- registry.json：已登记（方法论与验证 / mixed）；INDEX：已补导航
- 新消费者手册：`docs/research/factor-unit-usage.md`
