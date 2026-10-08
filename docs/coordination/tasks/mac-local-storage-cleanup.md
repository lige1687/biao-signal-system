# Mac 本机空间清理与外盘归档

- task-id: mac-local-storage-cleanup
- owner: 01a1155d-b204-7232-a993-4c9e0567af59 / root
- status: completed（参数缩写限定修复、原默认外盘规则及已封存第五批）
- updated_at: 2026-10-08T22:32:27.908648+08:00
- checked_coordination_sha: d255c92256af696f0d20f983232be993bb0fead7
- checked_at: 2026-10-08T22:32:27.908648+08:00
- read_task_ids: mac-local-storage-cleanup, research-dispatch-controller, classic-factor-research, daily-trading-system-audit, theory-workflow-system-increment, trend-trading-video
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

## 实现验收与发布依赖范围 2026-10-08T21:29:03.403586+08:00

- checked_coordination_sha: 427aac8380b4c01036e80ec434c0b1beac5cfc0e；已读规则及classic/daily/中控最新记录，无准确文件冲突。原10入口保持字节，不改running jobs、冻结raw、DB或daily配置。
- 本机6准确新/追加文件已落，25检查、Ruff/归置通过。只读真实外盘身份及小文件fsync/SHA读回通过，实际默认计划因内盘不足5GiB拒绝；0科研运行、0内盘备用大输出目录。
- 19项第五批归档并移除完成，实测净增2582315008B；持续系统写入与swap增长使余量继续变少，既有日志与swap未动。
- 发布增加一个精确未修改依赖：configs/storage-policy.v1.json，字节与daily已发布 8bde94333264ed9649acfb05d975ed32a6019d06 完全一致、SHA256 dbdcc8af8bd5f1d6be7ce5262e10d21177a4c4faae97d4a4d2aeda900877d4dd。只在自身成果树复用已发布blob，共享配置不改、不声称本任务重设策略；原基线不含该文件，不复制整项daily成果。
- 成果AGENTS只将本轮新块追加到原Git版本，不提交共享工作区其他人已有未提交前缀；当前本机完整原前缀保留。私有归档/完整回执仅外盘，远端只小代码/规范/证据摘要。其余文件范围沿用已登记，唯一root。

## 本轮交付完成 2026-10-08T21:36:30.062971+08:00

- checked_coordination_sha: 7ce0479abef4cbba6a8add48d23f8891010fd718；checked_at: 2026-10-08T21:36:30.062971+08:00；已读COORDINATION1.1及classic/daily/中控、自身最新记录，无新增同路径冲突。root唯一本记录和准确实现路径写者，无子agent。
- 实际成果源 428dd19607ecc75cbe9f59e5e2fe3018c53dd9fd，8文件54587B；后继进度 8dd49d0f2733701ce17dfc964eeb738a94c3f685，codex/mac-local-storage-cleanup-20261008普通push/fetch逐字核。旧AGENTS未提交他人前缀不混入Git，只在base追加自己的新块；本机原全文前缀完整保留。未合main/master或更改共享索引/HEAD。
- 默认政策：后续AI所有新大型结果默认已核外盘，10个登记输出型脚本通过统一启动器自动传 --out/--output；旧CLI字节不改、原科学检查/预算仍执行。临时普通文件和stdout/stderr外盘，原小报告/ledger/锁/代码/环境/DB/会话/工作树本机，冻结raw/旧正在运行进程原位。没有全局重写所有历史脚本/第三方IO。
- 25默认路由/错盘/不足/新目录/保存计划/参数冲突/模拟断盘及新子进程写入检查通过；Ruff/归置通过。真实外盘UUID/FS/device和2624B文件fsync/SHA读回通过。真实默认计划exit3容量拒绝且无内盘备用输出，0实际科研，不降5GiB要求。
- 19精准闲置缓存包全归档/源稳定/无占用/内容链接模式复验后移除。146325504→2728640512B，净增2582315008B（2.40GiB），外盘ZIP和恢复清单完整。当前可用约1.42GiB，不声称全部空间问题解决；swap总分配20:54的7936MiB→9216MiB增加1.25GiB，解释部分持续增长，未删swap、截断活动日志或停止当前进程。
- 恢复与私有证据：/Volumes/win+mac通用/个人资料归档/2026-10-08-第五批-210009；远端只小实现/规则/安全摘要，无个人原件/数据库/凭证/大日志。
- 失败保留：zsh临时文本因ENOSPC在任何源删除前失败，改外盘执行；首次Ruff15格式项修正、后验通过，未弱化测试。模拟挂载不冒充真实拔盘验证，容量预算不是硬配额，强制断盘竞态限度见md。
- 收尾：本轮所有准确已授权实现、清理和必要验证交付；没有运行中后台实验或待删原件。之后的新实验先核空间和对应原合同；正在运行与冻结路径继续保护，尚未满足内盘5GiB余量，不能假称新实验已获启动条件。scope_released=true，仅本轮新增实现/说明与AGENTS新增块；自身恢复记录/协调/进度继续由本owner维护。

