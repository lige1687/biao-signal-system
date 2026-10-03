# Pro 接续：历史爆量日价格位置研究候选

- task-id：dot-pro-strategy-definition
- 状态：paused（用户要求先分清三路目标，候选未定字段暂不实现；真实市场效果仍 blocked）
- 更新时间：2026-10-03T11:43:00Z，Etc/UTC
- 目标与用途：核原策略的“过去异常放量日价格位置”能否形成不夸大原义、收盘后真实可知的研究代理。本轮只把原 Pro 收盘代理草案落实为独立研究字段与合成测试，不认领整个量价方向。
- 验收：逐项原文→候选公式→具体用途对齐，区分原义/代理/待定；准确对象 id@version、单位、窗口、当时可得输入和缺失/行动处理可核；与当前已做证据去重；交可运行计算模块、CLI、字段合同和手算/前缀回归；未冻结不产市场结果，不输出买卖或资金动作。

## 已完成与历史材料

原 Pro 交付 LEI-exploration-continuation-2026-10-02.md 与 lei-v01-price-position-definition-review.md 已有：策略 §2.5、§4.5、实现 §4.8 的定义审阅；收盘代理高于历史最高异常日收盘只表示价格位置，不证明“所有买入者盈利”。量比暂用含当日的 20 报价窗口/两倍只是待确认代理，不能变成正式参数或参数扫描许可。
定义审阅文件 SHA-256 2d7b814ce6d64565165969297e5890486cf4b25100464506bc2d29864025d8f3；三路索引 f8ebdd107d5ea9594a490a568f3acf1fd163e72952d425a78ce407df34594b63。2026-10-02 后续云端阶段已交 V01 依赖 40/40＋panel hash、14 公告 hash 匹配及最低 Linux 环境就绪记录，旧 38 缺件状态不再适用。历史 Linux 为 Python 3.12.14、78 官方 wheel、18 依赖/21 imports、Parquet/只读 DB/V8/pipcheck 通过，未启动 API 或迁移 DB。该后续旧工作区目前缺失，原回执本轮未恢复，不声称当前环境重验通过；这也不是完整现行 registry、候选输入资格或市场效果已通过。今日解除暂停后 0 实验。
V01/P02 历史用途已封存，V01 旧效果证据不足；不把 V01 写成未做，也不把封存结论扩展到这个未冻结历史价位组合。P01 overhead120 筹码对象不是本候选，禁止同名混用。

## 正在做的范围、下一步及恢复条件

用户最新要求先分清三路目标、优先已经审清的具体增量，本路暂停继续读取、候选实现和测试；未开始代码写入，未形成新计算产物。此前范围登记51cb688fa9923ac2a6db257ba548416132cc1a8b推送读回后、尚未开始实现即收到暂停，本版纠正为paused，不把登记算交付。

最短checkpoint：只读核过原 Pro 草案及3deaad7a1724228780a62af49cf34fc046b0640a的volume_information.py；已有含当日20报价量比可复用，无新市场效果。未定：异常阈值/量或额选择、收盘代理是否采用、日历年闰日左界、价格尺度/行动时点、输入资格/缺失/单位合同。Air已保留历史爆量价位给本方，但这不替代候选语义确认。

原拟分支codex/lei-volume-price-candidate-20261003和docs/experiments/raw/lei-volume-price-candidate-2026-10-03/均未创建；候选字段/CLI/手算与前缀测试未实施。下一步只等待本路明确目标与需先确认字段的选择；未经明确恢复不续写，不从旧效果代选参数。真实行情资格、市场合同和资金效果仍缺条件。

## 归属、重叠与避让

technical-factor-sequence 的抵扣路径形状/C01/Q01，lei-technical-reader-research 的阅读页/137 起点等待，remote-core-review 的 black-reset 与旧 T2—T10 验收，以及 classic/external 的已封存研究均留原负责人。本线不实现 2B、不动全局 definitions.v1.json 或共享 workflow；只读引用他们的当前准确成果。Air当前完整日线回调/小时确认仍留原负责人，本线不进入资金对照。历史 V01/P02 与当前候选区分，但现行量价相关未登记活动仍未知。若同候选已被认领，暂停该重叠块，保留本方独立复核角色；不修改任何 Air task。

