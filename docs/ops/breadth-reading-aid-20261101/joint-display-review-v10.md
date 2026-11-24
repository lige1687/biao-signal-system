# B50与B200联合查询：大图展示复核

2026-11-02。结论：**可将现有两个联合选项移到大图外显区，保留同日价格／宽度标记，名称限定为数值查询。机构资料支持联合观察思路，但本轮保存证据不能为本地全A20/80、美国15/85这组联合极值背书。** 不新增买卖、顶底或收益结论，不改小图。

本次按 `joint-display-review-contract-v10.json` 只读指定7份输入，唯一新增本报告；网络请求、金融实验、子委派、源码修改均为0。下列代码行号绑定文末SHA，是修改前静态审核；未执行浏览器或渲染测试。

## 实际逻辑与同日投影

| 核查项 | 当前实现 | 判断／对应代码 |
|---|---|---|
| 联合高值 | CN：`B50>=80 && B200>=80`；US：`B50>=85 && B200>=85` | AND、包含等号，不是两者求和或满足其一。[zones.ts:161](/Users/yongbiaoli/Desktop/lei-signal-lab/web/src/components/trend/zones.ts:161)、[166](/Users/yongbiaoli/Desktop/lei-signal-lab/web/src/components/trend/zones.ts:166) |
| 联合低值 | CN：`B50<=20 && B200<=20`；US：`B50<=15 && B200<=15` | AND、包含等号；B20不参与。两条汇总比例同时满足，不等于另算“同一批股票同时低于两均线的比例”。[zones.ts:158](/Users/yongbiaoli/Desktop/lei-signal-lab/web/src/components/trend/zones.ts:158)、[167](/Users/yongbiaoli/Desktop/lei-signal-lab/web/src/components/trend/zones.ts:167) |
| 缺测与边界 | B50或B200为null／undefined不命中；NaN比较也不命中。B200恰为50不进入两个`base`条件 | 无缺测补0或沿用前值；缺测在布尔结果中与已知不满足同为false，展示时仍须区分未知。[zones.ts:164](/Users/yongbiaoli/Desktop/lei-signal-lab/web/src/components/trend/zones.ts:164)、[168](/Users/yongbiaoli/Desktop/lei-signal-lab/web/src/components/trend/zones.ts:168) |
| 日期对齐 | 以所选价格日期为共享轴，按日期Map找各周期宽度；无同日记录为null | 没有前填或移动到下一交易日；宽度有值但价格日期轴不存在的日期不进入图。[BreadthComparison.tsx:66](/Users/yongbiaoli/Desktop/lei-signal-lab/web/src/components/market-style/BreadthComparison.tsx:66) |
| 连续与单日标记 | 按连续命中下标合并；false／缺测行切断。单日用竖线，多日用区间底色 | 不是只画首次触发；区间末日取最后一个命中日，不延伸到下个未命中日。[zones.ts:178](/Users/yongbiaoli/Desktop/lei-signal-lab/web/src/components/trend/zones.ts:178)、[BreadthComparison.tsx:80](/Users/yongbiaoli/Desktop/lei-signal-lab/web/src/components/market-style/BreadthComparison.tsx:80) |
| 上下图投影 | 同一`marks`分别附到价格轴和宽度轴；两轴使用同一`view.dates`，共同缩放 | 已具备同日高亮，无需另造价格条件。当前是日期区间／竖线，不是价格点上的联合触发圆点。[BreadthComparison.tsx:205](/Users/yongbiaoli/Desktop/lei-signal-lab/web/src/components/market-style/BreadthComparison.tsx:205)、[213](/Users/yongbiaoli/Desktop/lei-signal-lab/web/src/components/market-style/BreadthComparison.tsx:213)、[226](/Users/yongbiaoli/Desktop/lei-signal-lab/web/src/components/market-style/BreadthComparison.tsx:226) |
| 回看与市场切换 | 回看日期竖虚线同步两轴；market改变后使用对应CN／US默认阈值，按钮文案随market改变；初始未选条件 | 保留已有`active`、`toggle`和内部key即可。强调周期、三线显示开关不改变联合查询所用的B50／B200。[BreadthComparison.tsx:27](/Users/yongbiaoli/Desktop/lei-signal-lab/web/src/components/market-style/BreadthComparison.tsx:27)、[231](/Users/yongbiaoli/Desktop/lei-signal-lab/web/src/components/market-style/BreadthComparison.tsx:231)、[246](/Users/yongbiaoli/Desktop/lei-signal-lab/web/src/components/market-style/BreadthComparison.tsx:246)、[288](/Users/yongbiaoli/Desktop/lei-signal-lab/web/src/components/market-style/BreadthComparison.tsx:288) |

