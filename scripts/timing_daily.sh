#!/bin/bash
# 宽度择时每日链（launchd: com.lei.timing.daily，交易日 17:30）：
#   1. 宽表尾巴刷新（用 16:30 precompute_a_share_ma 已更新的长表缓存）
#   2. 回填标的行情 + 重算宽度（新浪/东财，内置绕代理）
#   3. 样本外打分卡存档（按数据截至日去重）
# 任一步失败不阻断后续步（打分卡用现有数据也能存档），exit 0 便于 launchd 观测。
set -uo pipefail
ROOT=/Users/yongbiaoli/Desktop/lei-signal-lab
PY=/Users/yongbiaoli/.workbuddy/binaries/python/envs/default/bin/python3
export PYTHONPATH="$ROOT/src"
cd "$ROOT" || exit 1

"$PY" scripts/refresh_timing_matrix.py || echo "[warn] 宽表刷新失败（继续）"
"$PY" scripts/backfill_timing_data.py --refresh || echo "[warn] 行情/宽度回填失败（继续）"
"$PY" scripts/timing_scorecard.py
