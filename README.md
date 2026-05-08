# SUIT API — 校内 AI 算力调度平台

## 我做了什么

我开发了一套面向校园场景的 AI 算力调度与能力供给平台，重点解决"GPU 资源分散、任务排队靠人工、模型部署门槛高、算力使用无法量化"的问题。以往校内做深度学习训练或 AI 推理时，师生往往需要自己登录服务器手动跑命令、抢占 GPU、盯着终端等结果，一旦多人共用同一台机器，就只能排队或互相踢进程。更关键的是，很多实验室根本没有统一的模型服务能力——想调用一个大模型推理接口，要么自己搭 vLLM，要么直接在 Jupyter 里跑，既没有 API 鉴权，也没有用量统计，更谈不上给第三方系统提供标准化的 OpenAI 兼容接口。

我将整个平台拆成"管控调度层 + 计算执行层 + AI 能力层 + 前端交互层"四段架构。管控调度层负责全局任务编排、GPU 资源分配和节点健康监控；计算执行层通过轻量 Agent 自动上报 GPU 状态并接收容器化任务指令；AI 能力层对外暴露统一的 OpenAI 兼容推理网关，支持模型部署、版本管理和负载均衡；前端交互层提供任务提交、实时监控、模型管理和计费概览等完整控制台。

## 系统架构

```
外部调用者（浏览器 / 第三方应用 / 业务系统）
        │
        ▼
┌──────────────────────────────────────────────────────────────┐
│  管控节点 10.138.50.60                                        │
│                                                              │
│  nginx → frontend(Vue3) + backend(FastAPI) + scheduler       │
│  celery-worker(监控/计费) + celery-beat(定时任务)              │
│  PostgreSQL + Redis(调度队列/缓存/消息) + Prometheus          │
│                                                              │
│            │ HTTP API                                        │
│            ▼                                                  │
│  计算节点 10.138.50.151                                       │
│  node-agent(资源感知) → GPU 任务容器(训练/推理)                │
└──────────────────────────────────────────────────────────────┘
```

**核心原则：管控节点管全局，计算节点只管执行。** 新增计算节点只需安装 Docker + 启动 Agent 即可自动接入。

## 技术栈

| 层级 | 选型 |
|------|------|
| 前端 | Vue 3 + Vite + Element Plus + Pinia + ECharts |
| 后端 | FastAPI + SQLAlchemy 2.0 + Pydantic |
| 数据库 | PostgreSQL 16 |
| 缓存/队列 | Redis 7（调度队列 + 缓存 + Pub/Sub 通知） |
| 异步任务 | Celery（仅监控采集与计费，不参与调度） |
| 调度引擎 | 自研独立 Scheduler 服务（Redis List 队列 + GPU 感知分配） |
| 容器运行时 | Docker + NVIDIA Container Toolkit |
| 部署 | Docker Compose |
| 节点代理 | Python Agent（FastAPI + Docker SDK，资源感知上报） |
| 推理网关 | OpenAI 兼容接口（/v1/chat/completions, /v1/embeddings） |

## 核心功能

### 任务调度

用户提交训练或推理任务后，系统自动完成从排队到执行的全流程：后端校验写入数据库，任务进入 Redis 优先级队列（high/normal/low）；独立 Scheduler 服务监听队列，根据 GPU 显存、利用率等指标选择最优节点和 GPU；通过 Agent 下发容器化指令，任务在隔离容器中执行；执行过程中 Agent 实时回调状态，前端通过 WebSocket 推送任务进度。任务完成后自动释放 GPU 资源，调度下一个排队任务。

### AI 能力供给

平台对外暴露 OpenAI 兼容的标准 API，第三方系统可直接调用。支持通过 vLLM 等框架一键部署大语言模型到指定 GPU 节点，自动管理模型实例的生命周期（部署、上线、下线、扩缩容）。推理网关内置轮询负载均衡，当同一模型部署多个副本时自动分发请求。每次 API 调用记录 token 用量和延迟，为计费提供数据支撑。

