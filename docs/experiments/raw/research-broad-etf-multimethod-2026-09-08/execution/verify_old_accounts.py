import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    lock = json.loads((HERE/"baseline-hashes.json").read_text())
    base = ROOT/lock["baseline_root"]
    checked = []
    for relative, digest in lock["aggregate"].items():
        path=base/relative; assert sha(path)==digest, path; checked.append(str(path))
    for account, digest in lock["account_summaries"].items():
        path=base/"account-results"/account/"summary.json"; assert sha(path)==digest, path; checked.append(str(path))
    print(json.dumps({"status":"matched","files":len(checked),"accounts":len(lock["account_summaries"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()

