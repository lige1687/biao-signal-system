# 外部候选公式筛选组件：复现入口

读取顺序：上级报告 → protocol.json/cases.json → core/seed-*.json → adapter-result.json → restore-and-independent-check.json → controller-review.json → manifest.json/SHA256SUMS。

## 已测环境与恢复

Mac arm64、Python3.12.14、NumPy2.3.5；原生代数对照还需SymPy1.13.1/mpmath1.3.0。正常使用结构提示不依赖SymPy、SciPy、模型权重或LLM服务。Python3.11不满足上游type语法，失败回执保留。其他操作系统未测。

所有命令工作目录为仓库根目录；ROOT可为任何已恢复仓库路径。创建仓内虚拟环境并安装依赖（这些安装命令本轮未运行；实际复用已有环境）：

```sh
python3.12 -m venv .biao/candidate-env
.biao/candidate-env/bin/python -m pip install numpy==2.3.5
# 仅重现原生代数比较需要：
.biao/candidate-env/bin/python -m pip install sympy==1.13.1 mpmath==1.3.0
```

上游归档URL、2293875字节和SHA见provenance.json的archive，取回并解压到仓内自选目录。先核归档SHA `8df5596d37aa0f507ce5da30e58e63152c2b909dc95b9db99897b96e41512563` **以provenance.json完整64位值为准**；随后入口逐项核10源文件，不能只凭main最新。归档/依赖恢复不是自动下载授权模型。设UPSTREAM为该解压根目录（包含factorminer/）：

```sh
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD/src"
export LEI_FACTORMINER_SOURCE="$UPSTREAM"
python3.12 -m unittest discover -s tests/unit -p test_candidate_fingerprints.py -v
python3.12 -m lei_signal.research.candidate_fingerprints \
  --input docs/experiments/raw/external-candidate-diversity-2026-10-04/example-input.json \
  --upstream "$UPSTREAM" \
  --provenance docs/experiments/raw/external-candidate-diversity-2026-10-04/provenance.json \
  --output .biao/candidate-new-result.json
```

使用实际装有依赖的Python3.12（上例若用venv，替换解释器）；输出必须为新路径。预期5条全部保留，1同结构同条件提示、3待审查、1非法公式，自动删除0；重复输出退出2。输入SHA/可知时点由调用者声明，入口不读取行情或自行认证。

21对原生比较仅需检查保存结果，不能为新研究重复消耗原预算。必要独立复核可运行run_probe.py --upstream "$UPSTREAM" --output <新文件>，事先固定PYTHONHASHSEED=0/1/2；协议限定无sentence-transformers/sklearn/faiss的hash降级环境，脚本会拒绝其他后端，而非静默下载模型。禁止覆盖core/。

## 交付边界

Git包含原生源码路径/指纹、MIT许可、小人工输入/输出和第一方适配器；上游整包及依赖不重复入Git，按固定URL恢复。没有金融数据/权重/密钥。源码指纹和运行结果分开，所有声明只限已测后端/平台。原始probe概念context是8项，新适配器是10项，独立证据分开。资料和模型额度不足的下一金融问题不由本包视为通过。
