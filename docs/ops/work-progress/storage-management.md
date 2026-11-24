# Mac 清理与研究存储保护

- 更新时间：2026-10-07 07:59 UTC；本机 local，实际硬件标识未核。负责人为本次存储独立任务。
- 目标：核清可清理对象及实际释放量，默认不删数据的空间预检、输出预算、缓存引用与停止保护可用。
- 范围：只写存储独立模块、测试与本任务运维记录；不碰并行数据资格和 Rank IC 方案，不改因子/股票池/收益评估，不新建工作树，不复制大数据。
- 分支：当前共享 `codex/factor-unit-research-20260915`；检查时 HEAD `18e64fa632dba5dbad0e5fcae09b4ccc75f119a9`。这不是本任务成果提交；本任务未提交/推送，未暂存已有脏文件。

> 当前状态：旧版空间保护经独立审查发现四项高风险缺陷，不能采用。修正版一次新的官方 Library 下载票据仍返回403，本机未取得 ZIP，未做修正版验收或入口接入。所有统一入口的显式写入位置已完成只读核查，见末节；以下早期测试和交付状态保留为历史记录。

## 计划、完成与下一动作

1. 有限清理盘点：完成。精确候选、版本核对、拒读位置、空间快照、保留项见 `docs/ops/research-storage-guard-2026-10-07.md`；没有清理释放空间。专用清理 skill 未找到，未安装。
2. 小模块与历史验证：旧版交付及18项合成测试完成；独审后当前状态不通过，不能视为可靠保护。`src/lei_signal/research/storage_guard.py` 与 `tests/unit/test_research_storage_guard.py` 保留原样；修正版本机验收受下载403阻塞，未接入。早期低空间阻止、目录和空白检查记录保留在下文。
3. 清理执行：未批准、未执行。主控最新要求：59 MiB pip 清理不值得继续打断用户，不再发确认；先前子任务问题不替代父任务逐项授权。保留 `/Users/yongbiaoli/Library/Caches/pip/http-v2`（62,128,128 字节快照）及其他资料。同盘 Trash 不能释放空间，故不为表面动作去移动。
4. 当前无本负责人运行中的研究实验或清理后台任务。已有新增小产物，旧数据原位保留。
5. 主控下一步：通过官方 Library 支持恢复准确修正版文件的下载授权/本机材料化能力，取得并核包后才能完成本机验收；本任务不继续重试403或绕过。保留 Codex 更新暂存，因为版本更高且未确认废弃。其他大目录需完整引用/退休/移交证据及逐项授权，不能因重复哈希删除。
6. 系统目标登记：已按用户项目指引经本地 API 登记 `okr-1a9c771b2a06`，版本 4、paused，读回盘点/工具两项完成，清理/验收两项未完成。主控复用这一条，不再新建。先前错误创建请求被接口 409 拒绝、读回未创建后才修正；没有修改种子或其他目标。

## 验证与失败保留

- 最终测试：18 passed in 0.83s（仅合成小子进程及文件；必要的进程组测试经自动审批执行）。原沙箱停止权限失败及 `/tmp` 初次误拒已记录并修正，不删除失败历史。
- 真实低空间预检：389,345,280 字节可用，需要保留 536,870,912 再加输出 8,388,608，返回 `blocked_before_launch`，没有启动真实研究。
- 04:03:25 UTC 最新观察可用 3,972,087,808 字节；增加非本任务清理所致。实际删除/移动/清空数 0，清理释放 0。
- 2026-10-07 04:10:10 UTC 新观察可用 3,679,834,112 字节，约 3.43 GiB。上条约 3.70 GiB 的准确测量时间就是 04:03:25 UTC，不能当作当前固定空间。没有删除或移动既有资料，不推断空间变化原因。
- 聊天更新工具失败，未反复同样重试；本记录和最终回复作为回交证据。
- 程序不是全系统硬配额；旧入口未自动改接，第三方大块写入可能在轮询间隔内超限，进程组之外的新会话不受停止控制。完整限制和恢复条件保留在主文档。

## 2026-10-07：Library 独立审查包

