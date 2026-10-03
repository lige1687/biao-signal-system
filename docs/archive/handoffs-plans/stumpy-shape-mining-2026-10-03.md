# STUMPY多日形态候选发现 Implementation Plan

> For agentic workers: 按当前控制者顺序执行；只读助手仅核已有入口/资料边界，接口实现、测试和结果由主控单写。本任务采用现有研究规约与执行约定。

**Goal:** 提供一个可调用的原生多日形态发现→冻结模板→历史窗口相似距离工具，从人工序列和一份资格明确的旧ETF输入实际产出最多三个候选描述。

**Architecture:** 第一方shape_mining模块只处理数据身份/日期、调用STUMPY.stump/motifs/mass、保存候选状态；不重写距离或搜索算法。发现只读指定训练截止以前的输入，模板不随应用输入更新；apply行仅用当时以前的完整窗口，缺值不跨越。模块不接生产信号或已有金融预测入口。

**Tech Stack:** Python3.11 / STUMPY1.14.1 / numba0.61.2 / llvmlite0.44.0，现有NumPy2.1.1/SciPy1.17.1。依赖仅本仓.biao隔离，不修改全局环境/pyproject。

## Global Constraints

- 用户已明确“按照计划持续推进哈，然后可以发散”，视作B推荐路线的执行授权；首次只实现候选工具，不把自动形态称为LEI作者定义或已获金融有效性。
- 固定window=20观测（不是20收益间隔），max_candidates=3，max_distance=0.5*sqrt(20)，训练截止实际输入前固定。对数收盘后，各20点窗口均值归零、标准差归一的距离；忽略波动幅度，因此输出是形状描述。几何相似阈值不叫交易阈值。
- 输入单标的、日期严格升序无重复、报价正有限或null。缺失null留行；节假日/供应商历史/复权资格由提供方声明，不能由工具推断。无需收益标签，拒绝任何未来收益字段。
- STUMPY原生默认局部排除区可能仍重叠，本包装对每组返回成员再检查至少相距20行，并避免不同候选使用相同观察范围；不足3可输出更少，不扩大阈值求满。
- 时间边界：discovery_end固定；计算比较只作用于其后，缺20点窗口/有缺值/常数窗口输出null。相似度距离不归因于买卖动作。
- 官方来源最多6次（3精确PyPI元数据+3wheel），1核心工程批+3必要后续，0市场拟合/回测/外部模型/付费。不重跑已封存任何研究。
- 当前协调规则3b3660a01f5bc126e7b0854d116fc658811aef0f已推读回；工作基础ab96cf88ea91ff7d019c9b66ebca9d617b9d090d。只本模块/测试/raw/报告/计划/两进度写入，共享workflow/总定义/CLI/生产只读。

## Task 1: 薄接口与独立边界核验

Files: src/lei_signal/research/shape_mining.py；tests/unit/test_shape_mining.py。

Interfaces: discover(input,discovery_end,window=20,max_candidates=3)->JSON library；apply_library(input,library)->JSON observations；CLI discover/apply读取JSON并写新目录，拒绝覆盖。

- [x] 核wheel SHA、BSD3许可全文及三依赖要求；no-index/no-deps装入本仓.biao；保存准确命令/退出码。
- [x] 完成边界测试（实际先写实现草稿，未声称测试先失败再实现）：未来尾部改变不影响冻结库；未来尾部改变不影响过去输出；常数/缺值/负数/重复日期边界；手工独立标准化距离与原生mass一致；非重叠重复成员；错标的/改坏库拒绝；CLI可从新目录恢复。
- [x] 实现只调用现成STUMPY的discover/apply，模板摘要和内容SHA作为恢复身份，输入只支持close/日期/资产，不接受标签。
- [x] 实际一次pytest核心工程批（0真实拟合）并保存所有失败；任何修复必要时记后续批，不能悄悄重复或扩大参数。

## Task 2: 原生端到端与真实输入候选检查

Files: docs/experiments/raw/stumpy-shape-mining-2026-10-03/{protocol.json,run_probe.py,synthetic-input.json,core-evidence.json,README.md,manifest.json,SHA256SUMS}。

- [x] 调用前写protocol，固定人工序列与训练边界、一个已有ETF/字段/源SHA（助手仅定位，不替代主控实核）；真实材料不足时只阻塞此支，不伪造源。
- [x] 必要后续批运行真实CLI：人工重复/噪声对照与已有ETF训练段只用close发现≤3候选；后段产出已固定模板的相似距离。无目标列/模型/标签/收益评价。噪声会偶然有近似模式，不能把出现候选称为有效。
- [x] 独立目录恢复小输入与已冻结人工库；核每行人工距离，不重新跑发现或旧市场实验；测试拒绝缺依赖/篡改库/覆盖原输出。Linux/Windows未实测记未验证。
- [x] 真实ETF输入、模板和逐日距离只留本地忽略目录；仅安全汇总/指纹/恢复要求上传，既有来源到达与行动时点未知则标历史描述，不给当时预测资格。

## Task 3: 结案及继续入口

Files: docs/experiments/stumpy-shape-mining-2026-10-03.md；自己的registry/INDEX项及两进度；唯一coordination同名任务。

- [x] 写大白话能力结论、实测能力表/尚未测量金融增量表、失败/预算/许可/依赖/恢复与本轮停止依据。输出candidate_status=research_unqualified。
- [x] 归置/准确diff/秘密形态/文件大小检查；独立Git索引只提交本任务路径，推task/external-quant-progress并核完整commit/16以上准确文件。
- [x] 读取最新协调后更新自己的记录，普通推且读回；不切换/清理共享脏区、不强推、不合并部署。
- [x] 下一步准备将新表达作为研究提案，明确单位、模板发现期、适用对象/方向和现有信息比较，再走现有workflow-draft/contract；本轮不跳过其资格检查。InterpretML/PySR继续候选，未安装/未认领全领域。

实际收尾：核心及3后续已用；15测试、798独立距离、独立目录应用通过。金融增量未测量。发布步骤以协调记录及远端读回回执为准；复现文件实际命名见raw README。
