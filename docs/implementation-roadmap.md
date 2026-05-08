# 编码实施路线图

> 项目名称：SUIT API — 校内AI算力调度平台
> 共 7 个阶段，每个阶段可独立推进，通过接口约定相互对接

---

## 阶段总览

```
阶段1  基础骨架     → 后端服务 + 数据库 + 用户认证
阶段2  节点与Agent  → 计算节点 Agent + GPU 信息上报
阶段3  任务管理     → 任务 CRUD + 状态流转
阶段4  调度引擎     → 独立调度服务 + GPU 分配 + 全流程跑通
阶段5  前端控制台   → Vue3 管理界面
阶段6  AI能力层     → 模型管理 + OpenAI 兼容 API
阶段7  监控与计费   → GPU 监控 + 计费系统
```

## 阶段间关系

```
阶段1（基础骨架）
  │
  ├──→ 阶段2（节点与Agent）      可并行，只需约定 API 接口
  │
  ├──→ 阶段3（任务管理）         可并行，只需约定数据模型
  │         │
  │         └──→ 阶段4（调度引擎）  依赖阶段2的Agent + 阶段3的任务API
  │
  ├──→ 阶段5（前端控制台）       可并行，只需阶段1的API文档
  │
  └──→ 阶段6（AI能力层）         可并行，只需阶段1的骨架 + 阶段2的Agent
            │
            └──→ 阶段7（监控与计费） 可并行，独立模块
```

---

## 阶段1：基础骨架搭建

### 提示词

```
你是一个 Python 后端开发工程师。

项目：SUIT API — 校内AI算力调度平台
技术栈：FastAPI + SQLAlchemy 2.0 + PostgreSQL 16 + Redis 7
部署：Docker Compose

你的任务是搭建后端项目骨架，包含以下内容：

【目录结构】
backend/
├── Dockerfile
├── requirements.txt
├── alembic.ini
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI 入口，挂载所有 router
│   ├── config.py             # 配置管理（pydantic-settings，从 .env 读取）
│   ├── database.py           # SQLAlchemy engine + session
│   ├── dependencies.py       # get_db, get_current_user 依赖注入
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py           # User 表
│   │   ├── node.py           # Node, GpuDevice 表
│   │   └── task.py           # Task, TaskLog 表
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── user.py           # Pydantic 请求/响应模型
│   ├── routers/
│   │   ├── __init__.py
│   │   └── auth.py           # 认证路由
│   ├── services/
│   │   ├── __init__.py
│   │   └── auth_service.py   # 认证业务逻辑
│   └── utils/
│       ├── __init__.py
│       └── security.py       # JWT 生成/验证, 密码哈希
├── migrations/
│   └── env.py
deploy/
├── docker-compose.yml
└── .env.example

【数据库表定义】
-- 用户表
users (
  id              VARCHAR(36) PRIMARY KEY,  -- UUID
  username        VARCHAR(64) UNIQUE NOT NULL,
  password_hash   VARCHAR(256) NOT NULL,
  role            VARCHAR(20) DEFAULT 'user',  -- admin/user
  gpu_quota       INT DEFAULT 2,
  api_key         VARCHAR(128) UNIQUE,
  credits         DECIMAL(12,2) DEFAULT 0,
  created_at      TIMESTAMP DEFAULT NOW()
);

-- 计算节点表
nodes (
  id              VARCHAR(36) PRIMARY KEY,
  hostname        VARCHAR(128),
  ip              VARCHAR(45) NOT NULL UNIQUE,
  agent_port      INT DEFAULT 9000,
  gpu_count       INT DEFAULT 0,
  gpu_model       VARCHAR(64),
  total_memory_mb INT,
  status          VARCHAR(20) DEFAULT 'offline',
  last_heartbeat  TIMESTAMP,
  registered_at   TIMESTAMP DEFAULT NOW()
);

-- GPU 设备表
gpu_devices (
  id              VARCHAR(36) PRIMARY KEY,
  node_id         VARCHAR(36) REFERENCES nodes(id),
  gpu_index       INT NOT NULL,
  gpu_model       VARCHAR(64),
  memory_total_mb INT,
  memory_used_mb  INT DEFAULT 0,
  utilization     INT DEFAULT 0,
  temperature     INT DEFAULT 0,
  power_usage     INT DEFAULT 0,
  status          VARCHAR(20) DEFAULT 'idle',
  updated_at      TIMESTAMP DEFAULT NOW(),
  UNIQUE(node_id, gpu_index)
);

-- 任务表
tasks (
  id                  VARCHAR(36) PRIMARY KEY,
  user_id             VARCHAR(36) REFERENCES users(id),
  name                VARCHAR(128),
  task_type           VARCHAR(20),
  status              VARCHAR(20) DEFAULT 'pending',
  priority            INT DEFAULT 0,
  assigned_node_id    VARCHAR(36) REFERENCES nodes(id),
  assigned_gpu_indices INT[],
  container_image     VARCHAR(256),
  container_command   TEXT,
  container_id        VARCHAR(64),
  config_json         JSONB,
  result_json         JSONB,
  created_at          TIMESTAMP DEFAULT NOW(),
  started_at          TIMESTAMP,
  finished_at         TIMESTAMP,
  billed              BOOLEAN DEFAULT FALSE
);

-- 任务日志表
task_logs (
  id         BIGSERIAL PRIMARY KEY,
  task_id    VARCHAR(36) REFERENCES tasks(id),
  source     VARCHAR(20),
  message    TEXT,
  timestamp  TIMESTAMP DEFAULT NOW()
);

【API 接口】
POST /api/v1/auth/register  — 注册
  请求: {"username": "xxx", "password": "xxx"}
  响应: {"code": 0, "data": {"id": "...", "username": "..."}}

POST /api/v1/auth/login     — 登录
  请求: {"username": "xxx", "password": "xxx"}
  响应: {"code": 0, "data": {"access_token": "...", "token_type": "bearer"}}

GET  /api/v1/auth/me         — 当前用户信息（需 JWT）
  响应: {"code": 0, "data": {"id": "...", "username": "...", "role": "..."}}

【配置项】
DATABASE_URL=postgresql://suit:suit123@postgres:5432/suitdb
REDIS_URL=redis://redis:6379/0
JWT_SECRET=change-me-in-production
JWT_EXPIRE_MINUTES=1440

【完成标准】
1. docker compose up -d 能启动 postgres + redis + backend 三个容器
2. 能通过 POST /api/v1/auth/register 注册用户
3. 能通过 POST /api/v1/auth/login 获取 JWT token
4. 能通过 GET /api/v1/auth/me + Authorization: Bearer <token> 获取用户信息
5. 数据库迁移脚本能正常执行

【注意事项】
- 所有 API 响应统一格式: {"code": 0, "data": ..., "message": "ok"}
- 错误响应: {"code": 40001, "data": null, "message": "错误信息"}
- UUID 用 uuid.uuid4() 生成
- 密码用 bcrypt 哈希
- config.py 用 pydantic-settings，支持 .env 文件
```

