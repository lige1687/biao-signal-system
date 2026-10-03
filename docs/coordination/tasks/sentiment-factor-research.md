# LEI 情绪与市场状态因子研究

- task-id：sentiment-factor-research（唯一稳定映射；旧入口docs/progress/sentiment-factor-research.md、docs/ops/work-progress/sentiment-factor-research.md均保留）。
- 负责人／会话：本聊天/root，01a0ebfb-fd80-7c62-97c9-ac24d20f58e4；设备本地Air/Darwin arm64。仍负责原任务，不接管其他线、不结束研究。
- 更新时间：2026-10-03T14:12:53.174522+08:00（Asia/Shanghai）。
- 状态：blocked（原E核心历史输入与已耗来源预算限制；本轮安全协调登记正在完成。已封存有界子问题为completed，不代表整库完成）。
- 工作分支：task/sentiment-factor-progress；最近已推送完整成果commit：662a8101aadd70659c10e9c93e97c644eee61ea4。
- 基础完整commit：d197600b6394244465e1c31b1766b7fc2652197c（远端main已存在基线）；原共享源HEAD18e64fa632dba5dbad0e5fcae09b4ccc75f119a9不是全部任务成果。协调规则初读commit0b758e7e10f720c44cbd898d511ff392f2857535，提交前再读最新。

## 原始目标、用途、验收与规范

建立LEI Sentiment Factor Library：市场参与程度／个人调查看法／管理人自报敞口／期权成交构成，能否在已有价格信息后，稳定补充宽指与ETF未来涨跌和下跌风险判断。宽度指成员股票站上各自均线的比例，不能把它与调查都叫真实心理。

验收：相同对象、日期、未来目标、训练可知边界与简单历史平均/现有信息比较，报告量级、不确定性、时期反例与增量。投资资金收益、完整E、线上收益未测量；误差改善不是收益。原任务全文在成果分支docs/experiments/raw/sentiment-library-s01-readiness-2026-09-29/user-mission.txt。

规范：COORDINATION.md1.0及最新用户协作要求；本工作分支AGENTS与docs/research/current-standards.json，新研究实际绑定版本，旧合同不追填。本轮只是协调接入，不新建科学合同。最后AAII20有界协议sentiment.aaii-background@1.0.0，冻结规范与策略SHA见其standards-manifest和snapshots。

## 已完成及准确成果位置

成果统一链接：https://github.com/lige1687/biao-signal-system/tree/task/sentiment-factor-progress 。下面路径必须从最近成果commit或其后经确认的本任务提交读取：

- 18份情绪研究报告、31份实验/独立核验脚本、情绪库、协议/结论/输入指纹已同步；现有工作分支与远端662a8101aadd70659c10e9c93e97c644eee61ea4一致，427文件变化，未带共享源未推的14个其他功能提交。
- AAII20周平均：docs/experiments/sentiment-aaii-background-2026-10-02.md；SPY816同日期误差8.971→8.908个百分点，简单平均8.751更好；删2020后优势−0.247%。限定问题完成、稳定新增帮助未确认，不改规则。
- 短史宽度：docs/experiments/sentiment-breadth-effects-2026-10-02.md；147日期局部改善，删2025年4月训练影响后变差，原E资料阻塞没有解除。
- AAII极端/下跌风险及PutCall旧问题已结案，无稳定帮助；NAAIM78周只有有限线索，不推广完整家族。详细量级、反例、限制在各2026-09-29/30报告与raw中。
- docs/research/sentiment-factor-library/保存研究卡、目录、累计尝试与失败；docs/progress/sentiment-factor-research/verification.json保存本阶段31脚本语法、297JSON、18报告登记/结论及目录检查；0新拟合。
- 恢复后7份旧宽度相关缓存指纹未变：docs/progress/sentiment-factor-research/local-input-resume-check.json。未重跑原算术或市场实验。
- 已继续核对下一阶段边界：docs/progress/sentiment-factor-research/resume-boundary-check.json；共同/各窗口分母都可明确定义，指标自身首发档案不额外强求；旧Pro计划不是实际运行冻结合同。

## 正在做、下一步和暂避范围

本轮正在接入协调机制、补本分支AGENTS简短入口、映射旧进度、登记唯一任务文件；这不是市场计算。相关变更只限本任务记录、工作分支AGENTS增补和两个旧进度指向说明。科学工作当前因资料受阻，没有运行中拟合，不把计划写成正在运行。

本线继续负责原E合格历史20/50宽度输入资格及随后相同低宽度状态内AAII确认的具体问题。实际投入此前先读最新协调记录，资料合格和有限预算明确后才冻结设计。无需宽度先单独有正结果；不硬挡技术信号，不改15/85或±25阈值。

其他AI暂避同题重复派发、已封存模型重跑和对本任务文件并发写入；这不是排他锁，实际重叠要明确实现/复核分工。普通技术、宏观覆盖、QQQ/VXN、页面任务不属于本线，也不圈占全部情绪/宽度方向。共享src/lei_signal/research/workflow_evaluation.py由现有工具线维护，本线只复用数学核/冻结副本，本轮不改共享源码。

## 依赖、重叠与阻塞

核心依赖：真实历史成员与变更、价格/调整/缺价、计算版本和输入可知边界；已知当前494成员回填不合格。Investing旧正常导出无确认文件，不能继承Air登录。新的真正合格资料及明确有限预算才解除相关阻塞；用户无需发供应商询问稿，免费/有限免费优先。

