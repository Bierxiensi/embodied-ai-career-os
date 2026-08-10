#!/usr/bin/env bash
# Embodied AI Career OS 一键启动脚本（跨平台：Linux / macOS / Git Bash）
#
# 用法：bash start.sh
set -e

# 自动检测项目根目录（脚本所在目录）
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

echo "=========================================="
echo "  Embodied AI Career OS 启动"
echo "  Project: $PROJECT_DIR"
echo "=========================================="

# 1. 清理残留进程
echo "[1/4] 清理残留进程..."
# Windows Git Bash 没有 pkill，用 taskkill 兜底
if command -v pkill &>/dev/null; then
  pkill -f "uvicorn app.main" 2>/dev/null || true
  pkill -f "next dev" 2>/dev/null || true
  sleep 1
elif command -v taskkill &>/dev/null; then
  taskkill //f //im python.exe //fi "WINDOWTITLE eq uvicorn*" 2>/dev/null || true
  taskkill //f //im node.exe //fi "WINDOWTITLE eq next*" 2>/dev/null || true
  sleep 1
fi
# 兜底：杀端口占用
pid_8000=$(netstat -ano 2>/dev/null | grep ":8000 " | grep LISTENING | awk '{print $NF}' | head -1 || true)
pid_3000=$(netstat -ano 2>/dev/null | grep ":3000 " | grep LISTENING | awk '{print $NF}' | head -1 || true)
[ -n "$pid_8000" ] && { echo "  释放端口 8000 (PID $pid_8000)"; kill "$pid_8000" 2>/dev/null || taskkill //f //pid "$pid_8000" 2>/dev/null || true; }
[ -n "$pid_3000" ] && { echo "  释放端口 3000 (PID $pid_3000)"; kill "$pid_3000" 2>/dev/null || taskkill //f //pid "$pid_3000" 2>/dev/null || true; }
sleep 1

# 2. 启动后端
echo "[2/4] 启动后端 (FastAPI :8000)..."
cd "$BACKEND_DIR"
# 优先用 poetry/venv，其次系统 uvicorn
if [ -f ".venv/bin/uvicorn" ]; then
  UVICORN=".venv/bin/uvicorn"
elif [ -f ".venv/Scripts/uvicorn.exe" ]; then
  UVICORN=".venv/Scripts/uvicorn.exe"
elif [ -f ".venv/Scripts/uvicorn" ]; then
  UVICORN=".venv/Scripts/uvicorn"
else
  UVICORN="uvicorn"
fi
nohup $UVICORN app.main:app --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "  后端 PID: $BACKEND_PID  (uvicorn: $UVICORN)"

# 等待后端就绪
for i in $(seq 1 30); do
  if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "  ✓ 后端就绪 (等待 ${i}s)"
    break
  fi
  sleep 1
done

# 3. 检查前端依赖
echo "[3/4] 检查前端依赖..."
if [ ! -f "$FRONTEND_DIR/node_modules/.bin/next" ]; then
  echo "  node_modules 丢失，重新安装..."
  cd "$FRONTEND_DIR"
  npm install --silent 2>&1 | tail -3
  echo "  ✓ 依赖安装完成"
else
  echo "  ✓ 依赖已存在"
fi

# 4. 启动前端
echo "[4/4] 启动前端 (Next.js :3000)..."
cd "$FRONTEND_DIR"
nohup npx next dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "  前端 PID: $FRONTEND_PID"

# 等待前端就绪
for i in $(seq 1 30); do
  if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/dashboard 2>/dev/null | grep -q "200\|307"; then
    echo "  ✓ 前端就绪 (等待 ${i}s)"
    break
  fi
  sleep 1
done

echo ""
echo "=========================================="
echo "  启动完成"
echo "=========================================="
echo "  后端:   http://localhost:8000  (PID $BACKEND_PID)"
echo "  前端:   http://localhost:3000  (PID $FRONTEND_PID)"
echo "  Dashboard: http://localhost:3000/dashboard"
echo ""
echo "  日志: /tmp/backend.log / /tmp/frontend.log"
echo "=========================================="

# 验证
echo ""
echo "验证："
echo -n "  后端 /health: "
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8000/health
echo -n "  前端 /dashboard: "
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:3000/dashboard
