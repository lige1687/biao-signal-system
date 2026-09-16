"""factor_evidence：状态研究证据可靠性工具（因子证据可靠性 v1）。

隔离研究包：只消费"日期、二元状态、未来结果、合法性"观察表，做年份
稳定性、留一年、标签区间重叠审计与成对循环区块重抽的条件性敏感范围。
不生成因子、不重算状态/标签/目标、不读价格序列、不做收益账户或归因。

- ``contract``：独立协议 factor-evidence-reliability@1.0.0 的固定绑定。
- ``observations``：B1 观察表适配 + 规范观察表纯校验。
- ``stability``：全期/逐年/留一年统计与区间重叠审计。
- ``resampling``：circular_indices / paired_block_deltas（固定方法）。
- ``runner``：一次分析编排与产物落盘（manifest 最后原子定稿）。

能力边界见
``docs/experiments/raw/factor-evidence-reliability-v1-2026-09-16/capability-map.md``。
"""
