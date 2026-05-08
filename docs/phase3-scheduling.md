# 第三阶段：算力调度设计（GPU 调度核心）

> 项目名称：SUIT API — 校内AI算力调度平台
> 更新日期：2026-05-06
> 架构约定：独立 scheduler 服务 + Redis 调度队列 + Celery 不参与核心调度

---

## 1. 调度架构总览

```
用户提交任务
    │
    ▼
┌──────────────────────────┐
│ backend (FastAPI)         │
│                          │
│  task_service.submit()   │
│    → status: queued      │
│    → 写入 Redis 队列     │
│    → PUBLISH 通知        │
└──────────┬───────────────┘
           │ Redis
           ▼
┌──────────────────────────────────────────────────┐
│  scheduler 服务（独立 Docker 容器，持续运行）      │
│                                                  │
│  ┌────────────┐   ┌───────────────┐              │
│  │queue_mgr   │   │  scheduler    │              │
│  │(Redis List)│──→│  主循环        │              │
│  │            │   │  while True:  │              │
│  │ high队列   │   │   dequeue()   │              │
│  │ normal队列 │   │   allocate()  │              │
│  │ low队列    │   │   launch()    │              │
│  └────────────┘   └──────┬────────┘              │
│                          │                       │
│  ┌──────────────┐  ┌────▼──────────┐             │
│  │gpu_allocator │  │container_mgr  │             │
│  │              │  │               │             │
│  │ - 资源匹配   │  │ - 启动容器     │             │
│  │ - 型号校验   │  │ - 停止容器     │             │
│  │ - 负载均衡   │  │ - 状态查询     │             │
│  └──────────────┘  └────┬──────────┘             │
│                         │                        │
│  ┌──────────────┐  ┌────▼──────────┐             │
│  │  数据库      │  │ agent_client  │             │
│  │  (状态存储)  │  │ (HTTP通信)    │             │
│  └──────────────┘  └────┬──────────┘             │
│                         │                        │
└─────────────────────────┼────────────────────────┘
                          │
                          ▼
               ┌──────────────────┐
               │  计算节点 Agent   │
               │                  │
               │  - 执行容器       │
               │  - GPU 实时监控   │
               │  - 容器列表追踪   │
               │  - 心跳上报       │
               └──────────────────┘
```

### 调度服务 vs Celery 职责划分

```
scheduler 服务（独立容器）：
  ✅ 从 Redis 队列取任务
  ✅ GPU 分配决策
  ✅ 通过 Agent 启动/停止容器
  ✅ 任务完成时调度下一个
  ✅ 持续运行，主动轮询 + Pub/Sub

Celery worker（另一个容器）：
  ✅ GPU 指标定时采集
  ✅ 节点心跳超时检测
  ✅ 计费计算
  ❌ 不参与任务调度

Redis：
  DB0: 调度队列（suit:queue:high/normal/low）
  DB1: 调度结果缓存
  DB2: Celery broker
  DB3: Celery backend
  Pub/Sub: suit:task:finished 频道
```

---

## 2. Agent 资源感知

Agent 不只是"执行器"，必须是"资源感知器"。上报信息不完整会导致调度误判。

### 2.1 Agent 心跳数据结构

```json
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
```

### 2.2 为什么资源感知是致命问题

```
❌ Agent 不上报 GPU 进程信息 → 调度器不知道 GPU 是否真的空闲
   → 可能把任务分配到已满载的 GPU → 任务 OOM 失败

❌ Agent 不上报显存细节 → 调度器只知"已用"不知"可用"
   → 显存碎片化时误判为空闲 → 分配失败

✅ Agent 完整上报 → 调度器精确知道每张 GPU 的真实状态
   → 精确分配，避免 OOM
```

---

## 3. Redis 调度队列设计

### 3.1 队列结构

```
Redis DB0:
  suit:queue:high    — priority >= 10
  suit:queue:normal  — 0 <= priority < 10
  suit:queue:low     — priority < 0

入队（backend task_service.submit_task 执行）:
  LPUSH suit:queue:normal {"task_id": "xxx", "enqueued_at": 1714987200}

出队（scheduler 主循环执行）:
  先 RPOP suit:queue:high
  没有 → RPOP suit:queue:normal
  没有 → RPOP suit:queue:low

放回（资源不足时）:
  RPUSH suit:queue:normal {"task_id": "xxx", "enqueued_at": ...}

通知:
  PUBLISH suit:task:finished {"task_id": "xxx"}  — Agent 回调完成时
  PUBLISH suit:queue:new {"task_id": "xxx"}       — 新任务入队时
```

