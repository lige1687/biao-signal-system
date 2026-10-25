# 总览指标解释与样本身份补充 2026-10-25T23:26:46.853421+08:00

- task-id focus-stock-universe-20261024；owner 01a16bd6-3661-7cd3-a2ff-5cadfa181605/root；status active；scope_released false仅本轮明确范围。checked_coordination_sha 5ae490e0c9b5c8afe58fcc8c4f20e44a91525d02；checked_at 2026-10-25T23:26:46.853421+08:00。
- 已读COORDINATION1.1、self、market-style-observation-20261020、investor-workspace-simplification-20261012、research-utility-review-20261012、investor-observation-map、research-dispatch-controller。market-style工作台范围明确释放；其他现状无本轮同块活跃写者。root集成、助手只读文献及指标口径，保留既有脏区。
- 用户要求研究总览ICIR/RankIC参考与20日动量universe清楚；追加原抖音是否对齐、是否权威有效、外部情绪模型增量。服务研究解释层；report_only核既有来源，不新回测、改模型参数或策略、不宣称原模型复现。
- root写web/src/pages/factor-workbench/FactorWorkbench.tsx、该目录新增metric-reference组件及样式与必要纯函数；自己的docs/archive/handoffs-plans/focus-momentum-display-20261025/metric-reference/、原progress；新docs/experiments/factor-metric-reference-2026-10-25.md、registry本键及INDEX本行。现有静态数据、后端、源报告/冻结研究全部只读；UI不创造评级阈值。
- 验收已选dataset/pool/公式/未来收益期与静态来源一致，Spearman和不年化标明；数值参照不冒充学术及格线；区间与样本数可见，定义来源可点。检查两池切换、单因子、移动端和原观察入口，构建、相关测试、归置；仅本机代码，未自动提交/部署。
- 两原策略文件SHA沿已核df92d85b…b20/85e0e327…903且本轮实核未变。内部余16GiB，小代码/回执预计<2MiB，无大结果。阈值资料代理实报5调用16请求条目，超默认6，原样留账并停止该分支搜索；新增情绪模型问题最多6来源条目、复用先行。

---

# 当前：价格投影纠正与阶段顶底有界检验交付 2026-10-25T23:14:39.122374+08:00

- task-id/owner沿原；status completed仅本次自有UI与三A股目标历史用途；scope_released true。US独立focus/板块自身模型核心输入、原作者公式及真正未来验证仍未完成，未伪造效果。checked_coordination_sha d2fae4903a892316ce869a8c9f0740f96dec757a，最后fetch无他人增量。
- 用户最终指定价格投影=日期横轴、上方价格下方模型。默认视图已改，沪深300/上证价格与模型严格同日，光标/缩放/负值区间联动，1/3/5年/全部；共同截止2025-12-31、价格资料截至2026-10-23分列。全部从首个有效重合日2015-01-05开始。9前端测试、最终tsc/Vite、归置、375px无溢出及真实页面控件验证通过。
- 用户进一步澄清要看阶段预测顶底，期限委托AI。新报告docs/experiments/focus-momentum-turning-points-2026-10-25.md；固定旧300股A信号、三指数普通价格、20日主与60敏感性，预先冻结6警报规则/对手。独立确认顶底只作未来判卷，提前、同日、滞后分开。1核心计算及3核验、3资料请求，旧家族1核心1审计6资料保留，不调参。
- 20日主例沪深300：零线39警报5提前命中，覆盖5/30底部；增量底部Brier0.063896→0.064459，未见跨对象/期限稳定优势。科创低分位小样本线索保留；60日科创仅1.35时间块，区间不作可靠推断。普通指数不是全收益/ETF账户。无交易采用。
- 6合成测试、独立39事件/20随机标签/20极值/72训练记录/82误差汇总复算通过；原core-v1及原模型静态包SHA未改。报告已登记本键、INDEX本行、progress更新，工作台报告链接已实际点击读回；报告§8及raw/controller-review.json为主控书面验收。最终截图/回执docs/archive/handoffs-plans/focus-momentum-display-20261025/price-projection-correction/，研究raw/state.json闭环。
- 仅本地工作分支codex/factor-unit-research-20260915，原base18e64fa632dba5dbad0e5fcae09b4ccc75f119a9加既有脏区。源码报告未提交推送，远端不可复现；仅本题协调元数据push。无删除、外部写入、后台/生产规则/账户改动、安装/大行情下载/自动化。临时QA页已关闭，用户原页保留。范围内无待执行P0，恢复条件为新合格输入/原式/未来独立期。

