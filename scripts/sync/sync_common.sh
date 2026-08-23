#!/usr/bin/env bash
# 同步公共变量。被 sync_push.sh / sync_pull.sh source。
# 所有变量均可用环境变量覆盖，方便在不同机器/不同远端下复用。
set -euo pipefail

# 本脚本所在目录 (scripts/sync)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 项目根 (scripts/sync -> ../..)。另一台机器项目路径不同可用 LEI_PROJECT_DIR 覆盖。
PROJECT_DIR="${LEI_PROJECT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

# 同步包仓库（独立于项目仓库，互不干扰主代码工作树）
SYNC_DIR="${LEI_SYNC_DIR:-$HOME/lei-signal-sync}"
# 远端与分支（默认复用你的私有仓库 biao-signal-system 的 data-sync 分支）
SYNC_REMOTE="${LEI_SYNC_REMOTE:-git@github.com:lige1687/biao-signal-system.git}"
SYNC_BRANCH="${LEI_SYNC_BRANCH:-data-sync}"

# 本机 SQLite 路径（与运行中的后端解析口径一致）
DB_PATH="${LEI_SQLITE_PATH:-$HOME/.lei_signal_lab/lab.db}"
# 后端端口（导入前检测占用）
API_PORT="${LEI_SYNC_PORT:-8000}"

# Python 解释器（导出/导入脚本仅用标准库，任意 python3 即可）
PYTHON="${LEI_SYNC_PYTHON:-python3}"

# 让导出/导入脚本继承同样的 db 路径解析
export LEI_SQLITE_PATH="$DB_PATH"