### 3.2 QueueManager 代码

```python
# scheduler/queue_manager.py

import json
import time
import redis

class QueueManager:
    QUEUES = {
        "high": "suit:queue:high",
        "normal": "suit:queue:normal",
        "low": "suit:queue:low",
    }

    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.pubsub = self.redis.pubsub()

    def enqueue(self, task_id: str, priority: int = 0):
        """任务入队"""
        queue = self._get_queue_name(priority)
        data = json.dumps({"task_id": task_id, "enqueued_at": time.time()})
        self.redis.lpush(queue, data)
        self.redis.publish("suit:queue:new", json.dumps({"task_id": task_id}))

    def dequeue(self) -> dict | None:
        """按优先级出队：high → normal → low"""
        for queue_key in self.QUEUES.values():
            result = self.redis.rpop(queue_key)
            if result:
                return json.loads(result)
        return None

    def requeue(self, task_data: dict):
        """放回 normal 队列（资源不足时）"""
        self.redis.rpush(self.QUEUES["normal"], json.dumps(task_data))

    def queue_length(self) -> dict:
        """各队列长度"""
        return {
            name: self.redis.llen(key)
            for name, key in self.QUEUES.items()
        }

    def total_pending(self) -> int:
        return sum(self.queue_length().values())

    def subscribe_task_finished(self):
        """订阅任务完成通知"""
        self.pubsub.subscribe("suit:task:finished")
        return self.pubsub

    def subscribe_new_task(self):
        """订阅新任务通知"""
        self.pubsub.subscribe("suit:queue:new")
        return self.pubsub

    def _get_queue_name(self, priority: int) -> str:
        if priority >= 10:
            return self.QUEUES["high"]
        elif priority >= 0:
            return self.QUEUES["normal"]
        else:
            return self.QUEUES["low"]
```

---

## 4. 调度引擎（独立服务）

### 4.1 调度主循环

```python
# scheduler/scheduler.py

import time
import logging
from scheduler.queue_manager import QueueManager
from scheduler.gpu_allocator import GpuAllocator
from scheduler.container_manager import ContainerManager

logger = logging.getLogger(__name__)

class Scheduler:
    """独立调度服务主循环"""

    def __init__(self, db_session, redis_url: str):
        self.db = db_session
        self.queue = QueueManager(redis_url)
        self.allocator = GpuAllocator(db_session)
        self.container_mgr = ContainerManager(db_session)

    def run(self):
        """持续运行的调度循环"""
        logger.info("调度服务启动")

        # 启动 Pub/Sub 监听线程（收到通知立即调度）
        self._start_pubsub_listener()

        # 主循环：轮询兜底
        while True:
            try:
                self._schedule_one()
            except Exception as e:
                logger.error(f"调度异常: {e}")
            time.sleep(1)

    def _schedule_one(self):
        """尝试调度一个任务"""
        # 1. 从队列取任务
        task_data = self.queue.dequeue()
        if not task_data:
            return

        task_id = task_data["task_id"]

        # 2. 查数据库确认任务状态
        task = self.db.get(Task, task_id)
        if not task or task.status != "queued":
            logger.warning(f"任务 {task_id} 状态异常，跳过")
            return

        # 3. 分配 GPU
        allocation = self.allocator.allocate(task)
        if not allocation:
            # 没有可用 GPU，放回队列
            self.queue.requeue(task_data)
            logger.info(f"任务 {task_id} 无可用 GPU，放回队列")
            return

        # 4. 通过 Agent 启动容器
        try:
            container_id = self.container_mgr.launch(task, allocation)
            # 5. 更新任务状态为 running
            task.status = "running"
            task.assigned_node_id = allocation.node_id
            task.assigned_gpu_indices = allocation.gpu_indices
            task.container_id = container_id
            task.started_at = func.now()
            self.db.commit()
            logger.info(f"任务 {task_id} 已启动，节点 {allocation.node_id}，GPU {allocation.gpu_indices}")
        except Exception as e:
            # 启动失败，释放 GPU，标记失败
            self.allocator.release(allocation)
            task.status = "failed"
            task.result_json = {"error": str(e)}
            self.db.commit()
            logger.error(f"任务 {task_id} 启动失败: {e}")

    def on_task_finished(self, task_id: str):
        """任务完成时调用（由 callback 触发）"""
        # 释放 GPU
        self.allocator.release_by_task(task_id)
        # 立即尝试调度下一个
        self._schedule_one()

    def _start_pubsub_listener(self):
        """监听 Redis Pub/Sub，收到通知立即调度"""
        import threading

        def listener():
            pubsub = self.queue.subscribe_task_finished()
            pubsub.subscribe("suit:queue:new")
            for message in pubsub.listen():
                if message["type"] == "message":
                    logger.info(f"收到通知: {message['channel']}，立即调度")
                    self._schedule_one()

        thread = threading.Thread(target=listener, daemon=True)
        thread.start()
```