---

# 当前：焦点动量阶段顶底用途新增检验 2026-10-25T22:54:22.679549+08:00

- task-id/owner沿原；status active；scope_released false。用户明确补充创业板、科创、美股并澄清要看“阶段性预测的顶底效果”，时间尺度授权主控判断；这是新的用途问题，不重算旧20日收益研究或改变旧结论。
- checked_coordination_sha aa7817f0d623023fa77e7a96d9bad0ef9ffd164a；此前相关owner/协调规范已读，本次fetch无其他增量。新增自有范围 docs/experiments/focus-momentum-turning-points-2026-10-25.md、raw/focus-momentum-turning-points-2026-10-25/；registry仅本键、INDEX仅本行；原progress与本组件投影验收范围继续。
- 研究主问题：收盘可见焦点读数能否同日或提前提示后续确认的局部顶底，是否超过指数自身涨跌/波动和同池动量。20交易日为主、60日预定敏感性；顶底按左右固定窗口事后判卷，绝不把未来确认的极值当即时报警。全量误报、漏报、提前/滞后、途中不利变化、时期和相对基线增量一并保留。
- 输入复用已展示的固定300股daily_features及已存在指数缓存；沪深300主参照，创业板指/科创50按用户新增作对象对照；不是对应板块自身股票池。科创50发布前回算排除。US独立focus核心输入未合格，本分支不伪造效果。
- 旧家族已完成1核心+1审计、6资料请求保留；新用途至多1核心+3必要核验、6资料请求（当前1请求已用）且不参数搜索、不安装依赖、不抓大行情。预计新小产物<10MiB，内盘17GiB以上；仓外只读、不改旧冻结、不改交易/后台/账户、不删除。root唯一合同/报告/登记/接线；代理输入准备/计算各限定新raw不同文件，审查只读。
- 价格投影代码已9测试、构建和归置通过，真实页面默认上价格下模型、共同日期验证进行中；旧静态模型资产不变。

---

# 当前：按用户澄清改为同期价格上下投影 2026-10-25T22:40:48.942300+08:00

- task-id/owner沿原；status active；scope_released false仅web/src/components/focus-momentum/与原docs/archive/handoffs-plans/focus-momentum-display-20261025/、原progress；不触及其他组件、基本面原页或策略/API。
- 用户已明确选择“与宽度一致：日期横轴，上方价格、下方模型值”，并说“继续哈”；此前横轴模型值散点不是这次所需主图。默认改为同日价格和焦点动量上下曲线、联动光标，零下日同步投影；既有预测结果只作次级研究依据，不冒充价格。
- checked_coordination_sha 1d7e6d632f292e86bf67d15cbe5c669a984c759c；checked_at 2026-10-25T22:40:48.942300+08:00；已读COORDINATION1.1/self/market-style-observation-20261020/investor-workspace-simplification-20261012/research-dispatch-controller，远端其他改动仅downside成员/数据交付。现有BreadthComparison只读复用图形口径，原owner范围无同写。根策略文档SHA与此前确认相同，服务独立市场叙事展示层。
- 实现采用基本面已有overlayHistory价格接口（普通价格指数），严格按同日和模型覆盖对照，来源/资料期分别写清；不把已有全收益研究点位或未来收益当普通价格。数据可用性读回中，缺口显式。美股自身模型缺口保持，不将A模型代用美股。
- root唯一写view.tsx接线和原记录；实现代理只获新price-projection.tsx/data.ts/test路径及本组件CSS（派发后按精确新文件细分）；review代理只读。预期小产物<5MiB，内盘12434915328字节；无新行情采集/效果实验/规则/账户/外写/定时/删除/生产提交，外盘仍只读。
- 验收：日期轴、价格点位/动量百分比、严格对日缺值断线、同期阴影无前视、历史日期不冒今日、1/3/5年与全期、真实桌面/窄屏、相关测试/构建/归置。工作分支/base沿原加既有脏区，仅本地代码，远端不可复现。上轮验证保留，新更正另存回执不覆盖旧验收。

