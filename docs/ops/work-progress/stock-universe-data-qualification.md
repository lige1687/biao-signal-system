# 历史个股池与ETF共用资料资格交接

更新时间：2026-10-05（Asia/Shanghai）。负责人：宽基、行业ETF与个股量价资料线；设备：本地Mac，具体设备名未确认；工作分支：`codex/factor-unit-research-20260915`（共享脏工作区，只编辑本任务准确路径）。提交与远端推送：本阶段未提交、未推送，不能称已跨设备同步。

## 本阶段目标与验收

接续已授权的黑绿灰/绿色占比/变色频率/乖离同日选优主线，只做历史沪深300普通股池及现有8只ETF的共用资料资格。验收是可读的来源清单、准确指纹、逐代码/日期缺口、排序与可成交用途的分层结论，以及技术线可执行的恢复条件；旧18项量价结果不重跑，A01合同和技术定义不改。

## 2026-10-05实际完成

- 读回10月5日协调增补、环境/股票池方案、A01合同与v1.1资格、旧9月30日股票准备报告；两份策略源文件实际SHA-256与已确认指纹一致。
- 重算候选成员1,085日、439代码及12个检测到的变动日；重算1,944个候选成员日无收盘，其中3代码全缺、31代码局部缺。逐代码缺口保存在[只读manifest](../../experiments/raw/stock-universe-data-qualification-2026-10-05/read-only-source-manifest-v2.json)。当前另一份收盘长表的行数与SHA-256已变，旧回执不能沿用。
- 核127个旧个股开高低收文件与元数据指纹全匹配，但其选择方式不构成历史总体；核8只ETF来源及共同输入与10月4日回执同指纹。仅8只ETF限定回顾性输入可交技术线，个股主池同日排名及Top20/30净收益仍受资料资格阻塞。
- 公开来源4个定点检索已按事前有限预算用尽，没有得到两次2025临时调整的官方原件；没有行情下载、付费、跨项目资料或大包复制。核查报告：[同日选优历史个股池与ETF共用资料资格](../../experiments/stock-universe-shared-data-qualification-2026-10-05.md)。
- 复核脚本第一次因Parquet日期恢复为索引报错，第二次因质量对象含非ETF条目报错，已分别修复；第三次成功，输出为1,085日、439代码、12候选变动、1,944缺收盘，127旧文件及8 ETF源指纹匹配。失败步骤无市场拟合或数据写入。

## 当前状态与下一动作

资料资格这一有界审查`completed`；个股因子效用`not_evaluated / blocked_data`，8 ETF仅交输入资格，不替技术线宣称因子有效。当前无后台实验。技术负责人可直接按manifest绝对路径和SHA-256读取；合格的ETF支线可独立推进。个股恢复前需12个候选变动的逐次正式公告及身份映射、3全缺与31局部缺的真实报价/原因、439身份的同口径OHLC及行动/退市、来源时点/许可；净收益另需停牌、涨跌限制、成交及费用。新公开资料作业须另冻有限请求和磁盘预算，不能删失败/退市者凑池。

## 2026-10-05 周/月频个股资料委派增补

- 范围：源任务01a10228-d8a4-73ac-afb1-72b1c8b7003a，已有资料只读核验；首批PPO及修正顶底，周检查/月评价。不是旧18项重跑，不下载行情、不计算标签/模型。
- 完成：主源SHA匹配后复用439/1944缺口；补核127文件实际82股票代码候选、44基金/ETF、1指数；82股73与439相交。长收盘又少3行，当前4064305行及SHA见本轮资格。排出228完整周末、54月末，合并252日期；2026-06-30当周未闭合。当前行业为2026-09-22单快照，不能历史回填。
- 交付：[资料方案与最小云端清单](../../experiments/stock-week-month-data-qualification-2026-10-05.md)，证据`docs/experiments/raw/stock-week-month-qualification-2026-10-05/qualification.json`。Library上传/目录检查回执保存同raw，不交行情/账户。
- 状态：有界资料审查completed；historical universe仍BLOCKED_DATA，因子not_evaluated。供应商历史到达未知不绝对禁止有限回顾用途，但不能称实时可实施；当前历史成员不完整仍阻断主池无遗漏结论。
- 下一动作：云端专职线先核2022-01-04基线/完整生效链与身份；分片定位2025-03-10及09-08临时调样与3缺列证券；用户随后授权公开免费资料按便宜模型并行获取，本机不重复抓取。PPO先close/尺度，顶底需high/low及准确修正版本。未提交、未推送；沿共享本地工作区。
- 回调：一次应用消息工具失败，未确认是否投递，不原样重试；以本委派最终回执自动通知为准。

- 最终交接确认：Library `libfile_e6eed4ddc0108191ac61b67bbd1a8da8`，版本1，544290字节；报告SHA-256 `2bf234196eb87cd9ceeea5269d23d3c5317662c5d724bb95eb4cf10158732e6b`。含439规范代码/交易所、候选纳入日期、各股存量调整收盘覆盖、82股票归档路径/指纹及34缺口代码；1944是股票×成员日期记录。报告与机器清单、注册表及439代码追加核验通过，归置检查通过。回执`docs/experiments/raw/stock-week-month-qualification-2026-10-05/acceptance.json`，源报价未复制/改动，0行情/因子/标签/拟合。

## 2026-10-05 已授权BaoStock本机小样本探针启动

- 用户明确授权接收Library最新v1探针包，使用唯一portable_v2脚本。ZIP SHA及v2 SHA均匹配；首个Library下载受限网络失败，获准网络执行后同目标下载成功，未改变VPN/安全设置。
- 本机read-only preflight通过：BaoStock0.9.3，公共默认匿名端点，0网络数据请求；可用复权因子/基本信息方法均有本地说明。旧v1未运行。
- 当前进入run-01唯一匿名会话：固定4段raw日线adjustflag=3+3同窗因子+3基本信息，数据请求≤10、响应≤2MiB、间隔≥2秒、超时30秒，失败按原脚本关闭，不重新连接。输出及原合同在`docs/experiments/raw/baostock-bounded-air-probe-2026-10-05/`；不写主行情、不计算因子/标签/模型。启动不是成功，待读取真实回执。

## 2026-10-05 BaoStock本机小样本完成与交接

- 真实结果：一次匿名会话成功；4日线+3同窗复权因子+3证券基本信息共10查询全部成功，8547供应商字节，最短间隔2.000191792秒，0传输失败/内部重试。
- 日线：60070549行；600837140行至2025-03-04（104状态1/36状态0）；60198925行至2025-09-04（8状态1/17状态0）；60000015行。共229行，其中53条status0延用价且量额空，原样保留并隔离真实成交OHLC。复权因子仅600837同窗2条，其他成功空结果不能证明无全部行动。
- 基本信息outDate供应商原值：6007052025-05-27、6008372025-03-04、6019892025-09-05；未当官方终止公告或指数退出日。历史成员资格/官方行动仍缺，未计算因子、标签、模型，不写主行情。
- 本地验收：57文件回执哈希核对通过，完整响应/代码/日期/adjustflag=3/OHLC关系/预算核对通过；目录检查通过。报告已登记`docs/experiments/baostock-bounded-local-probe-2026-10-05.md`。
- Library交接完成：`libfile_37b07e16c14881919d26b35a611fd3d8`，版本0，ZIP118326字节，SHA-256`67760584aec21ae6f91eac2c96e58d53bf4e952465493aa7cc45d9f26935366f`；71档案条目回读哈希核对通过，含原始wire、解码副本、规范字段、原合同/v2脚本、版本/失败回执及中文报告。Library身份写回通过。
- 下一步：云端先独立只读复核该包，再按来源冻结有限扩量；本机不重连此run-01、不自动批量扩439股。未提交、未推送，所有输出在本任务raw；实际本机身份见execution-authorization.json，不猜测设备型号。

## 2026-10-05 同字节Library重交接

云端原文件官方下载HTTP502；按用户明确要求核本机ZIP可读、118326字节及SHA匹配后，使用正式替换流程给原`libfile_37b07e16c14881919d26b35a611fd3d8`增加版本1，返回`file_0000000034f8822fa8679fffcbb973c5`。替换成功，Library版本元数据写回核验成功，ZIP字节哈希未变。0新BaoStock会话/数据查询，报告和数据未改。新回执`docs/experiments/raw/baostock-bounded-air-probe-2026-10-05/library-identical-replacement-v1.json`；云端是否已能下载需原任务使用新版本/文件ID重试，不能先声称502已修好。

## 2026-10-05 B02冻结下一小批启动

- 用户明确放行Library `libfile_cb52c393a524819189053ad1bdeb62bf` v0；ZIP77627字节/SHA77624d4019fe1289a02c314fdac6abba045b2e0f9867884fd99295c406ba681d、runner SHA7521164902eb237a29c6e7fe52fa6676f565125557ffccfb43723be6017cec8c、合同SHAadee3e384ca5adb73770c3f5a00e7b76b9d7e7b03524bd5f4c115de0f5c907da及包内清单全匹配。
- 依次执行本机47合成案例、4CLI检查、独立preflight，均通过；实际Python3.11.7/BaoStock0.9.3/protocol00.9.30，7源hash/大小匹配；无安装更新，准备阶段无供应商网络调用。
- 测试输出独占`docs/experiments/raw/b02-targeted-gap-batch-2026-10-05/offline-review-01`；采集输出为尚不存在的新`run-01`。范围准确按包内6日线+2同窗因子+2基本信息，≤10查询/2MiB、一次匿名会话、无分页/重连。旧600705与首轮窗口不重抓。启动不是完成，等真实receipt。


### 2026-10-05 B02本机固定批次完成，交云端独立核对

- 设备：本机Mac；分支`codex/factor-unit-research-20260915`。本任务未提交或推送，共享区其他改动未暂存。
- 用户批准的冻结B02输入包、脚本及合同哈希匹配；47项离线案例、4项CLI检查和本机预检查先通过，随后一次采集完成。
- 实际1次匿名会话，精确6日线+2同窗因子+2基本信息，10查询成功、0传输失败、0内部重试；实收49,933字节，最短查询间隔2.000216041022213秒。
- 六段日线1,558条，供应商状态1原值1,505条、状态0原值53条；状态0量/金额空串保留。六个客户端调整表头空串未替换，原解码表头和全部逐行标记均3。不是已核准恢复或主表修补。
- 本机独立只读检查核对65个回执文件的大小/hash、代码、日期窗口、有序唯一、价格数值关系及请求调整方式绑定，通过。保存`docs/experiments/raw/b02-targeted-gap-batch-2026-10-05/local-verification.json`及检查脚本；不改原始run-01。
- 中文报告`docs/experiments/b02-targeted-gap-evidence-2026-10-05.md`已登记registry/INDEX，归置检查通过。
- 三个可直接读的Library文件均版本0：报告`libfile_3c5d193f2a388191b0371d427f119c09`（6,959字节；SHA256 340101daa0459f16b9db56cdeffc66a6911086299c9bd1f8b4ceb01fd94ed0f8）；原始回执`libfile_b3b1a9c9c3d08191890c134f8026f230`（166,119字节；fe43f8200dcc852387261abc9bf8e9d06fabc05c2ae19a8f654bf6057b8718e1）；原始查询清单`libfile_a8dbdea6ce688191b4800994c251d175`（105,375字节；20daf6cbc70ec7922a74178ea443579a63e5e3ffd7aeb8007c1c24f503d9fe21）。Library分别读前10行成功，尚非整文件云端hash或独立数据资格核准；交接元数据见raw下`library-delivery.json`及`library-handoff-local-files.json`。
- 完成的是B02资料取得及本机核对；历史成员、永久身份、公司行动/最终价值、历史行业和应有交易日完整性仍未全部证明。原439代码/1,944候选日期缺口未重新计数或宣告修复，旧研究负结果保持。主缓存、策略文档和规则未改；新特征、标签、拟合、Rank IC和回测均未执行。
- 下一操作：资料统筹直接读Library三个小文件独立核对合同范围，再只读对照B01/B02报价区间与旧缺口。未授权扩大查询，未安排后台任务。


## 2026-10-06 B01/B02接续核对完成；B03方案交付，行情未启动

- 当前设备本机Mac；分支`codex/factor-unit-research-20260915`；未提交/未推送。所有shell采用zsh、login=false、cwd=/tmp和绝对路径；不依赖workspace_info，不改另一任务src/tests。
- 用户本次范围：恢复233精确键及历史成员/行动/终止未决项，提交下一最小批次方案；本轮不立即行情抓取、不修主表、不改registry或研究结果、不拟合。
- 读回Library `libfile_457a3c87e3d88191b8b8fc59d449fbbe`版本0云审计小包：21,329字节/SHA256 3ed11716738a46f4b544a2551048fb178b2e7bf885a012162021592a756fa9e7；8个内部文件指纹匹配，旧34代码队列原件SHA86efbc695762692dd4dff168e5bfa922a180549853586f677205a8b46e294578亦已实际核准。该Library资料复制不是新增行情。
- 独立从指纹仍匹配的旧成员/收盘源重建1,944键，并读10个B01/B02日线查询窗口及对应规范副本：1,601正常原始观测、106供应商占位、233从未查询、4已查无返回，逐键/代码分类与云审计完全一致。233键涉及31代码；现有总原始键1,787。主修复0，原价与旧qfq未比较或混写；180原响应逐层审阅复用原独审，不冒称本轮全量再审。
- 七个当前安装客户端源文件大小/hash与B02匹配；只读文件，没有新导入会话或安装更新。本次源文件、两份策略原文指纹均与旧证据一致。
- 当前检查空闲7,817,805,824字节约7.28GiB，小资料交付不再因磁盘满阻碍；旧输入中的storage_hold保持历史事实，不回写原审计。初次Library helper临时路径解析失败发生在下载前，修正确切路径后取得原包并核哈希；没有行情请求/协议重试。PyArrow读取CPU权限警告保留，数据核对断言通过。
- 新产物仅本任务方案目录`docs/research/proposals/b03-remaining-gaps-2026-10-06/`及本进度追加：proposed-contract.json、proposal.md、233/120/4精确清单、local-reconciliation.json、当前客户端核对与验证证据、原审计小包。合同固定10日线查询（2个20键及8个10键，共120键），按缺口数降序/代码升序，另外21代码113键未放行；不是10股新研究池。
- B03方案合同SHA256 a273ae6cfe84a5cb8f07fc0fac40cd075233167a8fb402d5bb6b232fab3998a1；120键CSV SHA162575d8008e899233babdac9b6dc4c60c2b7d7ae6307ed0e7407b163a14821e；233键CSV SHA7219d6288ec9637fc958547ef0373da6353e8b4e9adda703942f5e6c7b2d4579。方案键/参数/顺序与0既有查询重叠检查通过；B03运行包、其离线案例及网络预检尚未运行，不借用B02测试冒称B03通过。归置检查通过。
- Library方案ZIP保存成功：`libfile_af1b372d04a08191b8865ae792088d4e` v0，file_id `file_00000000338081fd891cc6b3aaf078b3`，40,662字节，SHA256 d4045cb11e4391808a5544ff428795b37d06befdbccd6e07106b87e3cf7a0536；11文件回读包内哈希核对通过，Library元数据写回成功。本机zip核查不是云端下载独审通过。
- 真实阻断：完整官方历史成员基线/生效链、终止权益链及原件移交仍未齐；B02提到的已留公告不在当前小包，统筹先复用原件。106占位/4终止区域缺返回仍保留不补成交价。统一价格尺度、每因子历史/高低价与精确评价终点资格、需要行业时的历史行业/来源时点另核；不把它们混为单一前提或改变旧合同。
- 下一可派发动作：B03固定合同的离线运行包准备，复用B02保护流程并核新请求/预算/空响应/原表头/失败停止/存储硬检查；准备完成并经统筹/用户明确放行后才连接供应商。当前新增供应商调用0、主修复0、特征/标签/拟合/回测0，无后台任务；不自动续113键，不扩全A/分钟，不付费、配密钥或运行陌生软件。


