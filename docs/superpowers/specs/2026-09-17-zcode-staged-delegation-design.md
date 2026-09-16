# ZCode 分阶段执行与独立返修预算设计

日期：2026-09-17

## 1. 目标与已定边界

升级现有个人 Skill `$zcode-delegate`：Codex 在首次派发前根据完整任务的依赖关系与交付物自行决定正常执行阶段数量；正常进入下一阶段不占返修额度，整个 job 最多额外返修三次。

这项改造不改变以下既有边界：Codex 仍是目标所有者与最终验收者；ZCode 只执行冻结任务；每次回调后必须独立检查实际文件和新鲜测试；重大方向变化、策略定义、高风险操作和扩大范围仍由用户决定。

已有 protocol v1 job 保持原文件和原语义，可以继续查看或验收，但不迁移、不重写。新 job 使用 protocol v2。

## 2. 为什么分开“阶段”和“返修”

旧协议把每次 ZCode 调用都叫 round，并把三次调用同时当成任务进度和失败修正。这会造成两个问题：一个本来需要三段正常实施的任务没有返修余量；一个第一段失败的任务又可能被误报为已经推进到第二阶段。

新版使用两个独立概念：

- `stage`：预先计划的正常进度，例如实现基础能力、完成集成、补齐验收与文档。
- `repair`：Codex 复核当前阶段不通过后，要求 ZCode 在同一阶段纠正明确问题。

阶段数量没有协议硬上限，由 Codex 在派发前决定；返修预算固定为整个 job 最多三次，不是每个阶段三次。为了控制 Token 和调度成本，阶段必须有独立交付价值，不能按单个文件、命令或机械步骤拆分。

## 3. 阶段计划

目标合同新增 `stages`：

```json
{
  "stages": [
    {
      "id": "S1",
      "title": "实现可验证的核心改动",
      "goal_ids": ["G1", "G2"],
      "deliverables": ["具体文件或行为"],
      "acceptance": ["本阶段可独立检查的证据"],
      "depends_on": []
    }
  ]
}
```

所有 G 目标必须至少被一个阶段覆盖；依赖只能指向更早阶段；阶段 ID 连续且不可重复。合同与阶段计划共同计算指纹，派发后不可静默修改。若新事实要求改变目标、交付物或方向，暂停并与用户重新对齐；若只是当前阶段实现不合格，使用返修。

Codex 拆分时遵循：

1. 有真实依赖或不同验收证据时才拆阶段。
2. 相互独立且能一次交付的工作尽量合并。
3. 每个阶段结束都能回答“完成了什么、怎么验证、下一阶段依赖什么”。
4. 小任务只用一个阶段，不为表现流程完整而增加调用。

## 4. 状态与计数

protocol v2 的 `state.json` 保存：

- `stage_index`、`stage_count`、`current_stage_id`；
- `execution_seq`：每次实际调用 ZCode 都递增，用于文件名和回调去重；
- `current_attempt`：`initial` 或 `repair`；
- `repair_count`、`repair_budget=3`；
- 原 Codex task、工作区、绑定 ZCode session 和现有控制权转交记录。

正常阶段通过后，由 Codex 写入 `stage-S-review.json`，其中逐项记录验收证据。只有 `verified=true` 才能执行 `prepare-next-stage`。该命令增加 `stage_index` 和 `execution_seq`，不改变 `repair_count`。

当前阶段复核失败时，Codex 写反馈并执行 `prepare-repair`。准备提示本身不消耗预算；只有返修调用真正进入 `dispatched` 时才增加 `repair_count`。配置检查在模型启动前失败不消耗预算。返修保持当前 stage，增加 `execution_seq`，并继续绑定同一个 ZCode session。

返修三次耗尽后不能再调用 ZCode 修改该 job，但 Codex 仍可读取、测试并报告未完成证据。全部阶段均验证且所有 G 目标都有独立证据时，才允许 `accept`。

## 5. 命令与文件

新增或调整命令：

```text
jobctl create
jobctl record-stage-review --job ... --report-file ...
jobctl prepare-next-stage --job ...
jobctl prepare-repair --job ... --feedback-file ...
jobctl transfer-control ...
jobctl accept ...
```

