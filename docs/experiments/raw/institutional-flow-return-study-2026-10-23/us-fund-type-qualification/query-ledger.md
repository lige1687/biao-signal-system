# 查询与访问记录（2026-10-23）

工具：公开网页检索/打开 SEC 及发行人原始文件；未登录、购买、下载大包或调用账户。查询按用途合并记录，URL 的成功与失败以 `sources.md` 中精确链接为准。原先只留了分组查询，没有逐次请求日志，**首次核查的精确查询/打开次数未知**，不能由分组数充作次数。后续补查实际执行了 1 次网页工具调用，含 2 个 `open` 和 2 个 `find` 请求。

| 查询组 | 实际搜索或打开的关键字 / 路径 | 结果 |
|---|---|---|
| 早期原件 | `site:sec.gov/Archives/edgar/data/866256/ 2019 Parnassus Core Equity 497K`, `000119312519133114`；2020 Core Equity 497 | 2019 索引可读且确认系列/份额；初次访问单独 HTML `d686400d497k.htm` 网页工具返回 inaccessible。补查时同一 accession 的 SEC 完整提交 `.txt` 成功读到正文第 316–338 行，补上 2019 策略原件。初次访问失败仍保留在此。 |
| Contrafund 2019/20 | `site:sec.gov/Archives/edgar/data/24238/ 2020 Contrafund summary prospectus 497K FCNTX`, 2019/2020 `Principal Investment Strategies`, 2019 `485BPOS`, 2021 `000137949121000753` | 2019 485BPOS 的所读 `filing706.htm` 仅签名页；未找到可读 2019/20 SEC 497K 正文；2021 497K 正文成功，2022/23/26 锚点成功。补查的 2019 大学退休计划原件是当年简介，不是招募书。 |
| Magellan 早期 | `2019 Fidelity Magellan 497K FMAGX S000007112`, `000137949119002859`, 2020 497K；2019-12-31 NPORT `000175272420036361` | 2019/2020 策略原件成功；2019-12 NPORT XML 可定位，但按 accession 构造的 SEC 索引 URL 在网页工具中 inaccessible。 |
| Dodge & Cox 早期 | `2019 Dodge Cox Stock DODGX prospectus 485BPOS`, `2020 Dodge Cox Stock prospectus`, 2019-12-31 NPORT `000114554920011997`, 2020-03-31 NPORT | 2019/2020 招募书成功；2019-12 NPORT 申报头可读，2020-03 可作额外检查但未写入主表。 |
| 中间年份与近期 | 四基金各自 SEC `2022/2023/2026` summary/full prospectus；已有 2024/25 原件 | 中间若干年份可定位；不等于每份修订已比对。 |
| 公开制度 | SEC `2019 form n-port third month publicly available upon filing`, 2024 NPORT amendments, `2025 postponement`, `2026 proposal`, SEC NPORT data sets | 官方 2019、2025 规则及 2026 提案成功；用申报而非镜像数据集日期作时点。 |
| EDGAR 受理例子 | 三只 2019-12-31 `NPORT-P` 原始索引及 `Accepted`；尝试 Magellan 索引 | 三只原始索引/申报头成功；Magellan 索引访问失败，故未用。 |

未用网页搜索返回的第三方排名、回报表或基金介绍推断基金类型；没有做与结果相关的选样。

补查原始 `open` 请求：`https://www.sec.gov/Archives/edgar/data/866256/000119312519133114/0001193125-19-133114.txt`、`https://www.bu.edu/hr/documents/Fidelity_Contrafund_Fact_Sheet.pdf`，均成功；`find` 分别检索 `80% of its net assets` 和 `FCNKX`，均成功定位。波士顿大学页面由计划主办方发布，其性质已在结论中限定。
