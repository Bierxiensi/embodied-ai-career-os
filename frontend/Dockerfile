# Frontend Dockerfile — 开发态，支持热重载
FROM node:20-alpine

# 设置工作目录
WORKDIR /app

# 设置环境变量，确保在容器内可正常构建
ENV NEXT_TELEMETRY_DISABLED=1 \
    WATCHPACK_POLLING=true

# 先复制依赖清单，利用 Docker 缓存层
COPY package.json package-lock.json* ./

# 安装依赖
RUN npm ci || npm install

# 复制项目代码（开发态通过 volume 挂载覆盖，此处仅保证镜像可独立运行）
COPY . .

# 暴露端口
EXPOSE 3000

# 开发态启动，监听所有网卡，便于容器外访问
CMD ["npm", "run", "dev", "--", "-H", "0.0.0.0"]
