# 美国金融条件长期序列与历史发布版本补齐

## 一句话结论（大白话）

官方长期数据和真实历史发布版本已保存到外盘：NFCI、ANFCI各有801版，共3,951,152条非空“观察日期—发布版本”记录。它们让后续研究能够检查数据修订造成的前视偏差；尚未证明能改善收益或仓位判断。

## 范围与取得结果

本项承接公开、免费、去重、外盘保存和可持续获取的授权；仅补数据，不改生产指标、阈值或交易规则。抓取日期为2026-10-26，当前数据文件版本时间为2026-10-21 12:30:04 UTC，最新观察日期为2026-10-16。抓取日期、文件版本和观察日期分别记录。

| 数据 | 本次可读覆盖 | 相对原有资料的增量 | 使用边界 |
|---|---|---|---|
| Chicago Fed当前序列 | 1971-01-08—2026-10-16，2,911个连续周五，NFCI、ANFCI、Risk、Credit、Leverage、Nonfinancial_Leverage六列 | 原系统NFCI仅五周快照；新增完整长期原件和分项 | 当前修订版本不能直接当作历史当时值 |
| ALFRED NFCI | 2011-05-25—2026-10-21的801个发布版本，1,975,576条非空记录 | 可核同一观察日期在不同发布时间所见的值 | 2011-05-25之前没有本次取得的历史发布版本；无历史盘中发布时间保证 |
| ALFRED ANFCI | 同一801个版本，1,975,576条非空记录 | 可独立研究剔除经济活动、通胀相关变化后的金融条件及其修订 | 不可用NFCI的修订历史替代ANFCI |
| 官方贡献簿 | 2,911周；NFCI为105列贡献，ANFCI为105列加Macro | 可检查哪些指标类别解释指数变化 | 是模型贡献，不能称为105条已取得的底层原始数据；加总仍有小差额 |

原件来自[芝加哥联储当前数据页](https://www.chicagofed.org/research/data/nfci/current-data)及其页面声明的数据端点；发布版本来自[ALFRED NFCI公开下载表单](https://alfred.stlouisfed.org/series/downloaddata?seid=NFCI)和[ANFCI表单](https://alfred.stlouisfed.org/series/downloaddata?seid=ANFCI)。没有使用付费接口、密钥或账户授权。

## 金融含义与增量边界

NFCI汇总美国货币、债券、权益及银行和非银行金融条件；正负值反映相对其历史基准偏紧或偏松。ANFCI进一步移除与经济活动和通胀相关的指标变化。它们可作为现有OFR全球压力、波动率等资料之外的美国金融条件解释变量；两者与现有指标是否提供独立交易信息，仍需另立有界研究检验。[官方FAQ](https://api.data.chicagofed.org/NFCI/nfci-faqs-pdf.pdf)和[技术说明](https://api.data.chicagofed.org/NFCI/nfci-technical-report-pdf.pdf)已一并留存。

这批数据最明确的增量是历史版本，而不是又多两个名称。以2026-10-15与10-21两个版本对比：共同的2,910周中，NFCI有2,642周改变，最大绝对修订0.065；ANFCI有2,862周改变，最大0.089。原系统五点与10-15版完全吻合，后来分别下修0.001、0.001、0.001、0.001、0.003。这是直接可复核的修订反例，不是信号效果。

早期发布版本从1973-01-05开始，后期版本才扩展至1971-01-08。因此“当前序列有五十多年”与“历史发布版本有十五年”必须分开。发布版本日期只提供日级边界，研究决策不得早于该版本；若需要盘中或开盘前可知性，必须另核历史发布时间。

## 验证与限制

两套压缩长表均逐行对回原ZIP里的CSV行、观察日期、发布版本和值，来源SHA、唯一键、非空数值和日期边界通过；各最新版2,911个日期和值与同一Chicago官方当前CSV全部一致。空单元格保留为缺失，没有填零。NFCI由独立agent读回，ANFCI另由root完整读回。

贡献簿与当前CSV日期全对齐，但按±0.0005显示舍入容差，NFCI有551周、ANFCI有677周未闭合，最大绝对差分别约0.002041、0.002364。官方说明没有解释这些逐周残差的精确原因，故保留差额，不强行调整。Risk、Credit、Leverage三个CSV分项也不能直接相加为NFCI。

本项共55次取源HTTP：54次200、1次500。失败是一次NFCI“全部实时区间”下载；保留失败账，改为经小样验证的逐发布版本分批下载。最初归一化误把XLSX识别为普通ZIP，在输出发布版本前断言停止；修正版另存`normalized-v2`，源原件未变。ANFCI早期receipt误列4个AppleDouble系统旁文件，v2元数据排除这些文件，数据记录和原件不受影响。

新因子运行0次，收益、超额收益和账户增量均未检验；本数据验收不授予策略上线资格。A股长队列和中证成员核验是同批其他任务，不因本项完成而宣称全二十年universe已齐。

## 复用与更新

入口为[已获取数据目录](../ops/acquired-data-catalog.md)。外盘固定UUID为`DEBA1C85-6059-3865-B50A-A8EE1F80E4D9`；大型原件、长表和source-map位于本批外盘`controller-nfci`、`controller-anfci`目录，路径与SHA见下列记录。

- [NFCI归一化记录](raw/public-universe-deep-completion-2026-10-26/controller-nfci-normalization-receipt.json)与[独立读回](raw/public-universe-deep-completion-2026-10-26/method-review-nfci/normalized-v2-independent-readback.json)
- [ANFCI归一化v2记录](raw/public-universe-deep-completion-2026-10-26/controller-anfci-normalization-receipt-v2.json)与[root独立读回](raw/public-universe-deep-completion-2026-10-26/controller-anfci-root-independent.json)
- [贡献簿检查](raw/public-universe-deep-completion-2026-10-26/method-review-nfci/method-review.json)与[方法说明](raw/public-universe-deep-completion-2026-10-26/controller-anfci-methodology-review.md)

官方按周更新；公开访问在本次实测成功，不保证未来接口不变。后续先检查磁盘身份、现有source-map与ALFRED已登记版本，只有新增版本才生成精确请求清单；现有历史版本原件保留，不被当前修订数据覆盖。当前文件通过官方页面声明的下载端点获取，按版本时间和SHA判断是否新增。没有部署定时采集器。
