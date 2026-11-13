# 抖音羊驼神研究与科创50/100宽度观察试做

- task-id: douyin-yangtuoshen-20261113；owner: 01a1d305-954b-7ed2-9dc6-430491131d6c/root；status: blocked / partial_sources；scope_released: true；updated_at: 2026-11-13 Asia/Shanghai。
- 目标：按用户澄清只逐条看作者与投资模型、顶底及观察有关的视频；并制作科创50与科创100内部均线宽度的本地观察试做。复用已有快照、保留独立因子研究和生产/实盘边界。
- checked_coordination_sha: 6d05c778b9e4e96364b0c125abf3d275582e5584；已读 COORDINATION、research-dispatch-controller、market-observation-panel-v2-20261109、breadth-reading-aid-20261101、trae-observation-integration-20261108。相关已登记前端阶段均已释放；不接管其他任务。
- 工作树 codex/factor-unit-research-20260915@18e64fa632dba5dbad0e5fcae09b4ccc75f119a9，叠共享本地未提交修改；成果尚未提交，远端无法复现。
- 唯一写入：web/src/components/market-style/BreadthComparison.tsx（仅增加观察入口）、web/src/components/market-style/StarBreadthSnapshot.tsx、web/public/research/star-breadth-20261113.json；自身研究与进度 docs/experiments/douyin-yangtuoshen-2026-11-13.md、docs/ops/work-progress/douyin-yangtuoshen-20261113.md。保留已有文件字节备份及无关修改。无代理并发写这些文件。
- 数据：11/11官方成分快照，试算11/11—11/12、MA20/50/200，前复权价，严格同一交易日窗口、缺失不填，标明覆盖与单次快照；原始外盘运行在已验证外盘。仅观察，不把当前成分回填当历史在时成分、不宣称自动更新、不生成买卖规则。验证源码、数据计算、真实网页和日期/缺失提示；样本效果未评价。
- 历史已打开21条相关视频的部分片段或AI摘要；全量内容未完成。抖音媒体403仍需解决；mlx_whisper及登记模型现已核实存在，不再沿用旧报“本机无Whisper”的错误。Gemini 4 Argon高思考评审进行中。
- 当前仅登记/只读预研与研究型试算，0策略变更、真实交易、部署、通知、OKR变更、删数据和强推。

## 本轮交接与释放

- 科创50/100内部宽度为2026-11-12固定快照，已做独立原始数据重算、TypeScript及本地网页验证；不自动刷新，未提交或部署。原始数据、合同、备份保存在已核验外盘，路径详见研究报告。
- 完整相关视频音视频和字幕未取得：详情接口拒绝访问，当前平台摘要不可当原文。后续需要可访问视频或字幕，方可完成逐条整理与模型定义核对。
- Gemini 4 Argon高的两份复核请求仍在生成/搜索，尚无可用答复；旧回答高胜率和固定阈值缺核验证据，不予采纳。
- 本轮路径写入结束并释放；共享工作树其他未提交内容保留。未变更策略、账户、生产、OKR或外部发布。

## 用户要求接续

只读查旧视频完整转写方法、继续尝试其他相关视频和 Gemini 4 Argon 高。允许写入本任务既有研究与进度文档，尤其更正待核实的来源归属；不改其他路径。

## 二次接续交接

- 核实旧维克26条为完整音频转写，旧CDN修复发生于取得媒体URL之后；本次三条不同作品的详情解析均为403。用户澄清范围内仍未完成逐条完整观看，需要可访问音视频或字幕。
- 更正雪球jalp文章与抖音博主的身份归属未经证实，文章与视频模型也不能假定一致。又查看一条科创收藏视频的局部画面和评论，未取得完整内容。
- 两项 Gemini 4 Argon高重新提交后长时间生成且页面消失，未获取可用答复；研究文档保存错误来源与恢复状态。本轮文件修改结束并释放。

## 三次接续：多博主研究

- 用户扩展到量化舵及其他博主，重用已有完整音频与冻结研究，核实一条可访问完整音轨的其他博主视频，并继续 Gemini 4 Argon 高。checked_coordination_sha: 9b2e95531a97b510fe870980db03889535496c12；已读 COORDINATION、research-dispatch-controller、本任务及旧量化舵/维克/HMM研究；相同课题旧结果仅复用。
- 本轮唯一写者root，仅写新报告 docs/experiments/douyin-multicreator-models-2026-11-13.md 和自己的进度 docs/ops/work-progress/douyin-yangtuoshen-20261113.md；不修改共享前端/策略、生产和他人任务。媒体临时文件仅用于已授权来源研究，保留来源及时长。
- 羊驼神源音轨仍受403阻塞，已显示504个作者作品并粗筛，作品主页显示509，差额未知；标题筛选不代替内容完整审查。已有Gemini答复须独立核对。

## 三次接续交接及释放

- 新报告 docs/experiments/douyin-multicreator-models-2026-11-13.md 保存系统对照、旧研究增量和来源限制；B站两条完整音轨转写及抽帧已校验与外盘备份，同名抖音账号身份未经证实。完整相关抖音视频依然受媒体接口拒绝而未完成。
- 沪深供应商历史十日严格同向描述2016-01-15—2026-10-23，共2614个有效日期，输出及复核账本保存在 /Volumes/win+mac通用/LeiSignal-新实验结果/douyin-ten-day-streak-20261113/douyin-ten-day-streak-20261113-20261113T235122-42fa026b9f0e/；事后生命周期非PIT，未验证预测增量。
- Gemini 4 Argon高一轮得到回答并由本地数据核正其中两项过度推断，其他追问未取得可用回答；最新复核仍待页面结果。所有源码仅本地未部署，未修改策略、资金或生产；报告与自身进度完成写入并释放。
