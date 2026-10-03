# 保存结果的简单对手补充核查

## 一句话结论（大白话）

候选模型的误差与原已有信息模型相同；候选模型的误差比各ETF自己的历史平均小。

在原来相同ETF和日期上，把已保存模型与各ETF自己较早、已能知道结果的历史平均比较。这里只核算误差，不重新训练模型；局部误差更小不能证明长期有效，也不改变原研究结论。

B0 是共同训练平均，B1 是原已有信息模型，B2 是原增加候选信息的模型；asset_training_mean 是每只ETF自己的成熟历史平均，每只ETF内部各条训练记录同等分量。

评价记录 82 条，ETF 2 只，日期 41 个。每只ETF总分量相同。

误差先平方再按上述分量平均（MSE）；开平方后回到原目标的百分点单位（RMSE）。

| 方法 | 平均平方误差 | 开方误差 |
|---|---:|---:|
| B0 | 13.5846114503 | 3.68573078918 |
| B1 | 6.42998444055 | 2.5357413986 |
| B2 | 6.42998444055 | 2.5357413986 |
| asset_training_mean | 13.583732988 | 3.68561161655 |

| B2的比较对手 | 对手误差减B2误差（正数较好） | 相对减少 |
|---|---:|---:|
| B0 | 7.15462700976 | 52.6671% |
| B1 | 0 | 0% |
| asset_training_mean | 7.15374854746 | 52.6641% |

只报告当前资料中的数值，不提供稳定性或因果证据，不授权交易采用。

原运行：650fe3aea0ef457b842eaece39f474bd；原结论：not_supported；资料类型：synthetic；新增拟合：0。
原结果通过既有 workflow.check_publication 核查；本文件为辅助诊断，未登记研究报告。

## 来源指纹

```json
{
  "source_sha256": {
    "contract.json": "f49c74d2ecd88d24840344924e8e7057d162083e484fa2e2a121e26978643f21",
    "preflight.json": "b1e0d3e7f57ed290d0a5e186027f15196d672c4025c437e0815c9e5cc1f34f0a",
    "result.json": "fe3c501a1f28fff23d705a3a0b113f8f6f141c1003aed0354a920fdd8ced25d3",
    "receipt.json": "4541c35b7697ee5a3a8de9705d9fcab77b5b0a0cb114ddc01a29a34edf5580ca",
    "report.md": "5df4c1351bbde6b4f97d9628b17c60c04c0940462e0b3a4e29d1a553489f0081"
  },
  "review_code_sha256": {
    "baseline_review.py": "8a75b70a4ddfa6391aeeeb4279c4ba2d15640b32c6d7a5f91bb9f39e832e0873",
    "scripts/run_factor_lab.py": "e86090adad26d87310656d5691f492c11da14e93e2a3eb7cbe6dcd7f41988bc8"
  },
  "input_sha256": "825b3ebe78cf7379d2497c2e10b3f440802b63b01c55709402101f7b1e0d56f5"
}
```
