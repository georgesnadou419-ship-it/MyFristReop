# 第一阶段：系统总体架构设计

> 项目名称：SUIT API — 校内AI算力调度平台
> 更新日期：2026-05-06
> 版本：v1.1

---

## 1. 服务器角色分配

| IP | 角色 | 说明 | GPU |
|----|------|------|-----|
| **10.138.50.58** | 管控节点（调度中心） | 部署平台所有服务，统一管理所有计算节点 | 不需要 |
| **10.138.50.151** | 计算节点 #1 | 有GPU，用于测试和执行AI任务 | 有 |
| 后续扩展... | 计算节点 #N | 安装 Docker + Agent 即可接入 | 有 |

**核心原则：管控节点管全局，计算节点只管执行。**

---

## 2. 部署拓扑图

```
    ┌──────────────────────────────────────────────────────────┐
    │                  外部调用者                               │
    │  用户浏览器 / 第三方应用 / 业务系统                       │
    │  调用 AI 能力接口（OpenAI 兼容格式）                      │
    └────────────┬─────────────────┬───────────────────────────┘
                 │                 │
                 │ http://10.138.50.58          POST /v1/chat/completions
                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│   10.138.50.58  ──  管控节点 (Control Plane / 调度中心)              │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │  Docker Compose 部署                                        │   │
│   │                                                             │   │
│   │  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌──────────────────┐ │   │
│   │  │  nginx   │ │ frontend │ │ backend │ │  scheduler       │ │   │
│   │  │  :80     │ │ (Vue3)   │ │(FastAPI)│ │  (独立调度服务)   │ │   │
│   │  └─────────┘ └──────────┘ └─────────┘ └──────────────────┘ │   │
│   │                                                             │   │
│   │  ┌──────────────┐ ┌──────────┐ ┌─────────────┐             │   │
│   │  │  celery-worker│ │ postgres │ │    redis    │             │   │
│   │  │  (监控/计费)  │ │  :5432   │ │   :6379     │             │   │
│   │  └──────────────┘ └──────────┘ └─────────────┘             │   │
│   │                                                             │   │
│   │  ┌──────────────┐ ┌──────────────┐                         │   │
│   │  │  celery-beat  │ │  prometheus  │                         │   │
│   │  └──────────────┘ └──────────────┘                         │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│            │ HTTP API (Agent 上报心跳 / 接收指令)                    │
│            │                                                        │
│            ▼                                                        │
│                                                                     │
│   ┌──────────────────────┐    ┌──────────────────────┐             │
│   │  计算节点 #1          │    │  计算节点 #2          │  ...       │
│   │  10.138.50.151       │    │  后续扩展             │             │
│   │                      │    │                      │             │
│   │  ┌────────────────┐  │    │  ┌────────────────┐  │             │
│   │  │   node-agent   │  │    │  │   node-agent   │  │             │
│   │  │  (资源感知+)    │  │    │  │  (资源感知+)    │  │             │
│   │  └────────────────┘  │    │  └────────────────┘  │             │
│   │                      │    │                      │             │
│   │  ┌────────────────┐  │    │  ┌────────────────┐  │             │
│   │  │  GPU 任务容器   │  │    │  │  GPU 任务容器   │  │             │
│   │  │  训练 / 推理    │  │    │  │  训练 / 推理    │  │             │
│   │  └────────────────┘  │    │  └────────────────┘  │             │
│   └──────────────────────┘    └──────────────────────┘             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. 各服务器详细职责

### 3.1 管控节点 10.138.50.58

| 容器 | 端口 | 职责 |
|------|------|------|
| nginx | 80 | 反向代理，前端静态文件托管，API 路由 |
| frontend | - | Vue3 控制台（构建产物由 nginx 托管） |
| backend | 8000 | FastAPI 主服务（业务API + **AI推理网关**） |
| **scheduler** | - | **独立调度服务**（任务排队、GPU分配、容器编排） |
| celery-worker | - | 异步任务（监控采集、计费计算，**不含调度**） |
| celery-beat | - | 定时任务（心跳超时检测、周期性指标采集） |
| redis | 6379 | DB0: 调度队列 / DB1: 调度缓存 / DB2: Celery broker / DB3: Celery backend / Pub/Sub: 任务通知 |
| postgres | 5432 | 主数据库（用户、任务、节点、模型、计费） |
| prometheus | 9090 | 监控指标存储 |

**硬件要求：** 无GPU需求，普通服务器即可。建议 8C16G 以上。

### 3.2 平台的两个核心身份

```
身份1：任务调度平台
  - 用户提交训练/推理任务
  - 调度到 GPU 节点执行
  - 返回结果和日志

