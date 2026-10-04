"""Verify bounded execution and record acceptance without fitting."""
from pathlib import Path
import json,hashlib,datetime,subprocess,sys,platform
import numpy,pandas
H=Path(__file__).resolve().parent;R=H.parents[3]
def rd(p):return json.loads(p.read_text())
def put(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
checks=[];actual=0
for d in sorted((H/'continuous').iterdir()):
 if not d.is_dir():continue
 core=rd(d/'core-01/result.json');accepted=rd(d/'accepted-01/result.json');actual+=core['execution']['fits'];assert accepted['execution']['fits']==0;assert core['predictions']==accepted['predictions'];assert len(core['predictions'])==2536
 c=rd(d/'core-01/contract.json');proof=rd(d/'core-01/preflight.json');obs=proof['observations'];ids={x['id'] for x in core['predictions']};byday={}
 for x in obs:
  if x.get('feature_reason') is None:byday.setdefault(x['date'],[]).append(x['id'])
 dates={x['date'] for x in core['predictions']}
 assert len(dates)==317
 for day in dates:assert len(byday[day])==8 and set(byday[day])<=ids
 checks.append({'branch':d.name,'core_fits':core['execution']['fits'],'accepted_fits':0,'predictions_identical':True,'rows':2536,'dates':317,'ranking_membership_formed_without_labels_and_all8_mature_on_evaluation_dates':True,'contract_sha256':sha(d/'core-01/contract.json')})
assert actual==16
old=json.loads(subprocess.check_output(['git','show','473584b1bdadaeb1abfa8a902c0935badc9cf250:docs/research/definitions.v1.json'],text=True));new=rd(R/'docs/research/definitions.v1.json');lookup={(o['id'],o['version']):o for o in new['objects']};assert all(lookup[(o['id'],o['version'])]==o for o in old['objects'])
for x in rd(H/'brief.json')['source_documents']:assert sha(Path(x['path']))==x['sha256']
review={'status':'completed','evidence':'inconclusive_overall_with_positive_fixed_tree_increment','question':'fixed color-history8ETF extension','checks':checks,'original_definition_objects_unchanged':True,'actual_fits':16,'previous_stage_fits':32,'further_fits':0,'verdict_reason':'fixed tree return improvement against B1 positive both periods and leave-one asset; weaker than simple ownETF mean overall; ranking improvement period reversal; risk not stable','independent_numeric_checks':rd(H/'independent-verification.json'),'ranking_checks':rd(H/'ranking-independent-check.json')['independent_checks'],'limits':['historical reconstruction/source timing incomplete','seen history/exploratory/multiple previous tests','no net account, stock selection or market-index background evidence'],'budget_reason':'one fixed planned core batch complete; no tuning or repeat; new ablation question not performed','test_limit':'37 related pass; expanded51pass1missing old fixture failure retained','hygiene':'actual worktree checked using current main checkout checker code with __file__ bound to this root, exit0','scope_conflict':'15 remote task records checked before edits; separate technical implementation and sourceowner; no known overlap','time':datetime.datetime.now().astimezone().isoformat()}
put(H/'controller-review.json',review)
state=rd(H/'checkpoint.json');state.update(status='completed',stage='bounded historical comparisons and independent verification completed; publication sync pending',evidence='inconclusive',real_fits=16,next='verify safe remote publication; no repeated core experiments',time=review['time']);put(H/'checkpoint.json',state)
(H/'ENVIRONMENT.md').write_text(f'''# 本轮运行与恢复范围

实际Python {sys.version.split()[0]}；NumPy {numpy.__version__}；pandas {pandas.__version__}；LightGBM4.6.0。系统 {platform.platform()}。原本仓库局部运行时`docs/experiments/raw/color-gray-path-2026-10-04/.venv.local/bin/python`，没有新安装或全局改动。

LightGBM本机需进程变量`DYLD_LIBRARY_PATH=/opt/homebrew/lib/python3.11/site-packages/torch/lib`，用于既有libomp。此机器路径不是远端恢复前提；远端必须安装本系统匹配的OpenMP并核原运行时指纹，不能照搬路径。其他OS未测试。不需API密钥，不授予行情下载/付费或生产权限。

项目根目录运行，相对路径在本目录脚本中解析。先核manifest/SHA256SUMS及源许可；`workflow-input.local.json`、完整preflight和模型参数本机保留、未上传。清单记录准确大小/SHA及取得位置，接手者拿不到原输入不得声称完整复现。不要重新拟合已封存16次。

- 保存CSV可用标准库独立核算主要误差和高低组表。
- 完整分析重放需恢复原输入及模型参数后，设置`PYTHONPATH=src`，运行`analyze_saved.py`；这是重放、0拟合。
- `ranking_checks.py`需要完整原preflight；`diagnostics.py`需要原价格日历和保存CSV，缺文件应报告而非重训补齐。
- 首次执行设计入口`prepare.py`→`run_stages.py freeze freeze-02`→`run_stages.py execute core-01`已经执行；现在不再运行。
- 正式报告登记使用`publish.py`复用旧预测，4分支0新增真实拟合，已完成。

依赖原源码和科学定义跟随本工作分支，原数据不在Git；冻结合同绑定原件。恢复资料时不能修改旧锁、hash或成绩来匹配新路径。
''')
text=f'''# 2026-10-05 八ETF颜色连续表达扩展阶段

原任务负责人继续，非接管。固定8ETF研究完成16真实拟合，原4ETF32保持，不重跑。原20/60颜色作基线，加入绿色占比20/19对变色频率/有符号EMA距离；原文未改。工作发布codex/technical-factor-sequence-progress-20261004，基础完整473584b1bdadaeb1abfa8a902c0935badc9cf250；此阶段提交由本文件git log定位，尚未推送时仅本地。

成果：docs/experiments/color-sector-increment-2026-10-05.md；raw/color-sector-extension-2026-10-05包含合同、保存预测、analysis/diagnostics/controller-review、指纹/排除清单。2536条/317日8ETF：树涨幅误差8.0692→7.9592，两期与去一ETF均改善，指定模型内局部帮助；强ETF均值7.7285仍更好。同日树排名差额增加0.6687但2025负/2026H1正，60日范围含0；风险改善不稳定。整体证据不足，非否定所有黑色用途、非策略净收益。

已完成来源11件与原文SHA、37相关检查、原4ETF4340特征恒等、10144重复分支标签/模型重放、12680排名和独立4误差核算、4正式零拟合报告登记及当前工作树归置检查。失败保留：首次冻结缺新源登记0fit，扩大测试51通过1缺旧questions夹具失败。未动他人CSV/脏文件、生产和原文；无运行市场PID/助手。

当前正在做：安全发布并核远端；下一步只在新明确增量问题/合格资料后登记新范围。本轮已完成问题不重训、不调参。行业与宽基分开；个股PIT、代表指数背景、真实可成交和新未见资料仍缺。数据/完整preflight/权重仅本地不上传。其他AI避开同题新适配与原raw，sourceowner继续源资格，external只读方法审查；不独占其他技术方向，协调记录不是锁。

设备{platform.node()}，更新时间{review['time']}；规范与权限沿旧记录，source SHA aaf497e345404bacd0bc3db3899928de4ba5767fc10b332af5351dd13340c00d。下一步先核coordination/lei/task technical-factor-sequence与本报告，勿把局部增量当生产许可。

---

'''
for n in ['docs/ops/work-progress/technical-factor-sequence.md','docs/progress/technical-factor-sequence.md']:
 p=R/n;p.write_text(text+p.read_text())
print('controller checks verified',len(checks),'actual fits',actual)
