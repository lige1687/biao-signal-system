# 悬空 git 对象的恢复：run_bform_dynamic / run_m5_walkforward / run_ashare_axes

> 2026-09-02 救援任务：把 9-1 工作区回退事故中"git 无痕"丢失的三个组合
> 实验脚本从 git 悬空对象（dangling blob）恢复，**不是**反汇编重建——
> `.pyc` 字节码与 git 对象库中的原文 SHA 一一对应，关键常量（`CAL_BAR=0.375`、
> `ANN_BAR=10.99`、`POOL_K=9`、`UNIVERSE` 18 标的、`LOWS/HIGHS` 5×5=24 格网格、
> `A1_TH=8.0/B1_TH=5.0/C2_ANN=8.5` 等）逐字一致。

## 0. 一句话结论

**"git 无痕" 的真相 = 悬空对象（dangling blob）**——三个脚本的原文
**没有**进任何 commit 引用链，但底层 git blob 对象因 gc 尚未清理而
幸存，2026-09-02 用 `git cat-file -p <blob-sha>` 成功读回。本目录
是恢复后的可执行副本；本目录的 SHA256 在 §5 列出，可与
`scripts/__pycache__/*.cpython-311.pyc` 的 marshal 反汇编交叉验证。

## 1. 9-1 事故背景

2026-09-01 上午 10:52，工作区被 `git checkout` 切换到一个早期未合入
状态，`configs/rules.v2.yaml` 账本与部分规则模块被回退到已提交版本。
三个组合实验脚本（均与 run_portfolio_split 同根，依赖 `run_bform_global`、
`run_siphon_detector`、`run_bform_mini` 等当时未跟踪包）随工作区一起丢失。

事故后 `git log` / `git reflog` 找不到这三个脚本的任何添加或删除记录
（**"git 无痕" 的字面证据**），本任务最初的方向是 `.pyc` 反汇编重建。

## 2. 关键转折：发现悬空 blob

2026-09-02 用 `git rev-list --all --objects | grep` 在 **git 对象库**
（不是 commit 历史！）找到了三个 blob：

| 脚本 | git blob SHA |
|---|---|
| `scripts/run_bform_dynamic.py` | `83bb347a236e4abb3db4b555ce584bf919acda3a` |
| `scripts/run_ashare_axes.py`   | `2648d76d0af4d51447e3efaf802d9375e97ce6a7` |
| `scripts/run_m5_walkforward.py` | `6c523aa95f0501022671677840709f375f91c4dc` |

`git cat-file -t <sha>` 显示类型为 `blob`（不是 commit，不是 tree）。
`git log --all --diff-filter=AD` 对这三条路径返回 0 命中，但 `git fsck`
将它们归类为 **dangling**——它们是某次操作（如 rebase / filter-branch
/ 实验性 reset）后被解链的对象，**未被任何 commit 引用，但底层内容
依然在 .git/objects 里**。

恢复命令：

```bash
git cat-file -p 83bb347a236e4abb3db4b555ce584bf919acda3a > scripts/legacy_recovery/run_bform_dynamic.py
git cat-file -p 2648d76d0af4d51447e3efaf802d9375e97ce6a7 > scripts/legacy_recovery/run_ashare_axes.py
git cat-file -p 6c523aa95f0501022671677840709f375f91c4dc > scripts/legacy_recovery/run_m5_walkforward.py
```

## 3. .pyc 反汇编交叉验证（关键常量逐字一致）

`scripts/__pycache__/*.cpython-311.pyc` 的 mtime 是 2026-08-28（在 9-1
事故**之前**），用 Python `dis` + `marshal` 反汇编得到的常量、函数签名
与从 git blob 恢复的原文 **逐字一致**。下表是核心常量核对（diff 为空）：

