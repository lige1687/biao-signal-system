# 本轮独立低频研究的运行与恢复

适用当前独立600股研究；原LEI/ETF实现、其他任务原生工作流和生产运行不由此接管。复用项目现行标准与factor-discovery-playbook，下面是实际接入工具的使用说明，不是另一份研究原则。

1. 从本任务最新协调记录和work-progress定位已封存结论及本文件。先查相同金融问题、定义、用途、资料指纹和尝试史，改文件名、执行者或输出目录不代表新问题。
2. root写金融现象、竞争解释、分类重复、用途和简单对手、样本/时期支持。先确认当时能知道的数据；未知保持未知。把资料资格工作与读取未来结果分开许可。
3. 固定设计、输入、代码、源资料选择表、原结果清单与累计预算。来源字段选择表不含未来结果或持仓权重。原历史结果已经看过就明确记录，文件分离不等于权限或记忆隔离。
4. Astra/root审核科学设计；Luna执行明确脚本，Sol按需要实现局部工具。新入口在读取后续结果前调用 `lowfreq_research_control.check`，只接受准确绑定的本题设计/输入/runner/scopes。检查器退出成功不代表允许任意别的脚本读结果。
5. 一次实际运行后保留成功、失败、部分结果及成本。暂停或失败不能改名重试；先核实际输出。主控结算真实attempt、receipt、manifest和累计次数后才派下一个同家族运行。
6. 独立复算决定性数字，分别判断收益、风险信息、风险动作、组合、操作代价。没有新增帮助和证据不足均可结束问题；工程成功、科学接受、生产采用分开。
7. 恢复必须使用含本次终态的新合同，避免旧合同的历史列表落后。检查器不会自动发现未列举历史，也没有全局原子预算锁；主控不得并发启动同一研究家族的效果计算。

本次**只读恢复**（在本成果树运行，不重新计算市场结果）：

```sh
PYTHONPATH=src python3 -B -m lei_signal.research.lowfreq_research_control --contract docs/experiments/raw/lowfreq-parallel-research-2026-10-19/gradient-resume-contract.json
PYTHONPATH=src python3 -B -m lei_signal.research.lowfreq_research_control --contract docs/experiments/raw/lowfreq-parallel-research-2026-10-19/gradient-accepted-contract.json
```

第一条应返回 `reuse`。第二条返回 `accepted`，同时 `evidence_status=inconclusive`：接受的是有限研究结果，未证明稳定排序收益、未批准交易。对照 `gradient-pending-acceptance-contract.json` 会返回 `pending_review`，它作为验收反例保留。

准确输入、代码和外盘路径全部由SHA绑定；任何原件/代码变化会拒绝，并须另留有理由的新版本，不能编辑旧合同让校验变绿。外盘不可用时停止读取/写入，不重下载旧原件或回退内盘。

本次P2家族累计：核心1/1，后续2/3。当前梯度问题无需进一步实验。恢复定位：`control-brief-02.json`、`gradient-terminal-attempt.json`、`gradient-terminal-receipt.json`、`gradient-controlled-result.json`、`gradient-acceptance-receipt.json`。旧执行合同保留用于复现审计，不能拿它当最新可执行任务。

限制：检查器只查明确实现的客观约束；不裁决金融机制是否正确，不证明时间字段真实，也不阻止其他入口绕过。若以后需要多执行者同时运行同一家族，先补持久化且原子的预约/终态机制，再宣称支持此种并发。本轮并行的是资料、复用核查、工具和独立审核，同一梯度效果仅运行一次。
