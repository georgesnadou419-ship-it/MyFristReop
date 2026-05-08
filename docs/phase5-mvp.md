# 第五阶段：最小可运行版本（MVP）

> 项目名称：SUIT API — 校内AI算力调度平台
> 更新日期：2026-05-06

---

## 1. MVP 目标

**跑通一个完整流程：**
```
用户在控制台提交任务 → 调度器分配GPU → 计算节点执行 → 返回结果 → 控制台显示
```

**MVP 范围（只做核心功能）：**
- [x] 用户登录
- [x] 节点注册与心跳
- [x] 任务提交（镜像 + 命令）
- [x] GPU 调度（FIFO + 空闲GPU分配）
- [x] 任务执行（Docker 容器）
- [x] 任务状态查看
- [x] 任务日志查看
- [ ] 计费（后续）
- [ ] API 网关（后续）
- [ ] 监控图表（后续）

---

## 2. 部署架构

```
管控节点 10.138.50.58                计算节点 10.138.50.151
┌──────────────────────┐            ┌──────────────────────┐
│  docker-compose.yml  │            │  docker-compose.yml  │
│                      │            │  (agent only)        │
│  nginx       :80     │            │                      │
│  frontend    -       │            │  node-agent    :9000 │
│  backend     :8000   │◄───────────│  (资源感知增强版)     │
│  scheduler   -       │  HTTP API  │  + NVIDIA Driver     │
│  celery-worker -     │            │  + Docker            │
│  celery-beat -       │            └──────────────────────┘
│  redis       :6379   │
│  postgres    :5432   │
└──────────────────────┘
```

---

## 3. 管控节点部署步骤

### 3.1 前置条件

```bash
# 10.138.50.58 上执行

# 安装 Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 安装 Docker Compose (v2)
sudo apt install docker-compose-plugin

# 验证
docker --version
docker compose version
```

### 3.2 项目目录

```bash
# 在管控节点上
mkdir -p /opt/suit-api
cd /opt/suit-api

# 将项目代码上传到此目录
# 最终结构：
/opt/suit-api/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   └── migrations/
├── frontend/
│   ├── Dockerfile
│   └── dist/          # Vue 构建产物
├── deploy/
│   ├── docker-compose.yml
│   ├── nginx.conf
│   └── .env
└── scripts/
```

### 3.3 docker-compose.yml

```yaml
# deploy/docker-compose.yml

services:
  nginx:
    image: nginx:1.25-alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - ../frontend/dist:/usr/share/nginx/html
    depends_on:
      - backend
    restart: always

  backend:
    build: ../backend
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - /data/tasks:/data/tasks
      - /data/models:/data/models
    depends_on:
      - postgres
      - redis
    restart: always

  # 独立调度服务（核心！）
  scheduler:
    build: ../scheduler
    env_file:
      - .env
    volumes:
      - /data/tasks:/data/tasks
    depends_on:
      - redis
      - postgres
    restart: always

  celery-worker:
    build: ../backend
    command: celery -A app.tasks.celery_app worker -l info -Q monitoring,billing
    env_file:
      - .env
    depends_on:
      - redis
      - postgres
    restart: always

  celery-beat:
    build: ../backend
    command: celery -A app.tasks.celery_app beat -l info
    env_file:
      - .env
    depends_on:
      - redis
    restart: always

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: always

  postgres:
    image: postgres:16-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: suitdb
      POSTGRES_USER: suit
      POSTGRES_PASSWORD: ${DB_PASSWORD:-suit123}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    restart: always

volumes:
  postgres-data:
  redis-data:
```

### 3.4 nginx.conf

```nginx
server {
    listen 80;
    server_name _;

    # 前端静态文件
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket 代理
    location /ws/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 3.5 后端 Dockerfile

```dockerfile
# backend/Dockerfile

FROM python:3.11-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

### 3.6 requirements.txt

```
fastapi==0.111.0
uvicorn[standard]==0.30.1
sqlalchemy==2.0.31
alembic==1.13.1
psycopg2-binary==2.9.9
redis==5.0.7
celery==5.4.0
pydantic-settings==2.3.4
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
httpx==0.27.0
python-multipart==0.0.9
```

### 3.7 环境变量 .env

```bash
# deploy/.env

# 数据库
DATABASE_URL=postgresql://suit:suit123@postgres:5432/suitdb

# Redis
REDIS_URL=redis://redis:6379/0

# JWT
JWT_SECRET=your-jwt-secret-change-in-production
SECRET_KEY=your-app-secret-change-in-production

# Agent
AGENT_PORT=9000

# 调度
HEARTBEAT_TIMEOUT=60

# 计费
GPU_HOUR_RATE=1.0

# 密码
DB_PASSWORD=suit123
```

### 3.8 启动

```bash
cd /opt/suit-api/deploy

# 构建并启动
docker compose up -d --build

# 查看状态
docker compose ps

# 查看日志
docker compose logs -f backend
```

### 3.9 初始化数据库

```bash
# 数据库迁移
docker compose exec backend alembic upgrade head

# 创建管理员账号
docker compose exec backend python -m app.scripts.create_admin
```

---

## 4. 计算节点部署步骤

### 4.1 前置条件

