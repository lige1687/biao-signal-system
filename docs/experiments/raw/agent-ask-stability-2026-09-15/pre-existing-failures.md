# 既有失败（与本分支无关，开工即存在）

## tests/unit/test_agent_name_resolve.py::test_catalog_layer_resolves_index_not_in_watchlist

- 现象：`agent_mod._resolve_symbol_by_catalog("科创板块现在怎么看")` 期望命中
  别名表「科创 → 000688.SS」，实际返回 None。
- 复现：本分支与 main（90df76b6，临时 worktree 核对）表现一致——**main 上同样失败**，
  不是本轮改动引入。
- 直接原因（只读分析）：`_resolve_symbol_by_catalog` 开头先走
  `named_subject(message)` / `asks_for_sector(message)`——「科创板块现在怎么看」
  含「板块」，`asks_for_sector` 为真，函数提前 `return named`（None），
  别名表被短路。该短路是 2026-09-15 名称/板块轮（cb71cad6）引入的行为。
- 影响面评估：仅「口语别名 + 板块二字」组合（科创板块/恒生科技板块 这类）
  不再落到别名表；板块问题按新设计走板块识别。是否属于该轮有意的行为变更，
  需主控裁决——本轮不改对象识别语义（属已验收功能区），如实记录。
- 同文件其余 8 条全部通过；名称/板块/ETF 区分专项（test_agent_subject_names）
  全过。
