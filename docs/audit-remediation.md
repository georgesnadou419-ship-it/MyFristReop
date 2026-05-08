# 文档一致性整改记录

> 整改日期：2026-05-06
> 整改范围：`docs/`
> 处理结果：16 项问题已完成源文件修复与交叉校验

---

## 整改结果

1. 已清理后端目录结构中的过时调度任务描述，并将调度职责统一收敛到独立 `scheduler/` 服务。
2. 已统一 Agent 心跳示例结构，补齐 GPU、CPU、内存、磁盘与运行中容器信息。
3. 已在 `tasks` 表设计中补充计费状态字段。
4. 已补充 GPU 指标时序表及其索引定义。
5. 已明确 backend 与 scheduler 两处 Agent 客户端的职责边界，并区分 async / sync 用途。
6. 已补充任务状态实时推送的 WebSocket 端点与鉴权说明。
7. 已在 phase2 目录结构中补齐模型相关 `model.py` 占位文件说明。
8. 已修正 phase1 章节编号重复问题。
9. 已将调度器测试位置统一到 `scheduler/tests/`。
10. 已补全 MVP 文档中的 `scheduler/` 文件清单。
11. 已明确 `monitor_service` 负责历史查询，采集逻辑归属 Celery 任务。
12. 已移除非调度文档中的调度轮询配置描述，统一由 `scheduler` 配置管理。
13. 已在 phase1 明确 Redis DB 分配与 Pub/Sub 用途。
14. 已移除过时的 Agent Compose 部署描述。
15. 已移除 phase6 中的工期表述。
16. 已修正技术选型表中异步任务与调度队列的职责划分。

---

## 一致性说明

- 调度架构以 `phase3-scheduling.md` 为准。
- 实施落地细节以 `implementation-roadmap.md` 为准。
- 文档中的相同概念已按上述基准统一描述。

✅ 全部 16 个问题已修复，验证通过
