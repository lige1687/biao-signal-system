from pathlib import Path
import sys
P=Path(__file__).resolve().parents[1]/'research-package/src'
sys.path.insert(0,str(P))
from lei_signal.rules import first_ma_pullback,strict_structure,two_b_reversal,module_d_false_breakout
for module in [first_ma_pullback,strict_structure,two_b_reversal,module_d_false_breakout]:
 assert Path(module.__file__).resolve().is_relative_to(P),module.__file__
