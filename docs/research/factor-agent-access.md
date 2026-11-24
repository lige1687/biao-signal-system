# 因子研究材料通用接入手册

版本：1.0（2026-09-22）

## 这层解决什么问题

这层把已经产生的因子研究材料整理成统一的只读格式，让 Agent 能按“对象ID@版本”找到定义、旧研究说明和标准结果包。新增因子只要沿用正式定义、`ResearchBatch` 和数据目录，就不需要再给 Agent 增加该因子的专用代码。

它服务于研究说明层，不改变交易系统的道路、路牌、入场触发或过滤纪律。目录能读、结构核验通过，只说明“文件身份和格式对得上”。它不能证明因子对真实 ETF 投资有效，也不提供当前读数、生产资格、交易建议或下单授权。

## 固定入口

实现位于 `src/lei_signal/research/factor_access.py`：

- `load_access_catalog(...)`：读取纯数据目录，并从正式登记表展开所有允许用于说明的定义卡。
- `read_materials(...)`：按精确版本读取一个对象的目录材料和已核结果包。
- `read_comparison(...)`：只读取目录里已经写好的概念比较；没有记录就返回空，不临时生成实验。
- `pack_research_batch(...)`：把研究流程已经产生的 `ResearchBatch` 包成可保存的 JSON 数据。
- `validate_research_packet(...)`：重新核验保存后的结果包。

这些入口不会加载目录中的函数、模块、SQL、脚本或命令。目录出现这类字段会直接拒绝。

## 新增一个正式因子

下面用 `mixed.example.factor@1.0.0` 说明完整流程。例子里的研究计算必须由另行授权的研究任务完成；这里从已有结果开始。

### 1. 先登记准确身份

因子须先按定义规范进入 `docs/research/definitions.v1.json`，并明确允许 `description` 用途。调用者必须使用完整的 `mixed.example.factor@1.0.0`，不能用 `latest`、省略版本或把候选草案当正式对象。

加载目录后，`definitions` 会包含登记表中所有允许说明的正式定义，即使某个对象还没有材料绑定。没有绑定时，`read_materials` 仍返回完整定义卡和字段一致的空材料结构。

### 2. 由获准的研究流程产生 ResearchBatch

研究流程负责公式、数据和研究协议。本接入层只接收现成结果：

```python
from lei_signal.research.factor_access import pack_research_batch

# existing_batch 是其他已获准研究流程产生的 ResearchBatch。
packet = pack_research_batch(
    existing_batch,
    sources=[
        {
            "path": "docs/experiments/example-factor-2026-09-22.md",
            "sha256": "<该文件的64位sha256>",
        }
    ],
    calculated_at="2026-09-22T15:30:00+08:00",
)
```

不要在这段接入代码里调用 `calculate_batch`、行情接口、回测程序或 runner。现有 `factor_lab` 计算入口仍只接受合成资料；本模块没有改变它的权限。

`ResearchBatch.metadata` 必须保留定义卡、单位、协议、数据身份和状态。允许的资料身份只有两组：

| `synthetic` | `protocol.data_mode` | `data_status` | 含义 |
|---|---|---|---|
| `true` | `synthetic` | `synthetic_input` | 合成人工资料 |
| `false` | `historical_reconstruction` | `historical_reconstruction` | 已有历史结果的导入格式 |

支持第二种结构不代表仓库现在已有真实历史包，也不批准产生真实结果。两种身份的 `production_authorization` 都必须是 `not_authorized`。`qualified` 不能借这条通道写入。

结果值只接受合同已有的三种表达：连续数值、0到1之间的比例、布尔状态。布尔状态可保留 `true/false`，也可保留既有结果中的明确数值 `0/1`；其他数值不会被偷偷转成真假。缺值必须写清 `missing_reason`，日期和对象代码规范化后仍不允许重复。

### 3. 保存并核验结果包

把 `packet` 作为 JSON 保存到允许的仓库目录，例如：

```text
docs/experiments/raw/example-factor-2026-09-22/research-batch.json
```

