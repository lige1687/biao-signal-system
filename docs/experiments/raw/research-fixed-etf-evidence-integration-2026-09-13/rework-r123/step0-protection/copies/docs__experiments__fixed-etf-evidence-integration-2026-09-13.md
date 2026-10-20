# 固定 ETF 池证据与研究输入贯通：执行报告（fixed-etf-evidence-integration-2026-09-13）

任务书：[2026-09-13-fixed-etf-evidence-integration.md](../superpowers/plans/2026-09-13-fixed-etf-evidence-integration.md) v1.0.0。
任务协议（现行）：[protocol.json](raw/research-fixed-etf-evidence-integration-2026-09-13/protocol.json)
v1.0.1（sha256 `669f956a9b8b5b96e8d8ccd0fd953769733d5c85834b5b68ec21f1d085475dac`，
v1.0.0 原件丢失事故见 §7.3）；父协议：动量样板 v1.0.7
（`c42110c1deb2441415eff85669d986378f536c9f83f839c0bf5d300791024a3d`）。
研究原则 v1.1 / 定义标准 1.1.0 / 执行合同 1.0.1 / 报告模板 1.1.0；登记表容器 1.2.0。

## 一句话结论（大白话）

**这一轮把仓库里已保存的官方材料真正接进了研究输入：515300 的 6 条官方
分红公告与冻结记录逐字段核对一致（每 10 份→每份的换算独立手算全对）、
3 条拆分的方向与日期核到 PDF 原文、515050/562590 的上市交易日核到上市
公告书（2019-10-16 / 2023-10-18）；用这些事实生成了带经济指数列的派生
快照，派生快照算出的 772 个动量值与主控确认过的旧值完全一致，两个对象
的字段缺口清零；515050/562590 的"缺上市资格证据"发现改为"日期自洽但
资格未授予"。但真实预测研究仍被拒：10 只产品缺上市公告、20 条行动全部
缺历史可得时间、资格授予标准未建立。资料没清零，但每缺一份、为什么
影响结论，已经写到条。**

## 1. Task 0：有限收尾（主控 §10.2 T1–T3）

| 项 | 修复 | 验证 |
|---|---|---|
| T1 | 同期全部目标标签不可知时保留日期行（n=0/缺失/原因），`rank_diagnostic` 对空集合返回缺失而非崩溃；标签状态改逐行互斥分类（可用/行动不可知/端点未成熟/端点缺价/非观察日）并与总行数对账 | 主控 closeout 两个反例转为测试并全部通过（`test_all_labels_unavailable_keeps_date_rows_not_crash` 等） |
| T2 | 历史模式晚取得以受影响观察时点判别（不只比评价期末）；`observation_cutoff_assumption` 声明 15:00 仅为保守测试截点 | 期内晚取得（2026-01-01 可得、评价期至 2026-02-27）现被标事后重建 |
| T3 | v1.0.3 误存文件加旁置 README 指向主控重构件（7d7562f7…，哈希测试锁定）；恢复尝试未匹配的 v1.0.4 如实注明（protocol-v1.0.4.README.md + recover-v104-attempt.py） | 两个文件的哈希由测试锁定 |

### 版本管理事故自报（§7.3 专节）

本轮发生三起协议版本事故，均已如实登记：① v1.0.3 曾误存副本（1c8d99c1…，
主控 T3 指出）；② 封存的 v1.0.4（9b05212d…）在 Task 0 改码后被原地覆盖，
字节重构尝试未匹配（recover-v104-attempt.py 留档），仅存哈希记录；③ 生成
v1.0.1 时误覆盖 v1.0.0 副本（54a306d7…），字节不可恢复，但 run-03/04
manifest 绑定该哈希可核对任何声称的副本。规程已改为"生成→立即另存→
校验哈希→才可继续"；v1.0.5/v1.0.6/v1.0.7 与本任务 v1.0.1 均按此执行
（v1.0.6 为未消费的中间版本，已注明）。

## 2. Task 1–2：盘点与原文事实

- 盘点（[run-01/source-inventory.json](raw/research-fixed-etf-evidence-integration-2026-09-13/run-01/source-inventory.json)）：
  四组材料 156 文件全量哈希、4 组重复哈希登记、文本读取 8/80；
  [needs.csv](raw/research-fixed-etf-evidence-integration-2026-09-13/run-01/needs.csv)
  35 条需求（14 条上市 + 21 条行动）。159516/516690 等名单外产品仅登记不接入。
