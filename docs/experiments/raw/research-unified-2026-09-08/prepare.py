from pathlib import Path
import json,hashlib,shutil,datetime
P=Path(__file__).resolve().parent;R=P.parents[3];OLD=R/'docs/experiments/raw/research-first-round-2026-09-08';OUT=P/'e01';(OUT/'inputs/cache').mkdir(parents=True,exist_ok=True)
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=[]
def copy(src,dst):
 before=h(src);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst);assert before==h(src)==h(dst);files.append({'source':str(src),'snapshot':str(dst),'sha256':before,'bytes':dst.stat().st_size})
for s in ['SH000001','SZ399001','000300','000015','399006','510500','512100','588000','breadth_cn_all']:
 original=OLD/'dca/snapshot/cache'/f'{s}.parquet';src=original if original.exists() else Path('/Users/yongbiaoli/.lei_signal_lab/cache/timing')/f'{s}.parquet';copy(src,OUT/'inputs/cache'/src.name)
for src,dst in [(OLD/'dca/snapshot/source/scripts/dca_complete_trades_study.py',OUT/'inputs/legacy_study.py'),(OLD/'dca/snapshot/source/docs/experiments/raw/dca-complete-trades-2026-09-07/dca_complete_trades_results.json',OUT/'inputs/legacy_results.json'),(OLD/'E01-frozen-v1.md',OUT/'inputs/E01-frozen-v1.md')]:copy(src,dst)
SRC=Path('/Users/yongbiaoli/lei-signal-sync');d=P/'task-indices';d.mkdir(exist_ok=True)
for f in (SRC/'docs/glm-prompts/agent-integration-2026-09-07').glob('0[5-8]-*.md'):copy(f,d/f.name)
(OUT/'input-manifest.json').write_text(json.dumps({'captured_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':files},ensure_ascii=False,indent=2)+'\n');print(len(files),'inputs snapshotted')
