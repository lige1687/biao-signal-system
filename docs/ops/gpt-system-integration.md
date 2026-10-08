# LeiSignal 接入 GPT

负责人：当前 Codex 聊天 01a11721-303e-7c83-9451-c82078c9ba23。
协调任务：daily-trading-system-audit。此接入服务于策略的执行/复盘与解释层，
不改变买卖规则。工程验收和真实交易条件分别记录。

## 完成目标与验收

用户希望在聊天里问系统事实，定时收到持仓简报，并复核原有入场理由及退出条件。
把已有资料接进一个只读入口，再核实手机、网页的实际调用，才能称完成系统接入。

| 必需结果 | 核查方法 | 当前状态 |
|---|---|---|
| 统一查询持仓、背景、新闻、计划、成交、技术与研究 | CLI 真数据、逐源日期/故障及固定反例 | 10工具真实取数通过；总览75项目标台账已读回 |
| MCP 可被标准客户端调用 | 官方 SDK 客户端 initialize、tools/list、tools/call | 本机stdio与HTTP通过；不等于ChatGPT调用 |
| 不开放交易/账户写入或规则修改 | 固定只读工具/路径、无写工具、网络约束 | 写工具/外部地址被拒；恶意Host=421、Origin=403 |
| 每日信息与下午复核可见 | 当前聊天实际任务及报告 | 09:10、11:35 已触发；14:40 待发生 |
| 手机/网页 ChatGPT 调到本机 | 实际授权后的 ChatGPT 工具调用与返回数据比对 | 未接通；登录页已打开，等待用户恢复会话 |
| 原条件可逐笔检查 | 用户确认计划、正确产品资料、条件确认方式 | 29只中0项关联计划、0项产品技术结果 |

## 统一只读入口

源码：`src/lei_signal/integrations/gpt_context.py`。
优先本机 `http://127.0.0.1:8000` 的固定 GET；新闻、成交和已生成简报读取
`data/cache/portfolio-chat-briefing/packet-*.json`，普通查询不显式要求刷新行情或新闻。
基本面现有GET会按系统缓存有效期更新公开背景资料；不能把适配器只发GET说成
后端绝不访问公开数据源。查询不把私人持仓发给这些公开数据源。

| 查询 | 证据来源 | 使用边界 |
|---|---|---|
| 总览、持仓 | portfolio/workspace、portfolio；总览另读upgrades | 旧金额不是现值；穿透只包含已披露范围；目标台账不等于跨AI协调当前状态 |
| 基本面 | observations、overview、rates、us-macro、rates-history、macro-history | 仅observations按cn/us筛选；其余返回实际市场范围；逐项保留日期、质量及错误，仅背景 |
| 新闻 | 已生成 packet、来源回执、作者配置 | 抓取缺口不等于无新闻；标题不能代表完整建议 |
| 计划 | plans、plans/summary、workspace | 只复核已确认原条件；文字未可计算就说明 |
| 成交 | packet 中的 trade_ledger | 读取缓存；系统定价不是平台成交确认；旧快照另对账 |
| 技术/因子 | workspace 已有技术、冻结 factors/panel | 研究代理不是实时买卖点；不隐式刷新 symbol 行情 |
| 研究 | experiments 目录、registry、原报告字节 | 小范围搜索；白名单正文；SHA 与登记核对 |

每个视图返回 `view, available, generated_at, data, sources, limitations, errors`。
`generated_at` 是查询时间，不替代具体数据日期。来源失败独立保留，部分资料仍可使用。
不能把可读取接口、足够交易资料和收到通知合并成一个“已接通”状态。

CLI 示例（仓库根目录运行）：

```sh
PYTHONPATH=src python3 -m lei_signal.integrations.gpt_context --view overview
PYTHONPATH=src python3 -m lei_signal.integrations.gpt_context --view portfolio --code 013403
PYTHONPATH=src python3 -m lei_signal.integrations.gpt_context --view fundamentals --section rates-history
PYTHONPATH=src python3 -m lei_signal.integrations.gpt_context --view research-search --query 宽基 --limit 5
```

自然语言流程由项目技能 `.agents/skills/lei-system-chat/SKILL.md` 引导，
可在本项目中直接用，无需写仓外配置。讨论、待确认草稿、计划、申请、平台成交与
持仓对账保持各自状态；本接入不提供生产写入或下单工具。

