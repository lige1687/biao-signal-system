# 黑绿变化事件＋上一完成周颜色：语义与证据链补充审查

日期 2026-10-04T22:49:05.980425+08:00，report_only。受审成果a8227e62eead2745d90cf65b14875340015076d5；接续基础3029717c5d6160a230293f2eae61dfb613ce7071。原负责人自查证据包，供另一对话独立复核，不冒充外部审查已通过。本附件替换上一条聚宽方法采纳任务的当前目标，不覆盖其历史。

## 一句话结论（大白话）

本题确实测了“日线刚变色后，周线颜色还能帮助多少”，没有测完整的原文买卖流程，也不能据此说黑色本身没用。原始报告已披露这一范围。本次补清多头排列没有用于筛除样本、“首次”仅指一次连续同色段的起点，以及首个冻结定义三处文字变动。没有新增行情计算或修改原成绩。

## 1 原文→对象→代理范围

两份桌面原文现行SHA再次读取，列process-review-evidence.json/source_documents，与原冻结报告一致。原件不上传；仓库已存在的快照路径为docs/research/strategy-source-snapshots/2026-09-30/对应文件；原权威仍为桌面两文档，不以历史trading-spec-v1代替。

- 《LEI 技术交易体系》§2.7，191–205行：双条件向下、黑绿灰语义、多头/空头排列下不同用途、找多头排列→见黑→等绿，以及日周变化共振。特别是202行要求多头排列前提；203行存在跨日等待顺序；205行还指出横盘噪声和急反转缺陷。
- 《LEI 技术实现》§3.2，166–178行：收盘后生成信号、最早下一根开盘执行，周线完成才可用，行动尺度一致。§4.2定义ref(close,N)；§8.1定义同时跌破EMA20与20日前价。本文研究目标起点采用下一根收盘，不能冒称原文下一开盘成交。
- 准确对象：research.trend.daily20_non_green_to_green_week_context@1.0.0 与 research.trend.daily20_non_black_to_black_week_context@1.0.0；共同依赖research.trend.completed_week_color20@1.0.0。冻结完整定义在四contract.json的bindings.definition_closure，不用当前卡倒填旧实验。

| 条件 | 实际保留/省略 | 结论边界 |
|---|---|---|
| 20日判色 | 收盘对EMA20及ref(close,20)严格双高为绿、双低为黑，其余灰；未知单列，首20均值播种EMA | 明确研究计算定义，不把完整作者工具所有构成声称已复原 |
| 多头排列 | min(SMA20,EMA20)>max(SMA60,EMA60)，作为bull_group进入模型并分别展示；不作事件纳入硬条件 | 这是原交易条件的有意放宽，不是默认所有样本多头，更不是原文完整触发验证；排列分层描述不证明该子组有独立增量 |
| 首次转色 | 相邻有效日从其他两色进入目标色；每一段同色连续段只记录起点 | 不是一个趋势周期首次回调，不是先见黑再跨灰等待后的首次合法入场；多个事件可能同轮行情 |
| 周线 | 只用前一ISO周，当前周即便周五已收盘也不用；120周/252日暖启动为代理设定 | 比原文“周末完成即用”更迟；不是日周同时转绿精确共振 |
| 完整交易 | 未要求持仓、完整见黑等绿状态、结构失效、小时确认、时钟2点/4点环境；无资金/费用/成交 | 黑色是局部状态变化，不能直接叫卖出点；未检验完整原策略盈利 |

源码定位：src/lei_signal/research/color_event_information.py::prepare_observations（event、reason、bull_group字段）；technical_persistence_information.py::_segment_features（颜色和排列）；weekly_color_information.py::_weekly_history（完成周映射）。color_event_information.py开头说明及验证错误提示只写green，是遗留的不完整说明；实际event_color分支支持black，原执行/独立事件证据已覆盖两色。本次记录问题但不为文字改动改写冻结源码指纹。

## 2 冻结、来源、代码和时间

四分支统一raw/core/<green-return20|green-mae20|black-return20|black-mae20>/core-01/contract.json、receipt.json、result.json。freeze-01用于第一支，其余使用各自原冻结版本，准确路径从现有目录/账本定位；不得按新规范重冻历史。

process-review-evidence.json逐项保存本次实际合同/收据SHA、所有bindings.files的当前/冻结SHA、原输出回执SHA、原规范版本与定义差异。四合同本次均与收据一致、原输出均匹配、绑定代码/规范文件均匹配。定义闭包另有首支三处差异，不能用“文件指纹全匹配”掩盖闭包漂移。

输入docs/experiments/raw/volume-information-2026-09-30/execution/panel.json：1,582,974字节，SHA382d82ff21cb43758bca8e596026284ba2821038a79e1b4c331135119524679b；source-manifest SHA a0c3b15bc56ac34c4538ac9b11e505a83c0f8bed97175459d7eccb74c2b11c94。本次重新核相同。完整来源文件及原价行动审查沿冻结sources与preflight，本次未重新下载/复查全部原件。历史实际到达/全部行动完整性仍未认证。

