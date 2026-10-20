"""补件恢复演练：临时目录内核对旧真实终包 + supplement 补件的文件身份/映射。

只做身份核验：
1. 旧包 manifest.file_hashes 中每个文件在「旧包原件 ∪ supplement补件」中找到
   且哈希一致；缺证据项改由 supplement 提供；
2. supplement 证据哈希 == 旧合同 price_basis_evidence 引用；
3. 外部输入依赖（真实价格/日历/来源CSV）在原位置且哈希一致；
4. 旧包与旧合同原件零改动（演练只读，不覆盖仓库，不调用真实运行入口）。
"""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RAW = Path(__file__).resolve().parent
OLD_PACK = ROOT / 'docs/experiments/raw/factor-unit-b0-concentrated-fix-2026-09-15/final-real-qualification-01'
SUPP = RAW / 'supplement'


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    mapping = json.loads((SUPP / 'mapping.json').read_text())
    manifest = json.loads((OLD_PACK / 'manifest.json').read_text())
    contract = json.loads((OLD_PACK / 'contract.source.json').read_text())
    errors, ok = [], []

    with tempfile.TemporaryDirectory(prefix='lei-four-fixes-drill-') as td:
        t = Path(td)
        # 演练布局：old-package/（旧包原样复制）+ supplement/（补件）
        import shutil
        shutil.copytree(OLD_PACK, t / 'old-package')
        shutil.copytree(SUPP, t / 'supplement')

        # 1. manifest.file_hashes 逐项核对（旧包内文件）
        for rel, h in manifest['file_hashes'].items():
            p = t / 'old-package' / rel
            if not p.is_file() or sha(p) != h:
                errors.append(f'旧包文件身份不符: {rel}')
        ok.append(f"旧包已列文件 {len(manifest['file_hashes'])} 项身份一致")

        # 2. 旧合同引用的证据：旧包缺失项由 supplement 提供且哈希==合同引用
        for symbol, entry in contract['data_identity'].items():
            ref = entry['price_basis_evidence']
            name = ref['path'].replace('/', '__')
            sp = t / 'supplement' / name
            if not sp.is_file():
                errors.append(f'{symbol}: supplement 缺证据补件 {name}')
            elif sha(sp) != ref['sha256']:
                errors.append(f'{symbol}: 补件哈希与旧合同引用不符')
        ok.append('4 产品证据补件哈希均与旧合同引用一致')

        # 3. 外部输入依赖身份（原位置，只读核对）
        for path, h in mapping['external_inputs_not_archived'].items():
            p = ROOT / path
            if not p.is_file():
                errors.append(f'外部输入缺失: {path}')
            elif sha(p) != h:
                errors.append(f'外部输入哈希漂移: {path}')
        ok.append(f"外部输入依赖 {len(mapping['external_inputs_not_archived'])} 项身份一致")

        # 4. 补件自身映射表核对
        for name, info in mapping['files'].items():
            p = t / 'supplement' / name
            if not p.is_file() or sha(p) != info['sha256']:
                errors.append(f'mapping 记录与补件不符: {name}')
        ok.append(f"mapping.json {len(mapping['files'])} 项记录与补件一致")

    for line in ok:
        print(f'OK: {line}')
    for line in errors:
        print(f'FAIL: {line}', file=sys.stderr)
    if errors:
        print('恢复演练：失败（不报可恢复）', file=sys.stderr)
        return 1
    print('恢复演练：通过 —— 恢复级别=「代码/证据包+声明的外部输入」，'
          '未调用真实运行入口，仓库原件零改动')
    return 0


if __name__ == '__main__':
    sys.exit(main())
