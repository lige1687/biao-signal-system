"""为上一轮真实终包（final-real-qualification-01）生成补件目录 supplement/。

补件 = 旧合同副本 + 缺失的 real-evidence.json 原件 + 旧包 manifest 副本 +
对应 SHA 映射表 + README（含外部输入依赖清单）。

原则：
- 旧真实终包与旧合同保持原样，不改一字节；
- 补件只从原合同与原件只读复制，不运行真实计算/资格，不代表新代码重新执行过；
- 核对证据文件与旧合同引用哈希一致；不一致则报不可恢复（非零退出），不改旧合同；
- 原价格输入不随包复制，README 明确列出外部输入依赖路径/哈希：恢复级别是
  「代码/证据包 + 声明的外部输入」，不是无任何外部依赖的一包复放。
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RAW = Path(__file__).resolve().parent
OLD_RAW = ROOT / 'docs/experiments/raw/factor-unit-b0-concentrated-fix-2026-09-15'
OLD_PACK = OLD_RAW / 'final-real-qualification-01'
SUPP = RAW / 'supplement'


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    if SUPP.exists():
        print(f'REFUSE: {SUPP} 已存在（新输出排他创建）', file=sys.stderr)
        return 3
    contract = json.loads((OLD_PACK / 'contract.source.json').read_text())
    manifest = json.loads((OLD_PACK / 'manifest.json').read_text())

    # 1. 旧合同引用的每份 price_basis_evidence 必须与原件哈希一致
    evidence_refs = {}
    for symbol, entry in contract['data_identity'].items():
        ref = entry['price_basis_evidence']
        src = ROOT / ref['path']
        if not src.is_file():
            print(f'不可恢复：{symbol} 证据原件不存在 {ref["path"]}', file=sys.stderr)
            return 4
        actual = sha(src)
        if actual != ref['sha256']:
            print(f'不可恢复：{symbol} 证据原件哈希与旧合同引用不符 '
                  f'（合同 {ref["sha256"][:16]}… 实际 {actual[:16]}…）；不改旧合同',
                  file=sys.stderr)
            return 4
        evidence_refs[ref['path']] = actual

    # 2. 外部输入依赖（不随包复制）：真实价格输入、日历、来源裁定CSV
    external_inputs = {}
    for symbol, entry in contract['data_identity'].items():
        external_inputs[entry['path']] = entry['sha256']
    sd = contract['source_decision']
    external_inputs[sd['path']] = sd['sha256']
    for cal in contract['calendar_identity'].values():
        if isinstance(cal.get('source'), dict):
            external_inputs[cal['source']['path']] = cal['source']['sha256']

    SUPP.mkdir()
    shutil.copy2(OLD_PACK / 'contract.source.json', SUPP / 'contract.source.json')
    shutil.copy2(OLD_PACK / 'manifest.json', SUPP / 'manifest.old-package.json')
    ev_names = {}
    for path in evidence_refs:
        name = path.replace('/', '__')
        shutil.copy2(ROOT / path, SUPP / name)
        ev_names[path] = name

    mapping = {
        'note': '为旧运行（final-real-qualification-01，exit_code=2/restricted）补齐证据，'
                '不代表新代码重新执行过；旧包与旧合同原件未改。',
        'old_package': str(OLD_PACK.relative_to(ROOT)),
        'files': {
            'contract.source.json': {
                'from': str((OLD_PACK / 'contract.source.json').relative_to(ROOT)),
                'sha256': sha(SUPP / 'contract.source.json'),
            },
            'manifest.old-package.json': {
                'from': str((OLD_PACK / 'manifest.json').relative_to(ROOT)),
                'sha256': sha(SUPP / 'manifest.old-package.json'),
            },
            **{ev_names[p]: {'from': p, 'sha256': evidence_refs[p]}
              for p in evidence_refs},
        },
        'evidence_matches_old_contract': True,
        'external_inputs_not_archived': external_inputs,
        'old_package_exit_code': manifest['exit_code'],
        'old_package_qualification_status': manifest['qualification_status'],
    }
    (SUPP / 'mapping.json').write_text(
        json.dumps(mapping, ensure_ascii=False, indent=1) + '\n')

    ext_lines = '\n'.join(f'- `{p}`\n  sha256: `{h}`'
                          for p, h in sorted(external_inputs.items()))
    ev_lines = '\n'.join(f'- `{ev_names[p]}` ← `{p}`\n  sha256: `{d}`'
                         for p, d in sorted(evidence_refs.items()))
    (SUPP / 'README.md').write_text(f"""# 旧真实终包证据补件（supplement）

为上一轮真实资格包 `factor-unit-b0-concentrated-fix-2026-09-15/final-real-qualification-01`
（exit_code=2，restricted）补齐其合同引用但未随包保存的价格证据原件。

**本补件为旧运行补齐证据，不代表新代码重新执行过；不运行真实计算/资格；
旧包与旧合同原件保持原样未改。** 证据文件与旧合同引用哈希已逐一核对一致
（见 mapping.json，evidence_matches_old_contract=true）。

## 补件内容

- `contract.source.json` — 旧包运行合同副本（原字节）
- `manifest.old-package.json` — 旧包 manifest 副本
{ev_lines}

## 外部输入依赖（不随包/补件复制）

恢复级别是「代码/证据包 + 声明的外部输入」，**不是**无任何外部依赖的一包复放。
以下输入保持原位置原哈希，恢复演练只核对其身份：

{ext_lines}
""", encoding='utf-8')
    print(f'supplement written: {SUPP}')
    for p, d in sorted(evidence_refs.items()):
        print(f'  evidence ok: {p} == {d[:16]}…（与旧合同引用一致）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
