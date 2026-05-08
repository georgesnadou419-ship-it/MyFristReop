# 第六阶段：扩展路线

> 项目名称：SUIT API — 校内AI算力调度平台
> 更新日期：2026-05-06

---

## 1. 扩展路线总览

```
Phase 1: 单机验证 (当前)
└─ 10.138.50.58 (管控) + 10.138.50.151 (计算)
  └─ Docker Compose + 自研调度
  └─ 目标：跑通 MVP

Phase 2: 多节点扩展 (2~5 台)
  └─ 管控节点 1 台 + 计算节点 3~5 台
  └─ Agent 自动注册 + 分布式调度
  └─ 目标：多用户并发使用

Phase 3: 平台化运营 (5~15 台)
  └─ 引入 K8s 管理计算节点
  └─ 完善监控告警 + 计费系统
  └─ 目标：对标火山引擎 AI 平台基础版

Phase 4: 大规模集群 (15+ 台)
  └─ 多集群管理 + 弹性伸缩
  └─ 模型市场 + 自动化部署
  └─ 目标：完整 AI 能力供给平台
```

---

## 2. Phase 2: 多节点扩展

### 2.1 新增计算节点流程

```
当前状态：
管控: 10.138.50.58
  计算: 10.138.50.151 (2x RTX 3090)

新增一台服务器 10.138.50.xxx：

1. 服务器基础配置
   - 安装 Ubuntu 22.04
   - 安装 NVIDIA 驱动
   - 安装 Docker + NVIDIA Container Toolkit
- 确保能访问 10.138.50.58:8000

2. 部署 Agent
   docker run -d \
     --name node-agent \
     --gpus all \
     -v /var/run/docker.sock:/var/run/docker.sock \
-e CONTROL_PLANE=http://10.138.50.58:8000 \
     -e NODE_NAME=node-xxx \
     -e NODE_IP=10.138.50.xxx \
     suit-agent

3. 验证
- 打开 http://10.138.50.58 → 资源管理 → 看到新节点
   - 新节点 GPU 状态正常显示
   - 提交任务可调度到新节点

```

### 2.2 调度器升级

```
单节点 → 多节点，调度器需要增加：

1. 节点选择策略
   - 当前：只有一个节点，直接分配
   - 升级：多节点负载均衡（选GPU利用率最低的）

2. 跨节点数据传输
   - 任务数据需要提前同步到目标节点
   - 方案：共享存储（NFS）或 任务提交时上传

3. 节点健康检查
   - Agent 心跳超时 → 自动标记为 offline
   - offline 节点上的运行中任务 → 标记为 failed + 触发重调度

4. GPU 型号匹配
   - 不同节点可能有不同型号 GPU
   - 任务可指定 GPU 型号要求
```

### 2.3 共享存储方案

```
多节点之间需要共享数据（模型文件、训练数据）：

方案A: NFS 共享（推荐初期）
  └─ 在管控节点上搭建 NFS Server
  └─ 所有计算节点挂载 /data 共享目录
  └─ 优点：简单，任务数据天然共享
  └─ 缺点：IO 性能受限于网络

方案B: 分布式存储（MinIO / Ceph）
  └─ 对象存储，按需拉取
  └─ 优点：可扩展，高可用
  └─ 缺点：复杂度高

推荐初期用 NFS，后期迁移到 MinIO。
```

---

## 3. Phase 3: 引入 Kubernetes

### 3.1 什么时候引入 K8s？

```
触发条件（满足任一即可）：
□ 计算节点 > 5 台
□ 需要自动扩缩容（推理服务按需启停）
□ 需要复杂的调度策略（亲和性、污点容忍、资源配额）
□ 需要滚动更新（不停机升级模型服务）
□ 团队有人熟悉 K8s 运维
```

### 3.2 K8s 架构设计

```
┌─────────────────────────────────────────────────────────────────────┐
│                        K8s 集群                                     │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Master Node (可复用 10.138.50.58)                           │   │
│  │  - kube-apiserver                                           │   │
│  │  - etcd                                                     │   │
│  │  - kube-scheduler                                           │   │
│  │  - kube-controller-manager                                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │ Worker Node 1    │  │ Worker Node 2    │  │ Worker Node 3    │  │
│  │ 10.138.50.151    │  │ 10.138.50.xxx    │  │ 10.138.50.yyy    │  │
│  │                  │  │                  │  │                  │  │
│  │ kubelet          │  │ kubelet          │  │ kubelet          │  │
│  │ nvidia-device-   │  │ nvidia-device-   │  │ nvidia-device-   │  │
│  │   plugin         │  │   plugin         │  │   plugin         │  │
│  │                  │  │                  │  │                  │  │
│  │ GPU Pods:        │  │ GPU Pods:        │  │ GPU Pods:        │  │
│  │ - task-001       │  │ - task-003       │  │ - inference-001  │  │
│  │ - task-002       │  │                  │  │ - inference-002  │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  平台服务 (Namespace: suit-system)                           │   │
│  │  - backend (Deployment)                                     │   │
│  │  - frontend (Deployment)                                    │   │
│  │  - postgres (StatefulSet)                                   │   │
│  │  - redis (StatefulSet)                                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.3 K8s 下的任务执行方式变化

```
当前（Docker + Agent）：
  调度器 → Agent HTTP → docker run --gpus ...

