# 修订回应（v1.1，2026-09-17）

主控收口补正（同日）：修正workflow-map总表与§1.4残留的旧期望文件名、two-worked-mappings末表残留的合成入口；共三处机械同步，不改研究方法，不运行代码。以主控复核报告§6为本提案接受范围。

对主控复核（2026-09-17，裁决"框架可保留，事实与入口需限定返修"）R1–R3 的
逐条回应。修订前六文件原字节与哈希见 `history-v1/`（含 HASHES.txt）；
本轮仅改本目录文件，零代码、零真实计算、零网络、零共享写入。

## R1：状态必须引用最近裁决，删除重复待办

| 主控指出 | 旧说法（位置） | 新说法（位置） | 证据 |
|---|---|---|---|
| S1–S3 已经 §10 限定收口（118 回归、158 独立检查），不能仍列未完成 | "工具本身还有三项小收尾没完成"（README）；"S1–S3 限定收尾未完成（代码未落，派发受阻）"（two-worked-mappings）；"S1–S3 收尾未完成"（CSV 行8、workflow-map §3）；W1 待办（integration-proposal） | 全部改为"已于 2026-09-17 主控 §10 限定收口（118 项回归+ruff、158 项独立检查；保留快照核验超预算 3/1 违规记录；不增加有效性证据或真实运行权限）"；W1 标为历史已完成、不再派发 | factor-evidence-controller-review-2026-09-16 §10（本轮补读，文件 SHA 78888ca5… 与 execution 1 相同——§10 当时已在文中，是我未通读而误引 §9 与旧受阻报告）；runner/stability 工作区 SHA 与 §10 记录逐字一致 |
| 宽度执行规格已存在且用户已授权实施 | W3"起草宽度价格来源裁定与执行规格（只出文本）" | W3 撤回，改为"待决定事项（ZCode 任务链内）：一次补救真实尝试待用户授权"；不重复起草同职责任务 | `docs/archive/handoffs-plans/2026-09-17-breadth-first-description-execution.md` v1.0.0（含用户授权原话与家族 `breadth-unit-csi300-b200-21-v1`）；breadth-b200-first-description-controller-review-2026-09-17（首轮路径错误失败无数字；主控建议≠批准） |
| 每个当前状态写明截至时间、最近主控节号和范围 | CSV 无截至信息 | CSV 新增 `status_as_of` 与 `latest_ruling` 两列，逐行填写；workflow-map §3 加"截至 2026-09-17"并给节号 | 本表 |
| 旧验收 SHA 不代表状态永远最新 | integration-proposal M3"总览当前版本已被主控按 SHA 核验收口" | 改为"v1.1.0 曾被按 SHA 验收只证明当时版本被接受"，并提示下一次合规同步应引用 §10 | integration-proposal §M3 |
| 保留流程超预算记录，不把收口改成因子有效 | — | README、workflow-map §3/§4、CSV 行8、示例 A 均带"保留超支违规、不增加有效性证据或真实运行权限" | §10、§10.3 原文 |

## R2：运行入口及终版证据绑定正确

