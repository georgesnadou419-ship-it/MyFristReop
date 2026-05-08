<template>
  <section class="page">
    <div class="hero">
      <div>
        <p class="eyebrow">Monitor</p>
        <h1>GPU 实时监控</h1>
        <p class="subtitle">每 30 秒轮询一次节点快照，展示最近 1 小时的利用率、显存与温度曲线。</p>
      </div>
      <el-select v-model="selectedNodeId" placeholder="选择节点" class="node-select" @change="refreshData">
        <el-option
          v-for="node in nodes"
          :key="node.node_id"
          :label="`${node.ip} (${node.status})`"
          :value="node.node_id"
        />
      </el-select>
    </div>

    <el-row :gutter="16" class="summary-grid">
      <el-col v-for="card in summaryCards" :key="card.label" :xs="24" :sm="12" :lg="6">
        <div class="stat-card">
          <span class="label">{{ card.label }}</span>
          <strong>{{ card.value }}</strong>
        </div>
      </el-col>
    </el-row>

    <el-empty v-if="!groupedMetrics.length" description="暂无 GPU 指标数据" />

    <div v-else class="gpu-grid">
      <article v-for="gpu in groupedMetrics" :key="gpu.gpuIndex" class="gpu-card">
        <div class="gpu-header">
          <div>
            <p class="eyebrow">GPU-{{ gpu.gpuIndex }}</p>
            <h2>{{ activeNode?.hostname || activeNode?.ip }}</h2>
          </div>
          <div class="mini-metrics">
            <span>峰值利用率 {{ gpu.maxUtilization }}%</span>
            <span>最高温度 {{ gpu.maxTemperature }}°C</span>
          </div>
        </div>
        <div :ref="(el) => setChartRef(gpu.gpuIndex, el)" class="chart"></div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch, type ComponentPublicInstance } from "vue";
import * as echarts from "echarts";

import { fetchGpuHistory, fetchNodesOverview, type GpuMetricPoint, type NodeOverview } from "../../api/monitor";

type ChartMap = Map<number, HTMLDivElement>;
type InstanceMap = Map<number, echarts.ECharts>;

const nodes = ref<NodeOverview[]>([]);
const metrics = ref<GpuMetricPoint[]>([]);
const selectedNodeId = ref("");
const chartRefs: ChartMap = new Map();
const chartInstances: InstanceMap = new Map();
let timer: number | undefined;

const activeNode = computed(() => nodes.value.find((item) => item.node_id === selectedNodeId.value));

const summaryCards = computed(() => {
  const node = activeNode.value;
  if (!node) {
    return [];
  }
  return [
    { label: "节点状态", value: node.status },
    { label: "GPU 总数", value: String(node.gpu_count) },
    { label: "已占用 GPU", value: String(node.gpu_used) },
    { label: "CPU / 内存", value: `${node.cpu_percent}% / ${node.memory_percent}%` },
  ];
});

const groupedMetrics = computed(() => {
  const groups = new Map<number, GpuMetricPoint[]>();
  for (const point of metrics.value) {
    const current = groups.get(point.gpu_index) ?? [];
    current.push(point);
    groups.set(point.gpu_index, current);
  }
  return Array.from(groups.entries()).map(([gpuIndex, points]) => ({
    gpuIndex,
    points,
    maxUtilization: Math.max(...points.map((item) => item.utilization)),
    maxTemperature: Math.max(...points.map((item) => item.temperature)),
  }));
});

function setChartRef(gpuIndex: number, element: Element | ComponentPublicInstance | null) {
  const target = element instanceof HTMLDivElement
    ? element
    : element && "$el" in element && element.$el instanceof HTMLDivElement
      ? element.$el
      : null;

  if (target) {
    chartRefs.set(gpuIndex, target);
    return;
  }

  chartRefs.delete(gpuIndex);
}

async function refreshNodes() {
  nodes.value = await fetchNodesOverview();
  if (!selectedNodeId.value && nodes.value.length > 0) {
    selectedNodeId.value = nodes.value[0].node_id;
  }
}

