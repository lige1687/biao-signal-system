# A股与美股专业投资观察地图

- task-id：investor-observation-map（沿用原任务稳定标识；首次接入，不重启任务）。
- 负责人/会话：原聊天Codex，01a0fd40-f651-7360-9411-d90f80affdc4；设备MacBook-Air-126.local。用户明确要求继续负责，不接管、不结束。
- 更新时间：2026-10-03T14:14:21.762382+08:00（Asia/Shanghai，UTC+08:00）。
- 状态：active（协调接入与既有报告维护）；新增来源核查子项paused。没有运行中的市场实验。
- 原目标：整理A股/美股机构、专业个人的指标与事件，说明系统已有/缺失、阈值/组合读法及趋势、定投、价值投资用途，并避开其他任务已在研究的方向。
- 用途与验收：50组观察地图能定位来源、当前覆盖、限制、使用方法及负责人；本阶段统一任务记录可远端读回，工作分支AGENTS仅增补协作入口，原工作区/进程/封存结果保持。信息地图不是收益改善；线上收益未测量。
- 适用规范：COORDINATION.md v1.0，读取commit `0b758e7e10f720c44cbd898d511ff392f2857535`；工作分支原AGENTS、报告所绑定研究规范与策略源不变。此次为文档同步，不创建新实验合同。
- 工作分支：`task/investor-observation-map-progress`。
- 基础commit：`18e64fa632dba5dbad0e5fcae09b4ccc75f119a9`。
- 最近已推送成果commit：`5ad8672f8907c85d0cd2162583450c75ff1f2373`（本轮git ls-remote确认；AGENTS由GitHub读回逐字一致）。
- 成果入口：[持续进展](https://github.com/lige1687/biao-signal-system/blob/5ad8672f8907c85d0cd2162583450c75ff1f2373/docs/progress/investor-observation-map.md)、[主报告](https://github.com/lige1687/biao-signal-system/blob/5ad8672f8907c85d0cd2162583450c75ff1f2373/docs/experiments/investor-observation-map-2026-10-02.md)。

## 已完成与证据

已整理50组指标、6类事件和三类投资方法的读取顺序；A股两融已有来源字段，统一卡部分覆盖，美国FINRA/COT在当时主观察链未发现接入；A股交易行为代理不等于持续情绪调查。NAAIM旧来源过滤后的末期为2026-05-11，是当时数据审查结果，不声称最新行情。主报告§1—8保留覆盖、反例、阈值身份与去重范围。

同一成果commit中的`docs/experiments/raw/investor-observation-map-2026-10-02/`提供brief、source-ledger、coverage-evidence、unpublished-artifacts、verification-summary、sync-verification、sync-manifest；registry/INDEX只新增本任务单项。历史恢复与限定固定成交额检查为10 passed / 1 deselected（退出码0），不是本轮新跑。前次14文件同步已核本地/远端完整SHA与13项manifest内容；投资效果、实时来源和全应用未验证。

## 正在做、涉及文件与限定下一步

统一机制已接入：首次任务记录9c994de31b2c325ee49080df50009e3369a52f55已从远端fetch逐字读回，工作分支AGENTS仅追加入口，自己的两份旧进度已映射本记录，brief/manifest同步。当前保留地图维护责任，已继续完成下述公开成果版本核对；没有后台研究运行。下一步有新版本或反馈时先核协调/证据，更新相应覆盖条目；新增取数/生产接入/因子实验未启动。

只维护自己的`docs/coordination/tasks/investor-observation-map.md`，不改COORDINATION.md或他人任务。研究范围仍限主报告及本任务raw、进度；没有生产模块写入，不修改src/、web/，不认领FINRA/COT、ETF成本、事件日历的未来实现。AGENTS此次增补只在自己的工作分支，不把共享工作区已有AGENTS修改带入。

## 依赖、重叠与其他AI应避开的范围

推前再次获取到协调commit `b172008890b39e912c8f1d0cfb9125d1e414a97f`，完整规则与首读版本一致。已读取`lei-coordination-bootstrap`及新登记`technical-factor-sequence`：后者负责C01/Q01封存和抵扣路径形状资料资格，本任务不进入该研究/文件。未发现正在写本地图同一文件或跑同一实验的已登记任务；尚未登记者状态未知，不视为空闲。

只读核对本地`docs/ops/work-progress/market-observation.md`、`external-quant-resources.md`、`technical-factor-mainline.md`、`technical-factor-sequence.md`，其中market-observation与本任务在指标口径/阈值/政策措辞上有主题交叠，未见同一地图文件的写入声明。协调安排：本任务暂停该重叠部分的并行改写，原市场观察负责人维护来源及页面口径；我只维护地图自身清单、缺口、投资方式读取顺序，引用新版前先核版本。随后在远端`067b29d17c0488d04edeba8d056dbed424433cd0`读到market-observation正式登记：当前实现者为原市场观察负责人，工作成果`5106f18ad6ffaf11f8fbf88a33427fbe936530fd`；其范围是zones.ts的US_CPI_ZONES措辞及观察卡日期/来源提示。我不改这些块、不做第二份并行解释，地图仅读取其已验证结果；需要改同一口径时先在协调记录明确分工。历史进度显示情绪/宏观来源、NAAIM日期/成交额、宽度、EMA/SMA、经典因子、宽基ETF账户研究已有负责人。本任务仅读取并引用，暂停任何重叠实现或实验；只继续独立的观察地图说明与同步。不得重写本任务报告/清单或向本工作分支推送；此说明不是排他锁，后续重叠需先明确实现与独立验证分工。

## 阻塞、仅本地材料与恢复条件

- 来源预算6/6已用，新增资料核查暂停，需明确后续资料范围/预算才可继续；这不阻塞当前文档维护。生产接入、完整历史许可和效果检验未完成。
- 仓库为公开；策略原件、完整AAII/NAAIM数据、历史交接包、其他任务未提交源码均**仅本地，远端不可复现**，不随此次上传。准确位置、已知大小/指纹见成果commit的`unpublished-artifacts.json`和`coverage-evidence.json`。没有权重/tokenizer。
- 历史包相对路径`docs/ops/recovery/investor-observation-map/investor-observation-map-20261003.tar.gz`，414937字节，SHA256 `1e5692a765373bedf929b44b321347221c5dad71098bd52e6e39c588e2ff5ab8`；仍本地，不改冻结记录。AAII/NAAIM的许可与首发历史未逐期确认，需要由数据持有人安全提供合规材料，不能从文件存在推定许可。
- 系统升级目标只有提案文件，仓外运行数据库未写；不能冒称已登记。
- 本轮原生工作区创建操作`d686dcd6-a216-482b-80d2-c5ae351fe4a5`失败：checkout报告No space left on device。随后只读检查剩余约445MiB；改为仓内任务专属小文档目录和独立Git暂存索引。不重复全仓检出、不清理/删除数据、不影响其他运行任务。

## 本轮检查、运行状态与预算

已通过：目标remote、工作分支远端SHA、协调规则/初始化任务可读；源HEAD仍为基础commit，暂存区SHA256 `83bb48fe19dcb073d4a449bcef331c745c942128ea53ca2a19c1f6791cbe7f92`。协调与工作分支无.github工作流，本地未配置core.hooksPath；未知外部集成不作为已证不存在。前次成果提交GitHub Actions查询0条，未发部署或付费命令。
失败：原生worktree全仓检出空间不足，未原样重试。未运行：新依赖安装、交易/研究测试、市场实验、训练、回测；本轮只改协作文档。
本任务没有研究进程、远端实验ID或待恢复checkpoint；本轮一次Luna只读重叠检查已完成，无文件写入、网络资料检索或实验；不占数据输出。没有杀进程，也未把复制文件当迁移进程。源合同公开资料调用累计6/6（A2、美2、主控2）；累计市场实验0、拟合0、付费0；本轮新增上述研究用量0。旧市场观察18/18独立计账，不借用。

## 封存结论、负结果与禁止重复

已有部分覆盖，中美并未齐全；阈值按定义/原策略参考/历史展示/限定研究用途分开，没有统一跨市场买卖阈值。功能和离线文件检查不代表预测或线上收益。本任务无新的收益试验，也没有正向收益结论。

AAII20周背景、VXN、认沽认购、EMA/SMA等待、经典因子等沿原负责人封存记录，不换名/调参重跑。仅新证据、前提变化、冲突或用户明确要求才能重开对应问题。原始决定与失败见主报告§7—9、ARCHIVE和工作分支阶段记录。

## 最小接续与本版变化

每轮实质工作先fetch远端coordination/lei，读取规则及相关任务，核本文件的工作分支commit和资料指纹，再只推进未完成项。先确认新版是否修复旧缺口，不重复旧试验。同步不转移负责人，也不继承生产、数据或付费权限。

本版首次加入唯一协调记录，映射旧两份进展，不迁移/删除旧路径；登记准确成果SHA、用量、未交材料、范围及空间失败。AGENTS入口与旧进展映射已实施并随工作成果推送；本记录是唯一跨任务当前摘要。状态文件自身SHA用git log --本路径定位，不无限补交自身提交号。

首次普通推送被拒（non-fast-forward）：远端新增market-observation记录。已fetch并读取新增任务，只整合本任务文件，保留其他文件原字节；没有强推。最新完整规则读取commit `067b29d17c0488d04edeba8d056dbed424433cd0`，规则内容仍与首次相同。

第二次普通推送也因其他任务更新被拒；最新读取`3fab17d5bd7225eb447bb2358aa9ca1ec1f97e13`的technical-factor-sequence变化，仅其自身输入资格/成果更新，范围不冲突，规则未变。改用GitHub单文件创建接口提交本任务记录，避免写回过时的整棵树；原待推提交保留本地。

## 阶段完成与原任务独立续整（2026-10-03T14:14:21.762382+08:00）

最新完整规则及任务读取commit `a775d1ebfe656f667455ae00bdc023880193d1dc`；COORDINATION.md SHA256 `6871aa85da956453ca8e4d077e9bd9d9bf229df42c8447ffb94f97ba7f2461e0`与初读相同。已读7条其他任务：初始化、technical-factor-sequence、market-observation、lei-technical-reader-research、classic-factor-research、external-quant-resources、remote-core-review。新条目分别限定技术阅读/等待、经典风险、外部研究工具、转黑资格，本任务不写其模块或跑其研究；未发现本地图同文件/同实验执行冲突。market-observation口径/阈值/政策措辞的主题交叠已经通过暂停本任务重叠改写来避让，不把记录当排他锁，未来需要改共同内容时先明确实现者与独立检查者。

已推送工作成果 `5ad8672f8907c85d0cd2162583450c75ff1f2373`，6条准确变更：AGENTS.md、本任务两份进度、brief.json、coordination-verification.json、sync-manifest.json。原AGENTS字节前缀保留且远端逐字匹配；共享脏AGENTS/HEAD/index未修改。15项manifest指纹、JSON与diff检查通过；本机共享工作区归置检查exit0（不冒称完整独立发布树/云端运行通过）。没有重跑历史10项测试或科学实验。

同步后继续原任务的独立部分：核market-observation工作分支成果`5106f18ad6ffaf11f8fbf88a33427fbe936530fd`的远端完整SHA，比较5个已引用文件。observations.py、turnover_snapshot.py、market-observations.v1.json、SentimentPage.tsx这4个SHA256与原覆盖快照一致，现有证据可由远端准确版本取得；FundamentalsPage.tsx指纹不同，旧快照不能当当前页面验收，原来源/页面负责人保留。完整原/新SHA及路径在本工作成果的raw/coordination-verification.json；没有复制他人源码、重新改口径或消费新市场来源预算。证据定位改善不是数据实时性或投资收益改善。

当前没有本任务实验、下载、训练、checkpoint或运行中的子agent；Luna只读冲突核查已结束。本任务维持active/持续负责，新增来源子项paused（累计6/6），无新研究授权。所有原冻结材料/失败提交保留；原生worktree失败后没有清理其他目录。后续新阶段按同一task-id同步，不新起已有任务。
