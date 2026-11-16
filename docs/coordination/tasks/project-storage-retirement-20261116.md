# LeiSignal历史协调副本归档与本机退役

- task-id: project-storage-retirement-20261116；owner: 本用户对话 01a1e41b-e681-70e0-ab99-177ed8708f91/root；status: active；scope_released: false。
- 用户授权：在本会话已列出5个干净历史协调副本、外盘备份和移除后需恢复的影响后，用户确认“那你迁移一下或者删除一下，确定不用了就可以删了”。本轮仅退役下列5个完整备份的协调checkout，不删除研究成果或分支/提交，不接管原研究任务。
- checked_coordination_sha: 48b5786bbb6a30f29a227e449d18486772e1dc05；checked_at: 2026-11-16T19:41:25.177022+08:00。已读COORDINATION 1.1、research-dispatch-controller、mac-local-storage-cleanup、storage-autonomy-and-valuation-review-20261107，以及5个对应研究owner任务（ai-quant-practice-integration-20261101、factor-method-standards-increment-20261103、research-method-practice-20261031、research-utility-review-20261012、strategy-account-bridge-20261020）的当前完成/释放段。
- 冲突决定：只处理无本地改动、无ignored文件、HEAD已在远端coordination/lei祖先链、无活动句柄且未被运行配置引用的协调副本；5个原研究的代码、主raw、预算、状态与未完成项不变。用户本轮明确授权精确副本退役，不凭时间旧推断其他工作树闲置。
- 工作基线：主checkout codex/factor-unit-research-20260915@18e64fa632dba5dbad0e5fcae09b4ccc75f119a9加现有脏区；不切换、不暂存。协调元数据以外盘私有隔离Git index构建单路径提交，不创建新的全量checkout。未推源码，latest source成果不适用（无源码变更）。
- 已完成：固定卷UUID DEBA1C85-6059-3865-B50A-A8EE1F80E4D9验证；5个tar逐文件内容/链接/权限/时间读回、源稳定和完整archive SHA已核；恢复清单/纳秒时间/扩展属性与恢复说明留外盘。总原内容9840259165B，目录统计约9.4GiB，尚未声称实际释放。主web/API HTTP200。
- 唯一写入范围：本协调任务文件、外盘个人资料归档/LeiSignal-项目副本整理-20261116-193141/下本任务执行器/回执/原包保护，以及下列5个checkout及其Git worktree注册元数据的正常移除。原Git对象库、所有分支/提交、main/master、其他owner文件和工作树、冻结主路径、活动DB、会话、环境、未提交成果均保护。
- 验收：移除前重核归档SHA、源逐文件指纹/无新增/干净状态/HEAD、同盘和无占用；只用git worktree remove，不使用force；失败保留并停止该项。每项后实测内盘余量，最后核5项目录/注册消失、主HEAD/index及其他工作树保留、HTTP200和固定资源可用。冻结研究不重跑；无新科研、交易、部署、后台任务或通知。
- 预算：仅本地存储操作，无模型委派/付费/市场实验；外盘已有10GB恢复包保留，新增日志与回执预计<2MiB，本机仅Git小元数据预计<2MiB。未设置自动清理。
- 下一步：本记录普通push且远端读回后，完成新鲜核验和5项正常移除，再记录实测释放量及最终状态。

## 精确清单

- `.codex/worktrees/ai-quant-practice-coordination-20261101` @ `c09232acc029e4389f74985a161eb3278c79cfb4`；外盘同名tar/manifest已核。
- `.codex/worktrees/factor-standards-coordination-20261103` @ `6963c79a2f0698e500d73199a0b5b57e60fdc697`；外盘同名tar/manifest已核。
- `.codex/worktrees/research-method-practice-coordination-20261031` @ `f060ca42d7231f28618d5715cf66bd2ac49f43d8`；外盘同名tar/manifest已核。
- `.codex/worktrees/research-utility-review-coordination-20261012` @ `6d93ec2963ce3f208f8fc3ff6112da25419750d2`；外盘同名tar/manifest已核。
- `.codex/worktrees/strategy-account-bridge-coordination-20261020` @ `cc3940730351b6b9a3c183c631be159f2982dce4`；外盘同名tar/manifest已核。
