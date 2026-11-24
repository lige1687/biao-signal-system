# B04 runner 参数及授权适配计划

状态：仅计划，未修改或生成可执行B04 runner。基准runner SHA c9ee0652a026f59ce7b688617752aa8e84add16354ea0317fef20b19aee16cc1；其独审仅适用于原B03输入与身份。

## 必须改的差异

| 位置 | 原状态 | B04必须达到 |
|---|---|---|
| Embedded contract/baseline/execution identity constants (lines10..43) | B03 contract a273..., old selected120/remaining233/reconciliation inputs, amendment de5 hardcodes B03-run02 and only known run01 | Embed exact reviewed B04 contract 016b0b016907a5991fe740f1865614bff48a6dad05dd2b06af617e3b33d068be; selected79/remaining113/deferred34 and audited source hashes; new B04 execution-binding with BOTH B03 consumed attempts. Keep de5 solely protocol provenance, not a B04 release. |
| build_queries | Selected count exactly120, B03-specific text | Expected selected count79 from frozen B04 contract, unique79/date/code/deterministic ordering, ten calls and all original cap values stay mandatory. |
| validate_baseline_inputs | CSV six fields;120selected/233remaining/31partitions/113deferred; only12 B01/B02 files | Explicit reviewed four-field audited schema; selected79 subset remaining113, 21 partitions top10, deferred34; exact23 B01/B02+run02 data files. All reported hashes must be read back; do not spoof old input names or source status. |
| validate_current_dedup | Proof keys selected_120/remaining_233; only1 prior B03 attempt and known run01 5 files | New B04 contract/runner/execution-binding/attempt/root identity, actual selected79 still unqueried, both B03 attempts with5 history files each plus23 data baseline files/20 consumed daily windows, unknown additional attempt rejected. New proof required; original32ae/a79f hashes and old de5 grant cannot authorize B04. |
| Top-level CLI/authority gate lines146..200 | --release-amendment-sha256 matches consumed de5 B03-run02 identity | Require release-contract-sha256 exact B04 hash and fresh B04 execution-binding hash; de5 protocol-policy evidence not accepted as execution authority. Gate all writes/socket setup on new current proof and nonexistent B04 root. Missing/wrong/old grants all fail before writes or network. |
| write_portable_receipt/final message | Assertions selected120/deferred113 and consumed_run01 only; B03 schema/output texts | Exactly79 keys/34 deferred, B04 identity/output messages, retained both consumed B03 attempts and accurate cumulative sessions. Any first error must preserve partial/unattempted categories and consumed counts; no normal-row promise. |
| Module-level manifest/state/provenance/success messages and test fixture identities | Any B03-specific identity, baseline payload filenames, old proof hashes or consumed_run01-only provenance in globals and snapshots | Audit the complete AST literal inventory plus embedded payloads; B03 can appear only in explicitly labelled immutable predecessor provenance. B04 runtime grants, selection counts, CSV names and output messages must bind B04; old manifests/proofs are evidence only. |

## 必须保持的程序保护

准确函数源码指纹见runner-adaptation-readonly-check.json，cloud准备时核对函数差异，不能顺手改协议或保护条件。以下函数应逐字保留；若不得不改，必须单独指出原因、给实际diff并扩大相关独审，不能认为仍自动继承旧绿色测试：

validate_output_root, execute_declared_queries, bounded_official_decompress, validate_response_envelope, audited_send_msg, storage_check, append_ledger, verify_request, validate_daily_record, selected_key_accounting, qualify_result, persist_wire_chunk, run_call, stop_after_call

原函数源码指纹取AST定位的完整函数文本UTF8，不等于整文件SHA；整文件指纹单独记录。B03前身的标签可在明确的历史来源字段中保留，不能残留为活动查询数量、输入文件、当前attempt或许可条件。

## 必须验证的失败情况

- selected120 old CSV rejected
- remaining233/31 partition old inputs rejected
- missing B03-run02 history rejected
- altered run01/run02 evidence rejected
- unreviewed additional attempt rejected
- old B03 a273 contract or32ae/a79f proof rejected
- old de5 execution grant rejected even if protocol reused
- wrong attempt ID/root or existing output rejected
- missing/incorrect fresh B04 execution binding rejected
- 79selected+34deferred category accounting on success/error/empty/status0
- all prior budgets/pace/deadline/storage/no-retry guards unchanged
- real87/88 login and621 mixed response replay; historical rows not new B04 evidence
- unknown server/trailer forms fail; numeric daily checksum unknown preserved

## 本次实际检查及未做事项

本次AST静态定位和只执行纯build_queries的兼容检查已确认旧runner拒绝新79键；旧a273 contract SHA与新合同不同，旧proof的contract/attempt/root也全部不属于B04。新执行绑定尚未写出，故不能声称B04旧授权拒绝测试已通过；上述列为新runner必须通过的测试。没有普通runner入口、supplier socket、新登录或查询，也没有安装。

不能机械全局把120替换成79、233替换成113、113替换成34：原历史和字段指纹中的这些数字必须保留。应把当前批次计数从新冻结合同读取，把完整既有历史从准确源绑定读取；不开放任意CLI参数修改冻结范围或上限。

## 云端交回的最小结果

实际修改后的runner/新的B04执行绑定、精确SHA、实际patch、既有14项保护函数原文本指纹对比、覆盖上述失败情况的离线输出、无真实网络的current预检入口。先独审新字节，再本机current readback，最后父线程批准新许可。原B03 run01/run02目录与失败原件保留，不能重放。
