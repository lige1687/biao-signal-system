#!/usr/bin/env bash
# 安装「真全A宽度预计算」定时任务（macOS launchd）。
# 每个交易日 16:30 自动跑 scripts/precompute_a_share_ma.py，
# 把真实 MA20/50/200 上方占比宽度落盘，供 global-strip / 趋势图读取。
#
# 用法：
#   bash scripts/install_launchd.sh          # 仅安装+加载定时任务
#   bash scripts/install_launchd.sh --now    # 安装后立即跑一次预计算校验链路
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_SRC="$SCRIPT_DIR/com.lei.ashare.ma.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.lei.ashare.ma.plist"
VENV_PY="/Users/yongbiaoli/.workbuddy/binaries/python/envs/default/bin/python3"

echo "▶ 安装 lei 全A宽度预计算定时任务 (每个交易日 16:30)"
mkdir -p "$HOME/Library/LaunchAgents"
cp "$PLIST_SRC" "$PLIST_DST"

# 若已加载先卸载，避免重复（兼容新旧两种方式）
launchctl bootout "gui/$(id -u)/com.lei.ashare.ma" 2>/dev/null || true
launchctl unload "$PLIST_DST" 2>/dev/null || true

# 新版 macOS(13+) 用 bootstrap；老版本回退到 load
if launchctl bootstrap "gui/$(id -u)" "$PLIST_DST" 2>/dev/null; then
  launchctl enable "gui/$(id -u)/com.lei.ashare.ma" 2>/dev/null || true
  echo "✓ 已用 launchctl bootstrap 加载 (新版本 macOS)"
else
  launchctl load "$PLIST_DST" 2>/dev/null || true
  echo "✓ 已用 launchctl load 加载 (旧版本 macOS)"
fi
echo "  加载配置: $PLIST_DST"

if [ "${1:-}" = "--now" ]; then
  echo "▶ 立即跑一次预计算以校验链路 (约 5-15 分钟，取决于网络与限频)…"
  PYTHONPATH="$SCRIPT_DIR/../src" "$VENV_PY" "$SCRIPT_DIR/precompute_a_share_ma.py"
  echo "✓ 预计算完成。刷新 lei-signal-lab 页面即可看到真全A宽度 B20/B50/B200。"
else
  echo "完成。之后每个交易日 16:30 会自动跑；如需手动立即跑："
  echo "  PYTHONPATH=$SCRIPT_DIR/../src $VENV_PY $SCRIPT_DIR/precompute_a_share_ma.py"
fi
