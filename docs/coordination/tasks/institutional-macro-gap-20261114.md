# 机构宏观与择时公开框架及系统缺口

- task-id: institutional-macro-gap-20261114；owner: 01a1d305-954b-7ed2-9dc6-430491131d6c/root；status: active / iterative_research；scope_released: false；updated_at: 2026-11-14 Asia/Shanghai。
- checked_coordination_sha: c7e990649d7f247768cc6db7199cfdb5278ec513；已读COORDINATION、research-dispatch-controller、cross-market-risk-context-20261102、market-increment-map-20261102、gemini-factor-fit-20261104、market-observation-panel-v2-20261109；旧成果及预算封存不重跑。
- 目标：以机构公开材料对照系统现有宏观、压力、趋势及宽度，判断缺口及已知交易证据；针对已存ALFRED两个金融条件历史发布版本，只做NFCI与ANFCI可观察差异的描述性资格比较。无资金操作和预测回测，已有策略研究只引用。
- 数据与实验合同：2011-05-25—2026-10-21已存两个历史发布版本，单版本选最新共有观察周，同周零线之上/以下及最近4周变化符号比较，0单列，缺历史时排除；日级发布版本，至少次交易日后可得，不认定盘中。四周变化使用同一版本内相差28自然日的历史观察；不读预测标签、不根据结果选阈值。保留年份与连段，相关仅同期描述，非预测增量或交易。先写合同，再一次计算。
- 唯一写者root：docs/experiments/institutional-macro-gap-2026-11-14.md、docs/ops/work-progress/institutional-macro-gap-20261114.md、独立外盘run；不写共享前端、registry、策略、交易或生产。隔离只读本地与公开来源代理已派；所有实际外部检索总计上限6次，含失败；已用6，Gemini独立答复按用户请求。
- 基础 codex/factor-unit-research-20260915@18e64fa632dba5dbad0e5fcae09b4ccc75f119a9，dirty worktree保留；成果将仅本地，未部署。验收原始指纹、分母、独立抽样与结果解释；资料或时点不足则仅交描述性边界。

## 追加一项可执行的有界增量研究

既有ALFRED历史版本及SPY含分红调整日价均可复用，且用户要求结合系统看择时/宏观；追加检验“美国金融条件ANFCI能否改善下一季度回报判断”，不改原描述合同。已有数据和历史已见，探索性，不是账户回测。预测比较采用公开日级版本后一交易日收盘可得，至随后63个交易日收盘回报；基准固定为历史63/252日回报、63日波动及NFCI；候选再加ANFCI，另列训练均值对手。2015起按年度向前训练，训练标签须在评价年开始前成熟；同一评价样本、每年训练内标准化与固定岭系数0.001。主指标MSE和两模型配对差，按连续26周块重采样给95%经验范围；保存逐期/逐年反例。新合同与输入指纹先行、仅一批、不调参数、不新取数、不改生产/交易；受资料不足或质量不合格则阻断效力结论。

## 结果、验收和释放

- 新报告 docs/experiments/institutional-macro-gap-2026-11-14.md 与进度 docs/ops/work-progress/institutional-macro-gap-20261114.md 仅本地，未提交或部署。来源映射与已有指标去重、旧绩效和反例见报告。原策略原件指纹未变。
- 801发布版本同期描述：水平异向117次共17段，四周变化异向180次、57次至少一侧零；只描述不同，不是预测增量。
- SPY已见历史固定季度回报预测：2015-01-02—2026-07-16，600个评价日，价格+NFCI MSE 56.693，加ANFCI 61.056，均值对手47.025。增量−4.363百分点平方，26周块经验范围[−9.690,−0.118]，7年改善5年变差；非独立未来证据，不是账户交易效益。完整合同、结果、源指纹、逐行目标与抽样模型独立审阅见 /Volumes/win+mac通用/LeiSignal-新实验结果/institutional-macro-gap-20261114/institutional-macro-gap-20261114T000951-8c2541e0a5b5/。
- 两次Gemini 4 Argon高请求均未取得正文，其中一次刷新回到空白对话；不宣称有效回复。累计公开来源6次，描述1批、预测1批，无新行情、账户、生产、交易、删除或强推。实验路径与报告写入结束并释放；缺盈利预期完整版本、中国信用口径及未研究风险用途保留为边界。

## 用户要求Gemini多轮联合研究：接续登记

用户明确要求以批次交由 Gemini 4 Argon 高深度探索、返回建议与下一方向、由主控核原始证据并继续研究、再交回复核。已向此前有可读回答的网页对话实际提交第一批问题；上两轮无正文失败保留。优先核盈利预期变化和中国信用结构的现存资料及此前研究；旧6次来源、描述批和预测批账本不清零，旧研究结果不重跑。研究任务必须等待Gemini实际答复才声称跨模型完成。

