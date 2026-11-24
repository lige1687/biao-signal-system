# 周度 PPO RankIC 补充结果本机登记

更新时间：2026-10-06T13:42:16.511897+00:00。负责设备：当前 Mac 本机，唯一登记写者为本执行器。分支 `codex/factor-unit-research-20260915`，基线提交 `18e64fa632dba5dbad0e5fcae09b4ccc75f119a9`。本阶段未提交或推送。

目标：将已封存的周度 PPO 排序补充结果登记到报告库，保留原报告和原条目；随后仅只读盘点大文件候选。

## 阶段记录

- 2026-10-05：本机空间不足，取包未开始，报告、registry 和 INDEX 未写入。
- 2026-10-06：恢复 Shell 后可用空间约 6.6 GiB；核当前登记为 596 条，目标不存在。官方 Library 包 SHA 核对通过；148 文件完整解压量 26,504,141 字节，仅展开 43 文件、833,712 字节。
- 来源指纹核对：147 清单成员、60 原研究文件、6 原登记来源及冻结/放行/复核关联一致；未执行包内评价、拟合或复算脚本。
- 已写目标报告、唯一新 registry 条目（596→597）及一条 INDEX 导航；原文件和旧条目保持。归档来源见 `docs/experiments/raw/weekly-ppo-rankic-addendum-2026-10-05/registration-source.json`。
- 旧拟补丁未留在本机；根据当前内容及已核源包重新生成最小登记，实际差异证据保存在 `data/local-integration/weekly-ppo-rankic-register-20261005/registration.patch`，不冒称命中旧拟补丁指纹。

## 当前状态和下一步

已完成：登记读回、精确差异、目录规范检查和限定目录的只读候选盘点。无后台任务运行。
结果边界：原始 PPO 与模型分数分开；已有历史的回溯补充，近期仅 8/5 可计算周，无稳定模型增量证明；旧两资产改善周保留。没有真实指标新计算、训练、行情下载、src/tests 改动或交易。
验收证据：`data/local-integration/weekly-ppo-rankic-register-20261005/package-integrity.json`；最终登记检查已写入 `registration-validation.json`。
下一动作：父任务接收本机登记及只读候选清单。本轮清理未执行；科研登记无剩余阻塞，生产、提交和真实交易仍未授权。

## 验收与只读盘点收尾

登记精确差异核对通过：596→597，仅新增目标条目；既有条目无删除或变更；原报告字节不变；INDEX 只增一条导航；8 个保存总表数字核对照录，未重算；报告必需小节和本地链接可定位。目录归置检查通过。

Downloads/Desktop/Documents 顶层及桌面学业资料、归档杂项的有限目录核对未发现明显大型安装包。外交课 ZIP 9,989,738 字节，内含讲稿及演示稿，可能属于原创作业，保留。确认三个临时副本（tracked-before.json 3,866,758 字节、源 ZIP 48,649 字节、source-check.json 9,366 字节）与 data/local-integration/rank-ic-20261005 下保留件逐字节指纹一致，合计 3,924,773 字节；仅列候选，没有移动或删除。最后一次磁盘核对（2026-10-06 13:45 UTC）可用约 7.3 GiB，原始可用字节 7,801,270,272；空间变化不是本任务清理造成，本轮没有清理。

实际三文件登记差异 SHA-256：`811ce79aaf313e5937c951489259691a7c5d9aa7ee4e5a2e8c7c5b48ecdfa51e`。旧拟补丁 SHA 未在本机命中；本次来源重新核实后生成的差异与旧草稿分开记录。

注意：工作区原已有大量登记和索引改动，整份 git diff 的数量不能用作本任务变化量；本任务准确三文件差异以 registration-before 快照、registration.patch 和 registration-validation.json 为准。
