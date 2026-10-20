"""因子观测台 · 预计算 CLI。

用法：
    python3 scripts/precompute_factor_panel.py          # 用默认缓存目录
    LEI_CACHE_ROOT=/path python3 scripts/precompute_factor_panel.py

产出 ``$LEI_CACHE_ROOT/factor_panel_snapshot.json``，由 ``/api/factors/panel`` 读取。
板块中文名来自 ``lei_signal.api.labels.THS_INDUSTRY_NAMES``（仓库内权威映射）。
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lei_signal.api.labels import THS_INDUSTRY_NAMES  # noqa: E402
from lei_signal.market_context import factor_panel  # noqa: E402


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    name_map = {f"TH{num}.SECTOR": name for num, name in THS_INDUSTRY_NAMES.items()}
    snap = factor_panel.build_panel(name_map=name_map)
    print(
        f"因子面板快照完成：{snap['counts']['symbols']} 标的 / {snap['counts']['sectors']} 板块，"
        f"数据截止 {snap['data_as_of']}，落盘 {factor_panel._panel_path()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
