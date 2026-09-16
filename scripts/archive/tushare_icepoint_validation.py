#!/usr/bin/env python3
"""冰点机会信号·Tushare 多年历史终审（预注册骨架，2026-09-06）。

用户注册 tushare.pro 获取 token 后（环境变量 TUSHARE_TOKEN，接口
moneyflow_ind_dc 需要积分），本脚本把 retail-sentiment-ts 的终版信号
放到 2020 年起的多恐慌期上做最终审判。

预注册判定（写死，防挖矿）：
- 单元 = 恐慌事件（CN 冰点期，见下）内的信号触发组合；
- 通过标准：≥4 次恐慌事件，事件级 10 日超额胜率 ≥ 60%（多数事件同向）；
- 不通过（<50% 或方向分裂）→ 冰点机会信号降级为观察，页面标注更新；
- 强热警报同法复验（b200 数据需个股日线，用 tushare daily）。

数据边界声明：CN 冰点三票中「全A散户小单净流入」在 Tushare 无全史，
多年版以两票近似（两融余额变化 tushare margin 或东财 800 日 + 等权
指数动能），与单年版三票口径的差异如实标注。

用法：TUSHARE_TOKEN=xxx PYTHONPATH=src python3 scripts/tushare_icepoint_validation.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def main() -> int:
    token = os.environ.get("TUSHARE_TOKEN", "").strip()
    if not token:
        print("未设置 TUSHARE_TOKEN。请到 tushare.pro 注册 → 个人主页复制 token →\n"
              "export TUSHARE_TOKEN=xxx 后重跑（moneyflow_ind_dc 接口需要一定积分，\n"
              "积分不足时先完成新手任务/少量充值）。")
        return 1
    try:
        import tushare as ts
    except ImportError:
        print("未安装 tushare：pip3 install tushare")
        return 1
    pro = ts.pro_api(token)
    # 1) 行业资金流（东财源，含小单/超大单，2020 起）
    # 2) 两融余额（margin）与指数日线（daily）→ CN 冰点两票环境
    # 3) 板块日线 → r60/b50/b200 与 TS5 z（与单年版同口径）
    # 4) 事件研究：各恐慌事件的信号组合 10/20 日超额 → 事件级统计
    # 实现说明：以上管道与 retail_sentiment_ts_backtest 同构，token 就绪后
    # 按预注册标准输出判定；本骨架保持轻量以便先行审阅口径。
    print("token 已就绪；完整管道将在拿到 token 后的首个会话实现并执行（口径已预注册）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
