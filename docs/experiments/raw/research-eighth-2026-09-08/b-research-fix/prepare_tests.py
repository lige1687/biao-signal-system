from pathlib import Path
P=Path(__file__).resolve().parent
s=(P/'seventh-evidence/synthetic_checks.py').read_text()
s=s.replace("import ast, dataclasses, hashlib, json, sys, traceback", "import argparse, ast, dataclasses, hashlib, json, sys, traceback")
s=s.replace("OUT=ROOT/'attempt-01'; OUT.mkdir(exist_ok=False)", "parser=argparse.ArgumentParser();parser.add_argument('--attempt',required=True);args=parser.parse_args()\nOUT=ROOT/args.attempt; OUT.mkdir(exist_ok=False)")
s=s.replace("'snapshot/", "'research-package/").replace("'input-manifest.json'", "'source-manifest.json'")
s=s.replace("(ROOT/'research-package/src/lei_signal'/rel).read_text()", "(ROOT/('research-package/src/lei_signal' if rel=='backtest/engine.py' else 'frozen-provenance/src/lei_signal')/rel).read_text()")
s=s.replace("'snapshot_all_match':all(sha(ROOT/x['copy'])==x['sha256'] for x in manifest['files'])", "'source_all_match':all(sha(__import__('pathlib').Path(x['source']))==x['sha256'] for x in manifest['files'])")
s=s.replace("'snapshot_mismatches':snapshot_bad", "'intended_research_copy_changes':snapshot_bad")
(P/'replay16.py').write_text(s)