- 按主控接续要求保存 `lei-storage-guard-review-20261007.zip`，本地 `/private/tmp/lei-storage-review-20261007-8paw4598/lei-storage-guard-review-20261007.zip`，19,837 字节；7 个成员、解压总量 46,113 字节，均小于 1 MiB。包 SHA-256：`a6f410633e39b47fe15056406c4cc874f0376a79e2d1843a3275a84fa2611ac9`。
- 包内是四份本任务代码/测试/文档快照、审查说明、验证摘要与指纹清单。没有研究输入、账户、数据库、缓存或凭据；没有新运行真实研究。已有 18 项验证对应的代码/测试指纹再次核同，ZIP 完整性与所有成员大小/SHA 核对通过；未无理由重跑测试。
- Library 已保存成功，文件 `lei-storage-guard-review-20261007.zip`；`library_file_id=libfile_1f826e59bbac8191b63a432fc5f4a393`，`file_id=file_00000000f3d881f5badcc27a2174a4c1`，Library 路径 `/lei-storage-guard-review-20261007.zip`。本地文件的 Library 身份保存成功。
- 包内进度是上传前快照；本小节是随后补记的交付回执，不回改已冻结包。主控用上述 Library ID 交云端审查，不能把保存成功当独立审查通过。审查前不接入旧入口。
- 清理继续未批准、未执行，不再发确认；保留更大的待更新暂存与所有研究资料。约 3.70 GiB 的准确观察是 04:03:25 UTC、3,972,087,808 字节；04:10:10 UTC 为 3,679,834,112 字节。不得用包创建或上传时间替代这两个测量时间。
- 系统台账已补记本次 Library 交付，实际读回目标 `okr-1a9c771b2a06` 版本 6、paused，下一动作为云端独立审查。前面的版本 4 是首阶段快照；没有标独立审查通过或自动接入。

## 2026-10-07 06:45 UTC 后：修正版 Mac 验收接续

