# Stage 1 派发路由理由（2026-09-19）

GPT-6 Pro（主导方）在第 2 轮收敛中的原话推荐：「主执行推荐 glm-high，
flash-high 仅承接契约明确后的机械接线和样式」。本阶段包含前端区块实现、
既有 DTO 聚合链路的代码理解、以及字段来源对照（stage1-source-mapping.md
逐字段照抄纪律），属于需要诊断与实现选择的受限开发工作，不是纯机械执行，
故采用 glm-high。本轮不使用 flash-high（契约虽明确，但首次实现需要
代码理解与 UI 取舍）；若后续返修仅为样式/接线类机械修正，可按 GPT
口径降为 flash-high；若出现跨层架构问题再升级 glm-max。

说明：GPT 的最终确认轮（stage1-ack-request.txt）因 ChatGPT 通道截断未送达，
其第 2 轮完整收敛（round2_reply.txt）已含派发指令与验收口径，本路由
直接执行其既有指令；确认轮留待交付复审时一并呈报。
