# 03B 讨论、补测与计划链定向合入运行目录（2026-09-09）

## 一句话结论（大白话）

已把验收过的讨论依据、单标的补测和计划保存能力接进你实际使用的 `lei-signal-lab`，保留现有新工作台、价格链接、学习库和系统待升级。两个入口的计划保存与历史恢复在浏览器中通过，正式后端已重启，新接口可见，正式前端构建及页面访问通过。本轮证明工程接通，不证明任何交易收益提高。

## 1. 授权与范围

用户在总控明确“下一步向 lei-signal-lab 定向合入”后回复“开整”，据此执行。规范：交易规格v1.0、规则账本、MACD与板块边界，实验/回测原则 `experiment-backtest-principles.md` v1.0。本轮只服务证据解释和交易计划工程层，不改变入场/退出阈值，不新做收益实验，不执行真实交易、不发送通知、不使用收费模型验收。

- 开发来源：`/Users/yongbiaoli/lei-signal-sync`。
- 隔离合并树：`/Users/yongbiaoli/lei-signal-integration-20260909`，分支 `codex/03b-integration-20260909`。
- 实际目标：`/Users/yongbiaoli/Desktop/lei-signal-lab`。
- 共同基线6edce25，运行目录HEAD91c720e，多出的13个提交及已有未提交工作保留。

合入49个文件：22个后端/配置文件、8个前端文件、19个测试及必要引用材料。精确清单与前后内容摘要见 raw/deployment-manifest.json。本轮没有提交Git、清空工作区或改分支；源目录及隔离树保留，便于后续审阅。

## 2. 实际接入内容

讨论与证据：统一解析对象和意图，回答保存原问题身份、资料引用与比较窗口；回测编号随展示、冻结、继承、恢复传递；旧材料不补造缺失身份。补测任务绑定原问题、参数和输入材料，结果核验通过才作为对应问题依据。

计划：服务端给出的计划产物进入真实卡片，保存绑定原问题；重复保存返回原计划，缺失效价不能确认。非法NaN/Infinity价格返回结构化422。计划与实际基金报单仍沿用各自确认边界。

前端：在运行目录的新工作台设计内接入上述能力，保留流式回答、价格定位、资料区与既有导航。新工作台实际流式请求补入请求编号，路由识别到请求结束共用发送锁，连续操作不会重复提交。

必要只读依赖：讨论里的定投主题实际调用DCA状态/证据模块，因此连同引用账本和12份直接材料原样带入。9张引用均能读到材料哈希，适用性仍为unknown，不升级为支持任意新问题的结论。没有挂载独立DCA、mindset、research或observations新接口，没有接入这些独立新页面或计划写接口。

## 3. 验证与过程中发现的问题

| 检查 | 本轮真实结果 | 证据 |
|---|---|---|
| 证券识别与计划价格确认快测 | 20 passed | backend/fast-regression.log |
| 计划/待办/系统待升级/学习库相邻回归 | 23 passed | backend/adjacent-regression.log |
| 原03B讨论回归 | 18 passed，200.08秒 | backend-verification/regression-03b.log |
| 原R2契约首轮 | 22 passed / 1 failed，350.81秒 | backend-verification/regression-r2.log |
| 补齐依赖后独立重跑失败单例 | 1 passed，5.12秒 | backend-verification/dca-dependency-single-regression.log |
| 原固定检查 | 20/20通过 | backend-verification/ 三份 results.json |
| 前端构建、工作台、价格链接 | 通过，补齐请求编号与发送锁后再次通过 | frontend/ |
| 真实浏览器两入口 | 计划显示/保存/库内值一致、历史重开同plan_id | browser/results.json |
| 延迟识别时重复提交 | 700毫秒延迟，连续两次Enter只产生1条resolve+1条stream，CID非空 | browser/results.json |
| 运行目录构建 | 通过，736模块；仅原有大包体积提示 | runtime-web-build.log |

首轮唯一后端失败是遗漏DCA内部读状态依赖，补齐后还确认需要读取DCA路由模块中的账本路径常量，一并加入但不挂载独立路由。首轮与中间失败原样保留；准确口径为“首轮40/41，补齐依赖后失败单例通过”，不写成单次41全绿。

前端主控差异审阅发现新工作台合并遗漏流式请求编号、发送锁未覆盖解析与补测阶段，已在本轮直接修正并由实际浏览器网络请求验证。浏览器预跑也因新设计没有名为“发送”的按钮而超时，调整的是测试选择器，未用旧界面替换新设计。

本轮检查有交叉覆盖，不相加冒充独立场景总数。浏览器的目标价120是明确的控制输入，模型仅提供本地固定短解释，不是真实投资建议。后台真实回测链使用隔离行情/数据库；浏览器没有再跑完整补测任务的全部状态流程。

## 4. 数据库与实际服务落地

先以旧版本结构在临时库创建历史会话/消息，升级后原字段逐值保留，新身份缺失保持未知，完整性与幂等通过。原迁移定义未变；依赖范围实际为023—029，修正旧清单只写到027的不完整之处。

随后只读确认真实库已有029，在用户私有备份目录保全数据库，并仅对备份副本检查：新增迁移为空、必要字段存在、完整性ok、没有改业务行。检查后删除临时探测副本以回收空间，原始备份保留：

`/Users/yongbiaoli/.lei_signal_lab/backups/03b-integration-20260909-201253/lab-before.db`

因此实际代码落地没有再新增数据库迁移，没有历史观察迁入，也没有创建真实测试计划/补测任务。先合入后端并重启 `com.lei.backend`，确认接口后再合入前端；实际HTTP只读核查结果：

- OpenAPI共120个路径，新 `/api/copilot/backtest-requests` 可见；原 `/api/upgrades` 和 `/api/learning` 保留。
- `/api/upgrades`、`/api/learning`、`/api/agent/sessions` 均200。
- 5173上的 `/agent` 和实际工作台模块均200，模块含请求编号与服务端计划卡。
- 49个落地文件与隔离验收版本哈希逐一一致；清单外原有 `src/`、`web/src/`、`configs/` 文件全部保留原内容。

证据：backend-runtime-after.json、deployment-verification.json、apply-*.json、backend/real-schema-readonly-check.json。

## 5. 备份、回退与边界

双方源码初始摘要和被覆盖文件原文已保存于 raw/runtime-manifest.json、development-manifest.json 与 backup/。raw/apply_selected.py 只操作明确清单，并在每次操作前校验目标与来源哈希；如需回退，只恢复本轮文件，不用git reset/clean覆盖其他工作。数据库无需回退，不能为了代码回退盲目覆盖后续真实数据。

未覆盖：全仓全量测试、收费模型实际回答质量、实时行情新鲜度修复、完整浏览器补测状态循环、任何收益研究或自动交易。现有引用的unknown限制保留；已接通不等于所有研究依据已够用。

## 6. 台账

既有目标 `okr-bf3eb75c661f` 已记录用户“开整”的追加授权，开始阶段v30→v32。最终版本v34、状态review（待用户验收），进展快照见raw/goal-after.json；不自行标完成、不另建重复目标。

## ARCHIVE

- 归档类别：数据与质量；passed仅指本轮工程合入及所列验收成立。
- raw：`docs/experiments/raw/agent-03b-runtime-integration-2026-09-09/`。
- 总控负责后端合并、依赖裁决、迁移与备份检查、最终落地；Sol任务负责前端定向合并与独立机械回归，复用原浏览器任务完成双入口验证。没有为本轮小任务额外调用Spark。
- 定投引用材料原样迁入，保留原归档分类，不冒充本轮重新做过收益验收。
