# Mac 本机空间清理与外盘归档

- task-id: mac-local-storage-cleanup
- owner: 01a1155d-b204-7232-a993-4c9e0567af59 / root
- status: active（后继 AI 默认外盘与第五批）
- updated_at: 2026-10-08T20:34:15.766327+08:00
- checked_coordination_sha: ff4cc9ed72599d016e411c2c283acea62fa8d663
- checked_at: 2026-10-08T20:34:15.766327+08:00
- read_task_ids: daily-trading-system-audit, theory-workflow-system-increment, research-dispatch-controller
- rules: COORDINATION 1.1；用户既有清理授权；AGENTS 的 AI 使用存储资源；macos-cleaner 固定版本 d8d8528d25da61a68a1c91cc6f8c161068e52a13
- source baseline: 18e64fa632dba5dbad0e5fcae09b4ccc75f119a9；共享脏工作区只读，不切换，不操作其索引。
- work branch: codex/mac-local-storage-cleanup-20261008（进度小文档待发布）；此前三轮私有清单在外盘，未入 Git。
- goal: 在已确认不影响实验的范围内，将旧软件组件和更新副本核验归档到既有外盘，再移除本机副本；核实际可用空间、API、保留对象。另只读评估未来实验写盘和现有实验迁移条件。
- scope: 仓外 aiXcoder installer、TabNine models、Paradox launcher-v2.2024.14、pip 下载缓存、iStat Menus 7/Patch 下 13 个准确旧更新子目录；实际白名单和 inode 绑定在外盘 scope.json。任何占用/变化/校验失败项保留。
- conflict decision: daily owner 的已迁移媒体/模型、原 storage 配置及 native CLI preflight 实现都只读复用。没有共享源码、配置、registry/INDEX 或 raw 修改；唯一写者 root。
- preserve: 活动数据库、环境、会话、所有工作树、研究 raw 及冻结路径、活动日志、swap、现装应用、设置及最近占用的两个 iStat 子目录。
- validation: 设备 UUID、复制容量计划、逐文件 SHA-256 和链接/目录/权限清单、源未变、无打开句柄、删除后实际 df、API 健康；归档失败不移除原件。
- data: 私有归档和回执仅 /Volumes/win+mac通用/个人资料归档/2026-10-08-第四批-202744-fd8be8；远端不包含文件内容、个人文档、数据库或凭证。
- completed: 三轮旧归档复用；本轮盘点、存储入口和技能安全说明已核；本轮尚未复制或删除原件。
- next: 检查器计划→准确归档→内容读回→按项移除→结果测量；实验现有入口不自动重定向。
- blockers: 无需重复询问已授权的安全归档；所有实验全迁移超出可自动处理边界，不作为当前已授权迁移动作。
- research budget: 不运行市场/拟合/冻结实验；0 新研究。

## 第四批完成及未来实验写盘评估 2026-10-08T20:47:04.412938+08:00

