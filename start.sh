#!/usr/bin/env bash
# Embodied AI Career OS 一键启动脚本（环境自愈 + 端口避让 + 进程常驻）
#
# 用法：bash start.sh
# 停止：bash stop.sh
# 冒烟：bash scripts/smoke.sh
#
# 自愈能力（换机 / 首次克隆也能直接跑）：
#   1. .env 缺失 → 从 .env.example 复制
#   2. backend/.venv 缺失 → 自动创建虚拟环境并安装 requirements.txt
#   3. frontend/node_modules 缺失 → 自动 npm ci（无 lock 时回退 npm install）
#   4. 端口被占用 → 识别占用者身份：
#        - 是本项目实例 → 复用，不重复启动
#        - 是其他服务（如洪水预报系统）→ 自动避让到备用端口，绝不误杀
#   5. Windows / macOS / Linux 均保证服务在脚本退出后常驻
#      （Windows 走 PowerShell Start-Process，避免 nohup 子进程被回收）
#
# 端口可用环境变量覆盖：BACKEND_PORT=8100 FRONTEND_PORT=3100 bash start.sh
set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
LOG_DIR="$PROJECT_DIR/.workbuddy/logs"
BACKEND_LOG="$LOG_DIR/backend.log"
BACKEND_ERR_LOG="$LOG_DIR/backend.err.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
FRONTEND_ERR_LOG="$LOG_DIR/frontend.err.log"
PORTS_FILE="$LOG_DIR/ports.env"

mkdir -p "$LOG_DIR"

# 注意：脚本内所有 curl 都带 --noproxy '*'，避免 localhost 请求被 HTTP_PROXY 劫持。
# 此处不 export NO_PROXY：Windows 下 NO_PROXY 与 no_proxy 大小写冲突会让 Start-Process 报错。

BACKEND_SIGNATURE="Career OS"                 # 后端 / 返回 name=Embodied AI Career OS API
FRONTEND_SIGNATURE="Embodied AI Career OS"    # 前端 <title>

case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) IS_WIN=1 ;;
  *) IS_WIN=0 ;;
esac

echo "=========================================="
echo "  Embodied AI Career OS 启动"
echo "  Project: $PROJECT_DIR"
echo "=========================================="

# ---------- 工具函数 ----------
port_in_use() {
  netstat -ano 2>/dev/null | grep -q ":$1 .*LISTENING"
}

is_our_backend() {
  curl -s --noproxy '*' --max-time 3 "http://localhost:$1/" 2>/dev/null | grep -q "$BACKEND_SIGNATURE"
}

is_our_frontend() {
  curl -s --noproxy '*' --max-time 5 "http://localhost:$1/" 2>/dev/null | grep -q "$FRONTEND_SIGNATURE"
}

port_owner() {
  curl -s --noproxy '*' --max-time 3 "http://localhost:$1/" 2>/dev/null | tr -d '\n' | head -c 80 || true
}

pick_port() {
  local kind="$1"; shift
  for p in "$@"; do
    if ! port_in_use "$p"; then
      echo "$p|start"; return 0
    fi
    if [ "$kind" = "backend" ] && is_our_backend "$p"; then
      echo "$p|reuse"; return 0
    fi
    if [ "$kind" = "frontend" ] && is_our_frontend "$p"; then
      echo "$p|reuse"; return 0
    fi
    echo "  ! 端口 $p 被其他服务占用（$(port_owner "$p")），尝试下一个" >&2
  done
  echo "|fail"; return 0
}

# ---------- [1/5] 环境自检与依赖自愈 ----------
echo "[1/5] 环境自检..."