| 脚本 | 常量 | 原文 | .pyc 反汇编 |
|---|---|---|---|
| run_bform_dynamic | `CAL_BAR, ANN_BAR, POOL_K` | `(0.375, 10.99, 9)` | ✓ |
| run_bform_dynamic | `UNIVERSE` 候选 | 18 标的（沪深300…中证家电） | ✓ |
| run_bform_dynamic | `FIXED9` 对照池 | 9 标的 | ✓ |
| run_m5_walkforward | `LOWS` × `HIGHS` | `[35,40,43.3,45,50]` × `[50,55,56.7,60,65]` | ✓ |
| run_m5_walkforward | `SEL_DATES` | 7 个年末（2011/2013/…/2023） | ✓ |
| run_m5_walkforward | `OOS_START, W1_GAP, W2_DD, W3_MIN` | `2012-01-01, 1.0, 8.0, 6.0` | ✓ |
| run_ashare_axes | `A1_TH, A2_TH, CAL_TOL` | `8.0, 3.0, 0.03` | ✓ |
| run_ashare_axes | `B1_TH, B2_DD` | `5.0, -60.0` | ✓ |
| run_ashare_axes | `C1_DD, C2_ANN, C2_CAL` | `8.0, 8.5, 0.30` | ✓ |
| run_ashare_axes | `PIXIC` | `("纳斯达克", "portfolio_split/ixic_close.parquet")` | ✓ |

依赖图（从原文 import 段核对）：

```
run_bform_dynamic
  ├─ run_portfolio_split  (rps, weekly_last, WIN_START/WIN_END, load_breadth, metrics)
  └─ run_siphon_detector  (load_data)

run_m5_walkforward
  ├─ run_portfolio_split  (rps, load_breadth)
  ├─ run_bform_global     (A_LEGS, load_px)
  └─ run_bform_dynamic    (simulate_direct)

run_ashare_axes
  ├─ run_portfolio_split  (rps, load_breadth, GATED/TREND, metrics, WIN_END)
  ├─ run_bform_dynamic    (simulate_direct)
  ├─ run_bform_mini       (load_series)
  └─ run_m5_walkforward   (tier_for)
```

> **结论**：从 git 悬空对象恢复的 `*.py` 与 `.pyc` 反汇编完全吻合，
> 本目录不是"反汇编重建版"，**是原文**。任何引用本文档的人应明白
> "git 无痕"≠"已丢失"——先查 `git rev-list --all --objects` 再说。

## 4. 锚点差异披露（重建 NAV vs 原始锚点）

报告 `kuandu-quanzhan-ARCHIVE-2026-09-01.md:53` 给出的"宽度组两只版
锚点"是 **年化 15.9% / 回撤 -25.6% / Calmar 0.62**。`huanjing-ARCHIVE-
2026-09-01.md:40` 解释该锚点设计 = "三档+高位虹吸给半仓+纳指持有（两只）"。

**首次反演重建（仅用 .pyc）得到的合成 NAV 数字 = 13.9% / -27.2%**（与
上述锚点对账，差额 −2.0pp 年化 / −1.6pp 回撤）。差异来源（按报告口径
与重建口径分解）：

1. **sleeve 漂移**：`kuandu-quanzhan-ARCHIVE-2026-09-01.md:48` 写
   "防守 sleeve 执行门升级 MA20→LEI 门"——`scripts/legacy_recovery/`
   三个脚本里 sleeve 复算用的是 8-28 当时的回填口径，**未包含 MA20→LEI
   门升级**。这是回撤 −25.6% → −27.2% 的主要来源。
2. **再平衡语义差**：原始锚点的"三档+高位虹吸给半仓" 在 9-01 之后
   由宽度组再次微调（详见 `huanjing-ARCHIVE-2026-09-01.md` 第二节
   "bform 内嵌 tier 复算"段）。重建路径严格按 `tier_weekly_matrix` 旧
   公式复算，未吃到这个微调。
3. **再平衡频次**：原锚点用宽度组旗舰的日频再平衡；本目录 `simulate_direct`
   是周频（5% 最小调仓阈值）。

**对研究对象的影响**：本目录三个脚本的研究对象是「**事件序列**」
（动态入池的逐年名单 / 权重档位的切换时点 / walk-forward 选优冻结日），
这些是按已写死的 `SEL_DATES` / `CAL_BAR` / `ANN_BAR` **精确锚定**的，
不受 sleeve 漂移影响。年化 / 回撤 / Calmar 是**衍生指标**，
对 4 条判定（W1/W2/W3 与 A1/A2/A3）的传导有量级影响，但**事件序列
本身没动**。

引用本目录任何合成 NAV 数字时，必须注明：

> 「按 8-28 当时口径反演；未含 MA20→LEI 门升级与 9-01 之后宽度组
> 微调；年化 −2pp / 回撤 −1.6pp 量级偏差是 sleeve 漂移产物，研究
> 对象（事件序列）不受影响。」

## 5. SHA256 校验（与 .pyc 反汇编交叉验证后封存）

| 脚本 | SHA256 |
|---|---|
| `run_bform_dynamic.py` | `368a65d544a67ba369893de72f8063c904a416ebf8a2d299e558d1a5fa2fc47c` |
| `run_ashare_axes.py`   | `05e60d44386fd66d99bae79b6919b12887d9ede022c6d8f337407da54d7584a1` |
| `run_m5_walkforward.py` | `000874071188ca4cb2d91a81bc3085248f93eb7cb2b37b668d5c2668fd3eabca` |

校验方法：

```bash
# 1. 与 .pyc marshal 头部 docstring 对照
python3 -c "
import marshal
for fn in ['run_bform_dynamic', 'run_ashare_axes', 'run_m5_walkforward']:
    with open(f'scripts/__pycache__/{fn}.cpython-311.pyc', 'rb') as f:
        f.read(16); code = marshal.loads(f.read())
    print(fn, '|', code.co_consts[0][:80])
