#!/usr/bin/env bash
# Embodied AI Career OS 冒烟测试
#
# 用法：bash scripts/smoke.sh
# 前置：已执行 bash start.sh（后端 :8000 + 前端 :3000 在运行）
#
# 覆盖：
#   - 后端健康检查与数据库连通性
#   - 核心业务 API 返回结构（统一 ApiResponse 解包）
#   - 前端页面可访问性

set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORTS_FILE="$PROJECT_DIR/.workbuddy/logs/ports.env"
if [ -f "$PORTS_FILE" ]; then
  # shellcheck disable=SC1090
  source "$PORTS_FILE"
fi
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

# localhost 请求必须绕过代理，否则会被 HTTP_PROXY 劫持，导致测到别的服务
export NO_PROXY="localhost,127.0.0.1,::1"
export no_proxy="localhost,127.0.0.1,::1"

BACKEND="http://localhost:$BACKEND_PORT"
FRONTEND="http://localhost:$FRONTEND_PORT"
FAIL=0
PASS=0

ok()   { echo "  ✓ $1"; PASS=$((PASS + 1)); }
bad()  { echo "  ✗ $1"; FAIL=$((FAIL + 1)); }

check_api() {
  local path="$1"
  local desc="$2"
  local body
  body=$(curl -s --max-time 10 "$BACKEND$path" 2>/dev/null || true)
  if [ -z "$body" ]; then
    bad "$desc（无响应）"
  elif echo "$body" | grep -q '"success": *true'; then
    ok "$desc"
  else
    bad "$desc -> $(echo "$body" | head -c 160)"
  fi
}

echo "=========================================="
echo "  Career OS 冒烟测试"
echo "=========================================="

# ---------- 后端 ----------
echo "[后端] 健康检查"
if ! curl -s --max-time 5 "$BACKEND/health" >/dev/null 2>&1; then
  echo "  ✗ 后端未运行（$BACKEND）。请先执行：bash start.sh"
  exit 1
fi
# 身份校验：端口上必须是本项目后端，避免误测其他服务
root=$(curl -s --max-time 5 "$BACKEND/" || true)
if ! echo "$root" | grep -q "Career OS"; then
  echo "  ✗ 端口 $BACKEND_PORT 上的服务不是 Career OS 后端：$root"
  echo "    请改用空闲端口启动：BACKEND_PORT=8100 bash start.sh"
  exit 1
fi
ok "后端身份校验（端口 $BACKEND_PORT）"
body=$(curl -s --max-time 5 "$BACKEND/health")
echo "$body" | grep -q '"status": *"ok"' && ok "/health" || bad "/health -> $body"

body=$(curl -s --max-time 10 "$BACKEND/health/db")
echo "$body" | grep -q '"db": *"ok"' && ok "/health/db 数据库连通" || bad "/health/db -> $body"

echo "[后端] 业务 API"
check_api "/api/career"              "GET /api/career 职业目标"
check_api "/api/skills"              "GET /api/skills 技能图谱"
check_api "/api/tasks"               "GET /api/tasks 任务列表"
check_api "/api/projects"            "GET /api/projects 项目列表"
check_api "/api/projects/1"          "GET /api/projects/1 项目详情（含里程碑）"
check_api "/api/dashboard"           "GET /api/dashboard 仪表盘聚合"
check_api "/api/agent/runs?limit=5"  "GET /api/agent/runs Agent 运行记录"
check_api "/api/learning-logs"       "GET /api/learning-logs 学习日志"

# ---------- 种子数据 ----------
echo "[后端] 种子数据"
skills_body=$(curl -s --max-time 10 "$BACKEND/api/skills")
count=$(echo "$skills_body" | grep -o '"name"' | wc -l | tr -d ' ')
if [ "${count:-0}" -gt 0 ]; then
  ok "技能种子数据非空（$count 项）"
else
  bad "技能种子数据为空，init_db 可能未执行"
fi

# ---------- 前端 ----------
echo "[前端] 页面可访问性"
if ! curl -s --max-time 5 "$FRONTEND/dashboard" >/dev/null 2>&1; then
  bad "前端未运行（$FRONTEND/dashboard）"
else
  if ! curl -s --max-time 10 "$FRONTEND/" | grep -q "Embodied AI Career OS"; then
    bad "端口 $FRONTEND_PORT 上的服务不是 Career OS 前端"
  else
    ok "前端身份校验（端口 $FRONTEND_PORT）"
  fi

  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 20 "$FRONTEND/dashboard")
  [ "$code" = "200" ] && ok "/dashboard HTTP 200" || bad "/dashboard HTTP $code"

  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 20 "$FRONTEND/projects")
  [ "$code" = "200" ] && ok "/projects HTTP 200" || bad "/projects HTTP $code"

  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 20 "$FRONTEND/agents")
  [ "$code" = "200" ] && ok "/agents HTTP 200" || bad "/agents HTTP $code"
fi

# ---------- 汇总 ----------
echo ""
echo "=========================================="
echo "  通过 $PASS 项，失败 $FAIL 项"
echo "=========================================="

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
echo "  全部通过"
