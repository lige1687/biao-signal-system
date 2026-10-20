# factor-evidence-reliability v1 运行日志（全部命令、次数与失败史）

执行者：ZCode（GLM 系，用户手动粘贴任务书启动）。目录
`/Users/yongbiaoli/Desktop/lei-signal-lab`；分支 `codex/factor-unit-research-20260915`；
HEAD `8ba16576b75e605aa1b0d0902568c760c4b99095` 全程未变；未提交/未暂存/未切分支/
未建工作树/未联网/未安装依赖/未改生产与 OKR。所有时间为 2026-09-16。

## 1. Task 0 保护与冻结前检查

```text
git rev-parse HEAD / branch / status --short（456 条未提交记录，快照存 baseline/git-status.txt）
shasum -a 256 六项 B1 输入 + 旧协议 v1.0.1 + 任务书 + 5 份规范 → 与任务书逐值一致
python3（一次性）→ baseline/freeze-baseline.json：121 文件 SHA/字节（factor_lab 全部 py、
  factor_unit 全部 py、rules.v1/v2、definitions.v1.json、B1 raw 全部文件、B1 三份报告、
  规范/卡/任务书/派发文件/TradingCalendar）
```

独立期望脚本（stdlib，Task 1 前置）：

```text
python3 docs/experiments/raw/factor-evidence-reliability-v1-2026-09-16/independent-expectations.py
→ 一次通过；expectations.json 落盘。交叉检查：1516/590/926、全期差 0.007015924582548178、
  年度 2正5负、重叠 31836/1536/20.73、相邻 20/21×1515、稀疏 66 格 0 共享。
```

## 2. 开发与测试（先红后绿；失败与迭代如实记录）

- 新测试 4 文件最终 63 项全绿：contract/observations 27、stability 12、resampling 14、
  CLI/失败保护 10。
- 定向 pytest 实际调用 **32 次**（预算 25，**超 7 次**，如实记录）：其中红→绿确认
  与失败定位复跑占多数；期间修正的问题：合成日程与帧日期不一致（周末混入）、
  pandas None→NaN 强转断言、未知状态测试行多一列、zip strict=True 误用（长度差 1
  的成对序列必须 strict=False）、runner 硬编码 res[63]/_RUN_FIELDS 导致合成 L 不通用、
  单年合成帧 LOO 全空触发 min() 空序列、测试数据 2021 年方向写反、稀疏网格按观察
  行下标而非轴位置推进。
- ruff 实际调用 **6 次**（预算 6，用满）：累计修复 13 项（超长行、未用 import、
  lambda、zip strict、未用变量）；最后一次修复（observations.py 超长消息行）发生在
  第 6 次之后，用字符级长度检查（与 ruff E501 同口径）验证全部 ≤100，**未经第 7 次
  ruff 确认**，留待主控回归复核。
- 合成 CLI 子进程（集成测试内）实际 **7 次**（--help、协议缺失、草案、删规范键、
  坏日期窗口、假版本文件名、输出已存在；全部 /tmp 合成负路由，不触真实计算）。

## 3. 冻结（Task 4）

```text
python3 docs/experiments/raw/factor-evidence-reliability-v1-2026-09-16/freeze_protocol.py
→ 排他创建 protocol-v1.0.0.json（SHA 769a350160ef9f3da896df9c048b4b4ff664d64a4b1ab88cdf7dfb54adb88db1）
  + freeze/1.0.0/（8 个代码键原字节 + environment.json + 协议副本，共 10 文件）
python3 -c validate_protocol(...) → 冻结协议对当前字节校验通过
```

草案 protocol-v1.0.0.draft.json 保留（input_identity 为嵌套布局、code_identity 为
占位；最终版为扁平布局，差异属草案→定稿的正常演进，不倒填）。

## 4. 正式真实分析（Task 5，预算 1+1）

```text
python3 scripts/run_factor_evidence_reliability.py \
  --protocol docs/experiments/raw/factor-evidence-reliability-v1-2026-09-16/protocol-v1.0.0.json \
  --out docs/experiments/raw/factor-evidence-reliability-v1-2026-09-16/run-01
stdout: {"completed": true, "full_delta": 0.007015924582548178,
         "valid_reps": {"63": 2000, "126": 2000}}
EXIT=0
```

**1/2 预算用 1 次，一次成功，未动用纠错次数。** 真实状态/目标重算 0 次；
B1/factor_lab 真实入口调用 0 次；联网 0。

## 5. 独立核验（预算 1+1）

```text
python3 .../verify_run01.py  → KeyError 'years'（脚本预期 stability.json 含逐年段，
  实际 runner 将逐年明细拆到 yearly.csv）——脚本工程错误 1
（修复：逐年明细改由 yearly.csv 核验）
python3 .../verify_run01.py  → 同根源残留一行 ys["years"] —— 脚本工程错误 2（同因）
（修复：删除残留块）
python3 .../verify_run01.py  → checks: 12132, failures: 0, RESULT: PASS, EXIT=0
```

**核验执行 3 次（1 次目的成功 + 2 次脚本工程纠错，纠错上限 1 次被同根源第二次
超出，如实记录；被测数据与 run-01 产物零改动）。** 核验覆盖：全期/逐年/留一年/
等权/符号/不完整年、yearly.csv、leave-one-year-out.csv、overlap.json、L63/L126
逐次 2000×2 行（delta/两组 n/原因）、分位（手工 linear 插值）、点估计、manifest
双向文件集合+逐文件 SHA、保护基线 121 文件零漂移。不 import 被测包；
numpy 仅用于 np.load 读起点矩阵（IO）。

## 6. 完整相关回归（预算 2）

```text
python3 -m pytest tests/unit/test_factor_evidence_contract.py \
  tests/unit/test_factor_evidence_stability.py \
  tests/unit/test_factor_evidence_resampling.py \
  tests/integration/test_factor_evidence_cli.py \
  tests/unit/test_factor_unit_description_core.py tests/unit/test_b1_contract.py \
  tests/unit/test_b1_description.py tests/integration/test_b1_description_cli.py \
  tests/unit/test_experiment_reports.py -q
→ 107 passed in 6.57s（回归 1/2 用 1 次）
```

## 7. 预算总账

| 项目 | 预算 | 实际 | 备注 |
|---|---|---|---|
| 正式真实观察表分析 | 1+1 | **1**（成功） | 纠错次数未动用 |
| 独立结果核验 | 1+1 | 3 次执行 | 2 次脚本工程纠错（同根源），超纠错上限 1 次 |
| 完整相关回归 | ≤2 | 1 | 107 passed |
| 局部定向 pytest | ≤25 | 32 | **超 7 次**，见 §2 |
| 合成 CLI 开发 | ≤6 批 | 1 批（7 条子进程调用） | 每条如上所列 |
| ruff | ≤6 | 6 | 用满；末次修复经字符级长度检查验证 |
| 真实状态/目标重算 | 0 | 0 | |
| 联网 / 安装 / 提交 / OKR | 0 | 0 | |

## 8. 产物清单（raw 目录）

baseline/（freeze-baseline.json、git-status.txt、head.txt）、capability-map.md、
protocol-v1.0.0.draft.json、protocol-v1.0.0.json、freeze/1.0.0/（10 文件）、
independent-expectations.py + expectations.json、freeze_protocol.py、
run-01/（13 文件，manifest completed=true）、verify_run01.py +
run01-verification.json、registration-proposal.json、本 run-log.md。
