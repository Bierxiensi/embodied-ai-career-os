# Backend Dockerfile — 开发态，支持热重载
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量，避免 Python 写入 .pyc、保证日志实时输出
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# 安装依赖（利用 Docker 缓存层）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 开发态启动：监听所有网卡，便于容器外访问
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
