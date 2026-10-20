# 固定 ETF 池证据与研究输入贯通：连续长任务书

> **For agentic workers:** 使用 `executing-plans` 按 Task 0–7 连续执行。各任务完成局部验证后继续，最终一次交主控；无需每修一个测试就请求下一轮。不得自动新建用户侧任务。

**Goal:** 把仓库已经保存的官方材料，接成固定14只ETF的可追溯资格证据，再接到现有动量研究输入；交付真正可读回、可复算、能说明“还缺什么”的完整闭环，而不是再增加指标。

**Architecture:** 原始快照、公告、行动及旧结果只读；新任务目录保存证据引用、生成的资格记录、派生经济指数快照和新运行。复用既有身份解析、质量检查、经济指数与动量算法，仅增加薄的证据适配和必要入口参数。事实已核、当时可知、用途允许、实现可用、预测有效和生产授权分列。

**Tech Stack:** 仓库已有Python/pandas/NumPy/pytest/ruff与已有PDF读取能力；零新增依赖。接口代码块是本任务待实现设计，不代表已经实现。

版本：1.0.0；日期：2026-09-13。用户要求“检查完给一个尽可能的长任务”。这是在原范围上增加**既有本地资料的接入工作**，不是新增行情或研究对象。任务书制定完成不表示下列任务已执行。

## Global Constraints

- 默认全部离线：网络请求0、新供应商0、新行情0、新产品0、新交易因子0、新账户路径0、生产/OKR写入0。不安装Qlib/Alphalens或重建回测框架。
- 根及相关目录AGENTS优先。服务研究输入与证据层，不改变交易规格的道路、路牌、触发、过滤纪律。
- 必读权威：`docs/trading-spec-v1.md`；`docs/research/experiment-backtest-principles.md` v1.1；`definition-standard.md` v1.1.0；`ai-execution-contract.md` v1.0.1；`experiment-report-template.md` v1.1.0；唯一定义登记 `docs/research/definitions.v1.json` 容器1.2.0。
- 先读 `docs/experiments/momentum-prototype-controller-review-2026-09-13.md` §10 与执行报告§12。旧v0及旧实验继续其原协议，不倒填新版本。
- 本轮对象仅 `mixed.price.economic@1.0.0`、`mixed.momentum.raw@1.0.0`；目标仍 `protocol:momentum-next-close-21-session@1.0.0`。不变252/21、253条首次计算、月末观察、下一交易日收盘起算及随后21交易日结束。
- 固定评价期2019-09-02至2026-06-30；保持14只原池，不因资料不足删产品、换早上市产品或改区间求通过。273条属原政策资格，不混入本轮特征计算。
- 输入固定于原动量协议的canonical-snapshot-v2、calendar-merged、publication-evidence及21条normalized-actions。14只/18,916行先实际核对，不能硬造预期计数。
- 旧输入、旧run、公告原件、原主控反例、对象卡与底层质量/日历/身份/运行时只读。所有新产物拒绝覆盖；保留失败编号。现行协议指针允许另存版本后更新，历史字节绝不重写。
- 不使用allow_conditional/accept_structural放行；不把文件哈希一致、官方域名或自填trusted=true当作历史事实真实性证明。
- 不承诺本轮真实预测一定能跑；合法结果可以是“更多具体事实已核，但预测仍受限”。不以高相关、显著性、收益或测试数量作为价值证明。

## 1. 固定输入、事实边界与可写文件

仓库根 `/Users/yongbiaoli/Desktop/lei-signal-lab`。以下路径相对此根。

产品身份：159652.SZ、510300.SS、512400.SS、512890.SS、513870.SS、515050.SS、515130.SS、515170.SS、515300.SS、515880.SS、516220.SS、518850.SS、562590.SS、588000.SS。以固定snapshot清单复核，不添加名单外产品。

