<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import type { EChartsInstance } from '../../utils/echarts'
import type { DashboardCharts } from '../../api/admin'

const props = defineProps<{ data: DashboardCharts }>()

const trendRef = ref<HTMLElement>()
const pieRef = ref<HTMLElement>()
let trendChart: EChartsInstance | null = null
let pieChart: EChartsInstance | null = null
let initChart: ((el: HTMLElement) => EChartsInstance) | null = null

async function renderCharts() {
  if (!trendRef.value || !pieRef.value) return
  const mod = await import('../../utils/echarts')
  initChart = mod.initChart
  trendChart?.dispose()
  pieChart?.dispose()
  trendChart = initChart(trendRef.value)
  pieChart = initChart(pieRef.value)

  const dates = props.data.trend.map(p => p.date.slice(5))
  trendChart.setOption({
    color: ['#4338ca', '#6366f1', '#818cf8'],
    tooltip: { trigger: 'axis' },
    legend: { data: ['新增用户', '对话', '订单'] },
    grid: { left: 48, right: 24, top: 48, bottom: 32 },
    xAxis: { type: 'category', data: dates, boundaryGap: false },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      { name: '新增用户', type: 'line', smooth: true, data: props.data.trend.map(p => p.users) },
      { name: '对话', type: 'line', smooth: true, data: props.data.trend.map(p => p.conversations) },
      { name: '订单', type: 'line', smooth: true, data: props.data.trend.map(p => p.orders) },
    ],
  })

  pieChart.setOption({
    color: ['#e0e7ff', '#6366f1', '#4338ca', '#a5b4fc'],
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['42%', '68%'],
      center: ['50%', '45%'],
      data: props.data.membership_distribution,
      label: { formatter: '{b}\n{c}' },
    }],
  })
}

function onResize() {
  trendChart?.resize()
  pieChart?.resize()
}

onMounted(async () => {
  await nextTick()
  await renderCharts()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  trendChart?.dispose()
  pieChart?.dispose()
})
</script>

<template>
  <div class="chart-row">
    <div class="admin-panel-card chart-panel">
      <div class="panel-section-head">
        <h3>近 30 日趋势</h3>
      </div>
      <div class="admin-panel-body chart-panel-body">
        <div ref="trendRef" class="chart-box" />
      </div>
    </div>
    <div class="admin-panel-card chart-panel chart-panel--side">
      <div class="panel-section-head">
        <h3>会员等级分布</h3>
      </div>
      <div class="admin-panel-body chart-panel-body">
        <div ref="pieRef" class="chart-box" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.chart-box {
  height: 300px;
}
</style>
