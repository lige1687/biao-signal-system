# Mac 空间清理与后续实验写盘

- task-id: mac-local-storage-cleanup；owner: 01a1155d-b204-7232-a993-4c9e0567af59
- status: completed（本轮 17 项安全迁移及写盘评估）；更新：2026-10-08T20:45:28.304758+08:00
- 跨任务当前记录：coordination/lei 的 docs/coordination/tasks/mac-local-storage-cleanup.md。
- 本阶段基线：18e64fa632dba5dbad0e5fcae09b4ccc75f119a9；共享工作区仅只读，不切换、不更改主索引。

本轮依用户已确认的“不影响当前实验”范围，归档旧 IDE 组件、旧游戏启动器、pip 下载缓存与 iStat 更新副本，17 项均完成外盘全内容、链接及模式校验后移除本机原副本。完整私有回执在 /Volumes/win+mac通用/个人资料归档/2026-10-08-第四批-202744-fd8be8，未上传个人文件、数据库或凭证。

实测内盘可用 509898752 → 2392268800 字节，净增 1882370048 字节（约 1.75 GiB）；名义目录量 3392286720 字节不能算作释放量。外盘归档 1753315463 字节。来源 22,860 普通文件和 3,213 内部链接均有指纹/恢复清单。

保护项：活动 DB inode/设备不变；原 CLI/workflow、两 storage 配置、registry/definitions SHA 不变；原 raw 路径不移不删，全部工作树/会话/环境/活动日志保留。API health ok；归置通过；没有重跑实验或宣称所有实验已验证。原 Time Machine 快照已不在，但其物理释放没有隔离测量，未归因本轮。

后续新结果可以显式绑定外盘新目录，大输出与小报告/研究记录分开。外盘父目录 /Volumes/win+mac通用/LeiSignal-新实验结果 已准备，未改变既有任务默认写盘。原负责人 preflight 成果 3d3c172c5119ca9ec3f8c77b17116d416f86f86a 已只读审阅；本机旧入口仍未采用 --storage-plan，本轮没有覆盖原 owner 的源码/配置范围。现有冻结 raw 含精确路径与内容绑定，不能整批迁移。

只读实际路径计划检查：外盘 UUID/文件系统/设备与路由条件核过；内盘保留 5 GiB 的计划拒绝（需 5370806272 B，实测 2384359424 B），未降低余量、未运行研究或建立结果目录。首次 Data 挂载点不匹配失败与修正保留。不是科研合同/预算执行验收。

技能：macos-cleaner 固定 d8d8528d25da61a68a1c91cc6f8c161068e52a13，任务专用快照；计划 9 检查通过，0 自有命令被其识别，另审执行器准确 scope/inode/恢复及删除语义，不冒称命令自动受检。复制容量峰值/外盘保留 10 GiB 通过。没有全局安装、通知或新自动化。

本轮范围已交付。后续有新清理范围须仍绑定依赖/占用和恢复证据；五个旧代理工作树各有独有改动，不能自动删除。所有实验全迁移需要各原负责人和明确逐项依赖方案，不把本轮评估当迁移授权。

## 后继：AI默认大结果外盘及第五批 2026-10-08T21:33:21.500896+08:00

- 用户明确授权写skill或项目md、后续大结果外盘、必留本机继续留、可迁移继续迁移。选择项目md＋AGENTS入口＋通用启动器，0新子agent。
- checked_coordination_sha: 427aac8380b4c01036e80ec434c0b1beac5cfc0e；已读classic/daily/中控、自身和COORDINATION1.1，原classic四实现scope释放但旧CLI指纹受冻结约束，故保持10个原入口内容，不改其源或旧合同。
- 新文件：docs/ops/research-output-storage.md、configs/research-output-policy.v1.json、src/lei_signal/research/output_storage.py和两测试；AGENTS仅独立块追加，本机原前缀完整保留。文档规定未来AI默认统一入口，输出/临时普通文件/日志外盘；小报告与原科学账本本机。无盘/错盘/不足/已存在/参数冲突拒绝；断盘只停止新子进程，未停止任何当前任务。
- 25相关检查通过，Ruff/归置通过；真实盘身份及2624B小文件fsync/SHA读回通过。真实默认计划exit3容量拒绝，0实际研究或计算、0内部备用大输出。
- 19项（Gradle缓存/下载wrapper、17个闲置npx包）全归档及源再核后移除，实测146325504→2728640512B，净增2582315008B（2.40GiB）；后续系统swap分配增长等使余量降至约1.40GiB，份额只作部分归因，不更改swap/活动日志/进程。
- 私有清单在/Volumes/win+mac通用/个人资料归档/2026-10-08-第五批-210009；不上传原件、大日志、数据库/凭证。归档失败无，19源及holding不存在、对应ZIP均留。
- 发布依赖是daily已发表8bde94333264ed9649acfb05d975ed32a6019d06的configs/storage-policy.v1.json，SHA dbdcc8af8bd5f1d6be7ce5262e10d21177a4c4faae97d4a4d2aeda900877d4dd，与本机完全同字节；只复用blob，不重设其身份/规则或发布整项daily代码。
- 目前未运行的历史固定输出脚本/第三方工具不作全局IO重写，所有后续AI先按本入口选新外盘目录；明确旧路径的小记录和冻结复现继续原安排。不是“所有旧进程已切换”，不能宣称新入口现在能跨过5GiB余量限制。
- source publication pending；既有第四批提交4e23a898220cc99474892570afacfa413b12c860作本工作分支基础。测试/原始失败和恢复记录仅外盘，无改main/master、强推、部署、自动化或交易。

## 发布与最终读回 2026-10-08T21:36:30.062971+08:00

代码/项目规则8准确文件已普通推送并逐SHA/字节读回：codex/mac-local-storage-cleanup-20261008@428dd19607ecc75cbe9f59e5e2fe3018c53dd9fd；54,587B，含原daily已发布canonical policy原blob。共享主索引/HEAD/他人源码不改，AGENTS本机原前缀保留、发布仅自己的新增块。25相关检查、Ruff/归置、外盘小文件和容量拒绝回执已核；0实际科研。checked_coordination_sha=7ce0479abef4cbba6a8add48d23f8891010fd718，已读classic/daily/中控最终记录，本轮路径无新重叠。当前本机约1.42GiB，外盘约596GiB；不是5GiB余量已达标。该限定规则＋清理交付completed，外盘恢复清单保留，下一次新实验仍先预检和科学合同核对；不自动改旧进程/冻结路径。
