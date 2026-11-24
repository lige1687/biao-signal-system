---
name: lei-system-chat
description: 直接查询本机 LeiSignal 的今日买卖机会、持仓、自选、K线信号、行业基本面、消息及研究证据；按产品名称和资料日期给出简报。用户说“接入系统信息”“看今天机会”或调用本 Skill 时使用，无需旧对话上下文。
---

# LeiSignal 系统信息

让新对话直接取得真实系统资料，先给简短结论，再按需展开。系统是规则型主观趋势交易的辅助工具；技术判定来自 Python，基本面与新闻解释背景。

## 直接调用

用户可直接说：

- `$lei-system-chat 看今天的买入和卖出机会`
- `$lei-system-chat 分析易方达信息产业混合A，结合持仓行业和反对依据`
- `$lei-system-chat 看美国宏观，说明对我关注方向的影响`
- `$lei-system-chat 查通信ETF最近触发的信号和解除条件`

只查所问内容，无需读旧聊天、历史交接或整批研究报告。没有指定问题时，给出“今日机会 / 持仓 / 市场基本面 / 消息 / 单只产品 / 计划与成交记录”菜单。

## 找到系统

- 本机服务：`http://127.0.0.1:8000`；页面：`http://127.0.0.1:5188/opportunities`。
- 仓库默认位置：`/Users/yongbiaoli/Desktop/lei-signal-lab`。本 Skill 随仓库维护；其他目录执行可用脚本绝对路径，搬机后使用实际仓库路径。
- 普通查询优先用已注册的 `lei_system` MCP 对应工具；完整路由和脚本参数见 [接口与输出](references/api-usage.md)。没有该 MCP 时直接用随 Skill 附带的脚本，不安装新平台。
- `health` 只能证明服务在线。资料是否足够、新鲜，必须看各响应中的原始日期、范围和错误。

```sh
python3 /Users/yongbiaoli/Desktop/lei-signal-lab/.agents/skills/lei-system-chat/scripts/query.py health
python3 /Users/yongbiaoli/Desktop/lei-signal-lab/.agents/skills/lei-system-chat/scripts/query.py portfolio --code 001513
python3 /Users/yongbiaoli/Desktop/lei-signal-lab/.agents/skills/lei-system-chat/scripts/query.py technical --symbol 515880.SS
```

脚本只读现有数据；唯一生成操作是明确的 `opportunities --generate`，它通过已有流程整理资料并可能调用当前配置模型。普通信息查询不授权改代码、模型、计划、成交或定时任务。

## 今日机会的完整调用

用户要求生成或查看今天审查时，执行一次：

```sh
python3 /Users/yongbiaoli/Desktop/lei-signal-lab/.agents/skills/lei-system-chat/scripts/query.py opportunities --generate
```

1. 脚本检查 health，仅 POST 一次 `/api/opportunity-reviews/ensure`，正文 `{}`。资料未变由服务复用，保留准备ID和run ID。
2. 有 `preparation_id` 就用 `opportunities --preparation-id <返回ID> --wait-seconds 30` 续查。准备 `complete` 后读取它返回的 `run_id`；不要拿准备前的旧run冒充最终结果。
3. 用 `opportunities --run-id <返回ID> --wait-seconds 30` 读审查，直到 `complete` 或 `partial`。只做GET；单轮等待不超过45秒。若达到服务600秒准备上限、状态失败或同一故障不进展，保留实际状态与恢复条件，不反复ensure/重试模型。
4. `partial` 要说明未完成哪些环节；准备失败时完整审查未生成。仍可用 `technical` 和已核公开资料回答可核部分，标明这是本次人工整理的摘要。`pending`、`not_needed` 都不代表审核成功。
5. 默认输出6张卡及全部状态计数，查看其余对象用 `--symbol`、`--code`、`--intent buy|sell` 和 `--limit`。这些只筛选输出，不缩小服务原有生成范围。只想读取已知产品时用 `technical`，无需重新生成整批。

