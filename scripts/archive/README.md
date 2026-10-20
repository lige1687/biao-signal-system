# scripts/archive/ — 一次性研究脚本归档

2026-09-16 目录治理时从 `scripts/` 根层迁入。这里的脚本**不再维护、不保证可运行**，
仅作研究留痕与复现备查；对应实验的结论以 `docs/experiments/` 下的报告为准。

## 内容构成

| 类别 | 说明 |
|---|---|
| `agent_AA` ~ `agent_Z` 等 26 个目录 | 2026-09-03/04 前后多代理并行研究轮次各子代理的工作产物（一次性脚本 + 结果 JSON） |
| `round3_repro/`、`round4_repro/` | ROUND3/4 交付报告的复现脚本（报告已移至 `docs/archive/rounds/`） |
| 带日期后缀的 `*_2026082x.py` | 2026-08 底研究冲刺的一次性脚本 |
| `run_*` / `summarize_*` / `render_*` 等专题脚本 | 结案实验的一次性回测/汇总/渲染脚本 |

## 路径映射

旧实验报告中记录的复现命令 `python scripts/<name>.py ...`，
现在对应 `python scripts/archive/<name>.py ...`（能否运行取决于当年的依赖是否仍在）。

## 为什么归档而不是删除

- AGENTS.md 要求研究历史（含失败与证伪）保留；
- git 历史可追溯，需要时可随时移回；
- 归档后 `scripts/` 根层只剩生产脚本、研究工具链与运维脚本，职责清晰。

## 后续新规

新的一次性研究脚本**不再放 `scripts/` 根层**：结案即删或随实验
`docs/experiments/raw/<实验名>/` 归档，见 AGENTS.md「文件归置规约」。