- 主控云端独审发现旧版四项高风险缺陷：缺失 SSD 时向上寻找祖先而落到内置盘；输出路径被替换后可能逃出预算；收到 SIGTERM 后另起会话的写入者可能继续；仅确认进程组首进程退出。旧版 18 项绿色合成测试没有覆盖这些缺陷，不能称为可靠保护，本机正式入口仍未接入。
- 主控提供修正版 `libfile_362beae7a9fc8191a9c4cecd45c5bbf8` version 0，包名 `lei-ssd-storage-guard-cloud-review-20261007.zip`，54,018 字节，包 SHA-256 `487fe81216a0d6398051d0a4c72be9c57ca25b2c49d2f3bf94f0c0e14447fc90`，候选代码 SHA-256 `968a568f89567e08148db96bbeb68f7281362de49716291297e7ecd81017c0de`。主控报告云端 34+5 测试通过；这是传入证据，本机尚未独立核验。
- 本机 06:45:53.587897 UTC：内置可用 9,006,321,664 字节；`/Volumes/win+mac通用` 为已挂载卷，可用 652,974,751,744 字节。允许≤2MiB新本机小材料，低于512MiB则禁止新增；未写 SSD、未断盘、未碰运行数据库和已复制备份。
- 当前 Library 搜索/读取核准准确包名、54,018 字节及文件 `file_000000008c6881f58d2d0baa4a5a2420`；ZIP 不支持文本读取，未把元数据当代码。正式 prepare_materialize+当前 helper 首次网络失败无目标文件，必要网络审批后返回403；没有原样反复重试。按完整搜索结果走当前 Library 下载 helper 又报告 `Library prepare_materialize is not available`，会话已完成（exit1），未生成 ZIP。只产生官方辅助程序和小缓存约85,832字节，不能用云端路径冒充本机文件。
- 阻塞验收：未能读包内 Mac acceptance、未能核本机包字节/候选指纹、未能运行本机兼容性与合成测试。恢复条件是当前正式 Library 消费渠道可下载这份准确内容；不得通过改安全设置、未知下载脚本或未经核验副本绕过。缺包不影响当前入口只读分析；所有代码路径维持原状态。
- 本轮并行只读合同（不可扩权）：mission=定位一个入口的最小接入范围及验收；task_scope=只读既有入口与其输出行为；read_only_paths=AGENTS.md、scripts/run_factor_lab.py、src/lei_signal/research/workflow.py、docs/research/current-standards.json；write_paths=[]；network_allowed=false；max_agents=1；one_writer_per_file=true；preserve_dirty_worktree=true；executor=gpt-6-luna/low；controller_review.required=true；expected_outputs=入口候选、代码位置、写入边界、权限与验收缺口；stop_conditions=缺输入/需网络/需写文件/超范围。该助手不得声称读过尚未材料化的修正版，不执行研究或自行派发。
- 并行 Luna 只读助手已返回，无写入/测试/网络，未回退模型；主控独立核对 `workflow.py::_freeze_contract` 与 `freeze_workflow` 实际代码。最小提案是 `scripts/run_factor_lab.py` 的 `--workflow-draft` 分支调用前（41–46行），仅限定资料检查与合成演练，不改变已有冻结研究入口；正式新研究索引仍是 `--workflow-contract`。实际稿件冻结在创建 `--out` 之前写 `docs/experiments/raw/research-workflow-ledgers-2026-09-29/<digest>/attempts.jsonl` 和 `execution.lock`（124、140、882–900行）；输出目录写三份 contract/rehearsal/preflight JSON（1146–1157行）。因此仅监控 `--out` 的单目录补丁不足，还需分别约束仓库小台账与 SSD 输出，并在启动前禁止无预算字节码写入（入口12行先导入模块）。
- 暂定验收：缺预期 SSD 就停止而不回落内置盘；路径替换/移走/链接切换不能逃出已核身份的目录和预算；SIGTERM 后另外建立会话的写入者也不能继续；确认所有受控进程已停止而不是只确认首进程；全部目录内外写入有各卷预算。这些是针对原四项失败的必要检查，不代表已读 Mac acceptance 或已确认候选通过。
- 下一最小动作：恢复此准确 Library 包的正式材料化能力，核包54,018字节及上述 SHA，再读 Mac acceptance 才能确定本机合成检查和最小补丁。真实 SSD 创建/写入小文件或新增输出入口需主控按精确目录、字节预算、失败保留与停止条件取得相应授权；本轮没有自动执行。代码及测试仍分别为 `218ae0349931d37d0c27dd82dbfefa13fada5e01f1fa1e210c35dc362052ba9a`、`21f4b975fd65ba74503959f4d909467620ee5d2dc9b050f681d842b46168a3a4`，未切换数据路径。
- 本次新增辅助程序/小缓存85,832字节加有限文档更新，低于2MiB；未新增真实实验、未做测试确认、未删除旧失败或资料。Library下载会话55481已结束exit1，没有本任务挂起下载/研究命令；文件级归置自检通过。实际模型费用未知；没有给绿色本机测试或安全接入结论。

## 2026-10-07 07:51 UTC 后：一次官方刷新与完整写路径核查

- 用户通过主控要求解决403继续，并授权一次新官方票据/本机正确消费流程；若仍拒绝必须停止传输，不猜URL、不外传、不改安全或网络设置。另一任务正在删除明确获批的历史源备份，本负责人不读取或修改那些目录。
- 07:51:56.063870 UTC 本机可用5,779,529,728字节，SSD仍挂载。当前 Library SKILL 与材料化文档重新核对，从当前来源取得全新 helper；在实际项目工作区 `.biao/` 下新建私有接收目录，显式固定 `libfile_362beae7a9fc8191a9c4cecd45c5bbf8` 与 `file_000000008c6881f58d2d0baa4a5a2420`。正式返回新传输票据，下载地址与旧票据不同，版本0、54,018字节一致；没有返回已落本机的 workspace_path。
- 使用当前官方 helper 和完整未改传输对象立即消费该新票据，完整非秘密错误仍为 `library file transfer failed: download failed with HTTP status 403`，进程已结束exit1。目标ZIP仍不存在。当前helper与上一轮字节一致，不能说升级工具已修复；没有使用旧票据，也无法凭403确定服务端具体拒绝原因。停止该传输，不继续重试。本机包指纹、成员指纹、Mac acceptance与合成验收仍受阻，需要Library支持核查新票据对应文件的内容下载授权及当前Mac客户端材料化兼容性；不得索取/发送凭据或签名下载地址。
- 独立剩余工作：原统一入口所有可定位写路径清单。新只读双助手合同：max_agents=2，one_writer_per_file=true，write_paths=[]，network_allowed=false，preserve_dirty_worktree=true，controller_review.required=true。workflow写入审查由gpt-6-sol/medium负责（read_only_paths=AGENTS.md、src/lei_signal/research/workflow.py及其直接写入工具模块、scripts/run_factor_lab.py）；三个旧分支写入审查由gpt-6-luna/low负责（read_only_paths=AGENTS.md、factor_lab/runner.py、benchmark_pilot.py、classic_attribution.py及其直接写入工具模块、scripts/run_factor_lab.py）。不测试、不导入执行代码、不触碰活动数据库/备份/SSD、不派发更多助手，不认证尚未材料化修正版。输出仅写路径模板、触发条件、调用位置和静态核查盲点；主控在实际代码核关键路径后接收。

