import pathlib,json,shutil,tempfile,hashlib
R=pathlib.Path.cwd();O=R/'docs/experiments/raw/agent-runtime-integration-2026-09-15';rows=json.loads((O/'manifest.json').read_text())
assert all(r['status']=='take_developer' for r in rows)
p=O/'candidate/web/src/components/PlanDraftCard.tsx';s=p.read_text();old='（未落库，可重试）'; assert s.count(old)==1;s=s.replace(old,'（请按上述提示核对后继续）');p.write_text(s)
for r in rows:
 if r['path']=='web/src/components/PlanDraftCard.tsx': r['candidate_sha']=hashlib.sha256(p.read_bytes()).hexdigest();r['controller_adjustment']='已批准的单行保存失败文案补丁'
(O/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
T=pathlib.Path(tempfile.mkdtemp(prefix='lei-agent-integration-'))
for name in ['src','tests','configs','web']:
 shutil.copytree(R/name,T/name,ignore=shutil.ignore_patterns('node_modules','dist','__pycache__','.pytest_cache'))
for name in ['pyproject.toml','pytest.ini']:
 if (R/name).exists():shutil.copy2(R/name,T/name)
(T/'docs').symlink_to(R/'docs',target_is_directory=True)
(T/'web/node_modules').symlink_to(R/'web/node_modules',target_is_directory=True)
for r in rows:
 dest=T/r['path'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(O/'candidate'/r['path'],dest)
(O/'staging.json').write_text(json.dumps({'path':str(T),'runtime_source_untouched':True},indent=2))
print(T)
