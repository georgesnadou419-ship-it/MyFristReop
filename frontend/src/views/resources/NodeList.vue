<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useNodesStore } from '../../stores/nodes'
import GpuStatusCard from '../../components/GpuStatusCard.vue'

const nodesStore = useNodesStore()
let refreshTimer: number | null = null

const nodes = computed(() => nodesStore.nodes)

const loadData = () => nodesStore.refresh()

const getCpuUsage = (cpuUsage?: number, cpuPercent?: number) =>
  Math.round(Number(cpuUsage ?? cpuPercent ?? 0))

const getMemoryUsage = (memoryUsage?: number, memoryPercent?: number) =>
  Math.round(Number(memoryUsage ?? memoryPercent ?? 0))

onMounted(async () => {
  await loadData()
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
        <h2 class="page-title">资源管理</h2>
        <p class="page-subtitle">节点和 GPU 状态每 10 秒自动刷新一次。</p>
      </div>
      <el-button @click="loadData">刷新节点</el-button>
    </div>

    <div class="node-list">
      <article
        v-for="node in nodes"
        :key="node.id"
        class="node-card glass-card"
      >
        <div class="node-card__header">
          <div>
            <h3>{{ node.hostname || node.ip }}</h3>
            <p>{{ node.ip }}</p>
          </div>
          <div class="node-card__meta">
            <span class="status-text">
              <span class="status-dot" :class="node.status || 'offline'" />
              {{ node.status || 'offline' }}
            </span>
            <el-tag round>{{ node.gpu_count ?? node.gpus?.length ?? 0 }} GPU</el-tag>
          </div>
        </div>

        <div class="node-card__metrics">
          <div class="node-card__metric">
            <span>CPU 使用率</span>
            <strong>{{ getCpuUsage(node.cpu_usage, node.cpu_percent) }}%</strong>
          </div>
          <el-progress
            :percentage="getCpuUsage(node.cpu_usage, node.cpu_percent)"
            :show-text="false"
          />
          <div class="node-card__metric">
            <span>内存使用率</span>
            <strong>{{ getMemoryUsage(node.memory_usage, node.memory_percent) }}%</strong>
          </div>
          <el-progress
            :percentage="getMemoryUsage(node.memory_usage, node.memory_percent)"
            :show-text="false"
            status="success"
          />
        </div>

        <div class="node-card__gpus">
          <GpuStatusCard
            v-for="gpu in node.gpus || []"
            :key="`${node.id}-${gpu.gpu_index}`"
            :gpu="gpu"
            :node-status="node.status"
          />
          <el-empty
            v-if="!(node.gpus || []).length"
            description="该节点暂未上报 GPU 明细"
          />
        </div>
      </article>
    </div>
  </div>
</template>

<style scoped>
.node-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.node-card {
  border-radius: 24px;
  padding: 22px;
}

.node-card__header,
.node-card__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.node-card__header h3 {
  margin: 0;
  font-size: 24px;
}

.node-card__header p {
  margin: 6px 0 0;
  color: #64748b;
}

.node-card__meta {
  min-width: 180px;
}

.node-card__metrics {
  margin-top: 20px;
  display: grid;
  gap: 10px;
}

.node-card__metric {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.node-card__gpus {
  margin-top: 22px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}
</style>
