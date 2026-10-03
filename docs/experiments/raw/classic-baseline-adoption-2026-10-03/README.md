# 各ETF历史平均对照：工程验收证据

更新时间：2026-10-03 12:56:36 UTC（UTC；用户时区Asia/Shanghai）。

这里验证研究工具能否识别“新方法胜过原模型、仍输简单办法”，不是再做一次市场实验。四个代码/测试文件与当前任务分支绑定；主控验收JSON含源码SHA。

阅读顺序：本目录controller/acceptance.json → 工程报告../../classic-baseline-adoption-2026-10-03.md → 对应计划目录executor-receipt.json → 三批结果。

- 第1批：模块未实现，预期红测exit2，0拟合。日志executor-tests/round-01.log。
- 第2批：36通过、30失败。28项集成检查缺正式定义的历史资格附件；2项旧A01/A02归档检查缺原件。完整280741字节日志仅本地，SHA与保存结果清单见local-only-artifacts.json。没有改写旧材料让它“通过”。
- 第3批：36通过、2项旧归档检查未运行。日志executor-tests/round-03.log、记录的模型调用executor-tests/round-03-fit-calls.json。独立人工定义synthetic.test.sma_distance@1.0.0只服务测试，状态exists，不冒充真实研究资格。
- 主控另用不等数量的两ETF三条评价记录核两种权重；数字均吻合，成熟时间边界有效。已有真实CLI输出又经原check_publication及纯算术重核，九件原材料SHA不变。新增拟合0。
- 执行者真实CLI已通过。主控起初因磁盘errno28不能写输出，先完成只读核数；空间恢复后补做唯一一次独立CLI也exit0、0拟合、原件未变。没有重跑模型测试。
- 原shared工作区和已封存研究未动。大临时目录不进Git，没有数据、模型或生产效果交付声明。

## 最小可复核入口

在本任务分支根目录，已有项目依赖的Python3.11环境执行；新临时目录必须不存在：

```bash
PYTHONPATH="$PWD/src" PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q \
  tests/unit/test_classic_baseline_review.py \
  tests/integration/test_classic_baseline_review_entry.py \
  tests/unit/test_workflow_evaluation.py \
  -k 'not old_ridge_expression and not sealed_a02' -p no:cacheprovider \
  --basetemp docs/experiments/raw/classic-baseline-adoption-2026-10-03/recovery-check-01
```

预期36 passed / 2 deselected（本次macOS实际记录）；其他系统、全新依赖安装未验证。这个检查会生成4次人工模型拟合，并执行既有人工数值回归；不是0拟合命令，不应为刷新进展重复运行。两个被排除的测试缺旧原件，不能由绿色结果推断已通过。

真实使用入口见docs/research/research-workflow-usage.md的新段。只核保存结果的`--review-baselines`本身新增拟合0；新研究提前约定对照，旧封存研究直接引用既有结果。来源不全或源码不匹配时预期拒绝，不改旧锁/成绩。

## 文件与版本

manifest.json/SHA256SUMS记录本次交付文件内容；不对自己递归求哈希。实际commit由本目录Git历史与coordination/lei任务记录给出。磁盘临时满后空间恢复，本轮通过本地准确路径提交和普通push交付；基础HEAD为cf8d630954257fff441d55a974f8a0fe95eca443。精确成果SHA由远端分支及协调记录核对。恢复前读取远端并逐文件比较；不要reset/checkout脏工作区。没有模型/市场任务在后台持续运行，没有接管授权。
