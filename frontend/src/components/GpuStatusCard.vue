<script setup lang="ts">
import { computed } from 'vue'
import type { GpuInfo } from '../types'

const props = defineProps<{
  gpu: GpuInfo
  nodeStatus?: string
}>()

const utilization = computed(() =>
  Number(props.gpu.utilization_gpu ?? props.gpu.utilization ?? 0),
)
const memoryTotal = computed(() => Number(props.gpu.memory_total_mb ?? 0))
const memoryUsed = computed(() => Number(props.gpu.memory_used_mb ?? 0))
const memoryPercent = computed(() =>
  memoryTotal.value > 0 ? Math.round((memoryUsed.value / memoryTotal.value) * 100) : 0,
)

const toneClass = computed(() => {
  if (props.nodeStatus === 'offline') {
    return 'gpu-card is-offline'
  }
  if (['allocated', 'busy', 'running'].includes(props.gpu.status || '')) {
    return 'gpu-card is-busy'
  }
  return 'gpu-card is-idle'
})

const memoryLabel = computed(() => {
  const totalGb = (memoryTotal.value / 1024).toFixed(1)
  const usedGb = (memoryUsed.value / 1024).toFixed(1)
  return `${usedGb} / ${totalGb} GB`
})
</script>

<template>
  <div :class="toneClass">
    <div class="gpu-card__header">
      <strong>GPU-{{ gpu.gpu_index }}</strong>
      <el-tag size="small" :type="nodeStatus === 'offline' ? 'info' : gpu.status === 'idle' ? 'success' : 'danger'">
        {{ gpu.status || 'unknown' }}
      </el-tag>
    </div>
    <div class="gpu-card__model">{{ gpu.gpu_model || '未上报型号' }}</div>
    <div class="gpu-card__metric">
      <span>利用率</span>
      <span>{{ utilization }}%</span>
    </div>
    <el-progress :percentage="utilization" :show-text="false" :stroke-width="10" />
    <div class="gpu-card__metric">
      <span>显存</span>
      <span>{{ memoryLabel }}</span>
    </div>
    <el-progress :percentage="memoryPercent" :show-text="false" :stroke-width="10" status="success" />
    <div class="gpu-card__footer">
      <span>温度 {{ gpu.temperature ?? 0 }}°C</span>
      <span v-if="gpu.assigned_task_id">任务 {{ gpu.assigned_task_id }}</span>
      <span v-else>空闲中</span>
    </div>
  </div>
</template>

<style scoped>
.gpu-card {
  padding: 16px;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: rgba(255, 255, 255, 0.84);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.gpu-card.is-idle {
  box-shadow: inset 0 0 0 1px rgba(34, 197, 94, 0.12);
}

.gpu-card.is-busy {
  box-shadow: inset 0 0 0 1px rgba(239, 68, 68, 0.14);
}

.gpu-card.is-offline {
  background: rgba(241, 245, 249, 0.9);
}

.gpu-card__header,
.gpu-card__metric,
.gpu-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.gpu-card__model {
  color: #334155;
  font-size: 14px;
}

.gpu-card__footer {
  color: #64748b;
  font-size: 13px;
}
</style>
