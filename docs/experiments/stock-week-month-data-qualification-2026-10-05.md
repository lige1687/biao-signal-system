# 个股周检查、月评价：首轮资料资格与云端交接（2026-10-05）

## 一句话结论（大白话）

已有资料确实包含个股，能列出沪深300历史候选成员、逐股收盘缺口和周/月检查日期；但目前还没有可证明“那天真正属于股票池”的完整历史名单，不能开始声称没有遗漏失败股票的排序效果研究。建议首轮保留历史沪深300普通股作为主池，先补历史成员生效链，再分别补PPO所需收盘/行动和修正顶底所需高低价；不拿今天熟悉的股票或ETF替代。资料核查已完成，个股因子效果仍未评价。

## 本轮具体范围与验收

本轮只读核查服务于研究的数据资格层，接受用户“周检查/月评价、首批PPO与修正顶底”的最新范围。盘点事前固定为：10月5日个股清单及其三份成员/收盘源、127个旧文件与元数据、A01合同和量价代表合同、直接引用的日历，以及唯一当前行业成员缓存。没有扫描全部账户、全部会话或全部行情文件。四次官方说明/入口页面读取（含失败）是本轮小批上限，0行情请求、0购买、0新软件安装、0因子/未来结果/模型计算。仅新增本报告和raw资格证据，不修改原数据、旧合同、旧负结果或策略源。

验收证据为同目录研究raw中的`qualification.json`、`inspect_sources.py`及本文机器清单。主输入指纹、数量和旧缺口已核；新增身份分类、周/月日期与当前行业可用性已核；历史成员真实性、完整公司行动与退市资料**未通过**，明确阻塞后续效果，不将其写成因子失败。Library交接回执另在本地任务raw保存；本文不包含任何账户、持仓、凭据或完整行情。

## 实际已有资料：数量与完整性

| 资料 | 当次读回范围 | 能做什么 / 不能做什么 |
|---|---|---|
| BaoStock历史成员候选日表 | 2014-12-01—2026-06-30，2,813日、843,900行、682代码；正式2022-01-04—2026-06-30为1,085日、325,500行、439代码、300只/日 | 能列候选成员和12个检出的变动；原程序每20个交易日探测，端点相同时中间进出会漏，端点不同也只找首变动。没有完整正式变更链、永久证券身份、公告/到达时刻。不是已合格的historical universe，即“历史那天真正可观察的股票集合”。 |
| A股前复权收盘宽表 | 1990-12-19—2026-08-27，8,714日期、5,211代码列；正式439代码有436列 | 原件SHA不变，复用1,944候选成员日缺价：3个全缺列、31个局部空缺。全表首末不代表每股都有长历史。只含收盘，不能算要求高低价的顶底或ATR，不能证明行动处理正确。 |
| 另一收盘长表 | 2023-02-08—2026-09-30，4,064,305行、5,222六位代码，只有symbol/date/close | 比同日旧清单又少3行，当前SHA为`1df056b6496ef29a2af1585f563a92e863a71d1ba97fb9bd81ed7a14bfd7899f`，不得沿用4,064,308行旧回执。三只缺列仍0行，缺2020/2021预热，最多覆盖交叉核查。 |
| 127个归档行情文件 | 全部数据及元数据指纹与旧回执相符；实际上82个股票代码候选、44个ETF/基金、1个沪深300指数。股票2016-08-24—2026-09-01、194,493行，73个与正式439代码相交 | 纠正“127只个股”的数量说法。82个股票中72个在正式深市共同日历每日期都有一根记录；有记录不等于当日真实成交或公司行动合格。旧策略局部选池不能代表历史沪深300，更不能代表全A股；每股字段、日期、缺日与哈希在附录。 |
| 当前行业/板块成员 | 2026-09-22 16:47单一东方财富缓存，496板块，覆盖439候选中的428代码 | 这是当前板块快照，不是唯一标准行业分类，也无历史入退区间。不能填到2022—2026的行业字段，不能做历史行业调整后的排序。缺行业不应挡不使用行业的总体价格问题。 |
| 官方研究日历 | 已存深交所2019-09—2026-06逐日交易标志；正式1,085交易日与候选日表一致 | 可排228个完整交易周末和54个月末，合并252个不同观察日期。2026-06-30当周未闭合，不能当周末；月末已闭合。仅深交所来源，独立沪市日历及历史提前公布时间未核。 |

1,944的单位是“股票×候选成员日期”的记录：同一天多只股票缺价分别计数，不是1,944只股票，也不是1,944个不同日期。附录补交439代码逐项的规范交易所/供应商代码、首次/末次候选入池日、已存调整收盘首末与正值行数；nominal_raw_quote_file全部null，表示本轮固定盘点范围未获名义原价文件，不是断言整库永不存在。

三只缺列仍保留：600705的9个候选成员日（2022-01-04—01-14）、600837的767日（2022-01-04—2025-03-07）、601989的892日（2022-01-04—2025-09-05），合计1,668；另31代码276局部缺值，合计1,944。不能只凭缺价叫退市/停牌，不能删掉它们让样本看起来完整。12次候选变动的全代码和缺口区间在云端机器清单。旧程序里虽有`fetch_constituent_prices`，指定输出`constituent_prices_post_adjusted.parquet`实际不存在，而且请求只写close/tradestatus/isST；函数存在不是资料已获得，也不是OHLC来源。

## 资格分层：最小缺口是什么

| 必要事实 | 已有证据 | 首轮最小缺口与恢复标准 |
|---|---|---|
| 当时入池/出池 | 候选日表、探测审计、12次候选加入/剔除清单 | 首先是正式成员基线及**完整**生效链，不是再取一份今天300只。核2022-01-04基线、全部定期及临时调整、名称/代码与永久证券身份；12条只作检索线索，不证明没有第13条。仅W/M决策用途时，可直接核252个实际观察日期的当时成员，不强求每天名单，但结果终点仍要跟踪退出股票。 |
| 上市、退市、合并/换股 | 代码和候选退出日期；无逐证券终止价值 | 先核600705/600837/601989的真实身份、缺价原因与行动；指数退出不是退市，也不是自动卖出。保留换股/现金承接及原证券结束信息，不能把新代码无缝当同一股。 |
| 停牌/漏报 | 31个局部空值区间、旧82股日线日期 | 每个缺口区分正常停牌、尚未上市、漏报、行动、终止；没有证据写unknown。不能前填、删空日或把后来第一根报价顺延成计划结果。 |
| 公司行动和复权 | 当前供应商前复权收盘/局部OHLC | PPO需要可审计价格尺度；实时可用问题还需仅使用当时已知行动。若后来行动只把某个决策日以前全部价格乘同一系数，归一化均线差在数学上不变；应由专职线核实际调整方式与尺度中断，不能未经核实就一律认定未来污染，也不能因只用收盘就忽略分红/合并。按未来结果用途补现金与换股兑付；顶底高低价需同尺度行动处理。当前复权表无原价+行动链，严格经济财富回报和真实可实施用途尚不合格；明确采用供应商调整价的回顾信息诊断可另作带限制资格，不能称总回报或无偏总体效果。 |
| 历史行业 | 单个当前板块快照 | 不用行业的首轮价格比较可暂不加行业；需要行业条件增量时才补当时分类版本/生效区间。不得用当前快照“中性化”历史。 |
| 可成交执行 | 没有成套停复牌、价格限制、实际成交/费用资料 | Rank IC与信息比较不自动要求完整交易账户；净收益另外需要。当前不计算交易收益，不因缺交易字段要求推迟可独立成立的信息资格。 |

两份策略原文实际SHA均与确认值一致：技术体系`df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20`；技术实现`85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903`。来源层次、代码/合同/规范的准确指纹见附录；不使用历史V1定义新任务。

## 首轮股票池规则与可得性

**推荐主池：沿用`CN-CSI300-PIT-ordinary-v1`选池含义。** 每个完整周或月决策日取当时生效的沪深300普通A股；用永久证券身份绑定代码；不要求到今天仍上市，不按未来结果完整性挑股票；入池前预热用各股真实已有报价，上市前不补价；离开指数后不再作为新的排序候选，但先前观察的未来结果继续追踪其原定终点和行动。正式期仍2022—2026H1，大盘股结论不外推全A股。本轮可交439候选代码及252观察日期，**合格正式名单目前不可交**；完成生效链与身份核准后候选代码数可能变化，不得先把439钉成最终合格总数。

首个小批身份核查固定为候选临时变更：2025-03-10 `600837→601058`、2025-09-08 `601989→601298`，以及2022年初600705退出。箭头只是现有候选表加入/剔除配对，不是已核公司合并事实。先取得正式公告/生效及身份原件，再评估PPO的缺价原因，不能先抓439只OHLC填满文件夹。

**可选有限设计（需另立合同，不自动替换主池）：** 若只能核准2022-01-04那天完整300只基线，可把这300个身份固定为一个开始日队列，随后无论退出指数、退市或并购都持续记录结果与unknown。这避免“按今天还活着选股”，但只能说明该起始日大盘股队列，不能回答后续动态沪深300选股，更不是全A股。基线本身仍需正式证据，今天的名单回填不算；不能事后只保留72个日期齐全者。另一个82旧股池可以先做字段/接口演练；若另行明确冻结这个事后固定池、供应商调整价目标和缺失政策，允许有限回顾排序/分组诊断，但只回答这些被选中股票的历史关系，不能以其Rank IC证明普遍选股能力，也不完成用户要求的历史沪深300主池。创业板旧重建在2017-10-09已有反向链101/100身份冲突，当前名单不能替代完整历史；不在第一轮转去创业板绕开阻碍。

## PPO、修正顶底与周/月评价能否运行

“同一日的排名与随后结果是否对应”叫横截面Rank IC；分组比较看当日不同因子水平的股票后来有何差别；模型条件增量看已有趋势/近期涨跌等信息相同后，加入因子是否减少错误。三者回答不同问题，均不等于净交易收益。

| 用途 | 当前能复用 | 当前不能运行的直接原因 |
|---|---|---|
| PPO趋势强度的输入资格 | 已有日线收盘、日历、原云端`research.selection.ema12_26_normalized_spread@0.1.0`定义与计算交付链接 | 历史池未核、3全缺/31局部缺、行动尺度/时点未核。PPO是两条均线距离相对价格的强度表达，不能当转折或买点；不用高低价的PPO问题不强加全池OHLC门槛。 |
| 修正顶底结构的输入资格 | 82股票旧文件有high/low（也有open/close），可查日期/哈希 | 没有全池高低价及行动链；需要准确“修正后”的定义、确认时间和可复用代码。不能拿已登记simple_top3或旧顶部代理冒充修正定义。本轮不计算。 |
| 每周检查、约月后评价 | 228完整周末；54月末可作另一个固定月频用途；日线计算不改成周线计算 | 要明确月评价指下一自然月末还是原包下一收盘至第21收盘的20个间隔；这两种结果不可混用。候选资料缺历史池/结果端点与行动，尚不能构造标签。 |
| Rank IC/固定分组 | 周/月日期、候选成员、缺口列表可交后续设计 | 需同日实际合格股票、因子值及成熟结果，包含失败/退出者和缺失分布；平值、无变化、少资产日期保留为undefined，不填0。只做价格信息时无需虚构行业。 |
| 模型条件增量 | 复用原时间成熟检查、经济价格检查、共同支持、逐日全资产切分、已有模型比较 | 个股动态成员输入与精确候选定义/模型薄适配层还未核就绪；当前工作流不提供原生Rank IC评价器，代码中SVD的rank不是Rank IC。不能把日线ETF合同改asset名单就运行。 |

历史published_at/available_at未知本身只阻断“当时本路径已取得/实时可实施”的声明，不绝对禁止有限回顾研究；sourcehash只证明同一原件。回顾用途可以明确采用当前调整价代理，但历史成员不完整和终止结果选择性缺失仍会阻断无幸存者遗漏的主池结论。端点结果只按端点及行动资格处理，不能把完整途中报价强加给所有目标；顶底特征则确需足够的连续真实高低价。

后续模型先固定已有信息、简单历史参照和加入候选后的比较，在相同资产/日期/成熟目标上核差额；训练只用当时已经成熟的结果，同日全部股票一起按时间分开，不随机拆股票行。周观察约月结果会重叠；300只同日股票也不等于300个独立市场年份。旧A01的252日分段政策仅约束其原定义，不自动移植PPO或修正顶底；各候选从准确原包核预热/缺失/确认政策。

旧六ETF A01与18项八ETF量价结果保留，未按新池重新拟合。已登记周度PPO在八ETF未确认稳健增量也保留；这是个股尚未评价，不把ETF负结果当禁止研究个股的理由。包内PPO0.1.0尚非本地全局正式注册对象；本地登记检索不能据此断言云端没有定义。修正顶底准确ID/版本需由其现有交付包绑定，资料负责人不新造定义。

## 下一项真正能推进的操作与精确来源

