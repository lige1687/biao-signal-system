# BaoStock 定点交易状态核验

仅查询 8 代码、2026-10-26 至 10-30；未拼接价格或修改正式缓存。

- SDK 请求：8 次；登录 1 次。
- 33 个目标缺行：BaoStock 非交易 33；有交易冲突 0；未知 0。
- 超时：无；进程退出码：0。
- `tradestatus=0` 仅作为 BaoStock 当日非交易状态证据，不自动解释停牌原因；无返回行仍为未知。

| 日期 | 代码 | 状态 | BaoStock tradestatus |
|---|---|---|---|
| 2026-10-26 | sh600621 | vendor_nontrading | 0 |
| 2026-10-26 | sh601326 | vendor_nontrading | 0 |
| 2026-10-26 | sh605258 | vendor_nontrading | 0 |
| 2026-10-26 | sh688496 | vendor_nontrading | 0 |
| 2026-10-26 | sz002717 | vendor_nontrading | 0 |
| 2026-10-26 | sz002827 | vendor_nontrading | 0 |
| 2026-10-26 | sz301468 | vendor_nontrading | 0 |
| 2026-10-27 | sh600621 | vendor_nontrading | 0 |
| 2026-10-27 | sh601326 | vendor_nontrading | 0 |
| 2026-10-27 | sh605258 | vendor_nontrading | 0 |
| 2026-10-27 | sh688496 | vendor_nontrading | 0 |
| 2026-10-27 | sz002717 | vendor_nontrading | 0 |
| 2026-10-27 | sz002827 | vendor_nontrading | 0 |
| 2026-10-27 | sz301468 | vendor_nontrading | 0 |
| 2026-10-28 | sh601326 | vendor_nontrading | 0 |
| 2026-10-28 | sh605258 | vendor_nontrading | 0 |
| 2026-10-28 | sh688496 | vendor_nontrading | 0 |
| 2026-10-28 | sz002717 | vendor_nontrading | 0 |
| 2026-10-28 | sz002827 | vendor_nontrading | 0 |
| 2026-10-28 | sz301468 | vendor_nontrading | 0 |
| 2026-10-29 | sh601326 | vendor_nontrading | 0 |
| 2026-10-29 | sh605258 | vendor_nontrading | 0 |
| 2026-10-29 | sh688121 | vendor_nontrading | 0 |
| 2026-10-29 | sh688496 | vendor_nontrading | 0 |
| 2026-10-29 | sz002717 | vendor_nontrading | 0 |
| 2026-10-29 | sz002827 | vendor_nontrading | 0 |
| 2026-10-29 | sz301468 | vendor_nontrading | 0 |
| 2026-10-30 | sh601326 | vendor_nontrading | 0 |
| 2026-10-30 | sh605258 | vendor_nontrading | 0 |
| 2026-10-30 | sh688121 | vendor_nontrading | 0 |
| 2026-10-30 | sh688496 | vendor_nontrading | 0 |
| 2026-10-30 | sz002717 | vendor_nontrading | 0 |
| 2026-10-30 | sz002827 | vendor_nontrading | 0 |
