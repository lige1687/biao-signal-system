"""LEI 监督员 v1：计划台账 + 监督判定 + 漂移复议 + 待办催办。

判定层（Python 纯函数，可测，无 LLM）：store / monitor / drift / actions / grounding。
表达层（LLM / ark）只在 P4 接入，且只渲染 alert、过白名单校验、两次失败降级模板。

设计原则：判定权在 Python，不在 LLM。P0–P3 全程零 LLM 调用。
"""