## 2026-10-07 07:59 UTC：统一入口显式写入位置清单（只读核查）

结论：把 `--out` 指向外置盘，只能改变主要结果的位置。两个工作流仍先写内置盘仓库的运行记录和锁；登记报告时还会写报告库及登记表。磁盘保护必须在这些写入之前启动，并分别约束涉及的卷。没有正式接入，也没有运行研究或修正版测试。

此次入口是 `scripts/run_factor_lab.py` 的五个互斥分支。`--register-report` 仅用于 benchmark/contract；`--reuse-predictions` 仅用于 contract。ROOT 指当前源码所在仓库；协议中的输入、报告名和研究族决定具体路径，故没有虚构一份尚未选择的合同的实际输出清单。

| 入口与条件 | `--out` 下的显式写入 | `--out` 之外及失败时的写入 | 当前源码位置 |
|---|---|---|---|
| `--workflow-draft` | 新建目录；排他创建 `contract.json`、`rehearsal.json`、`preflight.json` | **结果目录创建之前**，仓库 `docs/experiments/raw/research-workflow-ledgers-2026-09-29/<digest(history.family)前24位>/attempts.jsonl` 与同目录 `execution.lock` 可被创建。记录研究族和演练成本；符合记录条件的检查失败也可追加 `gate_attempt`。演练抛错仍追加成本，失败不保证有 `--out` 失败文件。 | 入口41–46；`workflow.py:122,128,140,888,908,1172` |
| `--workflow-contract` | 新建目录；`contract.json`、`preflight.json`、`result.json`、`report.md`、`receipt.json`、`state.json`；异常可写 `failure.json` | 同一仓库记录/锁。首次检查后打开锁、登记运行再创建结果目录；符合条件的失败追加检查成本；计算及验收追加记录。外层捕获部分启动前错误时，也可能新建 `--out/failure.json`。 | 入口48–55；`workflow.py:1547,1563,1584,1644,1674,1681` |
| contract 同时 `--reuse-predictions` | 新一轮照常写上述文件；旧结果目录的 contract/preflight/result/receipt 作为输入 | `verify_receipt` 使用 `locked_journal`，以 `a+` 打开仓库 `attempts.jsonl`，不存在时会创建，不能当作完全无写入的读取。 | `workflow.py:1284,1298,1589` |
| contract 同时 `--register-report` | 先完成结果和 state 文件 | 验收后写 `<ROOT>/<contract.publication.report_path>`（限 `docs/experiments/` 下带日期的新 md）；以 `r+` 和文件锁原地重写并截断 `docs/experiments/registry.json`。没有显式临时文件/原子替换；报告写成后，登记表写入失败可留下部分登记结果。 | `workflow.py:1511–1544,1658` |
| `--protocol` | 新建目录；`protocol.source.json`、`values_<artifact_id>.csv` 与 `.meta.json`、可选 `targets*.csv`、`diagnostics_<name>.json`、可选 `validation.json`/`attribution.json`、`quality.json`、`summary.md`、`run.log`、最后写 `manifest.json`。JSON 清洗警告另写 `<原文件名>.sanitization.json`。 | 没发现调用路径的显式目录外写入。格式失败仍可新建目录写 `run.log`；资料不足可写 quality/log；意外错误尝试删除本轮 manifest 后刷新 log。已有结果目录先拒绝。 | 入口66；`runner.py:122,735,814,825,863` |
| `--benchmark-protocol` | 新建目录；`panel.csv`、`predictions.csv`、`results.json`、`trial-ledger.json`、`report.md`、`manifest.json` | 同时 `--register-report` 才额外排他创建 `<root>/<config.report_path>`，再写固定 `docs/experiments/registry.json.tmp` 并 replace 登记表，没有锁。写报告后发现登记重复可报错并留下报告。 | 入口59–62；`benchmark_pilot.py:361,385,444–467` |
| `--attribution-protocol` | 新建目录；`monthly-panel.csv`、`explanations.csv`、`coefficients.csv`、`results.json`、`model-card.json`、`attempt.json`、`manifest.json`；JSON 排他创建。 | 没发现调用路径的显式目录外写入；数据绑定使用协议 root，结果目录用传入 `--out` 解析。该入口拒绝 register/reuse。 | 入口31–39；`classic_attribution.py:74,333–375` |