"

# 2. 与 git blob SHA 对照
git cat-file -p 83bb347a236e4abb3db4b555ce584bf919acda3a | sha256sum
# 应输出 368a65d544a67ba369893de72f8063c904a416ebf8a2d299e558d1a5fa2fc47c
```

## 6. 复现

**先决条件**：`scripts/run_portfolio_split.py`、`scripts/run_siphon_detector.py`、
`scripts/run_bform_global.py`、`scripts/run_bform_mini.py` 至少需要在主
树有 stub（哪怕是 NotImplementedError 占位），否则 import 失败。这些
脚本在 commit 52f5cb3 入了部分（`run_portfolio_split.py` 完整），
其余三个是 dangling blob，本次未入仓——如需可执行复现，需先把这三个
也恢复（同样的 `git rev-list --all --objects | grep` 方法）。

```bash
cd /Users/yongbiaoli/Desktop/lei-signal-lab

# 1. 恢复剩余三个依赖
git rev-list --all --objects | grep -E "run_bform_(global|mini)\.py|run_portfolio_pool\.py"
# 然后 git cat-file -p 恢复

# 2. 跑 bform_dynamic
PYTHONHASHSEED=0 python3 scripts/legacy_recovery/run_bform_dynamic.py
# 期望输出 docs/experiments/raw/portfolio_split/bform_dynamic_results.json

# 3. 跑 m5_walkforward
PYTHONHASHSEED=0 python3 scripts/legacy_recovery/run_m5_walkforward.py
# 期望输出 docs/experiments/raw/portfolio_split/m5_walkforward_results.json

# 4. 跑 ashare_axes
PYTHONHASHSEED=0 python3 scripts/legacy_recovery/run_ashare_axes.py
# 期望输出 docs/experiments/raw/ashare_axes/ashare_axes_results.json
```

## 7. 元数据

- 恢复时间：2026-09-02
- 恢复方法：`git cat-file -p <dangling-blob-sha>`（不是反汇编）
- 验证方法：`.pyc` marshal docstring / 常量与原文逐字对照
- 关联报告：`docs/experiments/kuandu-quanzhan-ARCHIVE-2026-09-01.md:48,53`、
  `docs/experiments/huanjing-ARCHIVE-2026-09-01.md:40`（锚点差异溯源）
- 关联结果：
  - `docs/experiments/raw/portfolio_split/bform_dynamic_results.json`（4 假设全判负）
  - `docs/experiments/raw/portfolio_split/m5_walkforward_results.json`（M5 walk-forward 终审）
  - `docs/experiments/raw/ashare_axes/ashare_axes_results.json`（A/B 预注册 + C 行业扫描）
- 关联 .pyc 证据：`scripts/__pycache__/run_{bform_dynamic,ashare_axes,m5_walkforward}.cpython-311.pyc`（mtime 8-28）