| 主控指出 | 旧说法 | 新说法 | 证据 |
|---|---|---|---|
| 真实 B1 入口是 `b1_description.describe_b1`；`describe_states` 仅收 synthetic；共用 description_core ≠ 入口可互换 | 示例 A 与分流表把 `describe_states` 列为该问题类型的入口（未区分合成/真实） | workflow-map §1.5 表加"入口不可互换"脚注、§2 分流行分"合成/真实"两入口；示例 A 第 5 步改为 CLI→`describe_b1` 并写明两入口 docstring 自述；CSV 行4 同步 | `b1_description.py` docstring（"不调用 describe_states、不冒用 synthetic 身份"）；`state_description.py` docstring（"data_mode 必须 synthetic（真实模式未实现）"） |
| 示例 B 应指 closeout 目录终版协议与 v2 期望，不混配旧路径 | 示例 B 第 3/4 步指 `raw/factor-research-workbench-v1-2026-09-14/` 的 protocol-* 与 `independent-expectations.json` | 改指 `raw/factor-lab-final-closeout-2026-09-15/protocol-{1,2,3}*.json` + `independent-expectations-v2.json`（旧目录保留为历史）；本轮逐份静态核查三份协议：version 1.2.0、各 15 个 code_identity 键、data_mode=synthetic、expectation_source 冻结 v2 文件；v2 的 protocol_expectations 含 numerical/state/attribution 三案例（23/28/11 项） | 终版执行报告 §S2 与第 122–124 行 CLI；本轮对四份 JSON 的结构核查（未执行 CLI） |
| §7.3 是 2026-09-10 声明，不能据此断言后续工具无目标/成熟/证据检查 | workflow-map §1.1"未实现：TargetSpec/Evidence 合同未接 runner/schema/校验器" | 拆分为"通用合同未接入登记表自带接口（§7.3 原文范围）"与"后续具体消费者各自实现检查（factor_lab 时间审计、study_contract 成熟判定、factor_evidence 合同常量）"，并补反向提醒"规范写了也不等于机器自动查" | definition-standard §7.3 原文；factor-lab closeout §S3；factor-unit-usage §2 |
| "命令可跑"表述过强 | "命令（存在性已核，本轮未执行）"、"真实可跑的入口" | 统一收窄为"路径与参数已静态核查，本轮未执行"；一句话结论改为"第 1–5 步已有机器入口（静态核查），第 6/8 步是人工环节无代码入口" | workflow-map 一句话结论、§1.5 表头、two-worked-mappings 头部 |

## R3：合并建议与边界收紧

| 主控指出 | 处理 |
|---|---|
| "每一步都有可跑入口"与人工复核/授权矛盾 | 改为"每一步都有权威文档可依；第 1–5 步有机器入口（静态核查未执行），第 6 步复核与第 8 步授权是人工环节，没有也不应有代码入口"（一句话结论、§1 表第 8 行原有"无代码入口"保留） |
| 模板是否已含研究问题类型先查正文 | 已查：experiment-report-template v1.1.0 派发合同（T1）含"任务类型"枚举字段。M2 **撤回**，不再建议新增行，避免第二处重复权威 |
| 导航不能借提案另造权威总纲 | workflow-map §0 与 integration-proposal M1/明确不做均写明：提案层导航，不是第九份权威规范；手册引用须主控接受后 |
| 保留"本主线"限定范围，不泛指全仓 | CSV 行10 保持"本主线未发现…不推出全仓库为零"；README/流程图未出现全仓否定表述 |
| 不把同一对象不同用途变成必须走完八步 | workflow-map §0 新增"八步是路由不是关卡"；§4 原有"不串成关卡"保留 |
| 下一步 prompt 必须明确仍为待批 | W2 草案标注"仍为待批，不自动授权实现/真实运行/OKR"；宽度事项标"主控建议≠批准、本提案不新派"；integration-proposal 开头与"明确不做"重申不构成授权 |

## §5 交回要求执行情况

- history-v1：六文件原字节 + HASHES.txt（修改前已封存）。
- 仅本目录修改：README、workflow-map、capability-evidence.csv、
  two-worked-mappings、integration-proposal、sources-and-checks.json 同步；
  新增本文件与 history-v1/。未触碰其他任何路径。
- 补读范围限主控点名：factor-evidence-controller-review §10（同文件原哈希）、
  breadth-b200 阻断复核、宽度执行规格（前 40 行身份段）、b1_description.py /
  state_description.py docstring、experiment-report-template 全文、
  factor-lab-final-closeout §S2/§S3 段与 closeout 目录四份 JSON 结构。
  未展开全库、未读 ZCode 执行目录。
- 预算：事实补读（点名文件）不计入核销；终检用结构/链接/哈希综合核查 1 次、
  卫生检查 1 次，台账见 sources-and-checks.json `repair_round`。
- 零代码、零真实计算、零网络、零共享写入；旧结论留 history-v1，未覆盖历史。
