# LEI 公式语义与绝对时间：独立工具交付

- task-id：dot-formula-time-validation
- 状态：completed（仅本次独立校验器、合成回归与准确源码探针交付；未接生产，完整 registry 准入仍 blocked）
- 更新时间：2026-10-03T07:40:00Z，Etc/UTC
- 负责人/角色：当前 LEI 接续方，独立实现与验证；共享源码/registry 正式改造的原实现负责人尚待明确，本记录不取得其写入权。
- 目标与用途：拒绝未审阅的 RV20 公式合同语义变更；按绝对时间检验资料声明的真实可用时刻是否不晚于截止。服务研究计算前的合同/输入资格，不产生交易判断、市场效果或新收盘规则。
- 验收：可直接运行及导入、独立算术正反控、完整合同/精确依赖绑定、时区等价/截止/缺证边界、准确源码问题复现、来源字节不变、最终代码和回执远端可读。该有限验收已完成，源真实性/完整性与生产集成不在通过结论内。

## 工作分支、准确成果与版本

工作分支 codex/lei-formula-time-validation-20261003；基础完整 commit d444316817e9330c2d72a4a90c655467b45dd5bb；最近已推送成果完整 commit 7dd36a3c6b59bd409243e04549294ad809e7129d，已核远端 ref 相同，十文件内容与 Git blob 逐项读回一致。
成果只新增 docs/experiments/raw/lei-formula-time-boundaries-2026-10-03/：
validator.py、test_validator.py、probe_sources.py、README.md、fixtures/reviewed_binding.json、fixtures/pass.json、fixtures/block_formula.json、fixtures/block_time.json、evidence/source-probes-final.json、evidence/command-receipt.json。没有修改 src/configs/tests/registry/Air 输出或他人原文件。

