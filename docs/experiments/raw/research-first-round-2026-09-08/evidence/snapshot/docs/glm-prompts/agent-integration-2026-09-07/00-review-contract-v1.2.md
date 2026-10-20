# 总控补充协议 v1.2：01/02验收返修

2026-09-07，由Codex总控定稿。产品目标仍以00-product-goal为准。本文件覆盖00-controller-decisions A2/A4中尚有歧义的实施细节；不改策略、排序、资金和自动交易边界。主流程仍是标的讨论→必要补测→资金与进出讨论→完整计划。

## 1. 共用引用：保留兼容字段，补全事实

共用实现位置继续为 `src/lei_signal/data_provenance.py`。内部协议增加 `schema_version`；已有API字段暂保留为兼容别名，不静默改变旧字段含义。SQLite已部署迁移不得重写，用后续增量迁移补字段，旧记录标来源质量不明。

| 对象 | 规范字段 | 兼容处理 |
|---|---|---|
| 研究引用 evidence_ref | id、source_path、source_hash、source_version、status、window、statistic_kind、strategy_scope、limitations、compatibility | evidence_id→id，source→source_path，strategies→strategy_scope，note→limitations；status照抄明确来源，不推断有效性 |
| 行情引用 data_ref | source_id、instrument_id、market、observed_at、available_at、generated_at、last_valid_at、health、reason、calendar_ref、as_of_cutoff、source_policy_ref | source→source_id；ok→fresh、partial→incomplete，其余按实际状态映射；旧completeness仍保留 |
| 规则引用 rule_ref | rule_id、version、config_path、config_hash、definition_ref | 文件路径字符串可以保留给旧消费者，新记录必须保存实际版本及内容摘要；fallback要记录采用值与原因 |

`source_hash` 为实际读取材料的完整SHA256，文件哈希与条目ID一起保存；来源有多个文件则引用列表，不能把拼接字符串当一份可追溯文件。快照引用和必要字段随记录冻结，不能到展示历史时再读取今天文件充当旧依据。

时间未知用null及原因；历史字段里的"unknown"由适配器转为null，保留原值在legacy原文中。mtime只说明文件改动时间，不证明数据当时已公开。用户输入单列 origin=user_input。

兼容性枚举：`exact/reference/unknown/incompatible`。exact要求本标的、同模块/入场/退出/条件/期限/规则/费用与可用数据窗口匹配，保存source_run_ids。现有module_winrate表因配置不全默认为unknown；明确不同对象或条件为reference/incompatible。缺字段不能猜默认配置。本轮不重新设计收益实验。

## 2. 日期与当前状态

取消统一5交易日宽限作为“当前”依据。数据按其市场、对应交易时段和来源既有发布时间评价；没有可核实的来源周期，health=unknown。可额外显示本机参考滞后天数，但参考文件本身过期时不能据此标fresh。未来时间、空值、重复日期、窗口不完整需显式处理。

只读新增或复用独立日历适配器，不改变全局 `DEFAULT_TRADING_CALENDAR`，不影响既有周线和监督规则。适配器返回市场、时区、来源、内容摘要、覆盖范围、可信的交易日序列及数据截止。已有WeekdayCalendar未装节假日，不能当交易所完整日历。查不到可靠日历时返回未知，允许先交诚实降级版本。

每个state分别返回 `active:true/false/null`、`data_refs`、`health/reason`、`current`。`current=true`只在该state全部必要依赖已确认及时且有效时成立：deep20只依赖价格，bottom_zone还依赖宽度，不能相互误挡。缺数据=null，条件不满足=false；旧API布尔值暂保留但新消费者必须读结构化状态。旧数据触发只表示历史状态，不称当前机会。保存快照截止与有效日期，不能只用响应生成时间。

## 3. 保留两表存储；展示批次与可评价主张分开

继续使用agent_observations与agent_observation_outcomes，不再新建另一套账本。增加必要字段承载完整展示批次（`record_type=display_batch`）和单对象主张（`record_type=claim`），批次没有结果期限、不进命中分母。批次保存完整卡片/实际展示文本、成员ID、来源修订键、前一批次ID；空列表也是一份有效展示。

批次当前版本以来源自己的稳定修订序列为准。没有序列的现有封装在事务中比较当前批次内容：内容未变复用当前批次；变化则新建批次并链接前一批次；A→B→A也保留三次展示顺序。带明确旧修订键的重试不能重新成为当前。旧数据迁入独立标legacy，不接管实时当前版本。

