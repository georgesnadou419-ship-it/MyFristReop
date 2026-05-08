# 第二阶段：后端架构设计（FastAPI）

> 项目名称：SUIT API — 校内AI算力调度平台
> 更新日期：2026-05-06

---

## 1. 项目目录结构

```
SUIT_API/
├── docs/                           # 文档目录
│   ├── phase1-architecture.md
│   ├── phase2-backend.md
│   ├── phase3-scheduling.md
│   ├── phase4-frontend.md
│   ├── phase5-mvp.md
│   └── phase6-scaling.md
│
├── backend/                        # 后端主目录
│   ├── Dockerfile                  # 后端镜像
│   ├── requirements.txt            # Python 依赖
│   ├── alembic.ini                 # 数据库迁移配置
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI 入口，挂载所有 router
│   │   ├── config.py               # 配置管理（环境变量）
│   │   ├── database.py             # 数据库连接（SQLAlchemy engine/session）
│   │   ├── dependencies.py         # 公共依赖注入（get_db, get_current_user）
│   │   │
│   │   ├── models/                 # 数据库模型（SQLAlchemy ORM）
│   │   │   ├── __init__.py
│   │   │   ├── node.py             # Node, GpuDevice
│   │   │   ├── task.py             # Task, TaskLog
│   │   │   ├── user.py             # User
│   │   │   ├── api_call.py         # ApiCall
│   │   │   ├── billing.py          # BillingRecord
│   │   │   └── model.py            # AiModel, ModelInstance（阶段6使用，阶段1可先创建空文件）
│   │   │
│   │   ├── schemas/                # Pydantic 请求/响应模型
│   │   │   ├── __init__.py
│   │   │   ├── node.py
│   │   │   ├── task.py
│   │   │   ├── user.py
│   │   │   ├── api_call.py
│   │   │   ├── billing.py
│   │   │   └── model.py            # 模型相关 Schema（阶段6使用）
│   │   │
│   │   ├── routers/                # API 路由（按模块拆分）
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # 登录 / 注册 / Token
│   │   │   ├── nodes.py            # 节点管理 + Agent 心跳接口
│   │   │   ├── tasks.py            # 任务 CRUD + 提交 + 回调
│   │   │   ├── resources.py        # 资源查询（GPU 状态）
│   │   │   ├── models.py           # 模型管理（注册/部署/上下线）
│   │   │   ├── ai_gateway.py       # AI 推理网关（对外API，OpenAI兼容）
│   │   │   ├── billing.py          # 计费查询
│   │   │   └── admin.py            # 管理后台接口
│   │   │
│   │   ├── services/               # 业务逻辑层
│   │   │   ├── __init__.py
│   │   │   ├── node_service.py     # 节点注册、心跳处理、状态更新
│   │   │   ├── task_service.py     # 任务创建、状态流转、日志写入
│   │   │   ├── model_service.py    # 模型注册、部署、上下线、实例管理
│   │   │   ├── ai_service.py       # AI 推理请求处理（路由到模型实例）
│   │   │   ├── billing_service.py  # 计费计算
│   │   │   ├── monitor_service.py  # 监控数据查询（历史数据）
│   │   │   ├── agent_client.py     # Agent HTTP 客户端（async，供 model_service 调用）
│   │   │   └── auth_service.py     # 鉴权逻辑（JWT + API Key）
│   │   │
│   │   ├── tasks/                  # Celery 异步任务
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py       # Celery 实例配置
│   │   │   ├── monitor_tasks.py    # 监控采集异步任务
│   │   │   └── billing_tasks.py    # 计费计算异步任务
│   │   │
│   │   └── utils/                  # 工具函数
│   │       ├── __init__.py
│   │       ├── security.py         # JWT / 密码哈希 / API Key
│   │       └── exceptions.py       # 自定义异常
│   │
│   ├── migrations/                 # Alembic 迁移脚本
│   │   ├── env.py
│   │   └── versions/
│   │
│   └── tests/                      # 测试
│       ├── __init__.py
│       ├── test_nodes.py
│       └── test_tasks.py
│
├── frontend/                       # 前端主目录（Phase 4 详述）
│   └── ...
│
├── scheduler/                      # 独立调度服务（核心）
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                     # 调度服务入口
│   ├── scheduler.py                # 调度引擎主逻辑
│   ├── gpu_allocator.py            # GPU 分配策略
│   ├── queue_manager.py            # 任务队列管理（显式建模）
│   ├── container_manager.py        # 容器编排（通过 Agent）
│   ├── agent_client.py             # Agent HTTP 客户端（sync，供调度器调用）
│   ├── config.py                   # 调度服务配置
│   ├── database.py                 # 调度服务数据库连接
│   └── tests/
│       ├── __init__.py
│       └── test_scheduler.py
│
├── agent/                          # 计算节点 Agent（资源感知增强版）
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── agent.py                    # Agent 主程序（FastAPI）
│   ├── docker_executor.py          # Docker 容器执行器
│   ├── gpu_monitor.py              # GPU 状态采集 (nvidia-smi)
│   ├── container_tracker.py        # 运行中容器追踪
│   ├── resource_monitor.py         # CPU/内存/磁盘/网络监控
│   └── heartbeat.py                # 心跳上报（含完整资源信息）
│
├── deploy/                         # 部署配置
│   ├── docker-compose.yml          # 管控节点部署
│   ├── nginx.conf                  # Nginx 配置
│   ├── prometheus.yml              # Prometheus 配置
│   └── .env.example                # 环境变量示例
│
└── scripts/                        # 运维脚本
    ├── init_db.sh                  # 初始化数据库
    ├── add_node.sh                 # 添加计算节点
    └── backup.sh                   # 数据库备份
```

