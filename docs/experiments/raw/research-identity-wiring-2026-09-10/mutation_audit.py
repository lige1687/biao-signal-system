#!/usr/bin/env python3
"""第五轮自查：故意注入错误，检验测试能否发现（变异检测）。

前四轮问的是「哪个字段没被核验」。本轮换方向问：
**如果某个环节坏了，现有测试能不能发现？**

做法：逐个把关键逻辑改坏 → 跑相关测试 → 看是否有测试失败。
- 有测试挂 = 该处受测试保护（好）
- 全部通过 = **覆盖假象**：那段逻辑坏了没人知道（要补测试）

每次注入后一律在 finally 中还原原文，绝不留下改坏的代码。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "src/lei_signal/research"

TESTS = [
    "tests/unit/test_research_data_quality.py",
    "tests/unit/test_research_data_snapshot.py",
    "tests/unit/test_research_calendar_and_identity.py",
    "tests/integration/test_research_offline_loop_round2.py",
    "tests/integration/test_research_data_snapshot_cli.py",
]

#: (编号, 说明, 文件, 原片段, 改坏后的片段)
MUTATIONS: list[tuple[str, str, str, str, str]] = [
    (
        "M1",
        "阻断级问题只降级为「有条件」，不再判为「不可用」",
        "data_quality.py",
        '        if blocking:\n            verdict = UNUSABLE',
        '        if blocking:\n            verdict = CONDITIONAL',
    ),
    (
        "M2",
        "快照哈希比较永远相等（篡改检测失效）",
        "data_snapshot.py",
        '        if _sha256_text(text) != item["normalized"]["sha256"]:\n'
        '            mismatches.append(rel)',
        '        if False:\n            mismatches.append(rel)',
    ),
    (
        "M3",
        "accept_structural 不再检查裁决是否为「不可用」",
        "data_quality.py",
        '    if accept_structural and verdict == CONDITIONAL and not blockers["fixable"]:',
        '    if accept_structural and not blockers["fixable"]:',
    ),
    (
        "M4",
        "身份映射不再检查交易所冲突",
        "symbol_identity.py",
        '    if registered and REGISTERED_PRODUCTS[code] != exchange:',
        '    if False:',
    ),
    (
        "M5",
        "取消非正价格检查",
        "data_quality.py",
        '        if (finite <= 0).any():',
        '        if False:',
    ),
    (
        "M6",
        "取消公司行动重复 event_id 检查",
        "data_quality.py",
        '        if eid in seen:',
        '        if False:',
    ),
    (
        "M7",
        "日历把未知日期当作交易日（即「回退为工作日」那个禁忌）",
        "trading_calendar.py",
        '        return DayStatus(\n            day=key,\n            status=UNKNOWN,\n'
        '            reason=f"{month} 不在已取月份内；未知，不回退为工作日",\n        )',
        '        return DayStatus(\n            day=key,\n            status=TRADING,\n'
        '            reason="MUTATED: 未知当作交易日",\n        )',
    ),
    (
        "M8",
        "取消「同一批混用价格口径」的拒绝",
        "data_snapshot.py",
        '    if len(bases) > 1:\n        raise AcquisitionFailed(',
        '    if False:\n        raise AcquisitionFailed(',
    ),
    (
        "M9",
        "fresh_dir 直接返回已存在的目录（会覆盖旧证据）",
        "data_snapshot.py",
        '    requested = Path(requested)\n    if not requested.exists():\n        return requested',
        '    requested = Path(requested)\n    if True:\n        return requested',
    ),
    (
        "M10",
        "audit_mapping 谎称行数已核对",
        "symbol_identity.py",
        '    rows_after: int | None = None\n    rows_verified = False\n'
        '    if mapped_frames is not None:',
        '    rows_after = rows_before\n    rows_verified = True\n'
        '    if mapped_frames is not None:',
    ),
    (
        "M11",
        "取消「声明日历权威却不给日历对象」的拒绝",
        "data_quality.py",
        '    if calendar_authority != "none" and calendar is None:\n        raise ValueError(',
        '    if False:\n        raise ValueError(',
    ),
    (
        "M12",
        "取消快照版本核对",
        "data_snapshot.py",
        '    if got_transform != TRANSFORM_VERSION:\n        raise AcquisitionFailed(',
        '    if False:\n        raise AcquisitionFailed(',
    ),
    (
        "M13",
        "取消产物用途声明的交叉核对",
        "data_quality.py",
        '    if declared_uses is not None and use not in set(declared_uses):',
        '    if False:',
    ),
    (
        "M14",
        "预热不足不再阻断（改为仅提示）",
        "data_quality.py",
        '                BLOCK,\n                "warmup_insufficient",',
        '                INFO,\n                "warmup_insufficient",',
    ),
    (
        "M15",
        "行动缺 available_at 时不再产生任何 finding",
        "data_quality.py",
        '    if without_available_at:\n        fully_unknown =',
        '    if False:\n        fully_unknown =',
    ),
]

#: 第二批：**故意挑没有专门回归测试的地方**。
#: 第一批 15/15 全中，但那是选择偏差——我挑的正是刚写过测试的点。
BATCH2: list[tuple[str, str, str, str, str]] = [
    (
        "N1", "差异检测永远判为「仅追加」，历史修订被掩盖",
        "data_snapshot.py",
        '"historical_revision" if differing else "append_only"',
        '"append_only"',
    ),
    (
        "N2", "交易日整池零报价不再报告",
        "data_quality.py",
        '    empty_days = [d for d in known_trading if d not in present]\n    if empty_days:',
        '    empty_days = [d for d in known_trading if d not in present]\n    if False:',
    ),
    (
        "N3", "部分产品缺报价被判为「完整」",
        "trading_calendar.py",
        '            else:\n                verdict = "partial_quotes"',
        '            else:\n                verdict = "complete"',
    ),
    (
        "N4", "覆盖检查漏掉最后一个月（off-by-one）",
        "trading_calendar.py",
        '        while (y, m) <= (ey, em):',
        '        while (y, m) < (ey, em):',
    ),
    (
        "N5", "observed_at 取首日而非末日",
        "data_snapshot.py",
        'observed_at=last.strftime("%Y-%m-%d") if last is not None else None,',
        'observed_at=(frame.index.min().strftime("%Y-%m-%d")'
        ' if not frame.empty else None),',
    ),
    (
        "N6", "合并报告只取第一份（其余检查全丢）",
        "data_quality.py",
        '    findings = tuple(f for r in reports for f in r.findings)',
        '    findings = tuple(reports[0].findings) if reports else ()',
    ),
    (
        "N7", "可知时点边界改为严格大于（发布当日被判为不可知）",
        "trading_calendar.py",
        '        known = str(as_of)[:10] >= published',
        '        known = str(as_of)[:10] > published',
    ),
    (
        "N8", "结构属性被并入可修缺陷（分类失效）",
        "data_quality.py",
        '            "fixable": sorted({f.code for f in rel if not f.structural}),',
        '            "fixable": sorted({f.code for f in rel}),',
    ),
    (
        "N9", "取消六位码长度校验",
        "symbol_identity.py",
        '    if not (code.isdigit() and len(code) == 6):',
        '    if not code.isdigit():',
    ),
    (
        "N10", "空交集检测永远为假",
        "symbol_identity.py",
        '        empty = not shared',
        '        empty = False',
    ),
    (
        "N11", "同日内容冲突被降级为普通重复",
        "data_quality.py",
        '                Finding(\n                    BLOCK,\n'
        '                    "duplicate_conflict",',
        '                Finding(\n                    WARN,\n'
        '                    "duplicate_conflict",',
    ),
    (
        "N12", "导入映射不再检测重复身份（不同代码可合并成一只）",
        "data_snapshot.py",
        '            if mapped in symbol_mapping.values():',
        '            if False:',
    ),
    (
        "N13", "绑定不再强制用途（uses/not_for 失效）",
        "data_snapshot.py",
        "            card = d.resolve(registry, ref, purpose) if purpose"
        " else d.resolve(registry, ref)",
        "            card = d.resolve(registry, ref)",
    ),
    (
        "N14", "失败的请求不计入预算（预算泄漏）",
        "data_snapshot.py",
        "        except Exception as exc:  # noqa: BLE001 - 如实记录后原样上抛\n"
        "            self.calls.append(",
        "        except Exception as exc:  # noqa: BLE001\n            _ = exc\n"
        "            raise\n        if False:\n            self.calls.append(",
    ),
]

MUTATIONS = MUTATIONS + BATCH2


def run_tests() -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *TESTS, "-q", "--no-header", "-x", "--tb=no"],
        cwd=ROOT, capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout.strip().splitlines()[-1] if proc.stdout else ""


def main() -> int:
    print("先确认未注入时全绿…")
    code, line = run_tests()
    if code != 0:
        print(f"基线就不通过，停止：{line}")
        return 2
    print(f"  基线：{line}\n")

    results = []
    for tag, desc, filename, old, new in MUTATIONS:
        path = SRC / filename
        original = path.read_text(encoding="utf-8")
        if old not in original:
            results.append((tag, desc, "SKIP", "片段未找到（代码已变，需更新变异定义）"))
            print(f"{tag} SKIP  {desc}")
            continue
        try:
            path.write_text(original.replace(old, new, 1), encoding="utf-8")
            code, line = run_tests()
            caught = code != 0
            results.append((tag, desc, "CAUGHT" if caught else "MISSED", line))
            print(f"{tag} {'CAUGHT' if caught else '❌ MISSED'}  {desc}")
            if not caught:
                print(f"      → 覆盖假象：改坏了但测试全过（{line}）")
        finally:
            path.write_text(original, encoding="utf-8")   # 一律还原

    print("\n=== 汇总 ===")
    missed = [r for r in results if r[2] == "MISSED"]
    skipped = [r for r in results if r[2] == "SKIP"]
    print(f"注入 {len(results)} 处：被发现 {len(results)-len(missed)-len(skipped)}，"
          f"漏检 {len(missed)}，跳过 {len(skipped)}")
    for tag, desc, _, _last in missed:
        print(f"  ❌ {tag} 漏检：{desc}")

    print("\n还原核对：")
    code, line = run_tests()
    print(f"  {'全绿 ✅' if code == 0 else '⚠️ 未还原干净'} {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
