import { defineStore } from 'pinia'
import { getGpuResourcesApi, getNodesApi } from '../api/nodes'
import type { GpuInfo, NodeInfo } from '../types'

interface NodesState {
  nodes: NodeInfo[]
  loading: boolean
  lastUpdated: string | null
}

const toArray = <T>(value: T[] | null | undefined): T[] =>
  Array.isArray(value) ? value : []

const mergeNodesWithGpus = (nodes: NodeInfo[], gpuResources: GpuInfo[]) => {
  if (!gpuResources.length) {
    return nodes
  }

  return nodes.map((node) => {
    const gpus = gpuResources.filter(
      (gpu) => gpu.node_id === node.id || gpu.node_ip === node.ip,
    )

    return {
      ...node,
      gpus: gpus.length ? gpus : toArray(node.gpus),
      gpu_count: node.gpu_count ?? gpus.length,
    }
  })
}

export const useNodesStore = defineStore('nodes', {
  state: (): NodesState => ({
    nodes: [],
    loading: false,
    lastUpdated: null,
  }),
  getters: {
    onlineCount: (state) =>
      state.nodes.filter((node) => node.status === 'online').length,
    totalGpus: (state) =>
      state.nodes.reduce(
        (sum, node) => sum + (node.gpu_count ?? toArray(node.gpus).length),
        0,
      ),
    idleGpus: (state) =>
      state.nodes.reduce((sum, node) => {
        const idleCount = toArray(node.gpus).filter((gpu) =>
          ['idle', 'free', 'available'].includes(gpu.status || 'idle'),
        ).length
        return sum + idleCount
      }, 0),
  },
  actions: {
    async refresh() {
      this.loading = true
      try {
        const [nodes, gpuResources] = await Promise.all([
          getNodesApi().catch(() => [] as NodeInfo[]),
          getGpuResourcesApi().catch(() => [] as GpuInfo[]),
        ])
        this.nodes = mergeNodesWithGpus(toArray(nodes), toArray(gpuResources))
        this.lastUpdated = new Date().toISOString()
      } finally {
        this.loading = false
      }
    },
  },
})
