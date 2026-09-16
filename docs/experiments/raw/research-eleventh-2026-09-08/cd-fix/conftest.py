from __future__ import annotations

import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ELEVENTH_SRC = HERE.parent / "research-package" / "src"
TENTH_SRC = HERE.parents[1] / "research-tenth-2026-09-08" / "cd-contract" / "research-package" / "src"
sys.path.insert(0, str(ELEVENTH_SRC))

# 先锁定本批两个目标模块，避免缺失依赖的回退路径替换待验代码。
from lei_signal.rules import module_d_false_breakout, two_b_reversal  # noqa: E402,F401
import lei_signal.rules  # noqa: E402

assert Path(two_b_reversal.__file__).resolve().is_relative_to(ELEVENTH_SRC)
assert Path(module_d_false_breakout.__file__).resolve().is_relative_to(ELEVENTH_SRC)

# 第十一隔离包尚未复制 long_trend/volume；原 10 项测试仅对这两个未改依赖
# 使用第十冻结副本。目标 C/D 始终保持上面的第十一模块对象。
lei_signal.rules.__path__.append(str(TENTH_SRC / "lei_signal" / "rules"))