## 参数缩写漏拦截限定修复 2026-10-08T22:04:50.799821+08:00

- status: active；checked_coordination_sha: f83345b7c6414e1066f2498e570115a4966be653；checked_at: 2026-10-08T22:04:50.799821+08:00；已读COORDINATION1.1、自身、research-dispatch-controller（含限定修复末节）、daily-trading-system-audit、classic-factor-research、theory-workflow-system-increment相关记录。中控明确原owner修复，其他负责人只独审不写此范围；root唯一本记录及以下准确路径写者。
- 基线：原成果428dd19607ecc75cbe9f59e5e2fe3018c53dd9fd，原分支最新进度8dd49d0f2733701ce17dfc964eeb738a94c3f685。原独审已确认真实run_factor_evidence_reliability.py的--repo-r=/different绕过完整旗标检查；只有参数解析反例，0真实错盘输出。
- 准确写范围：src/lei_signal/research/output_storage.py；tests/unit/test_research_output_storage.py；tests/integration/test_research_output_routing_cli.py；必要docs/ops/research-output-storage.md说明及自己的docs/ops/work-progress/mac-local-storage-cleanup.md。本轮不改AGENTS/策略配置/10个原CLI/冻结合同/registry/INDEX。
- 验收：实际注册解析器能接受的输出、替代根目录、只读模式相关缩写（等号/分隔值）在建目录和启动前拒绝；合法完整参数保持。保留旧反例、原25项及针对回归，旧10CLI逐字保护。只做小合成测试；不清理、迁移、下载、真实科研、拔盘或停止他人进程；内盘不足5GiB不降低要求。
- 技术层：仅研究可靠存储/复现；两权威策略源SHA与已批准指纹一致，交易/科学语义及预算不变。资源入口已核4available；恢复证据放既有外盘第五批output-argument-repair，测试临时文件同处，不写本机大文件。
- 下一步：准确缩写检查与回归→必要25原检查及静态质量→原分支普通push/fetch逐字读回→交付中控复核。无需重做已封存清理或实验。

- 登记首次普通push因中控新记录被拒；已fetch并读新中控末节，本记录未变，当前 checked_at: 2026-10-08T22:05:37.130039+08:00。按新基线只重建自身准确记录，未强推、未改共享源码或其他任务。

## 参数缩写修复已发布并验收 2026-10-08T22:32:27.908648+08:00

- status: completed；checked_coordination_sha: d255c92256af696f0d20f983232be993bb0fead7；checked_at: 2026-10-08T22:32:27.908648+08:00；已读COORDINATION1.1、自身、中控原限定修复/独审、classic/daily/theory相关范围及video V8登记归属与V9新范围。唯一root写本5准确文件/自身记录，范围无重叠；他人registry/INDEX变动不恢复、不发布。
- 原工作分支codex/mac-local-storage-cleanup-20261008修复188b06d077044d1b2accfe24882bbf3d2627d90a，基线8dd49d0f2733701ce17dfc964eeb738a94c3f685。5准确文件50550B普通push/fetch，远端commit相等及每文件字节/SHA完全读回。无main/master合并、强推或共享索引/HEAD操作；原428dd196的8文件/清理成果未撤销。
- 仅新启动器、两测试、默认外盘说明及自己的进度改变；输出/替代根目录/只读长参数可能的缩写在建目录/启动前拒绝，含等号和分隔值。当前模块SHA256 aa722aa7641ea472231fa027fa53edcb78400615294410f256902834bc88ff95。10个原CLI、两存储策略本轮SHA不变；原合同/registry/INDEX均未由本任务修改。
- 本机55项通过（原25及新增回归），Ruff/归置/diff通过。只提取真实解析器AST构造、不导入/运行runner，10入口12种调用152种受保护参数写法拒绝；37完整非保护参数保留；6个在写/启动前拒绝场景通过。旧--repo-r反例两形式保存，0错误写盘事实、0市场研究、0清理/迁移/下载/拔盘/他人进程停止。
- 中控独立结果已实际读回 docs/experiments/raw/research-dispatch-controller-2026-10-07/goal-parallel-20261008/output-routing-controller-review.json 的repair_independent_verification：固定上述SHA，12缩写案例实际原解析器复核且mkdir/Popen=0、8合法完整命令与原版一致；没有重跑本任务55项或原设备独审。独立受影响行为已接受，主Goal整体验收仍归中控，不代表所有Goal完成。
- 真实容量预检仍明确因内盘不足5GiB拒绝，阈值与fallback=false安排不降低。尚未验证真实拔盘竞态、系统硬配额、全部历史/第三方写入；不改已有冻结路径或正在运行实验。
- 完整小回执/失败记录/测试临时文件在既有外盘第五批output-argument-repair：old-counterexample.json、parameter-acceptance.json、tests-verified.log、lint-verified.log、hygiene-final.log、source-publication-receipt.json；私人归档原件与DB未入Git。首次非快进/小文件写失败/2夹具类别期望错误/Ruff条件/他人共享SHA变化均保留且逐项解决，未忽略实际失败。
- scope_released=true：本轮src/lei_signal/research/output_storage.py、两相关测试与docs/ops/research-output-storage.md限定修复范围释放；私有恢复证据和自己进度继续由本owner保留。当前没有必需后台过程、科研重跑或清理动作；中控可按准确188b06d0成果接回。

