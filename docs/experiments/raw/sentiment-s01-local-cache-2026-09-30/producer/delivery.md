# S01 本地自算宽度：生成链路交接

用户的本地自算宽度有明确的生成代码，先前的只读数据库核查也已发现数值行。这里核的是另一件事：这些旧日期数值能否代表**当时的**标普 500 成分，并在当时可用于判断。单凭代码仍不能认定。

主回填脚本从一份成分名单取股票，向 Akshare/Sina 请求未复权的历史收盘价，再按每日有收盘价且能算出 20 日或 50 日均线的股票分别计算比例；内部缺价仅在均线计算时沿用最近价格。见 `scripts/backfill_breadth_full.py:70-78,99-120,155-184,195-211`。它没有按历史日期切换成分。另一条 `us_breadth.py` 生产同名 JSON，却不沿用缺价计算均线，且默认只保留最后 1260 个交易日；尾部刷新也会用后一种算法重写全史 JSON。见 `src/lei_signal/market_context/us_breadth.py:123-183` 和 `scripts/archive/refresh_sp500_breadth_tail.py:33-71`。

JSON 可转成回测 parquet 的 `b20/b50/b200`，但转换不保留成分、分母、数据版本和可得时间（`scripts/backfill_timing_data.py:130-145`）。另有归档路径请求 yfinance 复权价，直接替换该 parquet 和收盘价矩阵，却不更新 JSON（`scripts/archive/fetch_us_adjusted_matrix.py:20-62`；`scripts/archive/rebuild_us_breadth_qfq.py:20-43`）。因此同名 parquet 与 JSON 不保证同版。SQLite 入库脚本从 JSON 取宽度数值、从当前矩阵另算分母，并把 `available_at` 设为行情日期、`formal` 和 `complete` 设为固定标签（`scripts/archive/ingest_sp500_breadth_to_sqlite.py:100-119,169-219`）；这些标签不能证明真实历史发布时间或历史成分。

之前仓库核查观察到的是 2026-08-04 的成分名单快照；数据库只读核查发现固定 494 只成分的旧日期数值和同日 `available_at`。这确认本地有自算宽度，不证明 2008 年等旧日期包含当年已退出的公司。下一步应由主控只读比对实际缓存字节、版本和历史成员/价格来源；在此之前不进行 S01 收益检验。

本执行者只读取冻结合同、`AGENTS.md`、本轮研究状态、上轮 S01 核查文件，以及合同列出的仓库脚本和 `market_context` 模块。只写本目录 `lineage.json` 与 `delivery.md`；未访问用户仓外缓存、数据库或网络，未运行收益计算，未改代码。
