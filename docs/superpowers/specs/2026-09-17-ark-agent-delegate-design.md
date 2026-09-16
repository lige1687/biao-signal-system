# Ark Agent 委派与 Codex 回调设计

日期：2026-09-17

## 1. 决策与目标

新增独立的个人 Codex Skill：`$ark-agent-delegate`。它让当前 Codex 任务把一个已经对齐、边界明确的完整工作交给 Ark Agent 配置下的 Claude Code，在 Claude 停止时自动唤醒原 Codex 任务，由 Codex 独立复核，再向用户汇报。

这套流程追求四个结果：

1. 用户只需要在 Codex 中说明目标并调用 Skill，不操作 Claude 或 ZCode 图形界面。
2. 外部 Agent 工作期间 Codex 不轮询、不持续生成内容；完成后才由本地 Stop Hook 唤醒。
3. 总目标、验收标准和方向判断始终归当前 Codex 任务所有，外部 Agent 只执行已冻结的任务。
4. 模型与思考强度按任务难度使用，避免每次回调都用高强度 Astra，也避免为了表面便宜频繁切换模型导致上下文缓存失效。

本设计是 2026-09-13 统一委派方案在“Ark Agent 直接执行、自动回调、多阶段复核”方向上的后续决策。用户已明确改变以下旧边界：Ark Agent 允许直接在当前工作区执行、允许真正免确认的最高权限；正常执行阶段由 Codex 根据任务依赖和交付物自行拆分，整个任务最多额外返修三次。因此旧设计中“只读副本、不使用绕过权限参数、只执行一轮”的限制不再适用于这个新 Skill。ZCode 继续使用独立的 `$zcode-delegate`，两者不共用任务状态，但采用相同的阶段与返修语义。

## 2. 用户流程

典型调用：

```text
$ark-agent-delegate
把这个需求推进到可交付状态。先和我对齐目标；每个大阶段结束后给我看结果。
```

流程如下：

1. Codex 与用户对齐总目标、交付物、验收证据和禁止事项。
2. Codex 判断任务是否值得委派。一个本地编辑和一次测试就能完成的小修不派发；相关工作应合并为一个有完整交付价值的大任务，摊薄外部 Agent 的固定上下文成本。
3. Codex生成不可随意改写的目标合同、阶段计划与简短执行说明，创建独立 Ark job。阶段数量没有协议硬上限，但每个阶段必须有独立交付价值，不能把机械步骤拆成许多小调用。
4. 第一阶段启动新的 Claude Code session；不复用最近会话。
5. Codex 当前回合结束。Claude 工作期间不轮询。
6. Claude 最终回答包含带随机 nonce 的完成标记；Stop Hook 验证后把很短的通知排入原 Codex 任务。
7. Codex检查实际文件、代码差异和新鲜测试，不把 Claude 的 `completed` 当作验收。
8. 每个阶段结束，Codex向用户报告目标完成度、证据、偏离风险和下一步。默认等待用户确认后才进入下一阶段。
9. 当前阶段通过就正常前进，不消耗返修额度；复核未通过且问题可在原目标内修正时，才消耗一次返修。整个 job 最多返修三次。全部阶段与目标通过后由 Codex写最终验收记录；返修额度用尽仍未通过则如实报告阻塞。

纯读取、运行既定测试、检查哈希、整理证据等 Codex 内部复核不算新的 Ark 执行，也不需要用户逐项确认。进入预先冻结的下一阶段属于正常执行；要求 Ark 纠正一个未通过的既有阶段才算返修。

## 3. 组件与边界

Skill 根目录：

```text
~/.codex/skills/ark-agent-delegate/
```

任务记录：

```text
~/.codex/ark-agent-delegate/jobs/<job_id>/
```

组件分工：