### 节点管理与监控

每个计算节点运行轻量 Agent，每 10 秒上报心跳，包含 GPU 设备详情（型号、显存、温度、功耗、利用率、运行中的进程）、CPU/内存/磁盘使用率、以及当前运行的容器列表。管控节点实时聚合所有节点状态，前端 Dashboard 展示集群资源全景。GPU 指标写入时序表，支持历史趋势查询。

### 计费与配额

按 GPU 使用时长和 API 调用次数两种维度计费。每个用户有独立的信用额度（credits），任务执行和 API 调用自动扣费。计费记录明细可查，支持管理员调整用户配额。

## 数据库设计

系统包含 10 张核心表：

- **users** — 用户与 API Key 管理，角色区分 admin/user
- **nodes** — 计算节点注册与状态
- **gpu_devices** — GPU 设备实时状态（显存、温度、利用率）
- **tasks** — 任务全生命周期（pending → queued → running → success/failed/cancelled）
- **task_logs** — 任务执行日志（stdout/stderr）
- **models** — 模型注册表（名称、框架、镜像、GPU 需求）
- **model_instances** — 模型部署实例（节点、端口、状态）
- **api_calls** — API 调用记录（token 用量、延迟）
- **billing_records** — 计费明细
- **gpu_metrics** — GPU 指标时序数据

## 项目结构

```
SUIT_API/
├── backend/                    # FastAPI 后端服务
│   ├── app/
│   │   ├── main.py             # 应用入口
│   │   ├── config.py           # 配置管理
│   │   ├── database.py         # 数据库连接
│   │   ├── dependencies.py     # 公共依赖注入
│   │   ├── models/             # SQLAlchemy 数据模型
│   │   ├── schemas/            # Pydantic 请求/响应模型
│   │   ├── routers/            # API 路由（auth, tasks, nodes, models, ai_gateway, billing, monitor）
│   │   ├── services/           # 业务逻辑层
│   │   ├── tasks/              # Celery 异步任务（监控采集、计费）
│   │   └── utils/              # 工具函数（安全、响应格式化）
│   ├── migrations/             # Alembic 数据库迁移
│   ├── alembic.ini
│   ├── Dockerfile
│   └── requirements.txt
├── scheduler/                  # 独立调度服务（Docker 容器）
│   ├── scheduler.py            # 调度主循环
│   ├── queue_manager.py        # Redis 队列管理
│   ├── gpu_allocator.py        # GPU 资源匹配与分配
│   ├── container_manager.py    # 容器生命周期管理
│   ├── agent_client.py         # Agent HTTP 通信
│   └── config.py
├── agent/                      # 计算节点 Agent
│   ├── agent.py                # Agent 主服务（FastAPI）
│   ├── heartbeat.py            # 心跳上报
│   ├── gpu_monitor.py          # GPU 信息采集（nvidia-smi）
│   ├── resource_collector.py   # CPU/内存/磁盘采集
│   └── Dockerfile
├── frontend/                   # Vue3 前端
│   ├── src/
│   │   ├── views/              # 页面（Dashboard, TaskList, NodeList, ModelManage...）
│   │   ├── components/         # 组件
│   │   ├── api/                # Axios API 封装
│   │   ├── stores/             # Pinia 状态管理
│   │   └── router/             # Vue Router
│   ├── Dockerfile
│   └── vite.config.ts
├── deploy/                     # 部署配置
│   ├── docker-compose.yml      # 完整服务编排
│   ├── nginx.conf              # Nginx 反向代理
│   └── .env                    # 环境变量
└── docs/                       # 设计文档
    ├── phase1-architecture.md  # 系统总体架构
    ├── phase2-backend.md       # 后端模块设计
    ├── phase3-scheduling.md    # 调度与 GPU 分配
    ├── phase4-frontend.md      # 前端页面设计
    ├── phase5-mvp.md           # MVP 部署方案
    ├── phase6-scaling.md       # 扩展路线
    ├── implementation-roadmap.md  # 编码阶段规划
    ├── audit-remediation.md    # 文档一致性整改记录
    └── code-remediation.md     # 代码审计整改记录
```