### 4.2 调度服务入口

```python
# scheduler/main.py

from scheduler.scheduler import Scheduler
from scheduler.database import get_db_session
from scheduler.config import settings

def main():
    db = get_db_session(settings.DATABASE_URL)
    scheduler = Scheduler(db, settings.REDIS_URL)
    scheduler.run()

if __name__ == "__main__":
    main()
```

### 4.3 调度服务配置

```python
# scheduler/config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://suit:suit123@postgres:5432/suitdb"
    REDIS_URL: str = "redis://redis:6379/0"
    SCHEDULE_INTERVAL: int = 1  # 调度主循环空闲轮询间隔（秒）

settings = Settings()
```

---

## 5. GPU 分配器

```python
# scheduler/gpu_allocator.py

from dataclasses import dataclass
from scheduler.models import Node, GpuDevice, Task

@dataclass
class GpuAllocation:
    node_id: str
    node_ip: str
    gpu_indices: list[int]

class GpuAllocator:
    """GPU 分配策略"""

    def __init__(self, db_session):
        self.db = db_session

    def allocate(self, task: Task) -> GpuAllocation | None:
        """
        为任务分配 GPU

        策略（按顺序判断）：
        1. 资源匹配：GPU 型号/显存必须满足任务要求
        2. 负载均衡：选空闲 GPU 最多的节点
        3. 同节点优先：多张 GPU 尽量分配在同一节点
        """
        config = task.config_json or {}
        required_gpus = config.get("gpu_count", 1)
        required_model = config.get("gpu_model")       # 可选
        min_memory = config.get("min_memory_mb")        # 可选

        # 查询所有在线节点
        nodes = self.db.query(Node).filter(Node.status == "online").all()

        candidates = []

        for node in nodes:
            # 查询该节点空闲的 GPU
            query = self.db.query(GpuDevice).filter(
                GpuDevice.node_id == node.id,
                GpuDevice.status == "idle"
            )

            if required_model:
                query = query.filter(GpuDevice.gpu_model.contains(required_model))

            if min_memory:
                query = query.filter(GpuDevice.memory_total_mb >= min_memory)

            available_gpus = query.order_by(GpuDevice.gpu_index).all()

            if len(available_gpus) >= required_gpus:
                selected = available_gpus[:required_gpus]
                candidates.append({
                    "node_id": node.id,
                    "node_ip": node.ip,
                    "gpu_indices": [g.gpu_index for g in selected],
                    "free_gpu_count": len(available_gpus),
                    "avg_utilization": sum(g.utilization for g in selected) / len(selected),
                })

        if not candidates:
            return None

        # 排序：空闲GPU最多 → 平均利用率最低
        candidates.sort(key=lambda c: (-c["free_gpu_count"], c["avg_utilization"]))
        best = candidates[0]

        # 标记 GPU 为已分配
        for idx in best["gpu_indices"]:
            gpu = self.db.query(GpuDevice).filter(
                GpuDevice.node_id == best["node_id"],
                GpuDevice.gpu_index == idx
            ).first()
            if gpu:
                gpu.status = "allocated"

        self.db.commit()

        return GpuAllocation(
            node_id=best["node_id"],
            node_ip=best["node_ip"],
            gpu_indices=best["gpu_indices"]
        )

    def release(self, allocation: GpuAllocation):
        """释放 GPU"""
        for idx in allocation.gpu_indices:
            gpu = self.db.query(GpuDevice).filter(
                GpuDevice.node_id == allocation.node_id,
                GpuDevice.gpu_index == idx
            ).first()
            if gpu:
                gpu.status = "idle"
        self.db.commit()

    def release_by_task(self, task_id: str):
        """根据任务 ID 释放其占用的所有 GPU"""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task or not task.assigned_node_id:
            return

        for idx in task.assigned_gpu_indices or []:
            gpu = self.db.query(GpuDevice).filter(
                GpuDevice.node_id == task.assigned_node_id,
                GpuDevice.gpu_index == idx
            ).first()
            if gpu:
                gpu.status = "idle"

        self.db.commit()
```