取得run ID后，选中产品优先读取网页共用的产品简报：`brief --run-id <返回ID> --symbol 515880.SS`；基金用 `--holding-id <原持仓ID>`。该入口仅GET，返回一句话结论、双向近期事件、关键反方、背景与各自日期，同时绑定图表的技术快照。`summary.kind=facts`明确是系统事实整理，不能称作Agent已完成；背景/反方来自原审查，不能把它们称作刚重新审过当前图。读回失败时保留原因，不重新生成整批。

只读 `opportunities` 返回旧扫描候选，响应标 `saved_scan_only`；它与上述今日Agent审查分别说明。脚本没有强制重试失败项的开关。HTTP写入超时后不得盲目重复POST，应先核已返回ID或现有页面状态；拿不到回执就说明结果未知。

## 从材料到简报

- **先准确对象**：用持仓/自选中的中文名称及身份；A/C份额、ETF、指数分别处理。自选不等于持有。名称不唯一再问一次，不猜代码。
- **近期技术信号**：读 `technical` 的原事件日期、`is_recent`、状态、条件和解除条件，并看 `meta.bar_status/freshness`。已解除、失效或旧事件保留历史，不当今天新机会。盘中明确待收盘。MACD只说明均线强度，灰色表示分歧；它们单独不产生买卖结论。
- **基本面与反对依据**：行业产品匹配具体业务（通信设备关注光模块/AI硬件，不混同电信运营统计）；宽基用对应市场宏观。基金先看最新可得披露及成分日期，前十持仓覆盖有限，当前调仓未知；行业ETF只作行业参考，不替代基金自身技术条件。
- **日期与来源**：行情日、报告期、发布时间、核对时间分别保留。查询今天返回的旧资料仍是旧资料。`available=true` 不等于当日更新；无新闻不等于无风险。模型通过引用检查也不等于买卖有效。
- **需要最新信息时补证**：只搜索公开产品名和具体缺口，优先基金公司、交易所、官方公告；不要上传私人金额、账户或聊天。明确哪些来自系统，哪些是本次额外查到的；后者不会自动写回系统模型材料。
- **避免整包阅读**：先精简输出，再查具体产品/环节。保留 `output_omissions`、`sources`、`errors`、`limitations`；被截短不能当作“没有”。`--full` 仅在需要原件时使用，保存到本机小文件后筛选，不整包塞入对话。

## 用户看到的结果

第一句回答“今天关注什么”。必要时列产品卡或简表：**结论 / 支持与反对依据 / 买入与卖出关注条件 / 资料日期**。条件只用系统或用户已确认的原条件，未知直接写无法判断。偏利好/偏利空/影响不明用于有来源的背景解释，与技术触发分开。

默认产品中文名称，最多突出3—5个实际重点；不要展示旧信号总数、内部错误栈、未解释术语或令人迷惑的金融黑话（如「信贷免疫、走阔、传染、出清、高赔率、钝化、弱势底座、期限倒挂、Contango、Vol Crush、单因子、因果计算」等，一律用普通人听得懂的大白话，说不出人话就不说）。避免“不是A而是B”。原计划未记录时，先解释现有事实，保留未知，不要求用户补造历史。真实查询结果、完整Agent审查、策略有效与用户成交分别说明。

用户若明确要记交易、启用计划或更改份额，才读 [原确认流程](references/confirmed-records.md)，准确确认卡经人类确认后用原工具写入并读回。此查询Skill不提供下单功能。

## 运行边界

不因为调用Skill新增通知或日程；既有14:30机会生成是单独已授权流程，Skill不保证电脑离线时执行。其他暂停通知不恢复。服务不可用就给出所缺信息，不自动重启、装依赖、换模型、充值或修改配置。

存储查询使用现有 `storage`：只从 `available=true` 的资源 `read_path` 读取登记材料，使用前按仓库存储说明核身份；不自动迁移/删除、补下载或改链接。跨机需要本机服务和私有资料可用，仅有Skill不代表数据已移交。