## 快速启动

### 管控节点部署

```bash
# 1. 克隆项目
git clone <repo-url> && cd SUIT_API

# 2. 配置环境变量
cd deploy
cp .env.example .env
# 编辑 .env，设置 JWT_SECRET、数据库密码等

# 3. 启动所有服务
docker compose up -d --build

# 4. 执行数据库迁移
docker compose exec backend alembic upgrade head

# 5. 验证服务
curl http://localhost:8000/docs  # API 文档
# 浏览器访问 http://localhost    # 前端控制台
```

### 计算节点部署

```bash
# 1. 安装 Docker + NVIDIA Container Toolkit（确保 nvidia-smi 正常）

# 2. 启动 Agent
docker run -d --name node-agent \
  --network host \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e CONTROL_PLANE=http://10.138.50.60:8000 \
  -e NODE_NAME=gpu-node-1 \
  -e NODE_IP=10.138.50.151 \
  suit-agent:latest

# 3. 验证
# 管控节点日志中应出现 agent 心跳上报
```

## API 概览

| 模块 | 路径前缀 | 说明 |
|------|----------|------|
| 认证 | /api/v1/auth | 注册、登录、API Key 管理 |
| 任务 | /api/v1/tasks | 创建、查询、取消任务 |
| 节点 | /api/v1/nodes | 节点列表、心跳接收 |
| 模型 | /api/v1/models | 模型注册、部署、上下线 |
| 资源 | /api/v1/resources | GPU 资源查询 |
| 监控 | /api/v1/monitor | 节点概览、GPU 指标 |
| 计费 | /api/v1/billing | 用量统计、账单查询 |
| AI 网关 | /v1/ | OpenAI 兼容推理接口 |

## 文档索引

| 文档 | 内容 |
|------|------|
| [phase1-architecture.md](docs/phase1-architecture.md) | 系统总体架构设计 |
| [phase2-backend.md](docs/phase2-backend.md) | 后端 FastAPI 项目结构与模块拆分 |
| [phase3-scheduling.md](docs/phase3-scheduling.md) | 算力调度与 GPU 分配设计 |
| [phase4-frontend.md](docs/phase4-frontend.md) | 前端 Vue3 页面与接口设计 |
| [phase5-mvp.md](docs/phase5-mvp.md) | 最小可运行版本部署方案 |
| [phase6-scaling.md](docs/phase6-scaling.md) | 扩展路线（单机 → 多节点 → K8s） |
| [implementation-roadmap.md](docs/implementation-roadmap.md) | 编码阶段规划与自包含提示词 |
| [code-remediation.md](docs/code-remediation.md) | 代码审计整改记录（42 项问题） |

## 设计决策

**为什么不用 Kubernetes？** 校内初期 1~5 台服务器，Docker + 自研 Agent 完全够用。新增节点只需启动 Agent 容器，零配置自动接入。等节点超过 10 台再考虑引入 K8s，平台已预留 SchedulerBackend 抽象接口，迁移时只需实现新的后端即可。

**为什么调度器独立于 Celery？** Celery 适合异步任务（监控采集、计费计算），但调度需要实时响应（毫秒级取队列、分配 GPU、下发指令）。独立 Scheduler 服务直接消费 Redis List，无 Celery 的序列化开销和 worker 调度延迟，保证任务从排队到执行的链路最短。

**为什么用 Redis List 而不是数据库轮询？** 数据库轮询有固定延迟（通常 1~5 秒），且高频轮询会增加数据库负载。Redis List 的 BLPOP 是零延迟阻塞等待，任务入队后调度器立即收到通知，配合 Pub/Sub 实现亚秒级调度响应。
