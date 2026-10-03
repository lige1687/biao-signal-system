# 经典波动风险用途实现交接（2026-10-02）

## 一句话结论（大白话）
研究入口现在可以把过去20日的日涨幅波动，和接下来20个收盘间隔的日涨幅波动放在同一单位下比较；这是研究工具接线和人工价格验证，尚未计算真实市场效果，也没有改变买卖规则。

## 实际范围和交付
- 新增 `src/lei_signal/research/classic_volatility_risk_information.py`。复用经典 `factor_lab.benchmarks.local_features` 的严格S、固定种子E、20日简单累计涨幅及简单日涨幅标准差；不调用斜率模块的年化对数波动。
- KIND `classic_volatility_risk_information`，definition_ref `etf.reference.volatility20@1.0.0`，lookback20，warmup252，segmented恢复。
- baseline顺序 `S,E,return20,asset_510050,asset_510500,asset_588000`；added `volatility20`。两个连续值乘100，布尔/身份仍0/1；保留全部排定基础日，包括未满足预热和目标尚未成熟的日。
- `workflow_inputs._label` 增加独立 `forward_volatility` 分支：t+1..t+21完整21个报价收盘，计算20个简单相邻涨幅的样本标准差(ddof1)*100；无年化。任何路径缺报价/停牌或未知行动均不可算，绝不压缩路径。旧MAE路径允许已知停牌语义保留。
- `question_contract` 只对本新kind开放该目标，并固定两折、MSE、ridge lambda1、已有与新增信息集合、equal_asset、contained成熟条件以及60日/1000次/seed20261002。通用旧kind未开放新目标。
- `workflow_evaluation` 将新目标纳入连续预测，不新增参照模型，不事后截断连续预测。
- `workflow` 绑定新适配器、经典定义实际复用源码及其指标/源资格依赖，缓存明确包含新适配器与经典定义；真实preflight要求real_labels/effect_authorized均True、real_fits真正int4。新增固定人工价格演练检查两次拟合且有变化的波动目标。

## 调用
```python
from pathlib import Path
from lei_signal.research.classic_volatility_risk_information import build_qualification, prepare_risk_observations
qualification = build_qualification(payload, draft_contract, Path.cwd())
# qualification仅调用来源重建、过去/当日特征和日历成熟支持，不调用_label。
# draft_contract需要data.sha256、data.qualification.manifest_path及split.folds。
# 真实源采用top_etf_economic/1.0原规则，不改它的准入条件。
prepared = prepare_risk_observations(payload, authorized_contract, compute_labels=True)
```
返回 `source_quality`、`source_warnings`、`coverage`、`counts`、`scientific_support`。phases/folds只按日历加21判断成熟支持，未知未来报价不作为方案选择信息。真实标签计算要求两项真实授权，默认compute_labels=False；workflow_inputs路由只有双授权才算真实标签。

目标：`kind=forward_volatility,start_offset=1,end_offset=21,entry_field=close,path_field=close,unit=percentage_point,price_measure=economic_price,ddof=1,annualized=false`。question.target.price_basis=`close_to_close_path`。ddof/annualized缺省为1/False；提供错误值明确拒绝，True不能冒充整数ddof1。

## 验证证据和未验证项
检查文件：同目录 `implementation-checks.txt`。最多两批已完成：第一批18通过、两个测试夹具错误；训练支持应39（先排除21日未成熟），model_feature_count应7。第二批58通过，包含新模块、斜率和tsfresh回归、受控入口集成测试。验证了手算当前/未来简单收益标准差、S/E种子、百分点而非年化、ddof1而非总体标准差、未来价格变化隔离、前缀一致、停牌/缺价重置252日和目标拒绝、错误目标/定义/真实身份、仅来源资格不触标签、双授权路由、源码绑定缓存以及实际人工演练。

**最后新增声明防错未运行测试**：主控在第二批结束后要求明确拒绝错误ddof/annualized，本轮追加三个反例及三层防错，并将共享_label的配置检查放到读取未来路径之前。最终六个源码/测试文件AST语法检查通过；因两批上限不再启动第三批。主控须独立验证最终声明防错与真实资格、冻结、市场运行、数字；本执行者没有运行真实市场标签或拟合，没有取网络或写生产。

目录治理检查全绿。共享工作区原有修改保留，无提交、推送、删除或改规则定义。测试临时区仅本任务raw/pytest-tmp，保留失败记录。

## 策略来源
本次服务于已有技术价格信息的研究/风险描述层，不授权入场、退出或账户操作。实际桌面源SHA256与已确认版本一致：
- LEI 技术交易体系：`df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20`
- LEI 技术实现：`85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903`
