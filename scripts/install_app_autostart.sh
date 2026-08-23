#!/usr/bin/env bash
# 一键启用 lei-signal-lab 全套自启（只需在「自己的终端」里跑一次）：
#   - 看板后端 (127.0.0.1:8000)  + 看板前端 (http://localhost:5173)
#     登录自动启动 / 崩溃自动重启 / 重启电脑后自动恢复，从此不用手动启动。
#   - 全A宽度预计算 每个交易日 16:30 自动跑（落盘冻结快照，供全局 strip / 趋势图读取）。
#
# 用法：
#   bash ~/Desktop/lei-signal-lab/scripts/install_app_autostart.sh
#
# 必须在你本人的「终端.app」里执行（需要 GUI 登录会话，WorkBuddy 内无法 bootstrap）。
# 跑完立即生效，之后每次登录/重启都会自己起来。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS="$HOME/Library/LaunchAgents"
mkdir -p "$AGENTS"

# 接管前先清理手动占用的端口(8000 后端 / 5173 前端)，避免新旧进程抢端口导致反复崩溃重启
for port in 8000 5173; do
    pids="$(lsof -ti:"$port" 2>/dev/null || true)"
    if [ -n "$pids" ]; then
        echo "  • 清理占用 $port 的手动旧进程 (PID: $pids)"
        echo "$pids" | xargs kill 2>/dev/null || true
        sleep 1
    fi
done

install_agent () {
    local name="$1"
    local src="$SCRIPT_DIR/$name.plist"
    local dst="$AGENTS/$name.plist"
    echo "▶ 安装 $name"
    cp "$src" "$dst"
    # 先卸载旧实例（兼容新旧两种方式），再 bootstrap
    launchctl bootout "gui/$(id -u)/$name" 2>/dev/null || true
    launchctl unload "$dst" 2>/dev/null || true
    if launchctl bootstrap "gui/$(id -u)" "$dst" 2>/dev/null; then
        launchctl enable "gui/$(id -u)/$name" 2>/dev/null || true
        echo "  ✓ 已用 launchctl bootstrap 加载（新版 macOS，且 RunAtLoad 已触发立即启动）"
    else
        launchctl load "$dst" 2>/dev/null || true
        echo "  ✓ 已用 launchctl load 加载（旧版 macOS）"
    fi
}

install_agent com.lei.backend
install_agent com.lei.frontend
install_agent com.lei.ashare.ma
install_agent com.lei.sector.trend
install_agent com.lei.signal.scan

echo
echo "✅ 全部就绪。现在的效果："
echo "  • 看板后端(8000) + 前端(5173) 已经自动启动，崩溃会自愈，重启电脑后也会自己起来。"
echo "  • 全A宽度预计算 每个交易日 16:30 自动跑（无需手动）。"
echo "  • 行业板块趋势预计算 每个交易日 16:45 自动跑（/sectors 页数据源，无需手动）。"
echo "  • 今日自选信号扫描 交易日 11:35/14:45/15:05 自动跑（看盘主页横幅/红点数据源）。"
echo "  浏览器打开 http://localhost:5173 即可，以后不用再手动启动了。"
echo
echo "  如需临时停用某一项："
echo "    launchctl bootout gui/$(id -u)/com.lei.frontend    # 停用前端"
echo "    launchctl bootout gui/$(id -u)/com.lei.backend     # 停用后端"
echo "    launchctl bootout gui/$(id -u)/com.lei.ashare.ma   # 停用宽度预计算"
echo "    launchctl bootout gui/$(id -u)/com.lei.sector.trend # 停用板块趋势预计算"
echo "    launchctl bootout gui/$(id -u)/com.lei.signal.scan   # 停用今日信号扫描"
