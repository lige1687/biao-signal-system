# 基线文件恢复入口

此包按原路径恢复19份文件，供人工恢复和后续核验使用。先从 `baseline-delivery-manifest.json` 读取路径、字节数与SHA-256，再逐项核对。原始交付资格记录保存在 `baseline-delivery-qualification.json`，保持原字节；本轮对第3项的中控决定见 `central-review-decision.json`。

本包只证明这些文件按原字节进入此分支。19项原作者均未确认，快照整理人不是原作者；本包不证明纯Git研究流程可运行、不构成生产采用，也不启动或授权任何市场研究。
