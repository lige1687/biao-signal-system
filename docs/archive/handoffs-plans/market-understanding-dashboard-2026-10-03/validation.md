# 实际验证与限制

2026-10-03，Asia/Shanghai。基础959971e3；工作目录为任务独立worktree，未切换或清理共享Desktop检出。

## 已执行

| 检查 | 命令/动作 | 结果 |
|---|---|---|
| 图表数据边界 | `cd web && npm run test:market-dashboard` | exit0，14组合成检查；硬编码9/16市场清单、端点/单位、缺键、长度、日期、未来/null/真0、逐项日期、自然年闰日、差额及阈值身份 |
| 旧目录/观察边界 | `cd web && npm run test:market-understanding` | exit0，33项；只撤去已被用户否决布局的2个源码字符串断言，保留资料与链接边界 |
| 编译构建 | `cd web && npm run build` | exit0，749模块；仍有既存大chunk提示，未以新拆包扩项 |
| Diff | `git diff --check` | exit0 |
| 归置检查 | `python3 scripts/check_repo_hygiene.py` | exit1：旧检查器误报managed worktree的.git文件、用户要求docs/progress；与上一阶段相同2项，不冒称全绿 |
| 本地市场服务 | 三个只读GET，未强制刷新 | 全部200；rates有2项源缺失，macro/us-macro无错误；完整行情正确性/授权资格未证明 |
| 真实浏览器 | 独立5185前端连接现有8000，1280宽 | A股9卡7曲线，美股16卡16曲线；A股PE/股债收益差空卡、没有零替代；PMI50真实虚线可见 |
| 交互 | 中美切换、通胀分类、3年改1年、参考线开关、放大、Escape | 美股通胀2卡；窗口2025-08至2026-08、读数不变；隐藏线后标签改变；Escape关闭后焦点返回原放大按钮 |
| 手机 | 390×844、通胀曲线与放大图 | document.scrollWidth=innerWidth=390，无横向溢出；恢复默认viewport |
| 独立审查 | Sol只读检查model/UI/CSS/test | 未发现阻断缺陷；没有重复运行实验 |

首次读取接口耗时rates10.90s、macro5.36s、us-macro25.29s。响应正文SHA256分别为：

- rates：ed7624550bd46478a65119de7512d066a39fc70a8cb086766c2a39e37143a6f5
- macro：aa6bdf3b168037427095e0f7c4062b7ced5074a4a696fe88424d69d66e9b8314
- us-macro：66d918f75226b465ca02a9bfd3956dbed8507e8cbf1ac6f6c616c83e090eb0bb

正文未保存/未交付；这些指纹只识别该次响应，不能据此恢复行情。首次摘要误读asof而非as_of，打印null作废，不代表接口日期为空。页面没有使用顶层as_of为单项发布日期；逐项日期与单位经助手源码审查。

## 失败与修正

- 一次写入命令工作目录误设为web，重复前缀导致3次no such file，不产生目标文件；随后在准确路径写入。磁盘当时约107Mi，shell临时输入曾no space left on device；未删除资料，后续只写小文件，20:53检查约1.1Gi，原因未知。
- 首次tsc发现目标库不支持Array.at，改普通索引后通过。浏览器发现轴边界长小数、月度轴日期过长、Escape未归还焦点，分别用整洁范围边界、所属月标签和明确触发按钮修复；实际重新核过对应行为。
- 一次浏览器能力绑定变量名不存在，未改变页面；重新绑定已选浏览器后完成手机检查。

未验证：全后端恢复、跨操作系统、API服务失联的浏览器注入演练（模型错误路径有合成测试）、所有上游数值真实性与许可、首次发布时间/历史修订、线上部署或投资效果。不得把这次前端通过写成来源资格或收益有效。

独立临时目录最小恢复：复制model、zones、package与新测试到本任务证据目录下restore-local-6qopg1mu，仅链接现有node_modules；node run-market-dashboard-regression.mjs exit0，14检查通过。详见restore-smoke.json；不是干净依赖安装、整站或后台恢复。临时副本保留仅本地，不上传重复源码或依赖链接。

最后进程核对：20:55 Asia/Shanghai，自有前端PID49578/session59800仅监听127.0.0.1:5185，留给用户阅图；已有5173/8000未动。无金融研究进程。

提交前敏感形态扫描首次把旧安全回归中故意构造的example.com用户名/密码样例误报；准确排除该既有合成样例后继续，其余扫描不放宽。首次manifest未生成，后续重新生成并实际校验。