---

## 6. 容器管理器

```python
# scheduler/container_manager.py

import httpx
from scheduler.models import Node, Task
from scheduler.gpu_allocator import GpuAllocation

class ContainerManager:
    """通过 Agent 在计算节点上管理容器"""

    def __init__(self, db_session):
        self.db = db_session

    def launch(self, task: Task, allocation: GpuAllocation) -> str:
        """启动任务容器，返回 container_id"""
        node = self.db.query(Node).filter(Node.id == allocation.node_id).first()
        client = AgentClient(node.ip, node.agent_port)

        volumes = {
            f"/data/tasks/{task.id}": "/workspace",
            "/data/models": "/models:ro",
        }

        result = client.launch_task(
            task_id=task.id,
            image=task.container_image,
            gpus=allocation.gpu_indices,
            command=task.container_command,
            volumes=volumes,
        )

        return result["container_id"]

    def stop(self, task: Task):
        """停止任务容器"""
        node = self.db.query(Node).filter(Node.id == task.assigned_node_id).first()
        client = AgentClient(node.ip, node.agent_port)
        client.stop_task(task.container_id)

    def get_logs(self, task: Task, tail: int = 100) -> str:
        """获取容器日志"""
        node = self.db.query(Node).filter(Node.id == task.assigned_node_id).first()
        client = AgentClient(node.ip, node.agent_port)
        return client.get_logs(task.container_id, tail=tail)


class AgentClient:
    """Agent HTTP 客户端"""

    def __init__(self, node_ip: str, agent_port: int = 9000):
        self.base_url = f"http://{node_ip}:{agent_port}"
        self.client = httpx.Client(timeout=30.0)

    def launch_task(self, task_id, image, gpus, command, volumes) -> dict:
        resp = self.client.post(f"{self.base_url}/api/run", json={
            "task_id": task_id,
            "image": image,
            "gpus": gpus,
            "command": command,
            "volumes": volumes,
        })
        resp.raise_for_status()
        return resp.json()

    def stop_task(self, container_id: str) -> dict:
        resp = self.client.post(f"{self.base_url}/api/stop", json={
            "container_id": container_id,
        })
        resp.raise_for_status()
        return resp.json()

    def get_logs(self, container_id: str, tail: int = 100) -> str:
        resp = self.client.get(f"{self.base_url}/api/logs/{container_id}",
                               params={"tail": tail})
        resp.raise_for_status()
        return resp.json()["logs"]

    def health_check(self) -> bool:
        try:
            resp = self.client.get(f"{self.base_url}/api/health")
            return resp.status_code == 200
        except Exception:
            return False
```

---

## 7. 任务状态机

```
                    ┌──────────┐
        ┌──────────→│ pending  │←─── 创建任务
        │           └────┬─────┘
        │                │ submit_task() → 写入 Redis 队列
        │                ▼
        │           ┌──────────┐
        │           │  queued  │←─── 在 Redis 队列中等待
        │           └────┬─────┘
        │                │ scheduler 分配 GPU 成功
        │                ▼
        │           ┌──────────┐
        │           │ running  │←─── Agent 已启动容器
        │           └──┬───┬───┘
        │              │   │
        │    ┌─────────┘   └──────────┐
        │    ▼                        ▼
        │ ┌──────────┐          ┌──────────┐
        │ │ success  │          │  failed  │
        │ └──────────┘          └──────────┘
        │
        │ cancel (pending/queued 时)
        ▼
    ┌──────────┐
    │ cancelled│
    └──────────┘
```

状态流转触发：

| 转换 | 触发方 | 操作 |
|------|--------|------|
| → pending | backend task_service | 创建任务写入数据库 |
| pending → queued | backend task_service | 写入 Redis 队列 |
| queued → running | scheduler | 分配 GPU + Agent 启动容器 |
| running → success | Agent callback | 释放 GPU + 通知调度 |
| running → failed | Agent callback | 释放 GPU + 通知调度 |
| pending/queued → cancelled | 用户取消 | 从 Redis 队列移除（如在队列中） |

---

## 8. 调度策略