- `SKILL.md`：规定何时委派、目标对齐、用户复核、权限边界、模型与思考强度规则。
- `jobctl.mjs`：创建任务、冻结合同和阶段计划、推进阶段、记录返修预算、接受或取消任务。
- `dispatch-cli.mjs`：读取 Ark 配置，在新 session 或绑定 session 中调用 Claude Code。
- `claude-stop-hook.mjs`：验证 Stop 事件并使用 `codex queue` 唤醒原任务。
- `install-hook.mjs`：保留 Claude 现有设置并安装幂等 Stop Hook；真实修改前创建备份。
- `ark-agent-delegate.test.mjs`：使用假 Claude、假 Codex 和临时目录覆盖协议、权限参数、会话绑定与回调安全。
- `references/protocol.md`：状态文件、完成标记、失败恢复和诊断步骤。
- `references/task-contract.md`：目标合同和最终验收记录的结构。

第一版不建立常驻服务、网页工作台、消息队列或服务发现中心。状态文件就是审计记录，Stop Hook 就是通知机制。

## 4. 目标合同与任务状态

每个 job 至少保存：

- `state.json`：job、原 Codex thread、工作区、Claude session、当前阶段、总阶段数、全局返修计数、执行序号、回调复核级别和时间戳。
- `contract.json`：mission、G1/G2 等目标、每项目标的可观察证据、允许范围、保护路径、停止条件，以及 S1/S2 等阶段、阶段所覆盖的目标和阶段交付物。
- `request.md`：执行方法、项目约束、可能的测试命令和交付格式。
- `prompt-execution-N.md`：实际发给 Claude 的完整提示，注明当前 stage、attempt 类型和全局 repair 计数。
- `cli-execution-N-result.json`：脱敏后的 Claude JSON 结果、session ID 与用量。
- `callback-execution-N.json`：经过验证的 Stop 事件摘要。
- `stage-S-review.json`：Codex 对该阶段的独立验收；只有 `verified=true` 才能正常进入下一阶段。
- `final-report.json`：Codex逐项目标独立验收证据。

合同创建时记录 SHA-256。推进阶段、准备返修和最终接受时重新核对；合同内容变化时停止任务，不能把返修或推进阶段变成换目标。

阶段计划由 Codex 在首次派发前根据依赖关系确定。优先拆成少量、较大的可验证阶段，例如“实现 → 集成与测试 → 文档与收口”；互不依赖的工作可合并为一个阶段。阶段数量不按文件数、步骤数或预估 Token 机械计算。发现必须改变任务方向或增删冻结目标时，不得在 job 内偷偷重排，先与用户重新对齐。

状态限定为：`prepared`、`dispatched`、`callback_received`、`under_review`、`awaiting_user`、`stage_verified`、`accepted`、`failed`、`cancelled`。`callback_received` 只说明通知到达，不表示当前阶段完成。

## 5. Claude Code 调用

不调用 shell alias `ark-agent+`，因为 alias 会先运行 `ccswitch` 并修改全局 Claude 配置。Skill 直接调用 Claude 二进制，并显式加载：

```text
~/.claude/settings.ark-agent.json
```

第一阶段的关键参数：

```text
claude -p
  --settings ~/.claude/settings.ark-agent.json
  --session-id <预生成 UUID>
  --dangerously-skip-permissions
  --output-format json
  <prompt>
```

后续阶段和返修只能使用 `--resume <已绑定 session UUID>`。禁止 `--continue`、最近会话或 GUI 当前会话。

必须使用 `--dangerously-skip-permissions`。`--allow-dangerously-skip-permissions` 只允许用户选择该模式，并不真正启用免确认，不能满足无人值守要求。

调用时清除可能覆盖 Ark 配置的 Anthropic 模型和端点环境变量，但不打印、复制或写入密钥。provider 设置只从现有 Ark settings 读取。脚本通过参数数组启动进程，不拼接 shell 字符串。

## 6. 回调协议

Claude 最终回答必须以精确标记结束：

```text
ARK_AGENT_DELEGATE_DONE job_id=<uuid> nonce=<32 hex> execution=<n> stage=<S-id> attempt=<initial|repair> status=<completed|needs_input|failed>
```

Stop Hook 只在以下项目全部匹配时接收：

- hook event 是 `Stop`；
- job 存在；
- nonce 与本地状态一致；
- execution、stage 和 attempt 等于本地当前执行记录；
- session ID 等于该 job 绑定的 Claude session；
- 本轮尚未投递。

Hook 原子写 callback，使用投递锁去重，然后执行：

