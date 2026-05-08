<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useTasksStore } from '../../stores/tasks'
import TaskStatusBadge from '../../components/TaskStatusBadge.vue'

const route = useRoute()
const router = useRouter()
const tasksStore = useTasksStore()
const logContainerRef = ref<HTMLDivElement | null>(null)
let refreshTimer: number | null = null

const taskId = computed(() => String(route.params.id))
const task = computed(() => tasksStore.currentTask)
const logs = computed(() => tasksStore.logs)

const runtimeText = computed(() => {
  const seconds = Number(task.value?.runtime_seconds ?? 0)
  if (!seconds) {
    return '-'
  }

  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const remainSeconds = seconds % 60
  return `${hours}h ${minutes}m ${remainSeconds}s`
})

const loadData = async () => {
  await Promise.all([
    tasksStore.fetchTaskDetail(taskId.value),
    tasksStore.fetchLogs(taskId.value),
  ])
}

const scrollLogsToBottom = async () => {
  await nextTick()
  if (logContainerRef.value) {
    logContainerRef.value.scrollTop = logContainerRef.value.scrollHeight
  }
}

const handleCancel = async () => {
  await tasksStore.cancelTask(taskId.value)
  await loadData()
}

const handleDelete = async () => {
  await ElMessageBox.confirm('确认删除该任务记录吗？', '提示', {
    type: 'warning',
  })
  await tasksStore.deleteTask(taskId.value)
  await router.push('/tasks')
}

watch(logs, () => {
  scrollLogsToBottom()
})

onMounted(async () => {
  await loadData()
  await scrollLogsToBottom()
  refreshTimer = window.setInterval(loadData, 10000)
})

onUnmounted(() => {
  if (refreshTimer) {
    window.clearInterval(refreshTimer)
  }
})
</script>

<template>
  <div class="page-shell">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ task?.name || '任务详情' }}</h2>
        <p class="page-subtitle">查看任务状态、GPU 去向和实时日志。</p>
      </div>
      <div class="detail-actions">
        <el-button @click="router.push('/tasks')">返回列表</el-button>
        <el-button
          v-if="['queued', 'running'].includes(task?.status || '')"
          type="warning"
          @click="handleCancel"
        >
          {{ task?.status === 'running' ? '停止任务' : '取消任务' }}
        </el-button>
        <el-button
          v-if="['success', 'failed', 'cancelled'].includes(task?.status || '')"
          type="danger"
          @click="handleDelete"
        >
          删除任务
        </el-button>
      </div>
    </div>

    <div class="content-grid detail-grid">
      <section class="section-card glass-card">
        <h3 class="section-title">基本信息</h3>
        <div class="detail-grid__info">
          <div class="detail-grid__item">
            <span>任务状态</span>
            <TaskStatusBadge :status="task?.status" />
          </div>
          <div class="detail-grid__item">
            <span>任务类型</span>
            <strong>{{ task?.task_type || '-' }}</strong>
          </div>
          <div class="detail-grid__item">
            <span>创建时间</span>
            <strong>{{ task?.created_at || '-' }}</strong>
          </div>
          <div class="detail-grid__item">
            <span>运行时长</span>
            <strong>{{ runtimeText }}</strong>
          </div>
          <div class="detail-grid__item">
            <span>节点 IP</span>
            <strong>{{ task?.assigned_node_ip || task?.assigned_node_id || '-' }}</strong>
          </div>
          <div class="detail-grid__item">
            <span>GPU 索引</span>
            <strong>{{ (task?.assigned_gpu_indices || []).join(', ') || '-' }}</strong>
          </div>
          <div class="detail-grid__item detail-grid__item--full">
            <span>镜像</span>
            <strong>{{ task?.container_image || '-' }}</strong>
          </div>
          <div class="detail-grid__item detail-grid__item--full">
            <span>命令</span>
            <strong>{{ task?.container_command || '-' }}</strong>
          </div>
        </div>
      </section>

      <section class="section-card glass-card">
        <h3 class="section-title">实时日志</h3>
        <div ref="logContainerRef" class="terminal detail-terminal">
          <div
            v-for="(log, index) in logs"
            :key="log.id || index"
            class="terminal-line"
          >
            [{{ log.timestamp || '--:--:--' }}] {{ log.message }}
          </div>
          <div v-if="!logs.length" class="terminal-line">暂无日志输出</div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.detail-grid {
  grid-template-columns: minmax(360px, 0.95fr) minmax(0, 1.05fr);
}

.detail-actions {
  display: flex;
  gap: 12px;
}

.detail-grid__info {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.detail-grid__item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px;
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.9);
}

.detail-grid__item span {
  color: #64748b;
  font-size: 13px;
}

.detail-grid__item strong {
  font-size: 15px;
  line-height: 1.6;
  word-break: break-word;
}

.detail-grid__item--full {
  grid-column: 1 / -1;
}

.detail-terminal {
  max-height: 560px;
  overflow: auto;
}
</style>