- 证据包（[evidence-bundle.json](raw/research-fixed-etf-evidence-integration-2026-09-13/evidence-bundle.json)）
  12 条记录、11 条事实核验通过、原文读取 17/80：

| 记录 | 核对结果 |
|---|---|
| 515300 六份官方分红公告（PDF+抽取文本） | 主代码/除息日/金额逐字段与冻结行动一致；每10份→每份独立手算（0.6610/10=0.0661 等）全对；**公告送出日期构成真实公布下界** |
| 515300 第 7 条（2025-12-15） | 本地无官方原文——不核、不补、不改冻结值（unresolved） |
| 拆分 512890/515050/515880（官方 PDF） | 方向 1:2 / 1:3 / 1:3 与冻结比例一致；512890 拆分前后份额×净值算术自洽（73,055,390×2=146,110,780；1.6004/2=0.8002）；除权日一致 |
| 515050 上市公告（官方 PDF） | 上市交易日 **2019-10-16**（公告书 2019-10-11 上网公布）；主体"华夏中证5G通信主题ETF"与代码 515050 一致 |
| 562590 上市交易公告书（官方 PDF，40 页） | 上市时间 **2023-10-18**（公告日 2023-10-13） |
| 冲突登记 | 515300 公告文内基金全称含"红利低波动"字样而主代码为 515300——疑点登记，不自动裁决 |

## 3. Task 3：证据包校验与 listing 桥接

`src/lei_signal/research/qualification_bundle.py`：
`validate_evidence_bundle`（结构/来源哈希重算/精确身份/事实字段/时间格式；
**不信任 facts_verified 自述**——强制改 true 也不能越过来源检查）+
`listing_evidence_from_validated`（桥接 JSON 附原始公告路径/SHA/定位/抽取
规则）。14 项测试覆盖任务书全部反例（假路径/错哈希/错交易所/成立日冒充
上市/无定位/日期金额矛盾/合成冒充/同 ID 冲突/重复/未验证声明用途）。

## 4. Task 4–5：派生快照与接入

- 派生（[run-02](raw/research-fixed-etf-evidence-integration-2026-09-13/run-02/result.json)，
  真实输入一次）：14 只产品名义 OHLCV 逐字节保留、追加 economic_index
  事后重建列；离线读回哈希全对；**两对象字段绑定 directly_satisfiable=true**
  （缺 economic_index 的缺口清零）；**动量 772 正式键与 run-04 比对 0 差异**。
- 接入（Task 5）：动量 CLI 新增可选 `research_evidence` 协议字段（省略时
  行为不变）；已核上市事实经桥接传入 `check_snapshot(listing_evidence=…)`。
- 真实运行（纠错预算 1 次已用）：
  - run-03（v1.0.0，无证据接入）与
    [run-05](raw/research-fixed-etf-evidence-integration-2026-09-13/run-05/manifest.json)
    （v1.0.1，接入后）历史诊断均退出 0、772 值；
  - **发现差异精确为 2 条**（[qualification-delta.csv](raw/research-fixed-etf-evidence-integration-2026-09-13/qualification-delta.csv)）：
    515050/562590 的 starts_after_window 从"缺上市资格证据"变为
    "日期算法自洽，但来源的资格状态无法确认"——资格授予仍归底层闸门；
  - run-04/run-06 qualified 均 **退出 2 拒绝**：排序/研究信号用途未获允许
    （其余产品缺上市证据 + 20 条行动时间资格未证明 + 准入标准未建立）。
  - run-10（[manifest](raw/research-momentum-prototype-2026-09-13/run-10/manifest.json)）：
    终版合成示例（synthetic 模式，动量协议 v1.0.7 绑定）。

## 5. Task 6：还缺什么（三份交付）

- [qualification-delta.csv](raw/research-fixed-etf-evidence-integration-2026-09-13/qualification-delta.csv)：
  16 条发现对照，2 条改变、0 条消除；
- [consumer-map.md](raw/research-fixed-etf-evidence-integration-2026-09-13/consumer-map.md)：
  已接入/未接入/严格时间卡差异；
