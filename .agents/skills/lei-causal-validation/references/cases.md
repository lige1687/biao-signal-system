# 模拟日期切分案例

以下为日期级案例；约定结果结束日须早于检验开始日，且该结果在拟合
时已可取得。真实资料另查供应商到达时刻。每个日期两只ETF一起划分。

```python
def training_rows(rows, train_end, eval_start):
    return [row for row in rows
            if row["date"] <= train_end and row["label_end"] < eval_start]

def evaluation_rows(rows, eval_start, eval_end):
    return [row for row in rows if eval_start <= row["date"] <= eval_end]
```

训练截止4月3日，检验4月6日至7日：

| 观察日期 | 结果结束日 | 两ETF归属 |
|---|---|---|
| 4月1日 | 4月3日 | 可进入训练 |
| 4月2日 | 4月6日 | 不能进入训练，结果尚未成熟 |
| 4月6日 | 4月8日 | 检验，等结果发生后才可评分 |
| 4月7日 | 4月9日 | 检验，等结果发生后才可评分 |
| 4月8日 | 4月10日 | 之后资料，不进入这次训练或检验 |

用训练值 `[1, 3]` 确定的平均值是2。把检验值1000加进去再求平均得到
334.6667，是未来信息改变了历史预处理方法，不能用于当时预测。
这些案例只验证资料选择，不测因子收益，也不验证完整研究程序。
