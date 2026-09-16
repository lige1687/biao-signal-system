"""生成本轮正式合成正/负合同：结构沿用上一轮 b0fix-synthetic-positive-contract.json，
所有哈希按当前工作区实际文件重算（代码已修，旧合同内的代码指纹必然失效）。

负例 = 正例基础上把一个必需代码键哈希清零（身份错误，预期退出3）。
不联网、不读真实缓存、不计算任何因子/收益。
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RAW = Path(__file__).resolve().parent
OLD = ROOT / 'docs/experiments/raw/factor-unit-b0-concentrated-fix-2026-09-15/b0fix-synthetic-positive-contract.json'


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def refresh_ref(ref):
    p = ROOT / str(ref['path'])
    return {'path': ref['path'], 'sha256': sha(p)}


def main() -> None:
    contract = json.loads(OLD.read_text())
    contract.pop('_repo_root', None)
    contract['candidate_card'] = refresh_ref(contract['candidate_card'])
    contract['source_decision'] = refresh_ref(contract['source_decision'])
    contract['code_identity'] = {k: sha(ROOT / k) for k in contract['code_identity']}
    contract['standards'] = [
        {'path': s['path'], 'version': s['version'], 'sha256': sha(ROOT / s['path'])}
        for s in contract['standards']
    ]
    for entry in contract['data_identity'].values():
        entry['sha256'] = sha(ROOT / entry['path'])
        entry['price_basis_evidence'] = refresh_ref(entry['price_basis_evidence'])
    for cal in contract['calendar_identity'].values():
        for key in ('source', 'synthetic_schedule'):
            if isinstance(cal.get(key), dict):
                cal[key] = refresh_ref(cal[key])

    pos = RAW / 'four-fixes-synthetic-positive-contract.json'
    pos.write_text(json.dumps(contract, ensure_ascii=False, indent=1) + '\n')

    neg = json.loads(json.dumps(contract))
    neg['code_identity']['src/lei_signal/rules/dual_ma.py'] = '0' * 64
    neg_path = RAW / 'four-fixes-synthetic-negative-contract.json'
    neg_path.write_text(json.dumps(neg, ensure_ascii=False, indent=1) + '\n')
    print(pos)
    print(neg_path)


if __name__ == '__main__':
    main()
