# 第十批真实历史驱动脚本独立静态复核

## 一句话结论（大白话）

脚本按事先规定的日期检查整段旧事件，先确保新旧两次计算使用完全相同的历史价格，再使用现行颜色规则生成输入。四项核心要求与协议一致；没有为了挑结果调整检查日期。此结论是代码审查，不代表实际运行已经通过。

## 审查范围与结论

只读 `protocol.md`、补充01、`diagnose_history.py` 及冻结 `price_basis.py`。没有运行真实计算，没有读取 `history-diagnostic` 的事件、差异、摘要或进度来选择检查日期，没有修改运行脚本及已封存 C/D 子目录。

| 要求 | 静态证据 | 结论 |
|---|---|---|
| 同一次公司行动后的价格单位一致 | 按已生效日分段；`raw_asof` 用截至指定日的报价和已公告行动，PriceBasis 还要求行动已生效。段末与截断日重新生成价格后，`assert_frame_equal(raw.loc[:d], prefix_raw, check_exact=True)` 对每行每列做完全一致核验。预热期仍保留，行动前后分属不同段。 | 符合；不跨行动变化直接比较价格 |
| 使用原有颜色输入 | `events_for` 调用 `classify_colors(compute_features(raw))`，随后检查 `signal_color` 存在。调用来自第十副本的原色规则，不在驱动脚本另写颜色公式。 | 符合补充01，避免缺颜色导致 A/C 静默零事件 |
| 检查日期提前固定 | 先由四份既有报价的每年首末日、行动前最后报价日、行动日或其后第一报价日生成 `chosen`，按既定行动段筛选；在任何 `events_for` 调用前写 `run-lock.json` 的完整计划与来源指纹。共同截止 2026-06-30。 | 符合；日期不依赖信号或收益 |
| 比较整段已知事件 | 每个截断日用 `select(..., lo, d)` 包括段起点至当日所有 `available_date` 在内的事件；逐模块比较删除、新增，以及共同 ID 的完整事件字典变化，保留 before/after。 | 符合“不是只看最后一天”；但见下方身份唯一性边界 |

A/C/D 模块没有按确认类型过滤后才检查；观察、失败和各确认版本均留在事件列表。普通事件差异不会中止后续预定日期与模块；没有调用收益计算。实际数据单位不一致、来源指纹改变或异常输入时脚本会停止，这属于拒绝错误输入，不是挑选保留较好的日期。

## 完整性边界与后续验收

1. `select()` 使用 `{event_id: event}`。同次检测若产生重复 ID，后一个会覆盖前一个，而脚本未先断言唯一。因此“全部事件内容已比对”依赖 ID 唯一。此次未发现重复的实际证据，也没有读取事件结果；建议在当前固定计划结果验收时补查唯一性。已有 `raw-events.json.gz` 也来自这个去重后的集合，单靠该文件不能反推出被覆盖记录；不要把去重后的条数当唯一性证明。这个边界不要求重新选择日期。
2. 脚本假设每个基金在 2015—2026 各年都有报价，否则 `ys[0]` 会报错。PriceBasis 会拒绝重复或乱序日期。对本次锁定输入的最终运行成功与否，仍应查完成记录，不能仅凭本静态审查声称成功。
3. 输入完全一致通过后，事件比较覆盖原始序列字段；非有限数统一为 JSON null。报告应沿用协议的“固定历史检查日期诊断”，不能升级成每天、所有可能输入都不会改写历史的证明。
4. 结果明细在全部预定段结束后写盘，途中只有进度；运行中断不能当完整诊断。最终应核对完整计划、所有检查数、完成标记及末尾来源校验均存在。

## 追加：三个检测器的事件身份是否会重复

只读核查当前第十冻结包 `first_ma_pullback.py`、`two_b_reversal.py`、`module_d_false_breakout.py`、`features/pivots.py` 和 `domain/canonical.py`，没有依据真实输出改变范围。三个检测器都没有在返回前主动去重；A 直接返回列表，C/D 只排序。

**在本驱动已验证的“报价日期严格递增、一天一行”，并保持当前固定参数的条件下，可以从控制流程证明一次调用内的事件身份原始组合键不重复：**

