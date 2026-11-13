# 抖音羊驼神研究与科创50/100宽度观察试做

- task-id: douyin-yangtuoshen-20261113；owner: 01a1d305-954b-7ed2-9dc6-430491131d6c/root；status: blocked / core_source_access；scope_released: true；updated_at: 2026-11-13 Asia/Shanghai。
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