---

## 阶段2：计算节点 Agent

### 提示词

```
你是一个 Python 后端开发工程师。

项目：SUIT API — 校内AI算力调度平台
你的任务是开发计算节点 Agent，部署在每台 GPU 服务器上。

【背景】
平台架构：1个管控节点（10.138.50.58）+ N个计算节点
管控节点运行 FastAPI 后端（:8000），计算节点运行 Agent（:9000）
Agent 负责：① 上报本机 GPU/资源信息  ② 接收指令执行 Docker 容器

【目录结构】
agent/
├── Dockerfile
├── requirements.txt
├── agent.py                # FastAPI 主程序，监听 :9000
├── gpu_monitor.py          # GPU 信息采集（nvidia-smi）
├── resource_monitor.py     # CPU/内存/磁盘采集
├── container_tracker.py    # 运行中容器列表
└── heartbeat.py            # 心跳上报线程

【Agent 需要提供的 API（管控节点调用）】

GET  /api/health
  响应: {"status": "ok", "node_id": "node-151"}

POST /api/run
  请求: {
    "task_id": "task-001",
    "image": "pytorch/pytorch:2.0-cuda11.8",
    "gpus": [0],              -- GPU 索引列表，空数组表示不用 GPU
    "command": "python train.py",
    "volumes": {"/host/path": "/container/path"}
  }
  响应: {"container_id": "abc123", "status": "running"}
  说明: 用 docker SDK 执行 docker run，GPU 通过 --gpus '"device=0,1"' 指定

POST /api/stop
  请求: {"container_id": "abc123"}
  响应: {"status": "stopped"}
  说明: docker stop + docker rm

GET  /api/logs/{container_id}?tail=100
  响应: {"logs": "容器 stdout+stderr 最近 N 行"}
  说明: docker logs --tail N

【心跳上报（Agent 主动调用管控节点）】

每 10 秒 POST http://<CONTROL_PLANE>:8000/api/v1/nodes/heartbeat
请求体:
{
  "node_id": "node-151",
  "timestamp": "2026-05-06T14:30:00Z",
  "hostname": "gpu-server-1",
  "ip": "10.138.50.151",
  "agent_port": 9000,
  "gpus": [
    {
      "index": 0,
      "model": "NVIDIA GeForce RTX 3090",
      "uuid": "GPU-abc123",
      "memory_total": 24576,
      "memory_used": 8192,
      "memory_free": 16384,
      "utilization_gpu": 85,
      "utilization_memory": 72,
      "temperature": 72,
      "power_usage": 280,
      "power_limit": 350,
      "processes": [
        {"pid": 12345, "name": "python", "memory_used": 6144}
      ]
    }
  ],
  "cpu": {
    "percent": 45.2,
    "cores": 16,
    "load_average": [1.25, 1.10, 0.95]
  },
  "memory": {
    "total": 65536,
    "used": 40632,
    "available": 24904,
    "percent": 62.1
  },
  "disk": {
    "total": 1000000,
    "used": 550000,
    "free": 450000,
    "percent": 55.0
  },
  "running_containers": [
    {
      "container_id": "abc123",
      "task_id": "task-001",
      "image": "pytorch/pytorch:2.0-cuda11.8",
      "status": "running",
      "gpu_indices": [0],
      "started_at": "2026-05-06T13:00:00Z"
    }
  ]
}

【管控节点心跳 API（你需要在阶段1的后端中新增）】

POST /api/v1/nodes/heartbeat
  功能：接收 Agent 心跳，更新节点和 GPU 状态
  逻辑：
    1. 如果节点不存在（按 ip 判断），自动注册
    2. 更新 nodes 表的 last_heartbeat, status='online'
    3. 更新/插入 gpu_devices 表的 GPU 信息
    4. 更新 running_containers 信息
  响应: {"code": 0, "data": {"node_id": "..."}}

GET  /api/v1/nodes
  功能：列出所有节点及其 GPU 状态
  响应: {"code": 0, "data": [{"id": "...", "ip": "...", "gpus": [...]}]}

GET  /api/v1/resources/gpus
  功能：列出所有空闲 GPU
  响应: {"code": 0, "data": [{"node_id": "...", "gpu_index": 0, "status": "idle", ...}]}

【GPU 采集方式】
用 subprocess 执行 nvidia-smi -q -x，解析 XML 输出。
不要用 pynvml（减少依赖）。

【环境变量】
CONTROL_PLANE=http://10.138.50.58:8000
NODE_NAME=node-151
NODE_IP=10.138.50.151
AGENT_PORT=9000

【完成标准】
1. Agent 启动后每 10 秒上报心跳到管控节点
2. 管控节点 GET /api/v1/nodes 能看到节点和 GPU 信息
3. POST /api/run 能在计算节点上启动 Docker 容器
4. POST /api/stop 能停止容器
5. GET /api/logs/{id} 能获取容器日志
6. 容器启动/停止时，running_containers 信息实时更新

【注意事项】
- Agent 必须挂载 /var/run/docker.sock 才能操作 Docker
- GPU 容器必须用 nvidia-container-runtime（--gpus 参数）
- 心跳失败不能导致 Agent 崩溃（容错）
- 容器执行器要用 docker SDK（import docker），不要用 subprocess
```

