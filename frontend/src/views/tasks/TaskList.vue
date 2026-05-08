<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useTasksStore } from '../../stores/tasks'
import TaskStatusBadge from '../../components/TaskStatusBadge.vue'

const router = useRouter()
const tasksStore = useTasksStore()
let refreshTimer: number | null = null

const filters = reactive({
  status: '',
  search: '',
  page: 1,
  pageSize: 10,
})

const loadData = async () => {
  await tasksStore.fetchTasks({
    status: filters.status || undefined,
    page: filters.page,
    page_size: filters.pageSize,
  })
}

const tableData = computed(() =>
  tasksStore.tasks.filter((task) => {
    if (!filters.search.trim()) {
      return true
    }
    return task.name.toLowerCase().includes(filters.search.trim().toLowerCase())
  }),
)

const handleCancel = async (id: string) => {
  await tasksStore.cancelTask(id)
}

const handleDelete = async (id: string) => {
  await ElMessageBox.confirm('确认删除该任务记录吗？', '提示', {
    type: 'warning',
  })
  await tasksStore.deleteTask(id)
}

const handleStatusChange = async () => {
  filters.page = 1
  await loadData()
}

const handlePageChange = async (page: number) => {
  filters.page = page
  await loadData()
}

const handlePageSizeChange = async (pageSize: number) => {
  filters.pageSize = pageSize
  filters.page = 1
  await loadData()
}

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
        <h2 class="page-title">任务列表</h2>
        <p class="page-subtitle">筛选任务状态，查看调度去向与执行结果。</p>
      </div>
      <el-button type="primary" @click="router.push('/tasks/submit')">
        新建任务
      </el-button>
    </div>

    <section class="section-card glass-card">
      <div class="task-filters">
        <el-select
          v-model="filters.status"
          clearable
          placeholder="全部状态"
          style="width: 180px"
          @change="handleStatusChange"
          @clear="handleStatusChange"
        >
          <el-option label="运行中" value="running" />
          <el-option label="排队中" value="queued" />
          <el-option label="已成功" value="success" />
          <el-option label="已失败" value="failed" />
        </el-select>
        <el-input v-model="filters.search" placeholder="按任务名称搜索" clearable />
      </div>

      <el-table :data="tableData" stripe v-loading="tasksStore.loading">
        <el-table-column prop="name" label="名称" min-width="180" />
        <el-table-column prop="task_type" label="类型" width="120" />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <TaskStatusBadge :status="row.status" />
          </template>
        </el-table-column>
        <el-table-column label="GPU" min-width="130">
          <template #default="{ row }">
            {{ (row.assigned_gpu_indices || []).join(', ') || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="节点" min-width="160">
          <template #default="{ row }">
            {{ row.assigned_node_ip || row.assigned_node_id || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" min-width="180" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="router.push(`/tasks/${row.id}`)">
              查看详情
            </el-button>
            <el-button
              v-if="row.status === 'queued'"
              link
              type="warning"
              @click="handleCancel(row.id)"
            >
              取消
            </el-button>
            <el-button
              v-if="['success', 'failed', 'cancelled'].includes(row.status || '')"
              link
              type="danger"
              @click="handleDelete(row.id)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="task-pagination">
        <el-pagination
          v-model:current-page="filters.page"
          v-model:page-size="filters.pageSize"
          background
          layout="total, sizes, prev, pager, next"
          :total="tasksStore.total"
          :page-sizes="[10, 20, 50]"
          @current-change="handlePageChange"
          @size-change="handlePageSizeChange"
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.task-filters {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.task-pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
