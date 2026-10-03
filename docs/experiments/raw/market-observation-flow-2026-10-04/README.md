# 本轮接续与证据入口

先读报告 `docs/experiments/market-observation-flow-2026-10-04.md`、original-goals.md、source-ledger.json、validation.json、restore-validation.json，核manifest/SHA后读本任务最新coordination记录。发布源码codex/investor-observation-map-progress-20261004；原task/investor-observation-map-progress工作树保留，基础63eaa0be1ce36b844c2d70792fdc917eb35f0234，设计69ec46e3（完整SHA见manifest）。不是接管，原负责人继续。

恢复：在任务分支仓库根执行`cd web && npm ci && npm run test:market-observation && npm run build`。npm ci锁定安装尚未实际验证，不能把本机复用node_modules当跨机通过；真实图表还需要同版本原API，默认代理127.0.0.1:8000，可用LEI_API_PROXY指定批准服务。预览`npm run dev -- --host 127.0.0.1 --port 5185 --strictPort`。不要重启/杀共享API或同时写同输出。

已完成工程：四组同数据图/摘要/不一致，频率和官方口径差异透明，连续宏观追问。来源续核paused：访问账按20请求项入账，原登记6次含糊按批计算，应承认超限，不追加；旧预算和实验不重置。FINRA/CFTC/盈利不是已接入数据。PE官方历史单点与第三方不一致须先核原供方/真实接口版本，不能替换全史；本文不能授予生产取数、商业许可或历史预测资格。

本地未入Git：rates-input.local.json（只读接口原样）、preview-combination.local.jpg（公开市场预览）、restore-local-*（本机独立恢复副本）。位置/大小/SHA见manifest；复制不迁移进程/登录态/依赖。无权重/数据库/密钥新增，未复制私人策略原件。旧截图和恢复副本原样保留。

不要重跑：QQQ/VXN、宏观18/18、情绪AAII/NAAIM金融结论及旧冻结基础阶段。只在新输入/源码改动影响旧结论时做对应最小验证。本轮0新金融实验/模型调用/训练/付费；实际用户理解和线上收益未测量。

待解：来源发布/修订和许可、中国完整日历、盈利/净流量等缺口；系统待升级草案upgrade-goal-proposal.json尚未实际写服务端台账，等明确写入授权后先再检索避免重复。未解决输入用途不要凭软件complete解锁。
