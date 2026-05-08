import { defineStore } from 'pinia'
import {
  cancelTaskApi,
  createTaskApi,
  deleteTaskApi,
  getTaskDetailApi,
  getTaskLogsApi,
  listTasksApi,
  submitTaskApi,
} from '../api/tasks'
import type {
  CreateTaskPayload,
  TaskItem,
  TaskListParams,
  TaskListResult,
  TaskLog,
  TaskUpdateEvent,
} from '../types'

interface TasksState {
  tasks: TaskItem[]
  recentTasks: TaskItem[]
  total: number
  runningCount: number
  currentTask: TaskItem | null
  logs: TaskLog[]
  loading: boolean
}

const normalizeTaskList = (
  payload: TaskListResult | TaskItem[] | Record<string, unknown>,
  fallbackPage = 1,
  fallbackSize = 10,
): TaskListResult => {
  if (Array.isArray(payload)) {
    return {
      items: payload,
      total: payload.length,
      page: fallbackPage,
      page_size: fallbackSize,
    }
  }

  const map = payload as Record<string, unknown>
  const candidateItems =
    (map.items as TaskItem[] | undefined) ||
    (map.records as TaskItem[] | undefined) ||
    (map.list as TaskItem[] | undefined) ||
    []

  return {
    items: Array.isArray(candidateItems) ? candidateItems : [],
    total: Number(map.total ?? candidateItems.length ?? 0),
    page: Number(map.page ?? fallbackPage),
    page_size: Number(map.page_size ?? fallbackSize),
  }
}

const normalizeLogs = (payload: TaskLog[] | { logs: string | TaskLog[] }) => {
  if (Array.isArray(payload)) {
    return payload
  }

  if (Array.isArray(payload.logs)) {
    return payload.logs
  }

  if (typeof payload.logs === 'string') {
    return payload.logs
      .split('\n')
      .filter(Boolean)
      .map((line, index) => ({
        id: index,
        message: line,
      }))
  }

  return []
}

const replaceTask = (list: TaskItem[], nextTask: TaskItem) => {
  const index = list.findIndex((task) => task.id === nextTask.id)

  if (index >= 0) {
    list.splice(index, 1, {
      ...list[index],
      ...nextTask,
    })
    return
  }

  list.unshift(nextTask)
}

export const useTasksStore = defineStore('tasks', {
  state: (): TasksState => ({
    tasks: [],
    recentTasks: [],
    total: 0,
    runningCount: 0,
    currentTask: null,
    logs: [],
    loading: false,
  }),
  actions: {
    async fetchTasks(params: TaskListParams = {}) {
      this.loading = true
      try {
        const result = await listTasksApi(params)
        const normalized = normalizeTaskList(
          result as TaskListResult | TaskItem[] | Record<string, unknown>,
          params.page ?? 1,
          params.page_size ?? 10,
        )
        this.tasks = normalized.items
        this.total = normalized.total
      } finally {
        this.loading = false
      }
    },
    async fetchRecentTasks() {
      const result = await listTasksApi({ page: 1, page_size: 10 })
      const normalized = normalizeTaskList(
        result as TaskListResult | TaskItem[] | Record<string, unknown>,
        1,
        10,
      )
      this.recentTasks = normalized.items
    },
    async refreshRunningCount() {
      const result = await listTasksApi({ status: 'running', page: 1, page_size: 1 })
      const normalized = normalizeTaskList(
        result as TaskListResult | TaskItem[] | Record<string, unknown>,
        1,
        1,
      )
      this.runningCount = normalized.total
    },
    async fetchTaskDetail(id: string) {
      this.currentTask = await getTaskDetailApi(id)
      return this.currentTask
    },
    async fetchLogs(id: string) {
      const result = await getTaskLogsApi(id)
      this.logs = normalizeLogs(result)
    },
    async createTask(payload: CreateTaskPayload) {
      return createTaskApi(payload)
    },
    async submitTask(id: string) {
      const task = await submitTaskApi(id)
      replaceTask(this.tasks, task)
      replaceTask(this.recentTasks, task)
      if (this.currentTask?.id === task.id) {
        this.currentTask = { ...this.currentTask, ...task }
      }
      return task
    },
    async cancelTask(id: string) {
      const task = await cancelTaskApi(id)
      replaceTask(this.tasks, task)
      replaceTask(this.recentTasks, task)
      if (this.currentTask?.id === task.id) {
        this.currentTask = { ...this.currentTask, ...task }
      }
      return task
    },
    async deleteTask(id: string) {
      await deleteTaskApi(id)
      this.tasks = this.tasks.filter((task) => task.id !== id)
      this.recentTasks = this.recentTasks.filter((task) => task.id !== id)
      if (this.currentTask?.id === id) {
        this.currentTask = null
        this.logs = []
      }
    },
    handleTaskUpdate(update: TaskUpdateEvent) {
      const patch: TaskItem = {
        id: update.task_id,
        status: update.status,
        assigned_node_id: update.assigned_node_id,
        assigned_node_ip: update.assigned_node_ip,
        assigned_gpu_indices: update.assigned_gpu_indices,
        runtime_seconds: update.runtime_seconds,
        name: '',
      }

      const applyPatch = (list: TaskItem[]) =>
        list.map((task) =>
          task.id === update.task_id
            ? {
                ...task,
                ...patch,
                name: task.name,
              }
            : task,
        )

      this.tasks = applyPatch(this.tasks)
      this.recentTasks = applyPatch(this.recentTasks)

      if (this.currentTask?.id === update.task_id) {
        this.currentTask = {
          ...this.currentTask,
          ...patch,
          name: this.currentTask.name,
        }
      }

      if (update.status === 'running') {
        this.runningCount += 1
      } else if (
        ['success', 'failed', 'cancelled'].includes(update.status || '') &&
        this.runningCount > 0
      ) {
        this.runningCount -= 1
      }
    },
  },
})