if [ ! -f "$PROJECT_DIR/.env" ]; then
  if [ -f "$PROJECT_DIR/.env.example" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "  ✓ .env 缺失，已从 .env.example 生成"
  else
    echo "  ! .env 与 .env.example 均缺失，使用后端默认配置（SQLite + mock LLM）"
  fi
else
  echo "  ✓ .env 已存在"
fi

BASE_PYTHON=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    BASE_PYTHON="$candidate"
    break
  fi
done
if [ -z "$BASE_PYTHON" ]; then
  echo "  ✗ 未找到 python3 / python，请先安装 Python 3.11+"
  exit 1
fi

VPY=""
if [ -x "$BACKEND_DIR/.venv/Scripts/python.exe" ]; then
  VPY="$BACKEND_DIR/.venv/Scripts/python.exe"
elif [ -x "$BACKEND_DIR/.venv/bin/python" ]; then
  VPY="$BACKEND_DIR/.venv/bin/python"
fi

if [ -z "$VPY" ]; then
  echo "  · 未发现后端虚拟环境，正在创建并安装依赖（首次约 5-10 分钟）..."
  ( cd "$BACKEND_DIR" && "$BASE_PYTHON" -m venv .venv )
  if [ -x "$BACKEND_DIR/.venv/Scripts/python.exe" ]; then
    VPY="$BACKEND_DIR/.venv/Scripts/python.exe"
  elif [ -x "$BACKEND_DIR/.venv/bin/python" ]; then
    VPY="$BACKEND_DIR/.venv/bin/python"
  else
    echo "  ✗ 虚拟环境创建失败，请手动执行：cd backend && python -m venv .venv"
    exit 1
  fi
  "$VPY" -m pip install --upgrade pip -q
  ( cd "$BACKEND_DIR" && "$VPY" -m pip install -r requirements.txt )
  echo "  ✓ 后端依赖安装完成"
else
  echo "  ✓ 后端虚拟环境已存在"
fi

if [ ! -f "$FRONTEND_DIR/node_modules/.bin/next" ] && [ ! -f "$FRONTEND_DIR/node_modules/.bin/next.cmd" ]; then
  echo "  · 前端依赖缺失，正在安装（首次约 5-10 分钟）..."
  ( cd "$FRONTEND_DIR" && npm ci ) || ( cd "$FRONTEND_DIR" && npm install )
  echo "  ✓ 前端依赖安装完成"
else
  echo "  ✓ 前端依赖已存在"
fi

# 记录 node / npm 所在目录：Windows 下 cmd.exe 子进程需显式注入 PATH，
# 否则会报 "npm 不是内部或外部命令"（常见于 nvm / 免安装版 Node）。
NODE_DIR=""
if command -v npm >/dev/null 2>&1; then
  NODE_DIR="$(dirname "$(command -v npm)")"
elif [ -n "${NPM_PATH:-}" ] && [ -x "${NPM_PATH:-}" ]; then
  NODE_DIR="$(dirname "$NPM_PATH")"
fi
# 兜底探测常见安装位置（nvm / 官方安装包 / WorkBuddy 托管 Node）
if [ -z "$NODE_DIR" ]; then
  for p in "${NVM_HOME:-}" "/c/Program Files/nodejs" "/c/Program Files (x86)/nodejs" \
           "$LOCALAPPDATA/Programs/nodejs" "$HOME/.workbuddy/binaries/node/versions/22.22.2-2" \
           "$HOME/.workbuddy/binaries/node/versions/24.4.0"; do
    if [ -n "$p" ] && { [ -e "$p/npm.cmd" ] || [ -x "$p/npm" ]; }; then
      NODE_DIR="$p"
      break
    fi
  done
fi
if [ -z "$NODE_DIR" ]; then
  echo "  ! 未找到 npm，前端将无法启动（可用 NPM_PATH=/path/to/npm 指定）"
else
  echo "  ✓ npm 位于 $NODE_DIR"
fi

# ---------- [2/5] 端口规划 ----------
echo "[2/5] 端口规划..."

if [ -n "${BACKEND_PORT:-}" ]; then
  BACKEND_CANDIDATES=("$BACKEND_PORT")
else
  BACKEND_CANDIDATES=(8000 8010 8020)
fi
if [ -n "${FRONTEND_PORT:-}" ]; then
  FRONTEND_CANDIDATES=("$FRONTEND_PORT")
else
  FRONTEND_CANDIDATES=(3000 3010 3020)
fi

BACKEND_PICK=$(pick_port backend "${BACKEND_CANDIDATES[@]}")
FRONTEND_PICK=$(pick_port frontend "${FRONTEND_CANDIDATES[@]}")

BACKEND_PORT="${BACKEND_PICK%%|*}"
BACKEND_ACTION="${BACKEND_PICK##*|}"
FRONTEND_PORT="${FRONTEND_PICK%%|*}"
FRONTEND_ACTION="${FRONTEND_PICK##*|}"

if [ -z "$BACKEND_PORT" ] || [ -z "$FRONTEND_PORT" ]; then
  echo "  ✗ 找不到可用端口，请手动指定：BACKEND_PORT=8100 FRONTEND_PORT=3100 bash start.sh"
  exit 1
fi

cat > "$PORTS_FILE" <<EOF
# 由 start.sh 生成，供 scripts/smoke.sh / stop.sh 读取
BACKEND_PORT=$BACKEND_PORT
FRONTEND_PORT=$FRONTEND_PORT
EOF
echo "  后端端口 $BACKEND_PORT（$BACKEND_ACTION） · 前端端口 $FRONTEND_PORT（$FRONTEND_ACTION）"

# ---------- 进程启动（跨平台常驻） ----------
# Windows 注：PowerShell 5.1 的 Start-Process 在继承环境时，若同一变量存在大小写两份
# （如 https_proxy 与 HTTPS_PROXY，常见于代理注入的环境）会直接抛 ArgumentException。
# 因此启动子进程前先剥离代理变量；本地服务不需要走代理。
PS_CLEAN="env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u no_proxy -u NO_PROXY -u all_proxy -u ALL_PROXY"

launch_backend() {
  if [ "$IS_WIN" = "1" ]; then
    local wdir py out err
    wdir=$(cygpath -w "$BACKEND_DIR")
    py=$(cygpath -w "$VPY")
    out=$(cygpath -w "$BACKEND_LOG")
    err=$(cygpath -w "$BACKEND_ERR_LOG")
    $PS_CLEAN powershell.exe -NoProfile -Command "Start-Process -FilePath '$py' -ArgumentList '-m','uvicorn','app.main:app','--host','0.0.0.0','--port','$BACKEND_PORT' -WorkingDirectory '$wdir' -RedirectStandardOutput '$out' -RedirectStandardError '$err' -WindowStyle Hidden" > "$LOG_DIR/launch.log" 2>&1
  else
    ( cd "$BACKEND_DIR" && nohup "$VPY" -m uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" > "$BACKEND_LOG" 2>&1 & )
  fi
}

launch_frontend() {
  if [ "$IS_WIN" = "1" ]; then
    local wdir out err node_bin="" next_bin=""
    wdir=$(cygpath -w "$FRONTEND_DIR")
    out=$(cygpath -w "$FRONTEND_LOG")
    err=$(cygpath -w "$FRONTEND_ERR_LOG")
    if [ -x "$NODE_DIR/node.exe" ]; then
      node_bin=$(cygpath -w "$NODE_DIR/node.exe")
    elif [ -x "$NODE_DIR/node" ]; then
      node_bin=$(cygpath -w "$NODE_DIR/node")
    fi
    if [ -f "$FRONTEND_DIR/node_modules/next/dist/bin/next" ]; then
      next_bin=$(cygpath -w "$FRONTEND_DIR/node_modules/next/dist/bin/next")
    fi

    if [ -n "$node_bin" ] && [ -n "$next_bin" ]; then
      # 直接用 node 启动 next：绕开 cmd.exe 与 npm 的 PATH 依赖
      # （cmd /c npm 在部分环境拿不到注入的 PATH，会报 "npm 不是内部或外部命令"）
      $PS_CLEAN powershell.exe -NoProfile -Command "\$env:BACKEND_URL='http://localhost:$BACKEND_PORT'; Start-Process -FilePath '$node_bin' -ArgumentList '$next_bin','dev','-p','$FRONTEND_PORT' -WorkingDirectory '$wdir' -RedirectStandardOutput '$out' -RedirectStandardError '$err' -WindowStyle Hidden" >> "$LOG_DIR/launch.log" 2>&1
    else
      # 回退：npm run dev（依赖系统 PATH 中已有 npm）
      $PS_CLEAN powershell.exe -NoProfile -Command "\$env:BACKEND_URL='http://localhost:$BACKEND_PORT'; Start-Process -FilePath 'cmd.exe' -ArgumentList '/c','npm','run','dev','--','-p','$FRONTEND_PORT' -WorkingDirectory '$wdir' -RedirectStandardOutput '$out' -RedirectStandardError '$err' -WindowStyle Hidden" >> "$LOG_DIR/launch.log" 2>&1
    fi
  else
    ( cd "$FRONTEND_DIR" && BACKEND_URL="http://localhost:$BACKEND_PORT" nohup npm run dev -- -p "$FRONTEND_PORT" > "$FRONTEND_LOG" 2>&1 & )
  fi
}

# ---------- [3/5] 启动后端 ----------
echo "[3/5] 后端 (FastAPI :$BACKEND_PORT)..."
if [ "$BACKEND_ACTION" = "reuse" ]; then
  echo "  ✓ 已有本项目后端实例在运行，直接复用"
else
  launch_backend
  BACKEND_OK=0
  for _ in $(seq 1 45); do
    if is_our_backend "$BACKEND_PORT"; then
      BACKEND_OK=1
      break
    fi
    sleep 1
  done
  if [ "$BACKEND_OK" -ne 1 ]; then
    echo "  ✗ 后端启动失败，日志尾部："
    tail -n 20 "$BACKEND_LOG" 2>/dev/null || true
    tail -n 20 "$BACKEND_ERR_LOG" 2>/dev/null || true
    exit 1
  fi
  echo "  ✓ 后端就绪"
fi

# ---------- [4/5] 启动前端 ----------
echo "[4/5] 前端 (Next.js :$FRONTEND_PORT)..."
if [ "$FRONTEND_ACTION" = "reuse" ]; then
  echo "  ✓ 已有本项目前端实例在运行，直接复用"
else
  launch_frontend
  FRONTEND_OK=0
  for _ in $(seq 1 90); do
    code=$(curl -s --noproxy '*' -o /dev/null -w "%{http_code}" --max-time 25 "http://localhost:$FRONTEND_PORT/dashboard" 2>/dev/null || true)
    if { [ "$code" = "200" ] || [ "$code" = "307" ]; } && is_our_frontend "$FRONTEND_PORT"; then
      FRONTEND_OK=1
      break
    fi
    sleep 1
  done
  if [ "$FRONTEND_OK" -ne 1 ]; then
    echo "  ✗ 前端启动失败，日志尾部："
    tail -n 20 "$FRONTEND_LOG" 2>/dev/null || true
    tail -n 20 "$FRONTEND_ERR_LOG" 2>/dev/null || true
    exit 1
  fi
  echo "  ✓ 前端就绪"
fi

# ---------- [5/5] 结果 ----------
echo ""
echo "=========================================="
echo "  启动完成"
echo "=========================================="
echo "  后端:     http://localhost:$BACKEND_PORT"
echo "  前端:     http://localhost:$FRONTEND_PORT"
echo "  Dashboard http://localhost:$FRONTEND_PORT/dashboard"
echo "  API Docs  http://localhost:$BACKEND_PORT/docs"
echo ""
echo "  日志: $BACKEND_LOG"
echo "        $FRONTEND_LOG"
echo "  冒烟: bash scripts/smoke.sh"
echo "  停止: bash stop.sh"
echo "=========================================="