---

# 当前：焦点动量首页直读与A股效果映射接入完成（本地） 2026-10-25T18:36:34.227175+08:00

- task-id focus-stock-universe-20261024；owner 01a16bd6-3661-7cd3-a2ff-5cadfa181605/root；status completed 仅本轮已具数据的展示；scope_released true。美股映射/当前日数据仍未完成，原因是缺合格输入，不假称全市场实时观察。
- 用户明确纠正首页要直接看模型值，并要求横轴为模型值的A股/美股映射及金融含义。已将初始工具栏入口替换为首页“市场与情绪观察”数值卡；历史9.83%、零线上方、前日变化及同池/上涨比例/集中度，与历史2025-12-31、今日未知同屏。因子工作台有总览摘要与市场观察视图，默认数值映射，可切时间走势。
- A股映射复用冻结weekly表：沪深300/中证1000全收益各560共同周，横轴focus、纵轴后20交易日涨跌；共同窗口2015-01-09至2025-12-12、最晚结局2026-01-13；同频总体均值金线为+0.64%/+0.79%，保持相同坐标；未拟合/调参/新增效果实验。美股缺逐股历史池、成交额及复权价格，明确空状态，未拿现今巨头/ETF/A股替代。
- checked_coordination_sha 9a71b79f46bd0cb927cd5a4e9c85bf62a4599108；checked_at 2026-10-25T18:36:34.227175+08:00。增量downside-sensitivity-universe在自身14234成员链范围，与本任务展示无冲突；既有工作台/首页owner未新增范围。唯一写者与文件沿开工声明，新增mapping.tsx仍在自有组件目录。导出脚本最终路径scripts/archive/export_focus_momentum_observation_20261025.py（归置要求）；无scripts/research留存。
- 实际验证：4后端+4前端测试通过、最终tsc/Vite构建exit0（原有大chunk提示保留）、归置exit0；HTTP包与本地SHA一致，原daily/summary/weekly三份SHA未变。真实浏览器首页直读/因子摘要/两目标映射/US空状态/历史范围/报告/金融含义/375px无横向溢出验证；两助手独立只读复核无实质问题。
- 产物：docs/archive/handoffs-plans/focus-momentum-display-20261025/verification.json（命令完整输出、12个代码/数据文件SHA、来源核验、截图、相对开工快照精确diff）；progress沿原。静态资产1017813字节、SHA4a14051bd1ac5b40a94ae957a3982dfbe6110c18b0a360307eb0b0eeb1106f77。
- 边界：固定300股独立定义，原式/全A/实时/美股/账户效果未升格；观察不接入道路/买卖/情绪灯。0新增取数/新实验/新自动化/费用/删除，无8000重启或8193服务接管。金融含义说明分开价格强弱、参与面与成交集中，集中度不是净流入。
- 当前工作分支codex/factor-unit-research-20260915及base18e64fa632dba5dbad0e5fcae09b4ccc75f119a9加既有脏区；源码仅本地未提交/推送，远端不可复现。此提交仅本任务协调摘要，不包含其他任务或代码。

---

# 当前：焦点动量接入日常看盘与因子工作台 2026-10-25T18:13:38.072085+08:00

