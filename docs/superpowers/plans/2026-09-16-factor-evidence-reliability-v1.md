# 因子证据可靠性 v1：长任务执行计划

> For agentic workers: use executing-plans task-by-task；先读完整计划。用户已认可“稳定性、连续行情影响、不确定性、统一研究档案”的方向，并于 2026-09-16 明确“可以的，那开整吧，长任务启动”。本计划把授权收窄为以下任务，不需再问是否开始。项目禁止提交/切分支，覆盖技能中的默认提交建议。

**Goal:** 建成可复用的状态研究可靠性工具，并对 B1 已封存观察结果做一次固定方法的补充分析；回答结果对年份和连续行情有多敏感，不寻找更漂亮的参数。

**Architecture:** 新增隔离的 `factor_evidence` 包，只消费已有的“日期、状态、未来结果、合法性”观察表，不生成因子或未来结果。纯分析与 B1 文件适配分开；旧 `factor_lab`、`factor_unit`、规则及全部旧结果只读。首版真实接入只支持二元状态，不冒称所有对象都已接入。

**Tech Stack:** 现有 Python/numpy/pandas/pytest/ruff；零新依赖。主控已检查本环境无 arch/statsmodels；参考成熟方法的定义，写小型可独立复算的抽样索引实现，不另造回测框架。

## 0. 工作身份、权限、必读材料

目录 `/Users/yongbiaoli/Desktop/lei-signal-lab`；分支 `codex/factor-unit-research-20260915`；HEAD 必须为 `8ba16576b75e605aa1b0d0902568c760c4b99095`。大量未提交成果存在；禁止从 main 重建、切分支、工作树、暂存、提交、reset、stash。不是新交易策略；服务交易规格 §4–5 的“道路”状态研究，未涉及入场触发。

必读：AGENTS.md、CLAUDE.md、docs/trading-spec-v1.md、configs/rules.v1.yaml（只读导航；B1 实际使用 rules.v2.yaml，均不改）、.claude/skills/macd-reading/SKILL.md、docs/plan-sector-trend-page.md；研究原则 v1.1、执行合同 v1.0.1、定义标准 v1.1.0、报告模板 v1.1.0、唯一 definitions.v1.json 容器 1.2.0；本计划、B1 执行报告及 `docs/experiments/b1-closeout-controller-2026-09-16.md`。规范实际指纹冻结，不填 latest。

对象：`candidate:lei.dual_ma.bull_state@draft-1`，候选卡 `docs/experiments/raw/factor-research-workbench-v1-2026-09-14/candidate-card-dual-ma-bull-state-draft-1.md`，SHA `907d17631e27011423bebbf068bcb2bbc6e1b44a184618597cf54f868e066dc1`。不是已正式发布对象，不改登记表。

允许：新增研究代码、测试、任务独立原始证据、报告与使用手册；只对 B1 已存观察表作新的统计汇总和下述固定重抽分析。禁止：重算真实状态/标签、调用 B1 或 factor_lab 真实运行入口、读取价格另造标签、联网取数、安装依赖、扩池/周期/参数/行情分类、策略账户/归因/回归、生产/UI/OKR 写入。主控只读方法文档访问不算执行者网络授权，执行者联网为 0。

## 1. 输入身份与输出位置

基目录 `docs/experiments/raw/b1-dual-ma-first-real-description-2026-09-16/`，以下 SHA 由主控开工前独立读取：

| 相对路径 | SHA-256 |
|---|---|
| run-02/observations.csv | 1dfe4c206212c31809f53f4b66bb40b3dd4ec193b03daf37c1540f8307eb9d5d |
| run-02/summary.json | ce4c51ba5e0d7bb7f7e10630b07fc106a59c98f0d4f57ac290f861164c9bfcf7 |
| run-02/manifest.json | ca7154fc9bdde40c54490a37c8de47acfaaf138911735b1d6dac0c67bf614fde |
| run-02/input-package/calendar.json | aa43736b67bbcee04fc21eedf8d510b184b764adf138456c8bce93a3155eb6c1 |
| supplement/full-file-listing.json | 320f4c3139c8edbb92b812217310d646df68685cbaf10b4a83ff161b9ca8a453 |
| supplement/supplement-manifest.json | 982baa52667b35c732f39c3007a808a57db96acf977248bb3b834e1ede95c592 |

旧协议 v1.0.1 SHA `00a16465e5232d3760cedbe9bccb5332b05e4f777f1732e8911ee586974c3af2`；使用旧声明与封存源码解释旧数据，不拿当前 B1 新代码强行重验旧协议。

新 raw 唯一路径 `docs/experiments/raw/factor-evidence-reliability-v1-2026-09-16/`，若已存在他人产物，停止，不覆盖。正式输出其下 run-01，纠错另 run-02。本轮使用独立协议身份 `factor-evidence-reliability@1.0.0`，不能冒充 B1 v1.0.2。

