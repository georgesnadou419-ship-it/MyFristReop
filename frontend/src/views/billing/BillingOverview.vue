<template>
  <section class="page">
    <div class="hero">
      <div>
        <p class="eyebrow">Billing</p>
        <h1>计费中心</h1>
        <p class="subtitle">按任务聚合 GPU 消耗，分页查看账单，并用柱状图展示本月每日消耗。</p>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col v-for="card in cards" :key="card.label" :xs="24" :md="8">
        <div class="stat-card">
          <span class="label">{{ card.label }}</span>
          <strong>{{ card.value }}</strong>
        </div>
      </el-col>
    </el-row>

    <div class="chart-card">
      <div class="section-head">
        <h2>本月消耗</h2>
      </div>
      <div ref="chartRef" class="chart"></div>
    </div>

    <div class="table-card">
      <div class="section-head">
        <h2>计费明细</h2>
      </div>
      <el-table :data="records.items" stripe>
        <el-table-column prop="created_at" label="时间" min-width="160">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="task_name" label="任务名称" min-width="180">
          <template #default="{ row }">{{ row.task_name || row.resource_type }}</template>
        </el-table-column>
        <el-table-column prop="gpu_model" label="资源" min-width="140">
          <template #default="{ row }">{{ row.gpu_model || "-" }}</template>
        </el-table-column>
        <el-table-column prop="duration_display" label="时长" min-width="100" />
        <el-table-column prop="cost" label="费用" min-width="100">
          <template #default="{ row }">{{ Number(row.cost).toFixed(4) }}</template>
        </el-table-column>
      </el-table>
      <div class="pagination">
        <el-pagination
          background
          layout="prev, pager, next"
          :current-page="page"
          :page-size="pageSize"
          :total="records.total"
          @current-change="handlePageChange"
        />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import * as echarts from "echarts";

import { fetchBillingRecords, fetchBillingSummary, type BillingRecordItem, type BillingRecordsPage } from "../../api/billing";

const summary = ref({ total_credits: "0", used_credits: "0", remaining: "0" });
const records = ref<BillingRecordsPage>({ items: [], total: 0, page: 1, page_size: 20 });
const monthRecords = ref<BillingRecordItem[]>([]);
const page = ref(1);
const pageSize = 20;
const chartRef = ref<HTMLDivElement | null>(null);
let chart: echarts.ECharts | undefined;

const cards = computed(() => [
  { label: "总额度", value: Number(summary.value.total_credits).toFixed(2) },
  { label: "累计消耗", value: Number(summary.value.used_credits).toFixed(2) },
  { label: "当前余额", value: Number(summary.value.remaining).toFixed(2) },
]);

function formatDate(value: string) {
  return new Date(value).toLocaleString("zh-CN");
}

function buildMonthSeries(source: BillingRecordItem[]) {
  const currentMonth = new Date().getMonth();
  const currentYear = new Date().getFullYear();
  const grouped = new Map<string, { label: string; value: number; time: number }>();
  for (const item of source) {
    const date = new Date(item.created_at);
    if (date.getMonth() !== currentMonth || date.getFullYear() !== currentYear) {
      continue;
    }
    const key = date.toISOString().slice(0, 10);
    const current = grouped.get(key);
    grouped.set(key, {
      label: `${date.getMonth() + 1}-${date.getDate()}`,
      value: (current?.value ?? 0) + Number(item.cost),
      time: date.getTime(),
    });
  }
  return Array.from(grouped.values()).sort((a, b) => a.time - b.time);
}

function renderChart() {
  if (!chartRef.value) {
    return;
  }
  const series = buildMonthSeries(monthRecords.value);
  chart = chart ?? echarts.init(chartRef.value);
  chart.setOption({
    animationDuration: 500,
    tooltip: { trigger: "axis" },
    grid: { left: 32, right: 18, top: 30, bottom: 26 },
    xAxis: {
      type: "category",
      data: series.map((item) => item.label),
      axisLine: { lineStyle: { color: "#9cb0aa" } },
    },
    yAxis: { type: "value", name: "credits" },
    series: [
      {
        type: "bar",
        data: series.map((item) => Number(item.value.toFixed(4))),
        itemStyle: {
          borderRadius: [8, 8, 0, 0],
          color: "#147a65",
        },
      },
    ],
  });
  chart.resize();
}

async function loadSummary() {
  summary.value = await fetchBillingSummary();
}

async function loadRecords(currentPage = page.value) {
  records.value = await fetchBillingRecords(currentPage, pageSize);
  page.value = currentPage;
}

async function loadMonthChartData() {
  const data = await fetchBillingRecords(1, 200);
  monthRecords.value = data.items;
  await nextTick();
  renderChart();
}

async function refresh() {
  await Promise.all([loadSummary(), loadRecords(), loadMonthChartData()]);
}

async function handlePageChange(currentPage: number) {
  await loadRecords(currentPage);
}

onMounted(async () => {
  await refresh();
  window.addEventListener("resize", renderChart);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", renderChart);
  chart?.dispose();
  chart = undefined;
});
</script>

<style scoped>
.page {
  display: grid;
  gap: 18px;
}

.hero,
.stat-card,
.chart-card,
.table-card {
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 16px 40px rgba(20, 54, 48, 0.08);
}

.hero {
  padding: 24px;
  background:
    radial-gradient(circle at right top, rgba(255, 172, 94, 0.28), transparent 26%),
    linear-gradient(135deg, #fff7ef 0%, #ffffff 65%);
}

.eyebrow {
  margin: 0 0 6px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 12px;
  color: #a2551f;
}

.hero h1,
.section-head h2 {
  margin: 0;
  color: #15332e;
}

.subtitle {
  margin: 10px 0 0;
  max-width: 680px;
  color: #5d716c;
}

.stat-card,
.chart-card,
.table-card {
  padding: 20px;
}

.label {
  display: block;
  margin-bottom: 10px;
  color: #647771;
}

.stat-card strong {
  font-size: 28px;
  color: #123730;
}

.section-head {
  margin-bottom: 14px;
}

.chart {
  height: 320px;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
