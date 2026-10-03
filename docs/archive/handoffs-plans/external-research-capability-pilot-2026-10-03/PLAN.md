# 外部候选公式搜索试点 Implementation Plan

> **For agentic workers:** 采用 executing-plans 顺序推进；实现使用一个既有 Sol 助手，主控负责冻结、执行核心比较、证据和发布。用户已要求自主推进，不再询问执行模式。

**Goal:** 回答 DEAP 自动公式搜索是否比直接 NumPy 方法提供足以保留的可观察研究能力。

**Architecture:** 同一人工资料比较训练均值、线性/三次多项式及稀疏公式筛选，与相同规则的随机搜索和 DEAP 演化搜索。搜索与最终检查隔离；测试和范围外资料不参与候选选择，原始失败及全部尝试保留。

**Tech Stack:** Python3.11.7、NumPy2.1.1，隔离 DEAP1.4.3；JSON证据、项目原报告登记与独立Git索引。无市场输入、网络模型或新服务。

## Global Constraints

- 已确认首轮上限6次公开请求（含下载/失败），1核心+3必要后续工程批，0市场拟合、0付费服务。
- 冻结协议：docs/experiments/raw/external-symbolic-search-pilot-2026-10-03/protocol.json，SHA256 8e4088da68500f765d0a95b277630c2109f1033dd8ab0a727f097f337d1f50ff。只纠正实现错误，不改问题/数据/参数追求好结果。
- 工作基础c618dead611171c90a29f152b398a2767299756e；只写本试点目录/报告、自身进度及登记中自己的条目；不写共享workflow/定义/策略/生产。
- 原共享HEAD/index与其他任务文件不动；项目规则优先于通用技能默认文件位置和提交方式。
- 工程试验不走金融workflow：这里没有市场对象、因子定义、未来行情标签或交易规则，不能伪造对象ID让工具检查替代研究设计。

## Task 1：来源资格、预算和冻结（已完成）

- [x] 读取 coordination/lei@417e44430eca4ddf6995db65c9b1b491ec6515ce；自身范围记录远端逐字相同，13任务当前范围无已登记冲突。
- [x] 核两策略源实际SHA与批准值一致。服务研究执行层，交易语义不变。
- [x] 比较gplearn与DEAP两候选：前者额外scikit-learn依赖未具备；后者只需NumPy。选DEAP，未测试不等于否决gplearn所有用途。
- [x] 官方源码说明2次、PyPI准确版本1次、wheel下载1次，共4/6。核wheel大小/哈希/许可证，离线无依赖安装到仓库忽略目录，未改全局。
- [x] 冻结3人工问题、4资料分区、3搜索种子、57,600候选上限、直接基准与采用标准；两方案模型调用均0，AI实现消耗未计量。

## Task 2：有界比较入口（进行中）

**Files:** raw目录 run.py、test_run.py；协议只读。Sol单写这两个文件，主控不同时改。

**Interfaces:**
- `python3 run.py --output <new-directory>`：生成冻结人工资料；按协议运行直接基准和两个搜索方法；写 input-fingerprints.json、results.json、predictions.json。输出目录已有成果时拒绝覆盖。
- `python3 run.py --check-existing <directory>`：不再搜索、不导入DEAP；重新生成同指纹输入，独立AST解释导出式子，核预测/误差/计数及冻结身份，错误退出非零。
- 原始结果不得只保留赢家；每任务每搜索种子和错误计数全部交付。

**Checks:**
- [ ] 小测试：独立除零、非法AST、输入/版本或输出篡改拒绝、基准正常算术。执行命令记录退出码，不把帮助页/import当端到端。
- [ ] 主控读代码，核test/范围外资料没有进入训练或选择。核心脚本设600秒搜索上限，保留超时/失败而不暗中调参重开。
- [ ] 核心1批：`PYTHONPATH=.biao/external-research-pilot-20261003/deps python3 docs/experiments/raw/external-symbolic-search-pilot-2026-10-03/run.py --output docs/experiments/raw/external-symbolic-search-pilot-2026-10-03/core`。预期完成3问题×3种子×2搜索方法和每问题强直接基准；成败以真实输出核定。

## Task 3：必要复核、结论、最小恢复

- [ ] 主控使用已存输出执行check-existing；在独立临时目录只复制本试点源码/协议/证据再执行，不重跑搜索。核错误对照能拒绝改错的一份预测。
- [ ] 对照协议准确阈值判采用/拒绝；人工介入/耗时/依赖成本逐项记录，未测人力及金融效果写未测量。结果不明不追加参数。
- [ ] 仅在达到采用标准时整理最小可用研究接口；否则保留比较入口和不接入理由，不安装为默认skill、不修改正式依赖。
- [ ] README写相对路径运行/复核方式、安装指纹、输出和局限。SHA256SUMS、sources.json、review.json和command-receipts.json给另一机器核验。

## Task 4：归档及同步

- [ ] docs/experiments/external-symbolic-search-pilot-2026-10-03.md有大白话结论、性能与相对直接基准增量表、反例、成本/失败、ARCHIVE和决策卡。
- [ ] 工作分支registry/INDEX只追加此报告条目；不从共享脏登记复制。运行目录归置检查、准确差异/敏感内容/大小检查。
- [ ] 独立Git index从准确task基础建tree/commit；只推task/external-quant-progress，核完整远端SHA并读回本次文件。
- [ ] 更新同一个协调记录，写准确成果commit、预算、状态/限制、原负责人继续。核远端包含提交且内容相同；不合并/部署。

## 自检

设计五步均对应上述四任务。独立验证不重做搜索。当前范围只候选关系搜索这一具体缺口，未将一次人工任务扩大成完整自主研究、金融预测或线上收益。过去封存及预算不变。