---

## 阶段3：任务管理

### 提示词

```
你是一个 Python 后端开发工程师。

项目：SUIT API — 校内AI算力调度平台
你的任务是在后端中实现任务管理模块。

【背景】
任务是平台的核心实体。用户创建任务 → 提交到队列 → 调度执行 → 完成。
本阶段只做任务的 CRUD 和状态流转，调度执行在阶段4完成。

【数据库表】
已有 tasks 和 task_logs 表（阶段1创建），字段如下：

tasks:
  id, user_id, name, task_type, status, priority,
  assigned_node_id, assigned_gpu_indices, container_image,
  container_command, container_id, config_json, result_json,
  created_at, started_at, finished_at

task_logs:
  id, task_id, source, message, timestamp

status 枚举: pending → queued → running → success / failed / cancelled

【API 接口】

POST /api/v1/tasks  — 创建任务
  请求: {
    "name": "ResNet50 训练",
    "task_type": "train",          -- train / inference / custom
    "container_image": "pytorch/pytorch:2.0-cuda11.8",
    "container_command": "python train.py --epochs 50",
    "priority": 0,                 -- 0=normal, 10=high, -10=low
    "config_json": {
      "gpu_count": 1,
      "gpu_model": "RTX 3090",    -- 可选，GPU 型号要求
      "min_memory_mb": 8192,       -- 可选，最低显存要求
      "env_vars": {"KEY": "VALUE"},
      "max_runtime_seconds": 3600
    }
  }
  响应: {"code": 0, "data": {"id": "...", "status": "pending"}}

GET /api/v1/tasks — 任务列表（支持筛选和分页）
  参数: ?status=running&task_type=train&page=1&page_size=20
  响应: {"code": 0, "data": {"items": [...], "total": 100}}

GET /api/v1/tasks/{id} — 任务详情
  响应: {"code": 0, "data": {完整任务信息 + 最近日志}}

POST /api/v1/tasks/{id}/submit — 提交任务到调度队列
  条件: status 必须为 pending
  操作: status 改为 queued，写入 Redis 调度队列
  Redis 操作: LPUSH suit:queue:{priority} {"task_id": "...", "enqueued_at": ...}
  响应: {"code": 0, "data": {"status": "queued"}}

POST /api/v1/tasks/{id}/cancel — 取消任务
  条件: status 为 pending 或 queued
  操作: status 改为 cancelled
  如果已分配节点: 调用 Agent 停止容器

POST /api/v1/tasks/{id}/callback — Agent 任务状态回调
  请求: {
    "status": "running",           -- running / success / failed
    "container_id": "abc123",
    "exit_code": 0,                -- 任务结束时
    "error_message": "",           -- 失败时
    "logs_chunk": "最近日志"        -- 可选
  }
  操作:
    - status=running: 更新 tasks.status, started_at, container_id
    - status=success: 更新 tasks.status, finished_at, result_json
    - status=failed: 更新 tasks.status, finished_at, error 信息
    - 写入 task_logs
    - 任务结束时，通知调度器（Redis PUBLISH suit:task:finished {task_id}）

GET /api/v1/tasks/{id}/logs — 任务日志
  参数: ?tail=100
  响应: {"code": 0, "data": {"logs": [{"source": "stdout", "message": "...", "timestamp": "..."}]}}

DELETE /api/v1/tasks/{id} — 删除任务
  条件: status 为 success / failed / cancelled
  操作: 删除 tasks 和 task_logs

【Redis 队列约定】
队列名按优先级分:
  suit:queue:high    — priority >= 10
  suit:queue:normal  — 0 <= priority < 10
  suit:queue:low     — priority < 0

入队格式: LPUSH suit:queue:{level} {"task_id": "xxx", "enqueued_at": timestamp}
出队格式: RPOP suit:queue:{level}（先 high → normal → low）

任务完成通知: PUBLISH suit:task:finished {"task_id": "xxx"}

【完成标准】
1. POST /api/v1/tasks 能创建任务，返回 task_id
2. GET /api/v1/tasks 能查询任务列表，支持 status 筛选和分页
3. POST /api/v1/tasks/{id}/submit 能将任务状态改为 queued，并写入 Redis 队列
4. POST /api/v1/tasks/{id}/callback 能更新任务状态和日志
5. POST /api/v1/tasks/{id}/cancel 能取消排队中的任务
6. 任务日志能正确写入和查询

【注意事项】
- task_type 字段用于区分训练/推理/自定义，目前不影响逻辑，留给阶段6
- config_json 用 PostgreSQL 的 JSONB 类型
- callback 接口不需要鉴权（Agent 调用，通过内部网络保护）
- 所有写操作需要 JWT 鉴权（除 callback）
```

