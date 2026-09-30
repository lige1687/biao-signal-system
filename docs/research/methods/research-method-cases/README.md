# 研究方法案例台账（research-method-cases）

版本：v1.1.0（2026-09-19 M2 闭环升级）。上游合同：
`docs/research/proposals/factor-lib-selfevolution-2026-09-19/self-evolution-restricted-contract.md`（M1）；
`docs/research/proposals/factor-next-phase-4dir-2026-09-19/self-evolution-m2-contract.md`（M2，本次）。

## 这是什么（大白话）

这是一个"研究方法经验账本"：每次我们发现问题、改了研究流程的做法、
或者拒绝了一个改法，都记一条，并且必须同时留下"旧做法结果、新做法结果、
差异怎么解释"三样，不许只展示新做法。它的定位是**可审计的研究流程改进
记录**，不是"系统会自我进化"——任何方法变化都要人批准后才能用。

## 目录结构

- `schema.json` — 案例字段与校验规则（权威定义）。
- `cases/rmc-*.json` — 案例条目，文件名 = `id`。
- `TEMPLATE-method-change-case.json` — 新案例模板 v2（Before/After 双轨必填
  ＋失败模式标签＋审查轨迹）。

新增案例：复制模板 → 填全必填字段 → 存入 `cases/` → 用
`python3 docs/experiments/raw/factor-c1-2026-09-19/check_method_cases_v2.py`
校验（M2 权威校验器：M1 全部检查＋旧结果硬性检查＋五分类标签＋状态机审查轨迹
＋rejected 比例统计）。M1 的 check_method_cases.py 留在原处作历史快照，不再用于
新增案例（它不认识 failure_mode 字段）。

## 字段速览

`problem`（什么问题）/ `why_changed`（为什么改）/ `old_method`（旧做法）/
`new_method`（新做法或被拒候选）/ `scope`（适用范围）/ `rule_changed`
（是否改了交易规则或尺子）/ `evaluator_changed`（是否改了评价标准）/
`references`（仓库报告路径，无出处不入账）/ `before_after`
（旧结果/新结果/差异解释，三段缺一不可）/ `status`（方法状态）。

## status 语义（只有这四个值，不造第二套词汇）

| status | 含义 |
|---|---|
| proposed | 方法变化候选，等人工批准；批准前不得使用 |
| approved | 经人工（主控/GPT/用户）批准采纳的方法改进 |
| rejected | 被拒绝或暂缓的候选——反例，与正例同等重要 |
| observed | 已发生并留档的事实记录，未构成方法变更决策 |

**对象状态另说**：如需描述某个定义/因子对象本身的状态，引用因子库合同
F1 四态（exists / verified / research_ready / production_approved），写在可选
字段 `object_states`，只描述对象，不得当作方法状态使用。

## 审批状态机（M2，proposed→reviewed→approved/rejected→observed）

status 仍然只有 M1 的四个值，**不造新状态词**；"reviewed" 是审查轨迹里的
中间事件，不是第五个 status。转移规则：

```
proposed ──(人工 review_log 记 reviewed)──> 人工裁决
    ├─ approved   （review_log 追加 approved 记录，actor 必须是人）
    ├─ rejected   （review_log 追加 rejected 记录；反例入库，与正例同权重）
已发生事实 ──> observed（留档，不构成方法变更决策）
```

- `review_log`（可选字段，proposed 案例必填）记录每次人工审查：
  `{date, actor, decision: reviewed|approved|rejected|observed, note}`。
- **零自动采纳路径**：proposed→approved 只能由人工 actor 写入 review_log；
  校验器会拒绝 actor 含 auto/脚本字样的记录；台账文件与所有校验/统计脚本
  均无任何写 status 的代码路径。

## 失败模式五分类（M2 标签体系，互斥单选）

每条案例必填 `failure_mode: {category, reason}`（reason 一句话说明为什么归
这一类而不是相邻类）：

