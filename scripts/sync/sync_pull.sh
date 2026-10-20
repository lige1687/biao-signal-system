#!/usr/bin/env bash
# 拉取：从远端 data-sync 分支拉取同步包 → 导入到本机 SQLite + 情绪 CSV。
#
# 用法：
#   ./sync_pull.sh
# 环境变量同 sync_push.sh（见 sync_push.sh 头部说明）。
#
# 注意：
#   - 导入会「整表替换」本机对应表（远端覆盖本机），属镜像模型。
#   - 导入前若后端正在运行会被拒绝（占用 db），请先 biao stop。
#   - 导入前会自动备份本机 db（<db>.bak-<时间戳>）。
#   - 首次在新机器使用：需先让后端初始化过 db schema（跑一次 biao start 再 biao stop），
#     否则目标库无表，导入会跳过（打印 [skip]）。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/sync_common.sh"

cd "$SYNC_DIR"
echo "==> [1/2] 拉取远端同步包 ($SYNC_BRANCH)"
git fetch "$SYNC_REMOTE" "$SYNC_BRANCH"
current="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
if [ "$current" != "$SYNC_BRANCH" ]; then
  git checkout -b "$SYNC_BRANCH" "FETCH_HEAD"
else
  git reset --hard "origin/$SYNC_BRANCH"
fi

echo "==> [2/2] 导入到本机 (db=$DB_PATH)"
"$PYTHON" "$SCRIPT_DIR/import_sync.py" --db "$DB_PATH" --in "$SYNC_DIR" --project "$PROJECT_DIR"
echo "==> [完成] 导入完成。启动后端查看：biao start"