| 模块 | 身份组合与互斥理由 |
|---|---|
| A | 身份含标的、规则版本、可用日期及 `episode日期:均线周期:事件类型:入场版本/触碰日期`。每天每个周期只迭代一次；周期字典的键唯一。趋势重置失败后直接进入下一天；结构失败后直接进入下一周期；离开触碰区失败只在尚未确认时发生。触碰、失败、早期确认、共同确认身份不同，各确认又由已发送状态限制一次。不存在同一天同一周期两次发送相同组合键的路径。 |
| C | 身份含 `L1确认日期:sub_rule` 与可用日期。固定右侧确认根数下，每个低点位置对应不同确认日期，`swing_lows` 每个位置最多返回一个低点；每个 L1 只扫描一次。三种确认分别由 `v_done` 限制一次；任一失败立即返回。因此同一组合键不会重复。此前发现新旧 L1 重复代表同次市场动作，是**不同 L1 身份的业务重复**，不会被驱动的字典吞掉。 |
| D | 身份含波谷确认日期及可用日期，虽不含 confirmed/failed，但单个波谷第一次确认或失败都立即停止，最多发一条事件。`_zone_intervals` 生成互不重叠的半开区间：结束后清空起点，下一起点只可能在更后方；同一波谷确认日最多落入一个区间，故不会跨区间被扫描两次。不同波谷确认日期唯一，身份组合键不同。新旧波谷业务重复也会被保留。 |

`make_event_id` 把组合键做 SHA-256 后截取前 24 个十六进制字符。这不是数学上单射的编码，因此上面的证明针对**逻辑身份组合键**，不能代替所有实际字符串 ID 的运行时逐条唯一性断言；理论摘要碰撞也不能靠静态代码排除。当前代码未见会主动制造相同逻辑身份的路径，故字典覆盖是未显式验收的完整性边界，不应升级为已经证实的历史结果丢失。

`raw-events.json.gz` 已由 `select()` 构造，检查它没有重复 ID 只能确认落盘集合本身，不能反推未保存的原始完整列表或各截断列表都未重复。本次不声称完成这些列表的实际唯一性核验。

## 审阅时源文件指纹

- `docs/experiments/raw/research-tenth-2026-09-08/protocol.md`：`23e325c3a324d8944a4731d60da6b7dae2429abbf24920c69f9f4d7f4ba1ff5c`
- `docs/experiments/raw/research-tenth-2026-09-08/protocol-addendum-01.md`：`082d90736270ad371a1039153a85aaf382a764df33abc765e260a63dbcb9e4a2`
- `docs/experiments/raw/research-tenth-2026-09-08/diagnose_history.py`：`9978f0ae19599e29e1fda83183bc336b29230e393e3a3a10e1bd66e9d5b5df8b`
- `docs/experiments/raw/research-eighth-2026-09-08/product-qualification/price-helper/price_basis.py`：`ba443c4c69c2c42b55cd092ca19a1f552354daf4a2f5acf3be13d77ed64a3b4d`
- `docs/experiments/raw/research-tenth-2026-09-08/research-package/src/lei_signal/rules/first_ma_pullback.py`：`cbad98a136135a936470a1114e95bea656953c42c37637ee4e3f5bedc9153367`
- `docs/experiments/raw/research-tenth-2026-09-08/research-package/src/lei_signal/rules/two_b_reversal.py`：`f545654f5966ee97bd9583ab8245e22e796679c4a6a4f38eb61ece1997b9c307`
- `docs/experiments/raw/research-tenth-2026-09-08/research-package/src/lei_signal/rules/module_d_false_breakout.py`：`ee3f98f37b10cfd21396ac11695c9f56d3fe74a5f58b3fbbcc12fe9a69473937`
- `docs/experiments/raw/research-tenth-2026-09-08/research-package/src/lei_signal/features/pivots.py`：`ce8421c864c76cccaa5259de704001b69e44febf5f8f1eedbdc72ae6848baa90`
- `docs/experiments/raw/research-tenth-2026-09-08/research-package/src/lei_signal/domain/canonical.py`：`3e406f77dfa3f03c7ff4d2fe1989dd117a47e448d137d5ccce76d61864ee06a9`
