# 指数价格与指标走势同图叠加：2026-10-04

## 一句话结论（大白话）

原来上下分开的图已改为同一时间轴上的两条折线：蓝线看指数价格，橙线看指标，悬停一起看原值和日期。四个指数、日/月频和390像素窄屏均已实际操作核对；用户本人是否更容易看懂仍待验收，投资收益未测量。

## 用户目标与改动

用户原话：“映射图，其实是指数价格的映射图和对应数据的映射图……能直接看出来价格走势和对应指标的关系……有点看不懂”。按最新明确要求，映射是价格与数据的同期走势，不是ETF产品对应或未来预测。原图表优先/基本面合并/参考线有依据/Agent共用事实/避开远端任务仍保留。

基线73cbd557dcf57541ba22230f1d6a6b5ba815e70b；工作task/investor-observation-map-progress，发布codex/investor-observation-map-progress-20261004，准确本轮提交见本报告Git历史及coordination/lei唯一记录。开始范围登记118db53dd9d3f8cdd5c9c1b77acd21ae2119c9d4已推并原字节读回。

- 单图共用日期轴；价格点位在左，指标原单位在右，色标/数字/提示一致。不把指数重新缩放成另一个读数，不移动曲线追求贴合。
- 默认显示两条走势；统计散点/ETF/日历折叠，数据来源与专业说明按需展开。当前选择的指标给一句“橙线怎么看”。
- 悬停给同期间指数与指标原值及各自观测日期；月度所属月不是首次发布日期。缺失保持缺失，不补零或延用上一期。
- 两侧独立缩放，曲线交点不表示买卖点。参考仍是已有定义或当前窗口历史位置，未新增未经验证的机会/风险阈值。

## 实际证据与限制

| 检查 | 结果 | 证据 |
|---|---|---|
| 价格/单位/双轴/缺失/日期边界 | 17项foundation、15项context检查exit0；仅软件检查 | 既有run-market-foundation/context-regression.mjs；[检查/失败回执](raw/market-price-indicator-overlay-2026-10-04/status.json) |
| 完整编译 | TypeScript/Vite exit0，767模块；既有大包提醒保留 | [检查/失败回执](raw/market-price-indicator-overlay-2026-10-04/status.json) |
| 实际页面→选指标→同图→悬停→来源 | 标普500746共同期；纳斯达克切换、CAPE35个月；沪深300/上证切换通过 | [实际页面回执](raw/market-price-indicator-overlay-2026-10-04/ui-check.json) |
| 悬停原值与真实API一致 | 四个值核对通过 | [真实API核对](raw/market-price-indicator-overlay-2026-10-04/live-check.json) |
| 窄屏 | 390px页面宽度390、图318，左右轴/两曲线/提示完整 | [实际页面回执](raw/market-price-indicator-overlay-2026-10-04/ui-check.json) |
| 独立目录最低恢复 | 纯绘图文件逐字相同，6项检查exit0；复用本机esbuild | [独立恢复回执](raw/market-price-indicator-overlay-2026-10-04/restore-check.json) |
| 人理解/历史因果/收益 | 未测量/未检验 | 不用工程通过代替 |

源码在web/src/features/market-understanding/IndexComparison.tsx、index-overlay-model.ts、dashboard.css、navigation.ts；相关既有回归扩五个有实际边界意义的检查。API/指标公式/策略判定/Streamlit/生产部署未改。已有指数数据与新context的来源首次公布/修订资格仍未知，不冒称预测输入已合格。

原策略实际SHA：交易体系df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20；实现85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903，与确认指纹一致。本改动只服务叙事展示层，原件不上传。

## 失败、环境与运行

Python3.11.7/AkShare1.18.49只读预览PID15449因libmini_racer原生地址池错误退出133，未改库或共享服务。改用项目已有Python3.13.12/AkShare1.18.91/FastAPI0.141.1/Uvicorn0.52.3的独立只读预览，真实context返回200并经前端单位/日期合同检查。这个环境变化不能写成旧冻结研究已经在新环境复现。旧共享API1753/8000实际加载commit仍未知，保留；新只读17186/8045、Vite15493/5185，复制文件不会迁移进程。

其他失败：旧API拼错rates/history返回404，读现有loadHistory后改正确rates-history返回200；getTab缺browser与getByLabel无匹配，读取现有浏览器/DOM后采用实际控件角色成功。构建大包提醒保留，不为消除提醒改无关打包。未杀进程/改系统代理/安装依赖/重跑金融实验。

## 原ETF核查保存点

用户本轮优先图表，原产品资料核查保存到raw/../market-etf-product-qualification-2026-10-04/：管理人HTML、3个交易所PDF仅本地，元数据含来源、取得时间、大小SHA及未交状态。510300由2023历史映射更新到2026一季报的历史映射；财务人民币口径、报告期末/送出时间和替代复制方法明确，当前完整持仓/费用仍不填。

[2026一季报](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-04-22/510300_20260422_XODY.pdf)给跟踪对象、期末行业/部分持仓及季度申购赎回份额；这些不能当作当天完整权重或每日净资金流。[2024费率变更公告](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2024-11-20/510300_20241120_FOBE.pdf)确认自2024-11-22起管理费0.15%、托管费0.05%，未证明2026最新全部费用。管理人HTML静态费率为“--”，动态脚本两条各经一次请求头修复仍连接关闭；[2026分红公告](https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-01-12/510300_20260112_VTCZ.pdf)可核财务币种和分红日期。当前资料尚未穷尽，未采购或开放外传资格。

聚宽发送方已纠正范围；撤回的新增风格页面规划未写入/实现，仅已有公开资料只读请求留累计账，不再推进本项。原ETF资料核查不是撤回项目的重开。

## ARCHIVE：版本、预算和接续

本轮冻结的是工程证据与有限来源核查，不是全部扩大计划完成。0金融回测/拟合/训练/付费/新助手/模型调用；模型费用未知。撤回分发先读6项公开来源；原ETF18项（10网页请求项+8直接HTTP，含失败）；原累计账保留。真实页面/API只读请求与缓存底层HTTP精确数量未知；工具直接核API至少7项含两个404，不计作零。

封存的情绪、技术、QQQ/VXN与三源宏观资格工作不重做；当前工作只占本轮列明的图/回归/自有文档。下一步先验收用户能否直接辨认同期升降，再恢复当前ETF法律文件/持续输入资格；缺受限/付费许可不采购，缺数不造。恢复从raw/README.md、manifest与SHA开始，只有新证据/错误/授权才重开旧结论。