上方“参与转折观察”圆点来自另一套`breadthChangeAnnotations`，不是联合条件事件；不要用那些圆点数统计联合查询次数（[BreadthComparison.tsx:186](/Users/yongbiaoli/Desktop/lei-signal-lab/web/src/components/market-style/BreadthComparison.tsx:186)、[221](/Users/yongbiaoli/Desktop/lei-signal-lab/web/src/components/market-style/BreadthComparison.tsx:221)）。价格值为null但日期存在时，当前仍可投影日期色带，价格线断开；若以后另加价格点标记，必须跳过无有效价格的日，不能补价。

## 来源能支持到哪里

| 保存来源 | 对象／已读到的内容 | 对本地联合阈值的结论 |
|---|---|---|
| StockCharts ChartSchool | 个股站上各自均线的比例；美股50日<30%／>70%示例，150／200日50%中线；强趋势中极端可持续 | 不是B50和B200同时≤20／≥80或≤15／≥85的出处，也不为本地P10/P90背书。 |
| BofA《The Flow Show》2024-05-31表5索引摘录 | MSCI ACWI中**市场／国家层面**的Global Breadth Rule，`net 88%`市场低于50和200日均线，期限3个月；官方链接已过期，未取得可读正文 | 对象不是全A／标普500个股数比例，`net`公式未完整核定，不能换算成个股88%或12%。保存摘录只支持低侧规则线索，没有核定对称高侧公式。只作来源详情，不迁入本地筛选。 |
| NDR 2025年4月材料，Kathrein承载 | MSCI ACWI 50／200日宽度分为两者Upper Modes、Mixed、两者Lower Modes；搜索表格摘录为1994-05-31—2025-04-04各状态年化12.77／4.17／−1.47%，持有5.61% | 可以说存在联合趋势状态研究；具体Mode阈值未核，截图超时，不能推定为对称极值。状态期间收益表不是触发后的未来收益检验，不能把正负数移成底部／顶部准确率。 |
| 本系统既有设置 | CN B50/B200同时≤20或≥80；US同时≤15或≥85，默认关闭的查询项 | 在这次有界查找中，未核到**同对象、同数值、同联合条件**的机构出处。保留为本地历史数值查询；不是断言任何机构都未研究过。 |

保存事实记录主控本轮6次外部请求、累计17次，其中BofA官方过期、NDR截图失败均保留。**本代理只审保存事实，没有独立重读原网页、PDF或图。** BofA和NDR的数字不得写成“已独立核验的机构绩效”。既有账户研究也不能替代本题这两个联合极值的专门增量检验；高相关或低相关都不提供该验证。

## 需要处理的展示问题

1. **主要选项藏在双层折叠中。** 外层“图表设置与资料说明”始于[319行](/Users/yongbiaoli/Desktop/lei-signal-lab/web/src/components/market-style/BreadthComparison.tsx:319)，内层“更多数值条件标记”始于[336行](/Users/yongbiaoli/Desktop/lei-signal-lab/web/src/components/market-style/BreadthComparison.tsx:336)。把两个联合选项放到大图旁可见行即可；其余四项留原设置，避免同一按钮重复出现。保留内部`reversal_top/bottom`兼容key，界面不用“反转／顶底”命名。
2. **部分缺测容易被误读为已知不满足。** 联合条件遇任一空值为false，但灰带与缺测说明按当前强调周期生成（[267行](/Users/yongbiaoli/Desktop/lei-signal-lab/web/src/components/market-style/BreadthComparison.tsx:267)、[235行](/Users/yongbiaoli/Desktop/lei-signal-lab/web/src/components/market-style/BreadthComparison.tsx:235)）。例如强调B50、B50有效而B200空缺时，不能把“没有联合高亮”解释成已核定未满足。最小处理是可见说明“仅两项同日齐全时标记；缺任一项不作判断”；若显示当前是否满足，必须有“资料不足”状态，不能显示“不满足”。日期下拉目前只检查整条记录是否存在（[345行](/Users/yongbiaoli/Desktop/lei-signal-lab/web/src/components/market-style/BreadthComparison.tsx:345)），不能充当两周期完整性提示。
3. **标签须区分本地条件与外部参考。** 现有固定轨道提示称“固定经验参考”（[332行](/Users/yongbiaoli/Desktop/lei-signal-lab/web/src/components/market-style/BreadthComparison.tsx:332)），前置联合行宜明确“本地数值查询”，不得紧贴机构名字造成其已背书20/80、15/85的印象。P10/P90底色和联合色带是不同统计事实，联合行需有自己的两色图例，不应直接复用“机会／风险”含义。