[运行入口与限制](https://github.com/lige1687/biao-signal-system/blob/7dd36a3c6b59bd409243e04549294ad809e7129d/docs/experiments/raw/lei-formula-time-boundaries-2026-10-03/README.md)
[实际校验代码](https://github.com/lige1687/biao-signal-system/blob/7dd36a3c6b59bd409243e04549294ad809e7129d/docs/experiments/raw/lei-formula-time-boundaries-2026-10-03/validator.py)
[命令/结果回执](https://github.com/lige1687/biao-signal-system/blob/7dd36a3c6b59bd409243e04549294ad809e7129d/docs/experiments/raw/lei-formula-time-boundaries-2026-10-03/evidence/command-receipt.json)

适用 COORDINATION.md 1.0（规则 SHA-256 6871aa85da956453ca8e4d077e9bd9d9bf229df42c8447ffb94f97ba7f2461e0）；本阶段 fresh 核 coordination/lei@368add358cad92bab2102cc8c7dbd83fa749490f，规则 blob 126a1a01cd09439536c69fdd7264e3e292e4b852 未变，自己的旧 task blob 未变。沿选定 d444 的 AGENTS/current-standards 实际索引：research-standards/1.0、workflow 1.1，mission1.1.0/question_method1.2.0/increment1.1.0/principles1.2/execution1.1.0/definition1.2.0/template1.2.1。旧冻结研究不迁移、不改策略原文与阈值。

## 已完成、检查与准确边界

- 作者标准库 7 项集中测试通过；三个 CLI 合成样例退出 0/2/2，分别为正常/公式阻断/时间阻断。独立 5 项范围对照通过；发现的 UTC 转换溢出已最小返修并复核，极端范围 API 返回 unknown/blocked 而非抛出未处理异常。失败和修订没有伪称市场效果。
- 公式工具只支持已审 mixed.rv20@1.0.0 typed 合同。完整定义/参数/单位/端点/缺失/时间与两层精确依赖绑定；不是通用自然语言公式解析器。正常算式为 20 个本产品有效报价间简单收益率的样本标准差×sqrt(252)，需21价格、含当期、缺价不填充。合同同义改写也需重新审阅，不能以名称或子串证明语义。
- 时间工具比较带时区的完成/特征可用/全部依赖可用时刻，与全局及可选逐行 cutoff；同一绝对时刻跨时区等价。缺时区或可用时间完整性声明则 unknown/blocked，没有默认某市场15点新规则。只核声明一致性，不认证来源实际首发真值。
- 准确 source probe 退出0表示预期问题复现，不是原源码已修好：external@1ac596f65110e06c286f04707165251328df0962 与 technical@d444316817e9330c2d72a4a90c655467b45dd5bb 的 workflow 日线接口，对同绝对时刻时区写法/全局同日 cutoff 的准入不一致；external key 有相同截止问题。
- 公式 probe 调用真实 bound_reference 解析后的局部接口，仅在注明 resolver seam 用真实展开卡替代解析器；旧绑定接受同id/version的2倍公式，候选拒绝未审合同。标准库独立 RV20 逐行核算。完整原 resolver 另调用，仍因 lifecycle basis 缺 tests/unit/test_research_definitions.py（mixed.momentum.raw@1.0.0）而 blocked，不删basis、改生命周期或伪造文件绕入口。
- external registry 1.6.12 与 technical 1.6.0 分开；technical registry 未加载、不混到 external。17 external＋3 technical 文件前后 SHA 不变。原1ac payload只是明确额外输入，不把两个版本合称已升级共同主线。
- 发布检查：仅10 UTF-8新文件、总77,766字节；准确path/diff/大小/敏感扫描通过。基础树无.github，workflows404；成果精确SHA Actions0只是可见时点证据，仓外集成未全面确认。未强推、合并、部署、付费或上传策略原件/行情/数据库/凭据。

## 指纹、可复现与未覆盖

validator.py SHA-256 c30bae934955f3dec16e603257fa6925354088039dac6a7ace2cc2d48ea6cbde；
test_validator.py 3dfcc6b675d81f1fa9a4bf6f03a5cd88f93fb71551ca100e377b1d460d1f8fda；
probe_sources.py 74b9f1e536c1505aff1afd31e0bebb56812944406a2efc8c9359ac88d2180b87；
source-probes-final.json 5a61017ae9c7e3d491765714a45e6ca561c0fc723a42584743a48f0161026d2f。
其余冻结文件身份见成果 command-receipt。原本地 command-receipt SHA 5b5944fd3d5bc0d7c5c0a1a13c8ebf20c61431d90bddc4517581ad402eb1fd37 保留；仅发布副本执行位置改相对 cwd/标准 python3/额外源目录占位并注明移植，发布副本 SHA b47637a5a06baef7f192b8e6979d6681c6d56f8be2c55caefa2ffc6fd896570c。源码、测试结果及20源指纹未改。

独立校验器/7测试/3 CLI仅依赖 Python 标准库，按 README 可运行，不需联网安装。源码 probe 另需已有 NumPy/Pandas 及两套按pin materialize的额外来源目录；这十文件不包含完整源快照、原研究数据或 registry 依据闭包。不能说 clone 即可通过完整原registry；缺件保持 blocked。无权重/tokenizer。未运行新市场实验/标签/拟合、完整 workflow、账户/收益或生产集成；因子增量和线上收益未测量。
已批准策略副本身份保留：体系 df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20，实现 85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903；原文只读、不随本包推送。本交付是独立工具，不是市场实验归档或整套研究结束。

## 依赖、下一步、封存与历史

本次独立交付到此停止，没有无期限 active 后台工作。后续若要正式接入共享源码，须明确原实现者/独立验证者、准确选定分支与完整登记依据、真实源可用时点；该生产/主线改造未实施，不从本工具通过推定获准。本方不改 technical 抵扣路径、reader等待/UI、remote black-reset、外部已封存 Hypothesis 或 Pro 三路研究，不替任何 Air 任务改owner/状态。
本轮市场请求/实验/拟合/新安装/付费均0，合成测试与工程检查单列，不清零旧家族账本。保留旧 V01/K01/P01 的16:00+08历史成绩，不因新局部反例认定其无效；不重复已封存的缩放/未来价性质实验或市场收益计算。
历史首登记/暂停/拟定范围见本任务初始记录 53be5c72a6d4711d916361d5d1026e5fe144e609；阶段代码与回执以本版准确成果为准。无另写旧阶段入口可迁移，跨任务摘要仍只有本文件。自身状态提交从 git log -- 本路径定位，不无限补自指SHA。
本版新增：可运行代码与已通过验收、最小返修/限制、已推精确commit及10文件读回、移植回执说明，把有限独立工具标completed并保留生产/registry缺口。后续若有新授权，仅fresh相关task/rule变化、核成果/源指纹，再做限定未完成项；没有新事实不反复审旧记录。
