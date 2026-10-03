# 发布和修订的模拟案例

此例只检验单一资产、单一指标、固定描述期间的版本选择，不是数据接口。
时间均为带时区的真实可用时间占位例；真实数据必须另有来源证据。

```python
from datetime import datetime

events = [
    {"available_at": "2026-04-20T16:00:00+08:00", "value": 10, "version": "first"},
    {"available_at": "2026-05-10T16:00:00+08:00", "value": 12, "version": "revision"},
]

def known_version(events, decision_at):
    decision = datetime.fromisoformat(decision_at)
    if decision.utcoffset() is None:
        raise ValueError("decision time needs a timezone")
    parsed = []
    for event in events:
        available = datetime.fromisoformat(event["available_at"])
        if available.utcoffset() is None:
            raise ValueError("availability time needs a timezone")
        parsed.append((available, event))
    eligible = [(t, e) for t, e in parsed if t <= decision]
    return max(eligible, key=lambda pair: pair[0])[1] if eligible else None
```

4月20日15时尚无值；4月21日只能知道10；5月11日才可知道修订值12。
同一可用时间有多个版本时，本例无法确定优先级，须先查明并处理重复。
未知时间不能以描述期间结束日代替。此函数假设允许相等，真实研究须核
发布、计算与下单的顺序；也不证明历史版本清单完整。