---

## 2. 模块职责划分

### 2.1 Router 层（routers/）— 只做请求分发

```
职责：
- 定义 API 路径和 HTTP 方法
- 参数校验（Pydantic Schema）
- 调用 Service 层
- 返回响应

原则：Router 不写业务逻辑，只做"接单→派单→返回"
```

各 Router 的 API 路径规划：

```python
# auth.py
POST   /api/v1/auth/login          # 登录，返回 JWT
POST   /api/v1/auth/register       # 注册
GET    /api/v1/auth/me              # 当前用户信息

# nodes.py
GET    /api/v1/nodes                # 列出所有节点
GET    /api/v1/nodes/{id}           # 节点详情（含GPU状态）
POST   /api/v1/nodes/register       # Agent 注册节点（Agent调用）
POST   /api/v1/nodes/heartbeat      # Agent 心跳上报（Agent调用，含GPU/容器/资源完整信息）
PUT    /api/v1/nodes/{id}/status    # 管理员修改节点状态

# tasks.py
GET    /api/v1/tasks                # 任务列表（支持筛选/分页）
GET    /api/v1/tasks/{id}           # 任务详情
POST   /api/v1/tasks                # 创建任务
POST   /api/v1/tasks/{id}/submit    # 提交任务到调度队列
POST   /api/v1/tasks/{id}/cancel    # 取消任务
POST   /api/v1/tasks/{id}/callback  # Agent 任务状态回调
GET    /api/v1/tasks/{id}/logs      # 任务日志
DELETE /api/v1/tasks/{id}           # 删除任务
WS     /ws/tasks                    # 任务状态实时推送（WebSocket）

# WebSocket 推送格式: {"task_id": "...", "status": "running", "node_id": "..."}
# 连接时需在 query 参数中带 JWT token: ws://host/ws/tasks?token=xxx

# resources.py
GET    /api/v1/resources/overview   # 资源总览（节点数/GPU总数/使用率）
GET    /api/v1/resources/gpus       # 所有 GPU 实时状态

# models.py —— 模型管理（AI 能力供给核心）
GET    /api/v1/models               # 模型列表（管理端）
POST   /api/v1/models               # 注册模型
GET    /api/v1/models/{id}          # 模型详情
PUT    /api/v1/models/{id}          # 更新模型配置
DELETE /api/v1/models/{id}          # 删除模型
POST   /api/v1/models/{id}/deploy   # 部署模型（启动推理容器）
POST   /api/v1/models/{id}/stop     # 停止模型部署
GET    /api/v1/models/{id}/instances # 模型运行实例列表

# ai_gateway.py —— AI 推理网关（对外产品接口，OpenAI 兼容）
POST   /v1/chat/completions         # Chat 推理（OpenAI 兼容）
POST   /v1/completions              # 文本补全（OpenAI 兼容）
POST   /v1/embeddings               # 向量嵌入（OpenAI 兼容）
GET    /v1/models                   # 可用模型列表（对外）
POST   /v1/images/generations       # 图像生成（预留）

# billing.py
GET    /api/v1/billing/summary      # 用户计费汇总
GET    /api/v1/billing/records      # 计费明细

# admin.py
GET    /api/v1/admin/dashboard      # 管理后台数据
GET    /api/v1/admin/users          # 用户管理
PUT    /api/v1/admin/users/{id}     # 修改用户
```

