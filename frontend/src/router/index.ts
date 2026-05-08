import { createRouter, createWebHistory } from 'vue-router'
import Layout from '../components/Layout.vue'
import Dashboard from '../views/Dashboard.vue'
import Login from '../views/Login.vue'
import BillingOverview from '../views/billing/BillingOverview.vue'
import GpuMonitor from '../views/monitor/GpuMonitor.vue'
import NodeList from '../views/resources/NodeList.vue'
import TaskDetail from '../views/tasks/TaskDetail.vue'
import TaskList from '../views/tasks/TaskList.vue'
import TaskSubmit from '../views/tasks/TaskSubmit.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: Login,
      meta: { guestOnly: true },
    },
    {
      path: '/',
      component: Layout,
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'dashboard',
          component: Dashboard,
        },
        {
          path: 'resources',
          name: 'resources',
          component: NodeList,
        },
        {
          path: 'monitor',
          name: 'monitor',
          component: GpuMonitor,
        },
        {
          path: 'tasks',
          name: 'tasks',
          component: TaskList,
        },
        {
          path: 'tasks/submit',
          name: 'task-submit',
          component: TaskSubmit,
        },
        {
          path: 'tasks/:id',
          name: 'task-detail',
          component: TaskDetail,
        },
        {
          path: 'billing',
          name: 'billing',
          component: BillingOverview,
        },
      ],
    },
  ],
})

router.beforeEach((to) => {
  const token = localStorage.getItem('token')

  if (to.meta.requiresAuth && !token) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.meta.guestOnly && token) {
    return { name: 'dashboard' }
  }

  return true
})

export default router
