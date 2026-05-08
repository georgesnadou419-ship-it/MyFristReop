import request from './request'
import type { GpuInfo, NodeInfo } from '../types'

export const getNodesApi = () => request.get<unknown, NodeInfo[]>('/nodes')

export const getGpuResourcesApi = () =>
  request.get<unknown, GpuInfo[]>('/resources/gpus')