来源路径只允许位于 `docs/experiments/`、`docs/research/` 或 `tests/fixtures/`。每个路径都要写准确 SHA-256；绝对路径、`..`、越界符号链接、空来源和指纹漂移都会拒绝。`calculated_at` 必须带时区，并填写原研究结果的实际计算时间，不能改填结果包导出时间或后来查询时间。每行 `observation_date` 只是观察日期，不等于输入资料的截止时间，也不能代替历史可得时间证据。

### 4. 只改数据目录

在 `configs/factor-access.v1.json` 增加 binding：

```json
{
  "reference": "mixed.example.factor@1.0.0",
  "kind": "registered",
  "label": "示例因子",
  "aliases": ["示例因子", "示例简称"],
  "definition_notes": ["用大白话补充定义中最容易误解的地方。"],
  "sources": [
    {
      "path": "docs/experiments/example-factor-2026-09-22.md",
      "sha256": "<报告sha256>"
    }
  ],
  "evidence": [
    {
      "kind": "data_validation",
      "summary": "这份材料实际检查了什么。",
      "scope": "样本、日期和对象范围。",
      "limitations": ["没有回答什么，不能据此做什么。"],
      "sources": [
        {
          "path": "docs/experiments/example-factor-2026-09-22.md",
          "sha256": "<报告sha256>"
        }
      ]
    }
  ],
  "batches": [
    {
      "path": "docs/experiments/raw/example-factor-2026-09-22/research-batch.json",
      "sha256": "<结果包sha256>"
    }
  ]
}
```

`evidence.kind` 只能是 `calculation_check`、`data_validation`、`predictive_study`、`return_study` 或 `risk_description`。每条证据必须有摘要、范围、局限和至少一个来源。摘要要如实写研究回答了什么；计算对得上不等于因子有效。

同一个别名可以登记到多个对象或版本，目录会保留这种现实情况，Agent 必须请用户明确选择。目录不会擅自选最新版。

### 5. 做一次实际只读验收

保存目录和结果包后，用精确版本读取一次：

```python
from lei_signal.research.factor_access import load_access_catalog, read_materials

catalog = load_access_catalog()
materials = read_materials(catalog, "mixed.example.factor@1.0.0")
assert materials["reference"] == "mixed.example.factor@1.0.0"
```

这一步会重新核验来源和结果包，不会运行因子。检查返回的 `definition`、`sources_verified` 和 `batches` 是否属于同一精确版本，并确认时间字段仍是原记录，没有被导出或查询动作改写。

### 6. 可选的概念比较

如果已有报告明确比较两个或更多精确版本，可在 `comparisons` 增加纯文字记录。被比较对象可以是已有 binding，也可以是正式登记表中尚未绑定材料的定义。比较必须有非空来源和局限；没有目录记录时，Agent 不会临时计算一个比较。

## 候选草案

候选使用 `candidate:<id>@draft-<n>`，必须提供 `draft_definition`，并保持在 binding 内。候选不会进入正式 `definitions`，也不能配置 `legacy_panel` 冒充已有读数。正式登记后应新增正式精确版本，不要把候选字段原地改成生产身份。

## 消费和失败边界

读取某个 binding 时，会核验 binding、证据、结果包文件以及结果包内部来源的路径和指纹，并把去重后的完整来源链放进 `sources_verified`。其中任何一项漂移，只阻断该对象，不应把结论扩大成“全仓没有证据”。

遇到以下情况应停止并修正材料：

- 正式引用不存在、版本不完整，或定义卡与结果包不一致；
- 目录或结果包 schema 版本错误，包括用布尔值冒充数字版本；
- 资料身份组合矛盾，或试图声明 `qualified`、生产批准；
- 来源为空、越界、缺失或 SHA-256 不一致；
- 结果含无穷值、未解释缺值、错误值类型或规范化后的重复行；
- 候选被写成正式对象，或目录夹带可执行入口。

完成这些核验后，结果仍是只读研究材料。Agent 当前值消费边界保持关闭；使用者仍需另行判断研究设计、真实数据资格和因子是否对宽基或 ETF 有实际帮助。
