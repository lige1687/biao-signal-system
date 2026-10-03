# FactorHub 在 Codex 中的接入与可用工具检查

日期：2026-10-02。性质：工具兼容性和小范围公开数据查询检查，未研究策略收益。

## 一句话结论（大白话）

可以在 Codex 中接入 FactorHub。已在本项目安装官方客户端，增加一个只提供五项查询的 Codex 技能和项目配置；启动、工具识别、查询限制和错误处理通过 25 项检查。FactorHub 的实际数据查询仍需要授权密钥，当前尚未完成认证；重新打开可信项目后才由 Codex 加载新增入口。另外，已有 WeStock 技能已经实际返回沪深300 ETF 三天行情，可现在用于小范围资料查询。两者都未获准替代正式交易数据或技术判定。

## 问题、基准与范围

- 用户要求：“那你看看能不能有能装 在codex里边的呗，😃，或者能用的”，随后明确“继续”。
- 基准：2026-09-23检查后未安装；既有 FactorHub API 与 MCP 资料核查留存；用户级 `westock-data` 已存在。
- 本轮问题：能否提供 Codex 可调用的限定查询接入，以及现有工具能否实际获取一个 ETF 的行情。
- 技术层定位：数据资料查询与研究对照；不改道路、路牌、触发、失效、退出、参数或因子对象。不是新技术信息因子研究，因此未启动 `run_factor_lab.py` 统计流程。
- 显式采用当前索引的研究原则 v1.2、执行合同 v1.1.0 的适用工程条款和用户级 research-closure；不迁移旧冻结合同。实际模型为本会话当前执行模型，未调用子代理或改模型。

两份桌面策略原文实际 SHA-256 与用户确认值一致：

| 来源 | SHA-256 |
|---|---|
| `~/Desktop/lei signal doc/LEI 技术交易体系.md` | `df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20` |
| `~/Desktop/lei signal doc/LEI 技术实现.md` | `85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903` |

## 核心结果及相对已有能力的变化

| 检查 | 原有状态 | 本轮结果 | 能说明什么与限制 |
|---|---|---|---|
| Codex 接入方式 | 上轮因 OpenClaw 配置与回测权限未采用 | OpenAI 官方文档明确支持本地 MCP、项目配置与工具名单 | 上轮没有充分评估 Codex 自身限制工具的能力；不能据 OpenClaw 配置认定 Codex 不适用 |
| 官方发布包 | 旧检查为 0.1.0，10个工具 | 再核 PyPI 仍为 0.1.0；校验官方 wheel 指纹并独立安装 | 不将官网宣传的38个工具当成发布包能力 |
| 查询范围 | 发布包同时包含回测 | 本地服务只列出5个 GET 查询；直接调用回测也被拒绝；Codex 配置再限定相同5项 | 不是仅靠提示词拒绝回测；未验证宿主重新加载后的实际工具展示 |
| 启动与调用 | 未验证本机运行 | 真实 MCP 标准输入输出初始化、列工具、拒绝回测、无密钥错误通过；共25项断言 | 五项真实数据转发用模拟响应核对；FactorHub真实数据调用0次 |
| 缺少密钥与限流 | 发布包异常处理存在未导入 `httpx` 的问题 | 自有适配层绕开其异常处理，明确标 `isError`；模拟429准确提示停止 | 不改写已安装供应商代码；真实服务限流行为本轮未测 |
| ETF 查询替代 | 已装WeStock技能，但本轮尚未验证 | 使用本机已缓存1.0.3，查询510300三条未复权日线，退出码0，约0.5秒 | 一个ETF、三日的小范围查询成功；不是历史价格、分红或费用资格验收 |

WeStock 本轮返回：

| 日期 | 开盘 | 收盘 | 最高 | 最低 |
|---|---:|---:|---:|---:|
| 2026-09-30 | 4.42 | 4.43 | 4.44 | 4.42 |
| 2026-09-29 | 4.40 | 4.42 | 4.43 | 4.40 |
| 2026-09-28 | 4.50 | 4.42 | 4.50 | 4.40 |

命令明确传 `--fq bfq`；上述“未复权”是请求口径，尚未与交易所或另一独立来源核对。没有解读买卖信号。成交量及金额单位本轮未单独验证，因此不据其计算结论。

## 安装与使用

项目技能：`.agents/skills/factorhub-readonly/SKILL.md`。
项目 MCP 配置：`.codex/config.toml`。
服务适配器：`.agents/skills/factorhub-readonly/scripts/server.py`。
本机独立依赖：`logs/factorhub-codex-2026-10-02/venv`（已在仓库忽略目录中）。

开放 `list_factors`、`get_factor_scores`、`get_factor_nav`、`get_index_daily`、`get_trade_dates`。
`get_factor_scores` 明确是供应商绩效摘要，不能解释为逐日逐股票评分。

