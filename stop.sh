#!/usr/bin/env bash
# Embodied AI Career OS 停止脚本
#
# 用法：bash stop.sh
# 作用：仅结束本项目的前端 / 后端进程。
#
# 安全策略：按端口校验服务身份（后端 / 返回 name 含 "Career OS"，
# 前端 title 含 "Embodied AI Career OS"），不属于本项目的服务一律跳过，
# 避免误杀同机运行的其他项目（如洪水预报系统）。

set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$PROJECT_DIR/.workbuddy/logs"
PORTS_FILE="$LOG_DIR/ports.env"

if [ -f "$PORTS_FILE" ]; then
  # shellcheck disable=SC1090
  source "$PORTS_FILE"
fi
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

# localhost 请求必须绕过代理，否则身份校验会打到代理上
export NO_PROXY="localhost,127.0.0.1,::1"
export no_proxy="localhost,127.0.0.1,::1"

# 平台判定：Windows(Git Bash) 下 kill 对原生进程会静默失败，必须走 taskkill
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) IS_WIN=1 ;;
  *) IS_WIN=0 ;;
esac

echo "=========================================="
echo "  Career OS 停止"
echo "=========================================="

kill_port_if_ours() {
  local port="$1"
  local signature="$2"
  local label="$3"

  local body
  body=$(curl -s --max-time 3 "http://localhost:$port/" 2>/dev/null || true)
  if [ -z "$body" ]; then
    echo "  · 端口 $port 无服务，跳过"
    return 0
  fi
  if ! echo "$body" | grep -q "$signature"; then
    echo "  · 端口 $port 不是本项目$label，跳过（避免误杀）"
    return 0
  fi

  local pid
  pid=$(netstat -ano 2>/dev/null | grep ":$port " | grep -i "LISTENING" | awk '{print $NF}' | head -1 || true)
  if [ -n "$pid" ]; then
    if [ "$IS_WIN" = "1" ]; then
      # Git Bash 的 kill 对 Windows 原生进程常返回 0 却不生效，
      # 必须用 taskkill；MSYS_NO_PATHCONV 防止 /F 被改写成路径。
      MSYS_NO_PATHCONV=1 taskkill /F /T /PID "$pid" >/dev/null 2>&1 || true
    else
      kill "$pid" 2>/dev/null || true
    fi
    # 复检端口：仍在监听说明没杀掉，明确报错，不要假装成功
    sleep 1
    if netstat -ano 2>/dev/null | grep ":$port " | grep -qi "LISTENING"; then
      echo "  ✗ 停止$label 失败 (端口 $port, PID $pid) —— 请手动结束该进程"
      return 1
    fi
    echo "  ✓ 已停止$label (端口 $port, PID $pid)"
  fi
}

kill_port_if_ours "$BACKEND_PORT" "Career OS" "后端"
kill_port_if_ours "$FRONTEND_PORT" "Embodied AI Career OS" "前端"

# 兜底：本项目后端进程（命令行特征唯一）
if command -v pkill >/dev/null 2>&1; then
  pkill -f "uvicorn app.main" 2>/dev/null || true
fi

echo "=========================================="
echo "  已停止"
echo "=========================================="
