# 非代码材料与交付缺口

## 最小材料

|材料|用途/版本|是否必要/交付|
|---|---|---|
|payload/skills 的源代码、许可、provenance|固定 arch8.0.0、tsfresh0.21.2、statsmodels 有限核心和日历|已随 Git 包；大小/哈希/source_version 见 source-snapshot|
|两份策略副本和规范|业务定义、当前规范与历史比较边界|已随 Git 包；原件逐字节匹配|
|tsfresh 4 组原结果、合同、preflight、receipt、报告及接收材料|只读归档校验与保存预测检查|在本地补充包，未交远端；个别 preflight 约5 MB，不塞普通 Git|
|归档 family ledger 原字节|核原 receipt finish 记录，预算不重置|在本地补充包，未交远端；包含同族原历史，不筛行改指纹|
|panel.json、source-manifest.json|既有四ETF行情和字段来源|在本地补充包，未交远端；panel SHA 382d82ff21cb43758bca8e596026284ba2821038a79e1b4c331135119524679b|
|原供应商 PDF/行情/名义价来源|只有完整来源重新资格审查才需要|未纳入、未移交；准确清单 source-qualification-inputs.json，总字节 70,348,971|
|原 wheel/完整 PyPI 元数据|来源核查参考，运行不依赖|无需迁移安装原 macOS wheel；固定模块+许可已交，原 wheel 1d9cb343f15e71e9cee2415bffa1e3458aeb674a538118de71f1124b6c5b755a|
|模型权重/tokenizer/索引|不适用|没有神经模型；OLS 系数位于保存结果内，不另造权重包|
|运行数据库/schema|研究工具无需数据库|系统待升级目标 okr-4f4157e2957e 只留追加稿，外部 SQLite 未读取或写入；若将来同步先核 API/schema，不能改种子冒充进度|
|日志|旧失败、验证与本次命令|限定小证据已交；不导出系统或个人运行日志|
|密钥/登录态/SSH|禁止交付|只有变量名/空模板，不继承身份|

## 本地补充包（未交远端）

位置：`docs/ops/recovery/external-quant-handoff-20261003/research-materials.tar.gz`；文件数 68；压缩字节 8,326,487；SHA256 `a6fff0b74610b91474d3f7d217b3122dd1b4412d4ca15bc64a5acbe5c74f3818`。

文件级准确路径、大小、SHA、用途、版本、是否必须、交付状态及恢复方法见 evidence/materials-inventory.json。恢复时保持每个原相对路径和字节；restore.py 同时检查压缩包与每个解出文件。此包只是任务最小研究资料，没有正在写的数据库，也没有直接复制活跃 DB。

该包仍只在 Air。尚未获明确远端存储位置，原供应商再分发许可未确认；不得因仓库私有就自动上传。接手者可先完成纯合成工具测试；读取真实旧预测前必须取得完全匹配的补充包。曾有独立 Linux 恢复包，但本次未验证其中覆盖本批最新产物或接手者可访问，不能据旧恢复报告宣布本任务资料已交。

## 数据字段与资格

panel 是 `calendar` + `bars`，每条包含 asset/date、OHLC、volume、资料状态与已知价格调整信息；完整实际结构见原 panel/source-manifest/qualification。目标、权重、列与切分均以 run-*/contract 和 preflight 原件为准；result.predictions 的 id/asset/date/y/label_end/B0/B1/B2/fold 用于相同对象日期配对。字段不能从本说明反向改旧研究。

historical_reconstruction 只表示历史重建；供应商实际到达时间和完整价格调整可知时间没有获得正式证明。不能提升为“当时真实可获得”的资格。原来源与旧结果指纹保留；不因远端新路径或新下载改写旧证据。

## 外部服务

FactorHub 需用户安全配置 FACTORHUB_API_KEY、平台账户许可和外网；原 adapter 固定 factorhub.cn/api/v1，仅五 GET。429 后停止，禁止重试风暴。内网/VPN/公司商业授权未配置或验证。没有付费查询或账户交易在本次交接执行。