项目配置适用于可信项目；当前会话不会凭文件写入自动得到新工具。重新打开本项目后由宿主加载，具体宿主工具展示待该次加载确认。当前会话也可以运行技能中的 CLI 查询入口。

密钥只从 `FACTORHUB_API_KEY` 环境变量读取。当前环境没有该变量，本轮没有搜索历史凭据、读取密钥文件或传入真实密钥。若需认证实测，用户应授权现有密钥文件位置或在宿主安全环境中配置；不要在聊天或仓库粘贴密钥。配置固定官方 HTTPS 目标，不接受供应商基础地址覆盖。

新机器恢复依赖时，在仓库内建立相同虚拟环境，使用技能中 `references/requirements.lock.txt`；发布包0.1.0及MCP 1.30.0已锁定，不把MCP未来大版本自动升级作为兼容性已验证。

## 反例、未证明部分及停止理由

1. 能启动并列出工具不代表能读取付费或需要认证的数据。本轮FactorHub未认证，未实测指数或日历响应。
2. 官网38项与发布包10项不一致仍在；五项适配查询不包含财报、分红、指数成员权重等其他宣传能力。
3. 9月14日所测ETF行情和分红为空、scores为汇总的历史证据保留；本轮不改变该数据资格判断。
4. WeStock三日行情成功不证明完整历史覆盖、公司行动、数据单位、与正式本地数据完全相同或可用于收益研究。
5. Codex工具名单依据官方文档配置；实际拒绝回测由本地服务独立执行并经过真实MCP调用检查，未依赖宿主名单的未测行为。

接入可行性和至少一种可实际查询工具的问题已经回答。进一步核FactorHub真实响应需要凭据授权，进一步核ETF历史质量是另一个数据资格问题，不扩展本轮预算或重启旧实验。

## 预算、失败与复现证据

公开资料请求上限6次，实际6次：官方文档搜索、打开、Markdown抓取，PyPI JSON首次TLS超时、使用curl重试成功、wheel下载成功。超时完整保留为失败记录；没有关闭TLS校验。包管理器的依赖下载属于一次独立安装尝试，其输出留在 `install.log`，没有将下载次数冒充数据验证次数。

3项有边界的工程检查：独立安装；MCP协议与模拟GET/错误/限制检查；已有WeStock真实单ETF查询。另做技能格式、配置解析、指纹和目录检查。均无策略统计、资金模拟、供应商回测或生产修改。

目录检查首次发现 `.codex/` 未在检查脚本白名单中。按项目允许工具配置目录的既有约束，仅将 Codex 项目配置目录加入 `ROOT_KEEP_DIRS`；其他检查规则不变，复查通过。

证据目录：`docs/experiments/raw/factorhub-codex-2026-10-02/`。

- `manifest.json`：问题、来源请求、实际指纹、测试状态与恢复边界。
- `openai-mcp.md`、`pypi.json`、`factorhub_mcp-0.1.0-py3-none-any.whl`：公开原始资料与发布包。
- `adapter-checks.json`、`verify_adapter.py`：25项核对及重放入口。
- `westock-etf.txt`：真实查询输出，空错误输出另存。
- `install.log`：独立安装日志。
- `upgrades-before.json`：读取系统待升级现状。关联现有目标 `okr-4f4157e2957e`；未重复建目标。SQLite位于仓库外，依据用户“修改仓库之外内容前确认”的新约束，本轮未回写目标进展；本报告保存待补的接入成果与缺口。

复现协议检查：

```bash
PYTHONDONTWRITEBYTECODE=1 logs/factorhub-codex-2026-10-02/venv/bin/python docs/experiments/raw/factorhub-codex-2026-10-02/verify_adapter.py
```

## 来源

- [OpenAI 官方 MCP 文档](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)：Codex项目配置、本地服务及允许/禁用工具。
- [FactorHub PyPI 发布元数据](https://pypi.org/pypi/factorhub-mcp/json)：当前发布版本与wheel指纹。
- [FactorHub 官方源码仓库](https://github.com/michaelfeng/factorhub-mcp)：定位来源；实际检查以本轮保存的发布wheel为准。
- 本机 `westock-data` 技能及已缓存 `westock-data-skillhub@1.0.3`；本轮实际执行证据见原始输出和入口指纹，不把技能自称的供应商身份当作独立审计结果。
- 历史报告：`docs/experiments/factorhub-api-reuse-review-2026-09-14.md`、`docs/experiments/factor-reuse-refresh-2026-09-22.md`。

## ARCHIVE

工程可行性研究 execution=completed，evidence=supported，completion_reason=evidence_boundary。FactorHub认证/真实数据分支=blocked（缺授权密钥）；宿主重新加载后的工具展示=not_evaluated。WeStock单ETF三日查询=supported；正式历史研究资格=not_evaluated。总体登记verdict=mixed，用户验收和系统待升级回写未完成。安装技能不授权改变策略或生产交易。
