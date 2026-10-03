# 独立完整检出的失败与替代恢复

第一次 `git clone --no-local --no-hardlinks <已推送发布副本> <独立restore-checkout>` 的Git复制完成，但文件检出遇到 `No space left on device`，退出128，未成为可运行完整副本。随后最低检查因缺定义/源码/测试等失败，完整记录见 validation-attempt-01-incomplete-checkout.json；不能称通过。

检查失败时磁盘剩余195,608,576字节。原仓库包含22,532个Git文件，整仓库检出不是本任务最低材料。没有删除、clean、reset、杀进程或清走别人修改。替代方法在新独立目录只恢复manifest指定材料，用APFS写时复制生成独立文件和独立Git对象副本；没有硬链接或Git对象alternates。内容仍逐项SHA检查。跨机器Git传输建议稀疏检出，只取本任务路径；Linux/Windows未实测。

防错：再次恢复先核剩余空间与所需范围。完整项目源码/全部研究资料不因本任务验收而都需要检出；必要文件以manifest为准，未知或额外输入须单独取得资格。旧锁和旧结果不改写。

## 最小恢复第二次检查找到的真实配置依赖

只恢复最初manifest后，SHA检查通过，但规则运行失败：源码实际默认读取 configs/rules.v2.yaml，原manifest只列v1。这说明只有指纹/导入通过不能证明任务可运行。已补实际v2默认配置及目录校验器的MUST_TRACK配置/报告数据路径；不改规则内容。
独立Git对象副本来自第一次检出失败的clone，其index尚未建立，目录检查误报未跟踪。用 git read-tree HEAD 只恢复独立验证目录的Git索引，未重置共享目录或覆盖工作文件。未物化的其他历史资料仍保留为未检出，不冒称完整仓库干净。第二次失败及测试输出保存于 validation-attempt-02-minimum-input-gap.json。
