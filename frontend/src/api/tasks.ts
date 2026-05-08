import request from './request'
import type {
  CreateTaskPayload,
  TaskItem,
  TaskListParams,
  TaskListResult,
  TaskLog,
} from '../types'

export const createTaskApi = (payload: CreateTaskPayload) =>
  request.post<unknown, TaskItem>('/tasks', payload)

export const listTasksApi = (params: TaskListParams) =>
  request.get<unknown, TaskListResult | TaskItem[]>('/tasks', { params })

export const getTaskDetailApi = (id: string) =>
  request.get<unknown, TaskItem>(`/tasks/${id}`)

export const getTaskLogsApi = (id: string) =>
  request.get<unknown, TaskLog[] | { logs: string | TaskLog[] }>(`/tasks/${id}/logs`)

export const submitTaskApi = (id: string) =>
  request.post<unknown, TaskItem>(`/tasks/${id}/submit`)

export const cancelTaskApi = (id: string) =>
  request.post<unknown, TaskItem>(`/tasks/${id}/cancel`)

export const deleteTaskApi = (id: string) =>
  request.delete<unknown, { success: boolean }>(`/tasks/${id}`)
