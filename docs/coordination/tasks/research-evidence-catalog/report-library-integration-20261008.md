# 报告库整合：个股缺价小试点

- task-id：`research-evidence-catalog/report-library-integration-20261008`；负责人会话：`01a1074e-3d9d-70a2-a771-b079443ace18`；状态：completed。
- 目标已完成：把已独立接受的 `stock-gap-pilot-2026-10-08.md` 正文和唯一登记、索引接入主工作区与既有独立成果分支；主工作区保留本地增量，未发布整份根级登记文件。
- 本次协调检查：`checked_coordination_sha=60a10f7cd0463e8782ffb716c1e79ecb7a62defc`；开工时间 `2026-10-08T10:39:47+08:00`，交付记录时间 `2026-10-08T10:47:05+08:00`（Asia/Shanghai）。已读 `COORDINATION.md`、`research-dispatch-controller`、`classic-factor-research`、`risk-shape-information`、试点任务及本 task-id。中控确认试点负责人仅写报告/raw/其任务记录；本任务是两处共享登记文件唯一写者。未改他线任务资料。
- 来源：`codex/stock-data-qualification-20261008@60a465b8b4064de567e24a96642d26ff5e841d30`。报告 SHA-256 `1fd356715d44bc60dae99837730aa67a33fe225b0a01c05309f585284dad39c4`；报告加19份小型 raw 共20份、219071字节，与来源逐字节一致；成果分支远端读回检查包含报告及 raw 的21项路径记录，均逐字节相符。
- 主工作区登记：registry 620→621，写后 SHA-256 `a8655c8e012746ad5378f78269fa7a02782f19470d15332d447ae05b74636549`；INDEX 增一条导航，写后 SHA-256 `aa9640d6dee381c86e1c296e385a35b01235e28b28f5ab8c0682704e0bbc45c8`。两项均未提交、未推送；反向移除唯一新增内容精确恢复写前指纹。
- 独立成果分支：`codex/research-report-library-integration-20261008`，最终提交 `375b5f85e9e3701eee301dae0dcc33ff92925e9e`，远端 ref 读回相同。registry 199→200，SHA-256 `1fb8f8533e35dcd0d503c269493d84caa53614e3f74eef849b7b26ea04ee06ed`；INDEX SHA-256 `89b85d67e549e8ecee8ddc6d3805072f5e013f6366a9e628b9a2e6835f979cf1`。最终回执 SHA-256 `2dea5be2efe33aad33dcf09f1991ec37425707bb24350c03637486367682a631`，进度 SHA-256 `a483ea43dfd1da7cd8ae577d6152b83ed692f181467cbd0f5cd45f6f187a4446`，均由远端读取核对。
- 限制：试点只确认600837三个缺价日两来源原始价一致；旧前复权版本、完整历史成员资格未证，主表补价为0，因子效果未测。本任务未拟合、重抓行情、复跑因子或扩展试点。一次初始机械断言在写入一条登记后停止；已反向核对精确恢复基线后再完成另一处登记，失败与修复记入回执；一次只读校验中的预期哈希手误也已更正，无文件变更。
- 产物：`docs/experiments/raw/research-evidence-catalog-2026-10-07/stock-gap-registration-2026-10-08.json` 与 `docs/ops/work-progress/research-evidence-catalog.md`。远端成果提交及文件均已读回；无未验证的推送动作。
