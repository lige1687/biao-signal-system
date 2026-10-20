#!/usr/bin/env bash
# 推送：导出本机「个人管理数据」→ 写入同步包仓库 → 提交并推送到远端 data-sync 分支。
#
# 用法：
#   ./sync_push.sh
# 环境变量（均可选，用于不同机器/远端）：
#   LEI_SYNC_DIR      同步包仓库路径    默认 $HOME/lei-signal-sync
#   LEI_SYNC_REMOTE   远端 git 地址     默认 git@github.com:lige1687/biao-signal-system.git
#   LEI_SYNC_BRANCH   分支名           默认 data-sync
#   LEI_SQLITE_PATH   本机 SQLite 路径 默认 $HOME/.lei_signal_lab/lab.db
#   LEI_PROJECT_DIR   项目根（定位情绪CSV）默认 脚本所在上两级
#   LEI_SENTIMENT_ROOT 情绪CSV目录      默认 <项目>/data/sentiment
#   LEI_SYNC_PORT     后端端口(导出无影响) 默认 8000
#   LEI_SYNC_PYTHON   Python 解释器     默认 python3
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/sync_common.sh"

echo "==> [1/3] 导出个人管理数据 (db=$DB_PATH) -> $SYNC_DIR"
"$PYTHON" "$SCRIPT_DIR/export_sync.py" --db "$DB_PATH" --out "$SYNC_DIR" --project "$PROJECT_DIR"

cd "$SYNC_DIR"
current="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
if [ "$current" != "$SYNC_BRANCH" ]; then
  echo "==> 切换/创建分支 $SYNC_BRANCH"
  git checkout "$SYNC_BRANCH" 2>/dev/null || git checkout -b "$SYNC_BRANCH"
fi

# 仅暂存同步数据与脚本，不碰其它代码文件
git add manifest.json watchlist_*.json trade_*.json plan_*.json sentiment_*.json sentiment_csv scripts/sync 2>/dev/null || true
if git diff --cached --quiet; then
  echo "==> 无变更，无需推送"
  exit 0
fi

ts="$(date '+%Y-%m-%d %H:%M %Z')"
git commit -m "sync: 个人管理数据更新 @ $ts"
git push -u "$SYNC_REMOTE" "$SYNC_BRANCH"
echo "==> [完成] 已推送到 $SYNC_REMOTE ($SYNC_BRANCH)"