## MCP 本地运行

使用官方 Python MCP SDK，默认 stdio：客户端启动进程并通过标准输入/输出调用。
无界面组件，无付费模型调用。源码 `src/lei_signal/integrations/gpt_mcp.py`。
本轮隔离依赖在 `data/cache/gpt-system-integration/runtime`，不会修改系统 Python。

固定依赖见 `.agents/skills/lei-system-chat/references/mcp-requirements.txt`。
首次安装未固定 Starlette 时解析器选择1.7.0，与本机 FastAPI0.115 不兼容；
失败保留，兼容层固定0.38.6。运行时先选兼容层：

```sh
PYTHONPATH=data/cache/gpt-system-integration/runtime/compat:data/cache/gpt-system-integration/runtime:src python3 -m lei_signal.integrations.gpt_mcp --transport stdio
```

可选 `--transport streamable-http --port 8768`，只监听127.0.0.1。
stdio 对客户端已经提供私有工具；HTTP 模式不是公网发布，默认不作为后台常驻服务安装。
只有经过实际客户端调用验收的传输才标为通过。

所有工具只读，参数为基金代码、固定市场、目录内报告名、短查询与有上限的条数。
不提供通用 URL、SQL、文件路径、刷新和任意 HTTP 方法，也不提供账户写入。
诊断写到stderr；stdout保留给协议。
overview与fundamentals标注为可能访问外部公开资料，因为固定GET可触发原后台的TTL读取；
其余本地缓存/账本工具标注为本地读取。所有工具仍只读，不新增外部地址输入或私人资料外传。

本项目 `.codex/config.toml` 已登记以下服务，既有配置逐字保留；没有写用户全局配置。
`codex mcp get lei_system --json` 已读回enabled=true及启动参数。项目配置只在受信任项目加载，
当前已经运行的会话尚未动态发现新增工具，不能把配置读回说成它已实际调用。

```toml
[mcp_servers.lei_system]
command = "/opt/homebrew/bin/python3"
args = ["-m", "lei_signal.integrations.gpt_mcp", "--transport", "stdio"]
startup_timeout_sec = 30
tool_timeout_sec = 60

[mcp_servers.lei_system.env]
PYTHONPATH = "/Users/yongbiaoli/Desktop/lei-signal-lab/data/cache/gpt-system-integration/runtime/compat:/Users/yongbiaoli/Desktop/lei-signal-lab/data/cache/gpt-system-integration/runtime:/Users/yongbiaoli/Desktop/lei-signal-lab/src"
```

当前 Codex 可立即通过项目技能调用CLI，实际系统查询不依赖修改全局配置。
换机器需先按固定requirements在本仓cache安装SDK，并修正项目配置中的绝对路径；
运行中的API服务和私有资料仍是独立依赖，不会随Git成果自动迁移。

## 自然语言交易的实际边界

现有系统已实现解析确认卡和幂等写入；GPT只读连接尚未开放写工具。
不能把下列既有接口说成手机ChatGPT已经能一键记账：

1. 用户报已发生基金交易，`POST /api/copilot/trades/preview`只整理产品、方向、金额、日期与缺项，不落库。
2. 用户核对确认卡后，现有系统`POST /api/copilot/trades`才记账；同一request_id同载荷重试读回原记录，不同载荷返回409。
3. 以现有系统`GET /api/copilot/trades`即时读回。GPT的`trades`目前读已生成packet，缓存时间必须披露，不能当即时写后回执。
4. 计划先由`POST /api/plans`或`/api/plans/holding-watch`保存draft，做符合性检查，再经用户确认调用`/api/plans/{id}/confirm`，最后读回计划及版本。

尚无新的实际交易输入，本轮没有调用这些写接口。原条件、产品身份和规则版本不足时，
确认流程本身也可能拒绝；不能临时填阈值让它通过。平台成交和旧持仓对账仍分别核实。

## 手机与网页入口

两条可选路径，先核用户账户实际支持，再启用所需最小授权。

1. ChatGPT Remote 调用已连接的本机 Codex 聊天。代码和数据保持在本机，
   仍须用户在手机/网页进入该聊天并验证真实查询；官方功能说明不是本账户已连通证据。