| 文件 | 本轮职责 |
|---|---|
| `src/lei_signal/research/momentum_prototype.py` | Task 0有限边界收尾；经济指数/动量公式不改 |
| `scripts/run_momentum_research_prototype.py` | Task 0状态与空集合收尾；Task 5可选证据包绑定，旧默认语义不变 |
| `src/lei_signal/research/qualification_bundle.py` | 新增：验证任务级证据包、解析事实记录并适配已有listing_evidence参数；不是新质量引擎 |
| `scripts/prepare_momentum_qualified_inputs.py` | 新增：离线证据核验、派生快照、新协议生成，拒绝覆盖 |
| `tests/unit/test_qualification_bundle.py` | 新增：事实身份、时间和来源反例 |
| `tests/integration/test_momentum_qualified_inputs.py` | 新增：证据→快照→现有研究入口的完整测试 |
| `tests/unit/test_momentum_prototype.py`、`tests/integration/test_momentum_prototype_cli.py` | 仅Task 0及新可选接入的兼容性测试 |
| `docs/experiments/fixed-etf-evidence-integration-2026-09-13.md` | 新执行报告，沿既有模板 |
| `docs/experiments/raw/research-fixed-etf-evidence-integration-2026-09-13/` | 所有新协议、证据引用、解析件、快照、运行/失败/日志/指纹 |
| `docs/experiments/registry.json`、`docs/experiments/INDEX.md` | 最终对应报告登记和导航，保留并发修改 |

不改 `data_quality.py`、`data_snapshot.py`、`trading_calendar.py`、`symbol_identity.py`、`definitions.py`、`factor_runtime.py`、账户适配及生产/API/UI。确需改这些文件，只记录阻断与最小反例，继续其他任务。

## Task 0：把最后的有限边界并入本轮，不单开修复任务

主控§10已确认原早/晚/null时间反例修复；以下是新输入接入前的有限补充，不重开A/B/C2/D1。

- [ ] 读取 `raw/momentum-prototype-controller-review-2026-09-13/closeout-run-01/summary.json`（实际前缀为 `docs/experiments/`）。复现两个反例：历史模式中2025-06生效、2026-01才可得但评价期到2026-02的行动，不应标“非事后重建”；同一期所有产品的目标均不可知时，不应KeyError退出3。
- [ ] 先补失败测试：历史状态按真正受影响的信号/目标时点判别，而非仅和评价期末比较；空配对期输出n=0、value缺失及明确原因。保持正常控制组，不变计算公式。关键空期约定：

```python
empty = pd.DataFrame(columns=["momentum", "target"])
assert rank_diagnostic(empty) == {
    "n": 0, "value": None, "reason": "fewer_than_three_pairs"
}
```

- [ ] `target_label_status`分清端点未成熟、端点缺价、行动不可知、可用标签；当前不能用“总行数减行动不可知数”把原本future_incomplete行计为complete。逐行保留原因，分类采用明确优先序避免重复计数；总数与各互斥状态对账，诊断配对数另报。
- [ ] 15:00当前是测试中按收盘设的保守截点，不是已证实的实际决策时刻或数据到达时间。保留现有合成行为，但文档/元数据明确 `observation_cutoff_assumption`；真实研究缺报价可得依据仍受限，不能凭15:00字段获准。
- [ ] 协议历史修正：当前标v1.0.3文件为1c8d99…，不是此前主控核验7d7562…原件。主控已在 `closeout-run-01/recovered-protocol-v1.0.3.json` 重构出**字节哈希与7d7562…完全一致**的证据件，重构依据在summary。保留1c8d99…文件且加旁置说明，不再称原件；链接原历史指纹至重构件并注明来源，不偷偷覆盖。
- [ ] 跑本轮动量两份局部测试，保存真实命令/日志。恢复件无需改动；旧772值保留。Task 0失败只阻断新的真实计算，Task 1–3资料核对仍可继续。

## Task 1：冻结新协议，盘点本地可用材料

