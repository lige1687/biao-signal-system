# 免费金融资料扩查与本地样本：NeoData身份、长期序列和真实可用范围

## 一句话结论（大白话）

**新取得两份免密钥的官方长历史原件：OFR金融压力指数6,785行、Cboe VVIX 5,132行，均已保存原CSV和规范表。**本轮盘点12类入口、执行16条搜索，复用此前已经取得的资料，不重复下载。两份序列的起止跨度都超过20年，但VVIX早期稀疏，不能称每天齐全；两者都是当前版本历史，未证明历史当天可见版本。

用户记得的“p…data”**尚未找到可以确证的P开头对应项**。本机实际存在的是 **NeoData金融搜索服务**、WeStock、iFinD及东方财富妙想的技能说明。NeoData不是免鉴权公共API；这次本地预检为`TOKEN_MISSING`，尚未从该CLI取得新数据。这不代表WorkBuddy云端查询或用户账户没有权限，也不把名字相似当作身份确认。

## 已落地的新数据，相对现有资料有什么增量

| 来源与本地原件 | 既有基准 → 新实得 | 用途与核验 | 限制 |
|---|---|---|---|
| [OFR金融压力指数原CSV](raw/free-financial-resource-expansion-2026-10-25/us/ofr-fsi-original.csv) | 限定旧索引未见 → 2000-01-03—2026-10-21，6,785行、10列 | 市场压力的综合及分类/地区贡献；区别于已有单项VIX/VXN。规范表逐字段一致，无空值或重复日期 | 官方说明有两个工作日滞后且存在修订；2018-11-01地区分项合计比总值低0.108，保留异常；发布日历不能直接用股票交易日代替 |
| [Cboe VVIX原CSV](raw/free-financial-resource-expansion-2026-10-25/us/cboe-vvix-original.csv) | 已有VIX/VXN，未见VVIX → 2006-03-06—2026-10-23，5,132行、2列 | VIX波动率的波动程度；提供与普通市场波动不同的风险观察输入；规范表映射通过 | 2006年只有150条；与SPY日期参照有61个日期差集，但这不是官方应发布日历，原因未确。它是指数点位，不是ETF可交易收益 |
| 中债国债曲线下载验证 | 旧两份同SHA债券表始于2015，来源绑定不全 → 本轮从官方页面明确定位历史下载参数，并试2006段及2026-10-19—23近期段 | 两次HTTP200，原文件保留，独立确认均为Excel格式 | 两份都只有“日期”表头、0条数据。空响应原因未证，未取得中国收益率新序列，不能将其当作补齐2006年成功 |