---

## 阶段4：调度引擎

### 提示词

```
你是一个 Python 后端开发工程师。

项目：SUIT API — 校内AI算力调度平台
你的任务是开发独立的调度服务。

【背景】
调度服务是独立的 Docker 容器，持续运行。
它从 Redis 队列取出任务 → 分配 GPU → 通过 Agent 启动容器。
不依赖 Celery，是一个简单的 Python 进程。

【目录结构】
scheduler/
├── Dockerfile
├── requirements.txt
├── main.py                 # 入口，启动调度主循环
├── scheduler.py            # 调度主逻辑
├── queue_manager.py        # Redis 队列操作
├── gpu_allocator.py        # GPU 分配策略
├── container_manager.py    # 通过 Agent 管理容器
└── agent_client.py         # Agent HTTP 客户端

【调度主循环（scheduler.py）】

class Scheduler:
    def run(self):
        """持续运行的调度循环"""
        while True:
            # 1. 从 Redis 队列取任务（按优先级：high → normal → low）
            task_data = self.queue.dequeue()
            if not task_data:
                time.sleep(1)
                continue

            # 2. 从数据库查任务详情
            task = self.get_task(task_data["task_id"])
            if not task or task.status != "queued":
                continue

            # 3. 查询所有在线节点的 GPU 状态
            nodes = self.get_online_nodes()

            # 4. 分配 GPU
            allocation = self.allocator.allocate(task, nodes)
            if not allocation:
                # 没有可用 GPU，放回队列
                self.queue.requeue(task_data)
                time.sleep(5)
                continue

            # 5. 通过 Agent 启动容器
            try:
                result = self.container_mgr.launch(task, allocation)
                # 6. 更新任务状态为 running
                self.update_task_running(task, allocation, result["container_id"])
            except Exception as e:
                # 启动失败，释放 GPU，任务标记 failed
                self.allocator.release(allocation)
                self.update_task_failed(task, str(e))

【GPU 分配策略（gpu_allocator.py）】

class GpuAllocator:
    def allocate(self, task, nodes) -> Allocation | None:
        """
        分配逻辑：
        1. 从 task.config_json 读取要求：gpu_count, gpu_model, min_memory_mb
        2. 遍历所有在线节点
        3. 对每个节点，找 status='idle' 且满足型号/显存要求的 GPU
        4. 如果找到足够数量的 GPU，记录分配结果
        5. 多个候选节点时，选空闲 GPU 最多的（负载均衡）
        6. 在数据库中将分配的 GPU 标记为 status='allocated'
        """
        ...

    def release(self, allocation):
        """释放 GPU（将 status 改回 idle）"""
        ...

    def release_by_task(self, task_id):
        """根据任务 ID 释放其占用的所有 GPU"""
        ...

【容器管理（container_manager.py）】

class ContainerManager:
    def launch(self, task, allocation) -> dict:
        """
        通过 Agent 启动容器
        POST http://{node_ip}:{agent_port}/api/run
        {
          "task_id": task.id,
          "image": task.container_image,
          "gpus": allocation.gpu_indices,
          "command": task.container_command,
          "volumes": {
            "/data/tasks/{task_id}": "/workspace"
          }
        }
        """
        ...

    def stop(self, task):
        """通过 Agent 停止容器"""
        ...

【Agent 客户端（agent_client.py）】

class AgentClient:
    def __init__(self, node_ip, agent_port=9000):
        self.base_url = f"http://{node_ip}:{agent_port}"

    def launch_task(self, task_id, image, gpus, command, volumes) -> dict: ...
    def stop_task(self, container_id) -> dict: ...
    def get_logs(self, container_id, tail=100) -> str: ...
    def health_check(self) -> bool: ...

【队列管理（queue_manager.py）】

class QueueManager:
    QUEUES = ["suit:queue:high", "suit:queue:normal", "suit:queue:low"]

    def dequeue(self) -> dict | None:
        """按优先级出队：RPOP high → normal → low"""

    def requeue(self, task_data):
        """放回 normal 队列（资源不足时）"""

    def queue_length(self) -> dict:
        """各队列长度"""

【触发时机】
1. 主循环持续轮询（每 1 秒）
2. Redis Pub/Sub 监听 suit:task:finished 频道，收到后立即尝试调度
3. 两个机制并行：轮询保底，Pub/Sub 加速

【环境变量】
DATABASE_URL=postgresql://suit:suit123@postgres:5432/suitdb
REDIS_URL=redis://redis:6379/0
AGENT_PORT=9000

【完成标准】
1. 调度服务启动后持续监听 Redis 队列
2. 提交任务后，调度器自动分配 GPU 并通过 Agent 启动容器
3. 任务完成后（callback），调度器自动调度下一个排队任务
4. 没有空闲 GPU 时，任务保持 queued 状态等待
5. 多任务排队时按优先级调度
6. 任务失败时 GPU 被正确释放

【端到端验证流程】
1. 确保 Agent 在 10.138.50.151 运行且心跳正常
2. 提交一个无 GPU 任务：python -c "print('hello')"
   → 状态变化：pending → queued → running → success
3. 提交一个 GPU 任务：nvidia-smi
   → 在 151 节点的 GPU 上执行
4. 同时提交 3 个需要 1 GPU 的任务（假设只有 2 张空闲）
   → 2 个 running，1 个 queued
   → 前面完成后第 3 个自动调度
```