身份2：AI 能力供给平台（重点！）
  - 对外暴露统一的 AI API（OpenAI 兼容格式）
  - 模型管理（部署、上下线、版本管理）
  - API 鉴权 + 限流 + 计费
  - 第三方可直接调用
```

### 3.3 计算节点 10.138.50.151

| 组件 | 说明 |
|------|------|
| Docker | 容器运行时 |
| NVIDIA Driver + CUDA | GPU 驱动 |
| NVIDIA Container Toolkit | Docker GPU 支持 |
| node-agent | 轻量 Python 容器，负责心跳上报 + 接收指令 |

**硬件要求：** 必须有 NVIDIA GPU，已安装驱动。

---

## 4. 数据流：提交任务到执行完成

```
① 用户在浏览器 (http://10.138.50.58) 提交训练任务
        │
        ▼
② 管控节点 backend 收到请求，写入数据库 (status=pending)
        │
        ▼
③ backend 将任务写入 Redis 调度队列 (status=queued)
   LPUSH suit:queue:normal {"task_id": "task-001"}
   PUBLISH suit:queue:new 通知调度器
        │
        ▼
④ scheduler 服务（独立容器）收到通知
   从 Redis 队列取出任务
   查询所有计算节点的 GPU 状态（从数据库读，agent 每10秒更新）
   选择 10.138.50.151 的 GPU-0（空闲）
   通过 Agent API 下发指令
   POST http://10.138.50.151:9000/api/run
   {
     "task_id": "task-001",
     "image": "pytorch/pytorch:2.0-cuda11.8",
     "gpus": [0],
     "command": "python train.py --epochs 10",
     "volumes": {"/data/tasks/task-001": "/workspace"}
   }
        │
        ▼
⑤ 计算节点 node-agent 执行：
   docker run --gpus '"device=0"' \
     -v /data/tasks/task-001:/workspace \
     pytorch/pytorch:2.0-cuda11.8 \
     python train.py --epochs 10
        │
        ▼
⑥ node-agent 回调管控节点
   POST http://10.138.50.58:8000/api/v1/tasks/task-001/callback
   { "status": "running", "container_id": "abc123" }
        │
        ▼
⑦ 用户在控制台看到任务状态变为 "运行中"（WebSocket 实时推送）
        │
        ▼
⑧ 任务完成 → agent 回调 { "status": "success" }
        │
        ▼
⑨ backend 更新状态，PUBLISH suit:task:finished
        │
        ▼
⑩ scheduler 收到通知，释放 GPU，调度下一个排队任务
        │
        ▼
⑪ 用户在控制台看到结果，下载日志/模型文件
```

---

## 5. 技术选型总览

| 层级 | 组件 | 选型 | 版本建议 |
|------|------|------|----------|
| 前端 | 框架 | Vue 3 + Vite | 3.4+ / 5.x |
| 前端 | UI库 | Element Plus | 2.x |
| 前端 | 图表 | ECharts | 5.x |
| 前端 | HTTP | Axios | 1.x |
| 后端 | 框架 | FastAPI | 0.111+ |
| 后端 | ORM | SQLAlchemy + Alembic | 2.0+ |
| 后端 | 异步任务 | Celery + Redis | 5.4+ / 7.x（监控/计费） |
| 后端 | 调度队列 | Redis List | 独立于 Celery，scheduler 消费 |
| 后端 | WebSocket | FastAPI WebSocket | - |
| 数据库 | 主库 | PostgreSQL | 16 |
| 数据库 | 缓存 | Redis | 7 |
| 容器 | 运行时 | Docker + NVIDIA Container Toolkit | - |
| 容器 | 编排 | Docker Compose | v2 |
| 监控 | 采集 | Prometheus | 2.x |
| 节点代理 | Agent | Python (FastAPI + Docker SDK) | 轻量 |
| 调度 | 引擎 | 自研 Python | - |

---

## 6. 数据库核心表设计

```sql
-- 计算节点表
nodes (
  id              VARCHAR(36) PRIMARY KEY,  -- UUID
  hostname        VARCHAR(128),
  ip              VARCHAR(45) NOT NULL UNIQUE,
  agent_port      INT DEFAULT 9000,
  gpu_count       INT DEFAULT 0,
  gpu_model       VARCHAR(64),
  total_memory_mb INT,
  status          VARCHAR(20) DEFAULT 'offline',  -- online/offline/maintenance
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
  utilization     INT DEFAULT 0,       -- 0-100
  temperature     INT DEFAULT 0,       -- 摄氏度
  power_usage     INT DEFAULT 0,       -- 瓦特
  status          VARCHAR(20) DEFAULT 'idle',  -- idle/allocated/error
  updated_at      TIMESTAMP DEFAULT NOW(),
  UNIQUE(node_id, gpu_index)
);

-- 用户表
users (
  id              VARCHAR(36) PRIMARY KEY,
  username        VARCHAR(64) UNIQUE NOT NULL,
  password_hash   VARCHAR(256) NOT NULL,
  role            VARCHAR(20) DEFAULT 'user',  -- admin/user
  gpu_quota       INT DEFAULT 2,               -- 最多同时占用GPU数
  api_key         VARCHAR(128) UNIQUE,
  credits         DECIMAL(12,2) DEFAULT 0,     -- 余额
  created_at      TIMESTAMP DEFAULT NOW()
);

-- 任务表
tasks (
  id                  VARCHAR(36) PRIMARY KEY,
  user_id             VARCHAR(36) REFERENCES users(id),
  name                VARCHAR(128),
  task_type           VARCHAR(20),             -- train/inference/custom
  status              VARCHAR(20) DEFAULT 'pending',  -- pending/queued/running/success/failed/cancelled
  priority            INT DEFAULT 0,
  assigned_node_id    VARCHAR(36) REFERENCES nodes(id),
  assigned_gpu_indices INT[],                  -- 分配的GPU索引列表
  container_image     VARCHAR(256),
  container_command   TEXT,
  container_id        VARCHAR(64),             -- Docker容器ID
  config_json         JSONB,                   -- 额外配置
  result_json         JSONB,                   -- 执行结果
  created_at          TIMESTAMP DEFAULT NOW(),
  started_at          TIMESTAMP,
  finished_at         TIMESTAMP,
  billed              BOOLEAN DEFAULT FALSE,   -- 是否已计费
);

-- 模型注册表（AI 能力供给核心）
models (
  id                VARCHAR(36) PRIMARY KEY,
  name              VARCHAR(128) UNIQUE NOT NULL,   -- 如 "qwen-7b", "llama3-8b"
  display_name      VARCHAR(128),                   -- 显示名称
  model_type        VARCHAR(32),                    -- llm / embedding / cv / tts
  framework         VARCHAR(32),                    -- vllm / transformers / onnx
  model_path        VARCHAR(512),                   -- 模型文件路径（本地/远程）
  container_image   VARCHAR(256),                   -- 推理镜像
  launch_command    TEXT,                            -- 启动命令
  config_json       JSONB,                          -- 模型配置（端口、参数等）
  status            VARCHAR(20) DEFAULT 'offline',  -- online/offline/deploying/error
  replicas          INT DEFAULT 1,                  -- 副本数
  gpu_requirement   VARCHAR(64),                    -- GPU 要求（如 "1x RTX3090"）
  api_format        VARCHAR(32) DEFAULT 'openai',   -- openai / custom
  description       TEXT,
  created_at        TIMESTAMP DEFAULT NOW(),
  updated_at        TIMESTAMP DEFAULT NOW()
);

-- 模型部署实例表（每个运行中的推理容器）
model_instances (
  id                VARCHAR(36) PRIMARY KEY,
  model_id          VARCHAR(36) REFERENCES models(id),
  node_id           VARCHAR(36) REFERENCES nodes(id),
  container_id      VARCHAR(64),
  assigned_gpu_indices INT[],
  port              INT,                            -- 推理服务端口
  status            VARCHAR(20) DEFAULT 'starting', -- starting/running/stopping/stopped/error
  api_endpoint      VARCHAR(256),                   -- 实际 API 地址
  started_at        TIMESTAMP DEFAULT NOW()
);

-- 任务日志表
task_logs (
  id         BIGSERIAL PRIMARY KEY,
  task_id    VARCHAR(36) REFERENCES tasks(id),
  source     VARCHAR(20),    -- stdout/stderr/agent/system
  message    TEXT,
  timestamp  TIMESTAMP DEFAULT NOW()
);

-- API 调用记录表
api_calls (
  id              BIGSERIAL PRIMARY KEY,
  user_id         VARCHAR(36) REFERENCES users(id),
  api_key         VARCHAR(128),
  model_name      VARCHAR(64),
  endpoint        VARCHAR(128),
  tokens_input    INT DEFAULT 0,
  tokens_output   INT DEFAULT 0,
  latency_ms      INT,
  status_code     INT,
  created_at      TIMESTAMP DEFAULT NOW()
);

-- 计费记录表
billing_records (
  id              BIGSERIAL PRIMARY KEY,
  user_id         VARCHAR(36) REFERENCES users(id),
  task_id         VARCHAR(36) REFERENCES tasks(id),
  resource_type   VARCHAR(20),    -- gpu_time/api_call
  gpu_model       VARCHAR(64),
  duration_seconds INT,
  cost_credits    DECIMAL(10,4),
  created_at      TIMESTAMP DEFAULT NOW()
);

-- GPU 指标时序表（监控采集用）
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

-- 常用索引
CREATE INDEX idx_gpu_metrics_node_time ON gpu_metrics(node_id, timestamp);
```

---

## 7. 关键决策说明

### 为什么不用 Kubernetes？

| 维度 | K8s | Docker + 自研 Agent |
|------|-----|---------------------|
| 部署复杂度 | 高（需 kubeadm/k3s + etcd + CNI） | 低（docker-compose up） |
| GPU 支持 | 需 gpu-operator + device-plugin | nvidia-docker 原生支持 |
| 新增节点 | kubeadm join + 配置 | agent 启动即注册 |
| 运维成本 | 高（升级、etcd备份、CNI排障） | 低 |
| 适合规模 | 10+ 节点 | 1~10 节点 |

**结论：** 校内初期 1~5 台服务器，Docker + 自研 Agent 完全够用。等节点超过 10 台再考虑引入 K8s。

### 调度策略（单机/少节点阶段）

1. **FIFO**：先进先出
2. **资源匹配**：任务要求的 GPU 型号/显存必须匹配
3. **优先级**：支持 high/normal/low 三级
4. **抢占**：暂不实现，后续扩展

### Agent 通信方式

- **心跳**：Agent → 管控节点，HTTP POST，每 10 秒
- **指令**：管控节点 → Agent，HTTP POST（简单可靠）
- **日志**：Agent → 管控节点，HTTP POST（容器 stdout/stderr）
- **实时推送**：管控节点 → 前端，WebSocket

---

## 8. 文档索引

| 文档 | 内容 |
|------|------|
| [phase1-architecture.md](phase1-architecture.md) | 本文：系统总体架构设计 |
| [phase2-backend.md](phase2-backend.md) | 后端 FastAPI 项目结构与模块拆分 |
| [phase3-scheduling.md](phase3-scheduling.md) | 算力调度与GPU分配设计 |
| [phase4-frontend.md](phase4-frontend.md) | 前端 Vue3 页面与接口设计 |
| [phase5-mvp.md](phase5-mvp.md) | 最小可运行版本部署方案 |
| [phase6-scaling.md](phase6-scaling.md) | 扩展路线（单机→多节点→K8s） |
