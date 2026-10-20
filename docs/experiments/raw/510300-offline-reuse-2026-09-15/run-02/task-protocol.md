# 510300 离线输入复用与 B1 规格交接：任务协议 v1.0.0

2026-09-15。排他写入本文件；任何成功/失败/临时完整运行编号均留痕，绝不删除再用同一编号。

```text
【来源：执行agent交付，用户仅转交】
本协议与后续交付均由执行agent撰写，尚待主控独立核验。
不代表用户意见、主控认可或新增授权。
```

## 1. 身份（开工核对）

- 目录 `/Users/yongbiaoli/Desktop/lei-signal-lab`；分支 `codex/factor-unit-research-20260915`；
  HEAD `8ba16576b75e605aa1b0d0902568c760c4b99095`（与任务书一致；HEAD 不作为脏工作区
  源码身份，实际读取文件逐一见 `baseline/frozen-inputs-sha256.txt`）。
- `git status --porcelain` 429 行（大量既有未提交成果，不归属本任务；本任务不暂存/
  提交/切分支/新建工作树）。
- 授权来源：用户"继续推进这两个的剩余工作"；任务书
  `docs/superpowers/plans/2026-09-15-510300-offline-reuse-handoff.md`；
  主控裁决 `docs/experiments/factor-unit-four-fixes-controller-2026-09-15.md` v1.0.0。

## 2. 规范绑定（实际版本+哈希见 baseline）

研究原则 v1.1 / 定义标准 v1.1.0 / 执行合同 v1.0.1 / 模板 v1.1.0 / 交易规格 v1；
对象 `candidate:lei.dual_ma.bull_state@draft-1`（候选卡哈希
`907d17631e27011423bebbf068bcb2bbc6e1b44a184618597cf54f868e066dc1`，未入登记表）。
登记表 `docs/research/definitions.v1.json` 只读（容器 1.2.0，不新建对象）。

## 3. 范围与禁止

只做：七份 sh510300 原始响应的确定性拼接、证据封装、B1 规格文档。
禁止：联网、新依赖、真实状态/目标/收益/账户计算、修改 src 或旧脚本、改
study_contract/state_description/旧 CLI 以提前放行、把真实资料标 synthetic、
写 registry/INDEX（主控统一登记）、OKR、生产。

## 4. 固定输入身份（与主控 verification.json reuse.source_files 逐条一致）

- fetch-manifest `5ba8a51d93dcca331204b4df71aa47f5b15a76dedee8ee3ab951689e0979f0c4`
  （28 条中 symbol=sh510300 共 7 条，field=qfqday）；
- 七份原件 SHA 见 baseline，已与主控清单逐条比对一致；
- 日历 `docs/experiments/raw/research-calendar-completion-2026-09-10/calendar-merged/calendar.json`
  SHA `aa43736b67bbcee04fc21eedf8d510b184b764adf138456c8bce93a3155eb6c1`；
- 输入覆盖 2019-09-02 至 2026-02-03（主控交叉证据 1,558 个交易日；完整性从日历
  逐日推导，不靠行数放行）。

## 5. 预算与记账

- 正式拼装最多 1 次；修正后用新编号（run-02）再 1 次；/tmp 正式重放同样计数。
  单测内纯合成拼装不计真实拼装。所有完整运行（含失败、临时）逐次记入
  `run-log.md`，编号不复用。
- 本任务测试按需；相关回归（任务书指定七文件 pytest 命令）最多 1 次；ruff 仅本任务文件。
- 恢复演练 1 次，临时目录只读，不调用真实研究入口。

## 6. 目标声明边界

拟研究目标 `vendor_adjusted_price_change`：本次指定快照（2026-09-08 取回）的
历史描述目标，不是含分红财富（total_return_wealth），不是交易利润；
`data_mode=real`、`historical_reconstruction_only=true`；历史逐行 available_at=null；
精确复权 anchor unknown；不声称 point-in-time verified。