---

## 阶段5：前端控制台

### 提示词

```
你是一个 Vue3 前端开发工程师。

项目：SUIT API — 校内AI算力调度平台
你的任务是开发前端控制台。

【技术栈】
Vue 3 + Vite + TypeScript + Element Plus + Pinia + Axios + ECharts

【目录结构】
frontend/
├── index.html
├── vite.config.ts
├── package.json
├── tsconfig.json
├── src/
│   ├── main.ts
│   ├── App.vue
│   ├── router/index.ts
│   ├── stores/
│   │   ├── auth.ts             # 用户认证状态（token, user）
│   │   ├── nodes.ts            # 节点/GPU 状态
│   │   └── tasks.ts            # 任务状态
│   ├── api/
│   │   ├── request.ts          # Axios 实例（拦截器）
│   │   ├── auth.ts             # 认证接口
│   │   ├── nodes.ts            # 节点接口
│   │   └── tasks.ts            # 任务接口
│   ├── views/
│   │   ├── Login.vue           # 登录页
│   │   ├── Dashboard.vue       # 首页
│   │   ├── resources/
│   │   │   └── NodeList.vue    # 节点列表
│   │   └── tasks/
│   │       ├── TaskList.vue    # 任务列表
│   │       ├── TaskSubmit.vue  # 任务提交
│   │       └── TaskDetail.vue  # 任务详情
│   ├── components/
│   │   ├── Layout.vue          # 布局（侧边栏+顶栏）
│   │   ├── GpuStatusCard.vue   # GPU 状态卡片
│   │   └── TaskStatusBadge.vue # 任务状态标签
│   └── utils/
│       └── websocket.ts        # WebSocket 连接

【后端 API 基础路径】
开发时: http://10.138.50.58:8000/api/v1
生产时: /api/v1（nginx 反代）

vite.config.ts 中配置 proxy:
export default defineConfig({
  server: {
    proxy: {
'/api': 'http://10.138.50.58:8000'
    }
  }
})

【API 接口（对接后端）】

认证:
  POST /api/v1/auth/login    → {access_token, token_type}
  GET  /api/v1/auth/me        → {id, username, role}

节点:
  GET  /api/v1/nodes          → [{id, ip, hostname, status, gpu_count, gpus: [...]}]
  GET  /api/v1/resources/gpus → [{node_id, gpu_index, status, gpu_model, utilization, ...}]

任务:
  POST /api/v1/tasks          → 创建任务
  GET  /api/v1/tasks?status=&page=&page_size= → 任务列表
  GET  /api/v1/tasks/{id}     → 任务详情
  POST /api/v1/tasks/{id}/submit → 提交到队列
  POST /api/v1/tasks/{id}/cancel → 取消
  GET  /api/v1/tasks/{id}/logs   → 任务日志

【页面设计】

Login.vue:
  - 居中登录表单（用户名+密码）
  - 登录成功后存 token 到 localStorage，跳转 Dashboard

Layout.vue:
  - 左侧边栏：首页 / 资源管理 / 任务管理
  - 顶栏：用户名 + 退出按钮
  - 右侧内容区 <router-view>

Dashboard.vue:
  - 顶部 4 个统计卡片：在线节点数 / GPU 总数 / 空闲 GPU / 运行中任务
  - 中间：最近任务列表（表格，10 条）
  - 数据每 10 秒自动刷新

NodeList.vue:
  - 节点卡片列表
  - 每个节点显示：IP、状态、CPU/内存使用率
  - 每张 GPU 显示：型号、利用率进度条、显存进度条、温度
  - 空闲 GPU 绿色，已分配 GPU 红色，离线节点灰色
  - 数据每 10 秒自动刷新

TaskList.vue:
  - 顶部筛选栏：状态（全部/running/queued/success/failed）+ 搜索
  - 表格：名称、类型、状态（带颜色标签）、GPU、节点、创建时间、操作
  - 操作：查看详情、取消（queued时）、删除（完成时）
  - 分页

TaskSubmit.vue:
  - 表单：任务名称、类型（下拉）、镜像、命令（多行文本框）
  - GPU 要求：数量、型号（可选）、最低显存（可选）
  - 优先级：高/普通/低
  - 提交按钮 → POST /api/v1/tasks → POST /api/v1/tasks/{id}/submit
  - 提交成功后跳转任务列表

TaskDetail.vue:
  - 基本信息：名称、类型、状态、创建时间、运行时长
  - GPU 信息：节点IP、GPU索引、GPU型号
  - 实时日志：自动滚动的终端风格日志区
  - 操作按钮：取消、停止、删除

【Axios 拦截器（request.ts）】
- 请求拦截：自动带 Authorization: Bearer <token>
- 响应拦截：
  - code=0 正常，返回 data
  - code=401 跳转登录页
  - 其他错误 ElMessage.error(message)

【WebSocket】
连接 ws://10.138.50.58:8000/ws/tasks
后端推送：{"task_id": "...", "status": "running"}
收到后更新对应任务的状态

【完成标准】
1. 浏览器打开能看到登录页
2. 登录后进入 Dashboard，能看到节点数、GPU 数、运行中任务数
3. 资源管理页能看到节点列表和每张 GPU 的实时状态
4. 能提交任务（填写表单 → 提交 → 出现在任务列表）
5. 任务列表能按状态筛选，能看到状态变化
6. 任务详情能看到日志
7. 数据每 10 秒自动刷新
```

