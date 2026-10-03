# 可运行的公式与时间边界校验器

这份独立工具会挡住未经审阅的公式合同变更，以及截止时刻之后才可用的资料。同一个绝对时刻换成另一时区写法，资格保持一致。已有 LEI 源码未改，未接入生产，未做市场或收益实验。

## 使用

仅需 Python 标准库，无安装步骤。在本目录执行：

```sh
python3 -B validator.py fixtures/pass.json          # 退出 0：通过
python3 -B validator.py fixtures/block_formula.json # 退出 2：公式变更，阻断
python3 -B validator.py fixtures/block_time.json    # 退出 2：晚于截止，阻断
python3 -B -m unittest -v test_validator
```

也可直接导入 `validate_document(document)`、`validate_formula(formula)`、`qualify_bar(bar, decision_at)`；均返回明确状态与原因，不改变输入。时间未知的单行状态为 `unknown`，整份合同为 `blocked`，不会默认为通过。

公式输入同时提供完整定义/输入/缺失/时间/精确依赖合同和结构化算术说明，格式见 `fixtures/pass.json`。本版只支持已审阅的 `mixed.rv20@1.0.0`。正常定义是最近 20 个本产品有效报价间的简单收益率样本标准差乘以 √252，含当期；需 21 个有效价格；缺价不填充。`rv20_reference` 用独立标准库算术验证这些含义。

这不是“把子串匹配加强”：完整合同及两层依赖内容锁定，算子/参数/单位/端点/缺失逐项绑定，并有独立数值正反控。但机器不从任意自然语言公式自动证明数学等价；同义改写也须重新审阅。锁文件变动本身会拒绝，不能用新的说明覆盖旧实现。

时间输入必须明确带时区的实际 `session_completed_at`、`feature_available_at`、全部 `required_input_available_at`，并声明 `availability_complete: true`。实际可用时刻不能早于完成时刻或任何依赖；必须不晚于全局和可选单行决策时刻。没有默认市场收盘小时，没有默认时区。工具检查声明的一致性，不能证明声明的来源真实或完整。

## 精确源码反例

`probe_sources.py` 只导入哈希匹配的文件并喂合成输入。复现两版本 workflow 的时区与当日截止问题，以及 external key 的相同行为。公式探针调用真实 `bound_reference` 的“解析后”局部接口，以真实展开卡替代 resolver；完整原 resolver 另行调用且缺生命周期依据时保持 `blocked`。绝不删 basis、降级状态或伪造依据。源码数值与独立 RV20 算术逐行比较。

```sh
python3 -B probe_sources.py \
  --external-root /path/to/latest-source-1ac596f \
  --technical-root /path/to/code-readonly
```

输入固定为 external payload `1ac596f65110e06c286f04707165251328df0962`（登记表 1.6.12）和 technical `d444316817e9330c2d72a4a90c655467b45dd5bb` 的三文件只读对照。technical 的登记表 1.6.0 未加载，也未混入 external。精确输入哈希写在探针常量及 `evidence/source-probes-final.json`；前后 20 文件哈希一致。

实际回执见 `evidence/command-receipt.json`：7 项集中测试通过，三个 CLI 退出码为 0/2/2，源码探针退出 0。源码探针退出 0 表示预期问题被复现，并不表示原源码已修好。完整原登记准入仍受阻，不能据此判历史 V01/K01/P01 成绩无效。

本工具服务研究计算前的合同/输入资格检查；接入共享实现、完整登记依据和市场时间真值需原负责人另行处理。本包未修改共享 src/configs/tests 或正式登记，也不接管 Air 已有性质测试及 Pro 三路。