2. ChatGPT 自定义 MCP 插件通过 Secure MCP Tunnel 连本机只读服务。
   官方隧道从本机向外建立连接，不必把本机 API 公开。需要 Platform 的 tunnel_id、
   运行凭证、相应权限，以及 ChatGPT 所属账户/工作区允许插件。此轮尚未取得或创建这些。

官方`tunnel-client v0.0.16`已下载到本仓cache，仅执行帮助检查；ZIP的SHA256与官方清单及
发布API一致。没有执行init/run/doctor，没有创建隧道或使用账户密钥。
下一次激活只需验证实际账户支持、用户在平台配置的tunnel_id和Read+Use运行凭证，
再以本仓显式配置/`--mcp.command`绑定已验收的stdio服务；不使用默认仓外配置。
账号授权及首次ChatGPT真实工具返回仍未验收，不能把客户端准备好写成已连通。

2026-10-08 11:52 浏览器实查显示“你的会话已过期，请重新登录”。未读取令牌、未创建插件，
未把持仓发送到新接口。截图在本机缓存 `chatgpt-session-expired-20261008.jpg`。
完成本地验收之后，需要用户恢复登录，并批准账户连接所需的具体权限；仅该部分依赖此输入。
不要让用户把密钥粘贴到聊天。若启用隧道，凭证由用户在平台/安全存储里管理，
配置先形成可审阅的仓内方案，仓外改动须另获确认。

官方依据（2026-10-08核读）：

- [自定义 MCP 连接](https://developers.openai.com/api/docs/guides/custom-mcp-server)
- [私有 Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
- [官方 SDK 快速开始](https://developers.openai.com/plugins/build/app-quickstart)
- [ChatGPT Remote](https://developers.openai.com/blog/mastering-codex-remote-for-engineering)
- [Codex项目配置](https://learn.chatgpt.com/docs/config-file/config-basic)
- [隧道客户端核验版本](https://github.com/openai/tunnel-client/releases/tag/v0.0.16)

## 定时与交付证据

11:35信息简报、14:40原条件复核、09:10/17:10新变化提醒、周日20:00复盘保持原安排。
只在有新事件时提醒的检查允许空正文；午间日报必须交付信息或说明具体失败。
实际读取旧材料不能称刚抓取；事件准备、观察状态和消息已发分别核对。

今天09:10任务09:11触发，09:14核查，0新事件所以安静；11:35任务11:36触发、11:39成包，
11:41准备报告后在本聊天发出。两项首次定时执行已有证据，手机通知仍未验收。
回执和含私人资料的原包留本机cache，安全的验收摘要留原审查raw目录。

## 可复核证据

`docs/experiments/raw/daily-trading-system-audit-2026-10-08/`中的
`gpt-integration-live-receipt.json`、`gpt-integration-config-receipt.json`和
`gpt-integration-fundamentals-receipt.json`分别记录真实10工具、项目配置读回、新增基本面分区。
基本面首次验收保留us-macro的8秒超时：原API首次逐序列约15秒，后续只为该路径改30秒等待，
不删除原失败。12:24缓存后的实际调用返回11项、源as_of为2026-10-06、源errors为空；
不是冷缓存30秒完成的实测。固定30/8秒选择另由假opener验证，不靠慢等做测试。
增量见`gpt-integration-increment-receipt.json`。一般来源仍8秒等待、4MiB响应上限；
不接受用户自定义刷新或远端地址。首次初始化的目标台账GET可维护存储；本轮已核既有
台账seed-ready、75项目标，只读取现有记录，未调用目标写接口。
测试、兼容层失败、首次格式检查和zsh保留变量造成的包装命令失败均保留在同目录。
新增连接25项检查通过；原日报/通知22项有效证据复用，共47项相关检查通过。
最终静态检查、技能验证和归置检查通过；一条python_multipart弃用提醒仍保留。
成果分支只提交本任务源码、测试、说明和安全回执；项目配置提交仅自身lei_system段，
不会上传本机原有未跟踪factorhub配置。既有API源码依赖指纹另记在
`gpt-integration-dependencies.json`，不把其他负责人的脏API改动混进本分支。