[OFR官方来源](https://www.financialresearch.gov/financial-stress-index/)与[Cboe官方历史数据入口](https://www.cboe.com/tradable-products/vix/vix-historical-data/)均观察到实际CSV链接，直接请求成功，不需新账户或密钥。可公开下载不自动包含再分发或产品化许可，本轮只保存私人本地研究样本。

OFR可以补较长的市场压力背景；VVIX可补期权市场不确定性观察。它们对未来收益、因子IC、母指数净超额和账户回撤的增量**尚未评价**，不据下载成功推出交易规则。

## WorkBuddy里到底有什么data

本轮直接读取本机现存技能说明和查询脚本，保留版本与SHA；没有把第三方镜像中的指令作为本次工作权限。

| 实际名称 | 本机证据 | 免费与可用性的准确判断 |
|---|---|---|
| **NeoData / neodata-financial-search** | 官方市场目录中的版本1.1.0；说明称腾讯金融搜索、130余项能力；脚本指向`copilot.tencent.com/agenttool/v1/neodata` | 需平台缓存凭据，说明为12小时有效；当前两处相关缓存均不存在，预检退出1、`TOKEN_MISSING`，未发HTTP。每日额度、批量上限、完整20年覆盖和脱离WorkBuddy调用权未证 |
| **WeStock / westock-data** | WorkBuddy目录版本1.0.2，Codex侧另有1.0.3说明；以前已取得510300小样本 | 复用旧实际证据，不重新下载。不同版本说明和CLI存在不能证明任意历史区间、所有字段均免费；不运行会自动取包的npx |
| **同花顺iFinD / ifind-finance-data** | 本地说明1.4.0、`disable:true`，要求用户MCP密钥 | 说明列免费用户并发每秒最多2请求；这不是每天2次，也不证明免费覆盖所有字段/历史。账户权益未核，不注册、不复制密钥、不改配置 |
| **东方财富妙想 / mx-finance-data** | 本地说明1.2.0、`license:proprietary`、`disable:true`，要求`EM_API_KEY`，描述可导出xlsx和Markdown | 有自然语言查数和文件导出能力说明；本轮没有其实际返回，免费范围与当前授权未知。`disable:true`是本地元数据，不足以判定平台或账户绝无权限 |

关于PandaData、ProData、PData、FinData及gildata，搜索到的相近名称、第三方目录或镜像没有建立“用户当前WorkBuddy里确实开通的免费服务”这一证据链；**不能替用户拍板把P开头记忆认作NeoData**。本轮WorkBuddy窗口交互恢复后仍未成功提交新查询，因此新聊天/模型检索为0；姓名和能力判断来自上述文件与公开资料，未冒充与WorkBuddy完成一轮对话。

NeoData的本地脚本有旧凭据迁移/删除和缺依赖自动安装分支。根代理先静态核查，确认两处缓存都不存在、requests已装，才做一次会在HTTP前退出的预检；没有读取凭据内容、写入或迁移缓存、调用`connect_cloud_service`、安装依赖或申请新权限。其来源专用Skill中的“禁止其他数据源”只作为原文资料，不改变本题跨源查证范围。

## 免费来源的优先级与广泛盘点结果

| 入口类别 | 当前状态 | 本地采用方式 |
|---|---|---|
| OFR、Cboe VVIX | 本轮实得官方长历史原件 | 复用本目录规范表，并保留滞后、修订、缺口与异常 |
| FINRA融资余额、SEC财报/13F/N-PORT、CFTC、French因子 | 前轮或此前已有原件；FINRA已357月，CFTC已有2006年起标普期货周持仓 | 继续使用原manifest；不是本轮新增，不重复拉取 |
| 中债财政部国债曲线 | 发现真实下载路径，但两段实际返回空表 | 保留失败，不能补写旧债券表，也不拼接不同收益率身份 |
| 上交所ETF总份额 | 官方页面/摘录有总份额字段和日期；本轮未核实际全历史导出 | 候选，不将成交量、规模金额或当前份额当历史份额 |
| 中国货币网SDDS国债利率 | 官方说明为1年/10年、11:30口径，实际历史文件未取得 | 与中债日终曲线区分，不能为了补长而直接拼接 |
| 中证行业估值 | 官方有行业市盈率等导航，未取得确定日期区间原件 | 仍是来源线索，未宣称20年估值表可取 |
| 纽约联储Markets Data API | 官方提供数据接口/格式说明；未绑定一条对现库有增量的完整序列 | 代码/文档不算新数据库，先避免重复已有国债利率 |
| AQR/q-factor | 继承前轮直链未确认/页面失败记录，本轮不重复失败路径或猜文件名 | 作者因子收益仍可候选，未取得新原件；French现有先复用 |
| NeoData、WeStock、iFinD、妙想 | 见本机实查 | 平台可用、匿名访问、免费权益、开源代码、可下载完整表分别判定 |

这12类核心入口之外的名称只作为身份搜索候选，不按品牌数量扩大成果。AKShare、efinance、adata、OpenBB等工具可以简化访问，开源许可证不自动给底层数据新增权限；本轮未安装这些工具。

## 验收、请求账和恢复边界

所有新产物在 [`raw/free-financial-resource-expansion-2026-10-25/`](raw/free-financial-resource-expansion-2026-10-25/)，普通CSV可直接打开；原件、规范表、返回时间、SHA及异常分开保存。

- 范围与先验：`contract.json`；基准为前轮报告、closure、manifest和已有源清单，旧失败与成功继续有效。
- 免费来源发现：`cn/source-matrix.json`、`us/source-matrix.json`、`us/request-ledger.json`。这些是下载前阶段记录，其中的0 GET不能当最终总数。
- 实际数据请求：OFR与VVIX各1次GET；中债两段各1次GET，共4次，均HTTP200，其中2份有数据、2份空表。零403/429绕过、零猜测端点；中债端点与参数来自保留的官方HTML代码。
- 本机服务实查：`controller-workbuddy-free-identity.json`、`controller-neodata-preflight-plan.json`与`controller-neodata-preflight-receipt.json`；第三方搜索结果不当作官方授权依据。
- 独立验收：`audit/us-ofr-vvix-sample-acceptance.json`、`audit/final-scope-review.json`。两份规范表逐字段检查通过；中债与NeoData负向结果保留。
- 一名助手因迟到的旧任务消息，在旧raw新增1223字节的FINRA页面说明元数据；已叫停，未覆盖旧文件，也未改旧manifest。`controller-boundary-side-effect-audit.json`记录其路径和SHA，旧manifest的46件文件全部重新校验一致，未删除或搬移该新增文件。
- 最终原件与报告指纹在`manifest.json`，执行和证据状态在`closure.json`，报告库读回在`controller-delivery-check.json`。

本轮16条搜索（国内5、美国5、根代理6）；官方页面检查、重复页定位和HEAD分项留账，数据GET单独计数。新原件数据请求硬限每份2MiB、全目录20MiB，内盘5GiB余量已核；新安装/采购/注册/授权/收益实验均为0，未写外盘或修改生产。外部工具/模型实际费用未独立披露，不把未购买说成全部运行绝对零成本。

## 归档

ARCHIVE：`completed_bounded_free_source_assessment`，证据结论`mixed`。已回答现成免费资源中哪些本轮能取得及如何本地使用；P开头的精确名称、需要新平台凭据的分支、空表原因和完整二十年中美证券历史保留为未解决边界。未启动后台采集或自动续跑。