## 2. 方法裁定（执行者不得自换方法）

### 2.1 选择与排除

三个候选：只作年份描述（不足以表达连续行情影响）；拟合带时间相关修正的回归（增加模型设定和解释负担）；对成对的状态与未来结果整段抽取（本轮选择）。所谓整段抽取，是在原历史里随机选一段连续观察一起使用，避免把每天完全打散假装相互独立。

采用固定长度的循环区块重抽（Circular Block Bootstrap），**只作为假设条件下的历史敏感性诊断**。首尾相接是计算约定，不是真实行情连接；它不能证明行情机制不变，也不能消除资料口径、已见数据或研究选择偏差。不报“有95%概率因子有效”、p值、显著通过、独立样本数量或已排除过拟合。

主控 2026-09-16 实读的正式文档：

- https://bashtage.github.io/arch/bootstrap/timeseries-bootstraps.html （arch 8.0.0，方法分类及边界；非循环固定段对首尾观察抽取不足的提醒）
- https://bashtage.github.io/arch/bootstrap/generated/arch.bootstrap.CircularBlockBootstrap.html （类说明、参数、成对数组示例）

这些来源支持方法定义，不为本地参数背书。本轮不安装 arch，不宣称与其引擎逐值对过；用 numpy 写索引核心，独立枚举核算。同一报告记录引用范围、算法选择理由、未运行上游兼容核验。主控选择 L=63 与 126 是固定研究设定，不是最优参数、不是论文标准。

### 2.2 分析对象与固定输出

输入仍是 510300、观察日 2019-10-08 至 2025-12-31，目标 `P_vendor(t+22)/P_vendor(t+1)-1`，21 个变动区间，供应商调整价变化，不未经核验用作含分红财富。未来目标截止 2026-02-03 15:00+08，原件取得 2026-09-08，历史可得性未知；本轮全部为事后描述。

主要统计量 `delta = mean(main | state=true) - mean(main | state=false)`，单位为小数变化率，显示乘100写“百分点”。只用 B1 共同合法集合，不使用 aux 缺失来删主目标。辅助保留中位数差、上涨比例差、原 aux 描述，不能据它们另选赢家。

1. 全期与逐信号发生年：两组 n/均值/中位数/上涨比例，差值、正/零/负年份数。年度跨年标签仍按信号发生年，不当独立时期验证。
2. 全部七个年份逐一留出后的全期 delta（leave-one-year-out，意思是每次不计某一年）；不挑有利年份，缺任一组则 null+原因。另报两组都有值的年度差的等权均值及实际年份键集（改变了权重，只是另一描述视角，不替代全期结果，不是因果校正）。2019 不完整年份须标明。
3. 标签重叠审计：基于交易日序列的实际相邻价格区间，而不是共同日期点数；每个标签是 `(e,x]` 对应相邻 session 对的集合。输出相邻观察共享区间数量/比例及全表总区间引用数、唯一区间数；重用比只是描述，不是有效样本数。固定稀疏锚点 2019-10-08、步长23，只审计原规则，不扫描23种起点选最好。
4. 不确定性：主设定 L=63，敏感性 L=126；每种2000次，分别新建 `numpy.random.Generator(numpy.random.PCG64(20260916))`。n为完整评价日期轴长度，k=ceil(n/L)。每次从整数[0,n)等概率抽k个起点，按 `(start+j)%n, j=0..L-1` 拼接并截到n行。同一索引用于state/main/合法性，绝不可分别抽两组。先保留完整时间轴再按合法性计入每次统计，不把缺行压缩成连续行情。
5. 每次缺一组则 delta=null，保存原因和实际两组n；不额外抽取补足2000个有效值。有效重复不足1900/2000时不输出区间（本轮质量约定，不是学术门槛）；单组、空集、n<L、日历不完整时明确 not_estimable。有效时取 delta 重复分布的2.5%、97.5%分位，`numpy.quantile(method='linear')`，命名“条件性95%重抽范围”。同时列 L、有效重复数、点估计、上下界，不报赢面概率或用过零作机械采纳判决。
6. 两种L并排完整展示，不取有利一个；年份差异和短/长依赖假设不稳时要明确说明。无新模型训练、无过拟合概率估计；尝试史说明已知全期差、2正5负，不能再称事前发现或从未见过的验证。

## 3. 新增文件与接口

只新增以下文件（小型拆分如有必要仅在同一新包内，记入清单）。旧代码不改：

