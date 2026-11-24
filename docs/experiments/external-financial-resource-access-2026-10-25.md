# 外部金融资料与连接能力实查：WorkBuddy、TRAE、现有连接器

## 一句话结论（大白话）

**确有可利用的增量，已经取得六份非重复原始样本/接口返回，并保存规范表。最实用的是现有长桥接口能实际返回一致预期、期权统计及国内公告；TRAE 官方还有 iFinD、通达信金融插件入口，但本机连接状态和免费数据范围尚未核实。**WorkBuddy 当前会话主要提供搜索摘要与来源线索，不能把其中的后端名称当成已接通的独立数据库。

本轮完成有边界的来源能力与小样本核查，没有运行新因子收益实验。**二十年中美全部历史成员、退市证券、首发财务/预测版本仍未齐**；下面的资料不解除这些准入限制。原件取得、字段解析通过、适用于历史决策日研究是三种不同状态。

## 实际取得什么，相对已有资料增加什么

查重基准是旧来源清单及对应外盘原件，不重新下载既有 SEC 公司财报、CFTC 标普期货持仓、N-PORT 镜像和 French 因子收益。限定清单未见不代表扫描了所有磁盘。

| 新增来源／本地原件 | 原有基准 → 本轮实得 | 有什么用 | 关键限制与判断 |
|---|---|---|---|
| 长桥 AAPL 一致预期 JSON、CSV | 未见该原始返回 → 11 个财季、66 项指标，Q4 2024—Q2 2027；48 项已发布、18 项未发布预测 | 营收、利润、每股收益的现时预期与实际值，适合建立后续观察快照 | USD；总金额与每股数值不能混加。不是历史某天看到的预测版本；2 个调整后 EPS 差额与展示值相减差 0.0001，保留原值，原因未证 |
| 长桥 IWM 期权日统计 JSON、CSV | WorkBuddy 没有原始链 → 2026-09-28—10-23 共 20 个唯一日期 | 买卖权成交量、未平仓量及两种比率的短期观察 | 两类 put+call=total 共40项核对通过，比率精度通过；是全标的日汇总，不含逐合约价格、IV 或完整历史链。timestamp 全为04:00Z，即纽约午夜，不能当作当日统计已知的时刻 |
| 长桥 600000 公告目录 JSON、CSV | 未见该原始返回 → 50 条唯一公告ID、50个上交所 PDF 链接 | 事件研究定位正式原件，含 publish_at | 返回时间2025-11-25—2026-09-29；无 total/has_more/cursor，不能称全历史或最新公告全集。全部publish_at比URL路径日期早一天，须对原公告时区与修订核对，不能自动取其中一方当首发 |
| FINRA 官方融资余额 XLSX、CSV | 仅有来源说明 → 1997-01—2026-09，357 个连续月份 | 美国客户融资负债、闲置资金的低频背景资料 | 单位百万美元；2010-02前后分列口径变化。通常次月第三周公布，当前文件不是逐月首发版本，不能在参考月月末使用 |
| SEC 2013Q2 13F 官方 ZIP、28行预览 | 旧2013Q2 ZIP是财务报表包 → 新13F包含166份申报、95个CIK、87,715行明细 | 机构披露与多表解析的正式样本 | 按提交季度归档：提交2013-05-20—06-27，持仓期2009-09-30—2013-03-31，不能叫2013Q2持仓；旧 VALUE 单位千美元。发现行数/金额不符及重复，未放行干净持仓面板 |
| 510300 2024Q2 官方季报 PDF、季度字段 CSV | 已有官方目录链接，未存此PDF → 新原件14页，核对送出日期、份额及母指数 | 为基金申赎与份额口径提供正式披露锚点 | 报告期末2024-06-30，送出2024-07-19；不是6/28或7/1日频份额。当前文件修改时间2025年，未证明首发原版 |

