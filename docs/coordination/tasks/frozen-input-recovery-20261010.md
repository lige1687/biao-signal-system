# 原八目标8：冻结来源的备份与恢复核验

- task-id: frozen-input-recovery-20261010；owner/session: 01a123fc-553b-7b81-9952-36e1acb11dcc；status: active / read_only_inventory；updated_at: 2026-10-10T12:09:17.269715+08:00。
- checked_coordination_sha: c14e356c228de0472adfa2edfe3627d9f4836bc2；checked_at: 2026-10-10T12:09:17.269715+08:00；实际已读任务见下方结构区块。
- 系统原目标：okr-57eb3f28e526；实时API version=1、planned、authorization.granted=false。本轮只读核验及仓内小证据准备；不自行把系统授权改为true。用户本轮粘贴原八目标最终交接，按其接续顺序先核目标8。新建此唯一接续任务不接管旧中控、A/B/C任务。
- 问题/验收：按A manifest逐项定位25原来源；核本机字节/大小/指纹；复用已存在且可核的独立副本；另机恢复单独验收；写小回执，不将本机存在当备份完成。
- 输入基线：A29337ec9e6560171c459019834638ce2c6993ef9；manifest9f1c326b46e7afc22d2ad6454e9f754e64540442e120412326ce270a50799baf。原25只读，47材料中其余22仅上下文导航不扩大备份范围。
- 分支/写入：codex/frozen-input-recovery-20261010，base d2c142bc460e047b69a003107f1d4958f0695dcb；只写自己raw小回执和work-progress。共享API该原目标的本轮note/owner由root唯一写，保护原完成标准/历史/授权；不改registry/INDEX、源文件、配置或其他负责人文件。成果尚未发布。
- 查重/冲突决定：最新旧中控completed/scope_released；A冻结只读；B自己的交付及C已归档无本题执行；mac存储和daily资源范围只有旧清理/媒体/模型。本题无同目标现有owner，其他任务记录不因过时即视为放弃。范围不同，root唯一本任务写者，Sol只读证据审阅不写文件、不复算全链。
- 范围/预算：月度4/4与旧2/2耗尽并保持封存；市场实验、账户运行、重放、下载、调参、新chat/自动化/Goal=0。仅文件内容核对、既有Git查证和小记录，不借用科研预算。
- 边界/停止：仓外新备份需按用户AGENTS中仓外修改确认规则核具体许可；目标设备访问未明确，不自动远程改动。先完成不依赖它们的仓内核验与恢复方案，缺少权限/设备时写清待办，不虚称完成。
- 当前检查：本机25原件大小/指纹只读核同；独立副本、远端准确定位正在核；异机未运行；归置、成果发布尚未运行。
- 下一动作：保存逐项准确副本/缺口回执，准备只补缺且不覆盖的恢复计划；未获具体仓外许可前不复制资料。

<!-- lei-coordination-json:start -->
{
  "task_id": "frozen-input-recovery-20261010",
  "owner": "01a123fc-553b-7b81-9952-36e1acb11dcc",
  "status": "active",
  "stage": "read_only_inventory",
  "checked_coordination_sha": "c14e356c228de0472adfa2edfe3627d9f4836bc2",
  "checked_at": "2026-10-10T12:09:17.269715+08:00",
  "read_task_ids": [
    "research-dispatch-controller",
    "leisignal-risk-input-20261009",
    "leisignal-risk-run-20261009",
    "leisignal-risk-review-20261009",
    "mac-local-storage-cleanup",
    "daily-trading-system-audit"
  ],
  "work_branch": "codex/frozen-input-recovery-20261010",
  "base_commit": "d2c142bc460e047b69a003107f1d4958f0695dcb",
  "write_paths": [
    "docs/experiments/raw/frozen-input-recovery-2026-10-10/",
    "docs/ops/work-progress/frozen-input-recovery-20261010.md"
  ],
  "external_write_paths": [],
  "scope_released": false
}
<!-- lei-coordination-json:end -->
