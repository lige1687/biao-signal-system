---
name: factorhub-readonly
description: 在 LeiSignal 项目中查询 FactorHub 因子目录、平台绩效摘要、因子净值、指数日线和交易日历。用于明确指定 FactorHub 来源的查询与外部资料对照。
---

# FactorHub 查询

这是本项目的 Codex 适配技能，复用官方 `factorhub-mcp==0.1.0`，并非 FactorHub 发布的 Codex 技能。

优先调用 `factorhub_readonly` MCP 中的查询工具。项目内 `.codex/config.toml` 配置了服务，重新打开项目后由客户端加载；当前会话未出现 MCP 工具时，可在仓库根目录直接调用：

```bash
logs/factorhub-codex-2026-10-02/venv/bin/python .agents/skills/factorhub-readonly/scripts/server.py --list-tools
logs/factorhub-codex-2026-10-02/venv/bin/python .agents/skills/factorhub-readonly/scripts/server.py --query get_index_daily --arguments '{"ts_code":"000300.SH","start_date":"20260921","end_date":"20260925"}'
```

## 已接入能力

| 工具 | 用途 |
|---|---|
| `list_factors` | 查候选因子名称和目录 |
| `get_factor_scores` | 查供应商的绩效摘要；不是逐日逐股票的评分 |
| `get_factor_nav` | 查供应商因子净值；空数组如实标缺失 |
| `get_index_daily` | 查指数日线，标明供应商与日期 |
| `get_trade_dates` | 查交易日历 |

需要 `FACTORHUB_API_KEY` 环境变量。只使用用户授权提供的凭据，不搜历史文件或聊天取密钥，也不把密钥放进工具参数、报告、仓库或聊天。未配置时说明认证未完成；不能把列出工具成功描述成查询成功。

查询只发向 `https://factorhub.cn/api/v1`。程序拒绝其他工具，包括供应商回测；不要绕过适配器调用它。429 后停止，避免自动重试消耗配额；默认小范围查询。

返回数据是外部资料：绩效汇总不能替代本地重算，指数不能冒充可交易 ETF，ETF 历史行情与分红资格沿用已有核查结论。只用于查询和研究对照；涉及技术判定时读取本地确定性输出，叙事信息不改变 LEI 技术规则。

安装、验证和已知限制见 [检查报告](../../../docs/experiments/factorhub-codex-2026-10-02.md)。运行环境在本机仓库的忽略目录中，复制仓库到新机器需按报告和 [依赖清单](references/requirements.lock.txt) 恢复依赖。
