import request from './request'

export interface GpuMetricPoint {
  timestamp: string;
  node_id: string;
  gpu_index: number;
  utilization: number;
  memory_used: number;
  memory_total: number;
  temperature: number;
  power_usage: number;
}

export interface NodeOverview {
  node_id: string;
  hostname?: string | null;
  ip: string;
  status: string;
  gpu_count: number;
  gpu_used: number;
  cpu_percent: number;
  memory_percent: number;
  last_heartbeat?: string | null
}

export async function fetchNodesOverview() {
  return request.get<unknown, NodeOverview[]>('/monitor/nodes/overview')
}

export async function fetchGpuHistory(nodeId: string, hours = 1) {
  return request.get<unknown, GpuMetricPoint[]>('/monitor/gpu/history', {
    params: { node_id: nodeId, hours },
  })
}