### 2026-10-06 云端ZIP502后的原始文本交接完成

用户明确停止ZIP重试，授权既有准确合同、B02 runner、两份测试及保存来源绑定JSON分别转Library。先核六份来源绝对路径/大小/SHA，精确及简化标题检索并核10月5日起40个非ZIP目录项，未发现可复用的同类文本；已有ZIP不重复上传。通过官方Library保存六份原文件，各版本0，文件ID/源码指纹见`docs/research/proposals/b03-remaining-gaps-2026-10-06/original-text-library-handoff.json`。

六份完整Library文本读取均完成；显示层省略每份原件最后一个LF，按原末尾补回1字节0a后六份原字节/大小/SHA全部匹配，证据`original-text-full-read-verification.json`。这不是修改存档；字节下载本身不应再补换行。原本机源字节未变，元数据写回成功；B03原ZIP和合同不改。

新行情调用0、研究脚本执行0、安装0，主行情/registry/研究结果未动；只新增交接元数据和本进度。下一动作是云端从各文本ID完整读回、按原换行重建并核哈希，完成B03离线运行包准备；本机不执行任何查询或测试。


### 2026-10-06 B03选中键与既有采集去重原件交接完成

用户要求接续转移已有120键CSV和prior-acquisition/dedup回执。本机确认这对应`B03-selected-120-exact.csv`、`local-reconciliation.json`及`proposal-verification.json`；后者另绑定`remaining-233-exact.csv`，故四份准确原件一起转移。大小/哈希逐项匹配原B03包FILE-HASHES，未重建或改写原件。去重回执分别记录旧源分类/12个查询与规范副本来源，以及120/233清单哈希/0重叠；不凭描述捏造新prior-acquisition文件。

先查同类文本（精确/简化标题+46个近期非ZIP元数据），未找到可复用项。官方保存四原文件v0；Library CSV读取被表格解析增加index并丢前导零，核对失败已保存在`key-evidence-read-display-check.json`，不把这项说成原字节通过。两份CSV再以完全相同原字节的.csv.txt名称保存v0，原CSV Library项保留，未删除。普通文本完整读取保持代码/字段/日期原文；显示LF换行转换回原CRLF并补原末尾CRLF后两份CSV原字节/哈希匹配，证据`key-evidence-plain-csv-byte-check.json`。两JSON补原末尾LF后原字节匹配。不得用重新CSV序列化代替准确原字节还原。

首选可读ID：120键`libfile_a97595e05ad88191be2d9ac2119573ca`（6,420字节，162575d8008e899233babdac9b6dc4c60c2b7d7ae6307ed0e7407b163a14821e）；既有采集复核`libfile_02dc541d79388191a2f70e824686dd48`（5,630字节，03492e5d548cc53840433aa68f58b706da85a1f91136d3f6c041d8535497009d）；方案去重核对`libfile_cb1004187dd8819185c7d8b6ba7a3179`（660字节，ab3f8f29717fe7c49dc23d940b64df73269b15ef1fe8af03c91c792c46a7edc5）；233键`libfile_3fc8742981608191bc747dc333a4f150`（12,409字节，7219d6288ec9637fc958547ef0373da6353e8b4e9adda703942f5e6c7b2d4579）。全部v0，准确source_path/file_id及重建规则见`key-evidence-library-handoff.json`。

合同另引用旧云审计包及34代码队列SHA，来源保持`libfile_457a3c87e3d88191b8b8fc59d449fbbe` v0及包内original-gap-queue-frozen.json，未重试ZIP或重建。required_outputs是未来执行输出，不伪装为已有回执。本轮行情调用0、研究脚本执行0、原合同及数据变更0；只新增交接小证据与本进度，不改registry/报告/主行情。下一项仍由云端准备B03离线包及8MiB/512MiB真实程序检查；本机未运行新采集。


## 2026-10-06 B03本机离线/current preflight启动（未放行网络）

用户授权Library libfile_253b044757b081918a413636852e3711 v0已审包的本机离线检查及真实当前去重证明；尚不放行供应商连接。输入ZIP187,959字节/SHA08f9ccd1beeae839d752d6d4a5a1a743ae9f7d5c2b0d10c835fcb8acea1c3c7e、44文件CRC及43正文manifest哈希、runner c52c78cfdaa2312e882b135d032ff61e4df8df14c4bec03abcc19319c118b710和合同a273ae6cfe84a5cb8f07fc0fac40cd075233167a8fb402d5bb6b232fab3998a1全部匹配。准备原件仅复制到docs/experiments/raw/b03-targeted-gap-batch-2026-10-06/package/extracted-v0；拟采集run-01路径尚不存在，不创建它。先只读核12份来源与后续交接，随后在单独offline-review-01执行76+8检查。启动不算检查通过；不给无效模板填假证据，也不执行普通runner入口。


## 2026-10-06 B03本机离线/current preflight通过，待父线程精确释放

