<template>
  <div ref="chartRef" class="chart"></div>
</template>

<script setup lang="ts">
import * as echarts from "echarts";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

import type { TrendPoint } from "../../types/system";

const props = defineProps<{
  points: TrendPoint[];
}>();

const chartRef = ref<HTMLDivElement | null>(null);
let chart: echarts.ECharts | null = null;

const render = () => {
  if (!chartRef.value) {
    return;
  }
  if (!chart) {
    chart = echarts.init(chartRef.value);
  }

  chart.setOption({
    grid: { top: 16, left: 4, right: 6, bottom: 10, containLabel: true },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: props.points.map((point) => point.time),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { show: false },
    },
    yAxis: {
      type: "value",
      splitLine: { show: false },
      axisLabel: { show: false },
    },
    tooltip: {
      trigger: "axis",
      valueFormatter: (value: string | number) => `${value} RTF`,
      backgroundColor: "rgba(2, 6, 23, 0.92)",
      borderColor: "rgba(0, 240, 255, 0.18)",
      textStyle: { color: "#dff8ff" },
    },
    series: [
      {
        data: props.points.map((point) => point.value),
        type: "line",
        smooth: true,
        symbolSize: 8,
        lineStyle: {
          width: 3,
          color: "#00f0ff",
          shadowBlur: 12,
          shadowColor: "rgba(0, 240, 255, 0.2)",
        },
        itemStyle: {
          color: "#3b82f6",
          borderColor: "#dff8ff",
          borderWidth: 1,
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(0, 240, 255, 0.26)" },
            { offset: 0.55, color: "rgba(59, 130, 246, 0.14)" },
            { offset: 1, color: "rgba(124, 58, 237, 0.02)" },
          ]),
        },
      },
    ],
  });
};

const resize = () => chart?.resize();

watch(() => props.points, render, { deep: true });

onMounted(() => {
  render();
  window.addEventListener("resize", resize);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", resize);
  chart?.dispose();
});
</script>

<style scoped>
.chart {
  width: 100%;
  min-height: 260px;
}
</style>
