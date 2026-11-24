# 实际接口与精简输出

默认本机仓库 `/Users/yongbiaoli/Desktop/lei-signal-lab`，服务 `http://127.0.0.1:8000`。脚本从自身位置定位仓库，无需当前cwd或聊天里的路径；`--repo /准确仓库` 可显式选择现有运行资料。`--base-url` 只接受带端口的本机HTTP，不接受外网、凭证或重定向。

## 选所需入口

MCP名称在客户端可能带 `mcp__lei_system__` 前缀。脚本普通视图直接调用既有 `SystemContext`，保持其资料来源与资格检查。`technical`、今日审查和基金图表补齐原MCP未提供的接口。

| 用户问题 | MCP | 脚本 view 与参数 |
| --- | --- | --- |
| 系统是否在线 | 无 | `health` |
| 我的持仓/单只基金 | `portfolio(fund_code)` | `portfolio --code 001513`；不传code查清单 |
| 自选清单 | 暂无独立工具 | `watchlist --limit 20`，用已保存名称及本地准确产品目录补中文名；仍缺则标待核对 |
| 旧扫描 | `opportunities()` | `opportunities`，只读旧扫描 |
| 今日机会审查 | 暂无同等MCP | `opportunities --generate`；随后按ID GET续查 |
| 原审查结果 | 暂无 | `opportunities --run-id orb_... --code 001513 --intent sell` |
| 网页同份产品简报 | 暂无 | `brief --run-id orb_... --symbol 515880.SS`，基金改用 `--holding-id <原ID>`；仅GET，不启动模型 |
| 准备状态 | 暂无 | `opportunities --preparation-id opr_... --wait-seconds 30` |
| 产品近期信号/图表日期 | `analysis(symbol)`含详细原资料 | `technical --symbol 515880.SS`；默认仅近期事件 |
| 基金净值/行业参考图 | 暂无 | `holding-market --holding-id <portfolio返回id>`，不强制刷新 |
| 国内/美国宏观 | `fundamentals(market, section)` | `fundamentals --market cn --section observations` |
| 利率及历史 | `fundamentals(section)` | section取 `rates` / `rates-history` |
| 美国宏观/国内历史 | `fundamentals(section)` | section取 `us-macro` / `macro-history` |
| 持仓相关消息 | `news(fund_code, limit)` | `news --code 001513 --limit 5`；无code是全局，日期可能较旧 |
| 日常条件复核 | `daily_review(slot)` | `daily-review --slot 1440` |
| 已保存日报 | `latest_brief(slot)` | `latest-brief --slot 1440`，先核资料包日期 |
| 原计划与成交 | `plans(fund_code)` / `trades()` | `plans --code 001513` / `trades`，仅读取 |
| 因子现状 | `factors()` | `factors`，不启动研究 |
| 研究证据 | `research_search(query, limit)` | `research-search --query 通信 --limit 5` |
| 报告正文 | `research_report(name)` | `research-report --name <搜索返回准确name>`，核登记SHA |
| 系统目标进度 | `overview(query, limit)` | `overview --query <目标词>`，query只筛目标 |
| 固定资源与空间 | `storage()` | `storage`，本机只读 |

`observations`才按market筛选；其他基本面section以响应范围为准。港股或其他市场不能自动借美国宏观数据代替。普通GET可能按原服务缓存期限抓公开资料；查询并非保证刚刷新。

## 输出与续查

脚本输出：`view`、`queried_at`、`result`、`output_omissions`。

- `queried_at`仅此次查询时间；判断用result中的行情/报告原日期。
- 默认列表最多6项；`--limit 1..20`可调。长正文/图表/视频片段默认不输出；省略路径均列在 `output_omissions`。
- 自选先核 `count` 和 `output_omissions`，不要把前6项当全部；`--limit 20` 可扩大范围，超过20项时用 `--full` 在本地筛选。名称附 `name_source`，补名不改变ETF、指数或板块身份。
- 今日审查保留全批 `audit_counts`、实际筛选 `matching_cards/returned_cards`、每卡原审核及按支持/反对/未知等角色分组的证据。排序沿用服务，没有另造评分或胜率。
- 产品简报与网页共用 `opportunity-brief/1`：`summary`、`directions.buy/sell`、`background`、`opposition.buy/sell`、`dates`及原技术/净值资料。技术事件和图表来自同一份返回；历史审查生成时间单列。资料已过期或身份/日期不一致时不会当成近期触发，净值和行业ETF不替代基金技术条件。
- 新闻默认不输出视频全文/ASR逐段记录。需要原文时 `--full` 后在本地筛所需条目；标题、完整正文、本机转写的证据级别不可混淆。
- `sources/errors/limitations`保留；无匹配与数据失败分别看，不能因截短而下“没有事件”结论。
- `--full`不代表资料已合格，也不会更新数据。切勿把完整私人持仓/流水上传外部搜索。

例如在任意cwd调用：

```sh
python3 /Users/yongbiaoli/Desktop/lei-signal-lab/.agents/skills/lei-system-chat/scripts/query.py technical --symbol 515880.SS
python3 /Users/yongbiaoli/Desktop/lei-signal-lab/.agents/skills/lei-system-chat/scripts/query.py fundamentals --market us --section observations --limit 10
```

## 今日审查实际端点

- GET `/api/health`
- POST `/api/opportunity-reviews/ensure`，仅正文 `{}`，可能保存本轮审查并调用当前模型。
- GET `/api/opportunity-reviews/preparations/{preparation_id}`
- GET `/api/opportunity-reviews/runs/{run_id}`
- GET `/api/opportunity-reviews/runs/{run_id}/brief?subject_key={准确产品key}`
- GET `/api/opportunity-reviews/cards/{review_id}`（单卡原件，按确切返回ID）
- GET `/api/opportunity-reviews/technical/{symbol}`
- GET `/api/opportunity-reviews/market/holdings/{holding_id}`

脚本不提供任意URL、通用POST、SQL、删改、`retry_failed=true`、模型切换或真实账本确认。

准备running：按ID有界GET；complete：转其run；failed：保留error，停止本轮自动生成。run partial保留成功/失败项，pending不能当完成。请求超时可能已执行，禁止盲目重复POST。服务端准备上限当前600秒；网络失败不是电脑离线的充分证据。HTTP402意味着该API账户余额不足；只有本次实际收到该状态才能报告，不能照搬旧聊天故障。

## 特殊用途

真实记录只走 [确认流程](confirmed-records.md)，查询不代确认。存储使用前读仓库 `docs/ops/codex-storage-management.md`；只读固定资源表返回的合格路径，保留设备核对与内容指纹验证的区别。完整原系统说明：仓库 `docs/ops/gpt-system-integration.md`，只有涉及该模块实现或确认细节时再读。