- `src/lei_signal/research/factor_evidence/__init__.py`
- `.../contract.py`：独立协议/必需代码和规范键/固定B1输入身份验证；不设自填approval放行。
- `.../observations.py`：`load_b1_observations(root, protocol) -> (DataFrame, schedule, audit)`；包哈希、日期、布尔、共同集合核验。纯接口 `validate_observations(frame, schedule) -> (frame, audit)`，规范列 symbol/session/state/main/aux/legal/e_date/x_date；state接受真正布尔或缺失，文件适配严格将CSV字符串 true/false 解析，拒绝任意真值转换；非法数值/重复键/倒挂日期拒绝，合法缺失有原因。
- `.../stability.py`：`state_summary(frame) -> dict`、`year_stability(frame) -> dict`、`overlap_audit(frame, schedule, anchor, step) -> dict`。
- `.../resampling.py`：`circular_indices(n, block_length, starts) -> ndarray`（纯索引，不含随机）；`paired_block_deltas(frame, block_length, reps, seed) -> dict`（复用前者，返回起点矩阵、逐次结果、条件范围和限制）。
- `.../runner.py`、`scripts/run_factor_evidence_reliability.py`：冻结、校验、一次分析、落盘；CLI `--protocol PATH --out NEW_DIR`。0=工程完成（不等于有效），2=资料/数值不足，3=身份/合同错误。已有输出拒绝覆盖。
- `tests/unit/test_factor_evidence_contract.py`、`test_factor_evidence_stability.py`、`test_factor_evidence_resampling.py`、`tests/integration/test_factor_evidence_cli.py`。
- `docs/research/factor-evidence-reliability-usage.md`、`docs/experiments/factor-evidence-reliability-v1-2026-09-16.md` 及本轮 raw。

主控另负责 registry/INDEX 和路线图最终登记，执行者不动共享文件；交 registration-proposal.json。本阶段实验报告登记未合并前，不能自行称归档全部完成。

## Task 0：保护、事实与冻结前检查（G1）

- [ ] 核目录/分支/HEAD，记录 git status --short。只读检查以上输入SHA。
- [ ] 冻结旧 factor_lab、factor_unit全部py、rules.v1/v2、definitions.v1.json、B1 raw全部文件、B1两个主控报告的路径/完整SHA与字节数；记录基线，不搬走原文件。
- [ ] 写 capability-map.md：现有接口可复用范围；旧因子/目标计算一律不调用；首版 binary_state 已支持，feature/IC/factor_return/model attribution 明写未接入，禁止另造对象登记表。
- [ ] 先生成新协议草案，真实分析前按本计划固定参数、文件身份、规范版本、卡、输入来源声明；源码定稿后排他冻结新协议及源码原字节。不得复制旧B1授权字段代替本轮授权。

## Task 1：合法输入与独立期望（G1/G2）

- [ ] 先写失败测试，再实现 contract/observations。验证哈希、缺规范、裁剪代码键、宽松容差、假版本、重复日期、漏交易日、日期倒挂、CSV真假字符串/未知、NaN/inf/非布尔、合法性与理由矛盾；错身份必须计算前拒绝。
- [ ] 调用TradingCalendar只用于读取已封存日历，按评价窗推导应有观察日；输出键集严格相等。真实B1数据不得靠 synthetic=true绕过，纯函数合成入口与真实CLI校验分离。
- [ ] 独立期望脚本置raw，不import新被测包、旧汇总函数。用标准库统计/Fraction或明确手算常数。已知全期1516/590/926仅交叉检查，不替代日期和合法集合推导。

## Task 2：稳定性与重叠（G2）

- [ ] 先红后绿，实现稳定性与区间审计，所有年份保留、未知和空组结构化输出。
- [ ] 固定教学例：A年 true=[0.10,0.10], false=[0.20]；B年 true=[-0.10], false=[0,0]。全期差=-1/30，两年差均=-0.10，等权年度差=-0.10；去A/去B都=-0.10。另用正反方向年份证明不硬编码方向；单组/0值/缺值/顺序打乱（显式排序）有测试。
- [ ] 日序位置0..25：标签[1,22]和[2,23]各21个区间，共享20，比例20/21；[1,22]与[22,43]共享价格点但共享区间0。禁止点数当区间数。

## Task 3：成对整段重抽（G3）

- [ ] 先红后绿实现纯索引函数；n=5,L=3,starts=[4,1]，期望索引精确[4,0,1,1,2]，既覆盖绕回也覆盖尾部截断。n/L/reps非正、浮点、布尔参数拒绝；测试n<L不足出口。
- [ ] 成对例 state=[T,F,T,F,T], main=[.1,0,.2,-.1,.3]；以上索引生成true值[.3,.1,.2]、false值[0,0]，delta=.2。禁止独立打散状态/目标。
- [ ] n=4,L=2枚举所有16个有序起点对，独立计算各次两组n和delta，与被测函数逐值比；缺组次数也核对，不只对最终分位。用固定列表[0,1,2,3]手算linear分位2.5%=.075、97.5%=2.925。
- [ ] 正例、零差例、恒定目标、单组、缺失掩码、重复起点、同seed复现、换目标不改起点等测试。保存numpy版本与起点数组，使未来不依赖随机库版本恢复。

