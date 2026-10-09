# personal-quant-video-render-preview-rule

- status: active
- scope_released: false
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