- task-id focus-stock-universe-20261024；owner 01a16bd6-3661-7cd3-a2ff-5cadfa181605/root；status active；scope_released false仅下述新增展示范围。
- 用户本轮明确提出把焦点动量做到平常主要看板和因子看板；采用现有研究结果作为独立市场状态观察，不改买卖/情绪灯/策略。主看盘紧凑入口，因子工作台独立市场观察视图，共用冻结数据展示包；今日值未知、固定历史300股、截至2025-12-31与美股未评价必须可见。
- checked_coordination_sha 9f1993e84776778a8e867a345dc660c4236f35be；checked_at 2026-10-25T18:13:38.072085+08:00；已读COORDINATION1.1/self/research-dispatch-controller/research-utility-review-20261012/investor-workspace-simplification-20261012/market-style-observation-20261020/sentiment-factor-research相关当前记录。market-style与investor最近范围已释放；只在WorkspacePage顶部和FactorWorkbench导航/新视图插入，不动旧判断/曲线/进度接口，未发现同块活跃写者。
- 主仓codex/factor-unit-research-20260915，base 18e64fa632dba5dbad0e5fcae09b4ccc75f119a9加既有脏区。此次结果仅本地未提交、远端不可复现；不拿基线代表工作区。
- 具体写范围：新src/lei_signal/market_context/focus_momentum.py、scripts/research/export_focus_momentum.py、tests/unit/test_focus_momentum_observation.py、web/public/research/focus-momentum/、web/src/components/focus-momentum/；主控仅web/src/pages/WorkspacePage.tsx与web/src/pages/factor-workbench/FactorWorkbench.tsx插入及同工作台必要样式。自己的docs/archive/handoffs-plans/focus-momentum-display-20261025/与原progress。现有factors/sentiment API、App、vite、交易策略、原冻结研究全部不改。
- 预计分工：子代理universe_evidence写新导出器/测试/JSON；root写新组件和上述两个页面；model_source_hunt只读UI验收。后续按此范围真正派发，不把准备视为实现。
- 验收：源CSV/summary指纹绑定、空缺/篡改/日期语义测试、TypeScript与构建、真实主看盘到市场观察链接/图/日期/报告与移动宽度，来源冻结不变。静态展示包不依赖重启8000或新常驻服务。
- 上一研究已完成：docs/experiments/focus-stock-momentum-evaluation-2026-10-25.md；1冻结核心批次/1独立审计/6文献请求，固定300股独立版本未见稳定正预测增量；原式、全市场、美股与账户效果不升格。本轮0新效果实验/调参/行情下载；复用已冻结证据。
- 依赖：当前全市场实时资料未合格，展示历史状态不伪装今日监测。内盘余量16503504896字节，小产物预计<10MiB；仓外与外盘只读，不删除、不启动自动化、不改目标数据库。

---

# 当前：焦点股动量来源与中美观察用途调研结案

- task-id/owner沿原；status completed仅本轮source_review；scope_released=true仅本题归档项。updated_at 2026-10-24T13:44:03.438620+08:00；checked_coordination_sha 01b71f2366c5e8a96a9644685ba7ea56b12a8bfe；已读COORDINATION/self及已登记六相关task、strategy-account-bridge新增范围，最后fetch无增量，无同写冲突。
- 原来源 https://www.douyin.com/video/7699879945107016969 ，量化舵，2026-10-23 23:06发布；111.27秒原片、完整本地ASR、20关键帧及作者评论已核。作者未公开参数，画面成交额/评论成交量差异保留；逐段最低日圈点属事后选择，98%是同期历史表现比较而非预测胜率。支持保留热门股降温观察，预测/美股迁移/账户改善未验证。
- 本地报告 docs/experiments/focus-stock-momentum-source-review-2026-10-24.md，SHA a808f0dde2e3ad4cec32a86cb2733286e8e0ce9fb4c5653bf4dd4e5acec227f4；同名raw/source-manifest.json列原件/指纹/失败/验收；registry只加本键且保留旧项，INDEX只加本行，progress沿原。两表分别记录原声称性能及相对已有信息未测增量，给中美范围建议和反例。
- 归置exit0，报告/registry/manifest哈希读回一致；PNG首次断言因macOS ._说明文件计入40而失败，排除说明文件后20张通过，未删除。Codex open仅queued。媒体/转录/抽帧约12.67MB在已核外盘，无下载权重/付费/生产/交易/真实收益实验，已关闭本次搜索页。
- 工作分支/base沿原；源码报告未提交/推送，成果仅本地、远端不可复现，协调分支仅本摘要。原身份阻塞已解除；原版完整复现仍需完整定义/逐日底表，自定算法须另立定义，不能冒充复现。无待运行后台，无重跑封存实验。