---

## 阶段6：AI 能力层

### 提示词

```
你是一个 Python 后端开发工程师。

项目：SUIT API — 校内AI算力调度平台
你的任务是在后端中实现 AI 能力供给层。

【背景】
平台的核心价值是对外提供 AI API（类似火山引擎）。
用户/第三方应用通过 OpenAI 兼容格式调用模型推理。
你需要实现：模型管理 + 推理网关。

【新增数据库表】

-- 模型注册表
models (
  id              VARCHAR(36) PRIMARY KEY,
  name            VARCHAR(128) UNIQUE NOT NULL,  -- "qwen-7b", "llama3-8b"
  display_name    VARCHAR(128),
  model_type      VARCHAR(32),                   -- llm / embedding / cv / tts
  framework       VARCHAR(32),                   -- vllm / transformers / onnx
  model_path      VARCHAR(512),                  -- 模型文件路径
  container_image VARCHAR(256),                  -- 推理镜像
  launch_command  TEXT,                           -- 启动命令
  config_json     JSONB,                         -- 端口、参数等
  status          VARCHAR(20) DEFAULT 'offline', -- online / offline / deploying / error
  replicas        INT DEFAULT 1,
  gpu_requirement VARCHAR(64),                   -- "1x RTX3090"
  api_format      VARCHAR(32) DEFAULT 'openai',
  description     TEXT,
  created_at      TIMESTAMP DEFAULT NOW(),
  updated_at      TIMESTAMP DEFAULT NOW()
);

-- 模型运行实例表
model_instances (
  id              VARCHAR(36) PRIMARY KEY,
  model_id        VARCHAR(36) REFERENCES models(id),
  node_id         VARCHAR(36) REFERENCES nodes(id),
  container_id    VARCHAR(64),
  assigned_gpu_indices INT[],
  port            INT,
  status          VARCHAR(20) DEFAULT 'starting',
  api_endpoint    VARCHAR(256),  -- "http://10.138.50.151:8001"
  started_at      TIMESTAMP DEFAULT NOW()
);

【新增 API 接口】

模型管理:
  POST /api/v1/models               — 注册模型
  GET  /api/v1/models               — 模型列表
  GET  /api/v1/models/{id}          — 模型详情
  PUT  /api/v1/models/{id}          — 更新模型
  DELETE /api/v1/models/{id}        — 删除模型
  POST /api/v1/models/{id}/deploy   — 部署模型（启动推理容器）
  POST /api/v1/models/{id}/stop     — 停止模型部署
  GET  /api/v1/models/{id}/instances — 运行实例列表

AI 推理网关（OpenAI 兼容）:
  POST /v1/chat/completions
  POST /v1/completions
  POST /v1/embeddings
  GET  /v1/models                   — 可用模型列表（对外）

【推理网关实现（ai_gateway.py + ai_service.py）】

POST /v1/chat/completions 请求格式（OpenAI 兼容）:
{
  "model": "qwen-7b",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "你好"}
  ],
  "temperature": 0.7,
  "max_tokens": 1024,
  "stream": false
}

处理流程:
1. 从 Authorization: Bearer <api_key> 验证用户
2. 根据 model 名称找到对应的 model_instances（status=running）
3. 如果没有运行中的实例，返回错误（模型未部署）
4. 有多个实例时，选负载最低的（轮询）
5. 将请求转发到实例的 api_endpoint/v1/chat/completions
6. 返回结果给用户
7. 记录 api_calls（用户ID、模型、Token数、延迟）

流式响应（stream=true）:
- 使用 httpx 异步流式请求
- 逐 chunk 转发给客户端
- SSE 格式：data: {...}\n\n

【模型部署流程（model_service.py）】

deploy(model_id):
  1. 查模型配置（image、command、GPU要求）
  2. 通过调度器分配 GPU（调用 gpu_allocator）
  3. 通过 Agent 启动推理容器
     docker run --gpus '"device=0"' -p 8001:8000 {image} {command}
  4. 等待容器内推理服务就绪（健康检查）
  5. 记录 model_instances
  6. 更新 models.status = 'online'

stop(model_id):
  1. 查所有 model_instances
  2. 通过 Agent 停止每个容器
  3. 释放 GPU
  4. 删除 instances 记录
  5. 更新 models.status = 'offline'

【推理镜像约定】
推荐使用 vLLM 作为推理引擎:
  镜像: vllm/vllm-openai:latest
  启动: python -m vllm.entrypoints.openai.api_server --model {model_path} --port 8000
  健康检查: GET http://{node_ip}:{port}/health
  API: 原生支持 OpenAI 格式

【完成标准】
1. 能注册模型（POST /api/v1/models）
2. 能部署模型（POST /api/v1/models/{id}/deploy）→ 在计算节点启动推理容器
3. 能通过 POST /v1/chat/completions 调用模型推理
4. 返回 OpenAI 兼容格式的响应
5. 能停止模型部署（POST /api/v1/models/{id}/stop）
6. API Key 鉴权正常
7. 调用记录写入 api_calls 表
```