```text
codex queue --thread <原任务> ... --message <短通知>
```

回调正文只包含 job、execution、stage、attempt、报告状态和 callback 路径。完整 Claude 回答保存在本地，不复制进 Codex 对话。回调不能自行选择 Codex 目标；目标 thread 只从创建 job 时的本地状态读取。

普通 Claude 会话、子 Agent 停止或没有完成标记的回答即使触发 Stop Hook，也会立即被忽略。

## 7. 模型与思考强度

### 7.1 基本原则

Codex 控制端默认继承用户当前任务的模型，不在回调时随意切换模型家族。用户当前使用 Astra 时，普通回调仍使用 Astra，但降低该轮思考强度。这样既利用原对话上下文，也减少因切到 Sol 后重新读取长上下文而产生的输入开销。

job 创建时由 Codex根据工作性质写入 `callback_review_effort`：

| 工作性质 | 回调思考强度 |
|---|---|
| 权限失败、认证失败、缺文件、读取状态 | `low` |
| 常规代码实现、差异检查、测试失败分析 | `medium` |
| 策略定义、实验方法、目标偏移、资金或关键安全风险 | `high` |

Hook 默认不传 `-m`，让原任务沿用用户选定模型；只通过本次 `codex queue` 调用传递：

```text
-c 'model_reasoning_effort="low|medium|high"'
```

若用户明确指定 callback model，才使用 `-m`。第一版不自动使用 `xhigh`、`max` 或 `ultra`；这些档位只有用户明确要求，或已经出现两轮无法解决且 Codex先说明升级理由时才使用。

### 7.2 升级条件

以下情况把下一次复核提升到 `high`，不能由低强度回调直接批准：

- 实际改动超出目标合同或保护路径出现变化；
- 测试结果与报告不一致；
- 修改策略规格、规则账本、实验定义、资金或交易时点；
- 涉及密钥、权限、删除、部署或真实交易；
- 两轮返修仍未解决同一问题。

思考强度在派发前确定，避免先用低强度读完整结果、再无条件追加一个高强度回合。只有出现上面的真实升级信号才增加额外回合。

### 7.3 必须实测的 Codex 行为

本机 `codex queue` 支持 `-m` 和 `-c`，当前 Astra 支持 `low` 到 `ultra`。实现验收必须用隔离任务证明 `-c model_reasoning_effort=low` 只影响这次排队回合，不会把用户下一次手动提问永久留在低强度。如果当前 Codex 版本会持久化覆盖，则这一功能不能按原样发布；必须先实现并验证恢复原设置，不能靠假设。

## 8. Token 使用规则

1. 外部 Agent 运行时不轮询。Codex发出任务后结束当前回合，等待 Stop Hook。
2. 不复制聊天历史。任务说明只包含冻结目标、必要路径、项目约束和验收标准。
3. 大输出写入 job 文件，回调只传路径和摘要。
4. 不为一个局部改字、单文件机械修补启动 Ark。相关小工作应合成一个有完整交付价值的任务；无法合并时由当前 Codex直接完成。
5. 正常阶段数量由 Codex 按任务决定；返修在整个 job 内合计最多三次。默认每个阶段由用户复核后再继续。
6. 只运行与改动相称的测试。既定检查通过后，没有新变化或新风险就不重复全套测试。
7. 记录 Claude 返回的 usage；若出现异常固定上下文开销，在最终报告中说明，但不为测量用量反复发探针任务。
8. 不为了“使用更多模型”而切模型。模型切换必须解决能力问题，而不是制造额外上下文读取。

## 9. 用户复核与自动继续

默认 `user_checkpoint_each_stage=true`：

- Codex收到 callback 后先独立验证；
- 给用户一份简洁的阶段报告；
- 用户确认后才允许进入下一阶段或进行需要取舍的返修。

用户可以在创建 job 时明确设置 `unattended_repairs=true`。此时只有不改变目标、接口或策略含义的机械修复可以自动执行，例如格式、明确失败的单元测试、遗漏的固定交付文件。预先冻结且不改变方向的下一阶段仍按用户选择的阶段检查点规则执行；出现目标歧义、方案取舍、范围扩张或高风险操作必须暂停。