### 2.2 Service 层（services/）— 核心业务逻辑

```
职责：
- 所有业务逻辑集中在 Service 层
- Service 之间可以互相调用
- Service 不直接处理 HTTP 请求/响应
```

| Service | 职责 |
|---------|------|
| `node_service` | 节点注册、心跳处理（更新GPU/CPU/内存状态到数据库）、节点上下线 |
| `task_service` | 任务创建、状态流转（pending→queued→running→success/failed）、日志写入 |
| `model_service` | **模型管理核心**：模型注册、部署（启动推理容器）、上下线、实例管理 |
| `ai_service` | **AI推理核心**：接收外部API请求 → 路由到对应模型实例 → 返回结果 |
| `billing_service` | 计费计算：GPU时长 + API调用次数/Token |
| `monitor_service` | 监控数据查询（给前端提供历史数据），采集逻辑在 celery tasks/monitor_tasks.py |
| `auth_service` | JWT 生成/验证、密码校验、API Key 验证 |

**注意：调度逻辑已独立到 `scheduler/` 服务中，不在 backend 的 services 里。**

### 2.3 数据模型层（models/）— ORM 映射

```
职责：
- 定义数据库表结构（SQLAlchemy Model）
- 定义表关系（ForeignKey）
- 不包含业务逻辑
```

### 2.4 Schema 层（schemas/）— 数据校验

```
职责：
- 请求体校验（Pydantic BaseModel）
- 响应体序列化
- 不直接操作数据库
```

---

## 3. 调度逻辑：独立调度服务

```
⚠️ 重要修正：调度逻辑从 celery-worker 中独立出来，成为单独的服务

原因：
1. 调度是平台核心，不应混在通用异步任务中
2. 需要持久运行、主动轮询，不是被动触发
3. 后续扩展复杂调度策略时，独立服务更易维护
4. 可以独立扩缩容（调度瓶颈时单独加实例）
```

### 调度服务架构

```
┌─────────────────────────────────────────────────────────────┐
│  scheduler 服务（独立 Docker 容器）                          │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ queue_manager │  │  scheduler   │  │ container_manager│  │
│  │              │  │              │  │                  │  │
│  │ - 任务入队    │  │ - 轮询队列    │  │ - 启动容器       │  │
│  │ - 优先级排序  │  │ - 资源匹配    │  │ - 停止容器       │  │
│  │ - 队列状态    │  │ - 分配决策    │  │ - 状态查询       │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                 │                    │            │
│         └─────────────────┼────────────────────┘            │
│                           │                                 │
│                    ┌──────▼───────┐                         │
│                    │   Redis       │  任务队列               │
│                    │   + 数据库    │  状态存储               │
│                    └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

### 调度流程

```
Router (tasks.py)
  POST /api/v1/tasks          → task_service.create_task()     # 创建任务，status=pending
  POST /api/v1/tasks/{id}/submit → task_service.submit_task()  # status=pending→queued
                                  → queue_manager.enqueue(task) # 写入 Redis 队列

scheduler 服务（独立进程，持续运行）
  while True:
      task = queue_manager.dequeue()       # 从 Redis 取出最高优先级任务
      if task is None:
          sleep(1)
          continue
      allocation = gpu_allocator.find()    # 查找空闲GPU
      if allocation is None:
          queue_manager.requeue(task)      # 放回队列
          sleep(5)
          continue
      container_manager.launch(task, allocation)  # 通过 Agent 启动容器
      task_service.update_status(task, "running")
