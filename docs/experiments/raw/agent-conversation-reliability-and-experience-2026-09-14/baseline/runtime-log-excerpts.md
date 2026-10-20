# 运行仓 logs/backend.err.log 摘录（2026-09-14 只读诊断）
## 9/14 当天 locked 堆栈计数：
0
## 历史 locked 证据（newsfeed/watchlist）末次出现行号：
23018:newsfeed gnews:英伟达 失败: database is locked
29830:sqlite3.OperationalError: database is locked
29913:sqlite3.OperationalError: database is locked
29996:sqlite3.OperationalError: database is locked
30079:sqlite3.OperationalError: database is locked
## 9/14 18:49-18:59 预热记录：
2026-09-14 18:49:20,975 INFO lei_signal.api.preheat 预热 index 完成（9 个标的，耗时 129.9s）
2026-09-14 18:55:21,439 INFO lei_signal.api.preheat 预热 overseas 完成（17 个标的，耗时 360.5s）
2026-09-14 18:55:21,441 INFO lei_signal.api.preheat 预热 fundamentals 完成（0 个标的，耗时 0.0s）
2026-09-14 18:56:21,490 INFO lei_signal.api.preheat 预热 fundamentals 完成（0 个标的，耗时 0.0s）
2026-09-14 18:57:21,581 INFO lei_signal.api.preheat 预热 fundamentals 完成（0 个标的，耗时 0.0s）
2026-09-14 18:58:21,681 INFO lei_signal.api.preheat 预热 fundamentals 完成（0 个标的，耗时 0.0s）
