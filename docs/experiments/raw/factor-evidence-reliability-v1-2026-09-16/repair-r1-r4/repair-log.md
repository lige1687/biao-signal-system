# R1–R4 限定返修台账（2026-09-16）

执行者：ZCode（原执行 agent）。依据：主控《因子证据可靠性v1：主控复核与
限定返修》§8。范围：只修 R1–R4；旧冻结产物（run-01/、protocol-v1.0.0.json、
freeze/1.0.0/、verify_run01.py 及其输出、主控证据目录）全部只读；未重跑
B1 状态/目标、未重跑正式真实分析、未改种子/L/评价期/对象/统计目标；
未联网/安装/提交；registry/INDEX/OKR/生产零接触。

## 1. 修前红（反例固化，定向 pytest 第 1 批）

新增/改造失败测试 10 项，覆盖主控全部反例：

- R1：`test_object_ref_and_use_bound`（改 wrong.object@9 / production /
  删键必须拒）；合成产物身份对账 `test_run_analysis_synthetic_complete_manifest`
  （symbol/来源/L/reps/seed/用途逐项，断言不含 510300 与 B1 路径）；
  `test_run_analysis_real_mode_identity_conflict_rejected`；
  `test_run_analysis_requires_explicit_mode`。
- R2：`test_overlap_primary_legal_set_hand_example`（主控手算例：合法标签+
  一行排除+缺端点+仅接触端点；主结果 2 行 42 引用 42 唯一，secondary 3 行
  含非法行）；`test_overlap_sparse_classifies_expected_points`（应有 5 /
  可审计 3 / reasons {illegal_row:1, missing_endpoints:1}）；
  `test_overlap_sparse_grid_no_shared_intervals_synthetic`（含 missing_row
  分类）；`test_empty_frame_structured_not_estimable`；
  `test_run_analysis_single_group_completes_not_estimable`（单组完成诚实
  报告，不再 TypeError）；`test_main_returns_2_for_not_estimable_real_data`
  （进程内 monkeypatch 装载，出口 2、无输出目录）；
  `test_validate_rejects_multiple_symbols`。
- 红批结果：2 个收集错误（R1 常量不存在）+ 其余新测试失败，旧逻辑反例
  全部复现。

## 2. 最小修复（修后定向绿：72 passed；回归 116 passed）

代码改动 5 个键（对照表见 repair-manifest.json；__init__/CLI/TradingCalendar
三键零改动）：

| 文件 | 修复 |
|---|---|
| contract.py | R1：OBJECT_REF/FIXED_USE 常量 + validate_protocol 顶层逐值绑定 |
| observations.py | R2：多标的输入明确拒绝（不隐式合并） |
| stability.py | R2：overlap_audit 主结果=共同合法集合；all_rows_with_endpoints 独立命名；稀疏锚点沿原轴推进并分类应有/可审计/缺失原因；非法行保留原轴位置 |
| resampling.py | R2：空表结构化 not_estimable:empty_frame（不再抛参数异常） |
| runner.py | R1/R2/R4：_resolve_identity 真实/合成分离（合成不冒用 B1 身份；真实模式标的冲突/缺合同身份写盘前拒绝）；合成 protocol.source.json 为占位说明；单组/缺组完成诚实报告；_report_md 全字段 None 安全、组内百分比/组间百分点、目标口径与留一年措辞按 R4 精确化；卡片记录实际 L/reps/seed；main 资料不足出口 2（不建输出目录） |

## 3. 真实值不受影响的说明

全部改动位于：协议校验层（新增必需字段，不影响已通过的数学）、重叠审计的
集合选择与输出结构（run-01 输入全合法，主结果数值与旧输出相同——由
`test_overlap_real_b1_matches_independent_expectations` 对 expectations.json
逐值确认）、空表/单组分支（真实数据两组齐全不触发）、输出模板与身份元数据。
统计核心（分组均值/年度/留一年/重抽索引与分位）零改动；run-01 与
verify_run01.json 原样未动。

## 4. 预算实账（§8 限额）

| 项目 | 限额 | 实际 |
|---|---|---|
| 定向 pytest（含红批） | 6 | **5**（红 1 + 绿 4；第 5 批 72 passed 后停） |
| 完整相关回归 | 1 | 1（116 passed in 8.39s） |
| ruff | 2 | 2（发现 I001/SIM211，均已修；修后未经第 3 次 ruff，以字符级行长检查+语法检查复核，留主控回归确认） |
| 手册合成例 | 1 | 1（exit 0：50 行全合法、delta 0.02、直方图 {20:49}、索引 [4,0,1,1,2]） |
| 补件哈希核验 | 1 | 1（7 份原件复制前逐项匹配旧协议指纹，全部一致） |
| 合成 CLI/进程内输出测试 | 1 批 | 1 批（进程内 5 项新增用例；子进程负路由未重跑——上一轮 7 条负路由仍由回归覆盖） |
| 真实重跑 / 真实状态目标重算 | 0 | 0 |

## 5. 产物

- `repair-r1-r4/code-snapshot/`（8 键修后原字节）+ `repair-manifest.json`
  （新旧 SHA 对照、变更说明、绑定声明：旧 run-01 绑定旧字节，修后代码仅由
  合成测试证明，未来正式真实运行须新版本协议+主控授权）。
- `supplement/standards/`（5 规范+任务书+候选卡原字节）+
  `supplement-manifest.json`（路径映射、6 项真实输入外部依赖指纹、
  verify_run01.py 覆盖限度声明、32 次测试原件不可恢复声明）。
- 执行报告 §11 带日期纠正（口径/解释/返修摘要）。
- 手册 `docs/research/factor-evidence-reliability-usage.md` 合成例已修。

## 6. 未完成 / 留主控

- 修后 ruff 未第三次运行确认（额度用尽），建议主控回归时顺带执行。
- 未来任何正式真实运行需要新协议版本（绑定 repair 快照字节），本轮未获
  授权、未创建。
- 主控复核报告所述"完整 32 次测试原件"确认不可恢复，已如实声明，不补造。

## 7. 2026-09-17 追加纠正（S3，依据主控复核 §9.4）

§1"红批结果：2 个收集错误（R1 常量不存在）+ 其余新测试失败，旧逻辑
反例全部复现"表述过宽：收集错误意味着 pytest 在收集阶段即停止，当时
只能证明测试文件与尚未新增的 contract 常量不兼容，**不能**证明未被执行
的行为反例（身份冒用、单组渲染崩溃、区间口径等）已逐一运行并复现；
也未保存相应的逐项原始失败日志。行为层面的反例证据以主控复核
《因子证据可靠性v1：主控复核与限定返修》§9.1–9.3 及
raw/factor-evidence-controller-review-2026-09-16/review-repair.py 的
独立反例为准。本台账不回退代码重造红日志；§6 所述 32 次测试原始日志
不可恢复的限制继续保留，不补造。§2 的修后绿（72 定向 / 116 回归
passed）是修后状态证据，与本节过程证据限制分开陈述，互不替代。
