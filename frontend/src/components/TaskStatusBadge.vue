<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status?: string
}>()

const normalizedStatus = computed(() => props.status || 'unknown')

const tagType = computed(() => {
  switch (normalizedStatus.value) {
    case 'running':
      return 'primary'
    case 'success':
      return 'success'
    case 'queued':
    case 'pending':
      return 'warning'
    case 'failed':
      return 'danger'
    case 'cancelled':
      return 'info'
    default:
      return 'info'
  }
})

const label = computed(() => {
  switch (normalizedStatus.value) {
    case 'pending':
      return '待处理'
    case 'queued':
      return '排队中'
    case 'running':
      return '运行中'
    case 'success':
      return '已成功'
    case 'failed':
      return '已失败'
    case 'cancelled':
      return '已取消'
    default:
      return normalizedStatus.value
  }
})
</script>

<template>
  <el-tag :type="tagType" round effect="light">
    {{ label }}
  </el-tag>
</template>