- checked_coordination_sha: cfbae47c948683d67396cf650752db0f9a137aec；checked_at: 2026-10-08T20:47:04.412938+08:00；已读 COORDINATION1.1 和 daily-trading-system-audit、theory-workflow-system-increment、research-dispatch-controller 最新记录。冲突决定：其他 owner 源码、报告登记、既有 storage/preflight 范围未修改；root 唯一自身记录写者。
- completed: 17 精确路径归档后移除；22,860 普通文件和 3,213 内部链接的内容、类型、权限及恢复清单通过。原件移除前再次全指纹/源未变/无打开句柄核验。无失败或跳过。
- actual space: 内盘 509898752 → 2392268800 B，净增 1882370048 B（1.75 GiB）；名义目录量 3392286720 B，不替代物理测量。ZIP 总计 1753315463 B，外盘余量约 598 GiB。其他进程会继续影响容量。
- source outcome: codex/mac-local-storage-cleanup-20261008@4e23a898220cc99474892570afacfa413b12c860，唯一小进度文件 docs/ops/work-progress/mac-local-storage-cleanup.md 已普通推送/fetch逐字读回；共享 HEAD、源码/索引不操作。私有数据只存原外盘第四批目录，远端无原始个人资料。
- validation: API health ok；六份原 CLI/workflow/storage 配置/登记文件 SHA 相同，两活动数据库 inode/设备相同；归置通过。raw 路径均保留，盘点到验收略增长来自其他运行写入；不重跑科研，不宣称全部实验收益合格。
- cleaner: d8d8528d25da61a68a1c91cc6f8c161068e52a13 任务专用快照，未全局安装；计划 9 检查通过但识别 0 自有命令，额外核准确 scope/inode 和删除语义，未把缺少覆盖当自动通过。完整规则文本保留，exFAT ._ 元数据不删除。
- future outputs: /Volumes/win+mac通用/LeiSignal-新实验结果 父目录已准备，可在新任务开工前显式绑定大结果；当前 --out 仍会有内盘小记录。只读审阅已发布 native preflight@3d3c172c5119ca9ec3f8c77b17116d416f86f86a，本机现有入口尚未采用，未越权覆盖原owner范围。
- live path check: 正确 UUID/exfat/设备路径检查后，内盘保留 5 GiB 计划被容量拒绝（需 5370806272 B，实测 2384359424 B），未降低条件、未新运行实验。首次 Data 非独立挂载点修正为同设备 /，原失败回执保留。
- scope boundary: 全部现有实验不能自动搬走；冻结 raw、活动 DB/环境/会话/工作树保留。五旧代理树各有 8–95 独有修改；活动日志、swap 未动。现有冻结路径迁移需要各负责人明确依赖与恢复方案，本轮提问不解除原限制。
- previous batch: 原 Time Machine 快照已消失，缺少隔离物理释放测量，不归因本輪。前三轮清单不重做、不覆盖。
- next / stop: 本轮所有已验真非实验闲置项与写盘问题已交付；没有必要后台运行、待删源或实验重跑。未来新实验须先核当前磁盘、对应入口采用状态与实际余量；不自动改既有任务默认路径、不创建或恢复提醒。

## 用户授权后续默认写盘与项目说明 2026-10-08T21:00:09.425852+08:00

- checked_coordination_sha: 6599115559a75fe0f4a864c97913b002b93dfb10；checked_at: 2026-10-08T21:00:09.425852+08:00；已读规则、自身、classic-factor-research、daily-trading-system-audit、research-dispatch-controller。
- 用户原话：“写一个skill 或者项目md让后续ai写大结果文件可以放在外接磁盘…必须继续留本机的继续留…目前所有实验默认写盘切过去吧，cleaner能清理的清一下”。具体执行为所有后续 AI 大结果默认外盘、现有输出型 CLI 通过统一默认外盘启动器；不改变正在运行进程或冻结精确路径。
- 新准确写范围：docs/ops/research-output-storage.md；configs/research-output-policy.v1.json；src/lei_signal/research/output_storage.py；tests/unit/test_research_output_storage.py；tests/integration/test_research_output_routing_cli.py；AGENTS.md仅新增独立默认写盘入口段；自己的 work-progress 和协调记录。
- 冲突决定：原 classic CLI 四文件已 scope_released=true，但一些旧 CLI 自身指纹绑定在冻结合同，故不批改或替换；新统一启动器向原 CLI 传外盘新 --out/--output，不改旧源码/冻结合同。daily拥有的storage-health/配置/doc不改，原 storage-policy只读复用。主 registry/INDEX、workflow/raw/DB/环境全部只读。root 唯一写者，不派新子 agent。
- 支持输出型入口清单为本机10个脚本、12输出参数定义；特殊只读子命令不强塞 output。仓内固定写路径的历史 raw脚本不猴子补丁，后续AI按默认规则先做明确的新输出绑定；覆盖明细写项目md，不能冒称所有旧进程已切换。
- 验收：外盘正确身份及路由，无盘/错盘/不足/已有输出均拒绝且无结果写入；输出不写回内盘，留本机记录只小索引；原CLI参数及科学检查由原入口执行；小合成/假执行器验证默认路径与子命令，实际设备只探容量/新小文件，不执行科研。
- 清理：第五批准确 Gradle 下载/构建缓存和闲置 npx 子目录正在核依赖，过门后归档/移除；不清 npm内容缓存、运行环境/工作树/会话/活动日志/虚拟内存/原raw。设备/恢复指纹沿用已核盘身份，私有回执在本轮外盘目录。
- 已读两策略源 SHA 与已批准指纹一致；本改造只服务研究文件可靠存放及复现，不改变趋势规则、计算、数据资格、费用、研究预算或交易授权。
- 基线内盘实测521596928B且其他进程持续写入；只小源码/文档，不创建完整checkout、不安装依赖；保留5GiB阈值，不为跑实验降条件。