- 原包187,959字节、ZIP SHA08f9ccd1beeae839d752d6d4a5a1a743ae9f7d5c2b0d10c835fcb8acea1c3c7e、44档案CRC/43正文manifest及准确runner/合同指纹匹配；原件不改。
- 实际Mac Python3.11.7/BaoStock0.9.3/protocol00.9.30，7个当前源pins匹配；76项离线案例及8项CLI均通过，真实socket创建、官方login/行情查询均0。CLI导出的preflight-only-guarded.json是真实当前预检（不是云端结果），session gate通过、runner写入0；不重复无理由重跑预检。当前proof由实际12份基线及后续交接/采集根目录读回生成，模板原件仍无效未改。
- 12基线文件当前大小/hash不变；10个既有消耗的daily窗口与10待查窗口无重叠，120键仍从未查询，新增选中键0、既有/部分B03消耗0。检查包括已有独审目录，仅审查无新增采集；canonical roots下只有B01/B02两个实际query-manifest，B03包/模拟记录不当作已采集。旧成员/前复权主源及12份基线在验收再核指纹不变。没有读全部线程身份。
- 两个AST-selected已审只读验证函数对真实证明校验通过，无普通成功入口/客户端调用。proof sha32ae71c390c632f0232bcbb2985dcdeaf43a7f93b1f043305bab73c9c3385c6c；runner c52c78cfdaa2312e882b135d032ff61e4df8df14c4bec03abcc19319c118b710；合同a273ae6cfe84a5cb8f07fc0fac40cd075233167a8fb402d5bb6b232fab3998a1。证明checked_for_this_dispatch=true表示已实际核本轮资料，不代表交易或网络授权；network_release=false。
- 绑定的待采集绝对路径：/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/b03-targeted-gap-batch-2026-10-06/run-01，验收及提交时尚不存在，未创建。测试输出独立offline-review-01；证明/current收尾在current-recheck-01。验收空闲7,591,780,352字节，超过512MiB；程序8MiB输出/512MiB空间限制的本机合成案例已通过，不把文字规则冒称硬限制。
- 可读Library v0：证明libfile_fcebefb4a6848191b91575446d5cafb1（26,188字节）；验收libfile_8d8c4a22bebc819182d24bbf8851dca9；76案例libfile_18e64632d0c0819199a043e1cb44eb85；8CLI libfile_d41459916c8c819188a941a8c824b8dd；当前预检libfile_289a3066126c8191aed40bff8eb935c0；证明验证libfile_57bc15797a208191aab2bbd027d67f26。六份完整文本补回原末尾LF后逐字节/hash匹配，见raw/library-text-verification.json，完整交付meta见raw/library-delivery.json；Library元数据写回通过。
- 收尾证据preflight-acceptance.json、offline-review-01/*.json及完整两组执行日志已保存；当前归置检查通过。未提交/未推送，未修改src/tests、registry、规则、策略文档或主行情，没有新的因子/标签/拟合。当前无后台命令。
- 限定的本机离线/current预检阶段完成；实际B03采集尚未执行。唯一待释放事项是父线程审阅上述真实proofhash、准确runner/合同与唯一输出路径，明确释放一次匿名会话+10次日线；哈希、模板、离线通过或本记录均不替代此授权。收到释放后仍须按原程序空间/来源/输出路径检查，无重试/换目录/自动续113键。


## 2026-10-06 B03 run-01唯一实际采集获准并启动

父线程明确释放本轮proof32ae71c390c632f0232bcbb2985dcdeaf43a7f93b1f043305bab73c9c3385c6c、runner c52c78cfdaa2312e882b135d032ff61e4df8df14c4bec03abcc19319c118b710、合同a273ae6cfe84a5cb8f07fc0fac40cd075233167a8fb402d5bb6b232fab3998a1及唯一run-01路径；授权记录raw/execution-authorization-run-01.json。启动前3准确hash/12基线/7client pins再次一致，当前只存在B01/B02两个实际采集清单，run-01及live日志均尚不存在；空闲7,557,996,544字节。只执行冻结10个raw3日线请求/120键，一匿名连接，2MiB响应、8MiB输出、512MiB最低空间、2秒发送间隔、30秒超时，首次错误停止；不重试/重连/换源/新attempt/增查113键，主表/成员/qfq和拟合不动。启动不等于成功，等待真实台账与响应。


## 2026-10-06 B03 run-01实际停止；只读复核与Library交接完成

- 唯一已授权采集实际退出3：1次TCP连接成功、1次会话发送，收到87字节；冻结runner首次协议校验失败即停止。数据查询执行0/成功0/日线失败0/未执行10，实际日线0行。会话资格失败1、传输失败0；不得把客户端login success字样写成完整资格成功。无重试、重连、换源、logout或第二attempt。
- 120指定键全部not_attempted_unknown，不是已查无返回；113延后键未触及。旧1944分类仍1601正常原始观测、106占位、233从未查询、4已查无返回；未修主表，原价不与旧qfq拼接。
- 明确原因：冻结runner第508行要求回应head[0]与客户端00.9.30相等，实际服务端回应00.9.10；只读核旧B01/B02的23份已保存成功回应首字段均00.9.10。新增校验不相容，未指向行情不存在或服务器刚升级。当前87字节wire SHA fb91d860d8401189a211153998f1b7d26a5e54111e9de7936ec8a05bbfa1a692；protocol-source-evidence.json含全文hex、7client pins及23旧回应来源指纹，冻结runner原件未改。
- 本机结果验收：25份清单文件大小/hash及7条台账链核对通过；加校验清单共26文件396850字节。响应87字节低于2MiB、run输出低于8MiB；结束空闲7507521536字节高于512MiB。只有一次发送，间隔无可验对象；未超时。主成员/qfq两源、12基线文件及7客户端源指纹不变；主修复/特征/标签/拟合/Rank IC/回测0。原错误、wire和全部原始回执原样保留，normalized日线为空。原76+8离线通过未覆盖此真实服务器版本差异，不掩盖实际失败。
- 新只读审查仅raw/stopped-run-review-01与check_stopped_result.py；中文停止说明也在此目录，未改策略实验报告/registry/src/tests。Library七份结果各v0，完整文本读回（receipt分3页）按原分页LF及末尾LF还原后原大小/SHA全部匹配；回执library-delivery.json及library-full-text-verification.json。ledger.csv未造，原JSONL只做同字节.txt副本。Library元数据写回通过。
- 云端最小交接索引libfile_56dfcc5ef48881919c15ba27f6232e06 v0，5361字节，SHA d30e4b03d3e75a56103e54796e15530d0df6563a2772a4c5fa75a12db09f244c；含七份准确Library ID/版本/source_path/大小/完整SHA和重建说明，索引完整回读核对通过。停止说明libfile_661548b76ac4819190731e081b1d31b4；原receipt libfile_902ac40dcf28819182716688bb5419e2；原query-manifest libfile_e9fa1c3e3f68819197cc29636fab69c0；原120键回执libfile_095199a812b08191903fe16dd9b1b37f；协议诊断libfile_723552e7e6688191aeec991344e8135e；本机验收libfile_cd72f25902b881918f8f4107353d51f5；原台账同字节副本libfile_eb3fd16016008191b2d91d2e850c26a0。Library完整回读是交接校验，不声称父线程独立复审已完成。
- 当前实际采集停止，授权已消耗；本机无后台进程、无继续查询。下一操作由云端用87字节及旧成功回应离线修正校验、补失败案例并独立复审新runner/hash；重新生成真实当前去重证明及唯一新路径，再取得新一次精确放行。不得复用本轮proof、换目录重跑或自动续113键。未提交/未推送，分支沿codex/factor-unit-research-20260915。最终归置检查结果见stopped-run-review-01/repo-hygiene.log。


### 2026-10-06 已保存真实响应夹具补交，新增供应商调用0

父线程为离线修版本校验，明确只取B01/B02已保存匿名回应和公开行情。本机固定读取B01 run-01的manifest/receipt、匿名登录wire/decoded，以及daily-3-sh-601989 wire/decoded和现存客户端字段快照；未运行客户端/runner源代码，不登录/查询/重连，也未重试已消耗B03 run-01。

选中两份原始回应满足三类案例：成功匿名登录88字节；601989日线完整621字节wire/2644字节保存decodedtext，原请求2025-08-01..2025-09-19、raw adjustflag3，返回25行（8正常、17status0量额空占位），同一完整回应复用于正常/占位两个测试角色，不切片重造响应。最后返回日2025-09-04，保留请求终点与返回终点的差别。匿名/日线请求参数沿原manifest原值；B01没有保存发送字节，特别是匿名请求未留，未构造请求或补凭据。

新产物仅raw/b03-targeted-gap-batch-2026-10-06/saved-response-fixtures-01；JSON包含原始wire完整hex/base64、保存decodedtext全文（含SOH与原LF）、原请求方法/参数、准确原路径/大小/SHA及字段含义。原件hash匹配现存原回执，hex/base64和UTF8文本逆向恢复逐字节与原件相等；公开字段及密码/token/私钥等标记检查通过，只交anonymous协议与公开行情，不含私人账户资料。原raw未改、因子/标签/拟合0。

Library可读夹具libfile_354d110462e881919bff27be8104f065 v0，file_id file_00000000b4e081fd8e25809176afb615，15,563字节，SHA256 18a7edbb184d58760c8f177faa7a76c7f23dbd309c46e8a2c58c02f5b174b324。首次完整读取提示暂不可见，按返回指导精确标题检索找回同一已保存ID后完整读取187行；恢复原末尾一个LF后源字节/大小/hash和内含wire/decoded再次匹配，无重复上传。Library身份写回成功；local-verification.json、library-delivery.json、library-full-text-verification.json保留来源与失败/恢复记录。

下一动作：云端从该JSON恢复原wire，离线回放和修校验；本机无后台任务、无新供应商会话，原B03授权不恢复。原23头部/指纹证据继续保留，补充夹具不覆盖旧索引/失败回执。未提交/推送，未改src/tests/registry/主行情。收尾归置检查见同目录repo-hygiene.log。


## 2026-10-06 协议修订v1本机离线/current预检启动；run-02未放行

用户限定本轮仅76base/9CLI/32真实保存回应离线回放、当前来源/去重证明。Library同身份v1 ZIP240119字节/SHA c3ca57ed5d950c99f76e5d768f02093e25806d32a8fa754004d0a0e40ec0db07、64文件CRC/63正文manifest核对通过；runner c9ee0652a026f59ce7b688617752aa8e84add16354ea0317fef20b19aee16cc1、原合同a273ae6cfe84a5cb8f07fc0fac40cd075233167a8fb402d5bb6b232fab3998a1、修订de5ba1ba0b26fdadb311b81bf1dcc528abdcc5bb87962b15033dd4673d5eb238匹配独审原件。输入仅新增package/extracted-v1和input-v1.zip，v0/run-01保留。默认限制网络Library下载失败后获准下载同一指定文件成功，无行情供应商连接。offline-review-02与current-recheck-02将独立保留本机实际输出；拟run-02目前不存在，禁止创建或执行。真实报文尾部数字的外部checksum含义尚未核实，不能写成全协议校验通过。启动不代表测试已通过。


## 2026-10-06 协议修订v1本机离线/current预检通过，run-02待父线程另行放行

- 原包/64文件CRC与63正文manifest、runner c9ee0652a026f59ce7b688617752aa8e84add16354ea0317fef20b19aee16cc1、原合同a273ae6cfe84a5cb8f07fc0fac40cd075233167a8fb402d5bb6b232fab3998a1、修订de5ba1ba0b26fdadb311b81bf1dcc528abdcc5bb87962b15033dd4673d5eb238全部核准。现有Mac Python3.11.7/BaoStock0.9.3/protocol00.9.30，7源pins未变，无安装。
- 76基础/9CLI/32保存真实wire回放共117项均通过，完整命令/日志仅offline-review-02保存。第三套明确--inputs ./inputs并从还原包根运行。真实socket/供应商连接/登录/数据调用0；11次官方login函数调用只在注入模拟socket上回放，不是新匿名会话。87/88字节登录与621字节混合日线原响应恢复，25旧行（8正常/17占位）不计新增B03观测。CLI已导出本机真实current preflight且session_gate=true、network_actions=0、runner filesystem_writes=0，无需重复跑。
- 基线12文件与10已消耗日线窗口读回；选中120仍从未查、0窗口重叠，1787旧返回键未变。当前canonical roots只有B01/B02及已独审run-01共3真实manifest；run-01的5证据文件精确大小/SHA与修订匹配，manifest/ledger/87字节wire/receipt/旧proof wrapper保留；旧proof32ae71c390c632f0232bcbb2985dcdeaf43a7f93b1f043305bab73c9c3385c6c与wrapper680a4c51f5a6a6d862d46fdf449ff4ef95423cdbefebfe1ab8df11da74da374b分开核准。旧run-01仍1已消耗连接/会话、0日线，不删历史/复用旧授权；未发现其他未审B03 attempt。后续停止/夹具/Library交接和单一任务进度已读，无全会话身份盘点。
- 新proof a79f0ab0547a27838dfa703a22f883d8307a2d39276b65a0a727a65a3f237cfe，34217字节，绑定attempt B03-run-02-protocol-compatibility-2026-10-06和唯一 /Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/b03-targeted-gap-batch-2026-10-06/run-02；路径仍不存在，未创建。checked_for_this_dispatch=true为实际资料检查，不代表授权；network_release=false/new_separate_network_release=false。只执行两项AST-selected只读runner验证函数，准确proof门检通过；未执行普通成功入口。原模板保留无效。
- 主成员/qfq两源、12基线及5旧run文件再核不变；验收空闲7201271808字节高于512MiB。主修复/特征/标签/模型/收益试验0，无后台进程。daily尾部数字外部checksum语义仍UNVERIFIED，保留原数字；不称全协议/外部checksum校验完成。
- 七份Library均v0，完整text回读逐字节/hash通过（proof1085行2页还原原分页LF及末尾LF，其他末尾LF）；准确meta及check见current-recheck-02/library-delivery.json、library-full-text-verification.json。
  current-dedup-readback(1).json：libfile_5190365aff108191b2e195f08f48fb16，34217字节，SHA a79f0ab0547a27838dfa703a22f883d8307a2d39276b65a0a727a65a3f237cfe
  preflight-acceptance(1).json：libfile_374667b025c88191bd3a7dddd19c450b，5160字节，SHA 2d7ecb050335dbc8def0b235b3714b575b238c1311dbdc414fbac28314f5bf65
  offline-regressions(1).json：libfile_c628e46b3f348191877add8fbcad1c2f，12788字节，SHA 72240db86aae9d90e4f934a03d9d976d7a785def25a74805d3954c0b9af59e5c
  offline-cli-checks(1).json：libfile_5bbe30ba1d0c819189c7d65413922d3b，3109字节，SHA 7e528bc5e6ab9bf1fdbd8a8c902d86f11f556f2b653ac2614cd8b854b2ca77d9
  real-wire-regressions.json：libfile_53e974c968c481919244e2a2b8116a86，7582字节，SHA 3ef826eeb8b49aaecd2ff144f79a0a4adb0cc7cc99cc65d238a5bea081e9f86a
  preflight-only-guarded(1).json：libfile_d079353c006881919b9f750f909d7ff2，21032字节，SHA 7d0093eb4c95d87738e2283174fc6cc488e26f8fc433a7dfda38895ab0d68ce6
  proof-gate-check(1).json：libfile_32ecad5fc4a481919c69e0db6f0394e4，883字节，SHA a4000e0d526a54b5faa33cfbf6ca10b7b4006113f62853f955f61dc1a67a5ea3
- 云端最小索引 libfile_c06a705c34d88191aa7d0cf7554a8f2d v0，6135字节，SHA b3882d44527ee800ac8d5e165b3d73ded99cb6c2cca0dffda169a2671223601d，完整回读hash通过。初读暂不可见，精确标题找回同ID后读取成功，无重复上传；七项元数据写回成功。
- 阶段完成的是本机离线/current资格核查和交接，仍没有run-02行情授权。下一操作是父线程独立读准确proof/验收/三测试和新runner/合同/修订，确认新proof hash与唯一路径后再明确放行一次新attempt；本机不查询，不重试c52c旧runner，不自动续113键。未提交/推送，分支codex/factor-unit-research-20260915，src/tests/registry/主行情未改。归置收尾见current-recheck-02/repo-hygiene.log。


## 2026-10-06 B03 run-02新一次实际采集获准并启动

父线程明确释放proof a79f0ab0547a27838dfa703a22f883d8307a2d39276b65a0a727a65a3f237cfe、runner c9ee0652a026f59ce7b688617752aa8e84add16354ea0317fef20b19aee16cc1、原合同a273ae6cfe84a5cb8f07fc0fac40cd075233167a8fb402d5bb6b232fab3998a1、修订de5ba1ba0b26fdadb311b81bf1dcc528abdcc5bb87962b15033dd4673d5eb238及唯一不存在run-02路径。执行前4hash、12基线、5run-01旧证据、7客户端源与2主数据源再次核准，仅3已知实际manifest，未发现其他attempt，空闲7497433088字节。授权原件raw/execution-authorization-run-02.json；允许本轮1新匿名连接/会话、10日线/120键，2MiB响应、8MiB产物、512MiB最低空间、2秒发送间隔/30秒超时，首次错误停无重试/重连/换源。run-01旧1会话保留，不能称累计一次；113键不续。主表/qfq/成员/拟合不动，尾部数字checksum含义未知继续明示。启动不代表成功，等待run-02实际回执。


## 2026-10-06 B03 run-02完成：120行全停牌占位，主表未修复

- 唯一新一次获准run-02实际exit0，1新匿名连接/会话、10日线发送全部成功。保留run-01旧1次会话，累计B03为2次；无retry/reconnect/logout/额外查询。收到2960供应商字节，所有发送间隔含登录到首日线最短2.010842250秒；全轮约20秒，未超30秒操作时限。113延期键未触及，本轮授权消耗完。
- 实际raw120行，正常0、status0量额空/沿用价格占位120、已查无返回0、不合格0、未执行0。601059/601995各20占位，其余001979/002049/002252/002736/301269/600027/600150/600438各10占位。它们不能当真实成交填补旧价格或用于新收益拟合；无主行情/qfq/成员改动。旧1944资料分类更新为1601正常原始观测、226占位、113从未查询、4已查无返回；该更新仅本轮read-only证据，不回写旧封存或研究注册。累计原始记录1907（1681正常/226占位），口径区别于1944旧候选缺口。
- 本机独立标准库核对77份清单文件SHA和46条ledger链，通过；加checksums自身共78文件786571字节。完整wire独立bounded zlib解压与保存decoded逐字节相等，原record数组=client snapshot=normalized，120键/原价3/代码日期/占位空值及5层hash逐项核准。非压缩登录CRC32核对通过；全部daily尾部数字原值保留，外部checksum语义仍未知，绝不称全协议checksum已验证。12基线、5旧run证据、7客户端源与2主源指纹未变。收尾源核查空闲7491854336字节，另最新storage-check见raw；本轮全部run+review+授权+日志+核对脚本共1064054字节，低于8MiB，空间高于512MiB。
- 采集完成后exec transport断开，恢复及pwd超时；正进行的一次原三文件Library保存随后成功，本机连接恢复，继续独立核查。未重跑采集/未重复原文件保存。失败上下文见library-original-delivery.json/local-audit.log及本记录，不把短暂访问阻塞藏成一开始全绿。
- 新文件仅check_run02_result.py及run02-review-01；中文说明与独立acceptance、113精确键和原层可回放source-layer JSON保存。后者含每段原wire/requestwire base64与原decoded/client/normalized全文和大小/SHA，无重新序列化原数据；公开行情/匿名回应检查通过，无密码token账户资料，不传登录请求。原run-01及run-02未改、旧负结果保留、src/tests/registry/主数据未动。
  原件Library receipt(2).json：libfile_3721ed1bf4648191a34fb4590e3e81a5 v0，166187字节
  原件Library query-manifest(2).json：libfile_f50bb8a6cf8081918795ff71e52d4056 v0，121960字节
  原件Library selected-key-reconciliation(1).json：libfile_0ab35c6a389881918dc279e2e07e85a3 v0，24925字节
  新证据Library B03-run02-findings-2026-10-06.md：libfile_c6a3e32534dc8191aa600b794fff8a24 v0，3666字节，SHA 7da3bd2c5c62b0b035ddbabf7ae4adb9084e8c281ba3f6ccfab1b62ce8e387a1
  新证据Library acceptance(1).json：libfile_1a206da1d3948191a67bf3a058b40efd v0，40025字节，SHA 5ef176c45ba4e8255501687f41d04ab28637c50840bcc1dd52bab4b1e356dee0
  新证据Library B03-run02-source-layer-evidence.json：libfile_bd87bb04876c819198f59204779e4136 v0，158449字节，SHA 49ee5ee10fc317d10d812a884395231e7a7678c02e4404167b1a5858e52cd16d
  新证据Library deferred-113-exact.csv.txt：libfile_7616019f9aa081919ecce23503136947 v0，4209字节，SHA b116a13897d1bbdb1415dffe66867ec7bf389a903bd908f52807496bfb7ad511
  新证据Library B03-run02-attempt-ledger.jsonl.txt：libfile_e921ee491d0c8191b8a97486a594aa98 v0，22260字节，SHA ba022cd81117eee3d6d8c5d56b8d4aacf3c81d7f3088f12956222f57821c6602
- 云端小索引 libfile_d71ee8cbb534819192f0463bed38a6bf v0，7465字节，SHA fb9034ce5f48a8a093467a65b0dc38584f007dbf1632536f36342d5c0f8fc561，完整回读匹配。8文件全text回读逐字节/SHA与原件匹配（receipt6页、manifest4页，补原分页LF/末尾LF，其他6项补末尾LF）；不把给下载字节补LF当作规则。Library身份元数据全部写回成功，准确meta见本review三份delivery与full-text-verification。索引初读暂不可见，精确标题找回同ID后读取成功，无重复上传。
- 完成仅本轮资料取得、独立本机核查和交接，不是历史成分/证券身份/行动及终止权益/统一尺度/因子有效/真实交易资格通过。下一操作是父线程用原层证据独立核准120占位分类，再接资料资格缺口；113从未查键须新冻结/新授权，不自动下一批。无后台任务、未提交/推送，分支沿codex/factor-unit-research-20260915。最终归置检查见run02-review-01/repo-hygiene.log。


## 2026-10-06 B03 run-02云端独审通过；更新113未查键，B04仅准备

父线程独审小结libfile_9bf12aec3b948191a3027598ddaf3b5d v0/18667字节/SHA7c1efbeb30f2e30af5ab191f14cc2b6af4df39e5043b82a200e67064c86c3fb1已完整读取、按原LF恢复核准，原件复制B04方案source.json不改云审计。旧1944资料分类1601正常raw/226供应商占位/113未查询/4旧无返回。此前本机把status0直接叫“停牌占位”表述过强：现在明确只证明供应商非交易占位，不能当交易所停牌事实、正常成交或可执行交易价格。历史原件不改，解释以本独审为准；新增正常观测0、主修复0。

current remaining-113-exact.csv在B04方案目录按原4209字节/SHA b116a13897d1bbdb1415dffe66867ec7bf389a903bd908f52807496bfb7ad511复制；旧B03 remaining-233-exact.csv和run02 deferred113原路径/指纹保留。独立读23来源文件/1907旧返回键、20已消耗日线窗口、4实际manifest，未发现新增/未审attempt；剩113键与旧返回0重叠。按原数量降序/代码升序首10，与云审计逐窗/日期匹配79键，另34键保留不派发；10窗与20旧窗口无重叠。尚未执行B04 runner或供应商调用；在docs/research/proposals/b04-remaining-gaps-2026-10-06继续合同与适配计划准备，不改registry/主行情/旧run1/run2。


## 2026-10-06 B04最小合同与runner适配计划交付完成；无新采集

- 只准备合同和参数/授权适配方案；B03云审计解释已纳入：供应商status0占位不能直接称交易所停牌。remaining-state及113当前清单更新完成；旧233及原run02 113清单路径/指纹保留。原run01/run02消耗保持两会话/10日线，未重放。主行情/qfq/成员、研究效果registry及旧负结果未改。
- 新B04合同016b0b016907a5991fe740f1865614bff48a6dad05dd2b06af617e3b33d068be，34046字节；剩113的21代码按数量降序/代码升序首10分组：601088/603019/688041/688126各10，688012为9，300442/600030/600803/600958/601108各6，共79精确键，另34。23数据文件/1907返回键、20已消耗日线窗口和4真实manifest读回，79键/10窗无重叠，没有其他未审attempt。7现有0.9.3客户端源指纹匹配；所有上限与旧B03 caps逐字段相等，非日线请求全空。
- 旧c9ee runner只AST提取纯build_queries做兼容检查，实际拒绝B04（Exact 120-key deterministic selection mismatch），未执行普通入口。识别7组必须差异：嵌入合同/输入/执行身份，build_queries计数，baseline四字段/79-113-34/23源，current-dedup两次B03历史，新的CLI授权绑定，receipt输出，module/provenance/test标签。合同提供实际逐行diff；runner仅适配计划/源码位置与指纹/未来必要失败检查，未生成可执行patch或B04 runner，不能冒称未来新程序旧授权拒绝测试已通过。旧de5只复用协议政策含义，不复用其B03-run02执行身份/放行；日线尾部checksum语义未知继续保留。
- 过程中最终收尾脚本漏一个本地路径变量NameError，两个叙述文档已保存但最后guards未执行；核实际文件后只补未完成阶段。随后exec transport恢复超时，已有三文件Library保存成功后连接恢复。父线程16:45告知Mac已connected，继续核现状无重复写入/采集。失败与恢复记录preparation-build-failure.json；最终本机检查通过，没有降标准。
- 所有准备产物在docs/research/proposals/b04-remaining-gaps-2026-10-06；12份Library文本均v0完整回读逐字节/大小/SHA与本机原件相等，plain CSV/diff都是同字节.txt副本，身份元数据写回成功。完整sourcemeta/IDs见library-first-delivery.json、library-remaining-delivery.json、library-full-text-verification.json。
  proposal.md：libfile_2907847b6b3c8191a89ad026b24a06e7 v0，4939字节，SHA 9bcc18f3e7fd24e7937cde706b0ca96db5c4f917daac779ec8ebdd8c38d78263
  proposed-contract.json：libfile_93e22060220881919ac04846e228178c v0，34046字节，SHA 016b0b016907a5991fe740f1865614bff48a6dad05dd2b06af617e3b33d068be
  runner-adaptation-plan.md：libfile_b2c25c982f988191b80c9caeaf30b285 v0，5797字节，SHA 47688dca617d9dbc56a2c892955ab15a02f6d58bb4aff03926f7db23360fa0e6
  remaining-state.json：libfile_79dc602e63c88191a2a57483600bd949 v0，1860字节，SHA f4c7cd6d4f540aee535d9e231032f5c7927246635a4c78c01db3ba6e8b9c8be6
  remaining-113-exact.csv.txt：libfile_1f5600de1df88191958852e1ab28277d v0，4209字节，SHA b116a13897d1bbdb1415dffe66867ec7bf389a903bd908f52807496bfb7ad511
  B04-selected-79-exact.csv.txt：libfile_c18e83b8f5848191af95b61a3582831b v0，2951字节，SHA 0a5f7ee45bae6771e00c73ab1f994a11a3df51ea893a9aac89010e00f6ac1ce9
  deferred-34-exact.csv.txt：libfile_b7d0d5da0ba88191b05d7be402dcb11a v0，1286字节，SHA 940b3f8f486c7e265b3aa357eb13dd3b6026e4043dc06b666ce34e647344fd90
  proposal-verification.json：libfile_c64a9836904c8191b2c22a2da8035356 v0，29409字节，SHA 3558040627e385443d0e7bfdd0162f8fc37b46fe3f2fba02ddaf07f883ad28c1
  runner-adaptation-readonly-check.json：libfile_87c698fb0bec8191b5d2574a6612c790 v0，8970字节，SHA bb83edd1d3798626a3b2bae8eb59235a8f2ba20cdc08e217d4f5155830a7a817
  B03-hardcoded-literal-inventory.json：libfile_cfd443e612bc8191bf08f2b5b7643b72 v0，8183字节，SHA 5a97f063c429c2b961b6b9b642e4033bd833803476c8ad7c6bf2839ae5d45240
  contract-vs-B03.diff.txt：libfile_19c5a98fe9148191befb686eeea4b982 v0，42549字节，SHA 2aa47799c580d40725f5574f0cad28123892fa17bd838480a8f5da8da8783602
  preparation-acceptance.json：libfile_d505b4363cac8191861d7375244a175b v0，1313字节，SHA 4bef99e5b9d489ed7272c3c457b9e8cb0e1b34dfff20c8d9cc23b98ada39ae9d
- 最小云端索引 libfile_41da4f2fc81c81919e17d09a63b80437 v0，9324字节，SHA bab7b439e851f754ccd363f7ee7b09fe2d76b4c255223a9ce173c7495564351c，完整回读hash通过；初次立即标题搜索未索引到，同一已成功ID稍后可完整读取，无重复创建。归置检查通过。
- 当前准备范围完成：B04实际runner/新执行绑定和新网络许可仍未产生；准确独占B04 run-01路径只是提案且不存在。下一操作由云端按合同/差异计划生成实际patch和新runner/新绑定并独审，覆盖旧授权/旧120计数/缺run02历史/未知attempt等失败情况及原报文和预算保护；其后才本机新current proof/父线程新放行。本机本轮supplier连接/登录/查询0、因子/标签/拟合0，无后台任务，不自动启动下一阶段。未提交/推送，沿codex/factor-unit-research-20260915。


### B04 本机离线与当前预检开始（2026-10-06T17:28:45.701419+00:00）

按父线程授权仅执行离线测试及当前资料核对。包224793字节、56文件CRC与55载荷指纹已核验；runner dffaad233f2c、profile7367d45812cf、binding788ceec54c53、合同016b0b016907原件保留。B04 run-01尚不存在；供应商访问0、网络放行待父线程另行许可。B03两次已消耗历史保留。


## 2026-10-06 B04 本机离线与当前预检完成，采集待父线程另行许可

完成范围仅本机离线测试、当场资料核对和Library交接。本轮供应商连接/真实会话/查询均0，主行情、特征/标签/收益/模型不改、不运行。

原包224793字节、56文件CRC及55载荷大小/hash通过。四个指定原件指纹均核准：
- SCRIPT_SHA256: dffaad233f2ca3b44b81816c31545dc0b2e3b7e10281cf77ecef0fce7423771b
- SEALED_PROFILE_SHA256: 7367d45812cf753d5dc81afb77bcbe214d17a4af07e7787b60f9d4f8c4a30f2e
- EXECUTION_BINDING_SHA256: 788ceec54c536cea578d62dcf72caa615a5992ff967d0a1669ee536bda7fd1f6
- FROZEN_CONTRACT_SHA256: 016b0b016907a5991fe740f1865614bff48a6dad05dd2b06af617e3b33d068be

本机现有Python3.11.7/BaoStock0.9.3/protocol00.9.30，7源码大小/hash及当前预检通过；62继承保护、13命令行、24历史回应重放、42B04专项，共141项全通过。完整命令与日志在offline-review-01；官方login只对模拟socket执行，不是新提供方会话。

23份数据基线和两次B03各5份历史文件重新读回；4实际manifest、20已消耗日线窗口、1907原返回键未变。113未查键精确分成79选中和34延后，21代码分片；79键与旧返回无重叠，10拟查询窗口与20旧窗无重叠。60份限定的交接/授权/验收JSON及单一任务进度实际读取，无额外/未知attempt，不盘点全部会话身份。原B03 run01为1已消耗会话/0日线，run02为1已消耗会话/10日线；原件、旧proof及旧负结果保留。

新真实proof /Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/b04-targeted-gap-batch-2026-10-06/current-recheck-01/current-dedup-readback.json，62781字节/SHA a297c2d3198527ff09345a0b768a629c6c23c8f0baacdadfcbfbd4b2a957cf78，绑定四个B04指纹、attempt B04-run-01-remaining79-2026-10-06及唯一 /Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/b04-targeted-gap-batch-2026-10-06/run-01。该目录仍不存在、未创建。仅AST提取四个现审纯校验函数，证明通过，未执行普通成功入口；checked_for_this_dispatch=true只表示实际核对，network_release和new_separate_network_release=false，模板仍无效，旧B03许可不复用。

验收8666字节/SHA707312d72feba4a46351043254c13e97430c1f49cf1374cbb8f2b7947fa08e1c。两主源和33基线/历史文件收尾再核不变，证明时空闲6238871552字节、收尾5720944640字节，高于536870912门槛。日线外部数字checksum语义仍未核实；status0仅供应商非交易占位，不能证明交易所停牌或可交易价格。

8份Library正文均v0，完整text回读恢复原分页/末尾LF后与本机源字节、大小、SHA一致，全部身份元数据写回成功：
- current-dedup-readback(2).json：libfile_4ef2cab562708191be16aa5d92990c78 v0，62781字节，SHA a297c2d3198527ff09345a0b768a629c6c23c8f0baacdadfcbfbd4b2a957cf78
- B04-current-preflight-acceptance.json：libfile_771bc77363d08191a48b19b1f1e06176 v0，8666字节，SHA 707312d72feba4a46351043254c13e97430c1f49cf1374cbb8f2b7947fa08e1c
- proof-gate-check(2).json：libfile_9a5e2761106881919c7e36a9f8241ebc v0，1095字节，SHA 278ec4309a157d2b4eb2fe0ba9df229020bf5e380ca0abcdaea6aad91beac5f7
- preflight-only-guarded(2).json：libfile_113f64b16da4819197e6e5832f476613 v0，44412字节，SHA 3457631d4542a2998a4f494884dafa1357669d65902f8de37b676493a5134000
- offline-regressions(2).json：libfile_5d9e73f96e488191b3c324d445dc1041 v0，11269字节，SHA 6295a138e33b247dbb43cacba21ceeb9f1118b720bdd06903d0b30918dd692a4
- offline-cli-checks(2).json：libfile_496bb4b979188191ab21ac24a164c206 v0，4337字节，SHA ad676d8fa9b6068edd6a42692895f629824b29ecda82c238b5ca9e3a37117a96
- B04-binding-checks.json：libfile_b5938d3f46148191b2ff0f418d5773e9 v0，5649字节，SHA 176ec2e171d2303931dc413c94e4efcc138ffdbaa8da95d0dd0a6f5633dc02e9
- real-wire-regressions(1).json：libfile_de32365f2c2c81918cefc560f88ad38d v0，6626字节，SHA 3a4bf9cdf48cb07455b2920fcedf509d6e5d443ece82c0e4268b097bc9f77442

最小云端索引libfile_af4925a891e4819187afb5031f433016 v0，7532字节/SHA cf35640ba1dedca101525ab23fdf313eb07805feef738379c7f145425a4f16d6，148行完整回读精确字节核准。初读暂不可见、两个搜索参数不匹配及临时patch缺旧行均留在preparation-tool-error.json；核实际原件后重读同一已创建ID恢复，未重复上传。初始助手源码取得后的JS变量错误也留痕，无提供方或源修改。

归置检查已通过，见current-recheck-01/repo-hygiene.log。未提交/推送，沿codex/factor-unit-research-20260915，无后台采集。

下一项真正操作：父线程读取准确索引、proof、验收及本版runner/profile/binding，独立复核后单独明确放行一次新B04；当前不查询、不重放旧attempt、不续查34键。历史成分链、证券身份/公司行动及终止权益、统一复权、历史行业和当时可知数据及来源权利仍未合格，离线通过不代表因子效果或交易资格。


## 2026-10-06 B04 run-01 单次实际采集获准并启动

父线程明确放行proof a297c2d3198527ff09345a0b768a629c6c23c8f0baacdadfcbfbd4b2a957cf78及runner dffa/profile7367/binding788c/合同016b的完整指纹、唯一原不存在B04 run-01。执行前5授权hash、23基线/10B03历史/2主源/7现有客户端源核准，只有4既有实际manifest，空闲5196636160字节。授权保存raw/b04-targeted-gap-batch-2026-10-06/execution-authorization-run-01.json。仅新1匿名会话、79键10窗，延34不查；≤2MiB响应/≤8MiB本地/≥512MiB余量/≥2秒间隔/30秒时限/首错停止无重试重连换源。启动后许可消耗，无论成功失败不得重开或自动续查。B03两次消耗保留，不改主表、不跑研究效果。


## 2026-10-06 B04 run-01 单次实际采集完成并交接，许可已消耗

本轮程序实际退出0，1新匿名连接/会话、10冻结日线全部成功，收到2755字节；原wire/decoded/client/normalized及79精确键分类已保存。不重试、不重连、不注销、不额外查询，延后34键未查。79行全部为供应商status0非交易/重复价格/量额空占位，正常观测0，不证明交易所停牌，不填主行情，不做收益/因子/标签/模型。

B03两次旧消耗保留：此前2会话/10日线，本次B04后合计3会话/20日线/5802接收字节。连同B01/B02全部实际尝试为5会话、30日线、40数据请求、64282接收字节；更早B01自带1次注销不属于本次B04。旧1944候选来源分类现在为1601正常raw/305供应商占位/34未查/4旧无返回；主表仍未修复。所有批次共1986raw行，1681正常/305占位，口径区别于1944缺口。

本机标准库独立核准79清单文件hash，加checksums自身共80run文件/970982字节，46条台账指纹链和原回应受限解压、保存decoded/source数组/client/normalized逐字节与逐字符串相等；79键与冻结日期/代码/raw3一致，延34原CSV字节未变。全部实际send含登录到首日线最短2.0039780419901945秒，11操作最长2.432767秒；无超30秒。原日线数字checksum意义仍未知，原值保留；zlib完整性/文件SHA不冒充外部数字校验，非压缩登录CRC32独立核准。

首次只读核数到累计时，B01旧schema没有data_requests_by_kind，KeyError；当时review目录仍空，未产出验收，未重复采集。按各原manifest逐查询实际发送重算，并与全请求总数及已存在的分类计数交叉核对，整轮只读修复验证通过。原失败local-audit-run-01.log、修复后local-audit-run-01-corrected.log及audit-failure-and-resolution.json完整保留。

原23基线/10旧B03历史/7客户端源/2主源不变；Library交接后33基线/历史及2主源和79run清单再次核准。收尾空闲3531829248字节，≥536870912；B04整个目录含程序包/离线/current/采集/独审共2592423字节，<8388608。不存在第二个B04run，无后台任务。

8份Library文件均v0，17页全文恢复原分页LF和末尾LF后源字节/大小/hash全匹配，身份元数据写回：
- receipt(3).json：libfile_389fd8571874819184f41bfa0d891ac0 v0，180653字节，SHA db9f2aeaa8ff1b076c9af1115c18f413c835877db20e5bd90e42966d6d3d6d7b
- query-manifest(3).json：libfile_1edc5a1c4f2881918a62c3728c8d3f25 v0，110448字节，SHA be3c206b562d4acfa176f1c5f71d47ec8de1e6c7fb44d46066c4527bea227c81
- selected-key-reconciliation(2).json：libfile_6ffe8bf46f9c819192b9a0f0eb96e0ec v0，16477字节，SHA 5712f49c1b20d3b47babff52c7f9538ce12630641becc465af31ca1317ff173f
- acceptance(2).json：libfile_85e4e5a75d18819188bde12ca586a389 v0，49608字节，SHA d01154fe45c4079f2305d9350c5b6a44b0a4bfbdbf4c0a0de84fd78591572860
- B04-run01-source-layer-evidence.json：libfile_4b25bb8bd2148191a68af397cd3a86a4 v0，123840字节，SHA 6a25781e18bbe0333a6ce9a27f72fb25b7e1d98112bc15ae774f48fe01c0cfe8
- deferred-34-exact.csv(1).txt：libfile_6c0904f61dc08191a4dc6147308107ef v0，1286字节，SHA 940b3f8f486c7e265b3aa357eb13dd3b6026e4043dc06b666ce34e647344fd90
- B04-run01-findings-2026-10-06.md：libfile_02655642304c819197ec75a45886eb23 v0，3239字节，SHA 3d39f8c462efe33449c99d2e715c8dcab1988dc7b3a428dad5e1058a87f2920c
- B04-run01-attempt-ledger.jsonl.txt：libfile_59ecbae6828c8191839c9d2976d2fc30 v0，22263字节，SHA a8fde8bf1c2fa850c8e42f07556e0dbfcbad53f743ea7bbdc87028e0bca87d7c

最小云端索引libfile_d1f0d74ae7288191a20455f4b3a23652 v0，8525字节/SHA c380f4ef6320c42945fa2d250b7fbe0189c6c4436ef2fa14a1b4a0514253730f，172行全文回读与源字节一致。所有原层sourcebase64/UTF8反向恢复核准，不含私人账户或登录请求；准确meta见run01-review-01/library-delivery.json、library-full-text-verification.json与索引。

本次许可已经消耗完；完成的仅B04来源证据采集和本机核验。下一操作由父线程从原层独立审阅79占位分类、34未查和累计消耗，不能自动重开或续批。历史成分链、身份/公司行动及终止权益、统一价格尺度、历史行业和当时可知数据、数据使用权仍未合格；不宣称因子有效或交易资格通过。未提交/推送，沿codex/factor-unit-research-20260915，src/tests/registry/主行情未改。归置检查随后执行，见run01-review-01/repo-hygiene.log。


## 2026-10-06 旧qfq生产链与成员/身份/行动资格只读推进

父线程要求B04独审并行期间推进不依赖34未查分类的资格。仅已有439候选池和原1944最新1601正常raw/305供应商占位/34未查/4旧terminalnoreturn。旧正常raw不混写qfq，占位/无返回不当成交。范围固定inspection-scope.json，只读生产源码/原缓存hash/既有回执及32份已有官方文件，不联网、不provider、不fit、不改主行情或registry。最终交付精确来源/价格尺度条件及最小可执行修复方案，未知历史到达区别严格当时可知和有限回溯用途；不修改原研究合同。新产物docs/research/proposals/stock-price-scale-and-membership-2026-10-06及raw/stock-price-scale-provenance-2026-10-06。

## 2026-10-06 旧价格来源与最小资格方案只读交付完成

设备为本机Mac，沿codex/factor-unit-research-20260915，未提交或推送。固定范围实际核准99份来源指纹；原宽表49,432,584字节/SHA 5ad045c518d0bb4394d8c8cb946d207ad9b5b1454e5a776b1a3766c62b475b04、候选成员表SHA a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30均沿用，旧负结果保留。生产脚本确定为backfill_breadth_full.py调用AKShare stock_zh_a_daily(adjust=qfq)，原供应商新浪；只存收盘，现有代码名单不是历史全部A股。原安装版本、当次实际命令日志、逐股获取时间、原始调整因子和实际复权基准日未留证，当前客户端版本及文件mtime不能代替。

1,601正常raw实际分为600705九条、600837七百二十八条、601989八百六十四条，三者在旧表整列缺失，同一股票raw与旧qfq没有重叠，不能直接算比例拼补。原1,944来源分类仍为1601正常/305占位/34未查/4此前无返回；主行情未修复。5份已保存因子查询仅6条实际记录：600837为2022-07-28、2023-07-28、2024-08-08、2024-10-18；601989为2024-08-01、2025-06-18；600705窗口空。请求窗口、取得时间、原字符串及因子/basic各层来源指纹均在saved-factor-and-basic-inventory.json。空窗口不证明无行动，六行不证明完整因子链，也不等于原新浪尺度。

32份限定官方原件是创业板/深圳指数资料，不是沪深300起点和完整变更链；限定目录没有合格的三只终止/换股权益原件，不泛化到全部仓库或并行云端资料。下一步复用1个2022-01-04起点对象与12个候选差异对象，对正式有效名单及全部常规/临时变更和代码身份绑定官方证据；12差异不是完整链证明。正式原件若改变原439范围，先报告差异并采用来源/合同修订，不能暗扩取数。三只最小补件是完整预热名义报价、开始因子状态/有效行动链及受影响目标的终止权益；旧436列保留已声明的回溯代理限制。历史供应商到达未知限制指定供应商当时可用/实时实施的认证，单独这一项不否定明确标注的回溯研究，成员/字段/价格尺度/目标仍需合格。今日行业不能代替历史行业归属。

6份Library文件均v0，完整回读恢复原末尾LF后源字节/大小/SHA逐一匹配：
- qualification-plan.md：libfile_b3bd5a09e8b081919af86f8618dbb03d，17616字节，SHA b050cc54a55b13bae8539b6556c3422acc9e121016c6b2ffba688502822a6901。
- source-manifest.json：libfile_18f0ff618fc081918f6698c52a7be1d1，25917字节，SHA bd7d7e354b433e5b2824481fb1eea1784c4ee62981f20de35cc0dde5d99ffbd0。
- saved-factor-and-basic-inventory.json：libfile_e4c4c06ffe94819183f1e22b8ec76e32，32970字节，SHA 4d190301d9eabdb3b31ec43a3945639d1532cc4624fd92786a0e6c439e777ef2。
- official-local-scope-inventory.json：libfile_b6a0c2f980a08191adfce397af0f3241，38210字节，SHA dc7e14e25bc68520220b64967680a5e314c1c95667974ccc7f4848e8cd0811ba。
- field-definitions-and-samples.json：libfile_3addf031aab48191b80a4d3c961d89e7，3742字节，SHA e8bc66fcdcd1f09ea1b6a5a868c32360f6009ff89c5039e9a64adc6c590b8162。
- acceptance(3).json：libfile_de47f6d41868819198e99ee60e194f3f，3175字节，SHA 393238a07de2a0df2a5f1719a1e1ebfd5ef1039f4845f494187eea3705e613dc。

总索引stock-scale-membership-cloud-handoff.json：libfile_62feafbd9014819182f68519a415cbbb v0，7520字节/SHA bac3bacacbbc41f857926e1bb6f1739ab379010df018b76d9220495493cbcbed，141行全文源字节匹配。acceptance及索引各首读暂不可见，后续同一ID完整读回成功，没有重复上传；交付元数据与逐字节证据在raw目录library-delivery.json、library-full-text-verification.json、library-index-delivery.json及library-index-full-read-verification.json。

本轮provider请求/网页源取得/价格调整计算/特征标签模型收益/主数据和registry修改均为0，无后台任务，没有执行生产取数脚本，没有购买/配置密钥/安装软件。初检rg范围过宽命中代理镜像，已从固定清单和证据中排除。B04云端独立复核仍待父线程结果，不冒称已通过。归置检查见raw/stock-price-scale-provenance-2026-10-06/repo-hygiene.log。

下一项真正操作：父线程把已有官方沪深300起点、有效公告、证券身份及权益原件绑定到本索引的精确候选对象，先核起点和两处2025临时差异；此动作不依赖34未查询键，不要求新行情。若仍缺原件，再单独冻结最小外部资料/三段预热与因子作业的来源、权限和预算。439整体周检查/月评价研究尚未取得完整资格，不换成便利股票或ETF、不做新拟合/Rank IC/回测。

## 2026-10-06 官方成员原件绑定开始（本机只读）

父线程已告知B04云端独审通过，准确小审计ID libfile_c4fffe03fc348191a58cb50a1f9665cf；本次仅记录父线程结果，不冒称重新独审云端文件。来源分区1601正常/305占位/34未查/4旧无返回、主修复0保持。授权只读本机已有原件，产出隔离1起点+12候选变更映射，优先2022-01-04起点及2025-03-10/2025-09-08；不联网、不行情、不改主pool/价格。云端另查官方公开资料，本机不重复外部搜索。精确范围已冻结在docs/research/proposals/csi300-official-member-binding-2026-10-06/inspection-scope.json；源目录32份全文核指数身份，既有冻结成员表核候选增删，官方日期/名单缺证留null。

## 2026-10-06 本机官方成员对象映射交付完成

独立读回正式期1,085日期/325,500行/每日300候选/439代码，初始300名单与12处完整候选增删均存object-mapping.json；原成员SHA a45d53bf4e445438f534bd2019ec30ecd911f6bfb09272a9c663c7e01026bc30未变。完整读25HTML及7PDF的35页，共5,706,828字节，32原件hash与前次一致；46份限定来源读前读后及Library收尾核准不变。32文件均属深圳/创业板/其他国证指数，13对象没有本次范围内合格沪深300官方原件。逐对象官方URL/hash/公告时间/生效时间/官方名单和增删均null；不从标题或候选日期推官方日期，不以历史vendor arrival未知否定所有回溯。范围不包含云端并行来源，不能声称全局缺失。

优先对象为anchor-2022-01-04、change-2025-03-10（候选601058加入/600837移出）、change-2025-09-08（候选601298加入/601989移出）。最小需求为官方完整起点或此前起点加中间全部变更、两处官方临时公告和实际增删附件；其余十对象及未探测到的常规/临时/身份事件仍须用正式期完整官方目录与另一个完整锚核对。13对象不等于只需13文件，不强迫官方日期或集合迁就候选；官方差异需采用明确来源/合同修订后才改变范围。

首轮全文数字扫描去空格使“深证1000”和“300842”拼出假000300，写输出前停止，binding.log留痕；检查实际PDF定位后改独立六位代码匹配，binding-corrected.log程序退出0。初始PDF标题抽取碰到空白行，交付前仅修正本任务隔离audit标题字段并对齐脚本，原件和资格结论不改；failure-and-resolution.json保留失败原因。已安装pypdf替代缺失pdftotext，不安装软件。Arrow只读CPU探测权限提示保留，实际数据读回与核对已完成。

4份Library均v0，6页全文恢复分页/末尾LF后字节/大小/SHA一致，身份元数据写回：
- object-mapping.json：libfile_1a431e9c17808191911fbdecf8ff1ec0，43531字节/SHA 9e8c6fab10e8e0485e9f727bc8a071a8868f9cf52744c6d4f48b06e3aadfc261。
- local-originals-audit.json：libfile_af45d7bbda888191bdb5a3a69607bc89，59712字节/SHA cfd36911160570a1c63b12c3305a4d2dba3412111b33f42ef0ab34ed966e383b。
- binding-result.md：libfile_71fc74d305988191af360506f6f6014f，6974字节/SHA a405d0d17a006b7418a057e19e87366d52fbb87a8047ae7057c9b18d6829fe18。
- acceptance(4).json：libfile_6217018543c481918ba0cfd4ab6ed26a，979字节/SHA 79ed96e5a392c4ec57362166fedff9074c1f37ec27b844d327a2f7af69c35008。

交付元数据和完整读回证据在raw/csi300-official-member-binding-2026-10-06/library-delivery.json与library-full-read-verification.json；验收通过仅指资料盘点/逐项映射，qualified_membership_chain=false。外部来源抓取、行情请求、主pool或主价格写入、收益计算、Git提交/推送均0，无后台任务。归置检查见同目录repo-hygiene.log。

下一项真正操作：云端将已找到的官方起点与公告/附件按对象绑定，给出精确原URL/原文件hash/公告及有效时间/完整代码。缺附件不标完成；核正式链覆盖候选之外的变化，报告和采用任何官方差异后再安排精确资料补件。此操作不要求重查34键或新拟合。

## 2026-10-06 B05最后34键离线/current预检开始，未放行查询

父线程告知B05包云端离线独审通过，授权取得准确Library libfile_f306fb92de84819182bebaea9aec8719 v0，224391字节/SHA eff67a122498242de803005bb1b9e8c3af325eda72388f46564a43e4a10b4c48，49文件；仅本机离线/current预检。绑定runner6ea4209512e2a924008c8bde677ef50bb1d74144718cb7d18fa9c02142ff36f6、profile009da4769ca4e043e8e4df18f2c43b53475b3fd3e77c60a05139cc2e6b567497、bindingc23c45675ce96d99ea8a1af855783b9ea4647528f87321c96f77eb4efece7eb3、合同445a06a79bab5b5327daaf333b5a1bf5a1f7ca5defffa02e4c5454e556b28b8a。核34baseline/15旧历史/30消费日线窗口、34键未查无重叠、唯一B05 run01不存在；B03两次+B04一次共3次消费历史保留。未来查询上限11日线+1login=12，其余字节/空间/发送间隔/超时/首错停止沿冻结包，本轮不取得网络放行、不使用旧B04proof/grant。新资料与证明仅隔离raw/b05-targeted-gap-batch-2026-10-06；零provider和主数据修改，完成后交回准确新proof待单独放行。

## 2026-10-06 B05本机预检暂停：真实磁盘不足，输入核对已交回

同一本机Mac和codex/factor-unit-research-20260915；未提交/推送。本轮仅获离线/current授权，B05提供方连接、会话和数据发送均0，无新消耗。Library包下载经准确用户授权，224391字节/SHA eff67a122498242de803005bb1b9e8c3af325eda72388f46564a43e4a10b4c48；49文件CRC、48payload清单及四个B05指纹核准。ZIP自带一层目录，原结构保留，路径为raw/b05-targeted-gap-batch-2026-10-06/package/extracted-v0/b05-final-gap-runner-reviewed-2026-10-06。README首读路径误判与诊断len(bool)错误均记录package/package-integrity.json；没有执行采集入口或修改原件。

独立比对14个受保护函数及整个AuditedSocket与已审B04源码逐字节一致。62项基础演练在首个正常合成场景被真实存储门槛拦下，退出1，没有完整通过报告；失败stderr与command-results.json保留offline-review-01。失败后没有原样重跑，没有修改测试、降低512MiB门槛或删除资料。49项B05和24项旧回应检查尚未运行，不能写通过。另独立完成不受此卡点影响的16项只读/拒绝入口，全部通过；实际已安装Python3.11.7/BaoStock0.9.3和7份客户端源大小/hash核准，preflight-only确认零网络/零runner写入，证据在offline-client-review-01。

不受卡点影响的current核对完成：34baseline、15旧历史、30实际已消耗日线窗口，5实际manifest和79份相关交接。34待查键仍全部未查，剩余/选中CSV等于旧B04延后34原件，deferred0仅表头；与1986历史唯一返回键（包含上下文）和30旧窗均无重叠。三次B03+B04旧消耗按receipt实际核回3次会话发送/20日线发送/5802接收字节。原两主源、34baseline和15旧历史读后及Library交付后重新核不变，没有额外或未知实际attempt。B05唯一目标是raw/b05-final-gap-batch-2026-10-06/run-01，仍不存在且未创建；准备root的targeted名称不改变该唯一目标。

新输入读回proof raw/b05-targeted-gap-batch-2026-10-06/current-recheck-01/current-dedup-readback.json，79930字节/SHA bad6f1eb8097d3b361a3c0c397fe3d0f702ba300b9099cfd98d6bc9c151ba50f。只提取精确B05源码四个纯函数，输入proof校验通过，实际output-root存储校验失败。proof明确offline_overall_passed=false、network_release=false、new_separate_network_release=false；不是绿色放行proof，不准直接用该hash跑采集。状态B05-current-preflight-status.json，7671字节/SHA6cde7c14aea704328c72a05f3be9c70893a31317173731b38f8954f9c7a54af3，overall_passed=false。

磁盘原失败后实际观测501981184字节，current时498745344，云端正文回读时508231680，索引收尾475394048，均低于冻结536870912字节门槛；这是实际资源卡点，不是自设预算。受阻验收项是完整离线检查及真实输出目录的存储资格。已有授权内没有删除既有数据/归档或降低要求的路径；不会擅清资料或改参数来凑通过。恢复需真实空间≥536870912字节且满足空间预留，然后在新review目录重验受影响离线项、重新current读回/核空间并生成新的proof，再待父线程单独放行。

8份Library均v0，11页全文恢复分页/末尾LF后源字节/大小/hash一致，身份元数据已写回，准确元数据和各sourcehash见current-recheck-01/library-delivery.json与library-full-read-verification.json：
- 当前输入proof libfile_ab92e992680c819188017d016ca1a475，79930字节/SHA bad6f1eb8097d3b361a3c0c397fe3d0f702ba300b9099cfd98d6bc9c151ba50f。
- 受阻状态 libfile_d5eb5c66aed081918213295dfe2675e1，7671字节/SHA 6cde7c14aea704328c72a05f3be9c70893a31317173731b38f8954f9c7a54af3。
- 纯校验结果 libfile_1c1189321f3c8191a81b0357eb750a40。
- 实装预检 libfile_6651501bc334819183621a0298a4e744。
- CLI16结果 libfile_1e638f483ec08191b6c3ea6f09b37b00。
- 原失败stderr libfile_5d2ad4c1e2dc8191b22bd1d8f02cdc95。
- 受保护源码比对 libfile_a640e1e85f0881919e313ce6f3dddabd。
- 人读状态说明 libfile_af077229a5388191906b868b30e8a757。

最小索引libfile_2fd2767bad0c8191ba44bd18d9f28cb2 v0，8295字节/SHA2610e9f69d3abde6e096c07444770ea06a97472f7e29460f7d433f039ebabbee，181行完整读回精确匹配。索引明确整体受阻、禁止将此输入proof当绿色放行证明；原失败未藏，未使用云端通过代替本机未通过。已启动的本机进程均已实际结束，无后台采集。

本次暂停只影响完整离线/空间验收；输入核对、独立只读客户端/入口、原数据不变证据与Library交接已完成。没有provider、主池/价格/registry修改、因子/标签/模型/收益运算、安装或Git操作。归置检查见current-recheck-01/repo-hygiene.log。下一项真正操作是恢复足够实际磁盘空间，再生成全必要检查通过的新current proof；旧负结果、三次消耗和本次失败保留。

## 2026-10-07 固定82股小切片已交付；B05离线复验开始

父线程明确批准全部82只固定缓存描述性pilot，2022–2024按年、截止2024-12-31、≤1MiB输入切片及Library保存，不计算因子/未来收益/Rank IC/模型。名单直接来自资格盘点全部ordinary_stock_code_candidate，没有二次抽样或根据全期成功删除股票。旧回测params.symbols重建名单已见结果，原始选样及失败遗漏未知；不证明按盈利筛选，也不证明结果前冻结，不代表全A股/历史沪深300/PIT。

raw/stock-ppo82-cloud-input-2026-10-07/stock-ppo82-frozen-close-2020-2024-v1.zip包含close.parquet/calendar.json/pool.json/manifest.json，979日×82股，42缓存缺值（正式期22、预热20），保留null/NaN及原值。写前空间3518799872字节；ZIP287207字节/SHA418893633d01d209aeecf312f1a89eaa9fe599f22b40a8a41d65e27ce7e58447。只用新浪前复权宽表价格，不用旧腾讯重建价格；原50MB宽表、资格盘点、日历读前读后hash不变，四成员本地/正式Library下载字节核准。Library libfile_c9e9423412d88191b1f6ed1cb1916931 v0，file_00000000dd4481f580706978deef07fa，包定义版本v1；xattrs已写回。传输首次误用外层回应后改为单transfer，受限网络失败后仅对已授权Library下载获自动审查批准，未重复上传，失败留在library-byte-verification.json。

设备Mac，分支codex/factor-unit-research-20260915，未提交/推送。本次所有源只读，无行情/提供方请求、账户资料、因子/目标值/统计计算。B05旧负记录保持。父线程最新明确授权：股票交接后可重做必要B05离线门槛/current proof；没有提供方查询许可。将使用新offline-review-02/current-recheck-02，重验真实空间、受影响检查与34键/旧消耗；空间恢复本身不当作完整资格通过。

## 2026-10-07 B05必要离线/current复验通过，待父线程审阅及单独查询授权

在新offline-review-02按原脚本/原阈值执行，62基础/16入口/49B05/24旧回应检查全部通过，四命令实际退出0；原离线空间失败未覆盖。包48payload指纹重新一致，原受保护函数结论适用于完全相同源码，不重做无差异审查。安装Python3.11.7/BaoStock0.9.3及7源指纹新核准，CLI零网络/零主runner写入。合成/保存回应中的测试发送不计实际提供方发送。

current-recheck-02核34baseline+15旧历史+30实际消费窗口、5实际manifest、84份相关交接；34键仍未查询，与1986旧返回唯一键及30旧窗无重叠。三次旧B03/B04消耗为3会话/20日线/5802接收字节，未新增。宽表及候选成员两主源和49资料核读后不变，唯一正式B05 run-01仍不存在。输出目录最近现有祖先真实空间2146291712字节，保留536870912字节门槛与额外预留851968字节；未删资料/改阈值。四个纯函数从准确已审runner AST提取执行，输入proof及输出根门槛通过，未执行正常runner入口。

新proof current-recheck-02/current-dedup-readback.json：83541字节/SHA5e86a3f4d68fe08132fd97c2e150409e55f2b2baba64a5e966d1eda035dc7e03；状态8651字节/SHA640403c10b46755447b1c46dc282af6659544ed58be7c8a977fb730768d5bf3e。明确本机必要检查通过、network_release=false、new_separate_network_release=false，父线程仍须审阅和单独决定；当前状态变化后重核，不使用旧受阻proof。

11成员小证据ZIP36284字节/SHA2a55527267c5f31698dce52362e1177c1041a7aa8161567e4b8053b1c3d1fd9f，Library libfile_06921ad85ad88191b8cd6d81b7b59623 v0，file_00000000a55481f59ff33ab3ed2888d4保存成功并写回身份。首个正式下载HTTP403，已保留library-download-failure.json，不重复上传，准备刷新正式下载指令核字节。本机source/manifest核验通过不冒称远端已读回。没有真实提供方连接、会话、查询、行情新下载、因子/未来收益/模型计算或Git操作。

B05 Library后续刷新正式下载票据（确实不同）成功，36284字节/ZIP hash及11成员CRC/manifest hashes全部核准，证据library-byte-verification.json。没有重复上传或额外提供方连接。Library后再次核34baseline+15history及两主源指纹不变，B05正式run-01仍不存在；归置检查退出0，全绿。上述proof是记录的检查时点快照；交接/进度写入发生在其后，真正放行前仍需核当前交接状态及实时空间，父线程审阅和单独查询许可尚未取得。

## 2026-10-07 一次B05放行前立即复核停止：已审快照之后交接记录有追加

父线程独立云审已通过B05保存证据，并明确批准且仅批准一次原冻结批次，条件是包/源/历史/交接不变、34键未查、无B05尝试、输出根不存在、空间及预留通过；任一变动停止。立即只读核48包文件、34baseline、15history、两主源、84交接及7客户端源，包/源/实际查询历史无变化，5实际manifest一致，B05无attempt、正式run-01不存在，实际空间2503778304字节高于537722880门槛加预留。

但是proof生成之后，上轮按收尾规约追加进度2628字节，并新增cloud-handoff-package.json/library-delivery.json/library-byte-verification.json三份打包与Library保存/完整读回证据。progress旧76028字节前缀SHA8471630495dafcdc2e26a94ca462737f0b3f11ee32a0089013219b524236e8c5完全一致，新78656字节SHAabf2e32a2906d002fe2ecb7b8d3188490da9be5dc0eb17f7a273c2174106350e，确认仅追加，没有改写旧结论。按此次任何交接变动即停止的明确指令，未调用提供方，未以普通交付追加自行豁免。

停止证据在current-recheck-02/immediate-release-recheck-2026-10-07.json与B05-immediate-release-stop-2026-10-07.json。本次新增正常0/占位0/已尝试无返回0/未查34，新增连接/会话/日线发送/响应字节均0；旧3会话/20日线/5802字节保留。原runner/profile/binding/contract/proof均不改，无主价格拼接或复权修复声明，无拟合/收益计算。父线程需明确解决这4项纯归档追加并允许刷新当前证明或调整放行条件；未经新依据本线程不执行查询。本段进度是停止发生后的必要接续记录，不当作在原proof中。

停止证据6成员ZIP6283字节/SHA6bfebc640d4175aaeb7b30a5b6d08cbfc1967a14e2e86170925b9f3d14b13c3a已正式保存Library libfile_ca2f5b3e5374819185b062af6c42579c v0，file_00000000037c81f5921e34b1f1303911，身份xattrs写回成功。首正式下载及随后不同刷新票据均HTTP403；没有重复上传，release-stop-library-download-failure.json保留，remote_bytes_verified=false，不冒称云端完整读回通过。云端可按正式Library路线取上述准确版本并核ZIP/成员；若仍403则属于Library下载访问阻碍，不是提供方查询授权。归置检查exit0，全绿；所有本机进程已结束，无后台查询或新实际消耗，正式B05 root仍不存在。

## 2026-10-07 刷新B05当前证明：只核归档差异，不调用提供方

父线程确认上轮正确停止，现授权逐项核最初2628字节进度追加及3份交付记录，旧正文前缀hash一致、无新请求/窗口/数据/代码修改，仅已授权导出和预检证据；纳入刷新后的交接集合。本机另外单列此前停止后2462字节进度及停止证据，防止把后来记录冒充最初4项。冻结原runner/profile/binding/contract和全部取数源/旧历史，复用有效离线证据，不重跑未变检查。

本阶段隔离输出为raw/b05-targeted-gap-batch-2026-10-06/current-recheck-03/。证明生成前完成本段进度记录并冻结全文，生成后不再改本文件。本阶段实际核验、结果和最终交接状态见精确路径current-recheck-03/proof-delivery-receipt.jsonl；只有新证明current-dedup-readback.json及该指定仅追加回执被声明为本次衍生证据，不对目录或其他交接追加宽泛放行。回执不能改源、请求窗口、名单、预算、权限，不能授予网络调用。本次仅返回新proof和可独立核对的archive-delta-review.json，未获得重新查询许可；不重试/规避403，原停止证据远端字节读回仍未验证。代码与数据不提交/推送。

## 2026-10-07 原冻结B05唯一批次执行完成：34键全部提供方占位，常规补查关闭

父线程已明确接受04刷新证明c298613f8f4bbdbc7de66892c25a99a318c74d4cb61fc68c4423266fe0f2b832及delta2b94c4188ff4581ec8720542b5042a3e8088c72278922592a6e38eb178285163、精确衍生范围，并批准一次原批次。开跑前立即只读核220源/交接hash、固定48包文件/7客户端源、5实际query manifest、34键及原30窗，原runner/profile/binding/contract四pin不变，正式输出根不存在，无B05尝试。实际空间3781185536字节及预留通过；没有为授权消息改动冻结进度/证明。默认受限环境不试跑网络，准确经用户授权的公开匿名Baostock连接获自动审批后仅执行一次；不会将工具批准泛化为第二次取数。

正式唯一输出raw/b05-final-gap-batch-2026-10-06/run-01；2026-10-07T05:32:56..05:33:18 UTC，实际程序退出0。1连接/1登录/11日线发送，0logout/0因子/0基本资料、无重试/重连；接收2742字节。实际最短日线发送间隔2.00448179198429秒，所有日线调用≤30秒。原完成消息ten文字错误按授权保持，实际原合同/计数/请求全是11，不据文案改代码或数量。新增34键正常0/提供方status0占位34/成功查询无返回0/未查0；没有正常行情补入。旧三次B03/B04消耗3会话/20日线/5802字节保留；加本次累计4会话/31日线/8544字节。旧失败和封存结果保留，此次授权已消耗，输出根存在，禁止自动续跑/补查/重试。

独立本地读回见run01-review-01/post-run-audit.json，28943字节/SHAcc47d93606c3fa5068ac581e6ff1d6c54d73e64ca0ef8b8b8d1dd6a7c32c9e7b。85原始产物1122656字节，84项文件清单hash逐个核准、50条事件链顺序/hash核准；原wire独立zlib解码=保存解码文本，原字符串行=normalized保留行，34精确exchange/code/date无遗漏。空量额原样保留；客户端空复权表头与原解码头3分别留存未填。日线尾部数字校验含义仍未确证，不能冒称全协议已校验；提供方占位不独立证明具体停牌/公司行动原因。原receipt.json238331字节/SHAd98632261d2e2750b6a91c248715fd11671328eb7e7127816585b47115312a23。原34baseline+15history及两主源、48包读后不变。无价格拼接、复权修复、拟合/因子/未来收益/Rank IC/模型计算。

Library完整证据ZIP包含85全部原件及本地审计/实际命令/立即核验/日志，共95成员，221583字节/SHAd4a9c527bd74607597be2a1bd31b1a756805c2f05e48848b7114837313293365。正式保存libfile_a5328a2767e08191aefdfa4772152bc3 v0，file_000000009fc481f5a838dfa13d72a600，xattrs身份写回成功。本地CRC及全部成员sha匹配；本轮不执行Library下载、不重试旧403，远端字节读回明确未验证。准确返回元数据见run01-review-01/library-delivery.json。进度在消耗完成后才追加，04此前是执行前快照，不再可用于另一次尝试。

设备Mac/分支codex/factor-unit-research-20260915，未提交推送。本轮常规缺口补查实际关闭，不再取数据；下一动作仅父线程独立核上述包并采用本批占位分类。结论不是复权、历史股票池或个股研究完整资格通过；主价格表与其他研究结论保持。

Library保存后再次读回ZIP221583字节/SHAd4a9c527bd74607597be2a1bd31b1a756805c2f05e48848b7114837313293365、95成员CRC/全部payload哈希与85当前原件字节一致；旧49源+两主源、四pin仍一致。归置自检通过，final-local-readback.json保留。本机收尾实际可用空间462987264字节，低于冻结536870912字节门槛；该观测在已结束批次和Library保存之后，不宣称现在可启动后续作业。没有触发或尝试任何新提供方动作，不清理资料、不降低阈值；未来新任务先重新核真实空间。本任务批次及本地归档实际完成，远端字节读回未尝试仍未验证，所有进程已经结束。


## 2026-10-07 沪深300历史成员：最小修正评估完成，完整资格仍缺原件

父线程独立验收B05已完成，原1944缺口为1601正常来源、339提供方占位、4旧无返回、0未查，主表修复0，常规补查关闭。本阶段只读核四个Library证据对象、一个候选起点、12处候选变化及原32原件hash，没有再运行提供方、行情或研究试验。负责范围仍是本机数据资格。

复用Library libfile_0713d6d13a588191be63adf77b1e8cc0 v1，全文794行/36469字节，正文SHA b9b7af39378aa620ff4c7c7a97644b5cd5020c7a9f5f42c19fee81b0b0cb92e7。主控核15增15删与2023-03-20候选集合一致；28对名称—候选代码关联与2022-01-17集合一致，2022-01-04起点28旧在/28新缺。前者有转载代码截图，后者尚无直接官方56代码表，不扩大为其余272位置已正确。报道生效分别为2021-12-10及2022-12-09收盘后；原候选日期不能直接叫官方生效日期。

Luna（gpt-6-luna，低思考，无回退）只读独立核候选表：2022-01-04..01-14有9日期、2022-12-12..2023-03-17有64日期，各自仍为旧版本且每日300。32份原件5706828字节/hash全部不变，复用原不符合沪深300结论，不重读全文、不推广为全库无材料。主控检查生成器每20交易日探测，仅凭端点及第一次变化不能证明事件穷尽，审计JSON未保存原始成员回应/updateDate。

交付目录docs/research/proposals/csi300-membership-repair-qualification-2026-10-07：README.md（13825字节/SHA 42643faec26ed074a84c6a9c210bbcd740d4d95dce7ed514f218bab678930faa）、evidence-manifest.json（12595字节/SHA 52b99e7c6e80d9255f190ef9ed1c27b0132dfb1f8fa830e3dd04971c803e812e）及来源正文副本。首次正文写入多1末尾LF的大小失败已保留说明，仅修新副本，原源不变。

云端交接文件csi300-membership-qualification-2026-10-07-v1.json：27717字节/SHA 96fd847b21eda6b28c3c90e4c13fc102ffaa59fc5152d0ba0eeb893cf030aae3。Library libfile_1fb300ebd7348191920a47004486b6a1，创建版本0，file_00000000e898822fa4132839eece435e；本地身份已写回。Library正文328行完整读回，按本地原文件恢复唯一末尾LF后大小/全文hash完全一致；这是正文读回，不声称另做签名文件下载验证。详细回执library-delivery.json。

下一项真正操作是取得中证2022-01-04有效完整300代码名单，或2021-12-13完整名单加至01-04全部衔接事件；更早名单方案还需2021-11-26公告的完整56代码附件。尚无已验证官方原始URL，保留缺失。可并行核2022年30代码官方附件及2025两处临时完整替换关系；候选12差异不当完整目录。若仅取得较晚完整起点，可交真正可证实的有限时段，不能用今天名单回填冒充全期。原82固定缓存描述性探索按其另行授权独立推进，不替代历史成员目标，本机未启动它。

本阶段写前均核空间超过536870912字节，新增文档和辅助文件合计小于1MiB；本轮收尾写前实际空间4098314240字节。7个精确本地来源读后大小/hash不变；目录归置检查exit0全绿。无主数据/registry/技术内容修改，无新因子/标签/模型/收益计算，无提交推送；Mac，沿codex/factor-unit-research-20260915。评估方案完成，历史全期资格未通过，不能据本文件发布修复后的成员表。


## 2026-10-07 起点公开资料取得：官方28对代码已补齐，完整历史300名单仍缺

父线程新增授权：继续取得2022-01-04有效官方完整300股名单，或2021-12-13完整名单加全部衔接变更；公开只读检索/小附件总计10MiB，写前空间至少512MiB，无行情/B05/因子试验/成员修改。初始空闲3966742528字节；本轮36次公开HTTP读取成功，实际3996739字节（约3.81MiB）。首次默认环境DNS解析失败后，公开HTTPS按明确用户授权获自动审批，随后成功；未遇401/403/429，无登录、FTP连接或规避防爬。公开站点脚本仅作路由文本读取，未执行。

新证据：中证官方公告13888（2021-11-26）正文及实际链接Excel已取得；12月10日收市后生效，000300正式28增28删与旧change-2022-01-17逐项一致，15备选单列。Luna独立核正文、工作簿和候选起点，确认28旧全在、28新全缺，主控亦核关键集合。官方正文SHA f04250fc675f42e487a6091df32971ed4aa2b9b5a4ac7c5f6cc849ecca10a7a9；附件872904字节/SHA f6b9d596f3fa6072258aa1eb2c036517bf20cc74c7879eaad1069cb8e1747909。此前“仅名称关联”缺口由新官方原件解决，旧方案不覆盖，其他272成员仍未证明。附件创建/修改时间与公告、生效日期分开保留。

中证官网不加标题/指数关键词的2021-11-26..2022-01-04目录返回29条/总数29；15条调样或规则正文均读取，4份含“等指数”的宽范围附件按指数代码列检查无000300，12-10..01-04窄目录12条与其对应部分相符。这只说明当前官网目录内未发现另一次000300调整，不冒称全部历史渠道无遗漏。官网完整样本下载内部日期是20260930、300只、000300/沪深300；明确排除作2022起点。000300“拟生效历史文件”返回null；证券所属指数检索没有已见历史日期输入。Sol检查交易所实际公告导航，web工具历史分页不可读，未声称交易所全库穷尽。搜索工具多次把完整查询泛化为末词/日期数字，作为工具限制保留，没有据此断言不存在。

取得中证数据文件服务规范V4.5.4（490050字节/SHA 5eed1d83aef3a3158f86bce9c454a4db2728f89a228f375ea451f6465c5d3f7e），已定位正式样本目录、000300服务目录及日期/成员字段。规范不证明2022档案可得或已有权限。下一具体动作：按官网数据商务支持csicslt@csindex.com.cn索取2022-01-04开市有效300成员的代码/名称/交易所/有效日期，或Dec13完整名单加全部衔接；只要成员字段，不要价格。完整未发送请求稿、费用/访问/云端保存许可待确认项已备在报告。本轮只读授权不包含发信/订购，未发送或付款；用户如已有合法原件，可直接核验。多年正式链逆推是另一路线，本轮未替代用户指定历史起点而启动。

交付：proposals/csi300-membership-repair-qualification-2026-10-07/acquisition-result.md（9854字节/SHA 3274bb2565f510ae826f600855a056a08998f6556668fff451f84ad39dbadaec）；raw/csi300-anchor-acquisition-2026-10-07/acquisition-manifest.json（59437字节/SHA 7e6038a6d9d79d0fb3417ee7a5926643353bb27e4b1ff4fa33d177f3625887b2）；同raw official-20211210-csi300-event.json（7141字节/SHA cd3d8af1bd1e20f5917580ad97283692e411910e5feb8ecc26fcbca9b3de81d8）。所有原始成功响应、准确URL/查询参数和失败说明均留raw；原49份取得/检查文件及7旧源在收尾hash不变。正文提取一次通配误含receipt导致KeyError data，改按准确整数ID后完成，错误留manifest，未改原件。

Library最小文本交接libfile_fac474927dc081919432797c77e1bd9f v0，file_000000008fa081f59aaf8dd35be71b3e；73398字节/SHA 1eeeeb43645b3e5413f120fb0def8f172e2fa75a2a898739a1702c41b379e2e6，1712行分两段完整读回并恢复本地末尾LF后精确相同。本地Library身份已保存；大附件未复制到云端，按原件路径/URL/hash交接，无用户账户资料。

模型：Luna低思考核官方集合、Sol中等思考核交易所路径，无回退，实际费用未知。主成员、价格、规则、registry和旧负结果均未动，无收益/标签/模型运算，无提交推送；B05保持关闭。归置检查exit0通过。收尾写前真实空闲4368506880字节。公开资料取得阶段结果可交接；受阻验收为指定历史日期的官方完整300名单，当前公开路径没有该对象，恢复需官方档案或用户合法持有原件。数据资格责任仍由本线保留，不能把已取得28对增删写成完整起点通过。


## 2026-10-07 大样本个股输入资格完成：可立即推进数千股缓存探索，不等待沪深300完整历史起点

父线程新增授权：只读现有5211列价格缓存，沿用82股周检查/20交易日间隔的输入口径；只数历史覆盖和未来端点可得性，不计算因子、未来收益、排序相关、分组或模型效果；本机仅小型桥接，输出≤10MiB，写前空间≥512MiB。预检实际空间13239873536字节，主流程写前13104857088字节。仅一个价格矩阵、固定元数据/日历/旧82输入ZIP/生成脚本及5条basic原件；没有新行情下载、提供方调用或遍历全部会话。B05继续关闭，旧负结果和主数据、registry未改。

主价源8714行×5211代码，1990-12-19..2026-08-27，49432584字节，SHA5ad045c518d0bb4394d8c8cb946d207ad9b5b1454e5a776b1a3766c62b475b04。45408654单元中16549292有效正价、28859362空格；非空NaN/无穷/零负/重复日期/重复代码列均0，无全空列。日历2019-09..2026-06的1652交易日均在价表日期轴。前期空格不当停牌或退市证据，不据未来完整程度筛股。

每个t仅用此前连续252有效正收盘加t当日有效价决定资格，t+1和t+21两个未来端点仅单列可评价计数，不删除整股。2022–2024的151周，每周3551–4758只，中位4292，4984只至少一次具备输入；645439合格股票×周，其中625720两端成熟有效、730缺端点、18989因最后4周尚未成熟。延伸2022–2026H1的228周，5114只至少一次具备输入，1003597行合格，983537可评价；新增年份为独立扩展，不冒称已包含在旧82合同内。2026H1单独年度4843只至少一次合格，不误写为5114。54个月末覆盖另列，不把20交易日目标改成自然月。

关键纠正：5543代码名单与5211价格列不是严格子集，名单独有335（均920前缀），价格独有301655/688826/688836；净差332不能叫332退市/下载失败。600705/600837/601989主表仍缺列，5条既存basic仅000425和600958两条命中价格，覆盖2/5211≈0.0384%。上市/退市历史、永久身份、停牌原因、公司行动和历史行业没有完整证明，名单和价格版本不是历史当时股票全集。允许得出的只是在此保存缓存中的价格信息探索结论，不能声称历史全A股或幸存者无偏；完整CSI链只约束选择历史沪深300为总体的独立路线。

全量资格本机12.9478秒，峰值238747648字节。首轮979日×5211价格本体40812552字节；扩展1338日本体55778544字节。128列内存压缩实际355762/482234字节，估算全量约14483405/19632198字节（仅估算，预留2倍打包空间）。最初带全表pandas元数据的70.14MB线性估计被发现重复放大固定元数据，在transfer-estimate.json保留原因并替代；没有删旧证据。仅只读压缩样本0.37秒，云端因子/模型未实测，不承诺小时数。30GiB云环境足以容纳此输入；下一步复用82股精确冻结计算源，通过正式Library分片输入、256列固定代码段计时再全量，不能用计时段选绩效好的股票。本机此次没有导出价格或运行该段。

新文件范围：docs/experiments/raw/stock-large-exploration-qualification-2026-10-07/ 的只读脚本、per-code-coverage.csv、decision-input-counts.csv、qualification-summary.json、source-manifest.json、transfer-estimate.json及小型交接/核验回执；方案docs/research/proposals/stock-large-exploration-qualification-2026-10-07/README.md，13211字节/SHAd1990600cd1a7d127d76e7e7a4f11dd30c10bfefcd24b04b24aac5441eb1f105。原策略两文实际SHA与2026-09-29已确认指纹一致，无策略原文、规则或定义改写。

最小云桥接stock-large-exploration-qualification-2026-10-07-v1.json，198831字节/SHAcd4b556ed46602f4abccb41cdd08ad3d5443540b8260e0f5d06e8b589cfb13c2，含完整报告、规则、准确5211代码、252周/月日期输入计数、字段定义和来源hash，不含价格或账户。Library libfile_300cafd131448191bf0d6dde42632942 v0，file_00000000da7881f58f4a6c922d271127；316行完整读回、恢复本地唯一末尾LF后字节/hash完全一致，身份已保存，未使用签名下载或重试403。交接完成不代表已运行大样本效果研究。

Sol中思考独立核5代码×4日期，确认[t-252,t)及截尾逻辑；Luna低思考独立核名单差集与basic命中，均无模型回退，实际费用未知。主控逐代码合計与逐周合計两范围完全一致，12原源hash及9交付hash全部读回不变，final-local-check.json保留。本阶段小产物约1.12MB（另有不足0.3MB的/tmp Library辅助与读回），写前空闲11165573120字节，低于10MiB输出上限，归置检查通过。Mac，分支codex/factor-unit-research-20260915，未提交推送；本机无后台任务。当前数据资格责任已完成本轮大样本范围交付，未来收益计算不在此次授权中。


## 2026-10-07 首轮5211列输入交接完成：Library保存成功，云端材料化核字节待父线程执行

父线程新增明确许可：首轮2022–2024全原始可用代码名册价格切片，只导出输入，不计算因子/Y/Rank IC；完整名册而非事后曾合格4984；逐日仅过去252资格，保留不合格/无标签原因；原价格和既有源码不改。新增上限40MiB含一个交付包与核验，写前≥512MiB加预留；256列只允许之后云端无Y工程计时，不在Mac执行。授权消息已实际落实，不重问继续。

预检实际空闲11140853760字节，正式冻结前10858401792字节，高于578813952字节（512MiB+40MiB预留）。一 writer 本机直接完成，没有新增agent调用。只读12已有来源、6代码/规范pin和两策略原文；20项文件在导出及Library保存后hash/大小不变。两个原策略实际hash与确认指纹相符。旧主数据、规则、registry、旧实验/负结果、B05均未改，无提供方调用。沿codex/factor-unit-research-20260915，未提交/推送。

唯一新增输入根docs/experiments/raw/stock-large-cloud-input-2026-10-07/；新export_readonly.py/verify_input.py只是隔离导出/输入核验工具，不修改现有源码。ZIP stock-5211-frozen-close-2020-2024-v1.zip共16619603字节，SHA43ebf06bfe66c79c2fb332fa287db33d49a60f23c4c3da0e4bb39ea9d23fe192，14成员；manifest18729字节/SHA01d562a656889f320384ba3176a9636a816ce3b0f72f9882bae6bc46d71b7d79。close.parquet14137323字节，daily-input-status1178403字节、weekly-evaluation-status1206267字节，其余为完整名册/共享日历及原日历原件/字段定义/缺失和资格摘要/原资格来源/只读代码。价格切片不继承全宽pandas元数据，但原field类型、所有值和Arrow空值掩码不变，未填补、调价、拼接或删列。

精确范围：全部5211原价列，979共享交易日2020-12-18..2024-12-31；253准备期交易日、726正式交易日2022-01-04..2024-12-31；151完整周决策2022-01-07..2024-12-27，36个月末只作覆盖诊断。第一周此前252交易日2020-12-24..2022-01-06，准备期足够。全部227只从未输入合格及139只切片全空的代码仍在名册和价格表，不用未来存活或可评价并集择样。每日状态表保留所有726日×5211列的当前缺值/过去252缺值原因；每周状态保留当前不合格、未来端点未成熟、成熟端点缺值原因，不存收益或因子。

5101569价格单元中4558030正有限价、543539原空格，非空NaN/无穷/零负/重复日期/重复列均0。786861股票×周中645439输入合格、141422不合格；合格中625720两个端点成熟有效、18989尚未成熟、730成熟但端点缺失。包内consumer以availability重算所有状态，与已审资格输出一致；在保存前另一次原始列读取对所有979×5211价格及空值逐列相等。内存CRC/全部成员hash、写后唯一ZIP读回一致，未另存第二份行情包，整个导出与核验实际46.307秒；不是因子或模型耗时。

核心pin：原主价5ad045c518d0bb4394d8c8cb946d207ad9b5b1454e5a776b1a3766c62b475b04；原日历aa43736b67bbcee04fc21eedf8d510b184b764adf138456c8bce93a3155eb6c1，calendar.json导出fd07bb5e42f2eb7c0aeee7cbb1d84bf73f7f2147e4e0743d0cfa03753a6d57ac；完整5211排序代码换行列表571439ecf801342e0f3f495c54f0e00a90cd4fe801159cbd63d7aee0bb6b2e97；导出器8541bdacc1a79f3e8b92203da42205c0e265fa992c4e77b79388233ce591eca9；消费者1bd577caeb04877587545efab8571eef8d82884b921798fd9b981ca63e8d3ffc。旧取数3f4805526e4e7792c5c197b833d9839ab6d569ec8497cc52d02bb007ca7546e3；其余准确来源与旧82/script/规范pin均在manifest及export-verification.json。

正式Library保存成功：libfile_2b6573053b4c81919b7d5fa119b568d8 v0，file_00000000dda081f5923a6762b7ed3baf，路径/stock-5211-frozen-close-2020-2024-v1.zip，返回大小16619603，本地身份xattrs保存成功。没有在Mac请求材料化/签名下载或重试403；remote_bytes_verified=false，云端官方材料化与整个ZIP外部hash核验由父线程执行，不能把保存成功写成远端字节已验。包内verify_input.py可在官方材料化后以外部expected ZIP SHA核14成员/全部代码日期/所有状态；当前父线程缩放runner审阅仍独立进行，本机无256列计时和效果计算。

当前资料缺口完整保留：543539空值不可推断停牌原因；227从未资格、139全空不删；18989尾部尚无标签及730成熟缺端点不删整股；600705/600837/601989仍缺原主列；只有2/5211既存basic匹配。名册335个920代码不在主表、主表3个代码不在名单，代码/下载时点不是同一可靠快照；上市退出和永久身份、历史行业、状态和公司行动/复权锚/原始版本时间仍不完整。只能保存缓存探索，不声称历史全A或当时真实可用价格；完整CSI300链只影响选择历史CSI300总体的另线，不挡本包。

新增可见raw产物16660241字节（最终小回执之前），本轮/tmp当前helper11084字节，另预留100000字节核验/进度，总量远低于41943040字节；收尾核空间10692395008字节。export-verification.json、library-delivery.json、final-local-check.json及execution-notes.json保留。一次ps只读过程诊断被sandbox拒绝，未提权/重试，等待后实际导出exit0；Arrow CPU探测警告不影响已通过逐列核验。归置检查exit0全绿。本机输入交接已完成且无后台任务，下一项仅父线程按上述准确Library ID/v0官方材料化核字节后采用云端输入，不在Mac继续算效果。

## 2026-10-07 中控目标4资料资格接续：本机原件核回与用途边界

设备Mac，分支codex/factor-unit-research-20260915。中控只派本线补目标4资料资格与目标8只读空间测量；独占raw/stock-data-qualification-2026-10-07，报告docs/experiments/stock-data-qualification-2026-10-07.md。原PPO/P26实验和B01—B05封存结果不重跑，主价格/成员/规则/全局登记不修改。本轮新公开来源和提供方请求0、Library下载0，原403不重试。保存scope.json记录边界、0次请求预算、新输出1MiB与写前512MiB下限。

实际独立本机核回5,211输入ZIP 16,619,603字节/SHA43ebf06bfe66c79c2fb332fa287db33d49a60f23c4c3da0e4bb39ea9d23fe192，14成员CRC和逐成员SHA均匹配，20项导出来源/代码/两策略原文的大小与原SHA全匹配；没有重复执行全部逐价格单元计算。B04原1944分类1601正常raw/305占位/34未查/4旧无返回，与B05最后34键独立分类及原回执合并得1601/339/0/4，共1944；主价格修复仍0。已取得的中证公告13888和28对附件指纹核准；明确标记2026-09-30的现行名单不能回填2022。过去36次官方公开取得已复用，不重新检索，2022-01-04完整官方300成员起点仍缺。

新增消费边界：本包前253个准备期日，第一周2022-01-07含决策日仅257日，随后三周最多272日；交接中P26要求至少277个连续收盘，故本包不能直接替代P26原输入，2022-02-11的含不含当天口径要读原合同。此检查不判断云端原实验错，也不重算P26表现。云端PPO/P26原效果包本机限定路径未找到；需中控取得原合同、计算源及数值审计原件后才独立复核，不用交接数字冒充本机验证。

输出readback.json保留原包、源指纹、分类、准备期和环境快照；报告附保存缓存用途矩阵及严格缺件，registration-fragment.json交中控串行入库。新时点本机可用约13.27GiB、外接盘约602.17GiB，只测量未搬迁。`/workspace/scratch/3b760ccd9853`本机不存在。Git原115项跟踪变更保留，未提交推送，未启动本轮后台研究。下一实行动作：中控核PPO/P26原包；历史成员线取得完整官方历史起点原件后再核成员资格；资料本线不再消耗B05或官方公开来源额度。

## 2026-10-07 中控串行窗口：三份有限报告登记完成

中控在线核协调状态并排除并发写者后，明确授予本线串行写`docs/experiments/registry.json`和`INDEX.md`三项准确报告。本机写前两文件SHA分别5c48a3c66c0c45d20f0098104a77c0e42f767c8f3a91a306cb9bc78e8b0d06f1、7b0709f4e55d631c828ed4dc67b49b1f825ed7906fdb4c7d6bf3bfa2ff7c4f6a；三份作者报告SHA均核，目录作者动态快照补注的报告SHA8e61d7ed4ca119bece1209d920479a0d5ed3d63aadcb6d45e12741f93e8fb601匹配。新增资料资格、旧证据目录和原生流程入口核验三项，均mixed并明确实际有限结论；D—MAE真实接入和效果未登记为完成。

写后registry为612条，旧609条序列化字节重建后与写前整文件SHA一致；INDEX去掉本次三条后也与写前整文件SHA一致。三报告链接各1，报告库真实扫描均非待分类，类别均在原枚举内；两文件写后SHA分别b86488672cda210d2a7107ddb693a76f15b040ae8657529891a3340b9344d860、5e266d5453bbe82dd454818008c5d640fd044dd53c21a43399c002871a925fc3。归置检查exit0，报告库4项针对性测试通过。完整逐条回执位于本任务raw/stock-data-qualification-2026-10-07/registration-receipt.json，SHA78ce939692658377e42273ac431aed3ed4144c8368e22f15cf377e53631bbf6b；只登记/导航、未改三份报告正文或定义。共享脏工作分支不提交、不推送其他人的改动。本线串行窗口已完成，可交回中控。

## 2026-10-08 本线安全成果分支交付与远端读回

接中控Git协同接续，2026-10-08先fetch远端`coordination/lei@658c13cd12e7c8807cf5030839ecdd7c2de70c19`并读取`COORDINATION.md`及总任务登记，核本线同名报告/raw范围、历史效果原件缺口和三项登记窗口已释放。共享脏工作区不切分支、不暂存任何其他改动。在仓内`.codex/worktrees/stock-data-qualification-20261008`独立工作树建立`codex/stock-data-qualification-20261008`，只复制报告及raw目录8个小文件，共53,795字节；准确文件、大小、SHA与排除的大价格ZIP/本机逐日面板见`delivery-manifest.json`。报告SHA e1f4a927df508e936734daccd778ae1f77d2088864b98ebcebe56da428b92c6c；原价格ZIP16,619,603字节和主面板49,432,584字节仅本地，不随Git交付。

初始远端main基线缺本项目当前归置检查器，尝试兼容检查报299项旧布局违规；自己的未推单提交本机改接到原任务干净基线`18e64fa632dba5dbad0e5fcae09b4ccc75f119a9`后只剩Git worktree根`.git`指针文件被检查器误判1项。主工作区实际归置检查exit0；隔离树完整8文件安全/大小/格式/暂存路径检查通过，工作树干净。未修改检查器或删失败证据，具体限制写入`remote-publication-receipt.json`。

普通推送成功，远端分支`codex/stock-data-qualification-20261008`完整commit`a6be33c2493e982451e5c5b3646c102553b43f6b`，父提交为上述18e64；ls-remote及重新fetch一致，远端8文件经`git show FETCH_HEAD:<path>`逐字节/SHA全部核回，文件树不含ZIP、parquet、数据库或其他共享改动。远端登记仅有`registration-increment.json`三条准确补丁，绑定本机串行窗口原始registry/INDEX SHA及结果SHA；本机共享登记文件后续已有别人变更，因此不能把远端分支称作完整登记簿已经同步。远端读取回执仅本机在本raw目录，SHA e7603b947bee77b1f6ce54105fe422f6a807812f094392b3e0aa1345bbabbe45；本阶段进度文件也仅本机，均未伪称已推送。已完成本线安全成果发布，待中控记录成果commit与未交数据边界；无PR、合main、生产或交易动作。

## 2026-10-08 三键价格尺度小核验开工

更正（2026-10-08T10:28+08:00）：本节原选600705三日期后来被已存中证正式调样附件证伪——600705自2021-12-10收市后调出沪深300，不能作为原指数研究样本。原选择、2次已发生查询与结果不删除、不重置预算；`gap-pilot-20261008/selection-correction.json`保存纠错。经再次核远端协调`15f3b415a742ccccd125f6fa82aed370c49af111`并按排除已知官方冲突后的同规则固定600837的2022-01-04/05/06，仍只称候选成员，因为完整历史300名单缺失。中控在同一阶段增加准确报告`docs/experiments/stock-gap-pilot-2026-10-08.md`及raw内登记候选写入范围，本线于远端`coordination/lei@962e63d6`登记并逐字节读回；全局registry/INDEX仍由中控串行处理。至此总共4/6次公开响应、153482/20971520字节；600837原价交叉来源一致且相邻日连贯，当前新浪前复权示例价已算出，但旧缓存的因子快照与锚点未证，0旧主价修补、0新因子/标签/拟合。随后只完成该三键报告与验收，不继续换候选或用余下2请求找正结果。

中控新派有界阶段`stock-data-qualification/gap-pilot-20261008`，只答旧1601个正常来源缺价键中最先3键能否在相同来源/明确调整依据下恢复旧价。开工fetch并读远端协调`1d0637cd155be175021cbeb46653f38ea242a309`、COORDINATION及中控/本负责人记录；Git协调者随后在中央摘要登记准确嵌套raw路径，本负责人在原`risk-shape-information.md`追加本阶段范围并普通推`coordination/lei@a19be55717bc3e6a6634bb7be50d2671b82850cd`，从远端fetch读回本文件完整SHA一致。只写嵌套`docs/experiments/raw/stock-data-qualification-2026-10-07/gap-pilot-20261008/`与本进度，原报告、主价、冻结输入和全局登记只读，不同负责人不写同一文件。

本阶段预算新资料请求≤6，新增接收≤20MiB，旧B01—B05次数及失败保持原回执；首检真实空闲约4.54GiB，高于512MiB加20MiB预留。已按正式2022研究日期、缺列、正常未修复与代码/日期排序锁前三键为600705的2022-01-04/01-05/01-06。B01原名义收盘分别4.0000/3.9500/3.9600，与前后同源相邻preclose字符串四处精确一致，原因子窗口零行；旧前复权主面板没有600705列。`scope.json`与`saved-observations.json`保存精确原响应/主表/候选成员指纹及选择依据。当前新请求0/6、新取得0/20MiB、新因子/标签/拟合0；下一项只在缺原新浪调整证据的范围内查询，取得后逐键判补价资格，不扩大到其他股票或日期。

### 2026-10-08 三键小核验完成（旧开工选择以本节更正为准）

本线实际完成已纠正的固定600837三键，不再滚动换候选。B02原始收盘12.3300／12.3000／12.2000与本轮新浪原始日线逐日相等；保存B02的1月5—7日相邻收盘/前收盘三处精确衔接。本轮新浪调整表对应系数1.0697753579432000，按当前已装AKShare口径得到当下参考前复权11.53／11.50／11.40；原旧主面板600837整列缺失，旧系数快照/锚点及公司行动独立依据不完整，故三键旧价可恢复数0。官方完整沪深300历史起点仍缺，不能把“没有被已知28对调出证据排除”写成正式成员认证。报告`docs/experiments/stock-gap-pilot-2026-10-08.md`和同题raw的`comparison-v2.json`、`receipt.json`、四份新增公开响应、选择纠错均保存；报告SHA `1fd356715d44bc60dae99837730aa67a33fe225b0a01c05309f585284dad39c4`，receipt SHA `4c0e360e1e929f38dfba919aabdf54466b18787c563897cb5b44e647c544e1ba`。登记候选只写raw，registry/INDEX交中控串行。

同一预算累计4/6请求、153482/20971520应用解码字节，剩余2次未消耗；0新因子/标签/拟合、0主价/生产/账户改动。报告与18份raw产物本地逐字节核回，既有官方附件/B02原件/旧主价格SHA保持不变；归置检查通过。收尾磁盘空闲4209090560字节，大于512MiB+20MiB。阶段资料资格判定已完成，余下缺件须另有合法原件与新明确范围才可启动主价修复或全历史成员研究；本阶段不将缺件伪称本次未完成验收。

成果分支21份准确新文件普通推送至`codex/stock-data-qualification-20261008@be1fa845843a2599a811a8c161db39cda2f718b7`，随后重新fetch并对21份逐字节读回；本进度最终这条同步说明将在后续小提交再次读回，不能把前一提交误称已含本条。交付前另读协调`1211caa3eb1b08969b22ee8e6ff248529305670b`及中控/本负责人记录；本人completed状态已普通推至`coordination/lei@60a10f7c`并远端字节读回，中央摘要由中控单独维护。本阶段结束，不使用剩余预算继续追价。
