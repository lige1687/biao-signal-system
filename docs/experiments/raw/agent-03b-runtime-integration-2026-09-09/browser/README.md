# 03B 合并树真实浏览器验收（2026-09-09）

## 一句话结论（大白话）

03B 在隔离合并树的两个真实入口已接通：系统建议目标价 120 从服务端到页面、保存
请求和临时库都没有丢，刷新或从历史重开仍是同一个草稿；连续快速发送也只产生一条
请求。120 是测试用的已知控制输入，不是真实交易建议。

## 边界

- 按 `docs/research/experiment-backtest-principles.md` v1.0 执行，只给工程结论，
  不给收益或策略有效性结论。
- 生产模块实际导入根为 `/Users/yongbiaoli/lei-signal-integration-20260909/src`。
- 使用临时 SQLite、显式本地行情、本地固定短解释模型和随机本机端口 59971/59973；
  未使用真实 8000/5173，未访问外网、收费模型、真实业务库或台账。
- 除本目录脚本与证据外未改代码。十个相关生产文件运行前后哈希一致，比较退出码 0。

## 结果

- 最终退出码 0，`results.json` 为 `all_pass=true`，浏览器错误为空。
- 新 `/agent` 工作台：服务端产物显示“目标价(B)：120”，保存 POST 为 120，临时库
  API 读回 120；刷新后从“我的对话”重开，草稿编号保持
  `plan_000001_SS_20260909122454_b1f6e2f7`。
- 标的页控制台：显示、POST、临时库均为 120；到工作台从历史重开后仍显示 120，
  草稿编号保持 `plan_000001_SS_20260909122458_5dc85378`。
- 把 `/api/copilot/resolve` 人为延迟 700 毫秒后连续按两次 Enter，实际只产生 1 条
  resolve 请求和 1 条流式聊天请求；流式请求体的 `client_request_id` 是非空字符串。

## 覆盖限制

- 本轮没有运行完整回测，因此补测任务卡只记录为未启动，不能据此声称回测状态链已验。
- 标的页背景显示 `Not Found`，因为限定后端只挂载 agent、plans、copilot 与 backtest
  路由，没有挂载完整 symbols 详情路由；右侧真实 AgentConsole 已完成本轮验收。
- 目标价 120 和失效价 90 是明确标注的链路控制输入，只能证明字段传递与保存行为。

## 证据文件

- `results.json`：结构化断言与实际请求摘要。
- `run.log`、`exit-code.txt`：最终运行日志与退出码。
- `workspace-target-120.png`、`symbol-console-target-120.png`：真实 Chrome 截图。
- `source-before.sha256`、`source-after.sha256`、`source-hash-compare-exit.txt`：源码指纹。
- `git-status-before.txt`、`git-status-after.txt`：运行边界记录。
