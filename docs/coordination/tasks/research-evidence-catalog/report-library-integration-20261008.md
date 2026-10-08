# 报告库整合：个股缺价小试点

- task-id：`research-evidence-catalog/report-library-integration-20261008`；负责人会话：`01a1074e-3d9d-70a2-a771-b079443ace18`；状态：active。
- 目标：将已独立接受的 `stock-gap-pilot-2026-10-08.md` 正文及对应单条登记、索引分别追加到主工作区当前共享文件和既有独立成果分支的文件副本中；不发布根工作区整份登记文件。
- 检查基线：`checked_coordination_sha=60a10f7cd0463e8782ffb716c1e79ecb7a62defc`；时间 `2026-10-08T10:39:47+08:00`。已读 `COORDINATION.md`、`research-dispatch-controller`、`classic-factor-research`、`risk-shape-information` 和本 task-id。中控已接受小试点；试点负责人只写试点报告/raw/其自身任务记录，当前摘要未发现其写登记表或索引。其他写者窗口由中控确认已串行开放。冲突决定：本任务是两处共享登记文件本轮唯一写者；风险形状负责人只写试点与其进度，其他线路避让既定登记窗口。沿用前阶段报告与回执，不覆盖派发和历史失败记录。
- 允许路径：主工作区只写 `docs/experiments/registry.json`、`docs/experiments/INDEX.md`，仅本机留增量；发布分支只写这两份文件、报告、原提交已发布的19份小型raw证据，以及本任务回执和本进度记录。
- 主工作区登记前值来自既有回执：registry 620条、SHA-256 `06991fd4f24cd71328070de02ae2bc94cef737346259a46e75d4e1bc84667266`；INDEX SHA-256 `1499d032befa4c0c1a0de7ddbc8fd4feac49d3d518712897f610dab371f2f5e7`。写入前仍须核实际值；不同则停止该处并调查差异。
- 成果分支基线：`codex/research-report-library-integration-20261008@19508745c7160bc07f5bbdefe9ba52ab39a5199e`；须保留已有199条登记、四份报告及15份证据。
- 来源：试点提交 `codex/stock-data-qualification-20261008@60a465b8b4064de567e24a96642d26ff5e841d30`，报告路径 `docs/experiments/stock-gap-pilot-2026-10-08.md`，SHA-256 `1fd356715d44bc60dae99837730aa67a33fe225b0a01c05309f585284dad39c4`；候选路径 `docs/experiments/raw/stock-data-qualification-2026-10-07/gap-pilot-20261008/registry-candidate.json`。只按原提交读取报告和19份raw，不复制行情缓存或B02大原件。
- 验收：主工作区和成果分支各增加一条登记、一条索引且唯一；移除本次准确插入块后各自回到写前SHA；发布分支报告/19份raw逐字等于来源提交；远端提交和文件SHA读回一致。0拟合、0行情重抓、0重跑。
- 风险边界：旧调整版本与完整历史成分仍未证实、补价为0；不扩大报告结论，不改主策略或旧登记，不合main、不部署。仓外状态数据库不写。
