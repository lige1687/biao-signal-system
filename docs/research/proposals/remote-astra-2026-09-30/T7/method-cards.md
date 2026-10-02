# T7 方法卡（最多三篇）

访问日期以本机时间 2026-10-02 为准；PDF 在本机临时目录抽取文本阅读，未入库。新增来源请求共 8 次：子问题“少量组如何推断”3 次（1 次证书失败），子问题“按处理后的变量筛样本”5 次（含 1 次 404、2 次跳转）。

## 1. MacKinnon, Nielsen & Webb（2023）Cluster-Robust Inference: A Guide to Empirical Practice

- 来源：arXiv:2205.03285 v1（2022-05-06，作者注明已被 Journal of Econometrics 接收）。[摘要页](https://arxiv.org/abs/2205.03285)，[PDF](https://arxiv.org/pdf/2205.03285)，57 页，所读 PDF SHA-256 `8f151977…bdaa6`。
- 实读范围：§3.3 选择分组层级的两条经验规则（PDF 第 12–14 页）；§4.3、4.3.1、4.3.2 何时会失效（第 23–27 页）；§6.2 随机化推断（第 37–39 页）；§7 应报告什么（第 39–41 页）；§9 总结清单（第 50–51 页）。其余章节与第 8 节实证例未读。
- 作者原意（摘录）：“there is no magic number for G”（§4.3，G 为分组数）；推断的基本单位是组而不是单个观测，“absolutely essential to report the number of clusters, G … even more important than reporting N”（§7）；只有一两个大组或只有少数组受处理时，常规推断会严重失真，“even when it is based on CV3 or the WCR bootstrap”（§9 第 5 条），此时可用随机化推断核对（§6.2）；选分组层级时，保守做法是取使标准误最大的层级，前提是组数不至于少到推断不可靠（§9 第 1 条）。
- 本库用法（延伸，不是作者方法）：把“同一段行情里重叠的回撤”当作一组，报告组数、每组大小分布和最大组占比；不设通用最少组数；组很少时只描述并核对去掉每一组后的方向。
- 不能说：作者没有讨论交易规则，也没有给本系统任何通过线。

## 2. Montgomery, Nyhan & Torres（2018）How Conditioning on Posttreatment Variables Can Ruin Your Experiment and What to Do About It

- 来源：American Journal of Political Science 62(3): 760–775；作者主页提供的[发表前版本](https://sites.dartmouth.edu/nyhan/publications/)，所读 PDF SHA-256 `4153bc11…2298`。
- 实读范围：摘要与 §1 引言（第 1–2 页）；§3.2 中“只要不按处理后变量取样，随机化保证两组可比”的段落；§5.1–5.5 实践建议（第 22–25 页）。§3.3–3.4 推导、§4 实证、附录未精读。
- 作者原意（摘录）：“do not condition on post-treatment variables. Do not control for them in regressions. Do not subset your data based on them.”（§5）；按处理后变量取样造成的偏差“can be in any direction, it can be of any size”（§1）；样本流失时排除观测等同于按处理后变量取样，可改报“按原分配的效果”或用极值界限（§5.2–5.3）。
- 本库用法（延伸）：回撤身份必须由两种规则分歧之前就已确定的事实（趋势段、触碰日、均线组）界定；**不能只比较两种规则都入场的回撤，也不能删掉被规则 B 放弃的回撤**——那等于按规则的后果筛样本；放弃记 0 收益保留在分母里，相当于作者建议的“按原分配统计”。
- 与实验不同之处：回测中同一次回撤的两种结果都能算出来，所以样本内的配对差不需要随机分配；不确定性来自“未来的回撤会不会像这些一样”，这才是按时间分组要处理的。

## 3. Sullivan, Timmermann & White（1999）Data-Snooping, Technical Trading Rule Performance, and the Bootstrap（复用库内记录，未新读）

- 库内位置：`docs/literature-learning/READING.md` 的 sullivan1999 条目；库内注明只核过摘要，另有讨论稿方法节的跟进记录。
- 本题用法：一次只比较预先固定的一个条件（A3 两档），所有尝试记入家族账本；不因结果追加第三种 A3 形式或改窗口长度。
