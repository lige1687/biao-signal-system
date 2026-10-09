# Qlib 恢复包独立核验

审查人：/root/qlib_recovered_audit，GPT-6 Sol/medium；2026-10-09。仅内存读取两原ZIP的JSON、CSV及字节哈希，不运行包内代码，不加载pickle，不拟合、不求解、不计算新效果。

## 一句话结论（大白话）
旧Qlib运行的原包和输入都已找到，保存的预测确实与原模型一致；这证明了这次历史工程复现的数值一致性，不代表策略更赚钱。

- Qlib包SHA：23f6548fd3faa9b35b29c512f4f3a9b5a8ec6ef30eaf3871949d08bfe70537f2。
- 原来源包SHA：ae0b072081c2d2692b0e0f22a1b03d8c9214517d8c5c9042020b5352718cca7e。
- 协议14项源文件大小/SHA逐项相符。completed-package-manifest的55项逐项相符，与ZIP非自引用成员集合相等。
- 协议、执行许可、账本、独审、输出清单、回放状态、模型纯字节哈希、代码及依赖锁引用均吻合。
- 账本6事件：一次fit的reserved/success、两次predict各reserved/success。预算1次训练、2次预测、各99行共198次行应用已耗尽，不重跑。
- 按H1A:broad_etf:2025:B原evaluation_row_ids核对99行，新预测和回放CSV逐字节相同；源saved-predictions的broad_etf/2025/B恰99键、顺序一致。
- 独立重算保存数值差：预测最大3.552713678800501e-15，系数4.996003610813204e-16，截距0。均低于原定绝对容差1e-10，和原回执一致。

实际历史运行次数、Qlib内部调用与当时执行过程只能由保存日志/回执间接证明；本次未重现运行时。云端Library身份由root的官方登录页面核对。不能据此宣称因子有效、预测改善、可实盘或生产已接入。
