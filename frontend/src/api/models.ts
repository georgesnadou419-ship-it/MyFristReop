import request from './request'

export interface ModelRead {
  id: string
  name: string
  display_name?: string | null
  model_type?: string | null
  framework?: string | null
  model_path?: string | null
  container_image?: string | null
  launch_command?: string | null
  config_json?: Record<string, unknown> | null
  status: string
  replicas: number
  gpu_requirement?: string | null
  api_format: string
  description?: string | null
  created_at: string
  updated_at: string
}

export interface ModelInstanceRead {
  id: string
  model_id: string
  node_id: string
  container_id?: string | null
  assigned_gpu_indices?: number[] | null
  port?: number | null
  status: string
  api_endpoint?: string | null
  started_at: string
}

export interface ModelDeployResponse {
  model: ModelRead
  instances: ModelInstanceRead[]
}

export interface ModelPayload {
  name: string
  display_name?: string | null
  model_type?: string | null
  framework?: string | null
  model_path?: string | null
  container_image?: string | null
  launch_command?: string | null
  config_json?: Record<string, unknown> | null
  replicas?: number
  gpu_requirement?: string | null
  api_format?: string
  description?: string | null
}

export const listModelsApi = () => request.get<unknown, ModelRead[]>('/models')
export const getModelApi = (id: string) => request.get<unknown, ModelRead>(`/models/${id}`)
export const createModelApi = (payload: ModelPayload) => request.post<unknown, ModelRead>('/models', payload)
export const updateModelApi = (id: string, payload: Partial<ModelPayload>) =>
  request.put<unknown, ModelRead>(`/models/${id}`, payload)
export const deleteModelApi = (id: string) => request.delete<unknown, null>(`/models/${id}`)
export const deployModelApi = (id: string) =>
  request.post<unknown, ModelDeployResponse>(`/models/${id}/deploy`)
export const stopModelApi = (id: string) => request.post<unknown, ModelRead>(`/models/${id}/stop`)
export const listModelInstancesApi = (id: string) =>
  request.get<unknown, ModelInstanceRead[]>(`/models/${id}/instances`)