主控唯一写：现有报告 docs/experiments/institutional-macro-gap-2026-11-14.md 的新增接续章节和自己的 docs/ops/work-progress/institutional-macro-gap-20261114.md；隔离只读资料代理一名。先查当前版本、来源、预算和旧冻结；新增实证须另登记合同、消耗与产权。不得把姓名、账号、持仓、敏感数据和凭证交给外部服务，不改资金、策略、生产、部署或共享代码；需使用新公开来源时先确定独立子问题与本题累计预算，不能改名重置旧研究。checked_coordination_sha: c933a3ae5e48c3bfaefac93288da1bb575b77570，已读COORDINATION、自身及相关旧任务；唯一范围与他人无写入重叠。

## 用户更新：研究建议与指标联动

用户最新明确只做资料研究、与 Gemini / 网页 GPT 多轮讨论和建议清单，提交用户审议；停止新增实验、回测和指标实现，不更改生产、策略或交易。此前已完成结果只作受限历史证据。唯一写入仍为原报告和进度；只读代理核查现有指标及组合反例。已用原阶段公开来源 6/6、来源资格阶段 6/6，分别保留账本。网页 GPT 页面读取超时，尚未获取正文；Gemini 两轮有正文，第三轮已提交但未读到结果。任务保持 active，待跨模型迭代及建议审议材料。


## 用户批准观察补充及首页紧凑图：开始首批实现 2026-11-15T09:17:16+08:00

- task-id/owner沿用 institutional-macro-gap-20261114 / 01a1d305-954b-7ed2-9dc6-430491131d6c/root；status active，scope_released=false；checked_coordination_sha=c742eabf50609656d6bb5c8f637c712d2807d8d9。已读 COORDINATION、research-dispatch-controller、原任务、market-observation-panel-v2、douyin-yangtuoshen、breadth-reading-aid、cross-market-risk-context、microstructure、trae-observation-integration、trae-sector、erp-observation-clarity、focus-stock-universe 最新相关记录；涉及路径已释放，不覆盖他人已有改动。
- 用户认可五项候选、紧凑中美总览必须保留真实小图，并要求 GPT Pro 重新判断 COR3M 位置；原会话本轮回复已实际获得。用户授权观察层补充和首页布局；不授权新回测、交易、生产策略改动、部署、删除或强推。之前文献/来源预算和封存结论不清零。
- 本批唯一写者 root：web/src/components/market-observation-alerts/index.tsx、style.css、IndicatorThumbnail.tsx、MiniTrend.tsx、CompactOverview.tsx、compact-overview.css、CompactOverview.test.mjs；docs/superpowers/plans/2026-11-15-market-overview-compact.md；docs/experiments/market-homepage-review-2026-11-14.md 追加本轮评审；docs/ops/work-progress/institutional-macro-gap-20261114.md 追加进度。相关未列路径只读；若需新增写入先更新本记录。
- 现状：源码基线 codex/factor-unit-research-20260915@18e64fa632dba5dbad0e5fcae09b4ccc75f119a9 加共享脏区；5173 为本地开发服务，既有文件先按字节备份并保护；仅本地未部署，远端无本任务源码成果。
- 本批目标：增加中美四项核心紧凑历史图总览，保留现有用户自选及完整25项入口；真实末值、日期、参考线、缺项和股票池清楚呈现。科创仅标既存 2026-11-12 固定名单快照，盈利修正未合格保持未知；COR3M 已存在，按实际数据日期呈现并可进详情。五项其余缺失数据另分阶段，不以占位冒充已补。
- 验收：有意义的用户选择/缺失数据测试先红后绿，相关既有回归、TypeScript与不覆盖dist的构建；内置浏览器桌面页面核对1280宽下图表和切换、原自选不被重置。先登记推送并读回，再动共享前端；不做金融效益实验或新增数据下载。


## 补充精确写入范围 2026-11-15T09:25:12+08:00

- checked_coordination_sha=1487de332d80bc759cf7056f850719ae1a80d694；继续唯一写者 root。用户已要求把首页截图交给 GPT 审阅，增加本地验收截图 docs/ops/institutional-macro-gap-20261114/home-overview.jpg；只读连接器可读取该图，不上传仓库、账户数据或凭据。
- 实页核对发现 COR3M 预览简介将对象笼统称为标普成分股；增加 web/src/components/market-observation-alerts/indicatorCatalog.ts 与 web/src/components/market-observation-panel/model.ts 的准确表述范围，写明 Cboe 以市值选出的50只成分股与指数期权定价，原数据和规则不变。两文件所属前述 owner 记录均已释放，先备份原字节。
- 本次其余范围、数据预算和无生产交易边界不变；当前总览及五项缺口仍在验收，未声明完成。
