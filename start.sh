#!/usr/bin/env bash
# Embodied AI Career OS 一键启动脚本
#
# 用途：沙箱环境清理后，快速恢复前端 + 后端服务
# 用法：bash start.sh
#
# 注意：沙箱内的 localhost:3000 / localhost:8000 仅在沙箱内可访问，
#       浏览器需通过 IDE 预览域名（*.trae-preview.com）访问。

set -e

PROJECT_DIR="/workspace/embodied-ai-career-os"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
NPM="/root/.nvm/versions/node/v24.15.0/bin/npm"
NPX="/root/.nvm/versions/node/v24.15.0/bin/npx"

echo "=========================================="
echo "  Embodied AI Career OS 启动"
echo "=========================================="

# 1. 清理可能残留的进程
echo "[1/4] 清理残留进程..."
pkill -9 -f "uvicorn app.main" 2>/dev/null || true
pkill -9 -f "next-server" 2>/dev/null || true
pkill -9 -f "next dev" 2>/dev/null || true
sleep 2

# 2. 启动后端
echo "[2/4] 启动后端 (FastAPI :8000)..."
cd "$BACKEND_DIR"
nohup ./.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "  后端 PID: $BACKEND_PID"

# 等待后端就绪
for i in $(seq 1 30); do
  if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "  ✓ 后端就绪 (等待 ${i}s)"
    break
  fi
  sleep 1
done

# 3. 检查前端依赖，丢失则重装
echo "[3/4] 检查前端依赖..."
if [ ! -f "$FRONTEND_DIR/node_modules/.bin/next" ]; then
  echo "  node_modules 丢失，重新安装..."
  cd "$FRONTEND_DIR"
  $NPM install --silent 2>&1 | tail -3
  echo "  ✓ 依赖安装完成"
else
  echo "  ✓ 依赖已存在"
fi

# 4. 启动前端
echo "[4/4] 启动前端 (Next.js :3000)..."
cd "$FRONTEND_DIR"
nohup $NPX next dev > /tmp/frontend.log 2>&1 &
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
echo ""
echo "  ⚠ 沙箱内 localhost 仅 curl 可访问；浏览器请使用 IDE 预览域名"
echo "=========================================="

# 验证
echo ""
echo "验证："
echo -n "  后端 /health: "
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8000/health
echo -n "  前端 /dashboard: "
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:3000/dashboard