- [remaining-acquisition-request.md](raw/research-fixed-etf-evidence-integration-2026-09-13/remaining-acquisition-request.md)：
  待授权联网阶段（≤40 请求/20 份，仅交易所与管理人官方披露）——**本轮未执行**。

## 6. 收益、风险与代价解释

不适用：无账户收益计算；动量/经济指数为价格或指数变化比例。
validity=not_tested；production=not_authorized；
policy=not_applicable_no_account_policy。

## 7. 限制、复核与复现

### 7.1 身份与指纹

| 文件 | SHA-256（前 16 位，全值见任务证据目录） |
|---|---|
| 动量协议 v1.0.7 | `c42110c1deb24414` |
| 本任务协议 v1.0.1 | `669f956a9b8b5b96` |
| `momentum_prototype.py` | `5425e4f549471004` |
| `qualification_bundle.py` | `008c86b2f6d25c10` |
| `run_momentum_research_prototype.py` | `21d246a67e334817` |
| `prepare_momentum_qualified_inputs.py` | `e039f73abeb31a59` |
| 派生 snapshot.json（run-02） | `d43f8b2f57e56961` |
| evidence-bundle.json | `c7b4259f0ea24883` |
| run-05 manifest | `824ff85cf50a7617` |
| run-10 manifest | `6700a29660e10e53` |

git HEAD `8ba16576b75e605aa1b0d0902568c760c4b99095`；Python 3.11.7；
零网络（断网守卫自证）、零新增依赖、零新增行情/产品/因子/账户。

### 7.2 命令与日志

```sh
# 局部：89–92 passed（多轮），最终 90 passed
python3 -m pytest tests/unit/test_momentum_prototype.py \
  tests/integration/test_momentum_prototype_cli.py \
  tests/integration/test_momentum_qualified_inputs.py \
  tests/unit/test_qualification_bundle.py -q
# 派生（真实输入一次）
python3 scripts/prepare_momentum_qualified_inputs.py --protocol <动量协议v1.0.5时点> \
  --evidence-bundle <bundle> --run04-values <run-04/values.csv> --out <raw>/run-02
# 历史诊断与资格拒绝（v1.0.1 接入后）
python3 scripts/run_momentum_research_prototype.py --protocol <本任务协议> \
  --mode historical-diagnostic --out <raw>/run-05     # exit 0
python3 scripts/run_momentum_research_prototype.py --protocol <本任务协议> \
  --mode qualified-research --out <raw>/run-06        # exit 2（拒绝）
# 完整回归（22 文件）：391 passed in 50.24s（raw/.../full-regression.log）
python3 -m ruff check <本轮八文件>   # All checks passed!
```

### 7.3 版本管理事故（自报，见 §1）

三起（v1.0.3 误存 / v1.0.4 原地覆盖 / v1.0.0 副本覆盖），处置与规程修正
如 §1；run 产物 manifest 未做任何事后修改。

### 7.4 保护核对

896 项基线逐文件复算变化 0、缺失 0；run-04 值哈希未变
（`0db2492a…`）；旧 run-03～run-10 与主控反例未覆盖；他人未提交改动未
触碰；未提交 git。

### 7.5 尚余限制

- 真实预测研究仍被拒（run-06）：9+ 只产品缺上市公告原文；20 条行动仅有
  公布日期下界、无历史可得时间；listing 资格授予的准入标准未建立
  （底层恒为 unverified，属另行授权事项）。
- 515300 公告文内基金全称疑点、第 7 条分红无原文——登记于 conflicts/needs。
- 273 条月选资格、五分组、显著性等仍属政策/后续范围，本轮未触碰。

## 8. 最小决策卡

| 必答项 | 本轮答案 |
|---|---|
| 本轮判断什么 | 已保存官方材料能否接成可追溯资格证据并贯通研究输入 |
| 基准与增量 | 对照为 run-04（772 键独立核验值）；派生快照零差异复现；发现对照 2 改 0 消 |
| 收益解释 | 不适用：无资金、无收益计算；policy=not_applicable_no_account_policy |
| 代价与执行 | 无费用/成交；未接账户与生产 |
| 证据与结论 | 工程/证据链贯通（mixed）：事实更可信、缺口到条；预测资格仍不足 |
| 下一步与边界 | 最能改变资格的事：B 组官方分红公告原文 + 上市公告 10 份 + 时间规则授权；未获准冻结观察或生产；完成即停，交主控复核 |