## Task 4：冻结、CLI与失败保护（G4）

- [ ] 源码定稿后协议排他创建，文件名与内容版本一致，current指针不可执行；修改代码/目标/方法必须新版本，旧件保留。
- [ ] 必需键由代码常量定义，协议不能自己删检查；规范、本计划、方法设定、卡、输入及代码原字节入新包。标准JSON拒绝NaN/Infinity，合法缺失=null+原因。
- [ ] manifest最后原子定稿，包含全部输出相对路径（只排除顶层manifest本身）与SHA，文件集合双向一致；失败不能留下completed=true。元数据列单位、对象、目标、数据/用途限制；不要每行复制整张卡。
- [ ] 合成CLI覆盖合法完成、错哈希、删必需键、坏日期、输出已存在、写盘失败；导入不写盘。测试不得隐式运行真实观察分析。

## Task 5：一次真实观察表补充分析与独立核验（G5）

- [ ] 前述测试通过且协议冻结后，使用已存observations进行一次分析，所有年度/留一年/两种L在同一正式命令内完成，不先偷看结果选方法。
- [ ] 输入SHA和源声明不得变；输出 `stability.json`、`yearly.csv`、`leave-one-year-out.csv`、`overlap.json`、`resampling-L63-starts.npy`/L126同类、逐次delta与两组n/原因CSV、`uncertainty.json`、`evidence-card.json`、中文report及manifest。
- [ ] 独立核验只读取保存的抽样起点和输入表，重汇总全部逐次结果与分位，不再抽新种子；同时独立核全部年度/留一年/重叠计数，误差<=1e-12，键/整数/null严格相等。不调用被测汇总函数。此验证不生成新的市场观察。
- [ ] 验证保护基线零漂移；完整保存所有失败命令与stdout/stderr/退出码。任何真实结果不理想不是纠错理由。

## Task 6：报告、使用手册与交回（G6）

- [ ] 主报告按模板保留最小决策卡，账户收益/归因/可成交能力明确不适用。首段讲“哪些证据更可信/哪些不能据此判断”，不要把测试数当因子收益。
- [ ] evidence-card.json 是本轮生成的研究档案，不是第二对象表，包含 object_ref/use/symbol/target/window/input/protocol/code/observed_before/方法/结果路径/限制/五种资格/next_step；没有全局valid=true。
- [ ] 使用手册给一个不含真实数据的可运行合成例，说明其他二元状态如何提供合法观察表，宽度水平/数值特征不自动强转布尔；相关性IC、风险模型、真实时点验证尚未接入此模块。
- [ ] 完成返回G1–G6逐项状态、证据、命令、版本、实际预算、未接入项；开头标“执行agent声明，待主控复核，不代表用户意见或新授权”。不得自行宣布最终验收或OKR完成。

## 4. 资源预算与停止规则（整个委派工作，不按返修自动重置）

- 正式真实观察表分析：1次初跑 + 最多1次可定位工程错误纠错，共2次尝试；失败也记账。禁止B1状态/目标真实重算（0次）。
- 独立结果核验：1次 + 最多1次核验脚本工程纠错；原始起点重汇总，不另抽样。
- 完整相关回归最多2次；局部定向pytest最多25次；合成CLI开发最多6批，每批列出每条调用；测试内子进程按实际数量独立报告，不算真实统计运行。ruff最多6次。超预算先停相应分支，已完成部分照常交付，不把自报错误当许可。
- 完整回归：上述4个新测试文件 + tests/unit/test_factor_unit_description_core.py + test_b1_contract.py + test_b1_description.py + tests/integration/test_b1_description_cli.py + tests/unit/test_experiment_reports.py。不强制重跑全仓。
- 原件不一致、需要新数据/依赖、关键方法歧义、他人同文件冲突：停受影响分支，返回needs_input；不重开旧收口问题。
- ZCode最多3轮执行机会，后两轮仅主控已冻结目标内返修；任何额度追加必须主控/用户明确，不能自动继承初跑额度。

## 5. 自审与结论权限

已将用户认可方向映射到G1输入/复用、G2稳定性、G3连续行情不确定性、G4可复现输出、G5真实固定实例、G6可读档案。只建设一套小型状态可靠性能力，不造全面平台；合成验证与真实历史结果分开。以前已经看到全期差和年度方向，方法在此后确定，所有新分析必须标事后补充，不能制造新未知验证。

可靠范围包括负结果、范围很宽、方法敏感或not_estimable；不以范围排除0、因子显著或更高收益作为验收条件。下一步最多提出一个最能改变判断的实验，不自动执行跨市场、参数搜索、策略归因或实盘。