主张ID为完整SHA256，规范输入包括来源记录/对象/用途、claim、direction、payload、input_hash、规则/证据/数据引用、评价kind/version/config及期限；排除重试运行时间。不因缩短到8位导致可避免的身份碰撞。相同语义快照可复用主张，但批次成员关系必须记录，不能靠是否insert新对象判断删除/清空。

当前对象集合从当前展示批次的成员读取；单条superseded_by不是唯一权威。旧正文和原评价配置不可覆盖。展示失败/尚未输出给用户时不得写成已展示；如需记录生成过程，另标未展示，不进前向统计。旧记录不能补造实际展示时间。

## 4. 评价身份与研究分母

结果的所有读写必须显式完整匹配 `(observation_id,evaluation_version,horizon)`，版本不可省略。原评价配置保存 `evaluation_kind/config_hash`；改方法产生新版本，不给新方法借旧成绩。

另存 `sample_key`：来源类型、策略、标的、观察交易日、主张类别/方向、规则与评价配置共同确定。纯措辞/展示修订不得增加同组研究样本；每次展示原文仍可单独查询。同sample_key结果冲突则标conflict并排除比例，不能选较好的那份。

汇总分组至少包括source_type、strategy_scope、evaluation_kind、evaluation_version/config_hash、规则版本、direction、horizon和legacy_quality。查询同时支持instrument过滤与适用对象范围。`n_observations`展示记录数、`n_samples`去重后样本数分别返回；ready/pending/missing/not_applicable/conflict都可见。只用有效ready样本计算带方向命中率，未评价成功不能进分母。旧结果按旧版本单列，不与重算版相加。

展示批次ID不是独立恐慌事件ID。无冻结的历史事件划分，`independent_event_count=null`并说明未知；不拿板块数量/日期数量冒充独立事件。普通技术观察不报交易胜率；所有ready必须有有限有效数值与日期。

## 5. 到期、缺日和恢复

保留推荐1/5/20、情绪10/20交易日观察方法，不借机新增15/36等期限。现有错误的“按剩余行数”结果不改标签冒充严格交易日结果，记为legacy/available_rows参考；修正后的日历评价使用新版本。未知日历可先暂不产生ready，不要求GLM自行采购或拼造日历。

评价窗口以对应市场已完成交易时段为准，并受指定as_of截止约束；行情或资料晚于截止不得使用。起算日、目标交易日必须明确；缺目标价格标missing_data，数据后补到位再检查；不能跳到下一条有效价格替代。同日收盘到未来收盘只是观察变化，不宣称该价格可实际成交。

pending=尚未到期/尚不能确定到期；missing_data=到期数据缺失或无法完成计算，允许后续重试；not_applicable=主张不可按此方法评价，需明确原因。取消“60自然日后永久停止检查”的隐藏终止标准。ready结果按原数据快照冻结，历史价格修订需要新评价数据版本，不原地覆写。

JSON情绪日完成必须逐对象逐期限检查，不能只检查组键；旧格式无对象对应证据时不能按位置猜配。记录与新表同步须可重试且状态可见，失败不能打印统一存证成功。dry-run对两边均零写入、零通知。每个对象的坏数据隔离，不阻断其他对象。

## 6. 旧库迁入及旧接口

当前不自动迁入真实库。先提供只读preview：拟迁条数、同日修订、卡片/成绩不一致、无法考证来源、迁入后各组计数。能恢复原文的保存原文；不可证明旧成绩属于哪张卡时标unknown隔离，不能按同标的同日就强行挂上。

返修通过后才进行有备份的一次迁入，迁前后计数与内容摘要核对、失败可回退。普通每日任务只处理新记录/到期/缺数据重试，不隐式执行一次性全量迁入。旧journal公共读接口必须返回与当前卡片版本匹配的成绩，否则明确无匹配结果；先保全旧记录，不能直接清空唯一历史。

## 7. 下一批输出与只读成熟度

固定kind：`technical_forward_change`（推荐价格观察）、`sentiment_direction_change`（情绪方向观察）、`discussion_claim`（03实际展示且有明确可检验定义的主张）、`plan_rule_followup`（04按计划原逻辑检查）、`non_evaluable_explanation`（解释/假设，无胜率）。现有kind通过兼容映射读取，评价版本不可因改名混用。

discussion_claim必须附具体评价配置，不能把所有对话句子都变成信号。计划资金讨论和执行记录仍遵守原确认边界；不存在实际交易时不算实际盈利。定投月/季预期后排，等方法定稿。

语义状态只附可比样本数量、等待/缺失数量和有效方向比例，不自动改研究status、推荐次序、技术信号、仓位和行动权限。基本面/消息仍是解释层，不能自动加入硬过滤。
