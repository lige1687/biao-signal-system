# LEI 协调初始化阶段证据

2026-10-03（Asia/Shanghai）。负责人：Codex 会话 01a10051-4db1-7490-b40f-c13243767fc6，本机独立 worktree。
跨任务当前状态唯一入口：[lei-coordination-bootstrap](https://github.com/lige1687/biao-signal-system/blob/coordination/lei/docs/coordination/tasks/lei-coordination-bootstrap.md)。本文件只记录本分支阶段证据。

目标：建立协调入口，增补工作分支项目规则，兼容目录检查。基础提交：91a93ad2b881fbeed1ee15ae03d4fc3bbff08342。工作分支 codex/lei-coordination-setup-20261003。
已完成：AGENTS.md 追加协作段落，旧内容逐字保留；检查器仅新增 COORDINATION.md、docs/coordination、worktree .git 三项白名单。无策略、规则计算、研究或生产变更。
失败证据：旧检查器在协调 worktree 报上述 3 项；本次修复针对该兼容问题，不放宽其他路径。
验证：检查原 AGENTS.md 为当前文件完整前缀；目录检查分别在工作 worktree 和协调 worktree 上执行（协调树使用本分支更新后的检查器）。结果随协调状态登记；提交与推送最终状态以该入口为准。
后续：推送本分支、读回准确提交、更新协调状态。原任务未能从本聊天确认，等待用户给出名称或进度路径；没有移交或宣布其完成。研究预算 0，无数据产物。


## 2026-10-07 接续（仅本地，远端不可复现）

负责人／唯一协调Git写者：01a10051-4db1-7490-b40f-c13243767fc6；调度中控仍01a116c7-3700-7062-a6c6-53af00ef60a0。目标是八目标／四线可查、同步SHA可核，并区分文字规则和工具能力。成果分支codex/lei-coordination-refresh-20261007，基础34b6435a915b7adeff8f8c04484fb75295e908c1；本轮未推。

通过：remote正确，fetch读到ccc290e9b1c13286252c77ff281fbada8c1206c1；原16任务只读，未修改他人记录；独立工作区完整保留主区脏修改。当前主区AGENTS/CLAUDE是一般复用规则，没有coordination专用远端检查；原生factor_lab没有跨AI查重硬检查。只有旧成果分支AGENTS有协作文字。新增本分支AGENTS SHA记录说明和scripts/sync/check_coordination.py手动只读工具；8项负例／范围测试通过，目录检查通过。它不接运行框架、不装hook、不授权限，所有旧Markdown列未程序检查；不能声称所有AI已遵守。

失败：GitHub SSH正常读取，但4次安全提交写入Internal Server Error。已核远端没有本次提交；分别检查并发增量、线性重建、完整对象传输，仍同错。HTTPS现有Git/API凭据不可用且无进展，结束本次HTTPS进程，没有改网络、认证或权限。准确request-id和待推历史见协调目录新中控摘要。fetch成功不叫同步；等待普通写入恢复或现有授权可用写通道。

本地协调目录：.codex/worktrees/lei-coordination。开工待推commit c02c39bb10d6d0cc9755690a46b07eca210cfd99；旧合并待推89de34a43c58000c9a37511da69a69353948c213保留在codex/lei-coordination-pending-20261007。后续本地修改另提交，不伪装旧SHA代表最新。COORDINATION.md、本任务和中控摘要仅本地，工作分支工具／测试也未推。0行情、0研究标签、0拟合，不重跑已封存研究，不写仓外OKR。

最小恢复：读本地待推任务与本分支脚本→fetch远端、核新增范围和唯一写者→只整合本任务准确文件→普通推→fetch比完整SHA及文件→再称同步；涉及冲突共享修改继续暂停。其他独立研究沿原授权执行，本轮没有替原负责人结束或转移任务。


### 本轮实际在线反例回执

远端尚未包含本轮声明，工具实际拒绝此查询；在线读取成功不等于已登记。

```json
{
  "exit_code": 2,
  "checked_at": "2026-10-07T23:16:52+08:00",
  "online_verified": true,
  "work_clearance": false,
  "checked_coordination_sha": "ccc290e9b1c13286252c77ff281fbada8c1206c1",
  "rules_present": true,
  "mode": "online_declarations_only",
  "declared_checks_passed": false,
  "errors": [
    "unregistered task_id: native-risk-d-mae; human review required"
  ],
  "legacy_records_require_human_review": [
    "docs/coordination/tasks/classic-factor-research.md",
    "docs/coordination/tasks/dot-formula-time-validation.md",
    "docs/coordination/tasks/dot-pro-increment-review.md",
    "docs/coordination/tasks/dot-pro-source-qualification.md",
    "docs/coordination/tasks/dot-pro-strategy-definition.md",
    "docs/coordination/tasks/dot-trade-state-accounting.md",
    "docs/coordination/tasks/douyin-vike-increment.md",
    "docs/coordination/tasks/external-quant-resources.md",
    "docs/coordination/tasks/investor-observation-map.md",
    "docs/coordination/tasks/lei-coordination-bootstrap.md",
    "docs/coordination/tasks/lei-technical-reader-research.md",
    "docs/coordination/tasks/market-observation.md",
    "docs/coordination/tasks/remote-core-review.md",
    "docs/coordination/tasks/risk-shape-information.md",
    "docs/coordination/tasks/sentiment-factor-research.md",
    "docs/coordination/tasks/technical-factor-sequence.md"
  ],
  "declared_task_ids": [],
  "scope": "explicit declarations only; no lock, authorization, or legacy clearance"
}
```


### 安全写通道恢复的实际证据

独立成果分支首次普通push成功，fetch完整SHA为4a1bab7301c30b5e3d716a660ddc4df0617460d3，四个成果文件逐字读回相同。此前“本轮未推”是失败阶段历史，此处替代当前成果推送状态；协调分支仍待再次核验。没有因网络恢复删除旧失败记录，也不称所有AI已采用新规则。下一步协调文件普通推后在线查询与读回。


### 协调分支恢复与实际在线查询

规则／两份任务记录已普通推到coordination/lei，fetch逐字读回及其他负责人文件逐字不变通过，提交dbb9603223e9708d3afac63da09d8fe04da4597d。登记路径查询退出0；请求未登记共享scripts/run_factor_lab.py退出2。均从最新远端读取，legacy人工检查15份，work_clearance仍false，不授开工权限。此前SSH失败保留历史，当前网络阻塞已解除。

```json
{
  "registered": {
    "checked_at": "2026-10-07T23:20:36+08:00",
    "online_verified": true,
    "work_clearance": false,
    "checked_coordination_sha": "dbb9603223e9708d3afac63da09d8fe04da4597d",
    "rules_present": true,
    "mode": "online_declarations_only",
    "declared_checks_passed": true,
    "errors": [],
    "legacy_records_require_human_review": [
      "docs/coordination/tasks/classic-factor-research.md",
      "docs/coordination/tasks/dot-formula-time-validation.md",
      "docs/coordination/tasks/dot-pro-increment-review.md",
      "docs/coordination/tasks/dot-pro-source-qualification.md",
      "docs/coordination/tasks/dot-pro-strategy-definition.md",
      "docs/coordination/tasks/dot-trade-state-accounting.md",
      "docs/coordination/tasks/douyin-vike-increment.md",
      "docs/coordination/tasks/external-quant-resources.md",
      "docs/coordination/tasks/investor-observation-map.md",
      "docs/coordination/tasks/lei-technical-reader-research.md",
      "docs/coordination/tasks/market-observation.md",
      "docs/coordination/tasks/remote-core-review.md",
      "docs/coordination/tasks/risk-shape-information.md",
      "docs/coordination/tasks/sentiment-factor-research.md",
      "docs/coordination/tasks/technical-factor-sequence.md"
    ],
    "declared_task_ids": [
      "d-mae-independent-review",
      "factor-fusion-risk-exit",
      "lei-coordination-bootstrap",
      "native-risk-d-mae",
      "native-workflow-integration",
      "research-evidence-catalog",
      "stock-data-qualification"
    ],
    "scope": "explicit declarations only; no lock, authorization, or legacy clearance"
  },
  "unregistered_shared_path": {
    "checked_at": "2026-10-07T23:20:42+08:00",
    "online_verified": true,
    "work_clearance": false,
    "checked_coordination_sha": "dbb9603223e9708d3afac63da09d8fe04da4597d",
    "rules_present": true,
    "mode": "online_declarations_only",
    "declared_checks_passed": false,
    "errors": [
      "native-risk-d-mae: write not registered: scripts/run_factor_lab.py"
    ],
    "legacy_records_require_human_review": [
      "docs/coordination/tasks/classic-factor-research.md",
      "docs/coordination/tasks/dot-formula-time-validation.md",
      "docs/coordination/tasks/dot-pro-increment-review.md",
      "docs/coordination/tasks/dot-pro-source-qualification.md",
      "docs/coordination/tasks/dot-pro-strategy-definition.md",
      "docs/coordination/tasks/dot-trade-state-accounting.md",
      "docs/coordination/tasks/douyin-vike-increment.md",
      "docs/coordination/tasks/external-quant-resources.md",
      "docs/coordination/tasks/investor-observation-map.md",
      "docs/coordination/tasks/lei-technical-reader-research.md",
      "docs/coordination/tasks/market-observation.md",
      "docs/coordination/tasks/remote-core-review.md",
      "docs/coordination/tasks/risk-shape-information.md",
      "docs/coordination/tasks/sentiment-factor-research.md",
      "docs/coordination/tasks/technical-factor-sequence.md"
    ],
    "declared_task_ids": [
      "d-mae-independent-review",
      "factor-fusion-risk-exit",
      "lei-coordination-bootstrap",
      "native-risk-d-mae",
      "native-workflow-integration",
      "research-evidence-catalog",
      "stock-data-qualification"
    ],
    "scope": "explicit declarations only; no lock, authorization, or legacy clearance"
  }
}
```
