首次运行在读取具名元组报价时错误使用字典下标，进入第一笔订单前即以 `TypeError: tuple indices must be integers or slices, not str` 停止；未产出任何收益结果。原 `run-lock.json` 是失败运行前的锁。随后仅修正报价字段访问，下一次运行另存新锁。