- [ ] 保存工作区状态、git HEAD、实际源码哈希、原896项保护基线和本轮额外只读文件哈希；正式运行前固定 `protocol-v1.0.0.json` 及现行 `protocol.json`。规范/对象/输入/源目录/禁止范围/输出预算/实际授权原话进入协议。协议在最终实现锁定后绑定实际CLI与新增模块哈希。
- [ ] 第一轮只读下面四组明确本地材料及其中的source-manifest/原文引用，不扫描用户桌面、不无限恢复旧历史：
  1. `docs/experiments/raw/research-mixed-evaluation-2026-09-09/historical-qualification/`：已有515050、562590上市公告线索；159516等名单外产品只注明不在本轮，不接入。
  2. `docs/experiments/raw/research-rotation-clean-2026-09-09/full-pool-preparation/action-sources/`：normalized-actions、分红拆分原始来源、515050/512890/515880官方拆分资料。
  3. `docs/experiments/raw/research-rotation-clean-2026-09-09/full-pool-preparation/515300-official-qualification/`：六份已保存官方分红原文/文本、七次事件清单；第七次的二手限制不能抹掉。
  4. `docs/experiments/raw/research-calendar-completion-2026-09-10/` 与原数据来源报告：只复用现有日历资格和publication证据，不重建日历或查询网络。
- [ ] 本地来源读取上限80个文件（目录清单、重复哈希识别不计原文复核次数）；超过先列未核清单不扩读。PDF需要时按可用PDF技能读取，已有文本只作抽取索引，关键日期/单位回到原文页核对；扫描件无法可靠抽取即待核。
- [ ] 输出 `source-inventory.json`：源路径、SHA、已有来源清单绑定、适用产品/事件、原文可读性、历史来源是否可验证、重复关系。链接失效和缺文件独立记录；“仓库保存了”不等于“官方内容已核实”。
- [ ] 同步输出 `needs.csv`：固定14只首报价/评价期、每条行动的事实缺口、时间缺口、影响用途。先建立需求集合，再抽取文件；不为凑14份证据去写结论。

## Task 2：把原文抽成可回查的事实，不把时间猜成精确值

本轮任务级数据格式仅JSON：`evidence-bundle.json`，不是第二份对象登记表。最小字段：

```json
{
  "schema_version": "fixed-etf-evidence-bundle/1.0",
  "synthetic": false,
  "records": [{
    "record_id": "task-local-stable-id",
    "instrument_id": "515300.SS",
    "fact_type": "cash_dividend",
    "event_id": "exact-id-from-frozen-actions",
    "facts": {},
    "source": {"path": "actual-local-original", "sha256": "actual-64-hex"},
    "locator": {"page": 1, "section": "exact-location"},
    "short_supporting_text": "short excerpt checked against original",
    "time_evidence": {
      "kind": "unknown", "available_at": null,
      "published_date": null, "not_before": null, "not_after": null,
      "timezone": "Asia/Shanghai", "basis": "actual evidence or explicit missing"
    },
    "facts_verified": false,
    "historical_availability_verified": false,
    "allowed_for": [], "limitations": []
  }]
}
```

这是字段示例，不能原样把占位文字当记录；每一条实际值必须由本轮合法输入产生。未实现校验前不称接口可用。

- [ ] 上市事实区分上市交易日、基金成立日、募集日、第一笔缓存报价日；只有明确上市交易日能给listing_evidence。身份须原文或可验证关联来源支持，不靠文件名/基金简称猜代码。
- [ ] 分红明确“每10份”到“每份”的单位转换（独立手算如0.6610/10=0.0661），核登记/除息/发放日期；拆分方向必须说明旧1份变新几份。金额、日期、事件ID与冻结记录逐字段比较。
- [ ] 每个真实变换保留原文值、规范值、变换规则及来源；原始normalized-actions不修改。来源间冲突进入conflicts表，本轮不自动选择有利版本，不重新计算受冲突影响的真实值。
- [ ] `fetched_at`只记录本次读取/已有取得时间；文件修改时间、URL日期、文内落款日期不能自动当真实发布时间。只有来源确实证明“在某日公开”的情况下才记录相应时间界限；日期界限不是精确available_at。
- [ ] 完整历史可得性不足时，`available_at=null`保留。时间界限作为旁置证据；本轮不把“某日已公布”的保守界限直接写进旧卡要求的精确时间字段。需要让界限进入正式资格判定，必须另有版本化时间规则和授权，本轮只列差异。
- [ ] 形成按产品/事件的“事实已核/时间已核/未核/冲突/不适用”表。六份515300资料是待逐份验证的已有线索，不预设本轮全部自动通过。