async function refreshData() {
  await refreshNodes();
  if (!selectedNodeId.value) {
    metrics.value = [];
    return;
  }
  metrics.value = await fetchGpuHistory(selectedNodeId.value, 1);
  await nextTick();
  renderCharts();
}

function renderCharts() {
  for (const group of groupedMetrics.value) {
    const dom = chartRefs.get(group.gpuIndex);
    if (!dom) {
      continue;
    }

    const existing = chartInstances.get(group.gpuIndex);
    const chart = existing ?? echarts.init(dom);
    chartInstances.set(group.gpuIndex, chart);
    chart.setOption({
      animationDuration: 400,
      grid: { left: 40, right: 18, top: 36, bottom: 28 },
      tooltip: { trigger: "axis" },
      legend: { top: 4, textStyle: { color: "#1a3a34" } },
      xAxis: {
        type: "category",
        data: group.points.map((item) => new Date(item.timestamp).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })),
        axisLine: { lineStyle: { color: "#83a49b" } },
      },
      yAxis: [
        { type: "value", name: "利用率%", min: 0, max: 100 },
        { type: "value", name: "显存MB", min: 0 },
        { type: "value", name: "温度°C", min: 0, max: 120 },
      ],
      series: [
        {
          name: "利用率",
          type: "line",
          smooth: true,
          data: group.points.map((item) => item.utilization),
          lineStyle: { color: "#0b8f6a", width: 3 },
          areaStyle: { color: "rgba(11, 143, 106, 0.18)" },
        },
        {
          name: "显存",
          type: "line",
          smooth: true,
          yAxisIndex: 1,
          data: group.points.map((item) => item.memory_used),
          lineStyle: { color: "#ff7b4d", width: 2 },
        },
        {
          name: "温度",
          type: "line",
          smooth: true,
          yAxisIndex: 2,
          data: group.points.map((item) => item.temperature),
          lineStyle: { color: "#d64545", width: 2 },
        },
      ],
    });
    chart.resize();
  }
}

watch(groupedMetrics, () => nextTick(renderCharts));

onMounted(async () => {
  await refreshData();
  timer = window.setInterval(refreshData, 30000);
  window.addEventListener("resize", renderCharts);
});

onBeforeUnmount(() => {
  if (timer) {
    window.clearInterval(timer);
  }
  window.removeEventListener("resize", renderCharts);
  chartInstances.forEach((instance) => instance.dispose());
  chartInstances.clear();
});
</script>

<style scoped>
.page {
  display: grid;
  gap: 18px;
}

.hero {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 24px;
  border-radius: 24px;
  background:
    linear-gradient(135deg, rgba(12, 138, 102, 0.96), rgba(10, 93, 83, 0.88)),
    linear-gradient(180deg, #123c35 0%, #0d2f2a 100%);
  color: #effaf8;
}

.eyebrow {
  margin: 0 0 6px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 12px;
  opacity: 0.75;
}

.hero h1,
.gpu-card h2 {
  margin: 0;
}

.subtitle {
  margin: 10px 0 0;
  max-width: 680px;
  color: rgba(239, 250, 248, 0.82);
}

.node-select {
  width: 240px;
  align-self: flex-start;
}

.summary-grid {
  margin: 0;
}

.stat-card,
.gpu-card {
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 16px 40px rgba(20, 54, 48, 0.08);
}

.stat-card {
  padding: 20px;
}

.stat-card .label {
  display: block;
  margin-bottom: 10px;
  color: #58746d;
}

.stat-card strong {
  font-size: 24px;
  color: #123730;
}

.gpu-grid {
  display: grid;
  gap: 16px;
}

.gpu-card {
  padding: 20px;
}

.gpu-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.mini-metrics {
  display: flex;
  gap: 16px;
  color: #4f6862;
  font-size: 13px;
}

.chart {
  height: 320px;
}

@media (max-width: 900px) {
  .hero,
  .gpu-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .node-select {
    width: 100%;
  }

  .mini-metrics {
    flex-wrap: wrap;
  }
}
</style>
