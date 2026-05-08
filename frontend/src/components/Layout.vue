<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Coin,
  Cpu,
  DataAnalysis,
  Grid,
  Histogram,
  Operation,
  Plus,
  SwitchButton,
} from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import { useTasksStore } from '../stores/tasks'
import { taskWebSocket } from '../utils/websocket'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const tasksStore = useTasksStore()

const menuItems = [
  { index: '/', label: '首页', icon: DataAnalysis },
  { index: '/resources', label: '资源管理', icon: Cpu },
  { index: '/monitor', label: 'GPU监控', icon: Histogram },
  { index: '/tasks', label: '任务列表', icon: Grid },
  { index: '/tasks/submit', label: '提交任务', icon: Plus },
  { index: '/billing', label: '计费中心', icon: Coin },
]

const activeMenu = computed(() => {
  if (route.path.startsWith('/tasks/submit')) {
    return '/tasks/submit'
  }
  if (route.path.startsWith('/tasks')) {
    return '/tasks'
  }
  if (route.path.startsWith('/monitor')) {
    return '/monitor'
  }
  if (route.path.startsWith('/billing')) {
    return '/billing'
  }
  if (route.path.startsWith('/resources')) {
    return '/resources'
  }
  return '/'
})

const handleSelect = async (index: string) => {
  await router.push(index)
}

const handleLogout = async () => {
  await authStore.logout()
}

onMounted(() => {
  taskWebSocket.connect((payload) => {
    tasksStore.handleTaskUpdate(payload)
  })
})

onUnmounted(() => {
  taskWebSocket.disconnect()
})
</script>

<template>
  <div class="layout-shell">
    <aside class="layout-sidebar glass-card">
      <div class="layout-brand">
        <div class="layout-brand__mark">S</div>
        <div>
          <div class="layout-brand__title">SUIT API</div>
          <div class="layout-brand__subtitle">算力调度控制台</div>
        </div>
      </div>
      <el-menu
        :default-active="activeMenu"
        class="layout-menu"
        @select="handleSelect"
      >
        <el-menu-item
          v-for="item in menuItems"
          :key="item.index"
          :index="item.index"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>
      <div class="layout-sidebar__footer">
        <div class="layout-sidebar__caption">
          <el-icon><Operation /></el-icon>
          实时状态通过 WebSocket 推送
        </div>
      </div>
    </aside>

    <section class="layout-main">
      <header class="layout-header glass-card">
        <div>
          <div class="layout-header__eyebrow">Control Plane</div>
          <h1 class="layout-header__title">校内 AI 算力调度平台</h1>
        </div>
        <div class="layout-header__user">
          <div class="layout-header__meta">
            <strong>{{ authStore.user?.username || '未登录用户' }}</strong>
            <span>{{ authStore.user?.role || 'guest' }}</span>
          </div>
          <el-button type="danger" plain @click="handleLogout">
            <el-icon><SwitchButton /></el-icon>
            退出
          </el-button>
        </div>
      </header>

      <main class="layout-content">
        <router-view />
      </main>
    </section>
  </div>
</template>

<style scoped>
.layout-shell {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  min-height: 100vh;
  gap: 20px;
  padding: 20px;
}

.layout-sidebar {
  display: flex;
  flex-direction: column;
  padding: 20px 16px;
  border-radius: 28px;
}

.layout-brand {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 8px 10px 24px;
}

.layout-brand__mark {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  background: linear-gradient(135deg, #0f766e, #14b8a6);
  color: #fff;
  display: grid;
  place-items: center;
  font-size: 22px;
  font-weight: 800;
}

.layout-brand__title {
  font-size: 20px;
  font-weight: 800;
}

.layout-brand__subtitle {
  color: #64748b;
  font-size: 13px;
}

.layout-menu {
  border-right: none;
  background: transparent;
}

.layout-menu :deep(.el-menu-item) {
  height: 48px;
  border-radius: 14px;
  margin-bottom: 8px;
}

.layout-menu :deep(.el-menu-item.is-active) {
  background: rgba(15, 118, 110, 0.1);
  color: #0f766e;
}

.layout-sidebar__footer {
  margin-top: auto;
  padding: 20px 10px 10px;
}

.layout-sidebar__caption {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #64748b;
  font-size: 13px;
}

.layout-main {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.layout-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  border-radius: 28px;
  padding: 22px 28px;
}

.layout-header__eyebrow {
  color: #0f766e;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.layout-header__title {
  margin: 6px 0 0;
  font-size: 28px;
}

.layout-header__user {
  display: flex;
  align-items: center;
  gap: 16px;
}

.layout-header__meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.layout-header__meta span {
  color: #64748b;
  font-size: 13px;
  text-transform: uppercase;
}

.layout-content {
  min-height: 0;
}
</style>
