<script setup lang="ts">
import * as echarts from 'echarts'
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useNodesStore } from '../stores/nodes'
import { useTasksStore } from '../stores/tasks'
import TaskStatusBadge from '../components/TaskStatusBadge.vue'

const router = useRouter()
const nodesStore = useNodesStore()
const tasksStore = useTasksStore()
const chartRef = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null
let refreshTimer: number | null = null

const busyGpus = computed(() =>
  Math.max(nodesStore.totalGpus - nodesStore.idleGpus, 0),
)

const summaryCards = computed(() => [
  { label: '在线节点数', value: nodesStore.onlineCount },
  { label: 'GPU 总数', value: nodesStore.totalGpus },
  { label: '空闲 GPU', value: nodesStore.idleGpus },
  { label: '运行中任务', value: tasksStore.runningCount },
])

const loadData = async () => {
  await Promise.all([
    nodesStore.refresh(),
    tasksStore.fetchRecentTasks(),
    tasksStore.refreshRunningCount(),
  ])
}

const renderChart = async () => {
  await nextTick()
  if (!chartRef.value) {
    return
  }

  if (!chart) {
    chart = echarts.init(chartRef.value)
  }

  chart.setOption({
    color: ['#0f766e', '#2563eb', '#94a3b8'],
    tooltip: { trigger: 'item' },
    series: [
      {
        type: 'pie',
        radius: ['58%', '76%'],
        label: {
          color: '#334155',
          formatter: '{b}\n{c}',
        },
        data: [
          { name: '空闲 GPU', value: nodesStore.idleGpus },
          { name: '占用 GPU', value: busyGpus.value },
          {
            name: '离线节点',
            value: nodesStore.nodes.filter((node) => node.status === 'offline').length,
          },
        ],
      },
    ],
  })
}

watch(
  () => [nodesStore.totalGpus, nodesStore.idleGpus, nodesStore.nodes.length],
  () => {
    renderChart()
  },
)

onMounted(async () => {
  await loadData()
  await renderChart()
  refreshTimer = window.setInterval(loadData, 10000)
  window.addEventListener('resize', renderChart)
})

onUnmounted(() => {
  if (refreshTimer) {
    window.clearInterval(refreshTimer)
  }
  window.removeEventListener('resize', renderChart)
  chart?.dispose()
  chart = null
})
</script>

<template>
  <div class="page-shell">
    <div class="page-header">
      <div>
        <h2 class="page-title">Dashboard</h2>
        <p class="page-subtitle">
          汇总节点在线率、GPU 空闲情况和最近 10 条任务动态。
        </p>
      </div>
      <el-button @click="loadData">立即刷新</el-button>
    </div>

    <div class="stats-grid">
      <article
        v-for="card in summaryCards"
        :key="card.label"
        class="stats-card glass-card"
      >
        <div class="stats-label">{{ card.label }}</div>
        <div class="stats-value">{{ card.value }}</div>
      </article>
    </div>

    <div class="content-grid">
      <section class="section-card glass-card">
        <h3 class="section-title">最近任务</h3>
        <el-table :data="tasksStore.recentTasks" stripe>
          <el-table-column prop="name" label="任务名称" min-width="180" />
          <el-table-column prop="task_type" label="类型" width="120" />
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <TaskStatusBadge :status="row.status" />
            </template>
          </el-table-column>
          <el-table-column label="GPU" min-width="140">
            <template #default="{ row }">
              {{ (row.assigned_gpu_indices || []).join(', ') || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" min-width="180" />
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="router.push(`/tasks/${row.id}`)">
                详情
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <section class="section-card glass-card">
        <h3 class="section-title">GPU 分布</h3>
        <div ref="chartRef" class="dashboard-chart" />
      </section>
    </div>
  </div>
</template>

<style scoped>
.dashboard-chart {
  width: 100%;
  height: 360px;
}
</style>
