import request from './request'
import type { GpuInfo } from '../types'

export const listGpuResourcesApi = () =>
  request.get<unknown, GpuInfo[]>('/resources/gpus')
