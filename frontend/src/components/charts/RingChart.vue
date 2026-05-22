<template>
  <div ref="chartRef" class="chart"></div>
</template>

<script setup lang="ts">
import * as echarts from "echarts";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps<{
  value: number;
  title: string;
  color?: string;
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
    animationDuration: 500,
    title: {
      text: `${props.value}%`,
      subtext: props.title,
      left: "center",
      top: "34%",
      textStyle: {
        fontSize: 28,
        fontWeight: 700,
        fontFamily: "JetBrains Mono, Roboto Mono, monospace",
        color: "#ffffff",
        textShadowColor: "rgba(0, 240, 255, 0.28)",
        textShadowBlur: 18,
      },
      subtextStyle: {
        fontSize: 14,
        color: "#94a3b8",
      },
    },
    series: [
      {
        type: "pie",
        radius: ["68%", "88%"],
        silent: true,
        label: { show: false },
        startAngle: 90,
        data: [
          {
            value: props.value,
            itemStyle: {
              color:
                props.color ||
                new echarts.graphic.LinearGradient(0, 0, 1, 1, [
                  { offset: 0, color: "#00f0ff" },
                  { offset: 0.5, color: "#3b82f6" },
                  { offset: 1, color: "#7c3aed" },
                ]),
              shadowBlur: 18,
              shadowColor: "rgba(0, 240, 255, 0.28)",
            },
          },
          {
            value: 100 - props.value,
            itemStyle: {
              color: "rgba(148, 163, 184, 0.12)",
            },
          },
        ],
      },
    ],
  });
};

const resize = () => chart?.resize();

watch(() => [props.value, props.title, props.color], render, { deep: true });

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