所有入口在 `main` 之前已经导入 `factor_lab.runner`（入口12行）。未禁止字节码时，Python 可能在脚本、源码或依赖目录写 `__pycache__`；保护只放在 `main` 内不能覆盖这一步。相关直接辅助模块在本轮静态调用路径中未发现其他显式写入，但第三方库运行时缓存、临时目录和脱离进程组的写入无法凭静态阅读确认。无具体合同和运行监测，不能称为所有实际字节已受硬限制。此次未导入/执行这些模块。

两位助手仅阅读，均已结束，无模型回退。负责人独立核对了运行记录在 `--out` 之前、复用检查的 `a+` 副作用、两个报告登记路径、runner失败日志/manifest删除及attribution写入位置；没有无理由重新跑科学实验或旧18项测试。早期记录的行号是当时快照，下表和本节为此次实际源码身份。

| 已核源码 | SHA-256 |
|---|---|
| `scripts/run_factor_lab.py` | `a8542f48980a52edb6f59b276ef64dacf801aa48cf751fbd39165f9d30497476` |
| `src/lei_signal/research/workflow.py` | `967d92adc77a18c42f16fda27c80eb5a136eadd72e4918515302003216a43cb6` |
| `src/lei_signal/research/factor_lab/runner.py` | `97b49d9e14d5740a2b7f8e04cbb5a4d18e32d59e819e4a804d1d068f39f23917` |
| `src/lei_signal/research/factor_lab/benchmark_pilot.py` | `20709406a69e4657035a9a263bd736616abe104525c6f256cdad2302f7e06c66` |
| `src/lei_signal/research/factor_lab/classic_attribution.py` | `4448c7bee6743bdcbaf98903d332e9dd439f2df9591fe907bcc50360909e2e46` |

一次新官方票据失败的本机材料目录为 `.biao/storage-guard-mac-ticket-20261007-lu5rj5tx/`，仅保留11,085字节的官方 helper；目标 `lei-ssd-storage-guard-cloud-review-20261007.zip` 不存在。helper SHA-256为 `5c81478cd94a59d721a1677d0bd36f7cec23c18a21b48740b1c9ff94d27fb26f`，与之前官方版本一致。完整非秘密错误已留在上一节；签名地址、票据认证内容未写入报告。旧版代码和测试指纹保持之前值。正式下载拒绝后没有绕行、重试、安装软件或改变设置，也没有修改任何入口源码。

验收状态：写入位置静态核查完成；修正版包/成员SHA核对、Mac acceptance阅读和本机合成验收受官方下载403阻塞；正式保护接入未执行。恢复必须由官方渠道使这一准确文件可被本机正常材料化，随后核字节和指纹再继续本机小规模验收。任何实际SSD输出、生产切换或原文件删除不包含在本阶段。

最终核对：2026-10-07 08:01:26.348915 UTC，本机可用5,259,120,640字节，SSD仍挂载；接收目录只有11,085字节helper，ZIP确实不存在。进度文件约19.5KB，连同前轮85,832字节官方材料及本轮helper，远低于本阶段2MiB预算。归置自检通过，相关路径diff空白检查通过，进度内容已读回。此次仅补记录，没有新增实验、测试确认、原文件删除或SSD写入；本任务实际清理释放0字节。
