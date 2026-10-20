# 来源与证据层级

日期：2026-09-08。所有原文件或旧对象全文已有本目录复制件或明确哈希；历史对象读取命令与提交元信息见historical-source-manifest.json。

| 来源 | 位置 | 能支持的事实 | 不能支持的结论 |
|---|---|---|---|
| 两repo现行最高规格v1 | sources/sync/docs/trading-spec-v1.md及desktop同名；§4.6第80—82行、§9B第165—172行、§10第192—196行 | 六个月、均线密集、突破/跌回、目标必须事先存在 | 未规定价格区间起点，也未给B初始stop完整计算式 |
| 从旧对象1a321ce取回手册 | sources/handbook-30-videos-1a321ce.md；第3—7行说明整理来源；§3.2第240—250行、§3.5第274—280行、§5.4—5.5第485—518行 | 密集区是横盘箱体；时间/密集程度；进出逻辑一致 | 不是本次直接核过的30期视频原声，也未给watch重置时的边界公式 |
| 同旧对象的v2规格 | sources/trading-spec-v2-1a321ce.md；§4.6第128—133行、§9B第231—244行 | 126根代理、区间最高价、两种入场/失效区分 | bars_in_zone没有定义可执行起点，不能凭此补成唯一算法 |
| 两repo现行v2账本B段 | sources/sync/configs/rules.v2.yaml及desktop同名；第534—567行 | 横盘寿命与当前密集、zone_low_water、每生命周期一次确认 | “整个密集区”没有解释其价格边界是从watch当天初始化 |
| 第八批修正源码 | ../../research-eighth-2026-09-08/b-research-fix/research-package/src/lei_signal/rules/dense_breakout.py；_state_age_series、detect_dense_breakout_events | 已修初始化、原20根容忍；watch当日high/low初始化；失败后只重置观察状态 | 可复现不等于完整原作者体系 |
| 初版B提交8c18934 | sources/dense_breakout-first-8c18934.py；第179—180行 | 早期上沿为此前60根最高high | 不是当前算法，也不定义当前下沿stop |
| 8月10日版本ce7a2da | sources/dense_breakout-ce7a2da.py；第201—202行 | 当时仍使用60根上沿 | 不能证明V2 watch算法从何时最初设计 |
| 9月3日恢复3cdbd9e | sources/dense_breakout-restored-3cdbd9e.py；第241—267、282—329、362—363行 | 该历史对象已具有watch当天初始化/持续水位累计及独立年龄 | 提交说明是恢复工作区代码，不能把恢复日期说成最初发明日期 |
| 第八批candidate-review | 其B-six-events.json、selected-target-checks.json及review | 6个已存在事件、watch日、既定目标和当前上下沿可独立对账 | 不代表替代策略的全部信号 |
| 第八批518880名义日线及actions.json | product-qualification/bars-helper-native/sh518880-nominal.csv | 本产品无该冻结行动集中的分红/拆分，可直接用原价核区间 | 不将零行动推论泛化到未核历史/其他产品 |

当前工作区手册缺失、普通git路径历史无返回已留为检索过程说明；实际通过coverage-sync报告给出的旧对象定位成功。旧对象1a321ce是2026-09-01的未跟踪文件保存对象，不是本次新建或恢复进repo。
