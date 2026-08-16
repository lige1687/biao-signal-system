#!/usr/bin/env bash
# =============================================================================
# lei-signal-lab 看板进程管理（替代手动 restart / 手动 uvicorn）
#
# 设计原则：所有启停都由 macOS launchd 统一管理，本脚本只是 launchctl 的
#           薄封装。绝不直接 exec uvicorn/vite（会和 launchd 抢 8000/5173 端口）。
#
# 用法：  bash scripts/biao-ctl.sh [命令]
#   缺省（直接打 biao）= restart（★改完代码后用这一条★）
#   status            查看三个 agent 是否已加载 + 探测 8000/5173 端口
#   restart           干净重启 后端+前端（等同直接打 biao）
#   restart-backend   只重启后端
#   restart-frontend  只重启前端
#   start             启用三个 agent（bootstrap），平时不用
#   stop             停用三个 agent（bootout），临时关看板用
#   install          一键安装/重装自启（首次或 plist 改过之后跑一次）
#
# 注意：必须在你本人的「终端.app」里跑（需要 GUI 登录会话）。
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS="$HOME/Library/LaunchAgents"
DOMAIN="gui/$(id -u)"

B=com.lei.backend
F=com.lei.frontend
M=com.lei.ashare.ma
S=com.lei.sector.trend

case "${1:-restart}" in
  status)
    echo "=== launchd agents（loaded 才说明在管）==="
    launchctl list 2>/dev/null | grep -E "com\.lei\.(backend|frontend|ashare|sector)" || echo "  (无 com.lei.* 被 load —— 需先跑 install)"
    echo
    echo "=== 端口探测（HTTP 200 = 活着）==="
    for p in 8000 5173; do
      code=$(curl -s -m4 -o /dev/null -w "%{http_code}" "http://127.0.0.1:$p/" 2>/dev/null || echo 000)
      echo "  :$p -> HTTP $code"
    done
    ;;
  restart-backend)
    launchctl kickstart -k "$DOMAIN/$B" && echo "✓ 后端已干净重启（改代码已生效）"
    ;;
  restart-frontend)
    launchctl kickstart -k "$DOMAIN/$F" && echo "✓ 前端已干净重启（改代码已生效）"
    ;;
  restart)
    launchctl kickstart -k "$DOMAIN/$B"
    launchctl kickstart -k "$DOMAIN/$F"
    echo "✓ 后端 + 前端已干净重启（改代码已生效）"
    ;;
  start)
    for n in "$B" "$F" "$M" "$S"; do
      if launchctl bootstrap "$DOMAIN" "$AGENTS/$n.plist" 2>/dev/null; then
        launchctl enable "$DOMAIN/$n" 2>/dev/null || true
        echo "  ✓ 启用 $n"
      else
        echo "  ✗ $n 启用失败（检查 $AGENTS/$n.plist 路径）"
      fi
    done
    ;;
  stop)
    for n in "$B" "$F" "$M" "$S"; do
      if launchctl bootout "$DOMAIN/$n" 2>/dev/null; then
        echo "  ✓ 停用 $n"
      else
        echo "  - $n 原本就未运行"
      fi
    done
    ;;
  install)
    bash "$SCRIPT_DIR/install_app_autostart.sh"
    ;;
  *)
    echo "用法: bash scripts/biao-ctl.sh [restart|status|restart-backend|restart-frontend|start|stop|install]（缺省=restart）"
    ;;
esac