## Task 3：校验证据包，并适配已有上市证据参数

**新接口合同：**

- `validate_evidence_bundle(bundle: dict, *, root: Path, universe: set[str]) -> dict`：返回records_validated/rejected/conflicts/unresolved，逐项到record_id和原因。真实与合成分开；只有来源存在、SHA匹配、定位及字段规则通过者能被消费，错误记录不能从报告中消失。
- `listing_evidence_from_validated(validated: dict, *, out_dir: Path) -> dict`：生成现有listing验证器支持的桥接JSON及path/sha256引用。桥接记录额外绑定原始公告路径、SHA、页码及抽取规则，不能用自签JSON凭空认证事实。

实现前阅读 `_verify_listing_source/_validate_listing_evidence` 当前完整合同；由Task 2已核事实构造字段，不改变底层验证器。接口签名用于约束分工与输出，验收要求下列实际校验行为全部有代码和测试。

- [ ] 先写独立失败测试，覆盖：假路径/错哈希、同名错交易所、成立日冒充上市、无原文定位、相互矛盾日期/金额、合成记录冒充真实、同ID冲突、重复记录、未验证用途不允许。每个反向配合法正向。
- [ ] 实现实际文件哈希/唯一身份/事实字段/枚举/来源定位/时间格式及范围检查。不能仅靠 `facts_verified=true` 放行；测试将此值强制改true也不能越过底层证据检查。
- [ ] 合法listing记录生成临时JSON再用已有 `check_snapshot(..., listing_evidence=...)` 实际消费。哈希对上只证明内容未变，报告另列真实性核查范围和来源限制；不把机器字段校验宣传成官方事实自动认证。
- [ ] 读取前后比较原数据在六种用途上的判定及逐条finding。只允许证据确实解决的具体发现改变，未解决时间/缺价/数据声明限制保持；没有资料的产品仍出现在全池需求表。
- [ ] 运行 `python3 -m pytest tests/unit/test_qualification_bundle.py -q`；导出真实已核条目与合成测试分别的记录，不混在同一准入集合。

## Task 4：生成独立派生快照，填上真实计算列但不伪造资格

- [ ] 新CLI先核原输入哈希、登记来源及Task 3证据包；来源冲突或完整性失败先拒绝受影响阶段。重新抽取官方材料不得悄悄修正名义价、分红金额或事件日期。
- [ ] 复用 `reconstructed_economic_index` 与已核适配生成每产品economic_index，加入新目录CSV；名义OHLCV和日期行保留，原CSV不改，缺失保持缺失。基准仍为原首次有效报价I=1，不因本轮选点重新起算。
- [ ] 新snapshot绑定原snapshot及每份源CSV SHA、行动SHA、证据包SHA、变换代码/规则、实际派生时间；字段级说明close仍为名义价、economic_index为事后重建指数。未知available_at不填，`historical_reconstruction_only=true`不能因补列被清掉。
- [ ] 完全离线读回派生snapshot，hash篡改能被现有加载器发现；实际 `bind_definitions` 检查两个对象的字段。报告分开“missing_fields减少”和“用途仍受限”，不把directly_satisfiable当真正合格。
- [ ] 算术核验：动量772正式键与旧run-04保持；所有新经济指数用独立正向份额/现金核算抽核，分红/拆分边界做逐值对比。不能仅调用同一重建函数两次。
- [ ] 完整价格缩放包含每份现金分红；负价、无穷、全缺失、重复日期、未来追加不改变过去信号均有测试。日期/身份/缺失原因精确一致，数值atol=rtol=1e-12。

## Task 5：接到现有动量入口，保持旧模式兼容