K8s 下：
  调度器 → K8s API → kubectl apply (Pod yaml with GPU request)

  Pod yaml 示例：
  apiVersion: v1
  kind: Pod
  metadata:
    name: task-001
  spec:
    containers:
    - name: worker
      image: pytorch/pytorch:2.0-cuda11.8
      command: ["python", "train.py"]
      resources:
        limits:
          nvidia.com/gpu: 1    # 请求 1 张 GPU
      volumeMounts:
      - name: task-data
        mountPath: /workspace
    nodeSelector:
      gpu-model: rtx-3090      # 选择特定 GPU 型号的节点
```

### 3.4 调度器抽象层

```python
# 为未来 K8s 迁移预留接口

from abc import ABC, abstractmethod

class SchedulerBackend(ABC):
    """调度后端抽象接口"""

    @abstractmethod
    def launch_task(self, task, allocation) -> str:
        """启动任务，返回容器/Pod ID"""
        ...

    @abstractmethod
    def stop_task(self, container_id: str):
        """停止任务"""
        ...

    @abstractmethod
    def get_task_status(self, container_id: str) -> str:
        """获取任务状态"""
        ...

    @abstractmethod
    def get_task_logs(self, container_id: str, tail: int) -> str:
        """获取任务日志"""
        ...


class DockerSchedulerBackend(SchedulerBackend):
    """当前：Docker + Agent 调度"""
    ...


class K8sSchedulerBackend(SchedulerBackend):
    """未来：K8s 调度"""
    ...


# 配置切换
def get_scheduler_backend() -> SchedulerBackend:
    if settings.SCHEDULER_BACKEND == "k8s":
        return K8sSchedulerBackend()
    return DockerSchedulerBackend()
```

---

## 4. Phase 4: 完整 AI 能力供给平台

### 4.1 对标火山引擎的功能清单

| 功能 | 火山引擎 | 当前MVP | Phase 2 | Phase 3 | Phase 4 |
|------|---------|---------|---------|---------|---------|
| GPU资源管理 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 任务提交 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 任务调度 | ✅ | FIFO | 负载均衡 | K8s调度 | 智能调度 |
| 推理API | ✅ | - | - | ✅ | ✅ |
| 模型部署 | ✅ | - | - | ✅ | ✅ |
| 监控告警 | ✅ | 基础 | ✅ | ✅ | ✅ |
| 计费系统 | ✅ | - | 基础 | ✅ | ✅ |
| 模型市场 | ✅ | - | - | - | ✅ |
| 自动扩缩容 | ✅ | - | - | K8s HPA | ✅ |
| 多租户 | ✅ | - | - | ✅ | ✅ |
| API网关 | ✅ | - | - | ✅ | ✅ |

### 4.2 推理服务长期运行

```
训练任务 vs 推理服务的区别：

训练任务：
  - 一次性运行，完成后退出
  - 占用 GPU 时间段明确
  - 按时长计费

推理服务：
  - 长期运行，持续提供 API
  - 需要负载均衡（多副本）
  - 按调用次数/Token 计费
  - 需要自动扩缩容

推理服务部署方式：
  1. 用 vLLM / TGI 作为推理引擎
  2. 以 Docker 容器长期运行
  3. 管控节点做 API 网关，路由到推理容器
  4. 支持多副本 + 负载均衡
```

### 4.3 模型市场

```
Phase 4 实现：

模型仓库：
  - 存储预训练模型文件
  - 支持版本管理
  - 一键部署为推理服务

用户操作：
  1. 浏览模型市场（Qwen、ChatGLM、Llama 等）
  2. 选择模型 → 选择 GPU → 一键部署
  3. 自动生成 API Endpoint
  4. 通过 API Key 调用
```

---

## 5. 从当前到火山引擎的演进路径

```
            当前                              目标
             │                                 │
             ▼                                 ▼
    ┌─────────────────┐              ┌─────────────────┐
    │  单机 + Docker  │              │  大规模 AI 平台  │
    │  Compose        │              │                  │
    └────────┬────────┘              └─────────────────┘
             │
             ▼
    ┌─────────────────┐
    │  多节点 + Agent │  ← 新增节点只需部署 Agent
    │  自研调度       │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  K8s + GPU      │  ← 标准化容器编排
    │  Operator       │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  完整平台       │  ← 推理服务 + 模型市场 + 计费
    │  (对标火山引擎)  │
    └─────────────────┘
```

---

## 6. 各阶段技术栈变化

| 组件 | Phase 1 (当前) | Phase 2 | Phase 3 | Phase 4 |
|------|---------------|---------|---------|---------|
| 容器编排 | Docker Compose | Docker Compose | K8s | K8s |
| 调度器 | 自研 Python | 自研 Python | K8s Scheduler | K8s + 自研插件 |
| 节点管理 | Agent 心跳 | Agent 心跳 | K8s Node | K8s Node |
| GPU 管理 | nvidia-smi | nvidia-smi | nvidia-device-plugin | gpu-operator |
| 存储 | 本地目录 | NFS | K8s PV/PVC | 分布式存储 |
| 监控 | Prometheus | Prometheus | Prometheus + Grafana | Prometheus + Grafana + 自研 |
| 推理引擎 | - | - | vLLM / TGI | vLLM / TTI |
| API 网关 | Nginx | Nginx | K8s Ingress | APISIX / Kong |

---

## 7. 总结

```
核心原则：
1. 先跑通，再优化
2. 先单机，再分布式
3. 先 Docker，再 K8s
4. 先核心功能，再平台化

当前最重要的事：
→ 在 10.138.50.58 + 10.138.50.151 上跑通 MVP
→ 验证"提交任务 → 调度 → 执行 → 返回结果"全流程
→ 确认 GPU 调度隔离正确

不要过早引入 K8s。
单机 Docker + 自研调度器可以支撑到 5 台节点。
```