观察时点为t完整收盘后；周背景仅前一完成周。目标为t+1到t+21共21个收盘、20报价间隔，return或起点到最低收盘下探；真正成熟还需要t+21报价实际取得。训练label_end严格早于评价开始，评价label_end不晚于本期结束；两折截至2024末→2025、截至2025末→2026H1。日历可推导理论成熟，不能替代供应商当时真实到达记录。已有全部历史已见，非盲验证。

## 3 问题、方法和共同比较

问题是指定日色变化事件内，加入周类别能否改进未来20间隔收益/风险判断。类别本身不要求排序；用固定ridge1比较已有背景与新增两列周绿/周黑适配有限问题，但不穷尽非线性/所有模型，更不以负结果宣布永久无效。方法局限、小样本及未事前规定最小关注幅度均保留。

B1字段为ret20、ret60、vol20、bull_group及三ETF身份列；B2仅加week20_green/week20_black，没有周涨幅20/60。每个用途B1/B2使用相同ETF、事件日期、目标、训练成熟规则和权重；训练与主评分均每ETF同等总权重。简单整体训练均值、每ETF训练均值、ETF×周色均值并列；未知历史组的回退按原规则保留。描述表是每事件同等权重，不能和主评分权重混为一谈。

原报告成熟全历史绿142/黑167；较晚主评分绿64/黑59；两者分母不同。多个ETF同日及窗口重叠不当独立事件，原连续日期敏感性已保留。风险概率使用过去频率，是另一个统计估计器，不是新的已校准交易概率。

## 4 已有独立证据及本次发现

- 语义/设计：原contract.research_design.claim_mapping及controller_review，报告“原文到可计算定义”，controller-record.json；属于本负责人审查，不冒称另一团队已确认。
- 事件独立算法：independent_events.py与independent-events.json，325事件；未直接复用正式适配器计数。原暖启动前日周资格误读已纠正/保留日志。
- 数值独立复算：review_numbers.py及independent-numeric-review.json，直接价格重算目标并由保存系数核预测，最大差8.88e-16，四分支简单对手独立核对。没有重拟合。
- 保存产物恢复：verify_saved.py/evidence-index.json/portable-check.json，独立14文件目录正例exit0、篡改副本exit1；只证明保存算术，不证明原行情跨机器可恢复。
- 工程：原两新增测试通过；相关66通过3缺旧夹具失败，原失败未抹去；本次不重跑。

新增准确补充：首个green-return20冻结闭包与当前同ID@1.0.0存在三处变化：definition.transforms、status.definition_clarity、validation.tests。前一勘误逐项只列transforms，披露不完整；本附件及JSON补全另外两处原值/现值。原注册版本号未随说明更正改变，故仅ID@版本不足恢复该首支，必须以其完整合同和旧快照SHA6e10a6819254cdce3ef24b4b8e54e6c3e9d253f983ecf49ad1a1a93da01619e7定位。原历史隔离快照核验和发布证据见historical-snapshot-verification.json、registration.json；不覆盖原收据/成绩，原数值代码不变。后续三分支闭包与现行相同。

定义登记status.effectiveness仍为not_evaluated，是定义卡保留的建卡状态，不能作为最新实验结果；现有登记和报告记录本题completed/not_supported。当前存在静态定义状态与结果状态不同步的阅读风险，本附件明确区分，不为这次审查静默改旧卡或倒填效果。总研究对象永久有效性亦不能用本局部实验状态替代。

## 5 报告、登记、聊天与尚未解决项

原5条报告登记逐项附process-review-evidence.json/report_registry_entries，4子报告+总报告均存在。总报告“本实验范围内未发现实际增量”准确限定为**已有日线变化事件内，上一完成周颜色的额外价值**。聊天已明确纠正：黑色不需必跌，只需相对合理的事前基线有稳定帮助；本题不能代答黑色本身有没有帮助。报告/代码未扩大为生产或全Universe。

效果证据复用：原总报告性能表（绿142次平均+0.512%、黑167次+0.083%，非收益增量）；同条件四项预测误差差额−0.236484/−0.037705/−0.010469/−0.016543个百分点。此附件不是新的市场效果结案，无新统计、期限或模型；不为附加审查另建重复实验登记。

未解决：严格原文多头排列＋见黑等待＋持仓/小时触发的完整语义研究未由此题覆盖；黑色本身应引用其准确旧题而非此题推断；扩池127文件的行动、日历、历史选样、实际到达与许可缺口保持，六ETF18旧文件存在不等于本轮六ETF效果已完成；真正未见未来数据和完整市场跨机器恢复未验证。所有来源条件只能说有限回顾重建，不能概称已获完整历史资格。