```bash
# 10.138.50.151 上执行

# 1. 安装 NVIDIA 驱动（如果未安装）
sudo apt install nvidia-driver-535
sudo reboot

# 验证
nvidia-smi

# 2. 安装 Docker（如果未安装）
curl -fsSL https://get.docker.com | sh

# 3. 安装 NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# 验证
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

### 4.2 部署 Agent

```bash
# 创建 Agent 目录
mkdir -p /opt/suit-agent
cd /opt/suit-agent

# 将 agent 代码上传到此目录
# 或从管控节点拉取 Agent 镜像

# Agent Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn docker httpx psutil

COPY . .

CMD ["uvicorn", "agent:app", "--host", "0.0.0.0", "--port", "9000"]
EOF

# 构建
docker build -t suit-agent .

# 启动
docker run -d \
  --name node-agent \
  --gpus all \
  --network host \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /data/tasks:/data/tasks \
  -v /data/models:/data/models:ro \
  -e CONTROL_PLANE=http://10.138.50.58:8000 \
  -e NODE_NAME=node-151 \
  -e NODE_IP=10.138.50.151 \
  --restart always \
  suit-agent
```

### 4.3 验证 Agent

```bash
# 检查 Agent 是否运行
docker ps | grep node-agent

# 检查 Agent 是否能访问管控节点
curl http://10.138.50.151:9000/api/health

# 在管控节点上检查是否收到心跳
curl http://10.138.50.58:8000/api/v1/nodes
# 应该能看到 10.138.50.151 已注册
```

---

## 5. MVP 验证流程

```
步骤1: 打开浏览器 http://10.138.50.58
步骤2: 用管理员账号登录
步骤3: 进入"资源管理"，确认 10.138.50.151 节点在线，GPU 可见
步骤4: 进入"提交任务"
        - 镜像: python:3.11-slim
        - 命令: python -c "print('Hello from GPU!'); import time; time.sleep(10)"
        - GPU数量: 0（先测试无GPU任务）
步骤5: 提交，进入"任务列表"
步骤6: 观察状态变化: pending → queued → running → success
步骤7: 查看任务日志，应看到 "Hello from GPU!"
步骤8: 提交一个真实 GPU 任务
        - 镜像: nvidia/cuda:12.2.0-base-ubuntu22.04
        - 命令: nvidia-smi
步骤9: 确认任务在 151 节点执行，日志中看到 GPU 信息
```

---

## 6. MVP 文件清单

MVP 阶段需要创建的文件：

```
backend/
├── Dockerfile
├── requirements.txt
├── alembic.ini
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── dependencies.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── node.py         # Node, GpuDevice
│   │   ├── task.py         # Task, TaskLog
│   │   ├── user.py         # User
│   │   ├── model.py        # AiModel, ModelInstance（新增）
│   │   └── billing.py      # BillingRecord
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── node.py
│   │   ├── task.py
│   │   ├── user.py
│   │   └── model.py        # 模型相关 Schema（新增）
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── nodes.py
│   │   ├── tasks.py
│   │   ├── models.py       # 模型管理路由（新增）
│   │   └── ai_gateway.py   # AI 推理网关路由（新增，OpenAI兼容）
│   ├── services/
│   │   ├── __init__.py
│   │   ├── node_service.py
│   │   ├── task_service.py
│   │   ├── model_service.py    # 模型部署/上下线（新增）
│   │   ├── ai_service.py       # AI 推理请求路由（新增）
│   │   ├── billing_service.py
│   │   └── auth_service.py
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── celery_app.py
│   │   └── monitor_tasks.py    # 只有监控任务，没有调度任务
│   └── utils/
│       ├── __init__.py
│       └── security.py

scheduler/                      # 独立调度服务（新增！）
├── Dockerfile
├── requirements.txt
├── main.py                     # 调度服务入口
├── scheduler.py                # 调度引擎主循环
├── queue_manager.py            # Redis 任务队列管理
├── gpu_allocator.py            # GPU 分配策略
├── container_manager.py        # 通过 Agent 管理容器
├── agent_client.py             # Agent HTTP 客户端
├── config.py                   # 新增：调度服务配置
└── database.py                 # 新增：调度服务数据库连接

agent/                          # 计算节点 Agent（增强版）
├── Dockerfile
├── requirements.txt
├── agent.py                    # FastAPI 主程序
├── docker_executor.py          # Docker 容器执行器
├── gpu_monitor.py              # GPU 状态采集（nvidia-smi -q -x）
├── resource_monitor.py         # CPU/内存/磁盘采集
├── container_tracker.py        # 运行中容器追踪（新增）
└── heartbeat.py                # 心跳上报（含完整资源信息）

frontend/
├── (Vue3 项目，Phase 4 详述)

deploy/
├── docker-compose.yml
├── nginx.conf
└── .env
```

---

## 7. 常见问题

| 问题 | 解决方案 |
|------|----------|
| Agent 连不上管控节点 | 检查防火墙，确保 8000/9000 端口开放 |
| Docker 拉镜像慢 | 配置镜像加速器（阿里云/DaoCloud） |
| GPU 容器启动失败 | 确认 nvidia-container-toolkit 安装正确 |
| 任务一直 queued | 检查 Agent 心跳是否正常，节点是否 online |
| 数据库连接失败 | 检查 .env 中 DATABASE_URL 配置 |
