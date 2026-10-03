# 外部公式搜索试点：复核入口

## 用途与边界

本目录回答一个工程问题：在事先固定的人工资料上，DEAP是否比直接NumPy筛选增加可靠的候选关系。它不是金融实验，没有行情、因子获准交易或线上收益。3次搜索随机起点共用同一资料，不是3份独立历史证据。生成规则已知，属于有答案的能力检验，不是盲测AI发现能力。

冻结输入/算法/阈值见 `protocol.json`；来源/包指纹见 `sources.json`。首轮计划与授权见 `../../../archive/handoffs-plans/external-research-capability-pilot-2026-10-03/PLAN.md`。原始失败与真实次数随最终证据交付。

## 环境及隔离安装

实际运行环境Python3.11.7、NumPy2.1.1、macOS arm64；DEAP1.4.3只安装在本仓库忽略目录。没有更改生产pyproject或全局Python，未安装为默认Codex技能。其他操作系统未实测。

在已有相同NumPy环境中，下载 `sources.json` 中第4项的固定wheel，先核SHA256，再仅在本仓库隔离目录安装：

```sh
python3 -m pip install --no-index --no-deps --target .biao/external-research-pilot-20261003/deps .biao/external-research-pilot-20261003/deap-1.4.3-cp311-cp311-macosx_10_9_universal2.whl
```

该wheel仅适用于相应Python/macOS架构。Linux需独立取得同版本适配wheel并核官方SHA，不能将本机验证说成Linux已通过。许可证为上游LGPL v3；本仓库不复制第三方源码/二进制，仅保留自有试验代码与获取指纹。新环境从PyPI安装依赖需要联网，完整离线环境包没有交付；不从Air用户目录导入包。

## 先复核存档，不重新搜索

从仓库根目录执行；只需NumPy，不需DEAP、密钥或网络：

```sh
python3 docs/experiments/raw/external-symbolic-search-pilot-2026-10-03/run.py --check-existing docs/experiments/raw/external-symbolic-search-pilot-2026-10-03/core
```

检查重建人工输入、比对指纹、重新解释保存的公式并核对预测及误差。预期输出 `verified`，搜索评价计数57600。实际通过与否以 `review.json` 为准，说明文字不替代回执。SHA256SUMS只覆盖交付清单且不包含自身。

## 仅在新授权或实现错误需要时重开搜索

原输出拒绝覆盖。以下是原核心入口，不是要求接手者再跑一次：

```sh
PYTHONPATH=.biao/external-research-pilot-20261003/deps python3 docs/experiments/raw/external-symbolic-search-pilot-2026-10-03/run.py --output <new-output-directory>
```

运行前读最新协调记录、核协议SHA以及报告的封存/停止条件。0市场输入；固定600秒上限。不更换种子/参数追求通过。没有后台进程迁移或自动续跑能力；失败时按实际收据核已用预算，不能把保存文件当作进程checkpoint。

## 范围说明

- DEAP与随机控制共用表达式生成器，二者只比较演化选择/修改是否改善搜索；真正不依赖DEAP的对照是NumPy直接基准。
- 直接基准含一次/三次多项式及从既定字典逐步挑选的少量项，不拿偏弱的线性模型作为唯一对照。
- 最终测试和范围外资料不用于训练、挑候选或修参数；人工噪声任务强制保留为反例。
- 用户介入次数、助手消耗、总时长与实际节省的人工作业时间不同；未计量部分不能报告免费或省人力。

## 实际结案

本轮比较完成但未达到采用条件，因此未接入默认研究工具。27条保存结果、108项独立误差核数和临时目录恢复通过；改错预测被拒绝。后续默认只核存档，不重跑核心搜索。预检与核心合计220次人工拟合的分项预算与不可外推边界见上层报告及review.json。