最新完整读取协调commitd5f4c68459a1fbd40cf89e6813a15982f830bc31的规则与八份任务记录。初始化任务维护稳定规则；market-observation负责CPI说明、观察卡日期/来源和既有QQQ/VXN问题，investor-observation-map负责覆盖清单及阅读顺序，二者保留本线SPY/AAII与宽度原归属；lei-technical-reader-research负责阅读页、等待描述和待定2B，technical-factor-sequence负责抵扣路径输入资格并明确排除情绪/宽度。本线不改这些页面、候选、共享工具或登记表，未发现已登记的同模块写入或同实验运行冲突。追加读取classic-factor-research（经典风险结案）、external-quant-resources（外部工具依赖核查/共享整合暂停）、remote-core-review（转黑重置资格准备）；三者当前均不处理本线问题，共享workflow只读。本线复用外部资料资格/预测边界技能，不并发修改这些技能、共享数学核或定义登记。规则SHA256为6871aa85da956453ca8e4d077e9bd9d9bf229df42c8447ffb94f97ba7f2461e0；不修改规则或初始化检查器。其他任务尚未登记/过期时状态未知，不能说空闲。可能共享的数学核、宽度生产源与全局registry不作独占，本轮不修改共享研究实现；同步登记前不启动潜在重叠实验。若后来发现同模块/同实验活动，暂停冲突部分，先通过任务记录协调，不自动重开或接管。

## 运行状态、预算和封存

本轮本地检查无sentiment实验进程，协作树仅/root做文档，旧8个子代理不活跃；远端实验任务ID未确认，不能声称远端无运行任务。不杀进程、不回滚、不切换脏工作区；没有科学运行需迁移的checkpoint，恢复从完整保存阶段开始。

至少824次家族拟合、至少4次Pro，早期完整账未知。最新AAII20是80/80（68核心+12独立）用尽；6新页面+2find保守8次、超原6两次已披露。免费来源阶段24次操作耗尽；本轮0新市场拟合、0Pro、0付费。已耗预算不因同步重置。

禁止重复：AAII极端/风险、PutCall、NAAIM短史、宽度短史、AAII20同数据模型；不换参数追正结果，不把已见历史称全新验证。只有真正新输入、资格变化、定位错误、冲突证据或明确授权才另立版本，保留旧合同/锁/成绩。失败（缺周预检、写入隔离、算术复核、中文Git路径清单等）引用原raw及verification，不删历史。

## 数据与仅本地材料

数据缺口清单：成果分支docs/progress/sentiment-factor-research/artifact-locations.json。行情CSV/Parquet、缓存/旧模型输入和大资料不上传；模型权重/tokenizer不适用，年度统计系数不是上线许可。旧系统待升级两项review/version5仅为保存回执，未用户验收，本轮不写仓外数据库。

- 仅本地，远端不可完整复现：docs/archive/handoffs-plans/sentiment-remote-handoff-2026-10-03/artifacts/task-payload.tar.gz；12,945,754字节；SHA26bc33439993d9d2312052ed6f4e395b3bf81e7513380886582dbd7a78457c03，含657必要小材料，未进入普通Git。
- 仅本地：docs/experiments/raw/sentiment-open-source-input-2026-09-30/inputs/boris-stooq-2017.zip；515,591,518字节；SHAd9317c8fb2d63b9b00db5f933b6c9639d2bf7ea3b918169bb5cec5903dce85a1。完整路径以artifact-locations为准。
- 约26.06MB本机价格矩阵/26.04MB调整矩阵、宽度JSON等仅本地；尺寸、历史/当前SHA在清单。无授权远端资料存储位置；数据许可/时间资格未知处继续未知。登录/令牌/cookie/私钥不上传。
- 原共享工作区其他未提交代码/14个本地功能提交仅本地，不属于本任务成果，不能用此协调记录让别人接管。

## 本轮检查与接续最小操作

已通过：指定remote与工作分支SHA核对；COORDINATION.md完整读取；最新八份已登记任务完整阅读；无部署工作流/已配置pre-push钩子证据；本任务科学成果已远端验证。待本轮完成后补：AGENTS增补保持原文字节、仅本任务协调路径、协调推送后完整SHA与任务内容读回。

失败/未运行：此前Git中文路径报价导致候选清单比较失败，已纠正，不影响科学成绩；本轮不运行训练、全回测、市场模型或生产服务。Linux/全服务、原E收益依旧未验证。协调树旧hygiene会有三白名单误报，bootstrap已把兼容检查器留其成果分支；本线不重复开发/覆盖该检查器。

最小接续：先fetch最新coordination/lei，读规则、本记录与新增相关任务；核对成果分支实际ref、输入SHA及原累计账，再仅继续缺失输入资格工作。尚无合格输入不运行旧模型。本版新增唯一任务登记、当前归属与科学阻塞、准确远端成果及未交付数据；历史进度/科学证据原样保留。状态文件自身commit由git log --路径定位，不无限补写自身SHA。

首次普通协调推送被拒non-fast-forward，原提交eb94c8f3a57f79ff7f46e9552c9df16c123de4ca仅本地，未冒称同步。已fetch并阅读d5f4c68459a1fbd40cf89e6813a15982f830bc31新增阶段：外部工具只读依赖核查、观察地图文档完成及远端引用核对，无本线问题/模块冲突，规则未变。改用GitHub单文件创建接口，只提交本任务记录，避免整树覆盖并发更新；其他记录均保留。