## 输入、预算与未推送

已批准策略副本 SHA-256：体系 df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20；实现 85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903。本任务无模型权重/tokenizer。Pro handoff v2 原包 SHA-256 9cae0d0df6629be846d9c550fff034a3650daf5e7d458ccf943454b71f06b28f，43 文件静态指纹已核；源码旧快照仅为历史参考且无 Git 父链/未提交状态，不代替最新基线。
小包原件与恢复源仅本地；后续依赖/公告/Linux 原回执已历史交付、当前待恢复，远端不可复现。本次不上传原始行情/受限源材料。旧 V01/P02 预算沿原账，完整历史余额未确认，不重置。本轮新增市场实验 0、拟合 0、取数 0、付费 0。不重跑 V01/P02，不从旧结果选择价格代理或窗口。

## 规范、身份与同步边界

负责人为当前 dot LEI 接续主控；来源仍是 Oct2 Pro 三路（01a0fa8a-bb5f-701a-86c8-7083616c8033），不接管 Sep30 Air 任务。同 ID 若有第二写入者，停止覆盖并报告。

适用 COORDINATION.md 1.0；规范按本轮基线实际 current-standards.json（blob77fd228008dcb8e26218104be150180530332a12）：research-standards/1.0、workflow1.1、mission1.1.0、question_method1.2.0、increment1.1.0、principles1.2、execution1.1.0、definition1.2.0、template1.2.1。实现时按索引只读必要正文，完整入口/定义闭包未验不冒称通过；旧冻结合同、结果与预算保留原版本。首次登记的历史基线与完整规则核对保留本路径Git历史。

计划工作分支：codex/lei-volume-price-candidate-20261003（尚未创建）。本轮实现基础完整 commit：3deaad7a1724228780a62af49cf34fc046b0640a；已核远端技术分支相同。复用路径 src/lei_signal/research/volume_information.py，blob fa819fc81251da40a0a8bf9e73017adda53dbf08；已读该基线 AGENTS 和 current-standards，版本索引沿上述现行规范。最近已推送本任务研究成果 commit：无。恢复包仅本地，不代替本轮准确基础；旧1ac596f65110e06c286f04707165251328df0962的handoff payload不混作现行根树。此状态自身提交按路径Git历史定位，不无限补自指。

协调本轮只改此既有 task；后续实现只增上述独立 raw 目录，不改 COORDINATION.md、他人 task、AGENTS、规则账本、定义/实验 registry、共享源码、配置、正式测试或 Air 输出，不推 main/master、不合并、不部署、不调用付费计算。后续代码、研究小证据留独立工作分支，再在此记录索引。

## 本轮检查、恢复与版次

暂停前登记51cb688fa9923ac2a6db257ba548416132cc1a8b已推并逐字读回；从未通知开始实现。现按最新决定纠正原task状态，推前核到b51c454f39925101024b194d8e60a6d1eff03842，其间仅classic教学设计与remote-core暂停留档增量，不改本方记录，均完整保留。COORDINATION.md v1.0及blob126a1a01cd09439536c69fdd7264e3e292e4b852未变。

通过：两实现方确认0代码/测试写入；本次精确两task、UTF-8、大小、凭据形态和差异检查。推后核准确完整commit及逐字读回paused，才报告同步。已核协调基线无.github，Actions/statuses为空，不代表CI通过；外部自动化未知。旧首次登记/历史决定见本路径53be5c72a6d4711d916361d5d1026e5fe144e609；不重审整库。
未运行：候选代码和测试、市场计算、训练/拟合、全项目测试、真实交易；没有本任务运行中实现或市场进程。旧协调检查器仍由原负责人维护。
下一次交接：先确认用户对本路的独立目标及未定字段是否已经作出决定，再按原协调规则登记具体恢复范围；未明确恢复则保持暂停，不另写宽泛审查或重复旧实验。
本版新增：按最新用户要求将先前刚登记的active修正paused；仅核材料的checkpoint保留，0实现/0新增市场实验。原封存、失败和输入缺口不变。
