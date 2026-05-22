<template>
  <div class="metric-card">
    <div class="metric-meta">
      <span>{{ metric.label }}</span>
      <el-tag :type="tagType" effect="plain" round>{{ badgeText }}</el-tag>
    </div>
    <div class="metric-value">{{ metric.value }}</div>
    <p>{{ metric.hint }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { DashboardMetric } from "../types/system";

const props = defineProps<{
  metric: DashboardMetric;
}>();

const tagType = computed(() => {
  if (props.metric.tone === "success") return "success";
  if (props.metric.tone === "warning") return "warning";
  if (props.metric.tone === "danger") return "danger";
  return "info";
});

const badgeText = computed(() => {
  if (props.metric.tone === "success") return "Normal";
  if (props.metric.tone === "warning") return "Watch";
  if (props.metric.tone === "danger") return "Risk";
  return "Info";
});
</script>

<style scoped>
.metric-card {
  padding: 20px;
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.5), rgba(30, 41, 59, 0.4));
  border: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(12px);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.02);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.metric-card:hover {
  transform: translateY(-4px);
  box-shadow:
    0 0 15px rgba(0, 240, 255, 0.2),
    0 18px 36px rgba(2, 8, 23, 0.4);
}

.metric-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: #9fb3c8;
}

.metric-value {
  margin-top: 18px;
  font-size: 34px;
  font-weight: 700;
  color: #fff;
  font-family: var(--mono-font);
  font-variant-numeric: tabular-nums;
  text-shadow: 0 0 16px rgba(0, 240, 255, 0.18);
}

.metric-card p {
  margin: 10px 0 0;
  color: #7f94aa;
}
</style>