Codex内部读取、测试和审查可以连续完成，不因每一个检查动作打断用户。

## 10. 权限与安全边界

最高权限意味着 Claude 不弹确认框，并不扩大任务授权。每份 prompt 都必须重申：

- 只处理合同允许的工作区和文件；
- 不自动部署、合并、提交、交易、删除重要资料或更改策略定义；
- 不读取或输出任务无关凭据；
- 遇到重大歧义、范围扩大或保护路径变化时返回 `needs_input`。

由于 `--dangerously-skip-permissions` 取消了 Claude 的工具审批，路径范围主要依靠合同、Git/哈希基线和事后核查，属于“可检测，不是操作系统级阻止”。Skill 必须诚实说明这一点，不能把事后检查描述成沙箱。

## 11. 失败与恢复

- 配置或认证失败：在启动模型前尽量完成静态检查，记录失败，不消耗返修额度。
- Claude 非零退出或 JSON 无法解析：保存脱敏 stderr，状态置为 `failed`，不伪造 callback。
- 回调缺失：先读 CLI 结果、session、hook 日志和投递锁；不得盲目重发。
- session 不匹配：拒绝回调和返修。
- 重复 Stop：只投递一次。
- 工作区或合同指纹变化：停止任务，向用户说明变化，不自动迁移目标。
- 全局三次返修额度耗尽：输出未完成阶段、目标和证据，不包装为完成；未执行的正常阶段不能冒充返修失败。
- Hook 配置被外部工具覆盖：安装器可幂等修复，修改前备份原文件。

## 12. 测试与验收

### 12.1 不调用模型的自动测试

1. 第一阶段预生成 session，后续阶段和返修只 resume 精确 session。
2. CLI 参数包含 `--dangerously-skip-permissions`，且不把 `--allow-dangerously-skip-permissions` 误当成启用权限。
3. Ark settings 中的凭据不出现在日志、job 或测试输出。
4. 完整 prompt 包含合同指纹、目标、项目约束和完成标记。
5. 假 nonce、错误 execution、错误 stage/attempt、错误 session、普通 Stop 和重复 Stop 都不能唤醒 Codex。
6. 有效 callback 只唤醒登记的 thread，并按 job 复核级别生成正确的 `codex queue -c model_reasoning_effort=...` 参数。
7. Hook 安装保留现有 Claude 配置，重复运行不产生重复项，真实修改前有备份。
8. 合同修改、超过三次全局返修、未验证当前阶段、缺少目标证据时拒绝推进或验收。
9. 正常推进阶段不增加 `repair_count`；只有 `attempt=repair` 成功派发时才增加，启动前配置失败不消耗返修额度。

### 12.2 一次性真实烟雾测试

在 `/tmp` 独立目录启动一个最小 Ark session：创建一个固定内容文件、结束时输出完成标记、由假 Codex 接收 callback。验收真实写入、真实 session 绑定、真实 Stop Hook 和去重。只运行一次，不用真实项目做权限探针。

另建一个隔离 Codex 任务，验证低强度 callback 不永久改变后续手动回合。这个测试不包含项目代码，也不把测试任务留作正式工作入口。

### 12.3 完成条件

- 自动测试全部通过；
- Skill 结构校验通过；
- 真实 Ark 临时目录写入与 callback 通过；
- 不修改全局 `ccswitch` 当前选中 provider；
- 普通 Claude 会话不会误回调；
- 用户可以在 Codex 中只说 `$ark-agent-delegate` 开始完整流程；
- 回调后的 Codex报告包含当前阶段、全局返修用量、逐项目标证据、实际改动、测试、限制和下一步建议。

## 13. 第一版不做

- Ark 与 ZCode 自动互相讨论；
- 网页或桌面工作台；
- 常驻 HTTP 服务、WebSocket、消息总线或服务发现；
- 多 job 自动排队和并行写同一工作区；
- 自动部署、合并、提交、真实交易或删除重要数据；
- 根据字数、文件数或模型自述自动批准结果；
- 无限制自动返修；
- 为了测试 Token 用量反复调用真实模型。