| category | 大白话定义 |
|---|---|
| input 输入问题 | 数据/字段来源未核验、坏记录被当真用掉（"身份证自报没人查"） |
| time 时间问题 | "当时能不能知道"缺失：可知性、时点对齐、未来信息缺漏 |
| sample 样本问题 | 研究对象范围/覆盖/代表性缺陷（名单不对、覆盖不足以支撑结论） |
| engineering 工程问题 | 代码/测试/流程实现缺陷（测试没在看、身份未绑定、同名冲突） |
| interpretation 解释问题 | 转写失真、判断过满、结论超出证据（把判断写成事实） |

打标口径：rejection_case 打候选失败的原因；observation_case 打暴露的缺陷
类型；method_change_case 打被改进做法根治的缺陷类型。五分类仅用于人工复盘
归纳，不参与任何自动判定或过滤。

## 四条硬边界（违反任何一条，案例不得入账或台账停线复审）

1. **固定尺子**：trading-spec、评估标准、验收协议不可变。`rule_changed=true`
   或 `evaluator_changed=true` 的"改进"不属于方法改进，是越界，不入账。
2. **Before/After 双轨**：缺旧方法结果的记录不合格，不允许只展示新方法。
3. **失败案例必须入库**：被拒绝、被暂停、判负的候选与成功案例同权重
   入账，防止台账变成"成功经验收集器"。
4. **不自动部署**：candidate method → 人工 review → adopt；禁止
   candidate → auto use。台账本身没有任何执行权限。

## 当前案例一览（11 条，2 条 rejected；五分类=input 3 / engineering 4 / time 1 / sample 0 / interpretation 3）

| id | 主题 | kind | status | 失败分类 |
|---|---|---|---|---|
| rmc-2026-09-19-s2s3-module-rename | S2/S3 同名测试产物改名（首条 method_change_case） | method_change_case | approved | engineering |
| rmc-2026-09-10-rdf-root-entry | 研究数据基础：根治"调用方口头声明字段" | method_change_case | approved | input |
| rmc-2026-09-17-factor-method-reuse-pause | 外部因子方法复用试点暂缓 | rejection_case | rejected | interpretation |
| rmc-2026-09-09-breadth-price50-reject | 固定50日判负、停止围绕它优化 | rejection_case | rejected | interpretation |
| rmc-2026-09-19-s3-target-block | target 用途被资格墙阻塞（阻塞报告为合格交付） | observation_case | observed | time |
| rmc-2026-09-10-roadmap-v01-revision | 路线图 v0.1 过满判断逐条纠正 | observation_case | observed | interpretation |
| rmc-2026-09-13-momentum-protocol-binding | 协议身份未与实际算法绑定 | observation_case | observed | engineering |
| rmc-2026-09-13-momentum-bad-actions | 已发现错误的行动记录仍被消费于重建 | observation_case | observed | input |
| rmc-2026-09-13-rdf-listing-evidence | 上市日期自洽不能代替来源核验 | observation_case | observed | input |
| rmc-2026-09-13-rdf-halt-consumption | 直接价格入口消费未核验停牌记录 | observation_case | observed | engineering |
| rmc-2026-09-10-rdf-coverage-illusion | 四类漏放与覆盖假象自查 | observation_case | observed | engineering |

维护约定：新案例入账后同步本表。

## M2 三防线（可执行化）

1. **成功偏置 → rejected 比例统计**：
   `check_method_cases_v2.py` 每次运行都输出 status 分布与 rejected 比例
   （当前 2/11 = 18.2%），并保留"至少 1 条 rejected"的反例配额。
2. **偷改尺子 → 指纹比对**：
   `docs/experiments/raw/factor-c1-2026-09-19/check_ruler_changes.py` 对
   trading-spec、规则账本、研究原则/定义/模板/登记表、执行契约共 7 个尺子
   文件做 sha256 基线比对（`--snapshot` 建基线，默认比对、有变化即失败）。
3. **历史结果驱动修改 → before/after 旧结果硬性检查**：
   `check_method_cases_v2.py` 拒绝 old_result 为空的案例；old_result=「无」
   仅在 old_method 明确写「无既有方法」时允许（M1 校验只查非空，M2 补上
   口头"无"的对应关系核对）。

> 注（2026-09-19，GPT 评审建议）：当前校验器（check_method_cases.py）为
> 项目内审计辅助，不等同于通用 schema 标准验证器（未用 jsonschema 库执行
> schema.json 本体）。