```

### 调度触发时机

```
1. 实时：scheduler 服务持续轮询 Redis 队列（每 1 秒）
2. 唤醒：任务入队时通过 Redis Pub/Sub 通知 scheduler 立即处理
3. 回调：Agent 报告任务完成 → scheduler 立即尝试调度下一个
```

---

## 4. 任务队列设计

### 4.1 双队列架构

```
⚠️ 修正：任务队列分为两层

1. 调度队列（Redis List）—— scheduler 服务消费
   - 存放等待执行的 GPU 任务
   - 支持优先级（多个 List：high/normal/low）
   - scheduler 服务直接消费，不经过 Celery

2. 异步任务队列（Celery + Redis）—— celery-worker 消费
   - 监控采集、计费计算等非调度类异步任务
   - 定时任务通过 celery-beat 触发
```

### 4.2 调度队列（Redis List）

```python
# scheduler/queue_manager.py

import json
import redis

class QueueManager:
    """显式任务队列管理（Redis List）"""

    QUEUE_HIGH = "suit:queue:high"
    QUEUE_NORMAL = "suit:queue:normal"
    QUEUE_LOW = "suit:queue:low"

    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)

    def enqueue(self, task_id: str, priority: int = 0):
        """任务入队"""
        queue = self._get_queue(priority)
        data = json.dumps({"task_id": task_id, "enqueued_at": time.time()})
        self.redis.lpush(queue, data)  # 左侧入队
        # 通知 scheduler 有新任务
        self.redis.publish("suit:queue:new", task_id)

    def dequeue(self) -> dict | None:
        """按优先级出队：high → normal → low"""
        for queue in [self.QUEUE_HIGH, self.QUEUE_NORMAL, self.QUEUE_LOW]:
            result = self.redis.rpop(queue)  # 右侧出队（FIFO）
            if result:
                return json.loads(result)
        return None

    def requeue(self, task_data: dict):
        """放回队列（资源不足时）"""
        self.redis.rpush(self.QUEUE_NORMAL, json.dumps(task_data))

    def queue_length(self) -> dict:
        """各队列长度"""
        return {
            "high": self.redis.llen(self.QUEUE_HIGH),
            "normal": self.redis.llen(self.QUEUE_NORMAL),
            "low": self.redis.llen(self.QUEUE_LOW),
        }

    def _get_queue(self, priority: int) -> str:
        if priority >= 10:
            return self.QUEUE_HIGH
        elif priority >= 0:
            return self.QUEUE_NORMAL
        else:
            return self.QUEUE_LOW
```

### 4.3 Celery（仅用于监控/计费）

```python
# app/tasks/celery_app.py

from celery import Celery

celery_app = Celery(
    "suitworker",
    broker="redis://redis:6379/2",    # 注意：用不同的 Redis DB
    backend="redis://redis:6379/3",
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    # 注意：调度已独立到 scheduler 服务
    task_routes={
        "app.tasks.monitor_tasks.*": {"queue": "monitoring"},
        "app.tasks.billing_tasks.*": {"queue": "billing"},
    },
    beat_schedule={
        "check-heartbeat-timeout": {
            "task": "app.tasks.monitor_tasks.check_node_heartbeat",
            "schedule": 30.0,
        },
        "collect-gpu-metrics": {
            "task": "app.tasks.monitor_tasks.collect_all_gpu_metrics",
            "schedule": 15.0,
        },
        "calculate-billing": {
            "task": "app.tasks.billing_tasks.calculate_billing",
            "schedule": 300.0,
        },
    },
)
```

### 4.4 为什么这样拆分？

| 组件 | 职责 | 为什么独立 |
|------|------|-----------|
| **scheduler 服务** | GPU 任务调度（排队→分配→执行） | 核心服务，需要持续运行、低延迟响应、独立扩缩 |
| **celery-worker** | 监控采集、计费计算 | 辅助任务，可容忍延迟，不需要低延迟 |
| **Redis 调度队列** | 存放待执行任务 | 显式建模，可查询队列长度、支持优先级 |
| **Celery 队列** | 存放异步辅助任务 | 成熟方案，有重试/定时/监控 |

---

## 5. Agent 通信协议

```
⚠️ 注意：存在两个 AgentClient
- backend/app/services/agent_client.py — async 版本，供 model_service 部署推理容器时使用
- scheduler/agent_client.py — sync 版本，供调度器执行任务容器时使用
两者接口相同，只是 async/sync 区别。
```

### 5.1 管控节点 → Agent（下发指令）

```python
# backend/app/services/agent_client.py