低优先级输入防御限制：`evalBreadthRule`只排null，没有显式有限数／0—100检查；`viewFor`只把nullish转null（73—75行）。合法JSON数字中若出现越界百分数，仍可能命中。这里没有读取API，也未证明存在坏值；不把它报告成已发生的数据错误。前置展示不应绕过既有输入资格，必要时由控制者决定是否增加防御检查。

## 最小展示与桌面验收

建议可见行：**“同日数值查询　[B50与B200均≤20%]　[B50与B200均≥80%]”**，美股自动换15%／85%；旁注“本地条件，非顶底信号；两项同日齐全才标记”。保留两色数值图例和上下图同日标记；不加新横线、组合得分或机构规则开关。其余条件继续在折叠区。样式可复用[现有`.bc-rules`行](/Users/yongbiaoli/Desktop/lei-signal-lab/web/src/components/market-style/breadth-comparison.css:24)，桌面需实际检查换行后不压缩图。

以下为应验收的预期，**本次仅按源码推导，未运行测试**：

| 输入／操作 | 预期 |
|---|---|
| CN两项恰20或恰80；US恰15或恰85 | 分别命中低／高；等号文案一致。 |
| CN B50=19、B200=21；B50=81、B200=79 | 均不命中相应联合条件，防止AND误改OR。 |
| 中间日B50或B200为空 | 当日无联合标记，两边区间断开；没有填补、没有“已知不满足”结论。B20为空而另两项有效不应阻止联合查询。 |
| 一个命中日；连续多个命中日 | 单日上下图同日竖线，多日上下图区间一致，不遗漏单日、不移动日期。 |
| 切市场、切价格指数、缩放、切强调周期／三线显示 | 市场数值与按钮一起切换；联合条件仍用B50/B200；价格与宽度同日标记及既有选中日期线不丢失。纳指对照仍须明示其宽度来自标普500样本。 |
| 关掉联合选项；同时打开高低选项 | 关闭后旧标记消失；双开分别显示正确日期，无重复按钮／重复区间。P10/P90背景与数值查询含义可辨。 |

## 输入SHA256

| 指定输入 | SHA256 |
|---|---|
| web/src/components/trend/zones.ts | 55432101f0a18bc178ebcdfccb4957829c89152d79072b2aa62d945ba077a855 |
| web/src/components/market-style/BreadthComparison.tsx | 456813e3c8c5d9676c188aae22658577f0bb243134f85ff4a66d044bbdc336bf |
| web/src/components/market-style/breadth-comparison.css | 3b5693603712c1a33953631c0fa285aab73413d2399a8f61741b3fc753718ae7 |
| institutional-source-facts-v8.json | cd32134527d89533b0a736b79f579fd30103b5244678212ecdb121bbd67185fc |
| evidence-review-v6.md | d861479b2929b734c159669034573326f68093917e87738c9557226f2acde6d4 |
| breadth-erp-ma200-increment-review-2026-11-02.md | eb905f76a029ca81637f4f2d2b27afe643a3b2185e94020a1403f3c460edd7c7 |
| joint-source-facts-v10.json | dd1d549769fc3fd2a109ebba859bdce5720a5e5c5193ef477a434c4ce173fbc2 |

任务完成范围：联合谓词、已读源码投影通路、保存来源的归属边界和桌面接受条件。未重算金融效果、未查外部资料、未验收邻owner小图或最终修改后的实页；由主控接续工程验收。

## v10大图改动后的续核

结论：**核心联合展示逻辑通过静态复核，发现一处缺测说明与实际曲线不符，需改文案。** 未发现AND、等号、同日价格点、模式恢复或两类条件互斥的实质逻辑错误。本节对应下列新SHA；此前行号与修改前评语保留为审查历史。