## 本轮开工与此前历史

# 当前：来源已找到，归档原模型核验及中美观察范围

- task-id focus-stock-universe-20261024；owner 01a16bd6-3661-7cd3-a2ff-5cadfa181605/root；status active；scope_released false仅本轮自有条目；updated_at 2026-10-24T13:39:33.990517+08:00。
- checked_coordination_sha 4367807a021d13407dd08556ff1eddff04313097；已读 COORDINATION/self/research-dispatch-controller/market-observation/sentiment-factor-research/market-style-observation-20261020/downside-sensitivity-universe-20261023/investor-observation-map；最新strategy-account-bridge仅已有因子组合，不接管彼此。准备同步时远端引用已变，首次基线断言停止无写入；已读差异后恢复。冲突决定：root唯一写本题来源报告及登记键，不改其他任务数据/报告/生产。
- 范围：docs/experiments/focus-stock-momentum-source-review-2026-10-24.md、raw/focus-stock-momentum-source-review-2026-10-24/小清单、registry.json仅本报告键、INDEX.md仅本报告行；自身progress和输出计划。验收：准确原出处+日期、ASR/画面/评论核验、解释事后圈点、A美范围和观察增量边界、归档读回/归置。
- 原视频 https://www.douyin.com/video/7699879945107016969 ，量化舵，页面发布时间2026-10-23 23:06，111.27秒。原片/ASR/20帧已读，作者拒绝完整公式披露；评论成交量与画面成交额有歧义，不编造参数。旧blocked身份问题已解决，原公式复现和预测仍未成立。采用research-closure/lei-lowfreq-research/current-standards；没有新技术定义、收益实验、拟合、交易规则或生产改动。
- 外盘UUID DEBA1C85-6059-3865-B50A-A8EE1F80E4D9核对通过，64MiB计划、1MiB本地预算；资料在 /Volumes/win+mac通用/LeiSignal-新实验结果/focus-stock-universe-20261024/focus-stock-universe-20261024-20261024T133543-24c706c99401/result/ 。视频专用API forbidden不重试，实际页面媒体+本地已装ASR读取成功，无安装/权重下载。
- 工作分支codex/factor-unit-research-20260915，基础18e64fa632dba5dbad0e5fcae09b4ccc75f119a9；研究成果仅本地未提交/推送，只推协调元数据。两Sol只读证据助手结束，root独立核关键帧；效果运行0。下一步完成来源报告及两表，释放自有归档范围。

## 历史（以下旧阻塞已被本轮来源发现解除）

# 焦点股模型：中美股票范围与观察用途核对

- task-id：focus-stock-universe-20261024；owner：01a16bd6-3661-7cd3-a2ff-5cadfa181605 / root。
- 状态：blocked / model_identity_missing。股票范围建议可交付；原模型公式、零线与效果尚未核实，研究未结案。
- 日期：2026-10-24，Asia/Shanghai。工作分支 codex/factor-unit-research-20260915，基础 18e64fa632dba5dbad0e5fcae09b4ccc75f119a9；本记录仅本地，未提交源码。
- checked_coordination_sha：623b195bb4cd28c17a4170c365b650d3b3778875；checked_at：2026-10-24T10:59:44+08:00。
- 已读：COORDINATION、research-dispatch-controller、market-observation、sentiment-factor-research、market-style-observation-20261020、downside-sensitivity-universe-20261023、investor-observation-map 的相关现状。唯一写者 root，仅本记录与自己的协调摘要；相邻资料采集、因子工作台及旧情绪研究保持原负责人，不接管、不改冻结结果。

## 本轮问题与边界

用户询问“冰点焦点股东然模型”，认为可能选择成交集中的龙头，想了解 A 股、美股股票范围与观察用途。任务先确认身份，再评价适配及额外信息；不修改交易规则、生产界面或原策略。不把候选解释当作原模型。