前三项为已连接的 Longbridge 工具[实际返回与汇总](raw/external-financial-resource-access-2026-10-25/controller-connected-tool-summary.json)，不读取账户、持仓或订单。后三项下载来自 [FINRA 官方页面](https://www.finra.org/rules-guidance/key-topics/margin-accounts/margin-statistics)、[SEC 官方目录](https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets)与[基金管理人官方季报](https://www.huatai-pb.com/upload/pdf/1721370528878-htbrhs300jyxkfszszqtzjj2024nd2jdbg.pdf)。新原件均保存 SHA-256、来源与取得时刻；来源许可与研究有效性分别记录。

## WorkBuddy 与 TRAE 的真实边界

| 入口 | 本轮验证到哪一层 | 采用方式 |
|---|---|---|
| WorkBuddy AI V5.8.4 当前会话 | 19:27发起四项公开资料检索，19:29完成；19:36只提取已有结果，19:37完成。模型自述4次 domain_search、第二轮0新查询；根代理实际看见已完成答复，未取得其底层执行日志 | 用于检索出处和生成待核线索。neodata/westock/tdx/wenda名称不证明有独立可调用接口 |
| WorkBuddy 富途／Moomoo／复星财富 | 先前UI为待连接，本轮答复同样未授权，没有新连接 | 不列为可取数据；普通期权链权限也不自动包含历史链 |
| TRAE 官方 iFinD／通达信插件 | 官方文档明确列出金融插件；iFinD需API Key，有免费与付费范围区分 | 是值得继续核的专业入口。免费额度、历史长度、可导出字段、本账户权限均未验证，不能声称已获得二十年专业数据库 |
| 本机 TRAE CN | 已安装且应用清单显示运行；两次选取已安装窗口超时，插件状态未能读取；CLI0.209.1可执行但认证未确认 | 桌面与CLI认证分开；没有安装新版、改变设置、读取密钥或新授权 |
| Codex 插件目录搜索 | FactSet、LSEG、iFinD、通达信精确查询没有匹配；广义查询多为分析工具/数据仓库 | 仅是当次搜索结果，目录非穷举。实际运行时另发现真实长桥工具并完成上表3次查询，不以目录未命中推断没有工具 |

[TRAE 官方金融插件说明](https://docs.trae.cn/work_seven-popular-plugins-in-traework)支持 iFinD/通达信的存在及授权要求；[iFinD 官方服务入口](https://mcp.51ifind.com/)可作为后续权限核查入口。[WorkBuddy 官方连接器说明](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Connector)介绍外部服务接入机制，不提供账户已有数据许可的证明。

WorkBuddy 第二轮确实输出510300的20行季度份额（2021Q3—2026Q2），已另存为 **search-only** CSV，只有2024Q2一行与本轮官方PDF独立核对。没有总数/分页字段，不能称全历史。模型将区间命令标题称为可导出接口、将子集自洽称为大宗全量、将公告日列称为不会混入修订值，均未被验收。600000目标日两融未返回；大宗目标日搜索未见不等于确认零笔；IWM搜索摘要不替代历史期权链。

## 其他候选资源的取舍

- **复用现有**：SEC Apple companyfacts、MSFT submissions/历史引用、2013财务数据包，已有N-PORT镜像，CFTC 2006年以来标普期货分类持仓，French因子收益，国内部分基金申赎与持仓。Apple新下载提案误判重复，已撤回且保留旧版及更正记录，未产生重复GET。
- **公开但尚未取得**：AQR BAB、q-factor本轮未确认可核实的原件直链，停止猜测下载地址；FINRA卖空成交量可作候选，但不是尚未平仓的卖空头寸。
- **需密钥、授权或字段合同**：ALFRED逐次修订版本、Tushare积分接口、Wind/Choice/RQData/聚宽、WRDS/CRSP/Norgate/FactSet/LSEG。未读取凭证、注册、购买或绕过地区/收费限制；没有现有授权不能列为已可用。
- **工具而非额外数据库**：OpenBB、AKShare、解析Skill能统一调用或加工数据，开源代码不增加上游许可。已有持仓截断及长桥历史K线额度0/301607记录保留，没有重试。

上述候选对应的官网资料和既有原件路径见 `existing/resource-dedupe.json`、`official-sources/source-ledger.json` 与 `qualification-v2.md`。本轮没有把截图中TextIn等产品的额度陈述当作已验证事实。

## 本地验收与金融含义

FINRA 357个月无重复、无缺月；早期157个月的闲置资金只有合并值，后期200个月分现金与融资账户。当前历史文件适合描述和后续跟踪，未取得每月首次公布版本。官网还说明部分月度变化可能来自报告方法变化，不能全部解释成真实加减杠杆。

13F的7张表只在内存解析，原ZIP保留。141份有持仓汇总的申报中，4份申报行数与明细行数不同、38份申报金额与明细合计不同；另有127组排除明细行键后相同的记录。25份无持仓明细均是NT/NT-A通知；Put/Call、PRN与修订/组合申报需要保留，不能把所有行都当普通股票独立机构持仓，不能自动删重。数据来源正式不代表填报无误。

510300原件页1、2、12经文本和图片核对：期初55,328,887,690份 + 申购10,129,500,000份 − 赎回4,718,700,000份 = 期末60,739,687,690份，精确闭合；业绩比较基准为沪深300指数。这是季度份额流量，不是日频资金流，不是完整指数成员。

这些资料目前增加了**数据取得与口径核查能力**；对因子IC、策略净超额、账户回撤的增量均未评价。后续若使用，仍须锁定对象、历史成员、可得时间、母指数收益与费用，不能把本次数据验收当作策略采用。

## 可复现证据与状态

全部小原件与结果位于 [`raw/external-financial-resource-access-2026-10-25/`](raw/external-financial-resource-access-2026-10-25/)。

- 合同：`contract.json`；后补真实长桥工具固定3调用清单：`controller-connected-tool-subplan.json`。
- 非重复基线：`existing/resource-dedupe.json`、`additional-dedupe.json`、`additional-dedupe-longbridge.json`。
- 官方下载：`controller-small-acquisition-plan.json`、`controller-small-acquisition-receipts.json`；FINRA的`finra-margin-http-receipt.json`。3个原件GET均HTTP200，总2,816,239字节；各源一次，无重新下载旧成功原件。
- 应用与插件观察：`controller-app-and-plugin-observations.json`。模型自述调用数与根代理实际工具调用分开，不将聊天摘要冒充API原响应。
- 长桥3个原始JSON及对应`-normalized.csv`，字段/时间汇总`controller-connected-tool-summary.json`。
- 独立验收：`audit/workbuddy-probe-review.json`、`audit/local-sample-acceptance.json`、`audit/connected-tool-acceptance.json`；完整13F异常保留，不隐去负向结果。
- PDF口径：`controller-510300-pdf-qualification.json`、`controller-510300-quarterly-official.csv`及核对页图片；20行搜索结果单独标明未合格。
- 成果指纹与最终状态：`manifest.json`、`closure.json`、`controller-delivery-check.json`。

3次长桥调用全部实际返回；未调用私人账户接口，未新注册或授权，未购买，未安装软件，未扩大权限，未修改生产，未写外盘，未删除数据。外部模型/连接器实际成本未单独披露，不能推断为零；新增付费采购为0，新增收益实验为0。全部小产物在项目内，预算20MiB并保留5GiB内盘余量。

## 归档

ARCHIVE：`completed_bounded_source_assessment`，证据结论`mixed`。本轮问题已回答：哪些资料确实可得、能否存本地、当前适用于什么；更广泛的二十年universe任务没有宣称完成。未验证的专业授权和首发版本保留为明确边界，不承诺进程退出后自动采集。
