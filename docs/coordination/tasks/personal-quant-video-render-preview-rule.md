# personal-quant-video-render-preview-rule

- status: completed
- scope_released: true
- owner: 01a11ed4-6815-77f2-80d4-2880b2c8dea6
- checked_coordination_sha: 78c12879bfb2f79af4c94a6406ba0ce3b4074dee
- checked_at: 2026-10-09T15:40:12.055753+08:00
- read_tasks: trend-trading-video; nasdaq-story-video-20261009; dual-ma-video-copy-20261009; research-dispatch-controller; COORDINATION.md
- conflict_decision: trend原项目Skill已明确释放，最新仅ai_tools导出/工具；nasdaq与dual-ma最新仅独立影片版本，不改共享Skill；本任务唯一写者，仅下述三文件。
- authorization: 用户确认视频预览必须是真实视频工程渲染帧，并明确要求更新Skill。
- scope: .agents/skills/code-explainer-video/SKILL.md; references/staged-workflow.md; references/preproduction-workflow.md，以及自身协调记录。
- baseline: 本地codex/factor-unit-research-20260915@18e64fa632dba5dbad0e5fcae09b4ccc75f119a9的既有未跟踪Skill，逐文件备份后局部修改，不提交其他在途内容。
- branch: codex/video-render-preview-rule-20261009（仅协调记录）；Skill修改仅本地未提交/未推送，远端不可复现。
- budget: 三份文档定点编辑与校验，不运行研究、生成媒体或安装工具。
- validation: quick_validate、逐文件差异、引用、规则读回；同工程指定帧，禁止imagegen整幅概念图充当视频效果，静帧→15秒→全片顺序保留。

## 完成读回

- checked_coordination_sha: 601738d2b81c157c3b824fd2a7749788a7fb8b0e
- checked_at: 2026-10-09T15:41:42.175084+08:00
- 最新增量仅nasdaq交付记录，已读其明确不改共享Skill，无冲突。
- 三文件局部修改完成；quick_validate通过，本地引用均存在，逐文件差异读回通过。默认无旁白、素材按需、外盘及静帧/15秒/全片顺序保留。
- 新规则：实际工程指定帧预览，与后续视频共用场景；imagegen素材须合成入场景再导出；深色哑光在工程实现；保存帧来源。没有生成新媒体。
- Skill仅本地未提交/未推送；本远端记录不含Skill正文，不能声称Skill已远端同步。原文件备份位于当前任务work/skill-update-before。
- SKILL.md SHA256: 3145fe47fcf53d0fbd885ab43bcbc5f3a92bd0c76265485a35f80f95ab346b0f
- references/staged-workflow.md SHA256: b8ae38edfbf78ec8abb128b8f04f4992a8b9e542a4912496f8713e4fa91d74f7
- references/preproduction-workflow.md SHA256: 685e66bac7f61c13074a9c00c4fbac0094876ad13977f938262316708489ac60
