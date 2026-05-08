export interface ApiEnvelope<T> {
  code: number
  data: T
  message: string
}

export interface UserInfo {
  id: string
  username: string
  role: string
}

export interface LoginPayload {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface GpuInfo {
  id?: string
  node_id?: string
  node_ip?: string
  gpu_index: number
  gpu_model?: string
  status?: string
  utilization?: number
  utilization_gpu?: number
  temperature?: number
  memory_total_mb?: number
  memory_used_mb?: number
  assigned_task_id?: string
  processes?: Array<Record<string, unknown>>
}

export interface NodeInfo {
  id: string
  ip: string
  hostname?: string
  status?: string
  gpu_count?: number
  cpu_usage?: number
  cpu_percent?: number
  memory_usage?: number
  memory_percent?: number
  total_memory_mb?: number
  used_memory_mb?: number
  gpus?: GpuInfo[]
}

export interface TaskItem {
  id: string
  name: string
  task_type?: string
  status?: string
  priority?: number | string
  assigned_node_id?: string
  assigned_node_ip?: string
  assigned_gpu_indices?: number[]
  assigned_gpu_models?: string[]
  container_image?: string
  container_command?: string
  container_id?: string
  created_at?: string
  started_at?: string
  finished_at?: string
  runtime_seconds?: number
  result_json?: Record<string, unknown> | null
  config_json?: Record<string, unknown> | null
}

export interface TaskLog {
  id?: string | number
  source?: string
  message: string
  timestamp?: string
}

export interface TaskListResult {
  items: TaskItem[]
  total: number
  page: number
  page_size: number
}

export interface TaskListParams {
  status?: string
  page?: number
  page_size?: number
}

export interface CreateTaskPayload {
  name: string
  task_type: string
  container_image: string
  container_command: string
  priority: number
  gpu_count: number
  gpu_model?: string | null
  min_memory_mb?: number | null
  config_json?: Record<string, unknown>
}

export interface TaskUpdateEvent {
  task_id: string
  status?: string
  assigned_node_id?: string
  assigned_node_ip?: string
  assigned_gpu_indices?: number[]
  runtime_seconds?: number
}
