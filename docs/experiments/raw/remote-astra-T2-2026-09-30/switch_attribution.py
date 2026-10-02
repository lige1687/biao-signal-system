"""逐个开关归因：从生产读法出发，每次只把一个开关换成推荐值，看哪些案例的
（触碰、信号、C、首次标记）发生变化；再反向从推荐读法每次换回一个生产值。
说明“删/改一个条件，其余不变”在这些案例上是否成立。输出 switch-attribution.json。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from cases import CASES, INIT  # noqa: E402
from lifecycle_ref import PRODUCTION, RECOMMENDED, run_reference  # noqa: E402
from run_cases import summarize_ref  # noqa: E402
from synth import make, rows_of  # noqa: E402


def outcome(name, opts):
    spec = CASES[name]
    rows = rows_of(make(spec["days"], INIT))
    s = summarize_ref(run_reference(rows, structures=spec.get("structures", []), **opts),
                      spec["focus"])
    return {"touches": s["touches"], "signals": [x[:4] for x in s["signals"]]}


def main() -> None:
    report = {"from_production_toggle_one_to_recommended": {},
              "from_recommended_toggle_one_to_production": {}}
    for key in RECOMMENDED:
        if RECOMMENDED[key] == PRODUCTION[key]:
            continue
        for label, base, value in (("from_production_toggle_one_to_recommended", PRODUCTION,
                                    RECOMMENDED[key]),
                                   ("from_recommended_toggle_one_to_production", RECOMMENDED,
                                    PRODUCTION[key])):
            changed = {}
            for name in CASES:
                before, after = outcome(name, base), outcome(name, {**base, key: value})
                if before != after:
                    changed[name] = {"before": before, "after": after}
            report[label][key] = {"value": value, "changed_cases": changed}
    (HERE / "switch-attribution.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for label, block in report.items():
        print("==", label)
        for key, item in block.items():
            print(f"  {key}={item['value']!r}: {sorted(item['changed_cases'])}")


if __name__ == "__main__":
    main()