## 用户继续清理：只读盘点与资料决策 2026-10-08T22:51:55.665721+08:00

- status: active（只读诊断/准备决定清单）；checked_coordination_sha: 18b3b30aa6de8cbcfa8df8b90edf959869f2101f；checked_at: 2026-10-08T22:51:55.665721+08:00；已读COORDINATION1.1、自身、中控、daily及video最新外盘写入记录。唯一root维护自己的进度/以下私有小证据；不占已释放的实现源码、不碰其他owner媒体或登记。
- 用户当次：“继续清理存储？”；复用已封存五批及默认外盘修复，不重做清理或研究。本轮先只读元数据/依赖/打开文件检查；没有新删除、移动、应用停止、工具安装或仓外配置修改。
- 新准确记录范围：data/cache/mac-local-storage-cleanup/storage-review-20261008-2233/小盘点json、gate-table.md、decision-plan.md和检查日志（私有、不入Git）；自己的docs/ops/work-progress/mac-local-storage-cleanup.md及本协调记录。无其他共享文件修改。
- 实际22:33 storage：内盘15032049664B约14.0GiB，外盘640268763136B且UUID正常，4登记资源可读。swap实测total1024MiB/used642.81MiB；前轮约9216MiB已降，解释一部分余量回升，不能把当前回升算本轮清理。没有本地TimeMachine快照。
- 新浅层盘点：内盘主仓54.1GiB属于活动/冻结/独有工作，保留；Library/Caches约708MiB主要活动Codex；Chrome代码签名临时副本约1.31GiB且lsof实际589/4560持有，保留，不把名义量当可释放。
- 三个待决定目录：Desktop/学业资料/01-毕业论文（38文件）、lajibiyelunwenjian（12）、学校相关资料（37），约124MiB名义量。含毕业原稿/答辩/九月改动资料；当前项目相关文本未找到引用且lsof无占用，但不能判断用户手动使用/唯一文稿价值。不把未占用当退休证明，不自动删除或扩大旧课程授权。
- 其余技术学习目录含源码/node_modules、环境或Maven；量化项目/现有新内容项目不因为大就移动。现有冻结raw、数据库/环境/会话/工作树/活动日志、说明元数据都保留。
- 下一步：零动作集的技能检查→询问三个准确学业目录是否迁至既有外盘；明确确认后再逐文件恢复清单/复制与内容读回/源稳定/无占用核验后移除本机副本。实际物理释放仍未知，不能承诺124MiB必然释放。未经决定不实施这个新范围。

- 2026-10-08T22:56:56.728748+08:00 收尾检查：新18b3b30a包含中控修复正式接受及video/X报告正常登记，均不与本私有元数据/进度范围重叠。旧修复188b06d0及独审不重做；新增external-learning-x-review已读，其私有源码/报告范围不动。
- 首次本轮登记push因上述他人新记录非快进拒绝；已fetch/read三变化记录且自己的记录未变，只重建自身准确增量，未强推。此前只准备自己独立的新私有小计划，无潜在共享冲突文件修改。
- macos-cleaner零动作计划9检查通过，12目标全部保留/待决定；0 destructive commands，对空计划适用，不冒称删除命令受检。首次quote缺少引号的格式错误已原样保存并修正，未改检查器。
- 已向用户询问3准确学业目录完整外盘归档、核验后移除本机副本的决定；尚未收到确认，不能执行依赖该确认的移动/删除。两盘身份已核，不外推至原先所有用户资料已批准退休。