执行文件统一按实际调用序号命名：

```text
prompt-execution-1.md
cli-execution-1-result.json
callback-execution-1.json
stage-S1-review.json
```

完成标记包含全部路由字段：

```text
ZCODE_DELEGATE_DONE job_id=<uuid> nonce=<hex> execution=<n> stage=<S-id> attempt=<initial|repair> status=<completed|needs_input|failed>
```

Hook 必须同时验证 job、nonce、execution、stage、attempt 和绑定 session。回调仍只能从本地 state 读取 Codex 目标，不能接受模型指定的 thread。控制权只能在 `callback_received` 或 `stage_verified` 检查点通过现有 `transfer-control` 显式转交。

## 6. 用户检查点与自动继续

默认每个大阶段结束后：

1. 原 Codex Agent 独立检查差异、产物与测试。
2. 向用户说明当前阶段通过或未通过、返修已用次数、偏离风险与下一步。
3. 用户确认后才进入下一阶段。

用户明确要求无人值守时，Codex 可以自动推进预先冻结且没有方向取舍的阶段，并自动处理纯机械返修。目标歧义、方案取舍、范围扩张、策略含义变化、权限或高风险操作始终暂停。Codex 内部读取和测试不算阶段，也不消耗返修。

## 7. Token 与模型使用

- 派发前一次性冻结完整目标和阶段计划，不把聊天历史复制给 ZCode。
- 阶段应少而完整；小修改由 Codex 直接完成。
- 同一 job 的后续阶段与返修恢复精确绑定的 ZCode session，不使用最近会话快捷方式。
- ZCode 工作时 Codex 不轮询；Stop Hook 唤醒原主控 Agent。
- 回调只带短摘要与本地文件路径，大输出留在 job 目录。
- 正常阶段数由任务决定，但 Codex 必须在首轮前说明拆分理由，避免无意义地消耗模型调用。

## 8. 兼容与失败处理

- v1 状态仍由旧回调格式识别；v2 使用新字段。测试必须覆盖两者，直到所有活跃 v1 job 结束。
- 已 `accepted`、`cancelled` 或 `failed` 的 job 不允许推进、返修或转移控制权。
- callback 缺失时检查 CLI 结果、session、hook 日志与投递锁，不盲目重发。
- session、工作区或合同指纹不匹配时停止。
- ZCode 自报 `completed` 只表示交付待审，不能自动产生 `stage_verified`。
- 因方向变化需要重做阶段计划时，结束当前 job 并创建新合同，不在旧审计记录上改写历史。

## 9. 测试与验收

自动测试至少证明：

1. 单阶段、多阶段合同均可创建，非法依赖或未覆盖目标被拒绝。
2. 通过阶段后正常推进不增加 `repair_count`。
3. 未通过阶段不能正常推进；准备返修增加一次全局计数并保持 stage。
4. 三次返修后拒绝第四次，但正常阶段数量不受这个计数替代。
5. 后续阶段与返修均恢复同一 ZCode session。
6. v2 Hook 拒绝错误 execution、stage、attempt、nonce 或 session，并去重重复 Stop。
7. v1 已有 job 仍能读取状态和完成既有验收，不被迁移。
8. 控制权转交后，未来回调进入拥有完整任务上下文的原主控 Agent。
9. 只有全部阶段与目标都有 Codex 独立证据时才可 `accept`。
10. Skill 结构校验和完整自动测试通过。

完成自动测试后，在 `/tmp` 创建一个两阶段任务：第一阶段写固定文件，第二阶段读取并补充固定内容。验证两次正常执行的 `repair_count` 仍为零，再用假执行端验证一次返修计数；不为测量额度重复调用真实模型。

## 10. 不在本次范围

- Ark 与 ZCode 共用状态或自动互相讨论；
- 网页工作台、常驻服务、消息队列或并行修改同一工作区；
- 自动部署、合并、提交、交易或删除重要资料；
- 无限制返修或按每阶段重置返修预算；
- 根据模型自述、文件数量或字数自动验收；
- 改写已完成 job 的历史记录。