---

## 阶段7：监控与计费

### 提示词

```
你是一个 Python 后端开发工程师。

项目：SUIT API — 校内AI算力调度平台
你的任务是实现监控采集和计费系统。

【背景】
平台已有节点、GPU、任务数据。你需要：
1. 定时采集 GPU/节点指标，存入数据库
2. 任务完成时自动计算费用
3. 提供监控和计费查询 API

【新增数据库表】

-- GPU 指标时序表
gpu_metrics (
  id          BIGSERIAL PRIMARY KEY,
  node_id     VARCHAR(36) REFERENCES nodes(id),
  gpu_index   INT,
  utilization INT,
  memory_used INT,
  memory_total INT,
  temperature INT,
  power_usage INT,
  timestamp   TIMESTAMP DEFAULT NOW()
);

-- 计费记录表
billing_records (
  id               BIGSERIAL PRIMARY KEY,
  user_id          VARCHAR(36),
  task_id          VARCHAR(36),
  resource_type    VARCHAR(20),      -- gpu_time / api_call
  gpu_model        VARCHAR(64),
  duration_seconds INT,
  cost_credits     DECIMAL(10,4),
  created_at       TIMESTAMP DEFAULT NOW()
);

-- API 调用记录表
api_calls (
  id            BIGSERIAL PRIMARY KEY,
  user_id       VARCHAR(36),
  api_key       VARCHAR(128),
  model_name    VARCHAR(64),
  endpoint      VARCHAR(128),
  tokens_input  INT DEFAULT 0,
  tokens_output INT DEFAULT 0,
  latency_ms    INT,
  status_code   INT,
  created_at    TIMESTAMP DEFAULT NOW()
);

【Celery 定时任务】

# app/tasks/monitor_tasks.py

@celery_app.task
def collect_gpu_metrics():
    """每 30 秒采集一次所有节点的 GPU 指标"""
    nodes = db.query(Node).filter(Node.status == "online").all()
    for node in nodes:
        for gpu in node.gpus:
            db.execute(
                "INSERT INTO gpu_metrics (node_id, gpu_index, utilization, memory_used, ...) VALUES (...)",
                ...
            )
    # 清理 7 天前的旧数据

@celery_app.task
def check_node_heartbeat():
    """每 30 秒检查节点心跳超时"""
    timeout = datetime.now() - timedelta(seconds=60)
    offline_nodes = db.query(Node).filter(Node.last_heartbeat < timeout).all()
    for node in offline_nodes:
        node.status = "offline"
        # 释放该节点所有 GPU
        # 将该节点上运行的任务标记为 failed

# app/tasks/billing_tasks.py

@celery_app.task
def calculate_billing():
    """每 5 分钟计算一次计费"""
    # 查询最近完成的任务
    tasks = db.query(Task).filter(
        Task.status == "success",
        Task.billed == False
    ).all()

    for task in tasks:
        duration = (task.finished_at - task.started_at).total_seconds()
        gpu_count = len(task.assigned_gpu_indices or [])
        cost = (duration / 3600) * gpu_count * GPU_HOUR_RATE

        db.add(BillingRecord(
            user_id=task.user_id,
            task_id=task.id,
            resource_type="gpu_time",
            duration_seconds=int(duration),
            cost_credits=cost
        ))

        # 扣除用户余额
        user = db.query(User).get(task.user_id)
        user.credits -= cost
        task.billed = True

【API 接口】

监控:
  GET /api/v1/monitor/gpu/history?node_id=&gpu_index=&hours=24
    → GPU 指标时序数据（用于画图）
    → [{"timestamp": "...", "utilization": 85, "memory_used": 8192, ...}, ...]

  GET /api/v1/monitor/nodes/overview
    → 所有节点当前状态汇总
    → [{"ip": "...", "status": "online", "gpu_count": 2, "gpu_used": 1, "cpu_percent": 45, ...}]

计费:
  GET /api/v1/billing/summary
    → 用户计费汇总
    → {"total_credits": 150.0, "used_credits": 45.5, "remaining": 104.5}

  GET /api/v1/billing/records?page=1&page_size=20
    → 计费明细列表
    → {"items": [{"task_name": "...", "gpu_model": "...", "duration": "1h30m", "cost": 1.5}], "total": 50}

【前端页面（补充）】

GpuMonitor.vue:
  - 节点选择下拉框
  - 每张 GPU 的实时监控图表（ECharts 折线图）
    - X 轴：时间（最近 1 小时）
    - Y 轴：利用率 % / 显存 MB / 温度 °C
  - 数据每 30 秒刷新

BillingOverview.vue:
  - 余额卡片
  - 本月消耗图表（柱状图）
  - 计费明细表格（分页）

【完成标准】
1. GPU 指标每 30 秒自动采集并存入 gpu_metrics 表
2. 节点心跳超时 60 秒自动标记为 offline
3. 任务完成自动计算费用并扣减余额
4. GET /api/v1/monitor/gpu/history 返回时序数据
5. GET /api/v1/billing/summary 返回用户余额和消耗
6. 前端 GPU 监控页面显示实时图表
7. 前端计费页面显示余额和明细
```

---

## 各阶段对接约定

```
阶段1 提供：
  - 数据库表结构（所有阶段共用）
  - 用户认证 API（JWT）
  - 统一响应格式 {"code": 0, "data": ..., "message": "ok"}

阶段2 提供：
  - Agent API（/api/run, /api/stop, /api/logs, /api/health）
  - 心跳上报 POST /api/v1/nodes/heartbeat
  - 节点查询 GET /api/v1/nodes

阶段3 提供：
  - 任务 CRUD API
  - Redis 队列入队（submit 时）
  - 任务回调 POST /api/v1/tasks/{id}/callback

阶段4 消费：
  - Redis 队列（阶段3写入）
  - 节点/GPU 状态（阶段2更新）
  - Agent API（阶段2提供）

阶段5 消费：
  - 所有后端 API（阶段1-3提供）

阶段6 提供：
  - 模型管理 API
  - AI 推理 API（/v1/chat/completions）
  - 新增 models, model_instances, api_calls 表

阶段7 消费：
  - 任务数据（阶段3提供）
  - 节点数据（阶段2提供）
  - 用户数据（阶段1提供）
```