采用 research-closure、lei-lowfreq-research；本轮为定义与已有证据核对，真实市场效果实验 0、拟合 0。已发准确名称/页面链接澄清，尚未收到回复。公开发现请求 6 次（3 次工具调用，分别 2/3/1 个查询），未定位可靠原始公式；失败搜索保留为本轮成本，不据此声称模型不存在。用户需提供的核心资料是原模型准确名称或来源，而非替 AI 设计方法。

## 已确认与建议

1. 仓库检索未找到对应“焦点股”模型；`src/lei_signal/market_context/market_mood.py` 的 cn_mood 是融资变化与板块价格代理，明确不合成为冰点，与待查模型不能混同。旧冰点简化复现也不能借用为本题效果证据。
2. 条件性建议：若原定义确为成交额前列股票的动量，A 股主观察范围用沪深普通 A 股、北交所单列；美股主观察范围用美国主要交易所的本土普通股，境外发行人/ADR 单列，排除基金、杠杆产品、优先股和权证。成交额排序比直接按成交股数更适合衡量交易资金集中；确切窗口、选取数量与汇总公式待原定义确认。
3. 全市场焦点与大盘焦点分开。沪深300/中证1000、标普500/罗素2000可作预设分层对照；纳指100是独立适用范围。不能用少数大股解释全部市场，也不能用今天名单回填历史。
4. 观察至少分清：焦点股价格变化、其相对整个股票范围的强弱、其成交额占全范围的比例。低于零若是涨跌幅只说明下跌，若是相对涨跌只说明落后，若是标准化分数只说明低于基准水平；任何一种都不能仅凭负值判为极端低迷或未来反弹。
5. 拟评价用途是为宽基/ETF低频复盘区分少数热门股支撑、普遍转弱及修复是否扩散。独立增量须与指数自身涨跌、全范围涨跌和上涨家数比例比较，市场方向/反弹概率/提前时间/少亏少赚目前均未评价。

## 现有资料核对与更新

- `docs/experiments/common-universe-acquisition-2026-10-24.md`、raw/coverage-manifest.json 为早间13池来源目录，不能当完整历史回测资格。
- 已另外核新 `docs/experiments/raw/universe-history-completion-2026-10-24/controller-membership-admission.json`（10:44+08）：中证1000已有2022-12至2025-11的36个月成员获原负责人接受，中证2000已有2023-08至10三个月；不能沿用早间报告声称完全没有历史成员。该文件仍明确完整价格/退出/分红资料未合格、完整历史股票池未完成、效果运行0。
- 未读取外盘大原件、未重新取数。storage于10:59+08核内盘余量20,176,203,776字节，外盘身份正常；本轮仅新增小记录，无大结果。

## 委派、核验与恢复

Sol medium助手 universe_evidence 仅只读早间13池报告及小清单，write_paths=[]、network_allowed=false、max_agents=1。root独立核原代码及新增历史成员准入，纠正助手仅依据早间快照的覆盖限制；未将资料核查当科学性能结论。实际模型费用未知。

恢复唯一必要输入：准确模型名、页面链接或原公式。取得后先绑定原公式、股票筛选、价格口径、输出单位与可用时点，再决定是否已有同题效果证据或需有界检验。当前未建立新实验合同、不登记已结案报告、不修改系统目标数据库或规则、不创建后台任务。归置检查与协调推送读回由本轮工具回执确认。


## 交付前协调增量

2026-10-24T11:03:00+08:00：共享远端引用在准备同步时已从623b195变为c7f0ace93ffbeba4dfd5110d5a503600dd3ff0de，首次基线断言及时停止，未创建提交或修改索引。已读唯一变化downside-sensitivity-universe-20261023：本批资料补采已结案，成员36/3月结论不变，完整历史仍未完成。实际checked_coordination_sha更新为c7f0ace93ffbeba4dfd5110d5a503600dd3ff0de；范围不冲突。

协调摘要引用本地进度 docs/ops/work-progress/focus-stock-universe-20261024.md；scope_released=true，无活跃代码写入范围。归置检查本轮退出0。此协调副本已包含现有结论和阻塞；未提交源码或归档实验。