先做**历史名单/身份小批**，不启动收益：在[中证指数000300官方页](https://www.csindex.com.cn/#/indices/family/detail?indexCode=000300)定位2022年初有效基线及上述两次2025临时调样公告，保存原件、公布/生效日期、全加入剔除身份。当前网页只返回JavaScript壳，未取得公告，所以不能编造直链或说来源已打通。官方链必须能说明未检出的其他调整；两份公告通过不等于全期通过。可复用旧12次变动清单给每个日期建立待核任务，按正式发布者规则确认链的完整性。

身份与公司行动用[上交所上市公司公告查询](https://www.sse.com.cn/disclosure/listedinfo/announcement/)按600705/600837/601989检索停复牌、终止上市、换股/合并及现金处理；该公开入口本轮实际可读，但具体历史原件仍未取得。[深交所公告入口](https://www.szse.cn/disclosure/listed/notice/index.html)本轮超时，仅作为深市后续官方入口，不能称已获得证据。公开页面本轮没有购买成本；附件访问、完整性及再分发权仍要逐件核，0费用不代表许可已确认。

若官方名单链无法取得，现有BaoStock0.9.3已安装，旧程序实际使用`query_hs300_stocks(date)`。可在另一个有界资料作业逐个核**252个周/月观察日期**的返回名单及`updateDate`含义，绑定原响应、取得时间、供应商文档和再使用许可，并交正式公告交叉核准；这是供应商历史返回，不自动等同官方完整史。当前[BaoStock说明入口](http://www.baostock.com/mainContent?file=stock_data.md)读取失败，不能承诺其历史版本/完整性/费用条款；本轮没有调用API。无需安装新软件或配密钥。

建议下一资料作业先固定**最多6个官方文件/页面请求、≤2 MiB、价格请求0、付费0**：基线、完整调整链定位说明、两次临时调整、对应两项身份行动。这是待执行的小批建议，不是本机已耗预算。用户随后已授权便宜模型按来源并行拉取公开免费资料，由云端资料负责人冻结具体分片；本机本轮仍只读，不重复抓取。若仍无法找到正式基线/完整链，报告具体缺件，不能循环换源或删证券。资料合格后PPO先补收盘与行动，顶底再补高低价；价格候选沿旧合同腾讯`https://web.ifzq.gtimg.cn/appstock/app/fqkline/get`（sh600705/sh600837/sh601989、2020-12-18—2026-06-30）做单源有限兼容批，实际覆盖和复权/退市许可未测。本轮不执行行情请求；旧下一批“最多6请求”不是本任务已获行情授权。现有资料不足以推荐任何收费套餐；如需购买，先给缺字段、授权范围及真实报价，价格未知不写免费或估价。

## ARCHIVE / 最小决策卡

- 本轮资料核查：completed，合格historical universe：BLOCKED_DATA，PPO/修正顶底个股效果：not_evaluated；用户效果待验收。
- 新增实证纠正：127文件实际82股/44基金/1指数；长表再少3行并换SHA；周/月日期合并252个；当前行业仅事后快照。旧1,944缺口在原件SHA匹配后复用，没有重跑缺口研究。
- 恢复条件：正式基线/完整成员链与身份先合格，PPO再核收盘/行动/结果，顶底再核高低价和准确修正定义；行业只阻塞需要行业的用途。当前不能运行Rank IC、分组或模型效果。
- 验收：本地资格脚本退出0；PyArrow沙箱CPU查询警告不影响读取，保留于资格证据。目录治理检查和Library状态见同任务验收回执。未提交、未推送，原大数据及账户资料未上传。

## 云端最小机器清单与字段样例

以下是资料清单、定义来源、字段含义和资格标记，**没有原始行情、因子值、未来收益或模型输出**。云端只凭清单不能运行市场效果；大行情留本机，取得合法可用/再分发范围后再按具体文件批准交接。`sourcehash`是精确字节SHA-256，不能证明内容正确。所有null是未知或未计算，不是零。

```json
{
  "schema_version": "stock-week-month-cloud-handoff/1.0.0",
  "sourcehash_semantics": "SHA-256 of exact existing file bytes, not a claim of source accuracy",
  "data_status": "BLOCKED_DATA; not_evaluated",
  "qualification_evidence": {
    "path": "docs/experiments/raw/stock-week-month-qualification-2026-10-05/qualification.json",
    "sourcehash": "33dd041fa39a98b07756e65539fb6e69e66e6038462e74705a58ddc635130be7"
  },
  "sources": {
    "membership": {
      "path": "docs/experiments/raw/research-etf-breadth-confirmation-2026-09-09/prepared/csi300_membership_daily.parquet",
      "bytes": 136179,
      "sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "hash_algorithm": "sha256",
      "matches_prior_manifest": true
    },
    "membership_probe": {
      "path": "docs/experiments/raw/research-etf-breadth-confirmation-2026-09-09/prepared/csi300_membership_probe_audit.json",
      "bytes": 3351,
      "sourcehash": "163424317ba3b0b27dd13e37b5c178999c87d8e81b9bc5c3d1f388ae3c854f22",
      "hash_algorithm": "sha256",
      "matches_prior_manifest": true
    },
    "wide_close": {
      "path": "/Users/yongbiaoli/.lei_signal_lab/cache/a_share_klines_full.parquet",
      "bytes": 49432584,
      "sourcehash": "5ad045c518d0bb4394d8c8cb946d207ad9b5b1454e5a776b1a3766c62b475b04",
      "hash_algorithm": "sha256",
      "matches_prior_manifest": true
    },
    "long_close": {
      "path": "/Users/yongbiaoli/.lei_signal_lab/cache/a_share_klines.parquet",
      "bytes": 10794600,
      "sourcehash": "1df056b6496ef29a2af1585f563a92e863a71d1ba97fb9bd81ed7a14bfd7899f",
      "hash_algorithm": "sha256",
      "matches_prior_manifest": false
    },
    "calendar_szse": {
      "path": "docs/experiments/raw/research-calendar-completion-2026-09-10/calendar-merged/calendar.json",
      "bytes": 296252,
      "sourcehash": "aa43736b67bbcee04fc21eedf8d510b184b764adf138456c8bce93a3155eb6c1",
      "hash_algorithm": "sha256"
    },
    "legacy_audit": {
      "path": "docs/experiments/raw/price-volume-universe-qualification-2026-10-04/unqualified-pool-audit.json",
      "bytes": 70108,
      "sourcehash": "f737f3e3f3a7fffc2d7b1859e115f97f62c2ed4028a1bcb0e63137252c518b91",
      "hash_algorithm": "sha256"
    },
    "sector_current_snapshot": {
      "path": "/Users/yongbiaoli/.lei_signal_lab/cache/sector_members.json",
      "bytes": 204962,
      "sourcehash": "92ec5ee5a49f522d109692f48aaba8fe7ed51db4d8202728265d737c3be257ab",
      "hash_algorithm": "sha256"
    }
  },
  "strategy_sources": [
    {
      "path": "/Users/yongbiaoli/Desktop/lei signal doc/LEI 技术交易体系.md",
      "bytes": 65786,
      "sourcehash": "df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20",
      "hash_algorithm": "sha256"
    },
    {
      "path": "/Users/yongbiaoli/Desktop/lei signal doc/LEI 技术实现.md",
      "bytes": 36427,
      "sourcehash": "85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903",
      "hash_algorithm": "sha256"
    }
  ],
  "bound_contracts": [
    {
      "path": "AGENTS.md",
      "sourcehash": "345510fa39b12a995d3660fee40ce71475e58d7a32670e93ce70fddf91438cb0",
      "bytes": 23939
    },
    {
      "path": ".agents/skills/lei-data-availability/SKILL.md",
      "sourcehash": "f0218e2f8971770ff4e993f5d925998e9490f66a6e31f8195b7fbd0c11944b45",
      "bytes": 3206
    },
    {
      "path": ".agents/skills/lei-causal-validation/SKILL.md",
      "sourcehash": "4dd95c0f4d91771472d27d7678bd24fa2d92b0331cbb48e33aca2dfdadcb6fe7",
      "bytes": 3324
    },
    {
      "path": "configs/strategy-documents.v1.json",
      "sourcehash": "2e931d72814e096546c9a54dcc41c415fea5ad0042587deaf5cb87293133266b",
      "bytes": 806
    },
    {
      "path": "docs/research/current-standards.json",
      "sourcehash": "147c317b0ec5878f555c98dc4ffc71820c42c93365a604920671f5f224148c46",
      "bytes": 1209
    },
    {
      "path": "docs/research/research-workflow-usage.md",
      "sourcehash": "e47c181bcf3abdc822109815cba7bc322103bd28f7316eca23aacadca323c7d8",
      "bytes": 16082
    },
    {
      "path": "docs/research/lei-factor-research-mission.md",
      "sourcehash": "37e7bb1b13b1eddbe98930e42146806140274f91ea011f116c4602414625dbf8",
      "bytes": 10115
    },
    {
      "path": "docs/research/proposals/a01-universe-expansion-2026-09-29/contract.md",
      "sourcehash": "ebddd8623a4237e652f4b3ad8693f72877a3d2827327efca50c5c87cdd7d55b1",
      "bytes": 17833
    },
    {
      "path": "docs/research/proposals/a01-universe-expansion-2026-09-29/review-amendment-v1.1.md",
      "sourcehash": "5901dc69c8ca45498d4774388164b86a7192a1e0c5b803272c253b8867fdb4f7",
      "bytes": 3195
    },
    {
      "path": "docs/research/proposals/a01-universe-expansion-2026-09-29/data-acquisition-plan.md",
      "sourcehash": "9b6dfab5f338cff944751ee62daaf96d477cd7db65c2bf169f2004964d1023c2",
      "bytes": 7265
    },
    {
      "path": "docs/experiments/raw/price-volume-universe-qualification-2026-10-04/close_location_mean20-frozen/contract.json",
      "sourcehash": "d72918ced1ad9cb94a5ae6c71fc92b4d01a87fef0ad59cbd22a9f2902b6ba0ff",
      "bytes": 49169
    },
    {
      "path": "docs/experiments/raw/price-volume-universe-qualification-2026-10-04/factor-process-audit-2026-10-04.md",
      "sourcehash": "5846ea3a7380047b1edfb7bb7a35a6ec373cd97c699bda61bfb23e9973b29a82",
      "bytes": 12493
    },
    {
      "path": "docs/experiments/weekly-ppo-information-2026-10-05.md",
      "sourcehash": "13e2776503f64e74944b7debb3660496af643e65b5526b4b553ea5b7e196623c",
      "bytes": 3416
    },
    {
      "path": "docs/experiments/raw/weekly-ppo-information-2026-10-05/registration-source.json",
      "sourcehash": "3466985d99d0396c02d95db64eecb3c3d5b36891560f76bbafe68ec2079b0926",
      "bytes": 1768
    },
    {
      "path": "docs/experiments/price-only-path-six-factor-eight-etf-2026-10-04.md",
      "sourcehash": "c3737cc952eca1f5c34e6e0d9e9557468bb93d50f804794edd9a96a03a311cd2",
      "bytes": 7961
    },
    {
      "path": "docs/experiments/quantity-path-twelve-factor-eight-etf-2026-10-04.md",
      "sourcehash": "680e7b1ae02a5507ff360132c5a7ec55d6f6385f03a358d28883ee0b8cac8363",
      "bytes": 10686
    }
  ],
  "counts": {
    "formal_start": "2022-01-04",
    "formal_end": "2026-06-30",
    "dates": 1085,
    "codes": 439,
    "rows": 325500,
    "missing_member_close_rows": 1944,
    "absent_columns": [
      "600705",
      "600837",
      "601989"
    ],
    "provenance": "reused only after current sourcehash equality; no gap recount"
  },
  "membership_full": {
    "first": "2014-12-01",
    "last": "2026-06-30",
    "dates": 2813,
    "rows": 843900,
    "code_count": 682,
    "fields": [
      "date",
      "symbol",
      "version"
    ],
    "sample": [
      {
        "date": "2014-12-01",
        "symbol": "000001",
        "version": "29e4c59c472d"
      },
      {
        "date": "2014-12-01",
        "symbol": "000002",
        "version": "29e4c59c472d"
      }
    ]
  },
  "wide_close": {
    "rows": 8714,
    "code_columns": 5211,
    "first": "1990-12-19",
    "last": "2026-08-27",
    "fields": [
      "date",
      "six_digit_code_column=adjusted_close"
    ],
    "no_ohlc_or_actions_or_trade_status": true
  },
  "long_close": {
    "rows": 4064305,
    "first": "2023-02-08",
    "last": "2026-09-30",
    "code_count": 5222,
    "three_absent_rows": 0,
    "fields": [
      "symbol",
      "date",
      "close"
    ],
    "row_delta_vs_prior": -3
  },
  "weekly_period_ends_szse_only": [
    "2022-01-07",
    "2022-01-14",
    "2022-01-21",
    "2022-01-28",
    "2022-02-11",
    "2022-02-18",
    "2022-02-25",
    "2022-03-04",
    "2022-03-11",
    "2022-03-18",
    "2022-03-25",
    "2022-04-01",
    "2022-04-08",
    "2022-04-15",
    "2022-04-22",
    "2022-04-29",
    "2022-05-06",
    "2022-05-13",
    "2022-05-20",
    "2022-05-27",
    "2022-06-02",
    "2022-06-10",
    "2022-06-17",
    "2022-06-24",
    "2022-07-01",
    "2022-07-08",
    "2022-07-15",
    "2022-07-22",
    "2022-07-29",
    "2022-08-05",
    "2022-08-12",
    "2022-08-19",
    "2022-08-26",
    "2022-09-02",
    "2022-09-09",
    "2022-09-16",
    "2022-09-23",
    "2022-09-30",
    "2022-10-14",
    "2022-10-21",
    "2022-10-28",
    "2022-11-04",
    "2022-11-11",
    "2022-11-18",
    "2022-11-25",
    "2022-12-02",
    "2022-12-09",
    "2022-12-16",
    "2022-12-23",
    "2022-12-30",
    "2023-01-06",
    "2023-01-13",
    "2023-01-20",
    "2023-02-03",
    "2023-02-10",
    "2023-02-17",
    "2023-02-24",
    "2023-03-03",
    "2023-03-10",
    "2023-03-17",
    "2023-03-24",
    "2023-03-31",
    "2023-04-07",
    "2023-04-14",
    "2023-04-21",
    "2023-04-28",
    "2023-05-05",
    "2023-05-12",
    "2023-05-19",
    "2023-05-26",
    "2023-06-02",
    "2023-06-09",
    "2023-06-16",
    "2023-06-21",
    "2023-06-30",
    "2023-07-07",
    "2023-07-14",
    "2023-07-21",
    "2023-07-28",
    "2023-08-04",
    "2023-08-11",
    "2023-08-18",
    "2023-08-25",
    "2023-09-01",
    "2023-09-08",
    "2023-09-15",
    "2023-09-22",
    "2023-09-28",
    "2023-10-13",
    "2023-10-20",
    "2023-10-27",
    "2023-11-03",
    "2023-11-10",
    "2023-11-17",
    "2023-11-24",
    "2023-12-01",
    "2023-12-08",
    "2023-12-15",
    "2023-12-22",
    "2023-12-29",
    "2024-01-05",
    "2024-01-12",
    "2024-01-19",
    "2024-01-26",
    "2024-02-02",
    "2024-02-08",
    "2024-02-23",
    "2024-03-01",
    "2024-03-08",
    "2024-03-15",
    "2024-03-22",
    "2024-03-29",
    "2024-04-03",
    "2024-04-12",
    "2024-04-19",
    "2024-04-26",
    "2024-04-30",
    "2024-05-10",
    "2024-05-17",
    "2024-05-24",
    "2024-05-31",
    "2024-06-07",
    "2024-06-14",
    "2024-06-21",
    "2024-06-28",
    "2024-07-05",
    "2024-07-12",
    "2024-07-19",
    "2024-07-26",
    "2024-08-02",
    "2024-08-09",
    "2024-08-16",
    "2024-08-23",
    "2024-08-30",
    "2024-09-06",
    "2024-09-13",
    "2024-09-20",
    "2024-09-27",
    "2024-09-30",
    "2024-10-11",
    "2024-10-18",
    "2024-10-25",
    "2024-11-01",
    "2024-11-08",
    "2024-11-15",
    "2024-11-22",
    "2024-11-29",
    "2024-12-06",
    "2024-12-13",
    "2024-12-20",
    "2024-12-27",
    "2025-01-03",
    "2025-01-10",
    "2025-01-17",
    "2025-01-24",
    "2025-01-27",
    "2025-02-07",
    "2025-02-14",
    "2025-02-21",
    "2025-02-28",
    "2025-03-07",
    "2025-03-14",
    "2025-03-21",
    "2025-03-28",
    "2025-04-03",
    "2025-04-11",
    "2025-04-18",
    "2025-04-25",
    "2025-04-30",
    "2025-05-09",
    "2025-05-16",
    "2025-05-23",
    "2025-05-30",
    "2025-06-06",
    "2025-06-13",
    "2025-06-20",
    "2025-06-27",
    "2025-07-04",
    "2025-07-11",
    "2025-07-18",
    "2025-07-25",
    "2025-08-01",
    "2025-08-08",
    "2025-08-15",
    "2025-08-22",
    "2025-08-29",
    "2025-09-05",
    "2025-09-12",
    "2025-09-19",
    "2025-09-26",
    "2025-09-30",
    "2025-10-10",
    "2025-10-17",
    "2025-10-24",
    "2025-10-31",
    "2025-11-07",
    "2025-11-14",
    "2025-11-21",
    "2025-11-28",
    "2025-12-05",
    "2025-12-12",
    "2025-12-19",
    "2025-12-26",
    "2025-12-31",
    "2026-01-09",
    "2026-01-16",
    "2026-01-23",
    "2026-01-30",
    "2026-02-06",
    "2026-02-13",
    "2026-02-27",
    "2026-03-06",
    "2026-03-13",
    "2026-03-20",
    "2026-03-27",
    "2026-04-03",
    "2026-04-10",
    "2026-04-17",
    "2026-04-24",
    "2026-04-30",
    "2026-05-08",
    "2026-05-15",
    "2026-05-22",
    "2026-05-29",
    "2026-06-05",
    "2026-06-12",
    "2026-06-18",
    "2026-06-26"
  ],
  "monthly_period_ends_szse_only": [
    "2022-01-28",
    "2022-02-28",
    "2022-03-31",
    "2022-04-29",
    "2022-05-31",
    "2022-06-30",
    "2022-07-29",
    "2022-08-31",
    "2022-09-30",
    "2022-10-31",
    "2022-11-30",
    "2022-12-30",
    "2023-01-31",
    "2023-02-28",
    "2023-03-31",
    "2023-04-28",
    "2023-05-31",
    "2023-06-30",
    "2023-07-31",
    "2023-08-31",
    "2023-09-28",
    "2023-10-31",
    "2023-11-30",
    "2023-12-29",
    "2024-01-31",
    "2024-02-29",
    "2024-03-29",
    "2024-04-30",
    "2024-05-31",
    "2024-06-28",
    "2024-07-31",
    "2024-08-30",
    "2024-09-30",
    "2024-10-31",
    "2024-11-29",
    "2024-12-31",
    "2025-01-27",
    "2025-02-28",
    "2025-03-31",
    "2025-04-30",
    "2025-05-30",
    "2025-06-30",
    "2025-07-31",
    "2025-08-29",
    "2025-09-30",
    "2025-10-31",
    "2025-11-28",
    "2025-12-31",
    "2026-01-30",
    "2026-02-27",
    "2026-03-31",
    "2026-04-30",
    "2026-05-29",
    "2026-06-30"
  ],
  "unclosed_tail_week": [
    "2026-06-30"
  ],
  "candidate_codes_439": [
    "000001",
    "000002",
    "000063",
    "000066",
    "000069",
    "000100",
    "000157",
    "000166",
    "000301",
    "000333",
    "000338",
    "000408",
    "000425",
    "000538",
    "000568",
    "000596",
    "000617",
    "000625",
    "000630",
    "000651",
    "000656",
    "000657",
    "000661",
    "000703",
    "000708",
    "000723",
    "000725",
    "000728",
    "000733",
    "000768",
    "000776",
    "000783",
    "000786",
    "000792",
    "000800",
    "000807",
    "000858",
    "000860",
    "000876",
    "000877",
    "000895",
    "000938",
    "000963",
    "000975",
    "000977",
    "000983",
    "000988",
    "000999",
    "001280",
    "001289",
    "001391",
    "001965",
    "001979",
    "002001",
    "002007",
    "002008",
    "002024",
    "002027",
    "002028",
    "002032",
    "002044",
    "002049",
    "002050",
    "002064",
    "002074",
    "002120",
    "002129",
    "002142",
    "002153",
    "002157",
    "002179",
    "002180",
    "002202",
    "002230",
    "002236",
    "002241",
    "002252",
    "002271",
    "002304",
    "002311",
    "002352",
    "002353",
    "002371",
    "002384",
    "002410",
    "002414",
    "002415",
    "002422",
    "002456",
    "002459",
    "002460",
    "002463",
    "002466",
    "002475",
    "002493",
    "002508",
    "002532",
    "002555",
    "002558",
    "002568",
    "002594",
    "002600",
    "002601",
    "002602",
    "002603",
    "002607",
    "002624",
    "002625",
    "002648",
    "002673",
    "002709",
    "002714",
    "002736",
    "002739",
    "002756",
    "002773",
    "002791",
    "002812",
    "002821",
    "002837",
    "002841",
    "002916",
    "002920",
    "002938",
    "002939",
    "002945",
    "003816",
    "300003",
    "300014",
    "300015",
    "300033",
    "300059",
    "300122",
    "300124",
    "300136",
    "300142",
    "300144",
    "300207",
    "300223",
    "300251",
    "300274",
    "300308",
    "300316",
    "300347",
    "300394",
    "300408",
    "300413",
    "300418",
    "300433",
    "300442",
    "300450",
    "300454",
    "300476",
    "300496",
    "300498",
    "300502",
    "300529",
    "300558",
    "300595",
    "300601",
    "300628",
    "300661",
    "300676",
    "300677",
    "300750",
    "300751",
    "300759",
    "300760",
    "300763",
    "300769",
    "300782",
    "300803",
    "300832",
    "300866",
    "300888",
    "300896",
    "300919",
    "300957",
    "300979",
    "300999",
    "301165",
    "301236",
    "301269",
    "301308",
    "302132",
    "600000",
    "600009",
    "600010",
    "600011",
    "600015",
    "600016",
    "600018",
    "600019",
    "600023",
    "600025",
    "600026",
    "600027",
    "600028",
    "600029",
    "600030",
    "600031",
    "600036",
    "600039",
    "600048",
    "600050",
    "600061",
    "600066",
    "600079",
    "600085",
    "600089",
    "600104",
    "600109",
    "600111",
    "600115",
    "600118",
    "600132",
    "600143",
    "600150",
    "600160",
    "600161",
    "600176",
    "600183",
    "600188",
    "600196",
    "600219",
    "600221",
    "600233",
    "600276",
    "600299",
    "600309",
    "600332",
    "600340",
    "600346",
    "600352",
    "600362",
    "600372",
    "600377",
    "600383",
    "600406",
    "600415",
    "600426",
    "600436",
    "600438",
    "600460",
    "600482",
    "600489",
    "600515",
    "600519",
    "600521",
    "600522",
    "600547",
    "600549",
    "600570",
    "600584",
    "600585",
    "600588",
    "600600",
    "600606",
    "600655",
    "600660",
    "600674",
    "600690",
    "600703",
    "600705",
    "600732",
    "600741",
    "600745",
    "600754",
    "600760",
    "600763",
    "600795",
    "600803",
    "600809",
    "600837",
    "600845",
    "600848",
    "600872",
    "600875",
    "600884",
    "600886",
    "600887",
    "600893",
    "600900",
    "600905",
    "600918",
    "600919",
    "600926",
    "600930",
    "600938",
    "600941",
    "600958",
    "600989",
    "600999",
    "601006",
    "601009",
    "601012",
    "601018",
    "601021",
    "601058",
    "601059",
    "601066",
    "601077",
    "601088",
    "601100",
    "601108",
    "601111",
    "601117",
    "601127",
    "601136",
    "601138",
    "601155",
    "601162",
    "601166",
    "601169",
    "601186",
    "601211",
    "601216",
    "601225",
    "601229",
    "601231",
    "601236",
    "601238",
    "601288",
    "601298",
    "601318",
    "601319",
    "601328",
    "601336",
    "601360",
    "601377",
    "601390",
    "601398",
    "601456",
    "601555",
    "601600",
    "601601",
    "601607",
    "601615",
    "601618",
    "601628",
    "601633",
    "601658",
    "601668",
    "601669",
    "601688",
    "601689",
    "601696",
    "601698",
    "601699",
    "601727",
    "601728",
    "601766",
    "601788",
    "601799",
    "601800",
    "601808",
    "601816",
    "601818",
    "601825",
    "601838",
    "601857",
    "601865",
    "601868",
    "601872",
    "601877",
    "601878",
    "601881",
    "601888",
    "601898",
    "601899",
    "601901",
    "601916",
    "601919",
    "601933",
    "601939",
    "601966",
    "601985",
    "601988",
    "601989",
    "601990",
    "601995",
    "601998",
    "603019",
    "603087",
    "603160",
    "603185",
    "603195",
    "603233",
    "603259",
    "603260",
    "603288",
    "603290",
    "603296",
    "603338",
    "603369",
    "603392",
    "603486",
    "603501",
    "603517",
    "603658",
    "603659",
    "603799",
    "603806",
    "603833",
    "603882",
    "603893",
    "603899",
    "603939",
    "603986",
    "603993",
    "605117",
    "605499",
    "688005",
    "688008",
    "688009",
    "688012",
    "688036",
    "688041",
    "688047",
    "688065",
    "688072",
    "688082",
    "688111",
    "688126",
    "688169",
    "688183",
    "688187",
    "688223",
    "688256",
    "688271",
    "688303",
    "688363",
    "688396",
    "688472",
    "688506",
    "688521",
    "688561",
    "688599",
    "688981"
  ],
  "code_coverage_evidence": {
    "path": "docs/experiments/raw/stock-week-month-qualification-2026-10-05/code-source-coverage.json",
    "sourcehash": "9b60d740687ddaa5d09beb6d5b157f04dbd2c996004cf30087012789b22674c8",
    "schema_version": "stock-code-source-coverage/1.0.0"
  },
  "code_exchange_selection_date_and_stored_quote_coverage_439": [
    {
      "symbol": "000001",
      "exchange": "XSHE",
      "provider_symbol": "sz000001",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 8421,
        "first": "1991-04-03",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000002",
      "exchange": "XSHE",
      "provider_symbol": "sz000002",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 8415,
        "first": "1991-01-29",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000063",
      "exchange": "XSHE",
      "provider_symbol": "sz000063",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6818,
        "first": "1997-11-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000066",
      "exchange": "XSHE",
      "provider_symbol": "sz000066",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2023-03-17",
      "candidate_member_records": 291,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6757,
        "first": "1997-06-26",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000069",
      "exchange": "XSHE",
      "provider_symbol": "sz000069",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2024-06-14",
      "candidate_member_records": 591,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6878,
        "first": "1997-09-10",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000100",
      "exchange": "XSHE",
      "provider_symbol": "sz000100",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5132,
        "first": "2004-01-30",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000157",
      "exchange": "XSHE",
      "provider_symbol": "sz000157",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6138,
        "first": "2000-10-12",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000166",
      "exchange": "XSHE",
      "provider_symbol": "sz000166",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2785,
        "first": "2015-01-26",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000301",
      "exchange": "XSHE",
      "provider_symbol": "sz000301",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1076,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6067,
        "first": "2000-05-29",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000333",
      "exchange": "XSHE",
      "provider_symbol": "sz000333",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3081,
        "first": "2013-09-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000338",
      "exchange": "XSHE",
      "provider_symbol": "sz000338",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4635,
        "first": "2007-04-30",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000408",
      "exchange": "XSHE",
      "provider_symbol": "sz000408",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 982,
      "missing_close_member_records_reused": 5,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6813,
        "first": "1996-06-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000425",
      "exchange": "XSHE",
      "provider_symbol": "sz000425",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 13,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 7118,
        "first": "1996-08-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000538",
      "exchange": "XSHE",
      "provider_symbol": "sz000538",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 7697,
        "first": "1993-12-15",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000568",
      "exchange": "XSHE",
      "provider_symbol": "sz000568",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 7722,
        "first": "1994-05-09",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/000568.SZ.bars.parquet",
        "bytes": 96333,
        "sourcehash": "14d056520560e336c2e2143e0b46ba516a96fa5802bbb719dc88cc803f277d46",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "000596",
      "exchange": "XSHE",
      "provider_symbol": "sz000596",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 7038,
        "first": "1996-09-27",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/000596.SZ.bars.parquet",
        "bytes": 94540,
        "sourcehash": "c697303524bf2399ba2242efd77e80eecb791c42ba38fbc3e86e8ae95f36cf3b",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "000617",
      "exchange": "XSHE",
      "provider_symbol": "sz000617",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-06-12",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 738,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 7018,
        "first": "1996-10-22",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000625",
      "exchange": "XSHE",
      "provider_symbol": "sz000625",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6835,
        "first": "1997-06-10",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/000625.SZ.bars.parquet",
        "bytes": 88905,
        "sourcehash": "cbd0339b2dbfa669d85ce61195f4c8ff89b04d60c2740021aed8af54fe262f91",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "000630",
      "exchange": "XSHE",
      "provider_symbol": "sz000630",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2024-12-16",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 371,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6974,
        "first": "1996-11-20",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000651",
      "exchange": "XSHE",
      "provider_symbol": "sz000651",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6996,
        "first": "1996-11-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000656",
      "exchange": "XSHE",
      "provider_symbol": "sz000656",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-01-14",
      "candidate_member_records": 9,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6704,
        "first": "1996-11-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000657",
      "exchange": "XSHE",
      "provider_symbol": "sz000657",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2026-06-15",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 11,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6146,
        "first": "1996-12-05",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000661",
      "exchange": "XSHE",
      "provider_symbol": "sz000661",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-12",
      "candidate_member_records": 1074,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 7086,
        "first": "1996-12-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/000661.SZ.bars.parquet",
        "bytes": 98085,
        "sourcehash": "fc550f6050b036e64f98001c7eb17cd06ad370332129f6f83d19a395e16762f7",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "000703",
      "exchange": "XSHE",
      "provider_symbol": "sz000703",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2023-03-17",
      "candidate_member_records": 291,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6951,
        "first": "1997-03-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000708",
      "exchange": "XSHE",
      "provider_symbol": "sz000708",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6947,
        "first": "1997-03-26",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000723",
      "exchange": "XSHE",
      "provider_symbol": "sz000723",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-03-20",
      "candidate_member_last": "2023-12-08",
      "candidate_member_records": 178,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6527,
        "first": "1997-05-15",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000725",
      "exchange": "XSHE",
      "provider_symbol": "sz000725",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6084,
        "first": "2001-01-12",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/000725.SZ.bars.parquet",
        "bytes": 66621,
        "sourcehash": "35237aa972182c3538ce1e491657f95e9ff2b5a668e57a2aefb4755ade8e04cb",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "000728",
      "exchange": "XSHE",
      "provider_symbol": "sz000728",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-01-14",
      "candidate_member_records": 9,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6760,
        "first": "1997-06-16",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000733",
      "exchange": "XSHE",
      "provider_symbol": "sz000733",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-03-20",
      "candidate_member_last": "2024-12-13",
      "candidate_member_records": 423,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6992,
        "first": "1997-07-03",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000768",
      "exchange": "XSHE",
      "provider_symbol": "sz000768",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6897,
        "first": "1997-06-26",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/000768.SZ.bars.parquet",
        "bytes": 82552,
        "sourcehash": "754652436907617b008c0aa3c2c9f7e2d97b68e9f9d373f2a4066ead9daae489",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "000776",
      "exchange": "XSHE",
      "provider_symbol": "sz000776",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6147,
        "first": "1997-06-11",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000783",
      "exchange": "XSHE",
      "provider_symbol": "sz000783",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-06-10",
      "candidate_member_records": 103,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6743,
        "first": "1997-07-31",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000786",
      "exchange": "XSHE",
      "provider_symbol": "sz000786",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-12",
      "candidate_member_records": 1074,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6878,
        "first": "1997-06-06",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000792",
      "exchange": "XSHE",
      "provider_symbol": "sz000792",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 982,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6420,
        "first": "1997-09-04",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000800",
      "exchange": "XSHE",
      "provider_symbol": "sz000800",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2025-12-12",
      "candidate_member_records": 956,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6997,
        "first": "1997-06-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000807",
      "exchange": "XSHE",
      "provider_symbol": "sz000807",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2024-06-17",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 494,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6698,
        "first": "1998-04-08",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000858",
      "exchange": "XSHE",
      "provider_symbol": "sz000858",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6734,
        "first": "1998-04-27",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/000858.SZ.bars.parquet",
        "bytes": 99108,
        "sourcehash": "0d2c587860fe6637366a08bf5e9fd2016f5e9c9cc1088e1f936ad69dbf24d597",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "000860",
      "exchange": "XSHE",
      "provider_symbol": "sz000860",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-01-14",
      "candidate_member_records": 9,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6642,
        "first": "1998-11-04",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000876",
      "exchange": "XSHE",
      "provider_symbol": "sz000876",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-12",
      "candidate_member_records": 1074,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6656,
        "first": "1998-03-11",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000877",
      "exchange": "XSHE",
      "provider_symbol": "sz000877",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2024-06-14",
      "candidate_member_records": 488,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6578,
        "first": "1999-01-07",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000895",
      "exchange": "XSHE",
      "provider_symbol": "sz000895",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6146,
        "first": "1998-12-10",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000938",
      "exchange": "XSHE",
      "provider_symbol": "sz000938",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6253,
        "first": "1999-11-04",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/000938.SZ.bars.parquet",
        "bytes": 88851,
        "sourcehash": "0ded3d2b8aa0dc72015dc4c63c81c473fa84d043b366ce86bb6cf4d35a649ccf",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "000963",
      "exchange": "XSHE",
      "provider_symbol": "sz000963",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6277,
        "first": "2000-01-27",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000975",
      "exchange": "XSHE",
      "provider_symbol": "sz000975",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2024-12-16",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 371,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5841,
        "first": "2000-06-08",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000977",
      "exchange": "XSHE",
      "provider_symbol": "sz000977",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6235,
        "first": "2000-06-08",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000983",
      "exchange": "XSHE",
      "provider_symbol": "sz000983",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-06-12",
      "candidate_member_last": "2026-06-12",
      "candidate_member_records": 727,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6266,
        "first": "2000-07-26",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000988",
      "exchange": "XSHE",
      "provider_symbol": "sz000988",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2026-06-15",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 11,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6281,
        "first": "2000-06-08",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "000999",
      "exchange": "XSHE",
      "provider_symbol": "sz000999",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-12-11",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 616,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6146,
        "first": "2000-03-09",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "001280",
      "exchange": "XSHE",
      "provider_symbol": "sz001280",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2026-06-15",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 11,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 177,
        "first": "2025-12-03",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "001289",
      "exchange": "XSHE",
      "provider_symbol": "sz001289",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2025-12-12",
      "candidate_member_records": 853,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1111,
        "first": "2022-01-24",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "001391",
      "exchange": "XSHE",
      "provider_symbol": "sz001391",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2025-06-16",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 253,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 401,
        "first": "2024-12-30",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "001965",
      "exchange": "XSHE",
      "provider_symbol": "sz001965",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2024-06-17",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 494,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2103,
        "first": "2017-12-25",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "001979",
      "exchange": "XSHE",
      "provider_symbol": "sz001979",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 10,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2572,
        "first": "2015-12-30",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002001",
      "exchange": "XSHE",
      "provider_symbol": "sz002001",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5330,
        "first": "2004-06-25",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002007",
      "exchange": "XSHE",
      "provider_symbol": "sz002007",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2025-06-13",
      "candidate_member_records": 832,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5314,
        "first": "2004-06-25",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002008",
      "exchange": "XSHE",
      "provider_symbol": "sz002008",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2023-06-09",
      "candidate_member_records": 347,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5302,
        "first": "2004-06-25",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002008.SZ.bars.parquet",
        "bytes": 96388,
        "sourcehash": "68571ad057f2dd59d19604e5c60890447677e6f5ace5787f73c491ef44d23e1b",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "002024",
      "exchange": "XSHE",
      "provider_symbol": "sz002024",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-06-10",
      "candidate_member_records": 103,
      "missing_close_member_records_reused": 1,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5286,
        "first": "2004-07-21",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002027",
      "exchange": "XSHE",
      "provider_symbol": "sz002027",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5213,
        "first": "2004-08-04",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002028",
      "exchange": "XSHE",
      "provider_symbol": "sz002028",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2024-12-16",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 371,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5315,
        "first": "2004-08-05",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002032",
      "exchange": "XSHE",
      "provider_symbol": "sz002032",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2023-06-09",
      "candidate_member_records": 347,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5247,
        "first": "2004-08-17",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002044",
      "exchange": "XSHE",
      "provider_symbol": "sz002044",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-06-10",
      "candidate_member_records": 103,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4808,
        "first": "2005-05-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002049",
      "exchange": "XSHE",
      "provider_symbol": "sz002049",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 10,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4818,
        "first": "2005-06-06",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002049.SZ.bars.parquet",
        "bytes": 94216,
        "sourcehash": "4033b6f49366f1e5b395ee2fc43b0de4c928d91857d2293c205725c67a460287",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "002050",
      "exchange": "XSHE",
      "provider_symbol": "sz002050",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4931,
        "first": "2005-06-07",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002050.SZ.bars.parquet",
        "bytes": 91246,
        "sourcehash": "bd989c571826d44536b4f19cd8d43f879516396a0dfb81df4c9660b959af0bd4",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "002064",
      "exchange": "XSHE",
      "provider_symbol": "sz002064",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2023-12-08",
      "candidate_member_records": 460,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4836,
        "first": "2006-08-23",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002074",
      "exchange": "XSHE",
      "provider_symbol": "sz002074",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 982,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4594,
        "first": "2006-10-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002120",
      "exchange": "XSHE",
      "provider_symbol": "sz002120",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2023-12-08",
      "candidate_member_records": 469,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4607,
        "first": "2007-03-06",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002129",
      "exchange": "XSHE",
      "provider_symbol": "sz002129",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2025-12-12",
      "candidate_member_records": 956,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4156,
        "first": "2007-04-20",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002142",
      "exchange": "XSHE",
      "provider_symbol": "sz002142",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4621,
        "first": "2007-07-19",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002153",
      "exchange": "XSHE",
      "provider_symbol": "sz002153",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-01-14",
      "candidate_member_records": 9,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4498,
        "first": "2007-08-13",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002157",
      "exchange": "XSHE",
      "provider_symbol": "sz002157",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-06-10",
      "candidate_member_records": 103,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4505,
        "first": "2007-08-17",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002179",
      "exchange": "XSHE",
      "provider_symbol": "sz002179",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4555,
        "first": "2007-11-01",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002179.SZ.bars.parquet",
        "bytes": 92694,
        "sourcehash": "b961ba3cc08da29a01a66bdd9b72c5dd3414e16c145094400f8acad1e8f426e7",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "002180",
      "exchange": "XSHE",
      "provider_symbol": "sz002180",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-03-20",
      "candidate_member_last": "2025-12-12",
      "candidate_member_records": 665,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4219,
        "first": "2007-11-13",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002202",
      "exchange": "XSHE",
      "provider_symbol": "sz002202",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 602,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4504,
        "first": "2007-12-26",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002230",
      "exchange": "XSHE",
      "provider_symbol": "sz002230",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4358,
        "first": "2008-05-12",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002230.SZ.bars.parquet",
        "bytes": 92692,
        "sourcehash": "1c47a09bfd53be59763bdb06e3e61f470e966040df0b23ec6a5d317a9f5d32e8",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "002236",
      "exchange": "XSHE",
      "provider_symbol": "sz002236",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4415,
        "first": "2008-05-20",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002241",
      "exchange": "XSHE",
      "provider_symbol": "sz002241",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4407,
        "first": "2008-05-22",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002241.SZ.bars.parquet",
        "bytes": 95221,
        "sourcehash": "721e0aaec281d9ecce9217d65e7f481469f11cb8ffc5a50f3b9e81cd726322f4",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "002252",
      "exchange": "XSHE",
      "provider_symbol": "sz002252",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-12",
      "candidate_member_records": 1074,
      "missing_close_member_records_reused": 10,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3922,
        "first": "2008-06-23",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002271",
      "exchange": "XSHE",
      "provider_symbol": "sz002271",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2025-06-13",
      "candidate_member_records": 832,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4334,
        "first": "2008-09-10",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002304",
      "exchange": "XSHE",
      "provider_symbol": "sz002304",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4070,
        "first": "2009-11-06",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002304.SZ.bars.parquet",
        "bytes": 97511,
        "sourcehash": "fa3c470de3d6361fd3e357be98f5139d5aba130c091d70dfec51d5c56512a9b9",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "002311",
      "exchange": "XSHE",
      "provider_symbol": "sz002311",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4042,
        "first": "2009-11-27",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002352",
      "exchange": "XSHE",
      "provider_symbol": "sz002352",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3961,
        "first": "2010-02-05",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002353",
      "exchange": "XSHE",
      "provider_symbol": "sz002353",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2026-06-15",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 11,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3899,
        "first": "2010-02-05",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002371",
      "exchange": "XSHE",
      "provider_symbol": "sz002371",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3914,
        "first": "2010-03-16",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002371.SZ.bars.parquet",
        "bytes": 101948,
        "sourcehash": "469f8a9b1828c4cbfed831711e71d1aa17b1060deac24bfa2baec0a79a20921c",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "002384",
      "exchange": "XSHE",
      "provider_symbol": "sz002384",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 138,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3767,
        "first": "2010-04-09",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002384.SZ.bars.parquet",
        "bytes": 90556,
        "sourcehash": "31adc77d4356e1e2b7a9770c3b4d7e974e2aaea0fc47437f9e2cdeff95c4d373",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "002410",
      "exchange": "XSHE",
      "provider_symbol": "sz002410",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2024-12-13",
      "candidate_member_records": 714,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3903,
        "first": "2010-05-25",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002410.SZ.bars.parquet",
        "bytes": 95382,
        "sourcehash": "5a8a4cfc015a8c3c080a5b0e269c0038e5e0eafacc50bd7a20dab05f427af7b9",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "002414",
      "exchange": "XSHE",
      "provider_symbol": "sz002414",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2023-12-08",
      "candidate_member_records": 469,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3822,
        "first": "2010-07-16",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002415",
      "exchange": "XSHE",
      "provider_symbol": "sz002415",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3891,
        "first": "2010-05-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002415.SZ.bars.parquet",
        "bytes": 86127,
        "sourcehash": "2090c0fd4858e4eaf098dcccb5474785b7a55e4fdbc57c8b424445646c67ee1c",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "002422",
      "exchange": "XSHE",
      "provider_symbol": "sz002422",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2024-12-16",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 371,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3914,
        "first": "2010-06-03",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002456",
      "exchange": "XSHE",
      "provider_symbol": "sz002456",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-01-14",
      "candidate_member_records": 9,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3819,
        "first": "2010-08-03",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002459",
      "exchange": "XSHE",
      "provider_symbol": "sz002459",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2026-06-12",
      "candidate_member_records": 1065,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3805,
        "first": "2010-08-10",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002460",
      "exchange": "XSHE",
      "provider_symbol": "sz002460",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3807,
        "first": "2010-08-10",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002460.SZ.bars.parquet",
        "bytes": 97206,
        "sourcehash": "0cd93525f6376f4e49d979a0b24432a674b352a00ea9769875953de8e5a29ae3",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "002463",
      "exchange": "XSHE",
      "provider_symbol": "sz002463",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 380,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3881,
        "first": "2010-08-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002466",
      "exchange": "XSHE",
      "provider_symbol": "sz002466",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1076,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3722,
        "first": "2010-08-31",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002466.SZ.bars.parquet",
        "bytes": 97982,
        "sourcehash": "c1de57d065df58a70a5e62cb96ec6ac73139a65146915c4bed1c1d7e6aff3fab",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "002475",
      "exchange": "XSHE",
      "provider_symbol": "sz002475",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3842,
        "first": "2010-09-15",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002475.SZ.bars.parquet",
        "bytes": 94741,
        "sourcehash": "ea5b78169e1b8a77e9f2a707b30b4d60ef410b513b9fc74b22ce11c0c34abd77",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "002493",
      "exchange": "XSHE",
      "provider_symbol": "sz002493",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3832,
        "first": "2010-11-02",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002508",
      "exchange": "XSHE",
      "provider_symbol": "sz002508",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-01-14",
      "candidate_member_records": 9,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3821,
        "first": "2010-11-23",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002532",
      "exchange": "XSHE",
      "provider_symbol": "sz002532",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2026-06-15",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 11,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3681,
        "first": "2010-12-31",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002555",
      "exchange": "XSHE",
      "provider_symbol": "sz002555",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2025-06-13",
      "candidate_member_records": 832,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3478,
        "first": "2011-03-02",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002555.SZ.bars.parquet",
        "bytes": 94011,
        "sourcehash": "046a21adcfc112ede0a055b4f2d0341a2c811593ce2c768f1d094f8103010077",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "002558",
      "exchange": "XSHE",
      "provider_symbol": "sz002558",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 20,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3392,
        "first": "2011-03-02",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002568",
      "exchange": "XSHE",
      "provider_symbol": "sz002568",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2023-03-17",
      "candidate_member_records": 282,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3673,
        "first": "2011-03-25",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002594",
      "exchange": "XSHE",
      "provider_symbol": "sz002594",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3670,
        "first": "2011-06-30",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002594.SZ.bars.parquet",
        "bytes": 99836,
        "sourcehash": "f9a72b350802671f56d32c410e80d935564f72fe1023f1673a5c242e14d89a5f",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "002600",
      "exchange": "XSHE",
      "provider_symbol": "sz002600",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 600,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3415,
        "first": "2011-07-15",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002601",
      "exchange": "XSHE",
      "provider_symbol": "sz002601",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-12",
      "candidate_member_records": 1074,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3565,
        "first": "2011-07-15",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002602",
      "exchange": "XSHE",
      "provider_symbol": "sz002602",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 358,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3191,
        "first": "2011-07-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002603",
      "exchange": "XSHE",
      "provider_symbol": "sz002603",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-12-11",
      "candidate_member_last": "2024-12-13",
      "candidate_member_records": 245,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3642,
        "first": "2011-07-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002607",
      "exchange": "XSHE",
      "provider_symbol": "sz002607",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2023-03-17",
      "candidate_member_records": 291,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3477,
        "first": "2011-08-10",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002624",
      "exchange": "XSHE",
      "provider_symbol": "sz002624",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-06-10",
      "candidate_member_records": 103,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3215,
        "first": "2011-10-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002625",
      "exchange": "XSHE",
      "provider_symbol": "sz002625",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2025-12-15",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 129,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3286,
        "first": "2011-11-03",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002648",
      "exchange": "XSHE",
      "provider_symbol": "sz002648",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 982,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3533,
        "first": "2011-12-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002673",
      "exchange": "XSHE",
      "provider_symbol": "sz002673",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-01-14",
      "candidate_member_records": 9,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3460,
        "first": "2012-05-03",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002709",
      "exchange": "XSHE",
      "provider_symbol": "sz002709",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1076,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3033,
        "first": "2014-01-23",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002714",
      "exchange": "XSHE",
      "provider_symbol": "sz002714",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3032,
        "first": "2014-01-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002736",
      "exchange": "XSHE",
      "provider_symbol": "sz002736",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 10,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2816,
        "first": "2014-12-29",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002739",
      "exchange": "XSHE",
      "provider_symbol": "sz002739",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-01-14",
      "candidate_member_records": 9,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2367,
        "first": "2015-01-22",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002756",
      "exchange": "XSHE",
      "provider_symbol": "sz002756",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-03-20",
      "candidate_member_last": "2023-12-08",
      "candidate_member_records": 178,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2608,
        "first": "2015-05-15",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002773",
      "exchange": "XSHE",
      "provider_symbol": "sz002773",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-01-14",
      "candidate_member_records": 9,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2714,
        "first": "2015-06-26",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002791",
      "exchange": "XSHE",
      "provider_symbol": "sz002791",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2023-03-17",
      "candidate_member_records": 282,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2530,
        "first": "2016-03-29",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002812",
      "exchange": "XSHE",
      "provider_symbol": "sz002812",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2025-06-13",
      "candidate_member_records": 832,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2317,
        "first": "2016-09-14",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002812.SZ.bars.parquet",
        "bytes": 95476,
        "sourcehash": "ee30fa1480fdfceed7e6bc52e4b923c3067c6652dfa2d3a70284c632c2feb032",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "002821",
      "exchange": "XSHE",
      "provider_symbol": "sz002821",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2024-12-13",
      "candidate_member_records": 714,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2373,
        "first": "2016-11-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002821.SZ.bars.parquet",
        "bytes": 98045,
        "sourcehash": "4f0e688db513c0b149a7ad4955aa70e04c5478e64f828a965ab63ef04fbc667d",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "002837",
      "exchange": "XSHE",
      "provider_symbol": "sz002837",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2026-06-15",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 11,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2268,
        "first": "2016-12-29",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002841",
      "exchange": "XSHE",
      "provider_symbol": "sz002841",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2024-12-13",
      "candidate_member_records": 714,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2330,
        "first": "2017-01-19",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002916",
      "exchange": "XSHE",
      "provider_symbol": "sz002916",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2109,
        "first": "2017-12-13",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002920",
      "exchange": "XSHE",
      "provider_symbol": "sz002920",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 982,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2102,
        "first": "2017-12-26",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002938",
      "exchange": "XSHE",
      "provider_symbol": "sz002938",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1923,
        "first": "2018-09-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002939",
      "exchange": "XSHE",
      "provider_symbol": "sz002939",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-01-14",
      "candidate_member_records": 9,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1901,
        "first": "2018-10-26",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "002945",
      "exchange": "XSHE",
      "provider_symbol": "sz002945",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-01-14",
      "candidate_member_records": 9,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1844,
        "first": "2019-01-17",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "003816",
      "exchange": "XSHE",
      "provider_symbol": "sz003816",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1697,
        "first": "2019-08-26",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300003",
      "exchange": "XSHE",
      "provider_symbol": "sz300003",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2023-03-17",
      "candidate_member_records": 291,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3966,
        "first": "2009-10-30",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300003.SZ.bars.parquet",
        "bytes": 93434,
        "sourcehash": "2fc70a4dc9bf99af77c665ca4ce220e92939627ce91d1ca28a0ed9be1e3ba8d4",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "300014",
      "exchange": "XSHE",
      "provider_symbol": "sz300014",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4025,
        "first": "2009-10-30",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300014.SZ.bars.parquet",
        "bytes": 98965,
        "sourcehash": "cf4a1a1584df77588d5ac996a28774cff36c3d1e4135794083fff2467d99b73b",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "300015",
      "exchange": "XSHE",
      "provider_symbol": "sz300015",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4063,
        "first": "2009-10-30",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300033",
      "exchange": "XSHE",
      "provider_symbol": "sz300033",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4027,
        "first": "2009-12-25",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300059",
      "exchange": "XSHE",
      "provider_symbol": "sz300059",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3928,
        "first": "2010-03-19",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300059.SZ.bars.parquet",
        "bytes": 91126,
        "sourcehash": "3833d23a9a43879133213f1029d9f859ebcc11f98f7d773cc2309f0a1c35cc49",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "300122",
      "exchange": "XSHE",
      "provider_symbol": "sz300122",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3788,
        "first": "2010-09-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300122.SZ.bars.parquet",
        "bytes": 95303,
        "sourcehash": "552bb59bc416a1a570076f8e9a9d12913b7a346ca0cb5c918946224f16c638ea",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "300124",
      "exchange": "XSHE",
      "provider_symbol": "sz300124",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3843,
        "first": "2010-09-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300124.SZ.bars.parquet",
        "bytes": 91373,
        "sourcehash": "8159a3a9974da208b5b7b570a40bee2396582597acfbfdb580c438708169b5e3",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "300136",
      "exchange": "XSHE",
      "provider_symbol": "sz300136",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-01-14",
      "candidate_member_records": 9,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3767,
        "first": "2010-11-05",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300136.SZ.bars.parquet",
        "bytes": 88542,
        "sourcehash": "2edff18fc24d395106d02398c96df74c1e10ca01c4d4356e1bbfc257b82b5475",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "300142",
      "exchange": "XSHE",
      "provider_symbol": "sz300142",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2024-12-13",
      "candidate_member_records": 714,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3560,
        "first": "2010-11-12",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300144",
      "exchange": "XSHE",
      "provider_symbol": "sz300144",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-06-10",
      "candidate_member_records": 103,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3725,
        "first": "2010-12-09",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300207",
      "exchange": "XSHE",
      "provider_symbol": "sz300207",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2023-12-08",
      "candidate_member_records": 366,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3676,
        "first": "2011-04-21",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300223",
      "exchange": "XSHE",
      "provider_symbol": "sz300223",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2024-12-13",
      "candidate_member_records": 611,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3456,
        "first": "2011-05-31",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300223.SZ.bars.parquet",
        "bytes": 88040,
        "sourcehash": "b9bdc668c36587becf74bb9318a3027435bc5649a5f711dddcbdfc0bf71da5c8",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "300251",
      "exchange": "XSHE",
      "provider_symbol": "sz300251",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2025-12-15",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 129,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3541,
        "first": "2011-08-03",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300274",
      "exchange": "XSHE",
      "provider_symbol": "sz300274",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3571,
        "first": "2011-11-02",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300274.SZ.bars.parquet",
        "bytes": 96774,
        "sourcehash": "989f96f552c1796e84af9029a809bcf218411c6f504f973a094688fc243c57aa",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "300308",
      "exchange": "XSHE",
      "provider_symbol": "sz300308",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-12-11",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 616,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3326,
        "first": "2012-04-10",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300308.SZ.bars.parquet",
        "bytes": 100466,
        "sourcehash": "cafd5b644db81518967aaa66b0c4d9f25e01050e7e145390ce2a75203c6b02c1",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "300316",
      "exchange": "XSHE",
      "provider_symbol": "sz300316",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1076,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3371,
        "first": "2012-05-11",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300347",
      "exchange": "XSHE",
      "provider_symbol": "sz300347",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-12",
      "candidate_member_records": 1074,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3267,
        "first": "2012-08-17",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300347.SZ.bars.parquet",
        "bytes": 99452,
        "sourcehash": "fa7c2d13e96f59a6f3877ca85fc677dec9ff5b5c8c7d7d379746eca1d34887ac",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "300394",
      "exchange": "XSHE",
      "provider_symbol": "sz300394",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2024-12-16",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 371,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2787,
        "first": "2015-02-17",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300394.SZ.bars.parquet",
        "bytes": 97650,
        "sourcehash": "2e7883172bb552e352af810963adf6ea3c4d26058c0890a5180eca3a1c4bc0f0",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "300408",
      "exchange": "XSHE",
      "provider_symbol": "sz300408",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2841,
        "first": "2014-12-03",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300413",
      "exchange": "XSHE",
      "provider_symbol": "sz300413",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2558,
        "first": "2015-01-21",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300418",
      "exchange": "XSHE",
      "provider_symbol": "sz300418",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2024-06-17",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 494,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2747,
        "first": "2015-01-21",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300433",
      "exchange": "XSHE",
      "provider_symbol": "sz300433",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2758,
        "first": "2015-03-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300442",
      "exchange": "XSHE",
      "provider_symbol": "sz300442",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2024-06-17",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 494,
      "missing_close_member_records_reused": 6,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2741,
        "first": "2015-04-24",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300450",
      "exchange": "XSHE",
      "provider_symbol": "sz300450",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 843,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2593,
        "first": "2015-05-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300454",
      "exchange": "XSHE",
      "provider_symbol": "sz300454",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2024-12-13",
      "candidate_member_records": 611,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2011,
        "first": "2018-05-16",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300476",
      "exchange": "XSHE",
      "provider_symbol": "sz300476",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2025-12-15",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 129,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2719,
        "first": "2015-06-11",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300496",
      "exchange": "XSHE",
      "provider_symbol": "sz300496",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2024-12-13",
      "candidate_member_records": 611,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2540,
        "first": "2015-12-10",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300498",
      "exchange": "XSHE",
      "provider_symbol": "sz300498",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2619,
        "first": "2015-11-02",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300502",
      "exchange": "XSHE",
      "provider_symbol": "sz300502",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2024-12-16",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 371,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2546,
        "first": "2016-03-03",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300502.SZ.bars.parquet",
        "bytes": 100010,
        "sourcehash": "8af4e760f5e4a3efc3f3ceb3e2de79440b3598dae199bed1baa5a038592be4a0",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "300529",
      "exchange": "XSHE",
      "provider_symbol": "sz300529",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2023-06-09",
      "candidate_member_records": 347,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2444,
        "first": "2016-08-02",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300558",
      "exchange": "XSHE",
      "provider_symbol": "sz300558",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-06-10",
      "candidate_member_records": 103,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2382,
        "first": "2016-11-07",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300595",
      "exchange": "XSHE",
      "provider_symbol": "sz300595",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2023-06-09",
      "candidate_member_records": 347,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2332,
        "first": "2017-01-17",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300601",
      "exchange": "XSHE",
      "provider_symbol": "sz300601",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2023-12-08",
      "candidate_member_records": 469,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2322,
        "first": "2017-02-07",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300628",
      "exchange": "XSHE",
      "provider_symbol": "sz300628",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2294,
        "first": "2017-03-17",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300661",
      "exchange": "XSHE",
      "provider_symbol": "sz300661",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 982,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2232,
        "first": "2017-06-06",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300661.SZ.bars.parquet",
        "bytes": 92431,
        "sourcehash": "e4f6298c84f6eb0ff5adfde11848d0b054d3c95bc835d37fc2c1a83b0d72474d",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "300676",
      "exchange": "XSHE",
      "provider_symbol": "sz300676",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-06-10",
      "candidate_member_records": 103,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2204,
        "first": "2017-07-14",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300677",
      "exchange": "XSHE",
      "provider_symbol": "sz300677",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-06-10",
      "candidate_member_records": 103,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2209,
        "first": "2017-07-21",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300750",
      "exchange": "XSHE",
      "provider_symbol": "sz300750",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1076,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1993,
        "first": "2018-06-11",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300750.SZ.bars.parquet",
        "bytes": 82344,
        "sourcehash": "935ed24bf9f13c739cb291bd42689b5db40c659457e7e0f705996816bebd38e1",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "300751",
      "exchange": "XSHE",
      "provider_symbol": "sz300751",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2024-12-13",
      "candidate_member_records": 611,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1891,
        "first": "2018-11-09",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300759",
      "exchange": "XSHE",
      "provider_symbol": "sz300759",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2026-06-12",
      "candidate_member_records": 1065,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1837,
        "first": "2019-01-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300760",
      "exchange": "XSHE",
      "provider_symbol": "sz300760",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1076,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1909,
        "first": "2018-10-16",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300763",
      "exchange": "XSHE",
      "provider_symbol": "sz300763",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2024-06-14",
      "candidate_member_records": 488,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1806,
        "first": "2019-03-19",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300769",
      "exchange": "XSHE",
      "provider_symbol": "sz300769",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-03-20",
      "candidate_member_last": "2023-12-08",
      "candidate_member_records": 178,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1788,
        "first": "2019-04-15",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300782",
      "exchange": "XSHE",
      "provider_symbol": "sz300782",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2026-06-12",
      "candidate_member_records": 1065,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1746,
        "first": "2019-06-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300803",
      "exchange": "XSHE",
      "provider_symbol": "sz300803",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2025-12-15",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 129,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1643,
        "first": "2019-11-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300832",
      "exchange": "XSHE",
      "provider_symbol": "sz300832",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2024-06-17",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 494,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1528,
        "first": "2020-05-12",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300866",
      "exchange": "XSHE",
      "provider_symbol": "sz300866",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 411,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1456,
        "first": "2020-08-24",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300888",
      "exchange": "XSHE",
      "provider_symbol": "sz300888",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2022-06-10",
      "candidate_member_records": 94,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1440,
        "first": "2020-09-17",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300896",
      "exchange": "XSHE",
      "provider_symbol": "sz300896",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1076,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1433,
        "first": "2020-09-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300919",
      "exchange": "XSHE",
      "provider_symbol": "sz300919",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2024-12-13",
      "candidate_member_records": 611,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1377,
        "first": "2020-12-23",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300957",
      "exchange": "XSHE",
      "provider_symbol": "sz300957",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2024-12-13",
      "candidate_member_records": 611,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1317,
        "first": "2021-03-25",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300979",
      "exchange": "XSHE",
      "provider_symbol": "sz300979",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2026-06-12",
      "candidate_member_records": 971,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1296,
        "first": "2021-04-26",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "300999",
      "exchange": "XSHE",
      "provider_symbol": "sz300999",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1076,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1426,
        "first": "2020-10-15",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "301165",
      "exchange": "XSHE",
      "provider_symbol": "sz301165",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2026-06-15",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 11,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 915,
        "first": "2022-11-21",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "301236",
      "exchange": "XSHE",
      "provider_symbol": "sz301236",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2025-06-16",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 253,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1082,
        "first": "2022-03-15",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "301269",
      "exchange": "XSHE",
      "provider_symbol": "sz301269",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-12-11",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 616,
      "missing_close_member_records_reused": 10,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 980,
        "first": "2022-07-29",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "301308",
      "exchange": "XSHE",
      "provider_symbol": "sz301308",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2026-06-15",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 11,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 985,
        "first": "2022-08-05",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "302132",
      "exchange": "XSHE",
      "provider_symbol": "sz302132",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2025-06-16",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 253,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3796,
        "first": "2010-08-27",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600000",
      "exchange": "XSHG",
      "provider_symbol": "sh600000",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6377,
        "first": "1999-11-10",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600009",
      "exchange": "XSHG",
      "provider_symbol": "sh600009",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 1,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6864,
        "first": "1998-02-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600010",
      "exchange": "XSHG",
      "provider_symbol": "sh600010",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6063,
        "first": "2001-03-09",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600011",
      "exchange": "XSHG",
      "provider_symbol": "sh600011",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5928,
        "first": "2001-12-06",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600015",
      "exchange": "XSHG",
      "provider_symbol": "sh600015",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5477,
        "first": "2003-09-12",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600016",
      "exchange": "XSHG",
      "provider_symbol": "sh600016",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6166,
        "first": "2000-12-19",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600018",
      "exchange": "XSHG",
      "provider_symbol": "sh600018",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4748,
        "first": "2006-10-26",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600019",
      "exchange": "XSHG",
      "provider_symbol": "sh600019",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6078,
        "first": "2000-12-12",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600023",
      "exchange": "XSHG",
      "provider_symbol": "sh600023",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-12-11",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 616,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3086,
        "first": "2013-12-19",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600025",
      "exchange": "XSHG",
      "provider_symbol": "sh600025",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2111,
        "first": "2017-12-15",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600026",
      "exchange": "XSHG",
      "provider_symbol": "sh600026",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2024-06-17",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 494,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5735,
        "first": "2002-05-23",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600027",
      "exchange": "XSHG",
      "provider_symbol": "sh600027",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2024-06-17",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 494,
      "missing_close_member_records_reused": 10,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5169,
        "first": "2005-02-03",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600028",
      "exchange": "XSHG",
      "provider_symbol": "sh600028",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6027,
        "first": "2001-08-08",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600029",
      "exchange": "XSHG",
      "provider_symbol": "sh600029",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5508,
        "first": "2003-07-25",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600030",
      "exchange": "XSHG",
      "provider_symbol": "sh600030",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 6,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5643,
        "first": "2003-01-06",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600030.SS.bars.parquet",
        "bytes": 85040,
        "sourcehash": "2b83a523852d79541daa29f56cc70fff70fca6df652c7174badb99b1a0b08b99",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "600031",
      "exchange": "XSHG",
      "provider_symbol": "sh600031",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5576,
        "first": "2003-07-03",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600036",
      "exchange": "XSHG",
      "provider_symbol": "sh600036",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5849,
        "first": "2002-04-09",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600039",
      "exchange": "XSHG",
      "provider_symbol": "sh600039",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-03-20",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 794,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5545,
        "first": "2003-03-25",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600048",
      "exchange": "XSHG",
      "provider_symbol": "sh600048",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4855,
        "first": "2006-07-31",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600050",
      "exchange": "XSHG",
      "provider_symbol": "sh600050",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5662,
        "first": "2002-10-09",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600061",
      "exchange": "XSHG",
      "provider_symbol": "sh600061",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6901,
        "first": "1997-05-19",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600066",
      "exchange": "XSHG",
      "provider_symbol": "sh600066",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2024-12-16",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 371,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 7015,
        "first": "1997-05-08",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600079",
      "exchange": "XSHG",
      "provider_symbol": "sh600079",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-06-10",
      "candidate_member_records": 103,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6982,
        "first": "1997-06-06",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600085",
      "exchange": "XSHG",
      "provider_symbol": "sh600085",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 7034,
        "first": "1997-06-25",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600089",
      "exchange": "XSHG",
      "provider_symbol": "sh600089",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 982,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6891,
        "first": "1997-06-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600104",
      "exchange": "XSHG",
      "provider_symbol": "sh600104",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6857,
        "first": "1997-11-25",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600109",
      "exchange": "XSHG",
      "provider_symbol": "sh600109",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-06-10",
      "candidate_member_records": 103,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6867,
        "first": "1997-08-07",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600111",
      "exchange": "XSHG",
      "provider_symbol": "sh600111",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6956,
        "first": "1997-09-24",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600111.SS.bars.parquet",
        "bytes": 87747,
        "sourcehash": "0dba4a22aa7d33418b09132e7b4a61462465ee87c1b92175347a473e3a8976f6",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "600115",
      "exchange": "XSHG",
      "provider_symbol": "sh600115",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6784,
        "first": "1997-11-05",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600118",
      "exchange": "XSHG",
      "provider_symbol": "sh600118",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 20,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6954,
        "first": "1997-09-08",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600132",
      "exchange": "XSHG",
      "provider_symbol": "sh600132",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2024-12-13",
      "candidate_member_records": 714,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6849,
        "first": "1997-10-30",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600143",
      "exchange": "XSHG",
      "provider_symbol": "sh600143",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-06-10",
      "candidate_member_records": 103,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5250,
        "first": "2004-06-23",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600150",
      "exchange": "XSHG",
      "provider_symbol": "sh600150",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 14,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6641,
        "first": "1998-05-20",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600160",
      "exchange": "XSHG",
      "provider_symbol": "sh600160",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2024-12-16",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 371,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6716,
        "first": "1998-06-26",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600161",
      "exchange": "XSHG",
      "provider_symbol": "sh600161",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-12",
      "candidate_member_records": 774,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6605,
        "first": "1998-06-16",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600176",
      "exchange": "XSHG",
      "provider_symbol": "sh600176",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6510,
        "first": "1999-04-22",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600183",
      "exchange": "XSHG",
      "provider_symbol": "sh600183",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6661,
        "first": "1998-10-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600188",
      "exchange": "XSHG",
      "provider_symbol": "sh600188",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 982,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6752,
        "first": "1998-07-01",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600188.SS.bars.parquet",
        "bytes": 54139,
        "sourcehash": "e32a7edd6a63e6b8a1512f681dbb3344fd03a9aa590c837a417058b1711d5d77",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "600196",
      "exchange": "XSHG",
      "provider_symbol": "sh600196",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6718,
        "first": "1998-08-07",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600196.SS.bars.parquet",
        "bytes": 87171,
        "sourcehash": "19617da81a2c2956941aeeca4dd29d8bbd362747e06a64d683a5d4b701483952",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "600219",
      "exchange": "XSHG",
      "provider_symbol": "sh600219",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 982,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6295,
        "first": "1999-12-23",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600221",
      "exchange": "XSHG",
      "provider_symbol": "sh600221",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2026-06-15",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 11,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6217,
        "first": "1999-11-25",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600233",
      "exchange": "XSHG",
      "provider_symbol": "sh600233",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 803,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6225,
        "first": "2000-06-08",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600276",
      "exchange": "XSHG",
      "provider_symbol": "sh600276",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6227,
        "first": "2000-10-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600276.SS.bars.parquet",
        "bytes": 97200,
        "sourcehash": "77a288f4b75d5510572378b09826b0361b34bba2c199a62623fe744e0726cb22",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "600299",
      "exchange": "XSHG",
      "provider_symbol": "sh600299",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-01-14",
      "candidate_member_records": 9,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6117,
        "first": "2000-04-20",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600309",
      "exchange": "XSHG",
      "provider_symbol": "sh600309",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6022,
        "first": "2001-01-05",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600332",
      "exchange": "XSHG",
      "provider_symbol": "sh600332",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2025-12-12",
      "candidate_member_records": 956,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5966,
        "first": "2001-02-06",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600340",
      "exchange": "XSHG",
      "provider_symbol": "sh600340",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-01-14",
      "candidate_member_records": 9,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5297,
        "first": "2003-12-30",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600346",
      "exchange": "XSHG",
      "provider_symbol": "sh600346",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5716,
        "first": "2001-08-20",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600352",
      "exchange": "XSHG",
      "provider_symbol": "sh600352",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2023-03-17",
      "candidate_member_records": 291,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5522,
        "first": "2003-08-01",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600362",
      "exchange": "XSHG",
      "provider_symbol": "sh600362",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5897,
        "first": "2002-01-11",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600362.SS.bars.parquet",
        "bytes": 81443,
        "sourcehash": "c7912d320d53d0d4cdd70609199cede6833d06ea254074f0d7cfde4f7c00d1d7",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "600372",
      "exchange": "XSHG",
      "provider_symbol": "sh600372",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-12-11",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 616,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5602,
        "first": "2001-07-06",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600377",
      "exchange": "XSHG",
      "provider_symbol": "sh600377",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2024-12-16",
      "candidate_member_last": "2026-06-12",
      "candidate_member_records": 360,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6135,
        "first": "2001-01-16",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600383",
      "exchange": "XSHG",
      "provider_symbol": "sh600383",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2023-12-08",
      "candidate_member_records": 469,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6019,
        "first": "2001-04-12",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600406",
      "exchange": "XSHG",
      "provider_symbol": "sh600406",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5348,
        "first": "2003-10-16",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600415",
      "exchange": "XSHG",
      "provider_symbol": "sh600415",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2024-06-17",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 494,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5774,
        "first": "2002-05-09",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600426",
      "exchange": "XSHG",
      "provider_symbol": "sh600426",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5819,
        "first": "2002-06-20",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600436",
      "exchange": "XSHG",
      "provider_symbol": "sh600436",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5580,
        "first": "2003-06-16",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600438",
      "exchange": "XSHG",
      "provider_symbol": "sh600438",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 10,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5255,
        "first": "2004-03-02",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600438.SS.bars.parquet",
        "bytes": 89050,
        "sourcehash": "819e2e8827d06fa936729ba7c3eca7661b7fd54a8ffcaab84037d67ca09f2202",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "600460",
      "exchange": "XSHG",
      "provider_symbol": "sh600460",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 982,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5570,
        "first": "2003-03-11",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600460.SS.bars.parquet",
        "bytes": 86194,
        "sourcehash": "a919e6dc3f7f7a75e3a7991e42c81a6d424b2761d0865af9b2404b16b060f7d7",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "600482",
      "exchange": "XSHG",
      "provider_symbol": "sh600482",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 380,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5172,
        "first": "2004-07-14",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600489",
      "exchange": "XSHG",
      "provider_symbol": "sh600489",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 907,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5511,
        "first": "2003-08-14",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600515",
      "exchange": "XSHG",
      "provider_symbol": "sh600515",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-12-11",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 616,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5330,
        "first": "2002-08-06",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600519",
      "exchange": "XSHG",
      "provider_symbol": "sh600519",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5992,
        "first": "2001-08-27",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600519.SS.bars.parquet",
        "bytes": 99612,
        "sourcehash": "32179a25ec29302eb2374b05ddf155f7dd8dfc76cd9ea3d82b6f7a9e7e4901f8",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "600521",
      "exchange": "XSHG",
      "provider_symbol": "sh600521",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-01-14",
      "candidate_member_records": 9,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5641,
        "first": "2003-03-04",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600522",
      "exchange": "XSHG",
      "provider_symbol": "sh600522",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 138,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5658,
        "first": "2002-10-24",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600547",
      "exchange": "XSHG",
      "provider_symbol": "sh600547",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5347,
        "first": "2003-08-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600549",
      "exchange": "XSHG",
      "provider_symbol": "sh600549",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2026-06-15",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 11,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5718,
        "first": "2002-11-07",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600570",
      "exchange": "XSHG",
      "provider_symbol": "sh600570",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5409,
        "first": "2003-12-16",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600584",
      "exchange": "XSHG",
      "provider_symbol": "sh600584",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 5,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5337,
        "first": "2003-06-03",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600584.SS.bars.parquet",
        "bytes": 86811,
        "sourcehash": "7882f4d92ba7f8e54f7b478eb1411410232e2c30598c0a36a830e913d39c341e",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "600585",
      "exchange": "XSHG",
      "provider_symbol": "sh600585",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5900,
        "first": "2002-02-07",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600588",
      "exchange": "XSHG",
      "provider_symbol": "sh600588",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6075,
        "first": "2001-05-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600588.SS.bars.parquet",
        "bytes": 90865,
        "sourcehash": "2b9bf3e134e9a466fc891edbf61fcd384d4832c01c16c5d3f01a42f2d5c45e67",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "600600",
      "exchange": "XSHG",
      "provider_symbol": "sh600600",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 7917,
        "first": "1993-08-27",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600600.SS.bars.parquet",
        "bytes": 88856,
        "sourcehash": "98bee590336d403be9386f52168c53c79394a74685fbcfa1d460d225ae389319",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "600606",
      "exchange": "XSHG",
      "provider_symbol": "sh600606",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2024-06-14",
      "candidate_member_records": 591,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 7946,
        "first": "1992-04-10",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600655",
      "exchange": "XSHG",
      "provider_symbol": "sh600655",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2023-03-17",
      "candidate_member_records": 291,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 7845,
        "first": "1992-09-02",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600660",
      "exchange": "XSHG",
      "provider_symbol": "sh600660",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 8009,
        "first": "1993-06-10",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600660.SS.bars.parquet",
        "bytes": 85041,
        "sourcehash": "682c8bfcc2bc969a2c1c900107f00d74ec0f3bb594c51e8647cd28a922ccd859",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "600674",
      "exchange": "XSHG",
      "provider_symbol": "sh600674",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-03-20",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 794,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 7817,
        "first": "1993-09-24",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600690",
      "exchange": "XSHG",
      "provider_symbol": "sh600690",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 7795,
        "first": "1993-11-19",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600703",
      "exchange": "XSHG",
      "provider_symbol": "sh600703",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-01-14",
      "candidate_member_records": 9,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6949,
        "first": "1996-05-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600703.SS.bars.parquet",
        "bytes": 86833,
        "sourcehash": "273ce733baea916a973674258795effc8b32a5af8fb9025bd25dc5e19748cce1",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "600705",
      "exchange": "XSHG",
      "provider_symbol": "sh600705",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-01-14",
      "candidate_member_records": 9,
      "missing_close_member_records_reused": 9,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 0,
        "first": null,
        "last": null,
        "format": "column absent"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600732",
      "exchange": "XSHG",
      "provider_symbol": "sh600732",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-06-12",
      "candidate_member_last": "2024-12-13",
      "candidate_member_records": 367,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6634,
        "first": "1996-08-16",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600741",
      "exchange": "XSHG",
      "provider_symbol": "sh600741",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 7111,
        "first": "1996-08-26",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600745",
      "exchange": "XSHG",
      "provider_symbol": "sh600745",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2025-06-13",
      "candidate_member_records": 832,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6410,
        "first": "1996-08-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600745.SS.bars.parquet",
        "bytes": 88248,
        "sourcehash": "8a734642c32bd2cb6dc71e4a69be18189647172ed79ead400c58164e3ae8ca70",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "600754",
      "exchange": "XSHG",
      "provider_symbol": "sh600754",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-06-12",
      "candidate_member_last": "2024-06-14",
      "candidate_member_records": 244,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 7026,
        "first": "1996-10-11",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600760",
      "exchange": "XSHG",
      "provider_symbol": "sh600760",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 7009,
        "first": "1996-10-11",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600760.SS.bars.parquet",
        "bytes": 88284,
        "sourcehash": "0b5de2b215daeba6e32916ca4a7b2ce479d49dc5f2d375db70e703d4e1221d1a",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "600763",
      "exchange": "XSHG",
      "provider_symbol": "sh600763",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2023-12-08",
      "candidate_member_records": 469,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6808,
        "first": "1996-10-30",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600795",
      "exchange": "XSHG",
      "provider_symbol": "sh600795",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6967,
        "first": "1997-03-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600803",
      "exchange": "XSHG",
      "provider_symbol": "sh600803",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-03-20",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 794,
      "missing_close_member_records_reused": 6,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 7644,
        "first": "1994-01-03",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600809",
      "exchange": "XSHG",
      "provider_symbol": "sh600809",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 7873,
        "first": "1994-01-06",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600809.SS.bars.parquet",
        "bytes": 88679,
        "sourcehash": "b455568cf2d7c98bbbf1a6bd7d8d60a09065658c1a5a99f14d3ab290ea4cc9e7",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "600837",
      "exchange": "XSHG",
      "provider_symbol": "sh600837",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2025-03-07",
      "candidate_member_records": 767,
      "missing_close_member_records_reused": 767,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 0,
        "first": null,
        "last": null,
        "format": "column absent"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600845",
      "exchange": "XSHG",
      "provider_symbol": "sh600845",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 7560,
        "first": "1994-03-11",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600848",
      "exchange": "XSHG",
      "provider_symbol": "sh600848",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-06-10",
      "candidate_member_records": 103,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 7424,
        "first": "1994-03-24",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600872",
      "exchange": "XSHG",
      "provider_symbol": "sh600872",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-06-10",
      "candidate_member_records": 103,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 7524,
        "first": "1995-01-24",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600875",
      "exchange": "XSHG",
      "provider_symbol": "sh600875",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-06-12",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 738,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 7317,
        "first": "1995-10-10",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600884",
      "exchange": "XSHG",
      "provider_symbol": "sh600884",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-03-20",
      "candidate_member_last": "2023-12-08",
      "candidate_member_records": 178,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 7315,
        "first": "1996-01-30",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600886",
      "exchange": "XSHG",
      "provider_symbol": "sh600886",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 7145,
        "first": "1996-01-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600887",
      "exchange": "XSHG",
      "provider_symbol": "sh600887",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 7285,
        "first": "1996-03-12",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600893",
      "exchange": "XSHG",
      "provider_symbol": "sh600893",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 6724,
        "first": "1996-04-08",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600893.SS.bars.parquet",
        "bytes": 91166,
        "sourcehash": "d443b07bab4e30fe9e7c60226d5c1a7fe4bddaa2bb1e4c22e6baee7136b1c835",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "600900",
      "exchange": "XSHG",
      "provider_symbol": "sh600900",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 1,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 5109,
        "first": "2003-11-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600905",
      "exchange": "XSHG",
      "provider_symbol": "sh600905",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1076,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1266,
        "first": "2021-06-10",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600918",
      "exchange": "XSHG",
      "provider_symbol": "sh600918",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1514,
        "first": "2020-06-03",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600919",
      "exchange": "XSHG",
      "provider_symbol": "sh600919",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2440,
        "first": "2016-08-02",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600926",
      "exchange": "XSHG",
      "provider_symbol": "sh600926",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2391,
        "first": "2016-10-27",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600930",
      "exchange": "XSHG",
      "provider_symbol": "sh600930",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2025-12-15",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 129,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 273,
        "first": "2025-07-16",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600938",
      "exchange": "XSHG",
      "provider_symbol": "sh600938",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-12-11",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 616,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1057,
        "first": "2022-04-21",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600941",
      "exchange": "XSHG",
      "provider_symbol": "sh600941",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 982,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1126,
        "first": "2022-01-05",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600958",
      "exchange": "XSHG",
      "provider_symbol": "sh600958",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 16,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2760,
        "first": "2015-03-23",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600989",
      "exchange": "XSHG",
      "provider_symbol": "sh600989",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1770,
        "first": "2019-05-16",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "600999",
      "exchange": "XSHG",
      "provider_symbol": "sh600999",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4057,
        "first": "2009-11-17",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601006",
      "exchange": "XSHG",
      "provider_symbol": "sh601006",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4857,
        "first": "2006-08-01",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601009",
      "exchange": "XSHG",
      "provider_symbol": "sh601009",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4624,
        "first": "2007-07-19",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601012",
      "exchange": "XSHG",
      "provider_symbol": "sh601012",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3455,
        "first": "2012-04-11",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/601012.SS.bars.parquet",
        "bytes": 93376,
        "sourcehash": "9edbb7b858946187ce153d89d3aacc476c061ecd0a55e0eae46149318c18debe",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "601018",
      "exchange": "XSHG",
      "provider_symbol": "sh601018",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2025-12-15",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 129,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3727,
        "first": "2010-09-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601021",
      "exchange": "XSHG",
      "provider_symbol": "sh601021",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2796,
        "first": "2015-01-21",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601058",
      "exchange": "XSHG",
      "provider_symbol": "sh601058",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2025-03-10",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 318,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3647,
        "first": "2011-06-30",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601059",
      "exchange": "XSHG",
      "provider_symbol": "sh601059",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-12-11",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 616,
      "missing_close_member_records_reused": 20,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 849,
        "first": "2023-02-01",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601066",
      "exchange": "XSHG",
      "provider_symbol": "sh601066",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1989,
        "first": "2018-06-20",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601077",
      "exchange": "XSHG",
      "provider_symbol": "sh601077",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 262,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1659,
        "first": "2019-10-29",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601088",
      "exchange": "XSHG",
      "provider_symbol": "sh601088",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 10,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4514,
        "first": "2007-10-09",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601100",
      "exchange": "XSHG",
      "provider_symbol": "sh601100",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3563,
        "first": "2011-10-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601108",
      "exchange": "XSHG",
      "provider_symbol": "sh601108",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-06-10",
      "candidate_member_records": 103,
      "missing_close_member_records_reused": 6,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2143,
        "first": "2017-10-24",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601111",
      "exchange": "XSHG",
      "provider_symbol": "sh601111",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4798,
        "first": "2006-08-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601117",
      "exchange": "XSHG",
      "provider_symbol": "sh601117",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 982,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4034,
        "first": "2010-01-07",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601127",
      "exchange": "XSHG",
      "provider_symbol": "sh601127",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2024-12-16",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 371,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2455,
        "first": "2016-06-15",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/601127.SS.bars.parquet",
        "bytes": 91699,
        "sourcehash": "82cfe79478928fc033d5cc5f1945a377828a3f3aaa4f871825016b4b870754a6",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "601136",
      "exchange": "XSHG",
      "provider_symbol": "sh601136",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2024-12-16",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 371,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 892,
        "first": "2022-12-22",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601138",
      "exchange": "XSHG",
      "provider_symbol": "sh601138",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1996,
        "first": "2018-06-08",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601155",
      "exchange": "XSHG",
      "provider_symbol": "sh601155",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2024-06-14",
      "candidate_member_records": 591,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2597,
        "first": "2015-12-04",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601162",
      "exchange": "XSHG",
      "provider_symbol": "sh601162",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-06-10",
      "candidate_member_records": 103,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1902,
        "first": "2018-10-19",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601166",
      "exchange": "XSHG",
      "provider_symbol": "sh601166",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4729,
        "first": "2007-02-05",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601169",
      "exchange": "XSHG",
      "provider_symbol": "sh601169",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4546,
        "first": "2007-09-19",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601186",
      "exchange": "XSHG",
      "provider_symbol": "sh601186",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4470,
        "first": "2008-03-10",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601211",
      "exchange": "XSHG",
      "provider_symbol": "sh601211",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 19,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2697,
        "first": "2015-06-26",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601216",
      "exchange": "XSHG",
      "provider_symbol": "sh601216",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2023-12-08",
      "candidate_member_records": 469,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3645,
        "first": "2011-02-22",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601225",
      "exchange": "XSHG",
      "provider_symbol": "sh601225",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3059,
        "first": "2014-01-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/601225.SS.bars.parquet",
        "bytes": 64832,
        "sourcehash": "ed50ceeb3ae92573e188dec0b214584ed41d1fe80cdd61f37bfe139398410a3a",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "601229",
      "exchange": "XSHG",
      "provider_symbol": "sh601229",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2377,
        "first": "2016-11-16",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601231",
      "exchange": "XSHG",
      "provider_symbol": "sh601231",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-06-10",
      "candidate_member_records": 103,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3512,
        "first": "2012-02-20",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601236",
      "exchange": "XSHG",
      "provider_symbol": "sh601236",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-12",
      "candidate_member_records": 1074,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1729,
        "first": "2019-07-05",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601238",
      "exchange": "XSHG",
      "provider_symbol": "sh601238",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3490,
        "first": "2012-03-29",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/601238.SS.bars.parquet",
        "bytes": 74994,
        "sourcehash": "81a9ed0d8327c8f616f1e6e392b596c128ca502000c203a4bf97dac84115be73",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "601288",
      "exchange": "XSHG",
      "provider_symbol": "sh601288",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3912,
        "first": "2010-07-15",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601298",
      "exchange": "XSHG",
      "provider_symbol": "sh601298",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2025-09-08",
      "candidate_member_last": "2026-06-12",
      "candidate_member_records": 182,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1838,
        "first": "2019-01-21",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601318",
      "exchange": "XSHG",
      "provider_symbol": "sh601318",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4674,
        "first": "2007-03-01",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/601318.SS.bars.parquet",
        "bytes": 97435,
        "sourcehash": "0c7aaf36b4e2a5968cc2d31dc8366ae4cbf691c2bfe9220e52bf69ba40f78931",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "601319",
      "exchange": "XSHG",
      "provider_symbol": "sh601319",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1888,
        "first": "2018-11-16",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601328",
      "exchange": "XSHG",
      "provider_symbol": "sh601328",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4676,
        "first": "2007-05-15",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601336",
      "exchange": "XSHG",
      "provider_symbol": "sh601336",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3542,
        "first": "2011-12-16",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601360",
      "exchange": "XSHG",
      "provider_symbol": "sh601360",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3422,
        "first": "2012-01-16",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601377",
      "exchange": "XSHG",
      "provider_symbol": "sh601377",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 6,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3833,
        "first": "2010-10-13",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601390",
      "exchange": "XSHG",
      "provider_symbol": "sh601390",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4458,
        "first": "2007-12-03",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601398",
      "exchange": "XSHG",
      "provider_symbol": "sh601398",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4800,
        "first": "2006-10-27",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601456",
      "exchange": "XSHG",
      "provider_symbol": "sh601456",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2025-12-15",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 129,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1454,
        "first": "2020-07-31",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601555",
      "exchange": "XSHG",
      "provider_symbol": "sh601555",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-01-14",
      "candidate_member_records": 9,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3543,
        "first": "2011-12-12",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601600",
      "exchange": "XSHG",
      "provider_symbol": "sh601600",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4554,
        "first": "2007-04-30",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/601600.SS.bars.parquet",
        "bytes": 71775,
        "sourcehash": "d0b295be559e5b83e268d4d03f51e18bb840c905dcc7ec6c1cf2b2da70fd2901",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "601601",
      "exchange": "XSHG",
      "provider_symbol": "sh601601",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4530,
        "first": "2007-12-25",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601607",
      "exchange": "XSHG",
      "provider_symbol": "sh601607",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 841,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3992,
        "first": "2010-03-09",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601615",
      "exchange": "XSHG",
      "provider_symbol": "sh601615",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-03-20",
      "candidate_member_last": "2024-06-14",
      "candidate_member_records": 300,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1834,
        "first": "2019-01-23",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601618",
      "exchange": "XSHG",
      "provider_symbol": "sh601618",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4033,
        "first": "2009-09-21",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601628",
      "exchange": "XSHG",
      "provider_symbol": "sh601628",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4763,
        "first": "2007-01-09",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601633",
      "exchange": "XSHG",
      "provider_symbol": "sh601633",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3596,
        "first": "2011-09-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601658",
      "exchange": "XSHG",
      "provider_symbol": "sh601658",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1629,
        "first": "2019-12-10",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601668",
      "exchange": "XSHG",
      "provider_symbol": "sh601668",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4143,
        "first": "2009-07-29",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601669",
      "exchange": "XSHG",
      "provider_symbol": "sh601669",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3496,
        "first": "2011-10-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601688",
      "exchange": "XSHG",
      "provider_symbol": "sh601688",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3999,
        "first": "2010-02-26",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/601688.SS.bars.parquet",
        "bytes": 79645,
        "sourcehash": "9665fc7f810888ed5d6e85d5fcd766f60f4d2541cef3f479a62126499280e63a",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "601689",
      "exchange": "XSHG",
      "provider_symbol": "sh601689",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-03-20",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 794,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2774,
        "first": "2015-03-19",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/601689.SS.bars.parquet",
        "bytes": 97914,
        "sourcehash": "d8a3036ab77ebd601dbef2826aca00dfe4d0731ee426579c20731200c95b91f3",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "601696",
      "exchange": "XSHG",
      "provider_symbol": "sh601696",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-06-10",
      "candidate_member_records": 103,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1580,
        "first": "2020-02-26",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601698",
      "exchange": "XSHG",
      "provider_symbol": "sh601698",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1740,
        "first": "2019-06-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601699",
      "exchange": "XSHG",
      "provider_symbol": "sh601699",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-06-12",
      "candidate_member_last": "2025-12-12",
      "candidate_member_records": 609,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4809,
        "first": "2006-09-22",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601727",
      "exchange": "XSHG",
      "provider_symbol": "sh601727",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 20,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4027,
        "first": "2008-12-05",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601728",
      "exchange": "XSHG",
      "provider_symbol": "sh601728",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1076,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1216,
        "first": "2021-08-20",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601766",
      "exchange": "XSHG",
      "provider_symbol": "sh601766",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4281,
        "first": "2008-08-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601788",
      "exchange": "XSHG",
      "provider_symbol": "sh601788",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4114,
        "first": "2009-08-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601799",
      "exchange": "XSHG",
      "provider_symbol": "sh601799",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2025-12-12",
      "candidate_member_records": 956,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3729,
        "first": "2011-02-01",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601800",
      "exchange": "XSHG",
      "provider_symbol": "sh601800",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3515,
        "first": "2012-03-09",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601808",
      "exchange": "XSHG",
      "provider_symbol": "sh601808",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-12",
      "candidate_member_records": 1074,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4584,
        "first": "2007-09-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601816",
      "exchange": "XSHG",
      "provider_symbol": "sh601816",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1603,
        "first": "2020-01-16",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601818",
      "exchange": "XSHG",
      "provider_symbol": "sh601818",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3873,
        "first": "2010-08-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601825",
      "exchange": "XSHG",
      "provider_symbol": "sh601825",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 441,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1217,
        "first": "2021-08-19",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601838",
      "exchange": "XSHG",
      "provider_symbol": "sh601838",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2079,
        "first": "2018-01-31",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601857",
      "exchange": "XSHG",
      "provider_symbol": "sh601857",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4565,
        "first": "2007-11-05",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601865",
      "exchange": "XSHG",
      "provider_symbol": "sh601865",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2025-12-12",
      "candidate_member_records": 947,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1830,
        "first": "2019-02-15",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601868",
      "exchange": "XSHG",
      "provider_symbol": "sh601868",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1076,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1191,
        "first": "2021-09-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601872",
      "exchange": "XSHG",
      "provider_symbol": "sh601872",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 747,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4669,
        "first": "2006-12-01",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601877",
      "exchange": "XSHG",
      "provider_symbol": "sh601877",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3890,
        "first": "2010-01-21",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601878",
      "exchange": "XSHG",
      "provider_symbol": "sh601878",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2230,
        "first": "2017-06-26",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601881",
      "exchange": "XSHG",
      "provider_symbol": "sh601881",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2330,
        "first": "2017-01-23",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601888",
      "exchange": "XSHG",
      "provider_symbol": "sh601888",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4034,
        "first": "2009-10-15",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601898",
      "exchange": "XSHG",
      "provider_symbol": "sh601898",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1076,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4501,
        "first": "2008-02-01",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601899",
      "exchange": "XSHG",
      "provider_symbol": "sh601899",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4414,
        "first": "2008-04-25",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/601899.SS.bars.parquet",
        "bytes": 75225,
        "sourcehash": "d49497e81bb79c2d16db8827913225103df484d37f3dd2066571056240ceaeb0",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "601901",
      "exchange": "XSHG",
      "provider_symbol": "sh601901",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3536,
        "first": "2011-08-10",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601916",
      "exchange": "XSHG",
      "provider_symbol": "sh601916",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 907,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1633,
        "first": "2019-11-26",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601919",
      "exchange": "XSHG",
      "provider_symbol": "sh601919",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4475,
        "first": "2007-06-26",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601933",
      "exchange": "XSHG",
      "provider_symbol": "sh601933",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-06-10",
      "candidate_member_records": 103,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3791,
        "first": "2010-12-15",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601939",
      "exchange": "XSHG",
      "provider_symbol": "sh601939",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4583,
        "first": "2007-09-25",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601966",
      "exchange": "XSHG",
      "provider_symbol": "sh601966",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2023-06-09",
      "candidate_member_records": 338,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2446,
        "first": "2016-07-06",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601985",
      "exchange": "XSHG",
      "provider_symbol": "sh601985",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2727,
        "first": "2015-06-10",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601988",
      "exchange": "XSHG",
      "provider_symbol": "sh601988",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4883,
        "first": "2006-07-05",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601989",
      "exchange": "XSHG",
      "provider_symbol": "sh601989",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2025-09-05",
      "candidate_member_records": 892,
      "missing_close_member_records_reused": 892,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 0,
        "first": null,
        "last": null,
        "format": "column absent"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601990",
      "exchange": "XSHG",
      "provider_symbol": "sh601990",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-06-10",
      "candidate_member_records": 103,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1993,
        "first": "2018-06-13",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601995",
      "exchange": "XSHG",
      "provider_symbol": "sh601995",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 20,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1394,
        "first": "2020-11-02",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "601998",
      "exchange": "XSHG",
      "provider_symbol": "sh601998",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 4678,
        "first": "2007-04-27",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "603019",
      "exchange": "XSHG",
      "provider_symbol": "sh603019",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 10,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2845,
        "first": "2014-11-06",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "603087",
      "exchange": "XSHG",
      "provider_symbol": "sh603087",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2023-03-17",
      "candidate_member_records": 291,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1498,
        "first": "2020-06-29",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "603160",
      "exchange": "XSHG",
      "provider_symbol": "sh603160",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2023-03-17",
      "candidate_member_records": 291,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2389,
        "first": "2016-10-17",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/603160.SS.bars.parquet",
        "bytes": 96528,
        "sourcehash": "bcddb2d5ce1b6206d201665424ecbc83505bc4188dd8fd7ab369618f43239931",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "603185",
      "exchange": "XSHG",
      "provider_symbol": "sh603185",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2023-12-08",
      "candidate_member_records": 366,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1858,
        "first": "2018-12-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "603195",
      "exchange": "XSHG",
      "provider_symbol": "sh603195",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-12",
      "candidate_member_records": 1074,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1594,
        "first": "2020-02-06",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "603233",
      "exchange": "XSHG",
      "provider_symbol": "sh603233",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-06-10",
      "candidate_member_records": 103,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2205,
        "first": "2017-07-31",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "603259",
      "exchange": "XSHG",
      "provider_symbol": "sh603259",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2019,
        "first": "2018-05-08",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/603259.SS.bars.parquet",
        "bytes": 83324,
        "sourcehash": "783e95ec3d55a5a2a077a6edbce55f33899bcf7b528f16fd1a5b75b5ccd454cb",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "603260",
      "exchange": "XSHG",
      "provider_symbol": "sh603260",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1076,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2145,
        "first": "2017-10-30",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "603288",
      "exchange": "XSHG",
      "provider_symbol": "sh603288",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3054,
        "first": "2014-02-11",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/603288.SS.bars.parquet",
        "bytes": 94834,
        "sourcehash": "bfd46c1d01a10e838ea09a47cceecaa5e7a44ebe05d72952f604c90711731484",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "603290",
      "exchange": "XSHG",
      "provider_symbol": "sh603290",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2024-06-14",
      "candidate_member_records": 488,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1596,
        "first": "2020-02-04",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "603296",
      "exchange": "XSHG",
      "provider_symbol": "sh603296",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2024-06-17",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 494,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 741,
        "first": "2023-08-08",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "603338",
      "exchange": "XSHG",
      "provider_symbol": "sh603338",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-06-10",
      "candidate_member_records": 103,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2767,
        "first": "2015-03-25",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "603369",
      "exchange": "XSHG",
      "provider_symbol": "sh603369",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2953,
        "first": "2014-07-03",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "603392",
      "exchange": "XSHG",
      "provider_symbol": "sh603392",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1536,
        "first": "2020-04-29",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "603486",
      "exchange": "XSHG",
      "provider_symbol": "sh603486",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2024-06-14",
      "candidate_member_records": 582,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2005,
        "first": "2018-05-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "603501",
      "exchange": "XSHG",
      "provider_symbol": "sh603501",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2094,
        "first": "2017-05-04",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "603517",
      "exchange": "XSHG",
      "provider_symbol": "sh603517",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-06-10",
      "candidate_member_records": 103,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2295,
        "first": "2017-03-17",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "603658",
      "exchange": "XSHG",
      "provider_symbol": "sh603658",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-06-10",
      "candidate_member_records": 103,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2424,
        "first": "2016-09-01",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "603659",
      "exchange": "XSHG",
      "provider_symbol": "sh603659",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2025-06-13",
      "candidate_member_records": 832,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2085,
        "first": "2017-11-03",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "603799",
      "exchange": "XSHG",
      "provider_symbol": "sh603799",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2780,
        "first": "2015-01-29",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/603799.SS.bars.parquet",
        "bytes": 99933,
        "sourcehash": "140be1965b23f84c07f38f861b3c639b64daa099df712a9759b137bf89ea3c0e",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "603806",
      "exchange": "XSHG",
      "provider_symbol": "sh603806",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2025-12-12",
      "candidate_member_records": 956,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2891,
        "first": "2014-09-05",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "603833",
      "exchange": "XSHG",
      "provider_symbol": "sh603833",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2025-12-12",
      "candidate_member_records": 956,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2283,
        "first": "2017-03-28",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "603882",
      "exchange": "XSHG",
      "provider_symbol": "sh603882",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2023-06-09",
      "candidate_member_records": 347,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2176,
        "first": "2017-09-08",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "603893",
      "exchange": "XSHG",
      "provider_symbol": "sh603893",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2025-12-15",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 129,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1593,
        "first": "2020-02-07",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "603899",
      "exchange": "XSHG",
      "provider_symbol": "sh603899",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2024-12-13",
      "candidate_member_records": 714,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2816,
        "first": "2015-01-27",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "603939",
      "exchange": "XSHG",
      "provider_symbol": "sh603939",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2022-06-10",
      "candidate_member_records": 103,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2685,
        "first": "2015-02-17",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "603986",
      "exchange": "XSHG",
      "provider_symbol": "sh603986",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 2228,
        "first": "2016-08-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/603986.SS.bars.parquet",
        "bytes": 91945,
        "sourcehash": "1414dc600dedd4ee4a2d7fe631769ce2a6bf4109a1d9d5deeeca5ce257801701",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "603993",
      "exchange": "XSHG",
      "provider_symbol": "sh603993",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 3353,
        "first": "2012-10-09",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/603993.SS.bars.parquet",
        "bytes": 80466,
        "sourcehash": "67aba2c330efd4b2484e70119e0e5cd02b341729a9b5f790f26cddb606dd64d7",
        "hash_algorithm": "sha256"
      }
    },
    {
      "symbol": "605117",
      "exchange": "XSHG",
      "provider_symbol": "sh605117",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-03-20",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 794,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1300,
        "first": "2021-04-20",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "605499",
      "exchange": "XSHG",
      "provider_symbol": "sh605499",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1076,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1276,
        "first": "2021-05-27",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "688005",
      "exchange": "XSHG",
      "provider_symbol": "sh688005",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2023-12-08",
      "candidate_member_records": 366,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1720,
        "first": "2019-07-22",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "688008",
      "exchange": "XSHG",
      "provider_symbol": "sh688008",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1724,
        "first": "2019-07-22",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "688009",
      "exchange": "XSHG",
      "provider_symbol": "sh688009",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 597,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1724,
        "first": "2019-07-22",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "688012",
      "exchange": "XSHG",
      "provider_symbol": "sh688012",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 9,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1715,
        "first": "2019-07-22",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "688036",
      "exchange": "XSHG",
      "provider_symbol": "sh688036",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1675,
        "first": "2019-09-30",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "688041",
      "exchange": "XSHG",
      "provider_symbol": "sh688041",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-12-11",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 616,
      "missing_close_member_records_reused": 10,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 970,
        "first": "2022-08-12",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "688047",
      "exchange": "XSHG",
      "provider_symbol": "sh688047",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2025-06-16",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 253,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1015,
        "first": "2022-06-24",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "688065",
      "exchange": "XSHG",
      "provider_symbol": "sh688065",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-06-13",
      "candidate_member_last": "2024-06-14",
      "candidate_member_records": 488,
      "missing_close_member_records_reused": 4,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1462,
        "first": "2020-08-12",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "688072",
      "exchange": "XSHG",
      "provider_symbol": "sh688072",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2026-06-15",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 11,
      "missing_close_member_records_reused": 2,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1048,
        "first": "2022-04-20",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "688082",
      "exchange": "XSHG",
      "provider_symbol": "sh688082",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2024-06-17",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 494,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1159,
        "first": "2021-11-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "688111",
      "exchange": "XSHG",
      "provider_symbol": "sh688111",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1645,
        "first": "2019-11-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "688126",
      "exchange": "XSHG",
      "provider_symbol": "sh688126",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 10,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1533,
        "first": "2020-04-20",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "688169",
      "exchange": "XSHG",
      "provider_symbol": "sh688169",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-12",
      "candidate_member_records": 707,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1583,
        "first": "2020-02-21",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "688183",
      "exchange": "XSHG",
      "provider_symbol": "sh688183",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2026-06-15",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 11,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1337,
        "first": "2021-02-25",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "688187",
      "exchange": "XSHG",
      "provider_symbol": "sh688187",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-03-20",
      "candidate_member_last": "2026-06-12",
      "candidate_member_records": 783,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1204,
        "first": "2021-09-07",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "688223",
      "exchange": "XSHG",
      "provider_symbol": "sh688223",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-06-12",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 738,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1111,
        "first": "2022-01-26",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "688256",
      "exchange": "XSHG",
      "provider_symbol": "sh688256",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-12-11",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 616,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1483,
        "first": "2020-07-20",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "688271",
      "exchange": "XSHG",
      "provider_symbol": "sh688271",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-12-11",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 616,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 974,
        "first": "2022-08-22",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "688303",
      "exchange": "XSHG",
      "provider_symbol": "sh688303",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2023-03-20",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 794,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1237,
        "first": "2021-07-22",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "688363",
      "exchange": "XSHG",
      "provider_symbol": "sh688363",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2024-12-13",
      "candidate_member_records": 714,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1653,
        "first": "2019-11-06",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "688396",
      "exchange": "XSHG",
      "provider_symbol": "sh688396",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-04",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1085,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1579,
        "first": "2020-02-27",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "688472",
      "exchange": "XSHG",
      "provider_symbol": "sh688472",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2024-12-16",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 371,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 781,
        "first": "2023-06-09",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "688506",
      "exchange": "XSHG",
      "provider_symbol": "sh688506",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2024-12-16",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 371,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 882,
        "first": "2023-01-06",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "688521",
      "exchange": "XSHG",
      "provider_symbol": "sh688521",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2026-06-15",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 11,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1452,
        "first": "2020-08-18",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "688561",
      "exchange": "XSHG",
      "provider_symbol": "sh688561",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2024-06-14",
      "candidate_member_records": 582,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1481,
        "first": "2020-07-22",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "688599",
      "exchange": "XSHG",
      "provider_symbol": "sh688599",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2025-12-12",
      "candidate_member_records": 947,
      "missing_close_member_records_reused": 0,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1509,
        "first": "2020-06-10",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    },
    {
      "symbol": "688981",
      "exchange": "XSHG",
      "provider_symbol": "sh688981",
      "security_id": null,
      "selection_basis": "candidate CSI300 member table; official history not qualified",
      "candidate_member_first": "2022-01-17",
      "candidate_member_last": "2026-06-30",
      "candidate_member_records": 1076,
      "missing_close_member_records_reused": 6,
      "membership_sourcehash": "a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30",
      "nominal_raw_quote_file": null,
      "historical_actions": null,
      "suspension_delisting_cause": null,
      "stored_adjusted_close_coverage": {
        "positive_rows": 1479,
        "first": "2020-07-16",
        "last": "2026-08-27",
        "format": "close only; provider adjustment lineage not established"
      },
      "legacy_ohlcv_file": null
    }
  ],
  "candidate_changes_12_not_certified_exhaustive": [
    {
      "candidate_effective_date": "2022-01-17",
      "added_codes": [
        "000301",
        "002064",
        "002459",
        "002466",
        "002568",
        "002709",
        "002791",
        "300316",
        "300750",
        "300759",
        "300760",
        "300782",
        "300866",
        "300888",
        "300896",
        "300999",
        "600905",
        "601728",
        "601865",
        "601868",
        "601898",
        "601966",
        "603260",
        "603486",
        "605499",
        "688561",
        "688599",
        "688981"
      ],
      "removed_codes": [
        "000656",
        "000728",
        "000860",
        "002153",
        "002384",
        "002456",
        "002463",
        "002508",
        "002558",
        "002673",
        "002739",
        "002773",
        "002939",
        "002945",
        "300136",
        "600118",
        "600233",
        "600299",
        "600340",
        "600482",
        "600521",
        "600522",
        "600703",
        "600705",
        "601077",
        "601555",
        "601727",
        "601872"
      ],
      "official_effective_chain_verified": false
    },
    {
      "candidate_effective_date": "2022-06-13",
      "added_codes": [
        "000408",
        "000792",
        "000877",
        "001289",
        "002074",
        "002648",
        "002920",
        "300207",
        "300223",
        "300454",
        "300496",
        "300661",
        "300751",
        "300763",
        "300919",
        "300957",
        "300979",
        "600089",
        "600188",
        "600219",
        "600460",
        "600941",
        "601117",
        "601825",
        "603185",
        "603290",
        "688005",
        "688065"
      ],
      "removed_codes": [
        "000783",
        "002024",
        "002044",
        "002157",
        "002624",
        "300144",
        "300558",
        "300676",
        "300677",
        "300888",
        "600079",
        "600109",
        "600143",
        "600848",
        "600872",
        "601108",
        "601162",
        "601231",
        "601607",
        "601696",
        "601933",
        "601990",
        "603233",
        "603338",
        "603517",
        "603658",
        "603939",
        "688009"
      ],
      "official_effective_chain_verified": false
    },
    {
      "candidate_effective_date": "2023-03-20",
      "added_codes": [
        "000723",
        "000733",
        "002180",
        "002756",
        "300769",
        "600039",
        "600233",
        "600674",
        "600803",
        "600884",
        "601615",
        "601689",
        "605117",
        "688187",
        "688303"
      ],
      "removed_codes": [
        "000066",
        "000703",
        "002568",
        "002607",
        "002791",
        "300003",
        "300866",
        "600161",
        "600352",
        "600489",
        "600655",
        "601825",
        "601916",
        "603087",
        "603160"
      ],
      "official_effective_chain_verified": false
    },
    {
      "candidate_effective_date": "2023-06-12",
      "added_codes": [
        "000617",
        "000983",
        "600732",
        "600754",
        "600875",
        "601607",
        "601699",
        "601872",
        "688223"
      ],
      "removed_codes": [
        "002008",
        "002032",
        "002600",
        "002602",
        "300529",
        "300595",
        "601966",
        "603882",
        "688169"
      ],
      "official_effective_chain_verified": false
    },
    {
      "candidate_effective_date": "2023-12-11",
      "added_codes": [
        "000999",
        "002603",
        "300308",
        "301269",
        "600023",
        "600372",
        "600489",
        "600515",
        "600938",
        "601059",
        "601916",
        "688041",
        "688256",
        "688271"
      ],
      "removed_codes": [
        "000723",
        "002064",
        "002120",
        "002414",
        "002756",
        "300207",
        "300601",
        "300769",
        "600383",
        "600763",
        "600884",
        "601216",
        "603185",
        "688005"
      ],
      "official_effective_chain_verified": false
    },
    {
      "candidate_effective_date": "2024-06-17",
      "added_codes": [
        "000807",
        "001965",
        "300418",
        "300442",
        "300832",
        "600026",
        "600027",
        "600161",
        "600415",
        "603296",
        "688009",
        "688082"
      ],
      "removed_codes": [
        "000069",
        "000877",
        "002202",
        "300763",
        "600606",
        "600754",
        "601155",
        "601615",
        "603290",
        "603486",
        "688065",
        "688561"
      ],
      "official_effective_chain_verified": false
    },
    {
      "candidate_effective_date": "2024-12-16",
      "added_codes": [
        "000630",
        "000975",
        "002028",
        "002422",
        "002463",
        "300394",
        "300502",
        "600066",
        "600160",
        "600377",
        "600482",
        "601127",
        "601136",
        "688169",
        "688472",
        "688506"
      ],
      "removed_codes": [
        "000733",
        "002410",
        "002603",
        "002821",
        "002841",
        "300142",
        "300223",
        "300454",
        "300496",
        "300751",
        "300919",
        "300957",
        "600132",
        "600732",
        "603899",
        "688363"
      ],
      "official_effective_chain_verified": false
    },
    {
      "candidate_effective_date": "2025-03-10",
      "added_codes": [
        "601058"
      ],
      "removed_codes": [
        "600837"
      ],
      "official_effective_chain_verified": false
    },
    {
      "candidate_effective_date": "2025-06-16",
      "added_codes": [
        "001391",
        "002600",
        "301236",
        "302132",
        "601077",
        "601825",
        "688047"
      ],
      "removed_codes": [
        "002007",
        "002271",
        "002555",
        "002812",
        "300450",
        "600745",
        "603659"
      ],
      "official_effective_chain_verified": false
    },
    {
      "candidate_effective_date": "2025-09-08",
      "added_codes": [
        "601298"
      ],
      "removed_codes": [
        "601989"
      ],
      "official_effective_chain_verified": false
    },
    {
      "candidate_effective_date": "2025-12-15",
      "added_codes": [
        "002384",
        "002625",
        "300251",
        "300476",
        "300803",
        "300866",
        "600522",
        "600930",
        "601018",
        "601456",
        "603893"
      ],
      "removed_codes": [
        "000800",
        "001289",
        "002129",
        "002180",
        "600332",
        "601699",
        "601799",
        "601865",
        "603806",
        "603833",
        "688599"
      ],
      "official_effective_chain_verified": false
    },
    {
      "candidate_effective_date": "2026-06-15",
      "added_codes": [
        "000657",
        "000988",
        "001280",
        "002202",
        "002353",
        "002532",
        "002558",
        "002602",
        "002837",
        "300450",
        "301165",
        "301308",
        "600118",
        "600221",
        "600549",
        "601727",
        "688072",
        "688183",
        "688521"
      ],
      "removed_codes": [
        "000661",
        "000786",
        "000876",
        "000983",
        "002252",
        "002459",
        "002601",
        "300347",
        "300759",
        "300782",
        "300979",
        "600161",
        "600377",
        "601236",
        "601298",
        "601808",
        "603195",
        "688169",
        "688187"
      ],
      "official_effective_chain_verified": false
    }
  ],
  "missing_close_records": [
    {
      "symbol_code_only": "000408",
      "member_first": "2022-06-13",
      "member_last": "2026-06-30",
      "candidate_member_dates": 982,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 5,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2025-01-10",
          "last": "2025-01-16",
          "member_dates": 5
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "000425",
      "member_first": "2022-01-04",
      "member_last": "2026-06-30",
      "candidate_member_dates": 1085,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 13,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2022-05-27",
          "last": "2022-05-27",
          "member_dates": 1
        },
        {
          "first": "2022-08-01",
          "last": "2022-08-16",
          "member_dates": 12
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "001979",
      "member_first": "2022-01-04",
      "member_last": "2026-06-30",
      "candidate_member_dates": 1085,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 10,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2022-12-05",
          "last": "2022-12-16",
          "member_dates": 10
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "002024",
      "member_first": "2022-01-04",
      "member_last": "2022-06-10",
      "candidate_member_dates": 103,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 1,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2022-05-05",
          "last": "2022-05-05",
          "member_dates": 1
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "002049",
      "member_first": "2022-01-04",
      "member_last": "2026-06-30",
      "candidate_member_dates": 1085,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 10,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2025-12-30",
          "last": "2026-01-14",
          "member_dates": 10
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "002252",
      "member_first": "2022-01-04",
      "member_last": "2026-06-12",
      "candidate_member_dates": 1074,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 10,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2024-12-23",
          "last": "2025-01-06",
          "member_dates": 10
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "002736",
      "member_first": "2022-01-04",
      "member_last": "2026-06-30",
      "candidate_member_dates": 1085,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 10,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2024-08-22",
          "last": "2024-09-04",
          "member_dates": 10
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "300442",
      "member_first": "2024-06-17",
      "member_last": "2026-06-30",
      "candidate_member_dates": 494,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 6,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2026-02-06",
          "last": "2026-02-13",
          "member_dates": 6
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "301269",
      "member_first": "2023-12-11",
      "member_last": "2026-06-30",
      "candidate_member_dates": 616,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 10,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2025-03-17",
          "last": "2025-03-28",
          "member_dates": 10
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "600009",
      "member_first": "2022-01-04",
      "member_last": "2026-06-30",
      "candidate_member_dates": 1085,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 1,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2022-04-08",
          "last": "2022-04-08",
          "member_dates": 1
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "600027",
      "member_first": "2024-06-17",
      "member_last": "2026-06-30",
      "candidate_member_dates": 494,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 10,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2024-07-19",
          "last": "2024-08-01",
          "member_dates": 10
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "600030",
      "member_first": "2022-01-04",
      "member_last": "2026-06-30",
      "candidate_member_dates": 1085,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 6,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2022-01-19",
          "last": "2022-01-26",
          "member_dates": 6
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "600150",
      "member_first": "2022-01-04",
      "member_last": "2026-06-30",
      "candidate_member_dates": 1085,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 14,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2024-09-03",
          "last": "2024-09-18",
          "member_dates": 10
        },
        {
          "first": "2025-08-13",
          "last": "2025-08-18",
          "member_dates": 4
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "600438",
      "member_first": "2022-01-04",
      "member_last": "2026-06-30",
      "candidate_member_dates": 1085,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 10,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2026-02-25",
          "last": "2026-03-10",
          "member_dates": 10
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "600584",
      "member_first": "2022-01-04",
      "member_last": "2026-06-30",
      "candidate_member_dates": 1085,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 5,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2024-03-20",
          "last": "2024-03-26",
          "member_dates": 5
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "600705",
      "member_first": "2022-01-04",
      "member_last": "2022-01-14",
      "candidate_member_dates": 9,
      "close_column_present": false,
      "nonpositive_or_missing_close_member_dates": 9,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2022-01-04",
          "last": "2022-01-14",
          "member_dates": 9
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "600803",
      "member_first": "2023-03-20",
      "member_last": "2026-06-30",
      "candidate_member_dates": 794,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 6,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2025-03-19",
          "last": "2025-03-26",
          "member_dates": 6
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "600837",
      "member_first": "2022-01-04",
      "member_last": "2025-03-07",
      "candidate_member_dates": 767,
      "close_column_present": false,
      "nonpositive_or_missing_close_member_dates": 767,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2022-01-04",
          "last": "2025-03-07",
          "member_dates": 767
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "600900",
      "member_first": "2022-01-04",
      "member_last": "2026-06-30",
      "candidate_member_dates": 1085,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 1,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2022-10-26",
          "last": "2022-10-26",
          "member_dates": 1
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "600958",
      "member_first": "2022-01-04",
      "member_last": "2026-06-30",
      "candidate_member_dates": 1085,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 16,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2022-04-21",
          "last": "2022-04-28",
          "member_dates": 6
        },
        {
          "first": "2026-04-20",
          "last": "2026-05-06",
          "member_dates": 10
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "601059",
      "member_first": "2023-12-11",
      "member_last": "2026-06-30",
      "candidate_member_dates": 616,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 20,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2025-11-20",
          "last": "2025-12-17",
          "member_dates": 20
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "601088",
      "member_first": "2022-01-04",
      "member_last": "2026-06-30",
      "candidate_member_dates": 1085,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 10,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2025-08-04",
          "last": "2025-08-15",
          "member_dates": 10
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "601108",
      "member_first": "2022-01-04",
      "member_last": "2022-06-10",
      "candidate_member_dates": 103,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 6,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2022-03-31",
          "last": "2022-04-11",
          "member_dates": 6
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "601211",
      "member_first": "2022-01-04",
      "member_last": "2026-06-30",
      "candidate_member_dates": 1085,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 19,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2024-09-06",
          "last": "2024-10-09",
          "member_dates": 17
        },
        {
          "first": "2025-02-06",
          "last": "2025-02-07",
          "member_dates": 2
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "601377",
      "member_first": "2022-01-04",
      "member_last": "2026-06-30",
      "candidate_member_dates": 1085,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 6,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2022-08-17",
          "last": "2022-08-24",
          "member_dates": 6
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "601989",
      "member_first": "2022-01-04",
      "member_last": "2025-09-05",
      "candidate_member_dates": 892,
      "close_column_present": false,
      "nonpositive_or_missing_close_member_dates": 892,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2022-01-04",
          "last": "2025-09-05",
          "member_dates": 892
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "601995",
      "member_first": "2022-01-04",
      "member_last": "2026-06-30",
      "candidate_member_dates": 1085,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 20,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2025-11-20",
          "last": "2025-12-17",
          "member_dates": 20
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "603019",
      "member_first": "2022-01-04",
      "member_last": "2026-06-30",
      "candidate_member_dates": 1085,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 10,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2025-05-26",
          "last": "2025-06-09",
          "member_dates": 10
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "688012",
      "member_first": "2022-01-04",
      "member_last": "2026-06-30",
      "candidate_member_dates": 1085,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 9,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2025-12-19",
          "last": "2025-12-31",
          "member_dates": 9
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "688041",
      "member_first": "2023-12-11",
      "member_last": "2026-06-30",
      "candidate_member_dates": 616,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 10,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2025-05-26",
          "last": "2025-06-09",
          "member_dates": 10
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "688065",
      "member_first": "2022-06-13",
      "member_last": "2024-06-14",
      "candidate_member_dates": 488,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 4,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2023-06-16",
          "last": "2023-06-21",
          "member_dates": 4
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "688072",
      "member_first": "2026-06-15",
      "member_last": "2026-06-30",
      "candidate_member_dates": 11,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 2,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2026-06-29",
          "last": "2026-06-30",
          "member_dates": 2
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "688126",
      "member_first": "2022-01-04",
      "member_last": "2026-06-30",
      "candidate_member_dates": 1085,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 10,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2025-02-24",
          "last": "2025-03-07",
          "member_dates": 10
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    },
    {
      "symbol_code_only": "688981",
      "member_first": "2022-01-17",
      "member_last": "2026-06-30",
      "candidate_member_dates": 1076,
      "close_column_present": true,
      "nonpositive_or_missing_close_member_dates": 6,
      "missing_spans_on_formal_calendar": [
        {
          "first": "2025-09-01",
          "last": "2025-09-08",
          "member_dates": 6
        }
      ],
      "identity_verified": false,
      "absence_kind": "unknown: suspension, listing, delisting, action or source gap not distinguished"
    }
  ],
  "local_stock_files_82": [
    {
      "asset": "000568.SZ",
      "rows": 2392,
      "first": "2016-10-26",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/000568.SZ.bars.parquet",
        "bytes": 96333,
        "sourcehash": "14d056520560e336c2e2143e0b46ba516a96fa5802bbb719dc88cc803f277d46",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/000568.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "579a8c172b23bc1c6eeec04ea0c207a2a75c6a35fae9922a7664a298dc7c9299",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "000596.SZ",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/000596.SZ.bars.parquet",
        "bytes": 94540,
        "sourcehash": "c697303524bf2399ba2242efd77e80eecb791c42ba38fbc3e86e8ae95f36cf3b",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/000596.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "404bf21616f83e476d7f1192b4c36cce03c6b999a224e24343f3b898d7d8ddfb",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "000625.SZ",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/000625.SZ.bars.parquet",
        "bytes": 88905,
        "sourcehash": "cbd0339b2dbfa669d85ce61195f4c8ff89b04d60c2740021aed8af54fe262f91",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/000625.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "c690cf5c5adbd3e9eb6fdf23df9ea1b92d74fca58b083d80f7a59faf009f78e8",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "000661.SZ",
      "rows": 2424,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/000661.SZ.bars.parquet",
        "bytes": 98085,
        "sourcehash": "fc550f6050b036e64f98001c7eb17cd06ad370332129f6f83d19a395e16762f7",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/000661.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "06bd0cc136733974a0dd08a84f00e754f54f840db0b5de023a143ffd5602a9dd",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "000725.SZ",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/000725.SZ.bars.parquet",
        "bytes": 66621,
        "sourcehash": "35237aa972182c3538ce1e491657f95e9ff2b5a668e57a2aefb4755ade8e04cb",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/000725.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "923b6940014ea9ef5f8c667d5dbbd19aaac9db82f5cd59d4f7ad268ba58c6fdb",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "000768.SZ",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/000768.SZ.bars.parquet",
        "bytes": 82552,
        "sourcehash": "754652436907617b008c0aa3c2c9f7e2d97b68e9f9d373f2a4066ead9daae489",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/000768.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "6ec0a61a291c189aed1756b47a6cc7436f1a4e9fa34ceb73de51c5bb3b4c4522",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "000831.SZ",
      "rows": 2432,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/000831.SZ.bars.parquet",
        "bytes": 84352,
        "sourcehash": "035b1928771bd29440b8eeb6769b2fe7f6fa1fc1996521484dde86a369683eeb",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/000831.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "2cbb3482b9d83c0a8600d72854ebb7620a2157fff996e7df1b088aa0f6287075",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "000858.SZ",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/000858.SZ.bars.parquet",
        "bytes": 99108,
        "sourcehash": "0d2c587860fe6637366a08bf5e9fd2016f5e9c9cc1088e1f936ad69dbf24d597",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/000858.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "3ac028655526b1d778b88e152f6af7d45f94a55d5575682579d49c16808ccec1",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "000938.SZ",
      "rows": 2398,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/000938.SZ.bars.parquet",
        "bytes": 88851,
        "sourcehash": "0ded3d2b8aa0dc72015dc4c63c81c473fa84d043b366ce86bb6cf4d35a649ccf",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/000938.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "4701f9447b2e4adebf2b05033f1a438d958e2a2bb59fe9cc3e13e3143721a8b6",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "002008.SZ",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002008.SZ.bars.parquet",
        "bytes": 96388,
        "sourcehash": "68571ad057f2dd59d19604e5c60890447677e6f5ace5787f73c491ef44d23e1b",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002008.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "2022ec4e1f26ca73a021fa8ffa23979b4632b9cd0386c4f52af118e95a6c2e96",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "002049.SZ",
      "rows": 2307,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002049.SZ.bars.parquet",
        "bytes": 94216,
        "sourcehash": "4033b6f49366f1e5b395ee2fc43b0de4c928d91857d2293c205725c67a460287",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002049.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "3b96ec855ad1227aa5c6ff28677bea3a6ed4d1129e4908dd4ee531111bee9a97",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 10,
      "weekly_ends_with_bar": 226,
      "monthly_ends_with_bar": 53,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "002050.SZ",
      "rows": 2395,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002050.SZ.bars.parquet",
        "bytes": 91246,
        "sourcehash": "bd989c571826d44536b4f19cd8d43f879516396a0dfb81df4c9660b959af0bd4",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002050.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "fd4a61f4fad22c8d516684366704ffb3ec51187326f723e85fefc7f09fa5c5ff",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "002179.SZ",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002179.SZ.bars.parquet",
        "bytes": 92694,
        "sourcehash": "b961ba3cc08da29a01a66bdd9b72c5dd3414e16c145094400f8acad1e8f426e7",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002179.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "f842b41409541010af1310e21f70c6a354b3d39d2eb0d673a276702feea5329c",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "002185.SZ",
      "rows": 2417,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002185.SZ.bars.parquet",
        "bytes": 86048,
        "sourcehash": "23bc689ef39e6c252a09bada74132845c7a14cdb9a4542e11b8144357d48f3bc",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002185.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "b852e87f8bb7dd57db0ff13adec0c3701553e35bd9fc92c990c7ef7a6bfec3e3",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 10,
      "weekly_ends_with_bar": 225,
      "monthly_ends_with_bar": 53,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "002230.SZ",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002230.SZ.bars.parquet",
        "bytes": 92692,
        "sourcehash": "1c47a09bfd53be59763bdb06e3e61f470e966040df0b23ec6a5d317a9f5d32e8",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002230.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "4546bec2755584656f53a68d9d4f45f06672c8d659cca4c43be12d886adfb738",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "002241.SZ",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002241.SZ.bars.parquet",
        "bytes": 95221,
        "sourcehash": "721e0aaec281d9ecce9217d65e7f481469f11cb8ffc5a50f3b9e81cd726322f4",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002241.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "1d32b337eecfaab0654fbeced4d5510818b90b127cd9d859c41948da98d823d0",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "002281.SZ",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002281.SZ.bars.parquet",
        "bytes": 86358,
        "sourcehash": "118cb940578ac1e6aa8831dd60e72f6356dd21c77069552b7028fc17c9839f56",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002281.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "9ae370006e9de326ca7079091a0743044aadef77aa54a2aa7f017b1606ac952e",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "002304.SZ",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002304.SZ.bars.parquet",
        "bytes": 97511,
        "sourcehash": "fa3c470de3d6361fd3e357be98f5139d5aba130c091d70dfec51d5c56512a9b9",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002304.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "fda2768ff1973b8481cfe11718e0d32fc5e08f41c696f4962c21095fbd06d787",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "002326.SZ",
      "rows": 2423,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002326.SZ.bars.parquet",
        "bytes": 84154,
        "sourcehash": "9b73aea025c95d389db176cc4d9d97f3e71cdce90278c54ffe5a4a50b0023346",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002326.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "0c7bce819c21cbfbffce1401928e7fc711a0b5c1118410c027888223c8742c1b",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 5,
      "weekly_ends_with_bar": 227,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "002371.SZ",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002371.SZ.bars.parquet",
        "bytes": 101948,
        "sourcehash": "469f8a9b1828c4cbfed831711e71d1aa17b1060deac24bfa2baec0a79a20921c",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002371.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "934556decc65654e29e1b6f1d67424af399ddbfb1e654a1a59c88cf645270dbf",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "002384.SZ",
      "rows": 2363,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002384.SZ.bars.parquet",
        "bytes": 90556,
        "sourcehash": "31adc77d4356e1e2b7a9770c3b4d7e974e2aaea0fc47437f9e2cdeff95c4d373",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002384.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "b667a71dd32ca9a01e92b077c8ad3ba4fafd17edb78465a037f47595d0d39dfd",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "002410.SZ",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002410.SZ.bars.parquet",
        "bytes": 95382,
        "sourcehash": "5a8a4cfc015a8c3c080a5b0e269c0038e5e0eafacc50bd7a20dab05f427af7b9",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002410.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "05a15680af6e59e736ff8500e196dcb492d3ff18b5dd12571bbc072b592316fa",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "002415.SZ",
      "rows": 2431,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002415.SZ.bars.parquet",
        "bytes": 86127,
        "sourcehash": "2090c0fd4858e4eaf098dcccb5474785b7a55e4fdbc57c8b424445646c67ee1c",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002415.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "fe0de8829ad676720b32ffc136e02125f657fadaa0da3205e4121f53e9ff1a86",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "002460.SZ",
      "rows": 2432,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002460.SZ.bars.parquet",
        "bytes": 97206,
        "sourcehash": "0cd93525f6376f4e49d979a0b24432a674b352a00ea9769875953de8e5a29ae3",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002460.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "ceb2e53e656768b5f32af499b8edc875e532f8412991dd3c3fc5bee9d533e2af",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "002466.SZ",
      "rows": 2407,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002466.SZ.bars.parquet",
        "bytes": 97982,
        "sourcehash": "c1de57d065df58a70a5e62cb96ec6ac73139a65146915c4bed1c1d7e6aff3fab",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002466.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "fab932a8ebf555def4b327e71430431a46d5992c709c304dc409ddfa30204845",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "002475.SZ",
      "rows": 2432,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002475.SZ.bars.parquet",
        "bytes": 94741,
        "sourcehash": "ea5b78169e1b8a77e9f2a707b30b4d60ef410b513b9fc74b22ce11c0c34abd77",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002475.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "1f124369b51d82502de35f21664aa3c15ac8a54a65e772cf892deec88135b6fa",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "002555.SZ",
      "rows": 2414,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002555.SZ.bars.parquet",
        "bytes": 94011,
        "sourcehash": "046a21adcfc112ede0a055b4f2d0341a2c811593ce2c768f1d094f8103010077",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002555.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "43b32b171b9168a39e3555556e22a0d59a978b71aba7325c1f34419feeead6b3",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "002594.SZ",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002594.SZ.bars.parquet",
        "bytes": 99836,
        "sourcehash": "f9a72b350802671f56d32c410e80d935564f72fe1023f1673a5c242e14d89a5f",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002594.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "d09a77965e422359908ee80bdde66a73735e45f54e79908115c20421a98a9595",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "002747.SZ",
      "rows": 2385,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002747.SZ.bars.parquet",
        "bytes": 88373,
        "sourcehash": "7b844caa5f474a97bb65575bd5e21164ca1df0a167f8a4d64b761bcc69d30074",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002747.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "328f311bf571dd01d82aa89058284a74cad0f3b964ef3cef641a4b62e3e662b5",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "002812.SZ",
      "rows": 2322,
      "first": "2016-09-14",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002812.SZ.bars.parquet",
        "bytes": 95476,
        "sourcehash": "ee30fa1480fdfceed7e6bc52e4b923c3067c6652dfa2d3a70284c632c2feb032",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002812.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "df80fb3f2812dcdbcb810a57e3c7c6dc31c1a1082e58d570592867a878b0c50e",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 10,
      "weekly_ends_with_bar": 226,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "002821.SZ",
      "rows": 2378,
      "first": "2016-11-18",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002821.SZ.bars.parquet",
        "bytes": 98045,
        "sourcehash": "4f0e688db513c0b149a7ad4955aa70e04c5478e64f828a965ab63ef04fbc667d",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/002821.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "0cd783f53666669795fa5ef268c3e733706b56eca61970a28498d0f3a5db4cac",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "300003.SZ",
      "rows": 2426,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300003.SZ.bars.parquet",
        "bytes": 93434,
        "sourcehash": "2fc70a4dc9bf99af77c665ca4ce220e92939627ce91d1ca28a0ed9be1e3ba8d4",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300003.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "97184fcce6b375d692bc6e46b27fb518352d3d2ce43359f50fb24f1ffa5f1f8e",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "300014.SZ",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300014.SZ.bars.parquet",
        "bytes": 98965,
        "sourcehash": "cf4a1a1584df77588d5ac996a28774cff36c3d1e4135794083fff2467d99b73b",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300014.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "878477305d0dcc4af567e14eeff573f6e413c53b1281bf600e5791741837a87a",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "300059.SZ",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300059.SZ.bars.parquet",
        "bytes": 91126,
        "sourcehash": "3833d23a9a43879133213f1029d9f859ebcc11f98f7d773cc2309f0a1c35cc49",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300059.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "5cf1a6176b0be9334d9de7b8ffcbe86cfa468664eede598adde705b29c08a0e6",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "300073.SZ",
      "rows": 2411,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300073.SZ.bars.parquet",
        "bytes": 96158,
        "sourcehash": "71a9b4f6fba6fcec9ce7577edc48db91a4501772320043399227840f7afc91af",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300073.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "375bb15c4d0144bfbd8b41b12c3fa28cd1155e1850df26b340ca9a9cd76477b0",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "300122.SZ",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300122.SZ.bars.parquet",
        "bytes": 95303,
        "sourcehash": "552bb59bc416a1a570076f8e9a9d12913b7a346ca0cb5c918946224f16c638ea",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300122.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "2382e433978fe34dde848aa6e1b51d008274d6367df674763602da9ec2dbca5b",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "300124.SZ",
      "rows": 2422,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300124.SZ.bars.parquet",
        "bytes": 91373,
        "sourcehash": "8159a3a9974da208b5b7b570a40bee2396582597acfbfdb580c438708169b5e3",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300124.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "d4ce9d48294c809765439e5ca4d8ec6bd4d7641a2715c3e8f0c30b93676acbf7",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "300136.SZ",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300136.SZ.bars.parquet",
        "bytes": 88542,
        "sourcehash": "2edff18fc24d395106d02398c96df74c1e10ca01c4d4356e1bbfc257b82b5475",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300136.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "5f94a47280c5c0bd5ae2e616892b04d03cb046cc82d2462ab37bbb791da2cef8",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "300223.SZ",
      "rows": 2267,
      "first": "2016-12-16",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300223.SZ.bars.parquet",
        "bytes": 88040,
        "sourcehash": "b9bdc668c36587becf74bb9318a3027435bc5649a5f711dddcbdfc0bf71da5c8",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300223.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "c2211e1282b62bd69573b8b018d2b0989a4fa3f4bf5218cb7f9d4562850efadf",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "300274.SZ",
      "rows": 2431,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300274.SZ.bars.parquet",
        "bytes": 96774,
        "sourcehash": "989f96f552c1796e84af9029a809bcf218411c6f504f973a094688fc243c57aa",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300274.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "638e757c1a14a13c39de0f239309b369b591354d034ab26cd54bcadd5d3ef835",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "300308.SZ",
      "rows": 2403,
      "first": "2016-09-30",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300308.SZ.bars.parquet",
        "bytes": 100466,
        "sourcehash": "cafd5b644db81518967aaa66b0c4d9f25e01050e7e145390ce2a75203c6b02c1",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300308.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "a80cfd5f3db6f70e788890cde7624d86911160d4467364b8efc528ad2a22a538",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "300347.SZ",
      "rows": 2428,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300347.SZ.bars.parquet",
        "bytes": 99452,
        "sourcehash": "fa7c2d13e96f59a6f3877ca85fc677dec9ff5b5c8c7d7d379746eca1d34887ac",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300347.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "57ff9c948e61cb7b3e7dafb316a04027b21ff8ce85ec973219738ff0390041f6",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "300383.SZ",
      "rows": 2330,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300383.SZ.bars.parquet",
        "bytes": 77268,
        "sourcehash": "e9198fe8b5737704626be5d7ac4d7a8639bb4b983ecb6e2383f4ba5d6abfc6e6",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300383.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "b7def3ff8190cd67d9c720dd4ed0d8d8bf0e3bab2644d4f20930b888ba8b5ec3",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "300394.SZ",
      "rows": 2421,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300394.SZ.bars.parquet",
        "bytes": 97650,
        "sourcehash": "2e7883172bb552e352af810963adf6ea3c4d26058c0890a5180eca3a1c4bc0f0",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300394.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "fb1a3b80157c682b3bd3225dc62e0625e220e15dcb626ff94d66da4a2e911c83",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "300474.SZ",
      "rows": 2426,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300474.SZ.bars.parquet",
        "bytes": 96136,
        "sourcehash": "ab7bb5a2b635632ec32b98ef45dc3b1c140121d496ccd0540235d4d8e4e97156",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300474.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "b95dbec5194b41744191b5fde29d577d5815a202a99b4de291978e4ca311110e",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "300502.SZ",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300502.SZ.bars.parquet",
        "bytes": 100010,
        "sourcehash": "8af4e760f5e4a3efc3f3ceb3e2de79440b3598dae199bed1baa5a038592be4a0",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300502.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "473e749b5bebd109a1d862b43da670c03ced599a144a921b31cce50098fd9360",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "300661.SZ",
      "rows": 2237,
      "first": "2017-06-06",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300661.SZ.bars.parquet",
        "bytes": 92431,
        "sourcehash": "e4f6298c84f6eb0ff5adfde11848d0b054d3c95bc835d37fc2c1a83b0d72474d",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300661.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "5a00717552d66c5afe4e8aae0a4f400ffca2fc3136932f368595f17af4b10be0",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "300750.SZ",
      "rows": 1996,
      "first": "2018-06-13",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300750.SZ.bars.parquet",
        "bytes": 82344,
        "sourcehash": "935ed24bf9f13c739cb291bd42689b5db40c659457e7e0f705996816bebd38e1",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/300750.SZ.bars.meta.json",
        "bytes": 215,
        "sourcehash": "5c3f84128638834d0781d1f1fdedde18e19b926dc59042a0a4619adfaf824249",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "600030.SS",
      "rows": 2416,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600030.SS.bars.parquet",
        "bytes": 85040,
        "sourcehash": "2b83a523852d79541daa29f56cc70fff70fca6df652c7174badb99b1a0b08b99",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600030.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "4aa4de70ece9886848c0a88c2eb7d0b3e0e18d5266eb58626c3d49118b76ef18",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 6,
      "weekly_ends_with_bar": 227,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "600111.SS",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600111.SS.bars.parquet",
        "bytes": 87747,
        "sourcehash": "0dba4a22aa7d33418b09132e7b4a61462465ee87c1b92175347a473e3a8976f6",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600111.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "590d158b2341780e60727efdbd3f32d6a9ea46d43b19ad01f1e55036b305b66b",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "600188.SS",
      "rows": 1379,
      "first": "2017-12-28",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600188.SS.bars.parquet",
        "bytes": 54139,
        "sourcehash": "e32a7edd6a63e6b8a1512f681dbb3344fd03a9aa590c837a417058b1711d5d77",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600188.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "b7915950854e001426fee5d8d2e411a018c6b4f3124a493ef23a9984fd7e7140",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "600196.SS",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600196.SS.bars.parquet",
        "bytes": 87171,
        "sourcehash": "19617da81a2c2956941aeeca4dd29d8bbd362747e06a64d683a5d4b701483952",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600196.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "cfb6bca1fee0fafd06609c88c12042e7de0e5a00297ff37955ed03596402c0ff",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "600276.SS",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600276.SS.bars.parquet",
        "bytes": 97200,
        "sourcehash": "77a288f4b75d5510572378b09826b0361b34bba2c199a62623fe744e0726cb22",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600276.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "6ba0fe6965acd9924ffde2eec2ab73047bb12b7a2b1ed68406d5aed6805330cd",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "600362.SS",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600362.SS.bars.parquet",
        "bytes": 81443,
        "sourcehash": "c7912d320d53d0d4cdd70609199cede6833d06ea254074f0d7cfde4f7c00d1d7",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600362.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "965b5c4fe1f426aaacf3af30477b2a533ac373d0e109463026bf035629e09d42",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "600438.SS",
      "rows": 2401,
      "first": "2016-08-25",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600438.SS.bars.parquet",
        "bytes": 89050,
        "sourcehash": "819e2e8827d06fa936729ba7c3eca7661b7fd54a8ffcaab84037d67ca09f2202",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600438.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "dd990bbf0d5d738257b731f26ec2bc4c757ded2bf7515919c730ca9bff400ae0",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 10,
      "weekly_ends_with_bar": 226,
      "monthly_ends_with_bar": 53,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "600460.SS",
      "rows": 2348,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600460.SS.bars.parquet",
        "bytes": 86194,
        "sourcehash": "a919e6dc3f7f7a75e3a7991e42c81a6d424b2761d0865af9b2404b16b060f7d7",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600460.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "bf4f0ee7011614cc422ac6c8e1416a1ba951d7809acfdc22bfa145678f11b938",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "600519.SS",
      "rows": 2427,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600519.SS.bars.parquet",
        "bytes": 99612,
        "sourcehash": "32179a25ec29302eb2374b05ddf155f7dd8dfc76cd9ea3d82b6f7a9e7e4901f8",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600519.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "5ecf14c5706643cd0497a19d7e6893a6d7a50d183ee2a3fc80d68346af2bf639",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "600584.SS",
      "rows": 2415,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600584.SS.bars.parquet",
        "bytes": 86811,
        "sourcehash": "7882f4d92ba7f8e54f7b478eb1411410232e2c30598c0a36a830e913d39c341e",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600584.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "9e3feffbbf52744e85f9552d35cae72abcec1301c53807fef2853a155854036f",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 5,
      "weekly_ends_with_bar": 227,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "600588.SS",
      "rows": 2431,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600588.SS.bars.parquet",
        "bytes": 90865,
        "sourcehash": "2b9bf3e134e9a466fc891edbf61fcd384d4832c01c16c5d3f01a42f2d5c45e67",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600588.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "b1d412287893c89e5f4c5acc52b59074c16644dac5e3ef11eda08bf999ef8856",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "600600.SS",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600600.SS.bars.parquet",
        "bytes": 88856,
        "sourcehash": "98bee590336d403be9386f52168c53c79394a74685fbcfa1d460d225ae389319",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600600.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "28bb63ca1c69414e0bb5893234b5742a6d20c13669d475f128d243ae59a76e83",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "600660.SS",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600660.SS.bars.parquet",
        "bytes": 85041,
        "sourcehash": "682c8bfcc2bc969a2c1c900107f00d74ec0f3bb594c51e8647cd28a922ccd859",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600660.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "cbd1044b089bfb1c62987819da560a7c2a5c90fb1df852730405e41aa7860790",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "600703.SS",
      "rows": 2432,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600703.SS.bars.parquet",
        "bytes": 86833,
        "sourcehash": "273ce733baea916a973674258795effc8b32a5af8fb9025bd25dc5e19748cce1",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600703.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "69472e045e46271d682ec92fdac66eef38802d1a2a23f7cc3ce4bc609a1588b5",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "600745.SS",
      "rows": 2236,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600745.SS.bars.parquet",
        "bytes": 88248,
        "sourcehash": "8a734642c32bd2cb6dc71e4a69be18189647172ed79ead400c58164e3ae8ca70",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600745.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "85ee1e5ab0512ca93f82fcc15ca5e1e930bea0b52fa7b8c056cba00006d50d3a",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 3,
      "weekly_ends_with_bar": 226,
      "monthly_ends_with_bar": 53,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "600760.SS",
      "rows": 2352,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600760.SS.bars.parquet",
        "bytes": 88284,
        "sourcehash": "0b5de2b215daeba6e32916ca4a7b2ce479d49dc5f2d375db70e703d4e1221d1a",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600760.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "a3c9a51718103a59e0752121d07803011fc953174832617703af69c65aa906ae",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "600809.SS",
      "rows": 2205,
      "first": "2017-06-12",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600809.SS.bars.parquet",
        "bytes": 88679,
        "sourcehash": "b455568cf2d7c98bbbf1a6bd7d8d60a09065658c1a5a99f14d3ab290ea4cc9e7",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600809.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "09555585616b3fe46d62c8b50b5d31898bfdd92886f8e310d251e4c6de75f6d7",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "600850.SS",
      "rows": 2348,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600850.SS.bars.parquet",
        "bytes": 80970,
        "sourcehash": "3df5357431f756c6d6e91d4a759bbba96223cb8587585e6464f10afe10ba5b1f",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600850.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "8c2c337cc289d877f1ba3207059f126cc8070123aa4692bff4ba9a0be19cf748",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 1,
      "weekly_ends_with_bar": 227,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "600893.SS",
      "rows": 2402,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600893.SS.bars.parquet",
        "bytes": 91166,
        "sourcehash": "d443b07bab4e30fe9e7c60226d5c1a7fe4bddaa2bb1e4c22e6baee7136b1c835",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/600893.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "da8c842acf305e7e7b7549612287e12ed1a2ccb3c28d2312b5ef500d45cb8305",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "601012.SS",
      "rows": 2426,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/601012.SS.bars.parquet",
        "bytes": 93376,
        "sourcehash": "9edbb7b858946187ce153d89d3aacc476c061ecd0a55e0eae46149318c18debe",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/601012.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "c169aad8af6c310a390677b7afbb612b0317ad9614a8476ee5ab7d146fa5b2da",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "601127.SS",
      "rows": 2408,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/601127.SS.bars.parquet",
        "bytes": 91699,
        "sourcehash": "82cfe79478928fc033d5cc5f1945a377828a3f3aaa4f871825016b4b870754a6",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/601127.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "48075615f6b9ad175c7beabe223f372434030da7e0ee43695e8c557a9ab4689a",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "601225.SS",
      "rows": 1689,
      "first": "2018-01-09",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/601225.SS.bars.parquet",
        "bytes": 64832,
        "sourcehash": "ed50ceeb3ae92573e188dec0b214584ed41d1fe80cdd61f37bfe139398410a3a",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/601225.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "cbdea0b972f678c69d19126d38b345a62ac356b23379b15df2c3d15ef65a4245",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "601238.SS",
      "rows": 2423,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/601238.SS.bars.parquet",
        "bytes": 74994,
        "sourcehash": "81a9ed0d8327c8f616f1e6e392b596c128ca502000c203a4bf97dac84115be73",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/601238.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "08213c539cae83edb8569f35d56adcc8aa5145b857bb18c2fa3ee3e8a833d946",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "601318.SS",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/601318.SS.bars.parquet",
        "bytes": 97435,
        "sourcehash": "0c7aaf36b4e2a5968cc2d31dc8366ae4cbf691c2bfe9220e52bf69ba40f78931",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/601318.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "3800fe2be4e082f1d5bbc21a98e4a7eeb6e22527e54d6d244cb773516095d5e6",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "601600.SS",
      "rows": 2324,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/601600.SS.bars.parquet",
        "bytes": 71775,
        "sourcehash": "d0b295be559e5b83e268d4d03f51e18bb840c905dcc7ec6c1cf2b2da70fd2901",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/601600.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "f4b74b77466bb601bb61228afb6ce807bda053865aff8b3bcf18edf709fda0bf",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "601688.SS",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/601688.SS.bars.parquet",
        "bytes": 79645,
        "sourcehash": "9665fc7f810888ed5d6e85d5fcd766f60f4d2541cef3f479a62126499280e63a",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/601688.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "faa3cfc2dc81e428441cc29e566684b8dcea2fcce5c82b7acaa0c69353ca863c",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "601689.SS",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/601689.SS.bars.parquet",
        "bytes": 97914,
        "sourcehash": "d8a3036ab77ebd601dbef2826aca00dfe4d0731ee426579c20731200c95b91f3",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/601689.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "657580363134a3f3ed275e56fbbe436a456100b089ee2c1e27213c1790cf24ee",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "601899.SS",
      "rows": 2429,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/601899.SS.bars.parquet",
        "bytes": 75225,
        "sourcehash": "d49497e81bb79c2d16db8827913225103df484d37f3dd2066571056240ceaeb0",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/601899.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "bda1280c68b7d22eb966d166ae24858f5517b50277032623589e812f10831b5d",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "603160.SS",
      "rows": 2392,
      "first": "2016-10-17",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/603160.SS.bars.parquet",
        "bytes": 96528,
        "sourcehash": "bcddb2d5ce1b6206d201665424ecbc83505bc4188dd8fd7ab369618f43239931",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/603160.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "8910a141446c6e7cc9377684fb0aecc9fa0437c0f2f0a3249aeff9752646715a",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 10,
      "weekly_ends_with_bar": 226,
      "monthly_ends_with_bar": 53,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "603259.SS",
      "rows": 2022,
      "first": "2018-05-08",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/603259.SS.bars.parquet",
        "bytes": 83324,
        "sourcehash": "783e95ec3d55a5a2a077a6edbce55f33899bcf7b528f16fd1a5b75b5ccd454cb",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/603259.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "71130244b077cbedea4054b1986f52866f7025da5ff5ced313492f9c576a61ff",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "603288.SS",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/603288.SS.bars.parquet",
        "bytes": 94834,
        "sourcehash": "bfd46c1d01a10e838ea09a47cceecaa5e7a44ebe05d72952f604c90711731484",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/603288.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "fa5a04d9bb714924b8486d814545e305930e9d4f05ca4db7d0dd97e35351dffa",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "603799.SS",
      "rows": 2421,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/603799.SS.bars.parquet",
        "bytes": 99933,
        "sourcehash": "140be1965b23f84c07f38f861b3c639b64daa099df712a9759b137bf89ea3c0e",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/603799.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "2c87bc68cd31f505d42dd2455bf0d1e5f3587c93fa2ff1ce61d706ba5b425c2f",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "603986.SS",
      "rows": 2227,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/603986.SS.bars.parquet",
        "bytes": 91945,
        "sourcehash": "1414dc600dedd4ee4a2d7fe631769ce2a6bf4109a1d9d5deeeca5ce257801701",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/603986.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "186e70af63a50ab8c3c8fbd49ef26f7b14801583a972923b5f321477e6ba75a6",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    },
    {
      "asset": "603993.SS",
      "rows": 2433,
      "first": "2016-08-24",
      "last": "2026-09-01",
      "kind": "ordinary_stock_code_candidate",
      "file": {
        "path": "docs/experiments/raw/exit_three_piece/pool/603993.SS.bars.parquet",
        "bytes": 80466,
        "sourcehash": "67aba2c330efd4b2484e70119e0e5cd02b341729a9b5f790f26cddb606dd64d7",
        "hash_algorithm": "sha256"
      },
      "meta": {
        "path": "docs/experiments/raw/exit_three_piece/pool/603993.SS.bars.meta.json",
        "bytes": 215,
        "sourcehash": "6b99d65fa17a25927c47abb0a12737958f0593486671b7ef013f6657cfb7ad31",
        "hash_algorithm": "sha256"
      },
      "matches_prior_file_and_meta": true,
      "formal_calendar_dates_without_bar": 0,
      "weekly_ends_with_bar": 228,
      "monthly_ends_with_bar": 54,
      "schema_fields": [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "date"
      ]
    }
  ],
  "legacy_summary": {
    "all_files": 127,
    "stock_code_candidates": 82,
    "etf_or_fund": 44,
    "index": 1,
    "stock_overlap_formal": 73,
    "all_hashes_match": true,
    "stock_date_first": "2016-08-24",
    "stock_date_last": "2026-09-01",
    "stock_rows": 194493,
    "stock_without_any_formal_calendar_bar_gap": 72,
    "status": "local convenience sample; not a qualified historical universe"
  },
  "sector_snapshot": {
    "as_of": "2026-09-22 16:47",
    "boards": 496,
    "formal_codes_with_current_board": 428,
    "historical_industry_qualified": false,
    "reason": "one current Eastmoney board snapshot; no effective interval, no classification version history"
  },
  "field_definitions": {
    "date": "exchange-local trade date; not publication or availability time",
    "symbol": "six-digit exchange code; not permanent identity",
    "version": "12-character hash of candidate member code set; not official notice version",
    "close": "cached supplier adjusted close; price scale and future-action contamination unqualified",
    "open_high_low_close": "existing legacy supplier bars; no raw corporate-action lineage",
    "volume": "legacy supplier quantity; unit/adjustment reset not certified for stocks",
    "sourcehash": "exact bytes SHA-256; unchanged bytes permit reuse of prior coverage counts",
    "published_at": "time this exact source version became public; unknown=null",
    "available_at": "time the frozen data route could actually supply it; unknown=null",
    "retrieved_at": "current collection/inspection time, never historical availability",
    "effective_from_until": "membership/industry effective interval, lower inclusive upper exclusive",
    "decision_at": "completed weekly/monthly review time Asia/Shanghai, distinct from execution",
    "feature_asof": "latest input available_at allowed by decision_at; not computed here",
    "label_end": "future result end time; used only after maturity, no labels computed here",
    "gap_reason": "known suspension/listing/action/source omission or unknown; never infer from NaN"
  },
  "required_uncomputed_row_example": {
    "example_only": true,
    "security_id": null,
    "exchange": "XSHG",
    "symbol": "600837",
    "date": "2025-03-07",
    "candidate_member": true,
    "official_member": null,
    "membership_notice_sourcehash": null,
    "published_at": null,
    "available_at": null,
    "nominal_close": null,
    "action_chain_verified": false,
    "gap_reason": "unknown_absent_column",
    "historical_industry": null,
    "feature_definition_ref": null,
    "feature_value": null,
    "feature_qualified": false,
    "label_qualified": false,
    "live_eligible": false
  },
  "first_candidates": {
    "ppo": {
      "package_definition_ref": "research.selection.ema12_26_normalized_spread@0.1.0",
      "package_definition_source": "docs/experiments/weekly-ppo-information-2026-10-05.md",
      "global_registered_ref": null,
      "fields": [
        "close",
        "action/adjustment chain",
        "official calendar",
        "historical universe"
      ],
      "computed": false,
      "meaning": "normalized moving-average spread, trend strength; not a turning-point or buy signal"
    },
    "corrected_top_bottom": {
      "definition_ref": null,
      "status": "must bind corrected author package, do not substitute simple_top3",
      "fields": [
        "high",
        "low",
        "confirmation availability",
        "action scale",
        "official calendar",
        "historical universe"
      ],
      "computed": false
    }
  },
  "external_document_access": [
    {
      "url": "https://www.csindex.com.cn/#/indices/family/detail?indexCode=000300",
      "status": "javascript shell only; no announcement acquired"
    },
    {
      "url": "http://www.baostock.com/mainContent?file=stock_data.md",
      "status": "unavailable via browsing; capability/license not confirmed"
    },
    {
      "url": "https://www.sse.com.cn/disclosure/listedinfo/announcement/",
      "status": "public announcement search page read; no selected historical document acquired"
    },
    {
      "url": "https://www.szse.cn/disclosure/listed/notice/index.html",
      "status": "timeout; no document acquired"
    }
  ],
  "operations": {
    "source_document_reads": 4,
    "market_price_requests": 0,
    "factor_calculations": 0,
    "forward_label_calculations": 0,
    "fits": 0,
    "paid_calls": 0,
    "new_software_installs": 0,
    "local_inspection_runs": 1,
    "software_available_only": {
      "baostock": "0.9.3",
      "akshare": "1.18.49"
    }
  },
  "raw_market_data_uploaded": false,
  "personal_accounts_included": false,
  "use_limits": [
    "not qualified historical CSI300 members",
    "not all A-share",
    "not a no-survivorship-bias result",
    "not real-time available",
    "not tradable net return",
    "old negative studies unchanged"
  ]
}
```