- [ ] 新协议可增加 `research_evidence={path,sha256}` 可选字段；省略时保持旧行为。存在时必须验证证据包，相关模块进入codes必需键并锁实际路径/哈希；错误引用或校验失败退出3，不能忽略证据后仍称已绑定。
- [ ] 只把验证过的上市事实适配到现有 `_check_real_inputs`→`q.check_snapshot(..., listing_evidence=...)`。公司行动时间证据若只有日期/界限，旁置展示，不补写available_at，也不把预期声明当作已取得事实。
- [ ] 用新派生快照、同池同区间跑一次完整输入检查和一次历史诊断；报告从原始输入→证据→派生输入→对象绑定→用途检查→计算输出的对应身份。
- [ ] 真正预测分支只有所有实际要求满足才允许运行一次，不靠补经济指数列/改uses/缩区间/剔产品获得合格。本轮现实预期仍受限：给出机器拒绝与具体原因，不强行输出真实排序相关。
- [ ] 生成独立新编号终版合成示例，验证真实模块路径正向、未知/晚时间/全配对排除反向；不能通过patch质量结论来证明资格合格。Task 0新边界必须包含。
- [ ] `python3 -m pytest tests/integration/test_momentum_qualified_inputs.py tests/unit/test_momentum_prototype.py tests/integration/test_momentum_prototype_cli.py -q` 实跑保存日志。不得覆盖旧run-04/05/09或主控目录。

## Task 6：把“下一份资料到底要什么”写成可执行清单

- [ ] 输出 `qualification-delta.csv`：每产品/事件、原发现、补充来源、变化后的发现、是否解除、仍影响何种用途、需要哪份确切材料。未变化也是结果，不按消除多少告警排行。
- [ ] 输出 `consumer-map.md`：本轮入口已接入哪些证据/派生字段；原v0、账户、生产、UI仍未接入；严格时间卡无法吃日期界限的差异单列，不能全仓升级名字冒充迁移。
- [ ] 输出 `remaining-acquisition-request.md`，只列固定14只实际缺的官方上市/行动公告、历史发布依据，不默认索要全市场日历或大量行情；排出最能改变研究资格的顺序。
- [ ] 单列**待用户明确授权的后续联网阶段**：最多40次请求/20份资料，只访问相关交易所、基金管理人官方披露或其已核合法公告附件；无登录/密钥/付费/绕过限制，不拉行情、不扩池。这里只提供范围建议和来源线索，当前绝不执行，也不因此暂停本轮离线交付。
- [ ] 外部因子/工具只保留钩子：在数据资格与实际问题明确后才考虑Alphalens兼容，Qlib Alpha158已审结论不变；本轮不重新审包、不下载、不安装，不把后置项写成进展。

## Task 7：一次交付与最终验收

- [ ] 正式计算前锁定终版代码和协议并保存不可变版本文件；输出manifest引用该版本文件及哈希，current指针只是导航。别在运行后改协议再声称原运行属于终版。
- [ ] 最多2次完整回归；采用现有368项的20文件集合再加本轮两份新测试，实际计数实报。局部测试按需；真实历史最多1次，纠错仅允许1次新编号复跑；不以此额度授权任何账户路径。
- [ ] ruff检查本轮变更文件；manifest/输入/输出/原保护基线逐文件核验；报告链接检查。日志、全SHA、失败史、实际命令写入任务证据目录，不留仅/tmp的唯一交付。
- [ ] 报告使用既有模板与决策卡，分类“数据与质量 / mixed”。一句话说清：哪些真实事实更可信、哪些用途仍不能用、已经接通的实际程序是什么、下一项是否需要授权；不得说资料已全清零或策略有效。
- [ ] registry/INDEX仅登记本报告，引用本计划和主控最新复核；不写OKR、不提交git、不顺手改生产。完成即停，统一交回主控。

**完成标准：** 第三个AI可从原始公告定位→事实记录→证据验证→派生快照→对象/用途判定→实际结果逐段追溯；已知缺口不会因补元数据消失，合法输入能复算同一结果。工程完成和真实研究资格分别验收，允许“资料仍不够，但明确知道缺哪份、为什么影响结论”。

**中途阻断规则：** 仅暂停受影响部分。Task 0有待修边界时仍能核公告；缺官方原文时仍能交证据矩阵/拒绝测试；未授权联网时完整完成离线部分。不得因为等待资料而新增指标、换池、跑其他历史策略填时间。
