<template>
  <section class="page-stack">
    <div class="page-lead">
      <div>
        <h2>系统健康与资源仪表盘</h2>
        <p>
          聚合当前模型状态、资源占用和最近任务的 RTF 走势。当前骨架优先打通前端视图，GPU 和 CPU
          指标在后端未提供前采用占位数据。
        </p>
      </div>
      <el-button type="primary" @click="refreshDashboard" :loading="store.loading">
        刷新状态
      </el-button>
    </div>

    <div class="metrics-grid">
      <MetricCard v-for="metric in store.metrics" :key="metric.label" :metric="metric" />
    </div>

    <div class="two-columns">
      <el-card class="panel cyber-glow" shadow="never">
        <template #header>
          <div class="panel-header">
            <div>
              <h3>模型管理</h3>
              <p>列出当前后端支持的模型，激活模型允许直接卸载。</p>
            </div>
          </div>
        </template>

        <el-table :data="store.modelRows" stripe class="dashboard-table">
          <el-table-column prop="name" label="模型名称" min-width="180" />
          <el-table-column label="状态" min-width="120">
            <template #default="{ row }">
              <el-tag :type="row.status === 'Active' ? 'success' : 'info'" round>
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140">
            <template #default="{ row }">
              <el-button
                size="small"
                type="danger"
                plain
                :disabled="!row.canUnload"
                @click="store.unloadModel()"
              >
                卸载模型
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <div class="page-stack">
        <el-card class="panel cyber-glow" shadow="never">
          <template #header>
            <div class="panel-header">
              <div>
                <h3>GPU 显存占用</h3>
                <p>环形图可快速判断是否接近资源阈值。</p>
              </div>
            </div>
          </template>
          <RingChart :value="store.gpuUsage" title="GPU Memory" />
        </el-card>

        <el-card class="panel cyber-glow" shadow="never">
          <template #header>
            <div class="panel-header">
              <div>
                <h3>最近任务 RTF 趋势</h3>
                <p>RTF 小于 1 通常代表处理速度快于实时音频。</p>
              </div>
            </div>
          </template>
          <TrendChart :points="store.rtfTrend" />
        </el-card>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from "vue";

import MetricCard from "../components/MetricCard.vue";
import RingChart from "../components/charts/RingChart.vue";
import TrendChart from "../components/charts/TrendChart.vue";
import { useSystemStore } from "../store/system";

const store = useSystemStore();

const refreshDashboard = async () => {
  await store.refreshDashboard();
};

onMounted(() => {
  void refreshDashboard();
});
</script>

<style scoped>
.metrics-grid {
  display: grid;
  gap: 18px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.dashboard-table :deep(.cell) {
  color: #dce7f4;
}

@media (max-width: 1280px) {
  .metrics-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .metrics-grid {
    grid-template-columns: 1fr;
  }
}
</style>
