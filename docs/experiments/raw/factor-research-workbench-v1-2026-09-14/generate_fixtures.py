"""合成夹具生成脚本（factor-research-workbench-v1）。

确定性生成三份协议的合成输入文件；不 import lei_signal（独立于被测代码）。
输出目录已存在时拒绝覆盖（排他），保证输入身份稳定。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "synthetic_inputs"


def write_csv(df: pd.DataFrame, name: str) -> None:
    path = OUT / name
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    df.to_csv(path, index=False)
    print("written", path.relative_to(HERE))


def write_json(data, name: str) -> None:
    path = OUT / name
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("written", path.relative_to(HERE))


def geometric_prices(dates, entities: dict[str, float], base=100.0) -> pd.DataFrame:
    t = np.arange(len(dates), dtype=float)
    frame = pd.DataFrame({"date": dates})
    for name, growth in entities.items():
        frame[name] = np.round(base * (1.0 + growth) ** t, 6)
    return frame


def numerical() -> None:
    dates = pd.bdate_range("2017-01-02", periods=300)
    write_csv(geometric_prices(dates, {"alpha": 0.01, "beta": 0.005, "gamma": 0.0}),
              "numerical_prices_3.csv")
    five = geometric_prices(dates, {"alpha": 0.01, "beta": 0.005, "gamma": 0.0,
                                    "delta": 0.002, "epsilon": 0.0})
    # epsilon 在验证段中间缺 5 天报价：缺值行必须保留并给缺失原因。
    five.loc[260:264, "epsilon"] = np.nan
    write_csv(five, "numerical_prices_5.csv")


def bars(path_desc: str, length: int) -> pd.DataFrame:
    """V 形或下行价格路径的 OHLCV 合成日K。"""
    closes = []
    if path_desc == "v":
        closes = [120.0 - i for i in range(25)]  # 120..96 下行25根
        closes += [97.0 + i for i in range(length - 25)]  # 97.. 上行
    else:
        closes = [130.0 - i for i in range(length)]
    close = pd.Series(closes, dtype=float)
    frame = pd.DataFrame({
        "date": pd.bdate_range("2019-01-01", periods=length),
        "open": close.shift(1).fillna(close - 1.0),
        "high": close + 0.5,
        "low": close - 0.5,
        "close": close,
        "volume": 1_000_000.0,
    })
    return frame


def state() -> None:
    write_csv(bars("v", 65), "state_bars_dm_a.csv")
    write_csv(bars("down", 65), "state_bars_dm_b.csv")

    dates = pd.bdate_range("2018-01-01", periods=260)
    wide = geometric_prices(dates, {"m1": 0.01, "m2": 0.008, "m3": -0.005, "m4": 0.012})
    # 成员变更日 idx=220：m4 加入名单；idx=250：m3 当日无报价（覆盖不足演示）。
    wide.loc[250, "m3"] = np.nan
    write_csv(wide, "state_breadth_close.csv")
    write_json({"universe": "synthetic_idx", "segments": [
        {"start": str(dates[0].date()), "end": str(dates[219].date()),
         "members": ["m1", "m2", "m3"]},
        {"start": str(dates[220].date()), "end": str(dates[259].date()),
         "members": ["m1", "m2", "m3", "m4"]},
    ]}, "state_membership.json")


def attribution() -> None:
    # 基准账户：初始100；d1 买1份@50 费1 → 现金49；d2 分红到账2 → 51；
    # d3 期末价55 → 总资产 51+55=106，净损益6，产品净贡献6。
    equity = pd.DataFrame({
        "date": ["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08"],
        "cash": [100.0, 49.0, 51.0, 51.0],
        "receivable": [0.0, 0.0, 0.0, 0.0],
        "equity": [100.0, 99.0, 103.0, 106.0],
        "units_100001": [0.0, 1.0, 1.0, 1.0],
    })
    write_csv(equity, "attribution_equity_base.csv")
    write_csv(pd.DataFrame({
        "date": ["2026-01-06"], "symbol": ["100001"], "side": ["buy"],
        "notional": [50.0], "fee": [1.0],
    }), "attribution_trades_base.csv")
    write_csv(pd.DataFrame({
        "event_id": ["div-001", "div-001"], "date": ["2026-01-07", "2026-01-07"],
        "event": ["receivable", "cash_paid"], "amount": [2.0, 2.0],
    }), "attribution_events_base.csv")
    write_json([{"event_id": "div-001", "symbol": "100001", "type": "cash_dividend",
                 "effective_date": "2026-01-07", "cash": 2.0,
                 "available_at": "2026-01-07T15:00:00+08:00"}],
               "attribution_actions_base.json")
    write_csv(pd.DataFrame({
        "date": ["2026-01-06", "2026-01-07", "2026-01-08"], "symbol": ["100001"] * 3,
        "close": [50.0, 52.0, 55.0],
    }), "attribution_prices_base.csv")

    # 变体账户：唯一动作差异 = d3 以55卖出（费率政策一致：卖1%→0.55）。
    equity_v = pd.DataFrame({
        "date": ["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08"],
        "cash": [100.0, 49.0, 51.0, 105.45],
        "receivable": [0.0, 0.0, 0.0, 0.0],
        "equity": [100.0, 99.0, 103.0, 105.45],
        "units_100001": [0.0, 1.0, 1.0, 0.0],
    })
    write_csv(equity_v, "attribution_equity_variant.csv")
    write_csv(pd.DataFrame({
        "date": ["2026-01-06", "2026-01-08"], "symbol": ["100001", "100001"],
        "side": ["buy", "sell"], "notional": [50.0, 55.0], "fee": [1.0, 0.55],
    }), "attribution_trades_variant.csv")

    # 应收未付变体：分红 d3 仍为应收（期末应收2、现金49、市值55 → 权益106）。
    equity_r = pd.DataFrame({
        "date": ["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08"],
        "cash": [100.0, 49.0, 49.0, 49.0],
        "receivable": [0.0, 0.0, 2.0, 2.0],
        "equity": [100.0, 99.0, 101.0, 106.0],
        "units_100001": [0.0, 1.0, 1.0, 1.0],
    })
    write_csv(equity_r, "attribution_equity_receivable.csv")
    write_csv(pd.DataFrame({
        "event_id": ["div-101"], "date": ["2026-01-07"], "event": ["receivable"],
        "amount": [2.0],
    }), "attribution_events_receivable.csv")
    write_json([{"event_id": "div-101", "symbol": "100001", "type": "cash_dividend",
                 "effective_date": "2026-01-07", "cash": 2.0,
                 "available_at": "2026-01-07T15:00:00+08:00"}],
               "attribution_actions_receivable.json")


def main() -> int:
    if OUT.exists():
        print(f"refusing to overwrite {OUT}")
        return 3
    OUT.mkdir()
    numerical()
    state()
    attribution()
    return 0


if __name__ == "__main__":
    sys.exit(main())