| 项目 | 本次已核内容 |
|---|---|
| 原条件与来源不变 | `zones.ts` SHA与前次相同；仍调用`computeHighlightBands`（新77行）。两市AND／含等号／任一周期空值断区间已有定向测试；来源详情371—373行明确本地20/80、15/85未取得同范围同条件机构验证，BofA对象和完整公式、NDR模式限制保留。 |
| 同日价格点 | 新`jointProjection`在99—110行只取每段起始日；B50、B200及当日价格均有效才产出点。价格缺失则跳过整个起点标记，不挪到后续有效价格。236行明确系列名为“联合条件区段起点”；365行说明截断窗口起点不是首次触发。 |
| 联合缺测灰带 | 101行把任一B50/B200缺测转为联合资料null；283—285行用它生成灰带，同时关闭原参与／分位底色。仅B20缺失不影响联合资料资格。主控日志中相应helper测试已通过。 |
| 关闭后恢复 | track、compare、showPhases、backgroundMode原状态未被覆盖；348行仅在传参时用联合模式关闭轨道、强制三线，285行仅暂时禁原底色，349行暂隐外部参考。最后一个联合选项关掉后回到原值。 |
| 条件互斥 | 306—315行添加条件时删除另一类key；同为联合的两个key可并存，关闭一个不清另一个。旧条件分组368行排除了联合项，无重复按钮。该项本次按源码核查，未亲自执行UI切换。 |
| 桌面截图 | 已实际查看`joint-cn-v10.png`：A股双低／双高按钮外显且同时启用，阈值≤20%／≥80%，上下图竖向色带及价格起点标签可见，右侧读数仍完整；机构参考未与联合模式混叠。单张截图不能证明缺测、关闭恢复或美股交互，主控另验。 |

**待改文案：** [BreadthComparison.tsx:366](/Users/yongbiaoli/Desktop/lei-signal-lab/web/src/components/market-style/BreadthComparison.tsx:366)的联合缺测说明仍称“灰带内不连接宽度线”。实际232—234行逐条保留真实数据，例如仅B200缺测时，B50有效曲线会通过灰带。这不是数据补值，而是文案把联合资料不足误说成所有周期都断线。联合分支应改为：“缺失周期断线，其余有效曲线保留；该日不作联合判断。”普通模式说明可保持。

同一处语义的低成本澄清：[250行](/Users/yongbiaoli/Desktop/lei-signal-lab/web/src/components/market-style/BreadthComparison.tsx:250)无障碍描述“任一周期缺测”宜明确为“50日或200日缺测”，因为联合模式展示三线且B20不参与。没有发现把联合查询写成机会、风险或顶底预测的新文案。

已读测试文件与日志：`breadthChartDisplay.test.mjs:213—232`明确覆盖任一周期缺测及起始日价格缺失不后移；`zones.display.test.mjs:57—72`覆盖两市等号、AND与缺测断段。`tests-v10.log`显示25项通过、0失败。本代理未重跑测试；该日志没有直接覆盖React按钮互斥与关闭后恢复的实际点击流程，静态审查不能冒充真实UI验收。未读邻owner小图、未改源码或其他任务文件。

| 本次输入 | SHA256 |
|---|---|
| zones.ts | 55432101f0a18bc178ebcdfccb4957829c89152d79072b2aa62d945ba077a855 |
| BreadthComparison.tsx | 4e0b03fc8c7efb4341740cc13cb8693ca705e2d257935f2a80f26a6a9882f501 |
| breadth-comparison.css | 180fd85c3294b210e8107ff18425d744eb39f4631652ecf3e8774339780c3b12 |
| breadthChartDisplay.test.mjs | 38a4ba7a3bccc7ec65b7a7d35cfd42a6db8894fb1e77510cd251e282e9f484c8 |
| zones.display.test.mjs | 1fb470e5165eced92eead16c48627b281c5cab66d3ba501b5995563b15d15903 |
| tests-v10.log | fcd814e9093fb74489222769a8329e6c8c6fe5dbeb21d776a25a83e27ef22e94 |
| joint-cn-v10.png | dbf229ec47fc6139f9a19354442fb2749442d87611c02349b5602016a4fe5500 |

### 文案修正读回与结案

已读回最终`BreadthComparison.tsx:366`：联合模式改为“缺失周期断线，其余有效曲线保留；该日不作联合判断”；普通模式说明保留。250行无障碍描述已明确“灰带表示50日或200日缺测”。上述唯一待改问题及相关歧义均已关闭。

最终源码SHA256：`ad9f0d203cd9defaa8eb0e36609dfdf4ea054ce82b4d3fea263c8656e213e3a9`。本次受限代码／保存测试日志／A股截图复核完成，无剩余实质发现；最终两市交互验收仍由主控承担，不扩称本代理已完成真实浏览器全流程。
