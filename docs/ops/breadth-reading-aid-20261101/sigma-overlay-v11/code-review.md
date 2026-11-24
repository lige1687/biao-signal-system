# ERP 双σ实现只读复核（2026-11-03）

范围：按 `review-contract.json` 只读当前六个文件及 `before` 快照；未运行浏览器、金融实验或新来源查询。下面按可复核性列出发现。

## 发现

1. **P2：窄屏事件选择框可能横向溢出。** [erpCrossChart.css](../../../../web/src/components/observation-library/erpCrossChart.css) 第4行把旧版 `max-width: min(100%, 480px)` 改为 `max-width: 480px`；旧版第20行还有 `@media (max-width: 600px)` 下的 `label/select { width: 100%; }`，新版已删除。日期加阈值的 `<option>` 会使原生 `<select>` 有较宽的内在尺寸；在 320–400px 容器中，新规则没有把它约束到父宽度。复核方法：手机宽度打开“回看穿轨”，检查选择框右缘及页面横向滚动。建议恢复 `max-width: min(100%, 480px)` 并在窄屏给容器内选择框 `min-width: 0; width: 100%`。

2. **P2：有价格但 ERP 值全缺失时仍可显示双图。** [ErpCrossChart.tsx](../../../../web/src/components/observation-library/ErpCrossChart.tsx) 第42行的 `enough` 只要求至少两日期、任一价格非 null；没有要求 `aligned.values` 中有可画的 ERP 值。第121–122行因此会渲染空的 ERP 上图，而空态文案称“股债利差与价格缺少足够的共同历史”；资料断档时画面缺失状态与渲染门槛不一致。可用两日期、价格 `[3000, 3010]`、ERP `[null, null]` 的输入复核分支。建议至少要求同一索引上 ERP 与价格均为有限数，且符合“足够共同历史”的最小点数；这不改变任何穿轨规则。

3. **P3：价格标题的“同日”可能被读成实际价格日。** [ErpCrossChart.tsx](../../../../web/src/components/observation-library/ErpCrossChart.tsx) 第69行标题为“价格（点） · 同日穿轨位置”，但第80行显式允许 `aligned.priceDates[index] !== date`，并在 tooltip 中另列实际价格日。周频观测遇到非交易日价格对齐时，事件点与 ERP **共用观测周日期**，不一定是价格原始日期。建议标题写“同一观测周穿轨位置”；保留 tooltip 的实际价格日说明。

## 已核通过的核心逻辑

- [erpComparisonDisplay.ts](../../../../web/src/components/observation-library/erpComparisonDisplay.ts) 第9–12行以 `sigma:date:kind` 生成事件身份；同周同时穿越1.5σ和2σ时保留两个事件，且下拉框以 `id` 作值（`ErpCrossChart.tsx` 第119行）。
- [erpEventMarkers](../../../../web/src/components/observation-library/erpComparisonDisplay.ts) 第16–24行只在对应观测周的值为有限数时放标记，不把缺价格周的事件移至下一周；下拉框仍可列出事件。当前测试第7–31行覆盖同日双事件、缺值和缺周。
- [erpCrossings.ts](../../../../web/src/components/observation-library/erpCrossings.ts) 第10–19行要求连续合格周（间隔大于0且不超过10天）且前周未在轨外、本周严格越界，缺值重置前周；与原有首次穿轨规则一致。
- [erpSensitivity.ts](../../../../web/src/components/observation-library/erpSensitivity.ts) 第5–10行按同一 `middle/sigma` 计算三档上下轨，不改写输入。`innerErpRails` 从原±2σ宽度得到±1.5σ（半宽乘0.75）并对缺值保留未知。
- [ErpCrossChart.tsx](../../../../web/src/components/observation-library/ErpCrossChart.tsx) 第123、126–128行把历史检验限定为“2008—2026年10月”，并把1.5σ称为本地灵敏度参考；统计文案没有宣称未来收益或交易规则。此处数字沿用既有冻结结果，本轮未重新核算。