本次新增仅审查说明/逐文件证据/自有进度，0新模型拟合、标签、行情、安装、付费、代理或跨对话回复；旧预算保留。外部主控独立审查待验收，具体问题再按原授权最小处理，不预先增加新实验。

## 6 P2返修：四类黑色问题的实质覆盖表

外部审查指出上一规划“黑色本身应先引用旧定义”仍留待办却标规划完成，指正成立。上一条完成仅能指方法取舍文档，不是四类问题证据已全部核清。现追加实际覆盖；未覆盖不能从“下一步扩池”中消失。外部报告称已独立核246条评价标签，此处只记收到的审查意见，不代替对方将交的独立审查原件。

| 问题 | 精确规则/对象与合同 | 实际报告、支持范围 | 仍未覆盖 |
|---|---|---|---|
| 每日20黑色状态本身相对合理基线有没有帮助 | legacy configs/rules.v1.yaml::lei_color@1.0.0（并非definitions正式对象）；原合同docs/experiments/raw/lei-regime-increment-2026-09-29/protocol.md，结构化后录question.json不冒称事前注册 | lei-regime-increment-findings-2026-09-29.md：六ETF每日SMA下行样本内增加EMA同向确认，10间隔下探风险；简单单线预测误差2.905→2.895，平方误差改善0.69%，区间−0.78%至+2.09%；已有环境后3.214→3.203，改善0.69%，区间−0.71%至+2.28%。是微弱历史线索，非已可靠有效 | 非首次事件、未要求20组在60组上方，不是完整持仓退出；用途/期限经旧探索选择，真正新资料未验证；旧合同/小审查在主目录存在，本隔离树缺旧raw，不能称该旧题已可在远端完整恢复 |
| 日20首次转黑事件本身比不转黑有没有帮助 | 最新对象research.trend.daily20_non_black_to_black_week_context@1.0.0能定位事件，但没有独立“事件本身增量”合同；现有core/black-return20/core-01/contract.json与black-mae20/core-01/contract.json只在事件内比较周色 | 最新color-event-week-context-and-universe-2026-10-04.md保留黑事件167次成熟表现，属于事件内描述；不能用它与不同日期绿色组均值差认定事件增量 | 尚无该题相同背景下转黑/未转黑的正式配对效果结论；连续段起点不是趋势生命周期首次，不能伪造独立新对象ID或说本题已经完成 |
| 多头排列前提下转黑是否有风险/退出信息 | 原文§2.7第202–204行与legacy lei_color@1.0.0 + 排列条件；最新周色对象里的bull_group只作输入/描述，不是此完整问题的正式合同。当前审查未定位本线独立“多头转黑”效果合同/正式对象；不杜撰ID | 最新报告与core/auxiliary.json只有排列子组描述，可定位但不能代替该事件专属增量。旧每日10日EMA确认报告也不限定多头前提 | 多头前提下事件增量尚未由上述资料回答；持仓状态/原退出触发与remote-core负责人范围应先协调，不能跨线重启black-reset、账户或改语义。不得用无多头筛选的本轮回归代替原文条件研究 |
| 日转黑后再增加上一周颜色有没有帮助 | research.trend.daily20_non_black_to_black_week_context@1.0.0，依赖research.trend.completed_week_color20@1.0.0；本目录core/black-return20/core-01/contract.json、core/black-mae20/core-01/contract.json | color-event-black-return20-2026-10-04.md、color-event-black-mae20-2026-10-04.md及总报告：四ETF59条较晚共同评价，误差收益5.447450→5.457919、下探4.040473→4.057016；本固定方法范围未发现稳定增量 | 不是日周同时转色、不是全部标的/全部方法，更不是黑色本身无效；扩池及历史真实到达资格未闭合 |

此外research.trend.green_black60_state@1.0.0的green-black-state-information-2026-10-03.md及raw/green-black-state-information-2026-10-03/{return,risk}/accepted-01/contract.json是**60日状态加入已有20日信息**的不同问题，不能填补20日首次转黑或多头前提转黑缺口。

旧10日研究合同已实际从主目录只读，未取/复制旧行情或重跑旧40拟合；protocol/question/controller-review/review/manifest及当前规则、旧报告的路径与指纹追加process-review-evidence.json/coverage_sources。本附件只定位和复用已有独立证据，不宣称本次独立重核旧23070条预测。

后续顺序修正：先依此覆盖表核已授权待答问题和其他owner，再确定尚缺的有限用途；多头前提事件的语义/所有权/可用样本须先明确，扩池不是唯一下一步，也不是数据缺口之外唯一可研究方向。本次指定report_only不启动这些实验。数据维护方负责提供合格资料，主控负责解释研究代理边界，外部审查负责独立验收；原文变更仍需用户确认。