import httpx
from app.config import settings

class AgentClient:
    """与计算节点 Agent 通信的 async 客户端"""

    def __init__(self, node_ip: str, agent_port: int = 9000):
        self.base_url = f"http://{node_ip}:{agent_port}"
        self.client = httpx.AsyncClient(timeout=10.0)

    async def launch_task(self, task_id: str, image: str, gpus: list[int],
                          command: str, volumes: dict[str, str]) -> dict:
        """在计算节点上启动任务容器"""
        resp = await self.client.post(f"{self.base_url}/api/run", json={
            "task_id": task_id,
            "image": image,
            "gpus": gpus,
            "command": command,
            "volumes": volumes,
        })
        resp.raise_for_status()
        return resp.json()

    async def stop_task(self, container_id: str) -> dict:
        """停止任务容器"""
        resp = await self.client.post(f"{self.base_url}/api/stop", json={
            "container_id": container_id,
        })
        resp.raise_for_status()
        return resp.json()

    async def get_logs(self, container_id: str, tail: int = 100) -> str:
        """获取容器日志"""
        resp = await self.client.get(f"{self.base_url}/api/logs/{container_id}",
                                      params={"tail": tail})
        resp.raise_for_status()
        return resp.json()["logs"]

    async def health_check(self) -> bool:
        """检查 Agent 是否存活"""
        try:
            resp = await self.client.get(f"{self.base_url}/api/health")
            return resp.status_code == 200
        except Exception:
            return False
```

### 5.2 Agent → 管控节点（心跳 + 回调）

```
Agent 主动调用管控节点的 API：

心跳：
POST http://10.138.50.58:8000/api/v1/nodes/heartbeat
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
        {"pid": 12345, "name": "python", "memory_used": 6144},
        {"pid": 12346, "name": "python", "memory_used": 2048}
      ]
    },
    {
      "index": 1,
      "model": "NVIDIA GeForce RTX 3090",
      "uuid": "GPU-def456",
      "memory_total": 24576,
      "memory_used": 0,
      "memory_free": 24576,
      "utilization_gpu": 0,
      "utilization_memory": 0,
      "temperature": 35,
      "power_usage": 25,
      "power_limit": 350,
      "processes": []
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

任务回调：
POST http://10.138.50.58:8000/api/v1/tasks/{task_id}/callback
{
  "status": "running",          // 或 "success" / "failed"
  "container_id": "abc123def",
  "exit_code": 0,               // 任务结束时有
  "error_message": "",          // 失败时有
  "logs_chunk": "最新10行日志"   // 可选，实时日志推送
}
```

---

## 6. 关键配置文件

```python
# app/config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 应用
    APP_NAME: str = "SUIT API"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"

    # 数据库
    DATABASE_URL: str = "postgresql://suit:suit123@postgres:5432/suitdb"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # JWT
    JWT_SECRET: str = "jwt-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24小时

    # Agent 通信
    AGENT_PORT: int = 9000
    AGENT_TIMEOUT: int = 10

    # 调度
    HEARTBEAT_TIMEOUT: int = 60     # 心跳超时（秒）
    MAX_GPU_PER_USER: int = 2       # 单用户最大占用GPU数

    # 计费
    GPU_HOUR_RATE: float = 1.0      # GPU每小时费用（credits）

    class Config:
        env_file = ".env"
```

---

## 7. 总结

```
后端架构分层：

外部 AI API 请求 ──→ ai_gateway (OpenAI兼容) ──→ ai_service ──→ 模型实例
内部管理请求 ──→ Router ──→ Service ──→ Model ──→ 数据库
                                 ↓
                          scheduler (独立服务，Redis队列)
                                 ↓
                          Agent (执行容器)
                                 ↓
                          celery-worker (监控/计费)

关键修正：
1. 调度逻辑独立为 scheduler 服务（不再混在 celery-worker 中）
2. 新增 AI 服务层（model_service + ai_service + ai_gateway）
3. Agent 增强为"资源感知"版本（GPU/CPU/内存/容器完整采集）
4. 任务队列显式建模（Redis List，可查询、可监控、支持优先级）
```