### 8.1 单机调度

```
场景：10.138.50.151 有 2 张 RTX 3090

任务A提交 → 需要 1 张 GPU → 分配 GPU-0 → running
任务B提交 → 需要 1 张 GPU → 分配 GPU-1 → running
任务C提交 → 需要 1 张 GPU → 无空闲 GPU → queued（等待）
任务A完成 → GPU-0 释放 → scheduler 立即调度任务C → running
```

### 8.2 多节点调度

```
场景：
  10.138.50.151: 2x RTX 3090 (24GB)
  10.138.50.xxx: 4x A100 (80GB)

任务A: 需要 1x RTX 3090 → 匹配 151 节点 → 分配 GPU-0
任务B: 需要 2x A100    → 匹配 xxx 节点 → 分配 GPU-0,1
任务C: 不限型号        → 选空闲 GPU 最多的节点（负载均衡）
```

### 8.3 调度算法优先级

```
1. 资源匹配：GPU 型号/显存 必须满足任务要求
2. 优先级：high 队列 > normal 队列 > low 队列
3. 负载均衡：同等条件下，选空闲 GPU 最多的节点
4. 同节点优先：多张 GPU 尽量在同一节点（减少数据传输）
```

---

## 9. GPU 隔离

```
方式：Docker + NVIDIA Container Toolkit

任务A → docker run --gpus '"device=0"' → 只看到 GPU-0
任务B → docker run --gpus '"device=1"' → 只看到 GPU-1

隔离保证：
- 每个容器只能看到分配给它的 GPU
- 容器间 GPU 显存完全隔离
- 容器间 CUDA 计算互不干扰
```

---

## 10. 后续升级到 K8s

```
调度器已预留扩展接口：

scheduler/
├── scheduler.py          # 主循环（不变）
├── gpu_allocator.py      # GPU 分配（不变）
├── container_manager.py  # ← 替换这个文件即可
│   ├── DockerContainerManager  # 当前：通过 Agent 执行 Docker
│   └── K8sContainerManager     # 未来：通过 K8s API 创建 Pod
└── ...

切换方式：配置文件指定 container_manager 实现类
上层 scheduler.py 和 gpu_allocator.py 不用改
```

---

## 11. 完整调度流程示例

```
场景：用户提交一个 PyTorch 训练任务，需要 1 张 GPU

1. 用户 POST /api/v1/tasks
   → backend task_service.create_task()
   → 数据库写入，status = pending
   → 返回 task_id

2. 用户 POST /api/v1/tasks/{id}/submit
   → backend task_service.submit_task()
   → status 改为 queued
   → LPUSH suit:queue:normal {"task_id": "xxx"}
   → PUBLISH suit:queue:new {"task_id": "xxx"}

3. scheduler 收到 Pub/Sub 通知（或轮询到）
   → RPOP suit:queue:normal → 取出任务
   → 查数据库确认 status = queued
   → gpu_allocator.allocate(task)
     → 查询 10.138.50.151 的 GPU 状态
     → GPU-0: idle, GPU-1: idle → 选择 GPU-0
     → 标记 GPU-0 为 allocated
   → container_mgr.launch(task, allocation)
     → POST http://10.138.50.151:9000/api/run
       {
         "task_id": "xxx",
         "image": "pytorch/pytorch:2.0-cuda11.8",
         "gpus": [0],
         "command": "python train.py --epochs 50",
         "volumes": {"/data/tasks/xxx": "/workspace"}
       }
   → 更新数据库：status = running, container_id = "abc123"

4. Agent 在 10.138.50.151 执行
   docker run -d --gpus '"device=0"' \
     -v /data/tasks/xxx:/workspace \
     pytorch/pytorch:2.0-cuda11.8 \
     python train.py --epochs 50

5. Agent 回调
POST http://10.138.50.58:8000/api/v1/tasks/{id}/callback
   { "status": "running", "container_id": "abc123" }

6. 任务运行中... 用户在控制台看到实时状态

7. 训练完成，容器退出
   Agent 回调
   { "status": "success", "exit_code": 0 }

8. backend callback 处理
   → 更新 status = success, finished_at
   → PUBLISH suit:task:finished {"task_id": "xxx"}

9. scheduler 收到通知
   → on_task_finished(task_id)
   → gpu_allocator.release_by_task(task_id) → GPU-0 改回 idle
   → _schedule_one() → 检查队列是否有下一个任务
```
